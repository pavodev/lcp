from __future__ import annotations

import json
import os
import shutil
import traceback

from types import TracebackType
from typing import Any, Unpack, cast

from redis import Redis as RedisConnection
from rq.job import Job

from .configure import _get_batches
from .typed import MainCorpus, JSONObject, UserQuery, RawSent, Config, QueryArgs
from .utils import (
    CustomEncoder,
    Interrupted,
    _add_results,
    _get_status,
    _union_results,
    _row_to_value,
    PUBSUB_CHANNEL,
)
from .worker import SQLJob


def _query(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[tuple],
    **kwargs: Unpack[QueryArgs],  # type: ignore
) -> None:
    """
    Job callback, publishes a redis message containing the results
    """
    restart = kwargs.get("hit_limit", False)
    total_before_now = job.kwargs.get("total_results_so_far")
    results_so_far = job.kwargs.get("existing_results", {})
    results_so_far = {int(k): v for k, v in results_so_far.items()}
    meta_json = job.kwargs.get("meta_json")

    total_requested = (
        job.kwargs["total_results_requested"]
        if restart is False
        else kwargs["total_results_requested"]
    )
    done_part = job.kwargs["done_batches"]
    # this seemed to be wrong:
    # offset = job.kwargs.get("offset", False) if restart is False else False
    offset = restart if restart is not False else False

    if restart is False:
        needed = job.kwargs["needed"]
    else:
        needed = total_requested - total_before_now

    unlimited = needed == -1 or job.kwargs.get("simultaneous", False) or False

    aargs = (
        result,
        total_before_now,
        unlimited,
        offset,
        restart,
        total_requested,
    )

    new_res, n_results = _add_results(
        *aargs, kwic=False, meta=meta_json, is_vian=kwargs.get("is_vian", False)
    )

    total_found = total_before_now + n_results
    limited = not unlimited and total_found > job.kwargs["needed"]
    results_so_far = _union_results(results_so_far, new_res)
    limit = False if n_results < total_requested else total_found - total_requested

    just_finished = tuple(job.kwargs["current_batch"])
    done_part.append(just_finished)

    status = _get_status(total_found, tot_req=total_requested, **job.kwargs)
    hit_limit = False if not limited else needed
    job.meta["_status"] = status
    job.meta["hit_limit"] = hit_limit
    job.meta["total_results_so_far"] = total_found
    # the +1 could be wrong, maybe hit_limit should be -1?
    job.meta["start_at"] = 0 if restart is False else restart
    job.meta["_args"] = aargs[1:]
    # job.meta["lines_sent_to_fe"] = lines_sent_to_fe
    # job.meta["all_results"] = results_so_far

    if status == "finished":
        projected_results = total_found
        perc_words = 100.0
        perc_matches = 100.0
        job.meta["percentage_done"] = 100.0
    elif status in {"partial", "satisfied"}:
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([x[-1] for x in done_batches])
        proportion_that_matches = total_found / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
        perc_words = total_words_processed_so_far * 100.0 / job.kwargs["word_count"]
        perc_matches = min(total_found, total_requested) * 100.0 / total_requested
        job.meta["percentage_done"] = round(perc_matches, 3)
        # todo: can remove this for more accuracy if need be
        if total_requested < total_found:
            total_found = total_requested

    job.save_meta()  # type: ignore
    jso = dict(**job.kwargs)
    jso.update(
        {
            "result": results_so_far,
            "status": status,
            "job": job.id,
            "action": "query_result",
            "projected_results": projected_results,
            "percentage_done": round(perc_matches, 3),
            "percentage_words_done": round(perc_words, 3),
            "hit_limit": limit,
            "total_results_so_far": total_found,
            "batch_matches": n_results,
            "done_batches": done_part,
            "sentences": job.kwargs["sentences"],
            "total_results_requested": total_requested,
        }
    )
    jso["user"] = kwargs.get("user", jso["user"])
    jso["room"] = kwargs.get("room", jso["room"])

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _sentences(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[RawSent],
    **kwargs: int | bool | str | None,
) -> None:
    """
    Create KWIC data and send via websocket
    """
    total_requested = kwargs.get("total_results_requested")
    start_at = kwargs.get("start_at")

    base = Job.fetch(job.kwargs["base"], connection=connection)
    if "_sentences" not in base.meta:
        base.meta["_sentences"] = {}

    depends_on = job.kwargs["depends_on"]
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]

    depended = Job.fetch(depends_on, connection=connection)
    if "associated" not in depended.meta:
        depended.meta["associated"] = job.id
    depended.save_meta()  # type: ignore

    aargs: tuple[int, bool, Any, Any, Any] = depended.meta["_args"]
    if "total_results_requested" in kwargs:
        aargs = (aargs[0], aargs[1], start_at, aargs[3], total_requested)

    already = base.meta.get("already", [])

    if job.id not in already:
        already.append(job.id)
        base.meta["already"] = already
        new_res, _ = _add_results(
            depended.result,
            *aargs,
            kwic=True,
            sents=result,
            is_vian=depended.kwargs.get("is_vian", False),
            meta=depended.kwargs.get("meta_json"),
        )
        results_so_far = _union_results(base.meta["_sentences"], new_res)
    else:
        results_so_far = base.meta["_sentences"]

    if job.id not in already:
        base.meta["latest_sentences"] = job.id
        base.meta["_sentences"] = results_so_far

    base.save_meta()  # type: ignore

    jso = {
        "result": results_so_far,
        "status": depended.meta["_status"],
        "action": "sentences",
        "user": kwargs.get("user", job.kwargs["user"]),
        "room": kwargs.get("room", job.kwargs["room"]),
        "query": depended.id,
        "base": base.id,
        "percentage_done": round(depended.meta["percentage_done"], 3),
    }

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _document(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[JSONObject] | JSONObject,
) -> None:
    """
    When a user requests a document, we give it to them via websocket
    """
    user = job.kwargs["user"]
    room = job.kwargs["room"]
    if not room:
        return
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    jso = {
        "document": result,
        "action": "document",
        "user": user,
        "room": room,
        "corpus": job.kwargs["corpus"],
        "doc_id": job.kwargs["doc"],
    }
    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


def _document_ids(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[JSONObject] | JSONObject,
) -> None:
    """
    When a user requests a document, we give it to them via websocket
    """
    user = job.kwargs["user"]
    room = job.kwargs["room"]
    if not room:
        return
    formatted = {str(idx): name for idx, name in cast(list[tuple], result)}
    jso = {
        "document_ids": formatted,
        "action": "document_ids",
        "user": user,
        "room": room,
        "job": job.id,
        "corpus_id": job.kwargs["corpus_id"],
    }
    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


def _schema(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: bool | None = None,
) -> None:
    """
    This callback is executed after successful creation of schema.
    We might want to notify some WS user?
    """
    user = job.kwargs.get("user")
    room = job.kwargs.get("room")
    if not room:
        return
    jso = {
        "user": user,
        "status": "success" if not result else "error",
        "project": job.kwargs["project"],
        "project_name": job.kwargs["project_name"],
        "action": "uploaded",
        "gui": job.kwargs.get("gui", False),
        "room": room,
    }
    if result:
        jso["error"] = result

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _upload(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: MainCorpus | None,
) -> None:
    """
    Success callback when user has uploaded a dataset
    """
    if result is None:
        print("Result was none. Skipping callback.")
        return None
    project: str = job.args[0]
    user: str = job.args[1]
    room: str | None = job.args[2]
    user_data: JSONObject = job.kwargs["user_data"]
    is_vian: bool = job.kwargs["is_vian"]
    gui: bool = job.kwargs["gui"]

    if not room or not result:
        return
    jso = {
        "user": user,
        "room": room,
        "id": result[0],
        "user_data": user_data,
        "is_vian": is_vian,
        "entry": _row_to_value(result, project=project),
        "status": "success" if not result else "error",
        "project": project,
        "action": "uploaded",
        "gui": gui,
    }
    if result:
        jso["error"] = result

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _upload_failure(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    typ: type,
    value: BaseException,
    trace: Any,
) -> None:
    """
    Cleanup on upload fail, and maybe send ws message
    """
    print(f"Upload failure: {typ} : {value}: {traceback}")

    project: str
    user: str
    room: str | None

    if "project_name" in job.kwargs:  # it came from create schema job
        project = job.kwargs["project"]
        user = job.kwargs["user"]
        room = job.kwargs["room"]
    else:  # it came from upload job
        project = job.args[0]
        user = job.args[1]
        room = job.args[2]

    path = os.path.join("uploads", project)
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Deleted: {path}")

    form_error: str = str(trace)

    try:
        form_error = "".join(traceback.format_tb(trace))
    except Exception as err:
        print(f"cannot format object: {trace} / {err}")

    if user and room:
        jso = {
            "user": user,
            "room": room,
            "project": project,
            "action": "upload_fail",
            "status": "failed",
            "job": job.id,
            "traceback": form_error,
            "kind": str(typ),
            "value": str(value),
        }
        red = job._redis if hasattr(job, "_redis") else connection
        red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


def _general_failure(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    typ: type,
    value: BaseException,
    trace: TracebackType,
) -> None:
    """
    On job failure, return some info ... probably hide some of this from prod eventually!
    """
    form_error: str = str(trace)
    try:
        form_error = "".join(traceback.format_tb(trace))
    except Exception as err:
        print(f"cannot format object: {trace} / {err}")

    print("Failure of some kind:", job, trace, typ, value)
    if isinstance(typ, Interrupted) or typ == Interrupted:
        # jso = {"status": "interrupted", "action": "interrupted", "job": job.id, **kwargs, **job.kwargs}
        return  # do we need to send this?
    else:
        jso = {
            "status": "failed",
            "kind": str(typ),
            "value": str(value),
            "action": "failed",
            "traceback": form_error,
            "job": job.id,
            **job.kwargs,
        }
    # this is just for consistency with the other timeout messages
    if "No such job" in jso["value"]:
        jso["status"] = "timeout"
        jso["action"] = "timeout"

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _queries(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[UserQuery] | None,
) -> None:
    """
    Fetch or store queries
    """
    is_store: bool = job.kwargs.get("store", False)
    action = "store_query" if is_store else "fetch_queries"
    room: str | None = job.kwargs.get("room")
    jso: dict[str, Any] = {
        "user": str(job.kwargs["user"]),
        "room": room,
        "status": "success",
        "action": action,
        "queries": [],
    }
    if is_store:
        jso["query_id"] = str(job.kwargs["query_id"])
        jso.pop("queries")
    elif result:
        cols = ["idx", "query", "username", "room", "created_at"]
        queries: list[dict[str, Any]] = []
        for x in result:
            dct: dict[str, Any] = dict(zip(cols, x))
            queries.append(dct)
        jso["queries"] = queries
    made = json.dumps(jso, cls=CustomEncoder)
    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, made)


def _config(
    job: SQLJob | Job, connection: RedisConnection[bytes], result: list[MainCorpus]
) -> None:
    """
    Run by worker: make config data
    """
    fixed: Config = {}
    for tup in result:
        made = _row_to_value(tup)
        if not made["enabled"]:
            continue
        fixed[str(made["corpus_id"])] = made

    for name, conf in fixed.items():
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    jso: dict[str, str | bool | Config] = {
        "config": fixed,
        "_is_config": True,
        "action": "set_config",
    }
    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))

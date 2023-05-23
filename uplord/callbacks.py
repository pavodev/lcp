from __future__ import annotations

import json

from datetime import datetime
from types import TracebackType
from typing import Any, Dict, List, Tuple, Type
from uuid import UUID

from redis import Redis as RedisConnection
from rq.job import Job

from .configure import _get_batches
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
    job: SQLJob | Job, connection: RedisConnection, result: List[Tuple], **kwargs
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

    choices = {-1, False, None}
    unlimited = needed in choices or job.kwargs.get("simultaneous", False) or False

    aargs = (
        result,
        total_before_now,
        unlimited,
        offset,
        restart,
        total_requested,
    )

    new_res, n_results = _add_results(*aargs, kwic=False, meta=meta_json)

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

    job.save_meta()
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

    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _sentences(
    job: SQLJob | Job,
    connection: RedisConnection,
    result: List[Tuple[str | UUID, int, List[Any]]],
    **kwargs,
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
    depended.save_meta()

    aargs: Tuple[int, bool, Any, Any, Any] = depended.meta["_args"]
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
            meta=depended.kwargs.get("meta_json"),
        )
        results_so_far = _union_results(base.meta["_sentences"], new_res)
    else:
        results_so_far = base.meta["_sentences"]

    if job.id not in already:
        base.meta["latest_sentences"] = job.id
        base.meta["_sentences"] = results_so_far

    base.save_meta()

    jso = {
        "result": results_so_far,
        "status": depended.meta["_status"],
        "action": "sentences",
        "user": job.kwargs["user"],
        "room": job.kwargs["room"],
        "query": depended.id,
        "base": base.id,
        "percentage_done": round(depended.meta["percentage_done"], 3),
    }
    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _document(
    job: SQLJob | Job,
    connection: RedisConnection,
    result: List[Dict[str, Any]] | Dict[str, Any],
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
        "doc_id": job.args[-1][0],
    }
    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


def _schema(
    job: SQLJob | Job,
    connection: RedisConnection,
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

    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))  # type: ignore


def _upload(
    job: SQLJob | Job,
    connection: RedisConnection,
    result: Tuple = tuple(),
) -> None:
    """
    Success callback when user has uploaded a dataset
    """
    project: str = job.args[0]
    user: str = job.args[1]
    room: str | None = job.args[2]
    user_data: Dict[str, Any] = job.kwargs["user_data"]
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

    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))  # type: ignore


def _general_failure(
    job: SQLJob | Job,
    connection: RedisConnection,
    typ: Type,
    value: BaseException,
    traceback: TracebackType,
) -> None:
    """
    On job failure, return some info ... probably hide some of this from prod eventually!
    """
    print("Failure of some kind:", job, traceback, typ, value)
    if isinstance(typ, Interrupted) or typ == Interrupted:
        # jso = {"status": "interrupted", "action": "interrupted", "job": job.id, **kwargs, **job.kwargs}
        return  # do we need to send this?
    else:
        jso = {
            "status": "failed",
            "kind": str(typ),
            "value": str(value),
            "traceback": str(traceback),
            "job": job.id,
            **job.kwargs,
        }
    # this is just for consistency with the other timeout messages
    if "No such job" in jso["value"]:
        jso["status"] = "timeout"
        jso["action"] = "timeout"

    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))  # type: ignore


def _queries(
    job: SQLJob | Job,
    connection: RedisConnection,
    result: List[Tuple[str, Dict, str, str | None, datetime]] | None,
) -> None:
    """
    Fetch or store queries
    """
    is_store = job.kwargs.get("store")
    action = "store_query" if is_store else "fetch_queries"
    room = job.kwargs.get("room")
    jso: Dict[str, Any] = {
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
        queries: List[Dict[str, Any]] = []
        for x in result:
            dct: Dict[str, Any] = dict(zip(cols, x))
            queries.append(dct)
        jso["queries"] = queries
    made = json.dumps(jso, cls=CustomEncoder)
    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, made)  # type: ignore


def _config(job: SQLJob | Job, connection: RedisConnection, result=List[Tuple]) -> None:
    """
    Run by worker: make config data
    """
    fixed: Dict[str, Dict[str, int | str | bool | Dict[str, Any]]] = {"-1": {}}
    disabled: List[Tuple[str, int]] = []
    for tup in result:
        made = _row_to_value(tup)
        if not made["enabled"]:
            disabled.append((made["name"], made["corpus_id"]))
        fixed[str(made["corpus_id"])] = made

    for name, conf in fixed.items():
        if name == "-1":
            continue
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    jso = {
        "config": fixed,
        "_is_config": True,
        "action": "set_config",
        "disabled": disabled,
    }
    red = job._redis if hasattr(job, "_redis") else connection  # type: ignore
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))  # type: ignore

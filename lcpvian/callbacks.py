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
from .convert import _aggregate_results, _format_kwics
from .typed import (
    MainCorpus,
    JSONObject,
    UserQuery,
    RawSent,
    Config,
    QueryArgs,
    Results,
    Batch,
    QueryMeta,
)
from .utils import (
    CustomEncoder,
    Interrupted,
    _get_status,
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

    This is where we need to aggregate statistics over all jobs in the group
    """
    table = f"{job.kwargs['current_batch'][1]}.{job.kwargs['current_batch'][2]}"
    allowed_time = float(os.getenv("QUERY_ALLOWED_JOB_TIME", 0.0))
    duration = (job.ended_at - job.started_at).total_seconds()
    total_duration = job.kwargs.get("total_duration", 0.0) + duration
    duration_string = f"Duration ({table}): {duration} :: {total_duration}"
    from_memory = kwargs.get("from_memory", False)

    meta_json: QueryMeta = job.kwargs.get("meta_json")
    existing_results: Results = {0: meta_json}
    first_job = job
    if job.kwargs.get("first_job"):
        first_job = Job.fetch(job.kwargs["first_job"], connection=connection)

    existing_results = first_job.meta.get("all_non_kwic_results", existing_results)
    total_requested = kwargs.get(
        "total_results_requested", job.kwargs["total_results_requested"]
    )

    post_processes = job.kwargs.get("post_processes", {})
    stored = first_job.meta.get("progress_info", {})

    if from_memory:
        all_res = existing_results
        to_send = existing_results
        n_res = stored["total_results_so_far"]
        search_all = stored["search_all"]
        show_total = stored["show_total"]
    else:
        all_res, to_send, n_res, search_all, show_total = _aggregate_results(
            result, existing_results, meta_json, post_processes, total_requested
        )
        first_job.meta["all_non_kwic_results"] = all_res

    time_perc = 0.0
    if allowed_time > 0.0 and search_all:
        time_perc = total_duration * 100.0 / allowed_time

    total_before_now = job.kwargs.get("total_results_so_far")
    done_part = job.kwargs["done_batches"]
    total_found = total_before_now + n_res if show_total else -1
    just_finished = tuple(job.kwargs["current_batch"])
    done_part.append(just_finished)
    status = _get_status(
        total_found,
        tot_req=total_requested,
        search_all=search_all,
        time_so_far=total_duration,
        **job.kwargs,
    )
    job.meta["_status"] = status
    job.meta["results_this_batch"] = n_res
    job.meta["cut_short"] = total_requested if n_res > total_requested else -1
    # job.meta["_job_duration"] = duration
    # job.meta["_total_duration"] = total_duration
    job.meta["total_results_so_far"] = total_found

    if status == "finished":
        projected_results = total_found if show_total else -1
        perc_words = 100.0
        perc_matches = 100.0
        if search_all:
            perc_matches = time_perc
        job.meta["percentage_done"] = 100.0
    elif status in {"partial", "satisfied", "overtime"}:
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([x[-1] for x in done_batches])
        proportion_that_matches = total_found / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
        if not show_total:
            projected_results = -1
        perc_words = total_words_processed_so_far * 100.0 / job.kwargs["word_count"]
        perc_matches = min(total_found, total_requested) * 100.0 / total_requested
        if search_all:
            perc_matches = time_perc
        job.meta["percentage_done"] = round(perc_matches, 3)

    if from_memory:

        projected_results = stored["projected_results"]
        perc_matches = stored["percentage_done"]
        perc_words = stored["percentage_words_done"]
        total_found = stored["total_results_so_far"]
        n_res = stored["batch_matches"]

    progress_info = {
        "projected_results": projected_results,
        "percentage_done": round(perc_matches, 3),
        "percentage_words_done": round(perc_words, 3),
        "total_results_so_far": total_found,
        "batch_matches": n_res,
        "show_total": show_total,
        "search_all": search_all,
    }

    if "_sent_jobs" not in first_job.meta:
        first_job.meta["_sent_jobs"] = {}

    first_job.meta["progress_info"] = progress_info

    first_job.save_meta()  # type: ignore
    job.save_meta()  # type: ignore
    jso = dict(**job.kwargs)
    jso.update(
        {
            "result": to_send,
            "full_result": all_res,
            "status": status,
            "job": job.id,
            "action": "query_result",
            "projected_results": projected_results,
            "percentage_done": round(perc_matches, 3),
            "percentage_words_done": round(perc_words, 3),
            "from_memory": from_memory,
            "duration_string": duration_string,
            "total_results_so_far": total_found,
            "table": table,
            "first_job": first_job.id,
            "search_all": search_all,
            "batch_matches": n_res,
            "do_not_send": kwargs.get("do_not_send", False),
            "do_not_send_next": from_memory,
            "done_batches": done_part,
            "total_duration": total_duration,
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
    trr = "total_results_requested"
    total_requested = cast(int, kwargs.get(trr, job.kwargs[trr]))
    if not total_requested:
        total_requested = -1

    base = Job.fetch(job.kwargs["first_job"], connection=connection)
    base.meta["_sent_jobs"][job.id] = None
    base.save_meta()

    depends_on = job.kwargs["depends_on"]
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]

    depended = Job.fetch(depends_on, connection=connection)
    if job.kwargs["first_job"] != depends_on:
        total_requested = -1
    meta_json = depended.kwargs["meta_json"]
    is_vian = depended.kwargs.get("is_vian", False)
    is_first = not bool(depended.kwargs.get("first_job", ""))
    resuming = job.kwargs.get("resuming", False)
    offset = depended.meta.get("cut_short", -1) if resuming else -1
    to_send = _format_kwics(
        depended.result, meta_json, result, total_requested, is_vian, is_first, offset
    )
    cb: Batch = depended.kwargs["current_batch"]
    table = f"{cb[1]}.{cb[2]}"

    if len(to_send) < 3:
        print(f"No sentences found for {table} -- skipping WS message")
        return None

    jso = {
        "result": to_send,
        "status": depended.meta["_status"],
        "action": "sentences",
        "user": kwargs.get("user", job.kwargs["user"]),
        "room": kwargs.get("room", job.kwargs["room"]),
        "query": depended.id,
        "table": table,
        "first_job": base.id,
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
        # no need to send a message to the user for interrupts
        # jso = {"status": "interrupted", "action": "interrupted", "job": job.id}
        return
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
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[MainCorpus],
    publish: bool = True,
) -> dict[str, str | bool | Config]:
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
    if publish:
        red = job._redis if hasattr(job, "_redis") else connection
        red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return jso

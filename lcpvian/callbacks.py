"""
RQ Callbacks: post-process the result of an SQL query and broadcast
it to the relevant websockets

These jobs are usually run in the worker process, but in exceptional
circumstances, they are run in the main thread, like when fetching
jobs that were run earlier

These callbacks are hooked up as on_success and on_failure kwargs in
calls to Queue.enqueue in query_service.py
"""

from __future__ import annotations

import json
import os
import shutil
import traceback

from datetime import datetime
from types import TracebackType
from typing import Any, Unpack, cast
from uuid import uuid4

from redis import Redis as RedisConnection
from rq.job import Job

from .configure import _get_batches
from .convert import _aggregate_results, _format_kwics, _apply_filters, _get_all_sents
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
    _get_associated_query_job,
    PUBSUB_CHANNEL,
)
from .worker import SQLJob


def _get_first_job(
    job: SQLJob | Job, connection: RedisConnection[bytes]
) -> SQLJob | Job:
    """
    Helper to get the base job from a group of query jobs
    """
    first_job = job
    if job.kwargs.get("first_job"):
        first_job = Job.fetch(job.kwargs["first_job"], connection=connection)
    if "_sent_jobs" not in first_job.meta:
        first_job.meta["_sent_jobs"] = {}
    return first_job


def _query(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[tuple],
    **kwargs: Unpack[QueryArgs],  # type: ignore
) -> None:
    """
    Job callback, publishes a redis message containing the results

    This is where we need to aggregate statistics over all jobs in the group

    This callback can be run either in the worker or the main thread, and needs
    to handle normal queries, as well as queries fetched from redis memory

    When a new query is submitted, the QueryIteration object and the RQ Job
    object have an empty string as the `first_job` attribute/key. For subsequent
    batches, `first_job` is the initial job id. On this job's `meta`, we store
    the aggregated results that are calculated during this callback. Then we
    apply post_processes filters and send the result as a WS message.
    """
    table = f"{job.kwargs['current_batch'][1]}.{job.kwargs['current_batch'][2]}"
    allowed_time = float(os.getenv("QUERY_ALLOWED_JOB_TIME", 0.0))
    ended_at = cast(datetime, job.ended_at)
    started_at = cast(datetime, job.started_at)
    duration: float = round((ended_at - started_at).total_seconds(), 3)
    total_duration = round(job.kwargs.get("total_duration", 0.0) + duration, 3)
    duration_string = f"Duration ({table}): {duration} :: {total_duration}"
    from_memory = kwargs.get("from_memory", False)
    meta_json: QueryMeta = job.kwargs.get("meta_json")
    existing_results: Results = {0: meta_json}
    post_processes = job.kwargs.get("post_processes", {})
    is_base = not bool(job.kwargs.get("first_job"))
    total_before_now = job.kwargs["total_results_so_far"]
    done_part = job.kwargs["done_batches"]
    is_full = kwargs.get("full", job.kwargs["full"])

    first_job = _get_first_job(job, connection)
    stored = first_job.meta.get("progress_info", {})
    existing_results = first_job.meta.get("all_non_kwic_results", existing_results)
    total_requested = kwargs.get(
        "total_results_requested", job.kwargs["total_results_requested"]
    )

    if total_requested > job.meta.get("highest_requested", 0):
        job.meta["highest_requested"] = total_requested

    # ensure we don't send this same result again later if we don't need to
    send_stats = job.meta.get("_already_sent", False) and not (is_base and from_memory)
    job.meta["_already_sent"] = True

    # if from memory, we had this result cached, we just need to apply filters
    if from_memory:
        all_res = existing_results
        to_send = _apply_filters(all_res, post_processes)
        n_res = stored["total_results_so_far"]
        search_all = stored["search_all"]
        show_total = stored["show_total"]
    # if not cached, we do all the aggregation and filtering of previous+current result
    else:
        all_res, to_send, n_res, search_all, show_total = _aggregate_results(
            result, existing_results, meta_json, post_processes
        )
        first_job.meta["all_non_kwic_results"] = all_res

    # right now, when a job has no kwic element, we query all batches and only stop
    # if a time limit is reached. so the progress bar can reflect the amount of time used
    time_perc = 0.0
    if allowed_time > 0.0 and search_all:
        time_perc = total_duration * 100.0 / allowed_time

    total_found = total_before_now + n_res if show_total else -1

    offset_for_next_time = 0
    if total_before_now + n_res > total_requested:
        offset_for_next_time = total_requested - total_before_now

    job.meta["offset_for_next_time"] = offset_for_next_time

    just_finished = tuple(job.kwargs["current_batch"])
    done_part.append(just_finished)
    status = _get_status(
        total_found,
        done_batches=done_part,
        all_batches=job.kwargs["all_batches"],
        total_results_requested=total_requested,
        search_all=search_all,
        full=job.kwargs.get("full", False),
        time_so_far=total_duration,
    )
    job.meta["_status"] = status
    job.meta["_full"] = is_full
    job.meta["results_this_batch"] = n_res
    job.meta["total_results_requested"] = total_requested  # todo: can't this change!?
    job.meta["_search_all"] = search_all
    job.meta["_total_duration"] = total_duration
    job.meta["total_results_so_far"] = total_found

    batches_done_string = f"{len(done_part)}/{len(job.kwargs['all_batches'])}"

    # in these next conditions we basically build the progress information
    # for a query, based on its status and batch metadata.
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
        batches_done_string = stored["batches_done_string"]
        status = stored["status"]
        total_duration = stored["total_duration"]

    progress_info = {
        "projected_results": projected_results,
        "percentage_done": round(perc_matches, 3),
        "percentage_words_done": round(perc_words, 3),
        "total_results_so_far": total_found,
        "batch_matches": n_res,
        "show_total": show_total,
        "search_all": search_all,
        "batches_done_string": batches_done_string,
        "total_duration": total_duration,
        "status": status,
    }

    # so we do not override newer data with older data?
    info: dict[str, str | bool | int | float] = first_job.meta.get("progress_info", {})
    latest_total = cast(int, info.get("total_results_so_far", -1))
    is_latest = not info or total_found > latest_total
    if is_latest:
        first_job.meta["progress_info"] = progress_info

    can_send = not is_full or status == "finished"
    msg_id = str(uuid4())  # todo: hash instead?

    if "latest_stats_message" not in first_job.meta:
        first_job.meta["latest_stats_message"] = msg_id
    if job.meta["total_results_so_far"] >= first_job.meta["total_results_so_far"]:
        first_job.meta["latest_stats_message"] = msg_id

    first_job.save_meta()  # type: ignore

    use = perc_words if search_all or is_full else perc_matches
    time_remaining = _time_remaining(status, total_duration, use)

    user = cast(str, kwargs.get("user", job.kwargs["user"]))
    room = cast(str | None, kwargs.get("room", job.kwargs["room"]))

    jso = dict(**job.kwargs)
    jso.update(
        {
            "result": to_send,
            "full_result": all_res,
            "user": user,
            "room": room,
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
            "send_stats": send_stats,
            "first_job": first_job.id,
            "search_all": search_all,
            "batches_done": batches_done_string,
            "batch_matches": n_res,
            "full": is_full,
            "can_send": can_send,
            "done_batches": done_part,
            "msg_id": msg_id,
            "resume": False,
            "duration": duration,
            "offset": offset_for_next_time,
            "total_duration": total_duration,
            "remaining": time_remaining,
            "total_results_requested": total_requested,
        }
    )

    if job.kwargs["debug"] and job.kwargs["sql"]:
        jso["sql"] = job.kwargs["sql"]

    if is_full and status != "finished":
        jso["progress"] = {
            "remaining": time_remaining,
            "first_job": first_job.id,
            "job": job.id,
            "user": user,
            "room": room,
            "duration": duration,
            "total_duration": total_duration,
            "projected_results": projected_results,
            "percentage_done": round(perc_matches, 3),
            "percentage_words_done": round(perc_words, 3),
            "total_results_so_far": total_found,
            "action": "background_job_progress",
        }

    job.meta["payload"] = jso
    job.save_meta()  # type: ignore

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


def _time_remaining(status: str, total_duration: float, use: float) -> float:
    """
    Helper to estimate remaining time for a job
    """
    if status == "finished":
        return 0.0
    if use <= 0.0:
        return 0.0
    timed = (total_duration * (100.0 / use)) - total_duration
    return max(0.0, timed)


def _get_total_requested(kwargs: dict[str, Any], job: Job | SQLJob) -> int:
    """
    A helper to find the total requested -- remove this after cleanup ideally
    """
    total_requested = cast(int, kwargs.get("total_results_requested", -1))
    if total_requested > 0:
        return total_requested
    total_requested = job.kwargs.get("total_results_requested", -1)
    if total_requested > 0:
        return total_requested
    return -1


def _sentences(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[RawSent] | None,
    **kwargs: int | bool | str | None,
) -> None:
    """
    Create KWIC data and send via websocket
    """

    total_requested = _get_total_requested(kwargs, job)

    base = Job.fetch(job.kwargs["first_job"], connection=connection)

    depended = _get_associated_query_job(job.kwargs["depends_on"], connection)

    if total_requested > depended.meta.get("highest_requested", 0):
        depended.meta["highest_requested"] = total_requested

    if result:
        # _sents_job is a dict of {job_id: None} (so the keys are an ordered set)
        base.meta["_sent_jobs"][job.id] = None

    full = kwargs.get("full", job.kwargs.get("full", depended.meta.get("_full", False)))
    meta_json = depended.kwargs["meta_json"]
    is_vian = depended.kwargs.get("is_vian", False)
    # todo: are we really doing this thing about only first batch being limited?
    # if job.kwargs["first_job"] != depends_on:
    #    total_requested = -1
    # is_first = not bool(depended.kwargs.get("first_job", ""))
    # if is_first is False, it can trigger the 'get all kwic for non-first batch' idea
    is_first = True

    # get the offset/limit for kwic lines
    resume = cast(bool, job.kwargs.get("resume", False))
    offset = cast(int, job.kwargs.get("offset", 0) if resume else -1)
    prev_offset = cast(int, depended.meta.get("latest_offset", -1))
    if prev_offset > offset and not kwargs.get("from_memory"):
        offset = prev_offset
    total_to_get = job.kwargs.get("needed", total_requested)

    cb: Batch = depended.kwargs["current_batch"]
    table = f"{cb[1]}.{cb[2]}"
    total_so_far = depended.meta["total_results_so_far"]

    # status is calculated here on the offchance it is possible for a sent
    # job to have a different status from its associated query result?
    done_batches = depended.kwargs["done_batches"]
    if depended.kwargs["current_batch"] not in done_batches:
        done_batches.append(depended.kwargs["current_batch"])
    status = _get_status(
        total_so_far,
        done_batches=done_batches,
        all_batches=depended.kwargs["all_batches"],
        total_results_requested=total_requested,
        search_all=depended.meta["_search_all"],
        full=depended.kwargs.get("full", False),
        time_so_far=depended.meta["_total_duration"],
    )
    depended.meta["_status"] = status

    latest_offset = max(offset, 0) + total_to_get
    depended.meta["latest_offset"] = latest_offset

    # in full mode, we need to combine all the sentences into one message when finished
    get_all_sents = full and status == "finished"
    if get_all_sents:
        to_send, n_res = _get_all_sents(job, base, is_vian, meta_json, connection)
    else:
        to_send, n_res = _format_kwics(
            depended.result, meta_json, result, total_to_get, is_vian, is_first, offset
        )

    depended.save_meta()

    submit_query = job.kwargs["start_query_from_sents"]

    # if to_send contains only {0: meta, -1: sentences} or less
    if len(to_send) < 3 and not submit_query:
        print(f"No results found for {table} -- skipping WS message")
        return None

    perc_done = round(base.meta["progress_info"]["percentage_done"], 3)
    perc_done_base = base.meta.get("progress_info", {}).get("percentage_done", 0)
    perc_done = max(perc_done, perc_done_base)

    words_done = round(base.meta["progress_info"]["percentage_words_done"], 3)
    words_done_base = base.meta.get("progress_info", {}).get("percentage_words_done", 0)
    words_done = max(words_done, words_done_base)

    submit_payload = depended.meta["payload"]
    submit_payload["full"] = full
    submit_payload["total_results_requested"] = total_requested

    can_send = not full or status == "finished"
    msg_id = str(uuid4())  # todo: hash instead!
    if "sent_job_ws_messages" not in base.meta:
        base.meta["sent_job_ws_messages"] = {}
    base.meta["sent_job_ws_messages"][msg_id] = None
    base.save_meta()

    jso = {
        "result": to_send,
        "status": status,
        "action": "sentences",
        "full": full,
        "submit_query": submit_payload if submit_query else False,
        "user": kwargs.get("user", job.kwargs["user"]),
        "room": kwargs.get("room", job.kwargs["room"]),
        "query": depended.id,
        "table": table,
        "first_job": base.id,
        "msg_id": msg_id,
        "can_send": can_send,
        "percentage_done": perc_done,
        "percentage_words_done": words_done,
    }

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


def _document(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[JSONObject] | JSONObject,
    **kwargs,
) -> None:
    """
    When a user requests a document, we give it to them via websocket
    """
    user = cast(str, kwargs.get("user", job.kwargs["user"]))
    room = cast(str | None, kwargs.get("room", job.kwargs["room"]))
    if not room:
        return
    if isinstance(result, list) and len(result) == 1:
        result = result[0]

    msg_id = str(uuid4())
    jso = {
        "document": result,
        "action": "document",
        "user": user,
        "room": room,
        "msg_id": msg_id,
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
    **kwargs,
) -> None:
    """
    When a user requests a document, we give it to them via websocket
    """
    user = cast(str, kwargs.get("user", job.kwargs["user"]))
    room = cast(str | None, kwargs.get("room", job.kwargs["room"]))
    if not room:
        return None
    msg_id = str(uuid4())
    formatted = {str(idx): name for idx, name in cast(list[tuple], result)}
    jso = {
        "document_ids": formatted,
        "action": "document_ids",
        "user": user,
        "msg_id": msg_id,
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
        return None
    msg_id = str(uuid4())
    jso = {
        "user": user,
        "status": "success" if not result else "error",
        "project": job.kwargs["project"],
        "project_name": job.kwargs["project_name"],
        "action": "uploaded",
        "gui": job.kwargs.get("gui", False),
        "room": room,
        "msg_id": msg_id,
    }
    if result:
        jso["error"] = result

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


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
    msg_id = str(uuid4())

    if not room or not result:
        return None
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
        "msg_id": msg_id,
    }
    if result:
        jso["error"] = result

    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


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
        return None
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
    return None


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
    msg_id = str(uuid4())
    jso: dict[str, Any] = {
        "user": str(job.kwargs["user"]),
        "room": room,
        "status": "success",
        "action": action,
        "queries": [],
        "msg_id": msg_id,
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
    return None


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
    msg_id = str(uuid4())
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
        "msg_id": msg_id,
    }
    if publish:
        red = job._redis if hasattr(job, "_redis") else connection
        red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return jso

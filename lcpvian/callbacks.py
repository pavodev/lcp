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

from redis import Redis as RedisConnection
from rq.job import Job

from .configure import _get_batches
from .convert import _aggregate_results, _format_kwics, _apply_filters
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
    """
    table = f"{job.kwargs['current_batch'][1]}.{job.kwargs['current_batch'][2]}"
    allowed_time = float(os.getenv("QUERY_ALLOWED_JOB_TIME", 0.0))
    ended_at = cast(datetime, job.ended_at)
    started_at = cast(datetime, job.started_at)
    duration: float = (ended_at - started_at).total_seconds()
    total_duration = job.kwargs.get("total_duration", 0.0) + duration
    duration_string = f"Duration ({table}): {duration} :: {total_duration}"
    from_memory = kwargs.get("from_memory", False)
    meta_json: QueryMeta = job.kwargs.get("meta_json")
    existing_results: Results = {0: meta_json}
    post_processes = job.kwargs.get("post_processes", {})
    is_base = not bool(job.kwargs.get("first_job"))
    total_before_now = job.kwargs["total_results_so_far"]
    done_part = job.kwargs["done_batches"]

    first_job = _get_first_job(job, connection)
    stored = first_job.meta.get("progress_info", {})
    existing_results = first_job.meta.get("all_non_kwic_results", existing_results)
    total_requested = kwargs.get(
        "total_results_requested", job.kwargs["total_results_requested"]
    )

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
    job.meta["results_this_batch"] = n_res
    job.meta["_search_all"] = search_all
    job.meta["cut_short"] = total_requested if n_res > total_requested else -1
    # job.meta["_job_duration"] = duration
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

    progress_info = {
        "projected_results": projected_results,
        "percentage_done": round(perc_matches, 3),
        "percentage_words_done": round(perc_words, 3),
        "total_results_so_far": total_found,
        "batch_matches": n_res,
        "show_total": show_total,
        "search_all": search_all,
        "batches_done_string": batches_done_string,
        "status": status,
    }

    # so we do not override newer data with older data?
    is_latest = not first_job.meta.get(
        "progress_info"
    ) or total_found > first_job.meta.get("progress_info", {}).get(
        "total_results_so_far", -1
    )
    if is_latest:
        first_job.meta["progress_info"] = progress_info

    first_job.save_meta()  # type: ignore

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
            "send_stats": send_stats,
            "first_job": first_job.id,
            "search_all": search_all,
            "batches_done_string": batches_done_string,
            "batch_matches": n_res,
            "done_batches": done_part,
            "total_duration": total_duration,
            "sentences": job.kwargs["sentences"],
            "total_results_requested": total_requested,
        }
    )
    job.meta["payload"] = jso
    jso["user"] = kwargs.get("user", jso["user"])
    jso["room"] = kwargs.get("room", jso["room"])
    job.save_meta()  # type: ignore
    red = job._redis if hasattr(job, "_redis") else connection
    red.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


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


def _get_associated_query_job(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
) -> SQLJob | Job:
    """
    Helper to find the query job associated with sent job
    """
    depends_on = job.kwargs["depends_on"]
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]
    depended = Job.fetch(depends_on, connection=connection)
    return depended


def _sentences(
    job: SQLJob | Job,
    connection: RedisConnection[bytes],
    result: list[RawSent],
    **kwargs: int | bool | str | None,
) -> None:
    """
    Create KWIC data and send via websocket
    """
    total_requested = _get_total_requested(kwargs, job)

    base = Job.fetch(job.kwargs["first_job"], connection=connection)
    # _sents_job is a dict of {job_id: None} (so the keys are an ordered set)
    base.meta["_sent_jobs"][job.id] = None
    base.save_meta()

    depended = _get_associated_query_job(job, connection)

    meta_json = depended.kwargs["meta_json"]
    is_vian = depended.kwargs.get("is_vian", False)
    # todo: are we really doing this thing about only first batch being limited?
    # if job.kwargs["first_job"] != depends_on:
    #    total_requested = -1
    # is_first = not bool(depended.kwargs.get("first_job", ""))
    # if is_first is False, it can trigger the 'get all kwic for non-first batch' idea
    is_first = True

    # get the offset/limit for kwic lines
    resuming = job.kwargs.get("resuming", False)
    offset = job.kwargs.get("offset", 0) if resuming else -1
    total_to_get = job.kwargs.get("needed", total_requested)

    to_send, n_res = _format_kwics(
        depended.result, meta_json, result, total_to_get, is_vian, is_first, offset
    )
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

    new_cut_short = total_requested if n_res > total_requested else -1
    if new_cut_short > depended.meta.get("cut_short", -1):
        depended.meta["cut_short"] = new_cut_short
        depended.save_meta()

    # if send_stats is False, the previous query was a kwic pagination
    # query where only kwic results were needed. if this is the case, and if
    # this batch didn't contain enough kwic results, we set submit_query to true
    # so that we can submit a new query for the next batch from the sentences
    # action in sock.py
    not_otherwise_started = depended.kwargs.get("send_stats", True) is False
    submit_query = n_res < total_requested and not_otherwise_started

    # if to_send contains only {0: meta, -1: sentences} or less
    if len(to_send) < 3 and not submit_query:
        print(f"No results found for {table} -- skipping WS message", to_send)
        return None

    perc_done = round(base.meta["progress_info"]["percentage_done"], 3)
    perc_done_base = base.meta.get("progress_info", {}).get("percentage_done", 0)
    perc_done = max(perc_done, perc_done_base)

    words_done = round(base.meta["progress_info"]["percentage_words_done"], 3)
    words_done_base = base.meta.get("progress_info", {}).get("percentage_words_done", 0)
    words_done = max(words_done, words_done_base)

    jso = {
        "result": to_send,
        "status": status,
        "action": "sentences",
        "submit_query": depended.meta["payload"] if submit_query else False,
        "user": kwargs.get("user", job.kwargs["user"]),
        "room": kwargs.get("room", job.kwargs["room"]),
        "query": depended.id,
        "table": table,
        "first_job": base.id,
        "percentage_done": perc_done,
        "percentage_words_done": words_done,
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

"""
callbacks.py: post-process the result of an SQL query and broadcast
it to the relevant websockets

These jobs are usually run in the worker process, but in exceptional
circumstances, they are run in the main thread, like when fetching
jobs that were run earlier

These callbacks are hooked up as on_success and on_failure kwargs in
calls to Queue.enqueue in query_service.py
"""

import duckdb
import json
import os
import pandas
import shutil
import traceback

from datetime import datetime
from types import TracebackType
from typing import Any, Unpack, cast
from uuid import uuid4

from redis import Redis as RedisConnection
from rq.job import Job

from .configure import _get_batches
from .convert import (
    _aggregate_results,
    _format_kwics,
    _apply_filters,
    _get_all_sents,
)
from .exporter import Exporter
from .jobfuncs import _handle_export
from .typed import (
    BaseArgs,
    Batch,
    Config,
    DocIDArgs,
    JSONObject,
    MainCorpus,
    QueryArgs,
    RequestInfo,
    QueryMeta,
    RawSent,
    Results,
    SentJob,
    UserQuery,
)
from .utils import (
    CustomEncoder,
    Interrupted,
    _get_request_info,
    _update_request_info,
    _get_query_info,
    _update_query_info,
    _get_status,
    _row_to_value,
    _get_associated_query_job,
    _get_first_job,
    _get_progress,
    _get_total_requested,
    _decide_can_send,
    _sign_payload,
    _time_remaining,
    _publish_msg,
    _sharepublish_msg,
    format_meta_lines,
    TRUES,
)


PUBSUB_LIMIT = int(os.getenv("PUBSUB_LIMIT", 31999999))
MESSAGE_TTL = int(os.getenv("REDIS_WS_MESSSAGE_TTL", 5000))
RESULTS_SWISSDOX = os.environ.get("RESULTS_SWISSDOX", "results/swissdox")


def _query(
    job: Job,
    connection: RedisConnection,
    result: list[Any],
    **kwargs: Unpack[QueryArgs],
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
    query_info = _get_query_info(connection, job=job)
    # When called as a job callback, the kwargs come from the job
    # when called directly (sents form cache) the kwargs are passed directly
    _, schema, table, *_ = query_info["current_batch"]
    table = f"{schema}.{table}"

    meta_json: QueryMeta = cast(QueryMeta, query_info.get("meta_json"))
    all_non_kwic_results: Results = {0: meta_json}
    post_processes = query_info.get("post_processes", {})
    total_before_now = query_info["total_results_so_far"]
    done_part: list[Batch] = query_info["done_batches"]
    first_job = _get_first_job(job, connection)
    stored = query_info.get("progress_info", {})
    duration: float = round((job.ended_at - job.started_at).total_seconds(), 3)  # type: ignore
    total_duration = round(query_info.get("total_duration", 0.0) + duration, 3)
    just_finished = tuple(query_info["current_batch"])
    if just_finished not in done_part:
        done_part.append(just_finished)
    query_info["done_batches"] = done_part
    query_info["total_duration"] = total_duration
    _update_query_info(connection, job=job, info=query_info)
    from_memory = query_info.get("from_memory", False)
    # Make sure all_non_kwic_results is of type Results: int keys
    all_non_kwic_results = {
        int(k): v
        for k, v in (
            query_info.get("all_non_kwic_results") or all_non_kwic_results
        ).items()
    }

    # if from memory, we had this result cached, we just need to apply filters
    if from_memory:
        all_res = all_non_kwic_results
        to_send = _apply_filters(all_res, post_processes)
        n_res = query_info["total_results_so_far"]
        search_all = stored["search_all"]
        show_total = stored["show_total"]
    # if not cached, we do all the aggregation and filtering of previous+current result
    else:
        all_res, to_send, n_res, search_all, show_total = _aggregate_results(
            result,
            all_non_kwic_results,
            meta_json,
            post_processes,
            just_finished,
            done_part,
        )
        query_info["all_non_kwic_results"] = all_res

    # right now, when a job has no kwic element, we query all batches and only stop
    # if a time limit is reached. so the progress bar can reflect the amount of time used

    total_found = total_before_now + n_res if show_total else -1
    query_info["total_results_so_far"] = total_found
    _update_query_info(connection, job=job, info=query_info)

    job.meta["results_this_batch"] = n_res
    job.meta["_search_all"] = search_all
    job.meta["_total_duration"] = total_duration

    progress_info = {
        "batch_matches": n_res,
        "show_total": show_total,
        "search_all": search_all,
    }

    # so we do not override newer data with older data?
    info: dict[str, str | bool | int | float] = query_info.get("progress_info", {})
    latest_total = cast(int, info.get("total_results_so_far", -1))
    is_latest = not info or total_found > latest_total
    if is_latest:
        query_info["progress_info"] = progress_info

    msg_id = str(uuid4())  # todo: hash instead?

    query_info["latest_stats_message"] = msg_id

    if "_sent_jobs" not in query_info:
        query_info["_sent_jobs"] = {}
    if "_meta_jobs" not in query_info:
        query_info["_meta_jobs"] = {}

    all_ri_done = all(
        _get_status(query_info, ri) in ("finished", "satisfied")
        for ri in _get_request_info(connection, query_info["hash"])
    )
    if all_ri_done:
        query_info["running"] = False
    _update_query_info(connection, job=job, info=query_info)

    max_kwic = int(os.getenv("DEFAULT_MAX_KWIC_LINES", 9999))
    current_kwic_lines = min(max_kwic, total_found)

    action = "query_result"

    jso = {
        "result": to_send,
        "job": job.id,
        "action": action,
        "from_memory": from_memory,
        "total_results_so_far": total_found,
        "table": table,
        "first_job": first_job.id,
        "post_processes": post_processes,
        "search_all": search_all,
        "batch_matches": n_res,
        "done_batches": query_info["done_batches"],
        "current_kwic_lines": current_kwic_lines,
        "msg_id": msg_id,
        "resume": False,
        "duration": duration,
        "total_duration": total_duration,
    }

    dumped = json.dumps(jso, cls=CustomEncoder)

    return _publish_msg(connection, dumped, msg_id)


def _meta(
    job: Job,
    connection: RedisConnection,
    result: list[Any] | None,
    **kwargs: Unpack[SentJob],  # type: ignore
) -> None:
    """
    Process meta data and send via websocket
    """
    if not result:
        return None
    job_kwargs = cast(dict[str, Any], job.kwargs)
    # When called as a job callback, the kwargs come from the job
    # when called directly (sents form cache) the kwargs are passed directly
    kwargs = kwargs or cast(SentJob, job_kwargs)
    depended = _get_associated_query_job(job_kwargs["depends_on"], connection)
    query_info = _get_query_info(connection, job=depended)
    cb: Batch = query_info["current_batch"]
    table = f"{cb[1]}.{cb[2]}"

    to_send = {"-2": format_meta_lines(kwargs.get("meta_query", ""), result)}
    if not to_send["-2"]:
        return None

    msg_id = str(uuid4())  # todo: hash instead!
    if "meta_job_ws_messages" not in query_info:
        query_info["meta_job_ws_messages"] = {}
    query_info["meta_job_ws_messages"][msg_id] = None
    query_info["_meta_jobs"][job.id] = None
    _update_query_info(connection, job=depended, info=query_info)

    action = "meta"

    for ri in _get_request_info(connection, query_info["hash"]):

        status = _get_status(query_info, ri)
        jso = {
            "result": to_send,
            "status": status,
            "action": action,
            "query": depended.id,
            "table": table,
            "first_job": query_info["hash"],
            "msg_id": msg_id,
        }
        _sign_payload(jso, cast(JSONObject, ri))

        # # todo: just update progress here, but do not send the rest
        dumped = json.dumps(jso, cls=CustomEncoder)

        msg_ids = ri.get("msg_ids") or []
        msg_ids.append(msg_id)
        _update_request_info(connection, ri, cast(RequestInfo, {"msg_ids": msg_ids}))
        _publish_msg(connection, dumped, msg_id)

    return


def _sentences(
    job: Job,
    connection: RedisConnection,
    result: list[RawSent] | None,
    **kwargs: int | bool | str | None,
) -> None:
    """
    Create KWIC data and send via websocket
    """
    job_kwargs: dict = cast(dict, job.kwargs)
    # When called as a job callback, the kwargs come from the job
    # when called directly (sents form cache) the kwargs are passed directly
    depended = _get_associated_query_job(job_kwargs["depends_on"], connection)
    query_info = _get_query_info(connection, job=depended)
    meta_json = query_info["meta_json"]
    max_kwic = int(os.getenv("DEFAULT_MAX_KWIC_LINES", 9999))
    current_lines = query_info["current_kwic_lines"]
    total_so_far = query_info.get("total_results_so_far", 0)
    _, schema, table, *_ = query_info.get("current_batch", ["", "", ""])[2]
    table = f"{schema}.{table}"

    for ri in _get_request_info(connection, query_info["hash"]):

        # in full mode, we need to combine all the sentences into one message when finished
        get_all_sents = ri.get("full") and _get_status(query_info, ri) == "finished"
        to_send: Results

        total_requested = ri.get("total_results_requested", 200)
        total_to_get = cast(int, ri.get("needed", total_requested))
        offset = ri.get("offset", 0)
        full = ri.get("full", False)

        if get_all_sents:
            to_send = _get_all_sents(
                job, query_info, meta_json, max_kwic, current_lines, full, connection
            )
        else:
            to_send = _format_kwics(
                depended.result,
                meta_json,
                result,
                total_to_get,
                True,
                offset,
                max_kwic,
                current_lines,
                full,
            )

        status = _get_status(query_info, ri)

        more_data = not ri.get("no_more_data", False)
        submit_query = ri.get("start_query_from_sents", False)
        if submit_query and more_data:
            status = "partial"

        if status == "finished" and more_data:
            more_data = total_so_far >= total_requested

        # if to_send contains only {0: meta, -1: sentences} or less
        if len(to_send) < 3 and not submit_query:
            print(f"No results found for {table} kwic -- skipping WS message")
            return None

        # if we previously sent a warning about there being too much data, stop here
        if ri.get("been_warned"):
            print("Processed too much data -- skipping WS message")
            return None

        use_cache = os.getenv("USE_CACHE", "true").lower() in TRUES

        if not use_cache:
            perc_done = query_info.get("percentage_done", 0.0)
            words_done = query_info.get("percentage_words_done", 0.0)
        else:
            progress = _get_progress(job, query_info, ri)
            perc_done = progress.get("percentage_done", 0.0)
            words_done = progress.get("progress_info", 0.0)

        submit_payload = {k: v for k, v in query_info.items()}
        submit_payload.update({k: v for k, v in ri.items()})

        # Do not send if this is an "export" query
        can_send = not ri.get("to_export") and (not full or status == "finished")

        msg_id = str(uuid4())  # todo: hash instead!
        if "sent_job_ws_messages" not in query_info:
            query_info["sent_job_ws_messages"] = {}
        query_info["sent_job_ws_messages"][msg_id] = None
        query_info["_sent_jobs"][job.id] = None
        _update_query_info(connection, job=job, info=query_info)

        action = "sentences"

        jso = {
            "result": to_send,
            "status": status,
            "action": action,
            "full": full,
            "more_data_available": more_data,
            "submit_query": submit_payload if submit_query else False,
            "query": depended.id,
            "table": table,
            "first_job": query_info["hash"],
            "msg_id": msg_id,
            "can_send": can_send,
            "percentage_done": perc_done,
            "percentage_words_done": words_done,
        }
        _sign_payload(submit_payload, ri)
        _sign_payload(jso, ri)

        # todo: just update progress here, but do not send the rest
        dumped = json.dumps(jso, cls=CustomEncoder)

        job.save_meta()  # type: ignore

        msg_ids = ri.get("msg_ids") or []
        msg_ids.append(msg_id)
        _update_request_info(connection, ri, cast(RequestInfo, {"msg_ids": msg_ids}))
        _publish_msg(connection, dumped, msg_id)

    return


def _document(
    job: Job,
    connection: RedisConnection,
    result: list[JSONObject] | JSONObject,
    **kwargs: Unpack[BaseArgs],
) -> None:
    """
    When a user requests a document, we give it to them via websocket
    """
    job_kwargs: dict = cast(dict, job.kwargs)
    action = "document"
    user = cast(str, kwargs.get("user", job_kwargs["user"]))
    room = cast(str | None, kwargs.get("room", job_kwargs["room"]))
    if not room:
        return
    if isinstance(result, list) and len(result) == 1:
        result = result[0]

    tmp_result: dict[str, dict] = {
        "structure": {},
        "layers": {},
        "global_attributes": {},
    }
    for row in result:
        typ, key, props = cast(list, row)
        if typ == "layer":
            if key not in tmp_result["structure"]:
                tmp_result["structure"][key] = [*props.keys()]
            if key not in tmp_result["layers"]:
                tmp_result["layers"][key] = []
            keys = tmp_result["structure"][key]
            line = [props[k] for k in keys]
            tmp_result["layers"][key].append(line)
        elif typ == "glob":
            if key not in tmp_result["global_attributes"]:
                tmp_result["global_attributes"][key] = []
            tmp_result["global_attributes"][key].append(props)
        elif typ == "doc":
            tmp_result["doc"] = props
    result = cast(JSONObject, tmp_result)

    msg_id = str(uuid4())
    jso = {
        "document": result,
        "action": action,
        "user": user,
        "room": room,
        "msg_id": msg_id,
        "corpus": job_kwargs["corpus"],
        "doc_id": job_kwargs["doc"],
    }
    return _publish_msg(connection, jso, msg_id)


def _document_ids(
    job: Job,
    connection: RedisConnection,
    result: list[JSONObject] | JSONObject,
    **kwargs: Unpack[DocIDArgs],
) -> None:
    """
    When a user requests a document, we give it to them via websocket
    """
    job_kwargs: dict = cast(dict, job.kwargs)
    user = cast(str, kwargs.get("user", job_kwargs["user"]))
    room = cast(str | None, kwargs.get("room", job_kwargs["room"]))
    if not room:
        return None
    msg_id = str(uuid4())
    formatted = {
        str(idx): {
            "name": name,
            "media": media,
            "frame_range": (
                [frame_range.lower, frame_range.upper] if frame_range else [0, 0]
            ),
        }
        for idx, name, media, frame_range in cast(
            list[tuple[int, str, dict, Any]], result
        )
    }
    action = "document_ids"
    jso = {
        "document_ids": formatted,
        "action": action,
        "user": user,
        "msg_id": msg_id,
        "room": room,
        "job": job.id,
        "corpus_id": job_kwargs["corpus_id"],
    }
    return _publish_msg(connection, jso, msg_id)


def _schema(
    job: Job,
    connection: RedisConnection,
    result: bool | None = None,
) -> None:
    """
    This callback is executed after successful creation of schema.
    We might want to notify some WS user?
    """
    job_kwargs: dict = cast(dict, job.kwargs)
    user = job_kwargs.get("user")
    room = job_kwargs.get("room")
    if not room:
        return None
    msg_id = str(uuid4())
    action = "uploaded"
    jso = {
        "user": user,
        "status": "success" if not result else "error",
        "project": job_kwargs["project"],
        "project_name": job_kwargs["project_name"],
        "corpus_name": job_kwargs["corpus_name"],
        "action": action,
        "gui": job_kwargs.get("gui", False),
        "room": room,
        "msg_id": msg_id,
    }
    if result:
        jso["error"] = result

    return _publish_msg(connection, jso, msg_id)


def _upload(
    job: Job,
    connection: RedisConnection,
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
    job_kwargs: dict = cast(dict, job.kwargs)
    user_data: JSONObject = job_kwargs["user_data"]
    gui: bool = job_kwargs["gui"]
    msg_id = str(uuid4())
    action = "uploaded"

    # if not room or not result:
    #     return None
    jso = {
        "user": user,
        "room": room,
        "id": result[0],
        "user_data": user_data,
        "entry": _row_to_value(result, project=project),
        "status": "success" if not result else "error",
        "project": project,
        "action": action,
        "gui": gui,
        "msg_id": msg_id,
    }

    # We want to notify *all* the instances of the new corpus
    return _sharepublish_msg(cast(JSONObject, jso), msg_id)
    # return _publish_msg(connection, cast(JSONObject, jso), msg_id)


def _upload_failure(
    job: Job,
    connection: RedisConnection,
    typ: type,
    value: BaseException,
    trace: TracebackType,
) -> None:
    """
    Cleanup on upload fail, and maybe send ws message
    """
    print(f"Upload failure: {typ} : {value}: {traceback}")
    msg_id = str(uuid4())

    project: str
    user: str
    room: str | None

    job_kwargs: dict = cast(dict, job.kwargs)

    if "project_name" in job_kwargs:  # it came from create schema job
        project = job_kwargs["project"]
        user = job_kwargs["user"]
        room = job_kwargs["room"]
    else:  # it came from upload job
        project = job.args[0]
        user = job.args[1]
        room = job.args[2]

    uploads_path = os.getenv("TEMP_UPLOADS_PATH", "uploads")
    path = os.path.join(uploads_path, project)
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Deleted: {path}")

    form_error = str(trace)

    try:
        form_error = "".join(traceback.format_tb(trace))
    except Exception as err:
        print(f"cannot format object: {trace} / {err}")

    action = "upload_fail"

    if user and room:
        jso = {
            "user": user,
            "room": room,
            "project": project,
            "action": action,
            "status": "failed",
            "job": job.id,
            "msg_id": msg_id,
            "traceback": form_error,
            "kind": str(typ),
            "value": str(value),
        }
        return _publish_msg(connection, jso, msg_id)


def _general_failure(
    job: Job,
    connection: RedisConnection,
    typ: type,
    value: BaseException,
    trace: TracebackType,
) -> None:
    """
    On job failure, return some info ... probably hide some of this from prod eventually!
    """
    msg_id = str(uuid4())
    form_error = str(trace)
    action = "failed"
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
            "action": action,
            "msg_id": msg_id,
            "traceback": form_error,
            "job": job.id,
            **cast(dict, job.kwargs),
        }
    # this is just for consistency with the other timeout messages
    if "No such job" in jso["value"]:
        jso["status"] = "timeout"
        jso["action"] = "timeout"

    return _publish_msg(connection, jso, msg_id)


def _queries(
    job: Job,
    connection: RedisConnection,
    result: list[UserQuery] | None,
) -> None:
    """
    Fetch or store queries
    """
    job_kwargs: dict = cast(dict, job.kwargs)
    is_store: bool = job_kwargs.get("store", False)
    action = "store_query" if is_store else "fetch_queries"
    room: str | None = job_kwargs.get("room")
    msg_id = str(uuid4())
    jso: dict[str, Any] = {
        "user": str(job_kwargs["user"]),
        "room": room,
        "status": "success",
        "action": action,
        "queries": [],
        "msg_id": msg_id,
    }
    if is_store:
        jso["query_id"] = str(job_kwargs["query_id"])
        jso.pop("queries")
    elif result:
        cols = ["idx", "query", "username", "room", "created_at"]
        queries: list[dict[str, Any]] = []
        for x in result:
            dct: dict[str, Any] = dict(zip(cols, x))
            queries.append(dct)
        jso["queries"] = queries
    return _publish_msg(connection, jso, msg_id)


def _swissdox_to_db_file(
    job: Job,
    connection: RedisConnection,
    result: list[UserQuery] | None,
) -> None:
    print("export complete!")
    j_kwargs = cast(dict, job.kwargs)
    hash = j_kwargs.get("hash", "swissdox")
    dest_folder = os.path.join(RESULTS_SWISSDOX, "exports")
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    dest = os.path.join(dest_folder, f"{hash}.db")
    if os.path.exists(dest):
        os.remove(dest)

    for table_name, index_col, data in job.result:
        df = pandas.DataFrame.from_dict(
            {cname: cvalue if cvalue else [] for cname, cvalue in data.items()}
        )
        df.set_index(index_col)
        con = duckdb.connect(database=dest, read_only=False)
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")

    user = j_kwargs.get("user")
    room = j_kwargs.get("room")

    if user and room:
        userpath = os.path.join(RESULTS_SWISSDOX, user)
        if not os.path.exists(userpath):
            os.makedirs(userpath)
        cname = j_kwargs.get("name", "swissdox")
        original_userpath = j_kwargs.get("userpath", "")
        if not original_userpath:
            original_userpath = f"{cname}_{str(datetime.now()).split('.')[0]}.db"
        fn = os.path.basename(original_userpath)
        userdest = os.path.join(userpath, fn)
        if os.path.exists(userdest):
            os.remove(userdest)
        os.symlink(os.path.abspath(dest), userdest)
        msg_id = str(uuid4())
        jso: dict[str, Any] = {
            "user": user,
            "room": room,
            "action": "export_complete",
            "msg_id": msg_id,
            "format": "swissdox",
            "hash": hash,
            "offset": 0,
            "total_results_requested": 200,
        }
        _publish_msg(connection, jso, msg_id)


def _export_complete(
    job: Job,
    connection: RedisConnection,
    result: list[UserQuery] | None,
) -> None:
    print("export complete!")
    job_args: list = cast(list, job.args)
    j_kwargs: dict = cast(dict, job.kwargs)
    if len(job_args) < 3:
        # Swissdox
        return None
    hash, _, format, _ = job_args
    dep_kwargs: dict = cast(dict, job.dependency.kwargs) if job.dependency else {}
    user = j_kwargs.get("user", dep_kwargs.get("user", ""))
    room = j_kwargs.get("room", dep_kwargs.get("room", ""))
    offset: int = cast(int, j_kwargs.get("offset", 0))
    requested: int = cast(int, j_kwargs.get("total_results_requested", 0))
    if user and room and j_kwargs.get("download", False):
        msg_id = str(uuid4())
        jso: dict[str, Any] = {
            "user": user,
            "room": room,
            "action": "export_complete",
            "msg_id": msg_id,
            "format": format,
            "hash": hash,
            "offset": offset,
            "total_results_requested": requested,
        }
        _publish_msg(connection, jso, msg_id)
    return None


def _export_notifs(
    job: Job,
    connection: RedisConnection,
    result: list | None,
) -> None:
    if not result:
        return None
    RESULTS_USERS = os.environ.get("RESULTS_USERS", os.path.join("results", "users"))
    j_kwargs: dict = cast(dict, job.kwargs)
    user = j_kwargs.get("user", "")
    hash = j_kwargs.get("hash", "")
    jso: dict[str, Any]
    if user:
        msg_id = str(uuid4())
        jso = {
            "user": user,
            "action": "export_notifs",
            "msg_id": msg_id,
            "exports": result,
        }
        _publish_msg(connection, jso, msg_id)
    elif hash:
        for res in result:
            (_, _, _, _, user_id, format, offset, requested, _, fn, _, _) = res
            full = requested <= 0
            exp_class = Exporter.get_exporter_class(format)
            user_folder = os.path.join(RESULTS_USERS, user_id)
            srcfn = exp_class.get_dl_path_from_hash(hash, offset, requested, full)
            # TODO: maybe create an ExporterSwissdox class?
            if format == "swissdox":
                srcfn = os.path.join(
                    RESULTS_SWISSDOX,
                    "exports",
                    f"{hash}.db",
                )
            normfn = os.path.normpath(fn)
            destfn = os.path.join(user_folder, normfn)
            if not os.path.exists(os.path.dirname(destfn)):
                os.makedirs(os.path.dirname(destfn))
            if os.path.exists(destfn):
                os.remove(destfn)
            os.symlink(os.path.abspath(srcfn), destfn)

            user_id = res[4]
            msg_id = str(uuid4())
            jso = {
                "user": user_id,
                "action": "export_notifs",
                "msg_id": msg_id,
                "exports": [res],
            }
            _publish_msg(connection, jso, msg_id)
            continue
    return None


def _config(
    job: Job,
    connection: RedisConnection,
    result: list[MainCorpus],
    publish: bool = True,
) -> dict[str, str | bool | Config]:
    """
    Run by worker: make config data
    """
    action = "set_config"
    fixed: Config = {}
    msg_id = str(uuid4())
    for tup in result:
        made = _row_to_value(tup)
        if not made.get("enabled"):
            continue
        fixed[str(made["corpus_id"])] = made

    for conf in fixed.values():
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    jso: dict[str, str | bool | Config] = {
        "config": fixed,
        "_is_config": True,
        "action": action,
        "msg_id": msg_id,
    }
    if publish:
        _publish_msg(connection, cast(JSONObject, jso), msg_id)
    return jso

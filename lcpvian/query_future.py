import asyncio
import json
import logging
import traceback

from aiohttp import web
from redis import Redis as RedisConnection
from rq import Callback
from rq.job import Job
from typing import cast, TypedDict
from uuid import uuid4

from .abstract_query.create import json_to_sql
from .abstract_query.typed import QueryJSON
from .authenticate import Authentication
from .callbacks import _general_failure
from .dqd_parser import convert
from .jobfuncs import _db_query
from .typed import JSONObject
from .utils import (
    _get_query_info,
    _publish_msg,
    _update_query_info,
    hasher,
    push_msg,
    CustomEncoder,
)


# Move to typed
class RequestData(TypedDict, total=False):
    requested: int
    corpus: int
    status: str
    user: str
    room: str
    languages: list[str]


# move that to utils
def _get_query_batches(
    config: dict,
    languages: list[str],
) -> list[tuple[str, int]]:
    """
    Get a list of tuples in the format of (batch_suffix, size) to be queried
    """
    out: list[tuple[str, int]] = []
    all_languages = ["en", "de", "fr", "ca", "it", "rm"]
    all_langs = tuple([f"_{la}" for la in all_languages])
    langs = tuple([f"_{la}" for la in languages])
    batches = config["_batches"]
    for name, size in batches.items():
        stripped = name.rstrip("0123456789")
        if stripped.endswith("rest"):
            stripped = stripped[:-4]
        if not stripped.endswith(langs) and stripped.endswith(all_langs):
            continue
        out.append((name, size))
    return sorted(out, key=lambda x: x[-1])


# move that to utils, maybe?
def decide_batch(config: dict, query_info: dict) -> tuple[str, int] | None:
    """
    Find the best next batch to query.

    Pick the smallest batch first. Query the smallest available result until
    `requested` results are collected. Then, using the result count of the
    queried batches and the word counts of the remaining batches, predict the
    smallest next batch that's likely to yield enough results and return it.

    If no batch is predicted to have enough results, pick the smallest
    available (so more results go to the frontend faster).
    """
    is_full = query_info.get("full", False)
    requested = query_info.get("requested", 200)
    done_batches = query_info.get("done_batches", [])
    all_batches = _get_query_batches(config, query_info.get("languages", []))
    if len(done_batches) == len(all_batches):
        return None
    if not len(done_batches):  # return the smallest batch
        return all_batches[0]
    buffer = 0.1  # set to zero for picking smaller batches
    so_far = query_info.get("total_results_so_far", 0)
    # set here ensures we don't double count, even though it should not happen
    total_words_processed_so_far = sum([x[-1] for x in set(done_batches)]) or 1
    proportion_that_matches = so_far / total_words_processed_so_far
    first_not_done: tuple[str, int] | None = None
    for batch in all_batches:
        if batch in done_batches:
            continue
        if is_full:
            return batch
        if not first_not_done:
            first_not_done = batch
        expected = batch[-1] * proportion_that_matches
        if float(expected) >= float(requested + (requested * buffer)):
            return batch
    if not first_not_done:
        raise ValueError("Could not find batch")
    return first_not_done


# move that to callbacks or something
def _mycb(
    job: Job,
    connection: RedisConnection,
    result: dict | None = None,
) -> None:
    msg_id = cast(dict, job.kwargs).get("msg_id", "")
    jso = json.dumps(result, cls=CustomEncoder)
    return _publish_msg(connection, jso, msg_id)


# TODO
async def run_meta_on_batch():
    pass


# TODO
async def run_sentence_on_batch():
    pass


async def run_query(app, hash: str, json_query: dict, config: dict, qi: dict) -> None:
    """
    Continuously sends a query to the DB until all the results are fetched
    or all the batches have been queries
    """
    langs = qi.get("languages", [])
    lang = langs[0] or ""
    all_batches = _get_query_batches(config, langs)
    schema = config.get("schema_path", "")
    while 1:
        max_requested: int = max(x.get("requested", 200) for x in qi["requests"])
        total_results_so_far: int = qi.get("total_results_so_far", 0)
        if total_results_so_far >= max_requested:
            qi["status"] = "satisfied"
            _update_query_info(app["redis"], hash, info=qi)
            break  # we've got enough results
        batch = decide_batch(config, qi)
        if batch is None:
            qi["status"] = "complete"
            break  # we've exhausted all the batches
        sql_query, meta_json, post_processes = json_to_sql(
            cast(QueryJSON, json_query),
            schema=schema,
            batch=batch[0],
            config=config,
            lang=lang,
        )
        # genericize this logic
        current_query: asyncio.Future = asyncio.Future()
        msg_id = str(uuid4())
        app["futures"][msg_id] = current_query
        job = app["background"].enqueue(
            _db_query,
            on_success=Callback(_mycb, 5000),
            on_failure=Callback(_general_failure, 5000),
            args=(sql_query,),
            kwargs={"msg_id": msg_id},
        )
        qi["query_jobs"] = qi.get("query_jobs", {})
        qi["query_jobs"][batch[0]] = job.id
        _update_query_info(app["redis"], hash, info=qi)
        res = await current_query
        payload = {"job": job.id, "result": res}
        total_results_so_far += len(res)
        qi["total_results_so_far"] = total_results_so_far
        done_batches = qi.get("done_batches", [])
        if batch not in done_batches:
            done_batches.append(batch)
        qi["done_batches"] = done_batches
        all_done = len(done_batches) >= len(all_batches)
        if all_done:
            qi["status"] = "complete"
        _update_query_info(app["redis"], hash, info=qi)
        for r in qi["requests"]:
            if r["status"] == "satisfied":
                continue
            r_payload = {**payload}
            if all_done:
                r["status"] = "complete"
            elif total_results_so_far >= r["requested"]:
                r["status"] = "satisfied"
            r_payload.update(
                {"user": r["user"], "room": r["room"], "status": r["status"]}
            )
            _update_query_info(app["redis"], hash, info=qi)
            await push_msg(
                app["websockets"],
                r["room"],
                r_payload,
                skip=None,
                just=(r["room"], r["user"]),
            )
    return None


async def process_query(app, request_data) -> dict:
    """
    Determines whether it is necessary to send queries to the DB
    and returns the job info
    """
    need_to_run: bool = False
    is_full: bool = request_data.get("full") or False
    offset: int = request_data.get("offset", 0)
    requested: int = request_data.get("requested", 200)
    corpus_id = request_data.get("corpus", "")
    config = app["config"][corpus_id]
    schema = config.get("schema_path", "")
    try:
        json_query = json.loads(request_data["query"])
        json_query = json.loads(json.dumps(json_query, sort_keys=True))
    except json.JSONDecodeError:
        json_query = convert(request_data["query"], config)
    lang = request_data.get("languages", [])
    first_batch, *_ = _get_query_batches(config, lang)
    sql_query, _, _ = json_to_sql(
        cast(QueryJSON, json_query),
        schema=schema,
        batch=first_batch[0],
        config=config,
        lang=lang[0] if lang else None,
    )
    hash = hasher(sql_query)
    qi = _get_query_info(app["redis"], hash)
    qi_status = qi.get("status", "started")
    total_so_far = qi.get("total_results_so_far", 0) or 0
    if total_so_far > 0:
        actual_total = 0
        for qjbatch, qjid in qi.get("query_jobs", {}).items():
            try:
                query_job = Job.fetch(qjid, connection=app["redis"])
                actual_total += len(query_job.result)
                if actual_total > offset:
                    print(f"sending {len(query_job.result)} lines from cache")
            except:
                total_so_far = actual_total
                need_to_run = total_so_far < requested
        total_so_far = actual_total
    all_requests = qi.get("requests", [])
    need_to_run = need_to_run or qi_status not in ("satisfied", "complete")
    max_requested_so_far: int = (
        0 if not all_requests else max(x.get("requested", 0) for x in all_requests)
    )
    need_to_run = need_to_run or is_full or (requested > max_requested_so_far)
    request_data.update({"status": "started", "sent_so_far": 0})
    all_requests.append(request_data)
    qi.update(
        {
            "status": qi_status,
            "requests": all_requests,
            "requested": max_requested_so_far,
            "languages": request_data.get("languages", []),
            "full": qi.get("full") or is_full,
            "total_results_so_far": total_so_far,
        }
    )
    _update_query_info(app["redis"], hash, info=qi)
    res = {
        "status": "started",
        "job": hash,
    }
    if not need_to_run:
        return res
    asyncio.create_task(run_query(app, hash, json_query, config, qi))
    # if qi.sentences and do_sents:
    #     jobs.update({"sentences": True, "sentences_jobs": sents_jobs})
    return res


async def post_query(request: web.Request) -> web.Response:
    """
    Main query endpoint: generate and queue up corpus queries
    """
    app = request.app
    request_data = await request.json()
    # user = request_data.get("user", "")
    # room = request_data.get("room", "")
    # corpus = request_data.get("corpus", "")
    # if request_data.get("api"):
    #     room = "api"
    #     request_data["room"] = room
    #     request_data["to_export"] = request_data.get("to_export") or {"format": "xml"}
    # # Check permission
    # authenticator = cast(Authentication, app["auth_class"](app))
    # user_data: dict = {}
    # if "X-API-Key" in request.headers and "X-API-Secret" in request.headers:
    #     user_data = await authenticator.check_api_key(request)
    # else:
    #     user_data = await authenticator.user_details(request)
    # app_type = str(request_data.get("appType", "lcp"))
    # app_type = (
    #     "lcp"
    #     if app_type not in {"lcp", "videoscope", "soundscript", "catchphrase"}
    #     else app_type
    # )
    # allowed = authenticator.check_corpus_allowed(
    #     str(corpus), app["config"][str(corpus)], user_data, app_type, get_all=False
    # )
    # if not allowed:
    #     fail: dict[str, str] = {
    #         "status": "403",
    #         "error": "Forbidden",
    #         "action": "query_error",
    #         "user": user,
    #         "room": room,
    #         "info": "Attempted access to an unauthorized corpus",
    #     }
    #     msg = "Attempted access to an unauthorized corpus"
    #     # # alert everyone possible about this problem:
    #     print(msg)
    #     logging.error(msg, extra=fail)
    #     payload = cast(JSONObject, fail)
    #     just: tuple[str, str] = (room, user or "")
    #     await push_msg(app["websockets"], room, payload, just=just)
    #     print("pushed message")
    #     raise web.HTTPForbidden(text=msg)

    jobs = await process_query(app, request_data)
    return web.json_response(jobs)

from __future__ import annotations

import json
import logging
import os
import traceback

from collections.abc import Sequence

from typing import TypeAlias, cast

from aiohttp import web
from rq.job import Job

from .log import logged
from .qi import QueryIteration
from .typed import Batch, JSONObject
from .utils import ensure_authorised, push_msg

# from .worker import SQLJob


Iteration: TypeAlias = tuple[
    Job | None, str | None, dict[str, str | bool | None], list[str]
]


async def _do_resume(qi: QueryIteration) -> QueryIteration:
    """
    Resume a query, or decide that we need to query the next batch

    When resuming, there are two or three few possible situations we could be in:

    1. we have already got enough results via previous sql queries to fill
       the request, we just haven't sent them yet
    2. we have not got enough results, so we need to query this batch and the next one
    3? we had exactly the right number of results ... edge case

    """
    prev_job = Job.fetch(qi.previous, connection=qi.app["redis"])
    dones = cast(list[Sequence], prev_job.kwargs["done_batches"])
    done_batches: list[Batch] = [(a, b, c, d) for a, b, c, d in dones]
    so_far = prev_job.meta["total_results_so_far"]
    tot_req = qi.total_results_requested
    prev_total = qi.current_kwic_lines

    prev_batch_results = prev_job.meta["results_this_batch"]
    need_now = tot_req - prev_total

    next_offset = prev_job.meta["offset_for_next_time"]
    latest_offset = prev_job.meta.get("latest_offset", 0)
    qi.offset = max(latest_offset, next_offset)

    left_in_batch = prev_batch_results - qi.offset
    not_enough = left_in_batch < need_now
    qi.send_stats = False

    if qi.total_results_so_far >= qi.total_results_requested:
        qi.needed = qi.total_results_requested - prev_total

    elif not_enough:
        qi.needed = left_in_batch
        qi.start_query_from_sents = True
    else:
        raise ValueError("Backend error. Please debug")

    if qi.full:
        qi.start_query_from_sents = True

    prev = cast(Sequence, prev_job.kwargs["current_batch"])
    previous_batch: Batch = (prev[0], prev[1], prev[2], prev[3])
    if previous_batch not in done_batches:
        done_batches.append(previous_batch)
    qi.done_batches = done_batches
    qi.total_results_so_far = so_far

    return qi


async def _query_iteration(qi: QueryIteration, it: int) -> QueryIteration:
    """
    Oversee the querying of a single batch
    """
    max_jobs = int(os.getenv("MAX_SIMULTANEOUS_JOBS_PER_USER", -1))

    # handle resumed queries -- figure out if we need to query new batch
    if qi.resume:
        qi = await _do_resume(qi)
    else:
        qi.offset = 0

    jobs: dict[str, str | list[str] | bool] = {}

    qi.decide_batch()
    qi.make_query()

    # print query info to terminal for first batch only
    if not it and not qi.job and not qi.resume and qi.send_stats:
        query_type = "DQD" if qi.dqd else "JSON"
        form = json.dumps(qi.jso, indent=4)
        print(f"Detected query type: {query_type}")
        print(f"DQD:\n\n{qi.dqd}\n\nJSON:\n\n{form}\n\nSQL:\n\n{qi.sql}")

    # organise and submit query to rq via query service
    query_job, do_sents = await qi.submit_query()

    # simultaneous query setup for next iteration -- plz improve
    divv = (it + 1) % max_jobs if max_jobs > 0 else -1
    if qi.job and qi.simultaneous and it and max_jobs > 0 and not divv:
        if query_job.id not in qi.dep_chain:
            qi.dep_chain.append(query_job.id)

    assert qi.current_batch is not None
    schema_table = ".".join(qi.current_batch[1:3])

    if (
        qi.current_batch is not None
        and qi.job is not None
        and qi.send_stats
        and do_sents is not None
    ):
        print(f"\nNow querying: {schema_table} ... {query_job.id}")

    # prepare and submit sentences query
    if do_sents is not None:
        if qi.sentences or qi.send_stats:
            sents_jobs = qi.submit_sents(do_sents)

    jobs = {
        "status": "started",
        "job": qi.job_id if qi.job else qi.previous,
    }

    if qi.sentences and do_sents:
        jobs.update({"sentences": True, "sentences_jobs": sents_jobs})

    qi.job_info = jobs

    if qi.simultaneous and qi.current_batch is not None:
        qi.done_batches.append(qi.current_batch)
        qi.current_batch = None

    return qi  # job, depend, jobs, dep_chain


@ensure_authorised
@logged
async def query(
    request: web.Request,
    manual: JSONObject | None = None,
    app: web.Application | None = None,
) -> web.Response:
    """
    Main query endpoint: generate and queue up corpus queries

    This endpoint can be manually triggered for queries over multiple batches. When
    that happpens, manual is a dict with the needed data and the app is passed in
    as a kwarg.

    Because data can come in either through a request or through a dict, we normalise
    by creating a utils.QueryIteration dataclass. Use this to keep the namespace of this
    function from growing any larger...
    """
    # Turn request or manual dict into a QueryIteration object
    if manual is not None and isinstance(app, web.Application):
        # 'request' comes from sock.py, it is a non-first iteration
        qi = await QueryIteration.from_manual(manual, app)
    else:
        # request is from the frontend, most likely a new query...
        qi = await QueryIteration.from_request(request)

    # prepare for query iterations (just one if not simultaneous mode)
    iterations = len(qi.all_batches) if qi.simultaneous else 1
    http_response: list[dict[str, str | bool | list[str]]] = []
    out: Iteration

    try:
        for it in range(iterations):
            qi = await _query_iteration(qi, it)
            http_response.append(qi.job_info)
    except Exception as err:
        tb = traceback.format_exc()
        fail: dict[str, str] = {
            "status": "error",
            "action": "query_error",
            "type": str(type(err)),
            "traceback": tb,
            "user": qi.user,
            "room": qi.room or "",
            "info": f"Could not create query: {str(err)}",
        }
        msg = f"Error: {err} ({qi.user}/{qi.room})"
        # alert everyone possible about this problem:
        print(f"{msg}:\n\n{tb}")
        logging.error(msg, extra=fail)
        payload = cast(JSONObject, fail)
        room: str = qi.room or ""
        just: tuple[str, str] = (room, qi.user)
        await push_msg(qi.app["websockets"], room, payload, just=just)
        return web.json_response(fail)

    if qi.simultaneous:
        return web.json_response(http_response)
    else:
        return web.json_response(http_response[0])

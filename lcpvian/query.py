from __future__ import annotations

import json
import logging
import os
import traceback

from collections.abc import Sequence

from typing import TypeAlias, cast

from aiohttp import web
from rq.job import Job

from .callbacks import _query, _sentences
from .log import logged
from .qi import QueryIteration
from .typed import Batch, JSONObject
from .utils import _get_all_results, ensure_authorised, push_msg
from .worker import SQLJob


Iteration: TypeAlias = tuple[
    Job | None, str | None, dict[str, str | bool | None], list[str]
]


async def _do_resume(qi: QueryIteration) -> QueryIteration:
    """
    Resume a query, or decide that we need to query the next batch
    """
    prev_job = Job.fetch(qi.previous, connection=qi.app["redis"])
    hit_limit = prev_job.meta.get("hit_limit", 0)
    if hit_limit:
        # base = prev_job.kwargs.get("base", prev_job.id)
        _query(
            prev_job,
            qi.app["redis"],
            prev_job.result,
            hit_limit=hit_limit,
            total_results_requested=qi.total_results_requested,
        )
        current_batch = prev_job.kwargs["current_batch"]

        associated_sents = prev_job.meta.get("associated")
        if not associated_sents:
            msg = "Sent job not finished. todo: fix this"
            raise ValueError(msg)
        else:
            sent_job = Job.fetch(associated_sents, connection=qi.app["redis"])

            _sentences(
                sent_job,
                qi.app["redis"],
                sent_job.result,
                start_at=hit_limit,
                total_results_requested=qi.total_results_requested,
            )

        # todo: review this

        # basejob = Job.fetch(base, connection=qi.app["redis"])
        # res_so_far = basejob.meta.get("_sentences", {})

        # sent_result = Job.fetch(base, connection=qi.app["redis"]).result

        # latest_sents = basejob.meta.get("latest_sentences")
        # if latest_sents:
        #    latest_sents = Job.fetch(latest_sents, connection=qi.app["redis"])

        qi.current_batch = current_batch
        qi.previous_job = prev_job
        qi.done = True
        return qi
    else:
        # all_batches = prev_job.kwargs["all_batches"]
        dones = cast(list[Sequence], prev_job.kwargs["done_batches"])
        done_batches: list[Batch] = [(a, b, c, d) for a, b, c, d in dones]
        so_far = prev_job.meta["total_results"]
        tot_req = qi.total_results_requested
        needed = tot_req - so_far if tot_req != -1 else -1
        prev = cast(Sequence, prev_job.kwargs["current_batch"])
        previous_batch: Batch = (prev[0], prev[1], prev[2], prev[3])
        if previous_batch not in done_batches:
            done_batches.append(previous_batch)
        # qi.all_batches = all_batches
        qi.done_batches = done_batches
        qi.total_results_so_far = so_far
        qi.needed = needed
        ex = _get_all_results(qi)
        qi.existing_results = ex
        return qi


async def _query_iteration(qi: QueryIteration, it: int) -> QueryIteration:
    """
    Oversee the querying of a single batch
    """
    max_jobs = int(os.getenv("MAX_SIMULTANEOUS_JOBS_PER_USER", -1))

    # handle resumed queries -- figure out if we need to query new batch
    if qi.resuming:
        qi = await _do_resume(qi)

    jobs: dict[str, str | bool] = {}

    if qi.done:
        jobs = {
            "status": "started",
            "sentences": qi.sentences,
            "job": qi.job_id if qi.job else qi.previous,
        }
        qi.job_info = jobs
        if qi.simultaneous and qi.current_batch is not None:
            qi.done_batches.append(qi.current_batch)
            qi.current_batch = None
        return qi

    qi.decide_batch()
    qi.make_query()

    # print query info to terminal for first batch only
    if not it and not qi.job:
        query_type = "DQD" if qi.dqd else "JSON"
        form = json.dumps(qi.jso, indent=4)
        print(f"Detected query type: {query_type}")
        print(f"DQD:\n\n{qi.dqd}\n\nJSON:\n\n{form}\n\nSQL:\n\n{qi.sql}")

    # organise and submit query to rq via query service
    query_job = qi.submit_query()

    # simultaneous query setup for next iteration -- plz improve
    divv = (it + 1) % max_jobs if max_jobs > 0 else -1
    if qi.job and qi.simultaneous and it and max_jobs > 0 and not divv:
        qi.dep_chain.append(query_job.id)

    if qi.current_batch is not None and qi.job is not None:
        schema_table = ".".join(qi.current_batch[1:3])
        print(f"\nNow querying: {schema_table} ... {query_job.id}")

    # prepare and submit sentences query
    if qi.sentences and not qi.from_memory:
        sents_job = qi.submit_sents()

    jobs = {
        "status": "started",
        "job": qi.job_id if qi.job else qi.previous,
    }

    if qi.sentences and not qi.done and not qi.from_memory:
        jobs.update({"sentences": True, "sentences_job": sents_job.id})

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
    http_response: list[dict[str, str | bool]] = []
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

from __future__ import annotations

import json
import logging
import os
import traceback

from typing import Any, Dict, List, Tuple

from abstract_query.create import json_to_sql
from aiohttp import web
from rq.job import Job

from .callbacks import _query, _sentences
from .dqd_parser import convert
from .log import logged
from .utils import QueryIteration, _get_all_results, ensure_authorised, push_msg


def _get_word_count(qi: QueryIteration) -> int:
    """
    Sum the word counts for corpora being searched
    """
    corpora = qi.corpora
    config = qi.app["config"]
    languages = qi.languages

    total = 0
    for corpus in corpora:
        conf = config[str(corpus)]
        try:
            has_partitions = "partitions" in conf["mapping"]["layer"][conf["token"]]
        except (KeyError, TypeError):
            has_partitions = False
        if not has_partitions or not languages:
            total += sum(conf["token_counts"].values())
        else:
            counts = conf["token_counts"]
            for name, num in counts.items():
                for lang in languages:
                    if name.rstrip("0").endswith(lang):
                        total += num
                        break
    return total


async def _do_resume(qi: QueryIteration) -> QueryIteration:
    """
    Resume a query, or decide that we need to query the next batch
    """
    app = qi.app
    prev_job = Job.fetch(qi.previous, connection=app["redis"])
    hit_limit = prev_job.meta.get("hit_limit", 0)
    if hit_limit:
        # base = prev_job.kwargs.get("base", prev_job.id)
        _query(
            prev_job,
            app["redis"],
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
            sent_job = Job.fetch(associated_sents, connection=app["redis"])

            _sentences(
                sent_job,
                app["redis"],
                sent_job.result,
                start_at=hit_limit,
                total_results_requested=qi.total_results_requested,
            )

        # todo: review this

        # basejob = Job.fetch(base, connection=app["redis"])
        # res_so_far = basejob.meta.get("_sentences", {})

        # sent_result = Job.fetch(base, connection=app["redis"]).result

        # latest_sents = basejob.meta.get("latest_sentences")
        # if latest_sents:
        #    latest_sents = Job.fetch(latest_sents, connection=app["redis"])

        qi.current_batch = current_batch
        qi.previous_job = prev_job
        qi.done = True
        return qi
    else:
        all_batches = prev_job.kwargs["all_batches"]
        done_batches = prev_job.kwargs["done_batches"]
        so_far = prev_job.meta["total_results"]
        needed = (
            qi.total_results_requested - so_far
            if qi.total_results_requested not in {-1, False, None}
            else -1
        )
        previous_batch = prev_job.kwargs["current_batch"]
        done_batches.append(previous_batch)
        qi.all_batches = all_batches
        qi.done_batches = done_batches
        qi.total_results_so_far = so_far
        qi.needed = needed
        ex = _get_all_results(qi.previous, connection=app["redis"])
        qi.existing_results = ex
        return qi


def _make_query(
    qi: QueryIteration,
) -> Tuple[str | None, Dict[str, Any], str, Dict[str, List[Dict[str, Any]]]]:
    """
    Do any necessary query conversions

    Returns: the DQD/None, JSON, SQL and SQL metadata objects
    """
    if qi.current_batch is None:
        raise ValueError("Batch not found")

    kwa = dict(
        schema=qi.current_batch[1],
        batch=qi.current_batch[2],
        config=qi.app["config"][str(qi.current_batch[0])],
        lang=qi._determine_language(qi.current_batch[2]),
        vian=qi.is_vian,
    )
    txt: str | None = None
    try:
        json_query = json.loads(qi.query)
    except json.JSONDecodeError:
        json_query = convert(qi.query)
        txt = qi.query
    sql_query, meta_json = json_to_sql(json_query, **kwa)
    return txt, json_query, sql_query, meta_json


def _get_base(
    qi: QueryIteration,
    first_job: Job | None,
) -> str:
    """
    Find the original base of a query
    """
    if qi.simultaneous and first_job:
        return first_job.id
    elif qi.resuming and qi.done and qi.base:
        return qi.base
    elif qi.resuming and qi.done and not qi.base and qi.previous_job:
        # todo: not sure if this is right...
        return qi.previous_job.kwargs.get("base", qi.previous_job.id)
    final = qi.job_id if qi.base is None and qi.job_id else qi.base
    return final if final else ""


def _submit_sents(
    qi: QueryIteration, first_job: Job | None, dep_chain: List[str]
) -> Tuple[Job, List[str]]:
    """
    Submit a sentences job
    """
    app = qi.app
    skwargs = dict(
        user=qi.user,
        room=qi.room,
        simultaneous=qi.simultaneous,
        current_batch=qi.current_batch,
        query=qi.sents_query(),
        base=_get_base(qi, first_job),
        resuming=qi.done,
    )
    depends_on = qi.job_id if not qi.done and qi.job is not None else qi.previous
    to_use: List[str] | str = []
    if qi.simultaneous and depends_on:
        dep_chain.append(depends_on)
        to_use = dep_chain
    elif depends_on:
        to_use = depends_on
    sents_job = app["query_service"].sentences(depends_on=to_use, **skwargs)
    # if simultaneous:
    #    dep_chain.append(stats_job.id)
    return sents_job, dep_chain


def _submit_query(
    manual: Dict[str, Any] | None,
    qi: QueryIteration,
    word_count: int,
    meta: Dict,
    sql: str,
    qd: List[str],
) -> Job:
    """
    Helper to submit a query job
    """
    parent: str | None = None
    if manual is not None and qi.job is not None:
        parent = qi.job_id
    elif qi.resuming:
        parent = qi.previous

    query_kwargs = dict(
        original_query=qi.query,
        user=qi.user,
        room=qi.room,
        needed=qi.needed,
        total_results_requested=qi.total_results_requested,
        done_batches=qi.done_batches,
        all_batches=qi.all_batches,
        current_batch=qi.current_batch,
        total_results_so_far=qi.total_results_so_far,
        corpora=qi.corpora,
        base=qi.base,
        existing_results=qi.existing_results,
        sentences=qi.sentences,
        offset=qi.hit_limit,
        page_size=qi.page_size,
        languages=list(qi.languages),
        simultaneous=qi.simultaneous,
        is_vian=qi.is_vian,
        word_count=word_count,
        parent=parent,
        meta_json=meta,
        query=sql,
    )

    job = qi.app["query_service"].query(depends_on=qd, **query_kwargs)
    return job


@ensure_authorised
@logged
async def query(
    request: web.Request,
    manual: Dict[str, Any] | None = None,
    app: web.Application | None = None,
) -> web.Response:
    """
    Generate and queue up corpus queries

    This endpoint can be manually triggered for queries over multiple batches. When
    that happpens, manual is a dict with the needed data and the app is passed in
    as a kwarg.

    Because data can come in either through a request or through a dict, we normalise
    by creating a utils.QueryIteration dataclass. Use this to keep the namespace of this function
    from growing any larger
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
    http_response: List[Dict[str, str | bool | None]] = []
    first: Job | None = None
    dep_chain: List[str] = []
    depends: List[str] = []

    try:
        for it in range(iterations):
            out = await _query_iteration(qi, it, manual, first, depends, dep_chain)
            job, dep, jobs, dep_chain = out
            if not it and job:
                first = job
            if dep:
                depends.append(dep)
            http_response.append(jobs)
    except Exception as err:
        fail = {
            "status": "error",
            "type": str(type(err)),
            "info": f"Could not create query: {str(err)}",
        }
        extra = {
            "user": qi.user,
            "room": qi.room,
            "traceback": traceback.format_exc(),
            **fail,
        }
        logging.error("Query generation failed", extra=extra)
        # double trouble:
        await push_msg(qi.app["websockets"], qi.room, fail, just=(qi.room, qi.user))
        return web.json_response(fail)

    if qi.simultaneous:
        return web.json_response(http_response)
    else:
        return web.json_response(http_response[0])


async def _query_iteration(
    qi: QueryIteration,
    it: int,
    manual: Dict[str, Any] | None,
    first_job: Job | None,
    query_depends: List[str],
    dep_chain: List[str],
) -> Tuple[Job | None, str | None, Dict[str, str | bool | None], List[str]]:
    """
    Oversee the querying of a single batch
    """
    max_jobs = int(os.getenv("MAX_SIMULTANEOUS_JOBS_PER_USER", -1))
    depend: str | None = None

    # handle resumed queries -- figure out if we need to query new batch
    if qi.resuming:
        qi = await _do_resume(qi)

    jobs: Dict[str, str | bool | None] = {}

    if qi.done:
        jobs = {
            "status": "started",
            "sentences": qi.sentences,
            "job": qi.job_id if qi.job else qi.previous,
        }
        if qi.simultaneous and qi.current_batch is not None:
            qi.done_batches.append(qi.current_batch)
            qi.current_batch = None

        return qi.job, depend, jobs, dep_chain

    word_count = _get_word_count(qi)
    qi.decide_batch()

    dqd, jso, sql, meta = _make_query(qi)

    # print query info to terminal for first batch only
    if not it and manual is None:
        query_type = "DQD" if dqd else "JSON"
        form = json.dumps(jso, indent=4)
        print(f"Detected query type: {query_type}")
        print(f"DQD:\n\n{dqd}\n\nJSON:\n\n{form}\n\nSQL:\n\n{sql}")

    # organise and submit query to rq via query service
    job = _submit_query(manual, qi, word_count, meta, sql, query_depends)
    qi.job = job
    qi.job_id = job.id

    # simultaneous query setup for next iteration -- plz improve
    divv = (it + 1) % max_jobs if max_jobs > 0 else -1
    if qi.job and qi.simultaneous and it and max_jobs > 0 and not divv:
        depend = qi.job_id

    if qi.current_batch is not None and qi.job is not None:
        schema_table = ":".join(qi.current_batch[1:3])
        print(f"\nNow querying: {schema_table} ... {qi.job_id}")

    if qi.simultaneous and not it:
        first_job = qi.job

    # prepare and submit sentences query
    if qi.sentences:
        sents_job, dep_chain = _submit_sents(qi, first_job, dep_chain)

    jobs = {
        "status": "started",
        "job": qi.job_id if qi.job else qi.previous,
    }

    if qi.sentences and not qi.done:
        jobs.update({"sentences": True, "sentences_job": sents_job.id})

    if qi.simultaneous and qi.current_batch is not None:
        qi.done_batches.append(qi.current_batch)
        qi.current_batch = None

    return job, depend, jobs, dep_chain

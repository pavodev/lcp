import asyncio
import json
import logging
import os
import traceback

from aiohttp import web
from redis import Redis as RedisConnection
from rq.job import Job
from typing import cast, Generator
from uuid import uuid4

from .abstract_query.create import json_to_sql
from .abstract_query.typed import QueryJSON
from .authenticate import Authentication
from .convert import _aggregate_results
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

QUERY_TTL = os.getenv("QUERY_TTL", 5000)

SERIALIZABLES = (
    int,
    float,
    bool,
    str,
    bytes,
    bytearray,
    list,
    tuple,
    set,
    frozenset,
    dict,
)


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


class Request:
    """
    Received POST requests
    """

    def __init__(self, app: web.Application, request: str | dict = {}):
        self._app = app
        if isinstance(request, str):
            request = json.loads(request)
        request = cast(dict, request)
        self.synchronous: bool = request.get("synchronous", False)
        self.requested: int = request.get("requested", 0)
        self.full: bool = request.get("full", False)
        self.offset: int = request.get("offset", 0)
        self.corpus: int = request.get("corpus", 1)
        self.status: str = request.get("status", "started")
        self.user: str = request.get("user", "")
        self.room: str = request.get("room", "")
        self.languages: list[str] = request.get("languages", [])
        self.query: str = request.get("query", "")
        # job1: [200,400] --> sent lines 200 through 400
        self.lines_sent_per_job: dict[str, tuple[int, int]] = request.get(
            "lines_sent_per_job", {}
        )
        self._sync_buffer: dict = {}

    def serialize(self) -> str:
        """
        String representation of attributes that are in SERIALIZABLES
        """
        obj: dict = {}
        for k in dir(self):
            if k.startswith("_"):
                continue
            attr = getattr(self, k)
            if not isinstance(attr, SERIALIZABLES):
                continue
            obj[k] = attr
        return json.dumps(obj)

    def lines_for_job(self, qi, job: Job) -> tuple[int, int]:
        """
        Return the offset and number of lines requires in the current job
        """
        ret = (0, 0)
        if self.status == "satisfied":
            return ret
        lines_before_batch, lines_this_batch = qi.get_lines_job(job.id)
        if self.offset > lines_before_batch + lines_this_batch:
            return ret
        if self.offset + self.requested < lines_before_batch:
            return ret
        offset_this_batch: int = self.offset if self.offset > lines_before_batch else 0
        max_this_batch: int = offset_this_batch + min(self.requested, lines_this_batch)
        ret = (offset_this_batch, max_this_batch)
        self.lines_sent_per_job[job.id] = ret
        return ret

    @property
    def lines_sent_so_far(self) -> int:
        return sum(up - lo for lo, up in self.lines_sent_per_job.values())

    async def send_query(self, qi, job: Job):
        """
        Send the payload to the associated user
        and update the request accordingly
        """
        offset_this_batch, max_this_batch = self.lines_for_job(qi, job)
        results = {str(k): [] for k in qi.kwic_keys}
        lines_so_far = -1
        for k, v in job.result:
            if str(k) not in qi.kwic_keys:
                continue
            lines_so_far += 1
            if lines_so_far < offset_this_batch:
                continue
            if lines_so_far >= max_this_batch:
                continue
            results[str(k)].append(v)
        results.update(job.meta.get("stats_results", {}))
        if qi.status == "complete":
            self.status = "complete"
        elif self.lines_sent_so_far >= self.requested:
            self.status = "satisfied"
        payload = {
            "action": "query",
            "job": qi.hash,
            "user": self.user,
            "room": self.room,
            "status": self.status,
            "results": results,
        }
        qi.update()
        if self.synchronous:
            print(f"Sending results of job {job.id} (hash {qi.hash}) to sync request")
            self._sync_buffer.update(payload)
        else:
            print(
                f"Sending results of job {job.id} (hash {qi.hash}) to user '{self.user}' room '{self.room}'"
            )
            await push_msg(
                self._app["websockets"],
                self.room,
                payload,
                skip=None,
                just=(self.room, self.user),
            )


class QueryInfo:
    """
    Model the query based on the SQL of the first batch
    There is a single QueryInfo for potentially multiple POST requests (Request)
    """

    def __init__(
        self, hash: str, result_sets: list, app: web.Application, config: dict
    ):
        cn: RedisConnection = app["redis"]
        qi = _get_query_info(cn, hash)
        self._connection = cn
        self.hash = hash
        self.result_sets: list = result_sets
        self.requests: list[Request] = [Request(app, r) for r in qi.get("requests", [])]
        self.status: str = qi.get("status", "started")
        self.done_batches: list = qi.get("done_batches", [])
        # query_jobs is {batch: (job_id, nlines)}
        self.query_jobs: dict[str, tuple[str, int]] = qi.get("query_jobs", {})
        self.languages: list[str] = qi.get("languages", [])
        # running_batch is set to the running batch, or empty
        self.running_batch: str = qi.get("running_batch", "")
        self._config: dict = config
        self._stats_results: tuple[list, dict] = ([], {})

    def add_request(self, request: Request):
        self.requests.append(request)

    def get_running_requests(self) -> list[Request]:
        return [r for r in self.requests if r.status not in ("satisfied", "complete")]

    def get_lines_job(self, job_id: str) -> tuple[int, int]:
        lines_before_batch: int = 0
        lines_this_batch: int = 0
        for qjid, n in self.query_jobs.values():
            if qjid == job_id:
                lines_this_batch = n
                break
            lines_before_batch += n
        return (lines_before_batch, lines_this_batch)

    @property
    def kwic_keys(self) -> list[str]:
        return [
            str(n)
            for n, mr in enumerate(self.result_sets, start=1)
            if mr.get("type") == "plain"
        ]

    @property
    def non_kwic_keys(self) -> list[str]:
        return [
            str(n)
            for n, mr in enumerate(self.result_sets, start=1)
            if mr.get("type") != "plain"
        ]

    @property
    def full(self) -> bool:
        running_requests = self.get_running_requests()
        return any(r.full for r in running_requests) if running_requests else False

    @property
    def required(self) -> int:
        """
        The required number of results lines is the max offset+requested out of all the Request's
        """
        running_requests = self.get_running_requests()
        return (
            max(r.offset + r.requested for r in running_requests)
            if running_requests
            else 0
        )

    @property
    def stats_results(self) -> dict:
        """
        All the non-KWIC results
        """
        last_job_ids, last_results = self._stats_results
        job_ids = [id for id, _ in self.query_jobs.values()]
        if last_job_ids == job_ids:
            return last_results
        last_results = {}
        for qj in job_ids:
            try:
                job = Job.fetch(qj, self._connection)
                last_results.update(**job.meta.get("stats_results", {}))
            except:
                pass
        self._stats_results = (job_ids, last_results)
        return last_results

    @property
    def total_results_so_far(self) -> int:
        return sum(nlines for _, nlines in self.query_jobs.values())

    @property
    def all_batches(self) -> list[tuple[str, int]]:
        return _get_query_batches(self._config, self.languages)

    def update(self, obj: dict = {}):
        """
        Update the attributes of this instance and the entry in Redis
        """
        qi = _get_query_info(self._connection, self.hash)
        for k, v in obj.items():
            qi[k] = v
        for aname in dir(self):
            if aname.startswith("_"):
                continue
            attr = getattr(self, aname)
            if not isinstance(attr, SERIALIZABLES):
                continue
            qi[aname] = attr
        qi["requests"] = [r.serialize() for r in self.requests]
        _update_query_info(self._connection, self.hash, info=qi)

    def smart_batches(self) -> Generator[tuple[str, int] | None, None, None]:
        """
        Return the batches in an optimized ordered.

        Pick the smallest batch first. Query the smallest available result until
        `requested` results are collected. Then, using the result count of the
        queried batches and the word counts of the remaining batches, predict the
        smallest next batch that's likely to yield enough results and return it.

        If no batch is predicted to have enough results, pick the smallest
        available (so more results go to the frontend faster).
        """
        for batch in self.done_batches:
            yield batch
        if len(self.done_batches) == len(self.all_batches):
            return
        if not len(self.done_batches):  # return the smallest batch
            yield self.all_batches[0]
        buffer = 0.1  # set to zero for picking smaller batches
        while len(self.done_batches) < len(self.all_batches):
            so_far = self.total_results_so_far
            # set here ensures we don't double count, even though it should not happen
            total_words_processed_so_far = sum([x[-1] for x in self.done_batches]) or 1
            proportion_that_matches = so_far / total_words_processed_so_far
            first_not_done: tuple[str, int] | None = None
            for batch in self.all_batches:
                if batch in self.done_batches:
                    continue
                if self.full:
                    yield batch
                    break
                if not first_not_done:
                    first_not_done = batch
                expected = batch[-1] * proportion_that_matches
                if float(expected) >= float(self.required + (self.required * buffer)):
                    yield batch
                    break
            yield first_not_done


# TODO
async def run_sentence_and_meta(qi: QueryInfo, config: dict):
    """
    Build a query to fetch sentences, with a placeholder param :ids
    """
    schema = config["schema_path"]
    seg = config["segment"]
    name = seg.strip()
    lang = qi.languages[0] if qi.languages else ""
    underlang = f"_{lang}" if lang else ""
    seg_mapping = config["mapping"]["layer"].get(seg, {}).get("prepared", {})
    if lang:
        seg_mapping = (
            config["mapping"]["layer"]
            .get(seg, {})
            .get("partitions", {})
            .get(lang, {})
            .get("prepared")
        )
    seg_name = seg_mapping.get("relation", "")
    if not seg_name:
        seg_name = f"prepared_{name}{underlang}"
    annotations: str = ""
    for layer, properties in config["layer"].items():
        if (
            layer == seg
            or properties.get("contains", "").lower() != config["token"].lower()
        ):
            continue
        annotations = ", annotations"
        break
    script = f"SELECT {name}_id, id_offset, content{annotations} FROM {schema}.{seg_name} WHERE {name}_id = ANY(:ids);"


async def run_query_on_batch(app, qi: QueryInfo, json_query: dict, batch: tuple):
    """
    Send and run a SQL query againt the DB
    then update the QueryInfo and Request's accordingly
    and launch any required sentence/meta queries
    """
    batch_name, _ = batch
    sql_query, meta_json, post_processes = json_to_sql(
        cast(QueryJSON, json_query),
        schema=qi._config.get("schema_path", ""),
        batch=batch_name,
        config=qi._config,
        lang=qi.languages[0] if qi.languages else None,
    )
    main_query = app.to_job(_db_query, sql_query)
    res = await main_query
    n_res = sum(1 if str(r) in qi.kwic_keys else 0 for r, *_ in res)
    qi.query_jobs[batch_name] = (main_query.job.id, n_res)
    qi.update()
    if batch not in qi.done_batches:
        qi.done_batches.append(batch)
    all_done = len(qi.done_batches) >= len(qi.all_batches)
    if all_done:
        qi.status = "complete"
    qi.update()
    existing_results = qi.stats_results
    # Send _aggregate_results to the worker
    (_, to_send, _, _, _) = await app.to_job(
        _aggregate_results,
        res,
        existing_results,
        meta_json,
        post_processes,
        batch,
        qi.done_batches,
    )
    main_query.job.meta["stats_results"] = {
        k: v for k, v in to_send.items() if k in qi.non_kwic_keys
    }
    main_query.job.save_meta()
    return main_query.job


async def query_pipeline(app, qi: QueryInfo, json_query: dict) -> None:
    """
    Continuously sends a query to the DB until all the results are fetched
    or all the batches have been queries
    """
    main_pipeline: bool = False if qi.running_batch else True
    running_requests = []
    lines_so_far = 0
    for batch in qi.smart_batches():
        if not batch:
            qi.update({"status": "complete"})
            return
        batch_name, batch_size = batch
        if main_pipeline:
            qi.update({"running": batch_name})
        elif batch_name == qi.running_batch:
            # Let the main pipeline run the next batches from here on out
            break
        try:
            job_id, nlines = qi.query_jobs.get(batch_name, ("", 0))
            job = Job.fetch(job_id, app["redis"])
            # refresh redis memory
            app["redis"].expire(f"rq:job:{job.id}", QUERY_TTL)
            print(f"Retrieving query from cache: {batch_name} -- {job_id}")
        except:
            print(f"No job in cache for ({batch_name}), running it now")
            job = await run_query_on_batch(app, qi, json_query, batch)
            job_id, nlines = qi.query_jobs.get(batch_name, ("", 0))
        required_before_send = qi.required
        # for each request, try to send the results for this batch (if not sent yet)
        for req in qi.get_running_requests():
            running_requests.append(req)
            await req.send_query(qi, job)
            qi.update()
        # send sentences if needed
        # if qi.kwic_keys:
        #     min_offset = (
        #         0 if not running_requests else min(r.offset for r in running_requests)
        #     )
        #     if min_offset < lines_so_far + nlines:
        #         offset_this_batch = max(0, min_offset - lines_so_far)
        #         max_this_batch = nlines if qi.full else min(nlines, qi.required)
        #         counter = -1
        #         # now scan every result line and add sent ID if counter > offset and < max
        #     # Run sentence and meta SQL queries only if asked for KWICs
        #     # asyncio.create_task(run_sentence_and_meta_on_batch())
        lines_so_far += nlines
        if not qi.full and lines_so_far >= required_before_send:
            break  # we've got enough results
    if len(qi.done_batches) >= len(qi.all_batches):
        qi.update({"status": "complete"})
    else:
        qi.update({"status": "satisfied"})
    print(
        f"Fetched {qi.total_results_so_far} lines; done with query pipeline {qi.hash}"
    )
    return None


async def process_query(app, request_data) -> tuple[dict, asyncio.Task, Request]:
    """
    Determine whether it is necessary to send queries to the DB
    and return the job info + the asyncio task + QueryInfo instance
    """
    request: Request = Request(app, request_data)
    config = app["config"][request.corpus]
    try:
        json_query = json.loads(request.query)
        json_query = json.loads(json.dumps(json_query, sort_keys=True))
    except json.JSONDecodeError:
        json_query = convert(request.query, config)
    all_batches = _get_query_batches(config, request.languages)
    sql_query, meta_query, _ = json_to_sql(
        cast(QueryJSON, json_query),
        schema=config.get("schema_path", ""),
        batch=all_batches[0][0],
        config=config,
        lang=request.languages[0] if request.languages else None,
    )
    hash = hasher(sql_query)
    qi = QueryInfo(hash, meta_query.get("result_sets", []), app, config)
    qi.add_request(request)
    qi.update()
    res = {
        "status": "started",
        "job": hash,
    }
    task = asyncio.create_task(query_pipeline(app, qi, json_query))
    return (res, task, request)


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

    job_info, task, req = await process_query(app, request_data)

    if request_data.get("synchronous"):
        await task
        return web.json_response(req._sync_buffer)
    else:
        return web.json_response(job_info)

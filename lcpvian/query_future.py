import asyncio
import json
import logging
import os
import traceback

from aiohttp import web
from redis import Redis as RedisConnection
from rq.job import Job
from typing import cast, Any, Callable, Generator
from uuid import uuid4

from .abstract_query.create import json_to_sql
from .abstract_query.typed import QueryJSON
from .authenticate import Authentication
from .convert import _aggregate_results
from .dqd_parser import convert
from .jobfuncs import _db_query
from .typed import JSONObject, ObservableDict, ObservableList
from .utils import (
    _get_query_info,
    _publish_msg,
    _update_query_info,
    get_segment_meta_script,
    hasher,
    push_msg,
    CustomEncoder,
    CustomFuture,
    LCPApplication,
)

QUERY_TTL = int(os.getenv("QUERY_TTL", 5000))

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


def segment_ids_in_query_job(
    results: list, kwic_keys: list[str], offset: int = 0, upper: int | None = None
) -> dict[str, int]:
    counter = -1
    segment_ids: dict[str, int] = {}
    for key, (sid, *_) in results:
        if str(key) not in kwic_keys:
            continue
        counter += 1
        if counter < offset:
            continue
        if upper is not None and counter >= upper:
            break
        segment_ids[str(sid)] = 1
    return segment_ids


class Request:
    """
    Received POST requests
    """

    def __init__(self, app: LCPApplication, request: str | dict = {}):
        self._app = app
        request = cast(dict, request)
        # The attributes below are immutable
        self.id: str = str(request.get("id", uuid4()))
        self.synchronous: bool | str = request.get("synchronous", False)
        self.requested: int = request.get("requested", 0)
        self.full: bool = request.get("full", False)
        self.offset: int = request.get("offset", 0)
        self.corpus: int = request.get("corpus", 1)
        self.user: str = request.get("user", "")
        self.room: str = request.get("room", "")
        self.languages: list[str] = request.get("languages", [])
        self.query: str = request.get("query", "")
        # The attributes below are dynamic and need to update redis
        self.status: str = request.get("status", "started")
        # job1: [200,400] --> sent lines 200 through 400
        self.lines_sent_per_job: dict[str, tuple[int, int]] = request.get(
            "lines_sent_per_job", {}
        )
        # keep track of which segment jobs were already sent
        self.segment_sent_jobs: dict[str, int] = request.get("segment_sent_jobs", {})
        if "hash" in request:
            self.hash: str = request["hash"]

    def update(self, name: str | None = None, value: Any = None):
        """
        Update the associated redis entry
        """
        try:
            redis = self._app["redis"]
            rhash = self.hash
            id = self.id
        except:
            return
        self_serialized = self.serialize()
        if name:
            self_serialized[name] = value
        qi = _get_query_info(redis, rhash)
        if not any(r.get("id") == id for r in qi.get("requests", [])):
            return
        all_requests = [r for r in qi.get("requests", []) if r.get("id") != id]
        all_requests.append(self_serialized)
        _update_query_info(redis, hash=rhash, info={"requests": all_requests})

    def update_dict(self, attribute_name: str, update_dict: dict):
        """
        Update a dict attribute and make sure redis is synced.
        This is necessary because setting a key would not call setattr
        """
        attribute: dict = cast(dict, self.__getattribute__(attribute_name))
        attribute.update(update_dict)
        self.update(attribute_name, attribute)

    def __getattribute__(self, name: str):
        if name.startswith("_"):
            return super().__getattribute__(name)
        # manual re-implementation of @property decorator
        if name == "lines_sent_so_far":
            lines_sent_per_job = cast(dict, self.__getattribute__("lines_sent_per_job"))
            return sum(up - lo for lo, up in lines_sent_per_job.values())
        try:
            # Try to retrieve the value from redis first
            rhash = super().__getattribute__("hash")
            id = super().__getattribute__("id")
            app = super().__getattribute__("_app")
            qi = _get_query_info(app["redis"], rhash)
            all_requests = qi.get("requests", [])
            request: dict[str, Any] = next(
                (r for r in all_requests if r.get("id") == id), {}
            )
            assert name in request, Exception()
            value = request[name]
        except:
            # Retrieve the internal value instead
            value = super().__getattribute__(name)
        return value

    def __setattr__(self, name, value):
        self.update(name, value)  # make sure to update redis first
        super().__setattr__(name, value)

    def serialize(self) -> dict:
        """
        Return a dict that only contains key-value pairs in SERIALIZABLES.
        Use this to update the associated redis entry
        """
        obj: dict = {}
        for k in dir(self):
            if k.startswith("_"):
                continue
            attr = getattr(self, k)
            if not isinstance(attr, SERIALIZABLES):
                continue
            obj[k] = attr
        return obj

    def set_sync_future(self):
        """
        Set the `synchronous` attribute to the key used by the app
        to store a future resolved with the payload in the next send_*
        """
        assert self.synchronous, RuntimeError(
            "Tried to set the sync future of a non-synchronous request"
        )
        fut = CustomFuture()
        msg_id = str(uuid4())
        self.synchronous = msg_id
        self._app["futures"][msg_id] = fut

    def delete_if_done(self, qi: "QueryInfo"):
        queries_done: bool = qi.status == "complete" or self.status == "satisfied"
        print(
            f"[{self.id}] Delete if done {qi.status} ; {self.status} ; {queries_done}"
        )
        if not queries_done:
            return
        segments_done: bool = not qi.kwic_keys
        if not segments_done:
            non_null_query_jobs: list[str] = [
                jid for jid, (_, n) in self.lines_sent_per_job.items() if n > 0
            ]
            # each query job that sent lines must have sent the segment job(s)
            segments_done = all(
                any(
                    sid in self.segment_sent_jobs
                    for sid in qi.segment_jobs_for_query_job.get(qjid, {})
                )
                for qjid in non_null_query_jobs
            )
        print(f"[{self.id}] Segments done? {segments_done}")
        if not segments_done:
            return
        qi.delete_request(self)

    def lines_for_job(self, qi, job: Job) -> tuple[int, int]:
        """
        Return the offset and number of lines required in the current job
        """
        offset_max = (0, 0)
        lines_before_job, lines_this_job = qi.get_lines_job(job.id)
        if self.offset > lines_before_job + lines_this_job:
            return offset_max
        if self.offset + self.requested < lines_before_job:
            return offset_max
        offset_this_job: int = (
            self.offset - lines_before_job if self.offset > lines_before_job else 0
        )
        max_this_job: int = offset_this_job + min(self.requested, lines_this_job)
        offset_max = (offset_this_job, max_this_job)
        self.update_dict("lines_sent_per_job", {job.id: offset_max})
        return offset_max

    async def send_segments(self, qi, query_job: Job, seg_job_id: str, res):
        if seg_job_id in self.segment_sent_jobs:
            return
        offset_this_batch, max_this_batch = self.lines_for_job(qi, query_job)
        if max_this_batch == 0:
            return
        segment_ids: dict[str, int] = segment_ids_in_query_job(
            query_job.result, qi.kwic_keys, offset_this_batch, max_this_batch
        )
        self.update_dict("segment_sent_jobs", {seg_job_id: 1})
        results: dict[str, Any] = {}
        for rtype, [sid, *rem] in res:
            if sid not in segment_ids:
                continue
            results[rtype] = results.get(rtype, []) + [[sid, *rem]]
        payload = {
            "action": "segments",
            "job": qi.hash,
            "user": self.user,
            "room": self.room,
            "status": self.status,
            "results": results,
        }
        if self.synchronous:
            print(
                f"[{self.id}] Sending segments related to job {query_job.id} (hash {qi.hash}; batch {qi.get_jobs_batch(query_job.id)}) to sync request"
            )
            fut: CustomFuture = self._app["futures"][cast(str, self.synchronous)]
            fut.set_result(results)
            self.set_sync_future()
        else:
            print(
                f"[{self.id}] Sending segments of job {query_job.id} (hash {qi.hash}; {qi.get_jobs_batch(query_job.id)}) to user '{self.user}' room '{self.room}'"
            )
            await push_msg(
                self._app["websockets"],
                self.room,
                payload,
                skip=None,
                just=(self.room, self.user),
            )
        self.delete_if_done(qi)

    async def send_query(self, qi, job: Job):
        """
        Send the payload to the associated user
        and update the request accordingly
        """
        if self.status in ("satisfied", "complete"):
            return
        offset_this_batch, max_this_batch = self.lines_for_job(qi, job)
        if max_this_batch == 0:
            print(
                f"[{self.id}] No lines required for query job {job.id} (batch {qi.get_jobs_batch(job.id)}) for this request, skipping"
            )
            return
        _, results = qi.get_stats_results()  # fetch any stats results first
        lines_so_far = -1
        for k, v in job.result:
            sk = str(k)
            if sk in qi.stats_keys:
                continue
            if sk == "0":
                results[sk] = v[0]
            if sk not in qi.kwic_keys:
                continue
            if sk not in results:
                results[sk] = []
            lines_so_far += 1
            if lines_so_far < offset_this_batch:
                continue
            if lines_so_far >= max_this_batch:
                continue
            results[sk].append(v)
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
            print(
                f"[{self.id}] Sending results of job {job.id} (hash {qi.hash}; {qi.get_jobs_batch(job.id)}) to sync request"
            )
            fut: CustomFuture = self._app["futures"][cast(str, self.synchronous)]
            fut.set_result(results)
            self.set_sync_future()
        else:
            print(
                f"[{self.id}] Sending results of job {job.id} (hash {qi.hash}; {qi.get_jobs_batch(job.id)}) to user '{self.user}' room '{self.room}'"
            )
            await push_msg(
                self._app["websockets"],
                self.room,
                payload,
                skip=None,
                just=(self.room, self.user),
            )
        self.delete_if_done(qi)


class QueryInfo:
    """
    Model the query based on the SQL of the first batch
    There is a single QueryInfo for potentially multiple POST requests (Request)
    """

    def __init__(
        self,
        qhash: str,
        meta_json: dict,
        post_processes: dict,
        app: LCPApplication,
        config: dict,
    ):
        self._app = app
        self._connection = app["redis"]
        self._config: dict = config
        self.hash = qhash
        self.meta_json: dict = meta_json
        self.result_sets: list = meta_json.get("result_sets", [])
        self.post_processes: dict = post_processes
        self.languages: list[str] = self.qi.get("languages", [])

    def update(self, obj: dict = {}):
        """
        Update the attributes of this instance and the entry in Redis
        """
        qi = _get_query_info(self._connection, self.hash)
        for aname in dir(self):
            if aname.startswith("_") or aname == "requests":
                continue
            attr = getattr(self, aname)
            if not isinstance(attr, SERIALIZABLES):
                continue
            qi[aname] = attr
        for k, v in obj.items():
            qi[k] = v
        _update_query_info(self._connection, self.hash, info=qi)
        # Update the expiration of all the related jobs
        for qjid, _ in self.query_jobs.values():
            try:
                self._connection.expire(f"rq:job:{qjid}", QUERY_TTL)
            except:
                pass

    def get_observer(self, attribute_name: str) -> Callable:
        return lambda event, value, *_: self.update({attribute_name: value})

    def get_jobs_batch(self, job_id: str) -> str:
        batch_name = next(
            (bn for bn, (qjid, _) in self.query_jobs.items() if qjid == job_id), ""
        )
        return batch_name

    @property
    def qi(self) -> dict:
        return _get_query_info(self._connection, hash=self.hash)

    # Below are the attributes that need to be kept in sync with redis
    @property
    def running_batch(self) -> str:
        return self.qi.get("running_batch", "")

    @running_batch.setter
    def running_batch(self, value: str):
        self.update({"running_batch": value})

    @property
    def status(self) -> str:
        return self.qi.get("status", "started")

    @status.setter
    def status(self, value: str):
        self.update({"status": value})

    @property
    def done_batches(self) -> list:
        done_batches = self.qi.get("done_batches", [])
        return cast(
            list,
            ObservableList(*done_batches, observer=self.get_observer("done_batches")),
        )

    @done_batches.setter
    def done_batches(self, value: list):
        self.update({"done_batches": value})

    @property
    def query_jobs(self) -> dict:
        """
        Map batch names with (query_job_id, n_kwic_lines)
        """
        query_jobs = self.qi.get("query_jobs", {})
        return cast(
            dict,
            ObservableDict(observer=self.get_observer("query_jobs"), **query_jobs),
        )

    @query_jobs.setter
    def query_jobs(self, value: dict):
        self.update({"query_jobs": value})

    @property
    def segment_jobs_for_query_job(self) -> dict[str, list[str]]:
        # {query_job_id: [segment_job_id, segment_job_id]}
        segment_jobs_for_query_job = self.qi.get("segment_jobs_for_query_job", {})
        return cast(
            dict,
            ObservableDict(
                observer=self.get_observer("segment_jobs_for_query_job"),
                **segment_jobs_for_query_job,
            ),
        )

    @segment_jobs_for_query_job.setter
    def segment_jobs_for_query_job(self, value: dict[str, list[str]]):
        self.update({"segment_jobs_for_query_job": value})

    # Methods
    def has_request(self, request: Request, cache: bool = False):
        return any(r.id == request.id for r in self.requests)

    def add_request(self, request: Request):
        request.hash = self.hash
        serialized_requests = [
            r.serialize() for r in self.requests if r.id != request.id
        ]
        serialized_requests.append(request.serialize())
        _update_query_info(
            self._connection, self.hash, info={"requests": serialized_requests}
        )

    def delete_request(self, request: Request):
        if not self.has_request(request):
            return
        requests = [r.serialize() for r in self.requests if r.id != request.id]
        _update_query_info(self._connection, self.hash, info={"requests": requests})

    def get_running_requests(self) -> list[Request]:
        return [r for r in self.requests if r.status not in ("satisfied", "complete")]

    def get_lines_job(self, job_id: str) -> tuple[int, int]:
        """
        Return the number of kwic lines in the batches before this one
        and the number of kwic lines in this batch
        """
        lines_before_batch: int = 0
        lines_this_batch: int = 0
        for qjid, n in self.query_jobs.values():
            if qjid == job_id:
                lines_this_batch = n
                break
            lines_before_batch += n
        return (lines_before_batch, lines_this_batch)

    def get_stats_results(self) -> tuple[list, dict]:
        """
        All the non-KWIC results
        """
        if not self.query_jobs:
            return ([], {})
        try:
            first_job = next(
                Job.fetch(qjid, self._connection)
                for qjid, _ in self.query_jobs.values()
            )
            batches, stats = first_job.meta.get("stats_results", ([], {}))
            return (batches, stats)
        except:
            return ([], {})

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

    # Pseudo-attributes (no need to keep in sync)
    @property
    def requests(self) -> list[Request]:
        """
        Return the associated requests
        The class Request already implements utmost recency
        """
        qi = _get_query_info(self._connection, self.hash)
        return [Request(self._app, qr) for qr in qi.get("requests", [])]

    @property
    def all_batches(self) -> list[tuple[str, int]]:
        return _get_query_batches(self._config, self.languages)

    @property
    def kwic_keys(self) -> list[str]:
        return [
            str(n)
            for n, mr in enumerate(self.result_sets, start=1)
            if mr.get("type") == "plain"
        ]

    @property
    def stats_keys(self) -> list[str]:
        return [
            str(n)
            for n, mr in enumerate(self.result_sets, start=1)
            if mr.get("type") != "plain"
        ]

    @property
    def full(self) -> bool:
        running_requests: list[Request] = self.get_running_requests()
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
    def total_results_so_far(self) -> int:
        return sum(nlines for _, nlines in self.query_jobs.values())


async def segment_and_meta(
    app: LCPApplication,
    qi: QueryInfo,
    batch_name: str,
    query_job: Job,
    offset_this_batch: int,
    max_this_batch: int,
):
    """
    Build a query to fetch sentences, with a placeholder param :ids
    """
    all_segment_ids: dict[str, int] = segment_ids_in_query_job(
        query_job.result, qi.kwic_keys, offset_this_batch, max_this_batch
    )
    seg_job_ids = qi.segment_jobs_for_query_job.setdefault(query_job.id, [])
    existing_seg_ids: dict[str, int] = {}
    for sjid in seg_job_ids:
        try:
            # Retrieve any associated segment job query from cache
            sjob = Job.fetch(sjid, app["redis"])
            app["redis"].expire(f"rq:job:{sjob.id}", QUERY_TTL)
            print(f"Retrieving segment query from cache: {batch_name} -- {sjid}")
            existing_seg_ids.update({str(sid): 1 for sid, *_ in sjob.result})
            # Requests with new offset/requested values could (partially) reuse old results
            for r in qi.requests:
                await r.send_segments(qi, query_job, sjid, sjob.result)
        except:
            pass
    if existing_seg_ids:
        print(
            f"Found {len(existing_seg_ids)}/{len(all_segment_ids)} segments in cache for {batch_name}"
        )
    segment_ids: list[str] = [
        sid for sid in all_segment_ids if sid not in existing_seg_ids
    ]
    if not segment_ids:
        return []
    script = get_segment_meta_script(qi._config, qi.languages, batch_name, segment_ids)
    shash = hasher(script)
    if shash not in seg_job_ids:
        qi.segment_jobs_for_query_job[query_job.id].append(shash)
    try:
        segment_job = Job.fetch(shash, connection=app["redis"])
        print(f"Retrieving segment query from cache: {batch_name} -- {shash}")
        res = json.loads(json.dumps(segment_job.result, cls=CustomEncoder))
    except:
        segment_query = app.to_job(_db_query, script, job_id=shash)
        print(f"Running new segment query for {batch_name}")
        res = await segment_query
    for r in qi.requests:
        await r.send_segments(qi, query_job, shash, res)
    return res


# TODO: revise return conditions, right now it's run every time
async def run_aggregate(
    app: LCPApplication,
    qi: QueryInfo,
    offset: int,
    batch: tuple,
    meta_json: dict,
    post_processes: dict,
):
    job_id, _ = qi.query_jobs[batch[0]]
    job: Job = Job.fetch(job_id, connection=app["redis"])
    res: list = job.result
    stats_batches, stats_results = qi.get_stats_results()
    lines_so_far, n_res = qi.get_lines_job(job.id)
    past_batch = json.loads(json.dumps(batch, cls=CustomEncoder)) in json.loads(
        json.dumps(stats_batches, cls=CustomEncoder)
    )
    if n_res == 0 or lines_so_far + n_res < offset or past_batch:
        return
    new_stats_batches = [b for b in stats_batches] + [batch]
    (_, to_send, _, _, _) = await app.to_job(
        _aggregate_results,
        res,
        stats_results,
        meta_json,
        post_processes,
        batch,
        qi.done_batches,
    )
    new_stats_results = {k: v for k, v in to_send.items() if k in qi.stats_keys}
    try:
        first_job = Job.fetch(
            next(qjid for qjid, _ in qi.query_jobs.values()), app["redis"]
        )
    except:
        first_job = job
    serializer = CustomEncoder()
    first_job.meta["stats_results"] = serializer.default(
        [new_stats_batches, new_stats_results]
    )
    first_job.save_meta()


async def run_query_on_batch(
    app: LCPApplication, qi: QueryInfo, json_query: dict, batch: tuple
):
    """
    Send and run a SQL query againt the DB
    then update the QueryInfo and Request's accordingly
    and launch any required sentence/meta queries
    """
    batch_name, _ = batch
    sql_query, _, _ = json_to_sql(
        cast(QueryJSON, json_query),
        schema=qi._config.get("schema_path", ""),
        batch=batch_name,
        config=qi._config,
        lang=qi.languages[0] if qi.languages else None,
    )
    main_query = app.to_job(_db_query, sql_query, job_id=hasher(sql_query))
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
    return main_query.job


async def query_pipeline(app: LCPApplication, qi: QueryInfo, json_query: dict) -> None:
    """
    Continuously sends a query to the DB until all the results are fetched
    or all the batches have been queries
    """
    main_pipeline: bool = False if qi.running_batch else True
    has_kwic: bool = len(qi.kwic_keys) > 0
    running_requests: list[Request] = []
    lines_so_far = 0
    for batch in qi.smart_batches():
        if not batch:
            qi.status = "complete"
            return
        batch_name, batch_size = batch
        if main_pipeline:
            qi.running_batch = batch_name
        elif batch_name == qi.running_batch:
            # Let the main pipeline run the next batches from here on out
            print(
                "Done with serving cached results, letting the main pipeline do its job"
            )
            break
        try:
            job_id, nlines = qi.query_jobs.get(batch_name, ("", 0))
            job = Job.fetch(job_id, app["redis"])
            # refresh redis memory
            app["redis"].expire(f"rq:job:{job.id}", QUERY_TTL)
            print(
                f"{'MAIN: ' if main_pipeline else ''}Retrieving query from cache: {batch_name} -- {job_id}"
            )
        except:
            print(
                f"{'MAIN: ' if main_pipeline else ''}No job in cache for {batch_name}, running it now"
            )
            job = await run_query_on_batch(app, qi, json_query, batch)
            job_id, nlines = qi.query_jobs.get(batch_name, ("", 0))
        min_offset = min(r.offset for r in running_requests) if running_requests else 0
        await run_aggregate(app, qi, min_offset, batch, qi.meta_json, qi.post_processes)
        required_before_send = qi.required
        # for each request, try to send the results for this batch (if not sent yet)
        for req in qi.get_running_requests():
            running_requests.append(req)
            await req.send_query(qi, job)
            if has_kwic:
                # Signal that this job needs lines
                req.update_dict("lines_sent_per_job", {job_id: (0, 0)})
            qi.update()
        # send sentences if needed
        if has_kwic:
            min_offset = (
                0 if not running_requests else min(r.offset for r in running_requests)
            )
            lines_with_batch = lines_so_far + nlines
            # Send only if this batch exceeds the offset and this batch starts before what's required
            need_segments_this_batch = (
                lines_with_batch > min_offset and required_before_send > lines_so_far
            )
            print(
                f"{'MAIN: ' if main_pipeline else ''}in has_kwic, need segments for {batch_name}?",
                min_offset,
                lines_so_far,
                nlines,
                lines_with_batch,
                required_before_send,
                need_segments_this_batch,
            )
            if need_segments_this_batch:
                offset_this_batch = max(0, min_offset - lines_so_far)
                max_this_batch = (
                    nlines
                    if qi.full
                    else min(nlines, required_before_send - lines_so_far)
                )
                asyncio.create_task(
                    segment_and_meta(
                        app, qi, batch_name, job, offset_this_batch, max_this_batch
                    )
                )
        lines_so_far += nlines
        if not qi.full and lines_so_far >= required_before_send:
            break  # we've got enough results
    if main_pipeline:
        qi.running_batch = ""
    if len(qi.done_batches) >= len(qi.all_batches):
        qi.status = "complete"
    else:
        qi.status = "satisfied"
    return None


def process_query(app, request_data) -> tuple[dict, asyncio.Task, Request]:
    """
    Determine whether it is necessary to send queries to the DB
    and return the job info + the asyncio task + QueryInfo instance
    """
    request: Request = Request(app, request_data)
    print(
        f"Received new POST request: {request.id} ; {request.offset} -- {request.requested}"
    )
    if request.synchronous:
        request.set_sync_future()
    config = app["config"][request.corpus]
    try:
        json_query = json.loads(request.query)
        json_query = json.loads(json.dumps(json_query, sort_keys=True))
    except json.JSONDecodeError:
        json_query = convert(request.query, config)
    all_batches = _get_query_batches(config, request.languages)
    sql_query, meta_json, post_processes = json_to_sql(
        cast(QueryJSON, json_query),
        schema=config.get("schema_path", ""),
        batch=all_batches[0][0],
        config=config,
        lang=request.languages[0] if request.languages else None,
    )
    shash = hasher(sql_query)
    qi = QueryInfo(shash, meta_json, post_processes, app, config)
    qi.add_request(request)
    qi.update()
    res = {
        "status": "started",
        "job": shash,
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

    job_info, task, req = process_query(app, request_data)
    qi = QueryInfo(req.hash, {}, {}, cast(LCPApplication, app), {})

    if req.synchronous:
        buffer = {}
        while qi.has_request(req):
            fut: CustomFuture = app["futures"][req.synchronous]
            res = await fut
            buffer.update(res)
        # Delete references to any new future created for this request
        app["futures"].pop(req.synchronous, "")
        print(f"[{req.id}] Done with synchronous request")
        serializer = CustomEncoder()
        return web.json_response(serializer.default(buffer))
    else:
        return web.json_response(job_info)

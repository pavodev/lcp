import asyncio
import json
import logging
import os
import traceback

from aiohttp import web
from asyncio import Task
from redis import Redis as RedisConnection
from rq import Callback, Queue
from rq.job import get_current_job, Job
from typing import cast, Any, Callable, Generator
from uuid import uuid4

from .abstract_query.create import json_to_sql
from .abstract_query.typed import QueryJSON
from .authenticate import Authentication
from .callbacks import _general_failure
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
    refresh_job_ttl,
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
) -> list[list[str | int]]:
    """
    Get a list of tuples in the format of (batch_suffix, size) to be queried
    """
    out: list[list[str | int]] = []
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
        out.append([name, size])
    return sorted(out, key=lambda x: x[-1])


def segment_ids_in_query_job(
    results: list, kwic_keys: list[str], offset: int = 0, upper: int | None = None
) -> dict[str, int]:
    """
    Return the unique segment IDs listed in the query job's result for the provided offset+upper
    """
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

    def __init__(self, connection: RedisConnection, request: str | dict = {}):
        self._connection = connection
        request = cast(dict, request)
        # The attributes below are immutable
        self.id: str = str(request.get("id", uuid4()))
        self.synchronous: bool = request.get("synchronous", False)
        self.futures: list[str] = []
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
        # job1: [200,400,30] --> sent lines 200 through 400, need 30 segments
        self.lines_batch: dict[str, tuple[int, int, int]] = request.get(
            "lines_batch", {}
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
            redis = self._connection
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
            lines_batch = cast(dict, self.__getattribute__("lines_batch"))
            return sum(up for _, up, _ in lines_batch.values())
        try:
            # Try to retrieve the value from redis first
            rhash = super().__getattribute__("hash")
            id = super().__getattribute__("id")
            connection = super().__getattribute__("_connection")
            qi = _get_query_info(connection, rhash)
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

    # methods called from worker
    async def respond(self, msg_id: str):
        payload = self._connection.get(msg_id)
        # publish_msg here

    # methods called from app
    async def callback():
        pass

    # def add_sync_future(self) -> str:
    #     """
    #     Set the `synchronous` attribute to the key used by the app
    #     to store a future resolved with the payload in the next send_*
    #     """
    #     assert self.synchronous, RuntimeError(
    #         "Tried to add a future of a non-synchronous request"
    #     )
    #     fut = CustomFuture()
    #     msg_id: str = str(uuid4())
    #     self._app["futures"][msg_id] = fut
    #     self.futures = self.futures + [msg_id]
    #     return msg_id

    # def next_future(self) -> str:
    #     """
    #     Get the next undone future listed in self.futures
    #     """
    #     assert self.synchronous, RuntimeError(
    #         "Tried to get a future for a non-synchronous request"
    #     )
    #     try:
    #         msg_id = next(m for m in self.futures if not self._app["futures"][m].done())
    #     except:
    #         msg_id = self.add_sync_future()
    #     return msg_id

    def is_done(self, qi: "QueryInfo") -> bool:
        queries_done: bool = qi.status == "complete" or self.status == "satisfied"
        if not queries_done:
            return False
        if not qi.kwic_keys:
            return True
        nlines_query: int = sum(n for _, _, n in self.lines_batch.values())
        nlines_segments: int = sum(n for n in self.segment_sent_jobs.values())
        return nlines_segments >= nlines_query

    def delete_if_done(self, qi: "QueryInfo"):
        if not self.is_done(qi):
            return
        print(f"[{self.id}] DELETE REQUEST NOW")
        qi.delete_request(self)

    def lines_for_job(self, qi: "QueryInfo", job: Job) -> tuple[int, int]:
        """
        Return the offset and number of lines required in the current job
        """
        offset_and_lines_for_req = (0, 0)
        lines_before_job, lines_job = qi.get_lines_batch(job.id)
        if self.offset > lines_before_job + lines_job:
            return offset_and_lines_for_req
        if self.offset + self.requested < lines_before_job:
            return offset_and_lines_for_req
        lines_for_req: int = self.requested
        offset_for_req: int = self.offset - lines_before_job
        if offset_for_req < 0:
            # we got lines before: we need fewer this time around
            lines_for_req += offset_for_req
            offset_for_req = 0
        if offset_for_req + lines_for_req > lines_job:
            lines_for_req = lines_job - offset_for_req
        offset_and_lines_for_req = (offset_for_req, lines_for_req)
        return offset_and_lines_for_req

    async def send_segments(
        self, qi: "QueryInfo", query_job: Job, seg_job_id: str, res
    ):
        if seg_job_id in self.segment_sent_jobs:
            return
        offset_this_batch, lines_this_batch = self.lines_for_job(qi, query_job)
        if lines_this_batch == 0:
            return
        segment_ids: dict[str, int] = segment_ids_in_query_job(
            query_job.result,
            qi.kwic_keys,
            offset_this_batch,
            offset_this_batch + lines_this_batch,
        )
        sent_seg_ids: dict[str, int] = {}
        results: dict[str, Any] = {}
        for rtype, [sid, *rem] in res:
            if sid not in segment_ids:
                continue
            results[str(rtype)] = results.get(str(rtype), []) + [[sid, *rem]]
            sent_seg_ids[sid] = 1
        results["0"] = {"result_sets": qi.result_sets, "meta_labels": qi.meta_labels}
        payload = {
            "action": "segments",
            "job": qi.hash,
            "user": self.user,
            "room": self.room,
            "status": self.status,
            "result": results,
            "n": len(sent_seg_ids),
            "hash": self.hash,
            "seg_job_id": seg_job_id,
        }
        batch_name = qi.get_jobs_batch(query_job.id)
        to_msg = (
            "to sync request"
            if self.synchronous
            else f"to user '{self.user}' room '{self.room}'"
        )
        print(
            f"[{self.id}] Sending {len(sent_seg_ids)} segments for batch {batch_name} (hash {qi.hash}; job {query_job.id}) {to_msg}"
        )
        if self.synchronous:
            # msg_id: str = self.next_future()
            # fut: CustomFuture = self._app["futures"][msg_id]
            # fut.set_result(payload)
            pass
        else:
            # await push_msg(
            #     self._app["websockets"],
            #     self.room,
            #     payload,
            #     skip=None,
            #     just=(self.room, self.user),
            # )
            self.update_dict("segment_sent_jobs", {seg_job_id: len(sent_seg_ids)})
        print(f"[{self.id}] Sent {len(sent_seg_ids)} segments for batch {batch_name}")

    async def send_query(self, qi: "QueryInfo", job: Job):
        """
        Send the payload to the associated user
        and update the request accordingly
        """
        if self.lines_batch.get(job.id, (0, 0, 0))[1] > 0:
            # If some lines were already sent for this job
            return
        offset_this_batch, lines_this_batch = self.lines_for_job(qi, job)
        n_seg_ids: int = 0
        if qi.kwic_keys:
            n_seg_ids = len(
                segment_ids_in_query_job(
                    job.result,
                    qi.kwic_keys,
                    offset_this_batch,
                    offset_this_batch + lines_this_batch,
                )
            )
            if self.synchronous:
                # if one needs kwic lines, make sure there's a pending future for that
                # self.next_future()
                pass
        self.update_dict(
            "lines_batch",
            {job.id: (offset_this_batch, lines_this_batch, n_seg_ids)},
        )
        if lines_this_batch == 0:
            print(
                f"[{self.id}] No lines required for batch {qi.get_jobs_batch(job.id)} (job {job.id}) for this request, skipping"
            )
            return
        _, results = qi.get_stats_results()  # fetch any stats results first
        lines_so_far = -1
        for k, v in job.result:
            sk = str(k)
            if sk in qi.stats_keys:
                continue
            # if sk == "0":
            #     results[sk] = v[0]
            if sk not in qi.kwic_keys:
                continue
            if sk not in results:
                results[sk] = []
            lines_so_far += 1
            if lines_so_far < offset_this_batch:
                continue
            if lines_so_far >= offset_this_batch + lines_this_batch:
                continue
            results[sk].append(v)
        if qi.status == "complete" or self.lines_sent_so_far >= self.requested:
            self.status = "satisfied"
        results["0"] = {"result_sets": qi.result_sets, "meta_labels": qi.meta_labels}
        payload = {
            "action": "query_result",
            "job": qi.hash,
            "user": self.user,
            "room": self.room,
            "status": self.status,
            "result": results,
            "hash": self.hash,
        }
        qi.update()
        batch_name = qi.get_jobs_batch(job.id)
        to_msg = (
            "to sync request"
            if self.synchronous
            else f"to user '{self.user}' room '{self.room}'"
        )
        print(
            f"[{self.id}] Sending {lines_this_batch} results lines for batch {batch_name} (hash {qi.hash}; job {job.id}) {to_msg}"
        )
        if self.synchronous:
            # msg_id: str = self.next_future()
            # fut: CustomFuture = self._app["futures"][msg_id]
            # fut.set_result(payload)
            pass
        else:
            # Delegate this to sock.py
            # await push_msg(
            #     self._app["websockets"],
            #     self.room,
            #     cast(JSONObject, payload),
            #     skip=None,
            #     just=(self.room, self.user),
            # )
            pass


async def respond_request(qhash: str, msg_id: str):
    current_job: Job = cast(Job, get_current_job())
    connection: RedisConnection = current_job.connection
    qi = QueryInfo(qhash, connection=connection)
    # TODO: read payload from redis memory here
    payload = {}
    # Use TaskQ gather thingy from rq here?
    for req in qi.requests:
        await req.respond(payload)


class QueryInfo:
    """
    Model the query based on the SQL of the first batch
    There is a single QueryInfo for potentially multiple POST requests (Request)
    """

    def __init__(
        self,
        qhash: str,
        connection: RedisConnection,
        json_query: dict | None = None,
        meta_json: dict | None = None,
        post_processes: dict | None = None,
        config: dict | None = None,
    ):
        self._connection = connection
        self.hash = qhash
        qi = self.qi
        self.json_query: dict = json_query or qi.get("json_query", {})
        self.config: dict = config or qi.get("config", {})
        self.meta_json: dict = meta_json or qi.get("meta_json", {})
        self.post_processes: dict = post_processes or qi.get("post_processes", {})
        self.result_sets: list = self.meta_json.get("result_sets", [])
        self.meta_labels: list[str] = qi.get("meta_labels", [])
        self.languages: list[str] = qi.get("languages", [])
        self.update()

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
        for qjid, _ in self.query_batches.values():
            try:
                refresh_job_ttl(self._connection, qjid)
            except:
                pass

    def enqueue(
        self,
        method,
        *args,
        job_id: str | None = None,
        callback: Callable | None = None,
        **kwargs,
    ) -> Job:
        q = Queue("background", connection=self._connection)
        on_success: Callback | None = (
            Callback(callback, QUERY_TTL) if callback else None
        )
        return q.enqueue(
            method,
            on_success=on_success,
            on_failure=Callback(_general_failure, QUERY_TTL),
            result_ttl=QUERY_TTL,
            job_timeout=QUERY_TTL,
            args=args,
            job_id=job_id,
        )

    def get_observer(self, attribute_name: str) -> Callable:
        return lambda event, value, *_: self.update({attribute_name: value})

    def get_jobs_batch(self, job_id: str) -> str:
        batch_name = next(
            (bn for bn, (qjid, _) in self.query_batches.items() if qjid == job_id), ""
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
    def query_batches(self) -> dict:
        """
        Map batch names with (query_job_id, n_kwic_lines)
        """
        query_batches = self.qi.get("query_batches", {})
        return cast(
            dict,
            ObservableDict(
                observer=self.get_observer("query_batches"), **query_batches
            ),
        )

    @query_batches.setter
    def query_batches(self, value: dict):
        self.update({"query_batches": value})

    @property
    def segment_jobs_for_query_job(self) -> dict[str, list[str]]:
        """
        All the segment jobs associated to the query job
        """
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
        return [r for r in self.requests if not r.is_done(self)]

    def get_lines_batch(self, job_id: str) -> tuple[int, int]:
        """
        Return the number of kwic lines in the batches before this one
        and the number of kwic lines in this batch
        """
        lines_before_batch: int = 0
        lines_this_batch: int = 0
        for qjid, n in self.query_batches.values():
            if qjid == job_id:
                lines_this_batch = n
                break
            lines_before_batch += n
        return (lines_before_batch, lines_this_batch)

    def get_stats_results(self) -> tuple[list, dict]:
        """
        All the non-KWIC results
        """
        if not self.query_batches:
            return ([], {})
        try:
            first_job = next(
                Job.fetch(qjid, self._connection)
                for qjid, _ in self.query_batches.values()
            )
            batches, stats = first_job.meta.get("stats_results", ([], {}))
            return (batches, stats)
        except:
            return ([], {})

    def decide_next_batch(self, previous_batch: str | None = None) -> list:
        """
        Return the batches in an optimized ordered.

        Pick the smallest batch first. Query the smallest available result until
        `requested` results are collected. Then, using the result count of the
        queried batches and the word counts of the remaining batches, predict the
        smallest next batch that's likely to yield enough results and return it.

        If no batch is predicted to have enough results, pick the smallest
        available (so more results go to the frontend faster).
        """
        if not previous_batch or not len(self.done_batches):
            return self.all_batches[0]
        next_batch: list = next(
            (
                b
                for n, b in enumerate(self.done_batches)
                if n > 0 and self.done_batches[n - 1][0] == previous_batch
            ),
            [],
        )
        if next_batch:
            return next_batch

        buffer = 0.1  # set to zero for picking smaller batches
        while len(self.done_batches) < len(self.all_batches):
            so_far = self.total_results_so_far
            # set here ensures we don't double count, even though it should not happen
            total_words_processed_so_far = sum([x[-1] for x in self.done_batches]) or 1
            proportion_that_matches = so_far / total_words_processed_so_far
            first_not_done: list[str | int] | None = None
            for batch in self.all_batches:
                if batch in self.done_batches:
                    continue
                if self.full:
                    return batch
                if not first_not_done:
                    first_not_done = batch
                expected = cast(int, batch[-1]) * proportion_that_matches
                if float(expected) >= float(self.required + (self.required * buffer)):
                    return batch
            return cast(list, first_not_done)

        return []

    # Pseudo-attributes (no need to keep in sync)
    @property
    def requests(self) -> list[Request]:
        """
        Return the associated requests
        The class Request already implements utmost recency
        """
        qi = _get_query_info(self._connection, self.hash)
        return [Request(self._connection, qr) for qr in qi.get("requests", [])]

    @property
    def all_batches(self) -> list[list[str | int]]:
        return _get_query_batches(self.config, self.languages)

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
    def status(self) -> str:
        if len(self.done_batches) >= len(self.all_batches):
            return "complete"
        if self.total_results_so_far >= self.required:
            return "satisfied"
        return "started"

    @property
    def full(self) -> bool:
        running_requests: list[Request] = self.get_running_requests()
        return any(r.full for r in running_requests) if running_requests else False

    @property
    def required(self) -> int:
        """
        The required number of results lines is the max offset+requested out of all the Request's
        """
        # running_requests = self.get_running_requests()
        running_requests = self.requests
        return (
            max(r.offset + r.requested for r in running_requests)
            if running_requests
            else 0
        )

    @property
    def total_results_so_far(self) -> int:
        return sum(nlines for _, nlines in self.query_batches.values())

    # methods called from worker
    async def do_segment_and_meta(
        self,
        batch_name: str,
        offset_this_batch: int,
        lines_this_batch: int,
    ):
        """
        Build a query to fetch sentences, with a placeholder param :ids
        """
        current_job: Job = cast(Job, get_current_job())
        connection: RedisConnection = current_job.connection
        all_segment_ids: dict[str, int] = segment_ids_in_query_job(
            query_job.result,
            self.kwic_keys,
            offset_this_batch,
            offset_this_batch + lines_this_batch,
        )
        seg_job_ids = self.segment_jobs_for_query_job.setdefault(query_job.id, [])
        existing_seg_ids: dict[str, int] = {}
        for sjid in seg_job_ids:
            try:
                # Retrieve any associated segment job query from cache
                sjob = Job.fetch(sjid, connection)
                refresh_job_ttl(connection, sjob.id)
                print(f"Retrieving segment query from cache: {batch_name} -- {sjid}")
                existing_seg_ids.update({str(sid): 1 for _, [sid, *_] in sjob.result})
                # Requests with new offset/requested values could (partially) reuse old results
                for r in self.requests:
                    await r.send_segments(self, query_job, sjid, sjob.result)
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
        script, meta_labels = get_segment_meta_script(
            self.config, self.languages, batch_name, segment_ids
        )
        self.meta_labels = meta_labels
        self.update({"meta_labels": meta_labels})
        shash = hasher(script)
        if shash in seg_job_ids:
            return
        self.segment_jobs_for_query_job[query_job.id].append(shash)
        try:
            segment_job = Job.fetch(shash, connection=connection)
            print(f"Retrieving segment query from cache: {batch_name} -- {shash}")
            res = json.loads(json.dumps(segment_job.result, cls=CustomEncoder))
        except:
            segment_query = await job_query(connection, script, job_id=shash)
            print(f"Running new segment query for {batch_name}")
            res = await segment_query
        for r in self.requests:
            await r.send_segments(self, query_job, shash, res)

    async def run_aggregate(
        self,
        offset: int,
        batch: list,
    ):
        meta_json: dict = self.meta_json
        post_processes: dict = self.post_processes
        job_id, _ = self.query_batches[batch[0]]
        job: Job = Job.fetch(job_id, connection=self._connection)
        res: list = job.result
        stats_batches, stats_results = self.get_stats_results()
        lines_so_far, n_res = self.get_lines_batch(job.id)
        past_batch = json.loads(json.dumps(batch, cls=CustomEncoder)) in json.loads(
            json.dumps(stats_batches, cls=CustomEncoder)
        )
        if n_res == 0 or lines_so_far + n_res < offset or past_batch:
            return
        new_stats_batches = [b for b in stats_batches] + [batch]
        (_, to_send, _, _, _) = _aggregate_results(
            res,
            stats_results,
            meta_json,
            post_processes,
            batch,
            self.done_batches,
        )
        new_stats_results = {k: v for k, v in to_send.items() if k in self.stats_keys}
        stats_keys = f"{self.hash}::stats"
        self._connection.set(
            stats_keys,
            json.dumps([new_stats_batches, new_stats_results], cls=CustomEncoder),
        )
        self._connection.expire(stats_keys, QUERY_TTL)

    async def run_query_on_batch(self, batch) -> str:
        """
        Send and run a SQL query againt the DB
        then update the QueryInfo and Request's accordingly
        and launch any required sentence/meta queries
        """
        current_job: Job = cast(Job, get_current_job())
        connection: RedisConnection = current_job.connection
        batch_name, _ = batch
        sql_query, _, _ = json_to_sql(
            cast(QueryJSON, self.json_query),
            schema=self.config.get("schema_path", ""),
            batch=batch_name,
            config=self.config,
            lang=self.languages[0] if self.languages else None,
        )
        batch_hash = hasher(sql_query)
        res = await _db_query(sql_query)
        self._connection.set(batch_hash, json.dumps(res, cls=CustomEncoder))
        self._connection.expire(batch_hash, QUERY_TTL)
        res = res if res else []
        n_res = sum(1 if str(r) in self.kwic_keys else 0 for r, *_ in res)
        self.query_batches[batch_name] = (batch_hash, n_res)
        if batch not in self.done_batches:
            self.done_batches.append(batch)
        self.update()
        return batch_hash

    # called from the worker
    async def callback(self, batch_name: str):

        msg_id: str = str(uuid4())
        _publish_msg(
            self._connection,
            {"callback_query": "main", "batch": batch_name, "hash": self.hash},
            msg_id=msg_id,
        )

        # do next batch (if needed)
        do_next_batch(self.hash, self._connection, batch_name)

        # run needed segment+meta queries
        lines_before, lines_now = self.get_lines_batch(batch_name)
        lines_so_far = lines_before + lines_now
        # send sentences if needed
        if not self.kwic_keys:
            return

        min_offset = min(r.offset for r in self.requests)
        # Send only if this batch exceeds the offset and this batch starts before what's required
        need_segments_this_batch = (
            lines_so_far > min_offset and self.required > lines_so_far
        )
        print(
            f"in has_kwic, need segments for {batch_name}?",
            min_offset,
            lines_so_far,
            need_segments_this_batch,
        )
        if not need_segments_this_batch:
            return

        offset_this_batch = max(0, min_offset - lines_so_far)
        lines_this_batch = (
            lines_now if self.full else min(lines_now, self.required - lines_so_far)
        )
        await self.do_segment_and_meta(
            batch_name,
            offset_this_batch,
            lines_this_batch,
        )


async def do_batch(qhash: str, batch: list):
    current_job: Job | None = get_current_job()
    assert current_job, RuntimeError(f"No current jbo found for do_batch {batch}")
    connection = current_job.connection
    qi = QueryInfo(qhash, connection=connection)
    batch_name = cast(str, batch[0])
    if batch_name == qi.running_batch:
        # This batch is already running: stop here
        return
    # Now this is the running batch
    qi.running_batch = batch_name
    try:
        batch_hash, nlines = qi.query_batches.get(batch_name, ("", 0))
        # refresh redis memory
        refresh_job_ttl(connection, batch_hash)
        print(f"Retrieving query from cache: {batch_name} -- {batch_hash}")
    except:
        print(f"No job in cache for {batch_name}, running it now")
        await qi.run_query_on_batch(batch)
        batch_hash, nlines = qi.query_batches.get(batch_name, ("", 0))

    if qi.kwic_keys:
        # Indicate asap that lines are needed for this job
        for req in qi.get_running_requests():
            req.update_dict("lines_batch", {batch_hash: (0, 0, qi.required + 1)})

    min_offset = min(r.offset for r in qi.requests)
    await qi.run_aggregate(min_offset, batch)

    await qi.callback(batch_name)


async def qi_callback(job: Job, connection: RedisConnection, result: Any):
    qi: QueryInfo = QueryInfo(job.args[0], connection=connection)
    await qi.callback(result)


def do_next_batch(
    qhash: str, connection: RedisConnection, previous_batch_name: str | None = None
) -> Job | None:
    qi = QueryInfo(qhash, connection=connection)
    next_batch = qi.decide_next_batch(previous_batch_name)
    if not next_batch:
        return None
    return qi.enqueue(do_batch, qhash, next_batch, callback=qi_callback)


def launch_query(qhash: str) -> Job | None:
    """
    Continuously sends a query to the DB until all the results are fetched
    or all the batches have been queries
    """
    current_job: Job | None = get_current_job()
    assert current_job is not None, RuntimeError(f"No job found to launch the query")
    connection = current_job.connection
    return do_next_batch(qhash, connection)


def process_query(
    app: LCPApplication, request_data: dict
) -> tuple[Request, QueryInfo, Any]:
    """
    Determine whether it is necessary to send queries to the DB
    and return the job info + the asyncio task + QueryInfo instance
    """
    request: Request = Request(app["redis"], request_data)
    print(
        f"Received new POST request: {request.id} ; {request.offset} -- {request.requested}"
    )
    if request.synchronous:
        # request.add_sync_future()
        pass
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
        batch=cast(str, all_batches[0][0]),
        config=config,
        lang=request.languages[0] if request.languages else None,
    )
    shash = hasher(sql_query)
    qi = QueryInfo(shash, app["redis"], json_query, meta_json, post_processes, config)
    qi.add_request(request)
    qi.update()
    # TODO: try sending this to a worker instead?
    # no access to app: pass config and stuff directly
    # have the job complete only when req is done
    future: CustomFuture = app.to_worker(launch_query, shash)
    return (request, qi, future)


def get_handle_exception(app: LCPApplication, req: Request, qi: QueryInfo):
    def handle_exception(task):
        try:
            result = task.result()  # Will raise an exception if the task failed
            print(f"[{req.id}] Callback successfull")
        except Exception as e:
            print(f"Caught exception: {e}")
            qi.running_batch = ""  # No longer running
            if req.synchronous:
                return
            asyncio.create_task(
                push_msg(
                    app["websockets"],
                    req.room,
                    {"action": "failed", "status": "failed", "value": f"{e}"},
                    skip=None,
                    just=(req.room, req.user),
                )
            )

    return handle_exception


async def post_query(request: web.Request) -> web.Response:
    """
    Main query endpoint: generate and queue up corpus queries
    """
    app = cast(LCPApplication, request.app)
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

    (req, qi, future) = process_query(app, request_data)
    # task = asyncio.create_task(routine)
    # task.add_done_callback(get_handle_exception(app, req, qi))

    if req.synchronous:
        buffer = {}
        while 1:
            await asyncio.sleep(0.5)
            if not qi.has_request(req):
                break
            # if not req.futures:
            #     continue
            # msg_id: str = req.futures[0]
            # fut: CustomFuture = app["futures"][msg_id]
            # res = await fut
            # req.futures = req.futures[1:]
            # app["futures"].pop(msg_id)  # discard it now
            # for rtype, values in res["result"].items():
            #     if rtype == "0" or rtype in qi.stats_keys:
            #         buffer[rtype] = values
            #         continue
            #     buffer[rtype] = buffer.get(rtype, []) + values
            # if res["action"] == "segments":
            #     req.update_dict("segment_sent_jobs", {res["seg_job_id"]: res["n"]})
            # if not req.futures:
            #     req.delete_if_done(qi)
        # buffer["0"] = {"result_sets": qi.result_sets, "meta_labels": qi.meta_labels}
        print(f"[{req.id}] Done with synchronous request")
        serializer = CustomEncoder()
        return web.json_response(serializer.default(buffer))
    else:
        job_info = {
            "status": "started",
            "job": req.hash,
        }
        return web.json_response(job_info)

from __future__ import annotations

import json
import os

from typing import final, Unpack, Any

from aiohttp import web
from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job

from .callbacks import (
    _config,
    _document,
    _general_failure,
    _upload_failure,
    _queries,
    _query,
    _schema,
    _sentences,
    _upload,
)
from .jobfuncs import _db_query, _upload_data, _create_schema
from .typed import JSONObject, QueryArgs
from .worker import SQLJob


@final
class QueryService:
    """
    This magic class will handle our queries by alerting you when they are done
    """

    # __slots__: list[str] = ["app", "timeout", "upload_timeout", "query_ttl"]

    def __init__(self, app: web.Application) -> None:
        self.app = app
        self.timeout = int(os.getenv("QUERY_TIMEOUT", 1000))
        self.upload_timeout = int(os.getenv("UPLOAD_TIMEOUT", 43200))
        self.query_ttl = int(os.getenv("QUERY_TTL", 5000))
        self.remembered_queries = int(os.getenv("MAX_REMEMBERED_QUERIES", 999))

    def query(
        self,
        query: str,
        queue: str = "query",
        **kwargs: Unpack[QueryArgs],  # type: ignore
    ) -> SQLJob | Job:
        """
        Here we send the query to RQ and therefore to redis
        """
        hashed = hash(query)
        queries = self.app["memory"]["queries"]
        exists = queries.get(hashed)
        if exists:
            try:
                job = Job.fetch(exists, connection=self.app["redis"])
                if job.get_status() == "finished":
                    print("Query found in redis memory. Retrieving...")
                    _query(job, self.app["redis"], job.result)
                    return job
            except NoSuchJobError:
                queries.pop(hashed)

        job = self.app[queue].enqueue(
            _db_query,
            on_success=_query,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query,),
            kwargs=kwargs,
        )
        if self.remembered_queries > 0 and len(queries) >= self.remembered_queries:
            first = list(queries)[0]
            queries.pop(first)
        if self.remembered_queries:
            queries[hashed] = job.id
        return job

    def document(
        self,
        schema: str,
        corpus: int,
        doc_id: int,
        user: str,
        room: str | None,
        queue: str = "query",
    ) -> SQLJob | Job:
        query = f"SELECT {schema}.doc_export(:doc_id);"
        params = {"doc_id": doc_id}
        kwargs = {"document": True, "corpus": corpus, "user": user, "room": room}
        job: Job | SQLJob = self.app[queue].enqueue(
            _db_query,
            on_success=_document,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query, params),
            kwargs=kwargs,
        )
        return job

    def sentences(
        self,
        query: str,
        queue: str = "query",
        **kwargs: int | bool | str | None,
    ) -> SQLJob | Job:
        hashed = hash(query)
        sents = self.app["memory"]["sentences"]
        exists = sents.get(hashed)
        if exists:
            try:
                sjob: Job | SQLJob = Job.fetch(exists, connection=self.app["redis"])
                if sjob.get_status() == "finished":
                    print("Sentences found in redis memory. Retrieving...")
                    kwa = {
                        "total_results_requested": kwargs["total_results_requested"],
                    }
                    _sentences(sjob, self.app["redis"], sjob.result, **kwa)
                    return sjob
            except NoSuchJobError:
                sents.pop(hashed)

        job: Job | SQLJob = self.app[queue].enqueue(
            _db_query,
            on_success=_sentences,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            depends_on=kwargs["depends_on"],
            done=kwargs["done"],
            job_timeout=self.timeout,
            args=(query,),
            kwargs=kwargs,
        )
        if self.remembered_queries > 0 and len(sents) >= self.remembered_queries:
            first = list(sents)[0]
            sents.pop(first)
        if self.remembered_queries:
            sents[hashed] = job.id
        return job

    def get_config(self) -> SQLJob | Job:
        """
        Get initial app configuration JSON
        """
        query = "SELECT * FROM main.corpus WHERE enabled = true;"
        opts = {"config": True}
        job: Job | SQLJob = self.app["alt"].enqueue(
            _db_query,
            on_success=_config,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query,),
            kwargs=opts,
        )
        return job

    def fetch_queries(
        self, user: str, room: str, queue: str = "alt", limit: int = 10
    ) -> SQLJob | Job:
        """
        Get previous saved queries for this user/room
        """
        params: dict[str, str] = {"user": user}
        room_info: str = ""
        if room:
            room_info = " AND room = :room"
            params["room"] = room

        query = f"""SELECT * FROM lcp_user.queries 
                    WHERE username = :user {room_info}
                    ORDER BY created_at DESC LIMIT {limit};
                """
        opts = {
            "user": user,
            "room": room,
            "config": True,
        }
        job: Job | SQLJob = self.app[queue].enqueue(
            _db_query,
            on_success=_queries,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query, params),
            kwargs=opts,
        )
        return job

    def store_query(
        self,
        query_data: JSONObject,
        idx: int,
        user: str,
        room: str,
        queue: str = "alt",
    ) -> SQLJob | Job:
        """
        Add a saved query to the db
        """
        query = f"INSERT INTO lcp_user.queries VALUES(:idx, :query, :user, :room);"
        kwargs = {
            "user": user,
            "room": room,
            "store": True,
            "config": True,
            "query_id": idx,
        }
        params: dict[str, str | int | None | JSONObject] = {
            "idx": idx,
            "query": query_data,
            "user": user,
            "room": room,
        }
        job: Job | SQLJob = self.app[queue].enqueue(
            _db_query,
            result_ttl=self.query_ttl,
            on_success=_queries,
            on_failure=_general_failure,
            job_timeout=self.timeout,
            args=(query, params),
            kwargs=kwargs,
        )
        return job

    def upload(
        self,
        user: str,
        project: str,
        room: str | None = None,
        queue: str = "alt",
        gui: bool = False,
        user_data: JSONObject | None = None,
        is_vian: bool = False,
    ) -> SQLJob | Job:
        """
        Upload a new corpus to the system
        """
        kwargs = {
            "gui": gui,
            "user_data": user_data,
            "is_vian": is_vian,
        }
        job: Job | SQLJob = self.app[queue].enqueue(
            _upload_data,
            on_success=_upload,
            on_failure=_upload_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.upload_timeout,
            args=(project, user, room),
            kwargs=kwargs,
        )
        return job

    def create(
        self,
        create: str,
        project: str,
        path: str,
        schema_name: str,
        user: str | None,
        room: str | None,
        project_name: str,
        queue: str = "alt",
        drops: list[str] | None = None,
        gui: bool = False,
    ) -> SQLJob | Job:
        kwargs = {
            "project": project,
            "user": user,
            "room": room,
            "path": path,
            "project_name": project_name,
            "gui": gui,
        }
        job: Job | SQLJob = self.app[queue].enqueue(
            _create_schema,
            # schema job remembered for one day?
            result_ttl=60 * 60 * 24,
            job_timeout=self.timeout,
            on_success=_schema,
            on_failure=_upload_failure,
            args=(create, schema_name, drops),
            kwargs=kwargs,
        )
        return job

    def cancel(self, job: SQLJob | Job | str) -> str:
        """
        Cancel a running job
        """
        if isinstance(job, str):
            job_id = job
            job = Job.fetch(job, connection=self.app["redis"])
        else:
            job_id = job.id
        job.cancel()
        send_stop_job_command(self.app["redis"], job_id)
        if job not in self.app["canceled"]:
            self.app["canceled"].append(job)
        return job.get_status()

    def cancel_running_jobs(
        self,
        user: str,
        room: str,
        specific_job: str | None = None,
        base: str | None = None,
    ) -> list[str]:
        if specific_job:
            rel_jobs = [str(specific_job)]
        else:
            rel_jobs = self.app["query"].started_job_registry.get_job_ids()
            rel_jobs += self.app["query"].scheduled_job_registry.get_job_ids()

        jobs = set(rel_jobs)
        ids = []

        for job in jobs:
            maybe = Job.fetch(job, connection=self.app["redis"])
            if base and maybe.kwargs.get("simultaneous") != base:
                continue
            if base and maybe.kwargs.get("is_sentences"):
                continue
            if job in self.app["canceled"]:
                continue
            if room and maybe.kwargs.get("room") != room:
                continue
            if user and maybe.kwargs.get("user") != user:
                continue
            try:
                self.cancel(maybe)
                ids.append(job)
            except InvalidJobOperation:
                print(f"Already canceled: {job}")
            except Exception as err:
                print("Unknown error, please debug", err, job)
        return ids

    def get(self, job_id: str) -> Job | SQLJob | None:
        try:
            job = Job.fetch(job_id, connection=self.app["redis"])
            return job
        except NoSuchJobError:
            return None

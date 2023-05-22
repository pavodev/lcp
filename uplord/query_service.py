from __future__ import annotations

import json
import os

from typing import Any, Dict, List, Tuple, final

from aiohttp import web
from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job

from .callbacks import (
    _config,
    _document,
    _general_failure,
    _queries,
    _query,
    _schema,
    _sentences,
    _upload,
)

from .jobfuncs import _db_query, _upload_data, _create_schema
from .worker import SQLJob


@final
class QueryService:
    """
    This magic class will handle our queries by alerting you when they are done
    """

    # __slots__: List[str] = ["app", "timeout", "upload_timeout", "query_ttl"]

    def __init__(self, app: web.Application) -> None:
        self.app = app
        self.timeout = int(os.getenv("QUERY_TIMEOUT", 1000))
        self.upload_timeout = int(os.getenv("UPLOAD_TIMEOUT", 43200))
        self.query_ttl = int(os.getenv("QUERY_TTL", 5000))

    def query(
        self,
        query: str,
        params: Tuple = tuple(),
        queue: str = "query",
        **kwargs,
    ) -> SQLJob | Job:
        """
        Here we send the query to RQ and therefore to redis
        """
        return self.app[queue].enqueue(
            _db_query,
            on_success=_query,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query, params),
            kwargs=kwargs,
        )

    def document(
        self,
        schema: str,
        corpus: int,
        doc_id: int,
        user: str,
        room: str | None,
        queue: str = "query",
    ) -> SQLJob | Job:
        query = f"SELECT {schema}.doc_export(%s);"
        params = (doc_id,)
        kwargs = {"document": True, "corpus": corpus, "user": user, "room": room}
        return self.app[queue].enqueue(
            _db_query,
            on_success=_document,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query, params),
            kwargs=kwargs,
        )

    def sentences(
        self,
        query: str,
        params: Tuple,
        queue: str = "query",
        **kwargs,
    ) -> SQLJob | Job:
        kwargs["is_sentences"] = True
        depends_on = kwargs.get("depends_on")
        return self.app[queue].enqueue(
            _db_query,
            on_success=_sentences,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            depends_on=depends_on,
            args=(query, params),
            kwargs=kwargs,
        )

    def get_config(self) -> SQLJob | Job:
        """
        Get initial app configuration JSON
        """
        query = "SELECT * FROM main.corpus;"
        opts = {"config": True}
        return self.app["alt"].enqueue(
            _db_query,
            on_success=_config,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=(query,),
            kwargs=opts,
        )

    def fetch_queries(
        self, user: str, room: str, queue: str = "alt", limit: int = 10
    ) -> SQLJob | Job:
        """
        Get previous saved queries for this user/room
        """
        params: Tuple[str, str] | Tuple[str] = (user,)
        room_info: str = ""
        if room:
            room_info = " AND room = %s"
            params = (user, room)

        query = f"""SELECT * FROM lcp_user.queries 
                    WHERE username = %s {room_info}
                    ORDER BY created_at DESC LIMIT {limit};
                """
        args = (query, params)
        opts = {
            "user": user,
            "room": room,
            "config": True,
        }
        return self.app[queue].enqueue(
            _db_query,
            on_success=_queries,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            args=args,
            kwargs=opts,
        )

    def store_query(
        self,
        query_data: Dict[str, Any],
        idx: int,
        user: str,
        room: str,
        queue: str = "alt",
    ) -> SQLJob | Job:
        """
        Add a saved query to the db
        """
        query = f"INSERT INTO lcp_user.queries VALUES(%s, %s, %s, %s);"
        kwargs = {
            "user": user,
            "room": room,
            "store": True,
            "config": True,
            "query_id": idx,
        }
        params = (idx, json.dumps(query_data), user, room)
        return self.app[queue].enqueue(
            _db_query,
            result_ttl=self.query_ttl,
            on_success=_queries,
            on_failure=_general_failure,
            job_timeout=self.timeout,
            args=(query, params),
            kwargs=kwargs,
        )

    def upload(
        self,
        user: str,
        project: str,
        room: str | None = None,
        queue: str = "alt",
        gui: bool = False,
    ) -> SQLJob | Job:
        """
        Upload a new corpus to the system
        """
        kwargs = {"gui": gui}
        return self.app[queue].enqueue(
            _upload_data,
            on_success=_upload,
            on_failure=_general_failure,
            result_ttl=self.query_ttl,
            job_timeout=self.upload_timeout,
            args=(project, user, room),
            kwargs=kwargs,
        )

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
        drops: List[str] | None = None,
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
        return self.app[queue].enqueue(
            _create_schema,
            result_ttl=self.query_ttl,
            job_timeout=self.timeout,
            on_success=_schema,
            on_failure=_general_failure,
            args=(create, schema_name, drops),
            kwargs=kwargs,
        )

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
    ) -> List[str]:
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
            if maybe.kwargs.get("room") != room:
                continue
            if maybe.kwargs.get("user") != user:
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

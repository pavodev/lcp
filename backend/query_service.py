import json
import os

from typing import Any, Dict, List, Optional, Union

from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job

from .callbacks import _config, _general_failure, _queries, _query, _stats, _upload

from .jobfuncs import _db_query, _upload_data


class QueryService:
    """
    This magic class will handle our queries by alerting you when they are done
    """

    def __init__(self, app, *args, **kwargs):
        self.app = app
        self.timeout = int(os.getenv("QUERY_TIMEOUT", 180))
        self.query_ttl = int(os.getenv("QUERY_TTL", 500))

    def query(
        self,
        queue: str = "query",
        depends_on=None,
        kwargs: Dict = None,
    ) -> Job:
        """
        Here we send the query to RQ and therefore to redis
        """
        opts = {
            "on_success": _query,
            "on_failure": _general_failure,
            "kwargs": kwargs,
        }
        if depends_on:
            opts["depends_on"] = depends_on
        return self.app[queue].enqueue(
            _db_query, result_ttl=self.query_ttl, job_timeout=self.timeout, **opts
        )

    def statistics(
        self,
        queue: str = "query",
        depends_on: Optional[str] = None,
        kwargs: Dict[str, Any] = {},
    ) -> Job:
        kwargs["is_stats"] = True
        kwargs["depends_on"] = depends_on
        opts = {
            "is_stats": True,
            "on_success": _stats,
            "on_failure": _general_failure,
            "kwargs": kwargs,
            "depends_on": depends_on,
            "current_batch": kwargs["current_batch"],
            "base": kwargs["base"],
            "resuming": kwargs["resuming"],
        }
        return self.app[queue].enqueue(
            _db_query, result_ttl=self.query_ttl, job_timeout=self.timeout, **opts
        )

    def get_config(self, queue: str = "alt", **kwargs) -> Job:
        """
        Get initial app configuration JSON
        """
        opts = {
            "query": "SELECT * FROM main.corpus;",
            "config": True,
            "on_success": _config,
        }
        return self.app[queue].enqueue(
            _db_query, result_ttl=self.query_ttl, job_timeout=self.timeout, **opts
        )

    def fetch_queries(
        self, user: str, room: Optional[str] = None, queue: str = "alt", limit: int = 10
    ) -> Job:
        """
        Get previous saved queries for this user/room
        """
        if room:
            room_info = " AND room = %s"
            params = (user, room)
        else:
            room_info = ""
            params2 = (user,)
        query = f"SELECT * FROM lcp_user.queries WHERE username = %s {room_info} ORDER BY created_at DESC LIMIT {limit};"
        opts = {
            "user": user,
            "room": room,
            "query": query,
            "config": True,
            "params": params if room else params2,
            "on_success": _queries,
            "on_failure": _general_failure,
        }
        return self.app[queue].enqueue(
            _db_query, result_ttl=self.query_ttl, job_timeout=self.timeout, **opts
        )

    def store_query(
        self,
        query_data: Dict,
        idx: int,
        user: str,
        room: Optional[str] = None,
        queue: str = "alt",
    ) -> Job:
        """
        Add a saved query to the db
        """
        db_query = f"INSERT INTO lcp_user.queries VALUES(%s, %s, %s, %s);"
        opts = {
            "user": user,
            "room": room,
            "query": db_query,
            "store": True,
            "config": True,
            "query_id": idx,
            "params": (idx, json.dumps(query_data), user, room),
            "on_success": _queries,
            "on_failure": _general_failure,
        }
        return self.app[queue].enqueue(
            _db_query, result_ttl=self.query_ttl, job_timeout=self.timeout, **opts
        )

    def upload(
        self,
        data,
        user: str,
        corpus_id: str,
        room=None,
        config=None,
        queue: str = "alt",
        gui=False,
    ) -> Job:
        """
        Upload a new corpus to the system
        """

        if config is not None:
            with open(config, "r") as fo:
                config = json.load(fo)

        opts = {
            "on_success": _upload,
            "on_failure": _general_failure,
            "path": data,
            "user": user,
            "corpus_id": str(corpus_id),
            "config": config,
            "gui": gui,
            "room": room,
        }
        return self.app[queue].enqueue(
            _upload_data, result_ttl=self.query_ttl, job_timeout=self.timeout, **opts
        )

    def cancel(self, job_id: str) -> str:
        job = Job.fetch(job_id, connection=self.app["redis"])
        job.cancel()
        return job.get_status()

    def delete(self, job_id: str) -> str:
        job = Job.fetch(job_id, connection=self.app["redis"])
        job.cancel()
        job.delete()
        return "DELETED"

    def cancel_running_jobs(
        self,
        user: str,
        room: Optional[str],
        specific_job: Optional[str] = None,
        base: Optional[str] = None,
    ) -> List[str]:
        if specific_job:
            rel_jobs = [str(specific_job)]
            finished = []
        else:
            rel_jobs = self.app["query"].started_job_registry.get_job_ids()
            rel_jobs += self.app["query"].scheduled_job_registry.get_job_ids()
            # the two lines below are probably overkill...
            finished = self.app["query"].finished_job_registry.get_job_ids()
            rel_jobs += finished
            set_fin = set(finished)

        jobs = set(rel_jobs)

        ids = []

        for job in jobs:
            maybe = Job.fetch(job, connection=self.app["redis"])
            if base and maybe.kwargs.get("simultaneous") != base:
                continue
            if base and maybe.kwargs.get("is_stats"):
                continue
            if maybe.kwargs.get("room") == room and maybe.kwargs.get("user") == user:
                try:
                    maybe.cancel()
                    send_stop_job_command(self.app["redis"], job)
                except InvalidJobOperation:
                    print(f"Already canceled: {job}")
                    continue
                except Exception as err:
                    print("Unknown error, please debug", err, job)
                    continue
                if job not in set_fin:
                    self.app["canceled"].add(job)
                    print(f"Killing job: {job}")
                    ids.append(job)
                else:
                    print(f"Stopped finished job anyway: {job}")
        return ids

    def get(self, job_id: str) -> Optional[Job]:
        try:
            job = Job.fetch(job_id, connection=self.app["redis"])
            return job
        except NoSuchJobError:
            return None

import json
import os

from rq.job import Job
from rq.exceptions import NoSuchJobError

from .callbacks import _query, _queries, _upload, _config, _general_failure

from .jobfuncs import _db_query, _upload_data


class QueryService:
    """
    This magic class will handle our queries by alerting you when they are done
    """

    def __init__(self, app, *args, **kwargs):
        self.app = app
        self.timeout = int(os.getenv("QUERY_TIMEOUT"))

    def submit(self, queue="query", kwargs=None):
        """
        Here we send the query to RQ and therefore to redis
        """
        opts = {
            "on_success": _query,
            "on_failure": _general_failure,
            "kwargs": kwargs,
        }
        return self.app[queue].enqueue(_db_query, job_timeout=self.timeout, **opts)

    def get_config(self, queue="query", **kwargs):
        opts = {
            "query": "SELECT * FROM main.corpus;",
            "config": True,
            "on_success": _config,
        }
        return self.app[queue].enqueue(_db_query, job_timeout=self.timeout, **opts)

    def fetch_queries(self, user, room=None, queue="query"):
        if room:
            room_info = " AND room = %s"
            params = (user, room)
        else:
            room_info = ""
            params = (user,)
        query = f"SELECT * FROM lcp_user.queries WHERE username = %s {room_info} ORDER BY created_at DESC;"
        opts = {
            "user": user,
            "room": room,
            "query": query,
            "config": True,
            "params": params,
            "on_success": _queries,
            "on_failure": _general_failure,
        }
        return self.app[queue].enqueue(_db_query, job_timeout=self.timeout, **opts)

    def store_query(self, query_data, idx, user, room=None, queue="query"):
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
        return self.app[queue].enqueue(_db_query, job_timeout=self.timeout, **opts)

    def upload(
        self, data, user, corpus_id, room=None, config=None, queue="query", gui=False
    ):

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
        return self.app[queue].enqueue(_upload_data, job_timeout=self.timeout, **opts)

    def cancel(self, job_id):
        job = Job.fetch(job_id, connection=self.app["redis"])
        job.cancel()
        return job.get_status()

    def delete(self, job_id):
        job = Job.fetch(job_id, connection=self.app["redis"])
        job.cancel()
        job.delete()
        return "DELETED"

    def cancel_running_jobs(self, user, room):
        jobs = self.app["started_registry"].get_job_ids()
        jobs += self.app["scheduled_registry"].get_job_ids()
        jobs = set(jobs)
        for job in jobs:
            maybe = Job.fetch(job, connection=self.app["redis"])
            if maybe.kwargs.get("room") == room and maybe.kwargs.get("user") == user:
                maybe.cancel()
                maybe.delete()

    def get(self, job_id):
        try:
            job = Job.fetch(job_id, connection=self.app["redis"])
            return job
        except NoSuchJobError:
            return

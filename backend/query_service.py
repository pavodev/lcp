import json
import os

from rq.job import Job
from rq.exceptions import NoSuchJobError
from rq import get_current_job
from rq.command import PUBSUB_CHANNEL_TEMPLATE

from .configure import _get_batches
from .utils import CustomEncoder


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


def _get_status(results_so_far, **kwargs):
    """
    Is a query finished, or do we need to do another iteration?
    """
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    requested = kwargs["total_results_requested"]
    if requested in {0, -1, False, None}:
        return "partial"
    if len(results_so_far) >= requested:
        return "satisfied"
    return "partial"


def _query_success(job, connection, result, *args, **kwargs):
    """
    Job callback, publishes a redis message containing the results
    """
    results_so_far = job.kwargs.get("existing_results", [])
    total_found = len(results_so_far) + len(result)
    total_requested = job.kwargs["total_results_requested"]
    current_batch = job.kwargs["current_batch"]
    done_part = job.kwargs["done_batches"]

    unlimited = job.kwargs["needed"] in {0, -1, False, None}

    limited = not unlimited and len(result) >= job.kwargs["needed"]

    for res in result:
        # fix: move sent_id to own column
        fixed = []
        sent_id = res[0][0]
        tok_ids = res[0][1:]
        fixed = ((sent_id,), tuple(tok_ids), res[1])
        # end fix
        results_so_far.append(fixed)
        if not unlimited and len(results_so_far) >= total_requested:
            break

    just_finished = job.kwargs["current_batch"]
    job.kwargs["done_batches"].append(just_finished)

    status = _get_status(results_so_far, **job.kwargs)
    if status == "finished":
        projected_results = len(results_so_far)
        perc = 100.0
    elif status in {"partial", "satisfied"}:
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([x[-1] for x in done_batches])
        proportion_that_matches = total_found / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
        perc = total_words_processed_so_far * 100.0 / job.kwargs["word_count"]
    jso = {
        "result": results_so_far,
        "status": status,
        "job": job.id,
        "projected_results": projected_results,
        "percentage_done": round(perc, 3),
        "hit_limit": False if not limited else job.kwargs["needed"],
        "batch_matches": len(result),
        **kwargs,
        **job.kwargs,
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _general_failure(job, connection, typ, value, traceback, *args, **kwargs):
    """
    On job failure, return some info ... probably hide some of this from prod eventually!
    """
    print("FAILURE", job, traceback)
    jso = {
        "status": "failed",
        "kind": str(typ),
        "value": str(value),
        "traceback": str(traceback),
        "job": job.id,
        **kwargs,
        **job.kwargs,
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


async def _upload_data(**kwargs):
    """
    Script to be run by rq worker, convert data and upload to postgres
    """
    from corpert import Corpert
    from .pg_upload import pg_upload

    corpus_data = Corpert(kwargs["path"]).run()

    await get_current_job()._pool.open()

    async with get_current_job()._pool.connection() as conn:
        # await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            await pg_upload(
                conn, cur, corpus_data, kwargs["corpus_id"], kwargs["config"]
            )

    return True


async def _db_query(query=None, **kwargs):
    """
    The function queued by RQ, which executes our DB query
    """
    single_result = kwargs.get("single", False)
    params = kwargs.get("params", tuple())
    is_config = kwargs.get("config", False)
    is_store = kwargs.get("store", False)

    # this open call should be made before any other db calls in the app just in case
    await get_current_job()._pool.open()

    async with get_current_job()._pool.connection() as conn:
        # await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            result = await cur.execute(query, params)
            if is_store:
                return
            if is_config:
                result = await cur.fetchall()
                return result
            if single_result:
                result = await cur.fetchone()
                result = result[0]
            else:
                result = await cur.fetchall()
            return result


def _upload_success(job, connection, result, *args, **kwargs):
    """
    Success callback when user has uploaded a dataset
    """

    jso = {
        "user": job.kwargs["user"],
        "status": "success" if result else "unknown",
        "corpus_id": job.kwargs["corpus_id"],
        "action": "uploaded",
        "gui": job.kwargs["gui"],
        "config": job.kwargs["config"],
        "room": job.kwargs["room"],
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _prev_queries_success(job, connection, result, *args, **kwargs):
    is_store = job.kwargs.get("store")
    action = "store_query" if is_store else "fetch_queries"
    room = str(job.kwargs["room"]) if job.kwargs["room"] else None
    jso = {
        "user": str(job.kwargs["user"]),
        "room": room,
        "status": "success",
        "action": action,
    }
    if is_store:
        jso["query_id"] = str(job.kwargs["query_id"])
    else:
        cols = ["idx", "query", "username", "room", "created_at"]
        jso["queries"] = [dict(zip(cols, x)) for x in result]
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _make_config(job, connection, result, *args, **kwargs):
    """
    Run by worker: make config data
    """
    fixed = {}
    for tup in result:
        (
            corpus_id,
            name,
            current_version,
            version_history,
            description,
            corpus_template,
            schema_path,
            token_counts,
            mapping,
        ) = tup
        rest = {
            "shortname": name,
            "corpus_id": int(corpus_id),
            "current_version": current_version,
            "version_history": version_history,
            "description": description,
            "schema_path": schema_path
            if schema_path.endswith("1")
            else f"{schema_path}1",
            "token_counts": token_counts,
            "mapping": mapping,
        }
        corpus_template.update(rest)

        fixed[int(corpus_id)] = corpus_template

    for name, conf in fixed.items():
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    fixed["_uploads"] = {}

    # fixed["open_subtitles_en1"] = fixed["open_subtitles_en"]
    # fixed["sparcling1"] = fixed["sparcling"]

    jso = {"config": fixed, "_is_config": True, "action": "set_config"}

    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


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
            "on_success": _query_success,
            "on_failure": _general_failure,
            "kwargs": kwargs,
        }
        return self.app[queue].enqueue(_db_query, job_timeout=self.timeout, **opts)

    def get_config(self, queue="query", **kwargs):
        opts = {
            "query": "SELECT * FROM main.corpus;",
            "config": True,
            "on_success": _make_config,
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
            "on_success": _prev_queries_success,
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
            "on_success": _prev_queries_success,
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
            "on_success": _upload_success,
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

    def cancel_running_jobs(self, jobs):
        for idx in set(jobs):
            self.delete(idx)

    def get(self, job_id):
        try:
            job = Job.fetch(job_id, connection=self.app["redis"])
            return job
        except NoSuchJobError:
            return

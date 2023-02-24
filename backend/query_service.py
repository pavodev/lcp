import json
import os

from rq.job import Job
from rq import get_current_job
from rq.command import PUBSUB_CHANNEL_TEMPLATE

from .configure import _get_batches


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


def _get_status(results_so_far, **kwargs):
    """
    Is a query finished, or do we need to do another iteration?
    """
    needed = kwargs.get("needed", 50)
    if len(results_so_far) >= needed:
        return "finished"
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    return "partial"


def _publish_success_to_redis(job, connection, result, *args, **kwargs):
    """
    Job callback, publishes a redis message containing the results
    """
    results_so_far = job.kwargs.get("existing_results", [])
    needed = job.kwargs.get("needed", 50)
    current_batch = job.kwargs["current_batch"]
    done_part = job.kwargs["done_batches"]

    # try:
    #    for res in result:
    #        sent = res[2]["sentence"]
    #        sent = " ".join(s[1] for s in sent)
    #        results_so_far.append((sent, *res))
    #        if len(results_so_far) >= needed:
    #            break
    # except:
    #    pass

    for res in result:
        results_so_far.append(res)
        if len(results_so_far) >= needed:
            break

    just_finished = job.kwargs["current_batch"]
    job.kwargs["done_batches"].append(just_finished)

    status = _get_status(results_so_far, **job.kwargs)
    if status == "finished":
        projected_results = len(results_so_far)
    elif status == "partial":
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([s for c, n, s in done_batches])
        proportion_that_matches = len(results_so_far) / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
    jso = {
        "result": results_so_far,
        "status": status,
        "job": job.id,
        "projected_results": projected_results,
        **kwargs,
        **job.kwargs,
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso))


def _publish_failure(job, connection, typ, value, traceback, *args, **kwargs):
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
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso))


async def _do_query(query=None, **kwargs):
    """
    The function queued by RQ, which executes our DB query
    """
    single_result = kwargs.get("single", False)
    params = kwargs.get("params", tuple())
    is_config = kwargs.get("config", False)

    # this open call should be made before any other db calls in the app just in case
    await get_current_job()._pool.open()

    async with get_current_job()._pool.connection() as conn:
        # await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            result = await cur.execute(query, params)
            if is_config:
                result = await cur.fetchall()
                return result
            if single_result:
                result = await cur.fetchone()
                result = result[0]
            else:
                result = await cur.fetchall()
            return result


def _make_config(job, connection, result, *args, **kwargs):
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
            "corpus_id": corpus_id,
            "current_version": current_version,
            "version_history": version_history,
            "description": description,
            "schema_path": schema_path,
            "token_counts": token_counts,
            "mapping": mapping,
        }
        corpus_template.update(rest)

        fixed[name] = corpus_template

    for name, conf in fixed.items():
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    fixed["open_subtitles_en1"] = fixed["open_subtitles_en"]
    fixed["sparcling1"] = fixed["sparcling"]

    jso = {"config": fixed, "_is_config": True}

    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso))


class QueryService:
    """
    This magic class will handle our queries by alerting you when they are done
    """

    def __init__(self, app, *args, **kwargs):
        self.app = app

    def submit(self, queue="query", kwargs=None):
        """
        Here we send the query to RQ and therefore to redis
        """
        opts = dict(
            on_success=_publish_success_to_redis,
            on_failure=_publish_failure,
            kwargs=kwargs,
        )
        timeout = int(os.getenv("QUERY_TIMEOUT"))
        return self.app[queue].enqueue(_do_query, job_timeout=timeout, **opts)

    def get_config(self, queue="query", **kwargs):
        opts = {
            "query": "SELECT * FROM main.corpus;",
            "config": True,
            "on_success": _make_config,
        }
        return self.app[queue].enqueue(_do_query, **opts)

    def cancel(self, job_id):
        job = Job.fetch(job_id, connection=self.app["redis"])
        job.cancel()
        return job.get_status()

    def delete(self, job_id):
        job = Job.fetch(job_id, connection=self.app["redis"])
        job.cancel()
        job.delete()
        return "DELETED"

    def get(self, job_id):
        job = Job.fetch(job_id, connection=self.app["redis"])
        return job

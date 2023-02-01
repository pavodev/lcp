import json

from rq.job import Job
from rq import get_current_job
from rq.command import PUBSUB_CHANNEL_TEMPLATE


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


def _get_status(results_so_far, **kwargs):
    """
    Is a query finished, or do we need to do another iteration?
    """
    needed = kwargs.get("needed", 50)
    if len(results_so_far) >= needed:
        return "finished"
    if len(kwargs["done_partitions"]) == len(kwargs["all_partitions"]):
        return "finished"
    return "partial"


def _publish_success_to_redis(job, connection, result, *args, **kwargs):
    """
    Job callback, publishes a redis message containing the results
    """
    results_so_far = job.kwargs.get("existing_results", [])
    needed = job.kwargs.get("needed", 50)
    current_partition = job.kwargs["current_partition"]
    done_part = job.kwargs["done_partitions"]

    try:
        for res in result:
            sent = res[2]["sentence"]
            sent = " ".join(s[1] for s in sent)
            results_so_far.append((sent, *res))
            if len(results_so_far) >= needed:
                break
    except:
        pass

    print(
        f"Successful query over partition: {len(result)} results, combined: {len(results_so_far)}, need {needed}, current partition: {current_partition} ... done partitions: {done_part},"
    )

    just_finished = job.kwargs["current_partition"]
    job.kwargs["done_partitions"].append(just_finished)

    status = _get_status(results_so_far, **job.kwargs)
    if status == "finished":
        projected_results = len(results_so_far)
    elif status == "partial":
        done_partitions = job.kwargs["done_partitions"]
        total_words_processed_so_far = sum([s for c, n, s in done_partitions])
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

    # this open call should be made before any other db calls in the app just in case
    await get_current_job()._pool.open()

    async with get_current_job()._pool.connection() as conn:
        # await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            result = await cur.execute(query, params)
            if single_result:
                result = await cur.fetchone()
                result = result[0]
            else:
                result = await cur.fetchmany(25)
            return result


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

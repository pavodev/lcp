from rq import get_current_job, get_current_connection
from rq.job import Job

from collections import Counter

from .utils import Interrupted


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


async def _as_dict(result):
    out = Counter()
    for i, (r, freq) in enumerate(result):
        r = r[0] if isinstance(r, tuple) and len(r) == 1 else r
        out[r] += freq
    return dict(out)


async def _db_query(query=None, **kwargs):
    """
    The function queued by RQ, which executes our DB query
    """
    single_result = kwargs.get("single", False)
    params = kwargs.get("params", tuple())
    is_config = kwargs.get("config", False)
    is_store = kwargs.get("store", False)
    is_stats = kwargs.get("is_stats", False)
    current_batch = kwargs.get("current_batch")

    if is_stats:
        associated_query = kwargs["depends_on"]
        conn = get_current_connection()
        associated_query = Job.fetch(associated_query, connection=conn)
        hit_limit = associated_query.meta.get("hit_limit")
        if associated_query.get_status(refresh=True) in ("stopped", "canceled"):
            raise Interrupted()
        if associated_query.result is None:
            raise Interrupted()
        if not associated_query.result:
            return {}
        prev_results = associated_query.result
        # so we don't double count on resuming
        if hit_limit:
            prev_results = prev_results[hit_limit:]
        values = [(i[0][1], i[0][-1]) for i in prev_results]
        together = set()
        for start, end in values:
            at = int(start)
            if at == int(end):
                together.add(at)
                continue
            while at <= int(end):
                together.add(at)
                at += 1
        form = ", ".join([str(x) for x in sorted(together)])
        query = query.format(
            schema=current_batch[1], table=current_batch[2], allowed=form
        )

    # this open call should be made before any other db calls in the app just in case
    await get_current_job()._pool.open()

    async with get_current_job()._pool.connection() as conn:
        # await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            result = await cur.execute(query, params)
            if is_store:
                return
            if is_config or is_stats:
                result = await cur.fetchall()
                if is_stats:
                    result = await _as_dict(result)
                return result
            if single_result:
                result = await cur.fetchone()
                result = result[0]
            else:
                result = await cur.fetchall()
            return result

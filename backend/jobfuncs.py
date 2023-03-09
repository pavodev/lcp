from rq import get_current_job


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

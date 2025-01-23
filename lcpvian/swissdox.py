from rq import Callback, Queue
from rq.job import Job
from redis import Redis as RedisConnection

from .callbacks import _swissdox_to_db_file, _general_failure
from .jobfuncs import _db_query

EXPORT_TTL = 5000


async def export_swissdox(
    conn: RedisConnection,
    article_ids: list[str],
    project_id: str,
    corpus_name: str,
    **kwargs,
) -> Job:
    """
    Schedule jobs to fetch all the prepared segments and named entities associated with the matched documents
    """
    q = Queue("background", connection=conn)
    query = f"""SELECT * FROM main.export_to_swissdoxviz('swissdox_1', :article_ids);"""
    return q.enqueue(
        _db_query,
        on_success=Callback(_swissdox_to_db_file, EXPORT_TTL),
        on_failure=Callback(_general_failure, EXPORT_TTL),
        result_ttl=EXPORT_TTL,
        job_timeout=EXPORT_TTL,
        args=(query, {"article_ids": article_ids}),
        kwargs={"project_id": project_id, "name": corpus_name, **kwargs},
    )

from aiohttp import web

from .utils import ensure_authorised


@ensure_authorised
async def document(request: web.Request) -> web.Response:
    """
    Start a job fetching a corpus document via the doc_export functionality.

    The job's callback will send the document to the user/room via websocket
    """
    doc_id = request.match_info["doc_id"]
    request_data = await request.json()
    room = request_data.get("room")
    user = request_data.get("user")
    corpora = request_data["corpora"]
    if not isinstance(corpora, (list, tuple, set)):
        corpora = [corpora]
    corpus = list(corpora)[0]
    schema = request.app["config"][int(corpus)]["schema_path"]
    sql_query = f"SELECT {schema}.doc_export(%s);"
    kwargs = dict(query=sql_query, user=user, room=room, single=True, params=(doc_id,))
    job = request.app["query_service"].submit(kwargs=kwargs)
    jobs = {"status": "started", "job": job.id}
    return web.json_response(jobs)

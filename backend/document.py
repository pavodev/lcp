from aiohttp import web

from . import utils


@utils.ensure_authorised
async def document(request):
    """
    Return a corpus document via the doc_export functionality
    """
    request_data = await request.json()
    corpora = request_data["corpora"]
    doc_id = request.match_info["doc_id"]
    room = request_data.get("room")
    user = request_data.get("user")
    qs = request.app["query_service"]
    sql_query = f"SELECT {corpora[0]}.doc_export(%s);"
    query_kwargs = dict(
        query=sql_query, user=user, room=room, single=True, params=(doc_id,)
    )
    job = qs.submit(kwargs=query_kwargs)
    jobs = {"status": "started", "job": job.id}
    return web.json_response(jobs)

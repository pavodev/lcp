import json
from uuid import uuid4

from aiohttp import web

from . import utils


@utils.ensure_authorised
async def fetch_queries(request: web.Request) -> web.Response:
    """
    User wants to retrieve their stored queries from the DB
    """
    request_data = await request.json()
    user = request_data["user"]
    room = request_data["room"]
    qs = request.app["query_service"]
    job = qs.fetch_queries(user, room=room)
    jobs = {"status": "started", "job": job.id}
    return web.json_response(jobs)


@utils.ensure_authorised
async def store_query(request: web.Request) -> web.Response:
    """
    User wants to store one or more queries in the DB
    """
    data = await request.json()
    user = data["user"]
    room = data["room"]
    query = data["query"]
    to_store = dict(
        corpora=data["corpora"],
        query=query,
        page_size=data["page_size"],
        languages=data["languages"],
        total_results_requested=data["total_results_requested"],
        query_name=data["query_name"],
    )
    qs = request.app["query_service"]
    idx = uuid4()
    job = qs.store_query(to_store, idx, user=user, room=room)
    jobs = {"status": "started", "job": job.id, "query_id": str(idx)}
    return web.json_response(jobs)

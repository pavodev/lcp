from uuid import uuid4

from typing import cast

from aiohttp import web
from rq.job import Job

from .typed import JSONObject
from .utils import ensure_authorised
from .worker import SQLJob


@ensure_authorised
async def fetch_queries(request: web.Request) -> web.Response:
    """
    User wants to retrieve their stored queries from the DB
    """
    request_data: JSONObject = await request.json()
    user = cast(str, request_data["user"])
    room = cast(str | None, request_data["room"])
    job: Job | SQLJob = request.app["query_service"].fetch_queries(user, room)
    jobs: dict[str, str] = {"status": "started", "job": job.id}
    return web.json_response(jobs)


@ensure_authorised
async def store_query(request: web.Request) -> web.Response:
    """
    User wants to store one or more queries in the DB
    """
    request_data: JSONObject = await request.json()
    user = cast(str, request_data["user"])
    room = cast(str | None, request_data["room"])
    query = cast(JSONObject, request_data["query"])
    to_store = dict(
        corpora=request_data["corpora"],
        query=query,
        page_size=request_data["page_size"],
        languages=request_data["languages"],
        total_results_requested=request_data["total_results_requested"],
        query_name=request_data["query_name"],
    )
    idx = uuid4()
    args = (to_store, idx, user, room)
    job: Job | SQLJob = request.app["query_service"].store_query(*args)
    jobs: dict[str, str] = {"status": "started", "job": job.id, "query_id": str(idx)}
    return web.json_response(jobs)

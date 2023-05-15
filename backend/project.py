from aiohttp import web

from .utils import (
    ensure_authorised,
    _lama_api_create,
    _lama_api_revoke,
    _lama_project_create,
)


@ensure_authorised
async def project_create(request: web.Request) -> web.Response:
    request_data = await request.json()
    project_data = {
        "title": request_data.get("title"),
        "unit": request_data.get("unit"),
        "startDate": request_data.get("startDate"),
        "finishDate": request_data.get("finishDate"),
        "url": request_data.get("url"),
        "description": request_data.get("description"),
    }
    res = await _lama_project_create(request.headers, project_data)
    return web.json_response(res)


@ensure_authorised
async def project_api_create(request: web.Request) -> web.Response:
    project_id = request.match_info["project"]
    res = await _lama_api_create(request.headers, project_id)
    return web.json_response(res)


@ensure_authorised
async def project_api_revoke(request: web.Request) -> web.Response:
    apikey_id = request.match_info["key"]
    project_id = request.match_info["project"]
    res = await _lama_api_revoke(request.headers, project_id, apikey_id)
    return web.json_response(res)

from aiohttp import web

from .utils import (
    ensure_authorised,
    _lama_api_create,
    _lama_api_revoke,
    _lama_project_create,
)


@ensure_authorised
async def project_create(request: web.Request) -> web.Response:
    request_data: dict[str, str] = await request.json()
    keys = ["title", "unit", "startDate", "finishDate", "url", "description"]
    project_data = {k: request_data[k] for k in keys}
    res = await _lama_project_create(request.headers, project_data)
    return web.json_response(res)


@ensure_authorised
async def project_api_create(request: web.Request) -> web.Response:
    project_id: str = request.match_info["project"]
    res = await _lama_api_create(request.headers, project_id)
    return web.json_response(res)


@ensure_authorised
async def project_api_revoke(request: web.Request) -> web.Response:
    apikey_id: str = request.match_info["key"]
    project_id: str = request.match_info["project"]
    res = await _lama_api_revoke(request.headers, project_id, apikey_id)
    return web.json_response(res)

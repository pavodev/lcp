"""
project.py: endpoints for project management
"""

from aiohttp import web

from .utils import (
    _lama_api_create,
    _lama_api_revoke,
    _lama_project_create,
    _lama_project_update,
    _lama_project_users,
    _lama_invitation_remove,
    _lama_invitation_add,
    _lama_project_user_update,
)


async def project_create(request: web.Request) -> web.Response:
    request_data: dict[str, str] = await request.json()
    keys = ["title", "startDate", "finishDate", "description", "additionalData"]
    project_data = {k: request_data[k] for k in keys}
    project_data["unit"] = "----"  # leave it for now, need to be changed in LAMa
    res = await _lama_project_create(request.headers, project_data)
    return web.json_response(res)


async def project_update(request: web.Request) -> web.Response:
    request_data: dict[str, str] = await request.json()
    keys = ["title", "startDate", "finishDate", "description", "additionalData"]
    project_data = {k: request_data[k] for k in keys}
    project_data["unit"] = "----"  # leave it for now, need to be changed in LAMa
    res = await _lama_project_update(request.headers, request_data["id"], project_data)
    return web.json_response(res)


async def project_user_update(request: web.Request) -> web.Response:
    request_data: dict[str, str] = await request.json()
    project_id: str = request.match_info["project"]
    user_id: str = request.match_info["user"]
    keys = ["projectId", "userId", "active", "admin"]
    user_data = {k: request_data[k] for k in keys if k in request_data}
    res = await _lama_project_user_update(
        request.headers, project_id, user_id, user_data
    )
    return web.json_response(res)


async def project_api_create(request: web.Request) -> web.Response:
    project_id: str = request.match_info["project"]
    res = await _lama_api_create(request.headers, project_id)
    return web.json_response(res)


async def project_api_revoke(request: web.Request) -> web.Response:
    apikey_id: str = request.match_info["key"]
    project_id: str = request.match_info["project"]
    res = await _lama_api_revoke(request.headers, project_id, apikey_id)
    return web.json_response(res)


async def project_users(request: web.Request) -> web.Response:
    project_id: str = request.match_info["project"]
    res = await _lama_project_users(request.headers, project_id)
    return web.json_response(res)


async def project_users_invite(request: web.Request) -> web.Response:
    request_data: dict[str, str] = await request.json()
    project_id: str = request.match_info["project"]
    res = await _lama_invitation_add(
        request.headers, project_id, {"emails": request_data["emails"]}
    )
    return web.json_response(res)


async def project_users_invitation_remove(request: web.Request) -> web.Response:
    # project_id: str = request.match_info["project"]
    invitation_id: str = request.match_info["invitation"]
    res = await _lama_invitation_remove(request.headers, invitation_id)
    return web.json_response(res)

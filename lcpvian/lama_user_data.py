from aiohttp import web

from .utils import _lama_user_details


async def lama_user_data(request: web.Request) -> web.Response:
    """
    Returns user data and app settings
    """
    res = await _lama_user_details(request.headers)
    res["debug"] = request.app["_debug"]
    return web.json_response(data=res)

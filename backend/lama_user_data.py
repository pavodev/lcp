from aiohttp import web

from . import utils


async def lama_user_data(request: web.Request) -> web.Response:
    """
    Returns user data and app settings
    """
    res = await utils._lama_user_details(request.headers)
    return web.json_response(data=res)

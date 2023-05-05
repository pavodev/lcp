import os

from aiohttp import web

from .utils import ensure_authorised


@ensure_authorised
async def video(request: web.Request) -> web.Response:
    corpora = [i.strip() for i in request.rel_url.query["corpora"].split(",")]
    out = {}
    for corpus in corpora:
        try:
            paths = request.app["corpora"][corpus]["videos"]
        except (AttributeError, KeyError):
            paths = [f"{corpus}.mp4"]
        out[corpus] = paths
    return web.json_response(out)

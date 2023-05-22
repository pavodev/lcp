from json.decoder import JSONDecodeError

from aiohttp import web

from .utils import _filter_corpora, _lama_user_details, ensure_authorised


@ensure_authorised
async def corpora(request: web.Request) -> web.Response:
    """
    Return config to frontend
    """
    try:
        request_data = await request.json()
    except JSONDecodeError:  # no data was sent ... eventually this should not happpen
        request_data = {}
    is_vian = request_data.get("appType", "lcp") == "vian"

    if not request_data.get("all", False):
        user_data = await _lama_user_details(request.headers)
        corpora = _filter_corpora(request.app["config"], is_vian, user_data)
    else:
        corpora = request.app["config"]
    return web.json_response({"config": corpora})

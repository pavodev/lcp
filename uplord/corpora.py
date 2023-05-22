from json.decoder import JSONDecodeError

from aiohttp import web

from .utils import _filter_corpora, _lama_user_details, ensure_authorised


@ensure_authorised
async def corpora(request: web.Request) -> web.Response:
    """
    Return config to frontend
    """
    user_data = await _lama_user_details(request.headers)
    try:
        request_data = await request.json()
    except JSONDecodeError:  # no data was sent ... eventually this should not happpen
        request_data = {}
    is_vian = request_data.get("appType", "lcp") == "vian"

    corpora = _filter_corpora(request.app["config"], is_vian, user_data)
    return web.json_response({"config": corpora})

"""
corpora.py: /corpora endpoint, returns a dict of corpora available for a given
user and app, and return it as a JSON HTTP response

We use the complete version of this dict as app["config"], so no DB requests
are needed for this request.
"""

import logging

from json.decoder import JSONDecodeError

from .utils import _filter_corpora, _lama_user_details, ensure_authorised
from aiohttp import web
from aiohttp.client_exceptions import ClientOSError


@ensure_authorised
async def corpora(request: web.Request) -> web.Response:
    """
    Return config to frontend (as HTTP response, not WS message!)
    """
    request_data: dict[str, str | bool] = {}
    try:
        request_data = await request.json()
    except JSONDecodeError:  # no data was sent ... eventually this should not happpen
        pass
    is_vian = request_data.get("appType", "lcp") == "vian"

    if not request_data.get("all", False):
        try:
            user_data = await _lama_user_details(request.headers)
        except ClientOSError as err:
            jso = {
                "details": str(err),
                "type": err.__class__.__name__,
                "status": "warning",
            }
            logging.warning(f"Failed to login: {err}", extra=jso)
            return web.json_response({"error": "no login possible", "status": 401})
        corpora = _filter_corpora(request.app["config"], is_vian, user_data)
    else:
        corpora = request.app["config"]
    return web.json_response({"config": corpora})

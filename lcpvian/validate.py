from __future__ import annotations

import json
import traceback

from typing import cast

from aiohttp import web

from .dqd_parser import convert
from .typed import JSONObject


async def validate(
    user: str | None = None,
    room: str | None = None,
    query: str = "",
    query_name: str | None = None,
    **kwargs: bool | None,
) -> web.Response | JSONObject:
    """
    Validate a JSON/DQD query. This is called either as a GET endpoint,
    or inside sock.py's WS handler. Thus, we need to return either JSON
    or an HTTP response
    """
    is_websocket: bool = cast(bool, kwargs.get("_ws", False))
    result: JSONObject = {}
    try:
        json.loads(query)
        result = {"kind": "json", "valid": True, "action": "validate", "status": 200}
    except json.JSONDecodeError:
        try:
            json_query = convert(query)
            result = {
                "kind": "dqd",
                "valid": True,
                "action": "validate",
                "json": json_query,
                "status": 200,
            }
        except Exception as err:
            tb = traceback.format_exc()
            print("Error during DQD->JSON:", err, tb)
            result = {
                "kind": "dqd?",
                "valid": False,
                "action": "validate",
                "error": str(err),
                "status": 400,
                "traceback": tb,
            }
    if is_websocket:
        return result
    return web.json_response(result)

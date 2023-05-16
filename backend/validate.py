from __future__ import annotations

import json

from typing import Any, Dict

from aiohttp import web

from .dqd_parser import convert


async def validate(
    user: str | None = None,
    room: str | None = None,
    query: str = "",
    query_name: str | None = None,
    **kwargs,
) -> web.Response | Dict[str, Any]:
    """
    Validate user query?
    """
    is_websocket: bool = kwargs.get("_ws", False)
    result: Dict[str, Any] = {}
    try:
        json.loads(query)
        result = {"kind": "json", "valid": True, "action": "validate", "status": 200}
    except json.JSONDecodeError as err:
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
            result = {
                "kind": "dqd?",
                "valid": False,
                "action": "validate",
                "error": str(err),
                "status": 400,
            }
    if is_websocket:
        return result
    return web.json_response(result)

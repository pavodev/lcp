import json

from typing import Any, Dict, Optional, Union

from aiohttp import web

from .dqd_parser import convert


async def validate(
    user: Optional[str] = None,
    room: Optional[str] = None,
    query: Union[str, bytes, bytearray] = "",
    query_name: Optional[str] = None,
    **kwargs: Dict[str, Any]
) -> Union[Dict[str, Any], web.Response]:
    """
    Validate user query?
    """
    is_websocket = kwargs.get("_ws")
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

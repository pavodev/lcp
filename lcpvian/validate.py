from __future__ import annotations

import json
import traceback

from .dqd_parser import convert
from .typed import JSONObject


async def validate(
    user: str | None = None,
    room: str | None = None,
    query: str = "",
    query_name: str | None = None,
    **kwargs: bool | None,
) -> JSONObject:
    """
    Validate a JSON/DQD query. This is not an endpoint, it is called by sock.py
    """
    result: JSONObject = {}
    try:
        json.loads(query)
        result = {"kind": "json", "valid": True, "action": "validate", "status": 200}
    except json.JSONDecodeError:
        try:
            conf: dict = kwargs.get("config", {}).get(kwargs.get("corpus"))
            json_query = convert(query, conf)
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
    return result

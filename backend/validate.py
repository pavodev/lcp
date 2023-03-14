import json

from typing import Optional


async def validate(
    user: Optional[str] = None,
    room: Optional[str] = None,
    query: Optional[str] = None,
    query_name: Optional[str] = None,
    **kwargs
):
    """
    Validate user query: still mostly todo
    """
    try:
        json.loads(query)
        return {"kind": "json", "valid": True, "action": "validate"}
    except json.JSONDecodeError as err:
        return {
            "kind": "unknown",
            "valid": None,
            "action": "validate",
            "error": str(err),
        }

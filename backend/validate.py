import json

from typing import Optional, Union


async def validate(
    user: Optional[str] = None,
    room: Optional[str] = None,
    query: Union[str, bytes, bytearray] = "",
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

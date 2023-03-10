import json


async def validate(user=None, room=None, query=None, query_name=None, **kwargs):
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

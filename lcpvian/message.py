"""
message.py: endpoint for accessing redis data directly

Non-trival websocket messages, like query results, are assigned a `msg_id` and
stored in Redis. These ids are also in the messages themselves, so the frontend
can keep a record of them.

Frontend can *forget* a WS message to save memory, but remember the msg_id in
case the data might be needed. If frontend GETs `/get_message/<id>`, we fetch
the associated data from Redis and send it back to the user/room via WS again.

When a message is accessed, its time-to-live (TTL) is renewed to the value of
`REDIS_WS_MESSAGE_TTL` in `.env`

This is not yet used by the frontend, but might come in handy soon!
"""

import json
import os

from typing import cast

from aiohttp import web

from .typed import JSONObject
from .utils import ensure_authorised, push_msg

MESSAGE_TTL = os.getenv("REDIS_WS_MESSSAGE_TTL", 5000)


@ensure_authorised
async def get_message(request: web.Request) -> web.Response:
    """
    Fetch arbitrary JSON data from redis
    """
    uu: str = request.match_info["uuid"]
    data: bytes | None
    response: JSONObject
    data = request.app["redis"].get(uu, None)
    if data is not None:
        request.app["redis"].expire(uu, MESSAGE_TTL)
    else:
        data = await request.app["aredis"].get(uu, None)
        if data is not None:
            await request.app["aredis"].expire(uu, MESSAGE_TTL)
    if data is None:
        response = {"action": "fetch", "msg_id": uu, "status": "failed"}
        return web.json_response(response)
    jso: JSONObject = json.loads(data)
    room = cast(str, jso.get("room", ""))
    user = cast(str, jso.get("user", ""))
    await push_msg(request.app["websockets"], room or "", jso, just=(room, user))
    response = {"action": "fetch", "user": user, "room": room, "msg_id": uu}
    return web.json_response(response)

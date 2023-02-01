import json

import aiohttp


async def send_json_to_user_socket(sockets, session_id, msg, skip=None, just=None):
    """
    Send JSON websocket message
    """
    sent_to = set()
    for room, users in sockets.items():
        if session_id and room != session_id:
            continue
        for conn, user_id in users:
            if (room, conn, user_id) in sent_to:
                continue
            if skip and (room, user_id) == skip:
                continue
            if just and (room, user_id) != just:
                continue
            await conn.send_json(msg)
            sent_to.add((room, conn, user_id))
            if session_id is None:
                return


async def sock(request):
    """
    Socket has to handle incoming messages, but also send a message when
    queries have finished processing
    """
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    query_service = request.app["query_service"]
    sockets = request.app["websockets"]

    async for msg in ws:

        if msg.type != aiohttp.WSMsgType.TEXT:
            continue

        payload = msg.json()
        action = payload["action"]
        session_id = payload.get("room")
        user_id = payload["user"]

        if action == "joined":
            originally = len(sockets[session_id])
            sockets[session_id].add((ws, user_id))
            currently = len(sockets[session_id])
            if session_id and originally != currently:
                response = {"joined": user_id, "room": session_id, "n_users": currently}
                await send_json_to_user_socket(
                    sockets, session_id, response, skip=(session_id, user_id)
                )

        elif action == "left":
            try:
                sockets[session_id].remove((ws, user_id))
            except KeyError:
                continue
            currently = len(sockets[session_id])
            if session_id and currently:
                response = {"left": user_id, "room": session_id, "n_users": currently}
                await send_json_to_user_socket(
                    sockets, session_id, response, skip=(session_id, user_id)
                )

        elif action == "populate":
            sockets[session_id].add((ws, user_id))
            response = {}
            await send_json_to_user_socket(
                sockets, session_id, response, skip=(session_id, user_id)
            )

        # query actions
        elif action == "delete_query":
            query_id = payload["query_id"]
            query_service.delete(query_id)
            response = {"id": query_id, "status": "deleted"}
            await send_json_to_user_socket(sockets, session_id, response)

        elif action == "cancel_query":
            query_id = payload["query_id"]
            query_service.cancel(query_id)
            response = {"id": query_id, "status": "cancelled"}
            await send_json_to_user_socket(sockets, session_id, response)

        elif action == "query_result":
            response = {
                "result": payload["result"],
                "user": user_id,
                "room": session_id,
            }
            await send_json_to_user_socket(sockets, session_id, response)

    # connection closed
    # await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')

    # if user_id is not None:
    #    request.app['websockets'].remove((ws, user_id))

    return ws

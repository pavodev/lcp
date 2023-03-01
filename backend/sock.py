import json

import aiohttp
import async_timeout
import asyncio

from .query import query


async def send_finished_query_to_websockets(channel, app):
    """
    If redis publishes a message, it gets picked up here and broadcast to the
    correct websockets...
    """
    while True:
        try:
            async with async_timeout.timeout(1):
                message = await channel.get_message(ignore_subscribe_messages=True)
                if message is None:
                    continue
                payload = json.loads(message["data"])
                if "_is_config" in payload:
                    print(f"Config loaded: {len(payload['config'])} corpora")
                    app["config"] = payload["config"]
                    continue
                user = payload.get("user")
                room = payload.get("room")
                status = payload.get("status", "unknown")
                job = payload.get("job")
                current_batch = payload["current_batch"]
                print(
                    f"Query iteration: {payload['batch_matches']} results found -- {len(payload['result'])}/{payload['total_results_requested']} total\n"
                    + f"Status: {status} -- done {len(payload['done_batches'])}/{len(payload['all_batches'])} batches ({payload['percentage_done']}% done)"
                )
                if status == "partial":
                    payload["config"] = app["config"]
                    await query(None, payload, app)
                    # return  # return will prevent partial results from going back to frontend
                to_send = payload
                n_users = len(app["websockets"].get(room, set()))
                if status in {"finished", "satisfied", "partial"}:
                    done = len(payload["done_batches"])
                    total = len(payload["all_batches"])
                    to_send = {
                        "result": payload["result"],
                        "job": job,
                        "action": "query_result",
                        "user": user,
                        "room": room,
                        "n_users": n_users,
                        # "original_query": payload["original_query"],
                        "status": status,
                        # "done_batches": payload["done_batches"],
                        # "current_batch": payload["current_batch"],
                        # "all_batches": payload["all_batches"],
                        "percentage_done": payload["percentage_done"],
                        "total_results_requested": payload["total_results_requested"],
                        "hit_limit": payload["hit_limit"],
                        "projected_results": payload["projected_results"],
                        "batches_done": f"{done}/{total}",
                    }
                await send_json_to_user_socket(
                    app["websockets"], room, to_send, skip=None, just=None
                )
                await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pass


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

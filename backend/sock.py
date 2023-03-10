import json

import aiohttp
import async_timeout
import asyncio
from rq.job import Job

from .query import query
from .validate import validate


async def handle_redis_response(channel, app):
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
                user = payload.get("user")
                room = payload.get("room")

                # error handling
                if payload.get("status") == "failed":
                    await push_msg(app["websockets"], room, payload, just=(room, user))
                    continue

                # interrupt was sent? -- currently not used
                if payload.get("status") == "interrupted":
                    payload["action"] = "interrupted"
                    await push_msg(app["websockets"], room, payload, just=(room, user))
                    continue

                # handle configuration message
                if payload.get("action") == "set_config":
                    print(f"Config loaded: {len(payload['config'])-1} corpora")
                    app["config"] = payload["config"]
                    continue

                # handle fetch/store queries message
                elif payload.get("action") in ("fetch_queries", "store_query"):
                    await push_msg(
                        app["websockets"],
                        room,
                        payload,
                        skip=None,
                        just=(room, user),
                    )
                    continue

                # handle uploaded data (add to config, ws message if gui mode)
                elif payload.get("action") == "uploaded":
                    conf = payload["config"]
                    corpus_id = payload["corpus_id"]
                    # todo: better structure for this i guess?
                    app["config"]["_uploads"][corpus_id] = conf
                    if payload.get("gui"):
                        await push_msg(
                            app["websockets"],
                            room,
                            payload,
                            skip=None,
                            just=(room, user),
                        )
                        continue

                elif payload.get("action") == "stats":

                    await push_msg(
                        app["websockets"],
                        room,
                        payload,
                        skip=None,
                        just=(room, user),
                    )
                    continue

                # handle query progress
                else:
                    await _handle_query(app, payload, user, room)

                await asyncio.sleep(0.1)
        except asyncio.TimeoutError as err:
            print(f"Timeout: {err}")
        except Exception as err:
            to_send = {"error": str(err), "status": "failed"}
            print("Error", err)
            await push_msg(
                app["websockets"],
                room,
                to_send,
                skip=None,
                just=(room, user),
            )


async def _handle_query(app, payload, user, room):
    """
    Our subscribe listener has picked up a message, and it's about
    a query iteration. Create a websocket message to send to correct frontends
    """
    status = payload.get("status", "unknown")
    job = payload.get("job")
    the_job = Job.fetch(job, connection=app["redis"])
    job_status = the_job.get_status(refresh=True)
    if job_status in ("stopped", "canceled") or job in app["canceled"]:
        print(f"Query was stopped: {job} -- preventing update")
        return
    current_batch = payload["current_batch"]
    total = payload.get("total_results_requested")
    if not total or total == -1:
        total = "all"
    print(
        f"Query iteration: {job} -- {payload['batch_matches']} results found -- {len(payload['result'])}/{total} total\n"
        + f"Status: {status} -- done {len(payload['done_batches'])}/{len(payload['all_batches'])} batches ({payload['percentage_done']}% done)"
    )
    if (
        status == "partial"
        and not job_status in ("stopped", "canceled")
        and job not in app["canceled"]
    ):
        payload["config"] = app["config"]
        if payload["base"] is None:
            payload["base"] = job
        await query(None, payload, app)
        # return  # return will prevent partial results from going back to frontend
    to_send = payload
    n_users = len(app["websockets"].get(room, set()))
    if status in {"finished", "satisfied", "partial"}:
        done = len(payload["done_batches"])
        total_batches = len(payload["all_batches"])
        to_send = {
            "result": payload["result"],
            "job": job,
            "action": "query_result",
            "user": user,
            "room": room,
            "n_users": n_users,
            "status": status,
            "base": payload["base"],
            # "job_status": job_status,
            "percentage_done": payload["percentage_done"],
            "total_results_requested": payload["total_results_requested"],
            "hit_limit": payload["hit_limit"],
            "projected_results": payload["projected_results"],
            "batches_done": f"{done}/{total_batches}",
        }
    await push_msg(app["websockets"], room, to_send, skip=None, just=(room, user))


async def push_msg(sockets, session_id, msg, skip=None, just=None):
    """
    Send JSON websocket message
    """
    sent_to = set()
    for room, users in sockets.items():
        if session_id and room != session_id:
            continue
        if not session_id and room:
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
            # todo: can we add back this tiny optimisation?
            # if session_id is None:
            #     return


async def sock(request):
    """
    Socket has to handle incoming messages, but also send a message when
    queries have finished processing
    """
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    qs = request.app["query_service"]
    sockets = request.app["websockets"]

    async for msg in ws:

        if msg.type != aiohttp.WSMsgType.TEXT:
            continue

        payload = msg.json()
        action = payload["action"]
        session_id = payload.get("room")
        user_id = payload["user"]
        ident = (session_id, user_id)

        if action == "joined":
            originally = len(sockets[session_id])
            sockets[session_id].add((ws, user_id))
            currently = len(sockets[session_id])
            if session_id and originally != currently:
                response = {"joined": user_id, "room": session_id, "n_users": currently}
                await push_msg(sockets, session_id, response, skip=ident)

        elif action == "left":
            try:
                sockets[session_id].remove((ws, user_id))
            except KeyError:
                continue
            currently = len(sockets[session_id])
            if not currently:
                qs.cancel_running_jobs(user_id, session_id)
                if session_id:
                    sockets.pop(session_id)
            elif session_id:
                response = {"left": user_id, "room": session_id, "n_users": currently}
                await push_msg(sockets, session_id, response, skip=ident)

        elif action == "stop":
            jobs = qs.cancel_running_jobs(user_id, session_id)
            response = {
                "status": "stopped",
                "n": len(jobs),
                "action": "stopped",
                "jobs": jobs,
            }
            await push_msg(sockets, session_id, response, just=ident)

        elif action == "validate":
            response = await validate(**payload)
            await push_msg(sockets, session_id, response, just=ident)

        elif action == "populate":
            sockets[session_id].add((ws, user_id))
            response = {}
            await push_msg(sockets, session_id, response, skip=ident)

        elif action == "delete_query":
            query_id = payload["query_id"]
            qs.delete(query_id)
            response = {"id": query_id, "status": "deleted"}
            await push_msg(sockets, session_id, response)

        elif action == "cancel_query":
            query_id = payload["query_id"]
            qs.cancel(query_id)
            response = {"id": query_id, "status": "cancelled"}
            await push_msg(sockets, session_id, response)

        elif action == "query_result":
            response = {
                "result": payload["result"],
                "user": user_id,
                "room": session_id,
            }
            await push_msg(sockets, session_id, response)

    # connection closed
    await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message="Server shutdown")

    return ws

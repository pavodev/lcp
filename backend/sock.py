import json

from time import sleep

import aiohttp
import aioredis
import async_timeout
import asyncio

from rq.job import Job
from typing import Any, Dict, List, Optional, Tuple, Union

from .query import query
from .validate import validate


async def handle_redis_response(
    channel: aioredis.client.PubSub, app: aiohttp.web.Application, test: bool = False
) -> None:
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

                if payload.get("status") == "timeout":
                    await push_msg(app["websockets"], room, payload, just=(room, user))
                    continue

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
                    if payload["disabled"]:
                        for name, idx in payload["disabled"]:
                            print(f"Corpus disabled: {name}={idx}")
                    print(f"Config loaded: {len(payload['config'])-1} corpora")
                    app["config"] = payload["config"]
                    if test:
                        return
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
                    # conf = payload["config"]
                    # project = payload["project"]
                    # todo: better structure for this i guess?
                    # app["config"][-1][project] = conf
                    if payload.get("gui"):
                        await push_msg(
                            app["websockets"],
                            room,
                            payload,
                            skip=None,
                            just=(room, user),
                        )
                        continue

                elif payload.get("action") == "sentences":

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


async def _handle_query(
    app: aiohttp.web.Application,
    payload: Dict[str, Any],
    user: str,
    room: Optional[str],
) -> None:
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
    so_far = payload.get("total_results_so_far", -1)
    print(
        f"Query iteration: {job} -- {payload['batch_matches']} results found -- {so_far}/{total} total\n"
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
        if not payload.get("simultaneous"):
            await query(None, manual=payload, app=app)
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
            "batch_matches": payload["batch_matches"],
            "total_results_so_far": payload["total_results_so_far"],
            "percentage_done": payload["percentage_done"],
            "percentage_words_done": payload["percentage_words_done"],
            "total_results_requested": payload["total_results_requested"],
            "hit_limit": payload["hit_limit"],
            "projected_results": payload["projected_results"],
            "batches_done": f"{done}/{total_batches}",
            "simultaneous": payload.get("simultaneous", False),
        }
    await push_msg(app["websockets"], room, to_send, skip=None, just=(room, user))


async def push_msg(
    sockets: Dict[Optional[str], Tuple[Any, str]],
    session_id: Optional[str],
    msg: Union[Dict, List],
    skip: Optional[Tuple[Optional[str], str]] = None,
    just: Optional[Tuple[Optional[str], str]] = None,
) -> None:
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
            try:
                await conn.send_json(msg)
            except ConnectionResetError:
                print(f"Connection reset: {room}/{user_id}")
                pass
            sent_to.add((room, conn, user_id))
            # todo: can we add back this tiny optimisation?
            # if session_id is None:
            #     return


async def sock(request: aiohttp.web.Request) -> aiohttp.web.WebSocketResponse:
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
            sleep(2)
            jobs += qs.cancel_running_jobs(user_id, session_id)
            jobs = list(set(jobs))
            response = {
                "status": "stopped",
                "n": len(jobs),
                "action": "stopped",
                "jobs": jobs,
            }
            await push_msg(sockets, session_id, response, just=ident)

        elif action == "validate":
            payload["_ws"] = True
            response = await validate(**payload)
            await push_msg(sockets, session_id, response, just=ident)

        elif action == "enough_results":
            job = payload["job"]
            jobs = qs.cancel_running_jobs(user_id, session_id, base=job)
            response = {
                "status": "stopped",
                "n": len(jobs),
                "action": "stopped",
                "jobs": jobs,
            }
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
    await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message=b"Server shutdown")

    return ws

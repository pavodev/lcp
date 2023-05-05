import asyncio
import json
import traceback

from time import sleep
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import async_timeout

from aiohttp import WSCloseCode, WSMsgType, web
from aiohttp.http_websocket import WSMessage
from redis import asyncio as aioredis
from rq.job import Job

from .query import query
from .validate import validate


async def handle_redis_response(channel, app, test=False):
    """
    If redis publishes a message, it gets picked up here and broadcast to the
    correct websockets...

    This function cannot yet be handled by mypy, so leave it unannotated please
    """
    while True:
        try:
            room = None
            user = None
            async with async_timeout.timeout(2):
                message = await channel.get_message(ignore_subscribe_messages=True)
                if isinstance(message, dict) and message.get("data"):
                    payload = json.loads(message["data"])
                    user = payload.get("user")
                    room = payload.get("room")
                    status = payload.get("status")
                    action = payload.get("action")

                    if status == "timeout":
                        await push_msg(
                            app["websockets"], room, payload, just=(room, user)
                        )

                    elif status == "failed":
                        await push_msg(
                            app["websockets"], room, payload, just=(room, user)
                        )

                    # interrupt was sent? -- currently not used
                    elif status == "interrupted":
                        payload["action"] = "interrupted"
                        await push_msg(
                            app["websockets"], room, payload, just=(room, user)
                        )

                    # handle configuration message
                    elif action == "set_config":
                        if payload.get("disabled"):
                            for name, idx in payload["disabled"]:
                                print(f"Corpus disabled: {name}={idx}")
                        print(f"Config loaded: {len(payload['config'])-1} corpora")
                        app["config"] = payload["config"]
                        # payload["action"] = "update_config"
                        # await push_msg(app["websockets"], None, payload)
                        # if test:
                        #    return

                    # handle fetch/store queries message
                    elif action in ("fetch_queries", "store_query"):
                        await push_msg(
                            app["websockets"],
                            room,
                            payload,
                            skip=None,
                            just=(room, user),
                        )

                    # handle uploaded data (add to config, ws message if gui mode)
                    elif action == "uploaded":
                        app["query_service"].get_config()
                        # if payload.get("gui"):
                        #    await push_msg(
                        #        app["websockets"],
                        #        room,
                        #        payload,
                        #        skip=None,
                        #        just=None
                        #    )

                    elif action == "sentences":
                        await push_msg(
                            app["websockets"],
                            room,
                            payload,
                            skip=None,
                            just=(room, user),
                        )

                    # handle query progress
                    else:
                        await _handle_query(app, payload, user, room)

                    await asyncio.sleep(0.1)
        except (asyncio.TimeoutError, asyncio.CancelledError) as err:
            print(f"Warning: timeout in websocket listener:\n{message}")
        except Exception as err:
            to_send = {"error": str(err), "status": "failed"}
            print(f"Error: {str(err)}\n{traceback.format_exc()}")
            if user or room:
                await push_msg(
                    app["websockets"],
                    None,
                    to_send,
                    skip=None,
                    just=(room, user),
                )


async def _handle_query(
    app: web.Application,
    payload: Dict[str, Any],
    user: Optional[str],
    room: Optional[str],
) -> None:
    """
    Our subscribe listener has picked up a message, and it's about
    a query iteration. Create a websocket message to send to correct frontends
    """
    status = payload.get("status", "unknown")
    job = payload["job"]
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
        if "done_batches" in payload:
            payload["done_batches"] = [tuple(x) for x in payload["done_batches"]]
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
    sockets: Dict[Optional[str], Set[Tuple[Any, str]]],
    session_id: Optional[str],
    msg: Dict[str, Any],
    skip: Optional[Tuple[Optional[str], Optional[str]]] = None,
    just: Optional[Tuple[Optional[str], Optional[str]]] = None,
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


async def sock(request: web.Request) -> web.WebSocketResponse:
    """
    Socket has to handle incoming messages, but also send a message when
    queries have finished processing
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    qs = request.app["query_service"]
    sockets = request.app["websockets"]

    x: Optional[WSMessage] = None
    # async for x in ws:
    while True:
        x = await ws.receive()
        if x.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            raise StopAsyncIteration

        if x.type != WSMsgType.TEXT:
            continue

        payload = x.json()
        action = payload["action"]
        session_id = payload.get("room")
        user_id = payload["user"]
        ident: Tuple[Optional[str], Optional[str]] = (session_id, user_id)

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
            jobs = list(set(jobs))
            if jobs:
                response = {
                    "status": "stopped",
                    "n": len(jobs),
                    "action": "stopped",
                    "jobs": jobs,
                }
                await push_msg(sockets, session_id, response, just=ident)

        elif action == "validate":
            payload["_ws"] = True
            resp = await validate(**payload)
            if isinstance(resp, web.Response):
                continue
            await push_msg(sockets, session_id, resp, just=ident)

        elif action == "enough_results":
            job = payload["job"]
            jobs = qs.cancel_running_jobs(user_id, session_id, base=job)
            jobs = list(set(jobs))
            response = {
                "status": "stopped",
                "n": len(jobs),
                "action": "stopped",
                "jobs": jobs,
            }
            if jobs:
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
    # await ws.close(code=WSCloseCode.GOING_AWAY, message=b"Server shutdown")

    return ws

from __future__ import annotations

import asyncio
import json
import logging
import traceback

from typing import Any, Dict, List, Set, Tuple

from aiohttp import WSCloseCode, WSMsgType, web
from aiohttp.http_websocket import WSMessage
from rq.job import Job

from redis.asyncio.client import PubSub

from . import utils
from .query import query
from .validate import validate


async def handle_redis_response(
    channel: PubSub, app: web.Application, test: bool = False
) -> None:
    """
    If redis publishes a message, it gets picked up here in an async loop
    and broadcast to the correct websockets.

    We need to know if we're running c-compiled code or not, because
    channel.get_message() fails when compiled to c for some reason
    """
    message: Dict | Any = None
    payload: Dict | None = None

    try:
        if app.get("mypy"):
            async for message in channel.listen():
                await _process_message(message, channel, app)
        else:
            while True:
                message = await channel.get_message(
                    ignore_subscribe_messages=True, timeout=2.0
                )
                await _process_message(message, channel, app)

            if test is True:
                return None

    except (asyncio.TimeoutError, asyncio.CancelledError) as err:
        print(f"Warning: timeout in websocket listener ({err})")
    except Exception as err:
        formed = traceback.format_exc()
        print(f"Error: {str(err)}\n{formed}")
        to_send = {"error": str(err), "status": "failed"}
        if isinstance(payload, dict):
            user = payload.get("user", "")
            room = payload.get("room", "")
            if user:
                to_send["user"] = user
            if room:
                to_send["room"] = room
            if user and room:
                await push_msg(
                    app["websockets"],
                    room,
                    to_send,
                    skip=None,
                    just=(room, user),
                )
        extra = {"traceback": formed, **to_send}
        logging.error(str(err), extra=extra)


async def _process_message(message: Any, channel: PubSub, app: web.Application) -> None:
    await asyncio.sleep(0.1)
    if not message or not isinstance(message, dict):
        return
    if message.get("type", "") == "subscribe":
        return
    if not message.get("data"):
        return
    payload = json.loads(message["data"])
    if not payload or not isinstance(payload, dict):
        return
    await _handle_message(payload, channel, app)
    return None


async def _handle_message(
    payload: Dict[str, Any], channel: PubSub, app: web.Application
) -> None:
    """
    Build a message, do any extra needed actions and send on to the right websocket(s)
    """
    user = payload.get("user", "")
    room = payload.get("room", "")
    status = payload.get("status", "")
    action = payload.get("action", "")

    if status == "timeout":
        await push_msg(app["websockets"], room, payload, just=(room, user))
        return None

    if status == "failed":
        await push_msg(app["websockets"], room, payload, just=(room, user))
        return None

    # interrupt was sent? -- currently not used
    if status == "interrupted":
        payload["action"] = "interrupted"
        await push_msg(app["websockets"], room, payload, just=(room, user))
        return None

    # handle configuration message
    if action == "set_config":
        if payload.get("disabled"):
            for name, idx in payload["disabled"]:
                print(f"Corpus disabled: {name}={idx}")
        print(f"Config loaded: {len(payload['config'])-1} corpora")
        app["config"] = payload["config"]
        # payload["action"] = "update_config"
        # await push_msg(app["websockets"], None, payload)
        return None

    # handle fetch/store queries message
    if action in ("fetch_queries", "store_query"):
        await push_msg(
            app["websockets"],
            room,
            payload,
            skip=None,
            just=(room, user),
        )
        return None

    # handle uploaded data (add to config, ws message if gui mode)
    if action == "uploaded":
        app["query_service"].get_config()
        return None
        # if payload.get("gui"):
        #    await push_msg(
        #        app["websockets"],
        #        room,
        #        payload,
        #        skip=None,
        #        just=None
        #    )

    if action == "sentences":
        await push_msg(
            app["websockets"],
            room,
            payload,
            skip=None,
            just=(room, user),
        )
        return None

    if action == "query_result":
        await _handle_query(app, payload, user, room)
        return None


async def _handle_query(
    app: web.Application,
    payload: Dict[str, Any],
    user: str,
    room: str,
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
        if job not in app["canceled"]:
            app["canceled"].append(job)
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
            dones = [tuple(x) for x in payload["done_batches"]]
            current = tuple(payload["current_batch"])
            if current not in dones:
                dones.append(current)
            payload["done_batches"] = dones
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
            "is_vian": payload.get("is_vian", False),
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
    sockets: Dict[str, Set[Tuple[Any, str]]],
    session_id: str,
    msg: Dict[str, Any],
    skip: Tuple[str, str] | None = None,
    just: Tuple[str, str] | None = None,
) -> None:
    """
    Send JSON websocket message to one or more users
    """
    sent_to = set()
    for room, users in sockets.items():
        if room != session_id:
            continue
        for conn, user_id in users:
            if (room, user_id) in sent_to:
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
            sent_to.add((room, user_id))


async def sock(request: web.Request) -> web.WebSocketResponse:
    """
    Socket has to handle incoming messages, but also send a message when
    queries have finished processing
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    qs = request.app["query_service"]
    sockets = request.app["websockets"]

    msg: WSMessage | None = None
    # async for msg in ws:
    while True:
        msg = await ws.receive()
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            return ws
        if msg.type != WSMsgType.TEXT:
            continue

        payload = msg.json()
        action = payload["action"]
        session_id = payload["room"]
        user_id = payload["user"]
        ident: Tuple[str, str] = (session_id, user_id)

        if action == "joined":
            originally = len(sockets[session_id])
            sockets[session_id].add((ws, user_id))
            currently = len(sockets[session_id])
            if session_id and originally != currently:
                response = {"joined": user_id, "room": session_id, "n_users": currently}
                await push_msg(sockets, session_id, response, skip=ident)

        elif action == "left":
            await ws.close(code=WSCloseCode.GOING_AWAY, message=b"User left")
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

    # connection closed
    # await ws.close(code=WSCloseCode.GOING_AWAY, message=b"Server shutdown")

    return ws


async def ws_cleanup(sockets: Dict[str, Set[Tuple[web.WebSocketResponse, str]]]):
    """
    Periodically remove any closed websocket connections to ensure that app size
    doesn't irreversibly increase over time

    Send a message to other users about it, too
    """
    interval = 3600
    while True:
        for room, conns in sockets.items():
            to_close = set()
            for ws, uid in conns:
                if ws.closed:
                    to_close.add((ws, uid))
            for conn in to_close:
                print(f"Removing stale WS connection: {room}/{uid}")
                conns.remove(conn)
            n_users = len(conns)
            if not n_users or not to_close:
                continue
            for _, user_id in to_close:
                response = {"left": user_id, "room": room, "n_users": n_users}
                await push_msg(sockets, room, response)
        await asyncio.sleep(interval)

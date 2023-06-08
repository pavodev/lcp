from __future__ import annotations

import asyncio
import json
import logging
import traceback

from typing import Sized, cast

try:
    from aiohttp import WSCloseCode, WSMsgType, web
except ImportError:
    from aiohttp import web
    from aiohttp.http import WSCloseCode, WSMsgType

from aiohttp.http_websocket import WSMessage
from rq.job import Job

from redis.asyncio.client import PubSub

from .query import query
from .query_service import QueryService
from .utils import push_msg
from .validate import validate

from .typed import JSONObject, RedisMessage, Websockets
from .utils import PUBSUB_CHANNEL, _filter_corpora


async def _process_message(
    message: RedisMessage, channel: PubSub, app: web.Application
) -> None:
    await asyncio.sleep(0.1)
    if not message or not isinstance(message, dict):
        return
    if message.get("type", "") == "subscribe":
        return
    if not message.get("data"):
        return
    payload = json.loads(cast(bytes, message["data"]))
    if not payload or not isinstance(payload, dict):
        return
    await _handle_message(payload, channel, app)
    return None


async def handle_redis_response(
    channel: PubSub, app: web.Application, test: bool = False
) -> None:
    """
    If redis publishes a message, it gets picked up here in an async loop
    and broadcast to the correct websockets.

    We need to know if we're running c-compiled code or not, because
    channel.get_message() fails when compiled to c for some reason
    """
    message: RedisMessage = None

    try:
        if app.get("mypy", False) is True:
            async for message in channel.listen():
                await _process_message(message, channel, app)
                if message and test is True:
                    return None
        else:
            while True:
                message = await channel.get_message(
                    ignore_subscribe_messages=True, timeout=2.0
                )
                await _process_message(message, channel, app)
                if message and test is True:
                    return None

    except asyncio.TimeoutError as err:
        print(f"Warning: timeout in websocket listener ({err})")
    except asyncio.CancelledError as err:
        tb = traceback.format_exc()
        print(f"Canceled redis handler: {err}\n\n{tb}")
    except Exception as err:
        formed = traceback.format_exc()
        print(f"Error: {str(err)}\n{formed}")
        extra = {"error": str(err), "status": "failed", "traceback": formed}
        logging.error(str(err), extra=extra)


async def listen_to_redis(app: web.Application) -> None:
    """
    Using our async redis connection instance, listen for events coming from redis
    and delegate to the sender
    """
    async with app["aredis"].pubsub() as channel:
        await channel.subscribe(PUBSUB_CHANNEL)
        try:
            await handle_redis_response(channel, app, test=False)
        except KeyboardInterrupt:
            pass
        except Exception as err:
            raise err
        await channel.unsubscribe(PUBSUB_CHANNEL)
        try:
            await app["aredis"].quit()
        except Exception:
            pass
        try:
            app["redis"].quit()
        except Exception:
            pass


async def _handle_error(
    app: web.Application, user: str, room: str, payload: JSONObject
) -> None:
    """
    Sanitise errors send to FE if not in debug mode
    """
    payload["debug"] = app["_debug"]
    bad_keys = {"traceback", "original_query", "sentences_query", "sql"}
    if not app["_debug"]:
        for key in bad_keys:
            payload.pop(key, None)
    await push_msg(app["websockets"], room, payload, skip=None, just=(room, user))
    return None


async def _handle_message(
    payload: JSONObject, channel: PubSub, app: web.Application
) -> None:
    """
    Build a message, do any extra needed actions and send on to the right websocket(s)
    """
    user = cast(str, payload.get("user", ""))
    room = cast(str, payload.get("room", ""))
    action = payload.get("action", "")
    simples = (
        "fetch_queries",
        "store_query",
        "document",
        "document_ids",
        "sentences",
    )
    errors = (
        "failed",
        "upload_fail",
        "unregistered",
        "timeout",
        "interrupted",  # not currently used, maybe when rooms have multiple users
    )
    if action == "document_ids":
        app["config"][str(payload["corpus_id"])]["doc_ids"] = [
            payload["job"],
            payload["document_ids"],
        ]

    if action in simples:
        await push_msg(
            app["websockets"],
            room,
            payload,
            skip=None,
            just=(room, user),
        )
        return None

    if action in errors:
        await _handle_error(app, user, room, payload)
        return None

    # handle configuration message
    if action == "set_config":
        # assert needed for mypy
        assert isinstance(payload["config"], dict)
        print(f"Config loaded: {len(payload['config'])} corpora")
        app["config"].update(payload["config"])
        payload["action"] = "update_config"
        await push_msg(app["websockets"], "", payload)
        return None

    # handle uploaded data (add to config, ws message if gui mode)
    if action == "uploaded":
        vian = cast(bool, payload["is_vian"])
        user_data = cast(JSONObject | None, payload["user_data"])
        app["config"][str(payload["id"])] = payload["entry"]
        if payload.get("gui"):
            filt = _filter_corpora(app["config"], vian, user_data)
            payload["config"] = cast(JSONObject, filt)
            await push_msg(app["websockets"], "", payload)

    if action == "query_result":
        await _handle_query(app, payload, user, room)
        return None


async def _handle_query(
    app: web.Application,
    payload: JSONObject,
    user: str,
    room: str,
) -> None:
    """
    Our subscribe listener has picked up a message, and it's about
    a query iteration. Create a websocket message to send to correct frontends
    """
    status = payload.get("status", "unknown")
    job = cast(str, payload["job"])
    the_job = Job.fetch(job, connection=app["redis"])
    job_status = the_job.get_status(refresh=True)
    if job_status in ("stopped", "canceled") or job in app["canceled"]:
        if job not in app["canceled"]:
            app["canceled"].append(job)
        print(f"Query was stopped: {job} -- preventing update")
        return
    total = payload.get("total_results_requested")
    if not total or total == -1:
        total = "all"
    so_far = payload.get("total_results_so_far", -1)
    done_batch = len(cast(Sized, payload["done_batches"]))
    tot_batch = len(cast(Sized, payload["all_batches"]))
    print(
        f"Query iteration: {job} -- {payload['batch_matches']} results found -- {so_far}/{total} total\n"
        + f"Status: {status} -- done {done_batch}/{tot_batch} batches ({payload['percentage_done']}% done)"
    )
    if (
        status == "partial"
        and job_status not in ("stopped", "canceled")
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
        done = len(cast(Sized, payload["done_batches"]))
        total_batches = len(cast(Sized, payload["all_batches"]))
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


async def _ait(self: WSMessage) -> WSMessage:
    """
    Just a hack to fix aiohttp websocket response
    """
    return self


async def sock(request: web.Request) -> web.WebSocketResponse:
    """
    Socket has to handle incoming messages, but also send a message when
    queries have finished processing
    """
    ws = web.WebSocketResponse(autoping=True, heartbeat=17)
    # setattr(ws, "__aiter__", _ait)

    await ws.prepare(request)

    sockets = request.app["websockets"]

    msg: WSMessage | None = None
    if request.app["mypy"]:
        while True:
            msg = await ws.receive()
            await _handle_sock(ws, msg, sockets, request.app["query_service"])
    else:
        # mypyc bug?
        async for msg in ws:
            await _handle_sock(ws, msg, sockets, request.app["query_service"])

    # connection closed
    # await ws.close(code=WSCloseCode.GOING_AWAY, message=b"Server shutdown")

    return ws


async def _handle_sock(
    ws: web.WebSocketResponse, msg: WSMessage, sockets: Websockets, qs: QueryService
) -> None:
    if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
        try:
            await ws.close(code=WSCloseCode.GOING_AWAY, message=b"User left")
        except Exception:
            pass
        return None
    if msg.type != WSMsgType.TEXT:
        return None

    payload = msg.json()
    action = payload["action"]
    possible_session: str | None = payload["room"]
    if possible_session is None:
        print("No room: something wrong")
        return None
    session_id: str = possible_session
    possible_user: str | None = payload["user"]
    if possible_user is None:
        print("User not logged in! Nothing to do")
        return None
    user_id: str = possible_user
    ident: tuple[str, str] = (session_id, user_id)
    response: JSONObject

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
            return None
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
                # "jobs": jobs,
            }
            await push_msg(sockets, session_id, response, just=ident)

    elif action == "validate":
        payload["_ws"] = True
        resp = await validate(**payload)
        # should never be a response type, we do this for type check
        if isinstance(resp, web.Response):
            return None
        await push_msg(sockets, session_id, resp, just=ident)

    elif action == "enough_results":
        job = payload["job"]
        jobs = qs.cancel_running_jobs(user_id, session_id, base=job)
        jobs = list(set(jobs))
        response = {
            "status": "stopped",
            "n": len(jobs),
            "action": "stopped",
            # "jobs": jobs,
        }
        if jobs:
            await push_msg(sockets, session_id, response, just=ident)


async def ws_cleanup(sockets: Websockets) -> None:
    """
    Periodically remove any closed websocket connections to ensure that app size
    doesn't irreversibly increase over time

    Send a message to other users about it, too
    """
    interval = 3600
    while True:
        for room, conns in sockets.items():
            to_close = set()
            for ws, user in conns:
                if ws.closed:
                    to_close.add((ws, user))
            for conn in to_close:
                msg = f"Removing stale WS connection: {room}/{user}"
                print(msg)
                logging.info(msg)
                conns.remove(conn)
            n_users = len(conns)
            if not n_users or not to_close:
                continue
            for _, user in to_close:
                response: JSONObject = {
                    "left": user,
                    "room": room,
                    "n_users": n_users,
                }
                await push_msg(sockets, room, response)
        await asyncio.sleep(interval)
    return None

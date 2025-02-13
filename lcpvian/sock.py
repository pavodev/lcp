"""
sock.py: websocket utilities, both sending and receiving

Each message should have `action`, which is how we know how to handle the
message, plus `user` and `room`, which tell us where the message should be sent.

Message sending is always ultimately done by utils.push_msg, which can send a
message to all users in a room, a specific user, all users, etc. as required
for a given `action`.

The /ws endpoint is connected to sock().

`listen_to_redis()` is running on a loop as a background job in the main process.
When the worker process finishes processing DB data, it publishes the data to
the Redis channel we are listening to. The main thread gets the message and
broadcasts it to the correct user/room via websocket.
"""

import asyncio
import json
import logging
import os
import traceback

from collections.abc import Coroutine
from datetime import datetime
from typing import Any, Sized, cast

try:
    from aiohttp import WSCloseCode, WSMsgType, web
except ImportError:
    from aiohttp import web
    from aiohttp.http import WSCloseCode, WSMsgType

from aiohttp.http_websocket import WSMessage
from rq.job import Job

from redis.asyncio.client import PubSub
from redis.exceptions import ConnectionError


from .configure import _get_batches, CorpusConfig
from .export import export
from .query import query
from .query_service import QueryService
from .utils import push_msg
from .validate import validate

from .typed import JSON, JSONObject, QueryArgs, RedisMessage, Results, Websockets
from .utils import (
    PUBSUB_CHANNEL,
    _filter_corpora,
    _set_config,
    _sign_payload,
    _get_query_info,
    _get_request_info,
    _get_first_job,
    _get_status,
    _decide_can_send,
    _get_progress,
)


MESSAGE_TTL = os.getenv("REDIS_WS_MESSSAGE_TTL", 5000)
QUERY_TTL = os.getenv("QUERY_TTL", 5000)


async def _process_message(
    message: RedisMessage, channel: PubSub, app: web.Application
) -> None:
    """
    Check that a WS message contains data, and is not a subscribe message,
    then handle it if so.
    """
    await asyncio.sleep(0.1)
    if not message or not isinstance(message, dict):
        return
    if message.get("type", "") == "subscribe":
        return
    if not message.get("data"):
        return
    data = json.loads(cast(bytes, message["data"]))
    if "msg_id" in data:
        raw: bytes = app["redis"].get(data["msg_id"])
        if not raw and "shared_redis" in app:
            raw = app["shared_redis"].get(data["msg_id"])
        if not raw:
            return None
        payload: JSONObject = json.loads(raw)
        if "user" in data or "room" in data:
            # If the incoming data contains fresher information than from redis memory,
            # (as determined by the presence of a user/room in data)
            # then sign the payload with the information contained in data
            _sign_payload(payload, data)
        payload["status"] = data.get("status", payload.get("status", ""))
        if not payload or not isinstance(payload, dict):
            return
    else:
        payload = data
    await _handle_message(payload, channel, app)
    return None


async def handle_redis_response(
    channel: PubSub, app: web.Application, test: bool = False, retries: int = 5
) -> None:
    """
    If redis publishes a message, it gets picked up here in an async loop
    and broadcast to the correct websockets.

    We need to know if we're running c-compiled code or not, because
    channel.get_message() fails when compiled to c for some reason
    """
    message: RedisMessage = None

    try:
        while True:
            await asyncio.sleep(0.1)
            try:
                if app.get("mypy", False) is True:
                    async for message in channel.listen():
                        if message is None:
                            continue
                        await _process_message(message, channel, app)
                        if message and test is True:
                            return None
                else:
                    while True:
                        await asyncio.sleep(0.1)
                        message = await channel.get_message(
                            ignore_subscribe_messages=True, timeout=10.0
                        )
                        if message is None:
                            continue
                        await _process_message(message, channel, app)
                        if message and test is True:
                            return None
            except ConnectionError as err:
                print("Possibly too much data for redis pubsub?", err)
                await asyncio.sleep(app["redis_pubsub_limit_sleep"])

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


async def listen_to_redis(
    app: web.Application, instance: str, test: bool = False
) -> None:
    """
    Using our async redis connection instance, listen for events coming from redis
    and delegate to the sender, All the try/except logic is shutdown logic only
    """
    ainstance = f"a{instance}"
    if instance not in app or ainstance not in app:
        return
    while True:
        try:
            async with app[ainstance].pubsub() as channel:
                await channel.subscribe(PUBSUB_CHANNEL)
                await handle_redis_response(channel, app, test=test)
        except ConnectionError as err:
            print("Connection error in listen_to_redis", err)
        except KeyboardInterrupt:
            pass
        except Exception as err:
            raise err
        try:
            print("Attempt unsubscribe")
            await channel.unsubscribe(PUBSUB_CHANNEL)
            print("unsubscribe success")
        except:
            pass
        try:
            await app["aredis"].quit()
        except Exception:
            pass
        try:
            app["redis"].quit()
        except Exception:
            pass
        await asyncio.sleep(0.1)
    return None


async def _handle_error(
    app: web.Application, user: str, room: str, payload: JSONObject
) -> None:
    """
    Sanitise errors send to FE if not in debug mode
    """
    payload["debug"] = app["_debug"]
    bad_keys = {"traceback", "original_query", "sentences_query", "sql", "consoleSQL"}
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
    status = payload.get("status", "")
    do_full = payload.get("full") and status != "finished"
    to_export = payload.get("to_export")
    simples = (
        "fetch_queries",
        "store_query",
        "background_job_progress",
        "document",
        "document_ids",
        "started_export",
        "export_link",
    )
    errors = (
        "failed",
        "upload_fail",
        "unregistered",
        "timeout",
        "interrupted",  # not currently used, maybe when rooms have multiple users
    )

    # for non-errors, we attach a msg_id to all messages, and store the message with
    # this key in redis so that the FE can retrieve it by /get_message endpoint anytime
    if (
        action not in errors
        and "msg_id" in payload
        and "no_restart" not in payload
        and app["_use_cache"]
        # and False
    ):
        uu = payload["msg_id"]
        if not app["redis"].get(uu):
            app["redis"].set(uu, json.dumps(payload))
        app["redis"].expire(uu, MESSAGE_TTL)

    if action == "sentences":
        base = "rq:job:"
        first_id = cast(str, payload["first_job"])
        query_id: str = str(payload["query"])
        app["redis"].expire(base + query_id, QUERY_TTL)
        if query_id != first_id:
            app["redis"].expire(base + first_id, QUERY_TTL)

    # for document ids request, we also add this information to config
    # so that on subsequent requests we can just fetch it from there
    if action == "document_ids":
        app["config"][str(payload["corpus_id"])]["doc_ids"] = [
            payload["job"],
            payload["document_ids"],
        ]

    to_submit: None | Coroutine[None, None, web.Response] = None

    if (
        (status == "partial" or do_full)
        and action in ("sentences", "meta")
        and payload.get("submit_query")
        and not payload.get("no_restart")
    ):
        # we don't await till until after we send the ws message for performance
        to_submit = query(None, manual=payload.get("submit_query"), app=app)

    if action in ("sentences", "meta"):
        drops = ("can_send", "submit_query")
        for drop in drops:
            payload.pop(drop, None)

    if to_export and action == "query_result" and status in ("satisfied", "finished"):
        export_obj: Any = to_export
        if isinstance(export_obj, str):
            export_obj = json.loads(cast(str, to_export))
        export_obj["user"] = user
        export_obj["room"] = room
        corpus_id: str = str(cast(list, payload["current_batch"])[0])
        export_obj["config"] = app["config"][corpus_id]
        await export(app, cast(JSONObject, export_obj), cast(str, payload["first_job"]))

    if action in simples or action in ("sentences", "meta"):
        if not payload.get("full") and (
            action != "sentences" or len(cast(Results, payload["result"])) > 2
        ):
            await push_msg(
                app["websockets"],
                room,
                payload,
                skip=None,
                just=(room, user),
            )
        else:
            print(f"Not sending {action} message!")
        if to_submit is not None:
            await to_submit
            to_submit = None
        return None

    if action in errors:
        await _handle_error(app, user, room, payload)
        return None

    # handle configuration message
    if action == "set_config":
        return await _set_config(payload, app)

    if action == "export_notifs":
        room = ""
        for rid, users in app["websockets"].items():
            for _, uid in users:
                if uid != user:
                    continue
                room = rid
                break
        if room:
            await push_msg(
                app["websockets"],
                room,
                payload,
                skip=None,
                just=(room, user),
            )
        return

    # handle the final stage of a corpus being uploaded.
    # - add the corpus to config
    # - if corpus was uploaded via gui mode, send a ws message
    #   to all users with the latest config so the FE can show it
    if action == "uploaded":
        # TODO: Should be chnaged to accept all app types (catchphrase, soundscript, videoscope)
        app_type = "lcp"
        user_data = cast(JSONObject | None, payload["user_data"])
        conf: CorpusConfig = cast(CorpusConfig, payload["entry"])
        conf["_batches"] = _get_batches(conf)
        ids_to_names: list[tuple[str, str]] = [
            (sid, c.get("shortname", "")) for sid, c in app["config"].items()
        ]
        id_str = str(payload["id"])
        for sid, name in ids_to_names:
            if name != conf.get("shortname", "") or int(sid) >= int(id_str):
                continue
            app["config"].pop(sid, {})
        app["config"][id_str] = conf
        if payload.get("gui"):
            authenticator = app["auth_class"](app)
            filt = _filter_corpora(authenticator, app["config"], app_type, user_data)
            payload["config"] = cast(JSONObject, filt)
            await push_msg(app["websockets"], "", payload)

    if action == "query_result":
        await _handle_query(app, payload)

    if to_submit is not None:
        await to_submit

    return None


def _print_status_message(payload: JSONObject, status: str) -> None:
    """
    Helper to print query status to console
    """
    total: int | str | None
    total = cast(int, payload.get("total_results_requested", -1))
    if not total or total == -1:
        total = "all"
    so_far = cast(int, payload.get("total_results_so_far", -1))
    done_batch = len(cast(Sized, payload["done_batches"]))
    tot_batch = len(cast(Sized, payload["all_batches"]))
    explain = "done" if not payload.get("search_all") else "time used"
    pred = cast(int, payload.get("projected_results", -1))
    print(
        f"{payload['batch_matches']} results found -- {so_far}/{total} total, projected: {pred}\n"
        + f"Status: {status} -- done {done_batch}/{tot_batch} batches ({payload['percentage_done']}% {explain})\n"
        + cast(str, payload["duration_string"])
    )
    return None


async def _handle_query(
    app: web.Application,
    payload: JSONObject,
) -> None:
    """
    Our subscribe listener has picked up a message, and it's about
    a query iteration. Create a websocket message to send to correct frontends
    """
    job = cast(str, payload["job"])
    the_job = Job.fetch(job, connection=app["redis"])
    job_status = the_job.get_status(refresh=True)
    if job_status in ("stopped", "canceled") or job in app["canceled"]:
        if job not in app["canceled"]:
            app["canceled"].append(job)
        print(f"Query was stopped: {job} -- preventing update")
        return

    first_job = _get_first_job(the_job, app["redis"])
    is_base = first_job.id == the_job.id
    request_info = _get_request_info(app["redis"], first_job.id)
    query_info = _get_query_info(app["redis"], job=first_job)

    total_so_far = query_info.get("total_results_so_far", 0)

    greediest_qa: QueryArgs | dict = {}
    to_submit: None | Coroutine[None, None, web.Response] = None
    for ri in request_info:

        user: str = ri.get("user", "")
        room: str = cast(str, ri.get("room", "") or "")

        status = _get_status(query_info, ri)

        to_send = {k: v for k, v in payload.items()}
        _sign_payload(to_send, kwargs=ri)

        is_full = ri.get("full", False)
        can_send = _decide_can_send(
            status, is_full, is_base, ri.get("from_memory", False)
        )
        # todo: this should no longer happen, as we send a progress update message instead?
        if (
            (status == "partial" or (is_full and status != "finished"))
            and job_status not in ("stopped", "canceled")
            and job not in app["canceled"]
            and not ri.get("simultaneous")
            and not ri.get("from_memory")
            and not ri.get("no_restart")
        ):
            can_send = False
            # TODO: create the manual request parameters from request_info + query_info + payload
            to_send["config"] = app["config"]
            total_requested = ri.get("total_results_requested", 0)
            offset = ri.get("offset", 0)
            this_upper_bound = total_requested + offset
            if is_full or this_upper_bound > greediest_qa.get(
                "total_results_requested", 0
            ) + greediest_qa.get("offset", 0):
                greediest_qa = ri
            to_send["offset"] = total_requested

        progress = _get_progress(the_job, query_info, ri)
        try:
            _print_status_message(progress, status)
        except:
            print("status message", progress, status)

        if is_full and status != "finished":  # and no export?
            # Send updates to FE
            prog = cast(dict[str, JSON], progress)
            await push_msg(
                app["websockets"],
                room,
                prog,
                skip=None,
                just=(room, user),
            )

        if not can_send:
            print("Not sending WS message!")
        else:
            keys = [
                "result",
                "job",
                "action",
                "user",
                "room",
                "n_users",
                "status",
                "word_count",
                "full",
                "first_job",
                "table",
                "total_duration",
                "jso",
                "from_memory",
                "batch_matches",
                "offset",
                "current_kwic_lines",
                "total_results_so_far",
                "percentage_done",
                "percentage_words_done",
                "total_duration",
                "duration",
                "total_results_requested",
                "projected_results",
                "batches_done",
                "simultaneous",
                "consoleSQL",
                "to_export",
            ]
            ws_payload = {k: v for k, v in to_send.items() if k in keys}
            await push_msg(
                app["websockets"],
                room,
                ws_payload,
                skip=None,
                just=(room, user),
            )
        # end of request_info iteration
    if greediest_qa.get("full", False) or total_so_far < greediest_qa.get(
        "total_results_requested", 0
    ) + greediest_qa.get("offset", 0):
        manual = {k: v for k, v in payload.items()}
        manual["offset"] = greediest_qa.get("offset", 0)
        manual["total_results_requested"] = greediest_qa.get(
            "total_results_requested", 200
        )
        manual["full"] = greediest_qa.get("full", False)
        to_submit = query(None, manual=manual, app=app)
    if to_submit is not None:
        await to_submit


async def sock(request: web.Request) -> web.WebSocketResponse:
    """
    Socket has to handle incoming messages, but also send a message when
    queries have finished processing
    """
    ws = web.WebSocketResponse(autoping=True, heartbeat=17)

    await ws.prepare(request)

    sockets = request.app["websockets"]

    msg: WSMessage | None = None
    if request.app["mypy"]:
        while True:
            msg = await ws.receive()
            await _handle_sock(
                ws, msg, sockets, request.app["query_service"], request.app["config"]
            )
    else:
        # mypyc bug?
        async for msg in ws:
            await _handle_sock(
                ws, msg, sockets, request.app["query_service"], request.app["config"]
            )

    # connection closed
    # await ws.close(code=WSCloseCode.GOING_AWAY, message=b"Server shutdown")

    return ws


async def _handle_sock(
    ws: web.WebSocketResponse,
    msg: WSMessage,
    sockets: Websockets,
    qs: QueryService,
    conf: dict[str, Any],
) -> None:
    """
    Handle an incoming message based on its `action`

    * validate queries
    * query has enough results, so stop it (in simultaneous mode only)
    * user joins/leaves room
    """
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
    possible_user: str | None = payload.get("user", None)
    if possible_user is None:
        print("User not logged in! Nothing to do")
        return None
    user_id: str = possible_user
    ident: tuple[str, str] = (session_id, user_id)
    response: JSONObject

    # user opens the query page/joins a room
    if action == "joined":
        originally = len(sockets[session_id])
        sockets[session_id].add((ws, user_id))
        currently = len(sockets[session_id])
        if session_id and originally != currently:
            response = {"joined": user_id, "room": session_id, "n_users": currently}
            await push_msg(sockets, session_id, response, skip=ident)

    # user closes page or leaves a room
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

    # query is stopped, automatically or manually
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

    # user edited a query, triggering auto-validation of the DQD/JSON
    elif action == "validate":
        payload["config"] = conf
        resp = await validate(**payload)
        await push_msg(sockets, session_id, resp, just=ident)

    # used in simultaneous mode only: once FE sees enough results, cancel
    # any other ongoing jobs
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
    interval = 3600 * 48
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

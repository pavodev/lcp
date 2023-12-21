"""
utils.py: all miscellaneous helpers and tools used by backend
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import traceback

from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable, Coroutine, Mapping

from datetime import date, datetime, timedelta

from typing import Any, cast, TypeAlias

from uuid import UUID, uuid4

try:
    from aiohttp import web, ClientSession
except ImportError:
    from aiohttp import web
    from aiohttp.client import ClientSession

# here we remove __slots__ from these superclasses because mypy can't handle them...
from redis import Redis as RedisConnection

from redis._parsers import _AsyncHiredisParser, _AsyncRESP3Parser


from redis.utils import HIREDIS_AVAILABLE

if HIREDIS_AVAILABLE:
    DefaultParser = _AsyncHiredisParser
else:
    DefaultParser = _AsyncRESP3Parser

ParserClass = DefaultParser

from rq.command import PUBSUB_CHANNEL_TEMPLATE
from rq.connections import get_current_connection
from rq.job import Job

from .configure import CorpusConfig, CorpusTemplate
from .typed import (
    Batch,
    Config,
    Headers,
    JSON,
    JSONObject,
    MainCorpus,
    RunScript,
    Websockets,
)

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "lcpvian"

TRUES = {"true", "1", "y", "yes"}

MESSAGE_TTL = int(os.getenv("REDIS_WS_MESSSAGE_TTL", 5000))


class Interrupted(Exception):
    """
    Used when a user interrupts a query from frontend
    """

    pass


class CustomEncoder(json.JSONEncoder):
    """
    UUID and time to string, otherwise normal serialisation
    """

    def default(self, obj: Any) -> JSON:
        if isinstance(obj, bytes):
            return obj.decode("utf-8")
        if isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        default: JSON = json.JSONEncoder.default(self, obj)
        return default


def ensure_authorised(func: Callable) -> Callable:
    """
    auth decorator, still wip
    """
    return func

    # todo:
    # @wraps(func)
    # async def deco(request: web.Request, *args, **kwargs):
    #    headers = await _lama_user_details(getattr(request, "headers", request))

    #    if "X-Access-Token" in headers:
    #        token = headers.get("X-Access-Token")
    #        try:
    #            decoded = jwt.decode(
    #                token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"]
    #            )
    #            request.jwt = decoded
    #        except Exception as err:
    #            raise err
    #    if "X-Display-Name" in headers:
    #        username = headers.get("X-Display-Name")
    #        request.username = username
    #    if "X-Mail" in headers:
    #        username = headers.get("X-Mail")
    #        request.username = username

    #    if not request.username:
    #        raise ValueError("401? No username")

    #    return func(request, *args, **kwargs)

    # return deco


def _extract_lama_headers(headers: Mapping[str, Any]) -> dict[str, str]:
    """
    Create needed headers from existing headers
    """
    retval = {
        "X-API-Key": os.environ["LAMA_API_KEY"],
        "X-Remote-User": headers.get("X-Remote-User"),
        "X-Display-Name": headers["X-Display-Name"]
        if headers.get("X-Display-Name")
        else "",
        "X-Edu-Person-Unique-Id": headers.get("X-Edu-Person-Unique-Id"),
        "X-Home-Organization": headers.get("X-Home-Organization"),
        "X-Schac-Home-Organization": headers.get("X-Schac-Home-Organization"),
        "X-Persistent-Id": headers.get("X-Persistent-Id"),
        "X-Given-Name": headers["X-Given-Name"] if headers.get("X-Given-Name") else "",
        "X-Surname": headers["X-Surname"] if headers.get("X-Surname") else "",
        "X-Principal-Name": headers.get("X-Principal-Name"),
        "X-Mail": headers.get("X-Mail"),
        "X-Shib-Identity-Provider": headers.get("X-Shib-Identity-Provider"),
    }
    return {k: v for k, v in retval.items() if v}


def _check_email(email: str) -> bool:
    """
    Is an email address valid?
    """
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return bool(re.fullmatch(regex, email))


async def _lama_user_details(headers: Headers) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/user/details"
    async with ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            jso: JSONObject = await resp.json()
            jso["max_kwic"] = int(os.getenv("DEFAULT_MAX_KWIC_LINES", 9999))
            return jso


async def _lama_project_create(
    headers: Headers, project_data: dict[str, str]
) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile"
    async with ClientSession() as session:
        async with session.post(
            url, json=project_data, headers=_extract_lama_headers(headers)
        ) as resp:
            jso: JSONObject = await resp.json()
            return jso


async def _lama_api_create(headers: Headers, project_id: str) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/api/create"
    async with ClientSession() as session:
        async with session.post(url, headers=_extract_lama_headers(headers)) as resp:
            jso: JSONObject = await resp.json(content_type=None)
            return jso


async def _lama_api_revoke(
    headers: Headers, project_id: str, apikey_id: str
) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/api/{apikey_id}/revoke"
    data = {"comment": "Revoked by user"}
    async with ClientSession() as session:
        async with session.post(
            url, headers=_extract_lama_headers(headers), json=data
        ) as resp:
            jso: JSONObject = await resp.json(content_type=None)
            return jso


async def _lama_check_api_key(headers: Headers) -> JSONObject:
    """
    Get details about a user via their API key
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/api/check"
    key = headers["X-API-Key"]
    secret = headers["X-API-Secret"]
    api_headers = {"X-API-Key": key, "X-API-Secret": secret}
    async with ClientSession() as session:
        async with session.post(url, headers=api_headers) as resp:
            jso: JSONObject = await resp.json()
            return jso


async def _general_error_handler(
    kind: str, exc: Exception, request: web.Request
) -> None:
    """
    Catch exception, log it, try to send ws message
    """
    try:
        request_data = await request.json()
    except json.decoder.JSONDecodeError:
        return None
    tb = ""
    if hasattr(exc, "__traceback__"):
        tb = "".join(traceback.format_tb(exc.__traceback__))
    user = cast(str, request_data.get("user", ""))
    room = cast(str | None, request_data.get("room", None))
    job = str(exc).split("rq:job:")[-1] if kind == "timeout" else ""
    jso = {
        "user": user,
        "room": room,
        "error": str(exc),
        "status": kind,
        "action": kind,
        "traceback": tb,
    }
    msg = f"Warning: {kind}"
    if job:
        msg += f" -- {job}"
        jso["job"] = job
    logging.warning(msg, extra=jso)
    if user:
        connection = request.app["redis"]
        connection.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


async def handle_timeout(exc: Exception, request: web.Request) -> None:
    """
    If a job dies due to TTL, we send this...
    """
    await _general_error_handler("timeout", exc, request)


async def handle_lama_error(exc: Exception, request: web.Request) -> None:
    """
    If we get a connectionerror when trying to reach lama...
    """
    await _general_error_handler("unregistered", exc, request)


def _get_status(
    n_results: int,
    total_results_requested: int,
    done_batches: list[Batch],
    all_batches: list[Batch],
    search_all: bool = False,
    full: bool = False,
    time_so_far: float = 0.0,
) -> str:
    """
    Is a query finished, or do we need to do another iteration?

        finished: no more batches available
        overtime: query with time limitation ran out of time
        partial: currently fewer than total_results_requested
        satisfied: >= total_results_requested
    """
    if len(done_batches) == len(all_batches):
        return "finished"
    allowed_time = float(os.getenv("QUERY_ALLOWED_JOB_TIME", 0.0))
    too_long: bool = time_so_far > allowed_time
    if allowed_time > 0.0 and search_all and too_long and not full:
        return "overtime"
    if search_all:
        return "partial"
    if total_results_requested in {-1, False, None}:
        return "partial"
    if n_results >= total_results_requested and not full:
        return "satisfied"
    return "partial"


async def sem_coro(
    semaphore: asyncio.Semaphore, coro: Awaitable[list[tuple[int | str | bool]]]
) -> list[tuple[int | str | bool]]:
    """
    Stop too many tasks from running at once
    """
    async with semaphore:
        return await coro


async def gather(
    n: int, tasks: list[Coroutine], name: str | None = None
) -> list[list[RunScript]]:
    """
    A replacement for asyncio.gather that runs a maximum of n tasks at once.
    If any task errors, we cancel all tasks in the group that share the same name

    Used exclusively during upload/import right now

    Like asyncio.gather, it returns a list containing the results from the
    coroutine `tasks`,

    If there is an error, we try to cancel all jobs of the same type (name)
    """
    if n > 0:
        semaphore = asyncio.Semaphore(n)
        tsks = [asyncio.create_task(sem_coro(semaphore, c), name=name) for c in tasks]
    else:
        tsks = [asyncio.create_task(c, name=name) for c in tasks]
    try:
        gathered: list[list[RunScript]] = await asyncio.gather(*tsks)
        return gathered
    except BaseException as err:
        print(f"Error while gathering tasks: {str(err)[:1000]}. Cancelling others...")
        running_tasks = asyncio.all_tasks()
        current = asyncio.current_task()
        if current is not None:
            try:
                current.cancel()
            except Exception:
                pass
            name = current.get_name()
            running_tasks.remove(current)
        for task in running_tasks:
            if name is not None and task.get_name() == name:
                task.cancel()
        raise err


def _handle_large_msg(strung: str, limit: int) -> list[bytes] | list[str]:
    """
    Before we publish a message to redis pubsub, check if it's larger
    than the pubsub limit. If it is, we break it into chunks, wait between
    each publish, then join them back together on the other side

    strung is a serialised JSON object, return a list str/bytes to send,
    with a wait time determined by redis config in between each
    """
    # just a bit of extra room around our redis hard limit
    buffer = 100

    if limit == -1:
        return [strung]

    enc: bytes = strung.encode("utf-8")

    if len(enc) < limit:
        return [strung]
    cz = limit - buffer
    n_chunks = math.ceil(len(enc) / cz)
    chunks: list[bytes] = [enc[0 + i : cz + i] for i in range(0, len(enc), cz)]
    out: list[bytes] = []
    uu = str(uuid4())[:8]
    for i, chunk in enumerate(chunks, start=1):
        formed = f"#CHUNK#{uu}#{i}#{n_chunks}#".encode("utf-8")
        formed += chunk
        out.append(formed)
    return out


async def push_msg(
    sockets: Websockets,
    session_id: str,
    msg: JSONObject | bytes,
    skip: tuple[str | None, str] | None = None,
    just: tuple[str | None, str] | None = None,
    **kwargs,
) -> None:
    """
    Send JSON websocket message to one or more users/rooms

    A message can be sent to all users by passing an empty string as session_id
    """
    sent_to: set[tuple[str | None, str]] = set()
    for room, users in sockets.items():
        if session_id and room != session_id:
            continue
        for conn, user_id in users:
            if (room, user_id) in sent_to:
                continue
            if skip and (room, user_id) == skip:
                continue
            if just and (room, user_id) != just:
                continue
            try:
                if isinstance(msg, bytes):
                    await conn.send_bytes(msg)
                else:
                    await conn.send_json(msg)
            except ConnectionResetError:
                print(f"Connection reset: {room}/{user_id}")
                pass
            sent_to.add((room, user_id))


async def _set_config(payload: JSONObject, app: web.Application) -> None:
    """
    Helper to set the configuration on the app
    """
    # assert needed for mypy
    assert isinstance(payload["config"], dict)
    print(f"Config loaded: {len(payload['config'])} corpora")
    app["config"].update(payload["config"])
    payload["action"] = "update_config"
    await push_msg(app["websockets"], "", payload)
    return None


def _filter_corpora(
    config: Config,
    is_vian: bool,
    user_data: JSONObject | None,
    get_all: bool = False,
) -> Config:
    """
    Filter corpora based on app type and user projects
    """
    subtype: TypeAlias = list[dict[str, str]]

    ids: set[str] = set()
    if isinstance(user_data, dict):
        subs = cast(dict[str, subtype], user_data.get("subscription", {}))
        sub = cast(subtype, subs.get("subscriptions", []))
        for s in sub:
            ids.add(s["id"])
        for proj in cast(list[dict[str, Any]], user_data.get("publicProfiles", [])):
            ids.add(proj["id"])

    corpora: dict[str, CorpusConfig] = {}
    for corpus_id, conf in config.items():
        idx = str(corpus_id)
        if idx == "-1":
            corpora[idx] = conf
            continue
        allowed: list[str] = conf.get("projects", [])
        if get_all:
            corpora[idx] = conf
            continue
        if "all" in allowed:
            corpora[idx] = conf
            continue
        if is_vian and "vian" in allowed:
            corpora[idx] = conf
            continue
        if not is_vian and "lcp" in allowed:
            corpora[idx] = conf
            continue
        if not allowed or any(i in ids for i in allowed):
            corpora[idx] = conf
            continue
    return corpora


def _row_to_value(
    tup: MainCorpus,
    project: str | None = None,
) -> CorpusConfig:
    """
    Take a row of the main.corpus table and make a CorpusConfig dict
    """
    (
        corpus_id,
        name,
        current_version,
        version_history,
        description,
        template,
        schema_path,
        token_counts,
        mapping,
        enabled,
        sample_query,
    ) = tup
    ver = str(current_version)
    corpus_template = cast(CorpusTemplate, template)
    if not enabled:
        print(f"Corpus disabled: {name}={corpus_id}")

    schema_path = schema_path.replace("<version>", ver)
    if not schema_path.endswith(ver):
        schema_path = f"{schema_path}{ver}"
    layer = corpus_template["layer"]
    fc = corpus_template["firstClass"]
    tok = fc["token"]
    cols = layer[tok]["attributes"]

    projects: list[str] = corpus_template.get("projects", [])
    if not projects:
        projects = ["all"]
    if project and project not in projects:
        projects.append(project)
    corpus_template["projects"] = projects

    rest = {
        "shortname": name,
        "corpus_id": int(corpus_id),
        "current_version": int(ver) if ver.isnumeric() else ver,
        "version_history": version_history,
        "description": description,
        "schema_path": schema_path,
        "token_counts": token_counts,
        "mapping": mapping,
        "enabled": enabled,
        "segment": fc["segment"],
        "token": fc["token"],
        "document": fc["document"],
        "column_names": cols,
        "sample_query": sample_query,
    }

    together = {**corpus_template, **rest}
    return cast(CorpusConfig, together)


def _get_sent_ids(
    associated: str | list[str], total: int, offset: int = 0
) -> list[int] | list[str]:
    """
    Helper to format the query to retrieve sentences: get a list of unique sent
    ids needed in order to create KWIC results
    """
    out: list[int] = []
    conn = get_current_connection()
    job = _get_associated_query_job(associated, conn)
    if job.get_status(refresh=True) in ("stopped", "canceled"):
        raise Interrupted()
    if job.result is None:
        raise Interrupted()
    if not job.result:
        return out
    prev_results = job.result
    seg_ids: set[str | int] = set()
    rs = job.kwargs["meta_json"]["result_sets"]
    kwics = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"])
    counts: Counter[int] = Counter()
    to_use: int = next((int(i[0]) for i in prev_results if int(i[0]) in kwics), -2)
    added: Counter[int] = Counter()

    if to_use == -2:
        return out

    for res in prev_results:
        key = int(res[0])
        rest = res[1]
        if key != to_use:
            continue
        counts[key] += 1
        if offset > 0 and counts[key] - 1 < offset:
            continue
        if total >= 0 and added[key] >= total:
            continue
        seg_ids.add(rest[0])
        added[key] += 1

    return cast(list[str] | list[int], list(sorted(seg_ids)))


def _get_associated_query_job(
    depends_on: str | list[str],
    connection: RedisConnection,
) -> Job:
    """
    Helper to find the query job associated with sent job
    """
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]
    depended = Job.fetch(depends_on, connection=connection)
    return depended


def format_query_params(
    query: str, params: tuple | dict[str, Any]
) -> tuple[str, tuple]:
    """
    Helper to allow for sqlalchemy format query with asyncpg
    """
    if isinstance(params, tuple):
        return query, params
    out = []
    n = 1
    for k, v in params.items():
        in_query = f":{k}"
        if in_query in query:
            query = query.replace(in_query, f"${n}")
            n += 1
            out.append(v)
    return query, tuple(out)


def _get_first_job(job: Job, connection: RedisConnection[bytes]) -> Job:
    """
    Helper to get the base job from a group of query jobs
    """
    first_job = job
    if job.kwargs.get("first_job"):
        first_job = Job.fetch(job.kwargs["first_job"], connection=connection)
    return first_job


def _time_remaining(status: str, total_duration: float, use: float) -> float:
    """
    Helper to estimate remaining time for a job
    """
    if status == "finished":
        return 0.0
    if use <= 0.0:
        return 0.0
    timed = (total_duration * (100.0 / use)) - total_duration
    return max(0.0, round(timed, 3))


def _decide_can_send(
    status: str, is_full: bool, is_base: bool, from_memory: bool
) -> bool:
    """
    Helper to figure out if we can send query message to the user or not

    We don't exit early if we can't send, because we still need to store the
    message and potentially trigger a new job
    """
    if not is_full or status == "finished":
        return True
    elif is_base and from_memory:
        return True
    elif not is_base and not from_memory:
        return True
    return False


def _get_total_requested(kwargs: dict[str, Any], job: Job) -> int:
    """
    Helper to find the total requested -- remove this after cleanup ideally
    """
    total_requested = cast(int, kwargs.get("total_results_requested", -1))
    if total_requested > 0:
        return total_requested
    total_requested = job.kwargs.get("total_results_requested", -1)
    if total_requested > 0:
        return total_requested
    return -1


def _publish_msg(connection: RedisConnection, message: JSONObject, msg_id: str) -> None:

    if not isinstance(message, (str, bytes)):
        message = json.dumps(message, cls=CustomEncoder)
    connection.set(msg_id, message)
    connection.expire(msg_id, MESSAGE_TTL)
    connection.publish(PUBSUB_CHANNEL, json.dumps({"msg_id": msg_id}))
    return None

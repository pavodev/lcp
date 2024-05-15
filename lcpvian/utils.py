"""
utils.py: all miscellaneous helpers and tools used by backend
"""

import asyncio
import json
import logging
import math
import numpy as np
import os
import re
import shutil
import traceback

from dotenv import load_dotenv
from asyncpg import Range
from collections import Counter
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from datetime import date, datetime
from typing import Any, cast, TypeAlias
from uuid import uuid4, UUID

try:
    from aiohttp import web, ClientSession
except ImportError:
    from aiohttp import web
    from aiohttp.client import ClientSession

# here we remove __slots__ from these superclasses because mypy can't handle them...
from redis import Redis as RedisConnection

from redis._parsers import _AsyncHiredisParser, _AsyncRESP3Parser

from redis.utils import HIREDIS_AVAILABLE

DefaultParser: Any

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
    Websockets,
)

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "lcpvian"

TRUES = {"true", "1", "y", "yes"}
FALSES = {"", "0", "null", "none"}

MESSAGE_TTL = int(os.getenv("REDIS_WS_MESSSAGE_TTL", 5000))

# The query in get_config is complex because we inject the possible values of the global attributes in corpus_template
CONFIG_SELECT = """
mc.corpus_id,
mc.name,
mc.current_version,
mc.version_history,
mc.description,
mc.corpus_template::jsonb || a.glob_attr::jsonb AS corpus_template,
mc.schema_path,
mc.token_counts,
mc.mapping,
mc.enabled,
mc.sample_query
"""
CONFIG_JOIN = """CROSS JOIN
(SELECT
    json_build_object('glob_attr', jsonb_object_agg(
        t4.typ,
        case
            when array_length(t4.labels,1)=1 then to_json(t4.labels[1])
            else to_json(t4.labels)
        end
    )) AS glob_attr
    FROM
        (SELECT
            pg_type.typname AS typ,
            array_agg(pg_enum.enumlabel) AS labels
            FROM pg_enum
            JOIN pg_type ON pg_type.oid = pg_enum.enumtypid
            JOIN
                (SELECT
                    DISTINCT t2each.key AS typname
                    FROM
                        (SELECT
                            t1each.key AS layer,
                            t1each.value->>'attributes' AS attributes
                            FROM
                                (SELECT corpus_template->>'layer' AS lay FROM main.corpus) t1,
                                json_each(t1.lay::json) t1each
                        ) t2,
                        json_each(t2.attributes::json) t2each
                    WHERE
                        t2each.value->>'isGlobal' = 'true'
                ) t3 ON t3.typname = pg_type.typname
            GROUP BY typ
        ) t4
) a
"""


class Interrupted(Exception):
    """
    Used when a user interrupts a query from frontend
    """

    pass


class CustomEncoder(json.JSONEncoder):
    """
    Fix numpy objects and dates, otherwise normal serialisation
    """

    def default(self, obj: Any) -> JSON:
        if isinstance(obj, bytes):
            return obj.decode("utf-8")
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        # todo -- are we sure this isn't needed?:
        # ifisinstance(obj, uuid.UUID):
        #   return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        default: JSON = json.JSONEncoder.default(self, obj)
        return default


def load_env() -> None:
    """
    Load .env from ~/lcp/.env if present, otherwise from current dir/dotenv defaults
    """
    current = os.path.join(os.getcwd(), ".env")
    installed_path = os.path.expanduser("~/lcp/.env")
    loaded = False
    if os.path.isfile(installed_path):
        try:
            load_dotenv(installed_path, override=True)
            print(f"Loaded .env from {installed_path}")
            return None
        except:
            print(f"Could not load {installed_path}...")
    if not loaded:
        load_dotenv(override=True)
        print(f"Loaded .env from {current}")
    return None


def setup() -> None:
    """
    Command user can run as `lcp-setup` -- right now it just makes a .env

    We could add argparsing, input() based formatting of the .env, etc etc.
    """
    home = os.path.expanduser("~/lcp")
    os.makedirs(home, exist_ok=True)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_ex = os.path.join(root, ".env.example")
    out = os.path.join(home, ".env")
    if not os.path.isfile(out):
        shutil.copyfile(env_ex, out)
        print(
            f"""
            Created: {out} ...
            Edit this file with needed values for the app to run,
            then run `lcp` and `lcp-worker` commands to start app
            """.strip()
        )


def ensure_authorised(func: Callable[..., Any]) -> Callable[..., Any]:
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
        "X-Display-Name": (
            headers["X-Display-Name"] if headers.get("X-Display-Name") else ""
        ),
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
    url = f"{os.environ['LAMA_API_URL']}/user/details/v2"
    async with ClientSession() as session:
        async with session.post(url, data=_extract_lama_headers(headers)) as resp:
            jso: JSONObject = await resp.json()
            jso["max_kwic"] = int(os.getenv("DEFAULT_MAX_KWIC_LINES", 9999))
            return jso


async def _lama_project_user_update(
    headers: Headers, project_id: str, user_id: str, data: dict
) -> JSONObject:
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/account/{user_id}/modify"
    async with ClientSession() as session:
        async with session.post(
            url, json=data, headers=_extract_lama_headers(headers)
        ) as resp:
            jso: JSONObject = await resp.json()
            return jso


async def _lama_invitation_remove(headers: Headers, invitation_id: str) -> JSONObject:
    url = f"{os.environ['LAMA_API_URL']}/invitation/{invitation_id}/remove"
    async with ClientSession() as session:
        async with session.post(url, headers=_extract_lama_headers(headers)) as resp:
            jso: JSONObject = await resp.json()
            return jso


async def _lama_invitation_add(
    headers: Headers, project_id: str, invitation_data: dict
) -> JSONObject:
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/invitation/add"
    async with ClientSession() as session:
        async with session.post(
            url, json=invitation_data, headers=_extract_lama_headers(headers)
        ) as resp:
            jso: JSONObject = await resp.json()
            return jso


async def _lama_project_users(headers: Headers, project_id: str) -> JSONObject:
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/accounts"
    async with ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            jso: JSONObject = await resp.json()
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


async def _lama_project_update(
    headers: Headers, project_id: str, project_data: dict[str, str]
) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}"
    async with ClientSession() as session:
        async with session.post(
            url, headers=_extract_lama_headers(headers), json=project_data
        ) as resp:
            jso: JSONObject = await resp.json(content_type=None)
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
    n: int, tasks: list[Coroutine[None, None, Any]], name: str | None = None
) -> list[list[tuple[int | str | bool]]]:
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
        gathered: list[list[tuple[int | str | bool]]] = await asyncio.gather(*tsks)
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


def _format_config_query(template: str) -> str:
    """
    Select the appropriate fields from main.corpus
    and inject the possible values of the global attributes in corpus_template
    """
    return template.format(selects=CONFIG_SELECT, join=CONFIG_JOIN)


async def _set_config(payload: JSONObject, app: web.Application) -> None:
    """
    Helper to set the configuration on the app
    """
    # assert needed for mypy
    assert isinstance(payload["config"], dict)
    print(f"Config loaded: {len(payload['config'])} corpora")
    app["config"] = payload["config"]
    payload["action"] = "update_config"
    await push_msg(app["websockets"], "", payload)
    app["redis"].set("app_config", json.dumps(payload["config"]))
    app["redis"].expire("app_config", MESSAGE_TTL)
    return None


subtype: TypeAlias = list[dict[str, str]]


def _filter_corpora(
    config: Config,
    app_type: str,
    user_data: JSONObject | None,
    get_all: bool = False,
) -> Config:
    """
    Filter corpora based on app type and user projects
    """

    ids: set[str] = set()
    if isinstance(user_data, dict):
        subs = cast(dict[str, subtype], user_data.get("subscription", {}))
        sub = subs.get("subscriptions", [])
        for s in sub:
            ids.add(s["id"])
        for proj in cast(list[dict[str, Any]], user_data.get("publicProfiles", [])):
            ids.add(proj["id"])

    ids.add("all")
    corpora: dict[str, CorpusConfig] = {}
    for corpus_id, conf in config.items():
        if (
            get_all is False
            and len(
                [
                    project_id
                    for project_id in conf.get("projects", {})
                    if project_id in ids
                ]
            )
            == 0
        ):
            continue
        idx = str(corpus_id)
        if idx == "-1":
            corpora[idx] = conf
            continue
        # data_type: str | None = str(conf["meta"].get("dataType")) if conf and conf.get("meta") else None
        data_type: str = ""
        for slot in cast(dict, conf).get("meta", {}).get("mediaSlots", {}).values():
            if data_type == "video":
                continue
            data_type = slot.get("mediaType", "")
        if get_all or app_type in ("lcp", "catchphrase"):
            corpora[idx] = conf
            continue
        if app_type == "videoscope" and data_type in ["video"]:
            corpora[idx] = conf
            continue
        if app_type == "soundscript" and data_type in ["audio", "video"]:
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
    layer = corpus_template.get("layer", {})
    fc = corpus_template.get("firstClass", {})
    tok = fc.get("token", "")
    cols = layer.get(tok, {}).get("attributes", {})

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
        "segment": fc.get("segment"),
        "token": fc.get("token"),
        "document": fc.get("document"),
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
    kwargs: dict = cast(dict, job.kwargs)
    rs = kwargs.get("meta_json", {})["result_sets"]
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
    connection: "RedisConnection[bytes]",
) -> Job:
    """
    Helper to find the query job associated with sent job
    """
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]
    depended = Job.fetch(depends_on, connection=connection)
    return depended


def format_query_params(
    query: str, params: dict[str, int | str]
) -> tuple[str, tuple[int | str, ...]]:
    """
    Helper to allow for sqlalchemy format query with asyncpg
    """
    if isinstance(params, tuple):
        return query, params
    out = []
    n = 1
    if not isinstance(params, dict):
        return query, params
    for k, v in params.items():
        in_query = f":{k}"
        if in_query in query:
            query = query.replace(in_query, f"${n}")
            n += 1
            out.append(v)
    return query, tuple(out)


def format_meta_lines(
    query: str, result: list[dict[int, str | dict[Any, Any]]]
) -> dict[str, Any] | None:
    # replace this with actual upstream handling of column names
    pre_columns = re.match(
        r"SELECT -2::int2 AS rstype, ((.+ AS .+[, ])+?)FROM.+", query
    )
    if not pre_columns:
        return None
    columns: list[str] = [
        p.split(" AS ")[1].strip() for p in pre_columns[1].split(", ")
    ]  # [seg_id, layer1, layer2, etc.]
    layers: dict[str, None] = {
        c.split("_")[0]: None for c in columns if not c.endswith("_id")
    }
    formatted: dict[str, Any] = {}
    for res in result:
        seg_id = "0"
        segment: dict[str, dict[Any, Any]] = {layer: {} for layer in layers}
        for n, layer_prop in enumerate(columns):
            if not res[n + 1]:
                continue
            if layer_prop == "seg_id":
                seg_id = cast(str, res[n + 1])
            else:
                m = re.match(rf"^([^_]+)_(.+)$", layer_prop)
                if not m:
                    continue
                layer, prop = m.groups()
                if prop == "meta":
                    meta: str | dict[Any, Any]
                    if isinstance(res[n + 1], str):
                        meta = json.loads(cast(str, res[n + 1]))
                    else:
                        meta = res[n + 1]
                    if not isinstance(meta, dict):
                        continue
                    segment[layer] = {**(segment[layer]), **meta}
                else:
                    if isinstance(res[n + 1], dict):
                        segment[layer][prop] = json.dumps(res[n + 1])
                    elif any(
                        isinstance(res[n + 1], type)
                        for type in [int, str, bool, list, tuple, UUID, date]
                    ):
                        segment[layer][prop] = str(res[n + 1])
                    elif isinstance(res[n + 1], Range):
                        segment[layer][prop] = [
                            cast(str, res[n + 1]).lower,
                            cast(str, res[n + 1]).upper,
                        ]
        segment = {
            layer: props
            for layer, props in segment.items()
            if props and [x for x in props if x != "id"]
        }
        if not segment:
            continue
        formatted[str(seg_id)] = segment
    return formatted


def range_to_array(sql_ref: str) -> str:
    return f"jsonb_build_array(lower({sql_ref}), upper({sql_ref}))"


def _layer_contains(config: CorpusConfig, parent: str, child: str) -> bool:
    conf_layers: dict = config.get("layer", {})
    child_layer = conf_layers.get(child)
    parent_layer = conf_layers.get(parent)
    if not child_layer or not parent_layer:
        return False
    while parent_layer and (parents_child := parent_layer.get("contains")):
        if parents_child == child:
            return True
        parent_layer = conf_layers.get(parents_child)
    return False


def _determine_language(batch: str) -> str | None:
    """
    Helper to find language from batch
    """
    batch = batch.rstrip("0123456789")
    if batch.endswith("rest"):
        batch = batch[:-4]
    for lan in ["de", "en", "fr", "ca", "it"]:
        if batch.endswith(f"_{lan}"):
            return lan
    return None


def _get_first_job(job: Job, connection: "RedisConnection[bytes]") -> Job:
    """
    Helper to get the base job from a group of query jobs
    """
    first_job = job
    first_job_id_from_kwargs = cast(dict, job.kwargs).get("first_job")
    if first_job_id_from_kwargs:
        first_job = Job.fetch(first_job_id_from_kwargs, connection=connection)
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
    total_requested = cast(dict, job.kwargs).get("total_results_requested", -1)
    if total_requested > 0:
        return total_requested
    return -1


def _publish_msg(
    connection: "RedisConnection[bytes]", message: JSONObject | str | bytes, msg_id: str
) -> None:
    """
    Store a message with msg_id as key, and notify listener
    """
    if not isinstance(message, (str, bytes)):
        message = json.dumps(message, cls=CustomEncoder)
    connection.set(msg_id, message)
    connection.expire(msg_id, MESSAGE_TTL)
    connection.publish(PUBSUB_CHANNEL, json.dumps({"msg_id": msg_id}))
    return None

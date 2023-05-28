from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence

from datetime import date, datetime

from typing import Any, cast, final

from uuid import UUID

try:
    from aiohttp import web, ClientSession
except ImportError:
    from aiohttp import web
    from aiohttp.client import ClientSession
from redis import Redis as RedisConnection

# here we remove __slots__ from these superclasses because mypy can't handle them...
from redis.asyncio.connection import BaseParser

del BaseParser.__slots__  # type: ignore
from redis.asyncio.connection import HiredisParser, PythonParser

del HiredisParser.__slots__  # type: ignore
del PythonParser.__slots__  # type: ignore

from redis.utils import HIREDIS_AVAILABLE
from rq.command import PUBSUB_CHANNEL_TEMPLATE
from rq.connections import get_current_connection
from rq.job import Job

from .configure import CorpusConfig, CorpusTemplate
from .qi import QueryIteration
from .typed import Batch, Config, Headers, JSON, JSONObject, MainCorpus, Websockets
from .worker import SQLJob

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


class Interrupted(Exception):
    """
    Used when a user interrupts a query from frontend
    """

    pass


class CustomEncoder(json.JSONEncoder):
    """
    UUID and time to string
    """

    def default(self, obj: Any) -> JSON:
        if isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


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


def _extract_lama_headers(headers: Mapping) -> dict[str, str]:
    """
    Create needed headers from existing headers
    """
    retval = {
        "X-API-Key": os.environ["LAMA_API_KEY"],
        "X-Remote-User": headers.get("X-Remote-User"),
        "X-Display-Name": headers["X-Display-Name"].encode("cp1252").decode("utf8")
        if headers.get("X-Display-Name")
        else "",
        "X-Edu-Person-Unique-Id": headers.get("X-Edu-Person-Unique-Id"),
        "X-Home-Organization": headers.get("X-Home-Organization"),
        "X-Schac-Home-Organization": headers.get("X-Schac-Home-Organization"),
        "X-Persistent-Id": headers.get("X-Persistent-Id"),
        "X-Given-Name": headers["X-Given-Name"].encode("cp1252").decode("utf8")
        if headers.get("X-Given-Name")
        else "",
        "X-Surname": headers["X-Surname"].encode("cp1252").decode("utf8")
        if headers.get("X-Surname")
        else "",
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


def get_user_identifier(headers: dict[str, str | None]) -> str | None:
    """
    Get best possible identifier
    """
    persistent_id: str | None = headers.get("X-Persistent-Id")
    persistent_name: str | None = headers.get("X-Principal-Name")
    edu_person_unique_id: str | None = headers.get("X-Edu-Person-Unique-Id")
    mail: str | None = headers.get("X-Mail")

    if persistent_id and bool(re.match("(.*)!(.*)!(.*)", persistent_id)):
        return persistent_id
    elif persistent_name and str(persistent_name).count("@") == 1:
        return persistent_name
    elif edu_person_unique_id and str(edu_person_unique_id).count("@") == 1:
        return edu_person_unique_id
    elif mail and _check_email(mail):
        return mail
    return None


async def _lama_user_details(headers: Headers) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/user/details"
    async with ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json()


async def _lama_project_create(
    headers: Headers, project_data: dict[str, str]
) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile"
    async with ClientSession() as session:
        async with session.post(url, json=project_data, headers=headers) as resp:
            return await resp.json()


async def _lama_api_create(headers: Headers, project_id: str) -> JSONObject:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/api/create"
    async with ClientSession() as session:
        async with session.post(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json(content_type=None)


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
            return await resp.json(content_type=None)


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
            return await resp.json()


def _get_all_results(qi: QueryIteration) -> dict[int, Any]:
    """
    Get results from all parents -- reconstruct results from just latest batch
    """
    job: Job | SQLJob | str = qi.previous
    connection: RedisConnection = qi.app["redis"]
    out: dict[int, Any] = {}
    if isinstance(job, str):
        job = Job.fetch(job, connection=connection)

    # base = Job.fetch(job.kwargs["base"], connection=connection)
    # latest = Job.fetch(base.meta["latest_sentences"], connection=connection)
    # latest_sents = base.meta["_sentences"]
    # out = _union_results(out, latest_sents)

    while True:
        meta = job.kwargs.get("meta_json")
        batch, _ = _add_results(
            job.result, 0, True, False, False, 0, meta=meta, is_vian=qi.is_vian
        )
        out = _union_results(out, batch)
        parent = job.kwargs.get("parent", None)
        if not parent:
            break
        job = Job.fetch(parent, connection=connection)
    return out


def _get_kwics(result: dict) -> set[int]:
    """
    Helper to get set of kwic ids
    """
    itt = result.get("result_sets", result)
    kwics = [i for i, r in enumerate(itt, start=1) if r.get("type") == "plain"]
    return set(kwics)


def _add_results(
    result: list[tuple],
    so_far: int,
    unlimited: bool,
    offset: int | None,
    restart: bool | int,
    total_requested: int,
    kwic: bool = False,
    is_vian: bool = False,
    sents: list[tuple[str | UUID | int, int, list[Sequence[Any]]]] | None = None,
    meta: dict[str, list[JSONObject]] | None = None,
) -> tuple[dict[int, Any], int]:
    """
    todo: check limits here?
    """
    bundle: dict[int, Any] = {}
    counts: defaultdict[int, int] = defaultdict(int)
    if meta:
        rs = meta["result_sets"]
    else:
        rs = next(i for i in result if not int(i[0]))[1]["result_sets"]

    res_objs = [i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"]
    kwics = set(res_objs)
    n_skipped: Counter[int] = Counter()

    if meta:
        bundle[0] = meta

    if sents:
        bundle[-1] = {}
        for sent in sents:
            bundle[-1][str(sent[0])] = [sent[1], sent[2]]

    for x, line in enumerate(result):
        key = int(line[0])
        rest: list[Any] = line[1]
        if not key:
            bundle[key] = rest
            continue

        if key not in bundle:
            if kwic and key in kwics:
                bundle[key] = []
            elif not kwic and key not in kwics:
                bundle[key] = []

        if key in kwics and not kwic:
            counts[key] += 1
            continue
        elif key not in kwics and kwic:
            continue
        elif key not in kwics and not kwic:
            if key not in bundle:
                bundle[key] = [rest]
            else:
                bundle[key].append(rest)
            counts[key] += 1
            continue

        # doing kwics and this is a kwic line
        if not unlimited and offset and n_skipped[key] < offset:
            n_skipped[key] += 1
            continue
        if restart is not False and n_skipped[key] < restart:
            n_skipped[key] += 1
            continue
        if not unlimited and so_far + len(bundle.get(key, [])) >= total_requested:
            continue
        if is_vian is True:
            tok_ids = rest[1:-4]
            seg_id = rest[0]
            extras = rest[-4:]
            rest = [seg_id, tok_ids, extras]
        else:
            rest = [rest[0], rest[1:]]
        bundle[key].append(rest)
        counts[key] += 1

    for k in kwics:
        if k not in bundle:
            continue
        if len(bundle[k]) > total_requested:
            bundle[k] = bundle[k][:total_requested]

    return bundle, counts[list(kwics)[0]]


def _union_results(so_far: dict[int, Any], incoming: dict[int, Any]) -> dict[int, Any]:
    """
    Join two results objects
    """
    for k, v in incoming.items():
        if not k:
            if k in so_far:
                continue
            else:
                so_far[k] = v
                continue
        elif k == -1:
            if k not in so_far:
                so_far[k] = v
                continue
            else:
                so_far[k].update(v)
        elif k not in so_far:
            so_far[k] = []
        if isinstance(so_far[k], list):
            so_far[k] += v
    return so_far


async def handle_timeout(exc: Exception, request: web.Request) -> None:
    """
    If a job dies due to TTL, we send this...
    """
    try:
        request_data = await request.json()
    except json.decoder.JSONDecodeError:
        return None
    user = request_data["user"]
    room = request_data["room"]
    job = str(exc).split("rq:job:")[-1]
    jso = {
        "user": user,
        "room": room,
        "error": str(exc),
        "status": "timeout",
        "job": job,
        "action": "timeout",
    }
    logging.warning(f"RQ job timeout: {job}", extra=jso)
    connection = request.app["redis"]
    connection.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return None


async def handle_lama_error(exc: Exception, request: web.Request) -> None:
    """
    If we get a connectionerror when trying to reach lama...
    """
    request_data: JSONObject
    try:
        request_data = await request.json()
    except json.decoder.JSONDecodeError:
        request_data = {}
    user = cast(str, request_data.get("user", ""))
    room = cast(str | None, request_data.get("room", None))
    if user:
        jso = {
            "user": user,
            "room": room,
            "error": str(exc),
            "status": "unregistered",
            "action": "unregistered",
        }
        logging.warning(f"Unregistered user/no lama: {user}/{room}", extra=jso)
        connection = request.app["redis"]
        connection.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
        return None


def _get_status(n_results: int, tot_req: int, **kwargs) -> str:
    """
    Is a query finished, or do we need to do another iteration?
    """
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    if tot_req in {-1, False, None}:
        return "partial"
    if n_results >= tot_req:
        return "satisfied"
    return "partial"


async def sem_coro(semaphore: asyncio.Semaphore, coro: Awaitable[Any]):
    """
    Stop too many tasks from running at once
    """
    async with semaphore:
        return await coro


async def gather(n: int, tasks: list[Coroutine], name: str | None = None) -> list[Any]:
    """
    A replacement for asyncio.gather that runs a maximum of n tasks at once.
    If any task errors, we cancel all tasks in the group that share the same name
    """
    if n > 0:
        semaphore = asyncio.Semaphore(n)
        tsks = [asyncio.create_task(sem_coro(semaphore, c), name=name) for c in tasks]
    else:
        tsks = [asyncio.create_task(c, name=name) for c in tasks]
    try:
        return await asyncio.gather(*tsks)
    except BaseException as err:
        print(f"Error while gathering tasks: {str(err)}. Cancelling others...")
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


async def push_msg(
    sockets: Websockets,
    session_id: str,
    msg: JSONObject,
    skip: tuple[str, str] | None = None,
    just: tuple[str, str] | None = None,
) -> None:
    """
    Send JSON websocket message to one or more users
    """
    sent_to = set()
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
                await conn.send_json(msg)
            except ConnectionResetError:
                print(f"Connection reset: {room}/{user_id}")
                pass
            sent_to.add((room, user_id))


def _filter_corpora(
    config: Config,
    is_vian: bool,
    user_data: JSONObject | None,
    get_all: bool = False,
) -> Config:

    ids: set[str] = set()
    if isinstance(user_data, dict):
        subs = cast(dict, user_data.get("subscription", {}))
        sub = cast(list[dict[str, Any]], subs.get("subscriptions", []))
        for s in sub:
            ids.add(s["id"])
        for proj in cast(list[dict], user_data.get("publicProfiles", [])):
            ids.add(proj["id"])

    corpora: dict[str, CorpusConfig] = {}
    for corpus_id, conf in config.items():
        idx = str(corpus_id)
        if idx == "-1":
            corpora[idx] = conf
            continue
        allowed: list[str] = cast(list[str], conf.get("projects", []))
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
    ) = tup
    ver = str(current_version)
    corpus_template = cast(CorpusTemplate, template)
    if not enabled:
        print(f"Corpus disabled: {name}={corpus_id}")
        # disabled.append((name, corpus_id))
        # continue

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
    }

    together = {**corpus_template, **rest}
    return cast(CorpusConfig, together)


def _make_sent_query(
    query: str,
    associated: str | list[str],
    current_batch: Batch,
    resuming: bool,
) -> tuple[str, list[str]]:
    """
    Helper to format the query to retrieve sentences: add sent ids
    """
    conn = get_current_connection()
    if isinstance(associated, list):
        associated = associated[-1]
    if associated is None:
        return ""
    job = Job.fetch(associated, connection=conn)
    hit_limit = job.meta.get("hit_limit")
    if job.get_status(refresh=True) in ("stopped", "canceled"):
        raise Interrupted()
    if job.result is None:
        raise Interrupted()
    if not job.result:
        return "", []
    prev_results = job.result
    # so we don't double count on resuming
    if resuming:
        start_at = job.meta.get("start_at", 0)
    else:
        start_at = 0

    seg_ids = set()
    result_sets = job.kwargs["meta_json"]
    kwics = _get_kwics(result_sets)
    counts: Counter[int] = Counter()

    for res in prev_results:
        key = int(res[0])
        rest = res[1]
        if key in kwics:
            counts[key] += 1
            if start_at and counts[key] < start_at:
                continue
            elif hit_limit is not False and counts[key] > hit_limit:
                continue
            seg_ids.add(str(rest[0]))

    form = ", ".join(sorted(seg_ids))
    query = query.format(schema=current_batch[1], table=current_batch[2], allowed=form)

    return query, list(sorted(seg_ids))


@final
class WorkingParser(HiredisParser):
    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)

    def on_connect(self, *args, **kwargs) -> None:
        return super().on_connect(*args, **kwargs)

    def on_disconnect(self, *args, **kwargs) -> None:
        return super().on_disconnect(*args, **kwargs)

    async def read_from_socket(self) -> Any:
        return await super().read_from_socket()

    async def can_read_destructive(self, *args, **kwargs) -> bool:
        return False


@final
class WorkingPythonParser(PythonParser):
    async def can_read_destructive(self, *args, **kwargs) -> bool:
        return False


ParserClass = WorkingParser if HIREDIS_AVAILABLE else WorkingPythonParser


async def corpora(app_type: str = "all") -> JSONObject:
    """
    Helper to quickly show corpora in app
    """
    from dotenv import load_dotenv

    load_dotenv(override=True)

    headers: JSONObject = {}
    jso = {"appType": app_type, "all": True}

    url = f"http://localhost:{os.environ['AIO_PORT']}/corpora"
    async with ClientSession() as session:
        async with session.post(url, headers=headers, json=jso) as resp:
            return await resp.json()

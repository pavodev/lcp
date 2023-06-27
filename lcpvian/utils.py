from __future__ import annotations

import asyncio
import json
import logging
import operator
import os
import re
import traceback

from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence

from datetime import date, datetime

from typing import Any, cast, final, Literal, TypeAlias

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
from .typed import (
    Batch,
    Config,
    Headers,
    ResultSents,
    JSON,
    JSONObject,
    MainCorpus,
    QueryMeta,
    Results,
    RawSent,
    RunScript,
    Websockets,
)
from .worker import SQLJob

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


OPS = {
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "==": operator.eq,
    "<>": operator.ne,
    "!=": operator.ne,
    ">": operator.ge,
    ">=": operator.gt,
}


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
        async with session.post(url, json=project_data, headers=headers) as resp:
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


def _format_kwics(
    result: list,
    meta_json: QueryMeta,
    sents: list,
    total: int,
    is_vian: bool = False,
) -> dict[int, Any]:

    sen: ResultSents = {}
    out: Results = {0: meta_json, -1: sen}
    first_list: int | None = None
    rs = meta_json["result_sets"]
    kwics = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"])
    # counts: defaultdict[int, int] = defaultdict(int)

    for sent in sents:
        add_to = cast(ResultSents, out[-1])
        add_to[str(sent[0])] = [sent[1], sent[2]]

    for line in result:
        key = int(line[0])
        rest = line[1]
        if key not in kwics:
            continue
        if key not in out:
            out[key] = []
        if is_vian and key in kwics:
            first_list = _first_list(first_list, rest)
            rest = list(_format_vian(rest, first_list))
        elif key in kwics:
            rest = [rest[0], rest[1:]]

        bit = cast(list, out[key])
        bit.append(rest)
        # counts[key] += 1

    return out


def _first_list(first_list: int | None, rest: list) -> int:
    """
    Determine the first list item in a vian kwic item
    """
    if first_list is not None:
        return first_list
    return next(
        (i for i, x in enumerate(rest) if isinstance(x, (list, tuple))),
        len(rest),
    )


def _aggregate_results(
    result: list,
    existing: Results,
    meta_json: QueryMeta,
    post_processes: dict[int, Any],
    total_requested: int,
) -> tuple[Results, Results, int]:
    """
    Combine non-kwic results for storing and for sending to frontend
    """
    # all_results = {0: meta_json}
    results_to_send = {0: meta_json}
    n_results = 0
    rs = meta_json["result_sets"]
    kwics = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"])
    freqs = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "analysis"])
    counts: defaultdict[int, int] = defaultdict(int)

    for line in result:
        key = int(line[0])
        rest: list[Any] = line[1]
        if key in kwics:
            counts[key] += 1
            continue
        if key not in existing:
            existing[key] = []
        if key not in freqs:
            existing[key].append(rest)
            continue
        body = rest[:-1]
        total_this_batch = rest[-1]
        preexist = sum(i[-1] for i in existing[key] if i[:-1] == body)
        body.append(preexist + total_this_batch)
        existing[key] = [i for i in existing[key] if i[:-1] != body]
        existing[key].append(body)

    results_to_send = _apply_filters(existing, post_processes)
    n_results = list(counts.values())[0] if counts else -1

    return existing, results_to_send, n_results


def _get_kwics(result: dict[str, list[dict[str, Any]]]) -> set[int]:
    """
    Helper to get set of kwic ids
    """
    itt = cast(list[dict[str, Any]], result.get("result_sets", result))
    kwics = [i for i, r in enumerate(itt, start=1) if r.get("type") == "plain"]
    return set(kwics)


def _format_vian(
    rest: Sequence, first_list: int
) -> tuple[int | str, list[int], int | str, str | None, str | None, list[list[int]]]:
    """
    Little helper to build VIAN kwic sentence data
    """
    seg_id = cast(str | int, rest[0])
    tok_ids = cast(list[int], rest[1 : first_list - 3])
    gesture = cast(str | None, rest[first_list - 2])
    doc_id = cast(int | str, rest[first_list - 3])
    agent_name = cast(str | None, rest[first_list - 1])
    frame_ranges = cast(list[list[int]], rest[first_list:])
    out = (seg_id, tok_ids, doc_id, gesture, agent_name, frame_ranges)
    return out


def _make_filters(
    post: dict[int, list[dict[str, Any]]]
) -> dict[int, list[tuple[str, str, str | int | float]]]:
    """
    Because we iterate over them a lot, turn the filters object into something
    as performant as possible
    """
    out = {}
    for idx, filters in post.items():
        fixed: list[tuple[str, str, str | int | float]] = []
        for filt in filters:
            name, comp = cast(tuple[str, str], list(filt.items())[0])
            if name != "comparison":
                raise ValueError("expected comparion")

            bits: Sequence[str | int | float] = comp.split()
            last_bit = cast(str, bits[-1])
            body = bits[:-1]
            assert isinstance(body, list)
            if last_bit.isnumeric():
                body.append(int(last_bit))
            elif last_bit.replace(".", "").isnumeric():
                body.append(float(last_bit))
            else:
                body = bits
            made = cast(tuple[str, str, int | str | float], tuple(body))
            fixed.append(made)
        out[idx] = fixed
    return out


def _apply_filters(results_so_far: Results, post_processes: dict[int, Any]) -> Results:
    """
    Take the unioned results and apply any post process functions
    """
    if not post_processes:
        return results_so_far
    out: Results = {}
    post = _make_filters(post_processes)
    for k, v in results_so_far.items():
        for key, filters in post.items():
            if not filters:
                continue
            if int(k) < 1:
                continue
            if int(k) != int(key):
                continue
            for name, op, num in filters:
                v = _apply_filter(cast(list, v), name, op, num)
        out[k] = v
    return out


def _apply_filter(result: list, name: str, op: str, num: int | str | float) -> list:
    """
    Apply a single filter to a group of results, returning only those that match
    """
    out: list = []
    for r in result:
        total = r[-1]
        res = OPS[op](total, num)
        if res and r not in out:
            out.append(r)
    return out


def _fix_freq(v: list[list]) -> list[list]:
    """
    Sum frequency objects and remove duplicate
    """
    fixed = []
    for r in v:
        body = r[:-1]
        total = sum(x[-1] for x in v if x[:-1] == body)
        body.append(total)
        if body not in fixed:
            fixed.append(body)
    return fixed


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
    print(msg)
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


def _get_status(n_results: int, tot_req: int, **kwargs: Batch | list[Batch]) -> str:
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


async def push_msg(
    sockets: Websockets,
    session_id: str,
    msg: JSONObject,
    skip: tuple[str | None, str] | None = None,
    just: tuple[str | None, str] | None = None,
) -> None:
    """
    Send JSON websocket message to one or more users
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


def _get_sent_ids(associated: str | list[str]) -> list[int] | list[str]:
    """
    Helper to format the query to retrieve sentences: add sent ids
    """
    out: list[int] = []
    conn = get_current_connection()
    if isinstance(associated, list):
        associated = associated[-1]
    if associated is None:
        return []
    job = Job.fetch(associated, connection=conn)
    if job.get_status(refresh=True) in ("stopped", "canceled"):
        raise Interrupted()
    if job.result is None:
        raise Interrupted()
    if not job.result:
        return out
    prev_results = job.result

    seg_ids = set()
    result_sets = job.kwargs["meta_json"]
    kwics = _get_kwics(result_sets)
    counts: Counter[int] = Counter()

    for res in prev_results:
        key = int(res[0])
        rest = res[1]
        if key in kwics:
            counts[key] += 1
            seg_ids.add(rest[0])

    return list(sorted(seg_ids))


@final
class WorkingParser(HiredisParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return super().__init__(*args, **kwargs)

    def on_connect(self, *args: Any, **kwargs: Any) -> None:
        super().on_connect(*args, **kwargs)
        return None

    def on_disconnect(self, *args: Any, **kwargs: Any) -> None:
        super().on_disconnect(*args, **kwargs)
        return None

    async def read_from_socket(self) -> Literal[True]:
        return await super().read_from_socket()

    async def can_read_destructive(self, *args: Any, **kwargs: Any) -> bool:
        return False


@final
class WorkingPythonParser(PythonParser):
    async def can_read_destructive(self, *args: Any, **kwargs: Any) -> bool:
        return False


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


ParserClass = WorkingParser if HIREDIS_AVAILABLE else WorkingPythonParser

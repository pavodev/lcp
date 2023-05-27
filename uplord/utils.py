from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from collections import Counter, defaultdict

from datetime import date, datetime

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    cast,
    List,
    Mapping,
    Set,
    Coroutine,
    Tuple,
    final,
    Sequence,
    DefaultDict,
    Counter as CounterType,
)

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

from .configure import CorpusTemplate, CorpusConfig
from .qi import QueryIteration, BATCH_TYPE
from .worker import SQLJob

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


# tuple is in json type because we use it for batches
JSON_TYPE = List | Dict | Tuple | str | int | float | bool | None

JSON_DICT_TYPE = Dict[str, JSON_TYPE]

# an entry in main.corpus
MAINCORPUS_TYPE = Tuple[
    int,
    str,
    str | int | float,
    Any,
    str | None,
    Dict[str, JSON_TYPE],
    str,
    Dict[str, int] | None,  # todo: remove none when tangram fixed
    Dict[str, JSON_TYPE] | None,  # todo: remove none when tangram fixed
    bool,
]

WEBSOCKETS_TYPE = DefaultDict[str, Set[Tuple[web.WebSocketResponse, str]]]

CONFIG_TYPE = Dict[str, Dict[str, JSON_TYPE]]


class Interrupted(Exception):
    """
    Used when a user interrupts a query from frontend
    """

    pass


class CustomEncoder(json.JSONEncoder):
    """
    UUID and time to string
    """

    def default(self, obj: Any) -> None | str | int | float | bool | Dict | List:
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


def _extract_lama_headers(headers: Mapping) -> Dict[str, str]:
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


def get_user_identifier(headers: Dict[str, str | None]) -> str | None:
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


async def _lama_user_details(headers: Mapping[str, JSON_TYPE]) -> Dict[str, JSON_TYPE]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/user/details"
    async with ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json()


async def _lama_project_create(
    headers: Mapping[str, JSON_TYPE], project_data: Dict[str, str]
) -> Dict[str, JSON_TYPE]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile"
    async with ClientSession() as session:
        async with session.post(url, json=project_data, headers=headers) as resp:
            return await resp.json()


async def _lama_api_create(
    headers: Mapping[str, JSON_TYPE], project_id: str
) -> Dict[str, JSON_TYPE]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/{project_id}/api/create"
    async with ClientSession() as session:
        async with session.post(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json(content_type=None)


async def _lama_api_revoke(
    headers: Mapping[str, JSON_TYPE], project_id: str, apikey_id: str
) -> Dict[str, JSON_TYPE]:
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


async def _lama_check_api_key(headers: Mapping[str, JSON_TYPE]) -> Dict[str, JSON_TYPE]:
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


def _get_all_results(qi: QueryIteration) -> Dict[int, Any]:
    """
    Get results from all parents -- reconstruct results from just latest batch
    """
    job: Job | SQLJob | str = qi.previous
    connection: RedisConnection = qi.app["redis"]
    out: Dict[int, Any] = {}
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


def _get_kwics(result: Dict) -> Set[int]:
    """
    Helper to get set of kwic ids
    """
    itt = result.get("result_sets", result)
    kwics = [i for i, r in enumerate(itt, start=1) if r.get("type") == "plain"]
    return set(kwics)


def _add_results(
    result: List[Tuple],
    so_far: int,
    unlimited: bool,
    offset: int | None,
    restart: bool | int,
    total_requested: int,
    kwic: bool = False,
    is_vian: bool = False,
    sents: List[Tuple[str | UUID | int, int, List[Sequence[Any]]]] | None = None,
    meta: Dict[str, List[Dict[str, JSON_TYPE]]] | None = None,
) -> Tuple[Dict[int, Any], int]:
    """
    todo: check limits here?
    """
    bundle: Dict[int, Any] = {}
    counts: DefaultDict[int, int] = defaultdict(int)
    if meta:
        rs = meta["result_sets"]
    else:
        rs = next(i for i in result if not int(i[0]))[1]["result_sets"]

    res_objs = [i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"]
    kwics = set(res_objs)
    n_skipped: CounterType[int] = Counter()

    if meta:
        bundle[0] = meta

    if sents:
        bundle[-1] = {}
        for sent in sents:
            bundle[-1][str(sent[0])] = [sent[1], sent[2]]

    for x, line in enumerate(result):
        key = int(line[0])
        rest: List[Any] = line[1]
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


def _union_results(so_far: Dict[int, Any], incoming: Dict[int, Any]) -> Dict[int, Any]:
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
    request_data = await request.json()
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


async def gather(n: int, tasks: List[Coroutine], name: str | None = None) -> List[Any]:
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
    sockets: WEBSOCKETS_TYPE,
    session_id: str,
    msg: Mapping[str, JSON_TYPE],
    skip: Tuple[str, str] | None = None,
    just: Tuple[str, str] | None = None,
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
    config: CONFIG_TYPE,
    is_vian: bool,
    user_data: Dict[str, Any] | None,
    get_all: bool = False,
) -> CONFIG_TYPE:

    ids: Set[str] = set()
    if isinstance(user_data, dict):
        for sub in user_data.get("subscription", {}).get("subscriptions", []):
            ids.add(sub["id"])
        for proj in user_data.get("publicProfiles", []):
            ids.add(proj["id"])

    corpora: Dict[str, Dict[str, JSON_TYPE]] = {}
    for corpus_id, conf in config.items():
        idx = str(corpus_id)
        if idx == "-1":
            corpora[idx] = conf
            continue
        allowed: List[str] = cast(List[str], conf.get("projects", []))
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
    tup: MAINCORPUS_TYPE,
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

    projects: List[str] = corpus_template.get("projects", [])
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
    associated: str | List[str],
    current_batch: BATCH_TYPE,
    resuming: bool,
) -> str:
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
        return ""
    prev_results = job.result
    # so we don't double count on resuming
    if resuming:
        start_at = job.meta.get("start_at", 0)
    else:
        start_at = 0

    seg_ids = set()
    result_sets = job.kwargs["meta_json"]
    kwics = _get_kwics(result_sets)
    counts: CounterType[int] = Counter()

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

    return query.format(schema=current_batch[1], table=current_batch[2], allowed=form)


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


async def corpora(app_type: str = "all") -> Dict[str, Any]:
    """
    Helper to quickly show corpora in app
    """
    from dotenv import load_dotenv

    load_dotenv(override=True)

    headers: Dict[str, Any] = {}
    jso = {"appType": app_type, "all": True}

    url = f"http://localhost:{os.environ['AIO_PORT']}/corpora"
    async with ClientSession() as session:
        async with session.post(url, headers=headers, json=jso) as resp:
            return await resp.json()

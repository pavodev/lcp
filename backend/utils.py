import aiohttp
import asyncio
import json
import jwt
import os
import re

from collections import defaultdict, Counter
from datetime import date, datetime
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Iterable,
    Reversible,
    Tuple,
    Union,
    Sequence,
    Mapping,
    Sized,
    Set,
)
from uuid import UUID

from aiohttp import web
from rq.command import PUBSUB_CHANNEL_TEMPLATE
from rq.connections import Connection
from rq.exceptions import NoSuchJobError
from rq.job import Job


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

    def default(self, obj: Any):
        if isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def ensure_authorised(func: Callable):
    """
    auth decorator, still wip
    """
    return func

    @wraps(func)
    async def deco(request: web.Request, *args, **kwargs):
        headers = await _lama_user_details(getattr(request, "headers", request))

        if "X-Access-Token" in headers:
            token = headers.get("X-Access-Token")
            try:
                decoded = jwt.decode(
                    token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"]
                )
                request.jwt = decoded
            except Exception as err:
                raise err
        if "X-Display-Name" in headers:
            username = headers.get("X-Display-Name")
            request.username = username
        if "X-Mail" in headers:
            username = headers.get("X-Mail")
            request.username = username

        if not request.username:
            raise ValueError("401? No username")

        return func(request, *args, **kwargs)

    return deco


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


def get_user_identifier(headers: Dict[str, Any]) -> Optional[str]:
    """
    Get best possible identifier
    """
    persistent_id = headers.get("X-Persistent-Id")
    persistent_name = headers.get("X-Principal-Name")
    edu_person_unique_id = headers.get("X-Edu-Person-Unique-Id")
    mail = headers.get("X-Mail")

    if persistent_id and bool(re.match("(.*)!(.*)!(.*)", persistent_id)):
        return persistent_id
    elif persistent_name and str(persistent_name).count("@") == 1:
        return persistent_name
    elif edu_person_unique_id and str(edu_person_unique_id).count("@") == 1:
        return edu_person_unique_id
    elif mail and _check_email(mail):
        return mail
    return None


async def _lama_user_details(headers: Mapping[str, Any]) -> Dict:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/user/details"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json()


async def _lama_project_create(headers: Mapping[str, Any], project_data: Dict) -> Dict:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/profile"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=project_data, headers=headers) as resp:
            return await resp.json()


async def _lama_api_create(headers: Mapping[str, Any], project_id: str) -> Dict:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/profile/{project_id}/api/create"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json(content_type=None)


async def _lama_api_revoke(
    headers: Mapping[str, Any], project_id: str, apikey_id: str
) -> Dict:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/profile/{project_id}/api/{apikey_id}/revoke"
    data = {"comment": "Revoked by user"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, headers=_extract_lama_headers(headers), json=data
        ) as resp:
            return await resp.json(content_type=None)


async def _lama_check_api_key(headers) -> Dict:
    url = f"{os.environ['LAMA_API_URL']}/profile/api/check"
    key = headers["X-API-Key"]
    secret = headers["X-API-Secret"]
    api_headers = {"X-API-Key": key, "X-API-Secret": secret}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=api_headers) as resp:
            return await resp.json()


def _get_all_results(job: Union[Job, str], connection: Connection) -> Dict[int, Any]:
    """
    Get results from all parents -- reconstruct results from just latest batch
    """
    out: Dict[int, Any] = {}
    if isinstance(job, str):
        job = Job.fetch(job, connection=connection)

    # base = Job.fetch(job.kwargs["base"], connection=connection)
    # latest = Job.fetch(base.meta["latest_sentences"], connection=connection)
    # latest_sents = base.meta["_sentences"]
    # out = _union_results(out, latest_sents)

    while True:
        batch, _ = _add_results(job.result, 0, True, False, False, 0)
        out = _union_results(out, batch)
        parent = job.kwargs.get("parent", None)
        if not parent:
            break
        job = Job.fetch(parent, connection=connection)
    return out


def _get_kwics(result):
    """
    Helper to get set of kwic ids
    """
    if isinstance(result, dict):
        itt = result.get("result_sets", result)
        kwics = [i for i, r in enumerate(itt, start=1) if r.get("type") == "plain"]
        return set(kwics)
    for line in result:
        if not int(line[0]):
            res = line[1]["result_sets"]
            enum = enumerate(res, start=1)
            kwics = [i for i, r in enum if r.get("type") == "plain"]
            return set(kwics)
    return set()


def _add_results(
    result: List[List],
    so_far: int,
    unlimited: bool,
    offset: Optional[int],
    restart: Union[bool, int],
    total_requested: int,
    kwic: bool = False,
    sents: Optional[List[Tuple[str, int, List[Any]]]] = None,
) -> Tuple[Dict[int, Any], int]:
    """
    todo: check limits here?
    """
    bundle: Dict[int, Any] = {}
    counts: Dict[int, int] = defaultdict(int)
    rs = next(i for i in result if not int(i[0]))[1]["result_sets"]
    res_objs = [i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"]
    kwics = set(res_objs)
    n_skipped: Dict[int, int] = Counter()

    if sents:
        bundle[-1] = {}
        for sent in sents:
            bundle[-1][str(sent[0])] = [sent[1], sent[2]]

    for x, line in enumerate(result):
        key = int(line[0])
        rest = line[1]
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
        bundle[key].append(rest)
        counts[key] += 1

    for k in kwics:
        if k not in bundle:
            continue
        if len(bundle[k]) > total_requested:
            bundle[k] = bundle[k][:total_requested]

    return bundle, counts[list(kwics)[0]]


def _union_results(
    so_far: Dict[int, Any],
    incoming: Dict[int, Any],
) -> Dict[int, Any]:
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
    connection = request.app["redis"]
    connection.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _determine_language(batch: str) -> Optional[str]:
    """
    Helper to find language from batch
    """
    batch = batch.rstrip("0123456789")
    if batch.endswith("rest"):
        batch = batch[:-4]
    for lan in ["de", "en", "fr"]:
        if batch.endswith(f"_{lan}"):
            return lan
    return None


async def gather(
    n, *tasks: Tuple[asyncio.Task], name: Optional[str] = None
) -> Iterable[Any]:
    """
    A replacement for asyncio.gather that runs a maximum of n tasks at once.
    If any task errors, we cancel all tasks in the group that share the same name
    """
    if n > 0:
        semaphore = asyncio.Semaphore(n)

        async def sem_coro(coro: Awaitable[Any]):
            async with semaphore:
                return await coro

        group = asyncio.gather(
            *(asyncio.create_task(sem_coro(c), name=name) for c in tasks)
        )
    else:
        group = asyncio.gather(*(asyncio.create_task(c) for c in tasks))
    try:
        return await group
    except (BaseException) as err:
        print(f"Error while gathering tasks: {str(err)}. Cancelling others...")
        tasks = asyncio.all_tasks()
        current = asyncio.current_task()
        try:
            current.cancel()
        except:
            pass
        name = current.get_name()
        tasks.remove(current)
        for task in tasks:
            if name and task.get_name() == name:
                task.cancel()
        raise err

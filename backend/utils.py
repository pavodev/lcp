import aiohttp
import jwt
import os
import re

from aiohttp import web
from functools import wraps
from rq.connections import Connection
from rq.exceptions import NoSuchJobError
from rq.job import Job
from typing import Any, Dict, List, Optional, Tuple, Union

from datetime import date, datetime

from rq.command import PUBSUB_CHANNEL_TEMPLATE

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"

import json

from uuid import UUID


class Interrupted(Exception):
    """
    Used when a user interrupts a query from frontend
    """

    pass


class CustomEncoder(json.JSONEncoder):
    """
    UUID and time to string
    """

    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def ensure_authorised(func):
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


def _extract_lama_headers(headers: Dict[str, Any]) -> Dict[str, Optional[str]]:
    retval = {
        "X-API-Key": os.getenv("LAMA_API_KEY"),
        "X-Remote-User": headers.get("X-Remote-User"),
        "X-Display-Name": headers.get("X-Display-Name").encode("cp1252").decode("utf8")
        if headers.get("X-Display-Name")
        else "",
        "X-Edu-Person-Unique-Id": headers.get("X-Edu-Person-Unique-Id"),
        "X-Home-Organization": headers.get("X-Home-Organization"),
        "X-Schac-Home-Organization": headers.get("X-Schac-Home-Organization"),
        "X-Persistent-Id": headers.get("X-Persistent-Id"),
        "X-Given-Name": headers.get("X-Given-Name").encode("cp1252").decode("utf8")
        if headers.get("X-Given-Name")
        else "",
        "X-Surname": headers.get("X-Surname").encode("cp1252").decode("utf8")
        if headers.get("X-Surname")
        else "",
        "X-Principal-Name": headers.get("X-Principal-Name"),
        "X-Mail": headers.get("X-Mail"),
        "X-Shib-Identity-Provider": headers.get("X-Shib-Identity-Provider"),
    }
    return {k: v for k, v in retval.items() if v}


def _check_email(email: str) -> bool:
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return bool(re.fullmatch(regex, email))


def get_user_identifier(headers: Dict[str, Any]) -> Optional[str]:
    persistent_id = headers.get("X-Persistent-Id")
    persistent_name = headers.get("X-Principal-Name")
    edu_person_unique_id = headers.get("X-Edu-Person-Unique-Id")
    mail = headers.get("X-Mail")
    retval = None

    if persistent_id and bool(re.match("(.*)!(.*)!(.*)", persistent_id)):
        retval = persistent_id
    elif persistent_name and str(persistent_name).count("@") == 1:
        retval = persistent_name
    elif edu_person_unique_id and str(edu_person_unique_id).count("@") == 1:
        retval = edu_person_unique_id
    elif mail and _check_email(mail):
        retval = mail
    return retval


async def _lama_user_details(headers: Dict[str, Any]) -> Dict:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/user/details"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json()


def _get_all_results(job: Union[Job, str], connection: Connection) -> List[List[Tuple]]:
    """
    Get results from all parents -- reconstruct results from just latest batch
    """
    out = []
    if isinstance(job, str):
        job = Job.fetch(job, connection=connection)
    while True:
        batch = _add_results(job.result, 0, True, False, False, 0)
        out += list(reversed(batch))
        parent = job.kwargs.get("parent", None)
        if not parent:
            break
        job = Job.fetch(parent, connection=connection)
    return list(reversed(out))


def _add_results(
    result: List[List],
    so_far: int,
    unlimited: bool,
    offset: Optional[int],
    restart: Union[bool, int],
    total_requested: int,
) -> List[Tuple]:
    """
    Helper function, run inside callback
    """
    out = []
    for n, res in enumerate(result):
        if not unlimited and offset and n < offset:
            continue
        if restart is not False and n + 1 < restart:
            continue
        # fix: move sent_id to own column
        fixed = []
        sent_id = res[0][0]
        tok_ids = res[0][1:]
        fixed = ((sent_id,), tuple(tok_ids), res[1], res[2])
        # end fix
        out.append(fixed)
        if not unlimited and so_far + len(out) >= total_requested:
            break
    return out


def _push_stats(previous: str, connection: Connection) -> Dict[str, Any]:
    """
    Send statistics to the websocket
    """
    depended = Job.fetch(previous, connection=connection)
    base = depended.kwargs.get("base")
    basejob = Job.fetch(base, connection=connection) if base else depended

    jso = {
        "result": basejob.meta["_stats"],
        "status": depended.meta["_status"],
        "action": "stats",
        "user": basejob.kwargs["user"],
        "room": basejob.kwargs["room"],
    }
    connection.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))
    return {
        "stats": True,
        "stats_job": basejob.meta.get("latest_stats", None),
        "status": "faked",
        "job": previous,
    }


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

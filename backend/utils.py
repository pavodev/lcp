from functools import wraps
import os
import re

import aiohttp
import jwt

from datetime import date, datetime


import json
from uuid import UUID


class CustomEncoder(json.JSONEncoder):
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
    async def deco(request, *args, **kwargs):
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


def _extract_lama_headers(headers):
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
    return True if (re.fullmatch(regex, email)) else False


def get_user_identifier(headers):
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


async def _lama_user_details(headers: dict) -> dict:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/user/details"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json()

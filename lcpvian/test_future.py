import asyncio
import json

from aiohttp import web
from redis import Redis as RedisConnection
from rq import Callback
from rq.job import Job
from typing import cast
from uuid import uuid4

from .callbacks import _general_failure
from .jobfuncs import _db_query
from .utils import _publish_msg, CustomEncoder


def _mycb(
    job: Job,
    connection: RedisConnection,
    result: dict | None = None,
) -> None:
    msg_id = cast(dict, job.kwargs).get("msg_id", "")
    jso = json.dumps(result, cls=CustomEncoder)
    return _publish_msg(connection, jso, msg_id)


async def test_future_async(app):
    new_future = asyncio.Future()
    msg_id = str(uuid4())
    app["futures"][msg_id] = new_future
    query = "SELECT * FROM bnc1.tokenrest LIMIT 1;"
    app["background"].enqueue(
        _db_query,
        on_success=Callback(_mycb, 5000),
        on_failure=Callback(_general_failure, 5000),
        args=(query,),
        kwargs={"msg_id": msg_id},
    )
    res = await new_future
    print("Done", res)


async def test_future(request: web.Request) -> web.Response:
    asyncio.create_task(test_future_async(request.app))
    return web.json_response({"status": 200})

import json
import os

from aiohttp import web
from asyncio import sleep
from collections.abc import Callable
from typing import cast
from rq.connections import get_current_connection
from rq.job import Job
from uuid import uuid4

from .sock import pubsub_callback
from .typed import JSONObject
from .utils import CustomEncoder, ensure_authorised, PUBSUB_CHANNEL


CHUNKS = 500000 # SIZE OF CHUNKS TO STREAM, IN # OF CHARACTERS


async def fetch_and_process_results(
    uuid: str,
    job_ids: list[str]
) -> None:
    conn = get_current_connection()
    jobs: list[Job] = [Job.fetch(jid, connection=conn) for jid in job_ids]

    buffer: str = ""

    for j in jobs:
        for line in j.result:

            if len(f"{buffer}{line}\n") > CHUNKS:
                dump: str = json.dumps({
                    "action": "callback",
                    "uuid": uuid,
                    "message": buffer
                }, cls=CustomEncoder)
                conn.publish(PUBSUB_CHANNEL, dump)
                buffer = ""

            buffer += f"{line}\n"

    if buffer:
        dump: str = json.dumps({
            "action": "callback",
            "uuid": uuid,
            "message": buffer
        }, cls=CustomEncoder)
        conn.publish(PUBSUB_CHANNEL, dump)

    dump: str = json.dumps({
        "action": "callback",
        "uuid": uuid,
        "complete": True
    }, cls=CustomEncoder)
    conn.publish(PUBSUB_CHANNEL, dump)

    return None


async def _process_callback(response: web.StreamResponse, json_payload: str, uuid: str, request: web.Request) -> None:

    payload: JSONObject = json.loads(json_payload)

    if payload.get("complete"):
        request.app["pubsub_callbacks"].pop(uuid)
    else:
        await response.write(str(payload.get("message", "")).encode("utf-8"))

    return None


@ensure_authorised
async def export(request: web.Request) -> web.StreamResponse:
    """
    Fetch arbitrary JSON data from redis
    """
    hashed: str = request.match_info["hashed"]
    
    conn = request.app["redis"]
    job: Job = Job.fetch(hashed, connection=conn)
    finished_jobs = [
        *[Job.fetch(jid, connection=conn) for jid in request.app["query"].finished_job_registry.get_job_ids()],
        *[Job.fetch(jid, connection=conn) for jid in request.app["background"].finished_job_registry.get_job_ids()],
    ]
    associated_jobs_ids = [j.id for j in finished_jobs if j.kwargs.get("first_job") == hashed]
    
    response: web.StreamResponse = web.StreamResponse(
        status=200,
        reason='OK',
        headers={'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename=results.txt'},
    )
    await response.prepare(request)
    
    uuid: str = str(uuid4())
    callback: Callable = lambda payload: (await _process_callback(response, payload, uuid, request) for _ in '_').__anext__()
    pubsub_callback(uuid, callback, request.app)

    request.app["background"].enqueue(
        fetch_and_process_results,
        args=(uuid,[job.id, *associated_jobs_ids])
    )

    while request.app.get("pubsub_callbacks", {}).get(uuid):
        await sleep(0)
    
    await response.write_eof()
    return response
    
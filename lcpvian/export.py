# TODO: detect closed stream and stop job

from aiohttp import web
from asyncio import sleep
from rq.job import Job
from .utils import ensure_authorised


CHUNKS = 1000000 # SIZE OF CHUNKS TO STREAM, IN # OF CHARACTERS

async def stream_results(jobs: list[Job], resp: web.StreamResponse):
    buffer: str = ""
    for j in jobs:
        for line in j.result:

            if len(f"{buffer}{line}\n") > CHUNKS:
                await resp.write(buffer.encode("utf-8"))
                await sleep(0.01) # Give the machine some time to breathe!
                buffer = ""
            buffer += f"{line}\n"
    if buffer:
        await resp.write(buffer.encode("utf-8"))


@ensure_authorised
async def export(request: web.Request) -> web.StreamResponse:
    """
    Fetch arbitrary JSON data from redis
    """
    hashed: str = request.match_info["hashed"]
    
    response: web.StreamResponse = web.StreamResponse(
        status=200,
        reason='OK',
        headers={'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename=results.txt'},
    )
    await response.prepare(request)
    
    conn = request.app["redis"]
    job: Job = Job.fetch(hashed, connection=conn)
    finished_jobs = [
        *[Job.fetch(jid, connection=conn) for jid in request.app["query"].finished_job_registry.get_job_ids()],
        *[Job.fetch(jid, connection=conn) for jid in request.app["background"].finished_job_registry.get_job_ids()],
    ]
    associated_jobs = [j for j in finished_jobs if j.kwargs.get("first_job") == hashed]

    await stream_results([job, *associated_jobs], response)
    
    await response.write_eof()
    return response
    
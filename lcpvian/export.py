import json

from aiohttp import web
from asyncio import sleep
from typing import cast
from rq.job import Job

from .typed import JSONObject
from .utils import ensure_authorised

@ensure_authorised
async def export(request: web.Request) -> web.Response:
    """
    Fetch arbitrary JSON data from redis
    """
    hashed: str = request.match_info["hashed"]
    response: JSONObject
    
    job = Job.fetch(hashed, connection=request.app["redis"])
    
    finished_jobs = [Job.fetch(jid, connection=request.app["redis"]) for jid in request.app["query"].finished_job_registry.get_job_ids()]
    associated_jobs = [j for j in finished_jobs if j.kwargs.get("first_job") == hashed]
    
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename=results.txt'},
    )
    await response.prepare(request)
    
    for j in [job, *associated_jobs]:
        for line in j.result:
            await response.write(f"{str(line)}\n".encode('utf-8'))
    
    # import pdb; pdb.set_trace()
    await response.write_eof()
    return response
    
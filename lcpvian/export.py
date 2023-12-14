import json

from aiohttp import web
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
    
    print("Job meta", [str(k) for k in job.meta.keys])
    
    kwargs = job.kwargs
    
    room = cast(str, kwargs.get("room", ""))
    user = cast(str, kwargs.get("user", ""))
    
    response = {"action": "export", "user": user, "room": room, "hashed": hashed}
    return web.json_response(response)

import json
import os
from aiohttp import web

from io import BytesIO

from uuid import uuid4


async def _status_check(request, job):
    """
    What to do when user check status on an upload job
    """
    qs = request.app["query_service"]
    job = qs.get(job)
    if not job:
        ret = {"job": job, "status": "failed", "error": "Job not found."}
        return web.json_response(ret)
    status = job.get_status(refresh=True)
    msg = """Please wait: corpus processing in progress..."""
    corpus_id = job.kwargs["corpus_id"]
    if status == "failed":
        print("fail??", job.__dict__)
        msg = (
            "Something has gone wrong. Check your config file and try uploading again."
        )
    elif status == "finished":
        msg = f"""Upload is complete. You should be able to see your corpus in the web app, or query it by its identifier, {corpus_id}"""
    ret = {"job": job.id, "status": status, "info": msg}
    return web.json_response(ret)


async def upload(request):

    url = request.url
    exists = request.rel_url.query.get("job")
    if exists:
        return await _status_check(request, exists)

    gui_mode = request.rel_url.query.get("gui", False)
    username = request.rel_url.query["user"]
    room = request.rel_url.query.get("room", None)

    api_key = request.rel_url.query["key"]
    os.makedirs(os.path.join("uploads", username), exist_ok=True)
    data = await request.multipart()
    size = 0
    corpus_id = uuid4()
    filename = str(corpus_id) + ".vrt"
    path = os.path.join("uploads", username, filename)
    config = None
    # if os.path.isfile(path):
    #     return web.json_response({"status": "failure", "error": "file exists"})
    async for bit in data:
        if bit.name == "file":
            with open(path, "ba") as f:
                while True:
                    chunk = await bit.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
        if bit.name == "config":
            config = path.replace(".vrt", ".json")
            with open(config, "ba") as f:
                while True:
                    chunk = await bit.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

    qs = request.app["query_service"]
    job = qs.upload(path, username, corpus_id, room=room, config=config, gui=gui_mode)
    short_url = str(url).split("?", 1)[0]
    info = f"""Data upload has begun ({size} bytes). If you want to check the status, POST to:
        {short_url}?job={job.id}    
    """
    ret = {
        "status": "started",
        "job": job.id,
        "size": size,
        "corpus_id": str(corpus_id),
        "info": info,
    }

    return web.json_response(ret)


async def upload_status(request):
    api_key = request.rel_url.query["key"]
    corpus_id = request.rel_url.query["corpus_id"]

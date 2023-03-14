import json
import os

from aiohttp import web

from io import BytesIO

from uuid import uuid4


async def _status_check(request: web.Request, job: str) -> web.Response:
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
        msg = (
            "Something has gone wrong. Check your config file and try uploading again."
        )
    elif status == "finished":
        msg = f"""Upload is complete. You should be able to see your corpus in the web app, or query it by its identifier, {corpus_id}"""
    ret = {"job": job.id, "status": status, "info": msg}
    return web.json_response(ret)


async def upload(request: web.Request) -> web.Response:
    """
    Handle upload of data (save files, insert into db)
    """
    url = request.url
    exists = request.rel_url.query.get("job")
    if exists:
        return await _status_check(request, exists)

    gui_mode = request.rel_url.query.get("gui", False)

    # todo: best way to encode user? maybe not needed if api key exists
    username = request.rel_url.query.get("user", "unknown_user")
    room = request.rel_url.query.get("room", None)
    api_key = request.rel_url.query["key"]

    # todo: where will uploads go?
    os.makedirs(os.path.join("uploads", username), exist_ok=True)
    data = await request.multipart()
    size = 0
    corpus_id = uuid4()
    config_name = None
    # if os.path.isfile(path):
    #     return web.json_response({"status": "failure", "error": "file exists"})
    has_file = False
    async for bit in data:
        if bit.name == "file":
            ext = os.path.splitext(bit.filename)[-1]
            filename = str(corpus_id) + ext
            path = os.path.join("uploads", username, filename)
            with open(path, "ba") as f:
                while True:
                    chunk = await bit.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
            if size:
                has_file = True
        if bit.name == "config":
            config_name = os.path.splitext(path)[0] + ".json"
            with open(config_name, "ba") as f:
                while True:
                    chunk = await bit.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

    if not has_file:
        msg = "No file sent?"
        ret = {"status": "failed", "info": msg}
        return web.json_response(ret)

    qs = request.app["query_service"]
    kwa = dict(room=room, config=config_name, gui=gui_mode)
    job = qs.upload(path, username, corpus_id, **kwa)
    short_url = str(url).split("?", 1)[0]
    whole_url = f"{short_url}?job={job.id}"
    info = f"""Data upload has begun ({size} bytes). If you want to check the status, POST to:
        {whole_url}    
    """
    ret = {
        "status": "started",
        "job": job.id,
        "size": size,
        "corpus_id": str(corpus_id),
        "info": info,
        "target": whole_url,
    }

    return web.json_response(ret)

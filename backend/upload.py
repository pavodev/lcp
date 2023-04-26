import json
import os

from aiohttp import web

from io import BytesIO

from typing import Any, Dict, Union
from uuid import uuid4

from .pg_upload import pg_create

VALID_EXTENSIONS = {"vrt", "zip"}


async def _status_check(request: web.Request, job_id: str) -> web.Response:
    """
    What to do when user check status on an upload job
    """
    qs = request.app["query_service"]
    job = qs.get(job_id)
    if not job:
        ret = {"job": job_id, "status": "failed", "error": "Job not found."}
        return web.json_response(ret)
    status = job.get_status(refresh=True)
    msg = """Please wait: corpus processing in progress..."""
    project = job.kwargs["project"]
    if status == "failed":
        msg = (
            "Something has gone wrong. Check your config file and try uploading again."
        )
    elif status == "finished":
        msg = f"""Upload is complete. You should be able to see your corpus in the web app, or query it by its identifier, {project}"""
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

    request_data = await request.json()
    project_id = request_data.get("project")
    if not project_id:
        return web.json_response({"status": "failed"})

    # todo: where will uploads go?
    # os.makedirs(os.path.join("uploads", username), exist_ok=True)
    data = await request.multipart()
    size = 0
    config_name = None
    # if os.path.isfile(path):
    #     return web.json_response({"status": "failure", "error": "file exists"})
    has_file = False
    files = set()
    async for bit in data:
        if isinstance(bit.filename, str):
            ext = os.path.splitext(bit.filename)[-1]
            # filename = str(project) + ext
            path = os.path.join("uploads", project_id, bit.filename)
            with open(path, "ba") as f:
                while True:
                    chunk = await bit.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
                    files.add(path)
            if size:
                has_file = True

    constraints_file = os.path.join("uploads", project_id, "constraints.sql")

    ret: Dict[str, Any] = {}
    if not has_file:
        msg = "No file sent?"
        ret.update({"status": "failed", "info": msg})
        return web.json_response(ret)

    qs = request.app["query_service"]
    kwa = dict(room=room, constraints=constraints_file, gui=gui_mode)
    path = os.path.join("uploads", project_id)
    job = qs.upload(path, username, project_id, **kwa)
    short_url = str(url).split("?", 1)[0]
    whole_url = f"{short_url}?job={job.id}"
    info = f"""Data upload has begun ({size} bytes). If you want to check the status, POST to:
        {whole_url}    
    """
    ret.update(
        {
            "status": "started",
            "job": job.id,
            "size": size,
            "project": str(project_id),
            "info": info,
            "target": whole_url,
        }
    )

    return web.json_response(ret)


async def make_schema(request: web.Request) -> web.Response:
    """
    What happens when a user goes to /create and POSTS JSON
    """
    request_data = await request.json()
    template = request_data["template"]
    try:
        template = json.loads(template)
    except json.JSONDecodeError as err:
        msg = str(err)
        return web.json_response({"status": "failure", "message": msg})
    except Exception as err:
        msg = str(err)
        return web.json_response({"status": "failure", "message": msg})

    create_ddl, constraints_ddl = await pg_create(template)
    uu = str(uuid4())
    directory = os.path.join("uploads", uu)
    if not os.path.isdir("uploads"):
        os.makedirs("uploads")
    os.makedirs(directory)
    with open(os.path.join(directory, "constraints.sql"), "w") as fo:
        fo.write(constraints_ddl)
    with open(os.path.join(directory, "template.json"), "w") as fo:
        json.dump(template, fo)

    job = request.app["query_service"].create(create_ddl, project=uu)
    return web.json_response({"status": "started", "job": job.id, "project": uu})

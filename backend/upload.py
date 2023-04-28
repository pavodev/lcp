import json
import os

from tarfile import TarFile, is_tarfile
from typing import Any, Dict, Union
from uuid import uuid4
from zipfile import ZipFile, is_zipfile


from aiohttp import web
from py7zr import SevenZipFile, is_7zfile

from .pg_upload import pg_create


VALID_EXTENSIONS = ("vrt", "csv")
COMPRESSED_EXTENTIONS = ("zip", "tar", "tar.gz", "tar.xz", "7z")


async def _create_status_check(request: web.Request, job_id: str) -> web.Response:
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
        msg = f"""Template validated successfully"""
    ret = {
        "job": job.id,
        "status": status,
        "info": msg,
        "project": job.kwargs["project"],
    }
    return web.json_response(ret)


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

    # project_id = request_data.get("project")
    project_id = request.rel_url.query.get("project", "unknown_project")
    if not project_id:
        return web.json_response({"status": "failed"})

    data = await request.multipart()
    size = 0
    # if os.path.isfile(path):
    #     return web.json_response({"status": "failure", "error": "file exists"})
    has_file = False
    files = set()
    async for bit in data:
        if isinstance(bit.filename, str):
            if not bit.filename.endswith(VALID_EXTENSIONS + COMPRESSED_EXTENTIONS):
                continue
            to_delete = set()
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
            ziptar = [
                (".zip", is_zipfile, ZipFile, "namelist"),
                (".tar", is_tarfile, TarFile, "getnames"),
                (".tar.gz", is_tarfile, TarFile, "getnames"),
                (".tar.xz", is_tarfile, TarFile, "getnames"),
                (".7z", is_7zfile, SevenZipFile, "getnames"),
            ]
            for ext, check, opener, method in ziptar:
                if path.endswith(ext) and check(path):
                    print(f"Extracting {ext} file: {path}")
                    with opener(path, "r") as compressed:
                        for f in getattr(compressed, method)():
                            if not f.endswith(VALID_EXTENSIONS):
                                continue
                            just_f = os.path.join(
                                "uploads", project_id, os.path.basename(f)
                            )
                            dest = os.path.join("uploads", project_id)
                            print(f"Uncompressing {f} to {dest}")
                            if ext != ".7z":
                                compressed.extract(f, dest)
                            else:
                                compressed.extract(dest, [f])
                            try:
                                os.rename(os.path.join(dest, f), just_f)
                            except Exception as err:
                                print(f"Warning: {err}")
                                pass
                            print("Extracted", dest, f)
                    print(f"Extracting {ext} done!")
                    os.remove(path)  # todo: should we do this now?
                elif path.endswith(ext) and not check(path):
                    print(f"Something wrong with {path}. Ignoring...")
                    size = 0
                    os.remove(path)
                    f = os.path.basename(path)
                    ret = {"status": "failed", "msg": f"Problem uncompressing {f}"}
                    return web.json_response(ret)
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
    exists = request.rel_url.query.get("job")
    if exists:
        return await _create_status_check(request, exists)

    request_data = await request.json()

    template = request_data["template"]

    create_ddl, constraints_ddl, mapping = await pg_create(template)
    uu = str(uuid4())
    directory = os.path.join("uploads", uu)
    if not os.path.isdir("uploads"):
        os.makedirs("uploads")
    os.makedirs(directory)
    with open(os.path.join(directory, "constraints.sql"), "w") as fo:
        fo.write(constraints_ddl)
    with open(os.path.join(directory, "_mapping.json"), "w") as fo:
        json.dump(mapping, fo)
    with open(os.path.join(directory, "template.json"), "w") as fo:
        json.dump(template, fo)

    short_url = str(request.url).split("?", 1)[0]
    job = request.app["query_service"].create(create_ddl, project=uu)
    whole_url = f"{short_url}?job={job.id}"
    return web.json_response(
        {"status": "started", "job": job.id, "project": uu, "target": whole_url}
    )

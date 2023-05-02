import json
import os

from tarfile import TarFile, is_tarfile
from typing import Any, Dict, Optional, Tuple, Union
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
    short_url = str(request.url).split("?", 1)[0]
    whole_url = f"{short_url}?job={job_id}"
    qs = request.app["query_service"]
    job = qs.get(job_id)
    if not job:
        ret = {"job": job_id, "status": "failed", "error": "Job not found."}
        return web.json_response(ret)
    status = job.get_status(refresh=True)
    msg = f"""Please wait: corpus processing in progress..."""
    project = job.kwargs["project"]
    if status == "failed":
        msg = f"Error: {str(job.latest_result().exc_string)}"
    elif status == "finished":
        msg = f"""Template validated successfully"""
    ret = {
        "job": job.id,
        "status": status,
        "info": msg,
        "project": job.kwargs["project"],
        "target": whole_url,
    }
    return web.json_response(ret)


async def _status_check(request: web.Request, job_id: str) -> web.Response:
    """
    What to do when user check status on an upload job
    """
    qs = request.app["query_service"]
    job = qs.get(job_id)
    project = job.kwargs["project"]
    progfile = os.path.join("uploads", project, ".progress.txt")
    progress = _get_progress(progfile)

    if not job:
        ret = {"job": job_id, "status": "failed", "error": "Job not found."}
        return web.json_response(ret)
    status = job.get_status(refresh=True)
    msg = f"""Please wait: corpus processing in progress..."""
    project = job.kwargs["project"]
    if status == "failed":
        msg = f"Error: {str(job.latest_result().exc_string)}"
    elif status == "finished":
        msg = f"""Upload is complete. You should be able to see your corpus in the web app."""
    ret = {
        "job": job.id,
        "status": status,
        "info": msg,
        "project": project,
    }
    if progress:
        ret["progress"] = f"{progress[0]}/{progress[1]}"
    return web.json_response(ret)


def _get_progress(progfile: str) -> Optional[Tuple[int, int]]:
    """
    Attempt to get progress from saved file
    """
    if not os.path.isfile(progfile):
        return None
    with open(progfile, "r") as fo:
        data = fo.read()
    if "\nSetting constraints..." in data:
        return (-2, -2)
    if "\nComputing prepared segments" in data:
        return (-1, -1)
    bits = [
        i.lstrip(":progress:").split()[0].split(":")
        for i in data.splitlines()
        if i.startswith(":progress")
    ]
    if not bits:
        return None
    done_bytes = sum([int(i[-2]) for i in bits])
    total = int(bits[0][-1])
    return (done_bytes, total)
    # progress = round(done_bytes * 100.0 / total, 2)
    # return f"{progress}%"


def _ensure_word0(path: str) -> None:
    """
    In case the user didn't call word.csv word0.csv
    """
    template = os.path.join(path, "_data.json")
    with open(template, "r") as fo:
        data = json.load(fo)
        data = data["template"]
    tok = data["firstClass"]["token"]
    src = os.path.join(path, tok.lower() + ".csv")
    if os.path.isfile(src):
        dest = src.replace(".csv", "0.csv")
        os.rename(src, dest)
        print(f"Moved: {src}->{dest}")


def _correct_doc(path: str) -> None:
    """
    Fix incorrect JSON formatting...
    todo: remove this when fixed upstream
    """
    template = os.path.join(path, "_data.json")
    with open(template, "r") as fo:
        data = json.load(fo)
        data = data["template"]
    doc = data["firstClass"]["document"]
    docpath = os.path.join(path, f"{doc}.csv".lower())
    with open(docpath, "r") as fo:
        data = fo.read()
    data = data.replace("\t'{", "\t{").replace("}'\n", "}\n")
    with open(docpath, "w") as fo:
        fo.write(data)


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
                            if not str(f).endswith(VALID_EXTENSIONS):
                                continue
                            just_f = os.path.join(
                                "uploads", project_id, os.path.basename(str(f))
                            )
                            dest = os.path.join("uploads", project_id)
                            print(f"Uncompressing {f} to {dest}")
                            if ext != ".7z":
                                compressed.extract(f, dest)
                            else:
                                compressed.extract(dest, [f])
                            try:
                                os.rename(os.path.join(dest, str(f)), just_f)
                            except Exception as err:
                                print(f"Warning: {err}")
                                pass
                            print("Extracted", dest, f)
                    print(f"Extracting {ext} done!")
                    os.remove(path)  # todo: should we do this now?
                    print(f"Deleted: {path}")
                elif path.endswith(ext) and not check(path):
                    print(f"Something wrong with {path}. Ignoring...")
                    size = 0
                    os.remove(path)
                    fp = os.path.basename(path)
                    ret = {"status": "failed", "msg": f"Problem uncompressing {fp}"}
                    return web.json_response(ret)
            if size:
                has_file = True

    _ensure_word0(os.path.join("uploads", project_id))
    _correct_doc(os.path.join("uploads", project_id))

    return_data: Dict[str, Union[str, int]] = {}
    if not has_file:
        msg = "No file sent?"
        return_data.update({"status": "failed", "info": msg})
        return web.json_response(return_data)

    qs = request.app["query_service"]
    kwa = dict(room=room, gui=gui_mode)
    path = os.path.join("uploads", project_id)
    print(f"Uploading data to database: {project_id}")
    job = qs.upload(path, username, project_id, **kwa)
    short_url = str(url).split("?", 1)[0]
    whole_url = f"{short_url}?job={job.id}"
    info = f"""Data upload has begun ({size} bytes). If you want to check the status, POST to:
        {whole_url}    
    """
    return_data.update(
        {
            "status": "started",
            "job": job.id,
            "size": size,
            "project": str(project_id),
            "info": info,
            "target": whole_url,
        }
    )

    return web.json_response(return_data)


async def make_schema(request: web.Request) -> web.Response:
    """
    What happens when a user goes to /create and POSTS JSON
    """
    exists = request.rel_url.query.get("job")
    if exists:
        return await _create_status_check(request, exists)

    request_data = await request.json()

    template = request_data["template"]

    pieces = await pg_create(template)
    pieces["template"] = template
    uu = str(uuid4())
    directory = os.path.join("uploads", uu)
    if not os.path.isdir("uploads"):
        os.makedirs("uploads")
    os.makedirs(directory)

    with open(os.path.join(directory, "_data.json"), "w") as fo:
        json.dump(pieces, fo)

    short_url = str(request.url).split("?", 1)[0]
    job = request.app["query_service"].create(pieces["main_create"], project=uu)
    whole_url = f"{short_url}?job={job.id}"
    return web.json_response(
        {"status": "started", "job": job.id, "project": uu, "target": whole_url}
    )

"""
upload.py: /create and /upload endpoints, for creating new db schemata and for
importing data into them. These endpoints can also be polled, which returns
status information about the current task
"""

from __future__ import annotations

import json
import os
import re
import traceback

from collections.abc import Callable
from datetime import datetime, timedelta
from tarfile import TarFile, is_tarfile
from typing import cast
from uuid import uuid4
from zipfile import ZipFile, is_zipfile

from aiohttp import web, BodyPartReader
from py7zr import SevenZipFile, is_7zfile
from rq.job import Job

from .ddl_gen import generate_ddl
from .typed import Headers, JSON
from .utils import (
    _lama_check_api_key,
    _lama_project_create,
    ensure_authorised,
    _lama_user_details,
)


VALID_EXTENSIONS = ("vrt", "csv")
COMPRESSED_EXTENTIONS = ("zip", "tar", "tar.gz", "tar.xz", "7z")


async def _create_status_check(request: web.Request, job_id: str) -> web.Response:
    """
    What to do when user check status on an upload job
    """
    short_url = str(request.url).split("?", 1)[0]
    whole_url = f"{short_url}?job={job_id}"
    qs = request.app["query_service"]
    job: Job | None = qs.get(job_id)
    if not job:
        ret = {"job": job_id, "status": "failed", "error": "Job not found."}
        return web.json_response(ret)
    status = job.get_status(refresh=True)
    msg = f"""Please wait: corpus processing in progress..."""
    # project = job.kwargs["project"]
    if status == "failed":
        res = job.latest_result()
        msg = "Error"
        if res:
            msg += f": {res.exc_string}"
    elif status == "finished":
        msg = f"""Template validated successfully"""
    ret = {
        "job": job.id,
        "status": status,
        "info": msg,
        "project": job.kwargs["project"],
        "project_name": job.kwargs["project_name"],
        "target": whole_url,
    }
    return web.json_response(ret)


async def _status_check(request: web.Request, job_id: str) -> web.Response:
    """
    What to do when user check status on an upload job
    """
    qs = request.app["query_service"]
    job = qs.get(job_id)
    project = job.args[0]
    progfile = os.path.join("uploads", project, ".progress.txt")
    progress = _get_progress(progfile)

    if not job:
        ret = {"job": job_id, "status": "failed", "error": "Job not found."}
        return web.json_response(ret)
    status = job.get_status(refresh=True)
    msg = f"""Please wait: corpus processing in progress..."""

    if status == "failed":
        msg = f"Error: {str(job.latest_result().exc_string)}"
    elif status == "finished":
        msg = f"""
        Upload is complete. You should be able to see your
        corpus in the web app. You may need to grant permission to
        other users if you want to allow them to access it.
        """
    ret = {
        "job": job.id,
        "status": status,
        "info": " ".join(msg.split()),
        "project": project,
    }
    if progress:
        ret["progress"] = "/".join(str(x) for x in progress)
    return web.json_response(ret)


def _get_progress(progfile: str) -> tuple[int, int, str, str] | None:
    """
    Attempt to get progress from saved file
    """
    if not os.path.isfile(progfile):
        return None
    msg = "Importing corpus"
    unit = "byte"
    extra = ":progress:"
    with open(progfile, "r") as fo:
        data = fo.read()
    if "\nSetting constraints..." in data:
        msg = "Indexing corpus"
        unit = "task"
        extra = ":extras:"
    if "\nComputing prepared segments" in data:
        msg = "Optimising corpus"
        unit = "task"
        extra = ":extras:"
    bits = [
        i.strip(":").strip().split(":")
        for i in data.splitlines()
        if i.startswith(":progress:") and extra in i
    ]
    if not bits:
        return None
    done_bytes = sum([int(i[1]) for i in bits])
    total = int(bits[-1][2])
    done_bytes = min(done_bytes, total)
    return (done_bytes, total, msg, unit)


def _ensure_partitioned0(path: str) -> None:
    """
    In case the user didn't call word.csv word0.csv
    """
    template = os.path.join(path, "_data.json")
    with open(template, "r") as fo:
        data = json.load(fo)
        data = data["template"]
    srcs = [os.path.join(path, "fts_vector.csv")]
    for layer in ('token','segment'):
        lay = data["firstClass"][layer]
        srcs.append( os.path.join(path, lay.lower() + ".csv") )
    for src in srcs:
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


@ensure_authorised
async def upload(request: web.Request) -> web.Response:
    """
    Handle upload of data (save files, insert into db)
    """
    url = request.url
    job_id = request.rel_url.query["job"]
    checking = request.rel_url.query.get("check")
    if checking:
        return await _status_check(request, job_id)

    user_data = await _lama_user_details(request.headers)

    gui_mode = request.rel_url.query.get("gui", False)
    is_vian = request.rel_url.query.get("vian", False)

    job = Job.fetch(job_id, connection=request.app["redis"])
    project_id = job.kwargs["project"]
    username = job.kwargs["user"]
    room = job.kwargs["room"]
    project_name = job.kwargs["project_name"]
    cpath = job.kwargs["path"]

    ziptar = [
        (".zip", is_zipfile, ZipFile, "namelist"),
        (".tar", is_tarfile, TarFile, "getnames"),
        (".tar.gz", is_tarfile, TarFile, "getnames"),
        (".tar.xz", is_tarfile, TarFile, "getnames"),
        (".7z", is_7zfile, SevenZipFile, "getnames"),
    ]

    # username = request.rel_url.query.get("user_id", "")
    # room = request.rel_url.query.get("room", None)

    if not project_id:
        return web.json_response({"status": "failed"})

    data = await request.multipart()
    has_file = False
    bit: BodyPartReader
    async for bit in data:
        if not isinstance(bit.filename, str):
            continue
        if not bit.filename.endswith(VALID_EXTENSIONS + COMPRESSED_EXTENTIONS):
            continue
        ext = os.path.splitext(bit.filename)[-1]
        path = os.path.join("uploads", cpath, bit.filename)

        has_file = await _save_file(path, bit, has_file)

        for ext, check, opener, method in ziptar:
            if path.endswith(ext) and check(path):
                _extract_file(bit, path, cpath, ext, opener, method)
            elif path.endswith(ext) and not check(path):
                print(f"Something wrong with {path}. Ignoring...")
                os.remove(path)
                fp = os.path.basename(path)
                ret = {"status": "failed", "msg": f"Problem uncompressing {fp}"}
                return web.json_response(ret)

    _ensure_partitioned0(os.path.join("uploads", cpath))
    _correct_doc(os.path.join("uploads", cpath))

    return_data: dict[str, str | int] = {}
    if not has_file:
        msg = "No file sent?"
        return_data.update({"status": "failed", "info": msg})
        return web.json_response(return_data)

    qs = request.app["query_service"]
    kwa = dict(gui=gui_mode, user_data=user_data, is_vian=is_vian)
    path = os.path.join("uploads", cpath)
    print(f"Uploading data to database: {cpath}")
    job = qs.upload(username, cpath, room, **kwa)
    short_url = str(url).split("?", 1)[0]
    suggest_url = f"{short_url}?job={job.id}"
    info = f"""Data upload has begun. If you want to check the status, POST to:
        {suggest_url}
    """
    return_data.update(
        {
            "status": "started",
            "job": job.id,
            "project": str(project_id),
            "project_name": project_name,
            "info": info,
            "target": suggest_url,
        }
    )

    return web.json_response(return_data)


async def _save_file(path: str, bit: BodyPartReader, has_file: bool) -> bool:
    """
    Helper to save file sent by FE to server
    """
    with open(path, "ba") as f:
        while True:
            chunk = await bit.read_chunk()
            if not chunk:
                break
            f.write(chunk)
            has_file = True
    return has_file


def _extract_file(
    bit, path: str, cpath: str, ext: str, opener: Callable, method: str
) -> None:
    print(f"Extracting {ext} file: {bit.filename}")
    with opener(path, "r") as compressed:
        for f in getattr(compressed, method)():
            basef = os.path.basename(str(f))
            if not str(f).endswith(VALID_EXTENSIONS):
                continue
            just_f = os.path.join("uploads", cpath, basef)
            dest = os.path.join("uploads", cpath)
            print(f"Uncompressing {basef}")
            if ext != ".7z":
                compressed.extract(f, dest)
            else:
                compressed.extract(dest, [f])
            try:
                os.rename(os.path.join(dest, str(f)), just_f)
            except Exception as err:
                print(f"Warning: {err}")
                pass
            print(f"Extracted: {basef}")
    print(f"Extracting {ext} done!")
    os.remove(path)  # todo: should we do this now?
    print(f"Deleted: {path}")


@ensure_authorised
async def make_schema(request: web.Request) -> web.Response:
    """
    What happens when a user goes to /create and POSTs JSON
    """
    exists = request.rel_url.query.get("job")
    if exists:
        return await _create_status_check(request, exists)

    request_data = await request.json()

    template = request_data["template"]
    room = request_data.get("room", None)
    projects = request_data.get("projects")
    special = {"lcp", "vian", "all"}
    project = next(i for i in projects if i not in special)

    today = datetime.today()
    later = today + timedelta(weeks=52, days=2)

    try:
        key = request.headers.get("X-API-Key")
        assert isinstance(key, str), "Missing API key"
        secret = request.headers.get("X-API-Secret")
        assert isinstance(secret, str), "Missing API key secret"
        status = await _lama_check_api_key(request.headers)
    except Exception as err:
        tb = traceback.format_exc()
        msg = f"Could not verify user: bad crendentials?"
        print(msg)
        error = {"traceback": tb, "status": "failed"}
        # logging.error(msg, extra=error)
        error["message"] = f"{msg} -- {err}"
        return web.json_response(error)

    # user_id = status["account"]["eduPersonId"]
    user_acc = cast(dict[str, dict | str], status["account"])
    user_id: str = cast(str, user_acc["email"])
    # home_org = status["account"]["homeOrganization"]
    existing_project = cast(dict[str, JSON], status.get("profile", {}))

    ids = (existing_project.get("id"), existing_project.get("title"))
    if project and project not in ids:
        admin = os.environ["LAMA_USER"]
        admin_org = os.getenv("LAMA_HOME_ORGANIZATION", admin.split("@")[-1])
        headers: Headers = {
            "X-API-Key": os.environ["LAMA_API_KEY"],
            "X-Remote-User": admin,
            "X-Schac-Home-Organization": admin_org,
            "X-Persistent-Id": os.environ["LAMA_PERSISTENT_ID"],
        }
        start = template["meta"].get("startDate", today.strftime("%Y-%m-%d"))
        finish = template["meta"].get("finishDate", later.strftime("%Y-%m-%d"))
        profile: dict[str, str] = {
            "title": project,
            "unit": "LiRI",
            "startDate": start,
            "finishDate": finish,
        }
        try:
            existing_project = await _lama_project_create(headers, profile)
            if existing_project.get("status", True) is not False:
                proj = json.dumps(existing_project, indent=4)
                msg = f"New project created:\n{proj}"
                print(msg)
                # logging.info(msg, extra=existing_project)
        except Exception as err:
            tb = traceback.format_exc()
            msg = f"Could not create project: {project} already exists?"
            print(msg)
            error = {"traceback": tb, "status": "failed"}
            # logging.error(msg, extra=error)
            error["message"] = f"{msg} -- {err}"
            return web.json_response(error)

    corpus_folder = str(uuid4())
    if existing_project.get("status", True) is False:
        error = {
            "status": "failed",
            "message": f"Could not get project",
        }
        return web.json_response(error)

    proj_id = cast(str, existing_project["id"])

    corpus_name = template["meta"]["name"]
    corpus_version = template["meta"]["version"]
    corpus_name = re.sub(r"\W", "_", template["meta"]["name"].lower())
    corpus_name = re.sub(r"_+", "_", corpus_name)
    # below we add a random suffix to the corpus name.
    # suffix of the name has 1/65536 chance of collision,
    # which is on the borderline of being too high in prod.
    # becomes 1/4.3b chance if we use [0] instead of [1]
    # but the schema name gets noticeably uglier, so ...
    
    #  suffix = corpus_folder.split("-", 2)[1]
    suffix = re.sub(r"[^a-zA-Z0-9]", "", proj_id)
    version_n = re.sub(r"[^0-9]", "", str(corpus_version))
    
    schema_name = f"{corpus_name}__{suffix}_{version_n}"

    sames = [
        i["schema_name"]
        for i in request.app["config"].values()
        if "meta" in i
        and "schema_name" in i
        and i["meta"]["name"] == corpus_name
        and str(i["meta"]["version"]) == str(corpus_version)
    ]
    drops = [f"DROP SCHEMA IF EXISTS {i} CASCADE;" for i in set(sames)]

    # todo: is this the right approach?
    cv = f"'{corpus_version}'" if isinstance(corpus_version, str) else corpus_version
    delete = f"DELETE FROM main.corpus WHERE name = '{corpus_name}' AND current_version = {cv};"
    drops.append(delete)

    template["projects"] = [proj_id]
    template["schema_name"] = schema_name

    pieces = generate_ddl(template)
    pieces["template"] = template

    corpus_path = os.path.join(proj_id, schema_name)

    directory = os.path.join("uploads", corpus_path)
    os.makedirs(directory)

    with open(os.path.join(directory, "_data.json"), "w") as fo:
        json.dump(pieces, fo)

    short_url = str(request.url).split("?", 1)[0]
    job = request.app["query_service"].create(
        pieces["create"],
        project=proj_id,
        path=corpus_path,
        schema_name=schema_name,
        user=user_id,
        room=room,
        drops=drops,
        project_name=existing_project["title"],
    )
    whole_url = f"{short_url}?job={job.id}"
    return web.json_response(
        {
            "status": "started",
            "job": job.id,
            "project": proj_id,
            "path": corpus_path,
            "target": whole_url,
            "user_id": user_id,
        }
    )

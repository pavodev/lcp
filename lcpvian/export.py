from aiohttp import web
from rq import Callback
from rq.connections import get_current_connection
from rq.job import Job
from typing import Any, cast

from .callbacks import _export_complete, _general_failure
from .exporter import Exporter
from .exporter_xml import ExporterXml
from .swissdox import export_swissdox
from .typed import JSONObject
from .utils import _determine_language, push_msg
import os

EXPORT_TTL = 5000

# See at the bottom for the definition of the class Export


def get_exporter_class(format: str) -> type[Exporter]:
    assert format in ("dump", "xml"), TypeError(
        f"The export format {format} is not supported"
    )
    exp_class = Exporter
    if format == "xml":
        exp_class = ExporterXml
    return exp_class


async def exporter(
    hash: str, config: dict[str, Any], format: str, partition: str = "", **kwargs
) -> None:
    connection = get_current_connection()
    exp_class = get_exporter_class(format)
    total_requested = kwargs.get("total_results_requested", 200)
    offset = kwargs.get("offset", 0)
    full = kwargs.get("full", False)
    await exp_class(
        hash,
        connection,
        config,
        partition,
        total_results_requested=total_requested,
        offset=offset,
        full=full,
    ).export()


async def export(app: web.Application, payload: JSONObject, first_job_id: str) -> Job:
    """
    Schedule job(s) to export data to storage
    Called in sock.py after the last batch was queried
    """
    export_format = cast(str, payload.get("format", ""))
    room = payload.get("room", "")
    user = payload.get("user", "")
    print("Ready to start exporting")
    corpus_conf = payload.get("config", {})
    # Retrieve the first job to get the list of all the sentence and meta jobs that export_dump depends on (also batch for swissdox)
    first_job = Job.fetch(first_job_id, connection=app["redis"])
    depends_on = [
        jid
        for ks in ("_sent_jobs", "_meta_jobs")
        for jid in first_job.meta.get(ks, {}).keys()
    ]
    job: Job
    if export_format == "swissdox":
        batch: str = cast(dict, first_job.kwargs).get("current_batch", ["", "", ""])[2]
        underlang = _determine_language(batch) or ""
        if underlang:
            underlang = f"_{underlang}"
        job = app["background"].enqueue(
            export_swissdox,
            on_failure=Callback(_general_failure, EXPORT_TTL),
            result_ttl=EXPORT_TTL,
            job_timeout=EXPORT_TTL,
            depends_on=depends_on,
            args=(first_job_id, underlang, corpus_conf),
            kwargs={
                "download": payload.get("download", False),
                "room": room,
                "user": user,
            },
        )
    else:
        rest: dict[str, Any] = {}
        if depends_on:
            print("Scheduled dump export depending on", depends_on)
            rest = {"depends_on": depends_on}
        hash: str = first_job.id
        partition: str = ""
        languages: list[str] = cast(dict, first_job.kwargs).get("languages", [])
        partitions: dict = cast(dict, payload["config"]).get("partitions", {})
        if languages and languages[0] in partitions.get("values", []):
            partition = languages[0]
        exclude_from_payload = ("config", "format")
        exporter_payload = {
            k: v for k, v in payload.items() if k not in exclude_from_payload
        }
        job = app["background"].enqueue(
            exporter,
            on_success=Callback(_export_complete, EXPORT_TTL),
            on_failure=Callback(_general_failure, EXPORT_TTL),
            result_ttl=EXPORT_TTL,
            job_timeout=EXPORT_TTL,
            args=(hash, corpus_conf, export_format, partition),
            kwargs=exporter_payload,
            **rest,
        )

    room = cast(str, payload.get("room", ""))
    user = cast(str, payload.get("user", ""))
    export_msg: JSONObject = cast(
        JSONObject,
        {
            "room": room,
            "user": user,
            "action": "started_export",
            "job_id": str(job.id),
        },
    )
    await push_msg(
        app["websockets"],
        room,
        export_msg,
        skip=None,
        just=(room, user),
    )

    return job


async def download_export(request: web.Request) -> web.FileResponse:
    hash = request.match_info["hash"]
    format = request.match_info["format"]
    offset = cast(int, request.match_info["offset"])
    requested = cast(int, request.match_info["total_results_requested"])
    full = cast(bool, request.match_info.get("full", False))
    exporter_class = get_exporter_class(format)
    filepath = exporter_class.get_dl_path_from_hash(hash, offset, requested, full)
    assert os.path.exists(filepath), FileNotFoundError("Could not find the export file")
    return web.FileResponse(filepath)

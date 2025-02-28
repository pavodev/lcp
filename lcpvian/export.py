from aiohttp import web
from rq import Callback
from rq.connections import get_current_connection
from rq.job import Job
from typing import Any, cast

from .callbacks import _export_complete, _general_failure
from .exporter import Exporter
from .jobfuncs import _handle_export
from .swissdox import export_swissdox
from .typed import Batch, JSONObject
from .utils import (
    _determine_language,
    _get_all_jobs_from_hash,
    _get_query_info,
    push_msg,
    format_meta_lines,
)
import os

EXPORT_TTL = 5000

# See at the bottom for the definition of the class Export


async def exporter(
    hash: str, config: dict[str, Any], format: str, partition: str = "", **kwargs
) -> None:
    connection = get_current_connection()
    exp_class = Exporter.get_exporter_class(format)
    total_requested = kwargs.get("total_results_requested", 200)
    offset = kwargs.get("offset", 0)
    full = kwargs.get("full", False)
    exp_instance = exp_class(
        hash,
        connection,
        config,
        partition,
        total_results_requested=total_requested,
        offset=offset,
        full=full,
    )
    await exp_instance.export()
    await _handle_export(  # finish_export
        hash,
        format,
        create=False,
        offset=exp_instance._offset,
        requested=exp_instance._total_results_requested,
        delivered=exp_instance.n_results,
        path=exp_class.get_dl_path_from_hash(
            hash,
            exp_instance._offset,
            exp_instance._total_results_requested,
            exp_instance._full,
        ),
    )


async def export(app: web.Application, payload: JSONObject, first_job_id: str) -> Job:
    """
    Schedule job(s) to export data to storage
    Called in sock.py after the last batch was queried
    """
    export_format = cast(str, payload.get("format", ""))
    room = cast(str, payload.get("room", ""))
    user = cast(str, payload.get("user", ""))
    offset = payload.get("offset", 0)
    requested = payload.get("total_results_requested", 0)

    print("Ready to start exporting")
    corpus_conf: dict = cast(dict, payload.get("config", {}))
    # Retrieve the first job to get the list of all the sentence and meta jobs that export_dump depends on (also batch for swissdox)
    first_job = Job.fetch(first_job_id, connection=app["redis"])
    hash: str = first_job.id
    batch: str = cast(dict, first_job.kwargs).get("current_batch", (0, "", "", 0))

    userpath: str = f"{corpus_conf.get('shortname')}/results.{export_format}"
    init_export_job = app["internal"].enqueue(
        _handle_export,  # init_export
        on_failure=Callback(_general_failure, EXPORT_TTL),
        result_ttl=EXPORT_TTL,
        job_timeout=EXPORT_TTL,
        args=(hash, export_format, True, offset, requested),
        kwargs={"user_id": user, "userpath": userpath, "corpus_id": batch[0]},
    )

    depends_on = [
        jid
        for ks in ("_sent_jobs", "_meta_jobs")
        for jid in first_job.meta.get(ks, {}).keys()
    ]
    depends_on.append(init_export_job.id)

    job: Job
    query_info = _get_query_info(app["redis"], hash=hash)
    if export_format == "swissdox":
        _, _, batch, *_ = query_info.get("current_batch", ["", "", ""])
        underlang = _determine_language(batch) or ""
        if underlang:
            underlang = f"_{underlang}"
        article_ids: set[str] = set()
        _, _, meta_jobs = _get_all_jobs_from_hash(first_job_id, app["redis"])
        for j in meta_jobs:
            segs_to_meta = format_meta_lines(
                cast(str, cast(dict, j.kwargs).get("meta_query")), j.result
            )
            incoming_arids: set[str] = {
                str(v["Article"]["id"]) for v in cast(dict, segs_to_meta).values()
            }
            article_ids = article_ids.union(incoming_arids)
        conf: dict = cast(dict, corpus_conf)
        swissdox_kwargs = {
            "user": user,
            "room": room,
            "project_id": str(conf.get("project_id", "all")),
            "corpus_name": str(conf.get("shortname", "swissdox")),
            "hash": hash,
        }
        job = await export_swissdox(
            app["redis"], [a for a in article_ids], **swissdox_kwargs  # type: ignore
        )
        app["background"].enqueue(
            _handle_export,  # finish export
            on_failure=Callback(_general_failure, EXPORT_TTL),
            result_ttl=EXPORT_TTL,
            depends_on=job.id,
            job_timeout=EXPORT_TTL,
            args=(hash, export_format, False, offset, requested),
            kwargs={"delivered": 200},
        )
    else:
        rest: dict[str, Any] = {}
        if depends_on:
            print("Scheduled dump export depending on", depends_on)
            rest = {"depends_on": depends_on}
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

    export_msg: JSONObject = cast(
        JSONObject,
        {
            "room": room,
            "user": user,
            "action": "started_export",
            "format": export_format,
            "hash": hash,
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
    filepath = ""
    hash = request.rel_url.query["hash"]
    format = request.rel_url.query["format"]
    offset = request.rel_url.query.get("offset", "0")
    requested = request.rel_url.query.get("requested", "0")
    full = cast(bool, request.rel_url.query.get("full", False))
    if format == "swissdox":
        results_path = str(os.environ.get("RESULTS_PATH", "results"))
        filepath = os.path.join(results_path, hash, offset, "swissdox.db")
    else:
        exporter_class = Exporter.get_exporter_class(format)
        filepath = exporter_class.get_dl_path_from_hash(
            hash, cast(int, offset), cast(int, requested), full
        )
    assert os.path.exists(filepath), FileNotFoundError("Could not find the export file")
    # TODO: check user access to file
    content_disposition = f'attachment; filename="{os.path.basename(filepath)}"'
    headers = {
        "content-disposition": content_disposition,
        "content-length": f"{os.stat(filepath).st_size}",
    }
    return web.FileResponse(filepath, headers=headers)

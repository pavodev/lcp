from typing import Sequence, cast

from aiohttp import web

from .sock import push_msg
from .typed import Config, JSONObject
from .utils import ensure_authorised


@ensure_authorised
async def document(request: web.Request) -> web.Response:
    """
    Start a job fetching a corpus document via the doc_export functionality.

    The job's callback will send the document to the user/room via websocket
    """
    doc_id: int = int(request.match_info["doc_id"])
    request_data: dict[str, str] = await request.json()
    room: str | None = request_data.get("room")
    user: str = request_data.get("user", "")
    c: int | str | list[int] | list[str] = request_data["corpora"]
    corpora: list[int] = [int(c)] if not isinstance(c, list) else [int(i) for i in c]
    corpus = corpora[0]
    schema = request.app["config"][str(corpus)]["schema_path"]
    job = request.app["query_service"].document(schema, corpus, doc_id, user, room)
    info: dict[str, str] = {"status": "started", "job": job.id}
    return web.json_response(info)


@ensure_authorised
async def document_ids(request: web.Request) -> web.Response:
    """
    Get a dict of doc_id: doc_name

    As usual, it comes back via WS message. Only the first call will
    trigger a new job; subsequent calls get the stored result from config.
    """
    request_data: dict[str, str] = await request.json()
    room: str = request_data.get("room", "")
    user: str = request_data.get("user", "")
    corpus_id = str(request.match_info["corpus_id"])
    config: Config = request.app["config"]
    schema = cast(str, config[corpus_id]["schema_path"])

    if "doc_ids" not in config[corpus_id]:
        job = request.app["query_service"].document_ids(
            schema, int(corpus_id), user, room
        )
        info: dict[str, str] = {"status": "started", "job": job.id}
        return web.json_response(info)

    job_id: str
    doc_ids: JSONObject
    ids: Sequence = config[corpus_id]["doc_ids"]
    job_id, doc_ids = ids
    payload: JSONObject = {
        "document_ids": doc_ids,
        "action": "document_ids",
        "user": user,
        "room": room,
        "job": job_id,
        "corpus_id": int(corpus_id),
    }
    await push_msg(
        request.app["websockets"],
        room,
        payload,
        skip=None,
        just=(room, user),
    )
    early: JSONObject = {
        "status": "finished",
        "job": job_id,
        "document_ids": doc_ids,
    }
    return web.json_response(early)

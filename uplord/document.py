from typing import Any

from aiohttp import web

from .utils import ensure_authorised


@ensure_authorised
async def document(request: web.Request) -> web.Response:
    """
    Start a job fetching a corpus document via the doc_export functionality.

    The job's callback will send the document to the user/room via websocket
    """
    doc_id: int = int(request.match_info["doc_id"])
    request_data: dict[str, Any] = await request.json()
    room: str | None = request_data.get("room")
    user: str = request_data.get("user", "")
    c: int | str | list[int] | list[str] = request_data["corpora"]
    corpora: list[int] = [int(c)] if not isinstance(c, list) else [int(i) for i in c]
    corpus = corpora[0]
    schema = request.app["config"][str(corpus)]["schema_path"]
    job = request.app["query_service"].document(schema, corpus, doc_id, user, room)
    info: dict[str, str] = {"status": "started", "job": job.id}
    return web.json_response(info)

from aiohttp import web

from typing import Any, Dict

from .utils import ensure_authorised


@ensure_authorised
async def document(request: web.Request) -> web.Response:
    """
    Start a job fetching a corpus document via the doc_export functionality.

    The job's callback will send the document to the user/room via websocket
    """
    doc_id: int = int(request.match_info["doc_id"])
    request_data: Dict[str, Any] = await request.json()
    room: str | None = request_data.get("room")
    user = request_data.get("user", "")
    corpora: Any = request_data["corpora"]
    if not isinstance(corpora, (list, tuple, set)):
        corpora = [corpora]
    corpus: str | int = list(corpora)[0]
    schema = request.app["config"][str(corpus)]["schema_path"]
    job = request.app["query_service"].document(schema, int(corpus), doc_id, user, room)
    info: Dict[str, str] = {"status": "started", "job": job.id}
    return web.json_response(info)

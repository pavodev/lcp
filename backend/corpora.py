from aiohttp import web
from json.decoder import JSONDecodeError

from .utils import _lama_user_details, ensure_authorised


def _has_access(user, corpus):
    """
    Here we make a request to lama to find out if a user can access a corpus. or something
    """
    return True


@ensure_authorised
async def corpora(request: web.Request) -> web.Response:
    """
    Return config to frontend
    """
    user_data = await _lama_user_details(request.headers)
    ids = {"all"}
    try:
        request_data = await request.json()
    except JSONDecodeError:  # no data was sent ... eventually this should not happpen
        request_data = {}
    is_vian = request_data.get("appType", "lcp") == "vian"
    if is_vian:
        ids.add("vian")
    else:
        ids.add("lcp")
    for sub in user_data.get("subscription", {}).get("subscriptions", []):
        ids.add(sub["id"])
    for proj in user_data.get("publicProjects", []):
        ids.add(proj["id"])
    corpora = {}
    for corpus_id, conf in request.app["config"].items():
        if corpus_id == -1:
            corpora[corpus_id] = conf
        allowed = conf.get("projects", [])
        if is_vian and allowed and "vian" not in allowed and "all" not in allowed:
            continue
        elif not is_vian and allowed and "lcp" not in allowed and "all" not in allowed:
            continue
        if not allowed or any(i in ids for i in allowed):
            corpora[corpus_id] = conf
    return web.json_response({"config": corpora})

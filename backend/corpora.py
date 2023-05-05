from aiohttp import web

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
    ids = set()
    for sub in user_data.get("subscription", {}).get("subscriptions", []):
        ids.add(sub["id"])
    for proj in user_data.get("publicProjects", []):
        ids.add(proj["id"])
    corpora = {}
    for k, v in request.app["config"].items():
        if k == -1:
            corpora[k] = v
        elif v.get("project") in ids or "project" not in v:
            corpora[k] = v
    return web.json_response({"config": corpora})

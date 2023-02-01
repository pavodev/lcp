from aiohttp import web

from . import utils


def _has_access(user, corpus):
    """
    Here we make a request to lama to find out if a user can access a corpus. or something
    """
    return True


@utils.ensure_authorised
async def corpora(request):
    """
    User may request all corpora containing some feature. We look up all those corpora,
    and remove things the user can't access, and return corpus information object.

    JSON should contain some kind of query data for a table of corpora
    """
    request_json = await request.json()
    user = request_json["user"]
    requested = request_json["corpora"]
    # return all requested corpora that user can access
    possible_corpora = set([i for i in requested if _has_access(user, i)])
    return web.json_response({"corpora": possible_corpora})

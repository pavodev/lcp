import re

from aiohttp import web
from cquery import validate as validator

from . import utils


# @utils.ensure_authorised
async def validate(request):
    """
    Query validation for regexes or CQP/CQL/cquery

    Incoming POST data looks like this: {"query": 'querystring.*', "simple": True}

    Where simple is used for simple regex, rather than cquery.

    Returns:

    Empty JSON response if query is valid.

    If invalid and query is a regex, you get a dict {"error": {"pre": error_msg}}

    If invalid and query is a cquery, you get the above with pre, code and post keys.

    * pre describes the error
    * code shows the bad part of the code and contains a caret on a lower line
    * post gives suggestions for alternatives
    """
    data = await request.json()
    query = data["query"]
    simple = data.get("simple", False)
    if simple:  # simple being just a regex
        try:
            re.compile(query)
            output = {}
        except re.error as error:
            output = {"error": {"pre": str(error), "code": "", "post": ""}}
        return web.json_response(data=output)

    result = validator(query, traverse=True)
    output = (
        result
        if not hasattr(result, "pre")
        else {"error": {"pre": result.pre, "code": result.code, "post": result.post}}
    )
    return web.json_response(data=output)

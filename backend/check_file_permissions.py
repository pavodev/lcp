import re

from aiohttp import web

from . import utils


async def check_file_permissions(request: web.Request) -> web.Response:
    """
    Returns if user has access to file
    """
    retval = ("Error", 460)
    profiles_id = []
    uri = request.headers.get("X-Request-Uri")

    # For test
    # uri = "/video/3d4560a1-aaa9-4eae-bcf1-ac224989c7e3/video1.mp4"

    user_details_lama = await utils._lama_user_details(request.headers)
    for subscription in user_details_lama.get("subscription", {}).get("subscriptions"):
        profiles_id.extend(
            [profile.get("id") for profile in subscription.get("profiles")]
        )

    for public_profile in user_details_lama.get("publicProfiles", []):
        profiles_id.append(public_profile.get("id"))

    if uri:
        regex = "\/video\/(?P<profile_id>(.*))\/(?P<video_name>(.*))\.mp4"
        matches = re.match(regex, uri)
    else:
        matches = None

    if user_details_lama and matches and matches.groupdict():
        profile_id = matches.groupdict().get("profile_id")
        if profile_id in profiles_id:
            retval = ("OK", 200)
        elif not profile_id:
            retval = ("Invalid query", 464)
        elif not profile_id in profiles_id:
            retval = ("No permission", 465)
    elif not user_details_lama:
        retval = ("Invalid user", 461)

    return web.Response(body=retval[0], status=retval[1])

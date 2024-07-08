from aiohttp import web
from typing import Any, cast
from yarl import URL

from .authenticate import Authentication
from .configure import CorpusConfig
from .utils import _lama_user_details
from .typed import JSONObject, TypeAlias

subtype: TypeAlias = list[dict[str, str]]


# Authentication class used at LiRI with the Lama system
class Lama(Authentication):

    def __init__(self, app: web.Application) -> None:
        super().__init__(app)

    def check_corpus_allowed(
        self,
        corpus_id: str,
        corpus: CorpusConfig,
        user_data: JSONObject | None,
        app_type: str = "",
        get_all: bool = False,
    ) -> bool:

        ids: set[str] = set()
        if isinstance(user_data, dict):
            subs = cast(dict[str, subtype], user_data.get("subscription", {}))
            sub = subs.get("subscriptions", [])
            for s in sub:
                ids.add(s["id"])
            for proj in cast(list[dict[str, Any]], user_data.get("publicProfiles", [])):
                ids.add(proj["id"])

        ids.add("all")

        if get_all is False and not [
            project_id for project_id in corpus.get("projects", {}) if project_id in ids
        ]:
            return False
        idx = str(corpus_id)
        if idx == "-1":
            return True
        data_type: str = ""
        for slot in cast(dict, corpus).get("meta", {}).get("mediaSlots", {}).values():
            if data_type == "video":
                continue
            data_type = slot.get("mediaType", "")
        if get_all or app_type in ("lcp", "catchphrase"):
            return True
        if app_type == "videoscope" and data_type in ["video"]:
            return True
        if app_type == "soundscript" and data_type in ["audio", "video"]:
            return True

        return False

    async def check_file_permissions(self, request: web.Request) -> tuple[str, int]:
        msg, status = ("Error", 460)
        profiles_id: set[str] = set()
        uri: str = request.headers.get("X-Request-Uri", "")

        user_details_lama = await _lama_user_details(request.headers)
        sub = cast(dict[str, Any], user_details_lama["subscription"])
        subs = cast(list[dict[str, Any]], sub["subscriptions"])
        for subscription in subs:
            for profile in subscription["profiles"]:
                profiles_id.add(profile["id"])

        profiles = cast(
            list[dict[str, Any]], user_details_lama.get("publicProfiles", [])
        )
        for public_profile in profiles:
            profiles_id.add(public_profile["id"])

        profile_id: str = ""
        if uri and user_details_lama:
            profile_id = URL(uri).parts[-2]
            if profile_id in profiles_id:
                msg, status = ("OK", 200)
            elif not profile_id:
                msg, status = ("Invalid query", 464)
            elif profile_id not in profiles_id:
                msg, status = ("No permission", 465)
        elif not user_details_lama:
            msg, status = ("Invalid user", 461)

        return (msg, status)

    async def user_details(self, request: web.Request) -> JSONObject:
        user_details_lama = await _lama_user_details(request.headers)
        return user_details_lama

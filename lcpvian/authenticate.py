from aiohttp import web
from typing import cast

from .configure import CorpusConfig
from .typed import JSONObject, TypeAlias

subtype: TypeAlias = list[dict[str, str]]


# Default authentication class
class Authentication:

    def __init__(self, app: web.Application) -> None:
        self.app = app
        # self.all_corpora = app.all_corpora

    def basic(self):
        pass

    # Return (status_string, status_code) given a web request [async]
    async def check_file_permissions(self, request: web.Request) -> tuple[str, int]:
        return ("OK", 200)

    def check_user_ok(self, user):
        pass

    # Return True/False given a corpus_id, CorpusConfig, user_data and app_type
    def check_corpus_allowed(
        self,
        corpus_id: str,
        corpus: CorpusConfig,
        user_data: JSONObject | None,
        app_type: str = "",
        get_all: bool = False,
    ) -> bool:
        return True

    def query(self, corpora):
        # self.check_user_ok()
        # for c in self.all_corpora:
        #     pass
        # assert c in user.projects
        pass

    # Return user details given a web request [async]
    async def user_details(self, request: web.Request) -> JSONObject:
        # This is based on the configuration at LiRI
        user_data = {
            "user": {
                "id": "00000000-0000-0000-0000-000000000000",
                "displayName": "Foo Bar",
                "name": "Foo Bar",
                "email": "foo@bar.xyz",
                "homeOrganization": "FooBar",
            },
            "subscription": {"subscriptions": []},
            "publicProfiles": [
                {
                    "id": "848c1f0f-a1e3-4f6b-93da-4a7b26c6c6d9",
                    "project_id": "9d925a5b-f198-49c4-a577-4cddc1cbb78b",
                    "title": "Public",
                    "institution": "uzh.ch",
                    "additionalData": {"public": True},
                }
            ],
        }
        return cast(JSONObject, user_data)

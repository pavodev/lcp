import aiohttp
import os

from time import sleep

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from rq.command import PUBSUB_CHANNEL_TEMPLATE

from run import create_app, handle_redis_response, on_shutdown


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"

os.environ["_TEST"] = "true"


class MyAppTestCase(AioHTTPTestCase):
    async def tearDownAsync(self):
        await super().tearDownAsync()
        await on_shutdown(self._app)

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        app = await create_app(test=True)
        self._app = app

        pubsub = app["aredis"].pubsub()
        async with pubsub as p:
            await p.subscribe(PUBSUB_CHANNEL)
            await handle_redis_response(p, app, test=True)
            await p.unsubscribe(PUBSUB_CHANNEL)

        return app

    async def test_example(self):

        async with self.client.request("POST", "/corpora") as resp:
            self.assertEqual(resp.status, 200)
            conf_data = await resp.json()
            self.assertTrue(str(-1) in conf_data["config"])
            self.assertTrue("meta" in conf_data["config"][str(1)])

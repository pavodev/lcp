from __future__ import annotations

import os
import sys

from collections import defaultdict, deque

import aiohttp_cors
import asyncio
import logging

import uvloop

from dotenv import load_dotenv

load_dotenv(override=True)

SENTRY_DSN = os.getenv("SENTRY_DSN", None)

if SENTRY_DSN:

    import sentry_sdk
    from sentry_sdk.integrations.aiohttp import AioHttpIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.WARNING,
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[AioHttpIntegration(), sentry_logging],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", 1.0)),
        environment=os.getenv("SENTRY_ENVIRONMENT", "lcp"),
    )


from aiohttp import WSCloseCode, web
from aiohttp_catcher import Catcher, catch

from redis import Redis
from redis import asyncio as aioredis
from rq.exceptions import NoSuchJobError
from rq.queue import Queue

from backend.check_file_permissions import check_file_permissions
from backend.corpora import corpora
from backend.document import document
from backend.lama_user_data import lama_user_data
from backend.project import project_api_create, project_api_revoke, project_create
from backend.query import query
from backend.query_service import QueryService
from backend.sock import handle_redis_response, sock, ws_cleanup
from backend.store import fetch_queries, store_query
from backend.upload import make_schema, upload
from backend.utils import PUBSUB_CHANNEL, handle_timeout
from backend.validate import validate
from backend.video import video


REDIS_DB_INDEX = int(os.getenv("REDIS_DB_INDEX", 0))
_RHOST, _RPORT = os.getenv("REDIS_URL", "http://localhost:6379").rsplit(":", 1)
REDIS_HOST = _RHOST.split("/")[-1].strip()
REDIS_PORT = int(_RPORT.strip())
APP_PORT = int(os.getenv("AIO_PORT", 9090))


async def _listen_to_redis_for_queries(app: web.Application) -> None:
    """
    Using our async redis connection instance, listen for events coming from redis
    and delegate to the sender
    """
    pubsub = app["aredis"].pubsub()
    async with pubsub as p:
        await p.subscribe(PUBSUB_CHANNEL)
        try:
            await handle_redis_response(p, app)
        except KeyboardInterrupt:
            await p.unsubscribe(PUBSUB_CHANNEL)
            return
        except Exception as err:
            raise err
        await p.unsubscribe(PUBSUB_CHANNEL)


async def on_shutdown(app: web.Application) -> None:
    """
    Close websocket connections on app shutdown
    """
    msg = "Server shutdown"
    for room, conns in app["websockets"].items():
        for ws, uid in conns:
            try:
                await ws.close(code=WSCloseCode.GOING_AWAY, message=msg)
            except Exception as err:
                print(f"Issue closing websocket for {room}/{uid}: {err}")


async def start_background_tasks(app: web.Application) -> None:
    """
    Start the thread that listens to redis pubsub
    Start the thread that periodically removes stale websocket connections
    """
    app["redis_listener"] = asyncio.create_task(_listen_to_redis_for_queries(app))
    app["ws_cleanup"] = asyncio.create_task(ws_cleanup(app["websockets"]))


async def cleanup_background_tasks(app: web.Application) -> None:
    """
    Stop running background tasks: redis listener, stale ws cleaner
    """
    app["redis_listener"].cancel()
    await app["redis_listener"]
    app["ws_cleanup"].cancel()
    await app["ws_cleanup"]


async def create_app(*args, **kwargs) -> web.Application | None:
    """
    Build an instance of the app. If test=True is passed, it is returned
    before background tasks are added, to aid with unit tests
    """

    catcher = Catcher()

    await catcher.add_scenario(
        catch(NoSuchJobError).with_status_code(200).and_call(handle_timeout)
    )

    app = web.Application(middlewares=[catcher.middleware])
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )

    # all websocket connections are stored in here, as {room: {(connection, user_id,)}}
    # when a user leaves the app, the connection should be removed. If it's not,
    # the dict is periodically cleaned by a separate thread, to stop this from always growing
    app["websockets"] = defaultdict(set)

    resource = cors.add(app.router.add_resource("/corpora"))
    cors.add(resource.add_route("GET", corpora))
    cors.add(resource.add_route("POST", corpora))

    resource = cors.add(app.router.add_resource("/query"))
    cors.add(resource.add_route("POST", query))

    resource = cors.add(app.router.add_resource("/validate"))
    cors.add(resource.add_route("POST", validate))

    resource = cors.add(app.router.add_resource("/upload"))
    cors.add(resource.add_route("POST", upload))

    resource = cors.add(app.router.add_resource("/create"))
    cors.add(resource.add_route("POST", make_schema))

    resource = cors.add(app.router.add_resource("/video"))
    cors.add(resource.add_route("GET", video))

    resource = cors.add(app.router.add_resource("/ws"))
    cors.add(resource.add_route("GET", sock))

    resource = cors.add(app.router.add_resource("/document/{doc_id}"))
    cors.add(resource.add_route("POST", document))

    resource = cors.add(app.router.add_resource("/fetch"))
    cors.add(resource.add_route("POST", fetch_queries))

    resource = cors.add(app.router.add_resource("/store"))
    cors.add(resource.add_route("POST", store_query))

    resource = cors.add(app.router.add_resource("/project"))
    cors.add(resource.add_route("POST", project_create))

    resource = cors.add(app.router.add_resource("/project/{project}/api/create"))
    cors.add(resource.add_route("POST", project_api_create))

    resource = cors.add(app.router.add_resource("/project/{project}/api/{key}/revoke"))
    cors.add(resource.add_route("POST", project_api_revoke))

    resource = cors.add(app.router.add_resource("/settings"))
    cors.add(resource.add_route("GET", lama_user_data))

    resource = cors.add(app.router.add_resource("/check-file-permissions"))
    cors.add(resource.add_route("GET", check_file_permissions))

    # we keep two redis connections, for reasons
    app["aredis"] = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_INDEX)
    app["redis"] = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_INDEX)

    # different queues for different kinds of jobs
    app["query"] = Queue(connection=app["redis"])
    app["export"] = Queue(connection=app["redis"], job_timeout=-1)
    app["alt"] = Queue(connection=app["redis"], job_timeout=-1)
    app["query_service"] = QueryService(app)
    app["query_service"].get_config()
    app["canceled"] = deque(maxlen=99999)

    if kwargs.get("test"):
        return app

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    app.on_shutdown.append(on_shutdown)

    return app


async def start_app() -> None:
    try:
        maybe_app = await create_app()
        if not maybe_app:
            return None
        else:
            app = maybe_app
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, port=APP_PORT)
        await site.start()
        # wait forever
        await asyncio.Event().wait()
        return None
    except KeyboardInterrupt:
        return


# test mode should not start a loop
if "_TEST" in os.environ:
    pass

# this is how mypy starts the app
elif __name__ == "run":
    asyncio.run(start_app())

# development mode starts a dev server
elif __name__ == "__main__" or sys.argv[0].endswith("adev"):
    try:
        if sys.version_info >= (3, 11):
            with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
                runner.run(start_app())
        else:
            uvloop.install()
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            asyncio.run(start_app())
    except KeyboardInterrupt:
        print("Stopped.")

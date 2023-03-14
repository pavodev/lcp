import json
import os

from collections import defaultdict

import aiohttp
import aiohttp_cors
import async_timeout
import asyncio

from aiohttp import WSCloseCode, web
from dotenv import load_dotenv
from redis import Redis

# import redis.asyncio as redis
import asyncpg
import uvloop

from redis import Redis as redis
from redis import asyncio as aioredis
from rq import Queue
from rq.command import PUBSUB_CHANNEL_TEMPLATE
from rq.exceptions import NoSuchJobError
from sshtunnel import SSHTunnelForwarder

from backend.check_file_permissions import check_file_permissions
from backend.sock import handle_redis_response, sock
from backend.video import video

from aiohttp_catcher import Catcher, catch
from backend.document import document
from backend.lama_user_data import lama_user_data
from backend.query import query
from backend.store import fetch_queries, store_query
from backend.upload import upload

# from backend.validate import validate
from backend import utils
from backend.corpora import corpora
from backend.query_service import QueryService


load_dotenv(override=True)

USER = os.getenv("SQL_USERNAME")
PASSWORD = os.getenv("SQL_PASSWORD")
HOST = os.getenv("SQL_HOST")
DBNAME = os.getenv("SQL_DATABASE")
PORT = int(os.getenv("SQL_PORT", 5432))
VERBOSE = True if os.getenv("VERBOSE", "").lower() == "true" else False
RHOST, RPORT = os.environ["REDIS_URL"].rsplit(":", 1)
REDIS_HOST = RHOST.split("/")[-1].strip()
REDIS_PORT = int(RPORT.strip())


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


async def _listen_to_redis_for_queries(app: web.Application) -> None:
    """
    Using our async redis connection instance, listen for events coming from redis
    and delegate to the sender
    """
    pubsub = app["aredis"].pubsub()
    async with pubsub as p:
        await p.subscribe(PUBSUB_CHANNEL)
        await handle_redis_response(p, app)
        await p.unsubscribe(PUBSUB_CHANNEL)


async def on_shutdown(app: web.Application) -> None:
    """
    Close websocket connections on app shutdown
    """
    msg = "Server shutdown"
    for (ws, uid) in app["websockets"].values():
        try:
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message=msg)
        except Exception as err:
            print(f"Issue closing websocket for {uid}: {err}")


async def start_background_tasks(app: web.Application) -> None:
    """
    Start the thread that listens to redis pubsub
    """
    app["redis_listener"] = asyncio.create_task(_listen_to_redis_for_queries(app))


async def cleanup_background_tasks(app: web.Application) -> None:
    """
    Stop the redis listener
    """
    app["redis_listener"].cancel()
    await app["redis_listener"]


async def create_app(*args, **kwargs) -> None:

    catcher = Catcher()

    await catcher.add_scenario(
        catch(NoSuchJobError).with_status_code(200).and_call(utils.handle_timeout)
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

    app["websockets"] = defaultdict(set)

    tunnel = SSHTunnelForwarder(
        os.getenv("SSH_HOST"),
        ssh_username=os.getenv("SSH_USER"),
        ssh_password=None,
        ssh_pkey=os.getenv("SSH_PKEY"),
        remote_bind_address=(HOST, PORT),
    )
    tunnel.start()

    resource = cors.add(app.router.add_resource("/corpora"))
    cors.add(resource.add_route("GET", corpora))
    cors.add(resource.add_route("POST", corpora))

    resource = cors.add(app.router.add_resource("/query"))
    cors.add(resource.add_route("POST", query))

    # resource = cors.add(app.router.add_resource("/validate"))
    # cors.add(resource.add_route("POST", validate))

    resource = cors.add(app.router.add_resource("/upload"))
    cors.add(resource.add_route("POST", upload))

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

    resource = cors.add(app.router.add_resource("/settings"))
    cors.add(resource.add_route("GET", lama_user_data))

    resource = cors.add(app.router.add_resource("/check-file-permissions"))
    cors.add(resource.add_route("GET", check_file_permissions))

    conn = f"postgresql://{USER}:{PASSWORD}@localhost:{tunnel.local_bind_port}/{DBNAME}"
    app["db_conn"] = await asyncpg.connect(conn)
    # we keep two redis connections, for reasons
    app["aredis"] = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    app["redis"] = Redis(host=REDIS_HOST, port=REDIS_PORT)
    app["query"] = Queue(connection=app["redis"])
    # app["stats"] = Queue(connection=app["redis"])
    app["export"] = Queue(connection=app["redis"], job_timeout=-1)
    app["alt"] = Queue(connection=app["redis"], job_timeout=-1)
    app["query_service"] = QueryService(app)
    app["query_service"].get_config()
    app["canceled"] = set()

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    app.on_shutdown.append(on_shutdown)

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, port=9090)
    await site.start()
    # wait forever
    await asyncio.Event().wait()
    # return app
    return None


if __name__ == "__main__" or __name__ == "run":
    uvloop.install()  # documentation has this and the below...
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app = asyncio.run(create_app())
    # web.run_app(app, port=9090)

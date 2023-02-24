from collections import defaultdict
import os
import json

import aiohttp
from aiohttp import web, WSCloseCode
import async_timeout
import aiohttp_cors
import asyncio
from dotenv import load_dotenv
import psycopg
from redis import Redis

# import redis.asyncio as redis
from redis import Redis as redis
from redis import asyncio as aioredis
from rq import Queue
from rq.command import PUBSUB_CHANNEL_TEMPLATE
from sshtunnel import SSHTunnelForwarder
import uvloop
import asyncpg

from backend.check_file_permissions import check_file_permissions
from backend.video import video
from backend.sock import (
    sock,
    send_json_to_user_socket,
    send_finished_query_to_websockets,
)
from backend.lama_user_data import lama_user_data
from backend.query import query
from backend.document import document
from backend.validate import validate
from backend.corpora import corpora
from backend.query_service import QueryService


load_dotenv(override=True)

USER = os.getenv("SQL_USERNAME")
PASSWORD = os.getenv("SQL_PASSWORD")
HOST = os.getenv("SQL_HOST")
DBNAME = os.getenv("SQL_DATABASE")
PORT = int(os.getenv("SQL_PORT", 5432))
VERBOSE = True if os.getenv("VERBOSE", "").lower() == "true" else False
RHOST, RPORT = os.getenv("REDIS_URL").rsplit(":", 1)
REDIS_HOST = RHOST.split("/")[-1].strip()
REDIS_PORT = int(RPORT.strip())


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


async def _listen_to_redis_for_queries(app):
    """
    Using our async redis connection instance, listen for events coming from redis
    and delegate to the sender
    """
    pubsub = app["aredis"].pubsub()
    async with pubsub as p:
        await p.subscribe(PUBSUB_CHANNEL)
        await send_finished_query_to_websockets(p, app)
        await p.unsubscribe(PUBSUB_CHANNEL)


async def on_shutdown(app):
    """
    Close websocket connections on app shutdown
    """
    for (ws, uid) in set(app["websockets"].values()):
        await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message="Server shutdown")


async def start_background_tasks(app):
    """
    Start the thread that listens to redis pubsub
    """
    app["redis_listener"] = asyncio.create_task(_listen_to_redis_for_queries(app))


async def cleanup_background_tasks(app):
    """
    Stop the redis listener
    """
    app["redis_listener"].cancel()
    await app["redis_listener"]


async def create_app():

    app = web.Application()
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

    resource = cors.add(app.router.add_resource("/validate"))
    cors.add(resource.add_route("POST", validate))

    resource = cors.add(app.router.add_resource("/video"))
    cors.add(resource.add_route("GET", video))

    resource = cors.add(app.router.add_resource("/ws"))
    cors.add(resource.add_route("GET", sock))

    resource = cors.add(app.router.add_resource("/document/{doc_id}"))
    cors.add(resource.add_route("POST", document))

    resource = cors.add(app.router.add_resource("/settings"))
    cors.add(resource.add_route("GET", lama_user_data))

    resource = cors.add(app.router.add_resource("/check-file-permissions"))
    cors.add(resource.add_route("GET", check_file_permissions))

    conn = f"postgresql://{USER}:{PASSWORD}@localhost:{tunnel.local_bind_port}/{DBNAME}"
    app["db_conn"] = await asyncpg.connect(conn)
    # we keep two redis connections, for reasons
    app["aredis"] = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    app["redis"] = Redis(host=REDIS_HOST, port=REDIS_PORT)
    timeout = int(os.getenv("QUERY_TIMEOUT"))
    app["query"] = Queue(connection=app["redis"], job_timeout=timeout)
    app["export"] = Queue(connection=app["redis"], job_timeout=3000)
    app["query_service"] = QueryService(app)
    app["query_service"].get_config()

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


if __name__ == "__main__":
    uvloop.install()  # documentation has this and the below...
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app = asyncio.run(create_app())
    # web.run_app(app, port=9090)

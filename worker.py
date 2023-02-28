#!/usr/bin/env python3

import os
import sys
from rq import Connection, Worker
from rq.job import Job

from redis import Redis

from sshtunnel import SSHTunnelForwarder
import asyncpg
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

import asyncio
import uvloop


load_dotenv(override=True)

USER = os.getenv("SQL_USERNAME")
PASSWORD = os.getenv("SQL_PASSWORD")
HOST = os.getenv("SQL_HOST")
DBNAME = os.getenv("SQL_DATABASE")
PORT = int(os.getenv("SQL_PORT"))
rhost, rport = os.getenv("REDIS_URL").rsplit(":", 1)
REDIS_HOST = rhost.split("/")[-1].strip()
REDIS_PORT = int(rport.strip())


tunnel = SSHTunnelForwarder(
    os.getenv("SSH_HOST"),
    ssh_username=os.getenv("SSH_USER"),
    ssh_password=None,
    ssh_pkey=os.getenv("SSH_PKEY"),
    remote_bind_address=(HOST, PORT),
)

tunnel.start()


async def go():
    connstr = (
        f"postgresql://{USER}:{PASSWORD}@localhost:{tunnel.local_bind_port}/{DBNAME}"
    )
    # conn = psycopg2.connect(connstr)
    pool = AsyncConnectionPool(
        connstr, num_workers=8, min_size=8, timeout=60, open=False
    )

    class MyJob(Job):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            # self._db_conn = conn
            self._pool = pool
            self._redis = Redis(host=REDIS_HOST, port=REDIS_PORT)
            self._redis.pubsub()

    class MyWorker(Worker):
        job_class = MyJob

    with Connection():
        w = MyWorker(["default"])
        w.work()


if __name__ == "__main__":

    # go() # just do it sync right now

    uvloop.install()  # documentation has this and the below...
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app = asyncio.run(go())

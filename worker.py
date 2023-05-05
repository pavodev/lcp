#!/usr/bin/env python3

import os
import sys

from rq.connections import Connection
from rq.job import Job
from rq.worker import Worker

from redis import Redis

import psycopg

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
from sshtunnel import SSHTunnelForwarder

import asyncio
import uvloop


load_dotenv(override=True)

UPLOAD_USER = os.getenv("SQL_UPLOAD_USERNAME")
QUERY_USER = os.getenv("SQL_QUERY_USERNAME")
UPLOAD_PASSWORD = os.getenv("SQL_UPLOAD_PASSWORD")
QUERY_PASSWORD = os.getenv("SQL_QUERY_PASSWORD")
HOST = os.getenv("SQL_HOST")
DBNAME = os.getenv("SQL_DATABASE")
PORT = int(os.getenv("SQL_PORT", 25432))
rhost, rport = os.environ["REDIS_URL"].rsplit(":", 1)
REDIS_HOST = rhost.split("/")[-1].strip()
REDIS_PORT = int(rport.strip())


if os.getenv("SSH_HOST"):
    tunnel = SSHTunnelForwarder(
        os.getenv("SSH_HOST"),
        ssh_username=os.getenv("SSH_USER"),
        ssh_password=None,
        ssh_pkey=os.getenv("SSH_PKEY"),
        remote_bind_address=(HOST, PORT),
    )
    tunnel.start()
else:
    tunnel = None

if tunnel:
    upload_connstr = f"postgresql://{UPLOAD_USER}:{UPLOAD_PASSWORD}@localhost:{tunnel.local_bind_port}/{DBNAME}"
    query_connstr = f"postgresql://{QUERY_USER}:{QUERY_PASSWORD}@localhost:{tunnel.local_bind_port}/{DBNAME}"
else:
    upload_connstr = (
        f"postgresql://{UPLOAD_USER}:{UPLOAD_PASSWORD}@{HOST}:{PORT}/{DBNAME}"
    )
    query_connstr = f"postgresql://{QUERY_USER}:{QUERY_PASSWORD}@{HOST}:{PORT}/{DBNAME}"

pool = AsyncConnectionPool(
    query_connstr, num_workers=8, min_size=8, timeout=60, open=False
)
upool = AsyncConnectionPool(
    upload_connstr, num_workers=8, min_size=8, timeout=60, open=False
)

conn = asyncio.run(psycopg.AsyncConnection.connect(upload_connstr))


class MyJob(Job):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._connstr = upload_connstr
        self._db_conn = conn
        self._pool = pool
        self._upool = upool
        self._redis = Redis(host=REDIS_HOST, port=REDIS_PORT)
        self._redis.pubsub()


class MyWorker(Worker):
    job_class = MyJob


async def go():

    with Connection():
        w = MyWorker(["default"])
        w.work()


if __name__ == "__main__":

    # go() # just do it sync right now

    uvloop.install()  # documentation has this and the below...
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app = asyncio.run(go())

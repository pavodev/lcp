#!/usr/bin/env python3

import os
import sys

from rq.connections import Connection
from rq.job import Job
from rq.worker import Worker

from redis import Redis

import psycopg

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool, AsyncNullConnectionPool
from sshtunnel import SSHTunnelForwarder

import asyncio
import uvloop


load_dotenv(override=True)

UPLOAD_USER = os.environ["SQL_UPLOAD_USERNAME"]
QUERY_USER = os.environ["SQL_QUERY_USERNAME"]
UPLOAD_PASSWORD = os.environ["SQL_UPLOAD_PASSWORD"]
QUERY_PASSWORD = os.environ["SQL_QUERY_PASSWORD"]
HOST = os.environ["SQL_HOST"]
DBNAME = os.environ["SQL_DATABASE"]
_UPLOAD_POOL = os.getenv("UPLOAD_USE_POOL", "false")
UPLOAD_POOL = _UPLOAD_POOL.strip().lower() not in ("false", "no", "0", "")
MAX_CONCURRENT = int(os.getenv("IMPORT_MAX_CONCURRENT", 1))
REDIS_DB_INDEX = int(os.getenv("REDIS_DB_INDEX", 0))

QUERY_MIN_NUM_CONNS = int(os.getenv("QUERY_MIN_NUM_CONNECTIONS", 8))
IMPORT_MIN_NUM_CONNS = int(os.getenv("IMPORT_MIN_NUM_CONNECTIONS", 8))
IMPORT_MIN_NUM_CONNS = max(IMPORT_MIN_NUM_CONNS, MAX_CONCURRENT)

QUERY_MAX_NUM_CONNS = int(os.getenv("QUERY_MAX_NUM_CONNECTIONS", 8))
IMPORT_MAX_NUM_CONNS = int(os.getenv("IMPORT_MAX_NUM_CONNECTIONS", 8))
IMPORT_MAX_NUM_CONNS = max(IMPORT_MAX_NUM_CONNS, MAX_CONCURRENT)

POOL_WORKERS = int(os.getenv("POOL_NUM_WORKERS", 3))
PORT = int(os.getenv("SQL_PORT", 25432))
_RHOST, _RPORT = os.environ["REDIS_URL"].rsplit(":", 1)
REDIS_HOST = _RHOST.split("/")[-1].strip()
REDIS_PORT = int(_RPORT.strip())


if os.getenv("SSH_HOST"):
    tunnel = SSHTunnelForwarder(
        os.environ["SSH_HOST"],
        ssh_username=os.environ["SSH_USER"],
        ssh_password=None,
        ssh_pkey=os.environ["SSH_PKEY"],
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
    query_connstr,
    name="query-connection",
    num_workers=POOL_WORKERS,
    min_size=QUERY_MIN_NUM_CONNS,
    max_size=QUERY_MAX_NUM_CONNS,
    timeout=60,
    open=False,
)
upload_conn_type = AsyncNullConnectionPool if not UPLOAD_POOL else AsyncConnectionPool
min_size = IMPORT_MIN_NUM_CONNS if UPLOAD_POOL else 0
max_size = IMPORT_MAX_NUM_CONNS if UPLOAD_POOL else 0
upool = upload_conn_type(
    upload_connstr,
    name="upload-connection",
    num_workers=POOL_WORKERS,
    min_size=min_size,
    max_size=max_size,
    timeout=60,
    open=False,
)

# conn = asyncio.run(psycopg.AsyncConnection.connect(upload_connstr))


class MyJob(Job):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._connstr = upload_connstr
        # self._db_conn = conn
        self._pool = pool
        self._upool = upool
        self._redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_INDEX)
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

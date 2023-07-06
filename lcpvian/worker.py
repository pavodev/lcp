#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import logging
import os
import sys

from typing import Any

import uvloop

from dotenv import load_dotenv
from redis import Redis
from rq.connections import Connection
from rq.job import Job
from rq.worker import Worker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from sshtunnel import SSHTunnelForwarder

load_dotenv(override=True)

if os.getenv("CUSTOM_DOTENV"):
    load_dotenv(os.getenv("CUSTOM_DOTENV"), override=True)


SENTRY_DSN = os.getenv("SENTRY_DSN", None)

if SENTRY_DSN:

    import sentry_sdk
    from sentry_sdk.integrations.rq import RqIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.WARNING,
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[RqIntegration(), sentry_logging],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", 1.0)),
        environment=os.getenv("SENTRY_ENVIRONMENT", "lcp"),
    )


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
UPLOAD_MIN_NUM_CONNS = int(os.getenv("UPLOAD_MIN_NUM_CONNECTIONS", 8))
UPLOAD_MIN_NUM_CONNS = max(UPLOAD_MIN_NUM_CONNS, MAX_CONCURRENT) if UPLOAD_POOL else 0
QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", 1000))

QUERY_MAX_NUM_CONNS = int(os.getenv("QUERY_MAX_NUM_CONNECTIONS", 8))
UPLOAD_MAX_NUM_CONNS = int(os.getenv("UPLOAD_MAX_NUM_CONNECTIONS", 8))
UPLOAD_MAX_NUM_CONNS = max(UPLOAD_MAX_NUM_CONNS, MAX_CONCURRENT) if UPLOAD_POOL else 0
UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", 43200))

POOL_WORKERS = int(os.getenv("POOL_NUM_WORKERS", 3))
PORT = int(os.getenv("SQL_PORT", 25432))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


tunnel: SSHTunnelForwarder
if os.getenv("SSH_HOST"):
    tunnel = SSHTunnelForwarder(
        os.environ["SSH_HOST"],
        ssh_username=os.environ["SSH_USER"],
        ssh_password=None,
        ssh_pkey=os.environ["SSH_PKEY"],
        remote_bind_address=(HOST, PORT),
    )
    tunnel.start()
    HOST = "localhost"
    PORT = tunnel.local_bind_port


upload_connstr = (
    f"postgresql+asyncpg://{UPLOAD_USER}:{UPLOAD_PASSWORD}@{HOST}:{PORT}/{DBNAME}"
)
query_connstr = (
    f"postgresql+asyncpg://{QUERY_USER}:{QUERY_PASSWORD}@{HOST}:{PORT}/{DBNAME}"
)


query_kwargs = dict(
    pool_size=QUERY_MAX_NUM_CONNS,
    connect_args={
        "timeout": QUERY_TIMEOUT,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {"jit": "off"},
    },
    echo_pool=True,
)
upload_kwargs = dict(
    pool_size=UPLOAD_MAX_NUM_CONNS,
    connect_args={
        "timeout": UPLOAD_TIMEOUT,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {"jit": "off"},
    },
    echo_pool=True,
)
if not UPLOAD_POOL:
    upload_kwargs["pool_class"] = NullPool


class SQLJob(Job):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args)
        self._redis: Redis[bytes] = Redis.from_url(f"{REDIS_URL}/{REDIS_DB_INDEX}")
        self._redis.pubsub()
        self._pool = create_async_engine(query_connstr, **query_kwargs)
        self._upool = create_async_engine(upload_connstr, **upload_kwargs)


class MyWorker(Worker):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["job_class"] = SQLJob
        super().__init__(*args, **kwargs)


async def work() -> None:

    with Connection():
        w = MyWorker(["internal", "query", "background"])
        w.work()


def start_worker() -> None:

    try:
        if sys.version_info >= (3, 11):
            with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
                runner.run(work())
        else:
            uvloop.install()
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            asyncio.run(work())
    except KeyboardInterrupt:
        print("Worker stopped.")


if __name__ == "__main__":
    start_worker()

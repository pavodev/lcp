from __future__ import annotations

import json
import logging
import os
import shutil
import traceback

from typing import cast

import psycopg

from rq.job import get_current_job

from .configure import CorpusTemplate
from .impo import Importer
from .typed import Batch, JSONObject, MainCorpus
from .utils import _make_sent_query


async def _upload_data(
    project: str, user: str, room: str | None, **kwargs
) -> MainCorpus | None:
    """
    Script to be run by rq worker, convert data and upload to postgres
    """
    corpus = os.path.join("uploads", project)
    data_path = os.path.join(corpus, "_data.json")

    with open(data_path, "r") as fo:
        data: JSONObject = json.load(fo)

    constraints = cast(list[str], data["constraints"])
    perms = cast(str, data["perms"])
    constraints.append(perms)

    template = cast(CorpusTemplate, data["template"])

    if not template.get("project"):
        template["project"] = project

    upool = get_current_job()._upool  # type: ignore
    await upool.open()
    importer = Importer(upool, data, corpus)
    extra = {"user": user, "room": room, "project": project}
    row: MainCorpus | None = None
    try:
        msg = f"Starting corpus import for {user}: {project}"
        logging.info(msg, extra=extra)
        row = await importer.pipeline()
    except Exception as err:
        tb = traceback.format_exc()
        msg = f"Error during import/upload: {err}"
        print(msg, tb)
        extra["traceback"] = tb
        logging.error(msg, extra=extra)
        await importer.cleanup()
    finally:
        shutil.rmtree(corpus)  # todo: should we do this?
    return row


async def _create_schema(
    create: str,
    schema_name: str,
    drops: list[str] | None,
    user: str = "",
    room: str | None = None,
    **kwargs,
) -> None:
    """
    To be run by rq worker, create schema
    """
    timeout = int(os.getenv("UPLOAD_TIMEOUT", 43200))
    await get_current_job()._upool.open()  # type: ignore
    async with get_current_job()._upool.connection(timeout) as conn:  # type: ignore
        await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            try:
                if drops:
                    extra = {
                        "user": user,
                        "room": room,
                        "drops": drops,
                    }
                    msg = f"Attempting schema drop (create) * {len(drops)-1}"
                    print("Dropping/deleting:", "\n".join(drops))
                    logging.info(msg, extra=extra)
                    await cur.execute("\n".join(drops))
                print("Creating schema...\n", create)
                await cur.execute(create)
            except Exception:
                script = f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"
                extra = {
                    "user": user,
                    "room": room,
                    "schema": schema_name,
                }
                msg = f"Attempting schema drop (create): {schema_name}"
                logging.info(msg, extra=extra)
                await cur.execute(script)
    return None


async def _db_query(
    query: str,
    params: tuple = tuple(),
    config: bool = False,
    store: bool = False,
    document: bool = False,
    is_sentences: bool = False,
    resuming: bool = False,
    depends_on: str | list[str] = "",
    current_batch: Batch | None = None,
    **kwargs,
) -> list[tuple | JSONObject] | JSONObject | None:
    """
    The function queued by RQ, which executes our DB query
    """

    if is_sentences and current_batch:
        query, ids = _make_sent_query(query, depends_on, current_batch, resuming)
        params = tuple(list(params) + [ids])

    name = "_upool" if store else "_pool"
    # this open call should be made before any other db calls in the app just in case
    await getattr(get_current_job(), name).open()  # type: ignore
    timeout = int(os.getenv("QUERY_TIMEOUT", 1000))

    async with getattr(get_current_job(), name).connection(timeout) as conn:  # type: ignore
        if store:
            await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            result = await cur.execute(query, params)
            if store:
                return None
            try:
                if config or is_sentences:
                    result = await cur.fetchall()
                    return result
                if document:
                    result = await cur.fetchone()
                    return result[0]
                else:
                    return await cur.fetchall()
            except psycopg.ProgrammingError as err:
                tb = traceback.format_exc()
                print("Warning: psycopg error, no results?", err, tb)
                return []

from __future__ import annotations

import json
import logging
import os
import shutil
import traceback

from typing import Any, cast

from sqlalchemy.sql import text

from rq.job import get_current_job

from .configure import CorpusTemplate
from .impo import Importer
from .typed import DBQueryParams, JSONObject, MainCorpus, Sentence, UserQuery
from .utils import _get_sent_ids


async def _upload_data(
    project: str, user: str, room: str | None, **kwargs: dict[str, JSONObject]
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
    **kwargs: str | None,
) -> None:
    """
    To be run by rq worker, create schema
    """
    timeout = int(os.getenv("UPLOAD_TIMEOUT", 43200))
    extra = {"user": user, "room": room, "drops": drops, "schema": schema_name}

    async with get_current_job()._upool.begin() as conn:  # type: ignore
        try:
            if drops:
                msg = f"Attempting schema drop (create) * {len(drops)-1}"
                print("Dropping/deleting:", "\n".join(drops))
                logging.info(msg, extra=extra)
                await conn.execute(text("\n".join(drops)))
            print("Creating schema...\n", create)
            await conn.execute(text(create))
        except Exception:
            script = f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"
            extra.pop("drops")
            msg = f"Attempting schema drop (create): {schema_name}"
            logging.info(msg, extra=extra)
            await conn.execute(text(script))
    return None


async def _db_query(
    query: str,
    params: DBQueryParams = None,
    config: bool = False,
    store: bool = False,
    document: bool = False,
    **kwargs: str | None | int | float | bool | list[str],
) -> list[tuple] | tuple | list[JSONObject] | JSONObject | list[MainCorpus] | list[
    UserQuery
] | list[Sentence] | None:
    """
    The function queued by RQ, which executes our DB query
    """
    if "depends_on" in kwargs and "done" in kwargs:
        # this can only be done after the previous job finished...
        dep = cast(list[str] | str, kwargs["depends_on"])
        params = {"ids": _get_sent_ids(dep, cast(bool, kwargs["done"]))}

    name = "_upool" if store else "_pool"
    pool = getattr(get_current_job(), name)

    method = "begin" if store else "connect"

    if not params:
        params = {}

    async with getattr(pool, method)() as conn:

        # for eventual use in importer:
        # raw = await conn.get_raw_connection()
        # raw.cursor()._connection.copy_to_table)

        _n = 1
        while "%s" in query:
            query = query.replace("%s", f"${_n}", 1)
            _n += 1

        res = await conn.execute(text(query), params)
        if store:
            return None
        out: list[tuple] = [tuple(i) for i in res.fetchall()]
        return out

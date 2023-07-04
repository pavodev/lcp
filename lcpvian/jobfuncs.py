from __future__ import annotations

import json
import logging
import os
import shutil
import traceback

from typing import cast

from sqlalchemy.exc import SQLAlchemyError
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
    extra = {"user": user, "room": room, "drops": drops, "schema": schema_name}

    # todo: figure out how to make this block a little nicer :P
    async with get_current_job()._upool.begin() as conn:  # type: ignore
        raw = await conn.get_raw_connection()
        con = raw._connection
        async with con.transaction():
            try:
                if drops:
                    msg = f"Attempting schema drop (create) * {len(drops)-1}"
                    create = "\n".join(drops) + "\n" + create
                print("Creating schema...\n", create)
                await con.execute(create)
            except Exception:
                script = f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"
                extra.pop("drops")
                msg = f"Attempting schema drop (create): {schema_name}"
                logging.info(msg, extra=extra)
                await con.execute(script)
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
    # this can only be done after the previous job finished...
    if "depends_on" in kwargs and "sentences_query" in kwargs:
        dep = cast(list[str] | str, kwargs["depends_on"])
        total = cast(int, kwargs.get("total_results_requested"))
        offset = cast(int, kwargs.get("offset", -1))
        needed = cast(int, kwargs.get("needed", total))
        needed = max(-1, needed)  # todo: fix this earlier?
        ids: list[str] | list[int] | None = _get_sent_ids(dep, needed, offset=offset)
        if not ids:
            return []
        params = {"ids": ids}

    name = "_upool" if store else "_pool"
    pool = getattr(get_current_job(), name)
    method = "begin" if store else "connect"

    params = params or {}

    n = 1
    while "%s" in query:
        query = query.replace("%s", f"${n}", 1)
        n += 1

    async with getattr(pool, method)() as conn:
        try:
            res = await conn.execute(text(query), params)
            if store:
                return None
            out: list[tuple] = [tuple(i) for i in res.fetchall()]
            return out
        except SQLAlchemyError as err:
            print(f"SQL error: {err}")
            raise err

from __future__ import annotations

import csv
import json
import logging
import os
import pandas
import shutil
import traceback
import zipfile

from asyncpg import Range
from typing import Any, cast

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from rq.connections import get_current_connection
from rq.job import (get_current_job, Job)

from .configure import CorpusTemplate
from .impo import Importer
from .typed import DBQueryParams, JSONObject, MainCorpus, Sentence, UserQuery
from .utils import _get_sent_ids


async def _upload_data(
    project: str,
    user: str,
    room: str | None,
    debug: bool,
    **kwargs: dict[str, JSONObject | bool],
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
    importer = Importer(upool, data, corpus, debug)
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
    To be run by rq worker, create schema in DB for a new corpus
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
            return None
        params = {"ids": ids}

    name = "_upool" if store else "_pool"
    job = get_current_job()
    pool = getattr(job, name)
    method = "begin" if store else "connect"

    first_job_id = cast(str, kwargs.get("first_job", ""))
    if first_job_id:
        first_job: Job = Job.fetch(first_job_id, connection=get_current_connection())
        if first_job:
            first_job_status = first_job.get_status(refresh=True)
            if first_job_status in ("stopped", "canceled"):
                print("First job was stopped or canceled - not executing the query")
                raise SQLAlchemyError("Job canceled")

    params = params or {}

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


async def _swissdox_export(
    job_ids: dict[str,str],
    documents: dict[str,Any] = {},
    config: dict[str,Any] = {},
    underlang: str = "",
    **kwargs: str | None | int | float | bool | list[str],
) -> None:
    """
    Take all the results from the relevant jobs and write them to storage
    """
    prepared_segments_job: Job = Job.fetch(job_ids["prepared_segments"], connection=get_current_connection())
    named_entities_job: Job = Job.fetch(job_ids["named_entities"], connection=get_current_connection())

    path = os.path.join("results",config['meta'].get('name', 'anonymous_corpus'))

    if not os.path.exists(path):
        os.mkdir(path)

    ne_dict: dict[tuple[str,str],str] = {}

    # Documents
    doc_columns = [c for c in documents["columns"] if c != "id"]
    doc_indices = []
    doc_rows = []
    doc_attrs = config["layer"][config["document"]]["attributes"]
    for n, row in enumerate(documents["rows"]):
        id = row.pop("id", n)
        doc_indices.append(str(id))
        # Sanitize types -- should do the same for all dfs
        formed_row = []
        for cl in doc_columns:
            c = row.get(cl,"")
            type = doc_attrs.get(cl, doc_attrs.get("meta", {}).get(cl, {})).get("type")
            if type == "integer":
                c = int(c or 0)
            elif type in ("text","string"):
                c = str(c)
            elif cl == "char_range" and isinstance(c, Range):
                c = str(c)
            formed_row.append(c)
        doc_rows.append(formed_row)
    doc_pandas = pandas.DataFrame(data=doc_rows, index=doc_indices, columns=doc_columns)
    doc_pandas.to_feather(os.path.join(path,"documents.feather"))

    # Tokens
    seg: str = config["segment"]
    segment_mapping: dict[str,Any] = config["mapping"]["layer"][seg]
    tok_columns: list[str] = ["segment_id"]
    if "partitions" in segment_mapping and underlang:
        tok_columns += segment_mapping["partitions"][underlang[1:]]["prepared"]["columnHeaders"]
    else:
        tok_columns += segment_mapping["prepared"]["columnHeaders"]
    tok_indices = []
    tok_rows = []
    for row in prepared_segments_job.result:
        sid: str = str(row[0])
        for n, token in enumerate(row[2]):
            tok_indices.append( str(n + int(row[1])) )
            tok_rows.append( [sid, *token] )
    tok_pandas = pandas.DataFrame(data=tok_rows, index=tok_indices, columns=tok_columns)
    tok_pandas.to_feather(os.path.join(path,"tokens.feather"))

    # Named entities
    ne_nid = next(n for n, c in enumerate(cast(list, kwargs.get("ne_cols", []))) if c == "id")
    ne_colums: list[str] = [str(c) for n, c in enumerate(cast(list, kwargs.get("ne_cols", []))) if n != ne_nid]
    ne_indices = []
    ne_rows = []
    for row in named_entities_job.result:
        ne_indices.append(str(row[ne_nid]))
        ne_rows.append([str(r) for n, r in enumerate(row) if n != ne_nid])
    ne_pandas = pandas.DataFrame(data=ne_rows, index=ne_indices, columns=ne_colums)
    ne_pandas.to_feather(os.path.join(path,"namedentities.feather"))

    # Zip file
    with zipfile.ZipFile(os.path.join(path,"swissdox.zip"), mode="w") as archive:
        # archive.write(f"results/{corpus_index}/documents.tsv", "documents.tsv")
        archive.write(os.path.join(path,"documents.feather"), "documents.feather")
        archive.write(os.path.join(path,"tokens.feather"), "tokens.feather")
        archive.write(os.path.join(path,"namedentities.feather"), "namedentities.feather")

    return None
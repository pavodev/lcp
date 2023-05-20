from __future__ import annotations

import json
import os
import shutil

from typing import Any, List, Tuple

from rq.job import get_current_job

from .impo import Importer
from .utils import _make_sent_query


async def _upload_data(project: str, user: str, room: str | None, **kwargs) -> None:
    """
    Script to be run by rq worker, convert data and upload to postgres
    """
    # user and room are not really used yet...
    # user: Optional[str] = kwargs["user"]
    # room: Optional[str] = kwargs.get("room")

    # get template and understand it
    corpus = os.path.join("uploads", project)
    data_path = os.path.join(corpus, "_data.json")

    with open(data_path, "r") as fo:
        data = json.load(fo)

    template = data["template"]
    if "project" not in template:
        template["project"] = project
    mapping = data["mapping"]
    schema_name = template["schema_name"]
    constraints = data["constraints"]
    refs = data["refs"]
    perms = data["perms"]
    constraints.append(perms)
    create = data["prep_seg_create"]
    inserts = data["prep_seg_insert"]
    batches = data["batchnames"]
    extra = len(constraints) + len(batches)

    upool = get_current_job()._upool  # type: ignore
    await upool.open()

    args = (upool, template, mapping, corpus, schema_name, len(batches), extra)
    importer = Importer(*args)
    try:
        importer.update_progress("Importing corpus...")
        await importer.import_corpus()
        perc = int(importer.corpus_size / 100.0)
        fake_total = importer.corpus_size + (perc * extra)
        pro = f":progress:-1:{perc}:{fake_total} == {extra} extras"
        cons = "\n\n".join(constraints)
        importer.update_progress(f"Setting constraints...\n\n{cons}")
        await importer.process_data(constraints, importer.run_script, progress=pro)
        if len(refs):
            strung = "\n".join(refs)
            importer.update_progress(f"Running:\n{strung}")
            await importer.run_script(strung)
        await importer.prepare_segments(create, inserts, batches, progress=pro)
        importer.update_progress("Adding to corpus list...")
        await importer.create_entry_maincorpus()
    except Exception as err:
        print(f"Error: {err}")
        try:
            await importer.cleanup()
        except Exception:
            pass
        raise err
    finally:
        shutil.rmtree(corpus)  # todo: should we do this?
    return None


async def _create_schema(
    create: str, schema_name: str, drops: List[str] | None, **kwargs
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
                    await cur.execute("\n".join(drops))
                print("Creating schema...\n", create)
                await cur.execute(create)
            except Exception:
                script = f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"
                await cur.execute(script)
    return None


async def _db_query(
    query: str,
    params: Tuple = tuple(),
    config: bool = False,
    store: bool = False,
    single: bool = False,
    is_sentences: bool = False,
    resuming: bool = False,
    depends_on: str | List[str] = "",
    current_batch: Tuple[int, str, str, int] | None = None,
    **kwargs,
) -> List[Tuple[Any]] | None:
    """
    The function queued by RQ, which executes our DB query
    """

    if is_sentences and current_batch:
        query = _make_sent_query(query, depends_on, current_batch, resuming)

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
            if config or is_sentences:
                result = await cur.fetchall()
                return result
            if single:
                result = await cur.fetchone()
                result = result[0]
            else:
                result = await cur.fetchall()
            return result

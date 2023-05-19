from __future__ import annotations

import json
import os
import shutil

from collections import Counter
from rq.connections import get_current_connection
from rq.job import Job, get_current_job
from typing import Any, Dict, List, Tuple

from .impo import Importer
from .utils import Interrupted, _get_kwics


async def _upload_data(**kwargs) -> None:
    """
    Script to be run by rq worker, convert data and upload to postgres
    """
    # user and room are not really used yet...
    # user: Optional[str] = kwargs["user"]
    # room: Optional[str] = kwargs.get("room")

    # get template and understand it
    corpus = os.path.join("uploads", kwargs["project"])
    data_path = os.path.join(corpus, "_data.json")

    with open(data_path, "r") as fo:
        data = json.load(fo)

    template = data["template"]
    if "project" not in template:
        template["project"] = kwargs["project"]
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


async def _create_schema(**kwargs) -> None:
    """
    To be run by rq worker, create schema
    """
    drops = kwargs["drops"]
    schema_name = kwargs["schema_name"]
    timeout = int(os.getenv("UPLOAD_TIMEOUT", 43200))
    await get_current_job()._upool.open()  # type: ignore
    async with get_current_job()._upool.connection(timeout) as conn:  # type: ignore
        await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            try:
                if drops:
                    await cur.execute("\n".join(drops))
                print("Creating schema...\n", kwargs["create"])
                await cur.execute(kwargs["create"])
            except Exception:
                script = f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"
                await cur.execute(script)
    return None


def _make_sent_query(
    query: str,
    associated: str | List[str],
    current_batch: Tuple[int, str, str, int],
    resuming: bool,
):
    """
    Helper to format the query to retrieve sentences: add sent ids
    """
    conn = get_current_connection()
    if isinstance(associated, list):
        associated = associated[-1]
    job = Job.fetch(associated, connection=conn)
    hit_limit = job.meta.get("hit_limit")
    if job.get_status(refresh=True) in ("stopped", "canceled"):
        raise Interrupted()
    if job.result is None:
        raise Interrupted()
    if not job.result:
        return []
    prev_results = job.result
    # so we don't double count on resuming
    if resuming:
        start_at = job.meta.get("start_at", 0)
    else:
        start_at = 0

    seg_ids = set()
    result_sets = job.kwargs["meta_json"]
    kwics = _get_kwics(result_sets)
    counts: Dict[int, int] = Counter()

    for res in prev_results:
        key = int(res[0])
        rest = res[1]
        if key in kwics:
            counts[key] += 1
            if start_at and counts[key] < start_at:
                continue
            elif hit_limit is not False and counts[key] > hit_limit:
                continue
            seg_ids.add(str(rest[0]))

    form = ", ".join(sorted(seg_ids))

    return query.format(schema=current_batch[1], table=current_batch[2], allowed=form)


async def _db_query(**kwargs) -> List[Tuple[Any]] | None:
    """
    The function queued by RQ, which executes our DB query
    """
    query: str = kwargs["query"]
    single_result: bool = kwargs.get("single", False)
    params = kwargs.get("params", tuple())
    is_config: bool = kwargs.get("config", False)
    is_store: bool = kwargs.get("store", False)
    is_sentences: bool = kwargs.get("is_sentences", False)

    if is_sentences:
        current_batch = kwargs["current_batch"]
        resuming = kwargs.get("resuming", False)
        query = _make_sent_query(query, kwargs["depends_on"], current_batch, resuming)

    name = "_upool" if is_store else "_pool"
    # this open call should be made before any other db calls in the app just in case
    await getattr(get_current_job(), name).open()  # type: ignore
    timeout = int(os.getenv("QUERY_TIMEOUT", 1000))

    async with getattr(get_current_job(), name).connection(timeout) as conn:  # type: ignore
        if is_store:
            await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            result = await cur.execute(query, params)
            if is_store:
                return None
            if is_config or is_sentences:
                result = await cur.fetchall()
                return result
            if single_result:
                result = await cur.fetchone()
                result = result[0]
            else:
                result = await cur.fetchall()
            return result

import json
import os
import shutil

from collections import Counter
from rq.connections import get_current_connection
from rq.job import Job, get_current_job
from typing import Any, Dict, List, Optional, Tuple, Union

from .impo import Importer
from .utils import Interrupted, _get_kwics


async def _upload_data(**kwargs) -> bool:
    """
    Script to be run by rq worker, convert data and upload to postgres
    """
    # user and room are not really used yet...
    # user: Optional[str] = kwargs["user"]
    # room: Optional[str] = kwargs.get("room")

    # get template and understand it
    corpus_dir = os.path.join("uploads", kwargs["project"])
    data_path = os.path.join(corpus_dir, "_data.json")

    with open(data_path, "r") as fo:
        data = json.load(fo)

    template = data["template"]
    if "project" not in template:
        template["project"] = kwargs["project"]
    mapping = data["mapping"]
    constraints = data["main_constraints"]
    # todo: add this back when order problem is solved (no multiple keys on document)
    # constrs = [i for i in constraints.splitlines() if i.strip()]
    create = data["prep_seg_create"]
    inserts = data["prep_seg_insert"]
    batches = data["batchnames"]

    await get_current_job()._upool.open()

    importer = Importer(get_current_job()._upool, template, mapping, corpus_dir)
    try:
        importer.update_progress("Importing corpus...")
        await importer.import_corpus()
        importer.update_progress(f"Setting constraints...\n\n{constraints}")
        # todo: add this back when order problem is solved
        # await importer.process_data(
        #    importer.max_concurrent, constrs, importer.run_script, *tuple()
        # )
        await importer.run_script(constraints)
        await importer.prepare_segments(create, inserts, batches)
        importer.update_progress("Adding to corpus list...")
        await importer.create_entry_maincorpus()
    except Exception as err:
        print(f"Error: {err}")
        raise err
    finally:
        shutil.rmtree(corpus_dir)  # todo: should we do this?
    return True


async def _create_schema(**kwargs) -> None:
    """
    To be run by rq worker, create schema
    """
    timeout = int(os.getenv("UPLOAD_TIMEOUT", 43200))
    await get_current_job()._upool.open()
    async with get_current_job()._upool.connection(timeout) as conn:
        await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            print("Creating schema...\n", kwargs["create"])
            await cur.execute(kwargs["create"])
    return None


def _make_sent_query(
    query: str,
    associated: Union[str, List[str]],
    current_batch: Tuple[int, str, str],
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
    result_sets = job.meta["result_sets"]
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


async def _db_query(query: str, **kwargs) -> Optional[Union[Dict, List]]:
    """
    The function queued by RQ, which executes our DB query
    """
    single_result = kwargs.get("single", False)
    params = kwargs.get("params", tuple())
    is_config = kwargs.get("config", False)
    is_store = kwargs.get("store", False)
    is_sentences = kwargs.get("is_sentences", False)

    if is_sentences:
        current_batch = kwargs["current_batch"]
        resuming = kwargs.get("resuming", False)
        query = _make_sent_query(query, kwargs["depends_on"], current_batch, resuming)

    name = "_upool" if is_store else "_pool"
    # this open call should be made before any other db calls in the app just in case
    await getattr(get_current_job(), name).open()
    timeout = int(os.getenv("QUERY_TIMEOUT", 1000))

    async with getattr(get_current_job(), name).connection(timeout) as conn:
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

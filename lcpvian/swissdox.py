from rq import Callback, Queue
from rq.connections import get_current_connection
from rq.job import Job
from rq.registry import FinishedJobRegistry
from typing import Any, cast

from .callbacks import _export_complete, _general_failure
from .jobfuncs import _db_query, _swissdox_export
from .utils import (
    hasher,
    META_QUERY_REGEXP,
)

import json
import re

EXPORT_TTL = 5000

SWISSDOX_PREPARED_QUERY = """SELECT ps.content, sg.char_range
FROM "{schema}".prepared_{seg_table}{underlang} ps
CROSS JOIN "{schema}".{seg_table}{underlang}0 sg
WHERE ps.{seg_table}_id = sg.{seg_table}_id
AND {doc_multi_range} @> sg.char_range;"""

SWISSDOX_NE_QUERY = """SELECT {ne_selects_str}
FROM "{schema}".{ne_table} ne {ne_joins_str}
WHERE {ne_wheres_str};"""
SWISSDOX_NE_SELECTS = ["form", "type"]


async def swissdox_query(query: str, use_cache: bool = True) -> Job:
    """
    Here we send the query to RQ and therefore to redis
    """
    conn = get_current_connection()

    hashed = str(hasher(query))
    job: Job | None

    if use_cache:
        try:
            job = Job.fetch(hashed, connection=conn)
            if job is not None:
                return cast(Job, job)
        except:
            pass

    q = Queue("background", connection=conn)
    job = q.enqueue(
        _db_query,
        # on_success=Callback(_query, self.timeout),
        on_failure=Callback(_general_failure, EXPORT_TTL),
        result_ttl=EXPORT_TTL,
        job_timeout=EXPORT_TTL,
        job_id=hashed,
        args=(query,),
    )
    return cast(Job, job)


async def export_swissdox(
    # app: web.Application,
    first_job_id: str,
    underlang: str,
    config,
    download=False,
    **kwargs,
) -> Job:
    """
    Schedule jobs to fetch all the prepared segments and named entities associated with the matched documents
    Return a job depending on the former to execute _swissdox_export (see jobfuncs)
    """
    # conn = app["redis"]
    conn = get_current_connection()

    finished_jobs = [
        Job.fetch(jid, connection=conn)
        for registry in [
            FinishedJobRegistry(name=x, connection=conn)
            for x in ("query", "background")
        ]
        for jid in registry.get_job_ids()
    ]
    jobs = [
        j
        for j in finished_jobs
        if j.id == first_job_id or cast(dict, j.kwargs).get("first_job") == first_job_id
    ]

    meta_jobs: list[Job] = [j for j in jobs if cast(dict, j.kwargs).get("meta_query")]

    document_layer: str = config["firstClass"]["document"]

    documents: dict[str, Any] = {"columns": set({}), "rows": [], "ranges": dict({})}
    for j in meta_jobs:
        if not j.result:
            continue
        cols_from_sql = re.match(
            META_QUERY_REGEXP, cast(dict, j.kwargs).get("meta_query", "")
        )
        if not cols_from_sql:
            continue
        column_names = [
            p.split(" AS ")[1].strip() for p in cols_from_sql[1].split(", ")
        ]
        doc_columns: dict[str, int] = {
            p[len(f"{document_layer}_") :]: n + 1
            for n, p in enumerate(column_names)
            if p.startswith(f"{document_layer}_")
        }
        if not doc_columns:
            continue
        if not documents["columns"]:
            documents["columns"] = {k for k in doc_columns if k != "meta"}
        for res in j.result:
            doc: dict[str, Any] = {}
            for col_name, ncol in doc_columns.items():
                if col_name == "meta":
                    meta_obj: dict
                    if isinstance(res[ncol], str):
                        meta_obj = json.loads(res[ncol])
                    else:
                        meta_obj = res[ncol]
                    for k, v in meta_obj.items():
                        documents["columns"].add(k)
                        doc[k] = v
                else:
                    doc[col_name] = res[ncol]
                    if col_name == "char_range":
                        documents["ranges"][int(res[ncol].lower)] = res[ncol].upper
            documents["rows"].append(doc)

    # Optimize the list of ranges to look up (merge sequential ones)
    current_range: dict = {}
    doc_ranges = []
    for l, u in documents["ranges"].items():
        if not current_range:
            current_range = {"lower": l, "upper": u}
        if u < current_range["upper"]:
            continue
        next_lower_range = current_range["upper"] + 1
        if l > next_lower_range:
            doc_ranges.append(current_range)
            current_range = {"lower": l, "upper": u}
            next_lower_range = u + 1
        if next_lower_range in documents["ranges"]:
            current_range["upper"] = documents["ranges"][next_lower_range]["upper"]
    if current_range:
        doc_ranges.append(current_range)

    doc_multi_range = ",".join([f"[{r['lower']},{r['upper']})" for r in doc_ranges])
    doc_multi_range = "'{" + doc_multi_range + "}'::int8multirange"
    schema: str = cast(str, config["schema_path"])

    seg_table: str = cast(str, config["firstClass"]["segment"]).lower()
    query_prepared_segments: str = SWISSDOX_PREPARED_QUERY.format(
        schema=schema,
        seg_table=seg_table,
        underlang=underlang,
        doc_multi_range=doc_multi_range,
    )

    ne_table = "namedentity"
    ne_mapping = config["mapping"]["layer"]["NamedEntity"]
    if "partitions" in ne_mapping and underlang:
        ne_mapping = ne_mapping["partitions"][underlang[1:]]
    if "relation" in ne_mapping:
        ne_table = ne_mapping["relation"]
    ne_cols = ["id", "char_range"]
    # ne_selects = ["ne.namedentity_id AS id", "ne.char_range AS char_range"]
    ne_selects = ["ne.char_range AS char_range"]
    ne_joins = []
    ne_wheres = [f"{doc_multi_range} @> ne.char_range"]
    ne_attributes = config["layer"]["NamedEntity"].get("attributes", {})
    # for attr_name, attr_values in ne_attributes.items():
    for attr_name in ne_attributes:
        if attr_name not in SWISSDOX_NE_SELECTS:
            continue
        ne_cols.append(attr_name)
        # if attr_values.get("type", "") == "text":
        mapping = ne_mapping.get("attributes", {}).get(attr_name, {})
        if mapping.get("type") == "relation":
            lookup_key = mapping.get("key", attr_name)
            lookup_table = mapping.get("name", attr_name)
            new_label = f"ne_{attr_name}".lower()
            join_table: str = f"{schema}.{lookup_table} {new_label}"
            formed_join_condition = f"ne.{lookup_key}_id = {new_label}.{lookup_key}_id"
            ne_joins.append(join_table)
            ne_wheres.append(formed_join_condition)
            ne_selects.append(f"{new_label}.{attr_name} AS {attr_name}")
        else:
            ne_selects.append(f"ne.{attr_name} AS {attr_name}")

    ne_selects_str = ", ".join(ne_selects)
    ne_joins_str = "\n        CROSS JOIN ".join(ne_joins)
    if ne_joins_str:
        ne_joins_str = f"\n        CROSS JOIN {ne_joins_str}"
    ne_wheres_str = "\n        AND ".join(ne_wheres)
    query_named_entities: str = SWISSDOX_NE_QUERY.format(
        ne_selects_str=ne_selects_str,
        schema=schema,
        ne_table=ne_table,
        ne_joins_str=ne_joins_str,
        ne_wheres_str=ne_wheres_str,
    )

    prepared_segments_job = await swissdox_query(query_prepared_segments)
    named_entities_job = await swissdox_query(query_named_entities)
    depends_on = [prepared_segments_job.id, named_entities_job.id]

    print("Scheduled swissdox export depending on", depends_on)
    # q = app["background"]
    q = Queue("background", connection=conn)
    return q.enqueue(
        _swissdox_export,
        on_success=Callback(_export_complete, EXPORT_TTL),
        on_failure=Callback(_general_failure, EXPORT_TTL),
        result_ttl=EXPORT_TTL,
        job_timeout=EXPORT_TTL,
        depends_on=depends_on,
        args=(
            {
                "prepared_segments": prepared_segments_job.id,
                "named_entities": named_entities_job.id,
            },
            documents,
            config,
            underlang,
        ),
        kwargs={"ne_cols": ne_cols, "download": download},
    )

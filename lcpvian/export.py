# TODO: detect closed stream and stop job

from aiohttp import web
from asyncio import sleep
from rq import Callback
from rq.connections import get_current_connection
from rq.job import Job
from rq.registry import FinishedJobRegistry
from typing import Any, cast

from .callbacks import _export_complete, _general_failure
from .jobfuncs import _swissdox_export
from .typed import JSONObject
from .utils import _determine_language

import asyncio
import json
import re

EXPORT_TTL = 5000
CHUNKS = 1000000 # SIZE OF CHUNKS TO STREAM, IN # OF CHARACTERS

def _format_kwic(args: list, columns: list, sentences: dict[str,tuple], result_meta: dict) -> tuple[str,str,dict,list]:
    kwic_name: str = result_meta.get("name","")
    attributes: list = result_meta.get("attributes", [])
    entities_attributes: dict = next((x for x in attributes if x.get("name","") == "entities"), dict({}))
    entities: list = entities_attributes.get("data", [])
    sid, matches = args
    first_token_id, prep_seg = sentences[sid]
    matching_entities: dict[str,int|list[int]] = {}
    for n in entities:
        if n.get("type") in ("sequence","set"):
            matching_entities[n['name']] = []
        else:
            matching_entities[n['name']] = 0

    tokens: list[dict] = list()
    for n, token in enumerate(prep_seg):
        token_id = int(first_token_id) + n
        for n_m, m in enumerate(matches):
            if isinstance(m, int):
                if m == token_id:
                    matching_entities[entities[n_m]['name']] = cast(int, token_id)
            elif isinstance(m, list):
                if token_id in m:
                    me: list[int] = cast(list[int], matching_entities[entities[n_m]['name']])
                    me.append(token_id)
        token_dict = {columns[n_col]: col for n_col, col in enumerate(token)}
        token_dict["token_id"] = token_id
        tokens.append(token_dict)

    return (kwic_name,sid,matching_entities,tokens)

async def kwic(jobs: list[Job], resp: Any, config):
    sentence_jobs = [j for j in jobs if j.kwargs.get("sentences_query") and not j.kwargs.get("meta_query")]
    other_jobs = [j for j in jobs if j not in sentence_jobs]

    buffer: str = ""
    for j in other_jobs:

        if 'current_batch' not in j.kwargs:
            continue
        segment_mapping = config['mapping']['layer'][config['segment']]
        columns: list = []
        if "partitions" in segment_mapping and 'languages' in j.kwargs:
            lg = j.kwargs['languages'][0]
            columns = segment_mapping['partitions'].get(lg)['prepared']['columnHeaders']
        else:
            columns = segment_mapping['prepared']['columnHeaders']

        sentence_job: Job | None = next((sj for sj in sentence_jobs if sj.kwargs.get("depends_on") == j.id), None)
        sentences: dict[str, tuple]
        if sentence_job:
            sentences = {str(uuid): (first_token_id, tokens) for (uuid, first_token_id, tokens) in sentence_job.result}
        else:
            continue

        meta = j.kwargs.get("meta_json", {}).get("result_sets", [])
        kwic_indices = [n+1 for n, o in enumerate(meta) if o.get("type") == "plain"]

        for (n_type, args) in j.result:
            # We're only handling kwic results here
            if n_type not in kwic_indices:
                continue
            try:
                kwic_name, sid, matching_entities, tokens = _format_kwic(args, columns, sentences, meta[n_type-1])
                line: str = "\t".join([str(n_type),"plain",kwic_name,json.dumps({'sid': sid, 'matches': matching_entities, 'segment': tokens})])
            except:
                # Because queries for prepared segments only fetch what's needed for previewing purposes,
                # queries with lots of matches can only output a small subset of lines
                continue
            if len(f"{buffer}{line}\n") > CHUNKS:
                resp.write(buffer)
                await sleep(0.01) # Give the machine some time to breathe!
                buffer = ""
            buffer += f"{line}\n"
    if buffer:
        resp.write(buffer)


async def export_dump(
    filepath: str,
    job_id: str,
    config: dict
) -> None:
    """
    Read the results from all the query, sentence and meta jobs and write them in dump.tsv
    """
    output = open(filepath, "w")
    output.write((("\t".join(["index","type","label","data"])+f"\n")))

    conn = get_current_connection()
    job = Job.fetch(job_id, connection=conn)
    finished_jobs = [
        Job.fetch(jid, connection=conn)
        for registry in [
            FinishedJobRegistry(name=x, connection=conn)
            for x in ("queue","background")
        ]
        for jid in registry.get_job_ids()
    ]
    associated_jobs = [j for j in finished_jobs if j.kwargs.get("first_job") == job_id]

    meta = job.kwargs.get("meta_json", {}).get("result_sets", {})

    # Write KWIC results
    if next((m for m in meta if m.get("type")=="plain"),None):
        await kwic([job, *associated_jobs], output, config)

    # Write non-KWIC results
    for n_type, data in job.meta.get("all_non_kwic_results", {}).items():
        if n_type in (0,-1):
            continue
        info: dict = meta[n_type-1]
        name: str = info.get("name","")
        type: str = info.get("type","")
        attr: list[dict] = info.get("attributes", [])
        for line in data:
            d: dict[str,list] = {}
            for n, v in enumerate(line):
                attr_name: str = attr[n].get("name", f"entry_{n}")
                d[attr_name] = v
            output.write(("\t".join([str(n_type),type,name,json.dumps(d)])+f"\n"))

    output.close()


async def export_swissdox(
    app: web.Application,
    first_job_id: str,
    underlang: str,
    config,
) -> Job:
    """
    Schedule jobs to fetch all the prepared segments and named entities associated of the matched documents
    Return a job depending on the former to execute _swissdox_export (see jobfuncs)
    """
    finished_jobs = [
        Job.fetch(jid, connection=app["redis"])
        for registry in [
            FinishedJobRegistry(name=x, connection=app["redis"])
            for x in ("queue","background")
        ]
        for jid in registry.get_job_ids()
    ]
    jobs = [j for j in finished_jobs if j.id == first_job_id or j.kwargs.get("first_job") == first_job_id]

    meta_jobs: list[Job] = [j for j in jobs if j.kwargs.get("meta_query")]

    document_layer: str = config["firstClass"]["document"]

    documents: dict[str,Any] = {"columns": set(), "rows": [], "ranges": []}
    for j in meta_jobs:
        cols_from_sql = re.match(r"SELECT -2::int2 AS rstype, ((.+ AS .+[, ])+?)FROM.+", j.kwargs.get("meta_query",""))
        if not cols_from_sql:
            continue
        column_names = [p.split(" AS ")[1].strip() for p in cols_from_sql[1].split(", ")]
        doc_columns: dict[str,int] = {
            p[len(f"{document_layer}_"):]: n+1
            for n, p in enumerate(column_names)
            if p.startswith(f"{document_layer}_")
        }
        if not doc_columns:
            continue
        if not documents["columns"]:
            documents["columns"]= {k for k in doc_columns if k != "meta"}
        for res in j.result:
            doc: dict[str,Any] = {}
            for col_name, ncol in doc_columns.items():
                if col_name == "meta":
                    meta_obj: dict
                    if isinstance(res[ncol], str):
                        meta_obj = json.loads(res[ncol])
                    else:
                        meta_obj = res[ncol]
                    for k,v in meta_obj.items():
                        documents["columns"].add(k)
                        doc[k] = v
                else:
                    doc[col_name] = res[ncol]
                    if col_name == "char_range":
                        documents["ranges"].append(res[ncol])
            documents["rows"].append(doc)

    doc_multi_range = ",".join( [f"[{r.lower},{r.upper})" for r in documents['ranges']] )
    doc_multi_range = "'{" + doc_multi_range + "}'::int8multirange"
    schema: str = cast(str, config["schema_path"])

    seg_table: str = cast(str, config["firstClass"]["segment"])
    query_prepared_segments: str = f"""SELECT * FROM {schema}.prepared_{seg_table}{underlang} ps
        CROSS JOIN {schema}.{seg_table}{underlang}0 sg
        WHERE ps.{seg_table.lower()}_id = sg.{seg_table.lower()}_id
        AND {doc_multi_range} @> sg.char_range;"""

    ne_table = "namedentity"
    ne_mapping = config['mapping']['layer']['NamedEntity']
    if 'partitions' in ne_mapping and underlang:
        ne_mapping = ne_mapping['partitions'][underlang[1:]]
    if 'relation' in ne_mapping:
        ne_table = ne_mapping['relation']
    ne_cols = ["id", "char_range"]
    ne_selects = ["ne.namedentity_id AS id", "ne.char_range AS char_range"]
    ne_joins = []
    ne_wheres = [f"{doc_multi_range} @> ne.char_range"]
    for attr_name, attr_values in config['layer']['NamedEntity']['attributes'].items():
        ne_cols.append(attr_name)
        if attr_values.get("type", "") == "text":
            ne_selects.append(f"ne_{attr_name}.{attr_name} AS {attr_name}")
            ne_joins.append(f"{schema}.{ne_mapping['attributes'][attr_name]['name']} AS ne_{attr_name}")
            ne_wheres.append(f"ne.{attr_name}_id = ne_{attr_name}.{attr_name}_id")
            pass
        else:
            ne_selects.append(f"ne.{attr_name} AS {attr_name}")

    ne_selects_str = ", ".join( ne_selects )
    ne_joins_str = "\n".join( ne_joins )
    if ne_joins_str:
        ne_joins_str = f"\n        CROSS JOIN {ne_joins_str}"
    ne_wheres_str = "\n        AND ".join( ne_wheres )
    query_named_entities: str = f"""SELECT {ne_selects_str}
        FROM {schema}.{ne_table} ne {ne_joins_str}
        WHERE {ne_wheres_str};"""

    prepared_segments_job = await app["query_service"].swissdox_query(query_prepared_segments)
    named_entities_job = await app["query_service"].swissdox_query(query_named_entities)
    depends_on = [prepared_segments_job.id, named_entities_job.id]

    return app["background"].enqueue(
        _swissdox_export,
        on_failure=Callback(_general_failure, EXPORT_TTL),
        result_ttl=EXPORT_TTL,
        job_timeout=EXPORT_TTL,
        depends_on=depends_on,
        args=(
            {'prepared_segments': prepared_segments_job.id, 'named_entities': named_entities_job.id},
            documents,
            config,
            underlang
        ),
        kwargs={'ne_cols': ne_cols}
    )


async def export(
    app: web.Application,
    payload: JSONObject,
    first_job_id: str
) -> Job:
    """
    Schedule job(s) to export data to storage
    Called in sock.py after the last batch was queried
    """
    export_format = payload.get("format", "")
    print("All batches done! Ready to start exporting")
    corpus_conf = payload.get("config", {})
    # Retrieve the first job to get the list of all the sentence and meta jobs that export_dump depends on (also batch for swissdox)
    first_job = Job.fetch(first_job_id, connection=app["redis"])
    job: Job
    if export_format == "dump":
        depends_on = [
            jid
            for ks in ("_sent_jobs", "_meta_jobs")
            for jid in first_job.meta.get(ks, {}).keys()
        ]
        print("Scheduled dump export depending on", depends_on)
        job = app["background"].enqueue(
            export_dump,
            on_success=Callback(_export_complete, EXPORT_TTL),
            on_failure=Callback(_general_failure, EXPORT_TTL),
            result_ttl=EXPORT_TTL,
            job_timeout=EXPORT_TTL,
            depends_on=depends_on,
            args=(
                f"./results/dump_{first_job_id}.tsv",
                first_job_id,
                corpus_conf
            )
        )
    elif export_format == "swissdox":
        underlang = _determine_language( first_job.kwargs.get("current_batch")[2] ) or ""
        if underlang:
            underlang = f"_{underlang}"
        job = await export_swissdox(
            app,
            first_job_id,
            underlang,
            corpus_conf
        )

    return job
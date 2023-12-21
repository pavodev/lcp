# TODO: detect closed stream and stop job

from aiohttp import web
from asyncio import sleep
from rq.job import Job
from typing import Any, cast
from .utils import ensure_authorised

import json

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


async def kwic(jobs: list[Job], resp: web.StreamResponse, config):

    sentence_jobs = [j for j in jobs if j.kwargs.get("sentences_query")]
    other_jobs = [j for j in jobs if j not in sentence_jobs]

    buffer: str = ""
    for j in other_jobs:

        corpus_index: str = str(j.kwargs.get("current_batch")[0])
        segment_mapping = config[corpus_index]['mapping']['layer'][config[corpus_index]['segment']]
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
                await resp.write(buffer.encode("utf-8"))
                await sleep(0.01) # Give the machine some time to breathe!
                buffer = ""
            buffer += f"{line}\n"
    if buffer:
        await resp.write(buffer.encode("utf-8"))


@ensure_authorised
async def export(request: web.Request) -> web.StreamResponse:
    """
    Fetch arbitrary JSON data from redis
    """
    hashed: str = request.match_info["hashed"]
    
    response: web.StreamResponse = web.StreamResponse(
        status=200,
        reason='OK',
        headers={'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename=results.txt'},
    )
    await response.prepare(request)
    
    conn = request.app["redis"]
    job: Job = Job.fetch(hashed, connection=conn)
    finished_jobs = [
        *[Job.fetch(jid, connection=conn) for jid in request.app["query"].finished_job_registry.get_job_ids()],
        *[Job.fetch(jid, connection=conn) for jid in request.app["background"].finished_job_registry.get_job_ids()],
    ]
    associated_jobs = [j for j in finished_jobs if j.kwargs.get("first_job") == hashed]

    meta = job.kwargs.get("meta_json", {}).get("result_sets", {})

    await response.write((("\t".join(["index","type","label","data"])+f"\n")).encode("utf-8"))

    # Write KWIC results
    if next((m for m in meta if m.get("type")=="plain"),None):
        await kwic([job, *associated_jobs], response, request.app["config"])

    # Write non-KWIC results
    for n_type, data in job.meta.get("all_non_kwic_results", {}).items():
        # import pdb; pdb.set_trace()
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
            await response.write(("\t".join([str(n_type),type,name,json.dumps(d)])+f"\n").encode("utf-8"))
    
    await response.write_eof()
    return response
    
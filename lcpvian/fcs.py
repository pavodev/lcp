import asyncio
import json

from aiohttp import web
from typing import cast

from .authenticate import Authentication
from .query_classes import QueryInfo, Request
from .query_future import process_query
from .utils import LCPApplication


def _make_json_query(query: str, tok: str, seg: str) -> str:
    json_query: dict[str, list[dict]] = {
        "query": [{"unit": {"layer": seg, "label": "s"}}],
        "results": [{"label": "kwic", "resultsPlain": {"context": ["s"]}}],
    }
    words = query.split()
    assert len(words) > 0, RuntimeError("Cannot perform a search with no word")
    wunits = [
        {
            "unit": {
                "layer": tok,
                "label": f"t{n}",
                "partOf": [{"partOfStream": "s"}],
                "constraints": [
                    {
                        "comparison": {
                            "left": {"reference": "form"},
                            "comparator": "=",
                            "right": {"string": w},
                        }
                    }
                ],
            }
        }
        for n, w in enumerate(words, start=1)
    ]
    if len(wunits) == 1:
        json_query["query"].append(wunits[0])
        json_query["results"][0]["resultsPlain"]["entities"] = ["t1"]
    else:
        seq = {
            "sequence": {"partOf": [{"partOfStream": "s"}]},
            "label": "seq",
            "members": wunits,
        }
        json_query["query"].append(seq)
        json_query["results"][0]["resultsPlain"]["entities"] = ["seq"]
    return json.dumps(json_query)


async def _check_request_complete(qi: QueryInfo, request: Request):
    while 1:
        await asyncio.sleep(0.5)
        if not qi.has_request(request):
            break
    return


def _make_search_response(buffers, request_ids: dict[str, dict]) -> str:
    resp = """<?xml version='1.0' encoding='utf-8'?>
<sru:searchRetrieveResponse xmlns:sru="http://www.loc.gov/zing/srw/">
  <sru:version>1.2</sru:version>"""
    records: list[str] = []
    for rid, corpus in request_ids.items():
        payload = buffers[rid]
        cid = corpus["cid"]
        shortname = corpus["conf"]["shortname"]
        column_names: list[str] = corpus["conf"]["column_names"]
        space_after_id = (
            column_names.index("spaceAfter") if "spaceAfter" in column_names else -1
        )
        form_id = column_names.index("form")
        if "1" not in payload or "-1" not in payload:
            continue
        for sid, hits in payload["1"]:
            offset, tokens, *annotations = payload["-1"][sid]
            prep_seg = ""
            in_hit = False
            for n, token in enumerate(tokens):
                token_str = token[form_id]
                is_hit = offset + n in hits or offset + n in [
                    y for x in hits if isinstance(x, list) for y in x
                ]
                if in_hit and not is_hit:
                    after_space = prep_seg and prep_seg[-1] == " "
                    prep_seg = (
                        prep_seg.rstrip() + "</hits:Hit>" + (" " if after_space else "")
                    )
                if not in_hit and is_hit:
                    token_str = f"<hits:Hit>{token_str}"
                in_hit = is_hit
                if space_after_id < 0 or token[space_after_id] == "1":
                    token_str += " "
                prep_seg += token_str
            prep_seg = prep_seg.strip()
            if in_hit:
                prep_seg += "</hits:Hist>"
            records.append(
                f"""
    <sruc:record>
      <sru:recordSchema>http://clarin.eu/fcs/resource</sru:recordSchema>
      <sru:recordPacking>xml</sru:recordPacking>
      <sru:recordData>
        <fcs:Resource xmlns:fcs="http://clarin.eu/fcs/resource" pid="https://catchphrase.linguistik.uzh.ch/query/{cid}/{shortname}">
          <fcs:ResourceFragment>
            <fcs:DataView type="application/x-clarin-fcs-hits+xml">
              <hits:Result xmlns:hits="http://clarin.eu/fcs/dataview/hits">
                {prep_seg}
              </hits:Result>
            </fcs:DataView>
          </fcs:ResourceFragment>
        </fcs:Resource>
      </sru:recordData>
      <sru:recordPosition>1</sru:recordPosition>
    </sru:record>"""
            )
    resp += f"""
  <sru:numberOfRecords>{len(records)}</sru:numberOfRecords>
  <sru:records>{''.join(records)}
  <sru:/records>
</sru:searchRetrieveResponse>"""
    return resp


async def search_retrieve(
    app: LCPApplication,
    operation: str = "searchRetrieve",
    version: str = "1.2",
    query: str = "",
    maximumRecords: str = "",
    **extra_params,
) -> str:
    authenticator = cast(Authentication, app["auth_class"](app))
    public_corpora = {
        cid: conf
        for cid, conf in app["config"].items()
        if authenticator.check_corpus_allowed(cid, conf, {}, "lcp", get_all=False)
    }
    try:
        requested: int = int(maximumRecords)
        requested = min(requested, 50)
    except:
        requested = 50

    try:
        query_buffers = app["query_buffers"]
    except:
        query_buffers = {}
        app.addkey("query_buffers", dict[str, dict], query_buffers)

    request_ids: dict[str, dict] = {}
    async with asyncio.TaskGroup() as tg:
        for cid, conf in public_corpora.items():
            tok: str = conf["token"]
            seg: str = conf["segment"]
            json_query: str = _make_json_query(query, tok, seg)
            langs = ["en"]
            partitions = conf.get("partitions", {})
            if (
                partitions
                and partitions.get("values")
                and "en" not in partitions["values"]
            ):
                continue  # only do English for now
                # langs = [next(x for x in partitions["values"])]
            (req, qi, job) = process_query(
                app,
                {
                    "appType": "lcp",
                    "corpus": cid,
                    "query": json_query,
                    "languages": langs,
                    "offset": 0,
                    "requested": requested,
                    "synchronous": True,
                },
            )
            query_buffers[req.id] = {}
            request_ids[req.id] = {"cid": cid, "conf": conf}
            tg.create_task(_check_request_complete(qi, req))
    return _make_search_response(query_buffers, request_ids)


async def get_fcs(request: web.Request) -> web.Response:
    app = cast(LCPApplication, request.app)
    q = request.rel_url.query
    operation = q["operation"]
    resp: str = ""
    if operation == "searchRetrieve":
        resp = await search_retrieve(app, **q)
    # elif operation == "explain":
    #     resp = await explain(app, **q)
    return web.Response(body=resp, content_type="application/xml")
    # return web.json_response(resp)

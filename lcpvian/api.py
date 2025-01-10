"""
api.py: tools used on the command line for showing corpora, running queries etc.
"""

import asyncio
import json
import os

try:
    from aiohttp import ClientSession
except ImportError:
    from aiohttp.client import ClientSession

from aiohttp import web
from rq.job import Job

from .exporter_xml import ExporterXml
from .query import query as submit_query
from .typed import JSONObject
from .utils import Timer


AIO_PORT = os.getenv("AIO_PORT", 9090)
QUERY_TIMEOUT = os.getenv("QUERY_TIMEOUT", 1000)


async def corpora(app_type: str = "all") -> JSONObject:
    """
    Helper to quickly show corpora in app
    """
    from .utils import load_env

    load_env()

    headers: JSONObject = {}
    jso = {"appType": app_type, "all": True}

    url = f"http://localhost:{AIO_PORT}/corpora"
    async with ClientSession() as session:
        async with session.post(url, headers=headers, json=jso) as resp:
            result: JSONObject = await resp.json()
            return result


async def query(corpus: int, query: str) -> None:
    """
    Run a query and get results from websocket
    """
    sock_url = f"http://localhost:{AIO_PORT}/ws"
    query_url = f"http://localhost:{AIO_PORT}/query"
    async with ClientSession() as session:
        async with session.ws_connect(sock_url) as ws:
            msg = {"user": "api", "room": "api", "action": "joined"}
            await ws.send_json(msg)

            from textwrap import dedent

            headers: JSONObject = {}

            jso = {
                "user": "api",
                "room": "api",
                "appType": "lcp",
                "languages": ["en"],
                "total_results_requested": 100,
                "corpora": [corpus],
                "query": dedent(query),
            }

            async with session.post(query_url, headers=headers, json=jso) as resp:
                result: JSONObject = await resp.json()
                print(f"Query submission:\n{json.dumps(result, indent=4)}\n\n")

            async for message in ws:
                payload = message.json()
                print(f"Query data:\n{json.dumps(payload, indent=4)}\n")
                if payload["status"] != "partial":
                    msg = {"user": "api", "room": "api", "action": "left"}
                    await ws.send_json(msg)
                    return None


async def api_query(request: web.Request) -> web.Response:
    req_json = await request.json()
    if hash := req_json.get("export", ""):
        config = request.app["config"]
        # Need to handle partitions
        exporter = ExporterXml(hash, request.app["redis"], config)
        await exporter.export()
        return web.json_response({"status": 200, "message": "export complete"})
    res = await submit_query(request, api=True)
    res_json = json.loads(res.text)
    job_id = res_json.get("job", "")
    try:
        finish_job_timer = Timer(QUERY_TIMEOUT)
        while True:
            assert not finish_job_timer.elapsed(), TimeoutError(
                "Could not complete the query in time"
            )
            if Job.fetch(job_id, request.app["redis"]).is_finished:
                break
            await asyncio.sleep(5)

        export_job_timer = Timer(QUERY_TIMEOUT)
        while True:
            assert not export_job_timer.elapsed(), TimeoutError(
                "Could not run export job in time"
            )
            export_job = next(
                (
                    j
                    for j in [
                        Job.fetch(jid, request.app["redis"])
                        for jid in request.app[
                            "background"
                        ].started_job_registry.get_job_ids()
                    ]
                    + [
                        Job.fetch(jid, request.app["redis"])
                        for jid in request.app[
                            "background"
                        ].finished_job_registry.get_job_ids()
                    ]
                    if job_id in j.args
                ),
                None,
            )
            if export_job and export_job.is_finished:
                break
            await asyncio.sleep(5)

        res_str = ""
        with open(export_job.args[0], "r") as export_file:
            while t := export_file.read():
                res_str += t

    except TimeoutError as err:
        return web.json_response({"error": err.strerror, "status": 408})

    return web.json_response({"results": res_str})

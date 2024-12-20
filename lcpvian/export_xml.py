from redis import Redis as RedisConnection
from rq.job import Job
from typing import Any, cast

from .utils import _get_all_jobs_from_hash

import os

RESULTS_DIR = os.getenv("RESULTS", "results")


# TODO:
#   - create an Export class initiated with jobs
#   - the generic Export class has generators that yield plain results, stats/collocs, and meta
#   - create sub-Export classes for each format, including XML


async def kwic(
    query_jobs: list[Job],
    sentence_jobs: list[Job],
    meta_jobs: list[Job],
    kwic_info: list[dict],
    config: dict,
) -> None:
    xml_folder = os.path.join(RESULTS_DIR, query_jobs[0].id, "xml")
    with open(os.path.join(xml_folder, "_kwic.xml"), "w") as output:
        for info in kwic_info:
            if (n := info.get("res_index", 0)) <= 0:
                continue
            name: str = info.get("name", "")
            typ: str = info.get("type", "")
            info_attrs: list[dict] = info.get("attributes", [])
            output.write(f"\n<result type='{typ}' name='{name}'>")

            for query_job in query_jobs:
                sentence_job: Job = next(
                    j
                    for j in sentence_jobs
                    if cast(dict, j.kwargs).get("depends_on") == query_job.id
                )
                for result_n, result in query_job.result:
                    if result_n != n:
                        continue
                    sentence_id = result[0]
                    sid, s_offset, s_tokens = next(
                        r for r in sentence_job.result if str(r[0]) == sentence_id
                    )
                    output.write(f"\n    <u id='{sid}'>")
                    for n_token, token in enumerate(s_tokens):
                        v = token[0]
                        token_id = s_offset + n_token
                        str_args = [
                            f"arg_{ta_n}='{ta_v}'"
                            for ta_n, ta_v in enumerate(token)
                            if ta_n > 0
                        ]
                        str_args.append(f"id='{token_id}'")
                        if (
                            n_attr := next(
                                (
                                    match_n
                                    for match_n, match_id in enumerate(result[1])
                                    if match_id == token_id
                                ),
                                None,
                            )
                        ) is not None:
                            label = info_attrs[1]["data"][n_attr].get(
                                "name", f"match_{n_attr}"
                            )
                            str_args.append(f"match_label='{label}'")
                        output.write(f"\n        <w {' '.join(str_args)}>{v}</w>")
                    output.write(f"\n    </u>")
            output.write(f"\n</result>")
    return


async def non_kwic(job: Job, non_kwic_info: list[dict]):
    hash: str = cast(dict, job.kwargs).get("first_job", job.id)
    xml_folder = os.path.join(RESULTS_DIR, hash, "xml")
    with open(os.path.join(xml_folder, "_non_kwic.xml"), "w") as output:
        for info in non_kwic_info:
            if (n := info.get("res_index", 0)) <= 0:
                continue
            name: str = info.get("name", "")
            typ: str = info.get("type", "")
            info_attrs: list[dict] = info.get("attributes", [])
            output.write(f"\n<result type='{typ}' name='{name}'>")
            for result_n, result in job.result:
                if result_n != n:
                    continue
                output.write(f"\n    <entry>")
                for n_attr, attr in enumerate(result):
                    info_attr = info_attrs[n_attr]
                    name_attr = info_attr.get("name", f"attr_{n_attr}")
                    output.write(f"\n        <{name_attr}>{attr}</{name_attr}>")
                output.write(f"\n    </entry>")
            output.write(f"\n</result>")


async def export(hash: str, connection: "RedisConnection[bytes]", config: dict) -> None:

    hash_folder = os.path.join(RESULTS_DIR, hash)
    if not os.path.exists(hash_folder):
        os.mkdir(hash_folder)
    xml_folder = os.path.join(hash_folder, "xml")
    if not os.path.exists(xml_folder):
        os.mkdir(xml_folder)

    query_jobs, sent_jobs, meta_jobs = _get_all_jobs_from_hash(hash, connection)

    results_info = (
        cast(dict, query_jobs[0].kwargs).get("meta_json", {}).get("result_sets", [])
    )
    results_info_with_indices = [
        {**r, "res_index": n} for n, r in enumerate(results_info, start=1)
    ]

    kwic_info = [r for r in results_info_with_indices if r.get("type") == "plain"]
    non_kwic_info = [r for r in results_info_with_indices if r not in kwic_info]

    if kwic_info:
        await kwic(query_jobs, sent_jobs, meta_jobs, kwic_info, config)
    if non_kwic_info:
        await non_kwic(query_jobs[-1], non_kwic_info)

    with open(os.path.join(xml_folder, "results.xml"), "w") as output:
        output.write("<results>")
        kwic_filename = os.path.join(xml_folder, "_kwic.xml")
        non_kwic_filename = os.path.join(xml_folder, "_non_kwic.xml")
        if os.path.exists(kwic_filename):
            with open(kwic_filename, "r") as input:
                while line := input.readline():
                    output.write(f"    {line}")
            os.remove(kwic_filename)
        if os.path.exists(non_kwic_filename):
            with open(non_kwic_filename, "r") as input:
                while line := input.readline():
                    output.write(f"    {line}")
            os.remove(non_kwic_filename)
        output.write(f"\n</results>")

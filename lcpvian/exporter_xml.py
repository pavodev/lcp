import os

from redis import Redis as RedisConnection
from rq.job import Job
from typing import Any, cast
from xml.sax.saxutils import quoteattr

from .exporter import Exporter

RESULTS_DIR = os.getenv("RESULTS", "results")


def xmlattr(val: str) -> str:
    if not val:
        return "''"
    return quoteattr(val)


# TODO:
#   - the generic Export class has generators that yield plain results, stats/collocs, and meta
#   - create sub-Export classes for each format, including XML


class ExporterXml(Exporter):

    def __init__(
        self, hash: str, connection: "RedisConnection[bytes]", config: dict
    ) -> None:
        super().__init__(hash, connection, config)

    @staticmethod
    def get_dl_path_from_hash(hash: str) -> str:
        hash_folder = os.path.join(RESULTS_DIR, hash)
        if not os.path.exists(hash_folder):
            os.mkdir(hash_folder)
        xml_folder = os.path.join(hash_folder, "xml")
        if not os.path.exists(xml_folder):
            os.mkdir(xml_folder)
        filepath = os.path.join(xml_folder, "results.xml")
        return filepath

    async def kwic(self) -> None:
        first_job = self._query_jobs[0]
        xml_folder = os.path.join(RESULTS_DIR, first_job.id, "xml")

        kwic_info = [r for r in self.results_info if r.get("type") == "plain"]

        if not kwic_info:
            return

        with open(os.path.join(xml_folder, "_kwic.xml"), "w") as output:
            # for info in kwic_info:
            #     if (n := info.get("res_index", 0)) <= 0:
            #         continue
            #     name: str = info.get("name", "")
            #     typ: str = info.get("type", "")
            #     info_attrs: list[dict] = info.get("attributes", [])
            #     output.write(f"\n<result type='{typ}' name='{name}'>")

            #     for query_job in self._query_jobs:
            #         sentence_job: Job = next(
            #             j
            #             for j in self._sentence_jobs
            #             if cast(dict, j.kwargs).get("depends_on") == query_job.id
            #         )
            #         for result_n, result in query_job.result:
            #             if result_n != n:
            #                 continue
            #             sentence_id = result[0]
            #             sid, s_offset, s_tokens = next(
            #                 r for r in sentence_job.result if str(r[0]) == sentence_id
            #             )
            #             output.write(f"\n    <u id='{sid}'>")
            #             for n_token, token in enumerate(s_tokens):
            #                 v = token[0]
            #                 token_id = s_offset + n_token
            #                 str_args = [
            #                     f"arg_{ta_n}={xmlattr(ta_v)}"
            #                     for ta_n, ta_v in enumerate(token)
            #                     if ta_n > 0
            #                 ]
            #                 str_args.append(f"id='{token_id}'")
            #                 if (
            #                     n_attr := next(
            #                         (
            #                             match_n
            #                             for match_n, match_id in enumerate(result[1])
            #                             if match_id == token_id
            #                         ),
            #                         None,
            #                     )
            #                 ) is not None:
            #                     label = info_attrs[1]["data"][n_attr].get(
            #                         "name", f"match_{n_attr}"
            #                     )
            #                     str_args.append(f"match_label={xmlattr(label)}")
            #                 output.write(f"\n        <w {' '.join(str_args)}>{v}</w>")
            #             output.write(f"\n    </u>")
            #     output.write(f"\n</result>")
            last_kwic_name = ""
            for kwic_line in self.kwic_lines():
                name, segment, tokens = (
                    kwic_line.name,
                    kwic_line.segment,
                    kwic_line.tokens,
                )
                if name != last_kwic_name:
                    if last_kwic_name:
                        output.write(f"\n</result>")
                    output.write(f"\n<result type='plain' name='{name}'>")
                    last_kwic_name = name

                output.write(f"\n    <u id='{segment.id}'>")
                n_match = 0
                for token in tokens:
                    str_args = [
                        f"{ta_n}={xmlattr(ta_v)}"
                        for ta_n, ta_v in token.attributes.items()
                    ]
                    str_args.append(f"id='{token.id}'")
                    if token.match_label:
                        str_args.append(f"match_label={xmlattr(token.match_label)}")
                    output.write(f"\n        <w {' '.join(str_args)}>{token.form}</w>")
                output.write(f"\n    </u>")
            if last_kwic_name:
                output.write(f"\n</result>")

    async def non_kwic(self) -> None:
        job = self._query_jobs[-1]
        hash: str = cast(dict, job.kwargs).get("first_job", "")
        if not hash:
            hash = job.id

        non_kwic_info = [r for r in self.results_info if r.get("type") != "plain"]

        if not non_kwic_info:
            return

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

    async def export(self, filepath: str = "") -> None:
        results_filpath = ExporterXml.get_dl_path_from_hash(self._hash)
        xml_folder = os.path.dirname(results_filpath)

        await self.kwic()
        await self.non_kwic()

        with open(results_filpath, "w") as output:
            output.write('<?xml version="1.0" encoding="utf_8"?>')
            output.write(f"\n<results>")
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

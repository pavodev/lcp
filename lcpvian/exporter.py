import json
import os

from asyncio import sleep
from collections.abc import Generator
from dataclasses import dataclass
from redis import Redis as RedisConnection
from rq.job import Job
from typing import Any, cast

from .utils import _get_all_jobs_from_hash, format_meta_lines

RESULTS_DIR = os.getenv("RESULTS", "results")
CHUNKS = 1000000  # SIZE OF CHUNKS TO STREAM, IN # OF CHARACTERS


def _format_kwic(
    args: list, columns: list, sentences: dict[str, tuple], result_meta: dict, config={}
) -> tuple[str, str, dict, list, list]:
    """
    Return (kwic_name, sid, matches, tokens, annotations) for (sid,[tokens])+
    """
    kwic_name: str = result_meta.get("name", "")
    attributes: list = result_meta.get("attributes", [])
    entities_attributes: dict = next(
        (x for x in attributes if x.get("name", "") == "entities"), dict({})
    )
    entities: list = entities_attributes.get("data", [])
    sid, matches, *frame_range = (
        args  # TODO: pass doc info to compute timestamp from frame_range
    )
    first_token_id, prep_seg, annotations = sentences[sid]
    matching_entities: dict[str, int | list[int]] = {}
    for n in entities:
        n_type = n.get("type", "")
        is_span = n_type in ("sequence", "set") or (
            config.get("layer", {}).get(n_type, {}).get("contains", "").lower()
            == config["token"].lower()
        )
        if is_span:
            matching_entities[n["name"]] = []
        else:
            matching_entities[n["name"]] = 0

    tokens: list[dict] = list()
    for n, token in enumerate(prep_seg):
        token_id = int(first_token_id) + n
        for n_m, m in enumerate(matches):
            if isinstance(m, int):
                if m == token_id:
                    matching_entities[entities[n_m]["name"]] = cast(int, token_id)
            elif isinstance(m, list):
                if token_id in m:
                    me: list[int] = cast(
                        list[int], matching_entities[entities[n_m]["name"]]
                    )
                    me.append(token_id)
        token_dict = {columns[n_col]: col for n_col, col in enumerate(token)}
        token_dict["token_id"] = token_id
        tokens.append(token_dict)
    return (kwic_name, sid, matching_entities, tokens, annotations)


@dataclass()
class Token:
    """
    Private class representing a token
    """

    id: int
    form: str
    match_label: str
    attributes: dict[str, Any]


@dataclass()
class Segment:
    """
    Private class representing a segment
    """

    id: int


@dataclass()
class KwicLine:
    """
    A KWIC line has tokens (including hits) and is attached to a segment
    It has a name (specified by the query)
    """

    tokens: list[Token]
    segment: Segment
    meta: dict[str, Any]
    name: str


class Exporter:

    def __init__(
        self,
        hash: str,
        connection: "RedisConnection[bytes]",
        config: dict,
        partition: str = "",
        total_results_requested: int = 200,
        offset: int = 0,
    ) -> None:
        self._hash: str = hash
        self._config: dict = config
        self._total_results_requested = total_results_requested
        self._offset = offset
        seg_layer: str = self._config["segment"]
        seg_mapping: dict[str, Any] = self._config["mapping"]["layer"][seg_layer]
        if "partitions" in seg_mapping and partition in seg_mapping["partitions"]:
            seg_mapping = seg_mapping["partitions"][partition]
        self._column_headers = seg_mapping["prepared"]["columnHeaders"]
        query_jobs, sent_jobs, meta_jobs = _get_all_jobs_from_hash(hash, connection)
        self._connection = connection
        self._query_jobs: list[Job] = query_jobs
        self._sentence_jobs: list[Job] = sent_jobs
        self._meta_jobs: list[Job] = meta_jobs
        self._results_info: list[dict[str, Any]] = []
        self._info: dict[str, Any] = {}

    @staticmethod
    def get_dl_path_from_hash(hash: str, offset: int = 0, requested: int = 0) -> str:
        hash_folder = os.path.join(RESULTS_DIR, hash)
        if not os.path.exists(hash_folder):
            os.mkdir(hash_folder)
        dump_folder = os.path.join(hash_folder, "plain")
        if not os.path.exists(dump_folder):
            os.mkdir(dump_folder)
        filepath = os.path.join(dump_folder, "results.tsv")
        return filepath

    @property
    def n_results(self) -> int:
        last_job = self._query_jobs[-1]
        delivered = last_job.meta.get("total_results_so_far", -1)
        return delivered

    @property
    def info(self) -> dict[str, Any]:
        if not self._info:
            self._info = {}
            last_job = self._query_jobs[-1]
            lj_meta = cast(dict, last_job.meta)
            lj_payload = cast(dict, lj_meta.get("payload", {}))
            # lj_kwargs = cast(dict, last_job.kwargs)
            self._info["name"] = self._config["meta"].get(
                "name", self._config["shortname"]
            )
            self._info["word_count"] = lj_payload["word_count"]
            self._info["percentage"] = (
                sum(x[3] for x in lj_payload["done_batches"]) / lj_payload["word_count"]
            )
            self._info["projected"] = lj_payload["projected_results"]
            self._info["query"] = lj_payload["jso"]
            self._info["submitted_at"] = str(self._query_jobs[0].enqueued_at)
            completed_at = self._query_jobs[-1].ended_at
            if self._sentence_jobs:
                completed_at = self._sentence_jobs[-1].ended_at
            if self._meta_jobs:
                completed_at = self._meta_jobs[-1].ended_at
            self._info["completed_at"] = str(completed_at)
        return self._info

    @property
    def results_info(self) -> list[dict[str, Any]]:
        if not self._results_info:
            job = self._query_jobs[0]
            results_info = (
                cast(dict, job.kwargs).get("meta_json", {}).get("result_sets", [])
            )
            self._results_info = [
                {**r, "res_index": n} for n, r in enumerate(results_info, start=1)
            ]
        return self._results_info

    def kwic_lines(self) -> Generator[KwicLine, None, None]:
        kwic_info = [r for r in self.results_info if r.get("type") == "plain"]
        total_results_requested = self._total_results_requested
        for info in kwic_info:
            if (n := info.get("res_index", 0)) <= 0:
                continue
            name: str = info.get("name", "")
            info_attrs: list[dict] = info.get("attributes", [])

            counter = 0
            for query_job in self._query_jobs:
                for result_n, result in query_job.result:
                    if result_n != n:
                        continue
                    if counter >= self._offset + total_results_requested:
                        break
                    sentence_id = result[0]
                    try:
                        sid, s_offset, s_tokens = next(
                            r
                            for sj in self._sentence_jobs
                            for r in sj.result
                            if str(r[0]) == sentence_id
                        )
                    except:
                        print(
                            "sentence missing for a kwic match",
                            counter,
                        )
                        continue
                    segment: Segment = Segment(**{"id": sid})
                    tokens: list[Token] = []
                    for n_token, token in enumerate(s_tokens):
                        v = token[0]
                        token_id = s_offset + n_token
                        token_args = {
                            self._column_headers[ta_n]: ta_v
                            for ta_n, ta_v in enumerate(token)
                            if ta_n > 0
                        }
                        match_label = ""
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
                            match_label = info_attrs[1]["data"][n_attr].get(
                                "name", f"match_{n_attr}"
                            )

                        tokens.append(
                            Token(
                                **{
                                    "id": token_id,
                                    "form": v,
                                    "match_label": match_label,
                                    "attributes": token_args,
                                }
                            )
                        )
                    counter = counter + 1
                    if counter < self._offset:
                        continue
                    yield KwicLine(
                        **{  # type: ignore
                            "segment": segment,
                            "tokens": tokens,
                            "meta": {},
                            "name": name,
                        }
                    )

    async def kwic(self) -> None:
        buffer: str = ""
        for j in self._query_jobs:
            j_kwargs = cast(dict, j.kwargs)
            if "current_batch" not in j_kwargs:
                continue
            segment_mapping = self._config["mapping"]["layer"][self._config["segment"]]
            columns: list = []
            if "partitions" in segment_mapping and "languages" in j_kwargs:
                lg = j_kwargs["languages"][0]
                columns = segment_mapping["partitions"].get(lg)["prepared"][
                    "columnHeaders"
                ]
            else:
                columns = segment_mapping["prepared"]["columnHeaders"]

            sentences: dict[str, tuple] = {}
            for sentence_job in self._sentence_jobs:
                if cast(dict, sentence_job.kwargs).get("depends_on") != j.id:
                    continue
                if not sentence_job or not sentence_job.result:
                    continue
                for row in sentence_job.result:
                    uuid: str = str(row[0])
                    first_token_id = row[1]
                    tokens = row[2]
                    annotations = []
                    if len(row) > 3:
                        annotations = row[3]
                    sentences[uuid] = (first_token_id, tokens, annotations)

            formatted_meta: dict[str, Any] = {}
            for meta_job in self._meta_jobs:
                mjk = cast(dict, meta_job.kwargs)
                if mjk.get("depends_on") == j.id:
                    continue
                if not meta_job:
                    continue
                result = meta_job.result or []
                incoming_meta: dict[str, Any] = cast(
                    dict[str, Any],
                    format_meta_lines(cast(str, mjk.get("meta_query")), result),
                )
                formatted_meta.update(incoming_meta)

            meta = j_kwargs.get("meta_json", {}).get("result_sets", [])
            kwic_indices = [
                n + 1 for n, o in enumerate(meta) if o.get("type") == "plain"
            ]

            for n_type, args in j.result:
                # We're only handling kwic results here
                if n_type not in kwic_indices:
                    continue
                try:
                    kwic_name, sid, matching_entities, tokens, annotations = (
                        _format_kwic(
                            args,
                            columns,
                            sentences,
                            meta[n_type - 1],
                            config=self._config,
                        )
                    )
                    data = {
                        "sid": sid,
                        "matches": matching_entities,
                        "segment": tokens,
                        "annotations": annotations,
                    }
                    if sid in formatted_meta:
                        # TODO: check frame_range in meta here + return frame_range from _format_kwic to compute time?
                        data["meta"] = formatted_meta[sid]
                    line: str = "\t".join(
                        [str(n_type), "plain", kwic_name, json.dumps(data)]
                    )
                except Exception as err:
                    print("Issue with _format_kwic when exporting", err)
                    # Because queries for prepared segments only fetch what's needed for previewing purposes,
                    # queries with lots of matches can only output a small subset of lines
                    continue
                if len(f"{buffer}{line}\n") > CHUNKS:
                    self._output.write(buffer)
                    await sleep(0.01)  # Give the machine some time to breathe!
                    buffer = ""
                buffer += f"{line}\n"
        if buffer:
            self._output.write(buffer)

        # Write KWIC results
        # await kwic(
        #     [*self._query_jobs, *self._sentence_jobs, *self._meta_jobs],
        #     self._output,
        #     self._config,
        # )

    async def non_kwic(self) -> None:
        job = self._query_jobs[0]
        meta = cast(dict, job.kwargs).get("meta_json", {}).get("result_sets", {})
        for n_type, data in job.meta.get("all_non_kwic_results", {}).items():
            if n_type in (0, -1):
                continue
            info: dict = meta[n_type - 1]
            name: str = info.get("name", "")
            type: str = info.get("type", "")
            attr: list[dict] = info.get("attributes", [])
            for line in data:
                d: dict[str, list] = {}
                for n, v in enumerate(line):
                    attr_name: str = attr[n].get("name", f"entry_{n}")
                    d[attr_name] = v
                self._output.write(
                    ("\t".join([str(n_type), type, name, json.dumps(d)]) + f"\n")
                )

    async def export(self, filepath: str = "") -> None:
        filepath = Exporter.get_dl_path_from_hash(
            self._hash, self._offset, self._total_results_requested
        )

        self._output = open(filepath, "w")

        first_job = self._query_jobs[0]

        self._output.write((("\t".join(["index", "type", "label", "data"]) + f"\n")))

        # Write query itself in first row
        self._output.write(
            "\t".join(
                [
                    "0",
                    "query",
                    "query",
                    json.dumps(cast(dict, first_job.kwargs).get("original_query", {})),
                ]
            )
            + f"\n"
        )

        meta = cast(dict, first_job.kwargs).get("meta_json", {}).get("result_sets", {})
        # Write KWIC results
        if next((m for m in meta if m.get("type") == "plain"), None):
            await self.kwic()

        # Write non-KWIC results
        for n_type, data in (
            cast(dict, first_job.meta).get("all_non_kwic_results", {}).items()
        ):
            if n_type in (0, -1):
                continue
            info: dict = meta[n_type - 1]
            name: str = info.get("name", "")
            type: str = info.get("type", "")
            attr: list[dict] = info.get("attributes", [])
            for line in data:
                d: dict[str, list] = {}
                for n, v in enumerate(line):
                    attr_name: str = attr[n].get("name", f"entry_{n}")
                    d[attr_name] = v
                self._output.write(
                    ("\t".join([str(n_type), type, name, json.dumps(d)]) + f"\n")
                )

        self._output.close()

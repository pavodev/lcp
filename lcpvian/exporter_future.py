# TODO: create one directory per batch in request.sent_hashes
# once request.is_done() and all the directories have stats+kwic files,
# concatenate them in a single file and delete the request

import lxml.etree
import os
import shutil

from dataclasses import dataclass
from lxml.builder import E
from rq.job import get_current_job, Job
from typing import Any, cast

# from xml.sax.saxutils import escape, quoteattr, XMLGenerator

from .query_classes import Request, QueryInfo
from .typed import CorpusConfig
from .utils import _layer_contains

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

    id: str


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
    format = "plain"

    def __init__(self, request: Request, qi: QueryInfo) -> None:
        self._request: Request = request
        self._qi: QueryInfo = qi
        self._config: dict = qi.config
        seg_layer: str = self._config["segment"]
        seg_mapping: dict[str, Any] = self._config["mapping"]["layer"][seg_layer]
        self._column_headers = seg_mapping["prepared"]["columnHeaders"]
        self._results_info: list[dict[str, Any]] = []
        self._info: dict[str, Any] = {}

    @staticmethod
    def get_dl_path_from_hash(
        hash: str, offset: int = 0, requested: int = 0, full: bool = False
    ) -> str:
        hash_folder = os.path.join(RESULTS_DIR, hash)
        xml_folder = os.path.join(hash_folder, "xml")
        if full:
            full_folder = os.path.join(xml_folder, "full")
            if not os.path.exists(full_folder):
                os.makedirs(full_folder)
            return full_folder
        offset_folder = os.path.join(xml_folder, str(offset))
        requested_folder = os.path.join(offset_folder, str(requested))
        if not os.path.exists(requested_folder):
            os.makedirs(requested_folder)
        return requested_folder

    @classmethod
    async def export(cls, request_id: str, qhash: str, payload: dict) -> None:
        job: Job = cast(Job, get_current_job())
        request: Request = Request(job.connection, {"id": request_id})
        qi: QueryInfo = QueryInfo(qhash, job.connection)
        epath = cls.get_dl_path_from_hash(
            request.hash, request.offset, request.requested, request.full
        )
        try:
            exporter = cls(request, qi)
            await exporter.process_lines(payload, epath)
            if not request.is_done(qi):
                return
            qb_hashes = [bh for bh, _ in qi.query_batches.values()]
            for h in request.sent_hashes:
                if h not in qb_hashes:
                    continue
                hpath = os.path.join(epath, h)
                if not os.path.exists(f"{hpath}_query"):
                    return
                seg_exists = os.path.exists(f"{hpath}_segments")
                if qi.kwic_keys and not seg_exists:
                    return
            await exporter.finalize(epath)
            print(
                f"Exporting complete for request {request.id} (hash: {request.hash}) ; DELETED REQUEST"
            )
            qi.delete_request(request)
        except Exception as e:
            shutil.rmtree(epath)
            raise e

    async def process_query(self, payload: dict, epath: str, batch_hash: str) -> None:
        print(
            f"[Export {self._request.id}] Process query {batch_hash} (QI {self._request.hash})"
        )
        res = payload.get("result", [])
        if self._qi.stats_keys:
            stats = E.stats(
                *[
                    E.result(*[E.entry(":".join(str(x) for x in l)) for l in res[k]])
                    for k in self._qi.stats_keys
                ]
            )
            stats_path: str = os.path.join(epath, "stats.xml")
            with open(stats_path, "w") as stats_output:
                stats_str = lxml.etree.tostring(
                    stats, encoding="unicode", pretty_print="True"  # type: ignore
                )
                stats_output.write(stats_str)
        if self._qi.kwic_keys:
            bpath = os.path.join(epath, batch_hash)
            if not os.path.exists(bpath):
                os.mkdir(bpath)
            kwics = E.kwic(
                *[
                    E.result(
                        *[
                            E.seg(*[E.w(str(t), id=str(t)) for t in tokens], id=sid)
                            for sid, tokens in res[k]
                        ]
                    )
                    for k in self._qi.kwic_keys
                ]
            )
            kwic_path: str = os.path.join(bpath, "kwic.xml")
            with open(kwic_path, "w") as kwic_output:
                kwic_str = lxml.etree.tostring(
                    kwics, encoding="unicode", pretty_print="True"  # type: ignore
                )
                kwic_output.write(kwic_str)

    def format_tokens(self, offset: int, tokens: list) -> Any:
        tok = self._config["token"]
        return [getattr(E, tok)(t[0], id=str(offset + n)) for n, t in enumerate(tokens)]

    async def process_segments(
        self, payload: dict, epath: str, batch_hash: str
    ) -> None:
        print(
            f"[Export {self._request.id}] Process segments for {batch_hash} (QI {self._request.hash})"
        )
        bpath = os.path.join(epath, batch_hash)
        if not os.path.exists(bpath):
            os.mkdir(bpath)
        res = payload.get("result", [])
        meta_labels = self._qi.meta_labels
        config = cast(CorpusConfig, self._config)
        doc = config["document"]
        seg = config["segment"]
        doc_id = f"{doc}_id"
        seg_id = f"{seg}_id"
        all_docs = {}
        for meta_line in res["-2"]:
            ids = {k: v for k, v in zip(meta_labels, meta_line) if k.endswith("_id")}
            doc_tree = all_docs.get(ids[doc_id]) or lxml.etree.ElementTree(
                lxml.etree.XML(f"<{doc}></{doc}>", parser=None)
            )
            all_docs[ids[doc_id]] = doc_tree
            doc_root = doc_tree.getroot()
            for layer_attr, value in zip(meta_labels, meta_line):
                if layer_attr == doc_id:
                    continue
                layer, attr = layer_attr.split("_", 1)
                attrs = [(attr, value)]
                if isinstance(value, dict):
                    attrs = [(f"{attr}_{k}", v) for k, v in value.items()]
                node = doc_root
                if layer != doc:
                    if not _layer_contains(config, doc, layer):
                        continue
                    layer_id = ids[f"{layer}_id"]
                    node = doc_root.find(f".//{layer}[@id='{layer_id}']")
                    if node is None:
                        node = lxml.etree.XML(
                            f"<{layer} id='{layer_id}'></{layer}>", parser=None
                        )
                        doc_root.append(node)
                for a, v in attrs:
                    if not node.get(a):
                        node.set(a, str(v))
            seg_node = doc_root.find(f".//{seg}[@id='{ids[seg_id]}']")
            offset, tokens = res["-1"][ids[seg_id]]
            for token in self.format_tokens(offset, tokens):
                seg_node.append(token)
        for id, tree in all_docs.items():
            with open(os.path.join(bpath, f"{id}.xml"), "w") as doc_output:
                doc_output.write(lxml.etree.tostring(tree, encoding="unicode", pretty_print="True"))  # type: ignore
        # segments = E.segments(
        #     *[
        #         self.format_segment(sid, offset, tokens)
        #         for sid, (offset, tokens) in res["-1"].items()
        #     ]
        # )
        # segments_path: str = os.path.join(bpath, "segments.xml")
        # with open(segments_path, "a") as segments_output:
        #     segments_str = lxml.etree.tostring(
        #         segments, encoding="unicode", pretty_print="True"  # type: ignore
        #     )
        #     segments_output.write(segments_str)

    async def finalize(self, epath: str) -> None:
        print(f"Finalize export for {self._request.id} (hash: {self._request.hash})")

    async def process_lines(self, payload: dict, epath: str) -> None:

        action = payload.get("action", "")
        batch_name = payload.get("batch_name", "")
        batch_hash = self._qi.query_batches[batch_name][0]
        if action == "query_result":
            await self.process_query(payload, epath, batch_hash)
            query_path = os.path.join(epath, f"{batch_hash}_query")
            if not os.path.exists(query_path):
                os.mkdir(query_path)
        elif action == "segments":
            await self.process_segments(payload, epath, batch_hash)
            segments_path = os.path.join(epath, f"{batch_hash}_segments")
            if not os.path.exists(segments_path):
                os.mkdir(segments_path)

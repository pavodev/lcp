from __future__ import annotations

from typing import Any, cast

from .constraint import _get_constraints, Constraints, process_set
from .sequence import SQLSequence
from .sequence_members import Member, Sequence
from .typed import (
    QueryJSON,
    Joins,
    JSONObject,
    TGSD,
    ConfigJSON,
    ResultMetadata,
    JSON,
    Attribs,
    Details,
)
from .utils import (
    Config,
    QueryData,
    _label_layer,
    _get_table,
    _get_mapping,
    _get_underlang,
    _is_anchored
)

import re

COUNTER = f"""
    res0 AS (SELECT 0::int2 AS rstype,
      jsonb_build_array(count(*))
       FROM match_list) 

"""


class ResultsMaker:
    """
    A class to manage the creation of results SQL, data and metadata
    """

    def __init__(self, query_json: QueryJSON, conf: Config) -> None:
        self.query_json: QueryJSON = query_json
        self.conf: Config = conf
        self.config: ConfigJSON = conf.config
        self.schema: str = conf.schema
        self.lang: str = conf.lang or ""
        self.batch: str = conf.batch
        # self.vian: bool = conf.vian
        self.vian: bool = False
        self.segment = cast(str, self.config["segment"])
        self.token = cast(str, self.config["token"])
        self.document = cast(str, self.config["document"])
        self.conf_layer = cast(JSONObject, self.config["layer"])
        self.r = QueryData()
        self.r.label_layer = _label_layer(query_json.get("query", query_json))
        self._n = 1
        self._underlang = _get_underlang(self.lang, self.config)
        self._label_with_track: str | None = None
        self._label_mapping: dict[str,str] = dict() # Map entities' labels to potentially internal labels

    def add_query_entities(self, query_json: dict[str, Any]) -> None:
        """
        Look through the query part of the JSON and add entities to the entities list
        """
        query = query_json.get("query", [query_json])
        labels_so_far: set[str] = {e for e in self.r.entities}
        for obj in query:
            if "sequence" in obj:
                dict_entities: dict[str,list] = {e: [] for e in labels_so_far}
                set_entities: set[str] = set(e for e in labels_so_far)
                seq: Sequence = Sequence(obj, sequence_references=dict_entities)
                sqlseq: SQLSequence = SQLSequence(seq, self.conf, entities=set_entities, label_layer=self.r.label_layer)
                sqlseq.categorize_members(entities=dict_entities)
                for t, _, _, _ in sqlseq.fixed_tokens:
                    original_label: str = cast(str, t.obj['unit'].get("label", ""))
                    if original_label:
                        self.r.entities.add(original_label)
                        self._label_mapping[original_label] = t.internal_label
                        if original_label in self.r.label_layer:
                            self.r.label_layer[t.internal_label] = self.r.label_layer[original_label]
                self.r.sqlsequences.append(sqlseq)
                labels_so_far = labels_so_far.union({x for x in sqlseq._sequence_references})
                labels_so_far = labels_so_far.union({x for x in sqlseq._internal_references})
                labels_so_far = labels_so_far.union({x for x in sqlseq._internal_references.values()})

            elif "logicalOpNAry" in obj:
                coord = obj["logicalOpNAry"]
                for arg in coord["args"]:
                    self.add_query_entities(arg)
            elif "unit" in obj:
                unit = obj["unit"]
                if cast(str, unit.get("layer", "")).lower() == self.token.lower() and cast(
                    str, unit.get("label", "")
                ):
                    lab: str = unit["label"].lower()
                    self.r.entities.add(lab)
                    self._label_mapping[lab] = lab
        return None

    def add_set_objects(self, query_json: dict[str, Any]) -> None:
        """
        Look through the query part of the JSON and add set objects to the objects list
        """
        query = query_json.get("query", [query_json])
        for obj in query:
            if "sequence" in obj:
                seq = obj["sequence"]
                for member in seq["members"]:
                    self.add_set_objects(member)
            elif "set" in obj and cast(str, cast(dict, obj["set"]).get("label", "")):
                self.r.set_objects.add(cast(str, obj["set"]["label"]))
        return None

    def find_set(self, label) -> dict | None:
        for obj in self.query_json["query"]:
            if not isinstance(obj, dict):
                continue
            for k, v in obj.items():
                if not isinstance(v, dict):
                    continue
                if k == "set" and v.get("label") == label:
                    return v
        return None

    def results(self) -> QueryData:
        """
        Build the results section of the postgres query
        """
        strings = [COUNTER]
        attribs = []

        made: str
        meta: ResultMetadata

        self.add_query_entities(self.query_json)
        self.add_set_objects(self.query_json)

        results = self.query_json.get("results")
        if not results:
            raise ValueError("Results needed in JSON")

        # Check that all entity references are legit
        legal_refs = set()
        for obj in self.query_json.get("query", []):
            if "unit" in obj:
                legal_refs.add(cast(dict,obj['unit']).get("label",""))
            elif "sequence" in obj:
                sequence: dict[str,Any] = cast(dict[str,Any], obj['sequence'])
                if "repetition" in sequence and sequence['repetition'] != "1..1":
                    continue
                legal_refs.add(sequence.get("label", ""))
                members = sequence.get("members", [])
                for m in members:
                    if "unit" in m:
                        legal_refs.add(m['unit'].get("label",""))
            elif "set" in obj:
                legal_refs.add(cast(dict,obj['set']).get("label", ""))
                continue

        for result in results:
            if "resultsPlain" in cast(JSONObject, result):
                plain = cast(JSONObject, result["resultsPlain"])
                ents = cast(list[str], plain["entities"])
                for e in ents:
                    assert e in legal_refs, ReferenceError(f"Label {e} cannot be referenced (is not declared or scope-bound)")
                    self.r.entities.add(e)
                    lay, met = self.r.label_layer.get(e, (None, None))
                    if lay is None and met is None:
                        continue
                    for mem in cast(list, cast(JSONObject, met).get("members", [])):
                        if "label" in mem:
                            self.r.entities.add(mem["label"])

            elif "resultsCollocation" in cast(JSONObject, result):
                coll = cast(JSONObject, result["resultsCollocation"])
                if c := coll.get("center"):
                    assert c in legal_refs, ReferenceError(f"Label {c} cannot be referenced (is not declared or scope-bound)")
                    self.r.entities.add(cast(str, c).lower())
                # for s in cast(list[str], coll.get("space", [])):
                #    self.r.entities.add(s)
            elif "resultsAnalysis" in cast(JSONObject, result):
                stat = cast(JSONObject, result["resultsAnalysis"])
                attr = cast(list[str], stat.get("attributes", []))
                for a in attr:
                    lab: str = a.split(".",1)[0].lower()
                    assert lab in legal_refs, ReferenceError(f"Label {lab} cannot be referenced (is not declared or scope-bound)")
                    self.r.entities.add(lab)

        kind: str
        r: JSON

        for i, result in enumerate(results, start=1):
            kind, _r = next((x for x in list(result.items()) if x[0] != "label"), {})
            r = cast(JSONObject, _r)
            # varname = cast(str, r.get("label", f"untitled_{i}"))
            varname = cast(str, result.get("label", f"untitled_{i}"))
            if kind == "resultsPlain":
                context = cast(str, next((x for x in cast(list[str],r.get("context", ["s"]))), "s")) # list in case of parallel corpus
                # todo: handle 1+ contexts in case of parallel corpus queries
                enti = cast(list[str], r.get("entities", []))
                made, meta = self._kwic(i, varname, context, enti)
            elif kind == "resultsAnalysis":
                made, meta, filter_meta = self.stats(i, varname, r)
                if filter_meta:
                    self.r.post_processes[i] = filter_meta
            elif kind == "resultsCollocation":
                self._add_collocation_selects(r)
                made, meta = self.collocation(i, varname, r)

            strings.append(made)
            attribs.append(meta)

        self.r.meta_json = {"result_sets": attribs}
        self.r.needed_results = "\n , ".join(strings)
        return self.r

    def _add_collocation_selects(self, result: dict) -> None:
        """
        For collocation query with space, we add the 'space' obj to entities
        so its criteria end up in match_list.

        We do this even when the space object is a set object and otherwise
        not in entities. This might change ... if space is a set, maybe the
        criteria go into the collocation CTE instead of match_list CTE
        """
        space = result.get("space", [])
        feat = cast(str, result.get("attribute", "lemma"))
        attribs = cast(JSONObject, self.conf_layer[self.token])["attributes"]
        assert isinstance(attribs, dict)
        att_feat = cast(JSONObject, cast(JSONObject, attribs)[feat])
        is_text = cast(str, att_feat.get("type", "")) == "text"
        need_id = feat in attribs and is_text

        if not space:
            center = result["center"]
            if center in self.r.set_objects:
                raise ValueError(f"center cannot be set ({center})")
            else:
                # is this use of _id correct? is feat correct?
                idx = "_id" # if need_id else "" # always append id here
                formed = f"{center}.{self.token}{idx} as {center}"
                self.r.selects.add(formed.lower())
                self.r.entities.add(center)
            return None

        feat_maybe_id = f"{feat}_id" if need_id and not feat.endswith("_id") else feat
        # in_entities = False if not space else space[0].lower() in self.r.entities
        layer, _ = self.r.label_layer[space[0]]
        attr = f"{self.token.lower()}_id"
        self._n += 1
        formed = f"{space[0]}.{attr} AS {space[0]}"

        if space[0] not in self.r.set_objects:
            self.r.selects.add(formed.lower())
            self.r.entities.add(space[0])
            formed = f"{space[0]}.{feat_maybe_id} AS {space[0]}_{feat_maybe_id}"
        # thead.lemma_id AS thead_lemma_id
        else:
            formed = process_set(
                self.conf,
                self.r,
                self._n,
                self.token,
                self.segment,
                self._underlang,
                self.find_set(space[0]) or {},
                seg_label="___seglabel___",
                attribute=feat,
            )

        self.r.selects.add(formed.lower())
        # add entity: thead_lemma_id
        self.r.entities.add(f"{space[0]}_{feat_maybe_id}".lower())

    def _update_context(self, context: str) -> None:
        """
        Add kwic context joins, selects, needed objects
        """
        lay: str
        lay, _ = self.r.label_layer[context]
        first_class: dict[str,str] = cast(dict[str,str], self.config["firstClass"])
        keys = {first_class[f].lower() for f in {"token", "segment", "document"}}
        err = f"Context not allowed: {lay.lower()} not in {keys}"
        assert lay.lower() in keys, err
        select = f"{context}.{lay.lower()}_id AS {context}"
        self.r.selects.add(select.lower())
        self.r.entities.add(context.lower())
        return None

    def _process_entity(self, ent: str) -> tuple[list[str], list[Details]]:
        """
        Add kwic metadata and update entities list with requested kwic item
        """
        entities_involved: list[str] = []
        attribs: list[Details] = []
        lay: str
        rest: dict[str, Any]
        lay, rest = self.r.label_layer[ent]
        
        # sets are simple: just return their name
        if rest.get("_is_set"):
            entities_involved.append(ent)
            attribs.append({"name": ent, "type": "set", "multiple": True})
            return entities_involved, attribs
        
        # the user might have passed a sequence ...
        members = cast(list, rest.get("members", []))
        # if it is not a sequence or a set:
        if "members" not in rest:
            entities_involved.append(ent)
            mult = False
            typ = self.r.label_layer[ent][0]
            attribs.append({"name": ent, "type": typ, "multiple": mult})
            return entities_involved, attribs

        details: Details = {
            "name": ent,
            "type": "sequence",
            "multiple": True,
            "members": [],
        }

        if rest.get("_is_group"):
            details["type"] = "group"

        for i, mem in enumerate(members):
            if "unit" not in mem: continue
            label = cast(str, mem["unit"].get("label", ""))
            if not label:
                # If the token has no label then we don't need to fetch it?
                continue
                # label = f"anonymous_token_from_{ent}_{str(i)}".lower()
                # lay = self.token
            else:
                lay, _ = self.r.label_layer[label]
            if lay == self.token:
                field = f"{self.token}_id"
                if label not in self.r.set_objects:
                    formed = f"{label}.{field} as {label}"
                    self.r.selects.add(formed.lower())
                    if label not in self.r.entities:
                        self.r.entities.add(label)
                piece: Details = {"name": label, "type": lay, "multiple": False}
                cast(list, details["members"]).append(piece)
            entities_involved.append(label)

        if all(entities_involved):
            return entities_involved, [details]

        entities_involved = [ent]
        attribs = [{"name": ent, "type": "Token", "multiple": False}]

        return entities_involved, attribs

    def stats(
        self, i: int, varname: str, result: JSONObject
    ) -> tuple[str, ResultMetadata, list[dict[str, Any]]]:
        """
        Process a stats request
        """
        attributes = cast(list[str], result["attributes"])
        for att in attributes:
            lab = att.replace(".", "_").lower().strip()
            shortest = att.split(".", 1)[0]
            shortest = self._label_mapping.get(shortest, shortest)
            field = att.split(".")[-1]
            layer, _ = self.r.label_layer[shortest]
            layer_attrs = self.conf.config["layer"][layer].get("attributes", {})
            table = _get_table(layer, self.config, self.batch, self.lang)
            is_meta = field not in layer_attrs and field in layer_attrs.get("meta", {})
            conf_layer_info: dict[str,Any] = cast(dict[str,Any], self.conf_layer[layer])
            attrs = conf_layer_info["attributes"]
            mapping: dict[str,Any] = _get_mapping(layer, self.config, self.batch, self.lang)
            attrib_table = mapping.get("attributes", {}).get(field,{}).get("name",field)
            if is_meta:
                line = f"{shortest}.meta ->> '{field}' AS {lab}"
                self.r.selects.add(line)
            elif attrs[field].get("type", "") == "text" or "ref" in attrs[field]:
                formed_join = f"{self.schema}.{attrib_table} {lab}"
                self.r.joins[formed_join.lower()] = True
                formed_join_cond = f"{lab}.{field}_id = {shortest}.{field}_id"
                self.r.conditions.add(formed_join_cond.lower())
                line = f"{lab}.{field} AS {lab}"
                self.r.selects.add(line)
            else:
                line = f"{shortest}.{attrib_table} AS {lab}"
                self.r.selects.add(line)
            self.r.joins[ f"{self.schema}.{table} {shortest}".lower() ] = True
            self.r.entities.add(lab)

        functions = cast(list[str], result["functions"])
        filt = cast(JSONObject, result.get("filter", {}))
        made, meta, filter_meta = self._stat_analysis(
            i, varname, attributes, functions, filt
        )
        return made, meta, filter_meta

    def _kwic(
        self,
        i: int,
        label: str,
        context: str,
        ents: list[str],
    ) -> tuple[str, ResultMetadata]:
        """
        Produce a KWIC query and its JSON metadata
        """
        entout: list[str] = []
        select_extra = ""

        gest = "Gesture" in self.conf_layer or "gesture" in self.conf_layer
        doc_join = ""
        gesture_type = "null"

        self._update_context(context)
        context_layer = self.r.label_layer[context][0]

        # g, t, s, d = self._get_labels(gest)

        lay: str
        tokens: list[dict] = []

        for e in ents:
            lay, meta = self.r.label_layer[e]
            # todo: if group, add ARRAY[]
            if e in self.r.set_objects:
                select = process_set(
                    self.conf,
                    self.r,
                    self._n,
                    self.token,
                    self.segment,
                    self._underlang,
                    self.find_set(e) or {},
                    seg_label="___seglabel___",
                    attribute="___tokenid___",
                    label=e,
                )
                # cannot be lowercased because it is a subquery and may have WHERE
                self.r.selects.add(select)
                self.r.entities.add(e.lower())
                continue

            if lay == self.token:
                if e not in self.r.set_objects:
                    select = f"{e}.{self.token}_id as {e}"
                    self.r.selects.add(select.lower())
                    self.r.entities.add(e.lower())

        for e in ents:
            entities_list, attributes = self._process_entity(e)
            conf_layer_info: dict[str,Any] = cast(dict[str,Any], self.conf_layer.get(lay, {}))
            if (
                isinstance(attributes, list)
                and isinstance(attributes[0], dict)
                and attributes[0].get("type", "") in ("group", "sequence")
            ):
                entout += [cast(dict,attributes[0]).get("name","")]
                # entout += [f"ARRAY[{', '.join(entities_list)}]"]
            elif conf_layer_info.get("contains", "").lower() == self.token.lower():
                select = """(SELECT array_agg(contained_token.{token_lay}_id)
FROM {schema}.{token_table} contained_token
WHERE {entity}.char_range && contained_token.char_range
) AS {entity}_container""".format(
                    schema=self.schema,
                    token_lay=self.token.lower(),
                    token_table=self.batch,
                    entity=e
                )
                container_lab = f"{e}_container"
                self.r.selects.add(select)
                self.r.entities.add(container_lab)
                entout += [container_lab]
            else:
                entout += entities_list
            tokens += attributes

        ents_form = ", ".join(entout)
        doc_join = ""
        frame_range_base = "array[lower(match_list.{fr}), upper(match_list.{fr})]"
        extras: list[str] = []
        extra_meta: list[str] = []
        frame_ranges: list[dict[str, Any]] = []
        any_frame_range: str = ""

        # if self.vian:
        if _is_anchored(self.config, context_layer, 'time'):
            lab = context # TODO: accommodate corpora using FTS
            out_name = f"{lab}_frame_range"
            if not any_frame_range:
                any_frame_range = out_name
            formed = f"{lab}.frame_range AS {out_name}"
            self.r.selects.add(formed.lower())
            self.r.entities.add(out_name.lower())
            fr = frame_range_base.format(fr=out_name)
            extras.append(fr)
            extra_meta.append(lay)
            # for bit in [t, g, s, d]:
            #     if not bit:
            #         continue
            #     lab, lay = bit
            #     if lay != self.config["document"] and self._label_with_track is None:
            #         self._label_with_track = lab
            #     # todo: should this be here?
            #     if lab.lower() not in self.r.entities:
            #         continue
            #     out_name = f"{lab}_frame_range"
            #     if not any_frame_range:
            #         any_frame_range = out_name
            #     formed = f"{lab}.frame_range AS {out_name}"
            #     self.r.selects.add(formed.lower())
            #     self.r.entities.add(out_name.lower())
            #     fr = frame_range_base.format(fr=out_name)
            #     extras.append(fr)
            #     extra_meta.append(lay)

            # self._add_vian_agentname()

            # if d:
            #     d_label, _ = d
            #     doc_id = f"{self.document}_id"
            #     get_doc = d_label
            #     formed = f"{d_label}.{doc_id} {doc_id}"
            #     self.r.selects.add(formed.lower())
            #     self.r.entities.add(doc_id.lower())
            #     doc_join = ""
            # else:
            #     get_doc = "_doc.document_id"
            #     doc_join = f"""
            #     JOIN {self.schema.lower()}.{self.document.lower()} _doc
            #     ON _doc.frame_range @> match_list.{any_frame_range}
            #     """.strip()

            for ex in extra_meta:
                obj: dict[str, str | bool] = {
                    "name": f"{ex}_frame_range",
                    "type": "list[int]",
                    "multiple": True,
                }
                frame_ranges.append(obj)

            # gesture = "null"
            # # agent_name = "null"
            # agent_name = "match_list.agent_name"

            # if g:
            #     gesture_type = "str|null"
            #     gesture = f"match_list.{g[0]}_gesture"

            # select_extra = f", {get_doc}, {gesture}, {agent_name}"
            if extras:
                formed = ", ".join(extras)
                select_extra = ", " + formed

        attribs = self._make_attribs(
            context, context_layer, gesture_type, tokens, frame_ranges
        )

        out = f"""
            res{i} AS ( SELECT
            {i}::int2 AS rstype,
            jsonb_build_array({context}, jsonb_build_array({ents_form}) {select_extra})
        FROM
            match_list
            {doc_join}
        )
        """
        metadata: ResultMetadata = {
            "attributes": attribs,
            "name": label,
            "type": "plain",
        }
        return out, metadata

    # def _add_vian_agentname(self):
    #     """
    #     For VIAN queries we need access to agent_name
    #     """
    #     if not self._label_with_track:
    #         # segment_table = f"{self.segment}{_get_batch_suffix(self.batch)}"
    #         formed = f"{self.schema}.{self.segment} s"
    #         self.r.joins[formed] = None
    #         formed = f"s.{self.segment}_id = {{_base_label}}.{self.segment}_id"
    #         self.r.conditions.add(formed)
    #         self.r.entities.add("s")
    #         self.r.manual_track = "s"
    #         # self._label_with_track = "s"

    #     label = self._label_with_track or "s"

    #     formed = f"{self.schema}.track track0".lower()
    #     self.r.joins[formed] = None

    #     # todo: how do we know there is an s?
    #     formed = f"track0.track_id = {label}.track_id"
    #     self.r.conditions.add(formed)

    #     formed = f"{self.schema}.agent agent0".lower()
    #     self.r.joins[formed] = None
    #     formed = f"track0.agent_id = agent0.agent_id"
    #     self.r.conditions.add(formed)

    #     formed = f"agent0.name AS agent_name"
    #     self.r.selects.add(formed.lower())

    def _get_label_layer(self, name: str) -> None | tuple[str, str]:
        """
        Get a label/layer with layer matching name, or return None
        """
        return next(
            (
                (k, v)
                for k, (v, _) in self.r.label_layer.items()
                if v.lower() == name.lower()
            ),
            None,
        )

    def _get_labels(self, gesture: bool) -> TGSD:
        """
        Get labels and layers for token, gesture, segment and document
        """
        has_gesture: None | tuple[str, str]
        has_gesture = self._get_label_layer("gesture") if gesture else None
        if has_gesture:
            gesture_layer: str = has_gesture[0]
            formed = f"{gesture_layer}.type AS {gesture_layer}_gesture"
            self.r.selects.add(formed.lower())
            self.r.entities.add(f"{gesture_layer}_gesture".lower())

        out: list[tuple[str, str] | None] = [has_gesture]
        has: None | tuple[str, str]

        for i in ["token", "segment", "document"]:
            has = self._get_label_layer(i)
            assert has is None or (
                isinstance(has, tuple)
                and isinstance(has[0], str)
                and isinstance(has[1], str)
            )
            out.append(has)

        return (out[0], out[1], out[2], out[3])

    def _make_attribs(
        self,
        context: str,
        context_layer: str,
        gesture_type: str,
        tokens: list[dict],
        frame_ranges: list[dict],
    ) -> list[dict]:
        """
        Format kwic metadata for vian/non vian queries
        """

        out: list[dict]

        if not _is_anchored(self.config, context_layer, 'time'):
            out = [
                {
                    "name": "identifier",
                    "label": context,
                    "layer": context_layer,
                    "type": "str|int",
                    "multiple": False,
                },
                {
                    "name": "entities",
                    "multiple": True,
                    "data": tokens,
                    "type": "list[dict]",
                },
            ]
            return out

        out = [
            {
                "name": "identifier",
                "label": context,
                "layer": context_layer,
                "type": "str|int",
                "multiple": False,
            },
            {
                "name": "entities",
                "multiple": True,
                "data": tokens,
                "type": "list[dict]",
            },
            # {"name": "document_id", "type": "number", "multiple": False},
            # {"name": "gesture", "type": gesture_type, "multiple": False},
            # {"name": "agent", "type": "str", "multiple": False},
            {
                "name": "frame_ranges",
                "type": "list[dict]",
                "multiple": True,
                "data": frame_ranges,
            },
        ]
        return out

    def _process_filters(self, filt: JSONObject) -> tuple[str, list[dict[str, Any]]]:
        """
        Get a where string and metadata for stat filters
        """
        err = "non-simple comparison not supported here yet"
        if not filt:
            return "", []
        out: list[dict[str, Any]] = []
        wheres: set[str] = set()

        comp: dict[str, dict] = cast(dict[str,dict], filt)
        for k, v in comp.items():
            if k != "comparison":
                raise NotImplementedError("todo")
            if v.get('entity','').lower() == "frequency":
                out.append({k: v})
            else:
                # This needs to be revised (use Constraint from .constraints instead?)
                # out.append({})
                # entity, operator, type, text = _parse_comparison(v)
                # wheres.add(f"{entity} {operator.replace('=','~') if type == 'regexComparison' else operator} '{text}'")
                continue

        if wheres:
            strung = " WHERE " + " AND ".join(wheres)
        else:
            strung = ""
        return strung, out

    def _stat_analysis(
        self,
        i: int,
        label: str,
        attributes: list[str],
        functions: list[str],
        filt: JSONObject,
    ) -> tuple[str, ResultMetadata, list[dict[str, Any]]]:
        """
        Produce a frequency table and its JSON metadata
        """
        counts: list[str] = []
        for func in functions:
            if func.lower().startswith("freq"):
                counts.append(f"count(*) AS {func.lower()}")
            else:
                raise NotImplementedError("TODO?")
        if counts:
            jcounts = " , " + " , ".join(counts)
        else:
            jcounts = " "
        funcstr = " , ".join(functions)
        fixed: list[str] = []
        for att in attributes:
            fix = att.replace(".", "_")
            fixed.append(fix)
        nodes = " , ".join(fixed)
        wheres, filter_meta = self._process_filters(filt)
        out = f"""
            res{i} AS ( SELECT
                {i}::int2 AS rstype,
                jsonb_build_array({nodes}, {funcstr})
            FROM
                (
                    SELECT
                        {nodes}
                        {jcounts}
                    FROM
                        match_list
                    GROUP BY {nodes}
                ) x {wheres} )
        """
        attribs: Attribs = []
        for att in attributes:
            lab, feat = att.split(".", 1)
            lay = self.r.label_layer[lab][0]
            typed = f"{lay}.{lab}"
            attribs.append({"name": att, "type": typed})
        for func in functions:
            attribs.append({"name": func, "type": "aggregrate"})
        meta: ResultMetadata = {
            "attributes": attribs,
            "name": label,
            "type": "analysis",
        }
        return out, meta, filter_meta

    def _space_item(self, item: str) -> tuple[set[str], Joins]:
        """
        Unused method: when collocation space is not in self.r.entities,
        the joins/wheres do not happen in match_list and would need to
        happen in the collocation cte.

        Right now though, we add space to entities. If this changes,
        we use this data to format the joins and wheres inside the collation cte
        """
        if item.lower() in self.r.entities:
            return set(), {}

        wheres: set[str] = set()
        joins: Joins = {}
        lay: str
        rest: dict[str, Any]
        lay, rest = self.r.label_layer[item]
        cons: JSONObject = rest.get("constraints", {})

        if not cons:
            return wheres, joins

        constraints: Constraints | None = _get_constraints(
            cons,
            lay,
            item,
            self.conf,
            n=self._n,
            label_layer=self.r.label_layer,
            entities=self.r.entities,
            part_of=cast(str|None, rest.get("partOf", None)),
            set_objects=self.r.set_objects,
            allow_any=True,
        )

        if constraints is not None:
            self._n = constraints._n + 1
            constraints.make()
            cond = constraints.conditions()
            if cond:
                wheres.add(cond)
            for k, v in constraints.joins().items():
                joins[k] = v

        return wheres, joins

    def _freq_n_table(self) -> str:
        """
        Get the total word count table (it has one column, freq)
        """
        batch: str = self.batch
        if batch.endswith("rest"):
            batch = batch[:-4]
        else:
            batch = batch.rstrip("0123456789")
        return batch + "_n"

    def _freq_table(self) -> str:
        """
        Get freq 'cube' table for collocation data
        """
        batch: str = self.batch
        if batch.endswith("rest"):
            batch = batch[:-4]
        else:
            batch = batch.rstrip("0123456789")
        return batch + "_freq"

    def _other_fields(self, feature: str, freq_table: str) -> str:
        """
        Generate the IS NULL lines for unused fields in collocation queries (uncubing)
        """
        fields: set[str] = set()
        att: str
        data: dict[str, str | bool | dict[str, JSONObject]]
        config: dict[str,Any] = cast(dict[str,Any], self.config)
        layers_config: dict[str,Any] = config["layer"]
        token_info: dict[str,Any] = cast(dict[str,Any], layers_config[self.token])
        for att, data in token_info["attributes"].items():
            field = att
            if att == feature:
                continue
            if data["type"] in ("text","dict"):
                field = field + "_id"
            fields.add(field)
        if self.lang:
            for lay, info in layers_config.items():
                named = self.token + "@" + self.lang
                if lay.lower() != named.lower():
                    continue
                for att, data in info["attributes"].items():
                    field = att
                    if att == feature:
                        continue
                    if data["type"] in ("text","jsonb"):
                        field = field + "_id"
                    fields.add(field)

        if not fields:
            return ""

        formed = [f"{freq_table}.{a} IS NULL" for a in fields]
        return " WHERE " + " AND ".join(formed)

    @staticmethod
    def _parse_window(window: str, center: str | None) -> str:
        """
        Parse the x..y format window into an SQL string
        """
        if not window:
            return ""
        a, b = window.split("..", 1)
        a = a.replace("+", "+ ", 1).replace("-", "- ", 1)
        b = b.replace("+", "+ ", 1).replace("-", "- ", 1)
        if "*" in a and "*" in b:
            return ""
        elif "*" not in a and "*" in b:  # *..5
            return f">= {center} {a}"
        elif "*" in a and "*" not in b:  # 3..*
            return f"<= {center} {b}"
        else:  # 3..4
            return f"BETWEEN {center} {a} AND {center} {b}"

    @staticmethod
    def _within_sent(segment_id, **kwargs) -> str:
        """
        If we are limiting the collocation to the sentence, make that condition here

        Right now it is not controllable. Could fail if query doesn't involve segment data maybe?
        """
        seg_name = "__seglabel__"
        return f"AND tx.{segment_id} = match_list.{seg_name}"

    def collocation(
        self,
        i: int,
        label: str,
        result: JSONObject,
    ) -> tuple[str, ResultMetadata]:
        """
        Generate a string query and dict of query metadata

        self is the ResultsMaker object -- all this code could be methods on it,
        but danny put them here because that file is getting large...
        """
        space = cast(list[str], result.get("space", []))
        center = cast(str | None, result.get("center"))
        assert not (space and center), "Only one of space/center allowed!"
        freq_n = self._freq_n_table()
        freq_table = self._freq_table()
        windowed = self._parse_window(cast(str, result.get("window", "")), center)
        feat = cast(str, result.get("attribute", "lemma"))
        attribs = cast(JSONObject, self.conf_layer[self.token])["attributes"]
        assert isinstance(attribs, dict)
        att_feat = cast(JSONObject, cast(JSONObject, attribs)[feat])
        is_text = cast(str, att_feat.get("type", "")) == "text"
        
        need_id = feat in attribs and is_text
        feat_maybe_id = f"{feat}_id" if need_id and not feat.endswith("_id") else feat
        space_feat, lany, rbrack = "", "", ""
        if space:
            space_feat = f"{space[0]}_{feat_maybe_id}"
            if space[0] in self.r.set_objects:
                lany = " ANY ( "
                rbrack = " ) "
        token_id = f"{self.token}_id"
        segment_id = f"{self.segment}_id"

        null_fields = self._other_fields(feat, freq_table)
        feat_tab: str = feat
        config: dict[str,dict] = cast(dict[str,dict], self.config)
        mapping: dict[str,Any] = config["mapping"]["layer"].get(self.token,{})
        if mapping:
            attributes: dict[str,Any] = mapping.get("attributes", {})
            if self.lang and (partitions := mapping.get("partitions")):
                attributes = partitions.get(self.lang,{}).get("attributes",{})
            feat_tab = attributes.get(feat,{}).get("name",feat)
        # feat_tab = f"{feat}{self._underlang}"
        within_sent = self._within_sent(segment_id)

        if is_text:
            join_for_text_field = f"JOIN {self.schema}.{feat_tab} ON {feat_tab}.{feat_maybe_id} = x.{feat_maybe_id}"
        else:
            join_for_text_field = ""

        if space:
            if need_id:
                cte = f"""
                    collocates{i} AS (
                        SELECT {feat_tab}.{feat_maybe_id}
                        FROM match_list
                            CROSS JOIN {self.schema}.{feat_tab} {feat_tab}
                        WHERE {feat_tab}.{feat_maybe_id} = {lany}{space_feat}{rbrack}),
                """
            else:
                select_feat = space_feat
                if space[0] in self.r.set_objects:
                    select_feat = f"unnest({space_feat})"
                cte = f"""
                    collocates{i} AS (
                        SELECT {select_feat} AS {feat_maybe_id}
                        FROM match_list),
                """
        else:
            cte = f"""
            collocates{i} AS (
                SELECT tx.{feat_maybe_id}
                FROM match_list
                        JOIN {self.schema}.{self.batch} tx ON tx.{token_id} {windowed}
                    AND tx.{token_id} <> {center}
                    {within_sent}),
            """

        out = f"""
            {cte}
            resXn{i} AS (SELECT count(*) AS freq FROM collocates{i}),
            res{i} AS
                (SELECT {i}::int2 AS rstype,
                    jsonb_build_array({feat}, o, e)
                FROM (SELECT {feat}, o, 1. * x.freq / {freq_n}.freq * resXn{i}.freq AS e
                    FROM (SELECT {feat_maybe_id}, freq, count(*) AS o
                        FROM collocates{i}
                                JOIN {self.schema}.{freq_table} USING ({feat_maybe_id})
                        {null_fields}
                        GROUP BY {feat_maybe_id}, freq) x
                            {join_for_text_field}
                            CROSS JOIN {self.schema}.{freq_n}
                            CROSS JOIN resXn{i}) x)
        """

        meta_attribs: list[dict[str, str]] = [
            {"name": "Text", "type": "str"},
            {"name": "O", "type": "int"},
            {"name": "E", "type": "real"},
        ]

        meta: ResultMetadata = {
            "attributes": meta_attribs,
            "name": label,
            "type": "collocation",
        }
        return out, meta
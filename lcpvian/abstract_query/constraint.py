import re

from typing import Any, cast
from uuid import UUID

from .typed import JSONObject, Joins, LabelLayer, QueryType
from .utils import (
    Config,
    _get_underlang,
    _get_mapping,
    _get_table,
    arg_sort_key,
    QueryData,
    _joinstring,
    _parse_comparison,
    _is_anchored,
    _layer_contains,
)

from typing import Self

# for (NOT) EXISTS parts of queries
QUANTOR_TEMPLATE = """
{quantor} (SELECT 1 FROM {schema}.{base} {label}
             {joins}
             {conditions}
           )
"""

# callables allowed in dqd
FUNCS = ("length", "century", "decade", "year", "month", "day", "position", "range")


def _valid_uuid(val: Any) -> bool:
    try:
        UUID(str(val))
        return True
    except ValueError:
        return False


class Constraints:
    def __init__(
        self,
        schema: str,
        layer: str,
        label: str,
        config: Config,
        members: Any,
        conj: str = "AND",
        quantor: str | None = None,
        label_layer: LabelLayer | None = None,
        entities: set[str] | None = None,
        part_of: str | None = None,
        n: int = 1,
        is_set: bool = False,
        set_objects: set[str] | None = None,
        allow_any: bool = True,  # False,
    ) -> None:
        """
        Model constraints recursively as cross joins and WHERE clauses
        """
        self.schema = schema.lower()
        self.layer = layer
        self.label = label
        self.config = config
        self.quantor = quantor
        self.conj = conj
        self.members = members
        self._is_set = is_set
        self.entities: set[str] | None = entities
        self.part_of: str | None = part_of
        self._n: int = n or 0
        self.label_layer = label_layer
        self.set_objects = set_objects
        self.quantor_template = QUANTOR_TEMPLATE
        self._quantor_label: str | None = None
        self._allow_any: bool = allow_any

    def make(self):
        """
        Recursively build all constraints in the tree

        We split instantiating and building so we can apply a patch, the quantor label
        """
        for i in self.members:
            if self._quantor_label:
                i._quantor_label = self._quantor_label
            i.make()

    def __str__(self) -> str:
        return f"Constraints: {len(self.members)} / {self._quantor_label}"

    def _inner_labels(self) -> set[str]:
        inner_labels: set[str] = {self.label}
        for m in self.members:
            if isinstance(m, Constraints):
                inner_labels = inner_labels.union(m._inner_labels())
            else:
                inner_labels.add(m.label)
        return inner_labels

    def _build_subquery(self, member: Self) -> str:
        """
        Helper for quantors
        """
        base = _get_table(
            member.layer,
            self.config.config,
            self.config.batch,
            cast(str, self.config.lang),
        )
        member._quantor_label = self.label
        if isinstance(member, Constraints):
            for m in member.members:
                m._quantor_label = self.label
        member.make()
        not_allowed = f"{self.schema}.{base}".lower()
        joins: Joins = member.joins()
        label_layer = cast(LabelLayer, self.label_layer or dict())
        inner_labels: set[str] = self._inner_labels()
        outer_labels: set[str] = {l for l in label_layer if l not in inner_labels}
        crossjoins = "\n".join(
            f"CROSS JOIN {x}"
            for x in joins
            if not_allowed not in x.lower() and x.split(" ")[-1] not in outer_labels
        )
        conds = member.conditions()
        all_conds = [conds]
        for jcs in joins.values():
            if not isinstance(jcs, set) or not jcs:
                continue
            str_conds = [j for j in jcs if j and isinstance(j, str)]
            if not str_conds:
                continue
            all_conds.append(f"({' AND '.join(str_conds)})")
        conds = "WHERE " + " AND ".join(all_conds)
        template = self.quantor_template.format(
            schema=self.schema,
            base=base,
            quantor=member.quantor,
            label=member.label,
            joins=crossjoins,
            conditions=conds,
        )
        return template

    def conditions(self) -> str:
        """
        Build a single condition string from all constraints recursively
        """
        formed_out: str = self.part_of or ""
        out: dict[str, None] = {}
        for member in self.members:
            if isinstance(member, Constraints) and member.quantor:
                res = self._build_subquery(cast(Self, member))
                if res.strip():
                    out[res] = None
            elif isinstance(member, Constraints) and not member.quantor:
                member.make()
                cons = member.conditions()
                if cons.strip():
                    out[cons] = None
            elif isinstance(member, (TimeConstraint, Constraint)):
                # do we need a sublevel here?
                member.make()
                # Constraint instances necessarily connect their conditions with AND
                stripped_conditions = [c for c in member._conditions if c.strip()]
                conjunction = " AND ".join(stripped_conditions)
                if len(stripped_conditions) > 1 and self.conj.upper() != "AND":
                    out[f"({conjunction})"] = None
                elif stripped_conditions:
                    out[conjunction] = None
        if not out:
            return formed_out
        formed_conj: str
        if len(out) == 1:
            formed_conj = list(out)[0]
            if self.conj == "NOT":
                formed_conj = "NOT " + formed_conj
        else:
            formed_conj = "(" + f" {self.conj.upper()} ".join(out) + ")"
        formed_out = f"{formed_out} AND {formed_conj}" if formed_out else formed_conj
        return formed_out

    def joins(self) -> Joins:
        """
        Produce an ordered set of joins needed for this group of constraints

        We use dict keys, with all values as None, as the ordered set
        """
        out: Joins = {}
        for member in self.members:
            if isinstance(member, Constraints) and member.quantor:
                pass
            elif isinstance(member, Constraints) and not member.quantor:
                member.make()
                # todo: does this need nesting?
                for k, v in member.joins().items():
                    if not k.strip():
                        continue
                    if (
                        k in out
                        and v
                        and isinstance(out[k], set)
                        and isinstance(v, set)
                    ):
                        cast(set, out[k]).add(v)
                    else:
                        out[k] = v
            elif isinstance(member, (TimeConstraint, Constraint)):
                member.make()
                for k, v in member._joins.items():
                    if not k.strip():
                        continue
                    if (
                        k in out
                        and v
                        and isinstance(out[k], set)
                        and isinstance(v, set)
                    ):
                        out[k] = cast(set, out[k]).union(v)
                    else:
                        out[k] = v
        return out


class Constraint:
    def __init__(
        self,
        field: dict[str, Any],
        op: str,
        query: QueryType,
        label: str,
        layer: str,
        conf: Config,
        typ: str = "string",
        quantor: str | None = None,
        label_layer: dict | None = None,
        entities: set[str] | None = None,
        n: int = 1,
        is_set: bool = False,
        set_objects: set[str] | None = None,
        order: int | None = None,
        prev_label: str | None = None,
        allow_any: bool = True,  # False,
    ) -> None:
        """
        Model a single simple constraint, like form='word''
        """
        self.field_function = field.get("function", {})
        self.left = field
        self.field = field.get("entity", "")
        self._layer_info = self._get_layer_info(conf, layer)
        self._attribs = cast(dict[str, Any], self._layer_info.get("attributes", {}))
        self.type = typ
        self._query = query
        self._query_variable = (
            typ == "entity"
            and "." in cast(str, query)
            and cast(str, query).count(".") == 1
        )
        self.op = self._standardise_op(op)
        self.label = label
        self.quantor = quantor
        self.label_layer = label_layer
        self.conf = conf
        self.is_set_obj = set_objects is not None and self.label in set_objects
        self.config = conf.config
        self.original_layer = layer
        self.layer = self._layer(layer)
        self._is_meta = self.field in cast(
            dict[str, Any], self._layer_info.get("meta", self._attribs.get("meta", {}))
        )  # and self.layer == self.config["document"]
        field_in_dep = self.field in {
            x.get("name", "")
            for n, x in {
                "label": {"name": "label"},
                **cast(dict[str, dict], self._layer_info.get("attributes", {})),
            }.items()
            if n
            in (
                "source",
                "target",
                "label",
            )  # Revise special treatment of "label" here?
        }
        self._is_dependency = (
            self._layer_info.get("layerType") == "relation" and field_in_dep
        )
        self.schema = conf.schema.lower()
        self.lang = conf.lang
        self.batch = conf.batch.lower()
        self.entities = entities
        self._n = n
        # self.table = f"agent{n}" if self.field.startswith("agent") else self.label
        self.table = self.label
        self._label = ""  # fallback label for anonymous entities
        self.order = order
        self.prev_label = prev_label
        self._joins: Joins = {}
        self._conditions: set[str] = set()
        self._list_query = isinstance(query, (list, tuple, set))
        self._add_text = True
        self._formatted: str | int | float = self._to_sql(self._query)
        self._cast = self._get_cast(self.field, self._formatted)
        self._f_in_attrs = self.field.startswith(tuple(self._attribs))
        self._quantor_label: str | None = None
        self._made = False
        self._is_len = False
        self._is_set = is_set
        self._underlang = _get_underlang(self.lang, self.config)
        self._allow_any: bool = allow_any

    @staticmethod
    def _parse_date(date: str | int, filler_month="01", filler_day="01") -> str:
        str_date: str = f"{str(date)}".strip("()")
        if re.match(r"^\d{4}$", str_date):
            str_date = f"{str_date}-{filler_month}-{filler_day}"
        elif re.match(r"^\d{4}-\d{2}$", str_date):
            str_date = f"{str_date}-{filler_day}"
        elif not re.match(r"^\d{4}-\d{2}-\d{2}$", str_date):
            assert False, ValueError(f"Invalid date format: '{str(date)}'")
        str_date = re.sub(rf"-02-(29|3\d)$", "-02-28", str_date)
        str_date = re.sub(rf"-(04|06|09|11)-(3[1-9])$", "-\\1-30", str_date)
        return str_date

    def _add_join_on(self, table: str, constraint: str) -> None:
        """
        Associate one or more WHERE statements with a JOIN statement
        """
        table = table.lower()
        if table in self._joins:
            if self._joins[table] is None:
                self._joins[table] = set()
            assert isinstance(
                self._joins[table], set
            ), "Constraint _joins should be lists"
            cast(set, self._joins[table]).add(constraint)
        else:
            self._joins[table] = {constraint}

    def _get_layer_info(self, conf: Config, layer: str) -> JSONObject:
        """
        todo: remove this once metadata is standardised
        """
        info: dict

        # assert layer in conf.config["layer"], ReferenceError(
        #     f"No entity type named {layer} in this corpus"
        # )
        # info = cast(dict, conf.config["layer"][layer])
        info = cast(dict, conf.config["layer"].get(layer, {}))

        if conf.lang:
            lginfo: dict = cast(
                dict,
                conf.config["layer"]
                .get(f"{layer}@{conf.lang}", {})
                .get("attributes", {}),
            )
            for k, v in lginfo.items():
                info["attributes"][k] = v

        return cast(JSONObject, info)

    def _get_cast(self, field: str, query: Any) -> str:
        """
        Determine whether or not we need to cast to int, float, text or nothing
        """
        if isinstance(query, (list, tuple, set)):
            query = list(query)[0]
        if self._query_variable:
            return ""
        if self._is_meta:
            met = cast(
                dict, self._layer_info.get("meta", self._attribs.get("meta", {}))
            )
            typ = cast(str, cast(dict, met[self.field]).get("type", ""))
        else:
            met = cast(dict, self._attribs.get(self.field, {}))
            typ = cast(str, met.get("type", ""))
        if typ.startswith("int") and isinstance(query, int):
            return "::bigint"
        elif typ.startswith("int") and not isinstance(query, int):
            return "::text"
        elif typ.startswith("float") and isinstance(query, float):
            return "::float"
        elif typ.startswith("float") and not isinstance(query, float):
            return "::text"
        elif _valid_uuid(query):
            return "::uuid"
        return "::text"

    def _layer(self, layer: str) -> str:
        """
        If token table was requested, get batch instead
        """
        if layer == self.config["token"]:
            return self.conf.batch
        return layer

    def get_reference(
        self,
        reference: dict[str, Any],
        force_prefix: str | None = None,
        force_attributes: dict[str, Any] = {},
        force_mapping: dict[str, Any] = {},
        as_pointer: bool = False,
        no_join: bool = False,
    ) -> tuple[str, dict]:
        """
        Parse a reference object and return an SQL-compatible string reference.
        If no_join is False (default), will also add necessary joins
        """
        ref = ""
        sub_fields: list[str] = []
        if "entity" in reference:
            ref_field = reference["entity"]
            ref_label = self.label
            if force_prefix:
                ref_label = force_prefix
            if "." in ref_field:
                # If there's a dot in the reference string...
                pre_dot, *post_dots = ref_field.split(".")
                # ... and if the prefix is not an attribute name: treat it as a layer referencd
                if pre_dot not in force_attributes:
                    label_layer = self.label_layer or {}
                    assert pre_dot in label_layer, ReferenceError(
                        f"Reference to label '{pre_dot}' in '{ref_field} could not be resolved"
                    )
                    ref_layer = label_layer[pre_dot][0]
                    force_prefix = pre_dot
                    force_attributes = self.config["layer"][ref_layer].get(
                        "attributes", {}
                    )
                    force_mapping = _get_mapping(
                        ref_layer, self.config, self.batch, self.lang or ""
                    ).get("attributes", {})
                    new_ref = {"entity": ".".join(post_dots)}
                    # Now process the post-dot string as a reference to an attribute of the pre-dot layer
                    return self.get_reference(
                        new_ref, force_prefix, force_attributes, force_mapping
                    )
                ref_field = pre_dot
                sub_fields = post_dots
            # Retrieve the layer from the label (either provided as force_prefix, or before the dot)
            label_layer = self.label_layer or {}
            ref_layer = label_layer.get(ref_label, [self.layer])[0]
            if ref_label not in label_layer and ref_field in label_layer:
                ref_layer = label_layer[ref_field][0]
            ref_layer_attrs = force_attributes or self.config["layer"][ref_layer].get(
                "attributes", {}
            )
            ref_layer_mapping = self.config["mapping"]["layer"].get(ref_layer, {})
            field_meta_attrs = ref_layer_attrs.get("meta", {})
            is_meta = ref_field in field_meta_attrs
            # If ref_field is a label for a layer, and not part of the layer's attributes
            if (
                ref_field in label_layer
                and not is_meta
                and ref_field not in ref_layer_attrs
            ):  # Return a layer reference
                return (ref_field, {"type": "layer", "layer": ref_layer})
            field_mapping = (
                force_mapping
                or _get_mapping(
                    ref_layer, self.config, self.batch, self.lang or ""
                ).get("attributes", {})
            ).get(ref_field, {})
            ref = f"{ref_label}.{ref_field}"
            assert ref_field in ref_layer_attrs or is_meta, ReferenceError(
                f"No attribute named '{ref_field}' on {ref_layer} '{ref_label}'"
            )
            field_info = {
                "layer": ref_layer,
                "mapping": field_mapping,
                **ref_layer_attrs.get(ref_field, field_meta_attrs.get(ref_field, {})),
            }
            global_ref = field_info.get("ref", "")
            assert (
                not global_ref or global_ref in self.config["globalAttributes"]
            ), ReferenceError(
                f"No global attribute named '{global_ref}' could be found"
            )
            field_type = field_info.get("type", ("dict" if global_ref else ""))
            field_mapping_type = field_mapping.get("type", "")
            assert not global_ref or field_mapping_type == "relation", AssertionError(
                f"Structure mismatch: {ref_label}.{ref_field} reported as a global but non-relational attribute!"
            )
            as_pointer = as_pointer or (global_ref and not sub_fields)
            if alignment := ref_layer_mapping.get("alignment", {}).get("relation", {}):
                new_label = f"{ref_label}_alignment"
                formed_join_table = f"{self.schema}.{alignment} {new_label}"
                formed_join_condition = (
                    f"{ref_label}.alignment_id = {new_label}.alignment_id"
                )
                self._add_join_on(
                    formed_join_table.lower(), formed_join_condition.lower()
                )
                ref_label = new_label
            if is_meta or field_mapping_type == "json":
                meta_prefix = ".meta" if is_meta else ""
                arrow = "->" if field_type == "dict" else "->>"
                ref = f"({ref_label}{meta_prefix}{arrow}'{ref_field}')"
            elif field_mapping_type == "relation" and not field_type == "labels":
                ref_key = field_mapping.get("key", ref_field)
                if as_pointer:
                    return (f"{ref_label}.{ref_key}_id", field_info)
                ref_table = field_mapping.get("name", ref_field)
                new_ref_label = f"{ref_label}_{ref_key}".lower()
                join_table: str = f"{self.schema}.{ref_table} {new_ref_label}"
                formed_join_condition = (
                    f"{ref_label}.{ref_key}_id = {new_ref_label}.{ref_key}_id"
                )
                if not no_join:
                    self._add_join_on(join_table.lower(), formed_join_condition.lower())
                ref_label = new_ref_label
                ref = f"{ref_label}.{ref_field}"
            if sub_fields:
                assert (
                    field_type == "dict"
                    and field_mapping_type == "relation"
                    and global_ref
                ), ReferenceError(
                    f"Cannot reference sub-attributes on {ref_label}.{ref_field}"
                )
                new_ref = {"entity": ".".join(sub_fields)}
                global_attributes = (
                    self.config["globalAttributes"].get(ref_key, {}).get("keys", {})
                )
                return self.get_reference(
                    new_ref,
                    force_prefix=ref,
                    force_attributes=global_attributes,
                    force_mapping={k: {"type": "json"} for k in global_attributes},
                )

        elif "function" in reference:
            return self.parse_function(reference["function"])

        return (ref, field_info)

    def make(self) -> None:
        """
        Actually make the joins and the WHERE clause bits
        """
        if self._made:
            return None

        if not self.label:
            self.label = f"{self.layer.lower()}_{str(self._n)}"

        # Special handling of dependencies
        if self._is_dependency:
            self.deprel()
            self._made = True
            return None

        right_member = self._query
        if self.type == "entity" and isinstance(self._query, str):
            right_member = {"entity": self._query}

        mapping = _get_mapping(
            self.layer, self.config, self.batch, self.lang or ""
        ).get("attributes", {})

        left_ref: tuple[str, dict]
        right_ref: tuple[str, dict]
        both_lookups: bool = False
        if isinstance(right_member, dict):
            # First pass without joins, just to get the types of the references
            left_ref, right_ref = [
                self.get_reference(x, self.label, self._attribs, mapping, no_join=True)
                for x in (self.left, right_member)
            ]
            both_lookups = all(x[1].get("ref") for x in (left_ref, right_ref))

        # Left reference
        left_ref = self.get_reference(
            self.left,
            self.label,
            self._attribs,
            mapping,
            as_pointer=both_lookups,
        )

        # Right reference
        if isinstance(right_member, dict):
            right_ref = self.get_reference(
                right_member,
                self.label,
                self._attribs,
                mapping,
                as_pointer=both_lookups,
            )
        else:
            right_ref = (f"'{str(right_member)}'", {"type": "text"})

        cast: str = ""
        if self.type == "regex":
            cast = "::text"
        formed_condition: str = f"{left_ref[0]}{cast} {self.op} {right_ref[0]}"

        # Special case: labels
        left_ref_info = left_ref[1]
        left_type = left_ref_info.get("type")
        if left_type == "labels":
            assert self.op.lower().endswith("contain"), SyntaxError(
                f"Must use 'contain' on labels ({left_ref[0]} + {self.op})"
            )
            assert self.type in ("string", "regex"), TypeError(
                f"Contained labels can only be tested against strings or regexes ({left_ref[0]} + {self.op} + {right_ref[0]})"
            )
            ref_layer = left_ref_info.get("layer", self.layer)
            ref_layer_info = self.config["layer"].get(ref_layer, {})
            assert "nlabels" in ref_layer_info, KeyError(
                f"Missing 'nlabels' for layer '{ref_layer}' in config"
            )
            nbit = ref_layer_info["nlabels"]
            ref_mapping = left_ref_info.get("mapping", {})
            lookup_table = ref_mapping.get("name", "")
            inner_op = "~" if self.type == "regex" else "="
            inner_condition = (
                "(SELECT bit_or(0::bit(113)<<0)::bit(113) AS m UNION "  # In case no label matches the condition
                + f"SELECT bit_or(1::bit({nbit})<<bit)::bit({nbit}) AS m "
                + f"FROM {self.schema}.{lookup_table} WHERE label {inner_op} {right_ref[0]})"
            )
            # Use label_layer to store the inner conditions query-wide and give them unique labels
            if self.label_layer is None:
                self.label_layer = {}
            if self.label not in self.label_layer:
                self.label_layer[self.label] = (self.layer, {})
            meta: dict = self.label_layer[self.label][1]
            meta["labels inner conditions"] = meta.get("labels inner conditions", {})
            comp_str: str = f"{self.op} {self.type} {right_ref[0]}"
            n = meta["labels inner conditions"].get(
                comp_str, len(meta["labels inner conditions"])
            )
            meta["labels inner conditions"][comp_str] = n
            mask_label = f"{self.label}_mask_{n}"
            formed_join_table = f"{inner_condition} {mask_label}"
            self._add_join_on(formed_join_table, "")
            op = "=" if self.op.lower().startswith(("not", "!")) else ">"
            formed_condition = f"{left_ref[0]} & {mask_label}.m {op} 0::bit({nbit})"

        elif left_type == "date":
            right_ref_info = right_ref[1]
            assert right_ref_info.get("type") in ("date", "text", "number"), TypeError(
                f"Invalid date comparison ({left_ref[0]} {self.op} {right_ref[0]})"
            )
            q = right_ref[0]
            if self.op in (">", "<", ">=", "<=", "=", "!="):
                right_ref_no_quotes = right_ref[0].strip("'").strip('"')
                lower_date = self._parse_date(right_ref_no_quotes)
                upper_date = self._parse_date(
                    right_ref_no_quotes, filler_month="12", filler_day="31"
                )
                op = self.op
                if op == "=":
                    op = ">="
                    q = f"'{lower_date}'::date AND {left_ref[0]}::date <= '{upper_date}'::date"
                elif op == "!=":
                    op = "<"
                    q = f"'{lower_date}'::date OR {left_ref[0]}::date > '{upper_date}'::date"
                elif op in (">", ">="):
                    q = f"'{upper_date}'::date"
                elif op in ("<", "<="):
                    q = f"'{lower_date}'::date"
            formed_condition = f"{left_ref[0]}::date {op} {q}"

        self._joins.pop("", None)
        self._conditions.add(formed_condition)
        self.made = True
        return None

    def parse_function(
        self,
        fn_obj: dict[str, Any],
    ) -> tuple[str, dict]:
        fn = fn_obj.get("functionName", "")
        assert fn in FUNCS, NotImplementedError(
            f"Function '{fn}' not implemented (yet?)"
        )
        ars = fn_obj.get("arguments", [])
        assert ars, ValueError(f"Arguments of function '{fn}' are missing")
        parsed_ars = [self.get_reference(a) for a in ars]
        ars_str = ",".join([a[0] for a in parsed_ars])
        fn_str = f"{fn}({ars_str})"
        fn_info = {"type": "text"}
        if fn == "range":
            first_arg_str, first_arg_info = parsed_ars[0]
            assert first_arg_info.get("type") == "layer", TypeError(
                f"Range only applies to layer annotations (error in '{first_arg_str}')"
            )
            fn_str = (
                f"upper({first_arg_str}.char_range) - lower({first_arg_str}.char_range)"
            )
            fn_info = {"type": "number"}
        elif fn == "position":
            first_arg_str, first_arg_info = parsed_ars[0]
            assert first_arg_info.get("type") == "layer", TypeError(
                f"Range only applies to layer annotations (error in '{first_arg_str}')"
            )
            fn_str = f"lower({first_arg_str}.char_range)"
            fn_info = {"type": "number"}
        return (fn_str, fn_info)

    def id_field(self):
        """
        Handle querying on segment_id, token_id etc
        """
        is_uuid = _valid_uuid(self._query)
        cast = "::text" if not is_uuid else "::uuid"
        op = self.op
        qcast = ""
        if _valid_uuid(self._query):
            op = op.replace("~", "=")
            qcast = "::uuid"
        elif isinstance(self._formatted, int):
            cast = "::bigint"
        else:
            cast = "::text"

        col = f"{self.original_layer}_id"

        formed = f"{self.label}.{col}{cast} {op} {self._formatted}{qcast}"
        self._add_join_on(f"{self.schema}.{self.layer} {self.label}", formed)

    def metadata(self):
        """
        Handle metadata like IsPresident = No
        """
        lb, rb = "(", ")"
        if not self._cast:
            lb, rb = "", ""
        lab = self.label
        # mapping = _get_mapping(self.layer, self.config, self.batch, self.lang)
        mapping = self.config["mapping"]["layer"].get(self.layer, {})
        if (
            "alignment" in mapping
            and mapping["alignment"].get("hasMeta")
            and (relation := mapping["alignment"].get("relation"))
        ):
            lab = f"{self.label}_aligned"
            self._add_join_on(
                f"{self.schema}.{relation} {lab}",
                f"{self.label}.alignment_id = {lab}.alignment_id",
            )
        formed = f"{lb}{lab}.meta ->> '{self.field}'{rb}{self._cast} {self.op} {self._formatted}"
        # if self.layer == self.config["document"]:
        #     self._add_join_on(f"{self.schema}.{self.layer} {self.label}", formed)
        # else:
        self._conditions.add(formed)

    def deprel(self) -> None:
        """
        Handle dependency query
        """
        dep_table = _get_table(self.layer, self.config, self.batch, self.lang or "")
        label = f"deprel_{self.label}".lower()
        source, target = {
            x.get("name", "")
            for n, x in self._attribs.items()
            if n in ("source", "target")
        }
        field = self.field.lower().strip()
        if field in (source, target):
            assert self.type == "entity", TypeError(
                f"Invalid type for '{self.field}': dependency references must be entity labels"
            )
            entity_label = str(self._query).strip()
            lablay: dict[str, Any] = self.label_layer or {}
            entity_layer = lablay.get(entity_label, [""])[0]
            formed_condition = (
                f"{label}.{field} {self.op} {entity_label}.{entity_layer}_id"
            )
            self._add_join_on(
                f"{self.schema}.{dep_table} {label}", formed_condition.lower()
            )
        else:
            cast = "::text" if self.type == "regex" else ""
            lterm = f"{label}.{field}{cast}"
            formed_condition = f"{lterm.lower()} {self.op} {self._formatted}"
            self._add_join_on(f"{self.schema}.{dep_table} {label}", formed_condition)

    def _standardise_op(self, op: str) -> str:
        """
        post-process op: =, !=, etc
        """
        if self._query_variable:
            return op.replace("~", "=")
        if "CONTAIN" in op.upper():
            if op.startswith(("!", "NOT", "not")):
                op = "!contain"
            else:
                op = "contain"
        elif "NIN" in op.upper():
            op = "NOT IN"
        elif "IN" in op.upper():
            op = "IN"
        elif self.type == "regex":
            op = op.replace("=", "~")
        return op.upper()

    def date(self) -> None:
        q: str = f"{self._formatted}"
        op = self.op
        cast = self._cast
        labfield = f"{self.label.lower()}.{self.field.lower()}"
        if op in (">", "<", ">=", "<=", "=", "!="):
            lower_date = self._parse_date(q)
            upper_date = self._parse_date(q, filler_month="12", filler_day="31")
            cast = "::date"
            if op == "=":
                op = ">="
                q = f"'{lower_date}'::date AND {labfield}{cast} <= '{upper_date}'::date"
            elif op == "!=":
                op = "<"
                q = f"'{lower_date}'::date OR {labfield}{cast} > '{upper_date}'::date"
            elif op in (">", ">="):
                q = f"'{upper_date}'::date"
            elif op in ("<", "<="):
                q = f"'{lower_date}'::date"
        formed = f"{self.label.lower()}.{self.field.lower()}{cast} {op} {q}"
        self._conditions.add(formed)

    def _to_sql(self, query: QueryType) -> str | int | float:
        """
        Turn query into something that can be inserted into sql with f-string
        """
        # detect variable
        if self.type == "entity":
            return str(query)
        elif self.type == "math":
            if isinstance(query, str) and query.strip().isnumeric():
                return int(query.strip())
            elif (
                isinstance(query, str)
                and "." in query
                and query.strip().replace(".", "").isnumeric()
            ):
                return float(query.strip())
            else:
                # check that the expression is well-formed here?
                return f"({str(query)})"
        elif self.type == "function":
            # Hack for simple cases, need to do better
            function_name: str = cast(dict, query).get("functionName", "")
            function_arguments: list = cast(
                list[dict[str, str]], cast(dict, query).get("arguments", [{}])
            )
            first_argument: str = (
                function_arguments[0].get("entity", "").replace(".", "_")
            )
            return f"{function_name}({first_argument})"

        if isinstance(query, (list, tuple)):
            if len(query) == 1:
                query = query[0]
            else:
                items = [f"'{a}'" if isinstance(a, str) else str(a) for a in query]
                formed = ", ".join(items)
                return f"({formed})"
        return f"'{query}'" if isinstance(query, str) else cast(str, query)


class TimeConstraint:
    """
    Handle a constraint based on time
    """

    def __init__(
        self,
        schema: str,
        layer: str,
        label: str,
        quantor: str | None,
        label_layer: LabelLayer,
        conf: Config,
        boundary: str,
        comp1: dict[str, Any],
        obj: str,
        comp2: str = "",
        diff: str = "",
        op: str = ">=",
    ) -> None:
        self.schema: str = schema
        self.layer: str = layer
        self.label: str = label
        self.quantor: str | None = quantor
        self.boundary: str = boundary
        self.comp1: dict[str, Any] = comp1
        self.obj: str = obj
        self.comp2: str = comp2
        self.label_layer: LabelLayer = label_layer
        self.conf: Config = conf
        self.diff: int | float | None = self._parse_time(diff)
        self.op: str = op
        self._joins: Joins = {}
        self._conditions: set[str] = set()
        self._quantor_label: str | None = None
        self._made = False
        # start and end in time queries

    def make(self) -> None:
        """
        Build the constraint (populate _joins and _conditions)
        """
        is_start = "start" in self.boundary.lower()
        is_start_compare = "start" in self.comp2.lower()
        func = "lower" if is_start else "upper"
        func_compare = "lower" if is_start_compare else "upper"
        # sign = "-" if is_start else "+"
        sign = "-" if re.match(rf"-\s*[0-9]", self.obj) else "+"
        compare = self.obj.split(".", 1)[0]
        lte: str = ">=" if self.op not in (">", ">=", "<", "<=") else self.op
        # lte = ">=" if is_start else "<="
        # lab = self._quantor_label or self.label
        lab = self.label
        formed = f"{func}({lab}.frame_range) {lte} {func_compare}({compare}.frame_range) {sign} {self.diff} * 25"
        self._conditions.add(formed.lower())
        table: str = _get_table(
            self.layer, self.conf.config, self.conf.batch, cast(str, self.conf.lang)
        )
        join = f"{self.schema}.{table} {self.label}"
        self._joins[join.lower()] = self._joins.get(join.lower(), None)
        self._made = True
        return None

    @staticmethod
    def _parse_time(time: str) -> int | float | None:
        """
        Normalise a time in format "1ms" to number of seconds as int if possible, float fallback
        """
        if not time.strip():
            return None
        unit = "".join([i for i in time if i.isalpha()]).lower()
        amount: int | float = float(
            "".join([i for i in time if i.isnumeric() or i == "."])
        )
        if unit == "s":
            pass
        elif unit == "ms":
            amount = amount / 1000
        elif unit == "m":
            amount = amount * 60
        elif unit == "h":
            amount = amount * 3600
        elif unit == "d":
            amount = amount * 3600 * 24
        elif amount == "w":
            amount = amount * 3600 * 24 * 7
        if isinstance(amount, float) and amount.is_integer():
            amount = int(amount)
        return amount


def _get_constraint(
    constraint: JSONObject,
    layer: str,
    label: str,
    conf: Config,
    quantor: str | None = None,
    n: int = 1,
    order: int | None = None,
    prev_label: str | None = None,
    label_layer: LabelLayer = {},
    entities: set[str] | None = None,
    is_set: bool = False,
    set_objects: set[str] | None = None,
    allow_any: bool = True,  # False,
    top_level: bool = False,
) -> Constraint | Constraints | TimeConstraint | None:
    """
    Handle a single constraint, or nested constraints
    """

    first_key_in_constraint = next(iter(constraint), "")

    if first_key_in_constraint.endswith("Quantification"):
        obj: dict[str, Any] = cast(dict[str, Any], next(iter(constraint.values())))
        if "quantor" in obj:
            quantor_str: str = obj.get("quantor", "")
            if quantor_str.endswith(("EXIST", "EXISTS")):
                if quantor_str.startswith(("!", "~", "¬", "NOT")):
                    quantor_str = "NOT EXISTS"
                else:
                    quantor_str = "EXISTS"
            quantor = quantor_str
            constraint = obj.get("args", [{}])[0]
            obj_layer = label_layer.get(obj.get("label", ""), [""])[0]
            if _layer_contains(conf.config, layer, obj_layer) or all(
                _is_anchored(conf.config, x, "stream") for x in (layer, obj_layer)
            ):
                part_of = label
            first_key_in_constraint = next(iter(constraint), "")

    unit: dict[str, Any] = cast(dict[str, Any], constraint.get("unit", {}))
    if unit.get("constraints"):
        unit_layer: str = cast(str, unit.get("layer", ""))
        unit_label = (
            label  # Pass the parent's label if the layer is a dependency relation
        )
        if unit_layer.lower() not in ["deprel", "dependencyrelation"]:
            unit_label = unit.get("label", "")
        else:
            label_layer[label] = (layer, dict())
        part_of = unit.get("partOf", "")
        # Use the parent label as part_of if they are both stream-anchored
        if label != unit.get("label") and (
            _layer_contains(conf.config, layer, unit_layer)
            or all(_is_anchored(conf.config, x, "stream") for x in (layer, unit_layer))
        ):
            part_of = label
        args = (
            cast(JSONObject, unit["constraints"]),
            unit_layer,
            unit_label,
            conf,
            quantor,
            "AND",
            n,
            order,
            prev_label,
            label_layer,
            entities,
            part_of,
            is_set,
            set_objects,
            allow_any,
            top_level,
        )
        return _get_constraints(*args)

    elif first_key_in_constraint.startswith("logicalOp"):
        obj = cast(dict[str, Any], next(iter(constraint.values())))
        # the default operator is AND, and it can be missing
        if "operator" not in obj:
            obj["operator"] = "AND"

        return _get_constraints(
            obj.get("args", []),
            cast(str, obj.get("layer", layer)),  # todo: which layer is correct?
            cast(str, obj.get("label", label)),
            conf,
            cast(str | None, quantor),
            obj["operator"],
            n + 1,
            order,
            prev_label,
            label_layer,
            entities,
            "",  # no part_of here
            is_set,
            set_objects,
            allow_any,
            top_level,
        )

    if not len(constraint):
        if order is None:
            return None
        # This is a hack that needs to be improved to not ignore empty tokens in sequences
        constraint = {
            "comparison": {"entity": "_", "operator": "=", "entityComparison": "_"}
        }

    comp = cast(dict[str, Any], constraint.get("comparison", {}))
    assert (
        "left" in comp and "operator" in comp
    ), "left and/or operator not found in comparison"

    key, op, comparison_type, query = _parse_comparison(comp)
    key_str: str = key.get("entity", "")

    is_time_anchored = _is_anchored(conf.config, layer, "time")

    # Use a TimeConstraint if the right-hand side of a math comparison contains a time unit (ie ending in \d(s|m|ms|h|d|w))
    if (
        is_time_anchored
        and key.get("entity", "") in ("start", "end")
        and comparison_type == "mathComparison"
    ):  # and re.match(r".*\d(s|m|ms|h|d|w)([\s()*/+-]|$)",query):
        rest: dict = {
            "boundary": "start" if "start" in key_str.lower() else "end",
            "comp1": key,
            "obj": query,
            "comp2": query,
            "diff": re.sub(
                r"^.*?([0-9][0-9.]*(s|m|ms|h|d|w)?).*$", "\\1", cast(str, query)
            ),
            "op": op,
        }
        return TimeConstraint(
            conf.schema, layer, label, quantor, label_layer, conf, **rest
        )
    else:
        return Constraint(
            key,
            op,
            query,
            label,
            layer,
            conf,
            comparison_type.replace("Comparison", ""),
            quantor,
            label_layer,
            entities,
            n,
            is_set,
            set_objects,
            order,
            prev_label,
            allow_any,
        )


def _get_constraints(
    constraints: JSONObject,  # Should be an array of constraints (see cobquec)
    layer: str,
    label: str,
    conf: Config,
    quantor: str | None = None,
    op: str | None = "AND",
    n: int = 1,
    order: int | None = None,
    prev_label: str | None = None,
    label_layer: LabelLayer = {},
    entities: set[str] | None = None,
    part_of: str | None = None,
    is_set: bool = False,
    set_objects: set[str] | None = None,
    allow_any: bool = True,  # False,
    top_level=False,
) -> Constraints | None:
    """
    Create a Constraints object containing all subconstraints

    n is just an ever-incrementing number needed to make unique query names

    order and prev_label are for objects within a sequence

    If allow_any, even constraints belonging to objects not in entities
    will be created.

    top_level is special handling for constraints at base level (tangram4.json)
    """
    # if not constraints and order is None:
    #     return None

    if top_level:
        allow_any = True
        # sorry about this:
        first_unit: dict[str, Any] = next(
            (
                cast(dict[str, Any], cast(JSONObject, i)["unit"])
                for i in cast(
                    list[JSONObject],
                    sorted(
                        cast(list[dict], constraints), key=arg_sort_key
                    ),  # why do we assume the existence of an args key here?
                )
                if "unit" in cast(JSONObject, i)
            ),
            {},
        )
        first_layer = first_unit.get("layer", "")

    results = []
    # op = cast(str, constraints.get("operator", "AND"))

    lab = label or f"constraint_{n}"

    if part_of:
        part_of_layer: str = label_layer.get(part_of, ("", None))[0]
        segname = conf.config["segment"].lower()
        is_token = layer.lower() in (conf.config["token"].lower(), conf.batch.lower())
        if part_of == label:
            part_of = ""
        elif (
            is_token and part_of_layer.lower() == segname
        ):  # Use id for token in segment
            part_of = f"{part_of}.{segname}_id = {label}.{segname}_id"
        else:
            part_of = f"{part_of}.char_range && {label}.char_range"

    args = cast(list[JSONObject], constraints)
    for arg in sorted(args, key=arg_sort_key):
        arg_label = cast(str, lab if not top_level else arg.get("label", ""))
        tup = _get_constraint(
            arg,
            layer,
            arg_label,
            conf,
            quantor=None,  # quantor is not passed down to single constraints
            n=n,
            order=order,
            prev_label=prev_label,
            label_layer=label_layer,
            entities=entities,
            is_set=is_set,
            set_objects=set_objects,
            allow_any=allow_any,
            top_level=top_level,
        )
        if not isinstance(tup, TimeConstraint):
            n += 1
        results.append(tup)
    lay: str = layer if not top_level else first_layer
    return Constraints(
        conf.schema,
        lay,
        lab,
        conf,
        results,
        cast(str, op),
        quantor,
        label_layer,
        entities,
        part_of,
        n=n,
        is_set=is_set,
        set_objects=set_objects,
        allow_any=allow_any,
    )


def process_set(
    conf: Config,
    r: QueryData,
    _n: int,
    token: str,
    segment: str,
    _underlang: str | None,
    set_data: dict,
    seg_label: str | None = None,
    attribute="___tokenid___",
    label: str = "",
) -> str:
    batch = conf.batch
    schema = conf.schema
    config = conf.config

    joins: Joins = {}

    conditions: set[str] = set()
    if attribute == "___tokenid___":
        field = cast(str, config["token"]).lower() + "_id"
    elif (
        config["layer"][token]["attributes"].get(attribute, {}).get("type", "")
        == "text"
    ):
        field = attribute + "_id"
    else:
        field = attribute

    if not label:
        label = set_data.get("label", f"unknown_{_n}") + f"_{field}"

    first_unit: dict[str, Any] = next(
        (u["unit"] for u in set_data.get("members", []) if "unit" in u), {}
    )
    from_label = first_unit.get("label", "t")
    lay = first_unit.get("layer", token)
    assert config["layer"][lay].get("layerType") != "relation", TypeError(
        f"Cannot build a set of relational entities ({lay})"
    )

    lang: str = cast(str, _underlang)[1:] if _underlang else ""
    from_table = batch if lay == token else _get_table(lay, config, batch, lang)
    disallowed = f"{schema}.{lay} {from_label}"

    if "partOf" in first_unit:
        part_of_label = first_unit["partOf"]
        part_of_layer = r.label_layer.get(part_of_label, [""])[0]
        if part_of_label == "___seglabel___":
            part_of_layer = segment
        if part_of_layer.lower() == segment.lower():
            first_unit["partOf"] = seg_label

    conn_obj = _get_constraints(
        first_unit.get("constraints", []),
        first_unit.get("layer", ""),
        from_label,
        conf,
        label_layer=r.label_layer,
        entities=set(),
        part_of=first_unit.get("partOf", None),
        set_objects=r.set_objects,
        n=_n,
        is_set=True,
        top_level=False,
    )
    if conn_obj:
        _n = conn_obj._n + 1
        join = conn_obj.joins() if conn_obj else {}
        for k, v in join.items():
            if disallowed.lower() == k.lower():
                continue
            joins[k] = v
            if not isinstance(v, set):
                continue
            for join_condition in v:
                if not isinstance(join_condition, str):
                    continue
                conditions.add(join_condition)
        cond = conn_obj.conditions() if conn_obj else ""
        if cond:
            conditions.add(cond)

    if config["layer"][lay].get("contains") == config["token"]:
        joins[f"{schema}.{from_table} {from_label}"] = True
        conditions.add(f"{from_label}.char_range && anonymous_set_t.char_range")
        from_table = batch
        from_label = "anonymous_set_t"

    strung_joins = _joinstring(joins)
    strung_conds = "WHERE " + " AND ".join(conditions) if conditions else ""

    formed = f"""
              (SELECT array_agg({from_label}.{field})
              FROM {schema}.{from_table} {from_label}
               {strung_joins} 
               {strung_conds}
              ) AS {label}
    """
    return formed.strip()

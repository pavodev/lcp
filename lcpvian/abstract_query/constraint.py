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
FUNCS = (
    "length",
    "century",
    "decade",
    "year",
    "month",
    "day",
)


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
        crossjoins = "\n".join(
            f"CROSS JOIN {x}" for x in joins if not_allowed not in x.lower()
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
        out: set[str] = set()
        for member in self.members:
            if isinstance(member, Constraints) and member.quantor:
                res = self._build_subquery(cast(Self, member))
                if res.strip():
                    out.add(res)
            elif isinstance(member, Constraints) and not member.quantor:
                member.make()
                cons = member.conditions()
                if cons.strip():
                    out.add(cons)
            elif isinstance(member, (TimeConstraint, Constraint)):
                # do we need a sublevel here?
                member.make()
                # Constraint instances necessarily connect their conditions with AND
                stripped_conditions = [c for c in member._conditions if c.strip()]
                conjunction = " AND ".join(stripped_conditions)
                if len(stripped_conditions) > 1 and self.conj.upper() != "AND":
                    out.add(f"({conjunction})")
                elif stripped_conditions:
                    out.add(conjunction)
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
                        cast(set, out[k]).add(v)
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
        type: str = "string",
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
        self.field = field.get("entity", "")
        self._layer_info = self._get_layer_info(conf, layer)
        self._attribs = cast(dict[str, Any], self._layer_info.get("attributes", {}))
        self._pseudo_attribs = {
            "length",
            "position",
            "leftpos",
            "rightpos",
        }  # pseudo-attributes are computed
        self.type = type
        self._query = query
        self._query_variable = (
            type == "entity"
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
        self._is_dependency = self._layer_info[
            "layerType"
        ] == "relation" and self.field in {
            cast(dict[str, str], x).get("name", "")
            for n, x in {
                "label": {"name": "label"},
                **cast(dict[str, Any], self._layer_info.get("attributes", {})),
            }.items()
            if n
            in (
                "source",
                "target",
                "label",
            )  # Revise special treatment of "label" here?
        }
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

        assert layer in conf.config["layer"], ReferenceError(
            f"No entity type named {layer} in this corpus"
        )
        info = cast(dict, conf.config["layer"][layer])

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

        # Gather info about the field and proceed to some checks
        field, *attributes = self.field.split(".")
        field_info = self._attribs.get(
            field, self._attribs.get("meta", {}).get(field, {})
        )
        assert field_info or self.field_function, ReferenceError(
            f"{self.layer} {self.label} has no attribute named '{field}'"
        )
        field_type = field_info.get("type", "")
        field_ref = field_info.get("ref")
        attributes_mapping = _get_mapping(
            self.layer, self.config, self.batch, cast(str, self.lang)
        ).get("attributes", {})
        field_mapping = attributes_mapping.get(field, {})
        relational_field = field_mapping.get("type", "") == "relation"

        # Gather info about the attribute and proceed to some checks
        if "." in self.field:
            subattribute = ".".join(attributes)
            if field_ref:
                global_attribute = self.config.get("globalAttributes", {}).get(
                    field_ref
                )
                assert global_attribute, ReferenceError(
                    f"Could not find a global attribute for '{field}' named '{field_ref}'"
                )
                field_info = global_attribute
                field_type = field_info.get("type", "")

            if field_type == "dict":
                keys = field_info.get("keys", {})
                assert subattribute in keys, ReferenceError(
                    f"{self.label}'s {field} has no subattribute named '{subattribute}'"
                )
            else:
                raise TypeError(
                    f"{self.layer} {self.label}'s attribute '{field}' has no sub-attributes ('{subattribute}')"
                )

        # Special checks for entity comparisons
        entity_dict: dict[str, Any] = {}
        if self.type == "entity":
            entity_dict = self.parse_entity(field_type, relational_field)
            relational_entity = entity_dict.get("relational")
            entity_label: str = cast(str, entity_dict.get("label"))
            entity_layer: str = cast(str, entity_dict.get("layer"))
            entity_field: str = cast(str, entity_dict.get("field"))
            # Proceed immediately if simply comparing two FKs
            if relational_field and relational_entity:  # and field_type == "dict":
                formed_condition = f"{self.label}.{self.field}_id {self.op} {entity_label}.{entity_field}_id"
                entity_table = _get_table(
                    entity_layer, self.config, self.batch, cast(str, self.lang)
                )
                formed_join_table = f"{self.schema}.{entity_table} {entity_label}"
                self._add_join_on(formed_join_table.lower(), formed_condition.lower())
                self._made = True
                return None

        label: str = self.label
        field_ref = f"{self.label}.{self.field}"
        formatted: str = cast(str, self._formatted)

        if field_type == "labels" or self.op.lower().endswith("contain"):
            assert field_type == "labels" and self.op.lower().endswith(
                "contain"
            ), TypeError(
                f"Use the operator 'contain' if and only if testing an attribute of type 'labels' (attempted to use operator '{self.op}' on attribute of type {field_type})"
            )
            assert self.type in ("string", "regex"), TypeError(
                "Contained labels can only be tested against strings or regexes"
            )
            assert "nlabels" in self._layer_info, KeyError(
                f"Missing 'nlabels' for layer '{self.layer}' in config"
            )
            lookup_table = field_mapping.get("name", "")
            inner_op = "~" if self.type == "regex" else "="
            nbit = self._layer_info["nlabels"]
            inner_condition = f"(SELECT sum(1<<bit)::bit({nbit}) AS m FROM {self.schema}.{lookup_table} WHERE label {inner_op} {formatted})"
            # Use label_layer to store the inner conditions query-wide and give them unique labels
            if self.label_layer is None:
                self.label_layer = {}
            if label not in self.label_layer:
                self.label_layer[label] = (self.layer, {})
            meta: dict = self.label_layer[label][1]
            meta["labels inner conditions"] = meta.get("labels inner conditions", {})
            comp_str: str = f"{self.op} {self.type} {formatted}"
            n = meta["labels inner conditions"].get(
                comp_str, len(meta["labels inner conditions"])
            )
            meta["labels inner conditions"][comp_str] = n
            mask_label = f"{label}_mask_{n}"
            formed_join_table = f"{inner_condition} {mask_label}"
            self._add_join_on(formed_join_table, "")
            op = "=" if self.op.lower().startswith(("not", "!")) else ">"
            formed_condition = f"{field_ref} & {mask_label}.m {op} 0::bit({nbit})"
            self._conditions.add(formed_condition.lower())
            return None

        if (
            alignment := self.config["mapping"]["layer"]
            .get(self.layer, {})
            .get("alignment", {})
            .get("relation", {})
        ):
            label = f"{self.label}_alignment"
            formed_join_table = f"{self.schema}.{alignment} {label}"
            formed_join_condition = f"{self.label}.alignment_id = {label}.alignment_id"
            self._add_join_on(formed_join_table.lower(), formed_join_condition.lower())

        if self.field_function:
            field_ref = self.parse_field_function(attributes_mapping=attributes_mapping)
            self._cast = ""
        else:
            if self._is_meta:
                meta_op: str = "->"
                if self._cast in ("::text", "::int"):
                    meta_op += ">"
                field_ref = f"({label}.meta {meta_op} '{self.field}')"

            # Join any necessary table for the field
            if relational_field:
                field_table = field_mapping.get("name", field)
                field_label: str = f"{label}_{field}".lower()
                join_table: str = f"{self.schema}.{field_table} {field_label}"
                formed_join_condition = f"{label}.{field}_id = {field_label}.{field}_id"
                self._add_join_on(join_table.lower(), formed_join_condition.lower())
                formed_field = re.sub(r"^([^.]+)\.(.+)$", "\\1->>'\\2'", self.field)
                field_ref = f"({field_label}.{formed_field})"

        # Use a join if testing a relational entity (form = x.form  or  agent = x.agent)
        if entity_dict.get("relational"):
            entity_field = cast(str, entity_dict.get("field"))
            assert entity_field, NotImplementedError(
                f"Cannot process comparison '{self.field} {self.op} {self._query}'"
            )
            entity_label = cast(str, entity_dict.get("label"))
            entity_layer = cast(str, entity_dict.get("layer"))
            relation_label: str = f"{entity_label}_{entity_field}".lower()
            formatted = f"{relation_label}.{entity_field}::{self._cast}"
            formed_comparison = f"{field_ref}{self._cast} {self.op} {formatted}"
            entity_table = _get_table(
                entity_layer, self.config, self.batch, cast(str, self.lang)
            )
            join_table = f"{self.schema}.{entity_table} {relation_label}"
            self._add_join_on(join_table.lower(), formed_comparison)
        elif field_type == "date":
            # Handle date exceptionally for now, but later just use functions (year(date), month(date), etc.)
            self.date()
        else:
            if field_type == "categorical" and self.type != "regex":
                self._cast = ""
            formed_comparison = f"{field_ref}{self._cast} {self.op} {formatted}"
            self._conditions.add(formed_comparison)

        self._joins.pop("", None)
        self._made = True

        return None

    def parse_field_function(self, attributes_mapping: dict[str, Any]) -> str:
        fn = self.field_function.get("functionName", "")
        assert fn in FUNCS, NotImplementedError(
            f"Function '{fn}' not implemented (yet?)"
        )
        ars = self.field_function.get("arguments", [])
        assert ars, ValueError(f"Arguments of function '{fn}' are missing")
        assert "function" not in ars[0], NotImplementedError(
            "Nested functions are not supported yet"
        )
        single_arg = ars[0].get("entity", "")
        arg_mapping = attributes_mapping.get(single_arg, {})
        arg_field = single_arg
        if "." in single_arg:
            arg_field = single_arg.split(".")[0]
            arg_mapping = attributes_mapping.get(arg_field, {})
            assert arg_field in self._attribs, ReferenceError(
                f"{self.layer} entity '{self.label}' has no attribute named '{arg_field}'"
            )
            arg_type = self._attribs[arg_field].get(
                "type", self._attribs[arg_field].get("meta", {}).get("type")
            )
            if self._attribs[arg_field].get("ref"):
                arg_type = (
                    self.config.get("globalAttributes", {})
                    .get(arg_field, {})
                    .get("type")
                )
            assert arg_type == "dict", TypeError(
                f"Attribute '{arg_field} of {self.layer} entity '{self.label}' has no subattributes"
            )
        field_ref = f"{fn}({self.label}.{arg_field})"
        if arg_mapping.get("type") == "relation":
            arg_table = arg_mapping.get("name", "")
            self._add_join_on(
                f"{self.schema}.{arg_table} {self.label}_{arg_field}".lower(),
                f"{self.label}.{arg_field}_id = {self.label}_{arg_field}.{arg_field}_id".lower(),
            )
            formed_field = re.sub(r"^([^.]+)\.(.+)$", "\\1->>'\\2'", single_arg)
            field_ref = f"{fn}({self.label}_{arg_field}.{formed_field})"
        return field_ref

    def parse_entity(self, field_type, relational_field) -> dict[str, Any]:
        """
        Constraint is of type entity: check structure of entity references
        Return (True,False) if the entity is relational bt
        Add a condition if both self's field and entity's field point to relational tables
        """
        entity_label, *entity_field_split = cast(str, self._query).strip().split(".")
        entity_field = ".".join(entity_field_split)
        entity_layer = cast(dict, self.label_layer).get(entity_label, [""])[0]
        assert entity_layer in self.config["layer"], RuntimeError(
            f"Couldn't determine which layer to associate the label '{entity_label}' with"
        )
        entity_field_info = (
            self.config["layer"][entity_layer].get("attributes", {}).get(entity_field)
        )
        assert entity_field_info, ReferenceError(
            f"{entity_layer} {entity_label} has no attribute named '{entity_field}'"
        )
        entity_field_type = entity_field_info.get("type", "")
        if entity_field_ref := entity_field_info.get("ref"):
            entity_global_attribute = self.config.get("globalAttributes", {}).get(
                entity_field_ref
            )
            assert entity_global_attribute, ReferenceError(
                f"Could not find a global attribute for '{entity_label}' named '{entity_field}'"
            )
            entity_field_info = entity_global_attribute
            entity_field_type = entity_field_info.get("type", "")
        # assert field_type == entity_field_type, TypeError(
        #     f"Cannot compare {self.label}.{self.field} to {self._query}: incompatible types"
        # )
        entity_field_mapping = (
            _get_mapping(entity_layer, self.config, self.batch, cast(str, self.lang))
            .get("attributes", {})
            .get(entity_field, {})
        )
        relational_entity_field = entity_field_mapping.get("type", "") == "relation"
        if relational_entity_field and field_type == "dict":
            # Both self's field and the entity's field are relational: directly test their FK values
            assert relational_field, TypeError(
                f"Cannot compare {self.label}.{self.field} to {self._query}: incompatible types"
            )
        return {
            "label": entity_label,
            "field": entity_field,
            "layer": entity_layer,
            "field_info": entity_field_info,
            "field_mapping": entity_field_mapping,
            "relational": relational_entity_field,
        }

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

    def deprel(self):
        """
        Handle dependency query
        """
        lg: str = self.lang or ""
        dep_table = _get_table(self.layer, self.config, self.batch, lg)
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
            lablay: dict = self.label_layer or {}
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
    Handle a constraint based on time in VIAN
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
        func = "lower" if is_start else "upper"
        # sign = "-" if is_start else "+"
        sign = "-" if re.match(rf"-\s*[0-9]", self.obj) else "+"
        compare = self.obj.split(".", 1)[0]
        lte: str = ">=" if self.op not in (">", ">=", "<", "<=") else self.op
        # lte = ">=" if is_start else "<="
        lab = self._quantor_label or self.label
        formed = f"{func}({lab}.frame_range) {lte} {func}({compare}.frame_range) {sign} {self.diff} * 25"
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
        part_of = unit.get("partOf", label)
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
            quantor=None,  # quantor is always set directly in _get_constraint by exisentialQuantification
            n=n,
            order=order,
            prev_label=prev_label,
            label_layer=label_layer,
            entities=entities,
            is_set=is_set,
            set_objects=set_objects,
            allow_any=allow_any,
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

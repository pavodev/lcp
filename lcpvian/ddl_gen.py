"""
ddl_gen.py: create SQL code for corpus creation based on uploaded metadata JSON
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re

from collections import abc, defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from textwrap import dedent
from typing import Any, cast

from .typed import JSONObject


@dataclass
class DataNeededLater:
    """
    Everything that generate_ddl needs to return to upload.create function,
    which has been called by the /create endpoint.
    """

    create: str = ""
    constraints: list[str] = field(default_factory=list)
    prep_seg_create: str = ""
    prep_seg_insert: str = ""
    batchnames: list[str] = field(default_factory=list)
    mapping: dict[str, JSONObject] = field(default_factory=dict)
    perms: str = ""
    refs: list[str] = field(default_factory=list)

    def asdict(
        self,
    ) -> dict[str, str | list[str] | dict[str, int]]:
        return asdict(self)


class Globs:
    def __init__(self) -> None:
        self.base_map: dict[str, str] = {}
        self.layers: dict[str, dict[str, Any | str | list[str]]] = {}
        self.schema: list[str] = []
        self.tables: list[Table] = []
        self.types: list[Type] = []
        self.num_partitions: int = 0
        self.prep_seg_create: str = ""
        self.prep_seg_insert: str = ""
        self.batchnames: list[str] = []
        self.mapping: dict[str, JSONObject] = {}
        self.perms: str = ""


class DDL:
    """
    base DDL class for DB entities
    """

    def __init__(self) -> None:

        self.perms: Callable[[str, str], str] = lambda x, y: dedent(
            f"""
            GRANT USAGE ON SCHEMA {x} TO {y};
            GRANT SELECT ON ALL TABLES IN SCHEMA {x} TO {y};\n\n"""
        )

        self.create_scm: Callable[[str, str, str], str] = lambda x, y, z: dedent(
            f"""
            BEGIN;
            CREATE SCHEMA {x};
            DELETE FROM main.corpus WHERE name = '{y}' AND current_version = {z};
            SET search_path TO {x};"""
        )

        self.create_prepared_segs: Callable[[str, str], str] = lambda x, y: dedent(
            f"""
            CREATE TABLE prepared_{x} (
                {y}         uuid    PRIMARY KEY REFERENCES {x} ({y}),
                off_set     int,
                content     jsonb
            );"""
        )

        self.compute_prep_segs: Callable[[str, str, str], str] = lambda x, y, z: dedent(
            f"""
            WITH ins AS (
                   SELECT {x}
                        , min({y}) AS off_set
                        , to_jsonb(array_agg(toks ORDER BY {y}))
                     FROM (
                          SELECT {x}
                               , {y}
                               , jsonb_build_array(
                                    %s
                           ORDER BY {y}) x
                    GROUP BY {x})
             INSERT INTO {z}
             SELECT *
               FROM ins;"""
        )

        self.t = "\t"
        self.nl = "\n\t"
        self.end = "\n);"
        self.tabwidth = 8

        self.anchoring = {
            "location": ("2d_coord", "point"),
            "stream": ("char_range", "int4range"),
            "time": ("frame_range", "int4range"),
        }

        self._type_sizes = {
            "bigint": 8,
            "float": 8,
            "int": 4,
            "int2": 2,
            "int4": 4,
            "int8": 8,
            "int4range": 4,
            "int8range": 8,
            "smallint": 2,
            "text": 4,
            "uuid": 16,
        }
        return None

    def create_str(self) -> None:
        raise NotImplementedError

    # These will be implemented in each child class instead
    # def __lt__(self, other: object) -> bool:
    #     o = cast(DDL, other)
    #     assert hasattr(o, "name") and hasattr(self, "name")
    #     return bool(self.name < o.name)

    # def __eq__(self, other: object) -> bool:
    #     o = cast(DDL, other)
    #     assert hasattr(o, "name") and hasattr(self, "name")
    #     return bool(self.name == o.name)

    @staticmethod
    def fmt(string: str, quote: bool = True, comma: bool = False) -> str:
        if quote:
            string = "'" + string + "'"
        if comma:
            return string + ","
        else:
            return string

    def inlined(self, args: list[str]) -> str:
        """
        method returning indented lines with comma at end for printing
        """
        return (
            self.nl
            + self.nl.join(map(lambda x: x + ",", args[:-1]))
            + self.nl
            + args[-1]
        )


class Column(DDL):
    _not_null_constr = "ALTER COLUMN {} SET NOT NULL;"
    _pk_constr = "ADD PRIMARY KEY ({});"
    _fk_constr = "ADD FOREIGN KEY ({}) REFERENCES {}.{}({});"
    _uniq_constr = "ADD UNIQUE ({});"
    _idx_constr = "{} ({});"

    def __init__(
        self, name: str, typ: str, **constrs: bool | None | str | dict[str, str]
    ) -> None:
        super().__init__()
        self.name = name
        self.type = typ
        self.constrs = constrs
        self.tabwidth = 8
        # self.analyse_constr(constr)

    def ret_tabulate(self, maxi: int) -> str:
        """
        method for tabulating DDL rows.

        """
        return (
            self.name
            + self.t * math.ceil((maxi - len(self.name)) / self.tabwidth)
            + self.type
        )
        # + self.t * (math.ceil((self._max_strtype - len(self.type)) / 8) + 1)

    def ret_constrs(self, schema: str) -> str:
        """
        method for generating all DLL constraints for a column (if there are any)
        """
        ret = []

        if not self.constrs:
            return ""

        for k, v in self.constrs.items():
            if k == "primary_key" and v:
                ret.append(self._pk_constr.format(self.name))
            elif k == "foreign_key" and v:
                assert isinstance(v, dict)
                ret.append(
                    self._fk_constr.format(self.name, schema, v["table"], v["column"])
                )
            elif k == "unique" and v:
                ret.append(self._uniq_constr.format(self.name))
            elif k == "not_null" and v:
                ret.append(self._not_null_constr.format(self.name))

        return "\n".join(ret)

    def ret_idx(self) -> str:
        """
        method for generating the DLL index for a column (ATM everything is indexed)
        """
        if self.constrs.get("primary_key", False):
            return ""
        elif self.type == "int4range" or self.type == "int8range":
            return self._idx_constr.format("USING gist", self.name)
        else:
            return self._idx_constr.format("", self.name)


class Table(DDL):
    def __init__(
        self, name: str, cols: list[Column], anchorings: list[str] | None = None
    ) -> None:
        super().__init__()
        self.name = name.strip()
        self.header_txt = f"CREATE TABLE {self.name} ("
        self.cols = cols
        self.tabwidth = 8
        self.type_sizes: dict[str, int] = {}
        if anchorings:
            for anchor in anchorings:
                self.cols.append(Column(*self.anchoring[anchor]))
        self._max_ident = (
            math.ceil((max([len(col.name) for col in cols]) + 1) / self.tabwidth)
            * self.tabwidth
        )
        # self._max_strtype = max([len(col.type) for col in cols])
        # self._order_cols()

    def primary_key(self) -> list[Column]:
        return [x for x in self.cols if x.constrs.get("primary_key")]

    # def _order_cols(self) -> None:
    #    """
    #    method for ordering attributes for optimized storage

    #    this method breaks mypy so it is temporarily disabled
    #    """
    #    self.cols = sorted(
    #        self.cols,
    #        key=lambda x: (self.type_sizes.get(x.type, 4), reversor(x.name)),
    #        reverse=True,
    #    )
    #    return None

    def create_tbl(self) -> str:
        return (
            self.header_txt
            + self.inlined(
                [
                    self.fmt(col.ret_tabulate(self._max_ident), quote=False)
                    for col in self.cols
                ]
            )
            + self.end
        )

    def create_constrs(self, schema: str) -> list[str]:
        ret = [
            f"ALTER TABLE {schema}.{self.name} " + constr
            for col in self.cols
            if (constr := col.ret_constrs(schema))
        ]
        return ret

    def create_idxs(self, schema: str) -> list[str]:
        ret = [
            f"CREATE INDEX ON {schema}.{self.name} " + idx
            for col in self.cols
            if (idx := col.ret_idx())
        ]
        return ret

    def create_DDL(self, schema: str) -> str:
        return (
            self.create_tbl()
            + "\n\n"
            + "\n".join(self.create_constrs(schema))
            + "\n\n"
            + "\n".join(self.create_idxs(schema))
        )

    def __lt__(self, other: object) -> bool:
        o = cast(Table, other)
        assert hasattr(o, "name") and hasattr(self, "name")
        return bool(self.name < o.name)

    def __eq__(self, other: object) -> bool:
        o = cast(Table, other)
        assert hasattr(o, "name") and hasattr(self, "name")
        return bool(self.name == o.name)


class PartitionedTable(Table):
    max_id = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

    @staticmethod
    def half_hex(num: int | str) -> str:
        if isinstance(num, str):
            num = int(num, 16)
        res = hex(int(num / 2))

        return res

    @staticmethod
    def hex2uuid(num: int | str) -> str:
        if isinstance(num, int):
            num = hex(num)
        form = re.match(
            "(.{8})(.{4})(.{4})(.{4})(.{12})", num.replace("0x", "").rjust(32, "0")
        )
        if not form:
            raise ValueError(f"Cannot match {num}")

        return f"{form[1]}-{form[2]}-{form[3]}-{form[4]}-{form[5]}"

    def __init__(
        self,
        name: str,
        cols: list[Column],
        anchorings: list[str] | None = None,
        column_part: str = "segment_id",
        num_part: int = 10,
    ) -> None:
        super().__init__(name, cols, anchorings)
        self.base_name = self.name
        self.name = f"{self.base_name}0"
        self.num_partitions = num_part
        self.col_partitions = column_part
        self.header_txt = f"CREATE TABLE {self.name} ("

    def _create_maintbl(self) -> str:
        return (
            self.header_txt
            + self.inlined(
                [
                    self.fmt(col.ret_tabulate(self._max_ident), quote=False)
                    for col in self.cols
                ]
            )
            + f"\n) PARTITION BY RANGE ({self.col_partitions});"
        )

    def _create_subtbls(self) -> list[str]:
        tbls: list[str] = []
        cur_max: str | int = self.max_id

        for i in range(1, self.num_partitions + 1):
            end = "rest" if i == self.num_partitions else str(i)
            batchname = f"{self.base_name}{end}"
            tbl_n = f"CREATE TABLE {batchname} PARTITION OF {self.name}"
            cur_min = self.half_hex(cur_max)

            mmax = self.hex2uuid(cur_max)
            mmin = self.hex2uuid(cur_min if end != "rest" else 0)

            defn = f"{self.nl}FOR VALUES FROM ('{mmin}'::uuid) TO ('{mmax}'::uuid); "
            tbls.append(tbl_n + defn)

            cur_max = cur_min

        return tbls

    def create_constrs(self, schema: str) -> list[str]:
        ret = []

        pks = []
        for col in self.cols:
            if col.constrs.get("primary_key"):
                pks.append(col.name)
                col.constrs.pop("primary_key")

        # mypy cannot handle the lambda that used to be here :(
        starts = [i for i in pks if i == self.col_partitions]
        ends = [i for i in pks if i != self.col_partitions]
        pks = starts + ends

        ret.append(
            f"ALTER TABLE {schema}.{self.name} ADD PRIMARY KEY ({', '.join(pks)});"
        )

        ret += [
            f"ALTER TABLE {schema}.{self.name} " + constr
            for col in self.cols
            if (constr := col.ret_constrs(schema))
        ]
        return ret

    def create_tbl(self) -> str:
        main_t = [self._create_maintbl()]
        sub_ts = self._create_subtbls()

        return "\n\n".join(main_t + sub_ts)


class Type(DDL):
    def __init__(self, name: str, values: list[str]) -> None:
        super().__init__()
        self.name = name.strip()
        self.header_txt = f"CREATE TYPE {self.name} AS ENUM ("
        self.values = sorted(set(values))

    def create_DDL(self) -> str:
        return (
            self.header_txt
            + self.inlined([self.fmt(x) for x in self.values])
            + self.end
        )

    def __lt__(self, other: object) -> bool:
        o = cast(Type, other)
        assert hasattr(o, "name") and hasattr(self, "name")
        return bool(self.name < o.name)

    def __eq__(self, other: object) -> bool:
        o = cast(Type, other)
        assert hasattr(o, "name") and hasattr(self, "name")
        return bool(self.name == o.name)


class CTProcessor:
    def __init__(self, corpus_template: dict[str, Any], glos: Globs) -> None:
        self.corpus_temp = corpus_template
        self.schema_name = corpus_template["schema_name"]
        self.layers = self._order_ct_layers(corpus_template["layer"])
        self.globals = glos
        self.ddl = DDL()

    @staticmethod
    def _order_ct_layers(
        layers: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        # check if all layers referred to do exist
        referred = set([ref for v in layers.values() if (ref := v.get("contains"))])
        exists = set(layers)

        if not exists > referred:
            not_ex = referred - exists
            str_not_ex = ", ".join(sorted(["'" + elem + "'" for elem in not_ex]))

            raise Exception(f"The following referred layers do not exist: {str_not_ex}")

        ordered = {}
        to_append, last_append = [], []

        for k, v in layers.items():
            if v.get("layerType") == "relation":
                last_append.append((k, v))
            elif not v.get("contains"):
                ordered[k] = v
            else:
                to_append.append((k, v))

        for k, v in to_append:
            if v["contains"] in ordered:
                ordered[k] = v

        for k, v in last_append:
            ordered[k] = v

        return ordered

    @staticmethod
    def _process_attributes(
        attr_structure: abc.ItemsView[str, Any],
        tables: list[Table],
        table_cols: list[Column],
        types: list[Type],
    ) -> tuple[list[Table], list[Column]]:
        for attr, vals in attr_structure:
            nullable = vals.get("nullable", False) or False
            # TODO: make this working also for e.g. "isGlobal" & "text"
            if (typ := vals.get("type")) == "text":
                norm_col = f"{attr}_id"
                norm_table = Table(
                    attr,
                    [
                        Column(norm_col, "int", primary_key=True),
                        Column(attr, "text", unique=True),
                    ],
                )

                table_cols.append(
                    Column(
                        norm_col,
                        "int",
                        foreign_key={"table": attr, "column": norm_col},
                        nullable=nullable,
                    )
                )

                tables.append(norm_table)

            elif typ == "categorical":
                if vals.get("isGlobal"):
                    table_cols.append(Column(attr, f"main.{attr}", nullable=nullable))
                else:
                    enum_type = Type(attr, vals["values"])
                    types.append(enum_type)
                    table_cols.append(Column(attr, attr, nullable=nullable))

            elif not typ and attr == "meta":
                table_cols.append(Column(attr, "jsonb", nullable=nullable))

            else:
                raise Exception(f"unknown type for attribute: '{attr}'")

        return tables, table_cols

    def _process_unitspan(self, entity: dict[str, dict[str, Any]]) -> None:
        l_name, l_params = list(entity.items())[0]
        tables: list[Table] = []
        table_cols: list[Column] = []
        types: list[Type] = []

        table_name = l_name.lower()

        # create primary key column (if table that will be used to partition -> UUID)
        if l_name == self.globals.base_map["segment"]:
            table_cols.append(Column(f"{table_name}_id", "uuid", primary_key=True))
        else:
            table_cols.append(Column(f"{table_name}_id", "int", primary_key=True))

        tables, table_cols = self._process_attributes(
            l_params.get("attributes", {}).items(), tables, table_cols, types
        )

        anchs = [k for k, v in l_params.get("anchoring", {}).items() if v]
        if l_params.get("layerType") == "span" and (child := l_params.get("contains")):
            anchs += self.globals.layers[child]["anchoring"]

        if l_name == self.globals.base_map["token"]:
            part_ent = self.globals.base_map["segment"].lower()
            part_ent_col = f"{part_ent}_id"

            part_col = Column(
                part_ent_col,
                "uuid",
                primary_key=True,
                foreign_key={"table": part_ent, "column": part_ent_col},
            )
            table_cols.append(part_col)
            ptable = PartitionedTable(
                table_name, table_cols, anchorings=anchs, column_part=part_ent_col
            )
            tables.append(ptable)
        else:
            ptable = None
            table = Table(table_name, table_cols, anchorings=anchs)
            tables.append(table)

        if ptable and not self.globals.num_partitions:
            self.globals.num_partitions = ptable.num_partitions

        self.globals.layers[l_name] = {}
        self.globals.layers[l_name]["anchoring"] = anchs
        self.globals.layers[l_name]["table_name"] = (
            table.name if not ptable else ptable.name
        )

        self.globals.tables += tables
        self.globals.types += types

    def _process_relation(self, entity: dict[str, dict[str, Any]]) -> None:
        # TODO: create FK constraints
        l_name, l_params = list(entity.items())[0]
        table_name = l_name.lower()
        tables: list[Table] = []
        table_cols: list[Column] = []
        types: list[Type] = []

        source_col = self._get_relation_col(l_params["attributes"].pop("source"))
        target_col = self._get_relation_col(l_params["attributes"].pop("target"))

        if not source_col and target_col:
            raise Exception

        table_cols.append(source_col)
        table_cols.append(target_col)

        tables, table_cols = self._process_attributes(
            l_params.get("attributes", {}).items(), tables, table_cols, types
        )

        table = Table(table_name, table_cols)

        tables.append(table)

        self.globals.layers[l_name] = {}
        self.globals.layers[l_name]["table_name"] = table.name

        self.globals.tables += tables
        self.globals.types += types

    def _get_relation_col(self, rel_structure: dict[str, str]) -> Column:
        name = rel_structure["name"]
        table_name = self.globals.layers[rel_structure["entity"]]["table_name"]
        table = next(x for x in self.globals.tables if x.name == table_name)
        fk_col = f"{rel_structure['entity'].lower()}_id"
        typ = next(x for x in table.cols if x.name == fk_col).type
        nullable = rel_structure.get("nullable")

        return Column(name, typ, nullable=nullable)

    def process_layers(self) -> None:
        for layer, params in self.layers.items():
            if (layer_type := params.get("layerType")) in ["unit", "span"]:
                self._process_unitspan({layer: params})
            elif layer_type == "relation":
                self._process_relation({layer: params})
            else:
                raise Exception(
                    f"unknown layer type '{layer_type}' for layer '{layer}'."
                )

    def process_schema(self) -> str:
        corpus_name = re.sub(r"\W", "_", self.corpus_temp["meta"]["name"].lower())
        corpus_name = re.sub(r"_+", "_", corpus_name)
        corpus_version = str(int(self.corpus_temp["meta"]["version"]))
        corpus_version = re.sub(r"\W", "_", corpus_version.lower())
        corpus_version = re.sub(r"_+", "_", corpus_version)
        schema_name: str = self.schema_name

        scm: str = self.ddl.create_scm(schema_name, corpus_name, corpus_version)
        self.globals.schema.append(scm)
        query_user = os.getenv("SQL_QUERY_USERNAME", "lcp_dev_webuser")
        perms: str = self.ddl.perms(schema_name, query_user)
        self.globals.perms = perms
        return schema_name

    def create_compute_prep_segs(self) -> None:
        tok_tab = next(
            x
            for x in self.globals.tables
            if x.name == self.globals.base_map["token"].lower() + "0"
        )
        seg_tab = next(
            x
            for x in self.globals.tables
            if x.name == self.globals.base_map["segment"].lower()
        )

        tok_pk = next(
            x
            for x in tok_tab.primary_key()
            if self.globals.base_map["token"].lower() in x.name
        )
        rel_cols = sorted(
            [
                x
                for x in tok_tab.cols
                if not (x.constrs.get("primary_key") or "range" in x.name)
            ],
            key=lambda x: x.name,
        )
        rel_cols_names = [x.name.rstrip("_id") for x in rel_cols]

        mapd: dict[str, Any] = {}
        mapd["layer"] = {}
        tokname = self.globals.base_map["token"]
        mapd["layer"][self.globals.base_map["segment"]] = {}
        batchname = f"{tokname}<batch>"
        mapd["layer"][tokname] = {
            "batches": self.globals.num_partitions,
            "relation": batchname,
        }
        mapd["layer"][self.globals.base_map["segment"]]["prepared"] = {}
        mapd["layer"][self.globals.base_map["segment"]]["prepared"]["relation"] = (
            "prepared_" + seg_tab.name
        )
        mapd["layer"][self.globals.base_map["segment"]]["prepared"][
            "columnHeaders"
        ] = rel_cols_names
        mapd["layer"][self.globals.base_map["segment"]]["relation"] = seg_tab.name
        self.globals.mapping = mapd

        # corpus_name = re.sub(r"\W", "_", self.corpus_temp["meta"]["name"].lower())
        # corpus_version = str(int(self.corpus_temp["meta"]["version"]))

        searchpath = f"\nSET search_path TO {self.schema_name};"

        ddl: str = self.ddl.create_prepared_segs(
            seg_tab.name, seg_tab.primary_key()[0].name
        )

        self.globals.prep_seg_create = f"\n\n{searchpath}\n{ddl}"

        json_sel = (
            "\n                      , ".join(rel_cols_names)
            + f"\n                     ) AS toks\n                FROM {{batch}}\n                "
            + "\n                ".join(
                [
                    f"JOIN {fk['table']} USING ({fk['column']})"
                    for x in rel_cols
                    if (fk := x.constrs.get("foreign_key")) and (isinstance(fk, dict))
                ]
            )
        )

        query: str = (
            self.ddl.compute_prep_segs(
                seg_tab.primary_key()[0].name,
                tok_pk.name,
                f"prepared_{seg_tab.name}",
            )
            % json_sel
        )

        self.globals.prep_seg_insert = f"\n\n{searchpath}\n{query}"

        # todo: check this again
        for i in range(1, self.globals.num_partitions):
            if i == self.globals.num_partitions - 1 and i > 1:
                batch = batchname.replace("<batch>", "rest")
            else:
                batch = batchname.replace("<batch>", str(i))
            self.globals.batchnames.append(batch)


def generate_ddl(
    corpus_temp: dict[str, Any]
) -> dict[str, str | list[str] | dict[str, int]]:
    globs = Globs()
    globs.base_map = corpus_temp["firstClass"]

    processor = CTProcessor(corpus_temp, globs)

    schema_name = processor.process_schema()
    processor.process_layers()
    processor.create_compute_prep_segs()

    create_schema = "\n\n".join([x for x in globs.schema])
    create_types = "\n\n".join([x.create_DDL() for x in sorted(globs.types)])
    create_tbls = "\n\n".join([x.create_tbl() for x in sorted(globs.tables)])

    create = "\n".join([create_schema, create_types, create_tbls])

    # todo: i don't think this defaultdict trick is needed, all the tables
    # must have unique names right?
    constraints: defaultdict[str, list[str]] = defaultdict(list)
    refs: list[str] = []
    for table in sorted(globs.tables):
        constraints[table.name] += table.create_idxs(schema_name)
        cons = table.create_constrs(schema_name)
        for c in cons:
            if " REFERENCES " in c:
                refs.append(c)
            else:
                constraints[table.name].append(c)
    formed_constraints = ["\n".join(i) for i in constraints.values()]

    return DataNeededLater(
        create,
        formed_constraints,
        globs.prep_seg_create,
        globs.prep_seg_insert,
        globs.batchnames,
        globs.mapping,
        globs.perms,
        refs,
    ).asdict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Postgres DDL from CT.")
    parser.add_argument(
        "cmd", type=str, help="The command being run (ignore this)"  # nargs="+",
    )
    parser.add_argument(
        "ct_file", type=str, help="the corpus corpus_temp file (json)"  # nargs="+",
    )
    parser.add_argument(
        "-t", "--tabwidth", type=int, default=8, help="size of tabulator"
    )

    args = parser.parse_args()

    with open(args.ct_file) as f:
        corpus_temp = json.load(f)

    data = generate_ddl(corpus_temp)

    print(json.dumps(data, indent=4))

    return
    # need to comment out the below for mypy
    """

    globs = Globs()

    globs.base_map = corpus_temp["firstClass"]

    processor = CTProcessor(corpus_temp, globs)
    processor.ddl.tabwidth = args.tabwidth

    processor.process_schema()
    processor.process_layers()

    processor.create_compute_prep_segs()

    print("\n\n".join([x for x in globs.schema]))
    print()
    print(
        "\n\n".join([x.create_DDL() for x in sorted(globs.types, key=lambda x: x.name)])
    )
    print()
    print(
        "\n\n".join(
            [x.create_tbl() for x in sorted(globs.tables, key=lambda x: x.name)]
        )
    )
    print()
    print(
        "\n\n".join(
            [x.create_idxs() for x in sorted(globs.tables, key=lambda x: x.name)]
        )
    )
    print()
    print(
        "\n\n".join(
            [x.create_constrs() for x in sorted(globs.tables, key=lambda x: x.name)]
        )
    )
    """


if __name__ == "__main__":
    main()

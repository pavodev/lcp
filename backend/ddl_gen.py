import argparse
import json
import math
import re

from collections import OrderedDict
from textwrap import dedent

from typing import Dict, List


class Globs:
    def __init__(self) -> None:
        self.base_map: Dict = {}
        self.layers: Dict = {}
        self.schema: List = []
        self.tables: List = []
        self.types: List = []
        self.num_partitions: int = 0
        self.start_constrs: str = ""
        self.prep_seg_create: str = ""
        self.prep_seg_inserts: List[str] = []


class reversor:
    """
    class from https://stackoverflow.com/a/56842689
    used for reversing sort order
    """

    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return other.obj == self.obj

    def __lt__(self, other):
        return other.obj < self.obj


class DDL:
    """
    base DDL class for DB entities
    """

    perms = lambda x: dedent(
        f"""
        GRANT USAGE ON SCHEMA {x} TO lcp_dev_webuser;
        GRANT SELECT ON ALL TABLES IN SCHEMA {x} TO lcp_dev_webuser;\n\n"""
    )

    create_scm = lambda x, y, z: dedent(
        f"""
        BEGIN;

        DROP SCHEMA IF EXISTS {x} CASCADE;
        CREATE SCHEMA {x};
        DELETE FROM main.corpus WHERE name = '{y}' AND current_version = {z};
        SET search_path TO {x};"""
    )

    create_cons_preamble = lambda x: dedent(
        f"""

        SET search_path TO {x};\n"""
    )

    create_prepared_segs = lambda x, y: dedent(
        f"""
        CREATE TABLE prepared_{x} (
            {y}         uuid    PRIMARY KEY REFERENCES {x} ({y}),
            off_set     int,
            content     jsonb
        );"""
    )

    compute_prep_segs = lambda x, y, z: dedent(
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

    #    jsonb_sel =
    #                                form
    #                              , lemma
    #                              , xpos1
    #                              , xpos2
    #                             ) AS toks
    #                        FROM token0
    #                        JOIN form      USING (form_id)
    #                        JOIN lemma     USING (lemma_id)

    t = "\t"
    nl = "\n\t"
    end = "\n);"
    tabwidth = None

    anchoring = {
        "location": ("2d_coord", "point"),
        "stream": ("char_range", "int4range"),
        "time": ("frame_range", "int4range"),
    }

    type_sizes = {
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

    def create_str(self):
        raise NotImplementedError

    @staticmethod
    def fmt(string, quote=True, comma=False):
        if quote:
            string = "'" + string + "'"
        if comma:
            return string + ","
        else:
            return string

    @classmethod
    def inlined(cls, args):
        """
        method returning indented lines with comma at end for printing
        """
        return (
            cls.nl + cls.nl.join(map(lambda x: x + ",", args[:-1])) + cls.nl + args[-1]
        )


class Column(DDL):
    _not_null_constr = "ALTER COLUMN {} SET NOT NULL;"
    _pk_constr = "ADD PRIMARY KEY ({});"
    _fk_constr = "ADD FOREIGN KEY ({}) REFERENCES {}({});"
    _uniq_constr = "ADD UNIQUE ({});"
    _idx_constr = "{} ({});"

    def __init__(self, name, type, **constrs):
        self.name = name
        self.type = type
        self.constrs = constrs
        self.tabwidth = 8
        # self.analyse_constr(constr)

    def ret_tabulate(self, max):
        """
        method for tabulating DDL rows.

        """
        return (
            self.name
            + self.t * math.ceil((max - len(self.name)) / self.tabwidth)
            + self.type
        )
        # + self.t * (math.ceil((self._max_strtype - len(self.type)) / 8) + 1)

    def ret_constrs(self):
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
                ret.append(self._fk_constr.format(self.name, v["table"], v["column"]))
            elif k == "unique" and v:
                ret.append(self._uniq_constr.format(self.name))
            elif k == "not_null" and v:
                ret.append(self._not_null_constr.format(self.name))

        return "\n".join(ret)

    def ret_idx(self):
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
    def __init__(self, name, cols, anchorings=None):
        self.name = name.strip()
        self.header_txt = f"CREATE TABLE {self.name} ("
        self.cols = cols
        self.tabwidth = 8
        if anchorings:
            for anchor in anchorings:
                self.cols.append(Column(*self.anchoring[anchor]))
        self._max_ident = (
            math.ceil((max([len(col.name) for col in cols]) + 1) / self.tabwidth)
            * self.tabwidth
        )
        # self._max_strtype = max([len(col.type) for col in cols])
        self._process_cols()

    def primary_key(self):
        return [x for x in self.cols if x.constrs.get("primary_key")]

    def _order_cols(self):
        """
        method for ordering attributes for optimized storage

        """
        self.cols = sorted(
            self.cols,
            key=lambda x: (self.type_sizes.get(x.type, 4), reversor(x.name)),
            reverse=True,
        )

    def _process_cols(self):
        self._order_cols()

    def create_tbl(self):
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

    def create_constrs(self):
        ret = [
            f"ALTER TABLE {self.name} " + constr
            for col in self.cols
            if (constr := col.ret_constrs())
        ]

        return "\n".join(ret)

    def create_idxs(self):
        ret = [
            f"CREATE INDEX ON {self.name} " + idx
            for col in self.cols
            if (idx := col.ret_idx())
        ]

        return "\n".join(ret)

    def create_DDL(self):
        return (
            self.create_tbl()
            + "\n\n"
            + self.create_constrs()
            + "\n\n"
            + self.create_idxs()
        )


class PartitionedTable(Table):
    max_id = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

    @staticmethod
    def half_hex(num):
        if isinstance(num, str):
            num = int(num, 16)
        res = hex(int(num / 2))

        return res

    @staticmethod
    def hex2uuid(num):
        if isinstance(num, int):
            num = hex(num)
        form = re.match(
            "(.{8})(.{4})(.{4})(.{4})(.{12})", num.replace("0x", "").rjust(32, "0")
        )

        return f"{form[1]}-{form[2]}-{form[3]}-{form[4]}-{form[5]}"

    def __init__(
        self, name, cols, anchorings=None, column_part="segment_id", num_part=10
    ):
        super().__init__(name, cols, anchorings)
        self.base_name = self.name
        self.name = f"{self.base_name}0"
        self.num_partitions = num_part + 1  # rest is same size as smallest partition
        self.col_partitions = column_part
        self.header_txt = f"CREATE TABLE {self.name} ("

    def _create_maintbl(self):
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

    def _create_subtbls(self):
        tbls = []
        cur_max = self.max_id

        for i in range(1, self.num_partitions):
            batchname = f"{self.base_name}{i}"
            tbl_n = f"CREATE TABLE {batchname} PARTITION OF {self.name}"
            cur_min = self.half_hex(cur_max)

            mmax = self.hex2uuid(cur_max)
            mmin = self.hex2uuid(cur_min)

            defn = f"{self.nl}FOR VALUES FROM ('{mmin}'::uuid) TO ('{mmax}'::uuid); "
            tbls.append(tbl_n + defn)

            cur_max = cur_min

        mmax = self.hex2uuid(cur_min)
        mmin = self.hex2uuid(0)

        batchname = f"{self.base_name}rest"
        tbl_n = f"CREATE TABLE {batchname} PARTITION OF {self.name}"
        defn = f"{self.nl}FOR VALUES FROM ('{mmin}'::uuid) TO ('{mmax}'::uuid); "
        tbls.append(tbl_n + defn)

        return tbls

    def create_constrs(self):
        ret = []

        pks = []
        for col in self.cols:
            if col.constrs.get("primary_key"):
                pks.append(col.name)
                col.constrs.pop("primary_key")

        pks = sorted(pks, key=lambda x: x != self.col_partitions)
        ret.append(f"ALTER TABLE {self.name} ADD PRIMARY KEY ({', '.join(pks)});")

        ret += [
            f"ALTER TABLE {self.name} " + constr
            for col in self.cols
            if (constr := col.ret_constrs())
        ]

        return "\n".join(ret)

    def create_tbl(self):
        main_t = [self._create_maintbl()]
        sub_ts = self._create_subtbls()

        return "\n\n".join(main_t + sub_ts)


class Type(DDL):
    def __init__(self, name, values):
        self.name = name.strip()
        self.header_txt = f"CREATE TYPE {self.name} AS ENUM ("
        self.values = sorted(set(values))

    def create_DDL(self):
        return (
            self.header_txt
            + self.inlined([self.fmt(x) for x in self.values])
            + self.end
        )


class CTProcessor:
    def __init__(self, corpus_template, glos):
        self.corpus_temp = corpus_template
        self.layers = self._order_ct_layers(corpus_template["layer"])
        self.globals = glos

    @staticmethod
    def _order_ct_layers(layers):
        # check if all layers referred to do exist
        referred = set([ref for v in layers.values() if (ref := v.get("contains"))])
        exists = set(layers.keys())

        if not exists > referred:
            not_ex = referred - exists
            str_not_ex = ", ".join(sorted(["'" + elem + "'" for elem in not_ex]))

            raise Exception(f"The following referred layers do not exist: {str_not_ex}")

        ordered = OrderedDict()
        to_append, last_append = [], []

        for k, v in layers.items():
            if v.get("layerType") == "relation":
                last_append.append((k, v))
            elif not v.get("contains"):
                ordered[k] = v
            else:
                to_append.append((k, v))

        while len(to_append):
            for k, v in to_append:
                if v["contains"] in ordered:
                    ordered[k] = v
                    to_append.pop(to_append.index((k, v)))
                else:
                    continue

        for k, v in last_append:
            ordered[k] = v

        return ordered

    @staticmethod
    def _process_attributes(attr_structure, tables, table_cols, types):
        for attr, vals in attr_structure:
            nullable = res if (res := vals.get("nullable")) else False

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

    def _process_unitspan(self, entity):
        l_name, l_params = list(entity.items())[0]
        tables, table_cols, types = [], [], []

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
            table = PartitionedTable(
                table_name, table_cols, anchorings=anchs, column_part=part_ent_col
            )
        else:
            table = Table(table_name, table_cols, anchorings=anchs)

        tables.append(table)

        if isinstance(table, PartitionedTable) and not self.globals.num_partitions:
            self.globals.num_partitions = table.num_partitions

        self.globals.layers[l_name] = {}
        self.globals.layers[l_name]["anchoring"] = anchs
        self.globals.layers[l_name]["table_name"] = table.name

        self.globals.tables += tables
        self.globals.types += types

    def _process_relation(self, entity):
        # TODO: create FK constraints
        l_name, l_params = list(entity.items())[0]
        table_name = l_name.lower()
        tables, table_cols, types = [], [], []

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

    def _get_relation_col(self, rel_structure):
        name = rel_structure.get("name")
        table_name = self.globals.layers[rel_structure.get("entity")]["table_name"]
        table = [x for x in self.globals.tables if x.name == table_name][0]
        fk_col = f"{rel_structure.get('entity').lower()}_id"
        typ = [x for x in table.cols if x.name == fk_col][0].type
        nullable = rel_structure.get("nullable")

        return Column(name, typ, nullable=nullable)

    def process_layers(self):
        for layer, params in self.layers.items():
            if (layer_type := params.get("layerType")) in ["unit", "span"]:
                self._process_unitspan({layer: params})
            elif layer_type == "relation":
                self._process_relation({layer: params})
            else:
                raise Exception(
                    f"unknown layer type '{layer_type}' for layer '{layer}'."
                )

    def process_schema(self):
        corpus_name = re.sub("\W", "_", self.corpus_temp["meta"]["name"].lower())
        corpus_version = str(int(self.corpus_temp["meta"]["version"]))
        schema_name = corpus_name + corpus_version

        self.globals.schema.append(
            DDL.create_scm(schema_name, corpus_name, corpus_version)
        )
        self.globals.start_constrs = DDL.create_cons_preamble(schema_name)
        self.globals.perms = DDL.perms(schema_name)

    def create_compute_prep_segs(self):
        tok_tab = [
            x
            for x in self.globals.tables
            if x.name == self.globals.base_map["token"].lower() + "0"
        ][0]
        seg_tab = [
            x
            for x in self.globals.tables
            if x.name == self.globals.base_map["segment"].lower()
        ][0]

        tok_pk = [
            x
            for x in tok_tab.primary_key()
            if self.globals.base_map["token"].lower() in x.name
        ]
        tok_pk = tok_pk[0]
        rel_cols = sorted(
            [
                x
                for x in tok_tab.cols
                if not (x.constrs.get("primary_key") or "range" in x.name)
            ],
            key=lambda x: x.name,
        )
        rel_cols_names = [x.name.rstrip("_id") for x in rel_cols]

        mapd = {}
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
        self.globals.mapping = json.dumps(mapd)

        corpus_name = re.sub("\W", "_", self.corpus_temp["meta"]["name"].lower())
        corpus_version = str(int(self.corpus_temp["meta"]["version"]))
        schema_name = corpus_name + corpus_version

        searchpath = f"\nSET search_path TO {schema_name};"

        ddl = DDL.create_prepared_segs(seg_tab.name, seg_tab.primary_key()[0].name)

        self.globals.prep_seg_create = "\n\n" + searchpath + "\n" + ddl

        # todo: check this again
        for i in range(1, self.globals.num_partitions):
            if i == self.globals.num_partitions - 1 and i > 1:
                batch = batchname.replace("<batch>", "rest")
            else:
                batch = batchname.replace("<batch>", str(i))
            json_sel = (
                "\n                      , ".join(rel_cols_names)
                + f"\n                     ) AS toks\n                FROM {batch}\n                "
                + "\n                ".join(
                    [
                        f"JOIN {fk['table']} USING ({fk['column']})"
                        for x in rel_cols
                        if (fk := x.constrs.get("foreign_key"))
                    ]
                )
            )

            query = (
                DDL.compute_prep_segs(
                    seg_tab.primary_key()[0].name,
                    tok_pk.name,
                    f"prepared_{seg_tab.name}",
                )
                % json_sel
            )

            self.globals.prep_seg_inserts.append("\n\n" + searchpath + "\n" + query)


def generate_ddl(corpus_temp):
    globs = Globs()
    globs.base_map = corpus_temp["firstClass"]

    processor = CTProcessor(corpus_temp, globs)

    processor.process_schema()
    processor.process_layers()
    processor.create_compute_prep_segs()

    create_schema = "\n\n".join([x for x in globs.schema])
    create_types = "\n\n".join(
        [x.create_DDL() for x in sorted(globs.types, key=lambda x: x.name)]
    )
    create_tbls = "\n\n".join(
        [x.create_tbl() for x in sorted(globs.tables, key=lambda x: x.name)]
    )

    create_idxs = "\n\n".join(
        [x.create_idxs() for x in sorted(globs.tables, key=lambda x: x.name)]
    )
    create_constr = "\n\n".join(
        [x.create_constrs() for x in sorted(globs.tables, key=lambda x: x.name)]
    )

    return (
        "\n".join([create_schema, create_types, create_tbls]),
        "\n".join(
            [
                globs.start_constrs + create_idxs,
                create_constr,
                globs.perms,
            ]
        ),
        globs.prep_seg_create,
        globs.prep_seg_inserts,
        globs.mapping,
    )


def main():
    parser = argparse.ArgumentParser(description="Generate Postgres DDL from CT.")
    parser.add_argument(
        "ct_file", type=str, help="the corpus corpus_temp file (json)"  # nargs="+",
    )
    parser.add_argument(
        "-t", "--tabwidth", type=int, default=8, help="size of tabulator"
    )

    args = parser.parse_args()

    DDL.tabwidth = args.tabwidth

    with open(args.ct_file) as f:
        corpus_temp = json.load(f)

    a, b = generate_ddl(corpus_temp)

    print(a + b)
    return

    globs = Globs()

    globs.base_map = corpus_temp["firstClass"]

    processor = CTProcessor(corpus_temp, globs)

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


if __name__ == "__main__":
    main()

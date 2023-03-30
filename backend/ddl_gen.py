import argparse
import math
import json
import re

from collections import OrderedDict
from textwrap    import dedent



class Globs:
    layers = {}
    schema = []
    tables = []
    types  = []


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
    create_scm = lambda x: dedent(f"""
        BEGIN;

        DROP SCHEMA IF EXISTS {x} CASCADE;
        CREATE SCHEMA {x};
        SET search_path TO {x};""")

    t          = "\t"
    nl         = "\n\t"
    end        = "\n);"
    tabwidth   = None

    anchoring = {
        "location": ("2d_coord", "point"),
        "stream":   ("char_range", "int4range"),
        "time":     ("frame_range", "int4range")
    }

    type_sizes = {
        "bigint":    8,
        "float":     8,
        "int":       4,
        "int2":      2,
        "int4":      4,
        "int8":      8,
        "int4range": 4,
        "int8range": 8,
        "smallint":  2,
        "text":      4,
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
        return cls.nl                                         \
             + cls.nl.join(map(lambda x: x + ",", args[:-1])) \
             + cls.nl + args[-1]


class Column(DDL):
    _not_null_constr = "ALTER COLUMN {} SET NOT NULL;"
    _pk_constr       = "ADD PRIMARY KEY ({});"
    _fk_constr       = "ADD FOREIGN KEY ({}) REFERENCES {}({});"
    _uniq_constr     = "ADD UNIQUE ({});"
    _idx_constr      = "CREATE INDEX {} ON ({});"

    def __init__(self, name, type, **constrs):
        self.name          = name
        self.type          = type
        self.constrs       = constrs
        # self.analyse_constr(constr)

    def ret_tabulate(self, max):
        """
        method for tabulating DDL rows.

        """
        return self.name + self.t * math.ceil((max - len(self.name)) / self.tabwidth) \
             + self.type
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
        elif (self.type == "int4range" or self.type == "int8range"):
            return self._idx_constr.format("USING gist", self.name)
        else:
            return self._idx_constr.format("", self.name)


class Table(DDL):
    def __init__(self, name, cols, anchorings=None):
        self.name       = name.strip()
        self.header_txt = f"CREATE TABLE {self.name} ("
        self.constr_txt = f"ALTER TABLE {self.name} ALTER COLUMN %"
        self.cols       = cols
        if anchorings:
            for anchor in anchorings:
                self.cols.append(Column(*self.anchoring[anchor]))
        self._max_ident = math.ceil((max([len(col.name) for col in cols]) + 1) / self.tabwidth) * self.tabwidth
        # self._max_strtype = max([len(col.type) for col in cols])
        self._process_cols()

    def _order_cols(self):
        """
        method for ordering attributes for optimized storage

        """
        self.cols = sorted(self.cols, key=lambda x: (self.type_sizes.get(x.type, 4), reversor(x.name)), reverse=True)

    def _process_cols(self):
        self._order_cols()

    def create_tbl(self):
        return self.header_txt \
             + self.inlined([self.fmt(col.ret_tabulate(self._max_ident), quote=False) for col in self.cols]) \
             + self.end

    def create_constrs(self):
        ret = [f"ALTER TABLE {self.name} " + constr for col in self.cols if (constr := col.ret_constrs())]

        return "\n".join(ret)

    def create_idxs(self):
        ret = [f"ALTER TABLE {self.name} " + idx for col in self.cols if (idx := col.ret_idx())]

        return "\n".join(ret)

    def create_DDL(self):
        return self.create_tbl() + "\n\n" \
             + self.create_constrs() + "\n\n" \
             + self.create_idxs()




class PartitionedTable(Table):
    max_id = 0xffffffffffffffffffffffffffffffff

    @staticmethod
    def half_hex(num):
        if isinstance(num, str):
            num = int(num, 16)
        res = hex(int(num/2))

        return res

    @staticmethod
    def hex2uuid(num):
        if isinstance(num, int):
            num = hex(num)
        form = re.match('(.{8})(.{4})(.{4})(.{4})(.{12})', num.replace("0x", "").rjust(32, "0"))

        return f"{form[1]}-{form[2]}-{form[3]}-{form[4]}-{form[5]}"

    def __init__(self, name, cols, anchorings=None, column_part="segment_id", num_part=10):
        super(PartitionedTable, self).__init__(name, cols, anchorings)
        self.num_partitions = num_part + 1    # rest is same size as smallest partition
        self.col_partitions = column_part
        self.header_txt     = f"CREATE TABLE {self.name}0 ("

    def _create_maintbl(self):
        return self.header_txt \
             + self.inlined([self.fmt(col.ret_tabulate(self._max_ident), quote=False) for col in self.cols]) \
             + f"\n) PARTITION BY RANGE ({self.col_partitions});"

    def _create_subtbls(self):
        tbls = []
        cur_max = self.max_id

        for i in range(1, self.num_partitions):
            tbl_n   = f"{self.name}{i} PARTITION OF {self.name}0"
            cur_min = self.half_hex(cur_max)

            max = self.hex2uuid(cur_max)
            min = self.hex2uuid(cur_min)

            defn = f"{self.nl}FOR VALUES FROM ('{min}'::uuid) TO ('{max}'::uuid); "
            tbls.append(tbl_n + defn)

            cur_max = cur_min

        max = self.hex2uuid(cur_min)
        min = self.hex2uuid(0)

        tbl_n   = f"{self.name}rest PARTITION OF {self.name}0"
        defn = f"{self.nl}FOR VALUES FROM ('{min}'::uuid) TO ('{max}'::uuid); "
        tbls.append(tbl_n + defn)

        return tbls

    def create_constrs(self):
        ret = []

        for col in self.cols:
            pks = [self.col_partitions]
            if col.constrs.get("primary_key"):
                pks.append(col.name)
                col.constrs.pop("primary_key")

        pks = sorted(pks, key=lambda x: x != self.col_partitions)
        ret.append(f"ALTER TABLE {self.name} ADD PRIMARY KEY ({', '.join(pks)});")

        ret += [f"ALTER TABLE {self.name} " + constr for col in self.cols if (constr := col.ret_constrs())]

        return "\n".join(ret)


    def create_tbl(self):
        main_t = [self._create_maintbl()]
        sub_ts = self._create_subtbls()

        return "\n\n".join(main_t + sub_ts)






class Type(DDL):
    def __init__(self, name, values):
        self.name       = name.strip()
        self.header_txt = f"CREATE TYPE {self.name} AS ENUM ("
        self.values     = sorted(set(values))

    def create_DDL(self):
        return self.header_txt \
             + self.inlined([self.fmt(x) for x in  self.values]) \
             + self.end


class CTProcessor:
    def __init__(self, corpus_template, globals):
        self.corpus_temp = corpus_template
        self.layers      = self._order_ct_layers(corpus_template["layer"])
        self.globals     = globals

    @staticmethod
    def _order_ct_layers(layers):
        # check if all layers referred to do exist
        referred = set([ref for v in layers.values() if (ref := v.get("contains"))])
        exists   = set(layers.keys())

        if not exists > referred:
            not_ex     = referred - exists
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

    def _process_unitspan(self, entity):
        l_name, l_params = list(entity.items())[0]
        tables, types    = [], []

        table_name = l_name.lower()
        table_cols = []

        table_cols.append(Column(f"{table_name}_id", "int", primary_key=True))

        for attr, vals in l_params.get("attributes", {}).items():
            nullable = res if (res := vals.get("nullable")) else False

            if (type := vals.get("type")) == "text":
                norm_col = f"{attr}_id"
                norm_table = Table(attr, [Column(norm_col, "int",  primary_key=True),
                                          Column(attr,     "text", unique=True)])

                table_cols.append(Column(norm_col,
                                   "int",
                                   foreign_key={"table": attr, "column": norm_col},
                                   nullable=nullable))

                tables.append(norm_table)

            elif type == "categorical":
                enum_type = Type(attr, vals["values"])
                types.append(enum_type)
                table_cols.append(Column(attr, attr, nullable=nullable))

            elif vals.get("is_global"):
                table_cols.append(Column(attr, f"main.{attr}", nullable=nullable))

            elif not type and attr == "meta":
                table_cols.append(Column(attr, "jsonb", nullable=nullable))

            else:
                raise Exception(f"unknown type for attribute: '{attr}'")

        anchs = [k for k, v in l_params.get("anchoring", {}).items() if v]
        if l_params.get("layerType") == "span" and (child := l_params.get("contains")):
            anchs += self.globals.layers[child]["anchoring"]

        if l_name == "Token":
            part_col = Column("segment_id", "uuid", foreign_key={"table": "segment", "column": "segment_id"})
            table_cols.append(part_col)
            table = PartitionedTable(table_name, table_cols, anchorings=anchs, column_part="segment_id")
        else:
            table = Table(table_name, table_cols, anchorings=anchs)

        tables.append(table)

        self.globals.layers[l_name] = {}
        self.globals.layers[l_name]["anchoring"] = anchs

        self.globals.tables += tables
        self.globals.types  += types

    def _process_relation(self, entity):
        l_name, l_params = list(entity.items())[0]
        table_name = l_name.lower()

        source_col = self._get_relation_col(l_params.get("source"))
        target_col = self._get_relation_col(l_params.get("target"))

    def _get_relation_col(self, rel_structure):
        table_name = rel_structure.get("name")

    def process_layers(self):
        for layer, params in self.layers.items():
            if (layer_type := params.get("layerType")) in ["unit", "span"]:
                self._process_unitspan({layer: params})
            elif layer_type == "relation":
                self._process_relation({layer: params})
            else:
                raise Exception(f"unknown layer type '{layer_type}' for layer '{layer}'.")

    def process_schema(self):
        corpus_name = re.sub("\W", "_", self.corpus_temp["meta"]["name"].lower())
        corpus_version = str(int(self.corpus_temp["meta"]["version"]))
        schema_name = corpus_name + corpus_version

        self.globals.schema.append(DDL.create_scm(schema_name))





# def parse_CT(template):
#     for layer, defs in sorted(template["layer"].items(), key=lambda x: x :
#         table_name = layer.lower()


# def process_layer(layer_name, params, globs):
#     tables, types = [], []

#     table_name = layer_name.lower()
#     cols = []

#     cols.append(Column(table_name + "_id", "int", primary_key=True))

#     if (layer_type := params.get("layerType")) in ["unit", "span"]:
#         for attr, vals in params.get("attributes", {}).items():
#             nullable = res if (res := vals.get("nullable")) else False
#             if (type := vals.get("type")) == "text":
#                 norm_col = attr + "_id"
#                 norm_table = Table(attr, [Column(norm_col, "int", primary_key=True),
#                                           Column(attr, "text", unique=True)])

#                 cols.append(Column(norm_col, "int", foreign_key={"table": attr, "column": norm_col}, nullable=nullable))
#                 tables.append(norm_table)

#             elif type == "categorical":
#                 enum_type = Type(attr, vals["values"])
#                 types.append(enum_type)
#                 cols.append(Column(attr, attr, nullable=nullable))

#             elif not type and attr == "meta":
#                 cols.append(Column(attr, "jsonb", nullable=nullable))

#             elif vals.get("is_global"):
#                 cols.append(Column(attr, f"main.{attr}", nullable=nullable))
#             else:
#                 raise Exception(f"unknown type for attribute: '{attr}'")

#         anchs = [k for k, v in params.get("anchoring", {}).items() if v]
#         if params.get("layerType") == "span" and (child := params.get("contains")):
#             anchs += globs.layers[child]["anchoring"]
#         table = Table(table_name, cols, anchorings=anchs)
#         globs.layers[layer_name] = {}
#         globs.layers[layer_name]["anchoring"] = anchs
#     elif layer_type == "relation":
#         pass
#     else:
#         raise Exception(f"Unknown layer type '{layer_type}' for layer '{layer_name}'.")

#     tables.append(table)

#     globs.tables += tables
#     globs.types  += types


def main():
    parser = argparse.ArgumentParser(description="Generate Postgres DDL from CT.")
    parser.add_argument("ct_file", type=str, # nargs="+",
                        help="the corpus template file (json)")
    parser.add_argument("-t", "--tabwidth", type=int, default=8,
                        help="size of tabulator")

    args = parser.parse_args()

    DDL.tabwidth = args.tabwidth


    with open(args.ct_file) as f:
        corpus_temp = json.load(f)

    processor = CTProcessor(corpus_temp, Globs)


    processor.process_schema()
    processor.process_layers()

    # import ipdb; ipdb.set_trace()

    print("\n\n".join([x for x in Globs.schema]))
    print()
    print("\n\n".join([x.create_DDL() for x in Globs.types]))
    print()
    print("\n\n".join([x.create_tbl() for x in Globs.tables]))
    print()
    print("\n\n".join([x.create_idxs() for x in Globs.tables]))
    print()
    print("\n\n".join([x.create_constrs() for x in Globs.tables]))



if __name__ == "__main__":
    main()

import argparse
import math
import json


class Globs:
    layers = {}
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
    create_scm = "BEGIN;\n\nDROP SCHEMA IF EXISTS {} CASCADE;\nCREATE SCHEMA {};\nSET search_path TO {}\n\n;"
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
                assert type(v) == dict
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


class Type(DDL):
    def __init__(self, name, values):
        self.name       = name.strip()
        self.header_txt = f"CREATE TYPE {self.name} AS ENUM ("
        self.values     = sorted(set(values))

    def create_DDL(self):
        return self.header_txt \
             + self.inlined([self.fmt(x) for x in  self.values]) \
             + self.end


# def parse_CT(template):
#     for layer, defs in sorted(template["layer"].items(), key=lambda x: x :
#         table_name = layer.lower()


def order_ct_layers(layers):
    ordered = []

    # check if all layers referred to do exist
    referred = set([ref for v in layers.values() if (ref := v.get("contains"))])
    exist    = set(layers.keys())
    if not exist > referred:
        not_ex = referred - exist
        str_not_ex = ", ".join(sorted(["'" + elem + "'" for elem in not_ex]))

        raise Exception(f"The following referred layers do not exist: {str_not_ex}")

    simple_ord = sorted(layers.items(), key=lambda x: x[1].get("contains", ""))
    while len(simple_ord):
        for k, v in simple_ord:
            if not (conts := v.get("contains", None)):
                ordered.append((k, v))
                simple_ord.pop(simple_ord.index((k, v)))
            elif conts in [elem[0] for elem in ordered]:
                ordered.append((k, v))
                simple_ord.pop(simple_ord.index((k, v)))
            else:
                continue

    return ordered


def process_layer(layer_name, params, globs):
    tables, types = [], []

    table_name = layer_name.lower()
    cols = []

    cols.append(Column(table_name + "_id", "int", primary_key=True))

    for attr, vals in params.get("attributes", {}).items():
        if (type := vals.get("type", None)) == "text":
            norm_col = attr + "_id"
            norm_table = Table(
                            attr, [
                                Column(norm_col, "int", primary_key=True),
                                Column(attr, "text", unique=True)
                         ])

            cols.append(Column(norm_col, "int", foreign_key={"table": attr, "column": norm_col}))

            tables.append(norm_table)
        elif type == "categorical":
            enum_type = Type(attr, vals["values"])
            types.append(enum_type)
            cols.append(Column(attr, attr))
        elif not type and attr == "meta":
            cols.append(Column(attr, "jsonb",))
        else:
            raise Exception(f"unknown type for attribute: '{attr}'")

    anchs = [k for k, v in params.get("anchoring", {}).items() if v]
    if params.get("layerType", None) == "span" and (child := params.get("contains", None)):
        anchs += globs.layers[child]["anchoring"]
    table = Table(table_name, cols, anchorings=anchs)
    globs.layers[layer_name] = {}
    globs.layers[layer_name]["anchoring"] = anchs

    tables.append(table)

    globs.tables += tables
    globs.types  += types


def main():
    parser = argparse.ArgumentParser(description="Generate Postgres DDL from CT.")
    parser.add_argument("ct_file", type=str, # nargs="+",
                        help="the corpus template file (json)")
    parser.add_argument("-t", "--tabwidth", type=int, default=4,
                        help="size of tabulator")

    args = parser.parse_args()

    DDL.tabwidth = args.tabwidth


    with open(args.ct_file) as f:
        corpus_temp = json.load(f)

    layers = order_ct_layers(corpus_temp["layer"])

    for layer, props in layers:
        process_layer(layer, props, Globs)


    print("\n\n".join([x.create_DDL() for x in Globs.types]))
    print()
    print("\n\n".join([x.create_tbl() for x in Globs.tables]))
    print()
    print("\n\n".join([x.create_idxs() for x in Globs.tables]))
    print()
    print("\n\n".join([x.create_constrs() for x in Globs.tables]))



if __name__ == "__main__":
    main()

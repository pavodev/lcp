import os
import psycopg2

from textwrap import dedent


class SQLstats:
    check_tbl = lambda x, y: dedent(
        f"""
        SELECT EXISTS (
               SELECT 1
                 FROM information_schema.tables
                WHERE table_schema = '{x}'
                  AND table_name = '{y}');"""
    )

    copy_tbl = lambda x, y, z: dedent(
        f"""
        COPY {x}.{y} {z}
        FROM STDIN
        WITH CSV QUOTE E'\b' DELIMITER E'\t';"""
    )


class Table:
    def __init__(self, schema, name, columns=None):
        self.schema = schema
        self.name = name
        self.columns = columns

    def col_repr(self):
        return "(" + ", ".join(self.columns) + ")"

class Importer:
    def get_schema(self):
        return self.template["meta"]["name"] + str(self.template["meta"]["version"])

    def __init__(self, connection, template):
        self.con = connection
        self.cur = con.cursor()
        self.template = template
        self.get_schema()

    def create_constridx(self, constr_idxs):
        self.cur.execute(constr_idxs)

    def _check_tbl_exists(self, table):
        self.cur.execute(SQLstats.check_tbl(table.schema, table.name))

        if cur.fetchone()[0]:
            return True
        else:
            raise Exception(f"Error: table '{table.name}' does not exist.")

    def _copy_tbl(self, data_f):
        with open(data_f) as f:
            headers = f.readline().split("\t")

            table = Table(self.schema, data_f.split(".")[0], headers)

            self._check_tbl_exists(table)

            try:
                self.cur.copy_expert(
                    SQLstats.copy_tbl(table.schema, table.name, table.col_repr()), f
                )
                return True

            except Exception as e:
                raise e

    def import_corpus(self, data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

        for f in files:
            self._copy_tbl(f)



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
    def __init__(self, connection, template):
        self.connection = connection
        self.template = template
        self.name = self.template["meta"]["name"]
        self.version = self.template["meta"]["version"]
        self.schema = self.name + str(self.version)

    async def create_constridx(self, constr_idxs):
        async with self.connection:
            async with self.connection.cursor() as cur:
                await cur.execute(constr_idxs)

    async def _check_tbl_exists(self, table):
        async with self.connection:
            async with self.connection.cursor() as cur:
                await cur.execute(SQLstats.check_tbl(table.schema, table.name))

        if cur.fetchone()[0]:
            return True
        else:
            raise Exception(f"Error: table '{table.name}' does not exist.")

    async def _copy_tbl(self, data_f):
        with open(data_f) as f:
            headers = f.readline().split("\t")

            table = Table(self.schema, data_f.split(".")[0], headers)

            self._check_tbl_exists(table)

            async with self.connection:
                async with self.connection.cursor() as cur:
                    try:
                        await cur.copy_expert(
                            SQLstats.copy_tbl(
                                table.schema, table.name, table.col_repr()
                            ),
                            f,
                        )
                        return True
                    except Exception as e:
                        raise e

    async def import_corpus(self, data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

        for f in files:
            self._copy_tbl(f)

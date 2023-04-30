import aiofiles
import asyncio
import json
import os
import psycopg2
import sys

from textwrap import dedent

from .utils import gather


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

    main_corp = dedent(
        f"""
        INSERT
          INTO main.corpus (name, current_version, corpus_template, schema_path, token_counts, mapping, enabled)
        VALUES (%s, %s, %s, %s, %s, %s, true);"""
    )

    token_count = lambda x, y: dedent(
        f"""
        SELECT count(*)
          FROM {x}.{y};"""
    )


class Table:
    def __init__(self, schema, name, columns=None):
        self.schema = schema
        self.name = name
        self.columns = columns

    def col_repr(self):
        return "(" + ", ".join(self.columns) + ")"


class Importer:
    def __init__(self, connection, template, mapping):
        self.connection = connection
        self.template = template
        self.template["uploaded"] = True
        self.name = self.template["meta"]["name"]
        self.version = self.template["meta"]["version"]
        self.schema = self.name + str(self.version)
        self.token_count = None
        self.mapping = mapping
        self.max_concurrent = int(os.getenv("IMPORT_MAX_CONCURRENT", 1))
        if self.max_concurrent > 1:
            print(f"Processing concurrently * {self.max_concurrent}")
        else:
            print("Processing without concurrency")
        self.batchsize = int(float(os.getenv("IMPORT_MAX_COPY_BYTES", 1e9)))
        self.max_bytes = os.getenv("IMPORT_MAX_MEMORY_GB", "1")
        if self.max_bytes in {"-1", "0", ""}:
            self.max_bytes = None
        else:
            self.max_bytes = int(self.max_bytes) * 1000000000

    async def _get_positions(self, f, size):
        """
        Get the locations in an open aiofile to seek and read to
        """
        start_at = await f.tell()
        to_go = size - start_at
        positions = []

        while True:
            bat = int(self.batchsize)
            if start_at >= size:
                break
            await f.seek(start_at)
            lines = await f.read(self.batchsize)
            if not lines or not lines.strip():
                break
            if not lines.endswith("\n"):
                rest = await f.readline()
                bat += len(bytes(rest, "utf-8"))
            lines = None
            positions.append((start_at, bat))
            start_at = await f.tell()
        return positions

    async def copy_batch(self, start, chunk, cop, path, fsize, tot):
        base = os.path.basename(path)
        async with aiofiles.open(path) as f:
            await f.seek(start)
            data = await f.read(chunk)
            tell = await f.tell()
            if not data or not data.strip():
                return True
        async with self.connection.connection() as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                async with cur.copy(cop) as copy:
                    await copy.write(data)
                    pc = min(100, round(tell * 100 / fsize, 2))
                    print(f":progress:-1:{pc}%:{len(data)}:{tot} == {base}")
        return True

    async def create_constridx(self, constr_idxs):
        async with self.connection.connection() as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(constr_idxs)

    async def _check_tbl_exists(self, table):
        async with self.connection.connection() as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                script = SQLstats.check_tbl(table.schema, table.name)
                await cur.execute(script)
                res = await cur.fetchone()
                if res[0]:
                    return True
                raise AttributeError(f"Error: table '{table.name}' does not exist.")

    async def _copy_tbl(self, data_f, fsize, tot):
        base = os.path.basename(data_f)

        async with aiofiles.open(data_f) as f:
            headers = await f.readline()
            positions = await self._get_positions(f, fsize)

        table = Table(self.schema, base.split(".")[0], headers.split("\t"))
        await self._check_tbl_exists(table)
        cop = SQLstats.copy_tbl(table.schema, table.name, table.col_repr())

        if self.max_concurrent > 1:
            args = (cop, data_f, fsize, tot)
            await self.process_data(positions, self.copy_batch, *args)
            return True

        # no concurrency:
        done = 0
        async with aiofiles.open(data_f) as f:
            await f.readline()
            async with self.connection.connection() as conn:
                await conn.set_autocommit(True)
                async with conn.cursor() as cur:
                    async with cur.copy(cop) as copy:
                        for start, chunk in positions:
                            await f.seek(start)
                            data = await f.read(chunk)
                            await copy.write(data)
                            done += chunk
                            perc = round(done * 100 / tot, 2)
                            port = round(chunk * 100 / tot, 2)
                            print(
                                f":progress:{perc}%:{port}:{len(data)}:{tot} -- {base}"
                            )
        return True

    async def import_corpus(self, path):
        """
        Import all the .csv files in the corpus path
        """
        sizes = [
            (os.path.join(path, f), os.path.getsize(os.path.join(path, f)))
            for f in os.listdir(path)
            if f.endswith(".csv")
        ]
        corpus_size = sum(s[1] for s in sizes)
        await self.process_data(sizes, self._copy_tbl, *(corpus_size,))
        self.token_count = await self.get_token_count()

    async def process_data(self, iterable, method, *args):
        """
        Do the execution of copy_bath or copy_table from iterable data
        """
        # name = method.__name__
        name = "import"
        current_size = 0
        tasks = []
        for first, size in iterable:
            current_size += size
            if self.max_bytes and current_size >= self.max_bytes and tasks:
                print(
                    f"Doing {len(tasks)} {name} tasks...({current_size} >= {self.max_bytes})"
                )
                await gather(self.max_concurrent, *tasks, name=name)
                tasks = []
                current_size = 0
            tasks.append(method(first, size, *args))
        print(f"Doing {len(tasks)} remaining {name} tasks...")
        return await gather(self.max_concurrent, *tasks, name=name)

    async def get_token_count(self):
        """
        count inserted words/tokens in DB and return
        TODO: not working for parallel
        """
        token = self.template["firstClass"]["token"] + "0"

        async with self.connection.connection() as conn:
            async with conn.cursor() as cur:
                query = SQLstats.token_count(self.schema, token)
                await cur.execute(query)
                res = await cur.fetchone()
                if res:
                    return {token: res[0]}
        raise ValueError("could not get token count")

    async def create_entry_maincorpus(self):
        async with self.connection.connection() as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(
                    SQLstats.main_corp,
                    (
                        self.name,
                        self.version,
                        json.dumps(self.template),
                        self.schema,
                        json.dumps(self.token_count),
                        self.mapping,
                    ),
                )

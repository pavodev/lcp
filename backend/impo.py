import asyncio
import json
import os

import sys

from textwrap import dedent
from typing import (
    Any,
    Awaitable,
    Dict,
    Iterable,
    List,
    Optional,
    Union,
    Callable,
    Tuple,
    Coroutine,
)

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper

from psycopg_pool import AsyncConnectionPool

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
    def __init__(
        self, schema: str, name: str, columns: Optional[Iterable[str]] = None
    ) -> None:
        self.schema = schema
        self.name = name
        self.columns = columns

    def col_repr(self) -> str:
        if self.columns:
            return "(" + ", ".join(self.columns) + ")"
        else:
            return ""


class Importer:
    def __init__(
        self,
        connection: AsyncConnectionPool,
        template: Dict[str, Any],
        mapping: Dict[str, Any],
        project_dir: str,
    ) -> None:
        """
        Manage the import of a corpus into the DB via async psycopg connection
        """
        self.connection = connection
        self.template = template
        self.template["uploaded"] = True
        self.name = self.template["meta"]["name"]
        self.version = self.template["meta"]["version"]
        self.schema = self.name + str(self.version)
        self.token_count: Dict[str, int] = {}
        self.mapping = mapping
        self.max_concurrent = int(os.getenv("IMPORT_MAX_CONCURRENT", 2))
        self.batchsize = int(float(os.getenv("IMPORT_MAX_COPY_GB", 1)) * 1e9)
        self.max_bytes = int(os.getenv("IMPORT_MAX_MEMORY_GB", "1"))
        if self.max_bytes == -1:
            self.max_bytes = 0
        else:
            self.max_bytes = int(self.max_bytes * 1e9)
        self.project_dir = project_dir
        if self.max_concurrent < 1:
            self.update_progress(f"Processing concurrently without limit...")
        elif self.max_concurrent > 1:
            self.update_progress(f"Processing concurrently * {self.max_concurrent}")
        else:
            self.update_progress("Processing without concurrency")

    def update_progress(self, msg: str) -> None:
        """
        Both print and write progress information. We do this so the webapp
        can read this file to calculate progress information to show the user
        """
        print(msg)
        path = os.path.join(self.project_dir, ".progress.txt")
        with open(path, "a") as fo:
            fo.write(msg.rstrip() + "\n")

    async def _get_positions(
        self, f: AsyncTextIOWrapper, size: int
    ) -> List[Tuple[int, int]]:
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
            positions.append((start_at, bat))
            start_at = await f.tell()
        return positions

    async def copy_batch(
        self, start: int, chunk: int, cop: str, path: str, fsize: int, tot: int
    ) -> bool:
        """
        Copy a chunk of CSV into the DB, going no larger than self.batchsize
        plus potentially the remainder of a line
        """
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
                    self.update_progress(f":progress:{pc}%:{len(data)}:{tot} == {base}")
        return True

    async def create_constridx(self, constr_idxs: str) -> None:
        """
        Set constraints on the imported corpus
        """
        async with self.connection.connection() as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(constr_idxs)

    async def _check_tbl_exists(self, table: Table) -> bool:
        """
        Ensure that a table exists or raise AttributeError
        """
        async with self.connection.connection() as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                script = SQLstats.check_tbl(table.schema, table.name)
                await cur.execute(script)
                res = await cur.fetchone()
                if res and res[0]:
                    return True
                raise AttributeError(f"Error: table '{table.name}' does not exist.")

    async def _copy_tbl(self, csv_path: str, fsize: int, tot: int) -> bool:
        """
        Import csv_path to the DB, with or without concurrency
        """
        base = os.path.basename(csv_path)

        async with aiofiles.open(csv_path) as f:
            headers = await f.readline()
            positions = await self._get_positions(f, fsize)

        table = Table(self.schema, base.split(".")[0], headers.split("\t"))
        await self._check_tbl_exists(table)
        cop = SQLstats.copy_tbl(table.schema, table.name, table.col_repr())

        if self.max_concurrent != 1:
            args = (cop, csv_path, fsize, tot)
            await self.process_data(positions, self.copy_batch, *args)
            return True

        # no concurrency:
        done = 0
        async with aiofiles.open(csv_path) as f:
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
                            self.update_progress(
                                f":progress:{perc}%{len(data)}:{tot} -- {base}"
                            )
        return True

    async def import_corpus(self) -> None:
        """
        Import all the .csv files in the corpus path and count the total tokens
        """
        path = self.project_dir
        sizes = [
            (os.path.join(path, f), os.path.getsize(os.path.join(path, f)))
            for f in os.listdir(path)
            if f.endswith(".csv")
        ]
        corpus_size = sum(s[1] for s in sizes)
        await self.process_data(sizes, self._copy_tbl, *(corpus_size,))
        self.token_count = await self.get_token_count()

    async def process_data(
        self,
        iterable: Iterable[Tuple[Union[str, int], int]],
        method: Callable,
        *args: Any,
    ) -> None:
        """
        Do the execution of copy_bath or copy_table (method) from iterable data

        If the size of the combined tasks goes beyond self.max_bytes, we start
        those in the queue and wait for them to finish before adding more.

        All processing occurs with self.max_concurrent respected
        """
        # name = method.__name__
        name = "import"
        current_size = 0
        tasks: List[Coroutine] = []
        for first, size in iterable:
            current_size += size
            if self.max_bytes and current_size >= self.max_bytes and tasks:
                self.update_progress(
                    f"Doing {len(tasks)} {name} tasks...({current_size} >= {self.max_bytes})"
                )
                await gather(self.max_concurrent, *tasks, name=name)
                tasks = []
                current_size = 0
            tasks.append(method(first, size, *args))
        self.update_progress(f"Doing {len(tasks)} remaining {name} tasks...")
        await gather(self.max_concurrent, *tasks, name=name)
        return None

    async def get_token_count(self) -> Dict[str, int]:
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

    async def run_script(self, script, size, *args):
        """
        Run a simple script -- used for prepared segments
        """
        async with self.connection.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(script)

    async def prepare_segments(self, create, inserts):
        """
        Run the prepared segment scripts, potentially concurrently
        """
        print("Running\n", create)
        await self.run_script(create, -1)
        if inserts:
            print(f"Running inserts * {len(inserts)}\n{inserts[0]}\n")
        iterable = [(i, 1) for i in inserts]
        args = tuple()
        await self.process_data(iterable, self.run_script, *tuple())

    async def create_entry_maincorpus(self) -> None:
        """
        Add a row to main.corpus with metadata about the imported corpus
        """
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
        return None

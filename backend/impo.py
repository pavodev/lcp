from __future__ import annotations

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
    Callable,
    Tuple,
    Coroutine,
)

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper

from psycopg_pool import AsyncConnectionPool

from .utils import gather


class SQLstats:
    def __init__(self):
        self.check_tbl = lambda x, y: dedent(
            f"""
            SELECT EXISTS (
                   SELECT 1
                     FROM information_schema.tables
                    WHERE table_schema = '{x}'
                      AND table_name = '{y}');"""
        )

        self.copy_table = lambda x, y, z: dedent(
            f"""
            COPY {x}.{y} {z}
            FROM STDIN
            WITH CSV QUOTE E'\b' DELIMITER E'\t';"""
        )

        self.main_corp = dedent(
            f"""
            INSERT
              INTO main.corpus (name, current_version, corpus_template, schema_path, token_counts, mapping, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, true);"""
        )

        self.token_count = lambda x, y: dedent(
            f"""
            SELECT count(*)
              FROM {x}.{y};"""
        )


class Table:
    def __init__(
        self, schema: str, name: str, columns: Iterable[str] | None = None
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
        schema_name: str,
        n_batches: int,
    ) -> None:
        """
        Manage the import of a corpus into the DB via async psycopg connection
        """
        self.sql = SQLstats()
        self.connection = connection
        self.template = template
        self.template["uploaded"] = True
        self.name = self.template["meta"]["name"]
        self.version = self.template["meta"]["version"]
        self.schema = schema_name
        self.n_batches = n_batches
        self.token_count: Dict[str, int] = {}
        self.mapping = mapping
        self.max_concurrent = int(os.getenv("IMPORT_MAX_CONCURRENT", 2))
        self.batchsize = int(float(os.getenv("IMPORT_MAX_COPY_GB", 1)) * 1e9)
        self.max_bytes = int(os.getenv("IMPORT_MAX_MEMORY_GB", "1"))
        self.upload_timeout = int(os.getenv("UPLOAD_TIMEOUT", 300))
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

    async def cleanup(self):
        script = f"DROP SCHEMA IF EXISTS {self.schema} CASCADE;"
        self.update_progress(f"Running cleanup:\n{script}")
        await self.run_script(script)

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
            positions.append((start_at, min(bat, to_go)))
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
        async with self.connection.connection(self.upload_timeout) as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                async with cur.copy(cop) as copy:
                    await copy.write(data)
                    pc = min(100, round(tell * 100 / fsize, 2))
                    self.update_progress(f":progress:{pc}%:{len(data)}:{tot} == {base}")
        return True

    async def _check_tbl_exists(self, table: Table) -> bool:
        """
        Ensure that a table exists or raise AttributeError
        """
        async with self.connection.connection(self.upload_timeout) as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                script = self.sql.check_tbl(table.schema, table.name)
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
        cop = self.sql.copy_table(table.schema, table.name, table.col_repr())

        if self.max_concurrent != 1:
            args = (cop, csv_path, fsize, tot)
            await self.process_data(positions, self.copy_batch, *args)
            return True

        # no concurrency:
        done = 0
        async with aiofiles.open(csv_path) as fo:
            x = await fo.readline()
            async with self.connection.connection(self.upload_timeout) as conn:
                await conn.set_autocommit(True)
                async with conn.cursor() as cur:
                    async with cur.copy(cop) as copy:
                        for start, chunk in positions:
                            await fo.seek(start)
                            data = await fo.read(chunk)
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
        iterable: Any,  # sorry
        method: Callable,
        *args,
        **kwargs,
    ) -> List[Any]:
        """
        Do the execution of copy_bath or copy_table (method) from iterable data

        If the size of the combined tasks goes beyond self.max_bytes, we start
        those in the queue and wait for them to finish before adding more.

        All processing occurs with self.max_concurrent respected
        """
        x: List[Any] = []
        return x

    async def get_token_count(self) -> Dict[str, int]:
        """
        count inserted words/tokens in DB and return
        TODO: not working for parallel
        """
        token = self.template["firstClass"]["token"]
        names = []
        queries = []
        for i in range(self.n_batches + 1):
            formed = f"{token}{i}" if i < self.n_batches else f"{token}rest"
            names.append(formed)
            query = self.sql.token_count(self.schema, formed)
            queries.append(query)
        response = await self.process_data(queries, self.run_script, give=True)

        res: Dict[str, Any] = {k: int(v[0]) for k, v in zip(names, response)}
        return res

    async def run_script(self, script, *args, give: bool = False):
        """
        Run a simple script -- used for prepared segments
        """
        async with self.connection.connection(self.upload_timeout) as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(script)
                if give:
                    got = await cur.fetchone()
                    return got

    async def prepare_segments(self, create, insert, batchnames):
        """
        Run the prepared segment scripts, potentially concurrently
        """
        self.update_progress("Computing prepared segments...")
        self.update_progress("Running:" + create)
        await self.run_script(create)
        if insert:
            self.update_progress(f"Running {len(batchnames)} insert tasks:\n{insert}\n")
        inserts = [insert.format(batch=batch) for batch in batchnames]
        args = tuple()
        await self.process_data(inserts, self.run_script, *args)

    async def create_entry_maincorpus(self) -> None:
        """
        Add a row to main.corpus with metadata about the imported corpus
        """
        async with self.connection.connection(self.upload_timeout) as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(
                    self.sql.main_corp,
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

from __future__ import annotations

import importlib
import json
import os

from collections.abc import Callable, Coroutine, Sequence
from textwrap import dedent
from typing import Any, cast

import aiofiles

from aiofiles.threadpool.binary import AsyncBufferedReader
from aiofiles.threadpool.text import AsyncTextIOWrapper
from psycopg_pool import AsyncConnectionPool, AsyncNullConnectionPool

from .configure import CorpusTemplate
from .typed import JSONObject, MainCorpus, Params, RunScript
from .utils import gather


class SQLstats:
    def __init__(self) -> None:
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
            VALUES (%s, %s, %s, %s, %s, %s, true)
            RETURNING *;
            """
        )

        self.token_count = lambda x, y: dedent(
            f"""
            SELECT count(*)
              FROM {x}.{y};"""
        )


class Table:
    def __init__(
        self, schema: str, name: str, columns: list[str] | None = None
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
        connection: AsyncConnectionPool | AsyncNullConnectionPool,
        data: JSONObject,
        project_dir: str,
    ) -> None:
        """
        Manage the import of a corpus into the DB via async psycopg connection
        """
        _loader = importlib.import_module(self.__module__).__loader__
        self.sql: SQLstats = SQLstats()
        self.connection = connection
        self.template = cast(CorpusTemplate, data["template"])
        self.template["uploaded"] = True
        self.name: str = cast(dict, self.template["meta"])["name"]
        self.version: int | str | float = cast(dict, self.template["meta"])["version"]
        self.schema = cast(str, self.template["schema_name"])
        self.batches = cast(list[str], data["batchnames"])
        self.insert = cast(str, data["prep_seg_insert"])
        self.constraints = cast(list[str], data["constraints"])
        self.create = cast(str, data["prep_seg_create"])
        self.refs = cast(list[str], data["refs"])
        self.n_batches = len(self.batches)
        self.num_extras = self.n_batches + len(self.constraints)
        self.token_count: dict[str, int] = {}
        self.mapping = cast(JSONObject, data["mapping"])
        self.project_dir: str = project_dir
        self.corpus_size: int = 0
        self.max_concurrent = int(os.getenv("IMPORT_MAX_CONCURRENT", 2))
        self.mypy = "SourceFileLoader" not in str(_loader)
        self.batchsize = int(float(os.getenv("IMPORT_MAX_COPY_GB", 1)) * 1e9)
        self.max_gb = int(os.getenv("IMPORT_MAX_MEMORY_GB", "1"))
        self.max_bytes = int(max(0, self.max_gb) * 1e9)
        self.upload_timeout = int(os.getenv("UPLOAD_TIMEOUT", 300))
        return None

    def update_progress(self, msg: str) -> None:
        """
        Both print and write progress information. We do this so the webapp
        can read this file to calculate progress information to show the user
        """
        print(msg)
        path = os.path.join(self.project_dir, ".progress.txt")
        with open(path, "a") as fo:
            fo.write(msg.rstrip() + "\n")
        return None

    async def cleanup(self) -> None:
        """
        Drop all the data we just tried to import -- used as exception handling
        """
        script = f"DROP SCHEMA IF EXISTS {self.schema} CASCADE;"
        self.update_progress(f"Running cleanup:\n{script}")
        await self.run_script(script)
        return None

    async def _get_positions(
        self, f: AsyncBufferedReader, size: int
    ) -> list[tuple[int, int]]:
        """
        Get the locations in an open aiofile to seek and read to

        We can't make this into an async generator yet because mypy doesn't support this
        """
        start_at = await f.tell()
        to_go = size - start_at
        positions: list[tuple[int, int]] = []

        while True:
            bat = int(self.batchsize)
            if start_at >= size:
                break
            await f.seek(start_at)
            lines = await f.read(self.batchsize)
            if not lines or not lines.strip():
                break
            if not lines.endswith(b"\n"):
                rest = await f.readline()
                bat += len(rest)
            positions.append((start_at, min(bat, to_go)))
            start_at = await f.tell()
        return positions

    async def copy_batch(
        self,
        start: int,
        chunk: int,
        cop: str,
        csv_path: str,
        fsize: int,
        tot: int,
    ) -> None:
        """
        Copy a chunk of CSV into the DB, going no larger than self.batchsize
        plus potentially the remainder of a line
        """
        base = os.path.basename(csv_path)
        sz: int = 0
        async with aiofiles.open(csv_path, "r") as f:
            await f.seek(start)
            data = await f.read(chunk)
            if not data or not data.strip():
                return None
            async with self.connection.connection(self.upload_timeout) as conn:
                async with conn.cursor() as cur:
                    async with cur.copy(cop) as copy:
                        await copy.write(data)
                        sz = len(data)
        prog = f":progress:{sz}:{tot}:{base}:"
        self.update_progress(prog)
        return None

    async def _copy_tbl(self, csv_path: str, fsize: int, tot: int) -> None:
        """
        Import csv_path to the DB, with or without concurrency

        Note that we need to add the newline flag to open in order
        to get the correct number of bytes in the file. but then
        progress will show 100% instead of 98% which is worse UX.
        """
        base = os.path.basename(csv_path)
        async with aiofiles.open(csv_path, "rb") as fop:
            headers = await fop.readline()
            headlen = len(headers)
            positions = await self._get_positions(fop, fsize)

        self.update_progress(f":progress:{headlen}:{tot}:{base}:")
        tab = base.split(".")[0]
        table = Table(self.schema, tab, headers.decode("utf-8").split("\t"))
        script = self.sql.check_tbl(table.schema, table.name)
        exists = cast(list[tuple[bool]], await self.run_script(script, give=True))
        if exists[0][0] is False:
            raise ValueError(f"Table not found: {self.schema}.{tab}")
        cop = self.sql.copy_table(table.schema, table.name, table.col_repr())

        if self.max_concurrent != 1:
            args = (cop, csv_path, fsize - headlen, tot)
            await self.process_data(positions, self.copy_batch, *args)
            return None

        # no concurrency:
        async with aiofiles.open(csv_path, "rb") as f:
            async with self.connection.connection(self.upload_timeout) as conn:
                async with conn.cursor() as cur:
                    async with cur.copy(cop) as copy:
                        for start, chunk in positions:
                            await f.seek(start)
                            data = await f.read(chunk)
                            await copy.write(data)
                            sz = len(data)
                            headlen += sz
                            self.update_progress(f":progress:{sz}:{tot}:{base}:")
        return None

    async def import_corpus(self) -> None:
        """
        Import all the .csv files in the corpus path and count the total tokens
        """
        self.update_progress("Importing corpus...")
        path = self.project_dir
        sizes = [
            (os.path.join(path, f), os.path.getsize(os.path.join(path, f)))
            for f in os.listdir(path)
            if f.endswith(".csv")
        ]
        self.corpus_size = sum(s[1] for s in sizes)
        await self.process_data(sizes, self._copy_tbl, *(self.corpus_size,))
        return None

    async def process_data(
        self,
        iterable: Sequence[str | tuple[str | int, int]],
        method: Callable[..., Coroutine],
        *args,
        **kwargs,
    ) -> list[RunScript]:
        """
        Do the execution of copy_batch or copy_table (method) from iterable data

        If the size of the combined tasks goes beyond self.max_bytes, we start
        those in the queue and wait for them to finish before adding more.

        All processing occurs with self.max_concurrent respected
        """
        mc = self.max_concurrent
        name = "import"
        current_size = 0
        tasks: list[Coroutine] = []
        batches = f"in batches of {mc}" if mc > 0 else "concurrently"
        gathered: list[Any] = []
        cs: float | int = 0.0
        first: str | int = ""
        more: list = []
        give: bool = kwargs.get("give", False)
        mname = method.__name__
        progs = "Doing {} {} tasks {}...({}MB vs {}GB)"
        for tup in iterable:
            if isinstance(tup, (str, int)):
                first = tup
                size = 0
            else:
                first, size = tup
            current_size += size
            too_big = self.max_bytes and current_size >= self.max_bytes and len(tasks)
            if too_big:
                cs = current_size / 1e6
                msg = progs.format(len(tasks), mname, batches, f"{cs:.2f}", self.max_gb)
                self.update_progress(msg)
                more = await gather(mc, tasks, name=name)
                if len(more) and give is True:
                    gathered += more
                tasks = []
                current_size = 0
            tasks.append(method(first, size, *args, **kwargs))

        if tasks:
            cs = current_size / 1e6
            rem = f"remaining {mname}"
            msg = progs.format(len(tasks), rem, batches, f"{cs:.2f}", self.max_gb)
            self.update_progress(msg)
            more = await gather(mc, tasks, name=name)
            if len(more) and give is True:
                gathered += more
        return gathered

    async def get_token_count(self) -> dict[str, int]:
        """
        count inserted words/tokens in DB and return
        TODO: not working for parallel
        """
        fc = cast(dict[str, str], self.template["firstClass"])
        token = fc["token"]
        names: list[str] = []
        queries: list[str] = []
        for i in range(self.n_batches + 1):
            formed = f"{token}{i}" if i < self.n_batches else f"{token}rest"
            names.append(formed)
            query = self.sql.token_count(self.schema, formed)
            queries.append(query)
        task = self.process_data(queries, self.run_script, give=True)
        response = cast(list[list[tuple[int]]], await task)
        res: dict[str, int] = {k: int(v[0][0]) for k, v in zip(names, response)}
        return res

    async def run_script(
        self,
        script: str,
        *args: Any,
        give: bool = False,
        progress: str | None = None,
        # todo: params could get a more general type if it is used for anything else:
        params: Params | None = None,
    ) -> RunScript:
        """
        Run a simple script, and return the result if give

        If progress, also print/write progress info
        """
        async with self.connection.connection(self.upload_timeout) as conn:
            async with conn.cursor() as cur:
                await cur.execute(script, params or tuple())
                if isinstance(progress, str):
                    self.update_progress(progress)
                if not give:
                    return None
                res: RunScript = await cur.fetchall()
                return res
        return None

    async def prepare_segments(
        self,
        progress: str | None = None,
    ) -> None:
        """
        Run the prepared segment scripts, potentially concurrently
        """
        self.update_progress("Computing prepared segments...")
        await self.run_script(self.create)
        msg = f"Running {len(self.batches)} insert tasks:\n{self.insert}\n"
        self.update_progress(msg)
        inserts = [self.insert.format(batch=batch) for batch in self.batches]
        await self.process_data(inserts, self.run_script, progress=progress)
        return None

    async def create_entry_maincorpus(self) -> MainCorpus:
        """
        Add a row to main.corpus with metadata about the imported corpus
        """
        self.update_progress("Adding to corpus list...")
        params = (
            self.name,
            self.version,
            json.dumps(self.template),
            self.schema,
            json.dumps(self.token_count),
            json.dumps(self.mapping),
        )
        task = self.run_script(self.sql.main_corp, give=True, params=params)
        rows = cast(list[MainCorpus], await task)
        return rows[0]

    async def drop_similar(self) -> None:
        """
        Drop schemas from DB if they are the same as this one, minus the uuid

        This is dangerous and needs to be updated with logic checkin
        """
        start = self.schema[:-4]
        query = f"SELECT schema_name FROM information_schema.schemata WHERE schema_name ~ '^{start}';"
        results = cast(list[tuple[str]], await self.run_script(query, give=True))
        if not results:
            return None
        base = "DROP SCHEMA {schema} CASCADE;"
        scripts = [base.format(schema=s[0]) for s in results if s[0] != self.schema]
        # actually do the drops (in parallel):
        await self.process_data(scripts, self.run_script)
        return None

    async def pipeline(self) -> MainCorpus:
        """
        Run the entire import pipeline: add data, set indices, grant rights
        """
        await self.drop_similar()
        await self.import_corpus()
        self.token_count = await self.get_token_count()
        pro = f":progress:1:{self.num_extras}:extras:"
        cons = "\n".join(self.constraints)
        self.update_progress(f"Setting constraints...\n{cons}")
        await self.process_data(self.constraints, self.run_script, progress=pro)
        if len(self.refs):
            strung = "\n".join(self.refs)
            self.update_progress(f"Running:\n{strung}")
            await self.run_script(strung)
        await self.prepare_segments(progress=pro)
        return cast(MainCorpus, await self.create_entry_maincorpus())

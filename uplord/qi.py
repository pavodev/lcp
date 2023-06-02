import json
import sys

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TypeVar, cast
from uuid import uuid4

from abstract_query.create import json_to_sql
from aiohttp import web

# we need the below to avoid a mypy keyerror in the type annotation:
from aiohttp.web import Application
from rq.job import Job

# wish there was a nicer way to do this...delete once we are sure of 3.11+
if sys.version_info < (3, 11):
    Self = TypeVar("Self", bound="QueryIteration")
else:
    from typing import Self

from .configure import CorpusConfig
from .dqd_parser import convert
from .typed import Batch, JSONObject, Query, Results
from .worker import SQLJob

if sys.version_info <= (3, 9):
    QI_KWARGS = dict()
else:
    QI_KWARGS = dict(kw_only=True, slots=True)


@dataclass(**QI_KWARGS)
class QueryIteration:
    """
    Model an iteration of a query, with all its associated settings
    """

    config: dict[str, CorpusConfig]
    user: str
    room: str | None
    query: str
    corpora: list[int]
    all_batches: list[Batch]
    total_results_requested: int
    needed: int
    page_size: int
    languages: set[str]
    simultaneous: str
    base: None | str
    sentences: bool
    is_vian: bool
    app: Application
    hit_limit: bool | int = False
    resuming: bool = False
    previous: str = ""
    done: bool = False
    request_data: JSONObject | None = None
    current_batch: Batch | None = None
    done_batches: list[Batch] = field(default_factory=list)
    total_results_so_far: int = 0
    existing_results: Results = field(default_factory=dict)
    job: Job | SQLJob | None = None
    job_id: str | None = ""
    previous_job: Job | SQLJob | None = None
    dqd: str = ""
    sql: str = ""
    jso: Query = field(default_factory=dict)
    meta: dict[str, list[JSONObject]] = field(default_factory=dict)

    def make_query(self) -> None:
        """
        Do any necessary query conversions

        Produces: the DQD/None, JSON, SQL and SQL metadata objects
        """
        if self.current_batch is None:
            raise ValueError("Batch not found")

        kwa = dict(
            schema=self.current_batch[1],
            batch=self.current_batch[2],
            config=self.app["config"][str(self.current_batch[0])],
            lang=self._determine_language(self.current_batch[2]),
            vian=self.is_vian,
        )
        try:
            json_query = json.loads(self.query)
        except json.JSONDecodeError:
            json_query = convert(self.query)
            self.dqd = self.query
        sql_query, meta_json = json_to_sql(json_query, **kwa)
        self.jso = json_query
        self.sql = sql_query
        self.meta = meta_json
        return None

    @staticmethod
    def _get_query_batches(
        corpora: list[int],
        config: dict[str, CorpusConfig],
        languages: set[str],
        is_vian: bool,
    ) -> list[Batch]:
        """
        Get a list of tuples in the format of (corpus, batch, size) to be queried

        todo: make this not static
        """
        out: list[Batch] = []
        all_languages = ["en", "de", "fr", "ca"]
        all_langs = tuple([f"_{la}" for la in all_languages])
        langs = tuple([f"_{la}" for la in languages])
        for corpus in corpora:
            batches = config[str(corpus)]["_batches"]
            for name, size in batches.items():
                stripped = name.rstrip("0123456789")
                if stripped.endswith("rest"):
                    stripped = stripped[:-4]
                if not stripped.endswith(langs) and stripped.endswith(all_langs):
                    continue
                schema = config[str(corpus)]["schema_path"]
                out.append((corpus, schema, name, size))
        return sorted(out, key=lambda x: x[-1])

    @classmethod
    async def from_request(cls, request: web.Request) -> Self:
        """
        The first time we encounter the data, it's an aiohttp request

        Normalise it into this dataclass.
        """
        request_data = await request.json()
        corp = request_data["corpora"]
        if not isinstance(corp, list):
            corp = [corp]
        corpora_to_use = [int(i) for i in corp]
        langs = [i.strip() for i in request_data.get("languages", ["en"])]
        languages = set(langs)
        total_requested = request_data.get("total_results_requested", 1000)
        previous = request_data.get("previous", "")
        base = None if not request_data.get("resume") else previous
        is_vian = request_data.get("appType") == "vian"
        # todo: remove this line:
        is_vian = (
            "tangram" in request.app["config"][str(corpora_to_use[0])]["schema_path"]
        )
        sim = request_data.get("simultaneous", False)
        all_batches = cls._get_query_batches(
            corpora_to_use, request.app["config"], languages, is_vian
        )

        details = {
            "corpora": corpora_to_use,
            "request_data": request_data,
            "user": request_data["user"],
            "app": request.app,
            "room": request_data["room"],
            "config": request.app["config"],
            "page_size": request_data.get("page_size", 10),
            "all_batches": all_batches,
            "sentences": request_data.get("sentences", True),
            "languages": set(langs),
            "query": request_data["query"],
            "resuming": request_data.get("resume", False),
            "existing_results": {},
            "total_results_requested": total_requested,
            "needed": total_requested,
            "total_results_so_far": 0,
            "simultaneous": str(uuid4()) if sim else "",
            "previous": previous,
            "base": base,
            "is_vian": is_vian,
        }
        return cls(**details)

    @staticmethod
    def _determine_language(batch: str) -> str | None:
        """
        Helper to find language from batch
        """
        batch = batch.rstrip("0123456789")
        if batch.endswith("rest"):
            batch = batch[:-4]
        for lan in ["de", "en", "fr", "ca"]:
            if batch.endswith(f"_{lan}"):
                return lan
        return None

    def sents_query(self) -> str:
        """
        Build a query to fetch sentences (uuids to be filled in as params)
        """
        if not self.current_batch:
            raise ValueError("Need batch")
        schema = self.current_batch[1]
        lang = self._determine_language(self.current_batch[2])
        config = self.config[str(self.current_batch[0])]
        seg = cast(str, config["segment"])
        name = seg.strip()
        underlang = f"_{lang}" if lang else ""
        seg_name = f"prepared_{name}{underlang}"
        script = f"SELECT {name}_id, off_set, content FROM {schema}.{seg_name} WHERE {name}_id = ANY(:ids);"
        return script

    @classmethod
    async def from_manual(cls, manual: JSONObject, app: web.Application) -> Self:
        """
        For subsequent queries (i.e. over non-initial batches), there is no request;
        the request handler is manually called with JSON data instead of a request object.

        The non-serialisable app is passed in separately.
        """
        job_id = cast(str, manual["job"])
        job = Job.fetch(job_id, connection=app["redis"])

        done_batches = [
            tuple(i) for i in cast(list[Sequence[str | int]], manual["done_batches"])
        ]
        cur = cast(Sequence[int | str], manual["current_batch"])
        # sorry about this:
        current: Batch = (int(cur[0]), str(cur[1]), str(cur[2]), int(cur[3]))
        if current not in done_batches:
            done_batches.append(current)
        all_batches = [
            tuple(i) for i in cast(list[Sequence[int | str]], manual["all_batches"])
        ]

        corpora_to_use = cast(list[int], manual["corpora"])

        tot_req = cast(int, manual["total_results_requested"])
        tot_so_far = cast(int, manual["total_results_so_far"])
        needed = tot_req - tot_so_far if tot_req > 0 else -1

        details = {
            "corpora": corpora_to_use,
            "existing_results": manual["result"],
            "user": manual["user"],
            "room": manual["room"],
            "job": job,
            "app": app,
            "job_id": manual["job"],
            "config": app["config"],
            "simultaneous": manual.get("simultaneous", ""),
            "needed": needed,
            "previous": manual.get("previous", ""),  # comment out?
            "page_size": job.kwargs.get("page_size", 20),
            "total_results_requested": tot_req,
            "base": manual["base"],
            "query": job.kwargs["original_query"],
            "sentences": manual.get("sentences", True),
            "hit_limit": manual.get("hit_limit", False),
            "current_batch": None,
            "all_batches": all_batches,
            "total_results_so_far": tot_so_far,
            "languages": set(cast(list[str], manual["languages"])),
            "done_batches": done_batches,
            "is_vian": manual.get("is_vian", False),
        }
        return cls(**details)

    def decide_batch(self) -> None:
        """
        Find the best next batch to query
        """
        if self.current_batch is not None:
            return None

        buffer = 0.1  # set to zero for picking smaller batches

        so_far = self.total_results_so_far
        if self.is_vian:
            if self.done_batches:
                raise ValueError("VIAN corpora have only one batch!?")
            self.current_batch = self.all_batches[0]
            return None

        if not len(self.done_batches):
            self.current_batch = self.all_batches[0]
            return None

        if self.hit_limit != 0:  # do not change to 'if hit limit!'
            self.current_batch = self.done_batches[-1]
            return None

        # set here ensures we don't double count, even though it should not happen
        total_words_processed_so_far = sum([x[-1] for x in set(self.done_batches)])
        proportion_that_matches = so_far / total_words_processed_so_far
        first_not_done: Batch | None = None

        for batch in self.all_batches:
            if batch in self.done_batches:
                continue
            if not first_not_done:
                first_not_done = batch
                if self.needed == -1:
                    self.current_batch = batch
                    return None

            # todo: should we do this? next-smallest for low number of matches?
            if self.page_size > 0 and so_far < min(self.page_size, 25):
                self.current_batch = batch
                return None
            expected = batch[-1] * proportion_that_matches
            if float(expected) >= float(self.needed + (self.needed * buffer)):
                self.current_batch = batch
                return None

        if not first_not_done:
            raise ValueError("Could not find batch")
        self.current_batch = first_not_done
        return None

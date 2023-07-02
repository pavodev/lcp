import json
import sys

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TypeVar, cast
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
    sentences: bool
    is_vian: bool
    app: Application
    resuming: bool = False
    previous: str = ""
    request_data: JSONObject | None = None
    current_batch: Batch | None = None
    total_duration: float = 0.0
    done_batches: list[Batch] = field(default_factory=list)
    total_results_so_far: int = 0
    existing_results: Results = field(default_factory=dict)
    job: Job | SQLJob | None = None
    job_id: str = ""
    from_memory: bool = False
    previous_job: Job | SQLJob | None = None
    cut_short: int = -1
    dqd: str = ""
    sql: str = ""
    send_stats: bool = True
    full: bool = False
    sent_id_offset: int = 0
    jso: Query = field(default_factory=dict)
    meta: dict[str, list[JSONObject]] = field(default_factory=dict)
    job_info: dict[str, str | bool | list[str]] = field(default_factory=dict)
    word_count: int = 0
    iteration: int = 0
    first_job: str = ""
    query_depends: list[str] = field(default_factory=list)
    dep_chain: list[str] = field(default_factory=list)
    post_processes: dict[int, Any] = field(default_factory=dict)

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

        sql_query, meta_json, post_processes = json_to_sql(json_query, **kwa)
        self.jso = json_query
        self.sql = sql_query
        self.meta = meta_json
        self.post_processes = post_processes
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
        first_job = ""
        total_duration = 0.0
        total_results_so_far = 0
        cut_short = -1
        if previous:
            prev = Job.fetch(previous, connection=request.app["redis"])
            first_job = prev.kwargs.get("first_job") or previous
            total_duration = prev.kwargs.get("total_duration", 0.0)
            total_results_so_far = prev.meta.get("total_results_so_far", 0)
            cut_short = prev.meta.get("cut_short", 0)
        is_vian = request_data.get("appType") == "vian"
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
            "full": request_data.get("full", False),
            "query": request_data["query"],
            "resuming": request_data.get("resume", False),
            "existing_results": {},
            "total_results_requested": total_requested,
            "needed": total_requested,
            "total_duration": total_duration,
            "first_job": first_job,
            "cut_short": cut_short,
            "total_results_so_far": total_results_so_far,
            "simultaneous": str(uuid4()) if sim else "",
            "previous": previous,
            "is_vian": is_vian,
        }
        made: Self = cls(**details)
        made.get_word_count()
        return made

    def get_word_count(self) -> None:
        """
        Sum the word counts for corpora being searched
        """
        total = 0
        for corpus in self.corpora:
            conf = self.app["config"][str(corpus)]
            try:
                has_partitions = "partitions" in conf["mapping"]["layer"][conf["token"]]
            except (KeyError, TypeError):
                has_partitions = False
            if not has_partitions or not self.languages:
                total += sum(conf["token_counts"].values())
            else:
                counts = conf["token_counts"]
                for name, num in counts.items():
                    for lang in self.languages:
                        if name.rstrip("0").endswith(lang):
                            total += num
                            break
        self.word_count = total
        return None

    async def submit_query(self) -> tuple[Job, bool]:
        """
        Helper to submit a query job
        """
        job: Job | SQLJob
        if self.sent_id_offset or not self.send_stats:
            job = Job.fetch(self.previous, connection=self.app["redis"])
            self.job = job
            self.job_id = job.id
            return job, False

        parent: str | None = None
        parent = self.job_id if self.job is not None else None

        # elif self.resuming:
        # parent = self.previous

        query_kwargs = dict(
            original_query=self.query,
            user=self.user,
            room=self.room,
            needed=self.needed,
            total_results_requested=self.total_results_requested,
            done_batches=self.done_batches,
            all_batches=self.all_batches,
            current_batch=self.current_batch,
            total_results_so_far=self.total_results_so_far,
            corpora=self.corpora,
            existing_results=self.existing_results,
            sentences=self.sentences,
            page_size=self.page_size,
            send_stats=self.send_stats,
            post_processes=self.post_processes,
            languages=list(self.languages),
            simultaneous=self.simultaneous,
            total_duration=self.total_duration,
            is_vian=self.is_vian,
            dqd=self.dqd,
            first_job=self.first_job,
            jso=json.dumps(self.jso, indent=4),
            sql=self.sql,
            meta_json=self.meta,
            word_count=self.word_count,
            parent=parent,
        )

        queue = "query" if not self.full else "alt"

        from_memory: bool
        job, from_memory = await self.app["query_service"].query(
            self.sql, depends_on=self.query_depends, queue=queue, **query_kwargs
        )
        self.job = job
        self.job_id = job.id
        self.from_memory = from_memory
        if not self.first_job:
            self.first_job = job.id
        return job, True

    def submit_sents(self) -> list[str]:
        """
        Helper to submit a sentences job
        """
        depends_on = self.job_id if self.job_id else self.previous
        to_use: list[str] | str = []
        if self.simultaneous and depends_on:
            self.dep_chain.append(depends_on)
            to_use = self.dep_chain
        elif depends_on:
            to_use = depends_on

        # needed = self.total_results_requested
        offset = self.sent_id_offset if self.sent_id_offset > 0 else self.cut_short
        # if self.sent_id_offset:
        #    needed = self.needed
        needed = self.needed

        kwargs = dict(
            user=self.user,
            room=self.room,
            resuming=self.resuming,
            from_memory=self.from_memory,
            simultaneous=self.simultaneous,
            first_job=self.first_job or self.job_id,
            dqd=self.dqd,
            jso=json.dumps(self.jso, indent=4),
            sql=self.sql,
            offset=offset,
            needed=needed,
            total_results_requested=self.total_results_requested,
        )
        queue = "query" if not self.full else "alt"
        qs = self.app["query_service"]
        sents_jobs = qs.sentences(
            self.sents_query(), depends_on=to_use, queue=queue, **kwargs
        )
        return sents_jobs

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
        from_memory = manual.get("from_memory", False)
        sentences = manual.get("sentences", True)

        details = {
            "corpora": corpora_to_use,
            "existing_results": manual.get("full_result", manual["result"]),
            "user": manual["user"],
            "room": manual["room"],
            "job": job,
            "app": app,
            "job_id": manual["job"],
            "config": app["config"],
            "full": manual.get("full", False),
            "word_count": manual["word_count"],
            "simultaneous": manual.get("simultaneous", ""),
            "needed": needed,
            "previous": manual.get("previous", ""),  # comment out?
            "page_size": job.kwargs.get("page_size", 20),
            "cut_short": -1,
            "total_results_requested": tot_req,
            "first_job": manual["first_job"],
            "query": job.kwargs["original_query"],
            "sentences": sentences,
            "from_memory": from_memory,
            "total_duration": manual["total_duration"],
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

        if self.done_batches and not self.send_stats:
            self.current_batch = self.done_batches[-1]
            return None

        buffer = 0.1  # set to zero for picking smaller batches

        so_far = self.total_results_so_far
        if self.is_vian:
            if self.done_batches:
                raise ValueError("VIAN corpora have only one batch!?")
            self.current_batch = self.all_batches[0]
            return None

        if not len(self.done_batches):
            self.current_batch = next(
                (x for x in self.all_batches if x[-2].endswith("rest")),
                self.all_batches[0],
            )
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

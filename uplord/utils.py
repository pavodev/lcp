from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys

from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import date, datetime

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Tuple,
    Mapping,
    Set,
)
from uuid import UUID, uuid4

from abstract_query.create import json_to_sql
from aiohttp import web, ClientSession
from rq.command import PUBSUB_CHANNEL_TEMPLATE
from redis import Redis as RedisConnection
from rq.job import Job

from .dqd_parser import convert


PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


if sys.version_info <= (3, 9):
    QI_KWARGS = dict()
else:
    QI_KWARGS = dict(kw_only=True, slots=True)


class Interrupted(Exception):
    """
    Used when a user interrupts a query from frontend
    """

    pass


class CustomEncoder(json.JSONEncoder):
    """
    UUID and time to string
    """

    def default(self, obj: Any):
        if isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def ensure_authorised(func: Callable):
    """
    auth decorator, still wip
    """
    return func

    # todo:
    # @wraps(func)
    # async def deco(request: web.Request, *args, **kwargs):
    #    headers = await _lama_user_details(getattr(request, "headers", request))

    #    if "X-Access-Token" in headers:
    #        token = headers.get("X-Access-Token")
    #        try:
    #            decoded = jwt.decode(
    #                token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"]
    #            )
    #            request.jwt = decoded
    #        except Exception as err:
    #            raise err
    #    if "X-Display-Name" in headers:
    #        username = headers.get("X-Display-Name")
    #        request.username = username
    #    if "X-Mail" in headers:
    #        username = headers.get("X-Mail")
    #        request.username = username

    #    if not request.username:
    #        raise ValueError("401? No username")

    #    return func(request, *args, **kwargs)

    # return deco


def _extract_lama_headers(headers: Mapping) -> Dict[str, str]:
    """
    Create needed headers from existing headers
    """
    retval = {
        "X-API-Key": os.environ["LAMA_API_KEY"],
        "X-Remote-User": headers.get("X-Remote-User"),
        "X-Display-Name": headers["X-Display-Name"].encode("cp1252").decode("utf8")
        if headers.get("X-Display-Name")
        else "",
        "X-Edu-Person-Unique-Id": headers.get("X-Edu-Person-Unique-Id"),
        "X-Home-Organization": headers.get("X-Home-Organization"),
        "X-Schac-Home-Organization": headers.get("X-Schac-Home-Organization"),
        "X-Persistent-Id": headers.get("X-Persistent-Id"),
        "X-Given-Name": headers["X-Given-Name"].encode("cp1252").decode("utf8")
        if headers.get("X-Given-Name")
        else "",
        "X-Surname": headers["X-Surname"].encode("cp1252").decode("utf8")
        if headers.get("X-Surname")
        else "",
        "X-Principal-Name": headers.get("X-Principal-Name"),
        "X-Mail": headers.get("X-Mail"),
        "X-Shib-Identity-Provider": headers.get("X-Shib-Identity-Provider"),
    }
    return {k: v for k, v in retval.items() if v}


def _check_email(email: str) -> bool:
    """
    Is an email address valid?
    """
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return bool(re.fullmatch(regex, email))


def get_user_identifier(headers: Dict[str, Any]) -> str | None:
    """
    Get best possible identifier
    """
    persistent_id = headers.get("X-Persistent-Id")
    persistent_name = headers.get("X-Principal-Name")
    edu_person_unique_id = headers.get("X-Edu-Person-Unique-Id")
    mail = headers.get("X-Mail")

    if persistent_id and bool(re.match("(.*)!(.*)!(.*)", persistent_id)):
        return persistent_id
    elif persistent_name and str(persistent_name).count("@") == 1:
        return persistent_name
    elif edu_person_unique_id and str(edu_person_unique_id).count("@") == 1:
        return edu_person_unique_id
    elif mail and _check_email(mail):
        return mail
    return None


async def _lama_user_details(headers: Mapping[str, Any]) -> Dict[str, Any]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.environ['LAMA_API_URL']}/user/details"
    async with ClientSession() as session:
        async with session.get(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json()


async def _lama_project_create(
    headers: Mapping[str, Any], project_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/profile"
    async with ClientSession() as session:
        async with session.post(url, json=project_data, headers=headers) as resp:
            return await resp.json()


async def _lama_api_create(
    headers: Mapping[str, Any], project_id: str
) -> Dict[str, Any]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/profile/{project_id}/api/create"
    async with ClientSession() as session:
        async with session.post(url, headers=_extract_lama_headers(headers)) as resp:
            return await resp.json(content_type=None)


async def _lama_api_revoke(
    headers: Mapping[str, Any], project_id: str, apikey_id: str
) -> Dict[str, Any]:
    """
    todo: not tested yet, but the syntax is something like this
    """
    url = f"{os.getenv('LAMA_API_URL')}/profile/{project_id}/api/{apikey_id}/revoke"
    data = {"comment": "Revoked by user"}
    async with ClientSession() as session:
        async with session.post(
            url, headers=_extract_lama_headers(headers), json=data
        ) as resp:
            return await resp.json(content_type=None)


async def _lama_check_api_key(headers) -> Dict:
    """
    Get details about a user via their API key
    """
    url = f"{os.environ['LAMA_API_URL']}/profile/api/check"
    key = headers["X-API-Key"]
    secret = headers["X-API-Secret"]
    api_headers = {"X-API-Key": key, "X-API-Secret": secret}
    async with ClientSession() as session:
        async with session.post(url, headers=api_headers) as resp:
            return await resp.json()


def _get_all_results(job: Job | str, connection: RedisConnection) -> Dict[int, Any]:
    """
    Get results from all parents -- reconstruct results from just latest batch
    """
    out: Dict[int, Any] = {}
    if isinstance(job, str):
        job = Job.fetch(job, connection=connection)

    # base = Job.fetch(job.kwargs["base"], connection=connection)
    # latest = Job.fetch(base.meta["latest_sentences"], connection=connection)
    # latest_sents = base.meta["_sentences"]
    # out = _union_results(out, latest_sents)

    while True:
        meta = job.kwargs.get("meta_json")
        batch, _ = _add_results(job.result, 0, True, False, False, 0, meta=meta)
        out = _union_results(out, batch)
        parent = job.kwargs.get("parent", None)
        if not parent:
            break
        job = Job.fetch(parent, connection=connection)
    return out


def _get_kwics(result):
    """
    Helper to get set of kwic ids
    """
    itt = result.get("result_sets", result)
    kwics = [i for i, r in enumerate(itt, start=1) if r.get("type") == "plain"]
    return set(kwics)


def _add_results(
    result: List[Tuple],
    so_far: int,
    unlimited: bool,
    offset: int | None,
    restart: bool | int,
    total_requested: int,
    kwic: bool = False,
    sents: List[Tuple[str | UUID, int, List[Any]]] | None = None,
    meta: Dict[str, List[Dict[str, Any]]] | None = None,
) -> Tuple[Dict[int, Any], int]:
    """
    todo: check limits here?
    """
    bundle: Dict[int, Any] = {}
    counts: Dict[int, int] = defaultdict(int)
    if meta:
        rs = meta["result_sets"]
    else:
        rs = next(i for i in result if not int(i[0]))[1]["result_sets"]

    res_objs = [i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"]
    kwics = set(res_objs)
    n_skipped: Dict[int, int] = Counter()

    if meta:
        bundle[0] = meta

    if sents:
        bundle[-1] = {}
        for sent in sents:
            bundle[-1][str(sent[0])] = [sent[1], sent[2]]

    for x, line in enumerate(result):
        key = int(line[0])
        rest = line[1]
        if not key:
            bundle[key] = rest
            continue

        if key not in bundle:
            if kwic and key in kwics:
                bundle[key] = []
            elif not kwic and key not in kwics:
                bundle[key] = []

        if key in kwics and not kwic:
            counts[key] += 1
            continue
        elif key not in kwics and kwic:
            continue
        elif key not in kwics and not kwic:
            if key not in bundle:
                bundle[key] = [rest]
            else:
                bundle[key].append(rest)
            counts[key] += 1
            continue

        # doing kwics and this is a kwic line
        if not unlimited and offset and n_skipped[key] < offset:
            n_skipped[key] += 1
            continue
        if restart is not False and n_skipped[key] < restart:
            n_skipped[key] += 1
            continue
        if not unlimited and so_far + len(bundle.get(key, [])) >= total_requested:
            continue
        bundle[key].append(rest)
        counts[key] += 1

    for k in kwics:
        if k not in bundle:
            continue
        if len(bundle[k]) > total_requested:
            bundle[k] = bundle[k][:total_requested]

    return bundle, counts[list(kwics)[0]]


def _union_results(so_far: Dict[int, Any], incoming: Dict[int, Any]) -> Dict[int, Any]:
    """
    Join two results objects
    """
    for k, v in incoming.items():
        if not k:
            if k in so_far:
                continue
            else:
                so_far[k] = v
                continue
        elif k == -1:
            if k not in so_far:
                so_far[k] = v
                continue
            else:
                so_far[k].update(v)
        elif k not in so_far:
            so_far[k] = []
        if isinstance(so_far[k], list):
            so_far[k] += v
    return so_far


async def handle_timeout(exc: Exception, request: web.Request) -> None:
    """
    If a job dies due to TTL, we send this...
    """
    request_data = await request.json()
    user = request_data["user"]
    room = request_data["room"]
    job = str(exc).split("rq:job:")[-1]
    jso = {
        "user": user,
        "room": room,
        "error": str(exc),
        "status": "timeout",
        "job": job,
        "action": "timeout",
    }
    logging.warning(f"RQ job timeout: {job}", extra=jso)
    connection = request.app["redis"]
    connection.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _get_status(n_results: int, tot_req: int, **kwargs) -> str:
    """
    Is a query finished, or do we need to do another iteration?
    """
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    if tot_req in {-1, False, None}:
        return "partial"
    if n_results >= tot_req:
        return "satisfied"
    return "partial"


async def sem_coro(semaphore: asyncio.Semaphore, coro: Awaitable[Any]):
    """
    Stop too many tasks from running at once
    """
    async with semaphore:
        return await coro


async def gather(n: int, *tasks: Any, name: str | None = None) -> List[Any]:
    """
    A replacement for asyncio.gather that runs a maximum of n tasks at once.
    If any task errors, we cancel all tasks in the group that share the same name
    """
    if n > 0:
        semaphore = asyncio.Semaphore(n)
        tsks = [asyncio.create_task(sem_coro(semaphore, c), name=name) for c in tasks]
    else:
        tsks = [asyncio.create_task(c, name=name) for c in tasks]
    try:
        return await asyncio.gather(*tsks)
    except (BaseException) as err:
        print(f"Error while gathering tasks: {str(err)}. Cancelling others...")
        running_tasks = asyncio.all_tasks()
        current = asyncio.current_task()
        if current is not None:
            try:
                current.cancel()
            except Exception:
                pass
            name = current.get_name()
            running_tasks.remove(current)
        for task in running_tasks:
            if name is not None and task.get_name() == name:
                task.cancel()
        raise err


@dataclass(**QI_KWARGS)
class QueryIteration:
    """
    Model an iteration of a query, with all its associated settings
    """

    config: Dict[str, Dict[str, Any]]
    user: str
    room: str | None
    query: str
    corpora: List[int]
    all_batches: List[Tuple[int, str, str, int]]
    total_results_requested: int
    needed: int
    page_size: int
    languages: Set[str]
    simultaneous: str
    base: None | str
    sentences: bool
    is_vian: bool
    app: Any  # somehow fails when we do web.Application
    hit_limit: bool | int = False
    resuming: bool = False
    previous: str = ""
    done: bool = False
    request_data: Dict[str, Any] | None = None
    current_batch: Tuple[int, str, str, int] | None = None
    done_batches: List[Tuple[int, str, str, int]] = field(default_factory=list)
    total_results_so_far: int = 0
    existing_results: Dict[int, Any] = field(default_factory=dict)
    job: Job | None = None
    job_id: str | None = ""
    previous_job: Job | None = None
    dqd: str = ""
    sql: str = ""
    jso: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

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

    @classmethod
    async def from_request(cls, request):
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
        sim = request_data.get("simultaneous", False)
        all_batches = _get_query_batches(
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
        Build a query to fetch sentences (uuids to be filled in later)
        """
        if not self.current_batch:
            raise ValueError("Need batch")
        schema = self.current_batch[1]
        lang = self._determine_language(self.current_batch[2])
        config = self.config[str(self.current_batch[0])]
        name = config["segment"].strip()
        underlang = f"_{lang}" if lang else ""
        seg_name = f"prepared_{name}{underlang}"
        script = f"SELECT {name}_id, off_set, content FROM {schema}.{seg_name} "
        end = f"WHERE {name}" + "_id = ANY('{{ {allowed} }}');"
        return script + end

    @classmethod
    async def from_manual(cls, manual, app):

        job = Job.fetch(manual["job"], connection=app["redis"])

        corp = manual["corpora"]
        if not isinstance(corp, list):
            corp = [corp]
        corpora_to_use = [int(i) for i in corp]

        tot_req = manual["total_results_requested"]
        tot_so_far = manual["total_results_so_far"]
        falsey = {False, None, -1}
        needed = tot_req - tot_so_far if tot_req not in falsey else -1

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
            "all_batches": [tuple(x) for x in manual["all_batches"]],
            "total_results_so_far": tot_so_far,
            "languages": set([i.strip() for i in manual.get("languages", [])]),
            "done_batches": [tuple(x) for x in manual["done_batches"]],
            "is_vian": manual.get("is_vian", False),
        }
        return cls(**details)

    def as_dict(self) -> Dict[str, str | List[str] | Dict[Any, Any]]:
        return asdict(self)

    def decide_batch(self) -> None:
        """
        Find the best next batch to query
        """
        if self.current_batch is not None:
            return

        buffer = 0.1  # set to zero for picking smaller batches

        so_far = self.total_results_so_far
        if self.is_vian:
            self.current_batch = self.all_batches[0]
            return None

        if not len(self.done_batches):
            self.current_batch = self.all_batches[0]
            return None

        if self.hit_limit != 0:  # do not change to 'if hit limit!'
            self.current_batch = self.done_batches[-1]
            return None

        total_words_processed_so_far = sum([x[-1] for x in self.done_batches])
        proportion_that_matches = so_far / total_words_processed_so_far
        first_not_done: Tuple[int, str, str, int] | None = None

        for batch in self.all_batches:
            if batch in self.done_batches:
                continue
            if not first_not_done:
                first_not_done = batch
                if self.needed in {-1, False, None}:
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


def _get_query_batches(
    corpora: List[int], config: Dict[str, Dict], languages: Set[str], is_vian: bool
) -> List[Tuple[int, str, str, int]]:
    """
    Get a list of tuples in the format of (corpus, batch, size) to be queried
    """
    out: List[Tuple[int, str, str, int]] = []
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


async def push_msg(
    sockets: Dict[str, Set[Tuple[Any, str]]],
    session_id: str,
    msg: Dict[str, Any],
    skip: Tuple[str, str] | None = None,
    just: Tuple[str, str] | None = None,
) -> None:
    """
    Send JSON websocket message to one or more users
    """
    sent_to = set()
    for room, users in sockets.items():
        if room != session_id:
            continue
        for conn, user_id in users:
            if (room, user_id) in sent_to:
                continue
            if skip and (room, user_id) == skip:
                continue
            if just and (room, user_id) != just:
                continue
            try:
                await conn.send_json(msg)
            except ConnectionResetError:
                print(f"Connection reset: {room}/{user_id}")
                pass
            sent_to.add((room, user_id))


def _get_word_count(qi: QueryIteration) -> int:
    """
    Sum the word counts for corpora being searched
    """
    total = 0
    for corpus in qi.corpora:
        conf = qi.app["config"][str(corpus)]
        try:
            has_partitions = "partitions" in conf["mapping"]["layer"][conf["token"]]
        except (KeyError, TypeError):
            has_partitions = False
        if not has_partitions or not qi.languages:
            total += sum(conf["token_counts"].values())
        else:
            counts = conf["token_counts"]
            for name, num in counts.items():
                for lang in qi.languages:
                    if name.rstrip("0").endswith(lang):
                        total += num
                        break
    return total

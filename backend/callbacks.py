import json

from collections import defaultdict

from .configure import _get_batches
from .utils import CustomEncoder, Interrupted, _add_results, _get_kwics, _union_results
from datetime import datetime
from rq.command import PUBSUB_CHANNEL_TEMPLATE
from rq.connections import Connection
from rq.job import Job
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type, Union

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


def _query(
    job: Job, connection: Connection, result: List[List], *args, **kwargs
) -> None:
    """
    Job callback, publishes a redis message containing the results
    """
    restart = kwargs.get("hit_limit", False)
    total_before_now = job.kwargs.get("total_results_so_far")
    results_so_far = job.kwargs.get("existing_results", {})
    # lines_sent_to_fe = set()
    results_so_far = {int(k): v for k, v in results_so_far.items()}
    results_this_batch = len([i for i in result if int(i[0]) == 1])
    total_found = total_before_now + results_this_batch
    total_requested = (
        job.kwargs["total_results_requested"]
        if restart is False
        else kwargs["total_results_requested"]
    )
    current_batch = job.kwargs["current_batch"]
    done_part = job.kwargs["done_batches"]
    # this seemed to be wrong:
    # offset = job.kwargs.get("offset", False) if restart is False else False
    offset = restart if restart is not False else False

    if restart is False:
        needed = job.kwargs["needed"]
    else:
        needed = total_requested - total_before_now

    unlimited = needed in {-1, False, None} or job.kwargs.get("simultaneous", False)

    limited = not unlimited and total_found > job.kwargs["needed"]

    aargs = (
        result,
        total_before_now,
        unlimited,
        offset,
        restart,
        total_requested,
    )

    new_res, n_results = _add_results(*aargs, kwic=False)
    results_so_far = _union_results(results_so_far, new_res)

    # kwics = _get_kwics(results_so_far[0])
    # for k in kwics:
    #    for line in results_so_far.get(k, []):
    #        ids = [i for i in line if isinstance(i, (str, int))]
    #        ids = sorted(ids)
    #        lines_sent_to_fe.add(tuple(ids))
    # add everything: _add_results(result, 0, True, False, False, 0)

    just_finished = job.kwargs["current_batch"]
    job.kwargs["done_batches"].append(just_finished)

    status = _get_status(total_found, **job.kwargs)
    hit_limit = False if not limited else needed
    job.meta["_status"] = status
    job.meta["hit_limit"] = hit_limit
    job.meta["total_results_so_far"] = total_found
    # the +1 could be wrong, maybe hit_limit should be -1?
    job.meta["start_at"] = 0 if restart is False else restart
    job.meta["_args"] = aargs[1:]
    job.meta["result_sets"] = results_so_far[0]
    # job.meta["lines_sent_to_fe"] = lines_sent_to_fe
    # job.meta["all_results"] = results_so_far

    if status == "finished":
        projected_results = total_found
        perc_words = 100.0
        perc_matches = 100.0
        job.meta["percentage_done"] = 100.0
    elif status in {"partial", "satisfied"}:
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([x[-1] for x in done_batches])
        proportion_that_matches = total_found / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
        perc_words = total_words_processed_so_far * 100.0 / job.kwargs["word_count"]
        perc_matches = min(total_found, total_requested) * 100.0 / total_requested
        job.meta["percentage_done"] = round(perc_matches, 3)
        # todo: can remove this for more accuracy if need be
        if total_requested < total_found:
            total_found = total_requested

    job.save_meta()
    jso = dict(**job.kwargs)
    jso.update(
        {
            "result": results_so_far,
            "status": status,
            "job": job.id,
            "projected_results": projected_results,
            "percentage_done": round(perc_matches, 3),
            "percentage_words_done": round(perc_words, 3),
            "hit_limit": hit_limit,
            "total_results_so_far": total_found,
            "batch_matches": n_results,
            "sentences": job.kwargs["sentences"],
            "total_results_requested": total_requested,
        }
    )

    redis = job._redis if restart is False else connection

    redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _sentences(
    job: Job,
    connection: Connection,
    result: List[Tuple[str, int, List[Any]]],
    *args,
    **kwargs,
) -> None:

    base = Job.fetch(job.kwargs["base"], connection=connection)
    if "_sentences" not in base.meta:
        base.meta["_sentences"] = {}

    depends_on = job.kwargs["depends_on"]
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]

    depended = Job.fetch(depends_on, connection=connection)
    aargs: Tuple[int, bool, Optional[int], Union[int, bool], int] = depended.meta[
        "_args"
    ]

    new_res, _ = _add_results(depended.result, *aargs, kwic=True, sents=result)
    results_so_far = _union_results(base.meta["_sentences"], new_res)

    base.meta["latest_sentences"] = job.id
    base.meta["_sentences"] = results_so_far

    base.save_meta()

    jso = {
        "result": results_so_far,
        "status": depended.meta["_status"],
        "action": "sentences",
        "user": job.kwargs["user"],
        "room": job.kwargs["room"],
        "query": depended.id,
        "base": base.id,
        "percentage_done": round(depended.meta["percentage_done"], 3),
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _schema(job: Job, connection: Connection, result: Any, *args, **kwargs) -> None:
    """
    This callback is executed after successful creation of schema.
    We might want to notify some WS user?
    """
    print(f"Schema created: {job.id}")
    return


def _general_failure(
    job: Job,
    connection: Connection,
    typ: Type,
    value: str,
    traceback: TracebackType,
    *args,
    **kwargs,
) -> None:
    """
    On job failure, return some info ... probably hide some of this from prod eventually!
    """
    print("Failure of some kind:", job, traceback, typ, value)
    if isinstance(typ, Interrupted) or typ == Interrupted:
        # jso = {"status": "interrupted", "job": job.id, **kwargs, **job.kwargs}
        return  # do we need to send this?
    else:
        jso = {
            "status": "failed",
            "kind": str(typ),
            "value": str(value),
            "traceback": str(traceback),
            "job": job.id,
            **kwargs,
            **job.kwargs,
        }
    # this is just for consistency with the other timeout messages
    if "No such job" in jso["value"]:
        jso["status"] = "timeout"
        jso["action"] = "timeout"
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _upload(job: Job, connection: Connection, result, *args, **kwargs) -> None:
    """
    Success callback when user has uploaded a dataset
    """
    user = job.kwargs["user"]
    room = job.kwargs.get("room")
    if not user and not room:
        return
    jso = {
        "user": user,
        "status": "success" if result else "unknown",
        "project": job.kwargs["project"],
        "action": "uploaded",
        "gui": job.kwargs["gui"],
        "config": job.kwargs["config"],
        "room": room,
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _queries(
    job: Job,
    connection: Connection,
    result: Optional[List[Tuple[str, Dict, str, Optional[str], datetime]]],
    *args,
    **kwargs,
) -> None:
    is_store = job.kwargs.get("store")
    action = "store_query" if is_store else "fetch_queries"
    room = str(job.kwargs["room"]) if job.kwargs["room"] else None
    jso: Dict[str, Any] = {
        "user": str(job.kwargs["user"]),
        "room": room,
        "status": "success",
        "action": action,
        "queries": [],
    }
    if is_store:
        jso["query_id"] = str(job.kwargs["query_id"])
        jso.pop("queries")
    elif result:
        cols = ["idx", "query", "username", "room", "created_at"]
        queries: List[Dict[str, Any]] = []
        for x in result:
            dct: Dict[str, Any] = dict(zip(cols, x))
            queries.append(dct)
        jso["queries"] = queries
    made = json.dumps(jso, cls=CustomEncoder)
    job._redis.publish(PUBSUB_CHANNEL, made)


def _config(job: Job, connection: Connection, result, *args, **kwargs) -> None:
    """
    Run by worker: make config data
    """
    fixed: Dict[int, Dict] = {-1: {}}
    for tup in result:
        (
            corpus_id,
            name,
            current_version,
            version_history,
            description,
            corpus_template,
            schema_path,
            token_counts,
            mapping,
        ) = tup
        ver = str(current_version)
        schema_path = schema_path.replace("<version>", ver)
        if not schema_path.endswith(ver):
            schema_path = f"{schema_path}{ver}"
        rest = {
            "shortname": name,
            "corpus_id": int(corpus_id),
            "current_version": int(ver) if ver.isnumeric() else ver,
            "version_history": version_history,
            "description": description,
            "schema_path": schema_path,
            "token_counts": token_counts,
            "mapping": mapping,
        }
        corpus_template.update(rest)

        fixed[int(corpus_id)] = corpus_template

    for name, conf in fixed.items():
        if name == -1:
            continue
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    jso = {"config": fixed, "_is_config": True, "action": "set_config"}

    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _get_status(n_results: int, **kwargs) -> str:
    """
    Is a query finished, or do we need to do another iteration?
    """
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    requested = kwargs["total_results_requested"]
    if requested in {-1, False, None}:
        return "partial"
    if n_results >= requested:
        return "satisfied"
    return "partial"

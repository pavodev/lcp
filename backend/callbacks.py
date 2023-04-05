import json

from .configure import _get_batches
from .utils import CustomEncoder, Interrupted, _add_results
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
    results_so_far = job.kwargs.get("existing_results", [])
    total_found = len(results_so_far) + len(result)
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
        needed = total_requested - len(results_so_far)

    unlimited = needed in {-1, False, None} or job.kwargs.get("simultaneous", False)

    limited = not unlimited and len(result) > job.kwargs["needed"]

    args = (result, len(results_so_far), unlimited, offset, restart, total_requested)

    results_so_far += _add_results(*args)
    # add everything: _add_results(result, 0, True, False, False, 0)

    just_finished = job.kwargs["current_batch"]
    job.kwargs["done_batches"].append(just_finished)

    status = _get_status(results_so_far, **job.kwargs)
    hit_limit = False if not limited else needed
    job.meta["_status"] = status
    job.meta["hit_limit"] = hit_limit
    job.meta["total_results"] = len(results_so_far)
    # the +1 could be wrong, maybe hit_limit should be -1?
    job.meta["start_at"] = 0 if restart is False else restart
    # job.meta["all_results"] = results_so_far
    job.save_meta()
    if status == "finished":
        projected_results = len(results_so_far)
        perc_words = 100.0
        perc_matches = 100.0
    elif status in {"partial", "satisfied"}:
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([x[-1] for x in done_batches])
        proportion_that_matches = total_found / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
        perc_words = total_words_processed_so_far * 100.0 / job.kwargs["word_count"]
        perc_matches = total_found * 100.0 / total_requested
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
            "batch_matches": len(result),
            "stats": job.kwargs["stats"],
            "total_results_requested": total_requested,
        }
    )

    redis = job._redis if restart is False else connection

    redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _stats(
    job: Job,
    connection: Connection,
    result: Dict[Union[str, Tuple[str]], int],
    *args,
    **kwargs,
) -> None:

    base = Job.fetch(job.kwargs["base"], connection=connection)
    if "_stats" not in base.meta:
        base.meta["_stats"] = {}

    for r, v in result.items():
        if r in base.meta["_stats"]:
            base.meta["_stats"][r] += v
        else:
            base.meta["_stats"][r] = v

    base.meta["latest_stats"] = job.id

    base.save_meta()

    depends_on = job.kwargs["depends_on"]
    if isinstance(depends_on, list):
        depends_on = depends_on[-1]

    depended = Job.fetch(depends_on, connection=connection)

    jso = {
        "result": base.meta["_stats"],
        "status": depended.meta["_status"],
        "action": "stats",
        "user": job.kwargs["user"],
        "room": job.kwargs["room"],
        # "current_batch": list(job.kwargs["current_batch"]),
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


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
    print("FAILURE", job, traceback, typ, value)
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
    jso = {
        "user": job.kwargs["user"],
        "status": "success" if result else "unknown",
        "corpus_id": job.kwargs["corpus_id"],
        "action": "uploaded",
        "gui": job.kwargs["gui"],
        "config": job.kwargs["config"],
        "room": job.kwargs["room"],
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

    # fixed["open_subtitles_en1"] = fixed["open_subtitles_en"]
    # fixed["sparcling1"] = fixed["sparcling"]

    jso = {"config": fixed, "_is_config": True, "action": "set_config"}

    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _get_status(results_so_far: List[List], **kwargs) -> str:
    """
    Is a query finished, or do we need to do another iteration?
    """
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    requested = kwargs["total_results_requested"]
    if requested in {-1, False, None}:
        return "partial"
    if len(results_so_far) >= requested:
        return "satisfied"
    return "partial"

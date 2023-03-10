import json

from rq.command import PUBSUB_CHANNEL_TEMPLATE
from rq.job import Job
from .configure import _get_batches
from .utils import CustomEncoder, Interrupted

PUBSUB_CHANNEL = PUBSUB_CHANNEL_TEMPLATE % "query"


def _query(job, connection, result, *args, **kwargs):
    """
    Job callback, publishes a redis message containing the results
    """
    results_so_far = job.kwargs.get("existing_results", [])
    total_found = len(results_so_far) + len(result)
    total_requested = job.kwargs["total_results_requested"]
    current_batch = job.kwargs["current_batch"]
    done_part = job.kwargs["done_batches"]

    unlimited = job.kwargs["needed"] in {0, -1, False, None}

    limited = not unlimited and len(result) >= job.kwargs["needed"]

    for res in result:
        # fix: move sent_id to own column
        fixed = []
        sent_id = res[0][0]
        tok_ids = res[0][1:]
        fixed = ((sent_id,), tuple(tok_ids), res[1])
        # end fix
        results_so_far.append(fixed)
        if not unlimited and len(results_so_far) >= total_requested:
            break

    just_finished = job.kwargs["current_batch"]
    job.kwargs["done_batches"].append(just_finished)

    status = _get_status(results_so_far, **job.kwargs)
    job.meta["_status"] = status
    job.save_meta()
    if status == "finished":
        projected_results = len(results_so_far)
        perc = 100.0
    elif status in {"partial", "satisfied"}:
        done_batches = job.kwargs["done_batches"]
        total_words_processed_so_far = sum([x[-1] for x in done_batches])
        proportion_that_matches = total_found / total_words_processed_so_far
        projected_results = int(job.kwargs["word_count"] * proportion_that_matches)
        perc = total_words_processed_so_far * 100.0 / job.kwargs["word_count"]
    jso = {
        "result": results_so_far,
        "status": status,
        "job": job.id,
        "projected_results": projected_results,
        "percentage_done": round(perc, 3),
        "hit_limit": False if not limited else job.kwargs["needed"],
        "batch_matches": len(result),
        "stats": job.kwargs["stats"],
        **kwargs,
        **job.kwargs,
    }

    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _stats(job, connection, result, *args, **kwargs):

    base = Job.fetch(job.kwargs["base"], connection=connection)
    if "_stats" not in base.meta:
        base.meta["_stats"] = {}
    for r, v in result.items():
        if r in base.meta["_stats"]:
            base.meta["_stats"][r] += v
        else:
            base.meta["_stats"][r] = v

    base.save_meta()

    depended = Job.fetch(job.kwargs["depends_on"], connection=connection)

    jso = {
        "result": base.meta["_stats"],
        "status": depended.meta["_status"],
        "action": "stats",
        "user": job.kwargs["user"],
        "room": job.kwargs["room"],
        # "current_batch": list(job.kwargs["current_batch"]),
    }
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _general_failure(job, connection, typ, value, traceback, *args, **kwargs):
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
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _upload(job, connection, result, *args, **kwargs):
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


def _queries(job, connection, result, *args, **kwargs):
    is_store = job.kwargs.get("store")
    action = "store_query" if is_store else "fetch_queries"
    room = str(job.kwargs["room"]) if job.kwargs["room"] else None
    jso = {
        "user": str(job.kwargs["user"]),
        "room": room,
        "status": "success",
        "action": action,
    }
    if is_store:
        jso["query_id"] = str(job.kwargs["query_id"])
    else:
        cols = ["idx", "query", "username", "room", "created_at"]
        jso["queries"] = [dict(zip(cols, x)) for x in result]
    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _config(job, connection, result, *args, **kwargs):
    """
    Run by worker: make config data
    """
    fixed = {}
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
        rest = {
            "shortname": name,
            "corpus_id": int(corpus_id),
            "current_version": current_version,
            "version_history": version_history,
            "description": description,
            "schema_path": schema_path
            if schema_path.endswith("1")
            else f"{schema_path}1",
            "token_counts": token_counts,
            "mapping": mapping,
        }
        corpus_template.update(rest)

        fixed[int(corpus_id)] = corpus_template

    for name, conf in fixed.items():
        if "_batches" not in conf:
            conf["_batches"] = _get_batches(conf)

    fixed["_uploads"] = {}

    # fixed["open_subtitles_en1"] = fixed["open_subtitles_en"]
    # fixed["sparcling1"] = fixed["sparcling"]

    jso = {"config": fixed, "_is_config": True, "action": "set_config"}

    job._redis.publish(PUBSUB_CHANNEL, json.dumps(jso, cls=CustomEncoder))


def _get_status(results_so_far, **kwargs):
    """
    Is a query finished, or do we need to do another iteration?
    """
    if len(kwargs["done_batches"]) == len(kwargs["all_batches"]):
        return "finished"
    requested = kwargs["total_results_requested"]
    if requested in {0, -1, False, None}:
        return "partial"
    if len(results_so_far) >= requested:
        return "satisfied"
    return "partial"

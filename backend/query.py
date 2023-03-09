import json


from aiohttp import web
from rq.job import Job

from abstract_query.abstract_query import Query
from abstract_query.lcp_query import LCPQuery

from . import utils


def _get_word_count(corpora, config, languages):
    """
    Sum the word counts for corpora being searched
    """
    total = 0
    for corpus in corpora:
        conf = config[str(corpus)]
        has_partitions = "partitions" in conf["mapping"]["layer"]["Token"]
        if not has_partitions or not languages:
            total += sum(conf["token_counts"].values())
        else:
            counts = conf["token_counts"]
            for name, num in counts.items():
                for lang in languages:
                    if name.rstrip("0").endswith(lang):
                        total += num
                        break
    return total


def _decide_batch(
    done_batches, batches, n_results_so_far, needed_to_go, hit_limit, page_size
):
    """
    Find the best next batch to query
    """
    buffer = 0.1  # set to zero for picking smaller batches
    if not done_batches:
        # return next(b for b in batches if not b[1].endswith("rest"))
        return batches[0]
    if hit_limit:
        return done_batches[-1]
    if needed_to_go in {0, -1, False, None}:
        return next(
            p
            for p in batches
            if tuple(p) not in done_batches and list(p) not in done_batches
        )
    total_words_processed_so_far = sum([x[-1] for x in done_batches])
    proportion_that_matches = n_results_so_far / total_words_processed_so_far
    for schema, corpus, name, size in batches:
        if (schema, corpus, name, size) in done_batches or [
            schema,
            corpus,
            name,
            size,
        ] in done_batches:
            continue
        # should we do this? next-smallest for low number of matches?
        if not n_results_so_far or n_results_so_far < page_size:
            return (schema, corpus, name, size)
        expected = size * proportion_that_matches
        if n_results_so_far + expected >= (needed_to_go + (needed_to_go * buffer)):
            return (schema, corpus, name, size)
    return next(
        p
        for p in reversed(batches)
        if tuple(p) not in done_batches and list(p) not in done_batches
    )


def _get_query_batches(corpora, config, languages):
    """
    Get a list of tuples in the format of (corpus, batch, size) to be queried
    """
    out = []
    all_languages = ["en", "de", "fr", "ca"]
    for corpus in corpora:
        batches = config[str(corpus)]["_batches"]
        # config[corpus]['layer']['Token@en'] -- use this to determine languages?
        for name, size in batches.items():
            stripped = name.rstrip("0123456789")
            if stripped.endswith("rest"):
                stripped = stripped[:-4]
            if not stripped.endswith(
                tuple([f"_{l}" for l in languages])
            ) and stripped.endswith(tuple([f"_{l}" for l in all_languages])):
                continue
            schema = config[str(corpus)]["schema_path"]
            out.append((corpus, schema, name, size))
    return sorted(out, key=lambda x: x[-1])


@utils.ensure_authorised
async def query(request, manual=None, app=None):
    """
    Here we get the corpora and the search criteria, generate a JSON query, which gets submitted to query service

    POST data should contain `corpora` and `query`, room and user_id also allowed

    This endpoint can be manually triggered for queries over multiple batches. When
    that happpens, manual is a dict with the needed data and the app is passed in as a kwarg.
    """
    # manual means the request doesn't come from the frontend, but from the run.py file...
    if manual is not None:
        job = Job.fetch(manual["job"], connection=app["redis"])
        user = manual.get("user")
        room = manual.get("room")
        languages = set([i.strip() for i in manual.get("languages")])

        # done_batches = manual["done_batches"]
        # all_batches = manual["all_batches"]

        previous_batch = job.kwargs["current_batch"]
        done_batches = job.kwargs["done_batches"]
        done_batches.append(previous_batch)
        all_batches = job.kwargs["all_batches"]

        corpora_to_use = [int(i) for i in manual["corpora"]]
        existing_results = manual["result"]
        # todo: user may have changed page size ... try get it from ws message first?
        page_size = job.kwargs.get("page_size", 20)

        query = job.kwargs["original_query"]
        n_results_so_far = len(existing_results)
        total_results_requested = manual["total_results_requested"]
        unlimited = {0, -1, False, None}
        needed_to_go = (
            total_results_requested - n_results_so_far
            if total_results_requested not in unlimited
            else -1
        )
        config = manual["config"]
        hit_limit = manual.get("hit_limit")
    else:
        # request is from the frontend, most likely a new query
        hit_limit = False
        done_batches = []
        app = request.app
        config = request.app["config"]
        request_data = await request.json()
        corpora_to_use = [int(i) for i in request_data["corpora"]]
        query = request_data["query"]
        room = request_data.get("room")
        page_size = request_data.get("page_size", 10)
        user = request_data.get("user")
        languages = set([i.strip() for i in request_data.get("languages", ["en"])])
        total_results_requested = request_data.get("total_results_requested", 10000)
        existing_results = []
        n_results_so_far = 0
        all_batches = _get_query_batches(corpora_to_use, config, languages)
        needed_to_go = total_results_requested

    sql_query = query
    word_count = _get_word_count(corpora_to_use, config, languages)

    current_batch = _decide_batch(
        done_batches, all_batches, n_results_so_far, needed_to_go, hit_limit, page_size
    )

    offset = None if not hit_limit else hit_limit

    if "SELECT" not in query.upper():
        try:
            kwa = dict(
                corpus=current_batch[1],
                batch=current_batch[2],
                # limit=needed_to_go,
                config=app["config"][str(current_batch[0])],
                # offset=offset,
            )
            sql_query = LCPQuery(query, **kwa).sql
        except Exception as err:
            print("SQL GENERATION FAILED! for dev, assuming script passed", err)
            raise err

    if manual is None:
        print(f"QUERY:\n\n\n{sql_query}\n\n\n")

    qs = app["query_service"]
    query_kwargs = dict(
        query=sql_query,
        user=user,
        original_query=query,
        room=room,
        needed=needed_to_go,
        total_results_requested=total_results_requested,
        done_batches=done_batches,
        current_batch=current_batch,
        all_batches=all_batches,
        corpora=corpora_to_use,
        existing_results=existing_results,
        word_count=word_count,
        page_size=page_size,
        languages=list(languages),
    )
    job = qs.submit(kwargs=query_kwargs)

    print(f"\nNow querying: {current_batch[1]}.{current_batch[2]} ... {job.id}")

    jobs = {"status": "started", "job": job.id}
    return web.json_response(jobs)

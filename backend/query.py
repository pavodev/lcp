import json

from aiohttp import web

from abstract_query.abstract_query import Query
from abstract_query.lcp_query import LCPQuery

from . import utils


def _get_word_count(corpora, config):
    """
    Sum the word counts for corpora being searched
    """
    total = 0
    for corpus in corpora:
        total += sum(config[corpus]["token_counts"].values())
    return total


def _decide_batch(corpora, done_batches, batches, n_results_so_far, needed_results):
    """
    Find the best next batch to query
    """
    if not done_batches:
        return batches[0]
    total_words_processed_so_far = sum([s for c, n, s in done_batches])
    proportion_that_matches = n_results_so_far / total_words_processed_so_far
    for corpus, name, size in batches:
        if (corpus, name, size) in done_batches or [
            corpus,
            name,
            size,
        ] in done_batches:
            continue
        expected = size * proportion_that_matches
        if n_results_so_far + expected >= needed_results:
            return (corpus, name, size)
    return next(
        p
        for p in reversed(batches)
        if tuple(p) not in done_batches and list(p) not in done_batches
    )


def _get_query_batches(corpora, config):
    """
    Get a list of tuples in the format of (corpus, batch, size) to be queried
    """
    out = []
    for corpus in corpora:
        batches = config[corpus]["_batches"]
        for name, size in batches.items():
            out.append((corpus, name, size))
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
        user = manual.get("user")
        room = manual.get("room")
        done_batches = manual["done_batches"]
        needed_results = manual.get("needed")
        corpora_to_use = manual["corpora"]
        existing_results = manual["result"]
        all_batches = manual["all_batches"]
        query = manual["original_query"]
        n_results_so_far = len(existing_results)
        config = manual["config"]
    else:
        # request is from the frontend, most likely a new query
        done_batches = []
        app = request.app
        config = request.app["config"]
        request_data = await request.json()
        corpora_to_use = request_data["corpora"]
        query = request_data["query"]
        room = request_data.get("room")
        user = request_data.get("user")
        needed_results = request_data.get("needed", 100)
        existing_results = []
        n_results_so_far = 0
        all_batches = _get_query_batches(corpora_to_use, config)

    sql_query = query
    word_count = _get_word_count(corpora_to_use, config)

    current_batch = _decide_batch(
        corpora_to_use,
        done_batches,
        all_batches,
        n_results_so_far,
        needed_results,
    )

    if "SELECT" not in query.upper():
        try:
            kwa = dict(
                corpus=current_batch[0],
                batch=current_batch[1],
                limit=needed_results,
                config=app["config"][current_batch[0]],
            )
            sql_query = LCPQuery(query, **kwa).sql
        except:
            print("SQL GENERATION FAILED! for dev, assuming script passed")
            raise

    print(f"QUERY:\n\n\n{sql_query}\n\n\n")

    qs = app["query_service"]
    query_kwargs = dict(
        query=sql_query,
        user=user,
        original_query=query,
        room=room,
        needed=needed_results,
        done_batches=done_batches,
        current_batch=current_batch,
        all_batches=all_batches,
        corpora=corpora_to_use,
        existing_results=existing_results,
        word_count=word_count,
    )
    job = qs.submit(kwargs=query_kwargs)
    jobs = {"status": "started", "job": job.id}
    return web.json_response(jobs)

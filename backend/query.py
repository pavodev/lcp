import json

from aiohttp import web

from abstract_query.abstract_query import Query

from . import utils


def _get_partitions(corpora, config):
    """
    Get a list of partitions to search and their sizes
    """
    partitions = []
    for corpus in corpora:
        for part, size in config[corpus]["partitions"].items():
            partitions.append((corpus, part.strip(), size))
    return sorted(partitions, key=lambda x: x[-1])


def _get_word_count(corpora, config):
    """
    Sum the word counts for corpora being searched
    """
    total = 0
    for corpus in corpora:
        total += config[corpus].get("word_count", 0)
    return total


def _decide_partition(
    corpora, done_partitions, partitions, n_results_so_far, needed_results
):
    """
    Find the best next partition to query
    """
    if not done_partitions:
        return partitions[0]
    total_words_processed_so_far = sum([s for c, n, s in done_partitions])
    proportion_that_matches = n_results_so_far / total_words_processed_so_far
    for corpus, name, size in partitions:
        if (corpus, name, size) in done_partitions or [
            corpus,
            name,
            size,
        ] in done_partitions:
            continue
        expected = size * proportion_that_matches
        if n_results_so_far + expected >= needed_results:
            return (corpus, name, size)
    return next(
        p
        for p in reversed(partitions)
        if tuple(p) not in done_partitions and list(p) not in done_partitions
    )


@utils.ensure_authorised
async def query(request, manual=None, app=None):
    """
    Here we get the corpora and the search criteria, generate a JSON query, which gets submitted to query service

    POST data should contain `corpora` and `query`, room and user_id also allowed
    """
    # manual means the request doesn't come from the frontend, but from the run.py file...
    if manual is not None:
        user = manual.get("user")
        room = manual.get("room")
        done_partitions = manual["done_partitions"]
        needed_results = manual.get("needed")
        corpora_to_use = manual["corpora"]
        existing_results = manual["result"]
        all_partitions = manual["all_partitions"]
        query = manual["original_query"]
        n_results_so_far = len(existing_results)
        config = manual["config"]
    else:
        # request is from the frontend, most likely a new query
        done_partitions = []
        app = request.app
        config = request.app["config"]
        request_data = await request.json()
        corpora_to_use = request_data["corpora"]
        query = request_data["query"]
        room = request_data.get("room")
        user = request_data.get("user")
        needed_results = request_data.get("needed", 20)
        existing_results = []
        n_results_so_far = 0
        all_partitions = _get_partitions(corpora_to_use, config)

    sql_query = query
    word_count = _get_word_count(corpora_to_use, config)

    current_partition = _decide_partition(
        corpora_to_use,
        done_partitions,
        all_partitions,
        n_results_so_far,
        needed_results,
    )

    if "SELECT" not in query.upper():
        try:
            kwa = dict(corpus=current_partition[0], partition=current_partition[1])
            sql_query = Query(query, **kwa).sql
        except:
            print("SQL GENERATION FAILED! for dev, assuming script passed")
            raise

    # print(f"QUERY:\n\n\n{sql_query}")

    qs = app["query_service"]
    query_kwargs = dict(
        query=sql_query,
        user=user,
        original_query=query,
        room=room,
        needed=needed_results,
        done_partitions=done_partitions,
        current_partition=current_partition,
        all_partitions=all_partitions,
        corpora=corpora_to_use,
        existing_results=existing_results,
        word_count=word_count,
    )
    job = qs.submit(kwargs=query_kwargs)
    jobs = {"status": "started", "job": job.id}
    return web.json_response(jobs)

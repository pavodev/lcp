import json
import os

from typing import Any, Dict, List, Optional, Set, Tuple, Union

from aiohttp import web
from rq.job import Job

from abstract_query.create import json_to_sql

from . import utils
from .callbacks import _query
from .dqd_parser import convert
from .utils import _determine_language
from uuid import uuid4


def _make_sents_query(
    query: str, schema: str, config: Dict, lang: Optional[str]
) -> str:
    """
    Build a query to fetch sentences (uuids to be filled in later)
    """
    underlang = f"_{lang}" if lang else ""
    seg_name = f"prepared_segment{underlang}"
    script = f"SELECT segment_id, off_set, content FROM {schema}.{seg_name} "
    end = "WHERE segment_id = ANY('{{ {allowed} }}');"
    return script + end


def _get_word_count(
    corpora: List[int], config: Dict[str, Dict], languages: Set[str]
) -> int:
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
    done_batches: List[Union[Tuple[int, str, str, int], List[Any]]],
    batches: List[Union[Tuple[int, str, str, int], List[Any]]],
    so_far: int,
    needed: int,
    hit_limit: Union[bool, int],
    page_size: int,
) -> Union[Tuple[int, str, str, int], List[Any]]:
    """
    Find the best next batch to query
    """
    buffer = 0.1  # set to zero for picking smaller batches
    if not done_batches:
        # return next(b for b in batches if not b[1].endswith("rest"))
        return batches[0]
    if hit_limit:
        return done_batches[-1]
    if needed in {-1, False, None}:
        return next(
            p
            for p in batches
            if tuple(p) not in done_batches and list(p) not in done_batches
        )
    total_words_processed_so_far = sum([x[-1] for x in done_batches])
    proportion_that_matches = so_far / total_words_processed_so_far
    for schema, corpus, name, size in batches:
        if (schema, corpus, name, size) in done_batches or [
            schema,
            corpus,
            name,
            size,
        ] in done_batches:
            continue
        # should we do this? next-smallest for low number of matches?
        if not so_far or so_far < page_size:
            return (schema, corpus, name, size)
        expected = size * proportion_that_matches
        if so_far + expected >= (needed + (needed * buffer)):
            return (schema, corpus, name, size)
    return next(
        p
        for p in reversed(batches)
        if tuple(p) not in done_batches and list(p) not in done_batches
    )


def _get_query_batches(
    corpora: List[int], config: Dict[str, Dict], languages: Set[str]
) -> List[Tuple]:
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


async def _do_resume(
    request_data: Dict,
    app: web.Application,
    previous: Optional[str],
    total_results_requested: Optional[int],
) -> Tuple[bool, Tuple[Any, Any, Any, Any]]:
    """
    Resume a query!
    """
    prev_job = Job.fetch(previous, connection=app["redis"])
    hit_limit = prev_job.meta.get("hit_limit", 0)
    if hit_limit:
        base = prev_job.kwargs.get("base", prev_job.id)
        _query(
            prev_job,
            app["redis"],
            prev_job.result,
            hit_limit=hit_limit,
            total_results_requested=request_data["total_results_requested"],
        )
        current_batch = prev_job.kwargs["current_batch"]
        return True, (current_batch, prev_job, None, None)
    else:
        all_batches = prev_job.kwargs["all_batches"]
        done_batches = prev_job.kwargs["done_batches"]
        so_far = prev_job.meta["total_results"]
        needed = (
            total_results_requested - so_far
            if total_results_requested not in {-1, False, None}
            else -1
        )
        previous_batch = prev_job.kwargs["current_batch"]
        done_batches.append(previous_batch)
        return False, (
            all_batches,
            done_batches,
            so_far,
            needed,
        )


@utils.ensure_authorised
async def query(
    request: web.Request,
    manual: Optional[Dict] = None,
    app: Optional[web.Application] = None,
) -> web.Response:
    """
    Generate and queue up queries

    This endpoint can be manually triggered for queries over multiple batches. When
    that happpens, manual is a dict with the needed data and the app is passed in
    as a kwarg.
    """
    ###########################################################################
    # request doesn't come from frontend, but from the run.py file            #
    ###########################################################################
    unlimited = {-1, False, None}
    simultaneous: Optional[str] = None
    previous: Optional[str] = None
    if manual is not None and isinstance(app, web.Application):
        resuming = False
        job = Job.fetch(manual["job"], connection=app["redis"])
        base = manual["base"]
        existing_results = manual["result"]
        config = manual["config"]
        total_results_requested = manual["total_results_requested"]
        total_results_so_far = manual["total_results_so_far"]
        user = manual["user"]
        corpora_to_use = [int(i) for i in manual["corpora"]]
        room = manual.get("room")
        sentences = manual.get("sentences", True)
        hit_limit = manual.get("hit_limit", False)
        languages = set([i.strip() for i in manual.get("languages", [])])
        query = job.kwargs["original_query"]
        page_size = job.kwargs.get("page_size", 20)  # todo: user may change
        previous_batch = job.kwargs["current_batch"]
        done_batches = job.kwargs["done_batches"]
        all_batches = job.kwargs["all_batches"]
        done_batches.append(previous_batch)
        needed = (
            total_results_requested - total_results_so_far
            if total_results_requested not in unlimited
            else -1
        )
    else:
        #######################################################################
        # request is from the frontend, most likely a new query...            #
        #######################################################################
        done_batches = []
        existing_results = {}
        hit_limit = False
        job = False
        total_results_so_far = 0
        app = request.app
        config = request.app["config"]
        request_data = await request.json()
        corpora_to_use = [int(i) for i in request_data["corpora"]]
        query = request_data["query"]
        room = request_data.get("room")
        previous = request_data.get("previous")
        resuming = request_data.get("resume", False)
        sentences = request_data.get("sentences", True)
        page_size = request_data.get("page_size", 10)
        user = request_data.get("user")
        languages = set([i.strip() for i in request_data.get("languages", ["en"])])
        total_results_requested = request_data.get("total_results_requested", 10000)
        is_simultaneous = request_data.get("simultaneous", False)
        simultaneous = str(uuid4()) if is_simultaneous else None
        base = None if not resuming else previous
        all_batches = _get_query_batches(corpora_to_use, config, languages)
        needed = total_results_requested

    ############################################################################
    # prepare for query iterations (just one if not simultaneous mode)         #
    ############################################################################

    iterations = len(all_batches) if simultaneous else 1
    http_response = []
    current_batch = None
    first_job = None
    depends_on_chain = []
    max_jobs = int(os.getenv("MAX_SIMULTANEOUS_JOBS_PER_USER", -1))
    query_depends: List[str] = []
    qs = app["query_service"]

    print("\n\n\n\nTHE QUERY", query, "\n\n\n")

    for i in range(iterations):

        done = False

        ########################################################################
        # handle resumed queries                                               #
        ########################################################################

        if resuming:
            rargs = (request_data, app, previous, total_results_requested)
            done, r = await _do_resume(*rargs)

            if not done and len(r) == 4:
                all_batches, done_batches, total_results_so_far, needed = r
                existing_results = utils._get_all_results(
                    previous, connection=app["redis"]
                )
            else:
                current_batch, prev_job, _, _ = r

        #######################################################################
        # build new query sql (not needed if resuming a queried batch)        #
        #######################################################################

        if not done:

            word_count = _get_word_count(corpora_to_use, config, languages)

            if current_batch is None:
                current_batch = _decide_batch(
                    done_batches,
                    all_batches,
                    total_results_so_far,
                    needed,
                    hit_limit,
                    page_size,
                )

            try:
                lang = _determine_language(current_batch[2])
                kwa = dict(
                    schema=current_batch[1],
                    batch=current_batch[2],
                    config=app["config"][str(current_batch[0])],
                    lang=lang,
                )
                query_type = "JSON"
                # sql_query = json_to_sql(json.loads(query), **kwa)

                try:
                    json_query = json.loads(query)
                except json.JSONDecodeError as err:
                    json_query = convert(query)
                    query_type = "DQD"
                print(f"Detected query type: {query_type}")
                sql_query = json_to_sql(json_query, **kwa)
            except Exception as err:
                print("SQL GENERATION FAILED! for dev, assuming script passed", err)
                raise err

            ###################################################################
            # organise and submit query to rq via query service               #
            ###################################################################

            if manual is None and not resuming and not i:
                print(f"QUERY:\n\n\n{sql_query}\n\n\n")

            if manual is not None:
                parent = job.id
            elif resuming:
                parent = previous
            else:
                parent = None

            query_kwargs = dict(
                query=sql_query,
                user=user,
                original_query=query,
                room=room,
                needed=needed,
                total_results_requested=total_results_requested,
                done_batches=done_batches,
                current_batch=current_batch,
                all_batches=all_batches,
                total_results_so_far=total_results_so_far,
                corpora=corpora_to_use,
                base=base,
                existing_results=existing_results,
                word_count=word_count,
                sentences=sentences,
                offset=hit_limit,
                page_size=page_size,
                languages=list(languages),
                parent=parent,
                simultaneous=simultaneous,
            )

            job = qs.query(depends_on=query_depends, kwargs=query_kwargs)

            ###################################################################
            # simultaneous query setup for next iteration                     #
            ###################################################################

            # still figuring this out a little bit
            divv = (i + 1) % max_jobs if max_jobs else -1
            if simultaneous and i and max_jobs and max_jobs != -1 and not divv:
                query_depends.append(job.id)

            if current_batch is not None:
                print(
                    f"\nNow querying: {current_batch[1]}.{current_batch[2]} ... {job.id}"
                )

            if simultaneous and not i:
                first_job = job

        #######################################################################
        # prepare and submit sentences query                                  #
        #######################################################################

        if sentences and current_batch:
            sect = config[str(current_batch[0])]
            lang = _determine_language(current_batch[2])
            sents_query = _make_sents_query(query, current_batch[1], sect, lang)
            if simultaneous and first_job:
                the_base = first_job.id
            elif resuming and done:
                the_base = prev_job.kwargs.get("base", prev_job.id)
            else:
                the_base = job.id if base is None else base
            sents_kwargs = dict(
                user=user,
                room=room,
                current_batch=current_batch,
                query=sents_query,
                base=the_base,
                resuming=done,
                simultaneous=simultaneous,
            )
            depends_on = job.id if not done else previous
            if simultaneous:
                depends_on_chain.append(depends_on)
                to_use = depends_on_chain
            else:
                to_use = depends_on
            sents_job = qs.sentences(depends_on=to_use, kwargs=sents_kwargs)
            # if simultaneous:
            #    depends_on_chain.append(stats_job.id)

        #######################################################################
        # prepare for next iteration if need be, and return http response     #
        #######################################################################

        jobs = {"status": "started", "job": job.id if job else previous}

        if sentences:
            jobs.update({"sentences": True, "sentences_job": sents_job.id})

        if simultaneous:
            done_batches.append(current_batch)
            current_batch = None

        http_response.append(jobs)

    if simultaneous:
        return web.json_response(http_response)
    else:
        return web.json_response(http_response[0])

"""
Functions used in the conversion of SQL to JSON results

The role of these functions is to work together to create the Results
object, which holds kwic, collocation and frequency results, plus query
metadata and prepared_segment objects.

If a query has res1=kwic, res2=collocation, res3=freq, two objects would
be created. First, the non-kwic data would be made by _aggregate_results
via callbacks._query:

{0: query_metadata, 2: collocation_data, 3: freq_data}

and after that, _format_kwics via callbacks._sentences would produce:

{-1: prepared_segment_data, 0: query_metadata, 1: kwic_data}

the dicts could therefore be combined without losing any info if need be

Once non-kwic results are created, they need to be filtered with _apply_filters
so that certain transformations not possible to do in SQL can be applied.
Most commonly, this is when there is a "frequency > 10" type filter: we cannot
apply it in postgres because a given match could have 5 matches in one batch,
and 5 in another...

KWIC results need the results of queries over the prepared_segment table, which
is inserted as the -1 key in the Results object. FE does the job of formatting
the kwic line from matching token ids plus the relevant prepared_segment.
"""

import operator

from collections import defaultdict
from collections.abc import Sequence
from typing import Any, cast

from redis import Redis as RedisConnection
from rq.job import Job

from .typed import QueryMeta, RawSent, ResultSents, Results
from .utils import _get_associated_query_job

OPS = {
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "==": operator.eq,
    "<>": operator.ne,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
}


def _aggregate_results(
    result: list[list],
    existing: Results,
    meta_json: QueryMeta,
    post_processes: dict[int, Any],
) -> tuple[Results, Results, int, bool, bool]:
    """
    Combine non-kwic results for storing and for sending to frontend
    """
    results_to_send: Results = {0: meta_json}
    n_results = 0
    rs = meta_json["result_sets"]
    kwics = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"])
    freqs = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "analysis"])
    counts: defaultdict[int, int] = defaultdict(int)

    for line in result:
        key = int(line[0])
        rest: list[Any] = line[1]
        if not key and not n_results:
            n_results = rest[0]
            continue
        if key in kwics:
            counts[key] += 1
            continue
        if key not in existing:
            existing[key] = []
        if key not in freqs:
            current = cast(list, existing[key])
            current.append(rest)
            continue
        body = cast(list, rest[:-1])
        total_this_batch = rest[-1]
        preexist = sum(i[-1] for i in cast(list, existing[key]) if i[:-1] == body)
        combined = preexist + total_this_batch
        counts[key] = combined
        existing[key] = [i for i in cast(list, existing[key]) if i[:-1] != body]
        body.append(combined)
        cast(list, existing[key]).append(body)

    results_to_send = _apply_filters(existing, post_processes)

    show_total = bool(kwics) or (not kwics and len(freqs) == 1)

    return existing, results_to_send, n_results, not bool(kwics), show_total


def _format_kwics(
    result: list | None,
    meta_json: QueryMeta,
    sents: list[RawSent] | None,
    total: int,
    is_vian: bool,
    is_first: bool,
    offset: int,
    max_kwic: int,
    current_lines: int,
    full: bool,
) -> Results:
    """
    Take a DB query result, plus `sents`, the result of the query on the
    prepared_segment table, and create the data needed by frontend to display
    KWIC lines.

    {0: meta_json, -1: {sent_id: [sent_offset, sent_data]}, 1: [token_ids, ...]}

    For VIAN, the token_ids also include document_id, gesture info, etc.

    Often we don't want all the sentences, we use `offset` and `total` to get
    only a certain subset of them...
    """
    sen: ResultSents = {}
    out: Results = {0: meta_json, -1: sen}
    first_list: int | None = None
    rs: list[dict] = meta_json["result_sets"]
    kwics = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"])
    counts: defaultdict[int, int] = defaultdict(int)
    stops: set[int] = set()
    skipped: defaultdict[int, int] = defaultdict(int)

    if sents is None:
        print("Sentences is None: expired?")
        sents = []

    if result is None:
        print("Result is None: expired?")
        result = []

    for sent in sents:
        add_to = cast(ResultSents, out[-1])
        add_to[str(sent[0])] = [sent[1], sent[2]]

    for line in result:
        key = int(line[0])
        rest = line[1]
        if max_kwic and counts.get(key, 0) > max_kwic:
            continue
        # we should have one 0: n_results key always
        if not key:
            continue
        if key not in kwics:
            continue
        if key in stops:
            continue
        if total is not None and total > 0 and counts[key] >= total:
            stops.add(key)
            continue
        if offset is not None and offset > 0 and skipped[key] < offset:
            skipped[key] += 1
            continue
        if key not in out:
            out[key] = []
        if is_vian and key in kwics:
            first_list = _first_list(first_list, rest)
            rest = list(_format_vian(rest, first_list))
        elif key in kwics:
            rest = [rest[0], rest[1:]]
            # fix for vian inside lcp:
            if any(isinstance(i, list) for i in rest[1]):
                rest = [rest[0], rest[1][:-7]]
        if str(rest[0]) not in out[-1]:
            continue
        bit = cast(list, out[key])
        bit.append(rest)
        counts[key] += 1

    if max_kwic and not full:
        out = _limit_kwic_to_max(out, current_lines, max_kwic)

    return out


def _get_all_sents(
    job: Job,
    base: Job,
    is_vian: bool,
    meta_json: QueryMeta,
    max_kwic: int,
    current_lines: int,
    full: bool,
    connection: RedisConnection,
) -> Results:
    """
    Combine all sent jobs into one -- only done at the end of a `full` query
    """
    sen: ResultSents = {}
    out: Results = {0: meta_json, -1: sen}
    is_first = True
    got: Results
    for jid in base.meta["_sent_jobs"]:
        j = job if job.id == jid else Job.fetch(jid, connection=connection)
        dep = _get_associated_query_job(j.kwargs["depends_on"], connection)
        resume = j.kwargs.get("resume", False)
        offset = j.kwargs.get("offset", 0) if resume else -1
        needed = j.kwargs.get("needed", -1)
        got = _format_kwics(
            dep.result,
            meta_json,
            j.result,
            needed,
            is_vian,
            is_first,
            offset,
            0,
            0,
            full,
        )
        if got.get(-1):
            sents = cast(dict, out[-1])
            sents.update(cast(dict, got[-1]))
        for k, v in got.items():
            if k < 1:
                continue
            if k not in out:
                out[k] = []
            add_to = cast(list, out[k])
            add_to += cast(list, v)

    if max_kwic > 0:
        out = _limit_kwic_to_max(out, current_lines, max_kwic)

    return out


def _format_vian(
    rest: Sequence, first_list: int
) -> tuple[int | str, list[int], int | str, str | None, str | None, list[list[int]]]:
    """
    Little helper to build VIAN kwic sentence data, which has time,
    document and gesture information added to the KWIC data
    """
    seg_id = cast(str | int, rest[0])
    tok_ids = cast(list[int], rest[1 : first_list - 3])
    gesture = cast(str | None, rest[first_list - 2])
    doc_id = cast(int | str, rest[first_list - 3])
    agent_name = cast(str | None, rest[first_list - 1])
    frame_ranges = cast(list[list[int]], rest[first_list:])
    out = (seg_id, tok_ids, doc_id, gesture, agent_name, frame_ranges)
    return out


def _limit_kwic_to_max(to_send: Results, current_lines: int, max_kwic: int) -> Results:
    """
    Do not allow too many KWIC results to go to FE
    """
    too_many = False
    allowed: set[str | int] = set()
    for k, v in to_send.items():
        if k > 0:
            size = len(v)
            if size + current_lines > max_kwic:
                most_allowed = max_kwic - current_lines
                if not too_many and len(v) > most_allowed:
                    too_many = True
                assert isinstance(to_send[k], list)
                to_send[k] = cast(list, v)[:most_allowed]
                allowed.update(set(i[0] for i in cast(list, to_send[k])))
    if too_many:
        to_send[-1] = {k: v for k, v in cast(dict, to_send[-1]).items() if k in allowed}

    return to_send


def _make_filters(
    post: dict[int, list[dict[str, Any]]]
) -> dict[int, list[tuple[str, str, str | int | float]]]:
    """
    Because we iterate over them a lot, turn the filters object into something
    as performant as possible
    """
    out = {}
    for idx, filters in post.items():
        fixed: list[tuple[str, str, str | int | float]] = []
        for filt in filters:
            name, comp = cast(tuple[str, str], list(filt.items())[0])
            if name != "comparison":
                raise ValueError("expected comparion")

            bits: Sequence[str | int | float] = comp.split()
            last_bit = cast(str, bits[-1])
            body = bits[:-1]
            assert isinstance(body, list)
            if last_bit.isnumeric():
                body.append(int(last_bit))
            elif last_bit.replace(".", "").isnumeric():
                body.append(float(last_bit))
            else:
                body = bits
            made = cast(tuple[str, str, int | str | float], tuple(body))
            fixed.append(made)
        out[idx] = fixed
    return out


def _apply_filters(results_so_far: Results, post_processes: dict[int, Any]) -> Results:
    """
    Take the unioned results and apply any post process functions
    """
    if not post_processes:
        return results_so_far
    out: Results = {}
    post = _make_filters(post_processes)
    for k, v in results_so_far.items():
        for key, filters in post.items():
            if not filters:
                continue
            if int(k) < 1:
                continue
            if int(k) != int(key):
                continue
            for name, op, num in filters:
                v = _apply_filter(cast(list, v), name, op, num)
        out[k] = v
    return out


def _apply_filter(result: list, name: str, op: str, num: int | str | float) -> list:
    """
    Apply a single filter to a group of results, returning only those that match
    """
    out: list = []
    for r in result:
        total = r[-1]
        res = OPS[op](total, num)
        if res and r not in out:
            out.append(r)
    return out


def _fix_freq(v: list[list]) -> list[list]:
    """
    Sum frequency objects and remove duplicate
    """
    fixed = []
    for r in v:
        body = r[:-1]
        total = sum(x[-1] for x in v if x[:-1] == body)
        body.append(total)
        if body not in fixed:
            fixed.append(body)
    return fixed


def _first_list(first_list: int | None, rest: list) -> int:
    """
    Determine the first list item in a vian kwic item
    """
    if first_list is not None:
        return first_list
    return next(
        (i for i, x in enumerate(rest) if isinstance(x, (list, tuple))),
        len(rest),
    )

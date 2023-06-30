"""
Functions used in the conversion of SQL to JSON results
"""
import operator

from collections import defaultdict
from collections.abc import Sequence
from typing import Any, cast

from .typed import QueryMeta, ResultSents, Results


OPS = {
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "==": operator.eq,
    "<>": operator.ne,
    "!=": operator.ne,
    ">": operator.ge,
    ">=": operator.gt,
}


def _aggregate_results(
    result: list,
    existing: Results,
    meta_json: QueryMeta,
    post_processes: dict[int, Any],
) -> tuple[Results, Results, int, bool, bool]:
    """
    Combine non-kwic results for storing and for sending to frontend
    """
    # all_results = {0: meta_json}
    results_to_send = {0: meta_json}
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
            existing[key].append(rest)
            continue
        body = rest[:-1]
        total_this_batch = rest[-1]
        preexist = sum(i[-1] for i in existing[key] if i[:-1] == body)
        combined = preexist + total_this_batch
        counts[key] = combined
        existing[key] = [i for i in existing[key] if i[:-1] != body]
        body.append(combined)
        existing[key].append(body)

    results_to_send = _apply_filters(existing, post_processes)

    show_total = bool(kwics) or (not kwics and len(freqs) == 1)

    return existing, results_to_send, n_results, not bool(kwics), show_total


def _format_kwics(
    result: list,
    meta_json: QueryMeta,
    sents: list,
    total: int,
    is_vian: bool = False,
    is_first: bool = False,
    offset: int = -1,
) -> Results:

    sen: ResultSents = {}
    out: Results = {0: meta_json, -1: sen}
    first_list: int | None = None
    rs: list[dict] = meta_json["result_sets"]
    kwics = set([i for i, r in enumerate(rs, start=1) if r.get("type") == "plain"])
    counts: defaultdict[int, int] = defaultdict(int)
    stops: set[int] = set()

    for sent in sents:
        add_to = cast(ResultSents, out[-1])
        add_to[str(sent[0])] = [sent[1], sent[2]]

    for line in result:
        key = int(line[0])
        rest = line[1]
        if key not in kwics:
            continue
        if is_first and key in stops:
            continue
        if total is not None and total > 0 and counts.get(key, 0) >= total:
            stops.add(key)
            continue
        if key not in out:
            out[key] = []

        counts[key] += 1

        if offset is not None and offset > 0 and counts[key] - 1 < offset:
            continue

        if is_vian and key in kwics:
            first_list = _first_list(first_list, rest)
            rest = list(_format_vian(rest, first_list))
        elif key in kwics:
            rest = [rest[0], rest[1:]]

        bit = cast(list, out[key])
        bit.append(rest)

    return out


def _format_vian(
    rest: Sequence, first_list: int
) -> tuple[int | str, list[int], int | str, str | None, str | None, list[list[int]]]:
    """
    Little helper to build VIAN kwic sentence data
    """
    seg_id = cast(str | int, rest[0])
    tok_ids = cast(list[int], rest[1 : first_list - 3])
    gesture = cast(str | None, rest[first_list - 2])
    doc_id = cast(int | str, rest[first_list - 3])
    agent_name = cast(str | None, rest[first_list - 1])
    frame_ranges = cast(list[list[int]], rest[first_list:])
    out = (seg_id, tok_ids, doc_id, gesture, agent_name, frame_ranges)
    return out


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

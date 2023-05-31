from __future__ import annotations

import json
import os
import sys

from collections.abc import Iterable
from typing import Any, ClassVar

from lark import Lark
from lark.indenter import Indenter
from lark.lexer import Token


dqd_grammar = r"""
    ?start: _NL* [predicate+]

    predicate       : "Token"scope? label? _NL [_INDENT (property|predicate)+ _DEDENT]  -> token
                    | "Segment"scope? label? _NL                                        -> segment
                    | "DepRel" label? _NL [_INDENT property+ _DEDENT]                   -> deprel
                    | "Turn" label? _NL [_INDENT property+ _DEDENT]                     -> turn
                    | "sequence"scope? label? _NL [_INDENT predicate+ _DEDENT]          -> sequence
                    | "set" label? _NL [_INDENT predicate+ _DEDENT]                     -> set
                    | label "=> plain" _NL [_INDENT r_plain_prop+ _DEDENT]              -> results_plain
                    | label "=> analysis" _NL [_INDENT r_analysis_prop+ _DEDENT]        -> results_analysis
                    | label "=> collocation" _NL [_INDENT r_coll_prop+ _DEDENT]         -> results_collocation
    property        : VARIABLE OPERATOR STRING _NL                                      -> property
    repeat_loop     : /[\d+\*](\.\.[\d+\-\*])?/                                         -> loop
    label           : VARIABLE                                                          -> label
    scope           : "@"VARIABLE                                                       -> scope
    result_variable : VARIABLE _NL
    r_plain_prop    : "context" _NL [_INDENT (label _NL) _DEDENT]                       -> result_plain_context
                    | "entities" _NL [_INDENT (label _NL)+ _DEDENT]                     -> result_plain_entities
    r_analysis_prop : "attributes" _NL [_INDENT (STRING _NL)+ _DEDENT]                  -> result_analysis_attributes
                    | "functions" _NL [_INDENT (STRING _NL)+ _DEDENT]                   -> result_analysis_functions
                    | "filter" _NL [_INDENT (STRING _NL)+ _DEDENT]                      -> result_analysis_filter
    r_coll_prop     : "center" _NL [_INDENT (STRING _NL)+ _DEDENT]                      -> result_coll_center
                    | "window" _NL [_INDENT (STRING _NL)+ _DEDENT]                      -> result_coll_window
                    | "attribute" _NL [_INDENT (STRING _NL)+ _DEDENT]                   -> result_coll_attribute
                    | "space" _NL [_INDENT (STRING _NL)+ _DEDENT]                       -> result_coll_space
                    | "comment" _NL [_INDENT (STRING _NL)+ _DEDENT]                     -> result_coll_comment

    VARIABLE        : /[a-zA-Z_][a-zA-Z0-9_\.]*/
    OPERATOR        : /(<>|<|>|!=|~|¬|¬=|¬~|<=|>=|=|!)/
    STRING          : /[^\n\r ].*/
    SL_COMMENT      : /#[^\r\n]+/ _NL
    DL_COMMENT      : /<#(>|#*[^#>]+)*#+>/ _NL

    %import common.CNAME                                                                    -> NAME
    %import common.WS_INLINE
    %declare _INDENT _DEDENT
    %ignore WS_INLINE
    %ignore SL_COMMENT
    %ignore DL_COMMENT

    _NL: /(\r?\n[\t ]*)+/
"""


class TreeIndenter(Indenter):
    NL_type: str = "_NL"
    INDENT_type: str = "_INDENT"
    DEDENT_type: str = "_DEDENT"
    tab_len: int = 8
    OPEN_PAREN_types: ClassVar[list[str]] = []
    CLOSE_PAREN_types: ClassVar[list[str]] = []
    # this fixes mypy but not sure if it breaks anything:
    always_accept: Iterable[str] = ()


parser = Lark(dqd_grammar, parser="lalr", postlex=TreeIndenter())


def merge_constraints(constraints: list[dict[str, Any]]) -> dict[str, Any]:
    retval = {}
    if len(constraints) == 1 and len(constraints[0]) > 1:
        retval = {"constraints": {**constraints[0]}}
    elif len(constraints) == 1:
        retval = constraints[0]
    elif len(constraints) > 1:
        retval = {
            "constraints": {
                "operator": "AND",
                "args": [
                    (
                        constraint.get("constraints")
                        if len(constraint) == 1 and "constraints" in constraint
                        else constraint
                    )
                    for constraint in constraints
                ],
            }
        }
    return retval


def merge_filter(filters: list[dict]) -> dict[str, Any] | str:
    if len(filters) == 1:
        res: dict = filters[0]
        return res
    elif len(filters) > 1:
        return {"filters": {"operator": "AND", "args": filters}}
    return {}


def to_dict(tree: Any) -> Any:
    if isinstance(tree, Token):
        return tree.value

    if tree.data == "start":
        children = [to_dict(child) for child in tree.children]
        return {
            "$schema": "cobquec2.json",
            "query": [child for child in children if "results" not in child],
            "results": [
                child.get("results") for child in children if "results" in child
            ],
        }

    elif tree.data in ("sequence"):
        children = [to_dict(child) for child in tree.children]
        others = [child for child in children if child.get("layer") is None]
        members = [child for child in children if child.get("layer") is not None]
        return {
            tree.data: {
                **(
                    {k: v for child in others for k, v in child.items()}
                    if others
                    else {}
                ),
                "members": members,
            }
        }

    elif tree.data in ("set"):
        children = [to_dict(child) for child in tree.children]
        others = [child for child in children if child.get("layer") is None]
        constraints = merge_constraints(
            [child for child in children if child.get("layer") is not None]
        )
        return {
            tree.data: {
                **(
                    {k: v for child in others for k, v in child.items()}
                    if others
                    else {}
                ),
                **constraints,
            }
        }

    elif tree.data in ("turn", "token", "segment", "deprel"):
        children = [to_dict(child) for child in tree.children]
        constraints = merge_constraints(
            [child for child in children if "constraints" in child]
        )
        others = [child for child in children if "constraints" not in child]
        layer = (
            "DepRel"
            if tree.data == "deprel"
            else f"{tree.data[0].upper()}{tree.data[1:]}"
        )
        return {
            "layer": layer,
            **({k: v for child in others for k, v in child.items()} if others else {}),
            **constraints,
        }
    elif tree.data == "property":
        return {
            "constraints": {
                "comparison": " ".join([to_dict(child) for child in tree.children])
            }
        }
    elif tree.data == "label":
        return {"label": str(tree.children[0])}
    elif tree.data == "scope":
        return {"partOf": str(tree.children[0])}

    # Results
    elif tree.data == "results_plain":
        children = [to_dict(child) for child in tree.children]
        return {
            "results": {
                "plain": {
                    **(
                        {k: v for child in children for k, v in child.items()}
                        if children
                        else {}
                    ),
                }
            }
        }

    elif tree.data == "result_plain_context":
        name = tree.data.split("_")[2]
        children = [to_dict(child) for child in tree.children]
        return {name: children[0].get("label")}

    elif tree.data == "result_plain_entities":
        name = tree.data.split("_")[2]
        children = [to_dict(child) for child in tree.children]
        return {name: [child.get("label") for child in children]}

    elif tree.data == "results_analysis":
        children = [to_dict(child) for child in tree.children]
        return {
            "results": {
                "statAnalysis": {
                    **(
                        {k: v for child in children for k, v in child.items()}
                        if children
                        else {}
                    ),
                }
            }
        }

    elif tree.data in ("result_analysis_attributes", "result_analysis_functions"):
        name = tree.data.split("_")[2]
        children = [to_dict(child) for child in tree.children]
        return {name: children}

    elif tree.data in ("result_analysis_filter"):
        name = tree.data.split("_")[2]
        children = [to_dict(child) for child in tree.children]
        return {name: {"comparison": merge_filter(children)}}

    elif tree.data == "results_collocation":
        children = [to_dict(child) for child in tree.children]
        return {
            "results": {
                "collAnalysis": {
                    **(
                        {k: v for child in children for k, v in child.items()}
                        if children
                        else {}
                    ),
                }
            }
        }

    elif tree.data in (
        "result_coll_center",
        "result_coll_window",
        "result_coll_attribute",
        "result_coll_comment",
    ):
        name = tree.data.split("_")[2]
        children = [to_dict(child) for child in tree.children]
        return {name: children[0]}

    elif tree.data in ("result_coll_space"):
        name = tree.data.split("_")[2]
        children = [to_dict(child) for child in tree.children]
        return {name: children}


def convert(dqd_query: str) -> dict[str, Any]:
    data = parser.parse(dqd_query)
    res: dict = to_dict(data)
    return res


def cmdline() -> None:
    if os.path.isfile(sys.argv[-1]):
        with open(sys.argv[-1], "r") as fo:
            dqd = fo.read()
    else:
        dqd = sys.argv[-1]
    print(json.dumps(convert(dqd), indent=4))


if __name__ == "__main__":
    cmdline()

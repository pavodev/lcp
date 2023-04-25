import lark
import sys

from lark import Lark
from lark.indenter import Indenter


dqd_grammar = r"""
    ?start: _NL* [predicate+]

    predicate       : "Token"scope? label? _NL [_INDENT (property|predicate)+ _DEDENT]        -> token
                    | "Segment"scope? label? _NL                                        -> segment
                    | "DepRel" label? _NL [_INDENT property+ _DEDENT]                   -> deprel
                    | "Turn" label? _NL [_INDENT property+ _DEDENT]                     -> turn
                    | "sequence"scope? label? _NL [_INDENT predicate+ _DEDENT]          -> sequence
                    | "repeat" repeat_loop label? _NL [_INDENT predicate+ _DEDENT]      -> repeat
                    | "intersect" label? _NL [_INDENT (NAME _NL)+ _DEDENT]              -> intersect
                    | "group" label? _NL [_INDENT (NAME _NL)+ _DEDENT]                  -> group
                    | "all" label? "(" VARIABLE ")" _NL [_INDENT predicate+ _DEDENT]    -> all
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
    NL_type = "_NL"
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 8


parser = Lark(dqd_grammar, parser="lalr", postlex=TreeIndenter())


def tree_to_json(item, write=None):
    """Writes a Lark tree as a JSON dictionary."""
    if write is None:
        write = sys.stdout.write
    _tree_to_json(item, write, 0)


def _tree_to_json(item, write, level):
    indent = "  " * level
    level += 1
    if isinstance(item, lark.Tree):
        write(f'{indent}{{ "type": "{item.data}", "children": [\n')
        sep = ""
        for child in item.children:
            write(indent)
            write(sep)
            _tree_to_json(child, write, level)
            sep = ",\n"
        write(f"{indent}] }}\n")
    elif isinstance(item, lark.Token):
        # reminder: Lark Tokens are directly strings
        # token attrs include: line, end_line, column, end_column, pos_in_stream, end_pos
        write(
            f'{indent}{{ "type": "{item.type}", "text": "{item}", "line": {item.line}, "col": {item.column} }}\n'
        )
    else:
        assert False, item  # fall-through


def merge_constraints(constraints):
    retval = {}
    if len(constraints) == 1 and len(constraints[0].keys()) > 1:
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
                        if len(constraint.keys()) == 1
                        and "constraints" in constraint.keys()
                        else constraint
                    )
                    for constraint in constraints
                ],
            }
        }
    return retval


def merge_filter(filters):
    retval = {}
    if len(filters) == 1:
        retval = filters[0]
    elif len(filters) > 1:
        retval = {"filters": {"operator": "AND", "args": filters}}
    return retval


def to_dict(tree):
    if isinstance(tree, lark.lexer.Token):
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

    elif tree.data in ("sequence", "set"):
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
    # elif tree.data == 'all':
    #     return {
    #         "all": str(tree.children[0])
    #     }
    # elif tree.data == 'intersect':
    #     return {
    #         "intersect": str(tree.children[0])
    #     }
    # elif tree.data == 'group':
    #     return {
    #         "group": str(tree.children[0])
    #     }
    # elif tree.data == 'repeat':
    #     return {
    #         "repeat": str(tree.children[0])
    #     }

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


def convert(dqd_query):
    data = parser.parse(dqd_query)
    return to_dict(data)

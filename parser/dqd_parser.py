from __future__ import annotations

import json
import os
import re
import sys

from collections.abc import Iterable
from typing import Any, ClassVar

from lark import Lark
from lark.indenter import Indenter
from lark.lexer import Token


dqd_grammar = open("test_grammar.lark").read()

json_schema = json.loads(open("cobquec.auto.json").read())


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


def merge_filter(filters: list[dict[str, Any] | str]) -> dict[str, Any] | str:
    if len(filters) == 1:
        res: dict[str, Any] | str = filters[0]
        return res
    elif len(filters) > 1:
        return {"filters": {"operator": "AND", "args": filters}}
    return {}


def to_dict(tree: Any, schema_entry: dict={}) -> Any:
    
    if isinstance(tree, Token):
        return tree.value
    if len(tree.children) == 1 and isinstance(tree.children[0], Token):
        return tree.children[0].value
    
    
    named_children = dict()
    
    for child in tree.children:
        
        if isinstance(child, Token): continue
        
        child_name: str = child.data
        if child_name == "comparison":  # This is hard-coded, but it could be automated by looking up all the keys in schema_entry
            child_name = "constraints"  # and using the one that references child_name down the tree instead
        
        schema_entry = schema_entry.get("items", schema_entry)
        if "$ref" in schema_entry:
            schema_entry = json_schema.get("$defs",{}).get(re.sub(r".+\/","",schema_entry['$ref'])).get("properties", {})
        
        child_schema_entry = schema_entry.get(child_name, {})
        
        child_dict = to_dict(child, child_schema_entry)
        
        child_name = re.sub("__.*", "", child_name)
        child_name = re.sub("_([a-z])", lambda x: x[1].upper(), child_name)
        if child_name in named_children:
            if not isinstance(named_children[child_name],list):
                named_children[child_name] = [named_children[child_name]]
            named_children[child_name].append(child_dict)
        else:
            named_children[child_name] = child_dict
            
    return named_children    


def convert(dqd_query: str) -> dict[str, Any]:
    data = parser.parse(dqd_query)
    res: dict = to_dict(data, json_schema.get('properties',{}))
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

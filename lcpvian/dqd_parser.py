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

PARSER_PATH = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'parser'))

dqd_grammar_fn: str = next((os.path.join(PARSER_PATH,f) for f in sorted(os.listdir(PARSER_PATH)) if f.endswith(".lark")), "")
assert os.path.isfile(
    dqd_grammar_fn
), f"Could not find a valid lark file in the current directory"
dqd_grammar: str = open(dqd_grammar_fn).read()

json_schema_fn: str = next((os.path.join(PARSER_PATH,f) for f in sorted(os.listdir(PARSER_PATH)) if f.endswith(".json")), "")
assert os.path.isfile(
    json_schema_fn
), f"Could not find a valid json file in the current directory"
json_schema: dict = json.loads(open(json_schema_fn).read())

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


def to_camel(name: str) -> str:
    name = re.sub("__.*", "", name)
    name = re.sub("_([a-z])", lambda x: x[1].upper(), name)
    return name


def forward(schema: dict) -> tuple[dict, bool]:
    if "items" in schema:
        return forward(schema["items"])[0], True
    if "$ref" in schema:
        return forward( json_schema.get("$defs", {}).get(re.sub(r".+\/", "", schema["$ref"])) )
    
    if "oneOf" in schema:
        schema["properties"] = schema.get("properties", {})
        for o in schema["oneOf"]:
            f, _ = forward(o)
            schema["properties"] = {**schema["properties"], **f.get("properties",{})}
        
    return (schema, False)


def found_rule_down_the_line(property_schema: dict = {}, rule: str = "") -> bool:
    if "items" in property_schema:
        property_schema = property_schema["items"]

    if "$ref" not in property_schema and "oneOf" in property_schema:
        for o in property_schema["oneOf"]:
            found_in_one_of = found_rule_down_the_line(o, rule)
            if found_in_one_of:
                return True

    if "$ref" in property_schema:
        rule_ref = re.sub(r".+\/", "", property_schema.get("$ref", ""))
        if rule_ref == rule:
            return True
        elif rule_ref in json_schema.get("$defs", {}):
            return found_rule_down_the_line(json_schema["$defs"][rule_ref], rule)

    return False


def to_dict(tree: Any, properties_parent: dict = {}) -> Any:
    if isinstance(tree, Token):
        return tree.value

    name: str = tree.data
    camel_name: str = to_camel(name)
    
    schema, is_parent_array = forward(
        properties_parent.get(camel_name, properties_parent)
    )

    if schema.get("type", "") == "string" and not is_parent_array:
        assert (
            len(tree.children) == 1
        ), f"{camel_name} is a string but it has more than one child {tree.pretty()}"
        if isinstance(tree.children[0], Token):
            return tree.children[0].value
        elif isinstance(tree.children[0].children[0], Token):
            return tree.children[0].children[0].value
        else:
            assert (
                False
            ), f"Couldn't find a string for {camel_name} even going two levels deep {tree.pretty()}"

    children_properties = schema.get("properties", schema)

    values: Any = dict()
    skip_children_names = False
    for child in tree.children:
        if isinstance(child, Token):
            continue

        # Init some variables
        child_schema = schema
        is_child_array = is_parent_array

        child_name = to_camel(child.data)
        
        # Retrieve DQD name for Lark rule
        if child_name not in children_properties:
            fallback_name = to_camel(
                next(
                    (
                        pn
                        for pn, pv in schema.get("properties", schema).items()
                        if found_rule_down_the_line(pv, child.data)
                    ),
                    "",
                )
            )
            if fallback_name:
                child_name = fallback_name
                child_schema = schema
            else:
                skip_children_names = True
        
        if child_name in children_properties:
            child_schema = children_properties[child_name]
            is_child_array = child_schema.get("type", "") == "array"

        child_value = to_dict(child, child_schema)

        # If the child's name is already in the values, it must be an array
        if child_name in values:
            if isinstance(values[child_name], dict):
                values[child_name] = [values[child_name]]
            is_child_array = True

        if is_child_array:
            if child_name not in values:
                values[child_name] = []
            # Flat list
            if isinstance(child_value, list):
                values[child_name] += child_value
            else:
                values[child_name].append(child_value)

        else:
            values[child_name] = child_value

    list_values: list = list(values.values())
    if (
        skip_children_names
        and is_parent_array
        and all(isinstance(v, list) for v in list_values)
    ):
        assert (
            len(list_values) == 1
        ), f"Only one child list (<>{list_values}) can be embedded in a parent list ({camel_name})"
        values = list_values[0]

    return values


def convert(dqd_query: str) -> dict[str, Any]:
    data = parser.parse(dqd_query)
    res: dict = to_dict(data, {"start": json_schema})
    return res


def cmdline() -> None:
    if os.path.isfile(sys.argv[-1]):
        with open(sys.argv[-1], "r") as fo:
            dqd = fo.read()
    else:
        dqd = sys.argv[-1]
    print("Tree:", parser.parse(dqd).pretty())
    print(json.dumps(convert(dqd), indent=4))


if __name__ == "__main__":
    cmdline()

# TODO: add type number to math

import os
import re

from collections.abc import Iterable
from json import dumps
from typing import Any, ClassVar

from lark import Lark, Tree
from lark.grammar import Terminal, NonTerminal
from lark.indenter import Indenter
from lark.lexer import Token

test_dqd = """Layer1 label1
    left1 = right1
    year = 1999
    label1.year = 1999
    year(label1.date) = 1999
    left5 contain "right5"
    left6 = /right6/
    AND
        left7 = right7
        left8 = right8
    length(lemma, dummy) = 35 + 30

# This is a random comment
Layer2@label1 label2 # this is another random comment
    left2 != right2
    left3 >= right3
    left4 < right4
    start(label2) > start(label1)
    end(label2) < end(label1) - 30

sequence@label1 seq 1..2
    Token t1
    Token t2

set deps
    Token tx
        DepRel
            head = t2
            dep = tx

label1 = label2

!EXISTS
    Token@label2
        upos = "ADV"

results1 => plain
    context
        label1
    entities
        seq
        label2

results2 => analysis
    attributes
        label1.lemma
    functions
        frequency
    filter
        frequency > 2

results3 => collocation
    space
        seq
    attribute
        t2.form

results3 => collocation
    center
        t2
    window
        -32..+32
    attribute
        t2.form
"""

test_grammar: str = open(
    os.path.join(os.path.dirname(__file__), "newgrammar.lark")
).read()


class TreeIndenter(Indenter):
    NL_type: str = "_NL"
    INDENT_type: str = "_INDENT"
    DEDENT_type: str = "_DEDENT"
    tab_len: int = 8
    OPEN_PAREN_types: ClassVar[list[str]] = []
    CLOSE_PAREN_types: ClassVar[list[str]] = []
    # this fixes mypy but not sure if it breaks anything:
    always_accept: Iterable[str] = ()


test_parser = Lark(
    test_grammar, parser="earley", start="top", postlex=TreeIndenter(), debug=True
)

parsed = test_parser.parse(test_dqd)

print("Tree:", parsed.pretty())


def underscore_to_camel(s) -> str:
    return re.sub("_(.)", lambda m: f"{m[1].upper()}", s)


class Schema:
    def __init__(self, grammar, lark="newgrammar.lark"):
        self.grammar = grammar
        self.schema = {}
        self.defs = {}
        self.ignores = (
            "_NL",
            "_INDENT",
            "_DEDENT",
            '"@"',
            '","',
            '".."',
            '"..+"',
            '")"',
            '"set"',
            '"sequence"',
            '"=>"',
            '"plain"',
            '"context"',
            '"entities"',
            '"analysis"',
            '"functions"',
            '"attributes"',
            '"filter"',
            '"collocation"',
            '"space"',
            '"window"',
            '"center"',
            '"attribute"',
        )
        self.skips = {}
        self.poly = {}
        self.renames = {}
        with open(lark, "r") as larkfile:
            while line := larkfile.readline():
                line = line.strip()
                toskip = re.match(r".*// skip: ([^/]+)$", line)
                poly = re.match(r".*// type: ([^/]+)$", line)
                rename = re.match(r".*// rename: ([^/]+)$", line)
                if toskip:
                    rule_name = underscore_to_camel(line.split(":")[0].strip())
                    self.skips[rule_name] = toskip[1].strip()
                if poly:
                    rule_name = line.split(":")[0].strip()
                    self.poly[rule_name] = poly[1].strip()
                if rename:
                    rule_name = underscore_to_camel(line.split(":")[0].strip())
                    self.renames[rule_name] = {}
                    for r in rename[1].split(" "):
                        subrule_name, newname = r.split(">")
                        self.renames[rule_name][
                            underscore_to_camel(subrule_name.strip())
                        ] = newname.strip()

    def get_ref(self, x: dict):
        ref = x.get("$ref", "")
        ref_name = ref.removeprefix("#/$defs/")
        return (ref, ref_name)

    def collapse_anyOf(self, anyOf: list) -> list:
        o = []
        patterns = set()
        for x in anyOf:
            if "pattern" in x:
                patterns.add(x["pattern"])
            else:
                o.append(x)
        if patterns:
            disjunction = "|".join(p for p in patterns)
            o.append({"type": "string", "pattern": f"({disjunction})"})
        return o

    def get_value_of_terminal(self, terminal) -> str:
        if terminal.__class__ is not Token:
            if len(terminal.children) == 1:
                return self.get_value_of_terminal(terminal.children[0])
            else:
                disjuncts = [self.get_value_of_terminal(c) for c in terminal.children]
                return "(" + "|".join(disjuncts) + ")"
        value = ""
        if terminal.type == "REGEXP":
            value = re.sub(r"/(.+)/.*", "\\1", terminal.value)
        else:
            # remove trailing ( in function names
            value = terminal.value[1:-1].rstrip("(")
            value = re.sub('([+*?"(){}])', lambda m: "\\" + m[0], value)
        return value

    def get_terminal_regex(self, name) -> str:
        rgx = name[1:-1]
        if term := next((t for t in self.grammar.term_defs if t[0] == name), None):
            expansions = term[1][0]
            disjuncts: list[str] = []
            for expansion in expansions.children:
                value = self.get_value_of_terminal(expansion)
                disjuncts.append(value)
            if len(disjuncts) > 1:
                rgx = "(" + "|".join(d for d in disjuncts) + ")"
            else:
                rgx = disjuncts[0]
        else:
            rgx = re.sub('([+*?"(){}])', lambda m: "\\" + m[0], rgx)
        return rgx

    def process_expr(self, expr) -> dict | None:
        body: dict | None = None
        child, op = expr.children
        if op == "?":
            body = self.process_node(child)
            if body is None:
                return None
            body["required"] = False
        else:
            items = self.process_node(child)
            if items is None:
                return None
            body = {"items": items}
            if op == "*":
                body["type"] = ["array", "null"]
                body["required"] = False
            else:
                body["type"] = "array"
        return body

    def process_expansion(self, expansion) -> dict | None:
        body: dict | None = None
        children = self.process_children(expansion)
        if not children:
            return None
        if len(children) == 1:
            body = children[0]
        else:
            if all(c.get("type") == "string" for c in children):
                body = {"type": "string"}
                patterns = set()
                for c in children:
                    p = c.get("pattern", "")
                    if c.get("required") is False:
                        p += "?"
                    patterns.add(p)
                    if poly := c.get("poly"):
                        body["poly"] = poly
                body["pattern"] = f"({''.join(p for p in patterns)})"
            else:
                body = {"properties": children}
        return body

    def process_expansions(self, expansions) -> dict | None:
        body: dict | None = None
        if len(expansions.children) > 1:
            children = self.process_children(expansions)
            if not children:
                return None
            if all(c.get("type") == "string" for c in children):
                disjunction = "|".join(c.get("pattern", "") for c in children)
                body = {
                    "type": "string",
                    "pattern": f"({disjunction})",
                }
                if poly := next((c["poly"] for c in children if "poly" in c), None):
                    body["poly"] = poly
            else:
                body = {"anyOf": self.collapse_anyOf(children)}
        else:
            body = self.process_expansion(expansions.children[0])
        return body

    def process_node(self, node) -> dict | None:
        body: dict | None = None
        if node.data == "expr":
            body = self.process_expr(node)
        elif node.data == "expansions":
            body = self.process_expansions(node)
        elif node.data == "expansion":
            body = self.process_expansion(node)
        elif node.data == "value":
            first_child = node.children[0]
            if first_child.__class__ is NonTerminal:
                if first_child.name in self.ignores:
                    return None
                rn = underscore_to_camel(first_child.name)
                body = {"$ref": f"#/$defs/{rn}"}
            else:
                try:
                    name = first_child.name
                except:
                    name = str(first_child.children[0])
                if name in self.ignores:
                    return None
                pattern = self.get_terminal_regex(name)
                body = {"type": "string", "pattern": pattern}
                if name in self.poly:
                    body["poly"] = self.poly[name]
        return body

    def process_children(self, node):
        children = [self.process_node(c) for c in node.children]
        return [c for c in children if c is not None]

    def process_rule(self, rule_name, expansions):
        self.defs[rule_name] = self.process_expansions(expansions)

    def build_props(self, props):
        o = {}
        if "$ref" in props:
            o = {"$ref": props["$ref"]}
        if "properties" in props:
            o["type"] = "object"
            o["properties"] = {}
            requireds = []
            for x in props["properties"]:
                if "anyOf" in x:
                    assert all(
                        "$ref" in y for y in x["anyOf"]
                    ), "anyOf inside properties only accepts refs"
                    o["anyOf"] = o.get("anyOf", [])
                    for y in x["anyOf"]:
                        ref, ref_name = self.get_ref(y)
                        o["anyOf"].append({"required": [ref_name]})
                        o["properties"][ref_name] = {"$ref": ref}
                else:
                    assert "$ref" in x, "properties only accepts refs or anyOfs"
                    ref, ref_name = self.get_ref(x)
                    o["properties"][ref_name] = {"$ref": ref}
                    if x.get("required") is not False:
                        requireds.append(ref_name)
            if requireds:
                o["required"] = requireds
        elif "anyOf" in props:
            typs = set()
            o["anyOf"] = []
            for x in props["anyOf"]:
                p = self.build_props(x)
                typs.add(p.get("type", "object"))
                if "$ref" in p:
                    o["properties"] = o.get("properties", {})
                    ref, ref_name = self.get_ref(p)
                    o["properties"][ref_name] = {"$ref": ref}
                    o["anyOf"].append({"required": [ref_name]})
                else:
                    o["anyOf"].append(p)
            o["type"] = [t for t in typs] if len(typs) > 1 else next(t for t in typs)
        elif "items" in props:
            o["type"] = "array"
            o["items"] = self.build_props(props["items"])
            o["minItems"] = 1
        elif "poly" in props:
            o = {"type": ["string", props["poly"]], "pattern": props["pattern"]}
        else:
            o = props
        return o

    def make(self):
        defs = {}
        # First convert each rule
        for rule_name, props in self.defs.items():
            defs[rule_name] = self.build_props(props)
        # Now simplify the skips
        for rule_name, to_skip in self.skips.items():
            rule = defs[rule_name]
            dfpath = f"#/$defs/{to_skip}"
            if "$ref" in rule and rule["$ref"] == dfpath:
                defs[rule_name] = defs[to_skip]
        # Finally, rename keys
        for rule_name, renames in self.renames.items():
            if "properties" in defs[rule_name]:
                new_p = {
                    (renames[p] if p in renames else p): v
                    for p, v in defs[rule_name]["properties"].items()
                }
                defs[rule_name]["properties"] = new_p
            if "anyOf" in defs[rule_name]:
                new_a = [
                    (
                        {"required": [renames[a["required"][0]]]}
                        if "required" in a and a["required"][0] in renames
                        else a
                    )
                    for a in defs[rule_name]["anyOf"]
                ]
                defs[rule_name]["anyOf"] = new_a
            if "required" in defs[rule_name]:
                new_r = [
                    (renames[r] if r in renames else r)
                    for r in defs[rule_name]["required"]
                ]
                defs[rule_name]["required"] = new_r
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$defs": defs,
            **defs.pop("top", {}),
        }
        self.schema = schema
        return schema


def lark_grammar_to_json_schema(grammar):
    schema = Schema(grammar)
    for rule_name, _, expansions, _ in grammar.rule_defs:
        rn = underscore_to_camel(rule_name.value)
        schema.process_rule(rn, expansions)
    schema.make()
    return schema


def get_specs(name, schema) -> dict:
    specs = schema["$defs"].get(name, {})
    if "$ref" in specs:
        return get_specs(specs["$ref"].removeprefix("#/$defs/"), schema)
    return specs


def dqd_component(component, schema_obj, parent=""):
    schema = schema_obj.schema
    json_obj = {}
    if component.__class__ is Token:
        return component.value
    key = component.data
    key = re.sub(r"_(.)", lambda m: m[1].upper(), key)
    processed_children = [
        dqd_component(c, schema_obj, parent=key) for c in component.children
    ]
    specs = get_specs(key, schema)
    typ = specs.get("type", "")
    if typ == "array":
        json_obj[key] = processed_children
        if "properties" not in specs.get("items", {}):
            # Skip the key of the children
            json_obj[key] = [
                (c if c.__class__ is str else next(x for x in c.values()))
                for c in processed_children
            ]
    elif typ == "object":
        json_obj[key] = {
            next(x for x in c.keys()): next(x for x in c.values())
            for c in processed_children
        }
    elif typ == "string":
        children_strings = [
            (next(x for x in c.values()) if c.__class__ is dict else c)
            for c in processed_children
        ]
        assert all(
            c.__class__ is str for c in children_strings
        ), f"Non-string found for {key} ({children_strings})"
        value = "".join(children_strings)  # type: ignore
        json_obj[key] = value
        if value.__class__ is dict:
            # This is a case of "skip"
            json_obj[key] = next(x for x in value.values())
    elif "string" in typ and processed_children[0].__class__ is str:
        json_obj[key] = processed_children[0]
    elif "object" in typ and processed_children[0].__class__ is dict:
        obj = {
            next(x for x in c.keys()): next(x for x in c.values())
            for c in processed_children
        }
        json_obj[key] = obj
        first_entry = next({k: v} for k, v in obj.items())
        properties = specs.get("properties", {})
        if (
            "string" in typ
            and len(obj) == 1
            and next(x for x in first_entry) not in properties
        ):
            value = next(v for v in first_entry.values())
            json_obj[key] = value
    else:
        assert False, f"Type not supported: {typ}"
    # One exception for functionName: remove trailing (
    if key == "functionName":
        json_obj[key] = json_obj[key].removesuffix("(")
    if json_obj[key].__class__ is dict and key in schema_obj.renames:
        # Do any renaming necessary
        rnm = schema_obj.renames[key]
        obj = {rnm.get(k, k): v for k, v in json_obj[key].items()}
        json_obj[key] = obj
    return json_obj


def dqd_to_json(dqd, schema):
    json_obj = {}
    query, results = dqd.children
    assert query.data == "query" and results.data == "results", "Invalid DQD"
    json_obj["query"] = [
        dqd_component(c, schema, parent="query") for c in query.children
    ]
    # Skip the "result" key of the results
    json_obj["results"] = [
        next(v for v in dqd_component(c, schema, parent="results").values())
        for c in results.children
    ]
    return dumps(json_obj)


# from testgrammar import test_parser, parsed, lark_grammar_to_json_schema, dqd_to_json

# dqd_to_json(parsed, lark_grammar_to_json_schema(test_parser.grammar))

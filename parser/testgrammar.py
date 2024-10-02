import os
import re

from collections.abc import Iterable
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
    def __init__(self, grammar):
        self.grammar = grammar
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
        pass

    def get_terminal_regex(self, name) -> str:
        rgx = name[1:-1]
        if term := next((t for t in self.grammar.term_defs if t[0] == name), None):
            expansions = term[1][0]
            disjuncts: list[str] = []
            for expansion in expansions.children:
                value = expansion.children[0].children[0].children[0]
                if value.type == "REGEXP":
                    rgx = re.sub(r"/(.+)/.*", "\\1", value.value)
                else:
                    # remove trailing ( in function names
                    rgx = value.value[1:-1].rstrip("(")
                    rgx = re.sub('([+*?"(){}])', lambda m: "\\" + m[0], rgx)
                disjuncts.append(rgx)
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
                seq = "".join(
                    c.get("pattern", "") + ("?" if c.get("required") is False else "")
                    for c in children
                )
                body = {
                    "type": "string",
                    "pattern": f"({seq})",
                }
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
            else:
                body = {"oneOf": children}
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
        return body

    def process_children(self, node):
        children = [self.process_node(c) for c in node.children]
        return [c for c in children if c is not None]

    def process_rule(self, rule_name, expansions):
        self.defs[rule_name] = self.process_expansions(expansions)

    def solve_references(self):
        pass


def lark_grammar_to_json_schema(grammar):
    schema = Schema(grammar)
    for rule_name, _, expansions, _ in grammar.rule_defs:
        rn = underscore_to_camel(rule_name.value)
        schema.process_rule(rn, expansions)
    return schema

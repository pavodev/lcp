import os

from collections.abc import Iterable
from typing import Any, ClassVar

from lark import Lark
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
    length(lemma) = 35 + 30

# This is a random comment
Layer2@label1 label2 # this is another random comment
    left2 != right2
    left3 >= right3
    left4 < right4
    start(label2) > start(label1)

sequence@label1 seq 1..2
    Token t1
    Token t2

label1 = label2

!EXISTS
    Token@label2
        upos = "ADV"

results => plain
    context
        label1
    entities
        seq
        label2
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


def get_leaf_value(node: Any) -> str:
    out: str
    try:
        out = node.value
    except:
        out = get_leaf_value(node.children[0])
    return out


def nget(node: Any, prop: str) -> Any:
    out: Any
    try:
        out = next(
            (c for c in node.children if not isinstance(c, Token) and c.data == prop),
            None,
        )
    except:
        out = None
    return out


def process_quantifier(quantifier, range: list[int]) -> list[int]:
    if quantifier:
        r: Any = nget(quantifier, "range")
        if r:
            n_exact: int = int(
                next(
                    (
                        c.value
                        for c in r.children
                        if isinstance(c, Token) and c.type == "RANGE_EXACT"
                    ),
                    -1,
                )
            )
            if n_exact >= 0:
                range = [n_exact, n_exact]
            else:
                min: int = int(
                    next(
                        (
                            c.value
                            for c in r.children
                            if isinstance(c, Token) and c.type == "RANGE_MIN"
                        ),
                        0,
                    )
                )
                max: int = int(
                    next(
                        (
                            c.value
                            for c in r.children
                            if isinstance(c, Token) and c.type == "RANGE_MAX"
                        ),
                        -1,
                    )
                )
                range = [min, max]
        else:
            value: str = get_leaf_value(quantifier)
            if value == "+":
                range[1] = -1
            elif value == "?":
                range[0] = 0
            elif value == "*":
                range[0] = 0
                range[1] = -1
    return range


def process_brackets(node: Any) -> dict:
    section: Any = nget(node, "node_section")
    vp: Any = nget(node, "vp")
    query: Any = nget(node, "query")

    ir = nget(query, "inner_relation")
    if query and ir:
        op: str = "="
        if nget(ir, "not_"):
            op = "!="
        at: str = get_leaf_value(nget(query, "attribute"))
        if at == "word":
            at = "form"  # hack
        value: str = next(c for c in query.children if isinstance(c, Token)).value
        comparison_type: str = (
            "stringComparison"
            if nget(query, "modifier")
            and get_leaf_value(nget(query, "modifier")) == "%l"
            else "regexComparison"
        )
        if comparison_type == "regexComparison":
            value = f"/^{value[1:-1]}$/"
        return {
            "comparison": {
                "left": {"entity": at},
                "operator": op,
                comparison_type: value,
            }
        }

    elif section:
        processed_section: dict
        if nget(section, "not_"):
            processed_section = {
                "logicalOpUnary": {
                    "operator": "NOT",
                    "args": [process_brackets(section)],
                }
            }
        else:
            processed_section = process_brackets(section)

        if vp:
            disj: Any = nget(vp, "or_")
            operator: str = "OR" if disj else "AND"
            return {
                "logicalOpNAry": {
                    "operator": operator,
                    "args": [processed_section, process_brackets(vp)],
                }
            }
        else:
            return processed_section

    return {}


def process_node(
    node: Any, members: list, conf: dict[str, Any] = {"token": "Token"}
) -> None:

    token: dict[str, Any] = {"unit": {"layer": conf["token"]}}
    range: list[int] = [1, 1]
    label: Any = nget(node, "label")
    quantifier: Any = None

    if node.data == "brackets":  # Parentheses

        tmp_members: list = []
        children_nodes: list[Any] = nget(node, "expr").children
        for cn in children_nodes:
            process_node(cn, tmp_members, conf)

        quantifier = nget(node, "quantifier")
        range = process_quantifier(quantifier, range)

        if len(tmp_members) == 0:
            return
        elif len(tmp_members) == 1 and range == [1, 1]:
            token = tmp_members[0]
            if label:
                token["unit"]["label"] = get_leaf_value(label)
            members.append(token)
            return
        else:
            s: dict = {"sequence": {"members": tmp_members}}
            if label:
                s["sequence"]["label"] = get_leaf_value(label)
            if range != [1, 1]:
                s["sequence"]["repetition"] = {
                    "min": range[0],
                    "max": "*" if range[1] < 0 else str(range[1]),
                }
            members.append(s)
            return

    elif node.data == "node":

        if label:
            token["unit"]["label"] = get_leaf_value(label)

        empty_node: Any = nget(node, "empty_node")
        string_node: Any = nget(node, "string_node")
        bracket_node: Any = nget(node, "bracket_node")

        if string_node:
            comp: str = get_leaf_value(string_node)
            comp = f"/^{comp[1:-1]}$/"  # replace "s with /s
            token["unit"]["constraints"] = [
                {
                    "comparison": {
                        "left": {"entity": "form"},
                        "operator": "=",
                        "regexComparison": comp,
                    }
                }
            ]
            quantifier = nget(string_node, "quantifier")

        elif empty_node:
            quantifier = nget(empty_node, "quantifier")

        elif bracket_node:
            constraints: dict = process_brackets(bracket_node)
            token["unit"]["constraints"] = [constraints]
            quantifier = nget(bracket_node, "quantifier")

        range = process_quantifier(quantifier, range)

        if range == [1, 1]:
            members.append(token)
        else:
            members.append(
                {
                    "sequence": {
                        "members": [token],
                        "repetition": {
                            "min": str(range[0]),
                            "max": "*" if range[1] == -1 else str(range[1]),
                        },
                    }
                }
            )


# test is a Lark tree
def test_to_json(test: Any, conf: dict[str, Any] | None = None) -> dict:

    members: list = []
    nodes = test.children[0].children  # expr > _

    for n in nodes:
        process_node(n, members)

    out: dict = {}
    if len(members) == 1:
        out = members[0]
    elif len(members) > 1:
        out = {"sequence": {"members": members}}

    return out


test_parser = Lark(
    test_grammar, parser="earley", start="top", postlex=TreeIndenter(), debug=True
)
# print("Tree:", test_parser.parse(test_dqd).pretty())
print("Tree:", test_parser.parse(test_dqd).pretty())

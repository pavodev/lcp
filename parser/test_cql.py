import os

from lark import Lark

test_grammar: str = open(os.path.join(os.path.dirname(__file__), "cql.lark")).read()

parser = Lark(
    test_grammar,
    parser="earley",
    start="cql_query",
    propagate_positions=True,
    debug=True,
)

from lark import Lark
from lark.indenter import Indenter

dqd_grammar = r"""
    ?start: _NL* predicate+

    predicate       : "Token"scope? variable? _NL [_INDENT token_props+ _DEDENT]        -> token
                    | "Segment"scope? variable? _NL                                     -> segment
                    | "DepRel" variable? _NL [_INDENT deprel_props+ _DEDENT]            -> deprel
                    | "Document" variable? _NL [_INDENT document_props+ _DEDENT]        -> document
                    | "sequence"scope? variable? _NL [_INDENT predicate+ _DEDENT]       -> sequence
                    | "repeat" repeat_loop variable? _NL [_INDENT predicate+ _DEDENT]   -> repeat
                    | "intersect" variable? _NL [_INDENT string+ _DEDENT]               -> intersect
                    | "group" variable? _NL [_INDENT string+ _DEDENT]                   -> group
                    | "all" variable? "(" variable ")" _NL [_INDENT predicate+ _DEDENT]     -> all
    token_props     : "form" operator string                                            -> form
                    | "upos" operator string                                            -> upos
                    | "ufeat.VerbForm" operator string                                  -> ufeat_verbform
    deprel_props    : "head" operator string                                            -> head
                    | "dep" operator string                                             -> dep
                    | "label" operator string                                           -> label
    document_props  : "year" operator year                                              -> year
    repeat_loop     : /[\d+\*](\.\.[\d+\-\*])?/                                         -> loop

    year            : /[0-9]{1,4}/ _NL
    string          : NAME _NL
    ?value          : TOKEN _NL
    variable        : /[a-zA-Z_][a-zA-Z0-9_]*/
    ?scope          : "@"/[a-zA-Z_][a-zA-Z0-9_]*/                                       -> scope
    operator        : /(!|<>|!=|~|¬|¬=|¬~|<=|>=|=)/

    TOKEN           : /\w+/
    SL_COMMENT      : /#[^\r\n]+/ _NL
    DL_COMMENT      : /<#(>|#*[^#>]+)*#+>/ _NL

    %import common.CNAME -> NAME
    %import common.WS_INLINE
    %declare _INDENT _DEDENT
    %ignore WS_INLINE
    %ignore SL_COMMENT
    %ignore DL_COMMENT

    _NL: /(\r?\n[\t ]*)+/
"""

class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 8

parser = Lark(dqd_grammar, parser='lalr', postlex=TreeIndenter())

test_tree = """

Segment s1

Document d
    year >= 1920
    year <= 1990

all tdeps (tdep)
    Token@s tdep
    DepRel
        head = tcat
        dep = tdep

Token t0

DepRel
    head = t0
    dep = t1
    label = compoundprt

Token@s1 t1
    form = lemma
    upos = NOUN

intersect seq3
    seq1
    seq2

group np
    tcat
    tdeps

sequence
    Token@s tdet
        upos = DET

    repeat 1..* rep1
        Token@s
            upos = ADJ

    Token@s tnoun
        upos = NOUN
"""

def test():
    print(parser.parse(test_tree).pretty())

if __name__ == '__main__':
    test()

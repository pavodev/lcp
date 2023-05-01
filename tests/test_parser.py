import json
import os
import unittest

from backend import dqd_parser

os.environ["_TEST"] = "true"

DQD_QUERY = """
Turn d
    IsPresident = no
    PoliticalGroup != NI

Segment@d s

sequence seq
    Token@s t1
        upos = DET
    Token@s t2
        upos = ADJ
    Token@s t3
        upos = NOUN
        lemma.length > 5

set tdeps
    Token@s tx
        DepRel
            head = t3
            dep = tx

Token@s thead
    upos = VERB
    DepRel
        head = thead
        dep = t3

myKWIC1 => plain
    context
        s
    entities
        t1
        t2
        t3

myKWIC2 => plain
    context
        s
    entities
        seq

myStat1 => analysis
    attributes
        t1.lemma
        t2.lemma
        t3.lemma
    functions
        frequency
    filter
        frequency > 10

myStat2 => analysis
    attributes
        t3.lemma
        d.OriginalLanguage
    functions
        frequency
    filter
        frequency > 10

myColl1 => collocation
    center
        t3
    window
        -5..+5
    attribute
        lemma

myColl2 => collocation
    space
        tdeps
    attribute
        upos
    comment
        PoS collocations of all dependends

myColl3 => collocation
    space
        thead
    attribute
        lemma
"""

EXPECTED = {
    "$schema": "cobquec2.json",
    "query": [
        {
            "layer": "Turn",
            "label": "d",
            "constraints": {
                "operator": "AND",
                "args": [
                    {"comparison": "IsPresident = no"},
                    {"comparison": "PoliticalGroup != NI"},
                ],
            },
        },
        {"layer": "Segment", "partOf": "d", "label": "s"},
        {
            "sequence": {
                "label": "seq",
                "members": [
                    {
                        "layer": "Token",
                        "partOf": "s",
                        "label": "t1",
                        "constraints": {"comparison": "upos = DET"},
                    },
                    {
                        "layer": "Token",
                        "partOf": "s",
                        "label": "t2",
                        "constraints": {"comparison": "upos = ADJ"},
                    },
                    {
                        "layer": "Token",
                        "partOf": "s",
                        "label": "t3",
                        "constraints": {
                            "operator": "AND",
                            "args": [
                                {"comparison": "upos = NOUN"},
                                {"comparison": "lemma.length > 5"},
                            ],
                        },
                    },
                ],
            }
        },
        {
            "set": {
                "label": "tdeps",
                "constraints": {
                    "layer": "Token",
                    "partOf": "s",
                    "label": "tx",
                    "constraints": {
                        "layer": "DepRel",
                        "constraints": {
                            "operator": "AND",
                            "args": [
                                {"comparison": "head = t3"},
                                {"comparison": "dep = tx"},
                            ],
                        },
                    },
                },
            }
        },
        {
            "layer": "Token",
            "partOf": "s",
            "label": "thead",
            "constraints": {
                "operator": "AND",
                "args": [
                    {"comparison": "upos = VERB"},
                    {
                        "layer": "DepRel",
                        "constraints": {
                            "operator": "AND",
                            "args": [
                                {"comparison": "head = thead"},
                                {"comparison": "dep = t3"},
                            ],
                        },
                    },
                ],
            },
        },
    ],
    "results": [
        {"plain": {"label": "myKWIC1", "context": "s", "entities": ["t1", "t2", "t3"]}},
        {"plain": {"label": "myKWIC2", "context": "s", "entities": ["seq"]}},
        {
            "statAnalysis": {
                "label": "myStat1",
                "attributes": ["t1.lemma", "t2.lemma", "t3.lemma"],
                "functions": ["frequency"],
                "filter": {"comparison": "frequency > 10"},
            }
        },
        {
            "statAnalysis": {
                "label": "myStat2",
                "attributes": ["t3.lemma", "d.OriginalLanguage"],
                "functions": ["frequency"],
                "filter": {"comparison": "frequency > 10"},
            }
        },
        {
            "collAnalysis": {
                "label": "myColl1",
                "center": "t3",
                "window": "-5..+5",
                "attribute": "lemma",
            }
        },
        {
            "collAnalysis": {
                "label": "myColl2",
                "space": ["tdeps"],
                "attribute": "upos",
                "comment": "PoS collocations of all dependends",
            }
        },
        {
            "collAnalysis": {
                "label": "myColl3",
                "space": ["thead"],
                "attribute": "lemma",
            }
        },
    ],
}


class TestParser(unittest.TestCase):
    def test_parser(self):
        dqd_json = dqd_parser.convert(DQD_QUERY)
        self.assertDictEqual(dqd_json, EXPECTED)

"""
Module that stores custom types used around the backend

TypedDicts for CorpusConfig and CorpusTemplate are in configure.py
"""
import asyncio

from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, Mapping, TypeAlias
from uuid import UUID

from aiohttp import web
from rq.job import Job

from .configure import CorpusConfig

# arbitrary json we know nothing about
JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

# json when we know it is an object at least
JSONObject: TypeAlias = dict[str, JSON]

# all websocket connections to the app -- {room_id: {(ws_connection, user_id)...}}
Websockets: TypeAlias = defaultdict[str, set[tuple[web.WebSocketResponse, str]]]

# {corpus_id: corpus_config} shared between frontend and backend. keys are numbers cast to string
Config: TypeAlias = dict[str, CorpusConfig]

# corpus id, schema, table, size
Batch: TypeAlias = tuple[int, str, str, int]

# user's search query in JSON format
Query: TypeAlias = dict[str, str | list[JSONObject] | JSONObject]

# what can identify a sentence inside sentence results?
SentKey: TypeAlias = str | UUID | int

# a single token within a sentence
Token: TypeAlias = list[int | str | float]

# an offset, plus list of tokens. either as tuple or list
# todo: figure out which of these alternatives is needed?
Sentence: TypeAlias = tuple[int, list[Token]] | list[int | list[Token]]

RawSent: TypeAlias = tuple[SentKey, int, list[Token]]

# the different kinds of sql results in the importer
TableExists: TypeAlias = list[tuple[bool]]
SQLDrops: TypeAlias = list[tuple[str]]
WordCounts: TypeAlias = list[list[tuple[int]]]

# an entry in main.corpus
MainCorpus: TypeAlias = tuple[
    int,  # corpus id
    str,  # name
    str | int | float,  # current version
    str | int | float | None | list[str | int],  # version history
    str | None,  # description
    dict[str, JSON],  # corpus template
    str,  # schema path
    dict[str, int] | None,  # token counts -- todo: remove none when tangram fixed
    dict[str, JSON] | None,  # mapping -- todo: remove none when tangram fixed
    bool,
]

# what Importer.run_script can return
RunScript: TypeAlias = WordCounts | SQLDrops | TableExists | list[MainCorpus] | None

# the args needed to add an entry to main.corpus
MainCorpusEntry: TypeAlias = dict[str, int | float | str]
# right now MainCorpusEntry/nothing are the only possible params for run_script
Params: TypeAlias = MainCorpusEntry | tuple[()] | dict[str, Any] | None

# Request headers for LAMa  calls
Headers: TypeAlias = Mapping[str, JSON]

# a query to be stored, coming from frontend
UserQuery: TypeAlias = tuple[
    str, dict[str, str | int | list[str | int]], str, str | None, datetime
]

# what redis sends to the listener
RedisMessage: TypeAlias = dict[str, str | bytes | None] | None | str

# metadata we generate about a query
QueryMeta: TypeAlias = dict[str, list[JSONObject]]

# a group of sentences {sent_id: [offset, sent]}
ResultSents: TypeAlias = dict[SentKey, Sentence]

# kwic, collocation, freqdist data
Analysis: TypeAlias = list[list[str | float | int | list[int]]]

# -1, 0 and 1+ values in the Results object
ResultsValue: TypeAlias = ResultSents | QueryMeta | Analysis

# all the results put together into a single object
Results: TypeAlias = dict[
    int,  # -1 is sentences, 0 is metadata, more is kwic/freq/collocates
    ResultsValue,
]

# todo: figure this out -- eternally running background jobs
Task: TypeAlias = asyncio.Task

# params for db_query execute
DBQueryParams: TypeAlias = dict[
    str,
    list[str]
    | list[int]
    | str
    | dict[str, Any]
    | dict[str, list[int] | list[str]]  # sentences job
    | None,
]

# model a query iteration result
Iteration: TypeAlias = tuple[
    Job | None, str | None, dict[str, str | bool | None], list[str]
]

# todo: finish this one
QueryArgs: TypeAlias = Any

# one of the main endpoint functions like query(), upload()
Endpoint: TypeAlias = Callable[
    [web.Request], Awaitable[web.Response | web.WebSocketResponse]
]

# a kwic line for vian, with seg, toks, doc, gesture, agent and frame ranges
VianKWIC: TypeAlias = tuple[
    int | str, list[int], int | str, str | None, str | None, list[list[int]]
]

"""
Module that stores custom types used around the backend

TypedDicts for CorpusConfig and CorpusTemplate are in configure.py
"""
import asyncio

from collections import defaultdict
from datetime import datetime
from typing import Mapping, TypeAlias
from uuid import UUID

from aiohttp import web

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
# keep synced with SQLstats.main_corp
MainCorpusEntry: TypeAlias = tuple[str, int | float | str, str, str, str, str]
# right now MainCorpusEntry/nothing are the only possible params for run_script
Params: TypeAlias = MainCorpusEntry | tuple[()]

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

# all the results put together into a single object
Results: TypeAlias = dict[
    int,  # -1 is sentences, 0 is metadata, more is kwic/freq/collocates
    ResultSents | QueryMeta | Analysis,
]

# todo: figure this out -- eternally running background jobs
Task: TypeAlias = asyncio.Task

# kwargs to db_query
DBQueryParams: TypeAlias = (
    tuple[str, str]  # user,room
    | tuple[str]  # user
    | tuple[int, str, str, str]  # store query
    | tuple[list[str]]  # sentence ids
    | None
)

# todo: finish this one
from typing import Any

QueryArgs: TypeAlias = str | int | float | Any

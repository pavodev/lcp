"""
Module that stores custom types used around the backend
"""
from collections import defaultdict
from datetime import datetime
from typing import (
    Any,
    Mapping,
    TypeAlias,
    Sequence,
)
from uuid import UUID

from aiohttp import web

from .configure import CorpusConfig

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

JSONObject: TypeAlias = dict[str, JSON]

# an entry in main.corpus
MainCorpus: TypeAlias = tuple[
    int,
    str,
    str | int | float,
    Any,
    str | None,
    dict[str, JSON],
    str,
    dict[str, int] | None,  # todo: remove none when tangram fixed
    dict[str, JSON] | None,  # todo: remove none when tangram fixed
    bool,
]

Websockets: TypeAlias = defaultdict[str, set[tuple[web.WebSocketResponse, str]]]

Config: TypeAlias = dict[str, CorpusConfig]

Batch: TypeAlias = tuple[int, str, str, int]

Query: TypeAlias = dict[str, str | list[JSONObject] | JSONObject]

Sentence: TypeAlias = tuple[str | UUID | int, int, list[Sequence[Any]]]

# what Importer.run_script can return
RunScript: TypeAlias = (
    list[list[tuple[int]]]
    | list[tuple[str]]
    | list[tuple[bool]]
    | list[MainCorpus]
    | None
)

# the args needed to add an entry to main.corpus
# keep synced with SQLstats.main_corp
Params: TypeAlias = (
    tuple[str, int | float | str, str, str, str, str] | tuple[()] | tuple
)

Headers: TypeAlias = Mapping[str, JSON]

UserQuery: TypeAlias = tuple[str, dict, str, str | None, datetime]

RedisMessage: TypeAlias = dict[str, str | bytes | None] | None

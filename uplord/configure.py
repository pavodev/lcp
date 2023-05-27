from typing import Any, Dict, List, NotRequired, TypedDict


class Meta(TypedDict, total=False):
    date: str
    name: str
    author: str
    version: int | str | float
    website: NotRequired[str]
    corpusDescription: NotRequired[str | None]


class Attribute(TypedDict, total=False):
    type: str
    nullable: bool
    isGlobal: NotRequired[bool]
    name: NotRequired[str]


class Layer(TypedDict, total=False):
    abstract: bool
    contains: NotRequired[str]
    layerType: str
    attributes: Dict[str, Attribute | Dict[str, Attribute]]
    anchoring: NotRequired[Dict[str, bool]]
    values: NotRequired[List[str]]
    partOf: NotRequired[str]


class FirstClass(TypedDict, total=False):
    segment: str
    token: str
    document: str


class Partitions(TypedDict, total=False):
    values: List[str]


class CorpusTemplate(TypedDict, total=False):
    meta: Meta
    layer: Dict[str, Layer]
    firstClass: FirstClass
    partitions: NotRequired[Partitions]
    projects: NotRequired[List[str]]


class CorpusConfig(CorpusTemplate, total=False):
    shortname: NotRequired[str]
    corpus_id: int
    current_version: int | str | float
    version_history: str | None
    description: str | None
    schema_path: str
    token_counts: Dict[str, int]
    mapping: Dict[str, Any]
    enabled: bool
    segment: str
    token: str
    document: str
    column_names: List[str]
    _batches: NotRequired[Dict[str, int]]


def _generate_batches(n_batches: int, basename: str, size: int) -> Dict[str, int]:
    """
    We can create batchnames if we know three things:

    total number of batches
    the prefix of the table name
    the total size of the corpus
    """
    batches: Dict[str, int] = {}
    if n_batches < 2:
        named = basename.replace("<batch>", "") + "0"
        return {named: size}
    for i in range(1, n_batches):
        if i + 1 == n_batches and n_batches > 1:
            name = "rest"
        else:
            name = str(i)
        batch = basename.replace("<batch>", name)
        size = int(size / 2 if name != "rest" else size)
        batches[batch] = int(size)
    return batches


def _get_batches(config: CorpusConfig) -> Dict[str, int]:
    """
    Get a dict of batch_name: size for a given corpus
    """
    batches: Dict[str, int] = {}
    counts: Dict[str, int] = config["token_counts"]
    try:
        mapping = config["mapping"]["layer"][config["token"]]
    except (KeyError, TypeError):
        return counts
    if not mapping:
        return counts
    if "partitions" in mapping:
        for lang, details in mapping["partitions"].items():
            basename = details["relation"]
            if "<language>" in basename:
                basename = basename.replace("<language>", lang)
            size = counts[basename.replace("<batch>", "0")]
            n_batches = details["batches"]
            more = _generate_batches(n_batches, basename, size)
            batches.update(more)
    else:
        n_batches = mapping["batches"]
        name = mapping["relation"]
        size = counts[name.replace("<batch>", "0")]
        more = _generate_batches(n_batches, name, size)
        batches.update(more)
    if not batches:
        return counts
    return batches

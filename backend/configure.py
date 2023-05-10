from typing import Any, Dict


def _generate_batches(n_batches: int, basename: str, size: int) -> Dict[str, int]:
    """
    We can create batchnames if we know three things:

    total number of batches
    the prefix of the table name
    the total size of the corpus
    """
    batches: Dict[str, int] = {}
    for i in range(1, n_batches):
        if i + 1 == n_batches:
            name = "rest"
        else:
            name = str(i)
        batch = basename.replace("<batch>", name)
        size = size / 2 if name != "rest" else size
        batches[batch] = int(size)
    return batches


def _get_batches(config: Dict[str, Any]) -> Dict[str, int]:
    """
    Get a dict of batch_name: size for a given corpus
    """
    batches = {}
    counts = config["token_counts"]
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

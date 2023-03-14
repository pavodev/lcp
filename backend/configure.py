def _get_batches(config):
    """
    Get a dict of batch_name: size for a given corpus
    """
    batches = {}
    # word_count = config["meta"].get("word_count", config.get("word_count", 10000000))
    counts = config["token_counts"]

    mapping = config["mapping"]["layer"]["Token"]
    if "partitions" in mapping:
        for lang, details in mapping["partitions"].items():
            named = details["relation"].replace("<batch>", "0")
            size = counts[named]
            n_batches = details["batches"]
            for i in range(1, n_batches):
                if i + 1 == n_batches:
                    name = "rest"
                else:
                    name = str(i)
                batch = details["relation"].replace("<batch>", name)
                size = size / 2 if name != "rest" else size
                batches[batch] = int(size)
    else:
        n_batches = mapping["batches"]
        name = mapping["relation"].replace("<batch>", "0")
        size = counts[name]
        for i in range(1, n_batches):
            if i + 1 == n_batches:
                name = "rest"
            else:
                name = str(i)
            batch = mapping["relation"].replace("<batch>", name)
            size = size / 2 if name != "rest" else size
            batches[batch] = int(size)
    return batches

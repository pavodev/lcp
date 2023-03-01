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
            size = counts[details["relation"].replace("<part>", "0")]
            n_batches = details["batches"]
            for i in range(1, n_batches):
                if i + 1 == n_batches:
                    name = "rest"
                else:
                    name = str(i)
                batchname = details["relation"].replace("<part>", name)
                size = size / 2 if name != "rest" else size
                batches[batchname] = int(size)
    else:
        n_batches = mapping["batches"]
        size = counts[mapping["relation"].replace("<part>", "0")]
        for i in range(1, n_batches):
            if i + 1 == n_batches:
                name = "rest"
            else:
                name = str(i)
            batchname = mapping["relation"].replace("<part>", name)
            size = size / 2 if name != "rest" else size
            batches[batchname] = int(size)
    return batches

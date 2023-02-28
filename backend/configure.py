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
                total_size = counts[details["relation"].replace("<part>", "0")]
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

    # old code
    for corpus in corpora:
        if "batch" in config[corpus]:
            for part, size in config[corpus]["batch"].items():
                batch.append(corpus, part, size)
            continue
        total_words = config[corpus].get("word_count", 1000000)
        done_words = total_words
        num_batch = config[corpus].get("n_batch", 1)
        batch.append((corpus, "token_0", total_words))
        if num_batch <= 1:
            continue
        batch.pop()  # we don't need _0 if there are real batch
        for p in range(1, num_batch + 1):
            is_rest = p == num_batch
            suffix = "rest" if is_rest else str(p)
            size = int(done_words / 2)
            done_words = size
            if is_rest:
                so_far = sum([i[-1] for i in batch if i[0] == corpus])
                size = total_words - so_far
            name = f"token_{suffix}"
            batch.append((corpus, name, size))
            if is_rest:
                break
    return sorted(batch, key=lambda x: x[-1])

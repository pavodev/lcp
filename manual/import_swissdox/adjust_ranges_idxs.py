import lzma
import os
import sys

from datetime import datetime
from pathlib import Path


DATA_DIR = "/scratch/sdox_import/proc_files/"

def get_range_delta(art_file):
    delta = 0

    with lzma.open(art_file, "rt") as f:
        for line in f:
            _, end, *_ = line.split("\t")
            delta = end

    return int(delta)


def get_tree_delta(dep_file):
    delta = 0

    with lzma.open(dep_file, "rt") as f:
        for line in f:
            _, _, label, _, r_anch = line.split("\t")
            if label == "root":
                delta = r_anch

    return int(delta)


def get_id_delta(xz_file):
    delta = 0

    with lzma.open(xz_file, "rt") as f:
        for line in f:
            id, *_ = line.split("\t")
            delta = id

    return int(delta)


def generate_partitions(pref):
    return ["{:02x}".format(x) for x in range(pref)]


language = sys.argv[1]
partition = sys.argv[2]

partitions = generate_partitions(256)

div_id_deltas = [get_id_delta(Path(DATA_DIR, language, x, f"division_{language}.xz")) for x in partitions]
ne_id_deltas  = [get_id_delta(Path(DATA_DIR, language, x, f"ne_{language}.xz")) for x in partitions]
range_deltas  = [get_range_delta(Path(DATA_DIR, language, x, f"article_{language}.xz")) for x in partitions]
tok_id_deltas = [get_id_delta(Path(DATA_DIR, language, x, f"token_{language}.xz")) for x in partitions]
tree_deltas   = [get_tree_delta(Path(DATA_DIR, language, x, f"deprel_{language}.xz")) for x in partitions]

i            = partitions.index(partition)
now          = datetime.now()
current_time = now.strftime('%H:%M:%S')
print(current_time, partition)

div_Δ   = sum(div_id_deltas[:i])
ne_Δ    = sum(ne_id_deltas[:i])
range_Δ = sum(range_deltas[:i])
tok_Δ   = sum(tok_id_deltas[:i])
tree_Δ  = sum(tree_deltas[:i])

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_article_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"article_{language}.xz")), "rt") as in_f:
        for line in in_f:
            start, end, article_id, dateline, head, subhead, pubdate, source, source_name, meta, embedding = line.rstrip().split("\t")
            start, end = int(start), int(end)
            o_line = [f"[{start+range_Δ},{end+range_Δ})", article_id, dateline, head, subhead, pubdate, source, source_name, meta, embedding]
            out_f.write("\t".join(o_line))
            out_f.write("\n")

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_deprel_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"deprel_{language}.xz")), "rt") as in_f:
        for line in in_f:
            head, dependent, label, l_anch, r_anch = line.rstrip().split("\t")
            dependent, l_anch, r_anch = int(dependent), int(l_anch), int(r_anch)
            nhead = str(int(head) + tok_Δ) if head != r"\N" else head
            o_line = [nhead, str(dependent + tok_Δ), label, str(l_anch + tree_Δ), str(r_anch + tree_Δ)]
            out_f.write("\t".join(o_line))
            out_f.write("\n")

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_division_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"division_{language}.xz")), "rt") as in_f:
        for line in in_f:
            id, start, end, div_type = line.rstrip().split("\t")
            id, start, end = int(id), int(start), int(end)
            o_line = [str(id + div_Δ), f"[{start+range_Δ},{end+range_Δ})", div_type]
            out_f.write("\t".join(o_line))
            out_f.write("\n")

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_mwt_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"mwt_{language}.xz")), "rt") as in_f:
        for line in in_f:
            form_id, start, end = line.rstrip().split("\t")
            start, end = int(start), int(end)
            o_line = [form_id, f"[{start+range_Δ},{end+range_Δ})"]
            out_f.write("\t".join(o_line))
            out_f.write("\n")

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_ne_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"ne_{language}.xz")), "rt") as in_f:
        for line in in_f:
            id, form_id, ne_type, start, end = line.rstrip().split("\t")
            id, start, end = int(id), int(start), int(end)
            o_line = [str(id + ne_Δ), form_id, ne_type, f"[{start+range_Δ},{end+range_Δ})"]
            out_f.write("\t".join(o_line))
            out_f.write("\n")

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_segment_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"segment_{language}.xz")), "rt") as in_f:
        for line in in_f:
            id, start, end = line.rstrip().split("\t")
            start, end = int(start), int(end)
            o_line = [id, f"[{start+range_Δ},{end+range_Δ})"]
            out_f.write("\t".join(o_line))
            out_f.write("\n")

with lzma.open(str(Path(DATA_DIR, language, partition, f"adj_token_{language}.xz")), "wt") as out_f:
    with lzma.open(str(Path(DATA_DIR, language, partition, f"token_{language}.xz")), "rt") as in_f:
        for line in in_f:
            id, form_id, lemma_id, ufea_id, xpos, upos, start, end, segment_id = line.rstrip().split("\t")
            id, start, end = int(id), int(start), int(end)
            o_line = [str(id + tok_Δ), form_id, lemma_id, ufea_id, xpos, upos, f"[{start+range_Δ},{end+range_Δ})", segment_id]
            out_f.write("\t".join(o_line))
            out_f.write("\n")


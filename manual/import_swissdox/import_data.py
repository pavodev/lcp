import lzma
import psycopg
import re
import sys

from datetime import datetime


SCHEMA = "swissdox_1"

CONNECTION = {
    "host": "localhost",
    "port": "5433",
    "dbname": "lcp_production",
    "user": "lcp_production_owner",
}

TABLES_COPY = {
    # "article": ("article_%s.xz", f"COPY {SCHEMA}.article_%s (char_range, article_id, dateline, head, subhead, pubdate, source, source_name, meta, embedding) FROM STDIN WITH NULL '\\N';"),
    "deprel": ("deprel_%s.xz", f"COPY {SCHEMA}.deprel_%s FROM STDIN WITH NULL '\\N';"),
    "division": ("division_%s.xz", f"COPY {SCHEMA}.division_%s (division_id, char_range, type) FROM STDIN WITH NULL '\\N';"),
    "form": ("form_%s.xz", f"COPY {SCHEMA}.form_%s FROM STDIN WITH NULL '\\N';"),
    "fts_vector": ("fts_vector_%s.xz", f"COPY {SCHEMA}.fts_vector_%s0 FROM STDIN WITH NULL '\\N';"),
    "lemma": ("lemma_%s.xz", f"COPY {SCHEMA}.lemma_%s FROM STDIN WITH NULL '\\N';"),
    "mwt": ("mwt_%s.xz", f"COPY {SCHEMA}.mwt_%s FROM STDIN WITH NULL '\\N';"),
    "ne_form": ("ne_form_%s.xz", f"COPY {SCHEMA}.namedentity_form_%s (form_id, type, form) FROM STDIN WITH NULL '\\N';"),
    "ne": ("ne_%s.xz", f"COPY {SCHEMA}.namedentity_%s FROM STDIN WITH NULL '\\N';"),
    "segment": ("segment_%s.xz", f"COPY {SCHEMA}.segment_%s0 FROM STDIN WITH NULL '\\N';"),
    "token": ("token_%s.xz", f"COPY {SCHEMA}.token_%s0 (token_id, form_id, lemma_id, ufeat_id, upos, xpos, char_range, segment_id) FROM STDIN WITH NULL '\\N';"),
    "ufeat": ("ufeat_%s.xz", f"COPY {SCHEMA}.ufeat_%s FROM STDIN WITH NULL '\\N';"),
}


def jsonify_ufeats(string):
    if string:
        # change angular brackets to parens
        string = string.replace("[", "(").replace("]", ")")
        # put alternatves inside JSON-array
        string = re.sub(r"(\w+,\s*\w+)", r"[\1]", string)
        # convert pipes -separator to comma
        string = string.replace("|", ",")
        # converts equal to colon
        string = string.replace("=", ":")
        # surround literals with double quotes
        string = re.sub(r"([\w()]+)", r'"\1"', string)
        # re-bracketize
        string = re.sub(r"\(psor\)", "[psor]", string)

        return "{" + string + "}"
    else:
        return None


def open_lookup(fname):
    with open(fname) as f:
        l = (x for x in f.read().split("\n") if x)

        return {i: x for i, x in enumerate(l, start=1)}


def open_ne_lookup(fname):
    with open(fname) as f:
        lst = (x for x in f.read().split("\n") if x)

        return {i: tuple(x.split("\t")) for i, x in enumerate(lst, start=1)}

def open_idx(fname):
    with open(fname) as f:
        return set([x for x in f.read().split("\n") if x])


conn = psycopg.connect(**CONNECTION)
cur  = conn.cursor()

entity   = sys.argv[1]
language = sys.argv[2]

now          = datetime.now()
current_time = now.strftime('%H:%M:%S')

table     = TABLES_COPY[entity][0] % language
copy_stmt = TABLES_COPY[entity][1] % language

print(f"{current_time}: copying to table '{table}'")

# with lzma.open(table, "rt") as f:
#     with cur.copy(copy_stmt) as copy:
#         for line in f:
#             copy.write(line)
if entity == "form":
    lu = open_lookup(f"/scratch/sdox_v3/lookup/form.{language}.list")
    idx = open_idx(f"/scratch/sdox_import/idx/{language}/all_forms.idx")
    lu_cl = {k: v for k, v in lu.items() if str(k) in idx}
    for k, v in lu_cl.items():
        cur.execute(f"INSERT INTO {SCHEMA}.form_{language} VALUES (%s, %s);", (k, v))
elif entity == "lemma":
    lu = open_lookup(f"/scratch/sdox_v3/lookup/lemma.{language}.list")
    idx = open_idx(f"/scratch/sdox_import/idx/{language}/lemmas.idx")
    lu_cl = {k: v for k, v in lu.items() if str(k) in idx}
    for k, v in lu_cl.items():
        cur.execute(f"INSERT INTO {SCHEMA}.lemma_{language} VALUES (%s, %s);", (k, v))
elif entity == "ne_form":
    lu = open_ne_lookup(f"/scratch/sdox_v3/lookup/ner.{language}.list")
    idx = open_idx(f"/scratch/sdox_import/idx/{language}/nes.idx")
    lu_cl = {k: v for k, v in lu.items() if str(k) in idx}
    for k, v in lu_cl.items():
        cur.execute(f"INSERT INTO {SCHEMA}.namedentity_form_{language} VALUES (%s, %s);", (k, v))
elif entity == "ufeat":
    lu = open_lookup(f"/scratch/sdox_v3/lookup/features.{language}.list")
    idx = open_idx(f"/scratch/sdox_import/idx/{language}/feats.idx")
    lu_cl = {k: v for k, v in lu.items() if str(k) in idx}
    for k, v in lu_cl.items():
        cur.execute(f"INSERT INTO {SCHEMA}.ufeat_{language} VALUES (%s, %s);", (k, jsonify_ufeats(v)))
else:
    with cur.copy(copy_stmt) as copy:
        while block := sys.stdin.read(1024**2):
            copy.write(block)


conn.commit()


import csv
import json
import lzma
import os
import re
import sys
import uuid

from datetime import timedelta
from glob     import glob          as globb
from pathlib  import Path          as p
from timeit   import default_timer as timer


# that was probably only needed for wrongly parsed pseudo-csvs...
# csv.field_size_limit(sys.maxsize)


green = "\033[92m"
end   = "\033[0m"


### DATA & WRITE FILES

DATA_DIR = "./sdox_v3/"


def user_confirmation(message):
    conf = input(message)

    if conf.lower() != "y":
        print("aborting.")
        exit()


def yield_block(article):
    headers = []
    block   = []

    for line in article:
        if line:
            if line.startswith("#"):
                headers.append(line.strip())
            else:
                block.append(line.strip())
        else:
            yield headers, block
            headers = []
            block   = []

    if headers and block:
        yield headers, block


def yield_article(xzf):
    sent_list = []

    with lzma.open(xzf, "rt") as f:
        for line in f:
            line = line.strip()

            if line.startswith("# article") and sent_list:
                yield sent_list
                sent_list = [line]
            else:
                sent_list.append(line)

        if sent_list:
            yield sent_list


def range_lit(start, end):
    return f"{start}\t{end}"


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


def to_str(val):
    return str(val) if val else r"\N"

# def get_meta_dicts(meta_text_file):
#     """
#     function that builds the dictionaries
#     used as lookups for text IDs
#     """
#     line_doc, line_chp, line_trn,  = {}, {}, {}

#     lines = [l.split("\t").strip() for l in [x for x in yield_line(meta_text_file)]]

#     for line in lines:
#         num_line, key_val = line[0], {x.split("=")[0]: x.split("=")[1] for x in line[1].split("|")}
#         line_doc[num_line] = key_val.pop("Session")
#         line_chp[num_line] = key_val.pop("Chapter")
#         line_trn[num_line] = key_val

#     return line_doc, line_chp, line_trn


class MyDict:
    def __init__(self):
        self._dict = {}
        self._max  = 1

    def __str__(self):
        return str(self._dict)

    def update(self, value):
        if value and not value in self._dict:
            self._dict[value] = self._max
            self._max += 1

    def get(self, value):
        return self._dict.get(value, None)


class LanguageState:
    def __init__(self, language):
        self.form      = self.open_lookup(p(DATA_DIR, f"lookup/form.{language}.list"))
        self.ne_form   = self.open_ne_lookup(p(DATA_DIR, f"lookup/ner.{language}.list"))
        self.lemma     = self.open_lookup(p(DATA_DIR, f"lookup/lemma.{language}.list"))
        self.ufeats    = self.open_lookup(p(DATA_DIR, f"lookup/features.{language}.list"))
        self.cur_tok   = 1
        self.cur_ne    = 1
        self.cur_div   = 1
        self.docs      = {}

    @staticmethod
    def open_lookup(fname):
        with open(fname) as f:
            l = (x for x in f.read().split("\n") if x)

            return {x: i for i, x in enumerate(l, start=1)}

    @staticmethod
    def open_ne_lookup(fname):
        with open(fname) as f:
            lst = [x for x in f.read().split("\n") if x]

            return {tuple(x.split("\t")): i for i, x in enumerate(lst, start=1)}


class Article:
    def __init__(self, content_id, language, dateline, head, subhead, pubdate, source, source_name, meta, embeddings):
        self.content_id  = content_id
        self.language    = language
        self.dateline    = dateline
        self.head        = head
        self.subhead     = subhead
        self.pubdate     = pubdate
        self.source      = source
        self.source_name = source_name
        self.meta        = meta
        self.embeddings  = embeddings


class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class GlobalState:
    language_state = None
    source_mapping = MyDict()
    cur_language   = None
    cur_idx        = 0
    end_char       = None
    left           = 1
    cur_div        = None
    div_start      = None
    div_type       = None
    div_id         = 1
    cur_seg        = uuid.uuid4()

    @classproperty
    def right(cls):
        return cls.left + 1

    @classproperty
    def div_range(cls):
        return f"{cls.div_start}\t{cls.end_char}"

    @classmethod
    def fclose(cls):
        # for k, v in cls.language_state.form._dict.items():
        # for k, v in cls.language_state.form.items():
        #     cls.for_w.write("\t".join([str(v), k]))
        #     cls.for_w.write("\n")
        # for k, v in cls.language_state.ne_form._dict.items():
        # for k, v in cls.language_state.ne_form.items():
        #     cls.nef_w.write("\t".join([str(v), "\t".join(k)]))
        #     cls.nef_w.write("\n")
        # for k, v in cls.language_state.lemma._dict.items():
        # for k, v in cls.language_state.lemma.items():
        #     cls.lem_w.write("\t".join([str(v), k]))
        #     cls.lem_w.write("\n")
        # for k, v in cls.language_state.ufeats._dict.items():
        # for k, v in cls.language_state.ufeats.items():
        #     cls.ufe_w.write("\t".join([str(v), jsonify_ufeats(k)]))
        #     cls.ufe_w.write("\n")

        cls.art_w.close()
        cls.dep_w.close()
        cls.div_w.close()
        # cls.for_w.close()
        cls.fts_w.close()
        # cls.lem_w.close()
        cls.nen_w.close()
        # cls.nef_w.close()
        cls.seg_w.close()
        cls.tok_w.close()
        cls.mwt_w.close()
        # cls.ufe_w.close()

    @classmethod
    def fopen(cls):
        cls.art_w = lzma.open(p(OUTDIR, f"article_{cls.cur_language}.xz"),    "wt")
        cls.dep_w = lzma.open(p(OUTDIR, f"deprel_{cls.cur_language}.xz"),     "wt")
        cls.div_w = lzma.open(p(OUTDIR, f"division_{cls.cur_language}.xz"),   "wt")
        # cls.for_w = lzma.open(p(OUTDIR, f"form_{cls.cur_language}.xz"),       "wt")
        # cls.nef_w = lzma.open(p(OUTDIR, f"ne_form_{cls.cur_language}.xz"),    "wt")
        cls.fts_w = lzma.open(p(OUTDIR, f"fts_vector_{cls.cur_language}.xz"), "wt")
        # cls.lem_w = lzma.open(p(OUTDIR, f"lemma_{cls.cur_language}.xz"),      "wt")
        cls.nen_w = lzma.open(p(OUTDIR, f"ne_{cls.cur_language}.xz"),         "wt")
        cls.seg_w = lzma.open(p(OUTDIR, f"segment_{cls.cur_language}.xz"),    "wt")
        cls.tok_w = lzma.open(p(OUTDIR, f"token_{cls.cur_language}.xz"),      "wt")
        cls.mwt_w = lzma.open(p(OUTDIR, f"mwt_{cls.cur_language}.xz"),        "wt")
        # cls.ufe_w = lzma.open(p(OUTDIR, f"ufeat_{cls.cur_language}.xz"),      "wt")


class NestedSetTreeStructure:
    """
    Represents a tree structure with the nested set approach.
    """

    def __init__(self, key, left, right):
        self.nodes = {}
        if not right - left == 1:
            raise Exception("invalid anchors for initialization")
        self.nodes[key] = [left, right]

    def __str__(self):
        """
        Returns a pretty-print version of the tree.
        """
        lines     = []
        last_left = 0
        indent    = -1
        for key, node in sorted(self.nodes.items(), key=lambda item: item[1]):
            if node[0] - last_left == 1:
                indent += 1
            elif node[0] - last_left > 2:
                indent -= 1
            lines.append("{}{}  [{},{}]".format(
                (indent-1)*"│  " + ("" if node[0] == 1 else "├─╴"),
                key,
                node[0],
                node[1]
            ))
            last_left = node[0]
        return '\n'.join(lines)

    def shift_anchors(self, parent_left):
        """
        Makes space in the tree by incrementing all nodes to the right by 2.
        """
        for key, node in self.nodes.items():
            if node[0] > parent_left:
                self.nodes[key][0] += 2
            if node[1] > parent_left:
                self.nodes[key][1] += 2

    def add_node(self, key, parent):
        """
        Adds a node giving the id of the parent or None for the root node.
        """
        if parent is None:
            if len(self.nodes):
                raise Exception("there can only be one root node")
            else:
                self.nodes[key] = [1, 2]
        else:
            if parent in self.nodes:
                parent_node = self.nodes[parent]
            else:
                raise Exception("key does not exist: {}".format(parent))
            self.shift_anchors(parent_node[0])
            self.nodes[key] = [parent_node[0]+1, parent_node[0]+2]


class Header:
    def __init__(self, header, glob):
        self.header = header
        self.glob   = glob

    def process(self):
        [self.conll_sent_id] = [x.split("=")[1].strip() for x in self.header if x.startswith("# sent_id")]

        id_str   = [x for x in self.header if x.startswith("# div_id")]
        type_str = [x for x in self.header if x.startswith("# div_type")]

        if not (id_str and type_str):
            return

        div_id   = id_str[0].split("=")[1].strip()
        div_type = type_str[0].split("=")[1].strip()

        if not self.glob.cur_div and div_id:
            self.glob.cur_div   = div_id
            self.glob.div_type  = div_type
            self.glob.div_start = self.glob.cur_idx
        if not self.glob.cur_div == div_id:
            self.write_line()

            self.glob.cur_div   = div_id
            self.glob.div_start = self.glob.cur_idx
            self.glob.div_type  = div_type

    def write_line(self):
        self.glob.div_w.write("\t".join([ \
            str(self.glob.div_id),        \
            self.glob.div_range,          \
            self.glob.div_type]))
        self.glob.div_w.write("\n")
        self.glob.div_id += 1


class Token:
    @staticmethod
    def u_score2null(value):
        if value == "_":
            return None
        else:
            return value

    @staticmethod
    def _esc(string):
        return string.replace("'", "''").replace("\\", "\\\\") if string else None

    def __init__(self, w_id, form, lemma, upos, xpos, ufeats, head, deprel, deps, misc, glob):
        lemma, ufeats, misc = map(self.u_score2null, [lemma, ufeats, misc])
        # ufeats              = self.jsonify_ufeats(ufeats)
        # glob.language_state.form.update(form)
        # glob.language_state.lemma.update(lemma)
        # glob.language_state.ufeats.update(ufeats)

        self.id         = glob.language_state.cur_tok
        self.form_id    = glob.language_state.form.get(form)
        self.lemma_id   = glob.language_state.lemma.get(lemma)
        self.ufeat_id   = glob.language_state.ufeats.get(ufeats)
        self.form       = form
        self.lemma      = lemma
        self.ufeats     = ufeats
        self.upos       = self.u_score2null(upos)
        self.xpos       = self.u_score2null(xpos)
        self.start      = glob.cur_idx
        self.segment_id = glob.cur_seg
        self.deprel     = deprel
        self.w_id       = w_id
        self.p_id       = head
        self.length     = len(form)

        glob.end_char = self.end
        glob.cur_idx  = self.end
        glob.language_state.cur_tok += 1

    @property
    def end(self):
        return self.start + self.length

    @property
    def range(self):
        return f"{self.start}\t{self.end}"

    @property
    def fts_repr(self):
        return f" '1{self._esc(self.form)}':{self.w_id} '2{self._esc(self.lemma)}':{self.w_id} '6{self.xpos}':{self.w_id} '3{self.upos}':{self.w_id}"

    @property
    def copy_repr(self):
        return self.id, self.form_id, self.lemma_id, self.ufeat_id, self.upos, self.xpos, self.range, self.segment_id


class ContractToken(Token):
    @property
    def end(self):
        return self.start + self.len_mwt

    def __init__(self, w_id, form, lemma, upos, xpos, ufeats, head, deprel, deps, misc, glob, surftok, len_mwt):
        lemma, ufeats, misc = map(self.u_score2null, [lemma, ufeats, misc])
        # ufeats              = self.jsonify_ufeats(ufeats)
        # glob.language_state.form.update(form)
        # glob.language_state.lemma.update(lemma)
        # glob.language_state.ufeats.update(ufeats)

        self.id         = glob.language_state.cur_tok
        self.form_id    = glob.language_state.form.get(form)
        self.lemma_id   = glob.language_state.lemma.get(lemma)
        self.ufeat_id   = glob.language_state.ufeats.get(ufeats)
        self.form       = form
        self.lemma      = lemma
        self.ufeats     = ufeats
        self.upos       = self.u_score2null(upos)
        self.xpos       = self.u_score2null(xpos)
        self.start      = surftok.start
        self.segment_id = glob.cur_seg
        self.deprel     = deprel
        self.w_id       = w_id
        self.p_id       = head
        self.length     = len(form)
        self.len_mwt    = len_mwt

        glob.end_char = self.end
        glob.language_state.cur_tok += 1

class MWT(Token):
    def __init__(self, w_id, form, glob):
        # glob.language_state.form.update(form)

        self.id         = glob.language_state.cur_tok
        self.form_id    = glob.language_state.form.get(form)
        self.start      = glob.cur_idx
        self.segment_id = glob.cur_seg
        self.length     = len(form)
        self.w_id       = w_id

        glob.end_char = self.end
        glob.cur_idx  = self.end

    @property
    def copy_repr(self):
        return self.form_id, self.range

    # @property
    # def copy_repr(self):
    #     return self.id, self.form_id, self.range, self.segment_id


class Sentence:
    @staticmethod
    def split_lines(lines):
        ret_lines = []
        for line in lines:
            split_l = line.split("\t")
            ret_lines.append(split_l)

        return ret_lines

    @staticmethod
    def _append(lst, elem):
        """custom append function

           in contrast to the built-in method, this function returns
           the augmented list - useful for recursive calls
        """
        lst.append(elem)

        return lst

    @staticmethod
    def _traverse(hierarchy, graph, ids):
        """traverse flat list & build hierarchical structure

           the flat structure is a parent: children dict
        """
        for id in ids:
            hierarchy[id] = Sentence._traverse({}, graph, graph[id])

        return hierarchy

    @staticmethod
    def _ord_keys(dic, key_list):
        """traverse tree structure & build flat list

        """
        for el, vals in dic.items():
            Sentence._ord_keys(vals, Sentence._append(key_list, el))

        return key_list

    def __init__(self, lines, glob):
        self._lines      = self.split_lines(lines)
        self.glob        = glob
        self.proc_tokens = []
        self.proc_mwts   = []
        self.segment     = []
        self.deprel      = []
        self.fts_vector  = []

        self._compute_space_after()

    def _tree_ins_order(self):
        """ put list in hierarchical order for inserting

            1. create dictionary structure (recursively)
            2. flatten keys recursively into list
            3. go over original list and append to
               return list according to flattened keys
        """
        # index 2 = id, index 4 = head ATTENTION: adjust, if this changes!
        id_par   = [(x[0], x[6]) for x in self._lines if x[0].isdigit()]
        ret_list = []

        # get root and check iff one
        root = [id for (id, parent) in id_par if parent == "0"]
        if len(root) != 1:
            raise Exception("root error")

        # flat parent:children mapping initialization
        graph = {id: set() for (id, parent) in id_par}

        # flat parent:children mapping building
        for (id, parent) in id_par:
            if parent != "0":
                graph[parent].add(id)

        # sorting in reverse, since inserting is done by shifting to the right
        graph_sort = {k: sorted(v, key=lambda x: int(x), reverse=True) for k, v in graph.items()}

        # build hierarchical structure
        hier_ids = self._traverse({}, graph_sort,  root)

        # flatten keys into ordered list
        flat_keys = self._ord_keys(hier_ids, [])

        # re-order original rows for returning
        for i in flat_keys:
            for pair in id_par:
                if pair[0] == i:
                    ret_list.append(pair)
                    continue

        return ret_list

    def _process_tree(self, ins, token_dict, tok_par_dict):
        sent       = []
        fts_str    = ""
        root, rest = ins[0], ins[1:]
        tree       = NestedSetTreeStructure(root[0], self.glob.left, self.glob.right)
        for elem in rest:
            tree.add_node(*elem)

        # update globals
        self.glob.left = max([x[1] for x in tree.nodes.values()]) + 1

        # look-up running indices and flatten into list
        for k, v in tree.nodes.items():
            token_id = token_dict[k][0]
            deprel   = token_dict[k][1]
            head_id  = token_dict[tok_par_dict[k]][0] if tok_par_dict[k] else None
            sent.append((head_id, token_id, deprel, *v))

        self.deprel += sent
        # 4 = label_out (what am I?), 5 = labels_in (what do I encompass?)
        tok_id2sent_idx = {v[0]: k for k, v in token_dict.items()}
        for elem in sent:
            fts_str += f" '4{elem[2]}':{tok_id2sent_idx[elem[1]]}"
            fts_str += f" '5{elem[2]}':{tok_id2sent_idx[elem[1]]}"

        return fts_str

    def _handle_contraction(self, w_id, form):
        min, max     = [int(x) for x in w_id.split("-")]
        contract_ids = [str(x) for x in range(min, max+1)]

        mwt = MWT(w_id, form, self.glob)
        self.proc_mwts.append(mwt)

        contract_ids.reverse()

        return contract_ids, len(form)

    def _compute_space_after(self):
        start_end = []
        miscs     = [x[-1] for x in self._lines]

        for misc in miscs:
            if "start_char" in misc and "end_char" in misc:
                start = re.search(r"(?<=start_char=)\d+", misc)[0]
                end   = re.search(r"(?<=end_char=)\d+", misc)[0]
                start_end.append((start, end))
            else:
                start_end.append((False, False))

        self._space_after = [x[1] != y[0] if all((x, y)) else True for x, y in zip(start_end, start_end[1:])] + [False]

    def _process_lines(self):
        # self.glob.cur_idx += 1
        # set up local variables
        token_dict    = {}
        tok_par_dict  = {}
        fts_str       = ""
        contract_ids  = []
        start_char    = self.glob.cur_idx
        end_char_prev = None

        for line, space_after in zip(self._lines, self._space_after):
            w_id, form, *_ = line

            assert w_id
            assert form

            if "-" in w_id:
                contract_ids, len_mwt = self._handle_contraction(w_id, form)
                if space_after:
                    self.glob.cur_idx += 1
                continue

            if contract_ids:
                assert w_id == contract_ids.pop()
                token = ContractToken(*line, self.glob, self.proc_mwts[-1], len_mwt)
            else:
                token = Token(*line, self.glob)

            token_dict[w_id]   = token
            tok_par_dict[w_id] = token.p_id if token.p_id != "0" else None

            if space_after and not isinstance(token, ContractToken):
                self.glob.cur_idx += 1

            fts_str += token.fts_repr

            self.proc_tokens.append(token)

        # build tree (if possible)
        try:
            ins = self._tree_ins_order()
            fts = self._process_tree(ins, {k: (v.id, v.deprel) for k, v in token_dict.items()}, tok_par_dict)
        except:
            fts = None

        # create segment entry for writing
        self.segment = [
            self.glob.cur_seg,
            range_lit(start_char, self.glob.end_char)
        ]

        if fts:
            self.fts_vector = [
                self.glob.cur_seg,
                f"{fts_str}{fts}"
            ]

        # set new segment id
        self.glob.cur_seg = uuid.uuid4()

    def process(self):
        self._process_lines()


def get_article_id(lines):
    for line in lines:
        if line.startswith("# article"):
            return line.split("=")[1].strip()


def mwt2ids(string):
    if "-" in string:
        lower = int(string.split("-")[0])
        upper = int(string.split("-")[1]) + 1

        return list(range(lower, upper))
    else:
        return [int(string)]


def strlist2span(string):
    items = string.split(",")

    return items[0], items[-1]


def main():
    """
        adjust for new dir structure
    """
    # for partition in filter(lambda x: x == language if language else True, LANGUAGES):
    print(f"processing {partition}")
    glob    = GlobalState
    t_start = timer()

    article_counter = 0

    glob.cur_language = partition
    glob.fopen()
    print("loading look-up tables...")
    glob.language_state = LanguageState(partition)
    print("done")

    # xz_list = [x for x in sorted(os.listdir(p(DATA_DIR, "conll", partition)))]
    # xz_list = ["{:03x}.xz".format(x) for x in range(2**3)]
    xz_list = [x for x in sorted(globb(str(p(DATA_DIR, "conll", partition, f"{prefix}*.xz"))))]

    for xz_file in xz_list:
        xz_file = p(xz_file).name

        with lzma.open(p(DATA_DIR, "meta", f"{xz_file}"), "rt") as f:
            csv_r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            cols = (line for line in csv_r)
            meta_data = {col[0]: col[1:] for col in cols}

        with lzma.open(p(DATA_DIR, "dem", partition, f"{xz_file}"), "rt") as f:
            csv_r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            cols = (line for line in csv_r)
            dems = {col[0]: col[1] for col in cols}

        with lzma.open(p(DATA_DIR, "ner", partition, f"{xz_file}"), "rt") as f:
            ners = {}
            csv_r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            cols = (line for line in csv_r)
            for col in cols:
                try:
                    sent_id, tok_ids, ne_type, form = col
                    form = form.rstrip()
                except:
                    continue

                tok_ids = strlist2span(tok_ids)

                if sent_id not in ners:
                    ners[sent_id] = {tok_ids: (ne_type, form)}
                else:
                    ners[sent_id] = {**ners[sent_id], tok_ids: (ne_type, form)}

        for text in yield_article(p(DATA_DIR, "conll", partition, xz_file)):
            article_counter += 1
            if article_counter % 1_000 == 0:
                t_count = timer()
                t = timedelta(seconds=t_count-t_start)
                print(f"Processed {article_counter:,} articles. time elapsed: {t}")


            article_id = get_article_id(text)

            try:
                article = Article(article_id, *meta_data[article_id], dems[article_id])
            except:
                print(f"   no meta data found for article '{article_id}'")
                continue

            art_start = glob.cur_idx

            for i, hb in enumerate(yield_block(text)):
                headers, block = hb
                header = Header(headers, glob)
                header.process()

                sent = Sentence(block, glob)
                sent.process()

                for t_ids, type_form in ners.get(header.conll_sent_id, {}).items():
                    start_t_id, end_t_id = t_ids
                    ne_type, ne_form     = type_form

                    # glob.language_state.ne_form.update((ne_form, ne_type))
                    ne_form_id = glob.language_state.ne_form.get((ne_type, ne_form))

                    if "-" in start_t_id:
                        start = [x for x in sent.proc_mwts if x.w_id == start_t_id][0].start
                    else:
                        start = [x for x in sent.proc_tokens if x.w_id == start_t_id][0].start

                    if "-" in end_t_id:
                        end = [x for x in sent.proc_mwts if x.w_id == end_t_id][0].end
                    else:
                        end = [x for x in sent.proc_tokens if x.w_id == end_t_id][0].end

                    glob.nen_w.write("\t".join([str(glob.language_state.cur_ne), str(ne_form_id), ne_type, f"{start}\t{end}"]))
                    glob.nen_w.write("\n")
                    glob.language_state.cur_ne += 1

                for elem in sent.proc_tokens:
                    glob.tok_w.write("\t".join([to_str(x) for x in elem.copy_repr]))
                    glob.tok_w.write("\n")

                for elem in sent.proc_mwts:
                    glob.mwt_w.write("\t".join([str(x) for x in elem.copy_repr]))
                    glob.mwt_w.write("\n")

                for elem in sent.deprel:
                    glob.dep_w.write("\t".join([to_str(x) for x in elem]))
                    glob.dep_w.write("\n")

                glob.seg_w.write("\t".join([str(x) for x in sent.segment]))
                glob.seg_w.write("\n")
                glob.fts_w.write("\t".join([str(x) for x in sent.fts_vector]))
                glob.fts_w.write("\n")

            art_end = glob.end_char
            header.write_line()
            glob.cur_div = None

            if not art_start < art_end:
                print(f"   no text for article '{article_id}' in file '{xz_file}'")

            glob.art_w.write("\t".join([       \
                range_lit(art_start, art_end), \
                article.content_id,            \
                article.dateline,              \
                article.head,                  \
                article.subhead,               \
                article.pubdate,               \
                article.source,                \
                article.source_name,           \
                article.meta,                  \
                article.embeddings]))
            glob.art_w.write("\n")

            glob.cur_div = None
    glob.fclose()


if __name__ == "__main__":
    prefix = sys.argv[2]
    partition = sys.argv[1]
    signature = f"{partition}:{prefix}"
    OUTDIR = f"./proc_files/{partition}/{prefix}/"
    if not os.path.exists(OUTDIR):
        os.makedirs(OUTDIR)

    write_dir_msg = f"{signature} writing to dir {OUTDIR}"


    # print()
    # user_confirmation(
    #     data_file_msg + \
    #     "\n"          + \
    #     write_dir_msg + \
    #     "\n\ncontinue (y/Y)? "
    # )

    main()

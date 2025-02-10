import lzma
import re
import sys

from flair.nn     import Classifier
from flair.data   import Sentence as flairSentence
from pathlib      import Path
from statistics   import mode
from transformers import pipeline


NE_MAP = {
    "LOC":   "\u001b[31m",
    "MISC":  "\u001b[32m",
    "ORG":   "\u001b[33m",
    "PER":   "\u001b[34m",
    "OTHER": "\u001b[35m",
    "CLEAR": "\u001b[0m"
}


NE_MAP2 = {
    "LOC":   "L",
    "MISC":  "M",
    "ORG":   "O",
    "PER":   "P",
    "OTHER": "*"
}


SB_NER = pipeline(
    model="ZurichNLP/swissbert-ner",
    aggregation_strategy="simple"
)

FLAIR_NER = Classifier.load('ner-large')

class NE:
    __slots__ = (
        "ne_type",
        "probability",
        "original_start",
        "original_end"
    )

    def __init__(self, ne_type, original_start, original_end, probability=None):
        self.ne_type        = ne_type
        self.original_start = original_start
        self.original_end   = original_end
        self.probability    = probability


class Token:
    __slots__ = (
        "id",
        "form",
        "start",
        "end",
        "space_after",
        "NE",
        "range",
        "is_mwt",
        "trail_space"
    )
    ne_color_map = {
        "LOC":   "\u001b[41m",
        "MISC":  "\u001b[42m",
        "ORG":   "\u001b[43m",
        "PER":   "\u001b[44m",
        "OTHER": "\u001b[45m"
    }
    clear_color = "\u001b[0m"

    def __init__(self, id, form, start, end, space_after):
        self.id           = id
        self.form         = form
        self.start        = start
        self.end          = end
        self.space_after  = space_after
        self.NE           = None
        self.range        = range(int(start), int(end))
        self.is_mwt       = True if start == end else False
        self.trail_space  = " " if space_after else ""

    def __str__(self):
        return f"{self.form}{self.trail_space}"

    # @property
    # def ner_continues(self, ne_model):
    #     if ne_model == "swissbert":
    #         ne = self.ne_swissbert
    #     elif ne_model == "stanza":
    #         ne = self.ne_stanza
    #     else:
    #         raise Exception(f"no such NE model: {ne_model}")

    #     return True if ne.original_end - 2 >= self.end else False

    @property
    def color(self):
        if self.NE:
            tag, position = self.NE[0], self.NE[1]
            if position == "B":
                return Token.ne_color_map[tag] + self.form + self.trail_space
            elif position == "I":
                return self.form + self.trail_space
            elif position == "E":
                return self.form + Token.clear_color + self.trail_space
            elif position == "S":
                return Token.ne_color_map[tag] + self.form + Token.clear_color + self.trail_space
        else:
            return str(self)


class Sentence:
    __slots__ = (
        "id",
        "text",
        "tokens",
        "range2id",
        "stanza_ner"
    )

    def __init__(self, id, text, tokens, range2id, stanza_ner):
        self.id         = id
        self.text       = text
        self.tokens     = tokens
        self.range2id   = range2id
        self.stanza_ner = stanza_ner

    def __repr__(self):
        return f"{self.text}"


def yield_data_stdin():
    sent_list = []

    for line in sys.stdin:
        line = line.strip()

        if not line and sent_list:
            yield sent_list
            sent_list = []
        else:
            sent_list.append(line)

    if sent_list:
        yield sent_list


# def yield_data(xzf):
#     sent_list = []
#     with lzma.open(xzf, "rt") as f:
#         for line in f:
#             line = line.strip()

#             if not line and sent_list:
#                 yield sent_list
#                 sent_list = []
#             else:
#                 sent_list.append(line)

#         if sent_list:
#             yield sent_list


def val(string): return string.split("=")[1].strip()


def extract_data(block):
    id2range   = {}
    stanza_ner = {}
    cur_ner    = None
    tokens     = []

    for line, next_line in zip(block, block[1:]+["_\t_"]):
        if line.startswith("# text"):
            text = val(line)

        elif line.startswith("# sent_id"):
            sent_id = val(line)

        elif re.match(r"\d", line):
            id, form, *_, misc = line.split("\t")
            *_, next_misc      = next_line.split("\t") if re.match(r"\d", next_line) else (None, "_")

            if misc != "_":
                start = re.search("(?<=start_char=)\d+", misc)[0]
                end   = re.search("(?<=end_char=)\d+", misc)[0]
                if next_misc != "_":
                    next_start = re.search("(?<=start_char=)\d+", next_misc)[0]
                else:
                    next_start = False

                space_after = False if next_start and end == next_start else True

                range = (int(start), int(end))

                id2range[id] = range
                if not "ner=O" in misc:
                    try:
                        ner = re.search(r"(?<=ner=)[BIES]-\w+", misc)[0]
                    except:
                        import pdb; pdb.set_trace()
                    if ner.startswith("S"):
                        stanza_ner[range] = ner.lstrip("S-")
                    elif ner.startswith("B"):
                        cur_ner = range
                    elif ner.startswith("I"):
                        pass
                    elif ner.startswith("E"):
                        range = (cur_ner[0], range[1])
                        stanza_ner[range] = ner.lstrip("E-")
                    else:
                        raise Exception
            else:
                space_after = False
                # start still around from previous n-m token
                end = start

            tokens.append(Token(id, form, start, end, space_after))
        elif line == "# done":
            return False

    range2id = {tuple(v): k for k, v in id2range.items()}

    return Sentence(sent_id, text, tokens, range2id, stanza_ner)


def overlaps(tok_r, ne_r):
    if (tok_r.start >= ne_r.start) and (tok_r.stop <= ne_r.stop):
        return True
    elif (ne_r.start in tok_r) or (ne_r.stop - 1 in tok_r):
        return True
    else:
        return False


def get_tokids(tok_dict, min_c, max_c):
    return tuple([v for k, v in tok_dict.items() if overlaps(range(*k), range(min_c, max_c))])


def ensemble(flair_ner, sb_ner, stanza_ner):
    num_dict = {}
    ret      = {}

    for d in [flair_ner, sb_ner, stanza_ner]:
        for elem in d.keys():
            if elem in num_dict:
                num_dict[elem] += 1
            else:
                num_dict[elem] = 1

    for key in (k for k, v in num_dict.items() if v == 3):
        if len(set((vals := [flair_ner[key], sb_ner[key], stanza_ner[key]]))) >= 2:
            ret[key] = mode(vals)
        else:
            ret[key] = flair_ner[key]

    for key in (k for k, v in num_dict.items() if v == 2):
        if len(set((vals := [flair_ner.get(key), sb_ner.get(key), stanza_ner.get(key)]))) == 2:
            ret[key] = mode(vals)

    return ret


def get_tokens(tokens_dict, ne_dict, offset):
    ret = {}

    for char_range, ne_type in ne_dict.items():
        toks = get_tokids(tokens_dict, char_range[0]+offset, char_range[1]+offset)
        if toks:
            ret[toks] = ne_type

    return ret


def extract_spans(ne_lst):
    named_ents = []
    cur_elem   = []

    for tok in ne_lst:
        beis = tok.NE[1]

        cur_elem.append(tok)

        if beis in ["E", "S"]:
            named_ents.append((
                [x.id for x in cur_elem]
              , cur_elem[0].NE[0]
              , "".join([x.__str__() for x in cur_elem])
            ))
            cur_elem = []

    return named_ents


def print_ners(ners_dict, text):
    chars  = len(text) * [" "]
    offset = 0
    if ners_dict:
        for start_end, ne_type in ners_dict.items():
            chars = chars[:start_end[0]+offset] + [NE_MAP.get(ne_type, "\u001b[35m")] + chars[start_end[0]+offset:]
            offset += 1

            for i in range(*start_end):
                try:
                    chars[i+offset] = "█"
                except:
                    continue

            chars = chars[:i+offset+1] + [NE_MAP["CLEAR"]] + chars[i+offset+1:]
            offset += 1

    print("".join(chars))


def flair_map(nes):
    return {(x[0].start_position, x[-1].end_position): x.tag for x in nes}


# ACTION

# conll_file = sys.argv[1]
# debug = True if len(sys.argv) > 2 else False
debug = False

# fpath = Path(conll_file).absolute()
# language = fpath.parent.name
language = sys.argv[1]

SB_NER.model.set_default_language(f"{language}_CH")

# if debug:
#     for k, v in list(NE_MAP.items())[:-1]: print(f"{v}{k}{NE_MAP['CLEAR']}")

for block in yield_data_stdin():
    sent = extract_data(block)
    if not sent:
        quit()

    sent_printed = False
    # ids_ne  = set()

    offset = min([x[0] for x in sent.range2id.keys()])

    #-- STANZA NERs
    sent.stanza_ner = {(k[0] - offset, k[1] - offset): v for k, v in sent.stanza_ner.items()}

    #-- SWISSBERT NERs
    nes = SB_NER(sent.text)
    sb_ner = {(ne["start"], ne["end"]): ne["entity_group"] for ne in nes}

    #-- FLAIR NERs
    text = flairSentence(sent.text)
    FLAIR_NER.predict(text)
    flair_ner = flair_map(text.get_spans())

    # for ne in nes:
    #     ne_type = ne["entity_group"]
    #     sb_ner[(ne["start"], ne["end"])] = ne_type
    #     # SwissBERT character indices are shifted one to left (when larger than 0)
    #     start    = ne_s + offset if (ne_s := ne["start"]) == 0 else ne_s + offset + 1
    #     end      = ne["end"] + offset
    #     word_ids = get_tokids(sent.range2id, start, end)
    #     sb_toks[word_ids] = ne_type
        # if word_ids:
            # if debug:
            #     if not sent_printed:
            #         print(text)
            #         sent_printed = True
            #     print(f"\t{sent.sent_id}\t{','.join(word_ids)}\t{ne['entity_group']}\t{ne['word']}\t{ne['score']}")
            #     if len(word_ids) != len(ne["word"].split(" ")):
            #         import pdb; pdb.set_trace()
            # ids_ne.update(tuple([(word_ids, ne["entity_group"])]))

    flair_toks  = get_tokens(sent.range2id, flair_ner, offset)
    sb_toks     = get_tokens(sent.range2id, sb_ner, offset)
    stanza_toks = get_tokens(sent.range2id, sent.stanza_ner, offset)


    ens_dict = ensemble(flair_toks, sb_toks, stanza_toks)
    # ens_dict = stanza_toks

    for toks, ne_type in ens_dict.items():
        if len(toks) == 1:
            [token] = [x for x in sent.tokens if x.id == toks[0]]
            token.NE = (ne_type, "S")
        else:
            length = len(toks) - 1
            for bie, j in enumerate(toks):
                [token] = [x for x in sent.tokens if x.id == j]
                if bie == 0:
                    token.NE = (ne_type, "B")
                elif bie == length:
                    token.NE = (ne_type, "E")
                else:
                    token.NE = (ne_type, "I")
    if not debug:
        ne_idxs = extract_spans([tok for tok in sent.tokens if tok.NE])
        for ne in ne_idxs:
            print(f"{sent.id}\t{','.join(ne[0])}\t{ne[1]}\t{ne[2]}")

    else:
        print("SwissBERT  ", end="")
        print_ners(sb_ner, sent.text)
        print("stanza     ", end="")
        print_ners(sent.stanza_ner, sent.text)
        print("FLAIR      ", end="")
        print_ners(flair_ner, sent.text)
        print("-----------", end="")
        print("".join([tok.color for tok in sent.tokens if not tok.is_mwt]))
        print()


        # for tok in sent.tokens:
        #     for k, v in sb_ner.items():
        #         if overlaps(tok.range, range(*k)):
        #             tok.ne_swissbert = v
        #     for k, v in flair_ner.items():
        #         if overlaps(tok.range, range(*k)):
        #             tok.ne_flair = v
        #     for k, v in sent.stanza_ner.items():
        #         if overlaps(tok.range, range(*k)):
        #             tok.ne_stanza = v


import re
import sys
import stanza

from stanza.pipeline.core import DownloadMethod
from stanza.models.common.doc import ID, TEXT, LEMMA, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MISC, NER, START_CHAR, END_CHAR

FIELD_NUM = 10
FIELD_TO_IDX = {ID: 0, TEXT: 1, LEMMA: 2, UPOS: 3, XPOS: 4, FEATS: 5, HEAD: 6, DEPREL: 7, DEPS: 8, MISC: 9}


def convert_token_dict(token_dict):
	""" Convert the dictionary format input token to the CoNLL-U format output token. This is the reverse function of
	`convert_conll_token`.
	Input: dictionary format token, which is a dictionaries for the token.
	Output: CoNLL-U format token, which is a list for the token.
	"""
	token_conll = ['_' for i in range(FIELD_NUM)]
	misc = []
	for key in token_dict:
		if key == START_CHAR or key == END_CHAR:
			misc.append("{}={}".format(key, token_dict[key]))
		elif key == NER:
			# TODO: potentially need to escape =|\ in the NER
			misc.append("{}={}".format(key, token_dict[key]))
		elif key == MISC:
			# avoid appending a blank misc entry.
			# otherwise the resulting misc field in the conll doc will wind up being blank text
			# TODO: potentially need to escape =|\ in the MISC as well
			if token_dict[key]:
				misc.append(token_dict[key])
		elif key == ID:
			token_conll[FIELD_TO_IDX[key]] = '-'.join([str(x) for x in token_dict[key]]) if isinstance(token_dict[key], tuple) else str(token_dict[key])
		elif key in FIELD_TO_IDX:
			token_conll[FIELD_TO_IDX[key]] = str(token_dict[key])
	if misc:
		token_conll[FIELD_TO_IDX[MISC]] = "|".join(misc)
	else:
		token_conll[FIELD_TO_IDX[MISC]] = '_'
	# when a word (not mwt token) without head is found, we insert dummy head as required by the UD eval script
	if '-' not in token_conll[FIELD_TO_IDX[ID]] and HEAD not in token_dict:
		token_conll[FIELD_TO_IDX[HEAD]] = str(int(token_dict[ID] if isinstance(token_dict[ID], int) else token_dict[ID][0]) - 1) # evaluation script requires head: int
	return token_conll


def doc2conll(doc):
	""" Convert a Document object to a list of list of strings

	Each sentence is represented by a list of strings: first the comments, then the converted tokens
	"""
	doc_conll = []
	for sentence in doc.sentences:
		#sent_conll = list(sentence.comments)
		sent_conll = [sentence.comments[0]]
		#sent_conll = []
		for token_dict in sentence.to_dict():
			token_conll = convert_token_dict(token_dict)
			sent_conll.append("\t".join(token_conll))
		doc_conll.append(sent_conll)

	return doc_conll


sent_id = 1
div_cnt  = 1
headers  = {"id": "article", "lang_dist": "lang_dist"}


def yield_data():
    sent_list = []

    for line in sys.stdin:
        line = line.strip().split("\t")
        if line[1] == "id" and sent_list:

            yield sent_list
            sent_list = [line]
        else:
            #if len(line[2]) < 200:
            sent_list.append(line)

    yield sent_list


for i, block in enumerate(yield_data()):
    if i == 0:
        if not block:
            break
        nlp =  stanza.Pipeline(block[0][0], processors="tokenize, pos, lemma, depparse, mwt, ner", download_method=DownloadMethod.REUSE_RESOURCES, use_gpu=False, min_length_to_batch_separately=50)
        #nlp =  stanza.Pipeline(block[0][0], processors="tokenize, pos, lemma, depparse", download_method=DownloadMethod.REUSE_RESOURCES, use_gpu=True)

    bitmask = [x[1] not in headers and not x[1].endswith(("author", "creator")) for x in block]
    sents = [x[0] for x in zip(block, bitmask) if x[1]]
    meta = [x[0] for x in zip(block, bitmask) if not x[1]]

    docs = [stanza.Document([], text=t[2]) for t in sents]
    try:
        divs = nlp(docs)
    except:
        print(f"# skipped: {article}")
        continue

    [article] = [x[2] for x in meta if x[1] == "id"]
    [lang_dist] = [x[2] for x in meta if x[1] == "lang_dist"]
    print(f"# article = {article}")
    print(f"# lang_dist = {lang_dist}")

    n = 0
    for j, mask in enumerate(bitmask):
        if mask:
            div_type = block[j][1].split(".")[0]
            print(f"# div_id = {div_cnt}")
            print(f"# div_type = {div_type}")
            div_cnt += 1

            for k, conll_sent in enumerate(doc2conll(divs[n])):
                print("# sent_id = {}".format(sent_id))
                sent_id += 1

                print("\n".join(conll_sent))
                print()
            n += 1

print(f"# done")


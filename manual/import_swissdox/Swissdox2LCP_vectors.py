import sys
from sentence_transformers import SentenceTransformer


def yield_data():
    sent_list = []
    last_id = None

    for line in sys.stdin:
        line = line.strip().split("\t")
        if line[1] == "id":
            if sent_list:
                yield (last_id, '\n'.join([f[2] for f in sent_list]))
                sent_list = []
            last_id = line[2]
        elif line[1] == "lang_dist" or line[1].endswith('author') or line[1].endswith('creator'):
            pass
        else:
            sent_list.append(line)

    if last_id:
        yield (last_id, '\n'.join([f[2] for f in sent_list]))


model = SentenceTransformer('sentence-transformers/LaBSE')
data = list(yield_data())
ids = [x[0] for x in data]
texts = [x[1] for x in data]
embeddings = model.encode(texts)
#print(len(embeddings))
for i, id in enumerate(ids):
    print('{}\t[{}]'.format(id, ','.join(['{:e}'.format(x) for x in embeddings[i]])))


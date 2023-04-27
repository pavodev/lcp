#!/usr/bin/env python3
# -*- coding: utf8 -*-

import os


class CorpusData:

    """ requires a path to a corpus containing the files:
            vert_documents.csv, vert_segments.csv and vert_tokens.csv
        TODO: generalization
    """

    def __init__(
            self,
            path_corpus: str = '',  # path to the corpus-data
            corpus_name: str = '',  # if None, dir-name of path_corpus will be assumed
            path_schema_description: str = ''  # TODO: required, if the data-schema doesn't match the std-schema
    ):
        self.corpus_path = path_corpus
        self.corpus_name = path_corpus.split('/')[-1] if not corpus_name else corpus_name

        # current naming conventions TODO: define the csv-files produced from a corpus (path_schema_description)
        self.path_data_documents = os.path.join(path_corpus, "vert_documents.csv")
        self.path_data_segments = os.path.join(path_corpus, "vert_segments.csv")
        self.path_data_tokens = os.path.join(path_corpus, "vert_tokens.csv")
        self.path_data_forms = os.path.join(path_corpus, "vert_forms_.csv")  # (dynamically created)
        self.path_data_lemmata = os.path.join(path_corpus, "vert_lemmata_.csv")  # (dynamically created)
        self.path_data_tokens_ = os.path.join(path_corpus, "vert_tokens_.csv")  # (dynamically created)

        if not path_schema_description:  # std csv schema definitions
            self.documents = ["document_id", "char_range", "meta"]
            self.segments = ["segment_id", "char_range"]
            self.tokens = ["token_id", "form_id", "lemma_id", "xpos1", "xpos2", "char_range", "segment_id"]
        else: pass  # TODO: mapping; schema-conventions required (path_schema_description)

        self.export_data_as_csv()

    def export_data_as_csv(self):
        i_form, forms, i_lemma, lemmata = 1, {}, 1, {}
        with open(self.path_data_forms, "w") as fo_forms, open(
            self.path_data_lemmata, "w"
        ) as fo_lemmata:
            with open(self.path_data_tokens) as fi_tokens, open(
                self.path_data_tokens_, "w"
            ) as fo_tokens:
                for line in fi_tokens:
                    d = line.strip().split("\t")
                    form, lemma = d[1], d[2]
                    if form not in forms:
                        fo_forms.write("\t".join([str(i_form), str(form)]) + "\n")
                        forms[form] = i_form
                        i_form += 1
                    if lemma not in lemmata:
                        fo_lemmata.write("\t".join([str(i_lemma), str(lemma)]) + "\n")
                        lemmata[lemma] = i_lemma
                        i_lemma += 1
                    fo_tokens.write(
                        "\t".join(
                            [
                                d[0],
                                str(forms[d[1]]),
                                str(lemmata[d[2]]),
                                d[3],
                                d[4],
                                d[5],
                                d[6],
                            ]
                        )
                        + "\n"
                    )

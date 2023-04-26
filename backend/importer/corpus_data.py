#!/usr/bin/python
# -*- coding: utf8 -*-

from config import *


class CorpusData:

    """Corpus Data Processor
    - input: path to the corpus-data
    - output: csv-files (--> db-data-import)
    """

    def __init__(self, path_corpus):

        # SAMPLE-DATA (provided by Jonathan)
        self.path_data_documents = (
            PATH_BNC_DATA_DOCUMENTS  # TODO: extract data «documents» from corpus
        )
        self.path_data_segments = PATH_BNC_DATA_SEGMENTS  # TODO: " «segments» "
        self.path_data_tokens = PATH_BNC_DATA_TOKENS  # TODO: " «tokens» "
        self.path_data_forms = PATH_BNC_FORMS  # created from tokens
        self.path_data_lemmata = PATH_BNC_LEMMATA  # "
        self.path_data_tokens_ = PATH_BNC_TOKENS_  # tokens without duplicates

        # csv schema definitions
        self.documents = ["document_id", "char_range", "meta"]
        self.segments = ["segment_id", "char_range"]
        self.tokens = [
            "token_id",
            "form_id",
            "lemma_id",
            "xpos1",
            "xpos2",
            "char_range",
            "segment_id",
        ]

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

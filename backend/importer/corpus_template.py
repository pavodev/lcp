#!/usr/bin/env python3
# -*- coding: utf8 -*-

import os

from .config import PATH_BNC_SCRIPT_SCHEMA_SETUP


class CorpusTemplate:

    """Corpus Template Processor
    - input: path to corpus template ("CT")
    - output: psql-script (--> add new schema to db)"""

    def __init__(self, path_corpus_template: str = ""):

        self.name = "bnc1"  # (currently defined by the corpus template)

    # TODO
    @staticmethod
    def get_script_schema_setup() -> str:
        return PATH_BNC_SCRIPT_SCHEMA_SETUP  # currently provided by Jonathan

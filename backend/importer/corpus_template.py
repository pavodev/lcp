#!/usr/bin/env python3
# -*- coding: utf8 -*-


class CorpusTemplate:

    """ Corpus Template Processor
    - input: path to corpus template ("CT") TODO (Jonathan?)
    - output: sql-script which adds the new schema (depending on the ct) to the database
    """

    def __init__(self, path_corpus_template: str = "", path_to_schema_setup_script: str = ''):
        """ currently assumes, that the sql-script to create the new schema already exists """
        # TODO: create sql-script from corpus template (and remove path_to_schema_setup_script as param)
        self.path_to_schema_setup_script = path_to_schema_setup_script

    def get_path_to_schema_setup_script(self): return self.path_to_schema_setup_script

#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import psycopg2

from config import *
from CorpusTemplate import CorpusTemplate


class Importer:

    def __init__(self, config: DBConfig = DBConfig(), path_corpus_template: str = ''):
        self.db_config = config
        self.connection = None
        self.raw_connection = None
        self.cursor = None
        self.ct = CorpusTemplate(path_corpus_template)

    def connect(self):
        try:
            c = DBConfig().get4psycopg()
            self.connection = psycopg2.connect(c)
            self.cursor = self.connection.cursor()
        except:
            print(f"Cannot connect to database {self.db_config.name}")
        return self

    def add_schema(self, path_psql_script): os.system(f"psql {self.db_config.name} < {path_psql_script}")

    def import_corpus(self):
        # [schema-name, relation-name, src-path-csv, delimiter, force_null]
        for t in [[self.ct.name, "document", PATH_BNC_DATA_DOCUMENTS, '\t', ''],
                  [self.ct.name, "segment", PATH_BNC_DATA_SEGMENTS, '\t', ''],
                  [self.ct.name, "form", PATH_BNC_FORMS, '\t', ''],
                  [self.ct.name, "lemma", PATH_BNC_LEMMATA, '\t', ''],
                  [self.ct.name, "token0", PATH_BNC_TOKENS_, '\t', 'xpos1, xpos2']]:
            if t[4]: q = f"COPY {self.ct.name}.token0 " \
                         f"FROM '{PATH_BNC_TOKENS_}' " \
                         f"WITH (FORMAT CSV, DELIMITER '{t[3]}', FORCE_NULL (xpos1, xpos2));"
            else: q = f"COPY {t[0]}.{t[1]} FROM '{t[2]}' WITH (DELIMITER '{t[3]}');"
            self.cursor.execute(q)

    # TEST
    def get_rows(self): return self.cursor.fetchall()

    def print_tables(self):
        for t in ["document", "segment", "form", "lemma", "token0"]:
            self.cursor.execute(f"SELECT * FROM bnc1.{t};")
            for x in self.cursor.fetchall(): print(x)

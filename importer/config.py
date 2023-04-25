#!/usr/bin/python
# -*- coding: utf8 -*-

import os

# Note: postgresql "COPY" demands ABSOLUTE PATHS !
ROOT = '/'.join(os.path.abspath(__file__).split('/')[:-1])  # importer

# sample data provided by Jonathan
PATH_BNC_SCRIPT_SCHEMA_SETUP = f"{ROOT}/scripts/bnc.sql"  # schema
PATH_BNC_DATA_DOCUMENTS = f"{ROOT}/data/bnc/vert_documents.csv"  # data
PATH_BNC_DATA_SEGMENTS = f"{ROOT}/data/bnc/vert_segments.csv"
PATH_BNC_DATA_TOKENS = f"{ROOT}/data/bnc/vert_tokens.csv"

# newly created files (basing on PATH_BNC_TOKENS); can safely be deleted after the data import
PATH_BNC_LEMMATA = f"{ROOT}/data/bnc/vert_lemmata_.csv"
PATH_BNC_FORMS = f"{ROOT}/data/bnc/vert_forms_.csv"
PATH_BNC_TOKENS_ = f"{ROOT}/data/bnc/vert_tokens_.csv"


class DBConfig:

    """ general database configuration """

    def __init__(self,
        name="postgres",
        host="127.0.0.1",
        port="5432",
        user="schroffbe",
        pw='',
    ):
        self.name = name
        self.host = host
        self.port = port
        self.user = user
        self.pw = pw

    def get4psycopg(self):  # psycopg-init
        return f"dbname='{self.name}' user='{self.user}' host='{self.host}' password='{self.pw}'"

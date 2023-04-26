#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import psycopg2

from config import (
    PATH_BNC_SCRIPT_SCHEMA_SETUP,
    PATH_BNC_DATA_DOCUMENTS,
    PATH_BNC_DATA_SEGMENTS,
    PATH_BNC_DATA_TOKENS,
    PATH_BNC_LEMMATA,
    PATH_BNC_FORMS,
    PATH_BNC_TOKENS_,
)
from corpus_template import CorpusTemplate


class Importer:
    def __init__(
        self,
        path_corpus_template: str = "",
        connection=None,
    ):
        self.connection = connection
        self.ct = CorpusTemplate(path_corpus_template)

    async def add_schema(self, path_psql_script):
        # psql postgres ROOT = "/".join(os.path.abspath(__file__).split("/")[:-1]) f"{ROOT}/scripts/bnc.sql"
        os.system(f"psql {self.db_config.name} < {path_psql_script}")
        script = "CREATE SCHEMA..."
        params = tuple()
        async with self.connection:
            async with self.connection.cursor() as acur:
                await acur.execute(script, params)

    async def import_corpus(self):

        async with self.connection:
            async with self.connection.cursor() as acur:
                # [schema-name, relation-name, src-path-csv, delimiter, force_null]
                for t in [
                    [self.ct.name, "document", PATH_BNC_DATA_DOCUMENTS, "\t", ""],
                    [self.ct.name, "segment", PATH_BNC_DATA_SEGMENTS, "\t", ""],
                    [self.ct.name, "form", PATH_BNC_FORMS, "\t", ""],
                    [self.ct.name, "lemma", PATH_BNC_LEMMATA, "\t", ""],
                    [self.ct.name, "token0", PATH_BNC_TOKENS_, "\t", "xpos1, xpos2"],
                ]:
                    if t[4]:
                        q = (
                            "COPY %s.token0 "
                            "FROM '%s' "
                            "WITH (FORMAT CSV, DELIMITER '%s', FORCE_NULL (%s));"
                        )
                        params = (self.ct.name, PATH_BNC_TOKENS_, t[3], t[4])
                    else:
                        q = "COPY %s.%s FROM '%s' WITH (DELIMITER '%s');"
                        params = (t[0], t[1], t[2], t[3])
                    await acur.execute(q, params)
        return True

    # TEST
    def get_rows(self):
        return self.cursor.fetchall()

    def print_tables(self):
        for t in ["document", "segment", "form", "lemma", "token0"]:
            self.cursor.execute(f"SELECT * FROM bnc1.{t};")
            for x in self.cursor.fetchall():
                print(x)

#!/usr/bin/env python3
# -*- coding: utf8 -*-

from .corpus_data import CorpusData
from .corpus_template import CorpusTemplate


class Importer:

    def __init__(self, connection=None):
        self.connection = connection

    async def add_schema(self, corpus_template: CorpusTemplate) -> bool:
        """ reads/executes a sql-script to add a new database-schema to the database """
        with open(corpus_template.path_to_schema_setup_script) as fi: script = fi.read()
        async with self.connection:
            async with self.connection.cursor() as cur:
                await cur.execute(script, tuple())
        return True

    async def import_corpus(self, corpus_data: CorpusData) -> bool:
        """ reads csv-files (that is, the corpus) into the database """
        async with self.connection:
            async with self.connection.cursor() as cur:
                # TODO: generalization basing on ct-info (which defines relations/data)
                for t in [  # [schema-name, relation-name, src-path-csv, delimiter, force_null]
                    ["document", corpus_data.path_data_documents, "\t", ""],
                    ["segment", corpus_data.path_data_segments, "\t", ""],
                    ["form", corpus_data.path_data_forms, "\t", ""],
                    ["lemma", corpus_data.path_data_segments, "\t", ""],
                    ["token0", corpus_data.path_data_tokens_, "\t", "xpos1, xpos2"],
                ]:  # TODO: can any of the below be used as params? i don't know -- DANNY
                    if t[4]: q = (
                        f"COPY {corpus_data.corpus_name}.{t[0]} "
                        f"FROM {t[1]} "
                        f"WITH (FORMAT CSV, DELIMITER '{t[2]}', FORCE_NULL ({t[3]}));"
                    )
                    else: q = f"COPY {t[0]}.{t[1]} FROM {t[2]} WITH (DELIMITER {t[3]});"
                    await cur.execute(q, tuple())
        return True

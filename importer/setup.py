#!/usr/bin/python
# -*- coding: utf8 -*-

from config import DBConfig
from CorpusTemplate import CorpusTemplate
from CorpusData import CorpusData
from Importer import Importer


if __name__ == '__main__':

    ct = CorpusTemplate('fake/path/to/corpus_template/')
    corpus = CorpusData('fake/path/to/corpus/')
    corpus.export_data_as_csv()  # export files

    importer = Importer(config=DBConfig()).connect()
    importer.add_schema(ct.get_script_schema_setup())
    importer.import_corpus()  # import files

    # TEST
    # importer.cursor.execute("""SELECT version();""")
    # print(importer.get_rows())  # db-connection
    # importer.print_tables()  # data (all relations)

#!/usr/bin/env python3
# -*- coding: utf8 -*-

import os
import psycopg

from .corpus_data import CorpusData
from .corpus_template import CorpusTemplate
from .importer import Importer
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder


async def test():

    load_dotenv(override=True)

    USER = os.getenv("SQL_UPLOAD_USERNAME")
    PASSWORD = os.getenv("SQL_UPLOAD_PASSWORD")
    HOST = os.getenv("SQL_HOST")
    DBNAME = os.getenv("SQL_DATABASE")
    PORT = int(os.getenv("SQL_PORT", 25432))

    tunnel = SSHTunnelForwarder(
        os.getenv("SSH_HOST"),
        ssh_username=os.getenv("SSH_USER"),
        ssh_password=None,
        ssh_pkey=os.getenv("SSH_PKEY"),
        remote_bind_address=(HOST, PORT),
    )

    tunnel.start()

    connstr = (
        f"postgresql://{USER}:{PASSWORD}@localhost:{tunnel.local_bind_port}/{DBNAME}"
    )

    conn = await psycopg.AsyncConnection.connect(connstr)

    importer = Importer(connection=conn)
    await importer.add_schema(CorpusTemplate(path_to_schema_setup_script="PATH/TO/SCRIPT/REQUIRED"))
    await importer.import_corpus(CorpusData(path_corpus="PATH/TO/CORPUS/REQUIRED"))


if __name__ == "__main__":

    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
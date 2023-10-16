"""
Interface for interacting with lcpvian server

Not compiled to c!
"""
import asyncio
import json
import os
import sys

from .api import corpora, query
from .ddl_gen import main
from .dqd_parser import cmdline

COMMANDS = {"start", "lcpvian", "worker", "dqd", "ddl", "corpora", "query"}

command = next((i for i in reversed(sys.argv) if i in COMMANDS), "lcpvian")

if command == "lcpvian" or command == "start":
    from .app import start

    print("Starting application...")
    start()

elif command == "worker":
    from .worker import start_worker

    print("Starting worker...")
    start_worker()
elif command == "dqd":
    print("Parsing DQD...")

    cmdline()

elif command == "ddl":
    print("Creating DDL...")

    main(sys.argv[-1])

elif command == "corpora":
    types = {"lcp", "vian", "all"}
    app_type = next((x for x in reversed(sys.argv) if x in types), "all")
    res = asyncio.run(corpora(app_type))
    print(json.dumps(res, indent=4))

elif command == "query":
    corpus = next((i for i in sys.argv if i.isnumeric()), "1")
    if os.path.isfile(sys.argv[-1]):
        is_json = sys.argv[-1].endswith(".json")
        with open(sys.argv[-1], "r") as fo:
            data = json.load(fo) if is_json else fo.read()
    else:
        data = sys.argv[-1]
    asyncio.run(query(int(corpus), data))


else:
    print(f"Command not understood: {command}")

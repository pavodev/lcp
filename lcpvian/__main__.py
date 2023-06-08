"""
Interface for interacting with lcpvian server

Not compiled to c!
"""
import asyncio
import json
import sys

COMMANDS = {"start", "lcpvian", "worker", "dqd", "ddl", "corpora"}

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
    from .dqd_parser import cmdline

    cmdline()

elif command == "ddl":
    print("Creating DDL...")
    from .ddl_gen import main

    main()

elif command == "corpora":
    from .utils import corpora

    types = {"lcp", "vian", "all"}
    app_type = next((x for x in reversed(sys.argv) if x in types), "all")
    res = asyncio.run(corpora(app_type))
    print(json.dumps(res, indent=4))

else:
    print(f"Command not understood: {command}")

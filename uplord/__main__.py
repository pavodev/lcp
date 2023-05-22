"""
Interface for interacting with uplord server
"""
import sys

COMMANDS = {"start", "uplord", "worker", "dqd", "ddl"}

command = next(
    i for i in reversed(sys.argv) if i in COMMANDS or i.endswith("__main__.py")
)
if command.endswith("__main__.py"):
    command = "uplord"

if command == "uplord" or command == "start":
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

else:
    print(f"Command not understood: {command}")

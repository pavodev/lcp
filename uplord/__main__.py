"""
Interface for interacting with uplord server
"""

import asyncio
import sys

import uvloop

command = next(i for i in reversed(sys.argv) if not i.startswith("-"))

if command == "uplord" or command == "start" or command.endswith("__main__.py"):
    from .app import start

    print("Starting application...")
    start()

elif command == "worker":
    from .worker import start_worker

    print("Starting worker...")
    start_worker()
else:
    print(f"Command not understood: {command}")

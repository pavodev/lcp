#!/usr/bin/env python3

"""
Run various commands for LCP -- could add argparse etc if they take options
"""

import os
import subprocess
import traceback

from time import sleep

from .utils import load_env

FE_INSTALL = "yarn install"
FE_BUILD = "yarn build"
FE_SERVE = "yarn serve"
WORKER_START = "lcp-worker"
LCP = "lcp"

load_env()


ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
EDROPS_DIR = os.path.join(ROOT, "vian-eventdrops")
KILL_PORT = f"kill -9 `lsof -t -i:{os.getenv('AIO_PORT', '9090')}`"


def build():
    print("=============CALL BUILD================")
    os.chdir(FRONTEND_DIR)
    return subprocess.Popen(FE_BUILD.split())


def edrop():
    print("=============CALL EDROP================")
    os.chdir(EDROPS_DIR)
    return subprocess.Popen(FE_INSTALL.split())


def install():
    print("=============CALL INSTALL================")
    edrop().wait()
    os.chdir(FRONTEND_DIR)
    return subprocess.Popen(FE_INSTALL.split())


def serve():
    print("=============CALL SERVE================")
    os.chdir(FRONTEND_DIR)
    return subprocess.Popen(FE_SERVE.split())


def setup():
    print("=============CALL SETUP================")
    install().wait()
    build().wait()
    print("Finished! You can now run `lcp-frontend-serve` to run the frontend...")


def start_all() -> None:
    """
    Todo: all of this but properly
    """
    try:
        subprocess.Popen(KILL_PORT, shell=True).wait()
    except:
        pass
    commands = [serve()]
    sleep(15)
    print("START WORKER")
    commands.append(subprocess.Popen([WORKER_START]))
    sleep(15)
    print("START LCP")
    commands.append(subprocess.Popen([LCP]))
    sleep(15)
    print(f"Running {len(commands)} commands")
    try:
        while True:
            for c in commands:
                if (x := c.poll()) is not None:
                    print(f"Commmand {c} gave {x}")
                    break
                sleep(10)
    except (Exception, KeyboardInterrupt) as err:
        tb = traceback.format_exc()
        print(f"Error: {err}\n{tb}")
    finally:
        try:
            subprocess.Popen(KILL_PORT, shell=True).wait()
        except:
            pass
        for c in commands:
            try:
                c.terminate()
            except:
                pass
            try:
                c.kill()
            except:
                pass
    return None

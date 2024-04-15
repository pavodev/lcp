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
FE_YARN = "yarn"
WORKER_START = "lcp-worker"
NPM_INSTALL = "npm install"
LCP = "lcp"

load_env()


ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")

FRONTEND_SRC = os.path.join(FRONTEND_DIR, "src")
EDROPS_DIR = os.path.join(ROOT, "vian-eventdrops")
KILL_PORT = f"kill -9 `lsof -t -i:{os.getenv('AIO_PORT', '9090')}`"


def npm_install():
    return subprocess.Popen(NPM_INSTALL.split(), cwd=FRONTEND_SRC)


def yarn():
    return subprocess.Popen(FE_YARN.split(), cwd=FRONTEND_SRC)


def build():
    install().wait()
    return subprocess.Popen(FE_BUILD.split(), cwd=FRONTEND_SRC)


def edrop():
    return subprocess.Popen(FE_INSTALL.split(), cwd=EDROPS_DIR)


def install():
    return subprocess.Popen(FE_INSTALL.split(), cwd=FRONTEND_SRC)


def serve():
    return subprocess.Popen(FE_SERVE.split(), cwd=FRONTEND_SRC)


def setup():
    print("=============CALL SETUP================")
    edrop().wait()
    yarn().wait()
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
    commands.append(subprocess.Popen([WORKER_START], cwd=ROOT))
    sleep(15)
    commands.append(subprocess.Popen([LCP], cwd=ROOT))
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

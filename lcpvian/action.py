#!/usr/bin/env python3

"""
Run various commands for LCP -- could add argparse etc if they take options
"""

import os
import subprocess
import traceback

from time import sleep

from .utils import load_env

FE_INSTALL = "npm install"
FE_BUILD_CP = "npm run build:catchphrase"
FE_SERVE_CP = "npm run serve:catchphrase"
FE_BUILD_CP = "npm run build:catchphrase"
FE_SERVE_CP = "npm run serve:catchphrase"
FE_BUILD_SS = "npm run build:soundscape"
FE_SERVE_SS = "npm run serve:soundscape"
FE_BUILD_SS = "npm run build:soundscape"
FE_SERVE_SS = "npm run serve:soundscape"
WORKER_START = "lcp-worker"
LCP = "lcp"

load_env()


ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
EDROPS_DIR = os.path.join(ROOT, "vian-eventdrops")
KILL_PORT = f"kill -9 `lsof -t -i:{os.getenv('AIO_PORT', '9090')}`"


def npm_install():
    return subprocess.Popen(FE_INSTALL.split(), cwd=FRONTEND_DIR)


def edrop():
    return subprocess.Popen(FE_INSTALL.split(), cwd=EDROPS_DIR)


def build(ss: bool = False):
    npm_install().wait()
    cmd = FE_BUILD_SS if ss else FE_BUILD_CP
    return subprocess.Popen(cmd.split(), cwd=FRONTEND_DIR)


def serve(ss: bool = False):
    cmd = FE_SERVE_SS if ss else FE_SERVE_CP
    return subprocess.Popen(cmd.split(), cwd=FRONTEND_DIR)


def serve_ss():
    return serve(ss=True)


def serve_cp():
    return serve(ss=False)


def setup_cp():
    edrop().wait()
    npm_install().wait()
    build().wait()
    print("Finished! You can now run `lcp-frontend-serve` to run the frontend...")


def setup_ss():
    edrop().wait()
    npm_install().wait()
    build(ss=True).wait()
    print("Finished! You can now run `lcp-frontend-serve` to run the frontend...")


def start_app(ss: bool = False) -> None:
    """
    Todo: all of this but properly
    """
    if ss:
        server = serve_ss
    else:
        server = serve_cp
    try:
        subprocess.Popen(KILL_PORT, shell=True).wait()
    except:
        pass
    commands = [server()]
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
    except BaseException as err:
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


def start_cp():
    return start_app(ss=False)


def start_ss():
    return start_app(ss=True)

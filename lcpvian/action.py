#!/usr/bin/env python3

"""
Run various commands for LCP -- could add argparse etc if they take options
"""

import os
import subprocess
import traceback

from time import sleep

from .utils import load_env

load_env()


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

ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
KILL_PORT = f"kill -9 `lsof -t -i:{os.getenv('AIO_PORT', '9090')}`"


def npm_install() -> subprocess.Popen:
    return subprocess.Popen(FE_INSTALL.split(), cwd=FRONTEND_DIR)


def build(ss: bool = False) -> subprocess.Popen:
    npm_install().wait()
    cmd = FE_BUILD_SS if ss else FE_BUILD_CP
    return subprocess.Popen(cmd.split(), cwd=FRONTEND_DIR)


def serve(ss: bool = False) -> subprocess.Popen:
    cmd = FE_SERVE_SS if ss else FE_SERVE_CP
    return subprocess.Popen(cmd.split(), cwd=FRONTEND_DIR)


def serve_ss() -> subprocess.Popen:
    """
    Serve all processes needed for soundscript
    """
    return serve(ss=True)


def serve_cp() -> subprocess.Popen:
    """
    Serve all processes needed for catchphrase
    """
    return serve(ss=False)


def setup_cp() -> None:
    """
    Build catchphrase project
    """
    npm_install().wait()
    build().wait()
    print(
        "Finished! You can now run `lcp-frontend-serve` to run the catchphrase frontend..."
    )
    return None


def setup_ss():
    """
    Build soundscipt project
    """
    npm_install().wait()
    build(ss=True).wait()
    print(
        "Finished! You can now run `lcp-frontend-serve` to run the soundscript frontend..."
    )
    return None


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


def start_cp() -> None:
    return start_app(ss=False)


def start_ss() -> None:
    return start_app(ss=True)

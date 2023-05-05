import os
import sys

from setuptools import setup

from mypyc.build import mypycify

MODULE_PATH = "backend"

SKIPS = {"sock.py", "dqd_parser.py"}  # todo: make the files in here work

# use build_ext to do mypy c compilation
if any(a == "build_ext" for a in sys.argv):
    files = ["run.py", "worker.py"]
    for i in os.listdir(MODULE_PATH):
        if i not in SKIPS and i.endswith(".py"):
            files.append(os.path.join(MODULE_PATH, i))
    ext_modules = mypycify(files, multi_file=True, separate=False, verbose=True)
else:
    ext_modules = None

with open("requirements.txt") as f:
    REQUIRED = [i for i in f.read().splitlines() if i and not i.strip().startswith("#")]


def read(fname):
    """
    Helper to read README
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read().strip()


setup(
    name="uplord",
    version="0.0.1",
    description="corpus linguistics app",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://gitlab.uzh.ch/LiRI/projects/uplord",
    author="Danny McDonald",
    include_package_data=True,
    zip_safe=False,
    packages=[MODULE_PATH],
    package_data={
        MODULE_PATH: ["backend/py.typed"],
    },
    author_email="mcddjx@gmail.com",
    license="MIT",
    keywords=["corpus", "linguistics"],
    install_requires=REQUIRED,
    ext_modules=ext_modules,
)

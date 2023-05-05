import os

from setuptools import setup

ext_modules = None

# if these lines are used, we build a mypy version of the app that fails
# whenever types do not match exactly (!)

from mypyc.build import mypycify

files = ["run.py"]
for i in os.listdir("backend"):
    if "query" not in i and i.endswith(".py"):  # todo: make query work
        files.append(os.path.join("backend", i))

ext_modules = mypycify(files, multi_file=True, separate=False, verbose=True)

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
    packages=["backend"],
    package_data={
        "backend": ["backend/py.typed"],
    },
    author_email="mcddjx@gmail.com",
    license="MIT",
    keywords=["corpus", "linguistics"],
    install_requires=REQUIRED,
    ext_modules=ext_modules,
)

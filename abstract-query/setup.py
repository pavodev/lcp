import os
import sys

from setuptools import setup

if any(a == "build_ext" for a in sys.argv):
    from mypyc.build import mypycify

    ext_modules = mypycify(["abstract_query"], opt_level="3", debug_level="1")
else:
    ext_modules = []

required = []
with open("requirements.txt") as f:
    required = [
        i.split(" #")[0].strip()
        for i in f.read().splitlines()
        if i
        and not i.strip().startswith("#")
        and not i.strip().startswith("-r")
        and "git+" not in i
    ]
    required.append(
        "backports.zoneinfo @ http://github.com/morganwahl/zoneinfo/tarball/master#egg=zoneinfo-0.2.1"
    )


def read(fname):
    """
    Helper to read README
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read().strip()


setup(
    name="abstract_query",
    version="0.0.1",  # DO NOT EDIT THIS LINE MANUALLY. LET bump2version UTILITY DO IT
    description="abstract query representation",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://gitlab.uzh.ch/LiRI/projects/abstract-query",
    author="Danny McDonald",
    include_package_data=True,
    zip_safe=False,
    packages=["abstract_query"],
    author_email="mcddjx@gmail.com",
    license="MIT",
    keywords=["corpus", "linguistics"],
    install_requires=required,
    ext_modules=ext_modules,
)

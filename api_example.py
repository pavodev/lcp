#! /usr/bin/env python3

import argparse
import json
import os
import sys

from time import sleep

import requests


CREATE_URL = "http://localhost:9090/create"
UPLOAD_URL = "http://localhost:9090/upload"

VALID_EXTENSIONS = ("vrt", "csv")
COMPRESSED_EXTENTIONS = ("zip", "tar", "tar.gz", "tar.xz", "7z")


def _parse_cmd_line():
    """
    Helper for parsing CLI call and displaying help message
    """
    parser = argparse.ArgumentParser(description="Upload corpus to LCP")
    # parser.add_argument("corpus", type=str, help="Input file or folder path")
    parser.add_argument(
        "-c",
        "--corpus",
        type=str,
        required=True,
        help="Corpus path",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        required=True,
        help="Username",
    )
    parser.add_argument(
        "-k",
        "--api-key",
        type=str,
        required=True,
        help="API_KEY",
    )
    parser.add_argument(
        "-t",
        "--template",
        type=str,
        required=False,
        help="Template filepath",
    )

    kwargs = vars(parser.parse_args())
    return kwargs


def main(
    corpus: str = "", api_key: str = "", user: str = "", template: str = ""
) -> None:

    filt = None
    if os.path.isfile(corpus):
        base = os.path.dirname(corpus)
        filt = os.path.basename(base)
    else:
        base = corpus

    if not template and os.path.isfile(corpus):
        print("Error: no template specified and corpus is not a directory")
        return
    elif not template and os.path.isdir(corpus):
        template = next((i for i in os.listdir(corpus) if i.endswith(".json")), None)
        if template is None:
            print("Error: no template specified and no JSON found in corpus directory.")
            return
        template = os.path.join(corpus, template)
        print(f"Using template: {template}")

    headers = {"Content-Type": None}

    with open(template, "r") as fo:
        template_data = json.load(fo)

    params = {"user": user, "key": api_key, "template": template_data}

    print("Sending template...")
    resp = requests.post(CREATE_URL, headers=headers, json=params)

    sleep(3)

    print("Checking validity...")

    data = resp.json()

    project = data["project"]

    params.pop("template")
    params["project"] = project

    if os.path.isdir(corpus):

        files = {
            os.path.splitext(p)[0]: open(os.path.join(base, p), "rb")
            for p in os.listdir(base)
        }
        if filt:
            files = {
                k: v
                for k, v in files.items()
                if filt in k and k.endswith(VALID_EXTENSIONS + COMPRESSED_EXTENSIONS)
            }
    else:
        files = {os.path.splitext(corpus)[0]: open(corpus, "rb")}

    print("Sending data...")

    resp = requests.post(UPLOAD_URL, params=params, headers=headers, files=files)

    sleep(5)

    print("Checking validity...")

    data = resp.json()
    if "target" not in data:
        print(f"Failed: {data}")
        return
    new_url = data["target"]

    while True:
        print("Checking progress...")
        resp = requests.post(new_url, params=params)
        data = resp.json()
        print(data)
        if data["status"] in {"failed", "finished"}:
            break
        sleep(8)


if __name__ == "__main__":
    kwargs = _parse_cmd_line()
    main(**kwargs)

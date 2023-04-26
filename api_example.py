#! /usr/bin/env python3

import argparse
import json
import os
import sys

from time import sleep

import requests


CREATE_URL = "http://localhost:9090/create"
UPLOAD_URL = "http://localhost:9090/upload"


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
        required=True,
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
            files = {k: v for k, v in files.items() if filt in k and k.endswith(".csv")}
    else:
        files = {os.path.splitext(corpus)[0]: corpus}

    print("Sending data...")

    resp = requests.post(UPLOAD_URL, params=params, headers=headers, files=files)

    print("Checking validity...")

    sleep(5)

    data = resp.json()
    new_url = data["target"]

    while True:
        print("Checking progress...")
        resp = requests.post(new_url, params=params)
        data = resp.json()
        print(data)
        if data["status"] in {"failed", "finished"}:
            break
        sleep(3)


if __name__ == "__main__":
    kwargs = _parse_cmd_line()
    main(**kwargs)

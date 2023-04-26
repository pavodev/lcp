#! /usr/bin/env python3

import json
import os

import requests

from time import sleep


API_KEY = "YOUR_KEY_HERE"
USERNAME = "YOUR_USERNAME_HERE"
CREATE_URL = "http://localhost:9090/create"
UPLOAD_URL = "http://localhost:9090/upload"

template_path = sys.argv[-1]
base = sys.argv[-2]
filt = None
if os.path.isfile(base):
    base = os.path.dirname(base)
    filt = os.path.basename(base)

headers = {"Content-Type": None}

with open(template_path, "r") as fo:
    template_data = json.load(fo)

params = {"user": USERNAME, "key": API_KEY, "template": template_data}

print("Sending template...")
resp = requests.post(CREATE_URL, headers=headers, params=params)

time.sleep(3)

print("Checking validity...")

data = resp.json()
project = data["project"]

params.pop("template")
params["project"] = project

files = {
    os.path.splitext(p): open(os.path.join(base, p), "rb") for p in os.listdir(base)
}
if filt:
    files = {k: v for k, v in files.items() if filt in k}

print("Sending data...")

resp = requests.post(URL, params=params, headers=headers, files=files)

print("Checking validity...")
time.sleep(5)

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

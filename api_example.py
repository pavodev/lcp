#! /usr/bin/env python3

import requests
from time import sleep


API_KEY = "YOUR_KEY_HERE"
USERNAME = "YOUR_USERNAME_HERE"
URL = "http://localhost:9090/upload"

params = {"user": USERNAME, "key": API_KEY}
headers = {"Content-Type": None}
files = {
    "file": open("/home/danny/work/corpert/digitest2.vrt", "rb"),
    "config": open("/home/danny/work/corpert/corpus.json", "rb"),
}
resp = requests.post(URL, params=params, headers=headers, files=files)
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

#!/usr/bin/env python3
"""测试期自动接单：/tmp/map_override 存在且当前没有单时，自动下一单。"""
import json, time, urllib.request, pathlib

def get(p):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:8765"+p, timeout=5).read().decode())

def post(p):
    r=urllib.request.Request("http://127.0.0.1:8765"+p, data=b"", headers={"Content-Type":"application/json"})
    return urllib.request.urlopen(r, timeout=5).read()

while True:
    try:
        if pathlib.Path("/tmp/map_override").exists():
            d=get("/delivery")
            if not d.get("order"):
                post("/delivery/new")
    except Exception:
        pass
    time.sleep(3)

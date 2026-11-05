#!/usr/bin/env python3
"""盯礼物 → 跑单反应，写 /tmp/gift_watch.log。测试期间用。"""
import json, time, urllib.request, pathlib

LOG = pathlib.Path("/tmp/gift_watch.log")
BASE = "http://127.0.0.1:8765"

def get(p):
    with urllib.request.urlopen(BASE + p, timeout=5) as r:
        return json.loads(r.read().decode())

last = {"tips": None, "left": None, "place": None, "status": None}
LOG.write_text("")
while True:
    try:
        s = get("/sing_state"); d = get("/delivery")
        line = None
        if s["tips"] != last["tips"]:
            line = f"礼物 累计 {s['tips']} 次 / {s['coins']} 币 | 最近 {s.get('last_tip')}"
            last["tips"] = s["tips"]
        if d.get("order") and d["left"] != last["left"]:
            if last["left"] is not None and last["left"] - d["left"] > 4:
                line = (line or "") + f" | 加急 {last['left']}→{d['left']}s"
            last["left"] = d["left"]
        if d.get("order") and d["order"]["place_name"] != last["place"]:
            line = (line or "") + f" | 新单 {d['order']['place_name']} +{d['order']['pay']}"
            last["place"] = d["order"]["place_name"]
            last["left"] = d["left"]
        if not d.get("order"):
            last["place"] = None; last["left"] = None
        if line:
            LOG.open("a").write(f"[{time.strftime('%H:%M:%S')}] {line}\n")
    except Exception as e:
        LOG.open("a").write(f"[{time.strftime('%H:%M:%S')}] err {e}\n")
    time.sleep(1)

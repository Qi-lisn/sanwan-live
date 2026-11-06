#!/usr/bin/env python3
"""兜底：从直播伴侣日志里捡礼物事件，喂给 /tip。

抖音不给未登录的第三方连接推 WebcastGiftMessage，但伴侣能收到，
它的日志里有 GIFT_QUEUE 汇总行：target_id=3992 ... count=N
这里按 gift_id 事件去重后触发。
"""
import json, os, re, time, pathlib, urllib.request

LOGDIR = pathlib.Path.home() / "Library/Logs/Douyin Webcast Mate"
API = "http://127.0.0.1:8765/tip"
NAME = {"463": "玫瑰", "3992": "小心心", "3993": "点赞"}

def log(m):
    with open("/tmp/gift_from_mate.log", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {m}\n")

def post(gid, cnt):
    body = json.dumps({"nick": "观众", "gift": NAME.get(gid, gid), "count": cnt,
                       "value": cnt}, ensure_ascii=False).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=4).read()

seen = set()
pos = {}
_init = sorted(LOGDIR.glob("*.log"), key=lambda x: x.stat().st_mtime)
if _init:
    pos[str(_init[-1])] = _init[-1].stat().st_size   # 从末尾开始，不回放历史
while True:
    try:
        logs = sorted(LOGDIR.glob("*.log"), key=lambda p: p.stat().st_mtime)
        if not logs:
            time.sleep(2); continue
        p = logs[-1]
        off = pos.get(str(p), 0)
        with p.open("r", errors="ignore") as f:
            f.seek(off)
            chunk = f.read()
            pos[str(p)] = f.tell()
        for m in re.finditer(r"\[GIFT_QUEUE\].*target_id=(\d+).*?count=(\d+).*?last_msg_id=([\w_]+)", chunk):
            gid, cnt, mid = m.group(1), int(m.group(2)), m.group(3)
            if mid in seen:
                continue
            seen.add(mid)
            post(gid, max(1, cnt))
            log(f"gift id={gid} count={cnt} mid={mid}")
    except Exception as e:
        log(f"err {e}")
    time.sleep(2)

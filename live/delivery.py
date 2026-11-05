"""外卖小游戏：状态机 + 地图坐标。

状态: idle → accepted(去取餐) → carrying(配送中) → idle
超时扣钱，送达加钱。
"""
from __future__ import annotations
import random, time

# 地图坐标（1920×1080 舞台内，左上角为原点）
PLACES = [
    dict(id="office",  name="公司",     x=470,  y=640, kind="start"),
    dict(id="shop",    name="便利店",   x=760,  y=480),
    dict(id="community", name="小区",   x=1180, y=700),
    dict(id="school",  name="学校",     x=1340, y=330),
    dict(id="hospital", name="医院",    x=980,  y=250),
    dict(id="mall",    name="商场",     x=1520, y=560),
]

GOODS = ["奶茶", "炒饭", "麻辣烫", "炸鸡", "两杯咖啡", "一份饺子", "烧烤", "蛋糕"]

_state = dict(status="idle", order=None, progress=0.0, started=0.0, deadline=0.0,
              earned=0.0, delivered=0, late=0, total=0, last_result="", wage=1.0, rating="正常")
_seq = {"n": 0}


def _place(pid):
    return next(p for p in PLACES if p["id"] == pid)


def new_order(now=None, rng=None, place=None):
    now = time.time() if now is None else now
    rng = rng or random
    pool = [p for p in PLACES if p["id"] != "office"]
    if place:
        hit = [p for p in pool if p["id"] == place or p["name"] == place]
        dest = hit[0] if hit else rng.choice(pool)
    else:
        dest = rng.choice(pool)
    good = rng.choice(GOODS)
    dist = abs(dest["x"] - 470) / 1000 + abs(dest["y"] - 640) / 700
    pay = round(3.5 + dist * 3.0 + rng.random() * 1.5, 1)
    if place:
        pay = round(pay * 1.4, 1)          # 指定地点加价 40%
    limit = 45 + int(dist * 40)          # 秒
    _seq["n"] += 1
    _state.update(status="accepted", order=dict(seq=_seq["n"], good=good, place=dest["id"],
                  place_name=dest["name"], x=dest["x"], y=dest["y"], pay=pay,
                  limit=limit, accepted_at=now), progress=0.0,
                  started=now, deadline=now + limit, last_result="")
    _state["total"] += 1
    return _state["order"]


def rush(seconds=15, now=None):
    """打赏加急：剩余时间减少。"""
    if _state["status"] not in ("accepted", "carrying") or not _state["order"]:
        return 0
    o = _state["order"]
    o["limit"] = max(10, o["limit"] - seconds)   # 截止时间提前
    _state["last_result"] = f"加急 少 {seconds} 秒"
    return seconds


def pickup(now=None):
    now = time.time() if now is None else now
    if _state["status"] != "accepted":
        return False
    _state["status"] = "carrying"
    _state["started"] = now
    o = _state["order"]
    o["carry_at"] = now
    return True


def deliver(now=None):
    now = time.time() if now is None else now
    if _state["status"] != "carrying":
        return False
    o = _state["order"]
    late = now > o["accepted_at"] + o["limit"]
    if late:
        _state["late"] += 1
        _state["earned"] = round(_state["earned"] - 2.0, 1)
        _state["last_result"] = "超时了 扣两块"
        if _state["late"] >= 3:
            _state["wage"] = 0.8
            _state["rating"] = "差评 工资八折"
    else:
        _state["delivered"] += 1
        _state["earned"] = round(_state["earned"] + o["pay"], 1)
        _state["last_result"] = f"送到 {o['place_name']} 赚 {o['pay']} 块"
    _state.update(status="idle", order=None, progress=1.0)
    return True


def tick(now=None):
    now = time.time() if now is None else now
    if _state["status"] == "idle":
        return
    o = _state["order"]
    if not o:
        return
    total = max(1, o.get("carry_at", o["accepted_at"] + 8) - o["accepted_at"] + o["limit"] * 0.6)
    _state["progress"] = min(1.0, max(0.0, (now - o["accepted_at"]) / total))
    if _state["status"] == "accepted" and now - o["accepted_at"] > o["limit"] * 0.5:
        pickup(now)
    if now > o["accepted_at"] + o["limit"]:
        deliver(now)


def snapshot(now=None):
    tick(now)
    now = time.time() if now is None else now
    o = _state["order"]
    out = {"status": _state["status"], "progress": round(_state["progress"], 3),
           "earned": _state["earned"], "delivered": _state["delivered"],
           "late": _state["late"], "total": _state["total"], "places": PLACES,
           "wage": _state["wage"], "rating": _state["rating"],
           "last_result": _state["last_result"]}
    if o:
        out["order"] = {k: o[k] for k in ("seq", "good", "place_name", "x", "y", "pay", "limit")}
        out["left"] = max(0, round(o["accepted_at"] + o["limit"] - (time.time() if now is None else now)))
    return out


def reset():
    global _state
    _state = dict(status="idle", order=None, progress=0.0, started=0.0, deadline=0.0,
                  earned=0.0, delivered=0, late=0, total=0, last_result="", wage=1.0, rating="正常")


def qa_force_late(n=3):
    """仅用于验收：把超时次数与评分直接置位。"""
    _state["late"] = n
    _state["wage"] = 0.8
    _state["rating"] = "差评 工资八折"
    _state["last_result"] = "超时三次 差评"

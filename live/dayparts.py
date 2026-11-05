"""时段表：三万的一天。

时间用「当天分钟」表示，跨午夜的时段用 >1440 的值（例如 23:00-02:00 → 1380..1560）。
"""
from __future__ import annotations
import datetime as _dt

def _m(h, m=0): return h * 60 + m

# start/end 为当天分钟；end 可 >1440 表示跨日
BLOCKS = [
    dict(id="morning",   name="早班",     start=_m(6),    end=_m(10),   light="day",   energy=0.9, song_rate=0.10, map=False,
         intro="早班 开始干活"),
    dict(id="forenoon",  name="上午场",   start=_m(10),   end=_m(12),   light="day",   energy=0.8, song_rate=0.08, map=False,
         intro="上午场 人不多 正好摸鱼"),
    dict(id="lunch",     name="午高峰",   start=_m(12),   end=_m(14),   light="day",   energy=1.0, song_rate=0.04, map=True,
         intro="午高峰 跑单去了"),
    dict(id="afternoon", name="下午场",   start=_m(14),   end=_m(17),   light="day",   energy=0.7, song_rate=0.07, map=False,
         intro="下午场 有点困"),
    dict(id="dinner",    name="晚高峰",   start=_m(17),   end=_m(20),   light="dusk",  energy=1.0, song_rate=0.04, map=True,
         intro="晚高峰 再跑两单"),
    dict(id="prime",     name="黄金场",   start=_m(20),   end=_m(23),   light="warm",  energy=1.0, song_rate=0.14, map=False,
         intro="黄金场 唱歌"),
    dict(id="story",     name="故事场",   start=_m(23),   end=_m(2, 0)+24*60, light="dark", energy=0.4, song_rate=0.05, map=False,
         intro="故事场 说点慢的"),
    dict(id="sleep",     name="睡眠电台", start=_m(2),    end=_m(6),    light="black", energy=0.2, song_rate=0.02, map=False,
         intro="睡了 留个声音给你"),
]

_BY_ID = {b["id"]: b for b in BLOCKS}

def _minutes(now: _dt.datetime | None = None) -> int:
    now = now or _dt.datetime.now()
    return now.hour * 60 + now.minute

def _match(now: _dt.datetime | None = None):
    m = _minutes(now)
    for b in BLOCKS:
        for c in (m, m + 24 * 60):
            if b["start"] <= c < b["end"]:
                return b, c
    return _BY_ID["sleep"], m

def block_at(now: _dt.datetime | None = None) -> dict:
    return _match(now)[0]

def next_block(now: _dt.datetime | None = None) -> dict:
    cur = block_at(now)
    i = BLOCKS.index(cur)
    return BLOCKS[(i + 1) % len(BLOCKS)]

def seconds_left(now: _dt.datetime | None = None) -> int:
    now = now or _dt.datetime.now()
    b, c = _match(now)
    return max(0, (b["end"] - c) * 60 - now.second)

def snapshot(now: _dt.datetime | None = None) -> dict:
    b = block_at(now)
    return {"id": b["id"], "name": b["name"], "light": b["light"], "energy": b["energy"],
            "map": b["map"], "intro": b["intro"], "seconds_left": seconds_left(now),
            "next": next_block(now)["name"]}

def pack_lines(block_id: str, limit: int = 200) -> list[str]:
    from pathlib import Path
    p = Path(__file__).with_name("packs") / f"{block_id}.txt"
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()][:limit]

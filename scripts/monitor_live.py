#!/usr/bin/env python3
"""直播巡检（只读）：不重启、不改配置，只观察并记录异常。

每 30s 采样一次，写 /tmp/live_monitor.log；
异常写 ALERT 行，状态写 /tmp/live_monitor_status.json。
"""
import json, os, subprocess, time, urllib.request, pathlib, shutil

LOG = pathlib.Path("/tmp/live_monitor.log")
STATUS = pathlib.Path("/tmp/live_monitor_status.json")
BASE = "http://127.0.0.1:8765"
INTERVAL = 30
DANMAKU_LOG = pathlib.Path("/tmp/danmaku.out")

state = {"start": time.time(), "last_lines": -1, "last_lines_change": time.time(),
         "last_audio": time.time(), "alerts": []}

def log(msg):
    LOG.open("a").write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

def alert(msg):
    state["alerts"].append({"t": time.strftime("%H:%M:%S"), "msg": msg})
    state["alerts"] = state["alerts"][-20:]
    log(f"ALERT {msg}")

def get(path, timeout=6):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode())

def proc_alive(pat):
    try:
        out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, timeout=5)
        return bool(out.stdout.strip())
    except Exception:
        return False

def companion_fresh():
    d = pathlib.Path.home() / "Library/Logs/Douyin Webcast Mate"
    logs = sorted(d.glob("*.log"), key=lambda x: x.stat().st_mtime) if d.exists() else []
    if not logs: return None, None
    return time.time() - logs[-1].stat().st_mtime, logs[-1]

def room_ids():
    import re
    try:
        txt = (pathlib.Path.home() / "Library/Logs/Douyin Webcast Mate").glob("*.log")
        latest = sorted(txt, key=lambda x: x.stat().st_mtime)[-1].read_text(errors="ignore")
        cur = re.findall(r"room_id=(\d+)", latest)
        cur = cur[-1] if cur else None
    except Exception:
        cur = None
    got = None
    try:
        out = DANMAKU_LOG.read_text(errors="ignore")
        m = re.findall(r"connecting room (\d+)", out)
        got = m[-1] if m else None
    except Exception:
        pass
    return cur, got

def danmaku_quiet_seconds():
    try:
        return time.time() - DANMAKU_LOG.stat().st_mtime
    except Exception:
        return None

def once():
    now = time.time()
    status = {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        s = get("/stats"); a = get("/action_state"); c = get("/caption"); g = get("/sing_state")
        status.update({"lines": s["lines"], "replies": s["replies"], "uptime": round(s["uptime"]),
                       "activity": a["activity"], "auto_actions": a["auto_actions"],
                       "level": round(c.get("level", 0), 2), "song": g.get("title") or None,
                       "coins": g.get("coins")})
        if s["uptime"] < 120 and s["uptime"] < (now - state["start"]):
            alert("服务疑似重启（uptime 归零）")
        if s["lines"] != state["last_lines"]:
            state["last_lines"] = s["lines"]; state["last_lines_change"] = now
        elif now - state["last_lines_change"] > 600:
            alert(f"{int(now-state['last_lines_change'])}s 没有新台词")
        if c.get("level", 0) > 0.01:
            state["last_audio"] = now
        elif now - state["last_audio"] > 300:
            alert(f"{int(now-state['last_audio'])}s 没有音频输出")
    except Exception as e:
        alert(f"服务不可达: {e}")
        status["service"] = "DOWN"

    status["danmaku_proc"] = proc_alive("danmaku.py")
    if not status["danmaku_proc"]:
        alert("弹幕进程不在")
    q = danmaku_quiet_seconds()
    status["danmaku_log_age"] = round(q) if q is not None else None
    if q is None:
        alert("弹幕日志不存在")
    elif q > 120:
        alert(f"弹幕日志 {int(q)}s 没更新（可能断线）")
    age, lg = companion_fresh()
    status["companion_log_age"] = round(age) if age is not None else None
    if age is not None and age > 120:
        alert(f"伴侣日志 {int(age)}s 没更新（可能已下播/卡死）")
    cur_room, dm_room = room_ids()
    status["room_current"], status["room_danmaku"] = cur_room, dm_room
    if cur_room and dm_room and cur_room != dm_room:
        alert(f"弹幕房间不一致: 当前 {cur_room} vs 弹幕 {dm_room}")
    status["disk_free_gb"] = round(shutil.disk_usage("/").free / 1e9, 1)
    if status["disk_free_gb"] < 5:
        alert(f"磁盘剩余 {status['disk_free_gb']}GB")

    status["alerts"] = state["alerts"][-5:]
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1))
    log(json.dumps(status, ensure_ascii=False))
    return status

if __name__ == "__main__":
    log("monitor start")
    while True:
        try:
            once()
        except Exception as e:
            log(f"monitor error: {e}")
        time.sleep(INTERVAL)

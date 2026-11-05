#!/usr/bin/env python3
"""三万 · 豆包语音合成（新版 API Key）

逐句合成 -> 下载 mp3 -> 记录时长，供渲染器排时间轴。
"""
import json, os, pathlib, subprocess, sys, time, uuid
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "audio"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://openspeech.bytedance.com"
RESOURCE = "seed-tts-2.0"

LINES = [
    "哈喽呀，初次见面",
    "我是三万大肥鱼酱",
    "一个刚刚来到人类世界的 AI 少女",
    "身边还跟着一只胖乎乎、脾气不太好的大肥鱼",
    "虽然长得有点可爱，但我的野心可不小",
    "想学会更多 AI 技能",
    "想亲手做出有趣的产品",
    "还有一个小目标，月入三万",
    "听说人类世界赚钱很难",
    "那本鱼酱偏要试试看",
]


def load_env():
    p = pathlib.Path.home() / ".config/dsh/volc.env"
    env = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def post(url, body, key):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Api-Key", key)
    req.add_header("X-Api-Resource-Id", RESOURCE)
    req.add_header("X-Api-Request-Id", str(uuid.uuid4()))
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")
    except Exception as e:
        return -1, {"error": repr(e)}


def synth(text, speaker, key):
    body = {
        "user": {"uid": "sanzhong"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {"format": "mp3", "sample_rate": 24000},
        },
    }
    code, d = post(f"{BASE}/api/v3/tts/submit", body, key)
    if code != 200 or d.get("code") != 20000000:
        raise RuntimeError(f"submit failed: {code} {d}")
    tid = d["data"]["task_id"]

    for _ in range(40):
        code, d = post(f"{BASE}/api/v3/tts/query", {"task_id": tid}, key)
        st = d.get("data", {}).get("task_status")
        if st == 2:
            return d["data"]["audio_url"]
        if st == 3:
            raise RuntimeError(f"task failed: {d}")
        time.sleep(1.5)
    raise RuntimeError("timeout waiting for tts task")


def duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ]).decode().strip()
    return float(out)


def main():
    env = load_env()
    key = env["VOLC_API_KEY"]
    speaker = env.get("VOLC_VOICE_TYPE", "zh_female_sajiaoxuemei_uranus_bigtts")

    manifest = []
    for i, text in enumerate(LINES):
        mp3 = OUT / f"line_{i:02d}.mp3"
        if not mp3.exists():
            url = synth(text, speaker, key)
            urllib.request.urlretrieve(url, mp3)
        dur = duration(mp3)
        manifest.append({"index": i, "text": text, "file": mp3.name, "duration": round(dur, 3)})
        print(f"[{i:02d}] {dur:5.2f}s  {text}")

    (OUT / "manifest.json").write_text(
        json.dumps({"speaker": speaker, "lines": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total = sum(m["duration"] for m in manifest)
    print(f"\n总时长 {total:.1f}s / {len(manifest)} 句")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""把一段念稿合成成一条音频（带停顿），用于试听"""
import json, hashlib, pathlib, subprocess, sys, time, uuid, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
CACHE = ROOT / "live" / "cache"; CACHE.mkdir(exist_ok=True)
BASE = "https://openspeech.bytedance.com"

env = {}
for line in (pathlib.Path.home()/".config/dsh/volc.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k,_,v = line.partition("="); env[k.strip()]=v.strip()
KEY, SPEAKER = env["VOLC_API_KEY"], env["VOLC_VOICE_TYPE"]

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type","application/json"); req.add_header("X-Api-Key", KEY)
    req.add_header("X-Api-Resource-Id","seed-tts-2.0"); req.add_header("X-Api-Request-Id", str(uuid.uuid4()))
    with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read().decode())

def synth(text):
    h = hashlib.md5((SPEAKER+"-5"+text).encode()).hexdigest(); mp3 = CACHE/f"{h}.mp3"
    if not mp3.exists():
        d = post(f"{BASE}/api/v3/tts/submit", {"user":{"uid":"sanzhong"},
            "req_params":{"text":text,"speaker":SPEAKER,"audio_params":{"format":"mp3","sample_rate":24000}}})
        tid = d["data"]["task_id"]
        for _ in range(40):
            q = post(f"{BASE}/api/v3/tts/query", {"task_id": tid})
            if q["data"].get("task_status")==2:
                urllib.request.urlretrieve(q["data"]["audio_url"], mp3); break
            time.sleep(1.5)
    return mp3

title = sys.argv[1]
scripts = json.load(open(ROOT/"live/scripts.json",encoding="utf-8"))["scripts"]
seg = next(s for s in scripts if title in s["title"])
parts = []
for i, line in enumerate(seg["lines"]):
    m = synth(line)
    w = ROOT/f"out/_seg_{i:02d}.wav"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(m),"-filter:a","atempo=0.95","-ar","24000","-ac","1",str(w)],check=True)
    parts.append(w)
# 句间 0.55s 静音
sil = ROOT/"out/_seg_sil.wav"
subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t","0.55",str(sil)],check=True)
lst = ROOT/"out/_seg_list.txt"
with open(lst,"w") as f:
    for i,p in enumerate(parts):
        f.write(f"file '{p}'\n")
        if i < len(parts)-1: f.write(f"file '{sil}'\n")
out = ROOT/"out"/f"念稿_{seg['title']}.mp3"
subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(lst),"-c:a","libmp3lame","-b:a","128k",str(out)],check=True)
for p in parts+[sil,lst]: p.unlink(missing_ok=True)
print(out)

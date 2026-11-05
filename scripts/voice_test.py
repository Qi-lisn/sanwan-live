import json, hashlib, pathlib, subprocess, sys, time, uuid, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT/"live"/"cache"; CACHE.mkdir(exist_ok=True)
BASE="https://openspeech.bytedance.com"
env={}
for line in (pathlib.Path.home()/".config/dsh/volc.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k,_,v=line.partition("="); env[k.strip()]=v.strip()
KEY=env["VOLC_API_KEY"]
VOICES={
 "cancan":"zh_female_cancan_uranus_bigtts",
 "qingxin":"zh_female_qingxinnvsheng_uranus_bigtts",
 "vv":"zh_female_vv_uranus_bigtts",
 "xiaohe":"zh_female_xiaohe_uranus_bigtts",
 "sophie":"zh_female_sophie_uranus_bigtts",
 "tianmei":"zh_female_tianmeixiaoyuan_uranus_bigtts",
}
TEXT="末班车的时候 车厢是空的 你坐在那儿 喘气 玻璃上是你自己的脸"
def post(url, body):
    req=urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type","application/json"); req.add_header("X-Api-Key",KEY)
    req.add_header("X-Api-Resource-Id","seed-tts-2.0"); req.add_header("X-Api-Request-Id",str(uuid.uuid4()))
    with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read().decode())
for name, spk in VOICES.items():
    try:
        d=post(f"{BASE}/api/v3/tts/submit",{"user":{"uid":"sanzhong"},
            "req_params":{"text":TEXT,"speaker":spk,"audio_params":{"format":"mp3","sample_rate":24000}}})
        tid=d["data"]["task_id"]
        for _ in range(30):
            q=post(f"{BASE}/api/v3/tts/query",{"task_id":tid})
            if q["data"].get("task_status")==2:
                out=ROOT/"out"/f"音色_{name}.mp3"
                urllib.request.urlretrieve(q["data"]["audio_url"], out)
                print("ok", name, out); break
            time.sleep(1.2)
    except Exception as e:
        print("fail", name, str(e)[:120])

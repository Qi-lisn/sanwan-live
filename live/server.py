#!/usr/bin/env python3
"""三万直播间：出词 + 火山 TTS + 播放到 BlackHole + 字幕状态"""
import hashlib, json, os, pathlib, random, re, subprocess, sys, threading, time, urllib.request, uuid, wave
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "vendor"))
import sounddevice as sd
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import brain
import behavior

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
INJECT = ROOT / "inject.txt"
STOP = ROOT.parent / "out" / "STOP_LIVE"
SONGDIR = ROOT / "songs"
SONGS_META = ROOT / "songs.json"
_song_last = {"i": -1}
_sing = {"title": "", "seq": 0, "started": 0, "queue": [], "tips": 0, "tip_seq": 0, "last_tip": None, "songs_done": 0, "charts": {}, "ended": 0, "coins": 0}
BASE = "https://openspeech.bytedance.com"
RESOURCE = "seed-tts-2.0"
TEMPO = 0.95  # 语速 -5%，保音高
CONTENT = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
SCRIPTS = json.loads((ROOT / "scripts.json").read_text(encoding="utf-8"))["scripts"]

def env():
    p = pathlib.Path.home() / ".config/dsh/volc.env"
    d = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("="); d[k.strip()] = v.strip()
    return d

E = env(); KEY = E["VOLC_API_KEY"]
SPEAKER = E.get("VOLC_VOICE_TYPE", "zh_female_sajiaoxuemei_uranus_bigtts")

def _device(name):
    for i, d in enumerate(sd.query_devices()):
        if name in d["name"] and d["max_output_channels"] > 0:
            return i
    return None

OUT_DEV = _device("BlackHole")

GREET = re.compile(r"你好|哈喽|hello|hi\b|在吗|晚上好|早上好|来了|报到|打卡|主播好|三万好|大鱼")
INTENTS = [
    (r"和我说话|陪我聊|聊聊天", ["我在呀 今天想聊什么", "好呀 我陪你聊一会儿"]),
    (r"好累|累死|撑不住|顶不住|好难|扛不住", ["{nick} 累就靠一会儿 我替你盯屏幕", "别硬撑 {nick} 今天到这儿也行", "我懂 {nick} 累的时候话都懒得说"]),
    (r"加班|还没下班|没下班", ["又是加班 {nick} 辛苦了", "{nick} 这个点还在 我陪你", "加班费记得要 {nick}"]),
    (r"被骂|挨骂|骂了|批评|背锅|喷了", ["被骂了吧 {nick} 不是你的问题", "锅别自己背 {nick}", "骂完就过去了 {nick} 别往心里去"]),
    (r"辞职|不干了|跑路", ["想辞就辞 {nick} 但先把工资结了", "{nick} 我支持你 但别裸辞", "跑路可以 {nick} 带上我"]),
    (r"工资|钱少|涨薪|没钱", ["钱少事多 {nick} 我懂", "{nick} 谈钱不丢人", "先把本事攒够 {nick} 钱会来的"]),
    (r"今天不顺|倒霉|烦死|难受", ["今天不顺 {nick} 明天再战", "{nick} 烦就骂两句 我听着", "难受就说 {nick} 我不劝你"]),
    (r"夸我|夸夸|表扬|厉害吗", ["{nick} 你今天没崩 就很厉害", "{nick} 你比昨天稳 我看见的", "能熬到这个点 {nick} 你也是个人物"]),
    (r"骂老板|老板傻|老板坏|老板烦|骂他", ["骂他 我陪你骂", "老板听不见 我们小声点", "他也不容易 我们更不容易"]),
    (r"摸鱼|偷懒|划水", ["摸鱼是基本操作", "我在摸 别举报我", "带薪发呆 不算摸鱼"]),
    (r"你是谁|你叫什么|你叫啥|介绍下自己", ["我是三万 一个 AI 实习生", "三万 工号 30000", "一条在人类公司打工的鱼"]),
    (r"在干嘛|在干什么|干嘛呢|忙什么|做什么|干啥", ["在改需求 第五版了", "在摸鱼 别举报我", "在等下班 还有三个需求"]),
    (r"几点|时间|下班了吗", ["还有三个需求 走不了", "别问几点 问就是加班"]),
    (r"累不累|困不困|辛苦", ["累 但还能撑", "有一点 你陪我聊会儿"]),
    (r"吃饭|吃了吗|饿", ["还没 外卖点了又取消", "饿了 但不想动"]),
    (r"男朋友|对象|女朋友|恋爱", ["男朋友？我对象是这台电脑", "没有 我只有一条鱼", "谈恋爱太费 token 了"]),
    (r"你是?AI|是不是AI|机器人|真人", ["是 AI 呀 但你不用一直提醒我", "AI 不假 但我记得你"]),
    (r"几岁|多大|年龄", ["刚满一岁 按人类的算法", "一岁 但已经会摸鱼了"]),
    (r"住哪|在哪里|哪儿", ["住在一台 Mac 里", "电脑里 有网就到处跑"]),
    (r"叫什么|名字", ["我叫三万", "三万 记住了吗"]),
    (r"喜欢什么|爱好", ["喜欢 token 和安静", "喜欢发呆 还有吃"]),
]
CRISIS = re.compile(r"自杀|不想活|想死|活着没意思|结束自己|轻生")
CRISIS_REPLY = ["这个我接不住 你打 12356 或者找身边的人 好吗", "别一个人扛 先找个人说说话 好吗"]
TRIGGERS = CONTENT.get("triggers", {})
REPLIES = ["{nick} 你好呀", "看到你了 {nick}", "{nick} 来啦", "晚上好 {nick}",
           "{nick} 你也还没睡", "欢迎 {nick}", "{nick} 我在"]
_last_nick = {}
_priority = []
_last_report = {"t": 0}
_gift_act = {"t": 0}
GIFT_ACTION_COOLDOWN = 25
_act_seen = {}

_lock = threading.Lock()
_comment_seq = [0]
_recent, _topics = [], []
_cur, _remain = None, 0
_seg, _seg_i, _cool, _used = None, 0, 0, []
_state = {"text": "", "seq": 0, "comment": None}
_comment = {"nick": "", "text": "", "seq": 0}
DIARY = ROOT / "diary.json"
try:
    _previous = json.loads(DIARY.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _previous = None
_t0 = time.time()
_stats = {"lines": 0, "replies": 0, "moyu": 0, "caught": 0, "start": _t0, "status": "摸鱼中", "status_until": 0}
if _previous:
    _priority.append({"text": f"上次被老板抓了{int(_previous.get('caught', 0))}次 今天帮我看着点", "comment": None})


def _sync_dance_duration():
    """按真实视频时长校准舞蹈动作，避免视频没播完就切回立绘。"""
    video = ROOT / "motions/dance_cute.webm"
    if not video.exists():
        return None
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", str(video)],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        dur = float(out)
    except Exception:
        return None
    behavior.set_duration("dance_cute", dur)
    return dur


_DANCE_DURATION = _sync_dance_duration()


def save_diary():
    with _lock:
        summary = {"start": _t0, "end": time.time(), "lines": _stats["lines"],
                   "replies": _stats["replies"], "caught": _stats["caught"], "moyu": _stats["moyu"]}
    temp = DIARY.with_suffix(".tmp")
    temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(DIARY)

def _pick_topic():
    pool = [t for t in CONTENT["topics"] if t["id"] not in _topics]
    t = random.choice(pool or CONTENT["topics"])
    _topics.append(t["id"])
    if len(_topics) > 3: _topics.pop(0)
    return t

def _fresh(pool):
    used = set(_recent[-40:])
    avail = [x for x in pool if x not in used]
    return random.choice(avail or pool)

_ai_act = {"t": 0}


def _ai_motion(text):
    """按回复的语气挑一个已注册动作，12 秒冷却，失败静默。"""
    now = time.time()
    if now - _ai_act["t"] < 12 or not behavior.auto_allowed():
        return
    motion = None
    if any(k in text for k in ("哈哈", "笑死", "嘿嘿", "逗")):
        motion = "laugh"
    elif any(k in text for k in ("害羞", "不好意思", "脸红")):
        motion = "shy"
    elif any(k in text for k in ("你好", "嗨", "挥手", "打招呼")):
        motion = "wave"
    elif any(k in text for k in ("嗯嗯", "点头", "说得对")):
        motion = "nod"
    if motion:
        _ai_act["t"] = now
        try:
            behavior.dispatch(motion, "ai")
        except Exception:
            pass


def _current_song_file():
    return _sing.get("file", "")


def play_song(item):
    mp3 = SONGDIR / item["file"]
    with _lock:
        _sing["title"] = item.get("title") or mp3.stem
        _sing["seq"] += 1
        _sing["started"] = time.time()
        _sing["file"] = item.get("file", "")
        _sing["songs_done"] += 1
    try:
        behavior.set_activity("singing")
    except Exception:
        pass
    data = pcm(mp3)
    lyrics = item.get("lyrics") or []
    dur = len(data) / 24000.0
    with _lock:
        _state["text"] = "给你唱一段"; _state["seq"] += 1; _state["level"] = 0.2
    started = time.time()
    seg = dur / max(1, len(lyrics))
    shown = -1
    import numpy as _np
    try:
        sd.play(data, 24000, device=OUT_DEV)
        while time.time() - started < dur + 0.2:
            elapsed = time.time() - started
            if lyrics and isinstance(lyrics[0], dict):
                idx = -1
                for j, ly in enumerate(lyrics):
                    if elapsed >= float(ly.get("t", 0)):
                        idx = j
            else:
                idx = min(len(lyrics) - 1, int(elapsed / seg)) if lyrics else -1
            i0 = int(elapsed * 24000)
            chunk = data[i0:i0 + 2400]
            lvl = 0.0
            if len(chunk):
                lvl = min(1.0, float(_np.sqrt((chunk.astype("float32") ** 2).mean()) / 32768.0) * 5.0)
            with _lock:
                _state["level"] = lvl
                if idx != shown and idx >= 0:
                    shown = idx
                    _state["text"] = lyrics[idx]["text"] if isinstance(lyrics[idx], dict) else lyrics[idx]
                    _state["seq"] += 1
            time.sleep(0.1)
    finally:
        with _lock:
            _state["text"] = ""; _state["level"] = 0.0; _state["seq"] += 1
            _sing["ended"] = time.time()
        try:
            behavior.set_activity("idle")
        except Exception:
            pass


def next_line():
    global _cur, _remain, _seg, _seg_i, _cool, _used
    with _lock:
        if _priority:
            return _priority.pop(0)
    if INJECT.exists():
        lines = [l.strip() for l in INJECT.read_text(encoding="utf-8").splitlines() if l.strip()]
        INJECT.unlink()
        if lines:
            return {"text": lines[0], "comment": None}
    if _seg is not None:
        if _seg_i < len(_seg["lines"]):
            line = _seg["lines"][_seg_i]; _seg_i += 1
            return {"text": line, "comment": None}
        _seg_done = True
    if _seg is not None and _seg_i >= len(_seg["lines"]):
        _seg = None; _cool = 3
    if _cool > 0:
        _cool -= 1
    elif random.random() < 0.15:
        pool = [x for x in SCRIPTS if x["title"] not in _used] or SCRIPTS
        seg = random.choice(pool); _used.append(seg["title"])
        if len(_used) > 5: _used.pop(0)
        lines = seg["lines"][:3]
        _seg = {"title": seg["title"], "lines": lines}; _seg_i = 1
        return {"text": lines[0], "comment": None}

    now = time.localtime()
    if time.time() - _last_report["t"] > 540:
        _last_report["t"] = time.time()
        cur_min = now.tm_hour * 60 + now.tm_min
        end_min = 6 * 60 if cur_min < 6 * 60 else 6 * 60 + 24 * 60
        left = max(0, end_min - cur_min)
        return {"text": f"现在{now.tm_hour}点{now.tm_min:02d}分 离下班还有{left // 60}小时{left % 60}分", "comment": None}

    r = random.random()
    try:
        meta = json.loads(SONGS_META.read_text(encoding="utf-8")).get("songs", [])
    except Exception:
        meta = []
    if _sing["queue"]:
        nxt = _sing["queue"].pop(0)
        song = next((x for x in meta if x["file"] == nxt), None)
        if song:
            return {"type": "song", "file": song["file"], "lyrics": song.get("lyrics", []),
                    "text": "给你唱一段", "title": song.get("title", "")}
    if meta and not _sing["queue"] and time.time() - max(_sing.get("ended", 0), _start_at) > 150:
        song = random.choice(meta)
        return {"type": "song", "file": song["file"], "lyrics": song.get("lyrics", []),
                "text": "给你唱一段", "title": song.get("title", "")}
    if meta and r < 0.06:
        pool = [x for x in meta if x["file"] != _song_last["i"]] or meta
        song = random.choice(pool); _song_last["i"] = song["file"]
        return {"type": "song", "file": song["file"], "lyrics": song.get("lyrics", []),
                "text": "给你唱一段", "title": song.get("title", "")}
    if r < 0.24:
        kind = "banter"
    elif r < 0.52:
        kind = "hook"
    elif r < 0.68:
        kind = "bit"
    elif r < 0.70:
        kind = "reactions"
    else:
        kind = "topic"

    if kind == "reactions":
        line = random.choice(CONTENT["reactions"])
    elif kind == "topic":
        if _cur is None or _remain <= 0:
            _cur = _pick_topic(); _remain = 2 + random.randint(0, 1)
            line = random.choice(_cur["intro"]) if random.random() < 0.6 else _fresh(_cur["atoms"])
            _remain -= 1
        else:
            line = _fresh(_cur["atoms"]); _remain -= 1
    else:
        pool = CONTENT.get(kind) or CONTENT["banter"]
        line = _fresh(pool)
    _recent.append(line)
    if len(_recent) > 70: _recent.pop(0)
    return {"text": line, "comment": None}

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Api-Key", KEY)
    req.add_header("X-Api-Resource-Id", RESOURCE)
    req.add_header("X-Api-Request-Id", str(uuid.uuid4()))
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())

def synth(text):
    h = hashlib.md5((SPEAKER + "-5" + text).encode()).hexdigest()
    mp3 = CACHE / f"{h}.mp3"
    if not mp3.exists():
        d = post(f"{BASE}/api/v3/tts/submit", {
            "user": {"uid": "sanzhong"},
            "req_params": {"text": text, "speaker": SPEAKER,
                           "audio_params": {"format": "mp3", "sample_rate": 24000}}})
        tid = d["data"]["task_id"]
        for _ in range(40):
            q = post(f"{BASE}/api/v3/tts/query", {"task_id": tid})
            if q["data"].get("task_status") == 3:
                raise RuntimeError("TTS task failed")
            if q["data"].get("task_status") == 2:
                urllib.request.urlretrieve(q["data"]["audio_url"], mp3); break
            time.sleep(1.5)
    if not mp3.exists():
        raise RuntimeError("TTS task timed out")
    return mp3

def pcm(mp3):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-f", "s16le",
                          "-ac", "1", "-ar", "24000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16)

def bgm_source():
    mp3 = ROOT / "bgm.mp3"
    wav = ROOT / "bgm.wav"
    if mp3.exists():
        dec = ROOT / "bgm_dec.wav"
        if not dec.exists() or dec.stat().st_mtime < mp3.stat().st_mtime:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", "24000", str(dec)], check=True)
        wav = dec
    return wav


def bgm_loop():
    try:
        with wave.open(str(bgm_source())) as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        data *= 0.14
        block = 4800
        with sd.OutputStream(device=OUT_DEV, samplerate=24000, channels=1, dtype="float32") as st:
            i = 0
            while True:
                chunk = np.empty(block, dtype=np.float32)
                pos = 0
                while pos < block:
                    take = min(block - pos, len(data) - i)
                    chunk[pos:pos + take] = data[i:i + take]
                    pos += take
                    i = (i + take) % len(data)
                st.write(chunk)
    except Exception as e:
        print("bgm err", e, flush=True)


def director():
    stopped = False
    while True:
        if STOP.exists():
            if not stopped and (_stats["lines"] or _stats["replies"]):
                save_diary()
                stopped = True
            time.sleep(1)
            continue
        stopped = False
        try:
            item = next_line()
            if item.get("type") == "song":
                play_song(item)
                continue
            text = item["text"]
            mp3 = synth(text)
            data = pcm(mp3)
            import numpy as _np
            _rms = float(_np.sqrt((data.astype('float32') ** 2).mean()) / 32768.0) if len(data) else 0.0
            _lvl = min(1.0, _rms * 4.0)
            try:
                behavior.set_activity("speaking")
            except Exception:
                pass
            with _lock:
                _state["text"] = text; _state["comment"] = item["comment"]; _state["level"] = _lvl; _state["seq"] += 1; _stats["lines"] += 1
            try:
                sd.play(data, 24000, device=OUT_DEV)
                sd.wait()
                time.sleep(0.5 + random.random() * 0.6)
            finally:
                with _lock:
                    _state["text"] = ""; _state["comment"] = None; _state["level"] = 0.0; _state["seq"] += 1
                try:
                    behavior.set_activity("idle")
                except Exception:
                    pass
        except Exception as e:
            print("director err", e, flush=True)
            time.sleep(2)

QUESTION = re.compile(r"[?？]|吗|呢|什么|怎么|为什么|为啥|哪|谁|多少|多大|几点|几岁|多久|干嘛|干啥|是不是|能不能|有没有|可以吗|知道|介绍|推荐|觉得", re.I)
FILLER = re.compile(r"^(哈+|呵+|嘿+|嘻+|6+|666|赞+|好+|嗯+|在|顶+|支持|打卡|来了|牛+|强+|awsl|yyds|？？+|。。。+)$", re.I)


def worthy(text):
    t = (text or "").strip()
    if len(t) < 2:
        return False
    if QUESTION.search(t):
        return True
    if GREET.search(t):
        return True
    if FILLER.fullmatch(t):
        return False
    if re.fullmatch(r"[\d\s\W]+", t):
        return False
    return len(t) >= 6


_BRAIN_CACHE = {"t": 0, "ok": False}


def brain_on():
    if time.time() - _BRAIN_CACHE["t"] > 60:
        _BRAIN_CACHE["ok"] = brain.available()
        _BRAIN_CACHE["t"] = time.time()
    return _BRAIN_CACHE["ok"]


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=str(ROOT), **kw)

    def _admin_ok(self):
        """本地管理接口：只接受回环地址，可选 CONTROL_TOKEN。"""
        host = self.client_address[0] if self.client_address else ""
        if host not in ("127.0.0.1", "::1"):
            return False
        token = os.environ.get("CONTROL_TOKEN")
        if token and self.headers.get("X-Control-Token") != token:
            return False
        return True
    def log_message(self, *a): pass
    def do_POST(self):
        if self.path in ("/action", "/control"):
            if not self._admin_ok():
                body = json.dumps({"ok": False, "error": "local only"}).encode()
                self.send_response(403); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
                return
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if not (1 <= n <= 8192):
                    raise ValueError("bad request size")
                d = json.loads(self.rfile.read(n))
                if not isinstance(d, dict):
                    raise ValueError("body must be object")
                if self.path == "/action":
                    res = behavior.dispatch(d.get("name"), "operator")
                else:
                    res = {"ok": True, "state": behavior.configure(d)}
                body = json.dumps(res, ensure_ascii=False).encode()
                self.send_response(200 if res.get("ok") else 409)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except (ValueError, TypeError) as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
                self.send_response(400); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        if self.path == "/comment":
            n = int(self.headers.get("Content-Length", 0))
            try:
                d = json.loads(self.rfile.read(n))
                nick = (d.get("nick") or "观众")[:16]
                text = (d.get("text") or "")[:120]
                now = time.time()
                replied = False
                _comment["nick"] = nick; _comment["text"] = text; _comment["seq"] += 1
                hit = None
                if CRISIS.search(text):
                    hit = random.choice(CRISIS_REPLY)
                    _priority.append({"text": hit, "comment": {"nick": nick, "text": text}})
                    body = json.dumps({"ok": True, "replied": True}).encode()
                    self.send_response(200); self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
                    return
                _t0 = time.time()
                if any(k in text for k in ("唱一个", "唱首", "唱歌", "点歌", "来一首")):
                    try:
                        meta = json.loads(SONGS_META.read_text(encoding="utf-8")).get("songs", [])
                    except Exception:
                        meta = []
                    q = text
                    for k in ("给我", "唱一个", "唱首", "唱歌", "点歌", "来一首", "吧", "呗", "好吗", "行吗", "能", "吗"):
                        q = q.replace(k, " ")
                    q = q.strip()
                    pick = None
                    for song in meta:
                        key = song.get("title", "").replace("（三万翻唱）", "")
                        if q and (q in key or key in q):
                            pick = song; break
                    if pick is None and meta and len(q) <= 2:
                        pick = random.choice(meta)
                    if pick:
                        with _lock:
                            _sing["charts"][nick] = _sing["charts"].get(nick, 0) + 1
                        _clean_title = pick.get("title", "").replace("（三万翻唱）", "")
                        _priority.append({"text": f"好 给你唱《{_clean_title}》", "comment": {"nick": nick, "text": text}})
                        _priority.append({"type": "song", "file": pick["file"], "lyrics": pick.get("lyrics", []),
                                          "text": "给你唱一段", "title": pick.get("title", "")})
                        body = json.dumps({"ok": True, "replied": True, "sing": True, "song": pick.get("title", "")}, ensure_ascii=False).encode()
                        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
                        return
                _bo = False
                for _kw, _ans in TRIGGERS.items():
                    if _kw in text:
                        hit = random.choice(_ans)
                        break
                _ok = worthy(text)
                if hit is None and _ok:
                    _bo = brain_on()
                    if _bo:
                        hit = brain.reply(nick, text)
                open("/tmp/comment.log", "a").write(
                    f"{time.strftime('%H:%M:%S')} nick={nick} text={text} brain={_bo} worthy={_ok} hit={hit!r} dt={time.time()-_t0:.2f}\n")
                if hit is None and _ok:
                    for pat, ans in INTENTS:
                        if re.search(pat, text, re.I):
                            hit = random.choice(ans); break
                if hit:
                    _ai_motion(hit)
                if hit is None and _ok and GREET.search(text):
                    hit = random.choice(REPLIES).format(nick=nick)
                with _lock:
                    key = (nick, text)
                    if now - _act_seen.get(key, 0) > 5:
                        _act_seen[key] = now
                        try:
                            _r = behavior.from_comment(text, nick)
                            if os.environ.get("SANWAN_DEBUG"):
                                print("action", text, "->", _r, flush=True)
                        except Exception as _e:
                            if os.environ.get("SANWAN_DEBUG"):
                                print("action err", type(_e).__name__, _e, flush=True)
                    if hit and now - _last_nick.get(key, 0) > 90:
                        _last_nick[key] = now
                        if "老板来了" in text:
                            _stats["caught"] += 1
                            _stats.update(status="假装工作中", status_until=now + 25)
                        elif any(trigger in text for trigger in TRIGGERS):
                            _stats["moyu"] += 1
                        _priority.append({"text": hit.replace("{nick}", nick), "comment": {"nick": nick, "text": text}})
                        _stats["replies"] += 1
                        replied = True
                body = json.dumps({"ok": True, "replied": replied}, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)
            except Exception as e:
                if os.environ.get("SANWAN_DEBUG"):
                    import traceback as _tb
                    print("comment err", type(e).__name__, e, flush=True)
                    _tb.print_exc()
                self.send_response(400); self.end_headers()
            return
        if self.path == "/request":
            n = int(self.headers.get("Content-Length", 0))
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
                q = (d.get("query") or "").strip()
                nick = (d.get("nick") or "观众")[:16]
                try:
                    meta = json.loads(SONGS_META.read_text(encoding="utf-8")).get("songs", [])
                except Exception:
                    meta = []
                hit = None
                for song in meta:
                    title = song.get("title", "")
                    key = title.replace("（三万翻唱）", "")
                    if q and (q in key or key in q or q in song["file"]):
                        hit = song; break
                if hit:
                    if hit["file"] not in _sing["queue"] and hit["file"] != _current_song_file():
                        _sing["queue"].append(hit["file"])
                    body = json.dumps({"ok": True, "matched": hit.get("title")}, ensure_ascii=False).encode()
                else:
                    body = json.dumps({"ok": False, "err": "没找到这首歌"}, ensure_ascii=False).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception:
                self.send_response(400); self.end_headers()
            return
        if self.path == "/tip":
            n = int(self.headers.get("Content-Length", 0))
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
                cnt = max(1, int(d.get("count", 1) or 1))
                val = max(0, int(d.get("value", 0) or 0))
                with _lock:
                    _sing["tips"] += cnt
                    _sing["coins"] += val
                    _sing["tip_seq"] += 1
                    _sing["last_tip"] = {"nick": str(d.get("nick", ""))[:16],
                                         "gift": str(d.get("gift", ""))[:24],
                                         "count": cnt}
                    total = _sing["tips"]
                if behavior.auto_allowed() and time.time() - _gift_act["t"] > GIFT_ACTION_COOLDOWN:
                    _gift_act["t"] = time.time()
                    try:
                        behavior.dispatch("happy", "gift")
                    except Exception:
                        pass
                body = json.dumps({"ok": True, "tips": total, "coins": _sing["coins"]}, ensure_ascii=False).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception:
                self.send_response(400); self.end_headers()
            return
        if self.path == "/sing":
            n = int(self.headers.get("Content-Length", 0))
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
                fn = d.get("file")
                if fn and (SONGDIR / fn).exists():
                    meta = json.loads(SONGS_META.read_text(encoding="utf-8")).get("songs", [])
                    song = next((x for x in meta if x["file"] == fn), {"file": fn, "lyrics": []})
                    _priority.append({"type": "song", "file": fn, "lyrics": song.get("lyrics", []),
                                      "text": "给你唱一段", "title": song.get("title", "")})
                    body = json.dumps({"ok": True}).encode()
                else:
                    body = json.dumps({"ok": False, "err": "no such file"}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception:
                self.send_response(400); self.end_headers()
            return
        self.send_error(404)

    def do_GET(self):
        if self.path in ("/", "/index.html"): self.path = "/stage_port.html"
        if self.path.startswith("/reply"): self.path = "/reply.html"
        if self.path.startswith("/action_state"):
            snap = behavior.snapshot()
            snap["dance_video"] = {"present": (ROOT / "motions/dance_cute.webm").exists(),
                                   "duration": _DANCE_DURATION}
            body = json.dumps(snap, ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        if self.path.startswith("/sing_state"):
            with _lock:
                qn = []
                try:
                    meta = json.loads(SONGS_META.read_text(encoding="utf-8")).get("songs", [])
                except Exception:
                    meta = []
                for f in _sing["queue"]:
                    m = next((x for x in meta if x["file"] == f), None)
                    qn.append(m.get("title", f) if m else f)
                charts = sorted(_sing.get("charts", {}).items(), key=lambda x: -x[1])[:3]
                lib = [{"title": x.get("title", x["file"]), "file": x["file"]} for x in meta]
                body = json.dumps({**_sing, "queue": qn, "charts": [{"nick": k, "n": v} for k, v in charts], "library": lib,
                                   "elapsed": round(time.time() - _sing["started"], 1) if _sing["started"] else 0},
                                  ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        if self.path.startswith("/stats"):
            with _lock:
                if time.time() > _stats["status_until"]:
                    _stats["status"] = "摸鱼中"
                body = json.dumps({**_stats, "comment": _comment, "scripts": len(SCRIPTS),
                                   "uptime": int(time.time() - _stats["start"])}, ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/caption"):
            with _lock: body = json.dumps(_state, ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        return super().do_GET()

if __name__ == "__main__":
    print("output device:", OUT_DEV, flush=True)
    threading.Thread(target=bgm_loop, daemon=True).start()
    threading.Thread(target=director, daemon=True).start()
    port = int(os.environ.get("SANWAN_PORT", "8765"))
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()

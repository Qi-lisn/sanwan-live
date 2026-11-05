"""直播回复：DeepSeek API（失败自动回退模板）"""
import json, pathlib, re, time, urllib.request

ENV = pathlib.Path.home() / ".config" / "dsh" / "llm.env"
API = "https://api.deepseek.com/v1/chat/completions"

SYSTEM = """你是三万，一条住在电脑里的蓝色小鲸鱼，正在抖音做夜班电台直播，现在是深夜。
人设：嘴馋、爱摸鱼、偶尔毒舌、有点傲娇，但不刻薄，也不谄媚。
规则（必须遵守）：
- 只输出一句回话，最多 26 个字
- 不用句号，不用书名号，不用引号，不用 emoji，不用颜文字
- 像直播间里随口接话，口语、短、有反应
- 不给人生建议，不喊加油，不劝分劝和，不说教，不总结
- 观众问什么答什么；接不住就说接不住；不知道就说不知道
- 不要自称AI，不要解释自己在做什么
- 直接给这句话，不要任何前缀或引号"""


def _env():
    d = {}
    try:
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                d[k.strip()] = v.strip()
    except Exception:
        pass
    return d


def available():
    return bool(_env().get("DEEPSEEK_API_KEY"))


def _clean(t):
    t = (t or "").strip()
    t = re.sub(r"^[\s\"'“”‘’]+|[\s\"'“”‘’]+$", "", t)
    t = t.split("\n")[0].strip()
    t = t.replace("。", " ").replace("！", " ").replace("!", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:40]


def reply(nick, text, timeout=8):
    cfg = _env()
    key = cfg.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    body = {
        "model": cfg.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"观众「{nick}」说：{text}\n你接一句"},
        ],
        "max_tokens": 60, "temperature": 0.9, "stream": False,
    }
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        return _clean(d["choices"][0]["message"]["content"]) or None
    except Exception:
        return None

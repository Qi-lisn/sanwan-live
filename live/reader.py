#!/usr/bin/env python3
"""从直播伴侣的「互动消息」面板截图 -> OCR -> 喂给 /comment"""
import sys, re, json, time, subprocess, pathlib, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "vendor"))
import Quartz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

ROOT = pathlib.Path(__file__).resolve().parent
SHOT = "/tmp/dy_win.png"
CROP = "/tmp/dy_crop.png"
ENGINE = RapidOCR()
SKIP = ("互动消息", "展示本场", "说点什么", "发送", "在线观众", "展开", "更多",
        "切勿", "谨防", "诈骗", "分享", "点赞", "为主播", "直播间", "交易")

def win_id():
    wins = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements, Quartz.kCGNullWindowID)
    best = None
    for w in wins:
        owner = w.get("kCGWindowOwnerName", "")
        if "直播伴侣" in owner or "Douyin Webcast Mate" in owner:
            b = w.get("kCGWindowBounds", {})
            if b.get("Width", 0) > 600:
                if best is None or b["Width"] > best[1]:
                    best = (w.get("kCGWindowNumber"), b["Width"])
    return best[0] if best else None

def grab():
    wid = win_id()
    if not wid: return None
    subprocess.run(["screencapture", "-l", str(wid), "-x", "-o", SHOT], check=True)
    return crop(SHOT)

def crop(path):
    im = Image.open(path); W, H = im.size
    box = (int(W*0.795), int(H*0.66), int(W*0.99), int(H*0.945))
    c = im.crop(box)
    c = c.resize((c.width*2, c.height*2), Image.LANCZOS)
    c.save(CROP)
    return CROP

def post(nick, text):
    req = urllib.request.Request("http://127.0.0.1:8765/comment",
        data=json.dumps({"nick": nick, "text": text}, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())

def messages(img):
    results, _ = ENGINE(img)
    for row in results or []:
        line = row[1].strip()
        if re.search(r"\d{1,2}\s*:\s*\d{2}", line): continue
        if any(w in line for w in ("关播", "开始直播", "推流", "实时码率", "直播中", "申请开播")):
            continue
        pair = re.fullmatch(r"(.{1,16}?)[：:]\s*(.+)", line)
        if pair:
            nick, text = (part.strip() for part in pair.groups())
        else:
            if any(word in line for word in SKIP) or not re.fullmatch(
                r"老板来了|你好|哈喽|在吗|晚上好|和我说话|陪我聊|聊聊天|hello|hi", line, re.I
            ):
                continue
            nick, text = "观众", line
        if nick and text:
            yield nick, text


def main():
    visible = set()
    while True:
        try:
            img = grab()
            if not img:
                time.sleep(3)
                continue
            current = set()
            for message in messages(img):
                if message in visible or message in current:
                    current.add(message)
                    continue
                nick, text = message
                try:
                    reply = post(nick, text)
                    current.add(message)
                    print(f"[{time.strftime('%H:%M:%S')}] {nick}: {text} -> replied={reply.get('replied')}", flush=True)
                except Exception as e:
                    print("post err", e, flush=True)
            visible = current
            time.sleep(2.5)
        except Exception as e:
            print("err", e, flush=True); time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--preview":
        for nick, text in messages(crop(sys.argv[2])):
            print(nick, text)
    else:
        main()

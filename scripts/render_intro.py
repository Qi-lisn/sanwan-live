#!/usr/bin/env python3
"""三万 · 自我介绍成片渲染

读 out/audio/manifest.json（逐句时长）-> 排时间轴 -> 合成音轨 -> 出 mp4
"""
import json, math, os, pathlib, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
SR = 24000
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"

LEAD = 0.8
GAP = 0.35
TAIL = 1.4
SUB_Y = 1530


def load_manifest():
    return json.loads((ROOT / "out/audio/manifest.json").read_text(encoding="utf-8"))


def timeline(manifest):
    t = LEAD
    out = []
    for m in manifest["lines"]:
        out.append({**m, "start": round(t, 3), "end": round(t + m["duration"], 3)})
        t += m["duration"] + GAP
    return out, round(t - GAP + TAIL, 3)


def gradient_bg():
    stops = [(0.0, (150, 206, 255)), (0.45, (206, 235, 255)), (1.0, (255, 246, 228))]
    t = np.linspace(0, 1, H, dtype=np.float32)
    g = np.zeros((H, 3), dtype=np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        m = (t >= p0) & (t <= p1)
        k = ((t[m] - p0) / (p1 - p0))[:, None]
        g[m] = np.array(c0, dtype=np.float32) + (np.array(c1, dtype=np.float32) - np.array(c0, dtype=np.float32)) * k
    g3 = np.repeat(g[:, None, :], W, axis=1)
    return Image.fromarray(g3.astype(np.uint8))


def radial(size, color, radius, alpha):
    w, h = size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * alpha
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def bubbles(n=38, seed=11):
    rng = np.random.default_rng(seed)
    return [dict(x=rng.uniform(0, W), y=rng.uniform(0, H + 200), r=rng.uniform(4, 24),
                 speed=rng.uniform(30, 95), a=rng.uniform(15, 60)) for _ in range(n)]


def draw_bubbles(frame, bs, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for b in bs:
        y = (b["y"] - b["speed"] * t) % (H + 120) - 60
        x = b["x"] + math.sin(t * 0.8 + b["r"]) * 12
        d.ellipse([x - b["r"], y - b["r"], x + b["r"], y + b["r"]],
                  fill=(255, 255, 255, int(b["a"] + 40)), outline=(255, 255, 255, int(b["a"] + 90)), width=2)
    frame.alpha_composite(layer)


def wrap(text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def smart_wrap(text, font, max_w):
    """优先在标点处断行，其次均分，避免把词拆开。"""
    if font.getlength(text) <= max_w:
        return [text]
    marks = "、，。！？；：,.!?;: "
    best, best_score = None, 1e9
    for i in range(1, len(text)):
        left, right = text[:i], text[i:]
        if font.getlength(left) > max_w or font.getlength(right) > max_w:
            continue
        score = abs(font.getlength(left) - font.getlength(right))
        if text[i - 1] in marks:
            score -= 400
        if score < best_score:
            best, best_score = (left, right), score
    if best:
        return list(best)
    return wrap(text, font, max_w)


def subtitle(text, alpha):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT, 62, index=0)
    lines = smart_wrap(text, font, 880)
    if len(lines) > 2:
        font = ImageFont.truetype(FONT, 54, index=0)
        lines = smart_wrap(text, font, 900)
    lh = int(font.size * 1.38)
    total_h = lh * len(lines)
    y0 = SUB_Y - total_h // 2
    # 底部提亮，让深色字落在浅底上
    for i in range(200):
        yy = H - 200 + i
        d.line([(0, yy), (W, yy)], fill=(255, 255, 255, int(40 * i / 200 * alpha)))
    for i, ln in enumerate(lines):
        w = font.getlength(ln)
        x = (W - w) / 2
        y = y0 + i * lh
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            d.text((x + dx, y + dy), ln, font=font, fill=(255, 255, 255, int(230 * alpha)))
        d.text((x, y), ln, font=font, fill=(24, 44, 84, int(250 * alpha)))
    return layer


def build_audio(tl, total):
    buf = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for item in tl:
        mp3 = ROOT / "out/audio" / item["file"]
        wav = mp3.with_suffix(".wav")
        if not wav.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                            "-ar", str(SR), "-ac", "1", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        s = int(item["start"] * SR)
        buf[s:s + len(data)] += data
    peak = np.abs(buf).max()
    if peak > 0:
        buf = buf / peak * 0.9
    pcm = (buf * 32767).astype(np.int16)
    out = ROOT / "out" / "narration.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out


def main():
    man = load_manifest()
    tl, total = timeline(man)
    print(f"视频时长 {total:.1f}s")

    bg = gradient_bg()
    glow_big = radial((1400, 1400), (255, 226, 160), 700, 110)
    disc = radial((620, 210), (40, 62, 110), 320, 34)
    bs = bubbles()

    char = Image.open(ROOT / "assets/character.png").convert("RGBA")
    cw = 820
    char = char.resize((cw, int(char.height * cw / char.width)), Image.LANCZOS)

    audio = build_audio(tl, total)
    n = int(total * FPS)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(audio), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", str(ROOT / "out" / "sanzhong_intro.mp4")]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for i in range(n):
        t = i / FPS
        f = bg.copy().convert("RGBA")
        f.alpha_composite(glow_big, (W // 2 - 300, -320))
        draw_bubbles(f, bs, t)

        bob = math.sin(t * 2 * math.pi / 4.2) * 14
        sway = math.sin(t * 2 * math.pi / 7.0) * 6
        cx = int((W - char.width) / 2 + sway)
        cy = int(1445 - char.height + bob)

        # 脚下光台，盖住原图阴影
        f.alpha_composite(disc, (W // 2 - 310, 1368))
        f.alpha_composite(char, (cx, cy))

        for item in tl:
            if item["start"] <= t < item["end"]:
                fade = 0.14
                if t < item["start"] + fade:
                    a = (t - item["start"]) / fade
                elif t > item["end"] - fade:
                    a = max(0.0, (item["end"] - t) / fade)
                else:
                    a = 1.0
                f.alpha_composite(subtitle(item["text"], max(0.0, min(1.0, a))))
                break
        proc.stdin.write(f.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()
    print("->", ROOT / "out" / "sanzhong_intro.mp4")


if __name__ == "__main__":
    main()

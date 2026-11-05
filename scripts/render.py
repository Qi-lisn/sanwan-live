#!/usr/bin/env python3
"""三万 · 自我介绍视频渲染器

用法:
  python3 render.py --out out/test-5s.mp4 --dur 5 --placeholder

画面: 1080x1920 / 30fps
分层素材放 assets/layers/，命名见 README。
"""
import argparse, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 安全区: 顶部 200 / 底部 380 不放关键内容
SUB_Y = 1470
CHAR_BOTTOM = 1310
CHAR_W = 960


def gradient_bg():
    top = np.array([8, 20, 44], dtype=np.float32)
    bot = np.array([17, 52, 102], dtype=np.float32)
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    g = top[None, None, :] + (bot - top)[None, None, :] * t
    g = np.repeat(g, W, axis=1).astype(np.uint8)
    return Image.fromarray(g, "RGB")


def glow(size, color=(60, 130, 255), radius=520, alpha=90):
    w, h = size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * alpha
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def make_bubbles(n=34, seed=7):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append(dict(
            x=float(rng.uniform(0, W)),
            y=float(rng.uniform(0, H + 200)),
            r=float(rng.uniform(5, 26)),
            speed=float(rng.uniform(35, 110)),
            alpha=float(rng.uniform(18, 70)),
        ))
    return out


def draw_bubbles(frame, bubbles, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for b in bubbles:
        y = (b["y"] - b["speed"] * t) % (H + 120) - 60
        x = b["x"] + math.sin(t * 0.9 + b["r"]) * 10
        d.ellipse([x - b["r"], y - b["r"], x + b["r"], y + b["r"]],
                  fill=(150, 205, 255, int(b["alpha"])),
                  outline=(200, 230, 255, int(b["alpha"] * 1.4)), width=2)
    frame.alpha_composite(layer)


def whale_placeholder(blink=False, mouth_open=False):
    """临时占位鲸鱼，仅用于验证构图。"""
    w, h = 900, 900
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body = (50, 110, 235, 255)
    light = (110, 165, 250, 255)
    belly = (196, 225, 255, 255)

    # 尾巴
    d.polygon([(170, 400), (60, 320), (85, 520)], fill=light)
    # 身体
    d.ellipse([140, 300, 780, 720], fill=body)
    # 肚皮
    d.ellipse([230, 560, 700, 730], fill=belly)
    # 鳍
    d.ellipse([300, 600, 470, 690], fill=light)
    # 眼睛
    ex, ey = 640, 450
    if blink:
        d.arc([ex - 34, ey - 14, ex + 34, ey + 22], 200, 340, fill=(12, 30, 60, 255), width=7)
    else:
        d.ellipse([ex - 30, ey - 30, ex + 30, ey + 30], fill=(255, 255, 255, 255))
        d.ellipse([ex - 12, ey - 14, ex + 16, ey + 16], fill=(12, 30, 60, 255))
        d.ellipse([ex + 2, ey - 8, ex + 12, ey + 2], fill=(255, 255, 255, 255))
    # 嘴
    if mouth_open:
        d.ellipse([600, 510, 660, 550], fill=(120, 30, 50, 255))
    else:
        d.arc([560, 480, 700, 560], 20, 120, fill=(20, 45, 90, 255), width=6)
    # 腮红
    d.ellipse([520, 510, 590, 550], fill=(255, 150, 170, 80))
    return img


def load_layers():
    """读取 assets/layers/ 下的分层素材；缺文件返回 None。"""
    base = os.path.join(ROOT, "assets", "layers")
    need = ["body.png", "eyes_open.png", "eyes_closed.png"]
    if not all(os.path.exists(os.path.join(base, n)) for n in need):
        return None
    out = {n[:-4]: Image.open(os.path.join(base, n)).convert("RGBA")
           for n in os.listdir(base) if n.endswith(".png")}
    return out


def fit_layer(img, width):
    if img.width == width:
        return img
    h = int(img.height * width / img.width)
    return img.resize((width, h), Image.LANCZOS)


def compose_character(t, layers):
    if layers is None:
        blink = (t % 4.0) < 0.12
        img = whale_placeholder(blink)
        return fit_layer(img, CHAR_W)
    img = layers["body"].copy()
    eyes = "eyes_closed" if (t % 4.0) < 0.12 else "eyes_open"
    img.alpha_composite(layers[eyes])
    if "mouth_open" in layers and "mouth_closed" in layers:
        img.alpha_composite(layers["mouth_open"] if int(t * 8) % 2 == 0 else layers["mouth_closed"])
    return fit_layer(img, CHAR_W)


def subtitle_layer(lines, idx, t, line_start, line_end):
    """底部字幕，当前行淡入淡出。"""
    txt = lines[idx]
    fade = 0.12
    if t < line_start + fade:
        a = (t - line_start) / fade
    elif t > line_end - fade:
        a = max(0.0, (line_end - t) / fade)
    else:
        a = 1.0
    a = max(0.0, min(1.0, a))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_PATH, 66, index=0)
    # 底部渐变压暗，保证白字可读
    for i in range(220):
        yy = H - 220 + i
        d.line([(0, yy), (W, yy)], fill=(0, 0, 0, int(90 * i / 220)))
    bbox = d.textbbox((0, 0), txt, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) / 2
    d.text((x + 2, SUB_Y + 3), txt, font=font, fill=(0, 0, 0, int(120 * a)))
    d.text((x, SUB_Y), txt, font=font, fill=(255, 255, 255, int(245 * a)))
    return layer


def build_timeline(lines, dur):
    # 按字数分配时长，最少 1.1s
    weights = [max(1, len(l)) for l in lines]
    total = sum(weights)
    out, t0 = [], 0.0
    for w in weights:
        d = max(1.1, dur * w / total)
        out.append((t0, t0 + d))
        t0 += d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "test.mp4"))
    ap.add_argument("--dur", type=float, default=5.0)
    ap.add_argument("--placeholder", action="store_true")
    ap.add_argument("--still", default=None, help="输出某一秒的静帧 png")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    bg = gradient_bg()
    glow_img = glow((1100, 1100))
    bubbles = make_bubbles()

    lines = ["我叫三万", "DeepSeek 图标上那条蓝鲸鱼"]
    tl = build_timeline(lines, args.dur)

    layers = None if args.placeholder else load_layers()
    if layers is None and not args.placeholder:
        print("assets/layers 不全，回退占位图形")

    n = int(args.dur * FPS)
    proc = None
    if not args.still:
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([W // 2 - 200, CHAR_BOTTOM - 55, W // 2 + 200, CHAR_BOTTOM + 5],
                                   fill=(0, 0, 0, 65))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))

    char_cache = {}
    for i in range(n):
        t = i / FPS
        frame = bg.copy().convert("RGBA")
        # 光晕
        frame.alpha_composite(glow_img, (W // 2 - 550, 520))
        draw_bubbles(frame, bubbles, t)

        # 角色浮动
        bob = math.sin(t * 2 * math.pi / 2.6) * 10
        key = (round(t % 4.0, 2) < 0.12)
        if key not in char_cache:
            char_cache[key] = compose_character(t, layers)
        ch = char_cache[key]
        cx = (W - ch.width) // 2
        cy = int(CHAR_BOTTOM - ch.height + bob)
        # 影子
        frame.alpha_composite(shadow)
        frame.alpha_composite(ch, (cx, cy))

        for idx, (s, e) in enumerate(tl):
            if s <= t < e:
                frame.alpha_composite(subtitle_layer(lines, idx, t, s, e))
                break

        rgb = frame.convert("RGB")
        if args.still:
            rgb.save(args.still)
            print("still ->", args.still)
            break
        proc.stdin.write(rgb.tobytes())

    if proc:
        proc.stdin.close()
        proc.wait()
        print("video ->", args.out)


if __name__ == "__main__":
    main()

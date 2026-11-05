#!/usr/bin/env python3
"""V0.4: 从 V0.3 图层推导肩/肘/腕补绘蒙版与极限角度测试图。
输入: .joint-v03/native/  输出: live2d/v04_project/{masks,tests}
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage

V = ".joint-v03/native/"
OUT = "live2d/v04_project/"
SH, EL, WR = (503, 411), (455, 622), (413, 785)
F = "/System/Library/Fonts/Hiragino Sans GB.ttc"

M = Image.open(V + "character_master_expanded.png").convert("RGBA")
UP = Image.open(V + "arm_screen_left_upper.png").convert("RGBA")
FO = Image.open(V + "arm_screen_left_fore.png").convert("RGBA")
HA = Image.open(V + "hand_screen_left_open.png").convert("RGBA")
Ma = np.array(M)[:, :, 3]

base = np.array(M).copy()
for im in (UP, FO, HA):
    base[np.array(im)[:, :, 3] > 8] = 0
BASE = Image.fromarray(base)
Image.fromarray(base).save(OUT + "layers/torso_base.png")

# 前臂 + 手掌顶部 8px（技术重叠，复制同源像素）
fa, ha = np.array(FO), np.array(HA)
top = np.where(ha[:, :, 3] > 12)[0].min()
band = ha.copy(); band[top + 8:, :, :] = 0
fo = fa.copy(); m = band[:, :, 3] > 0; fo[m] = band[m]
Image.fromarray(fo).save(OUT + "layers/arm_fore_overlap8.png")

# 躯干轮廓估计：身体 + 肘以上手臂，闭运算填形
up_a = np.array(UP)[:, :, 3] > 8
up_a[EL[1] + 1:, :] = False
torso = ndimage.binary_fill_holes(
    ndimage.binary_closing(np.array(BASE)[:, :, 3] > 20 | up_a, structure=np.ones((25, 25))))

def rot(im, a, c): return im.rotate(a, center=c, resample=Image.BICUBIC)

def comp(shoulder=0, elbow=0, wrist=0):
    h = rot(HA, wrist, WR) if wrist else HA
    fh = Image.new("RGBA", M.size, (0, 0, 0, 0)); fh.alpha_composite(FO); fh.alpha_composite(h)
    if elbow: fh = rot(fh, elbow, EL)
    arm = Image.new("RGBA", M.size, (0, 0, 0, 0)); arm.alpha_composite(UP); arm.alpha_composite(fh)
    if shoulder: arm = rot(arm, shoulder, SH)
    out = BASE.copy(); out.alpha_composite(arm); return out

def holes(c):
    ca = np.array(c)[:, :, 3] > 20
    return (~ca) & (Ma > 20)

yy, xx = np.mgrid[0:Ma.shape[0], 0:Ma.shape[1]]
disk = lambda c, r: (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r

sh = np.zeros_like(Ma, bool)
for a in (-12, -25, -40, -60): sh |= holes(comp(shoulder=a)) & torso
sh = ndimage.binary_closing(sh, structure=np.ones((7, 7)))

el = np.zeros_like(Ma, bool)
for e in (-25, -45): el |= holes(comp(elbow=e)) & disk(EL, 55)
el = ndimage.binary_closing(el, structure=np.ones((5, 5)))

wr = np.zeros_like(Ma, bool)
for w in (-15, 15): wr |= holes(comp(wrist=w)) & disk(WR, 45)
wr = ndimage.binary_dilation(wr, iterations=2)

for n, m in (("shoulder", sh), ("elbow", el), ("wrist_seam", wr)):
    Image.fromarray((m * 255).astype(np.uint8)).save(OUT + f"masks/{n}_fill_mask.png")
    print(n, int(m.sum()))

masks = {"shoulder": sh, "elbow": el, "wrist": wr}
font = lambda s: ImageFont.truetype(F, s)

def render(path, title, shoulder=0, elbow=0, wrist=0):
    c = comp(shoulder, elbow, wrist); arr = np.array(c.copy())
    for n, col in (("shoulder", (255, 40, 60)), ("elbow", (255, 180, 30)), ("wrist", (0, 200, 255))):
        ov = np.zeros_like(arr); ov[masks[n]] = [col[0], col[1], col[2], 90]
        arr = np.array(Image.alpha_composite(Image.fromarray(arr), Image.fromarray(ov.astype(np.uint8))))
    bg = Image.new("RGB", M.size, (246, 246, 250)).convert("RGBA"); bg.alpha_composite(Image.fromarray(arr))
    d = ImageDraw.Draw(bg); d.rectangle([0, 0, bg.width - 1, 64], fill=(10, 10, 18, 235))
    d.text((20, 14), title, font=font(30), fill=(255, 255, 255))
    d.text((20, bg.height - 50), f"剩余空洞 {int(holes(c).sum()):,} px（彩色=补绘蒙版）", font=font(26), fill=(255, 200, 90))
    bg.convert("RGB").crop((0, 0, 900, 1150)).save(path, quality=92)

render(OUT + "tests/shoulder_-60.png", "肩部 -60° · 补绘蒙版", shoulder=-60)
render(OUT + "tests/elbow_-45.png", "肘部 -45° · 补绘蒙版", elbow=-45)
render(OUT + "tests/wrist_+15.png", "手腕 +15° · 补绘蒙版", wrist=15)
render(OUT + "tests/combo.png", "肩 -60° + 肘 -45° + 腕 +15°", -60, -45, 15)
print("renders ok")

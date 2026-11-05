#!/usr/bin/env python3
"""V0.4.3 肩部重绘验收（几何 + 美术分离）。

用法: python3 scripts/verify_shoulder_v4.py <shoulder_fill_v4.png>
输出: live2d/v043/review/report.json / report.md / *.png
"""
import json, sys, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
V42 = ROOT / "live2d/v042"
OUT = ROOT / "live2d/v043/review"
SH = (503, 411)
BAND = (455, 455, 530, 545)      # 需要检查的贴片接缝区
STRAP = (555, 380, 625, 700)     # 肩带/扣具区
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
font = lambda s: ImageFont.truetype(FONT, s)

def rot(im, a, c): return im.rotate(a, center=c, resample=Image.BICUBIC)

def main(path):
    p = pathlib.Path(path)
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {"file": str(p), "geometry": {}, "art": {}, "verdict": {}}
    if not p.exists():
        print("FAIL: 文件不存在", p); return

    master = Image.open(V42.parent.parent / ".joint-v03/native/character_master_expanded.png").convert("RGBA")
    torso = Image.open(V42 / "torso_base_clean.png").convert("RGBA")
    mask = np.array(Image.open(V42 / "shoulder_repaint_mask_v3.png").convert("L")) > 12
    fill = Image.open(p).convert("RGBA")
    fa = np.array(fill)[:, :, 3]
    Ma = np.array(master)[:, :, 3]

    # 1 格式
    rep["geometry"]["format"] = {"size": list(fill.size), "mode": fill.mode,
        "ok": fill.size == (1152, 1495) and fill.mode == "RGBA" and (fa < 250).any(),
        "transparent_pct": round(float((fa < 12).mean()) * 100, 1)}
    # 2 蒙版
    cov = int(((fa > 20) & mask).sum()); spill = int(((fa > 20) & ~mask).sum()); miss = int(((fa <= 20) & mask).sum())
    rep["geometry"]["mask"] = {"mask_px": int(mask.sum()), "covered": cov, "missing": miss, "spill": spill,
        "coverage_pct": round(cov / mask.sum() * 100, 2), "spill_pct": round(spill / mask.sum() * 100, 2),
        "ok": miss <= mask.sum() * 0.02 and spill <= mask.sum() * 0.02}

    comp = torso.copy(); comp.alpha_composite(fill)
    # 3 袖子残留：与原袖子纹理相关性（克隆检测）
    arm = np.zeros(mask.shape, bool)
    for f in ("arm_screen_left_upper.png", "arm_screen_left_fore.png"):
        arm |= np.array(Image.open(ROOT / ".joint-v03/native" / f).convert("RGBA"))[:, :, 3] > 8
    g_fill = np.array(comp.convert("L"), dtype=float)
    g_orig = np.array(master.convert("L"), dtype=float)
    sel = mask & arm & (fa > 200)
    corr = float(np.corrcoef(g_fill[sel], g_orig[sel])[0, 1]) if sel.sum() > 500 else 1.0
    mad = float(np.abs(g_fill[sel] - g_orig[sel]).mean()) if sel.sum() > 500 else 0.0
    rep["art"]["sleeve_clone"] = {"corr": round(corr, 3), "mean_abs_diff": round(mad, 1),
        "ok": corr <= 0.80, "note": ">0.80 说明仍在克隆原袖子"}

    # 4 接缝带
    x0, y0, x1, y1 = BAND
    gx = np.abs(np.diff(g_fill, axis=1)); gy = np.abs(np.diff(g_fill, axis=0))
    gmag = gx[:-1, :] + gy[:, :-1]
    band = gmag[y0:y1, x0:x1].mean()
    ring = gmag[y0 - 30:y1 + 30, x0 - 30:x1 + 30].mean()
    rep["art"]["seam_band"] = {"band_grad": round(float(band), 1), "ring_grad": round(float(ring), 1),
        "ratio": round(float(band / max(ring, 1e-6)), 2), "ok": band / max(ring, 1e-6) <= 1.5}

    # 5 肩带/扣具/头发未被动
    comp_arr = np.array(comp, dtype=np.int16)[:, :, :3]
    torso_arr = np.array(torso, dtype=np.int16)[:, :, :3]
    diff = np.abs(comp_arr - torso_arr).max(axis=2)
    sx0, sy0, sx1, sy1 = STRAP
    strap_sel = np.zeros(mask.shape, bool); strap_sel[sy0:sy1, sx0:sx1] = True
    strap_sel &= ~mask
    strap_diff = float(diff[strap_sel].max()) if strap_sel.any() else 0.0
    outside = float(diff[~ndimage.binary_dilation(mask, iterations=4)].max())
    rep["art"]["untouched"] = {"strap_max_diff": strap_diff, "outside_max_diff": outside,
        "ok": strap_diff <= 2 and outside <= 2}

    # 6 运动
    arm_up = Image.open(ROOT / ".joint-v03/native/arm_screen_left_upper.png").convert("RGBA")
    arm_fo = Image.open(ROOT / ".joint-v03/native/arm_screen_left_fore.png").convert("RGBA")
    hand = Image.open(V42 / "hand_open_clean.png").convert("RGBA")
    ys = np.arange(mask.shape[0])[:, None]
    rows = []
    base = comp
    for ang in (0, -12, -25, -40, -60):
        fh = Image.new("RGBA", base.size, (0, 0, 0, 0)); fh.alpha_composite(arm_fo); fh.alpha_composite(hand)
        a = Image.new("RGBA", base.size, (0, 0, 0, 0)); a.alpha_composite(arm_up); a.alpha_composite(fh)
        if ang: a = rot(a, ang, SH)
        c = base.copy(); c.alpha_composite(a)
        holes = (np.array(c)[:, :, 3] < 20) & (Ma > 20)
        rows.append({"angle": ang, "shoulder": int((holes & mask).sum()) + int((holes & ~mask & (ys <= 691)).sum()),
                     "forearm_zone": int((holes & ~mask & (ys > 691)).sum())})
        bg = Image.new("RGB", base.size, (240, 240, 246)).convert("RGBA"); bg.alpha_composite(c)
        d = ImageDraw.Draw(bg); d.rectangle([0, 0, 700, 54], fill=(10, 10, 16, 235))
        d.text((16, 12), f"肩 {ang}°  肩区洞 {rows[-1]['shoulder']}  前臂区 {rows[-1]['forearm_zone']}", font=font(26), fill=(255, 255, 255))
        bg.convert("RGB").crop((0, 0, 860, 1080)).save(OUT / f"shoulder_{ang}.png", quality=90)
    rep["geometry"]["motion"] = {"ok": all(r["shoulder"] <= 5 for r in rows), "rows": rows}

    # 7 结构特写
    bg = Image.new("RGB", base.size, (240, 240, 246)).convert("RGBA"); bg.alpha_composite(base)
    bg.convert("RGB").crop((380, 360, 620, 700)).resize((720, 1020)).save(OUT / "structure_zoom.png")

    rep["geometry"]["pass"] = all(v.get("ok") for k, v in rep["geometry"].items() if isinstance(v, dict))
    rep["art"]["pass"] = all(rep["art"][k]["ok"] for k in ("sleeve_clone", "untouched"))  # seam 单独看
    rep["verdict"] = {"geometry": "PASS" if rep["geometry"]["pass"] else "FAIL",
                      "art": "PASS" if rep["art"]["pass"] else "FAIL",
                      "note": "美术是否「像外套」仍需人工看 structure_zoom.png 与 shoulder_-60.png"}
    (OUT / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))
    print(json.dumps(rep["verdict"], ensure_ascii=False))
    print(json.dumps(rep["art"], ensure_ascii=False, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))
    print(json.dumps(rep["geometry"].get("motion", {}), ensure_ascii=False))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "live2d/v043/shoulder_fill_v4.png")

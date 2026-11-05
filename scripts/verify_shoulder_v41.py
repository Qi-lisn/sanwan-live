#!/usr/bin/env python3
"""V4.1 肩部最终修订验收。用法: python3 scripts/verify_shoulder_v41.py <png>"""
import json, sys, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

ROOT = pathlib.Path(__file__).resolve().parents[1]
V42 = ROOT / "live2d/v042"; OUT = ROOT / "live2d/v043/review41"
SH = (503, 411)
STRIP_ORIG = (570, 630, 596, 670)   # 原口袋反光条（含余量）
HEM_Y = 691                          # 蒙版下缘
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
font = lambda s: ImageFont.truetype(FONT, s)
rot = lambda im, a, c: im.rotate(a, center=c, resample=Image.BICUBIC)

def main(path):
    p = pathlib.Path(path); OUT.mkdir(parents=True, exist_ok=True)
    rep = {"file": str(p), "geometry": {}, "art": {}, "verdict": {}}
    if not p.exists():
        print("FAIL: 文件不存在", p); return
    master = Image.open(ROOT/".joint-v03/native/character_master_expanded.png").convert("RGBA")
    torso = Image.open(V42/"torso_base_clean.png").convert("RGBA")
    mask = np.array(Image.open(V42/"shoulder_repaint_mask_v3.png").convert("L")) > 12
    fill = Image.open(p).convert("RGBA")
    fa = np.array(fill)[:, :, 3]; Ma = np.array(master)[:, :, 3]
    ta = np.array(torso)[:, :, 3]

    # 1 格式
    rep["geometry"]["format"] = {"size": list(fill.size), "mode": fill.mode,
        "ok": bool(fill.size == (1152, 1495) and fill.mode == "RGBA" and (fa < 250).any())}
    # 2 覆盖率
    cov = int(((fa > 20) & mask).sum()); miss = int(((fa <= 20) & mask).sum())
    rep["geometry"]["coverage"] = {"mask_px": int(mask.sum()), "covered": cov, "missing": miss,
        "pct": round(cov / mask.sum() * 100, 2), "ok": cov / mask.sum() >= 0.98}
    # 3 溢出
    spill = int(((fa > 20) & ~mask).sum())
    rep["geometry"]["spill"] = {"px": spill, "pct": round(spill / mask.sum() * 100, 2), "ok": spill <= mask.sum() * 0.02}

    comp = torso.copy(); comp.alpha_composite(fill)
    arr = np.array(comp)[:, :, :3].astype(int)
    g = np.array(comp.convert("L"), dtype=float)

    # 4 重复反光条：亮蓝白细条连通块
    strip = (arr[:, :, 2] > 200) & (arr[:, :, 2] - arr[:, :, 0] > 25) & (arr[:, :, 1] > 180)
    region = np.zeros_like(strip); region[600:800, 440:660] = True
    lab, n = ndi.label(strip & region)
    blobs = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(xs) > 150: blobs.append([int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), len(xs)])
    rep["art"]["pocket_strip"] = {"blobs": blobs, "count": len(blobs), "ok": len(blobs) == 1}

    # 5 双下摆：蒙版下缘以下仍覆盖原有不透明像素
    below = np.zeros_like(mask); below[HEM_Y + 1:, :] = True
    hem_over = int(((fa > 20) & below & (ta > 20)).sum())
    rep["art"]["double_hem"] = {"over_px": hem_over, "ok": hem_over <= 500}

    # 6 原反光条/肩带/扣具完整
    x0, y0, x1, y1 = STRIP_ORIG
    d_strip = float(np.abs(arr[y0:y1, x0:x1] - np.array(torso)[:, :, :3].astype(int)[y0:y1, x0:x1]).max())
    strap_sel = np.zeros_like(mask); strap_sel[380:700, 555:625] = True; strap_sel &= ~mask
    d_strap = float(np.abs(arr - np.array(torso)[:, :, :3].astype(int)).max(axis=2)[strap_sel].max()) if strap_sel.any() else 0
    rep["art"]["original_intact"] = {"strip_diff": d_strip, "strap_diff": d_strap,
        "ok": d_strip <= 3 and d_strap <= 3}

    # 7 边缘硬缝：alpha 边界梯度 vs 内部
    edge = ndi.binary_dilation(fa > 20, iterations=1) & ~ndi.binary_erosion(fa > 20, iterations=1)
    gx = np.abs(np.diff(g, axis=1)); gy = np.abs(np.diff(g, axis=0)); gm = gx[:-1, :] + gy[:, :-1]
    e = float(gm[edge[:-1, :-1]].mean()) if edge.any() else 0
    inner = ndi.binary_erosion(mask & (fa > 20), iterations=5)
    i_ = float(gm[inner[:-1, :-1]].mean()) if inner.any() else 1
    rep["art"]["edge_seam"] = {"edge_grad": round(e, 1), "inner_grad": round(i_, 1),
        "ratio": round(e / max(i_, 1e-6), 2), "ok": e / max(i_, 1e-6) <= 2.0}

    # 8 运动
    up = Image.open(ROOT/".joint-v03/native/arm_screen_left_upper.png").convert("RGBA")
    fo = Image.open(ROOT/".joint-v03/native/arm_screen_left_fore.png").convert("RGBA")
    ha = Image.open(V42/"hand_open_clean.png").convert("RGBA")
    ys = np.arange(mask.shape[0])[:, None]; rows = []
    for ang in (0, -12, -25, -40, -60):
        fh = Image.new("RGBA", comp.size, (0,0,0,0)); fh.alpha_composite(fo); fh.alpha_composite(ha)
        a = Image.new("RGBA", comp.size, (0,0,0,0)); a.alpha_composite(up); a.alpha_composite(fh)
        if ang: a = rot(a, ang, SH)
        c = comp.copy(); c.alpha_composite(a)
        holes = (np.array(c)[:, :, 3] < 20) & (Ma > 20)
        rows.append({"angle": ang, "shoulder": int((holes & mask).sum()) + int((holes & ~mask & (ys <= HEM_Y)).sum()),
                     "forearm": int((holes & ~mask & (ys > HEM_Y)).sum())})
        bg = Image.new("RGB", comp.size, (240,240,246)).convert("RGBA"); bg.alpha_composite(c)
        d = ImageDraw.Draw(bg); d.rectangle([0,0,760,52], fill=(10,10,16,235))
        d.text((14,10), f"肩 {ang}°  肩区洞 {rows[-1]['shoulder']}  前臂区 {rows[-1]['forearm']}", font=font(26), fill=(255,255,255))
        bg.convert("RGB").crop((0,0,860,1080)).save(OUT/f"shoulder_{ang}.png", quality=90)
    rep["geometry"]["motion"] = {"ok": all(r["shoulder"] <= 5 for r in rows), "rows": rows}

    bg = Image.new("RGB", comp.size, (240,240,246)).convert("RGBA"); bg.alpha_composite(comp)
    bg.convert("RGB").crop((380,360,620,800)).resize((720,1320)).save(OUT/"structure_zoom.png")

    rep["geometry"]["pass"] = all(rep["geometry"][k].get("ok", True) for k in ("format","coverage","spill","motion"))
    rep["art"]["pass"] = all(rep["art"][k]["ok"] for k in ("pocket_strip","double_hem","original_intact","edge_seam"))
    rep["verdict"] = {"geometry": "PASS" if rep["geometry"]["pass"] else "FAIL",
                      "art": "PASS" if rep["art"]["pass"] else "FAIL"}
    (OUT/"report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)))
    print(json.dumps(rep["verdict"], ensure_ascii=False))
    for k in ("coverage","spill"): print(k, rep["geometry"][k])
    for k in ("pocket_strip","double_hem","original_intact","edge_seam"): print(k, rep["art"][k])
    print("motion", rep["geometry"]["motion"]["rows"])

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "live2d/v043/shoulder_fill_v41.png")

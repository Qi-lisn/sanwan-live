#!/usr/bin/env python3
"""V0.4 肩部补绘验收：检查 shoulder_fill.png 是否合格。

用法: python3 live2d/tools/verify_shoulder.py [路径]
默认: live2d/v04_project/layers/shoulder_fill.png
输出: live2d/v04_project/tests/shoulder_verify/{report.json,report.md,*.png}
"""
import json, sys, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJ = ROOT / "live2d/v04_project"
OUT = PROJ / "tests/shoulder_verify"
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
SH = (503, 411); EL = (455, 622)
CANVAS = (1152, 1495)

def font(s, b=False):
    return ImageFont.truetype(FONT, s, index=1 if b else 0)

def load(p, size=None):
    return Image.open(p).convert("RGBA")

def rot(im, a, c):
    return im.rotate(a, center=c, resample=Image.BICUBIC)

def main(path=None):
    path = pathlib.Path(path) if path else PROJ / "layers/shoulder_fill.png"
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"file": str(path), "checks": {}, "pass": False}

    v42 = ROOT / "live2d/v042"
    use42 = (v42 / "shoulder_repaint_mask_v3.png").exists()
    torso = load((v42 / "torso_base_clean.png") if use42 else (PROJ / "layers/torso_base.png"))
    master = load(PROJ / "reference/master_expanded.png")
    mask = np.array(Image.open((v42 / "shoulder_repaint_mask_v3.png") if use42 else (PROJ / "masks/shoulder_fill_mask.png")).convert("L")) > 12
    M = np.array(master)

    def fail(msg):
        report["error"] = msg
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
        print("FAIL:", msg)
        return report

    # 1 文件
    if not path.exists():
        return fail(f"文件不存在: {path}")
    f = load(path)
    a = np.array(f)[:, :, 3]
    checks = report["checks"]
    checks["size"] = {"ok": f.size == CANVAS, "value": list(f.size), "expect": list(CANVAS)}
    checks["rgba"] = {"ok": f.mode == "RGBA", "value": f.mode}
    checks["has_alpha"] = {"ok": bool((a < 250).any()), "transparent_ratio": round(float((a < 12).mean()) * 100, 1)}
    if not all([checks["size"]["ok"], checks["rgba"]["ok"], checks["has_alpha"]["ok"]]):
        return fail("格式不合格（尺寸/模式/透明通道）")

    # 2 与蒙版匹配
    fill = a > 20
    covered = int((mask & fill).sum()); spill = int((fill & ~mask).sum()); missing = int((mask & ~fill).sum())
    iou = covered / max(1, int((mask | fill).sum()))
    checks["coverage"] = {
        "mask_px": int(mask.sum()), "covered": covered, "missing": missing, "spill": spill,
        "coverage_pct": round(covered / max(1, int(mask.sum())) * 100, 2),
        "spill_pct": round(spill / max(1, int(mask.sum())) * 100, 2),
        "iou": round(iou, 3),
        "ok": missing <= int(mask.sum() * 0.02) and spill <= int(mask.sum() * 0.05),
    }

    # 3 叠加 + 材质/边缘
    comp = torso.copy(); comp.alpha_composite(f)
    ca = np.array(comp)[:, :, 3]
    hole_in_mask = int(((ca < 20) & mask).sum())
    checks["no_hole"] = {"ok": hole_in_mask == 0, "px": hole_in_mask}

    edge = ndimage.binary_dilation(mask, iterations=2) & ~mask
    inside = ndimage.binary_erosion(mask, iterations=2)
    def mean_rgb(img_arr, region):
        m = region & (img_arr[:, :, 3] > 20)
        return img_arr[:, :, :3][m].mean(axis=0) if m.any() else np.array([0, 0, 0])
    c_arr = np.array(comp)
    fill_mean = mean_rgb(c_arr, inside)
    edge_mean = mean_rgb(c_arr, edge)
    seam = float(np.abs(fill_mean - edge_mean).mean())
    checks["edge_continuity"] = {"ok": seam < 45, "mean_diff": round(seam, 1)}

    # 纹理丰富度：补绘区梯度 vs 邻近躯干梯度（过低=平涂/模糊）
    gray = np.array(comp.convert("L"), dtype=np.float32)
    gx = np.abs(np.diff(gray, axis=1)); gy = np.abs(np.diff(gray, axis=0))
    g = gx[:-1, :] + gy[:, :-1]
    fill_g = float(g[inside[:-1, :-1]].mean()) if inside.any() else 0
    ring = ndimage.binary_dilation(mask, iterations=14) & ~ndimage.binary_dilation(mask, iterations=3)
    ring_g = float(g[ring[:-1, :-1]].mean()) if ring.any() else 1
    ratio = fill_g / max(1e-6, ring_g)
    checks["texture"] = {"ok": ratio > 0.45, "fill_grad": round(fill_g, 2),
                         "ring_grad": round(ring_g, 2), "ratio": round(ratio, 2)}

    # 4 关节合成 0..-60
    arm_up = load(PROJ / "layers/arm_upper.png")
    arm_fo = load(PROJ / "layers/arm_fore.png")
    hand = load(PROJ / "layers/hand_open.png")
    base_with_fill = comp
    angles = [0, -12, -25, -40, -60]
    joint = []
    for ang in angles:
        fh = Image.new("RGBA", CANVAS, (0, 0, 0, 0)); fh.alpha_composite(arm_fo); fh.alpha_composite(hand)
        arm = Image.new("RGBA", CANVAS, (0, 0, 0, 0)); arm.alpha_composite(arm_up); arm.alpha_composite(fh)
        if ang: arm = rot(arm, ang, SH)
        c = base_with_fill.copy(); c.alpha_composite(arm)
        holes = int((((np.array(c)[:, :, 3] < 20) & (M[:, :, 3] > 20))).sum())
        body_holes = int((((np.array(c)[:, :, 3] < 20) & (M[:, :, 3] > 20) & mask).sum()))
        joint.append({"angle": ang, "holes_total": holes, "holes_in_shoulder_mask": body_holes})
        # 出图
        bg = Image.new("RGB", CANVAS, (246, 246, 250)).convert("RGBA"); bg.alpha_composite(c)
        d = ImageDraw.Draw(bg)
        d.rectangle([0, 0, CANVAS[0]-1, 56], fill=(10, 10, 18, 235))
        d.text((16, 12), f"肩 {ang}° · 空洞(肩区) {body_holes:,} px", font=font(28), fill=(255, 255, 255))
        bg.convert("RGB").crop((0, 0, 860, 1080)).save(OUT / f"shoulder_{ang}.png", quality=90)
    checks["joint"] = {"ok": all(j["holes_in_shoulder_mask"] == 0 for j in joint), "detail": joint}

    # 6 其他部位未受影响
    comp_arr = np.array(comp, dtype=np.int16)[:, :, :3]
    torso_arr = np.array(torso, dtype=np.int16)[:, :, :3]
    outside_mask = ~ndimage.binary_dilation(mask, iterations=6)
    diff = np.abs(comp_arr - torso_arr).max(axis=2)
    outside = float(diff[outside_mask].max()) if outside_mask.any() else 0
    checks["others_untouched"] = {"ok": outside <= 2, "max_diff_outside": outside}

    report["pass"] = all(c.get("ok", True) for c in checks.values())
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))

    # markdown
    lines = ["# 肩部补绘验收报告", "", f"文件: `{path}`", ""]
    for k, v in checks.items():
        if k == "joint":
            lines.append(f"- **关节合成**: {'✅' if v['ok'] else '❌'}")
            for j in v["detail"]:
                lines.append(f"  - {j['angle']}°: 肩区空洞 {j['holes_in_shoulder_mask']} px")
        elif isinstance(v, dict):
            mark = "✅" if v.get("ok") else "❌"
            extra = {kk: vv for kk, vv in v.items() if kk != "ok"}
            lines.append(f"- **{k}**: {mark} {extra}")
    lines.append("")
    lines.append(f"## 结论: {'通过' if report['pass'] else '未通过'}")
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return report

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

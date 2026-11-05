#!/usr/bin/env python3
"""生成一段 60 秒原创环境铺底音乐（无版权问题）"""
import numpy as np, wave, pathlib

SR = 24000
DUR = 60
n = SR * DUR
t = np.arange(n) / SR

# 和弦：Am - F - C - G，每 8 秒换一个
chords = [
    [220.00, 261.63, 329.63],  # Am
    [174.61, 220.00, 261.63],  # F
    [261.63, 329.63, 392.00],  # C
    [196.00, 246.94, 293.66],  # G
]
out = np.zeros(n, dtype=np.float32)
seg = 8 * SR
for i in range(DUR // 8):
    s, e = i * seg, (i + 1) * seg
    root = chords[i % 4]
    tt = t[s:e] - t[s]
    env = np.minimum(1, tt / 2.0) * np.minimum(1, (seg / SR - tt) / 2.0)
    for j, f in enumerate(root):
        out[s:e] += (0.10 / (j + 1)) * np.sin(2 * np.pi * f * tt) * env
        out[s:e] += (0.05 / (j + 1)) * np.sin(2 * np.pi * f * 1.003 * tt) * env
    # 低音
    out[s:e] += 0.08 * np.sin(2 * np.pi * (root[0] / 2) * tt) * env

# 极轻的噪声铺底 + 缓慢起伏
rng = np.random.default_rng(3)
air = rng.normal(0, 1, n).astype(np.float32)
air = np.convolve(air, np.ones(200) / 200, mode="same")
out += air * 0.012
lfo = 0.85 + 0.15 * np.sin(2 * np.pi * t / 12)
out *= lfo

out = out / max(1e-6, np.abs(out).max()) * 0.5
pcm = (out * 32767).astype(np.int16)
p = pathlib.Path(__file__).parent / "bgm.wav"
with wave.open(str(p), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("bgm ->", p, f"{DUR}s")

#!/usr/bin/env python3
"""V0.4.2: 生成肩部补绘工程输入（蒙版 v3 / 清理底图 / 参考图 / 覆盖图）。
输入 .joint-v03/native/，输出 live2d/v042/。
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from scipy import ndimage

V=".joint-v03/native/"; OUT="live2d/v042/"
SH=(503,411)
M=Image.open(V+"character_master_expanded.png").convert("RGBA")
UP=Image.open(V+"arm_screen_left_upper.png").convert("RGBA")
FO=Image.open(V+"arm_screen_left_fore.png").convert("RGBA")
HA=Image.open(V+"hand_screen_left_open.png").convert("RGBA")
Ma=np.array(M)[:,:,3]

# 1) 手层补全
arm_union=np.zeros_like(Ma,bool)
for im in (UP,FO,HA): arm_union |= np.array(im)[:,:,3]>8
ys,xs=np.where(np.array(HA)[:,:,3]>12)
box=np.zeros_like(Ma,bool); box[ys.min():ys.max()+1, xs.min():xs.max()+1]=True
residue=box&(Ma>20)&~arm_union
hand=np.array(HA).copy(); hand[residue]=np.array(M)[residue]
Image.fromarray(hand).save(OUT+"hand_open_clean.png")

# 2) 底图清理
base=np.array(M).copy()
for a in (np.array(UP)[:,:,3], np.array(FO)[:,:,3], hand[:,:,3]): base[a>8]=0
base[:,:,3]=np.array(Image.fromarray(base[:,:,3]).filter(ImageFilter.GaussianBlur(0.6)))
Image.fromarray(base).save(OUT+"torso_base_clean.png")
Ba=base[:,:,3]

# 3) 蒙版 v3
holes=(Ma>20)&(Ba<=20)
bridge=np.zeros_like(holes)
for y in range(370,680):
    xs2=np.where(Ba[y]>20)[0]
    if len(xs2)>=2: bridge[y, xs2.min():xs2.max()+1]=True
mask=ndimage.binary_closing(holes&bridge,structure=np.ones((5,5)))
mask=ndimage.binary_dilation(mask,iterations=12)&((Ma>20)|ndimage.binary_dilation(Ma>20,iterations=6))
Image.fromarray((mask*255).astype(np.uint8)).save(OUT+"shoulder_repaint_mask_v3.png")
soft=ndimage.gaussian_filter(mask.astype(np.float32),3)
Image.fromarray((soft*255).astype(np.uint8)).save(OUT+"shoulder_repaint_mask_v3_soft.png")
print("mask", int(mask.sum()))

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage

ROOT = ".joint-v03/native/"
SHOULDER=(503,411); ELBOW=(455,622); WRIST=(413,785)
FONT="/System/Library/Fonts/Hiragino Sans GB.ttc"
def font(s,b=False): return ImageFont.truetype(FONT,s,index=1 if b else 0)

M=Image.open(ROOT+"character_master_expanded.png").convert("RGBA")
UP=Image.open(ROOT+"arm_screen_left_upper.png").convert("RGBA")
FO=Image.open(ROOT+"arm_screen_left_fore.png").convert("RGBA")
HA=Image.open(ROOT+"hand_screen_left_open.png").convert("RGBA")
PH=Image.open(ROOT+"UNDERPAINT_PLACEHOLDER_NOT_FINAL.png").convert("RGBA")
Ma=np.array(M)[:,:,3]

base=np.array(M).copy()
for im in (UP,FO,HA):
    a=np.array(im)[:,:,3]; base[a>8]=0
BASE=Image.fromarray(base)
BODY=np.array(BASE)[:,:,3]>20
DIST=ndimage.distance_transform_edt(~BODY)

def rot(im,ang,c): return im.rotate(ang,center=c,resample=Image.BICUBIC)

def build(shoulder_deg=0, elbow_deg=0, wrist_deg=0, placeholder=False):
    fh=Image.new("RGBA",M.size,(0,0,0,0)); fh.alpha_composite(FO); fh.alpha_composite(HA)
    if wrist_deg:
        h2=rot(HA,wrist_deg,WRIST)
        fh=Image.new("RGBA",M.size,(0,0,0,0)); fh.alpha_composite(FO); fh.alpha_composite(h2)
    if elbow_deg: fh=rot(fh,elbow_deg,ELBOW)
    arm=Image.new("RGBA",M.size,(0,0,0,0)); arm.alpha_composite(UP); arm.alpha_composite(fh)
    if shoulder_deg: arm=rot(arm,shoulder_deg,SHOULDER)
    out=BASE.copy()
    if placeholder: out.alpha_composite(PH)
    out.alpha_composite(arm)
    return out, arm

def holes(comp):
    ca=np.array(comp)[:,:,3]>20
    h=(~ca)&(Ma>20)
    return h, h&(DIST<=18), h&(DIST>18)

def bbox(im):
    a=np.array(im)[:,:,3]>12
    if not a.any(): return None
    ys,xs=np.where(a); return (int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max()))

def checker(w,h,step=14):
    im=Image.new("RGB",(w,h),(248,248,250)); d=ImageDraw.Draw(im)
    for y in range(0,h,step):
        for x in range(0,w,step):
            if (x//step+y//step)%2: d.rectangle([x,y,x+step-1,y+step-1],fill=(214,214,222))
    return im

def paint(comp):
    h,near,bg=holes(comp)
    arr=np.array(comp.copy()); ov=np.zeros_like(arr)
    ov[near]=[255,45,60,175]; ov[bg]=[70,140,255,110]
    out=Image.alpha_composite(comp,Image.fromarray(ov.astype(np.uint8)))
    edge=ndimage.binary_dilation(near,iterations=2)&~near
    ov2=np.zeros_like(arr); ov2[edge]=[255,215,60,220]
    return Image.alpha_composite(out,Image.fromarray(ov2.astype(np.uint8))), int(h.sum()), int(near.sum()), int(bg.sum())

CROP=(60,300,780,900); PW,PHH=320,296
def panel(comp,title,sub,ok):
    vis,_,_,_=paint(comp)
    p=checker(PW,PHH).convert("RGBA")
    p.alpha_composite(vis.crop(CROP).resize((PW,PHH),Image.LANCZOS))
    d=ImageDraw.Draw(p); d.rectangle([0,0,PW-1,44],fill=(10,10,18,235))
    d.text((8,4),title,font=font(17,True),fill=(255,255,255))
    d.text((8,26),sub,font=font(13),fill=(150,225,170) if ok else (255,120,140))
    return p

rows=[]; stats=[]
row=[]
for s in (0,-12,-25,-40,-60):
    comp,_=build(shoulder_deg=s)
    h,n,b=holes(comp); stats.append(("肩",s,int(h.sum()),int(n.sum()),int(b.sum()),bbox(comp)))
    row.append(panel(comp,f"肩 {s}°",f"需补 {int(n.sum()):,} / 背景 {int(b.sum()):,}",n.sum()==0))
rows.append(("① 肩抬起（0 → -60°）",row))

row=[]
for e in (0,-25,-45):
    comp,_=build(elbow_deg=e)
    h,n,b=holes(comp); stats.append(("肘",e,int(h.sum()),int(n.sum()),int(b.sum()),bbox(comp)))
    row.append(panel(comp,f"肘 {e}°",f"需补 {int(n.sum()):,}",n.sum()==0))
row+=[None,None]; rows.append(("② 肘弯曲（0 → -45°）",row))

row=[]
for w in (-15,0,15):
    comp,_=build(wrist_deg=w)
    h,n,b=holes(comp); stats.append(("腕",w,int(h.sum()),int(n.sum()),int(b.sum()),bbox(comp)))
    row.append(panel(comp,f"腕 {w:+d}°",f"需补 {int(n.sum()):,}",n.sum()==0))
row+=[None,None]; rows.append(("③ 手腕摆动（±15°）",row))

# 组合动作 + 占位底图对比
comp,_=build(shoulder_deg=-60,elbow_deg=-45,wrist_deg=15)
h,n,b=holes(comp); stats.append(("组合",-60,int(h.sum()),int(n.sum()),int(b.sum()),bbox(comp)))
comp_ph,_=build(shoulder_deg=-60,elbow_deg=-45,wrist_deg=15,placeholder=True)
h2,n2,b2=holes(comp_ph)
row=[panel(comp,"组合 无底图",f"需补 {int(n.sum()):,}",n.sum()==0),
     panel(comp_ph,"组合 带占位",f"需补 {int(n2.sum()):,}（占位掩盖）",False),None,None,None]
rows.append(("④ 肩-60° + 肘-45° + 腕+15°（有/无占位底图）",row))

HEAD=104; T=30; GAP=10
W=24+5*(PW+GAP)+12; HH=HEAD+4*(T+PHH+GAP)+10
grid=Image.new("RGB",(W,HH),(16,16,24)); d=ImageDraw.Draw(grid)
d.text((24,14),"三万 V0.3 关节结构 · 实际图层旋转测试",font=font(25,True),fill=(255,255,255))
d.text((24,50),"画布 1152×1495（原图右移100）· 关节点 肩(503,411)/肘(455,622)/腕(413,785) · 红=需补绘 蓝=背景空洞",font=font(15),fill=(165,165,200))
y=HEAD
for title,row in rows:
    d.text((24,y),title,font=font(17,True),fill=(140,195,255)); y+=T
    for c,p in enumerate(row):
        if p: grid.paste(p.convert("RGB"),(24+c*(PW+GAP),y))
    y+=PHH+GAP
grid.save("live2d/guides/v03_joint_motion_tests.png")

print(f"{'关节':<4}{'角度':>6}{'总空洞':>9}{'需补绘':>9}{'背景':>9}  bbox")
for s in stats:
    print(f"{s[0]:<4}{s[1]:>6}{s[2]:>9}{s[3]:>9}{s[4]:>9}  {s[5]}")

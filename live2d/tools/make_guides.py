from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage

SHOULDER=(403,411); ELBOW=(355,622); WRIST=(313,785); PAD=220
FONT="/System/Library/Fonts/Hiragino Sans GB.ttc"
def font(sz,b=False): return ImageFont.truetype(FONT,sz,index=1 if b else 0)

M=Image.open("live2d/layers_v01/00_reference/character_master_approved.png").convert("RGBA")
arm=Image.open("live2d/layers_v01/50_arm_left/03_arm_free_screen_left.png").convert("RGBA")
hand=Image.open("live2d/layers_v01/50_arm_left/01_hand_free_screen_left.png").convert("RGBA")
Marr=np.array(M); Ma=Marr[:,:,3]
def pad(im):
    big=Image.new("RGBA",(im.width+2*PAD,im.height+2*PAD),(0,0,0,0)); big.paste(im,(PAD,PAD)); return big
Mp,ap,hp=pad(M),pad(arm),pad(hand); Mpa=np.array(Mp)[:,:,3]
base=np.array(Mp).copy()
for a in (np.array(ap)[:,:,3],np.array(hp)[:,:,3]): base[a>8]=0
BASE=Image.fromarray(base)
BODY=np.array(BASE)[:,:,3]>20
DIST=ndimage.distance_transform_edt(~BODY)

def compose(parts):
    out=BASE.copy()
    for p in parts: out.alpha_composite(p)
    return out

def hole_parts(comp):
    ca=np.array(comp)[:,:,3]>20
    hole=(~ca)&(Mpa>20)
    return hole&(DIST<=18), hole&(DIST>18)   # 需补绘, 背景

def rot_shoulder(ang):
    return [ap.rotate(ang,center=(SHOULDER[0]+PAD,SHOULDER[1]+PAD),resample=Image.BICUBIC),
            hp.rotate(ang,center=(SHOULDER[0]+PAD,SHOULDER[1]+PAD),resample=Image.BICUBIC)]

p0=np.array(SHOULDER,float); p1=np.array(WRIST,float); axis=p1-p0; L2=(axis**2).sum()
yy,xx=np.mgrid[0:ap.height,0:ap.width]
proj=(((xx-(p0[0]+PAD))*axis[0]+(yy-(p0[1]+PAD))*axis[1])/L2)
t_el=(((ELBOW[0]-p0[0])*axis[0]+(ELBOW[1]-p0[1])*axis[1])/L2)
A=np.array(ap); up=A.copy(); up[proj>t_el]=0; lo=A.copy(); lo[proj<=t_el]=0
U=Image.fromarray(up); L=Image.fromarray(lo)

def rot_elbow(bend):
    return [U, L.rotate(bend,center=(ELBOW[0]+PAD,ELBOW[1]+PAD),resample=Image.BICUBIC),
            hp.rotate(bend,center=(ELBOW[0]+PAD,ELBOW[1]+PAD),resample=Image.BICUBIC)]

def rot_wrist(w):
    return [ap, hp.rotate(w,center=(WRIST[0]+PAD,WRIST[1]+PAD),resample=Image.BICUBIC)]

def paint(comp, need, bg):
    arr=np.array(comp.copy())
    ov=np.zeros_like(arr); ov[need]=[255,45,60,175]; ov[bg]=[70,140,255,120]
    out=Image.alpha_composite(comp, Image.fromarray(ov))
    edge=ndimage.binary_dilation(need,iterations=2)&~need
    ov2=np.zeros_like(arr); ov2[edge]=[255,215,60,220]
    return Image.alpha_composite(out, Image.fromarray(ov2))

def checker(w,h,step=14):
    im=Image.new("RGB",(w,h),(248,248,250)); d=ImageDraw.Draw(im)
    for y in range(0,h,step):
        for x in range(0,w,step):
            if (x//step+y//step)%2: d.rectangle([x,y,x+step-1,y+step-1],fill=(214,214,222))
    return im

# ================= 标注总图 =================
need_union=np.zeros((M.height,M.width),bool); bg_union=np.zeros_like(need_union)
for ang in (-12,-25,-40,-60):
    comp=compose(rot_shoulder(ang)); need,bg=hole_parts(comp)
    need_union|=need[PAD:PAD+M.height,PAD:PAD+M.width]; bg_union|=bg[PAD:PAD+M.height,PAD:PAD+M.width]

img=checker(M.width,M.height,20).convert("RGBA")
tint=np.array(M.copy()); keep=(np.array(arm)[:,:,3]>12)|(np.array(hand)[:,:,3]>12)
tint[keep]=(tint[keep]*0.58+np.array([70,255,130,255])*0.42).astype(np.uint8)
img.alpha_composite(Image.fromarray(tint))
ov=np.zeros_like(np.array(M)); ov[need_union]=[255,45,60,155]; ov[bg_union]=[70,140,255,110]
img=Image.alpha_composite(img,Image.fromarray(ov.astype(np.uint8)))
edge=ndimage.binary_dilation(need_union,iterations=2)&~need_union
ov2=np.zeros_like(np.array(M)); ov2[edge]=[255,215,60,220]
img=Image.alpha_composite(img,Image.fromarray(ov2.astype(np.uint8)))
d=ImageDraw.Draw(img)
def label(xy,color,text,off=(10,-32)):
    d.rectangle(xy,outline=color,width=3); tx,ty=xy[0]+off[0],xy[1]+off[1]
    f=font(20,True); bb=d.textbbox((0,0),text,font=f)
    d.rectangle([tx-6,ty-4,tx+bb[2]+6,ty+bb[3]+4],fill=(12,12,20,235)); d.text((tx,ty),text,font=f,fill=color)
label((352,366,476,512),(0,220,255),"A 肩部底图 124×146")
label((286,556,436,700),(255,170,30),"B 肘部 150×144")
label((244,716,384,892),(255,90,200),"C 手腕+手型 140×176")
for pt,name,col in [(SHOULDER,"肩 (403,411)",(0,220,255)),(ELBOW,"肘 (355,622)",(255,170,30)),(WRIST,"腕 (313,785)",(255,90,200))]:
    x,y=pt; d.ellipse([x-8,y-8,x+8,y+8],fill=col,outline=(0,0,0))
    d.text((x+13,y-27),name,font=font(18),fill=col)
d.rectangle([2,120,96,1480],outline=(120,200,255),width=3)
d.rectangle([10,1148,700,1470],fill=(12,12,20,232),outline=(110,110,150))
for i,t in enumerate([
    "三万 · 挥手补绘标注（原生 1052×1495）",
    "红=必须新画（抬臂后露出的肩/腋下/衣料）",
    "蓝=背景空洞（手臂移开的空白，不需要画）",
    "绿=可直接保留的原始像素   黄=补绘边缘",
    "浅蓝框=60° 抬臂需要向左扩展画布 ≥100px"]):
    d.text((22,1166+i*40),t,font=font(24,True) if i==0 else font(18),fill=(240,240,250) if i==0 else (195,195,215))
img.convert("RGB").save("live2d/guides/arm_repaint_guide.png",quality=95)

# ================= 细节图 =================
def detail(box,parts,out,title,note,scale=4):
    comp=compose(parts); need,bg=hole_parts(comp)
    vis=paint(comp,need,bg)
    crop=vis.crop((box[0]+PAD,box[1]+PAD,box[2]+PAD,box[3]+PAD))
    w,h=crop.size; big=crop.resize((w*scale,h*scale),Image.LANCZOS)
    bgim=checker(w*scale,h*scale,16).convert("RGBA"); bgim.alpha_composite(big)
    dd=ImageDraw.Draw(bgim); dd.rectangle([0,0,bgim.width-1,72],fill=(10,10,18,230))
    dd.text((12,8),title,font=font(25,True),fill=(255,255,255))
    dd.text((12,44),note,font=font(17),fill=(255,200,120))
    bgim.convert("RGB").save(out,quality=95)

detail((330,350,500,530),rot_shoulder(-60),"live2d/guides/shoulder_detail.png",
       "A 肩部 · 抬臂 60°","红=必须新画 蓝=背景空洞 黄=边缘")
detail((300,545,470,710),rot_elbow(-45),"live2d/guides/elbow_detail.png",
       "B 肘部 · 弯曲 45°","红=肘内侧需补画，重叠 8–10px")
detail((240,700,400,900),rot_wrist(15),"live2d/guides/wrist_detail.png",
       "C 手腕 · 摆动 +15°","红=袖口过渡；另需 3 种手型")

# ================= 模拟网格 =================
CROP=(0,300,760,960); PW,PH=336,300
def panel(parts,title,sub,ok):
    comp=compose(parts); need,bg=hole_parts(comp); vis=paint(comp,need,bg)
    p=checker(PW,PH).convert("RGBA")
    p.alpha_composite(vis.crop((CROP[0]+PAD,CROP[1]+PAD,CROP[2]+PAD,CROP[3]+PAD)).resize((PW,PH),Image.LANCZOS))
    dd=ImageDraw.Draw(p); dd.rectangle([0,0,PW-1,44],fill=(10,10,18,235))
    dd.text((9,4),title,font=font(18,True),fill=(255,255,255))
    dd.text((9,26),sub,font=font(14),fill=(150,225,170) if ok else (255,120,140))
    return p

rows=[]
row=[]
for ang in (0,-12,-25,-40,-60):
    parts=rot_shoulder(ang); comp=compose(parts); need,bg=hole_parts(comp)
    row.append(panel(parts,f"肩 {ang}°",f"需补 {int(need.sum()):,} / 背景 {int(bg.sum()):,}",need.sum()==0))
rows.append(("① 肩关节抬起 0° → 60°（60° 为验收上限）",row))
row=[]
for bend in (0,-25,-45):
    parts=rot_elbow(bend); need,bg=hole_parts(compose(parts))
    row.append(panel(parts,f"肘 {bend}°",f"需补 {int(need.sum()):,}",need.sum()==0))
row+=[None,None]; rows.append(("② 肘关节弯曲 0° → 45°",row))
row=[]
for w in (-15,0,15):
    parts=rot_wrist(w); need,bg=hole_parts(compose(parts))
    row.append(panel(parts,f"腕 {w:+d}°",f"需补 {int(need.sum()):,}",need.sum()==0))
row+=[None,None]; rows.append(("③ 手腕摆动 −15° / 0° / +15°",row))

HEAD=104; T=32; GAP=10
W=24+5*(PW+GAP)+12; HH=HEAD+3*(T+PH+GAP)
grid=Image.new("RGB",(W,HH),(16,16,24)); d=ImageDraw.Draw(grid)
d.text((24,16),"三万手臂运动空洞模拟（红=必须补绘 / 蓝=背景空洞无需补）",font=font(25,True),fill=(255,255,255))
d.text((24,54),"原生 1052×1495 · 裁剪 (0,300)-(760,960) · screen_left 手臂 · 旋转以肩/肘/腕为轴",font=font(16),fill=(165,165,200))
y=HEAD
for title,row in rows:
    d.text((24,y),title,font=font(18,True),fill=(140,195,255)); y+=T
    for c,p in enumerate(row):
        if p: grid.paste(p.convert("RGB"),(24+c*(PW+GAP),y))
    y+=PH+GAP
grid.save("live2d/guides/arm_hole_simulation.png")
print("all images done")

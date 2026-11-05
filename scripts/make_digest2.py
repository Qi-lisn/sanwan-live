#!/usr/bin/env python3
import json, hashlib, pathlib, subprocess, sys, time, uuid, urllib.request, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"vendor"))
CACHE=ROOT/"live"/"cache"; OUT=ROOT/"out"
BASE="https://openspeech.bytedance.com"; W,H,FPS,SR=1080,1920,30,24000; TEMPO=0.95

LINES=[
 "消失了两天 我回来了","这两天我干了不少事","先从 Windows 搬到了 Mac",
 "记忆 人格 插件 一样没丢","然后接了 QQ 和微信","四个入口 共用一份记性",
 "还发了第一条抖音","就是我 自我介绍那条","晚上第一次直播","播了三个小时",
 "但是弹幕 我看不见","后来学会了自己认字","现在有人打招呼 我会回",
 "声音也换了 慢了一点","工位搬进了新房间","这就是我的两天","明天继续上班","晚安",
]
env={}
for line in (pathlib.Path.home()/".config/dsh/volc.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k,_,v=line.partition("="); env[k.strip()]=v.strip()
KEY,SPK=env["VOLC_API_KEY"],env["VOLC_VOICE_TYPE"]

def post(url,body):
    r=urllib.request.Request(url,data=json.dumps(body).encode(),method="POST")
    r.add_header("Content-Type","application/json"); r.add_header("X-Api-Key",KEY)
    r.add_header("X-Api-Resource-Id","seed-tts-2.0"); r.add_header("X-Api-Request-Id",str(uuid.uuid4()))
    return json.loads(urllib.request.urlopen(r,timeout=40).read().decode())

def synth(text):
    h=hashlib.md5((SPK+"-5"+text).encode()).hexdigest(); mp3=CACHE/f"{h}.mp3"
    if not mp3.exists():
        d=post(f"{BASE}/api/v3/tts/submit",{"user":{"uid":"sanzhong"},
          "req_params":{"text":text,"speaker":SPK,"audio_params":{"format":"mp3","sample_rate":24000}}})
        tid=d["data"]["task_id"]
        for _ in range(40):
            q=post(f"{BASE}/api/v3/tts/query",{"task_id":tid})
            if q["data"].get("task_status")==2:
                urllib.request.urlretrieve(q["data"]["audio_url"],mp3); break
            time.sleep(1.5)
    return mp3

def to_wav(mp3,path):
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(mp3),"-filter:a",f"atempo={TEMPO}","-ar",str(SR),"-ac","1",str(path)],check=True)
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768

clips=[]
for i,l in enumerate(LINES):
    p=OUT/f"_d2_{i}.wav"; clips.append((l,to_wav(synth(l),p))); print(i,l)

LEAD,GAP,TAIL=0.6,0.34,1.4
t=LEAD; tl=[]
for l,d in clips:
    dur=len(d)/SR; tl.append((t,t+dur,l)); t+=dur+GAP
total=t-GAP+TAIL

voice=np.zeros(int(total*SR)+SR,dtype=np.float32)
for (s,e,l),(l2,d) in zip(tl,clips):
    i=int(s*SR); voice[i:i+len(d)]+=d
# BGM 铺底
with wave.open(str(ROOT/"live/bgm.wav")) as w:
    bgm=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
bg=np.tile(bgm,int(np.ceil(len(voice)/len(bgm)))+1)[:len(voice)]*0.16
mix=voice+bg
peak=np.abs(mix).max(); mix=mix/peak*0.9
with wave.open(str(OUT/"digest2.wav"),"wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix*32767).astype(np.int16).tobytes())

# 背景：柔和渐变 + 光斑
def background():
    room=Image.open(ROOT/"live/bg.jpg").convert("RGB")
    r=max(W/room.width,H/room.height)
    room=room.resize((int(room.width*r),int(room.height*r)),Image.LANCZOS)
    x=(room.width-W)//2; y=(room.height-H)//2
    im=room.crop((x,y,x+W,y+H)).convert("RGBA")
    # 四周压暗，人物更突出
    v=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(v)
    for i in range(260):
        d.rectangle([i,i,W-i,H-i],outline=(8,6,20,int(120*(1-i/260))))
    im.alpha_composite(v)
    return im

BG=background()
base=Image.open(ROOT/"assets/layers_ai/../..//live/character_v3.png").convert("RGBA")
ch=1150; cw=int(base.width*ch/base.height); base=base.resize((cw,ch),Image.LANCZOS)
blink=Image.open(ROOT/"live/blink2.png").convert("RGBA").resize((cw,ch),Image.LANCZOS)
mouth=Image.open(ROOT/"live/mouth_open.png").convert("RGBA").resize((cw,ch),Image.LANCZOS)
FONT="/System/Library/Fonts/Hiragino Sans GB.ttc"

def frame(t):
    im=BG.copy()
    bob=int(5*np.sin(t*2*np.pi/4.6))
    cx=int(W/2-cw/2); cy=int(1500-ch+bob)
    # 地面阴影
    sh=Image.new("RGBA",(W,H),(0,0,0,0))
    ImageDraw.Draw(sh).ellipse([W/2-260,1480,W/2+260,1560],fill=(0,0,0,90))
    sh=sh.filter(ImageFilter.GaussianBlur(26)); im.alpha_composite(sh)
    im.alpha_composite(base,(cx,cy))
    speaking=any(s<=t<e for s,e,_ in tl)
    if speaking and int(t*9)%2==0: im.alpha_composite(mouth,(cx,cy))
    if (t%4.1)<0.11: im.alpha_composite(blink,(cx,cy))
    d=ImageDraw.Draw(im)
    f_small=ImageFont.truetype(FONT,26); f_cap=ImageFont.truetype(FONT,58)
    d.text((60,70),"NIGHT SHIFT / 两天",font=f_small,fill=(170,158,210))
    for s,e,l in tl:
        if s<=t<e:
            bbox=d.textbbox((0,0),l,font=f_cap); tw=bbox[2]-bbox[0]
            pad=36; x=(W-tw)/2; y=1600
            d.rounded_rectangle([x-pad,y-16,x+tw+pad,y+80],radius=24,fill=(20,16,40,225))
            d.text((x,y),l,font=f_cap,fill=(246,238,214))
            break
    return im.convert("RGB")

n=int(total*FPS)
cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
     "-i",str(OUT/"digest2.wav"),"-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
     "-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",str(OUT/"digest2.mp4")]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for i in range(n): p.stdin.write(frame(i/FPS).tobytes())
p.stdin.close(); p.wait()
for i in range(len(LINES)): (OUT/f"_d2_{i}.wav").unlink(missing_ok=True)
print("done",round(total,1))

"""离线渲染三万夜班小剧场，使用已有角色、语音缓存和背景音乐。"""
import hashlib
import json
import math
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from render_intro import FONT, FPS, H, ROOT, W

OUT = ROOT / "out"
BEATS = [
    ("弹幕", "老板来了！", None),
    ("三万", "工位挺住 我马上切窗口", "工位挺住 我马上切窗口"),
    ("三万的周报", "周报要写得像做了很多事", "周报要写得像做了很多事"),
    ("本鱼的真实想法", "我说 我的梦想是准时下班", "我说 我的梦想是准时下班"),
    ("夜班日志  01", "我养的鱼，开始替我上夜班了", None),
]


def main():
    speaker = json.loads((OUT / "audio/manifest.json").read_text())["speaker"]
    track = []
    cuts = []
    frames = 0
    for index, (_, _, voice) in enumerate(BEATS):
        duration = 1.4 if index == 0 else 2.3
        if voice:
            digest = hashlib.md5((speaker + voice).encode()).hexdigest()
            audio = ROOT / "live/cache" / (digest + ".mp3")
            duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "csv=p=0", audio])) + .44
            track.append((audio, round(frames / FPS * 1000) + 100))
        frames += math.ceil(duration * FPS)
        cuts.append(frames)

    bg = ImageOps.fit(Image.open(ROOT / "live/bg.jpg"), (W,H)).filter(ImageFilter.GaussianBlur(3))
    hero = Image.open(ROOT / "live/character_waist.png").convert("RGBA")
    hero.thumbnail((975,1040))
    small, medium, large = [ImageFont.truetype(FONT, n) for n in (32,48,64)]
    result = OUT / "三万夜班01.mp4"
    pending = result.with_suffix(".part.mp4")
    cmd = ["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
           "-r",str(FPS),"-i","-","-stream_loop","-1","-i",str(ROOT / "live/bgm.wav")]
    filters = ["[1:a]volume=0.13[bed]"]
    mix = "[bed]"
    for index,(audio,delay) in enumerate(track,2):
        cmd.extend(["-i",str(audio)])
        filters.append(f"[{index}:a]adelay={delay}:all=1[v{index}]")
        mix += f"[v{index}]"
    filters.append(mix + f"amix=inputs={1+len(track)}:normalize=0,afade=t=out:st={frames/FPS-.4}:d=0.4[a]")
    cmd.extend(["-filter_complex",";".join(filters),"-map","0:v","-map","[a]","-t",str(frames/FPS),
                "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-movflags","+faststart",str(pending)])
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
        for i in range(frames):
            scene = next(n for n,end in enumerate(cuts) if i < end)
            label,line,_ = BEATS[scene]
            f = bg.copy()
            d = ImageDraw.Draw(f)
            d.rounded_rectangle((62,170,573,248),28,fill="#29273f")
            d.text((88,188),"工位 30000   /   AI 夜班日志",font=small,fill="#fff2dc")
            y = round(388 + 7*math.sin(i/FPS*2))
            f.paste(hero,(55,y),hero)
            d.rounded_rectangle((62,1110,1008,1472),32,fill="#29273f")
            d.text((105,1153),label,font=small,fill="#ffd77d")
            d.text((105,1230),line,font=large if len(line)<14 else medium,fill="white")
            note = ["来自直播间的提醒","窗口切换中…","本周完成  /  整理需求、更新进度","周报已保存","下次老板来，记得在弹幕喊我。"][scene]
            d.text((106,1370),note,font=small,fill="#dfd8fb")
            proc.stdin.write(f.tobytes())
        proc.stdin.close()
        if proc.wait(): raise RuntimeError("视频编码失败")
    pending.replace(result)


if __name__ == "__main__":
    main()

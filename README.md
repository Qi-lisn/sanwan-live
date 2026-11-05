# 三万夜班电台 · AI 虚拟主播直播系统

给「三万」——一条住在电脑里的蓝色小鲸鱼——做抖音直播的全套工具：舞台页面、语音合成、
抖音弹幕直连、点歌台、AI 回复、以及用 Seed-VC 做的「真唱歌」。

## 它是什么

- **舞台页**：HTML 页面（1920×1080），OBS 浏览器源采集，推给抖音直播伴侣
- **念稿与闲聊**：夜班树洞语料 + 话题/吐槽/提问/小动作多种内容轮换，不念死稿
- **弹幕直连**：连抖音直播间 WebSocket，拿到真实弹幕、进场、礼物（不用截图 OCR）
- **AI 回复**：DeepSeek 生成短句回复，超时自动回退模板；危机语句走 12356 兜底
- **点歌台**：观众发「点歌 勋章」，识别歌名 → 排队 → 自动切歌，带歌名动画、曲库、点歌榜、打赏罐
- **唱歌**：Seed-VC 零样本变声，把歌曲人声换成三万的音色，再和原伴奏混音
- **Live2D**：渲染管线（Cubism + pixi-live2d-display），等模型接入

## 目录

```
live/           舞台与直播服务
  server.py       出词 / TTS / 播放 / 接口
  brain.py        DeepSeek 回复
  danmaku.py      抖音弹幕直连
  content.json    语料（话题/吐槽/提问/小动作）
  scripts.json    念稿
  songs.json      曲库与歌词
  stage_sing.html 卖艺点歌台（当前使用）
  stage_wide.html 横屏电台版
  live2d.html     Live2D 渲染页
train/          Seed-VC 唱歌流水线
  make_song.py    一键：分离 → 变声 → 混音
  register_songs.py  把成品登记进曲库
scripts/        抖音发布、渲染、TTS 等脚本
docs/           Live2D 需求书等文档
assets/         立绘与图层
```

## V1 动作系统与控制台

- 控制台：`http://127.0.0.1:8765/control.html`（本机运维用，别暴露到公网）
- 动作：`wave` 挥手 / `happy` 开心 / `shy` 害羞 / `nod` 点头 / `laugh` 笑 / `dance_cute` 跳舞
- 接口：`GET /action_state`、`POST /action {"name":"wave"}`、`POST /control {"auto_actions":true}`
- 自动动作默认**关闭**；打开后弹幕含「跳个舞 / 挥手 / 可爱」会触发，带冷却
- 跳舞需要 `live/motions/dance_cute.webm`（透明背景），没有时退回整图摇摆示意
- `paused` 只停角色动作，不停 TTS、唱歌和推流

## 跑起来

1. 安装依赖

```bash
pip install -r requirements.txt
npm install
```

2. 配置密钥（复制 `.env.example` 为 `.env` 填好，或写到 `~/.config/dsh/`）

3. 启动舞台与弹幕

```bash
python3 live/server.py          # 舞台 + TTS + 接口，127.0.0.1:8765
python3 live/danmaku.py auto    # 弹幕直连，auto 会从直播伴侣日志里读当前房间号
```

4. OBS 加浏览器源：`http://127.0.0.1:8765/stage_sing.html`，1920×1080，开虚拟摄像头

5. 直播伴侣选 OBS 虚拟摄像头，开始直播

## 弹幕直连依赖（需自行安装）

弹幕走 [saermart/DouyinLiveWebFetcher](https://github.com/saermart/DouyinLiveWebFetcher)（AGPL-3.0）。
因为许可证原因**没有放进本仓库**，请自行放入：

```bash
git clone https://github.com/saermart/DouyinLiveWebFetcher.git live/vendor/douyin_fetcher
```

并把它 `liveMan.py` 里的 `from py_mini_racer import MiniRacer` 换成本仓库使用的
PyExecJS 垫片（Apple Silicon 上 py-mini-racer 不可用），见 `docs/danmaku-mac.md`。

## 唱歌（Seed-VC）

```bash
# 1) 准备参考音色：用 TTS 生成 10–20 秒干净人声，存成 train/ref_sanwan.wav
# 2) 转换整首
python3 train/make_song.py 歌曲.mp3 '' '' 输出名
# 3) 登记进曲库
python3 train/register_songs.py
```

CPU 上 4 分钟的歌约 35–40 分钟。MPS 不支持 float64，代码里默认强制 CPU。

## 版权与合规

- 翻唱音频（`live/songs/*.mp3`）**不入库**，请自己准备合法来源的歌曲
- 音色来自火山引擎 TTS，请勿用于商业发行或转售
- 抖音直播需遵守平台规则：AI 生成内容需标注，无人直播有风险

## License

代码 MIT。第三方组件各自遵循其许可证（见文内链接）。

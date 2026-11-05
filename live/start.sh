#!/bin/zsh
# 启动：舞台服务 + 抖音弹幕直连
cd "${0:A:h}/.." || exit 1
ROOM=$(cat live/room.txt)
if ! lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null; then
  nohup python3 live/server.py >/tmp/live.log 2>&1 &
  sleep 2
fi
echo "弹幕直连房间：$ROOM"
python3 live/danmaku.py "$ROOM"

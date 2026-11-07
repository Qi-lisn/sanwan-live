#!/usr/bin/env bash
# 开播准备：起后端、弹幕、巡检，并把 OBS 切到城市地图
set -e
cd "$(dirname "$0")/.."
echo "[1/4] 停旧后端"
lsof -ti tcp:8765 | xargs -r kill 2>/dev/null || true
sleep 2
echo "[2/4] 起后端 (AUTO=1 CHAT=1 目标 20 单)"
SANWAN_DELIVERY_AUTO=1 SANWAN_DELIVERY_CHAT=1 SANWAN_DAILY_GOAL=20 \
  nohup python3 live/server.py >/tmp/live.log 2>&1 &
sleep 6
echo "[3/4] 起弹幕 + 巡检 + 礼物兜底"
pkill -f "live/danmaku.py" 2>/dev/null || true
nohup python3 -u live/danmaku.py auto >/tmp/danmaku.out 2>&1 &
nohup python3 scripts/monitor_live.py >/dev/null 2>&1 &
nohup python3 scripts/gift_from_mate.py >/dev/null 2>&1 &
sleep 4
echo "[4/4] OBS 切城市地图"
touch /tmp/map_override
nohup node scripts/daypart_switch.js >/tmp/dp_switch.log 2>&1 &
sleep 6
curl -s http://127.0.0.1:8765/delivery | python3 -c "import sys,json;d=json.load(sys.stdin);print('  订单:',d['status'],(d.get('order') or {}).get('place_name'),'| 今日',d['delivered'],'/',d.get('goal'))"
echo "完成。OBS 里确认「地图」源已显示。"

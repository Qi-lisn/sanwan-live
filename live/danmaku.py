#!/usr/bin/env python3
"""抖音直播弹幕直连 -> 喂给本机 /comment

用法: python3 live/danmaku.py 7703933670848138019
      python3 live/danmaku.py https://live.douyin.com/7703933670848138019
"""
import json, os, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor" / "douyin_fetcher"))
sys.path.insert(0, str(ROOT.parent / "vendor"))

from liveMan import DouyinLiveWebFetcher  # noqa: E402

os.chdir(pathlib.Path(__file__).resolve().parent / "vendor" / "douyin_fetcher")

API = "http://127.0.0.1:8765/comment"
LOG = ROOT.parent / "out" / "danmaku.log"


def log(line):
    ts = time.strftime("%H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")
    print(f"[{ts}] {line}", flush=True)


def post(nick, text):
    req = urllib.request.Request(API, data=json.dumps({"nick": nick, "text": text}, ensure_ascii=False).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())


class Fetcher(DouyinLiveWebFetcher):
    def __init__(self, room_id):
        super().__init__(room_id)
        # 直接给定 room_id，跳过网页解析（抖音网页版对无登录环境会返回空壳）
        self._DouyinLiveWebFetcher__room_id = room_id

    def _wsOnMessage(self, ws, message):
        import gzip
        from protobuf.douyin import PushFrame, Response
        package = PushFrame().parse(message)
        response = Response().parse(gzip.decompress(package.payload))
        if response.need_ack:
            ack = PushFrame(log_id=package.log_id, payload_type='ack',
                            payload=response.internal_ext.encode('utf-8')).SerializeToString()
            ws.send(ack, 2)
        for msg in response.messages_list:
            method = msg.method
            log(f"METHOD {method}")
            handler = {
                'WebcastChatMessage': self._parseChatMsg,
                'WebcastGiftMessage': self._parseGiftMsg,
                'WebcastLikeMessage': self._parseLikeMsg,
                'WebcastMemberMessage': self._parseMemberMsg,
                'WebcastSocialMessage': self._parseSocialMsg,
                'WebcastRoomUserSeqMessage': self._parseRoomUserSeqMsg,
                'WebcastRoomStatsMessage': self._parseRoomStatsMsg,
                'WebcastRoomRankMessage': self._parseRankMsg,
            }.get(method)
            if handler:
                try:
                    handler(msg.payload)
                except Exception as e:
                    log(f"parse err {method}: {type(e).__name__}: {e}")

    def _parseChatMsg(self, payload):
        log("CHAT_RAW")
        from protobuf.douyin import ChatMessage
        try:
            m = ChatMessage().parse(payload)
        except Exception as e:
            log(f"chat parse err {type(e).__name__}: {e}")
            return
        nick = (m.user.nick_name or "").strip()
        text = (m.content or "").strip()
        if not nick or not text:
            return
        log(f"{nick}: {text}")
        try:
            r = post(nick, text)
            if r.get("replied"):
                log(f"  -> 已排回复")
        except Exception as e:
            log(f"  post err {e}")

    def _parseMemberMsg(self, payload):
        from protobuf.douyin import MemberMessage
        try:
            m = MemberMessage().parse(payload)
            nick = (m.user.nick_name or "").strip()
            if nick:
                log(f"(进场) {nick}")
        except Exception:
            pass

    def _parseGiftMsg(self, payload):
        from protobuf.douyin import GiftMessage
        try:
            m = GiftMessage().parse(payload)
            nick = (m.user.nick_name or "").strip()
            name = m.gift.name
            cnt = m.combo_count
            log(f"(礼物) {nick} {name}x{cnt}")
            send_tip(nick, name, int(cnt or 1), int(getattr(m.gift, "diamond_count", 0) or 0) * int(cnt or 1))
        except Exception:
            pass

    def _parseLikeMsg(self, payload):
        pass

    def _parseRankMsg(self, payload):
        pass

    def _parseRoomUserSeqMsg(self, payload):
        pass

    def _parseRoomStatsMsg(self, payload):
        pass


def auto_room():
    import glob
    logs = sorted(glob.glob(str(pathlib.Path.home()/"Library/Logs/Douyin Webcast Mate"/"*.log")),
                  key=lambda p: pathlib.Path(p).stat().st_mtime)
    if not logs:
        return None
    txt = pathlib.Path(logs[-1]).read_text(encoding="utf-8", errors="ignore")
    found = re.findall(r"room_id=(\d+)", txt)
    return found[-1] if found else None


def send_tip(nick, gift, count=1, value=0):
    """统一礼物上报：真实礼物与 --sim-gift 走同一条路径。"""
    try:
        req = urllib.request.Request("http://127.0.0.1:8765/tip",
            data=json.dumps({"nick": nick, "gift": gift, "count": count, "value": value},
                            ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=4).read().decode()
        log(f"  tip -> {r[:80]}")
        return r
    except Exception as e:
        log(f"  tip err {e}")
        return None


def parse_room(arg):
    m = re.search(r"(\d{6,})", arg)
    return m.group(1) if m else None


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--sim-gift":
        # 用法: python3 live/danmaku.py --sim-gift 昵称 礼物 数量 单价
        nick = sys.argv[2] if len(sys.argv) > 2 else "测试观众"
        gift = sys.argv[3] if len(sys.argv) > 3 else "玫瑰"
        cnt = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        unit = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        out = send_tip(nick, gift, cnt, unit * cnt)
        print(out or "failed")
        return
    if len(sys.argv) < 2:
        print("need room id"); sys.exit(1)
    room = auto_room() if sys.argv[1] == "auto" else parse_room(sys.argv[1])
    if not room:
        print("bad room"); sys.exit(1)
    LOG.parent.mkdir(exist_ok=True)
    log(f"connecting room {room}")
    while True:
        try:
            f = Fetcher(room)
            f.start()
        except Exception as e:
            log(f"fatal {type(e).__name__}: {e}")
        log("disconnected, retry in 5s")
        time.sleep(5)


if __name__ == "__main__":
    main()

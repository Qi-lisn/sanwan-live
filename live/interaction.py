"""DSH delivery-scene danmaku interaction rules.

Only active when SANWAN_DELIVERY_CHAT=1. Never changes real gifts/coins.
A deterministic rule layer handles route and earnings questions before the LLM.
"""
from __future__ import annotations

import collections
import random
import re
import threading
import time
from typing import Any

_LOCK = threading.RLock()
_RECENT = collections.OrderedDict()  # bounded (nickname, normalized message) -> last time
_LAST_USER: dict[str, float] = {}
_LAST_GLOBAL = -1e12
_LAST_CMD = -1e12
_LAST_SCENE = -1e12
_SCENE_I = 0
_PENDING_DESTINATION: str | None = None

PLACES = {"学校": "school", "便利店": "shop", "小区": "community", "医院": "hospital", "商场": "mall"}


def _clean_name(nick: str) -> str:
    # Keep spoken nick short; avoid punctuation and markup.
    return re.sub(r"[\r\n\t<>\[\]{}]", "", nick or "观众").strip()[:12] or "观众"


def _status(ds: dict[str, Any]) -> str:
    status = ds.get("status", "idle")
    return {"accepted": "正在去商家取餐", "carrying": "已经取到餐，正在送去客户那里"}.get(status, "正在等下一单")


def _summary(ds: dict[str, Any]) -> str:
    order = ds.get("order") or {}
    if not order:
        return "还没接到单，你要不要帮我选个目的地"
    good = order.get("good", "外卖")
    dest = order.get("place_name", "客户那里")
    return f"这单是{good}，要送到{dest}"


def _pick_response(msg: str, ds: dict[str, Any], delivery: Any) -> tuple[str, str] | None:
    o = ds.get("order") or {}
    active = ds.get("status") in ("accepted", "carrying")
    msg = re.sub(r"[\s，。！？!?、~～…]+", "", msg)
    # Commands must be anchored rather than match any sentence mentioning a destination.
    direct = re.fullmatch(r"(?:下一单|换一单|再来一单|接单|接一单|来一单|开工|开始接单)", msg)
    if direct:
        if active:
            return "这单还没送到呢，送完再接下一单", "order_busy"
        order = delivery.new_order()
        return f"接到了，{order['good']}送{order['place_name']}，出发", "new_order"

    target = re.fullmatch(r"(?:去|送去|下一单去|下一单送|送到)(学校|便利店|小区|医院|商场)", msg)
    if target:
        name = target.group(1)
        if active:
            if delivery is not _NO_COMMANDS:
                queue_destination(PLACES[name])
            return f"这单先送完，下单我再去{name}", "destination_busy"
        order = delivery.new_order(place=PLACES[name])
        return f"好，{order['good']}送{name}，这就出发", "destination_order"

    if re.search(r"(送哪|送到哪|去哪儿|去哪里|目的地|送什么|送的什么|送的啥|这单是什么|这单是啥|什么单|什么餐|啥外卖|点了什么)", msg):
        return _summary(ds), "order_info"
    if re.search(r"(还要多久|剩多久|多久送到|快到了吗|到哪了|进度|现在在哪|走到哪)", msg):
        if not active:
            return "这会儿在等单，刚好能和你们聊两句", "location_idle"
        left = ds.get("left")
        if isinstance(left, (int, float)):
            return f"{_status(ds)}，倒计时还剩{max(0, round(left))}秒", "location_info"
        return _status(ds), "location_info"
    if re.search(r"(这单多少钱|一单多少钱|赚多少|赚了多少|收入|挣了多少|今天几单|送了几单)", msg):
        if "这单" in msg or "一单" in msg:
            return f"这单模拟运费{float(o.get('pay', 0)):.1f}元" if active else "还没接单呢，等等看", "fare"
        count = int(ds.get("delivered", 0))
        earn = float(ds.get("earned", 0.0))
        return f"今天模拟送了{count}单，模拟收入{earn:.1f}元", "earnings"
    if re.search(r"(催单|快点|加速|冲快点|闯红灯|超速)", msg):
        return "别催别催，安全送到才算本事", "safety"
    if re.search(r"(累不累|辛苦了|辛苦啦|加油|慢点骑|路上小心|注意安全)", msg):
        return "收到，慢慢骑稳稳送，谢啦", "care"
    if re.fullmatch(r"(?:666+|哈哈+|哈哈哈+|冲+|厉害+|支持+|好耶+|好可爱|太可爱了)", msg):
        return random.choice(("你们一夸，我电动车都飘了", "别夸了，下一单还等着我呢", "嘿嘿，被你看见我摸鱼了")), "reaction"
    return None


def handle_comment(nick: str, message: str, delivery: Any, now: float | None = None) -> dict[str, Any] | None:
    """Return None to let existing /comment logic handle a normal chat message.

    Return {reply, kind, suppressed?} if this module handles it. A suppressed
    result deliberately stops duplicate responses from falling into the old LLM.
    """
    global _LAST_GLOBAL, _LAST_CMD
    now = time.monotonic() if now is None else now
    msg = (message or "").strip()[:120]
    if not msg:
        return None

    # 合规：不讨论/教授 AI 虚拟形象开播方法
    if re.search(r"(怎么开的播|怎么开播|如何开播|怎么做的|怎么实现|用什么软件|什么模型|什么技术|虚拟人怎么|AI主播怎么|无人直播|自动直播|教程|教教|搭建方法|怎么搭)", msg):
        return {"reply": "这个不聊，换个话题吧", "kind": "refuse"}
    # 身份询问：直说
    if re.search(r"(你是真人|真人吗|是不是真人|你是AI|是AI吗|机器人吗|虚拟人吗)", msg):
        return {"reply": "我是AI虚拟形象，不是真人，画面是模拟的", "kind": "identity"}
    # 噪音：纯符号、单字重复、超短
    if re.fullmatch(r"[^\w\u4e00-\u9fa5]+", msg):
        return {"reply": "", "kind": "noise", "suppressed": True}
    if len(msg) <= 12 and re.search(r"(.)\1{3,}", msg):
        return {"reply": "", "kind": "noise", "suppressed": True}
    # Candidate pre-filter: avoid even calling snapshot() for unrelated comments.
    if not (re.search(r"送|单|餐|目的地|去哪里|去哪|^去(?:学校|便利店|小区|医院|商场)|进度|到了|赚|收入|几单|多久|哪了|在哪|快点|催|超速|红灯|辛苦|累不|加油|安全|慢点|^哈|^6|^冲|厉害|支持|好耶|可爱", msg)):
        return None
    who = _clean_name(nick)
    norm = re.sub(r"\s+", "", msg)
    key = (who, norm)
    with _LOCK:
        ds = delivery.snapshot()  # only accessed on a recognized candidate
        # Intention identification must occur before cooldown; unrelated
        # messages must still pass through to the existing response system.
        picked = _pick_response(msg, ds, delivery if False else _NO_COMMANDS)
        if picked is None:
            return None
        if now - _RECENT.get(key, -1e12) < 8:
            return {"reply": "", "kind": "duplicate", "suppressed": True}
        is_command = picked[1] in ("new_order", "destination_order", "destination_busy")
        is_query = picked[1] in ("order_info", "earnings", "location_info", "location_idle", "fare")
        # 指令与查询都优先：只受 24 秒重复消息约束；闲聊才走限频
        if not (is_command or is_query) and (now - _LAST_USER.get(who, -1e12) < 7 or now - _LAST_GLOBAL < 1.8):
            return {"reply": "", "kind": "cooldown", "suppressed": True}
        # Run the command ONLY after cooldown checks. `_NO_COMMANDS` above
        # emits a marker and never mutates the live delivery state.
        if picked[1] in ("new_order", "destination_order", "destination_busy"):
            picked = _pick_response(msg, ds, delivery)
        _RECENT[key] = now
        _LAST_USER[who] = now
        _LAST_GLOBAL = now
        _RECENT.move_to_end(key)
        while len(_RECENT) > 300:
            _RECENT.popitem(last=False)
        if len(_LAST_USER) > 500:
            # No session data persists after process restart.
            stale = [u for u, t in _LAST_USER.items() if now - t > 120]
            for u in stale: _LAST_USER.pop(u, None)
        return {"reply": picked[0], "kind": picked[1], "suppressed": False}


class _NoCommands:
    def new_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"good": "外卖", "place_name": "目的地"}


_NO_COMMANDS = _NoCommands()


_SCENE_IDLE = [
    "这会儿没单，我先靠边停会儿", "你们想让我下一单去哪，弹幕说", "系统还没派单，我先发会儿呆",
    "等单的时候最舒服，就是有点晒", "今天单量一般，是不是都在上班", "我这车电量还行，能跑一下午",
    "刚送完一单，喘口气", "有人要点外卖吗，我顺路", "这会儿路上车不多，正好歇着",
    "我在等一个新订单，别催", "闲着也是闲着，谁想听我念叨", "这城市挺好看，就是坡多",
]

_SCENE_TO_SHOP = [
    "出发去商家取餐了，别挡我道", "这单得先去店里拿货，稍等", "骑车去店里的路上，风还挺大",
    "商家别拖我后腿啊，我赶时间", "取餐路上，顺便看两眼街景", "这店我熟，第三次来了",
    "导航说前面右转，我信它一次", "车流有点多，我慢点", "去店里的路上，红灯真多",
    "马上到店，希望餐已经做好了", "这单的店在商场后面，绕一下", "取餐去，别眨眼",
]

_SCENE_CARRYING = [
    "已经拿到餐了，正在往客户那边赶", "这单有点远，我加把劲", "路上颠，汤别洒了",
    "还有一段路，应该来得及", "客户地址有点绕，我在找楼号", "这单送完能歇两分钟",
    "风把我头发吹乱了，不管了", "前面在修路，我绕一下", "这单的客户备注写了别敲门，我记着",
    "骑车的时候最怕突然窜出个电动车", "快到了，先把餐袋扶正", "今天路况还行，没堵",
]

_SCENE_STORY = [
    "说起来，我昨天送过一单到海边那栋楼，客户是个钓鱼的老头，非要塞我一条鱼。我没要，虚拟形象吃不了。",
    "你们知道这城市几点最好看吗，傍晚，海面是橘色的，我正好在桥上过。",
    "我算过，跑一单平均四块多，够买半杯奶茶。所以我一般跑两单才敢想奶茶的事。",
    "有时候送到门口，听见里面有电视声，我就想，里面的人在过什么样的日子。",
    "我这车没有后视镜，拐弯全靠回头，所以你们看我老歪头不是卖萌。",
    "刚来这城市的时候我迷路过三次，现在闭着眼都知道哪条巷子能抄近道。",
    "送夜单最舒服，路上没人，风是凉的，就是有点孤单。",
    "有人问我累不累。我这个设定里没有累这个参数，但我可以演一下。",
]

_LAST_PICK = collections.deque(maxlen=10)


def _pick(pool, key):
    """不重复抽：10 条内不再出现同一条。"""
    global _SCENE_I
    for _ in range(20):
        t = pool[(_SCENE_I * 7 + random.randrange(len(pool))) % len(pool)]
        if t not in _LAST_PICK:
            _LAST_PICK.append(t)
            _SCENE_I += 1
            return t
    return pool[random.randrange(len(pool))]


def scene_line(ds: dict[str, Any], now: float | None = None) -> str:
    """配送场景的主动台词：按状态分组 + 不重复 + 偶尔讲一段。"""
    global _LAST_SCENE
    now = time.monotonic() if now is None else now
    with _LOCK:
        status = ds.get("status", "idle")
        o = ds.get("order") or {}
        # 每 6~8 句插一段稍长的，打破一句一句的节奏
        if random.random() < 0.08:
            return _pick(_SCENE_STORY, "story")
        good = o.get("good", "外卖"); dest = o.get("place_name", "客户")
        if status == "accepted":
            pool = _SCENE_TO_SHOP + [
                f"这单是{good}，送{dest}，我先去店里拿",
                f"接到一单{good}，目的地{dest}",
                f"先去取{good}，回头送{dest}",
            ]
            return _pick(pool, "shop")
        if status == "carrying":
            pool = _SCENE_CARRYING + [
                f"{good}拿到了，往{dest}走",
                f"这单送{dest}，路有点远",
                f"手里拎着{good}，去{dest}那栋",
            ]
            return _pick(pool, "carry")
        return _pick(_SCENE_IDLE, "idle")


def queue_destination(place: str) -> None:
    global _PENDING_DESTINATION
    if place not in PLACES.values():
        raise ValueError("invalid destination")
    with _LOCK:
        _PENDING_DESTINATION = place


def consume_destination() -> str | None:
    global _PENDING_DESTINATION
    with _LOCK:
        place = _PENDING_DESTINATION
        _PENDING_DESTINATION = None
        return place


def peek_destination() -> str | None:
    with _LOCK:
        return _PENDING_DESTINATION


def reset_for_test() -> None:
    global _LAST_GLOBAL, _LAST_SCENE, _SCENE_I, _PENDING_DESTINATION
    with _LOCK:
        _RECENT.clear(); _LAST_USER.clear()
        _LAST_GLOBAL = _LAST_SCENE = -1e12
        _SCENE_I = 0
        _PENDING_DESTINATION = None

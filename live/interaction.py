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
        if now - _RECENT.get(key, -1e12) < 24:
            return {"reply": "", "kind": "duplicate", "suppressed": True}
        is_command = picked[1] in ("new_order", "destination_order", "destination_busy")
        # 游戏指令优先级高于聊天限频：只受 24 秒重复消息约束
        if not is_command and (now - _LAST_USER.get(who, -1e12) < 7 or now - _LAST_GLOBAL < 1.8):
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


def scene_line(ds: dict[str, Any], now: float | None = None) -> str:
    """Contextual ambient lines for the delivery scene, not old office scripts."""
    global _LAST_SCENE, _SCENE_I
    now = time.monotonic() if now is None else now
    with _LOCK:
        if now - _LAST_SCENE < 15:
            # The original director calls next_line after every spoken line.
            # We need a line even during the gap, so cycle casual delivery banter.
            text = ["路口车还挺多，我先看看方向", "谁有想吃的，弹幕告诉我", "我这小电驴，又得继续跑单了", "你们觉得今晚能送到第几单"][ _SCENE_I % 4]
        else:
            o = ds.get("order") or {}
            if o:
                text = f"这单{o.get('good', '外卖')}要送去{o.get('place_name', '客户那里')}，你们给我指指路"
            else:
                text = "暂时没单，弹幕选一个地方我去跑"
        _LAST_SCENE = now
        _SCENE_I += 1
        return text


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

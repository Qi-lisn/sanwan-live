"""三万外卖小游戏状态机。

与现有 DSH 直播服务 API 保持兼容：
  idle -> accepted（去商家） -> carrying（送往客户） -> idle
状态由 server.py /delivery 输出供 stage_map.html 读取；舞台不维护第二套模拟收入。
"""
from __future__ import annotations

import os
import random
import time

PLACES = [
    dict(id='office', name='公司', x=470, y=640, kind='start'),
    dict(id='shop', name='便利店', x=760, y=480),
    dict(id='community', name='小区', x=1180, y=700),
    dict(id='school', name='学校', x=1340, y=330),
    dict(id='hospital', name='医院', x=980, y=250),
    dict(id='mall', name='商场', x=1520, y=560),
]
GOODS = ['奶茶', '炒饭', '麻辣烫', '炸鸡', '两杯咖啡', '一份饺子', '烧烤', '蛋糕']
_SEQ = {'n': 0}


def _initial():
    return dict(status='idle', order=None, progress=0.0, started=0.0, deadline=0.0,
                earned=0.0, delivered=0, late=0, total=0, last_result='',
                wage=1.0, rating='正常', next_order_at=0.0)


_state = _initial()


def _schedule(order):
    """游戏内部时间轴，均相对 accepted_at，保持距离和礼物加急的效果。"""
    limit = float(order['limit'])
    pickup_at = min(12.0, max(4.0, limit * 0.22))
    delivered_at = max(pickup_at + 3.0, min(limit - 2.0, limit * 0.78))
    return pickup_at, delivered_at


def new_order(now=None, rng=None, place=None):
    if not place:
        # A viewer may have chosen the NEXT destination while we were delivering.
        try:
            import interaction
            place = interaction.consume_destination()
        except ImportError:
            pass
    now = time.time() if now is None else now
    rng = rng or random
    pool = [p for p in PLACES if p['id'] != 'office']
    matches = [p for p in pool if p['id'] == place or p['name'] == place] if place else []
    dest = matches[0] if matches else rng.choice(pool)
    good = rng.choice(GOODS)
    dist = abs(dest['x'] - 470) / 1000 + abs(dest['y'] - 640) / 700
    pay = round(3.5 + dist * 3.0 + rng.random() * 1.5, 1)
    if place:
        pay = round(pay * 1.4, 1)
    limit = 45 + int(dist * 40)
    _SEQ['n'] += 1
    order = dict(seq=_SEQ['n'], good=good, place=dest['id'], place_name=dest['name'],
                 x=dest['x'], y=dest['y'], pay=pay, limit=limit, accepted_at=now)
    _state.update(status='accepted', order=order, progress=0.0,
                  started=now, deadline=now + limit, last_result='', next_order_at=0.0)
    _state['total'] += 1
    return order


def rush(seconds=15, now=None):
    """礼物加急：缩短剩余截止时间，不重置订单。"""
    if _state['status'] not in ('accepted', 'carrying') or not _state['order']:
        return 0
    o = _state['order']
    o['limit'] = max(10, int(o['limit']) - int(seconds))
    _state['deadline'] = o['accepted_at'] + o['limit']
    _state['last_result'] = f'加急 少 {seconds} 秒'
    return seconds


def pickup(now=None):
    now = time.time() if now is None else now
    if _state['status'] != 'accepted':
        return False
    _state['status'] = 'carrying'
    _state['started'] = now
    _state['order']['carry_at'] = now
    return True


def deliver(now=None):
    now = time.time() if now is None else now
    if _state['status'] != 'carrying':
        return False
    o = _state['order']
    late = now > o['accepted_at'] + o['limit']
    if late:
        _state['late'] += 1
        _state['earned'] = round(_state['earned'] - 2.0, 1)
        _state['last_result'] = '超时了 扣两块'
        if _state['late'] >= 3:
            _state['wage'] = 0.8
            _state['rating'] = '差评 工资八折'
    else:
        _state['delivered'] += 1
        _state['earned'] = round(_state['earned'] + o['pay'], 1)
        _state['last_result'] = f"送到 {o['place_name']} 赚 {o['pay']} 块"
    _state.update(status='idle', order=None, progress=1.0, next_order_at=now + 4.0)
    return True


def tick(now=None):
    now = time.time() if now is None else now
    if _state['status'] == 'idle':
        # 晚间 20:00 后 dayparts.map=False。开播时可显式设置此环境变量
        # 保持自动配送循环，而不影响未开启的原电台、点歌系统。
        if os.environ.get('SANWAN_DELIVERY_AUTO') == '1' and now >= _state.get('next_order_at', 0):
            new_order(now=now)
        return
    o = _state.get('order')
    if not o:
        return
    elapsed = max(0.0, now - o['accepted_at'])
    pickup_at, delivered_at = _schedule(o)

    # 先处理已过期的单，避免礼物加急后“反而准时”的逻辑漏洞。
    if elapsed > o['limit']:
        if _state['status'] == 'accepted':
            pickup(now)
        if _state['status'] == 'carrying':
            deliver(now)
        return

    if _state['status'] == 'accepted' and elapsed >= pickup_at:
        pickup(now)
    if _state['status'] == 'carrying' and elapsed >= delivered_at:
        deliver(now)
        return
    if _state['status'] == 'accepted':
        _state['progress'] = round(min(1, elapsed / pickup_at) * .28, 3)
    else:
        progress = max(0, min(1, (elapsed - pickup_at) / max(1, delivered_at - pickup_at)))
        _state['progress'] = round(.28 + .72 * progress, 3)


def snapshot(now=None):
    now = time.time() if now is None else now
    tick(now)
    o = _state['order']
    result = dict(status=_state['status'], progress=round(_state['progress'], 3),
                  earned=_state['earned'], delivered=_state['delivered'],
                  late=_state['late'], total=_state['total'], places=PLACES,
                  wage=_state['wage'], rating=_state['rating'],
                  last_result=_state['last_result'])
    if o:
        pick, done = _schedule(o)
        elapsed = max(0, now - o['accepted_at'])
        if _state['status'] == 'accepted':
            phase_progress = min(1, elapsed / max(1, pick))
        else:
            phase_progress = min(1, max(0, (elapsed - pick) / max(1, done - pick)))
        result['phase_progress'] = round(phase_progress, 3)
        result['order'] = {k: o[k] for k in
                           ('seq', 'good', 'place_name', 'x', 'y', 'pay', 'limit')}
        result['left'] = max(0, round(o['accepted_at'] + o['limit'] - now))
    return result


def reset():
    global _state
    _state = _initial()


def qa_force_late(n=3):
    _state['late'] = n
    _state['wage'] = .8
    _state['rating'] = '差评 工资八折'
    _state['last_result'] = '超时三次 差评'

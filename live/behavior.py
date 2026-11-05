"""Sanwan live action controller. No external dependencies; loopback HTTP exposed by server.py."""
import collections
import threading
import time

ALLOWED = {
    'wave': {'duration': 2.5, 'kind': 'gesture'},
    'happy': {'duration': 2.0, 'kind': 'expression'},
    'shy': {'duration': 2.0, 'kind': 'expression'},
    'nod': {'duration': 1.4, 'kind': 'gesture'},
    'laugh': {'duration': 1.8, 'kind': 'expression'},
    'dance_cute': {'duration': 8.0, 'kind': 'performance'},
    'idle': {'duration': 0.0, 'kind': 'system'},
}
PRIORITY = {'idle': 0, 'nod': 1, 'laugh': 1, 'wave': 2, 'happy': 2, 'shy': 2, 'dance_cute': 3}

_lock = threading.RLock()
_sequence = 0
_history = collections.deque(maxlen=40)
_state = {
    'enabled': True, 'auto_actions': False, 'paused': False,
    'activity': 'idle', 'motion': 'idle', 'motion_until': 0,
    'last_action': None, 'last_source': None,
}
_last_auto = {}


def _expire():
    if _state['motion_until'] and time.monotonic() > _state['motion_until']:
        _state['motion'] = 'idle'
        _state['motion_until'] = 0


def snapshot():
    with _lock:
        _expire()
        return {**_state, 'seq': _sequence, 'recent': list(_history)[-12:]}


def set_activity(activity):
    if activity not in ('idle', 'speaking', 'singing'):
        raise ValueError('invalid activity')
    with _lock:
        _state['activity'] = activity


def set_duration(name, seconds):
    """让动作时长与真实素材对齐（例如舞蹈视频实际时长）。"""
    with _lock:
        if name in ALLOWED and seconds and seconds > 0:
            ALLOWED[name]['duration'] = round(float(seconds), 2)
            return True
        return False


def auto_allowed():
    """自动触发渠道（弹幕/礼物/AI）的总开关。"""
    with _lock:
        return bool(_state['enabled'] and _state['auto_actions'] and not _state['paused'])


def configure(data):
    with _lock:
        for key in ('auto_actions', 'paused', 'enabled'):
            if key in data:
                if not isinstance(data[key], bool):
                    raise ValueError(f'{key} must be boolean')
                _state[key] = data[key]
        if _state['paused']:
            _send('idle', 'operator', bypass=True)
        return snapshot()


def _send(name, source, bypass=False):
    global _sequence
    if name not in ALLOWED:
        raise ValueError('unknown action')
    if not bypass and (not _state['enabled'] or _state['paused']):
        return {'ok': False, 'reason': 'controller disabled or paused'}
    _expire()
    if name == 'dance_cute' and _state['activity'] == 'singing' and source != 'operator':
        return {'ok': False, 'reason': 'singing'}
    current = _state['motion']
    # 人工操作总是可以接管（包括打断舞蹈）；自动触发才受优先级约束
    if not bypass and source != 'operator' and current != 'idle' and _state['motion_until'] > time.monotonic():
        if PRIORITY.get(name, 0) <= PRIORITY.get(current, 0):
            return {'ok': False, 'reason': 'lower priority', 'current': current}
    if name == 'dance_cute' and _state['motion'] == 'dance_cute' and not bypass:
        return {'ok': False, 'reason': 'already dancing'}
    _sequence += 1
    item = {'seq': _sequence, 'name': name, 'source': source, 'at': time.time(),
            'duration': ALLOWED[name]['duration']}
    _history.append(item)
    _state['motion'] = name
    _state['motion_until'] = time.monotonic() + item['duration'] if item['duration'] else 0
    _state['last_action'] = name
    _state['last_source'] = source
    return {'ok': True, 'event': item}


def dispatch(name, source='operator'):
    with _lock:
        return _send(name, source, bypass=(name == 'idle'))


def from_comment(text, nick='viewer'):
    """保守的本地规则：可同时命中多个动作时，跳过冷却中的那个。"""
    with _lock:
        if not auto_allowed():
            return None
        cands = []
        if any(x in text for x in ('跳个舞', '跳舞', '舞蹈')):
            cands.append(('dance_cute', 35))
        if any(x in text for x in ('可爱', '好看', '喜欢你', '漂亮')):
            cands.append(('shy', 15))
        if any(x in text for x in ('你好', '打招呼', '挥手', '嗨')):
            cands.append(('wave', 8))
        if any(x in text for x in ('笑一个', '笑死', '搞笑')):
            cands.append(('laugh', 12))
        now = time.monotonic()
        for action, cooldown in cands:
            if action == 'dance_cute' and _state['activity'] == 'singing':
                continue
            if now - _last_auto.get(action, -1e9) < cooldown:
                continue
            _last_auto[action] = now
            return _send(action, f'comment:{nick[:16]}')
        return None

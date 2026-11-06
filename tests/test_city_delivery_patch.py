"""在原仓库根目录运行 python -m pytest tests/test_city_delivery_patch.py。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'live'))
import delivery


def test_auto_cycle_succeeds_before_deadline():
    delivery.reset()
    order = delivery.new_order(now=1000, place='小区')
    assert delivery.snapshot(now=1001)['status'] == 'accepted'
    assert delivery.snapshot(now=1015)['status'] == 'carrying'
    done = delivery.snapshot(now=1000 + order['limit'] * .82)
    assert done['status'] == 'idle'
    assert done['delivered'] == 1 and done['earned'] == order['pay']


def test_phase_progress_and_rush():
    delivery.reset()
    delivery.new_order(now=1000, place='商场')
    a = delivery.snapshot(now=1001)
    assert 0 <= a['phase_progress'] <= 1
    before = a['left']
    delivery.rush(15)
    assert delivery.snapshot(now=1001)['left'] == before - 15


def test_overdue_late_still_penalized():
    delivery.reset()
    o = delivery.new_order(now=1000)
    late = delivery.snapshot(now=1000 + o['limit'] + 1)
    assert late['status'] == 'idle'
    assert late['late'] == 1 and late['earned'] == -2


def test_night_auto_dispatch_is_opt_in(monkeypatch):
    delivery.reset()
    monkeypatch.delenv('SANWAN_DELIVERY_AUTO', raising=False)
    assert delivery.snapshot(now=1000)['status'] == 'idle'
    monkeypatch.setenv('SANWAN_DELIVERY_AUTO', '1')
    d = delivery.snapshot(now=1000)
    assert d['status'] == 'accepted'
    first = d['order']['seq']
    assert delivery.snapshot(now=1001)['order']['seq'] == first

"""在原仓库根目录运行 python -m pytest tests/test_city_delivery_patch.py。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'live'))
import delivery


def test_auto_cycle_succeeds_before_deadline():
    delivery.reset()
    order = delivery.new_order(now=1000, place='小区')
    assert delivery.snapshot(now=1001)['status'] == 'accepted'
    delivery.tick(now=1015)
    assert delivery.snapshot(now=1015)['status'] == 'carrying'
    delivery.tick(now=1000 + order['limit'] * .82)
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
    delivery.rush(o['limit'] - 10)
    delivery.tick(now=1000 + o['limit'] + 1)
    late = delivery.snapshot(now=1000 + o['limit'] + 1)
    assert late['status'] == 'idle'
    assert late['late'] == 1 and late['earned'] == -2


def test_night_auto_dispatch_is_opt_in(monkeypatch):
    delivery.reset()
    monkeypatch.delenv('SANWAN_DELIVERY_AUTO', raising=False)
    assert delivery.snapshot(now=1000)['status'] == 'idle'
    monkeypatch.setenv('SANWAN_DELIVERY_AUTO', '1')
    delivery.tick(now=1000)
    d = delivery.snapshot(now=1000)
    assert d['status'] == 'accepted'
    first = d['order']['seq']
    assert delivery.snapshot(now=1001)['order']['seq'] == first


def test_sparse_tick_completes_on_schedule_and_preserves_queue():
    delivery.reset()
    first = delivery.new_order(now=1000, place='school')
    queued = delivery.new_order(now=1001, place='hospital')
    assert queued['queued'] and delivery.snapshot(now=1001)['order']['seq'] == first['seq']
    delivery.tick(now=2000)
    state = delivery.snapshot(now=2000)
    assert state['delivered'] == 1 and state['late'] == 0
    delivery.tick(now=2005)
    assert delivery.snapshot(now=2005)['order']['place_name'] == '医院'


def test_discount_applies_to_completed_order():
    delivery.reset()
    delivery.qa_force_late()
    order = delivery.new_order(now=1000)
    delivery.tick(now=1000 + order['limit'])
    assert delivery.snapshot(now=2000)['earned'] == round(order['pay'] * .8, 1)


def test_concurrent_orders_preserve_first():
    from concurrent.futures import ThreadPoolExecutor
    delivery.reset()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: delivery.new_order(now=1000), range(8)))
    assert sum(not order.get('queued') for order in results) == 1
    assert delivery.snapshot(now=1000)['total'] == 1


def test_idle_manual_dispatch_clears_old_pending():
    delivery.reset()
    first = delivery.new_order(now=1000, place='school')
    delivery.new_order(now=1001, place='hospital')
    delivery.tick(now=1000 + first['limit'])
    second = delivery.new_order(now=1200, place='mall')
    assert not second.get('queued')
    assert delivery.snapshot(now=1200)['pending'] is None
    delivery.tick(now=1400)
    delivery.tick(now=1500)
    assert delivery.snapshot(now=1500)['status'] == 'idle'


def test_snapshot_pending_cannot_mutate_state():
    delivery.reset()
    delivery.new_order(now=1000)
    delivery.new_order(now=1001, place='hospital')
    state = delivery.snapshot(now=1001)
    state['pending']['place'] = 'mall'
    assert delivery.snapshot(now=1001)['pending']['place'] == 'hospital'

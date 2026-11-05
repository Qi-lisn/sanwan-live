import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "live"))
import delivery


def setup_function(_):
    delivery.reset()


def test_order_lifecycle():
    o = delivery.new_order(now=1000)
    assert delivery.snapshot(now=1000)["status"] == "accepted"
    assert delivery.pickup(now=1010) is True
    assert delivery.snapshot(now=1010)["status"] == "carrying"
    assert delivery.deliver(now=1020) is True
    s = delivery.snapshot(now=1020)
    assert s["status"] == "idle" and s["delivered"] == 1
    assert s["earned"] == o["pay"]


def test_late_penalty():
    o = delivery.new_order(now=0)
    delivery.pickup(now=1)
    delivery.deliver(now=o["limit"] + 100)
    s = delivery.snapshot(now=o["limit"] + 100)
    assert s["late"] == 1 and s["earned"] == -2.0


def test_progress_monotonic():
    o = delivery.new_order(now=0)
    p1 = delivery.snapshot(now=5)["progress"]
    p2 = delivery.snapshot(now=15)["progress"]
    assert 0 <= p1 <= p2 <= 1


def test_places_have_coords():
    for p in delivery.PLACES:
        assert 0 < p["x"] < 1920 and 0 < p["y"] < 1080


def test_rush_reduces_time():
    delivery.new_order(now=1000)
    before = delivery.snapshot(now=1001)["left"]
    delivery.rush(15)
    after = delivery.snapshot(now=1001)["left"]
    assert after == before - 15


def test_specified_place():
    o = delivery.new_order(now=0, place="school")
    assert o["place_name"] == "学校"
    o2 = delivery.new_order(now=0, place="商场")
    assert o2["place_name"] == "商场"


def test_late_three_times_penalty():
    for i in range(3):
        o = delivery.new_order(now=0)
        delivery.pickup(now=1)
        delivery.deliver(now=o["limit"] + 50)
    s = delivery.snapshot(now=1000)
    assert s["late"] == 3 and s["wage"] == 0.8 and "差评" in s["rating"]

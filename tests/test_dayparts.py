import datetime as dt, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "live"))
import dayparts


def t(h, m=0):
    return dt.datetime(2026, 11, 5, h, m)


def test_boundaries():
    assert dayparts.block_at(t(5, 59))["id"] == "sleep"
    assert dayparts.block_at(t(6, 0))["id"] == "morning"
    assert dayparts.block_at(t(9, 59))["id"] == "morning"
    assert dayparts.block_at(t(10, 0))["id"] == "forenoon"
    assert dayparts.block_at(t(12, 0))["id"] == "lunch"
    assert dayparts.block_at(t(14, 0))["id"] == "afternoon"
    assert dayparts.block_at(t(17, 0))["id"] == "dinner"
    assert dayparts.block_at(t(20, 0))["id"] == "prime"
    assert dayparts.block_at(t(23, 0))["id"] == "story"


def test_midnight_wrap():
    assert dayparts.block_at(t(23, 59))["id"] == "story"
    assert dayparts.block_at(t(0, 30))["id"] == "story"
    assert dayparts.block_at(t(1, 59))["id"] == "story"
    assert dayparts.block_at(t(2, 0))["id"] == "sleep"


def test_seconds_left():
    assert dayparts.seconds_left(t(6, 0)) == 4 * 3600
    assert dayparts.seconds_left(t(0, 30)) == 90 * 60
    assert dayparts.seconds_left(t(23, 59)) == 121 * 60


def test_packs_exist():
    for b in dayparts.BLOCKS:
        lines = dayparts.pack_lines(b["id"])
        assert len(lines) >= 8, b["id"]
        assert all(len(l) <= 40 for l in lines), b["id"]


def test_snapshot_fields():
    snap = dayparts.snapshot(t(21, 0))
    assert snap["id"] == "prime" and snap["light"] == "warm"
    assert 0 < snap["seconds_left"] <= 3 * 3600
    assert snap["next"] == "故事场"

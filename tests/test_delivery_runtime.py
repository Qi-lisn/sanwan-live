"""隔离模型、音频硬件与真实直播的服务端回归。"""
import importlib.util
import json
import sys
import threading
import types
import urllib.request
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "live"))


@pytest.fixture
def server(monkeypatch, tmp_path):
    sd = types.SimpleNamespace(query_devices=lambda: [], play=lambda *a, **k: None,
                               stop=lambda: None)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    read = Path.read_text

    def read_test_config(path, *args, **kwargs):
        if path.name == "volc.env":
            return "VOLC_API_KEY=test"
        if path.name == "diary.json":
            raise FileNotFoundError
        return read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_test_config)
    spec = importlib.util.spec_from_file_location("sanwan_runtime_test", ROOT / "live/server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "brain_on", lambda: False)
    monkeypatch.setattr(mod, "STOP", tmp_path / "STOP")
    monkeypatch.setattr(mod, "INJECT", tmp_path / "inject")
    monkeypatch.setenv("SANWAN_DELIVERY_CHAT", "1")
    monkeypatch.delenv("SANWAN_DELIVERY_AUTO", raising=False)
    mod.delivery.reset()
    mod.interaction.reset_for_test()
    yield mod
    mod.delivery.reset()


def test_auto_dispatch_handles_queued_race(server, monkeypatch):
    monkeypatch.delenv("SANWAN_DELIVERY_CHAT")
    server._last_report["t"] = server.time.time()
    monkeypatch.setattr(server.random, "random", lambda: 1)
    monkeypatch.setattr(server.dayparts, "block_at", lambda: {"map": True})
    monkeypatch.setattr(server.delivery, "new_order",
                        lambda: {"queued": True, "place_name": "随机地点"})
    assert "下一单" in server.next_line()["text"]


@pytest.mark.parametrize("comment,should_interrupt", [(None, True), ({"nick": "甲", "text": "送哪"}, False)])
def test_reply_finishes_but_monologue_yields(server, monkeypatch, comment, should_interrupt):
    class Finished(BaseException):
        pass

    count = 0
    def next_line():
        nonlocal count
        count += 1
        if count > 1:
            raise Finished()
        return {"text": "去学校", "comment": comment}

    clock = [100.0]
    monkeypatch.setattr(server, "time", types.SimpleNamespace(
        time=lambda: clock[0], sleep=lambda duration: clock.__setitem__(0, clock[0] + duration)))
    monkeypatch.setattr(server, "next_line", next_line)
    monkeypatch.setattr(server, "synth", lambda text: None)
    monkeypatch.setattr(server, "pcm", lambda _: np.zeros(48000, dtype=np.int16))
    stopped = []
    monkeypatch.setattr(server.sd, "stop", lambda: stopped.append(True))
    server._priority.append({"text": "后一个回答", "comment": {"nick": "乙", "text": "收入"}})
    with pytest.raises(Finished):
        server.director()
    assert bool(stopped) == should_interrupt
    assert server._state["text"] == "" and server._state["comment"] is None


def test_http_orders_gifts_comments_and_caption(server):
    http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    worker = threading.Thread(target=http.serve_forever, daemon=True)
    worker.start()

    def api(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{http.server_port}{path}", data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as response:
            return json.load(response)

    try:
        first = api("/delivery/new", {"place": "school"})["order"]
        queued = api("/delivery/new", {"place": "hospital"})
        assert queued["queued"]
        assert api("/delivery")["order"]["seq"] == first["seq"]
        api("/tip", {"nick": "测试", "gift": "模拟", "count": 1, "value": 10})
        state = api("/delivery")
        assert state["order"]["seq"] == first["seq"] and state["pending"]["place"] == "mall"
        reply = api("/comment", {"nick": "甲", "text": "下一单去医院"})
        assert reply["replied"] and api("/delivery")["pending"]["place"] == "hospital"
        server._state.update(text="这单送学校", seq=1, comment={"nick": "甲", "text": "送哪"})
        assert api("/caption")["comment"]["text"] == "送哪"
        api("/delivery/reset", {})
        assert api("/delivery")["pending"] is None
    finally:
        http.shutdown()
        http.server_close()
        worker.join(timeout=3)

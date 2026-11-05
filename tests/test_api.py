"""端到端回归：动作接口、礼物统计、自动开关、暂停、优先级、重复弹幕。"""
import json, os, pathlib, subprocess, sys, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("SANWAN_TEST_PORT", "8821"))


def api(path, body=None, timeout=20):
    url = f"http://127.0.0.1:{PORT}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode() or "{}"
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, SANWAN_PORT=str(PORT))
        cls.proc = subprocess.Popen([sys.executable, "live/server.py"], cwd=str(ROOT), env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(120):
            try:
                code, _d = api("/action_state", timeout=2)
                if code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.25)
        cls.proc.terminate()
        raise RuntimeError("server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=8)
        except Exception:
            cls.proc.kill()

    def _state(self):
        return api("/action_state")[1]

    def test_00_director_produces_lines(self):
        """导演线程要能正常出词：出词停滞通常意味着 next_line 抛异常。"""
        time.sleep(4)
        lines0 = api("/stats")[1]["lines"]
        self.assertGreaterEqual(lines0, 0)
        time.sleep(6)
        lines1 = api("/stats")[1]["lines"]
        self.assertGreater(lines1, lines0, "导演没有继续出词（可能 next_line 异常）")

    def test_01_manual_action(self):
        code, d = api("/action", {"name": "nod"})
        self.assertEqual(code, 200)
        self.assertTrue(d["ok"])
        self.assertEqual(self._state()["motion"], "nod")

    def test_02_tip_updates_stats(self):
        before = api("/sing_state")[1]
        code, d = api("/tip", {"nick": "测试大哥", "gift": "小心心", "count": 2, "value": 20})
        self.assertEqual(code, 200)
        after = api("/sing_state")[1]
        self.assertEqual(after["tips"], before["tips"] + 2)
        self.assertEqual(after["coins"], before["coins"] + 20)
        self.assertEqual(after["tip_seq"], before["tip_seq"] + 1)
        self.assertEqual(after["last_tip"]["nick"], "测试大哥")

    def test_03_auto_off_blocks_action_and_gift(self):
        api("/control", {"auto_actions": False, "paused": False})
        seq0 = self._state()["seq"]
        api("/comment", {"nick": "路人A", "text": "跳个舞"})
        api("/tip", {"nick": "大哥", "gift": "小心心", "count": 1, "value": 1})
        time.sleep(0.6)
        self.assertEqual(self._state()["seq"], seq0, "关闭自动后不应产生动作")

    def test_04_auto_on_triggers_action(self):
        api("/control", {"auto_actions": True})
        api("/action", {"name": "idle"})
        api("/comment", {"nick": "路人B", "text": "好可爱啊"})
        time.sleep(0.8)
        st = self._state()
        self.assertEqual(st["motion"], "shy")
        self.assertIn("comment", st["last_source"])

    def test_05_pause_blocks_then_recovers(self):
        api("/control", {"paused": True})
        code, d = api("/action", {"name": "wave"})
        self.assertEqual(code, 409)
        self.assertFalse(d["ok"])
        api("/control", {"paused": False})
        code, d = api("/action", {"name": "nod"})
        self.assertEqual(code, 200)
        self.assertTrue(d["ok"])

    def test_06_auto_action_cannot_override_dance(self):
        api("/control", {"paused": False, "auto_actions": True})
        api("/action", {"name": "idle"})
        api("/comment", {"nick": "点舞哥", "text": "跳个舞"})
        time.sleep(0.6)
        self.assertEqual(self._state()["motion"], "dance_cute")
        api("/comment", {"nick": "挥手哥", "text": "挥手"})
        time.sleep(0.6)
        self.assertEqual(self._state()["motion"], "dance_cute", "自动动作不应打断舞蹈")
        api("/action", {"name": "idle"})

    def test_08_operator_can_interrupt_dance(self):
        api("/control", {"paused": False, "auto_actions": True})
        api("/action", {"name": "dance_cute"})
        code, d = api("/action", {"name": "wave"})
        self.assertEqual(code, 200)
        self.assertTrue(d["ok"])
        self.assertEqual(self._state()["motion"], "wave")
        api("/action", {"name": "idle"})

    def test_07_duplicate_comment_fires_once(self):
        time.sleep(8.2)  # 等挥手冷却过去，避免上一项测试影响
        api("/control", {"auto_actions": True, "paused": False})
        api("/action", {"name": "idle"})
        seq0 = self._state()["seq"]
        api("/comment", {"nick": "重复哥", "text": "挥手"})
        api("/comment", {"nick": "重复哥", "text": "挥手"})
        time.sleep(0.8)
        self.assertEqual(self._state()["seq"], seq0 + 1, "同一条弹幕只应触发一次")

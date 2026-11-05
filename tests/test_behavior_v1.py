"""动作控制器单元测试：自动开关、唱歌互斥、优先级。"""
import importlib.util, pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("behavior_v1", ROOT / "live/behavior.py")
behavior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(behavior)


class BehaviorUnit(unittest.TestCase):
    def setUp(self):
        behavior.configure({"enabled": True, "auto_actions": True, "paused": False})
        behavior.set_activity("idle")
        behavior.dispatch("idle")
        behavior._last_auto.clear()

    def test_auto_allowed_follows_switch(self):
        self.assertTrue(behavior.auto_allowed())
        behavior.configure({"auto_actions": False})
        self.assertFalse(behavior.auto_allowed())

    def test_comment_action_blocked_when_auto_off(self):
        behavior.configure({"auto_actions": False})
        self.assertIsNone(behavior.from_comment("跳个舞", "t"))

    def test_dance_blocked_while_singing(self):
        behavior.set_activity("singing")
        r = behavior.dispatch("dance_cute", "comment:t")
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "singing")
        r2 = behavior.dispatch("dance_cute", "operator")
        self.assertTrue(r2["ok"])

    def test_lower_priority_cannot_override(self):
        behavior.dispatch("dance_cute", "operator")
        r = behavior.dispatch("wave", "operator")
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "lower priority")

    def test_pause_blocks_everything_except_idle(self):
        behavior.configure({"paused": True})
        self.assertFalse(behavior.dispatch("wave")["ok"])
        self.assertTrue(behavior.dispatch("idle")["ok"])
        self.assertFalse(behavior.auto_allowed())


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'live'))
import behavior

class BehaviorTests(unittest.TestCase):
    def test_invalid_action(self):
        with self.assertRaises(ValueError):
            behavior.dispatch('run_arbitrary_shell')
    def test_manual_action_and_stop(self):
        self.assertTrue(behavior.dispatch('wave')['ok'])
        self.assertEqual(behavior.snapshot()['motion'], 'wave')
        behavior.dispatch('idle')
        self.assertEqual(behavior.snapshot()['motion'], 'idle')
    def test_auto_defaults_off(self):
        behavior.configure({'auto_actions': False, 'paused': False})
        self.assertIsNone(behavior.from_comment('跳舞'))
    def test_auto_action(self):
        behavior.configure({'auto_actions': True})
        outcome = behavior.from_comment('跳个舞', 'tester')
        self.assertTrue(outcome['ok'])
        self.assertEqual(behavior.snapshot()['motion'], 'dance_cute')
        behavior.configure({'paused': True})
        self.assertEqual(behavior.snapshot()['motion'], 'idle')
        self.assertFalse(behavior.dispatch('dance_cute')['ok'])
        behavior.configure({'paused': False, 'auto_actions': False})
    def test_bad_flag(self):
        with self.assertRaises(ValueError):
            behavior.configure({'auto_actions': 'yes'})

if __name__ == '__main__':
    unittest.main()

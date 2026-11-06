import importlib
import json
import pathlib
import sys
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'live'))


def test_delivery_brain_uses_order_and_followup_context(monkeypatch):
    fake = types.ModuleType('brain')
    fake.API = 'https://api.example.invalid/chat'
    fake._env = lambda: {'DEEPSEEK_API_KEY': 'test-only', 'DEEPSEEK_MODEL':'test-chat'}
    monkeypatch.setitem(sys.modules, 'brain', fake)
    if 'brain_delivery' in sys.modules:
        del sys.modules['brain_delivery']
    mod = importlib.import_module('brain_delivery')
    calls = []

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *exc): pass
        def read(self):
            return json.dumps({'choices':[{'message':{'content':'好嘞，我骑着小电驴慢慢来'}}]}).encode()

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data))
        assert timeout == 4.0
        return FakeResponse()

    monkeypatch.setattr(mod.urllib.request, 'urlopen', fake_urlopen)
    snapshot={'status':'carrying','delivered':3,'earned':19.8,
              'order':{'good':'奶茶','place_name':'学校'},'left':22}
    first = mod.reply('路人甲', '今天怎么样', snapshot)
    second = mod.reply('路人甲', '那你累不累', snapshot)
    assert first and second
    assert '学校' in calls[0]['messages'][0]['content']
    assert '虚拟动漫女生' in calls[0]['messages'][0]['content']
    assert '今天怎么样' in str(calls[1]['messages'])
    assert calls[0]['max_tokens'] <= 90

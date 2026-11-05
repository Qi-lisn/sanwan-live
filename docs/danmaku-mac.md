# Mac 上跑抖音弹幕直连

上游 `DouyinLiveWebFetcher` 依赖 `py-mini-racer` 执行签名脚本，这个包在 Apple Silicon 上一调就崩。
本仓库改用 **PyExecJS + 本机 Node** 执行同一份 `sign.js`。

把上游 `liveMan.py` 里这一行：

```python
from py_mini_racer import MiniRacer
```

替换成：

```python
import execjs as _execjs


class MiniRacer:
    """在 Apple Silicon 上用 Node(execjs) 替代 py-mini-racer"""
    def __init__(self):
        self._ctx = None

    def eval(self, script):
        self._ctx = _execjs.compile(script)

    def call(self, name, *args):
        return self._ctx.call(name, *args)
```

另外两点：

- 脚本里 `sign.js` / `a_bogus.js` 是按**当前工作目录**找的，启动前 `os.chdir` 到 `live/vendor/douyin_fetcher`
- 网页版直播间对无登录环境返回空壳，`room_id` 解析会失败；直接从直播伴侣日志里取：
  `~/Library/Logs/Douyin Webcast Mate/*.log` 里的 `room_id=`

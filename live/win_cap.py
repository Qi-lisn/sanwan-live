import sys, subprocess, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "vendor"))
import Quartz

wins = Quartz.CGWindowListCopyWindowInfo(
    Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements, Quartz.kCGNullWindowID)
for w in wins:
    owner = w.get("kCGWindowOwnerName", "")
    if "Douyin Webcast Mate" in owner or "直播伴侣" in owner:
        b = w.get("kCGWindowBounds", {})
        print(w.get("kCGWindowNumber"), owner, int(b.get("Width",0)), int(b.get("Height",0)), int(b.get("X",0)), int(b.get("Y",0)), w.get("kCGWindowName",""))

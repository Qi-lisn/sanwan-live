import sys, subprocess, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "vendor"))
import Quartz, Vision
from PIL import Image

SHOT = "out/win.png"
im = Image.open(SHOT); W, H = im.size
box = (int(W*0.785), int(H*0.44), int(W*0.985), int(H*0.77))
im.crop(box).save("out/ocr_crop.png")

url = Quartz.CFURLCreateWithFileSystemPath(None, str(pathlib.Path("out/ocr_crop.png").resolve()), Quartz.kCFURLPOSIXPathStyle, False)
src = Quartz.CGImageSourceCreateWithURL(url, None)
img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
req = Vision.VNRecognizeTextRequest.alloc().init()
req.setRecognitionLevel_(1)
req.setRecognitionLanguages_(["zh-Hans", "en-US"])
req.setUsesLanguageCorrection_(True)
Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None).performRequests_error_([req], None)
for obs in (req.results() or []):
    print(repr(obs.topCandidates_(1)[0].string()))

"""Grid of demo images for review: python review.py out.png file..."""
import sys
from PIL import Image
out, fs = sys.argv[1], sys.argv[2:]
ims = [Image.open(f) for f in fs]; w, h = ims[0].size
s = Image.new("RGB", (w * 2 + 8, (h + 8) * ((len(ims) + 1) // 2)), (30, 30, 30))
for i, im in enumerate(ims): s.paste(im, ((i % 2) * (w + 8), (i // 2) * (h + 8)))
s.save(out)

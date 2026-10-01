"""Build an enlarged, pixel-sharp preview sheet from PNG files.

python preview.py out.png scale file1.png [file2.png ...]
Images are laid out in a row on a checkerboard so transparency is visible.
"""
import sys
from PIL import Image

out, scale, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
imgs = [Image.open(f).convert("RGBA") for f in files]
pad = 4
w = sum(i.width for i in imgs) * scale + pad * (len(imgs) + 1)
h = max(i.height for i in imgs) * scale + pad * 2
sheet = Image.new("RGBA", (w, h), (40, 40, 48, 255))
check = Image.new("RGBA", (w, h))
for y in range(0, h, 8):
    for x in range(0, w, 8):
        c = (58, 58, 68, 255) if (x // 8 + y // 8) % 2 else (48, 48, 56, 255)
        check.paste(c, (x, y, x + 8, y + 8))
sheet = check
x = pad
for im in imgs:
    big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    sheet.alpha_composite(big, (x, pad))
    x += big.width + pad
sheet.convert("RGB").save(out)
print("preview", out, sheet.size)

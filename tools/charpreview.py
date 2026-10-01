"""Labelled x3 contact sheet of game sheets on a checkerboard.

python charpreview.py <out.png> <scale> <sheet name or prefix> ...
python charpreview.py all            -> generated/preview_characters_all.png (all non-mage, non-terrain sheets from the manifest that this task made)
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ART = Path(__file__).resolve().parent.parent
SHEETS = ART / "sheets"
PREFIXES = ("enemy_", "npc_", "items")


def checker(w, h, s=8):
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            c = (70, 70, 82, 255) if (x // s + y // s) % 2 else (56, 56, 66, 255)
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=c)
    return im


def build(out, scale, names):
    m = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
    blocks = []
    for n in names:
        e = m[n]
        im = Image.open(SHEETS / e["file"]).convert("RGBA")
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        cw, ch = e["cell"][0] * scale, e["cell"][1] * scale
        rows = sorted(e["anims"].items(), key=lambda kv: kv[1]["row"])
        lw = 110
        b = Image.new("RGBA", (big.width + lw + 8, big.height + 18), (32, 32, 40, 255))
        dr = ImageDraw.Draw(b)
        dr.text((4, 2), f"{n}  cell {e['cell'][0]}x{e['cell'][1]}", fill=(255, 255, 160, 255))
        b.alpha_composite(checker(big.width, big.height), (lw, 16))
        b.alpha_composite(big, (lw, 16))
        for a, info in rows:
            dr.text((4, 16 + info["row"] * ch + ch // 2 - 5), f"{a} ({info['frames']})", fill=(220, 220, 220, 255))
        # cell grid
        for x in range(0, big.width + 1, cw):
            dr.line([(lw + x, 16), (lw + x, 16 + big.height)], fill=(90, 90, 110, 255))
        for y in range(0, big.height + 1, ch):
            dr.line([(lw, 16 + y), (lw + big.width, 16 + y)], fill=(90, 90, 110, 255))
        blocks.append(b)
    # pack blocks in columns up to a max height
    maxh = 2400
    cols, col, hcur = [], [], 0
    for b in blocks:
        if col and hcur + b.height > maxh:
            cols.append(col)
            col, hcur = [], 0
        col.append(b)
        hcur += b.height + 6
    cols.append(col)
    W = sum(max(b.width for b in c) + 10 for c in cols) + 10
    H = max(sum(b.height + 6 for b in c) for c in cols) + 10
    sheet = Image.new("RGBA", (W, H), (24, 24, 30, 255))
    x = 10
    for c in cols:
        y = 10
        for b in c:
            sheet.alpha_composite(b, (x, y))
            y += b.height + 6
        x += max(b.width for b in c) + 10
    sheet.convert("RGB").save(out)
    print("preview", out, sheet.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["all"]:
        m = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
        build(ART / "generated" / "preview_characters_all.png", 3, [n for n in m if n.startswith(PREFIXES)])
    else:
        m = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
        names = [n for p in a[2:] for n in m if n == p or n.startswith(p)]
        build(a[0], int(a[1]), names)

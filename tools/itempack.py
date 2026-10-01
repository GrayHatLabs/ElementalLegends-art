"""Downscale the 32x32 item generations into 16x16 cells and pack the items sheet.

python itempack.py
Each item is cropped to its bbox, box-filtered to fit 14x14 (items already <=14 px stay 1x),
snapped back to its own original palette, alpha-thresholded, and given a 1 px dark
outline so it stays crisp. One row per item (coin: 4-frame spin if coin_spin_*.png exist).
"""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from charpack import clean, update_manifest, SHEETS, GEN  # noqa: E402

D = GEN / "char_items"
ORDER = ["coin", "gem", "apple", "golden_apple", "bread", "meat", "mana_potion", "antidote", "heart",
         "heart_container", "key", "chest_closed", "chest_open", "gold_pile"]
CELL = 16
FIT = 15
OUTLINE = (20, 12, 16, 255)


def palette(im):
    return list({p[:3] for p in im.getdata() if p[3] > 128})


def nearest(c, pal):
    return min(pal, key=lambda q: (q[0] - c[0]) ** 2 * 3 + (q[1] - c[1]) ** 2 * 4 + (q[2] - c[2]) ** 2 * 2)


SIZES = {"heart": 9, "coin": 11, "gem": 11, "key": 13, "apple": 13, "golden_apple": 13, "mana_potion": 13, "antidote": 13}


def shrink(im, fit=FIT):
    im = clean(im)
    im = im.crop(im.getbbox())
    pal = palette(im)
    s = 1.0 if max(im.size) <= fit else min(fit / im.width, fit / im.height)
    if s < 1.0:
        w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
        # premultiplied box filter
        im = im.resize((w, h), Image.BOX)
        px = im.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                px[x, y] = (*nearest((r, g, b), pal), 255) if a >= 110 else (0, 0, 0, 0)
        # inner outline: bright edge pixels become dark so the silhouette stays crisp
        src = im.copy().load()
        for y in range(h):
            for x in range(w):
                p = src[x, y]
                if p[3] == 0 or sum(p[:3]) < 200:
                    continue
                edge = any(not (0 <= x + dx < w and 0 <= y + dy < h) or src[x + dx, y + dy][3] == 0
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if edge:
                    px[x, y] = OUTLINE
    # outline: transparent pixels that touch opaque ones become dark (only around the shape)
    w, h = im.size
    out = Image.new("RGBA", (w + 2, h + 2))
    out.alpha_composite(im, (1, 1))
    src = out.copy().load()
    op = out.load()
    if False:
        for y in range(h + 2):
            for x in range(w + 2):
                if src[x, y][3] == 0 and any(
                        0 <= x + dx < w + 2 and 0 <= y + dy < h + 2 and src[x + dx, y + dy][3] > 0
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    op[x, y] = OUTLINE
    return out.crop(out.getbbox())


def cellify(im):
    c = Image.new("RGBA", (CELL, CELL))
    c.alpha_composite(im, ((CELL - im.width) // 2, max(0, CELL - 2 - im.height)))
    return c


def main():
    rows = []
    for k in ORDER:
        frames = [D / f"{k}.png"]
        if k == "coin":
            spin = [D / f"coin_spin_{i}.png" for i in (0, 2, 3, 2)]
            if all(p.exists() for p in spin):
                frames = spin
        rows.append((k, [cellify(shrink(Image.open(f).convert("RGBA"), SIZES.get(k, FIT))) for f in frames]))
    cols = max(len(r[1]) for r in rows)
    sheet = Image.new("RGBA", (CELL * cols, CELL * len(rows)))
    anims = {}
    for ri, (k, fr) in enumerate(rows):
        for fi, im in enumerate(fr):
            sheet.alpha_composite(im, (fi * CELL, ri * CELL))
        anims[k] = {"row": ri, "frames": len(fr), "fps": 8 if len(fr) > 1 else 1}
    sheet.save(SHEETS / "items.png")
    update_manifest({"items": {"file": "items.png", "cell": [CELL, CELL], "anims": anims}})
    print("items sheet", sheet.size)


if __name__ == "__main__":
    main()

"""Contact sheet for the chunky regeneration: python chunky_preview.py
-> generated/preview_chunky_all.png
Top: every regenerated character, old (sheets/_old_tall) vs new, all rows, x3.
Bottom: all new characters (idle_down) standing on 24 px grass tiles with a 24 px grid, x3.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ART = Path(__file__).resolve().parent.parent
SHEETS = ART / "sheets"
OLD = SHEETS / "_old_tall"
S = 3
PAIRS = ["mage_fire", "mage_ice", "enemy_skeleton_fire", "enemy_skeleton_neutral", "npc_merchant",
         "enemy_imp_fire", "enemy_imp_neutral", "enemy_zombie", "npc_dryad", "enemy_gravelord",
         "npc_innkeeper", "npc_scholar"]
STRIP = ["mage_fire", "mage_ice", "mage_storm", "mage_earth", "enemy_skeleton_neutral", "npc_merchant",
         "enemy_imp_fire", "enemy_zombie", "npc_dryad", "npc_innkeeper", "npc_scholar", "enemy_gravelord"]
BG = (32, 32, 40, 255)


def checker(w, h, s=8):
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            c = (70, 70, 82, 255) if (x // s + y // s) % 2 else (56, 56, 66, 255)
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=c)
    return im


def sheet_block(path, entry, label):
    im = Image.open(path).convert("RGBA")
    big = im.resize((im.width * S, im.height * S), Image.NEAREST)
    b = Image.new("RGBA", (max(big.width, 150), big.height + 14), BG)
    ImageDraw.Draw(b).text((2, 1), f"{label} {entry['cell'][0]}x{entry['cell'][1]}", fill=(255, 255, 160, 255))
    b.alpha_composite(checker(big.width, big.height), (0, 14))
    b.alpha_composite(big, (0, 14))
    return b


def main():
    new = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
    old = json.loads((OLD / "manifest_entries.json").read_text())
    blocks = []
    for n in PAIRS:
        parts = []
        if n in old:
            parts.append(sheet_block(OLD / old[n]["file"], old[n], f"OLD {n}"))
        parts.append(sheet_block(SHEETS / new[n]["file"], new[n], f"NEW {n}"))
        w = sum(p.width for p in parts) + 8 * len(parts)
        h = max(p.height for p in parts)
        blk = Image.new("RGBA", (w, h), BG)
        x = 0
        for p in parts:
            blk.alpha_composite(p, (x, 0))
            x += p.width + 8
        blocks.append(blk)
    # grid of blocks, 3 per row
    per = 3
    rows = [blocks[i:i + per] for i in range(0, len(blocks), per)]
    top_w = max(sum(b.width + 16 for b in r) for r in rows)
    top_h = sum(max(b.height for b in r) + 16 for r in rows)
    # strip
    T = 24
    grass = Image.open(SHEETS / "terrain" / "theme0_wall.png").convert("RGBA").crop((0, 0, T, T))
    tiles_w = len(STRIP) * 2 + 1
    tiles_h = 3
    strip = Image.new("RGBA", (tiles_w * T, tiles_h * T))
    for ty in range(tiles_h):
        for tx in range(tiles_w):
            strip.alpha_composite(grass, (tx * T, ty * T))
    for i, n in enumerate(STRIP):
        e = new[n]
        cw, ch = e["cell"]
        im = Image.open(SHEETS / e["file"]).convert("RGBA").crop((0, 0, cw, ch))
        tx = 1 + i * 2
        foot_y = 2 * T + 20  # feet land 4 px above the bottom of tile row 1 (cell bottom 2px under feet)
        strip.alpha_composite(im, (tx * T + T // 2 - cw // 2, foot_y + 2 - ch))
    sb = strip.resize((strip.width * S, strip.height * S), Image.NEAREST)
    d = ImageDraw.Draw(sb)
    for x in range(0, sb.width + 1, T * S):
        d.line([(x, 0), (x, sb.height)], fill=(255, 255, 255, 110))
    for y in range(0, sb.height + 1, T * S):
        d.line([(0, y), (sb.width, y)], fill=(255, 255, 255, 110))
    W = max(top_w, sb.width) + 16
    H = top_h + sb.height + 40
    out = Image.new("RGBA", (W, H), BG)
    y = 8
    for r in rows:
        x = 8
        for b in r:
            out.alpha_composite(b, (x, y))
            x += b.width + 16
        y += max(b.height for b in r) + 16
    ImageDraw.Draw(out).text((8, y), "NEW characters on 24 px grass tiles (grid = 24 px), x3", fill=(255, 255, 160, 255))
    out.alpha_composite(sb, (8, y + 16))
    p = ART / "generated" / "preview_chunky_all.png"
    out.save(p)
    print("saved", p, out.size)


if __name__ == "__main__":
    main()

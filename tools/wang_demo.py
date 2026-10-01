"""Assemble a demo map from a Wang tileset to check seams and look.

python wang_demo.py <tileset_dir> <out.png> [tile_px] [scale]
Corner grid: 0 = lower terrain, 1 = upper terrain. Tile index = NW*8+NE*4+SW*2+SE.
"""
import json
import sys
from pathlib import Path
from PIL import Image

d = Path(sys.argv[1])
out = sys.argv[2]
tile_px = int(sys.argv[3]) if len(sys.argv) > 3 else 0
scale = int(sys.argv[4]) if len(sys.argv) > 4 else 3
info = json.loads((d / "tileset.json").read_text())
tiles = {}
for i, t in enumerate(info["tileset"]["tiles"]):
    c = t["corners"]
    idx = (c["NW"] == "upper") * 8 + (c["NE"] == "upper") * 4 + (c["SW"] == "upper") * 2 + (c["SE"] == "upper")
    im = Image.open(d / f"tileset_tiles_{i}_image.png").convert("RGBA")
    if tile_px:
        im = im.resize((tile_px, tile_px), Image.NEAREST)
    tiles[idx] = im

# Corner map (one more row/col than tiles): a winding path and a clearing.
corners = [
    "000000000000000",
    "000011000000000",
    "000011000000000",
    "000011111100000",
    "000011111110000",
    "000000111110000",
    "000000011100000",
    "000000011000000",
    "000000011000000",
    "000000000000000",
]
rows, cols = len(corners) - 1, len(corners[0]) - 1
ts = next(iter(tiles.values())).width
img = Image.new("RGBA", (cols * ts, rows * ts))
for y in range(rows):
    for x in range(cols):
        v = lambda yy, xx: int(corners[yy][xx])
        idx = v(y, x) * 8 + v(y, x + 1) * 4 + v(y + 1, x) * 2 + v(y + 1, x + 1)
        img.alpha_composite(tiles[idx], (x * ts, y * ts))
img.resize((img.width * scale, img.height * scale), Image.NEAREST).convert("RGB").save(out)
print("demo", out, img.size)

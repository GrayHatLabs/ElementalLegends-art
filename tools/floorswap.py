"""Make a water set's floor match the wall set's floor (free, local).

python floorswap.py <wall_dir> <water_dir> [out_dir]
PixelLab regenerates the floor texture in every tileset, so the floor of the water set
(upper terrain there) differs from the floor of the wall set (lower terrain there).
Each pixel of a water-set tile is classified as floor if its colour is nearer to the
water set's own floor tile colours than to its water tile colours AND it is not a dark
edge pixel of the shoreline; floor pixels are replaced by the wall-set floor tile pixel
at the same position (base tiles tile seamlessly by position, so seams stay invisible).
Pass --strict when the water and floor palettes overlap.
Writes tileset.json-compatible tiles to out_dir (default <water_dir>_fixed).
"""
import json
import shutil
import sys
from pathlib import Path
from PIL import Image


def load(d):
    d = Path(d)
    info = json.loads((d / "tileset.json").read_text())
    out = {}
    for i, t in enumerate(info["tileset"]["tiles"]):
        c = t["corners"]
        k = (c["NW"] == "upper") * 8 + (c["NE"] == "upper") * 4 + (c["SW"] == "upper") * 2 + (c["SE"] == "upper")
        out[k] = (i, Image.open(d / f"tileset_tiles_{i}_image.png").convert("RGBA"))
    return info, out


def d2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def nearest(c, pal):
    return min(d2(c, p) for p in pal)


SIDE, FACE = 1, 5


def swap(wall_dir, water_dir, out_dir=None, strict=False):
    wall_dir, water_dir = Path(wall_dir), Path(water_dir)
    out_dir = Path(out_dir) if out_dir else water_dir.with_name(water_dir.name + "_fixed")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(water_dir, out_dir, ignore=shutil.ignore_patterns("demo*.png", "*_fixed"))
    _, W = load(wall_dir)
    info, A = load(water_dir)
    wall_floor = W[0][1]
    floor_tile = A[15][1]
    water_tile = A[0][1]
    fpal = set(p[:3] for p in floor_tile.get_flattened_data())
    wpal = set(p[:3] for p in water_tile.get_flattened_data())
    n = floor_tile.width
    wt = water_tile.load()
    wf = wall_floor.load()
    for k, (i, im) in A.items():
        px = im.load()
        out = im.copy()
        op = out.load()
        if k != 0:
            water = [[False] * n for _ in range(n)]
            for y in range(n):
                for x in range(n):
                    c = px[x, y][:3]
                    dw, df = nearest(c, wpal), nearest(c, fpal)
                    if strict:  # overlapping palettes (e.g. murky swamp water vs mud): only colours unique to water
                        water[y][x] = c in wpal and c not in fpal
                    else:
                        water[y][x] = c == wt[x, y][:3] or (c in wpal and c not in fpal) or (dw < df and dw < 900)
            for y in range(n):
                for x in range(n):
                    if water[y][x]:
                        continue
                    near = any(water[yy][xx] for yy in range(max(0, y - SIDE), min(n, y + SIDE + 1))
                               for xx in range(max(0, x - SIDE), min(n, x + SIDE + 1)))
                    below = any(water[yy][x] for yy in range(y + 1, min(n, y + FACE + 1)))
                    # Edges running off the tile border: judge by the neighbouring tile's water, which we
                    # do not know here, so keep a band only where water is visible inside this tile.
                    if not (near or below):
                        op[x, y] = wf[x, y]
        out.save(out_dir / f"tileset_tiles_{i}_image.png")
    print("floorswap ->", out_dir)
    return out_dir


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--strict"]
    swap(*args, strict="--strict" in sys.argv)

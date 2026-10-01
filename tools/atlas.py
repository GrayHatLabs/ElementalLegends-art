"""Build a 4x4 atlas by Wang index (k at col k%4,row k//4): python atlas.py <tileset_dir> <out.png> [tile_px]"""
import json, sys
from pathlib import Path
from PIL import Image

def atlas(d, tile_px=24):
    d = Path(d)
    info = json.loads((d / "tileset.json").read_text())
    out = Image.new("RGBA", (tile_px * 4, tile_px * 4))
    seen = set()
    for i, t in enumerate(info["tileset"]["tiles"]):
        c = t["corners"]
        k = (c["NW"] == "upper") * 8 + (c["NE"] == "upper") * 4 + (c["SW"] == "upper") * 2 + (c["SE"] == "upper")
        seen.add(k)
        im = Image.open(d / f"tileset_tiles_{i}_image.png").convert("RGBA")
        if im.width != tile_px:
            im = im.resize((tile_px, tile_px), Image.NEAREST)
        out.alpha_composite(im, ((k % 4) * tile_px, (k // 4) * tile_px))
    assert seen == set(range(16)), f"missing wang indices in {d}: {set(range(16)) - seen}"
    return out

if __name__ == "__main__":
    atlas(sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 24).save(sys.argv[2])

"""Build final 24px terrain assets + terrain.json + contact sheet (free, local).

python build_terrain.py
Inputs: generated/tiles_<N>_<short>_wall/, generated/tiles_<N>_<short>_water_fixed/ (floor-swapped
water set, see floorswap.py), generated/deco_<N>_<name>/image.png.
Outputs: sheets/terrain/theme<N>_wall.png, theme<N>_water.png (96x96, 4x4 by Wang index),
theme<N>_deco_<name>.png (24x24), terrain.json; generated/preview_terrain_all.png.
"""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas import atlas  # noqa: E402
from terrain_gen import THEMES, tdir  # noqa: E402

ART = Path(__file__).resolve().parent.parent
GEN = ART / "generated"
OUT = ART / "sheets" / "terrain"
TP = 24


def water_dir(t):
    return tdir(t, "water").with_name(tdir(t, "water").name + "_fixed")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = {
        "tile_size": TP,
        "source_tile_size": 32,
        "atlas_layout": "4x4 grid of 24x24 tiles; tile with Wang index k is at column k%4, row k//4",
        "wang_index": "k = NW*8 + NE*4 + SW*2 + SE, where a corner is 1 if it is the UPPER terrain",
        "downscale": "32px PixelLab tiles -> 24px with Pillow NEAREST",
        "notes": "Water atlases have their floor pixels replaced with the wall atlas floor tile (tools/floorswap.py) "
                 "so wall-atlas index 0 and water-atlas index 15 are the identical floor tile.",
        "themes": [],
    }
    for t, th in THEMES.items():
        wall_png, water_png = f"theme{t}_wall.png", f"theme{t}_water.png"
        atlas(tdir(t, "wall"), TP).save(OUT / wall_png)
        atlas(water_dir(t), TP).save(OUT / water_png)
        is_lava = "lava" in th["water"].lower()
        decos = {}
        for n, desc in th.get("decos", {}).items():
            im = Image.open(GEN / f"deco_{t}_{n}" / "image.png").convert("RGBA").resize((TP, TP), Image.NEAREST)
            f = f"theme{t}_deco_{n}.png"
            im.save(OUT / f)
            decos[n] = {"file": f, "prompt": desc}
        doc["themes"].append({
            "index": t,
            "name": th["name"],
            "wall": {"file": wall_png, "lower": "floor (walkable)", "upper": "wall (solid)",
                     "lower_prompt": th["floor"], "upper_prompt": th["wall"], "transition_prompt": th["wall_tr"],
                     "floor_tile_index": 0, "wall_tile_index": 15},
            "water": {"file": water_png, "lower": "lava (hazard)" if is_lava else "water (not walkable)",
                      "upper": "floor (walkable)", "lower_prompt": th["water"], "upper_prompt": th["floor"],
                      "transition_prompt": th["water_tr"], "liquid_tile_index": 0, "floor_tile_index": 15},
            "decos": decos,
            "palette_images": {k: f"generated/palettes/theme{t}_{k}.png" for k in
                               (("wall", "water", "deco") if th.get("decos") else ("wall", "water"))},
        })
    (OUT / "terrain.json").write_text(json.dumps(doc, indent=2))
    contact_sheet()
    print("built", OUT)


def contact_sheet():
    rows = []
    for t, th in THEMES.items():
        demos = []
        for d in (tdir(t, "wall"), water_dir(t)):
            p = d / "demo24.png"
            subprocess.run([sys.executable, str(ART / "tools" / "wang_demo.py"), str(d), str(p), str(TP), "3"],
                           check=True, capture_output=True)
            demos.append(Image.open(p).convert("RGBA"))
        decos = [Image.open(OUT / f"theme{t}_deco_{n}.png").convert("RGBA").resize((TP * 3, TP * 3), Image.NEAREST)
                 for n in th.get("decos", {})]
        rows.append((f"{t}: {th['name']}", demos, decos))
    dw, dh = rows[0][1][0].size
    pad, label = 8, 16
    width = pad + 2 * (dw + pad) + 3 * (TP * 3 + pad)
    height = pad + len(rows) * (label + dh + pad)
    sheet = Image.new("RGBA", (width, height), (32, 32, 40, 255))
    draw = ImageDraw.Draw(sheet)
    y = pad
    for name, demos, decos in rows:
        draw.text((pad, y + 2), f"{name}   [wall | water/lava | decos]", fill=(230, 230, 230, 255))
        y += label
        x = pad
        for im in demos:
            sheet.alpha_composite(im, (x, y))
            x += dw + pad
        for im in decos:
            bg = Image.new("RGBA", im.size, (70, 70, 80, 255))
            bg.alpha_composite(im)
            sheet.alpha_composite(bg, (x, y))
            x += im.width + pad
        y += dh + pad
    sheet.convert("RGB").save(GEN / "preview_terrain_all.png")


if __name__ == "__main__":
    main()

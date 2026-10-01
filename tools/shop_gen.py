"""Shop interior art (theme 10 SHOP INTERIOR + shop furniture). Own helper; never touches the key.

python shop_gen.py pal                      -> generated/shop_palettes/*.png
python shop_gen.py wall                     -> generated/shop_tiles_10_wall/ (1 tileset generation)
python shop_gen.py deco [name]              -> generated/shop_deco_10_<name>/image.png
python shop_gen.py obj <name> <tag> [view]  -> generated/shop_objects/obj_<name>/<tag>.png (objects.py gen)
python shop_gen.py pack <name> <tag>        -> sheets/<name>.png + manifest_objects.json (objects.py pack)
python shop_gen.py build                    -> sheets/terrain/theme10_*.png + terrain.json entry 10
python shop_gen.py preview                  -> generated/preview_shop_interior.png
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import objects  # noqa: E402
from atlas import atlas  # noqa: E402
from terrain_palette import swatch, OUTLINE  # noqa: E402

ART = Path(__file__).resolve().parent.parent
GEN = ART / "generated"
SPAL = GEN / "shop_palettes"
SHEETS = ART / "sheets"
TER = SHEETS / "terrain"
LOG = GEN / "shop_usage.log"
STYLE = "SNES Zelda A Link to the Past style"
TP = 24
T = 10
WALL_DIR1 = GEN / "shop_tiles_10_wall"
WALL_DIR = GEN / "shop_tiles_10_wall_v2"  # v2 attempt (rejected: floor changed, noisy); final = v1 + paint_timber()

PLASTER = [(244, 232, 200), (228, 212, 172), (204, 184, 140)]
TIMBER = [(104, 70, 44), (76, 50, 34), (52, 34, 26)]
PLANK = [(200, 144, 84), (176, 122, 68), (148, 100, 56), (120, 80, 44), (92, 60, 36)]
ACCENT = [(200, 56, 56), (136, 32, 36), (64, 112, 200), (72, 156, 80), (224, 184, 72), (232, 216, 168), (160, 160, 156)]
RUG = [(184, 44, 44), (140, 32, 36), (96, 24, 32), (224, 184, 72), (168, 128, 56), (232, 216, 168), (48, 64, 116)]

FLOOR = (f"warm honey-brown wooden plank floor of long horizontal boards with thin dark seams and tiny nail dots, "
         f"cosy house interior, gentle shading, {STYLE} house interior floor, not neon")
WALL_V2 = (f"raised interior house wall seen from above, half-timbered tudor wall top: a grid of thick dark brown wooden "
        f"timber beams with small cream plaster panels between them, wood grain on the beams, cosy cottage interior, "
        f"{STYLE} house interior wall, not stone, not brick, not plain")
WALL = (f"raised interior house wall seen from above, thick wall top of smooth cream plaster framed by dark brown "
        f"timber beams, cosy cottage interior, {STYLE} house interior wall, not stone, not brick")
WALL_TR = "dark wooden wainscot skirting board with a soft shadow at the base of the wall"
DECOS = {
    "crate": f"single small square wooden storage crate with dark planks and corner nails, {STYLE}, warm browns",
    "sacks": f"two plump tied burlap grain sacks leaning together, pale tan cloth, {STYLE}, warm muted colors",
    "pot": f"single round clay pot with a small green potted plant, terracotta orange-brown, {STYLE}",
}
DECO_NEG = "neon colors, background, floor, ground, grass, text, frame"

# Shop furniture for objects.py: (description, gen_w, gen_h, palette, cell_w, cell_h, scale)
OS = objects.STYLE
SHOP_OBJ = {
    "obj_shop_counter": (f"long wooden merchant shop counter, wide and low, high top-down three-quarter view showing both the top "
                         f"and the front, thick polished medium-brown oak wooden counter top with visible wood grain and a lighter front edge highlight, "
                         f"not yellow, front made of warm reddish-brown wooden panels with plain carved square insets and lighter trim, "
                         f"not black, a brass bell, a small stack of gold coins, a potion bottle and an open ledger book on the top, {OS}",
                         240, 80, "../shop_palettes/shop_obj", 120, 40, 2),
    "obj_shelf": (f"tall wooden wall shelf cabinet standing upright, front view, three shelves filled with colourful "
                  f"potion bottles red blue and green, clay jars and rolled parchment scrolls, dark wood frame, {OS}",
                  96, 112, "../shop_palettes/shop_obj", 48, 56, 2),
    "obj_barrel": (f"single wooden barrel standing upright, brown curved wooden staves with dark iron hoops, "
                   f"round wooden lid visible on top, high three-quarter view, {OS}",
                   44, 52, "../shop_palettes/shop_obj", 22, 26, 2),
    "obj_rug": (f"rectangular ornate persian carpet rug lying flat on the floor, seen from directly above, rich red field "
                f"covered with a detailed woven pattern, wide gold and cream patterned border with small blue motifs, "
                f"a large central gold medallion and corner ornaments, cream fringe tassels along the two short ends, "
                f"flat, no shadow, no dark outline band, {OS}",
                192, 96, "../shop_palettes/shop_rug", 96, 48, 2),
}


def log(what):
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {what}\n")


def pixellab(*args):
    subprocess.run([sys.executable, str(ART / "tools" / "pixellab.py"), *map(str, args)], check=True)


def pal():
    SPAL.mkdir(parents=True, exist_ok=True)
    swatch(PLANK + PLASTER + TIMBER + OUTLINE, SPAL / "theme10_wall.png")
    swatch(PLANK[:4] + TIMBER + [(200, 176, 128), (168, 140, 96), (200, 104, 56), (72, 156, 80), (48, 112, 56)] + OUTLINE,
           SPAL / "theme10_deco.png")
    swatch(PLANK + TIMBER + PLASTER[:2] + ACCENT + OUTLINE, SPAL / "shop_obj.png")
    swatch(RUG + TIMBER[1:] + OUTLINE, SPAL / "shop_rug.png")
    print("palettes ->", SPAL)


def wall():
    if (WALL_DIR / "tileset.json").exists():
        print("exists", WALL_DIR)
    else:
        floor_id = json.loads((WALL_DIR1 / "tileset.json").read_text())["metadata"]["terrain_ids"]["lower"]
        pixellab("tileset", WALL_DIR.name, FLOOR, WALL_V2, 32, WALL_TR, SPAL / "theme10_wall.png", "0.25", floor_id)
        log("tileset theme10 wall")
    subprocess.run([sys.executable, str(ART / "tools" / "wang_demo.py"), str(WALL_DIR), str(WALL_DIR / "demo24.png"), "24", "3"], check=True)


def deco(only=None):
    for n, desc in DECOS.items():
        if only and n != only:
            continue
        d = GEN / f"shop_deco_10_{n}"
        if (d / "image.png").exists():
            continue
        pixellab("image", d.name, desc, 32, 32, SPAL / "theme10_deco.png", DECO_NEG)
        log(f"deco {n}")


def _objects():
    objects.OBJ.update(SHOP_OBJ)
    objects.GEN = GEN / "shop_objects"  # raws go to generated/shop_objects/obj_<name>/


def obj(name, tag, view="high top-down"):
    _objects()
    objects.gen(name, tag, "map", view)
    log(f"obj {name} {tag}")


def pack(name, tag):
    _objects()
    if name == "obj_rug":  # lies flat: centred in the cell, no base offset
        desc, w, h, p, cw, ch, sc = SHOP_OBJ[name]
        im = objects.clean(Image.open(objects.GEN / f"obj_{name}" / f"{tag}.png"))
        im = im.crop(im.getbbox())
        f = max(im.width / cw, im.height / ch, 1.0)
        im = objects.mode_downscale(im, max(1, round(im.width / f)), max(1, round(im.height / f)))
        im = im.crop(im.getbbox())
        cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cell.alpha_composite(im, ((cw - im.width) // 2, (ch - im.height) // 2))
        cell.save(SHEETS / f"{name}.png")
        m = json.loads(objects.MANIFEST.read_text())
        m["sprites"][name] = {"file": f"{name}.png", "cell": [cw, ch],
                              "anims": {"idle": {"row": 0, "frames": 1, "fps": 4}}}
        m["sprites"] = dict(sorted(m["sprites"].items()))
        objects.MANIFEST.write_text(json.dumps(m, indent=2))
        print("packed", name, cell.size)
    else:
        objects.pack(name, [tag])


CREAM = (244, 232, 200)
BEAM_HI, BEAM, BEAM_LO, BEAM_DK = (140, 96, 60), (104, 70, 44), (76, 50, 34), (52, 34, 26)
PL_HI, PL, PL_SH, PL_DK = (244, 232, 200), (230, 214, 174), (210, 190, 148), (188, 166, 124)


def timber_texture():
    """Seamless 24x24 half-timbered plaster pattern (period = one tile, aligned to the tile grid):
    a thick post on the tile's left edge, a rail across the middle, a diagonal brace in the lower panel,
    cream plaster panels with light speckle and soft shading under the timbers."""
    im = Image.new("RGBA", (TP, TP))
    p = im.load()
    put = lambda x, y, c: p.__setitem__((x % TP, y % TP), c + (255,))
    for y in range(TP):
        for x in range(TP):
            c = PL
            if (x * 7 + y * 13) % 29 == 0:
                c = PL_SH
            elif (x * 5 + y * 11) % 31 == 0:
                c = PL_HI
            put(x, y, c)
    # diagonal brace (lower panel, rising left->right) with plaster shadow beneath it
    for i in range(0, 12):
        x, y = 5 + i * 19 // 11, 23 - i
        for dx, c in ((0, BEAM_HI), (1, BEAM), (2, BEAM), (3, BEAM_LO)):
            put(x + dx, y, c)
        put(x + 4, y, PL_SH)
    for y in range(TP):  # plaster shade right of the post
        put(5, y, PL_SH)
    for x in range(TP):  # plaster shade under the rail
        put(x, 13, PL_SH)
        put(x, 14, PL_DK if x % 2 else PL_SH)
    for y in range(TP):  # vertical post x 0..4 with grain
        for x, c in ((0, BEAM_HI), (1, BEAM), (2, BEAM), (3, BEAM), (4, BEAM_LO)):
            put(x, y, BEAM_LO if (y % 7 == 3 and x in (2, 3)) else c)
    for x in range(TP):  # horizontal rail y 8..12 with grain
        for y, c in ((8, BEAM_HI), (9, BEAM), (10, BEAM), (11, BEAM_LO), (12, BEAM_DK)):
            put(x, y, BEAM_LO if (x % 8 == 5 and y in (9, 10)) else c)
    for y in range(8, 13):  # joint where post meets rail
        put(4, y, BEAM_DK)
    put(2, 10, BEAM_DK)  # peg
    return im

def painted_atlas():
    """v1 atlas with its flat cream wall pixels replaced by the timber texture (free, local)."""
    a = atlas(WALL_DIR1, TP)
    tex = timber_texture().load()
    px = a.load()
    for y in range(a.height):
        for x in range(a.width):
            if px[x, y][:3] == CREAM:
                px[x, y] = tex[x % TP, y % TP]
    return a


def build():
    painted_atlas().save(TER / f"theme{T}_wall.png")
    decos = {}
    for n, desc in DECOS.items():
        p = GEN / f"shop_deco_10_{n}" / "image.png"
        if not p.exists():
            continue
        f = f"theme{T}_deco_{n}.png"
        Image.open(p).convert("RGBA").resize((TP, TP), Image.NEAREST).save(TER / f)
        decos[n] = {"file": f, "prompt": desc}
    entry = {
        "index": T,
        "name": "SHOP INTERIOR",
        "wall": {"file": f"theme{T}_wall.png", "lower": "floor (walkable)", "upper": "wall (solid)",
                 "lower_prompt": FLOOR, "upper_prompt": WALL, "transition_prompt": WALL_TR,
                 "floor_tile_index": 0, "wall_tile_index": 15,
                 "postprocess": "flat cream wall pixels repainted locally with a seamless 24px half-timber "
                                "pattern (tools/shop_gen.py timber_texture/painted_atlas)"},
        "decos": decos,
        "palette_images": {"wall": "generated/shop_palettes/theme10_wall.png",
                           "deco": "generated/shop_palettes/theme10_deco.png"},
        "notes": "Indoor theme: no water/lava set (importer treats a missing water atlas as None).",
    }
    tj = TER / "terrain.json"
    doc = json.loads(tj.read_text())
    doc["themes"] = [t for t in doc["themes"] if t.get("index") != T] + [entry]
    doc["themes"].sort(key=lambda t: t["index"])
    tj.write_text(json.dumps(doc, indent=2))
    print("terrain.json theme 10 written;", len(decos), "decos")


def preview():
    """Mock 16x13-tile shop room: walls on the border ring, planks inside."""
    W, H = 16, 13
    at = Image.open(TER / f"theme{T}_wall.png").convert("RGBA")
    tile = lambda k: at.crop(((k % 4) * TP, (k // 4) * TP, (k % 4 + 1) * TP, (k // 4 + 1) * TP))
    # Corner grid (W+1 x H+1): 1 = wall. Wall band 1.5 tiles thick at the top (back wall), 1 elsewhere.
    def up(cx, cy):
        if cy >= H - 1 and 7 <= cx <= 9:  # door opening in the bottom wall
            return False
        return cx <= 1 or cx >= W - 1 or cy <= 1 or cy >= H - 1
    room = Image.new("RGBA", (W * TP, H * TP))
    for y in range(H):
        for x in range(W):
            k = up(x, y) * 8 + up(x + 1, y) * 4 + up(x, y + 1) * 2 + up(x + 1, y + 1)
            room.alpha_composite(tile(k), (x * TP, y * TP))
    # door gap in the bottom wall (centre) shown as floor
    d = GEN / "shop_objects"
    spr = lambda n: Image.open(SHEETS / f"{n}.png").convert("RGBA")
    dec = lambda n: Image.open(TER / f"theme{T}_deco_{n}.png").convert("RGBA") if (TER / f"theme{T}_deco_{n}.png").exists() else None
    rug = spr("obj_rug")
    room.alpha_composite(rug, ((W * TP - rug.width) // 2, 6 * TP + 12 - rug.height // 2))
    shelf = spr("obj_shelf")
    for x in (3 * TP, (W - 3) * TP - shelf.width):
        room.alpha_composite(shelf, (x, 2 * TP - 6))
    counter = spr("obj_shop_counter")
    room.alpha_composite(counter, ((W * TP - counter.width) // 2, 3 * TP))
    bar = spr("obj_barrel")
    for (x, y) in ((TP + 14, 2 * TP + 4), ((W - 1) * TP - bar.width - 14, 2 * TP + 4),
                   (TP + 14, (H - 1) * TP - bar.height - 12), ((W - 1) * TP - bar.width - 14, (H - 1) * TP - bar.height - 12)):
        room.alpha_composite(bar, (x, y))
    for n, (x, y) in (("crate", (3, 10)), ("sacks", (12, 10)), ("pot", (2, 6))):
        im = dec(n)
        if im:
            room.alpha_composite(im, (x * TP, y * TP))
    # merchant behind counter (if available) and the mage
    mm = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
    for n, (x, y) in (("npc_merchant", (W * TP // 2 - 12, 3 * TP - 22)), ("mage_fire", (W * TP // 2 - 12, 8 * TP))):
        if n in mm and (SHEETS / f"{n}.png").exists():
            cw, ch = mm[n]["cell"]
            room.alpha_composite(Image.open(SHEETS / f"{n}.png").convert("RGBA").crop((0, 0, cw, ch)), (x, y))
    out = room.resize((room.width * 2, room.height * 2), Image.NEAREST)
    out.convert("RGB").save(GEN / "preview_shop_interior.png")
    print("wrote", GEN / "preview_shop_interior.png", room.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"pal": lambda: pal(), "wall": lambda: wall(), "deco": lambda: deco(*a[1:]),
     "obj": lambda: obj(*a[1:]), "pack": lambda: pack(*a[1:]), "build": lambda: build(),
     "preview": lambda: preview()}[a[0]]()

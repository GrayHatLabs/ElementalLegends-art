"""Lair dungeon decoration props (themes 4..9) for Elemental Legends. Reuses objects.py helpers.

python props.py gen <name>[,<name>...] [tag]   -> generated/props_<name>/<tag>.png (1 generation each, parallel)
python props.py gentheme <t> [tag]             -> all props of theme t
python props.py pack <name> [tag]              -> sheets/<name>.png + sheets/manifest_props.json entry
python props.py packall                        -> pack every prop (uses PICK for the chosen tag)
python props.py preview                        -> generated/preview_props_all.png
"""
import colorsys
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixellab import call, wait_job, download, save_b64, find_urls, find_b64, GEN  # noqa: E402
from objects import b64, clean, mode_downscale, floor_patch, STYLE, SHEETS  # noqa: E402
import terrain_palette as TP  # noqa: E402

MANIFEST = SHEETS / "manifest_props.json"
PALDIR = GEN / "props_palettes"
USAGE = GEN / "props_usage.log"
LOCK = threading.Lock()

O = TP.OUTLINE
FIRE = [(252, 236, 136), (248, 184, 56), (232, 112, 24), (184, 56, 16)]
HOLY = [(248, 252, 255), (200, 236, 252), (136, 200, 240), (88, 148, 220)]
VIOLET = [(244, 208, 255), (208, 136, 248), (160, 80, 216), (104, 48, 160)]
GOLD = [(248, 216, 96), (208, 160, 48), (144, 100, 32)]
RED = [(200, 64, 56), (152, 40, 40), (104, 28, 32)]
BONE = [(240, 232, 208), (208, 196, 164), (160, 148, 120)]
IRON = [(120, 120, 128), (84, 84, 92), (56, 56, 64)]
WHITE = [(248, 248, 252), (224, 232, 244)]
MUSH = [(208, 72, 56), (240, 220, 180)]
DPURP = [(104, 84, 112), (76, 60, 84), (52, 44, 60)]

BASE = {
    4: TP.MOSS + TP.GREY[1:] + TP.CANOPY[1:4] + O,
    5: TP.GREY + [(96, 96, 104), (72, 72, 80)] + O,
    6: TP.TAN + TP.SAND[1:] + O,
    7: TP.REDBLK + TP.CHAR + O,
    8: TP.BLUE_MARBLE + TP.BLUEGREY[1:] + WHITE + O,
    9: TP.OBSID + TP.PURPLE_BRICK + O,
}
FLAME = {4: FIRE, 5: FIRE, 6: FIRE, 7: FIRE, 8: HOLY, 9: VIOLET}

TOP = "high top-down"
FLATV = "high top-down"
FLATD = "lying flat on the floor, seen from directly above, flat floor decal, no walls"

# name: (description, gen_w, gen_h, accent colours, cell_w, cell_h, kind)  kind: stand | flat | fire | pulse
P = {
    # ---- 4 Overgrown Shrine (mossy green stone)
    "prop_4_statue": ("ancient moss-covered stone guardian statue, a robed stone warrior holding a big sword point-down in front of him with both hands, "
                      "standing on a square stone plinth, thick green moss and ivy vines growing over the grey stone, chunky wide silhouette, full body visible, front view",
                      48, 80, [], 24, 40, "stand"),
    "prop_4_pillar": ("single round grey stone column pillar with a square base and square capital, wrapped in green ivy vines and moss patches, cracked weathered stone, front view",
                      40, 80, [], 24, 48, "stand"),
    "prop_4_brazier": ("round mossy grey stone brazier bowl on a short stone pedestal, burning a bright orange and yellow fire flame, green ivy leaves curling around the pedestal, front view",
                       48, 64, FIRE, 24, 32, "fire"),
    "prop_4_roots": (f"thick gnarled brown tree roots spreading out across the ground in a wide tangle, small green moss patches on the roots, {FLATD}",
                     96, 64, TP.WOOD + TP.DIRT[1:3], 48, 32, "flat"),
    "prop_4_clump": ("small clump of green leafy ivy vines with three red-capped and brown mushrooms growing from it",
                     48, 48, MUSH + TP.WOOD[:2], 24, 24, "stand"),
    "prop_4_banner": ("tattered green cloth banner hanging from a horizontal wooden pole, a golden leaf emblem embroidered on it, frayed ragged bottom edge, ivy vines curling on the pole, front view",
                      48, 64, GOLD[:2] + TP.WOOD[:2], 24, 32, "stand"),
    # ---- 5 Underground Crypt (grey stone, bones)
    "prop_5_statue": ("hooded mourner stone statue, a tall weeping figure in a long hooded robe with the face hidden in shadow and hands clasped in prayer, "
                      "standing on a square stone plinth, cold grey stone, chunky wide silhouette, full body visible, front view",
                      48, 80, [], 24, 40, "stand"),
    "prop_5_pillar": ("grey stone crypt pillar column with a row of carved bone-white skulls around the top capital, square base, cracked cold grey stone, front view",
                      40, 80, BONE[:2], 24, 48, "stand"),
    "prop_5_brazier": ("black iron brazier bowl on a tall thin three-legged iron stand, a bone-white skull fixed on the front of the bowl, burning a bright orange fire flame, front view",
                       48, 64, FIRE + BONE[:2], 24, 32, "fire"),
    "prop_5_runes": (f"faded ritual circle carved into stone, a thin ring of grey carved runes with a small skull symbol in the centre, {FLATD}",
                     96, 96, BONE[:2], 48, 48, "flat"),
    "prop_5_bones": ("small pile of old white bones with a skull on top, ribs and leg bones heaped together",
                     48, 48, BONE, 24, 24, "stand"),
    "prop_5_banner": ("tattered dark grey-purple funeral banner hanging from a horizontal iron rod, a white skull emblem on it, torn ragged bottom edge, front view",
                      48, 64, DPURP + BONE[:2], 24, 32, "stand"),
    # ---- 6 Ruined Castle (tan sandstone)
    "prop_6_statue": ("stone knight statue in full plate armour and a closed helmet, both hands resting on the pommel of a big sword planted point-down, "
                      "standing on a square plinth, tan sandstone, chunky wide silhouette, full body visible, front view",
                      48, 80, [], 24, 40, "stand"),
    "prop_6_pillar": ("tan sandstone castle column pillar with a square base and square capital, a chunk broken off one side, weathered blocks, front view",
                      40, 80, [], 24, 48, "stand"),
    "prop_6_brazier": ("black iron brazier bowl on a tall iron tripod stand, burning a bright orange and yellow fire flame, front view",
                       48, 64, FIRE + IRON, 24, 32, "fire"),
    "prop_6_rug": (f"rectangular faded red royal carpet with a wide ornate gold patterned border and a gold diamond pattern in the middle, a small frayed torn corner, perfectly flat rectangle seen from directly overhead, {FLATD}",
                   96, 64, RED + GOLD[:2], 48, 32, "flat"),
    "prop_6_rubble": ("small pile of broken tan sandstone rubble blocks with a dented round red and grey shield and a rusty sword lying on top",
                      48, 48, RED[:2] + IRON[:2], 24, 24, "stand"),
    "prop_6_banner": ("tattered red castle banner with a golden lion crest, hanging from a horizontal wooden pole, frayed ragged bottom edge, front view",
                      48, 64, RED + GOLD[:2] + TP.WOOD[:2], 24, 32, "stand"),
    # ---- 7 Dragon Fortress (black-red volcanic)
    "prop_7_statue": ("black obsidian dragon statue sitting upright on a square stone plinth, wings folded, horned head looking forward, small glowing orange eyes, "
                      "black and dark red volcanic stone, chunky wide silhouette, full body visible, front view",
                      48, 80, TP.GLOW, 24, 40, "stand"),
    "prop_7_pillar": ("thick massive wide black volcanic stone column pillar with thin glowing orange lava cracks running down it, jagged spiky capital, square base, front view",
                      48, 80, TP.GLOW + [TP.LAVA[1]], 24, 48, "stand"),
    "prop_7_brazier": ("black iron brazier shaped like a dragon claw gripping a bowl of fire, on a short black stand, burning a big orange-red fire flame, front view",
                       48, 64, FIRE, 24, 32, "fire"),
    "prop_7_mosaic": (f"round dark red and black stone mosaic medallion inlaid in a floor, a golden coiled dragon symbol in the centre, {FLATD}",
                      96, 96, GOLD + RED[:2], 48, 48, "flat"),
    "prop_7_hoard": ("small heap of shiny gold coins and treasure, a gold goblet and a red gem on top, a few jagged glossy black obsidian shards sticking out of the heap",
                     48, 48, GOLD + [RED[0], (96, 92, 104)], 24, 24, "stand"),
    "prop_7_banner": ("black war banner with a red dragon emblem, hanging from a spiked black iron rod, torn ragged bottom edge, front view",
                      48, 64, RED + [GOLD[1]], 24, 32, "stand"),
    # ---- 8 Forgotten Sanctuary (blue-white marble)
    "prop_8_statue": ("white marble angel statue with large folded feathered wings and hands together in prayer, long flowing robe, standing on a square plinth, "
                      "pale blue-white marble with small gold details, chunky wide silhouette, full body visible, front view",
                      48, 80, GOLD[:2], 24, 40, "stand"),
    "prop_8_pillar": ("thick massive wide white marble fluted greek column with an ionic scroll capital and square base, pale blue-white marble with a gold band, front view",
                      48, 80, GOLD[:2], 24, 48, "stand"),
    "prop_8_brazier": ("tall white marble pedestal with a wide shallow silver bowl on top with gold trim, a big bright pale cyan-blue holy fire flame rising from the bowl, front view",
                       48, 64, HOLY + GOLD[:2], 24, 32, "fire"),
    "prop_8_mosaic": (f"round blue and gold marble mosaic floor medallion with an eight-pointed golden star in the centre, inlaid tiles, {FLATD}",
                      96, 96, GOLD + [(40, 88, 160)], 48, 48, "flat"),
    "prop_8_books": ("small pile of fallen old leather books, one book lying open, with two melted white candles burning with small flames",
                     48, 48, [(120, 56, 48), (64, 88, 136), (136, 100, 64), FIRE[0], FIRE[1]] + BONE[:2], 24, 24, "stand"),
    "prop_8_banner": ("long blue tapestry with a golden sun emblem and gold fringe at the bottom, hanging from a gold rod, front view",
                      48, 64, GOLD + [(64, 96, 184), (40, 64, 140)], 24, 32, "stand"),
    # ---- 9 Dark Tower (purple-black)
    "prop_9_statue": ("dark idol statue, a sinister hunched horned demon figure with small glowing violet eyes, carved from black-purple stone, "
                      "sitting on a square stone plinth, chunky wide silhouette, full body visible, front view",
                      48, 80, VIOLET[1:3], 24, 40, "stand"),
    "prop_9_pillar": ("short stout very wide square black-purple stone column pillar, as wide as half its height, with glowing violet runes carved down its front, pointed spiky capital, square base, front view",
                      48, 80, VIOLET[:3], 24, 48, "stand"),
    "prop_9_brazier": ("black iron brazier bowl on a thin twisted iron stand, burning a bright violet purple magic fire flame, front view",
                       48, 64, VIOLET + IRON[1:], 24, 32, "fire"),
    "prop_9_circle": (f"thin glowing violet line drawing of a magic summoning circle, two thin rings with small rune glyphs between them and a thin six-pointed star inside, mostly empty so the floor shows through, {FLATD}",
                      96, 96, VIOLET, 48, 48, "pulse"),
    "prop_9_cage": ("simple square iron cage with thick light grey iron vertical bars and a ring on top, a heavy grey iron chain coiled on the floor beside it",
                    48, 48, IRON + [(120, 72, 48)], 24, 24, "stand"),
    "prop_9_banner": ("dark purple tapestry with a glowing violet eye emblem, hanging from a black iron rod, torn ragged bottom edge, front view",
                      48, 64, VIOLET[1:3] + [GOLD[1]], 24, 32, "stand"),
}
PICK = {"prop_4_statue": "b", "prop_6_rug": "b", "prop_7_pillar": "b", "prop_8_pillar": "b", "prop_9_pillar": "c", "prop_7_hoard": "c", "prop_8_brazier": "b", "prop_9_circle": "b", "prop_9_cage": "b"}  # name -> chosen tag (default "a")
FIRE_FRAMES, FPS = 4, 4


def theme_of(name):
    return int(name.split("_")[1])


def palette_png(name):
    PALDIR.mkdir(parents=True, exist_ok=True)
    t = theme_of(name)
    cols, seen = [], set()
    for c in P[name][3] + BASE[t]:
        if c not in seen:
            seen.add(c)
            cols.append(c)
    p = PALDIR / f"{name}.png"
    TP.swatch(cols, p)
    return p


def gen_one(name, tag="a"):
    desc, w, h, acc, cw, ch, kind = P[name]
    d = GEN / f"props_{name}"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{tag}.png"
    body = {"description": f"{desc}, {STYLE}", "image_size": {"width": w, "height": h},
            "view": FLATV if kind in ("flat", "pulse") else TOP,
            "outline": "selective outline", "shading": "medium shading", "detail": "medium detail",
            "color_image": b64(palette_png(name))}
    for attempt in range(6):
        try:
            r = call("POST", "/map-objects", body)
            j = wait_job(r["background_job_id"]) if r.get("background_job_id") else r
            break
        except SystemExit as e:
            msg = str(e)
            if "429" in msg or "503" in msg or "502" in msg:
                time.sleep(20 + 15 * attempt)
                continue
            print("FAILED", name, tag, msg[:300])
            return
    else:
        print("GAVE UP", name, tag)
        return
    (d / f"{tag}.json").write_text(json.dumps(j, default=str)[:4000])
    lr = j.get("last_response") or {}
    import base64
    if isinstance(lr.get("image"), str):
        out.write_bytes(base64.b64decode(lr["image"]))
    elif isinstance(lr.get("image"), dict) and "base64" in lr["image"]:
        save_b64(lr["image"], out)
    else:
        imgs = list(find_b64(j))
        if imgs:
            save_b64(imgs[0][1], out)
        else:
            urls = list(find_urls(j))
            if not urls and r.get("object_id"):
                info = call("GET", f"/objects/{r['object_id']}")
                urls = list(find_urls(info))
                if not urls:
                    save_b64(list(find_b64(info))[0][1], out)
            if urls:
                download(urls[0][1], out)
    with LOCK:
        with USAGE.open("a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {name} {tag} {w}x{h}\n")
    print("saved", out, Image.open(out).size, flush=True)


def gen_many(names, tag="a"):
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda n: gen_one(n, tag), names))


# ---------------------------------------------------------------- packing
def fit(name, tag):
    desc, w, h, acc, cw, ch, kind = P[name]
    flat = kind in ("flat", "pulse")
    # thin diagonal lines on decals are only 8-connected: keep small pieces there
    im = clean(Image.open(GEN / f"props_{name}" / f"{tag}.png"), min_speck=1 if flat else 24)
    im = im.crop(im.getbbox())
    room_h = ch if flat else ch - 2
    if kind == "fire":
        room_h -= 2  # headroom so the taller flicker frames are not clipped
    f = max(im.width / cw, im.height / room_h, 1.0)
    if abs(f - round(f)) < 0.08:
        f = round(f)
    im = downscale(im, max(1, round(im.width / f)), max(1, round(im.height / f)), 0.25 if flat else 0.5)
    im = im.crop(im.getbbox())
    im = outline(im, theme_of(name), 0.6 if flat else 0.45)
    cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    y = (ch - im.height) // 2 if flat else ch - 2 - im.height
    cell.alpha_composite(im, ((cw - im.width) // 2, y))
    return cell


def downscale(im, tw, th, keep=0.5):
    """Mode downscale (objects.mode_downscale) with a coverage threshold: a target pixel is opaque when at least
    `keep` of its source block is opaque, so thin glowing lines on flat decals survive."""
    from collections import Counter
    sw, sh = im.size
    src = im.load()
    out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    dst = out.load()
    for y in range(th):
        y0, y1 = int(y * sh / th), max(int(y * sh / th) + 1, int((y + 1) * sh / th))
        for x in range(tw):
            x0, x1 = int(x * sw / tw), max(int(x * sw / tw) + 1, int((x + 1) * sw / tw))
            c = Counter(src[i, j] for j in range(y0, y1) for i in range(x0, x1))
            total = sum(c.values())
            solid = total - sum(v for k, v in c.items() if k[3] == 0)
            if solid < keep * total or solid == 0:
                continue
            dst[x, y] = max(((v, k) for k, v in c.items() if k[3] > 0))[1]
    return out


def outline(im, t, k=0.45):
    """Darken the silhouette edge (selective outline) so props read against busy floors; flames keep their colour."""
    im = im.copy()
    px = im.load()
    src = im.copy().load()
    W, H = im.size
    for y in range(H):
        for x in range(W):
            c = src[x, y]
            if c[3] == 0 or is_flame(c, t):
                continue
            if any(not (0 <= x + dx < W and 0 <= y + dy < H) or src[x + dx, y + dy][3] == 0
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = (int(c[0] * k), int(c[1] * k), int(c[2] * k), 255)
    return im


def is_flame(c, t):
    r, g, b, a = c
    if a == 0:
        return False
    hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if t == 8:
        return v > 0.78 and b >= r and (s > 0.12 or v > 0.95)
    if t == 9:
        return v > 0.55 and s > 0.35 and 0.72 < hh < 0.92
    return v > 0.65 and s > 0.45 and (hh < 0.17 or hh > 0.97)


def flame_section(cell, t):
    """Rows (y0, y1) at the top made mostly of flame pixels, and the flame centre x."""
    px = cell.load()
    W, H = cell.size
    rows = []
    for y in range(H):
        op = [x for x in range(W) if px[x, y][3]]
        fl = [x for x in op if is_flame(px[x, y], t)]
        rows.append((op, fl))
    y0 = next((y for y in range(H) if rows[y][1]), None)
    if y0 is None:
        return None
    y1 = y0
    while y1 < H and rows[y1][0] and len(rows[y1][1]) >= 0.45 * len(rows[y1][0]):
        y1 += 1
    xs = [x for y in range(y0, y1) for x in rows[y][0]]
    cx2 = min(xs) + max(xs)  # 2 * centre
    return y0, y1, cx2


def flicker(cell, t):
    sec = flame_section(cell, t)
    if not sec:
        print("no flame found")
        return [cell]
    y0, y1, cx2 = sec
    W, H = cell.size
    top = cell.crop((0, y0, W, y1))
    flip = Image.new("RGBA", top.size, (0, 0, 0, 0))
    tp, fp = top.load(), flip.load()
    for y in range(top.height):
        for x in range(W):
            nx = cx2 - x
            if 0 <= nx < W:
                fp[nx, y] = tp[x, y]

    def stretched(src):
        """flame one pixel taller: rows shift up by one, the lowest flame row is duplicated."""
        c = cell.copy()
        c.paste((0, 0, 0, 0), (0, y0, W, y1))
        c.alpha_composite(src, (0, y0))
        tall = Image.new("RGBA", (W, src.height + 1), (0, 0, 0, 0))
        tall.alpha_composite(src, (0, 0))
        tall.alpha_composite(src.crop((0, src.height - 1, W, src.height)), (0, src.height))
        c.paste((0, 0, 0, 0), (0, max(0, y0 - 1), W, y1))
        c.alpha_composite(tall, (0, max(0, y0 - 1)))
        return c

    def placed(src):
        c = cell.copy()
        c.paste((0, 0, 0, 0), (0, y0, W, y1))
        c.alpha_composite(src, (0, y0))
        return c
    return [cell, stretched(top), placed(flip), stretched(flip)]


def pulse(cell, t):
    """2-frame glow pulse for magic floor circles: brighten flame/glow pixels one ramp step."""
    b = cell.copy()
    px = b.load()
    for y in range(b.height):
        for x in range(b.width):
            c = px[x, y]
            if is_flame(c, t) or (c[3] and t == 9 and colorsys.rgb_to_hsv(*[v / 255 for v in c[:3]])[1] > 0.3):
                px[x, y] = tuple(min(255, v + 40) for v in c[:3]) + (255,)
    return [cell, b]


def rug_border(cell):
    """Gold trim 2 px inside the rug edge (the generation lost its border at this size)."""
    c = cell.copy()
    px = c.load()
    x0, y0, x1, y1 = c.getbbox()
    for x in range(x0 + 2, x1 - 2):
        for y in (y0 + 2, y1 - 3):
            if px[x, y][3]:
                px[x, y] = GOLD[1] + (255,)
    for y in range(y0 + 2, y1 - 2):
        for x in (x0 + 2, x1 - 3):
            if px[x, y][3]:
                px[x, y] = GOLD[1] + (255,)
    return c


MODS = {"prop_6_rug": rug_border}


def pack(name, tag=None):
    tag = tag or PICK.get(name, "a")
    desc, w, h, acc, cw, ch, kind = P[name]
    cell = fit(name, tag)
    if kind == "fire":
        frames = flicker(cell, theme_of(name))
    elif kind == "pulse":
        frames = pulse(cell, theme_of(name))
    else:
        frames = [cell]
    if name in MODS:
        frames = [MODS[name](f) for f in frames]
    sheet = Image.new("RGBA", (cw * len(frames), ch), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, (i * cw, 0))
    sheet.save(SHEETS / f"{name}.png")
    with LOCK:
        m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
        m["sprites"][name] = {"file": f"{name}.png", "cell": [cw, ch],
                              "anims": {"idle": {"row": 0, "frames": len(frames), "fps": FPS}}}
        m["sprites"] = dict(sorted(m["sprites"].items()))
        MANIFEST.write_text(json.dumps(m, indent=2))
    print("packed", name, tag, sheet.size, len(frames), "frames")


# ---------------------------------------------------------------- preview
def hero():
    mm = json.loads((SHEETS / "manifest.json").read_text())["sprites"]["mage_fire"]
    cw, ch = mm["cell"]
    return Image.open(SHEETS / "mage_fire.png").convert("RGBA").crop((0, 0, cw, ch))


def theme_strip(t, frame=0):
    m = json.loads(MANIFEST.read_text())["sprites"]
    names = [n for n in P if theme_of(n) == t and n in m]
    flats = [n for n in names if P[n][6] in ("flat", "pulse")]
    stands = [n for n in names if n not in flats]
    W, H = 24 * 11, 24 * 4
    bg = floor_patch(t, W, H)
    labels = []
    x = 12
    base = 70
    mg = hero()
    for n in stands[:3] + ["mage"] + stands[3:]:
        if n == "mage":
            bg.alpha_composite(mg, (x, base - mg.height + 2))
            labels.append(("mage", x))
            x += mg.width + 6
            continue
        e = m[n]
        cw, ch = e["cell"]
        sh = Image.open(SHEETS / e["file"]).convert("RGBA")
        k = frame % e["anims"]["idle"]["frames"]
        bg.alpha_composite(sh.crop((k * cw, 0, (k + 1) * cw, ch)), (x, base + 2 - ch))
        labels.append((n.split("_", 2)[2], x))
        x += cw + 6
    for n in flats:
        e = m[n]
        cw, ch = e["cell"]
        sh = Image.open(SHEETS / e["file"]).convert("RGBA")
        k = frame % e["anims"]["idle"]["frames"]
        bg.alpha_composite(sh.crop((k * cw, 0, (k + 1) * cw, ch)), (x, (H - ch) // 2))
        labels.append((n.split("_", 2)[2] + " (flat)", x))
        x += cw + 6
    return bg, labels


def preview():
    NAMES = {4: "Overgrown Shrine", 5: "Underground Crypt", 6: "Ruined Castle",
             7: "Dragon Fortress", 8: "Forgotten Sanctuary", 9: "Dark Tower"}
    S = 3
    rows = []
    for t in range(4, 10):
        try:
            bg, labels = theme_strip(t)
        except Exception as ex:  # theme not packed yet
            print("skip", t, ex)
            continue
        # flame frames strip
        m = json.loads(MANIFEST.read_text())["sprites"]
        fr = None
        bn = f"prop_{t}_brazier"
        if bn in m:
            e = m[bn]
            fr = Image.open(SHEETS / e["file"]).convert("RGBA")
            pad = floor_patch(t, fr.width + 8, fr.height + 8)
            pad.alpha_composite(fr, (4, 4))
            fr = pad.resize((pad.width * S, pad.height * S), Image.NEAREST)
        rows.append((t, bg.resize((bg.width * S, bg.height * S), Image.NEAREST), labels, fr))
    W = max(r[1].width + (r[3].width + 20 if r[3] else 0) for r in rows) + 20
    H = sum(r[1].height + 40 for r in rows) + 10
    out = Image.new("RGBA", (W, H), (32, 32, 40, 255))
    d = ImageDraw.Draw(out)
    y = 6
    for t, im, labels, fr in rows:
        d.text((10, y), f"theme {t} - {NAMES[t]}   (prop_{t}_*)", fill=(255, 230, 140, 255))
        for lab, x in labels:
            d.text((10 + x * S, y + 14), lab, fill=(230, 230, 230, 255))
        out.alpha_composite(im, (10, y + 28))
        if fr:
            out.alpha_composite(fr, (10 + im.width + 20, y + 28))
            d.text((10 + im.width + 20, y + 14), "brazier frames", fill=(230, 230, 230, 255))
        y += im.height + 40
    out.save(GEN / "preview_props_all.png")
    print("wrote preview", out.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen":
        gen_many(a[1].split(","), *(a[2:]))
    elif a[0] == "gentheme":
        gen_many([n for n in P if theme_of(n) == int(a[1])], *(a[2:]))
    elif a[0] == "pack":
        pack(a[1], *(a[2:]))
    elif a[0] == "packtheme":
        for n in P:
            if theme_of(n) == int(a[1]):
                pack(n, *(a[2:]))
    elif a[0] == "packall":
        for n in P:
            if (GEN / f"props_{n}" / f"{PICK.get(n, 'a')}.png").exists():
                pack(n)
    elif a[0] == "preview":
        preview()

"""Relic / dungeon-puzzle art for Elemental Legends (uses pixellab.py; never touches the key).

python relics.py gen <key>[,<key>...] [tag]   -> generated/relic_<key>/<tag>.png (1 generation each, <=6 parallel)
python relics.py build                        -> all sheets/*.png + sheets/manifest_relics.json
python relics.py preview                      -> generated/preview_relics_all.png

Raws live in generated/relic_*; only sheets/manifest_relics.json is written (never manifest_objects/props).
"""
import base64
import json
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixellab import call, wait_job, download, save_b64, find_urls, find_b64, GEN  # noqa: E402
from objects import clean, mode_downscale, checker, floor_patch, STYLE, PAL  # noqa: E402

ART = GEN.parent
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest_relics.json"
USAGE = GEN / "relics_usage.log"
_lock = threading.Lock()

ICON = "game item icon, single object centred, bold black outline, simple readable shape, SNES Zelda A Link to the Past item style"
TOP = "top-down three-quarter view seen slightly from above"

# key: (method, description, gen_w, gen_h, palette)   method: bf = bitforge (transparent), map = /map-objects
SPEC = {
    # ---- item icons (32 -> 16) and big versions (48 -> 24)
    "i_vine_whip": ("bf", f"a coiled green magic vine whip with small leaves, a leafy wrapped wooden handle, {ICON}", 32, 32, ""),
    "i_spirit_lantern": ("bf", f"a small brass lantern with a glowing blue spirit flame inside, carry handle on top, {ICON}", 32, 32, ""),
    "i_titan_gloves": ("bf", f"a pair of heavy grey stone gauntlets with gold trim and gold knuckle plates, {ICON}", 32, 32, ""),
    "i_ember_boots": ("bf", f"a pair of red-orange leather boots with glowing ember flames at the soles, {ICON}", 32, 32, ""),
    "i_feather_cloak": ("bf", f"a flowing cloak made of white and pale blue feathers, {ICON}", 32, 32, ""),
    "i_dungeon_map": ("bf", f"a rolled-up parchment map scroll tied with a red ribbon, {ICON}", 32, 32, ""),
    "i_finder": ("bf", f"a round gold compass amulet with a glowing cyan crystal in the centre and a needle, {ICON}", 32, 32, ""),
    "i_small_key": ("bf", f"a single small silver key, simple round bow, {ICON}", 32, 32, ""),
    "i_big_key": ("bf", f"a large ornate gold key with a red gem set in its bow, {ICON}", 32, 32, ""),
    "i_lore_tablet_icon": ("bf", f"a small grey stone tablet with carved rune lines, rounded top, {ICON}", 32, 32, ""),
    "b_vine_whip": ("bf", f"a coiled green magic vine whip with small leaves, a leafy wrapped wooden handle, {ICON}", 48, 48, ""),
    "b_spirit_lantern": ("bf", f"a brass lantern with a glowing blue spirit flame inside, carry handle on top, {ICON}", 48, 48, ""),
    "b_titan_gloves": ("bf", f"a pair of heavy grey stone gauntlets with gold trim and gold knuckle plates, {ICON}", 48, 48, ""),
    "b_ember_boots": ("bf", f"a pair of red-orange leather boots with glowing ember flames at the soles, {ICON}", 48, 48, ""),
    "b_feather_cloak": ("bf", f"a flowing cloak made of white and pale blue feathers, {ICON}", 48, 48, ""),
    "b_dungeon_map": ("bf", f"a rolled-up parchment map scroll tied with a red ribbon, {ICON}", 48, 48, ""),
    "b_finder": ("bf", f"a round gold compass amulet with a glowing cyan crystal in the centre and a needle, {ICON}", 48, 48, ""),
    "b_big_key": ("bf", f"a large ornate gold key with a red gem set in its bow, {ICON}", 48, 48, ""),
    # ---- dungeon objects (map-objects, ~2x target)
    "big_chest": ("map", f"two large ornate treasure chests side by side on a plain background: on the left a big CLOSED chest, on the right the SAME big chest OPEN with its lid flipped up and gold light glowing inside; red lacquered wood with heavy shiny gold metal bands, gold corners and a big gold lock plate, {TOP}, bold thick black outline, {STYLE}", 192, 72, "none"),
    "whip_post": ("map", f"a short thick wooden post standing upright, a big shiny brass ring attached to the top of the post, dark iron bands around the post, {TOP}, {STYLE}", 32, 52, "none"),
    "gap_post": ("map", f"a short thick old weathered grey wooden post standing upright, cracked wood with green moss, a tarnished brass ring attached to the top, {TOP}, {STYLE}", 32, 52, "none"),
    "boulder": ("map", f"a single heavy round grey boulder rock, cracks and highlights, {TOP}, {STYLE}", 44, 40, "theme5_wall"),
    "big_boulder": ("map", f"one huge round grey boulder rock blocking a path, deep cracks, a little green moss on top, {TOP}, {STYLE}", 96, 88, "none"),
    # pairs: intact/broken (or up/down) in ONE image so they match
    "pot": ("map", f"two clay pots side by side on a plain background: on the left an intact round terracotta clay pot jar with a wide body and short neck, on the right the SAME pot smashed into a few broken terracotta shards lying flat on the floor, {TOP}, {STYLE}", 96, 40, "none"),
    "crate": ("map", f"two wooden crates side by side on a plain background: on the left an intact sturdy square wooden crate box with plank boards and dark iron corner braces, on the right the SAME crate smashed into splintered broken planks lying flat on the floor, {TOP}, {STYLE}", 112, 44, "none"),
    "floor_switch": ("map", f"two square grey stone floor pressure plate switches side by side, seen from directly above, flat on the floor: on the left the switch with its square button raised up, on the right the same switch with the button pressed down flush, {STYLE}", 80, 36, "theme5_wall"),
    "crystal_switch": ("map", f"a round glowing orange crystal orb sitting on a short grey stone pedestal, dungeon crystal switch, {TOP}, {STYLE}", 32, 48, "none"),
    "elem_crystal": ("map", f"a tall pointed pale white-grey crystal shard standing upright in a small carved dark grey stone base, unlit, {TOP}, {STYLE}", 32, 52, "none"),
    "ice_block": ("map", f"a square block of solid pale blue ice, translucent cube with white frosty highlights on the top face, {TOP}, {STYLE}", 48, 48, "none"),
    "lore_tablet": ("map", f"an upright engraved grey stone tablet with a rounded top, carved lines of ancient runes, standing on the floor, {TOP}, {STYLE}", 36, 48, "theme5_wall"),
    "lock_door_small": ("map", f"a locked dungeon door in a stone wall, front view, heavy dark wooden door under a stone arch with a big iron lock plate and a black keyhole in the middle, {STYLE}", 96, 48, "none"),
    "lock_door_big": ("map", f"a big locked dungeon boss door in a stone wall, front view, heavy iron-banded dark door under a stone arch with a large ornate gold lock with a red gem in the middle, {STYLE}", 96, 48, "none"),
    "peg_block": ("map", f"a square solid stone barrier block seen from above, smooth bevelled top face, bright orange colour, {TOP}, {STYLE}", 48, 48, "none"),
    # ---- terrain overlays
    "pit": ("map", f"a square dark bottomless pit hole in a stone floor, black void, crumbling stone edges, seen from directly above, {STYLE}", 48, 48, "none"),
    "lava": ("bf", "a seamless square tile of bubbling molten orange-red lava, bright yellow cracks, top-down, SNES Zelda style texture", 48, 48, ""),
    "thorns": ("map", f"a dense wall of dark green thorny bramble vines with sharp thorns, blocking a path, {TOP}, {STYLE}", 48, 48, "none"),
}


# second-attempt prompts (tag "b"): used when the first generation was clearly wrong
RETRY = {
    "lock_door_small": f"a wide low locked dungeon doorway in a stone wall, front view, the doorway is twice as wide as it is tall, flat stone lintel on top, a wide heavy dark wooden double door filling the opening with a big iron lock plate and a black keyhole in the middle, fills the whole image width, {STYLE}",
    "lock_door_big": f"a wide low big locked dungeon boss doorway in a stone wall, front view, the doorway is twice as wide as it is tall, flat carved stone lintel on top, a wide heavy iron-banded dark double door filling the opening with a large ornate gold padlock with a red gem in the middle, fills the whole image width, {STYLE}",
    "thorns": f"a tangled clump of brown thorny bramble briar vines covered in many long sharp pale thorns, only a few small dark green leaves, a prickly barrier, square shape, {TOP}, {STYLE}",
    "b_big_key": f"only one single large ornate gold key, diagonal, with a red gem set in its round bow, {ICON}",
    "b_feather_cloak": f"a hooded cape cloak seen from the back, hanging straight down, made of layered white and pale blue feathers, cape shape, {ICON}",
    "i_feather_cloak": f"a hooded cape cloak seen from the back, hanging straight down, made of layered white and pale blue feathers, cape shape, {ICON}",
    "b_titan_gloves": f"two big chunky gauntlet gloves side by side, fingers pointing up, made of grey stone blocks with gold cuffs and gold knuckle plates, {ICON}",
}


RETRY2 = {  # third (last) attempt, tag "c"
    "i_feather_cloak": f"a folded white cape with a gold clasp at the collar, the cape is covered in rows of white and light blue bird feathers, simple bell-shaped silhouette, {ICON}",
}


def b64(path):
    return {"type": "base64", "base64": base64.b64encode(Path(path).read_bytes()).decode()}


def log(msg):
    with _lock, USAGE.open("a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def _gen_once(key, tag, desc_override=None, init=None, strength=300):
    method, desc, w, h, pal = SPEC[key]
    desc = desc_override or (RETRY2.get(key) if tag == "c" else None) or (RETRY.get(key) if tag != "a" else None) or desc
    d = GEN / f"relic_{key}"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{tag}.png"
    if method == "bf":
        body = {"description": desc, "image_size": {"width": w, "height": h}, "no_background": True,
                "outline": "single color black outline", "shading": "medium shading", "detail": "medium detail",
                "view": "high top-down",
                "negative_description": "background, floor, text, frame, blurry, multiple objects"}
        r = call("POST", "/create-image-bitforge", body)
        save_b64(r["image"], out)
    else:
        body = {"description": desc, "image_size": {"width": w, "height": h}, "view": "high top-down",
                "outline": "single color outline", "shading": "medium shading", "detail": "medium detail"}
        if pal and pal != "none":
            body["color_image"] = b64(PAL / f"{pal}.png")
        if init:
            body["init_image"] = b64(init)
            body["init_image_strength"] = int(strength)
        r = call("POST", "/map-objects", body)
        j = wait_job(r["background_job_id"]) if r.get("background_job_id") else r
        (d / f"{tag}.json").write_text(json.dumps(j, default=str)[:3000])
        lr = j.get("last_response") or {}
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
                download(urls[0][1], out)
    log(f"{key} {tag} {method} {w}x{h}")
    print("saved", out, Image.open(out).size, flush=True)
    return out


def gen(key, tag="a", **kw):
    for attempt in range(6):
        try:
            return _gen_once(key, tag, **kw)
        except SystemExit as e:
            msg = str(e)
            if "429" in msg and attempt < 5:
                time.sleep(20 + 10 * attempt)
                continue
            print("FAILED", key, tag, msg[:300], flush=True)
            return None


def gen_many(keys, tag="a", **kw):
    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(lambda k: gen(k, tag, **kw), keys))


# ----------------------------------------------------------------------------- packing helpers
def raw(key, tag="a"):
    return clean(Image.open(GEN / f"relic_{key}" / f"{tag}.png").convert("RGBA"))


def crop(im):
    return im.crop(im.getbbox())


def scale_to(im, f):
    """Downscale by factor f: exact NEAREST for (near-)integer factors, mode-downscale otherwise."""
    if abs(f - round(f)) < 0.08 and round(f) >= 1:
        f = round(f)
        return im.resize((max(1, round(im.width / f)), max(1, round(im.height / f))), Image.NEAREST)
    return mode_downscale(im, max(1, round(im.width / f)), max(1, round(im.height / f)))


def fit_im(im, cw, ch, base=2, centre=False, maxw=None, maxh=None):
    im = crop(im)
    maxw = maxw or cw
    maxh = maxh or (ch - base)
    f = max(im.width / maxw, im.height / maxh, 1.0)
    im = crop(scale_to(im, f))
    return place(im, cw, ch, base, centre)


def place(im, cw, ch, base=2, centre=False):
    cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    y = (ch - im.height) // 2 if centre else ch - base - im.height
    cell.alpha_composite(im, ((cw - im.width) // 2, max(0, y)))
    return cell


def save_sheet(name, rows, cw, ch, fps=None):
    """rows: list of (row_name, [frames]). Writes sheet + manifest entry."""
    cols = max(len(fr) for _, fr in rows)
    sheet = Image.new("RGBA", (cw * cols, ch * len(rows)), (0, 0, 0, 0))
    anims = {}
    for ri, (rn, fr) in enumerate(rows):
        for fi, im in enumerate(fr):
            sheet.alpha_composite(im, (fi * cw, ri * ch))
        anims[rn] = {"row": ri, "frames": len(fr), "fps": (fps or {}).get(rn, 4 if len(fr) > 1 else 1)}
    SHEETS.mkdir(exist_ok=True)
    sheet.save(SHEETS / f"{name}.png")
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
    m["sprites"][name] = {"file": f"{name}.png", "cell": [cw, ch], "anims": anims}
    m["sprites"] = dict(sorted(m["sprites"].items()))
    MANIFEST.write_text(json.dumps(m, indent=2))
    print("packed", name, sheet.size, list(anims))


# ----------------------------------------------------------------------------- local recolour / derive helpers
import colorsys  # noqa: E402


def _hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)


def _rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v)))
    return (round(r * 255), round(g * 255), round(b * 255), 255)


def recolor(im, pred, fn):
    im = im.copy()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            c = px[x, y]
            if c[3] and pred(x, y, c):
                px[x, y] = fn(c)
    return im


def largest_component(im):
    from objects import _components
    px = im.load()
    comps = list(_components(im.width, im.height, lambda x, y: px[x, y][3] > 0))
    keep = set(max(comps, key=len))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    o = out.load()
    for p in keep:
        o[p] = px[p]
    return out


def halves(key, tag, n=2):
    """Split a pair image into n equal-width halves sharing ONE crop window (no jump when swapping)."""
    im = raw(key, tag)
    hw = im.width // n
    parts = [im.crop((i * hw, 0, (i + 1) * hw, im.height)) for i in range(n)]
    boxes = [p.getbbox() for p in parts]
    win = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    return [p.crop(win) for p in parts]


def widen(im, tw):
    """Make a symmetric door wider by repeating plank columns at 1/3 and 2/3 of its width."""
    while im.width < tw:
        need = tw - im.width
        xs = [im.width // 3, im.width - im.width // 3 - 1]
        cols = []
        for i, x in enumerate(xs):
            if i == 1 and len(cols) * 1 >= need:
                break
            cols.append(x)
        out = Image.new("RGBA", (im.width + len(cols), im.height), (0, 0, 0, 0))
        sx = dx = 0
        for x in sorted(cols):
            out.alpha_composite(im.crop((sx, 0, x + 1, im.height)), (dx, 0))
            dx += x + 1 - sx
            out.alpha_composite(im.crop((x, 0, x + 1, im.height)), (dx, 0))
            dx += 1
            sx = x + 1
        out.alpha_composite(im.crop((sx, 0, im.width, im.height)), (dx, 0))
        im = out
    return im


ELEM = {  # hue, saturation for element crystals
    "fire": (0.02, 0.85), "ice": (0.53, 0.65), "storm": (0.14, 0.80), "earth": (0.30, 0.70),
}


def elem_crystal(elem, lit):
    """Recolour the pale generated crystal into an element colour (dim or lit + glow ring)."""
    base = crop(raw("elem_crystal", "a"))
    base = crop(scale_to(base, 2))
    hue, sat = ELEM[elem]
    # crystal pixels: brighter than the dark stone base and in the upper part
    def is_cry(x, y, c):
        h, s, v = _hsv(c)
        return v > 0.42 and y < base.height - 3
    def tint(c):
        h, s, v = _hsv(c)
        if lit:
            return _rgb(hue, sat * (1.15 - v * 0.6), 0.55 + v * 0.5)
        return _rgb(hue, sat * 0.45, 0.25 + v * 0.45)
    im = recolor(base, is_cry, tint)
    cell = place(im, 16, 28)
    if lit:  # 1 px glow halo around the crystal part + sparkles
        px = cell.load()
        src = cell.copy().load()
        glow = _rgb(hue, sat * 0.55, 1.0)
        top = 28 - 2 - im.height
        for y in range(28):
            for x in range(16):
                if src[x, y][3] == 0 and y < top + im.height - 4:
                    if any(0 <= x + dx < 16 and 0 <= y + dy < 28 and src[x + dx, y + dy][3]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        px[x, y] = glow
        for sx, sy in ((2, top + 3), (13, top + 7), (3, top + 12)):
            if 0 <= sy < 28 and px[sx, sy][3] == 0:
                px[sx, sy] = (255, 255, 240, 255)
    return cell


def peg_down(up):
    """Lowered barrier peg: flat tile in the block's colours (ALttP style outline square)."""
    cols = sorted({c for c in up.getdata() if c[3]}, key=lambda c: sum(c[:3]))
    sat = [c for c in cols if _hsv(c)[1] > 0.35]
    dark, mid, light = sat[len(sat) // 6], sat[len(sat) // 2], sat[-max(1, len(sat) // 6)]
    im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([2, 2, 21, 21], fill=(24, 20, 28, 255))
    d.rectangle([3, 3, 20, 20], outline=light, fill=dark)
    d.rectangle([5, 5, 18, 18], outline=mid)
    for i in range(6, 18, 4):
        d.point((i, 11), fill=mid)
        d.point((i + 2, 13), fill=mid)
    return im


def lava_frames(n=4):
    """Seamless 24x24 bubbling lava, palette taken from the generated lava; animated by phase."""
    import math
    src = raw("lava", "a")
    pal = sorted({c[:3] for c in src.getdata() if c[3] and _hsv(c)[1] > 0.3}, key=lambda c: sum(c))
    # 5-step ramp from the generated colours (dark red -> yellow)
    ramp = [pal[int(i * (len(pal) - 1) / 4)] for i in range(5)]
    ramp[0] = (120, 28, 16)
    frames = []
    T = 2 * math.pi / 24
    bubbles = [(5, 6), (16, 4), (11, 15), (20, 18), (3, 19)]
    for f in range(n):
        ph = 2 * math.pi * f / n
        im = Image.new("RGBA", (24, 24))
        px = im.load()
        for y in range(24):
            for x in range(24):
                v = (math.sin(T * x * 2 + ph) + math.sin(T * y * 2 - ph) +
                     math.sin(T * (x + y) + ph * 2) * 0.8 + math.sin(T * (x - 2 * y) * 1 + ph) * 0.6)
                k = int((v + 3.4) / 6.8 * 4.99)
                px[x, y] = ramp[max(0, min(4, k))] + (255,)
        for i, (bx, by) in enumerate(bubbles):  # bubble grows/pops on a staggered cycle
            s = (f + i) % n
            if s == 1:
                px[bx, by] = ramp[4] + (255,)
            elif s == 2:
                for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    px[(bx + dx) % 24, (by + dy) % 24] = ramp[4] + (255,)
                px[bx, by] = (255, 248, 200, 255)
            elif s == 3:
                for dx, dy in ((-1, 0), (2, 0), (0, -1), (1, 2)):
                    px[(bx + dx) % 24, (by + dy) % 24] = ramp[3] + (255,)
        frames.append(im)
    return frames


def pit_tile():
    im = fit_im(raw("pit", "a"), 24, 24, base=0, maxw=24, maxh=24)
    im = Image.new("RGBA", (24, 24), (0, 0, 0, 0)) if im.getbbox() is None else im
    px = im.load()
    bb = im.getbbox()
    x0, y0, x1, y1 = bb
    # deeper ALttP-style depth bands under the top lip
    bands = [(52, 46, 58), (34, 30, 40), (20, 18, 26)]
    for i, col in enumerate(bands):
        y = y0 + 2 + i
        for x in range(x0 + 2, x1 - 2):
            if px[x, y][3] and sum(px[x, y][:3]) < 90:
                px[x, y] = col + (255,)
    return im


# ----------------------------------------------------------------------------- build everything
ICONS = ["vine_whip", "spirit_lantern", "titan_gloves", "ember_boots", "feather_cloak", "dungeon_map",
         "finder", "small_key", "big_key", "lore_tablet_icon"]
BIG = ["vine_whip", "spirit_lantern", "titan_gloves", "ember_boots", "feather_cloak", "dungeon_map", "finder", "big_key"]
BIG_TAG = {"titan_gloves": "b", "feather_cloak": "b", "big_key": "b"}


def bf_raw(key, tag="a"):
    im = Image.open(GEN / f"relic_{key}" / f"{tag}.png").convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return largest_component(im) if key == "b_big_key" else im


def build_items():
    from itempack import shrink, cellify
    rows = []
    for k in ICONS:
        src = bf_raw("i_feather_cloak", "c") if k == "feather_cloak" else bf_raw(f"i_{k}")
        rows.append((k, [cellify(shrink(src, 15 if k not in ("small_key",) else 13))]))
    save_sheet("relic_items", rows, 16, 16)
    rows = []
    for k in BIG:
        # The 48 px generations came out mushy (and the big key twice drew two keys), so the
        # big icons use the same clean 32 px generations as the small ones, at ~1:1 (fit 22 px).
        # Feather cloak: third 32 px attempt ("c") is the one used (a = ring, b = angel).
        src = bf_raw("i_feather_cloak", "c") if k == "feather_cloak" else bf_raw(f"i_{k}")
        rows.append((k, [place(shrink(src, 22), 24, 24, base=1)]))
    save_sheet("relic_items_big", rows, 24, 24)


def build_objects():
    # big chest pair -> shared window, exact /2
    for name, part in zip(("obj_big_chest_closed", "obj_big_chest_open"), halves("big_chest", "a")):
        save_sheet(name, [("idle", [place(scale_to(part, 2), 40, 32)])], 40, 32)
    for name, key in (("obj_whip_post", "whip_post"), ("obj_gap_post", "gap_post")):
        save_sheet(name, [("idle", [place(crop(scale_to(crop(raw(key)), 2)), 16, 26)])], 16, 26)
    save_sheet("obj_boulder", [("idle", [place(crop(scale_to(crop(raw("boulder")), 2)), 22, 20)])], 22, 20)
    save_sheet("obj_big_boulder", [("idle", [fit_im(raw("big_boulder"), 48, 44)])], 48, 44)
    p_up, p_br = halves("pot", "a")
    save_sheet("obj_pot", [("idle", [place(crop(scale_to(p_up, 2)), 16, 18)])], 16, 18)
    save_sheet("obj_pot_broken", [("idle", [place(crop(scale_to(p_br, 2)), 16, 18, base=4)])], 16, 18)
    c_up, c_br = halves("crate", "a")
    save_sheet("obj_crate", [("idle", [place(crop(scale_to(c_up, 2)), 20, 20)])], 20, 20)
    save_sheet("obj_crate_broken", [("idle", [place(crop(scale_to(c_br, 2)), 20, 20, base=3)])], 20, 20)
    # floor switch: only the 'up' half is used; 'down' is derived (button area darkened, highlight removed)
    up = fit_im(halves("floor_switch", "a")[0], 16, 16, base=0, maxw=15, maxh=15, centre=True)
    bb = up.getbbox()
    cx0, cy0 = bb[0] + (bb[2] - bb[0]) // 4, bb[1] + (bb[3] - bb[1]) // 4
    cx1, cy1 = bb[2] - (bb[2] - bb[0]) // 4, bb[3] - (bb[3] - bb[1]) // 4
    down = recolor(up, lambda x, y, c: cx0 <= x < cx1 and cy0 <= y < cy1,
                   lambda c: (int(c[0] * 0.45), int(c[1] * 0.45), int(c[2] * 0.5), 255))
    save_sheet("obj_floor_switch_up", [("idle", [up])], 16, 16)
    save_sheet("obj_floor_switch_down", [("idle", [down])], 16, 16)
    # crystal switch: generated orange; blue by hue swap of the warm orb pixels
    cs = place(crop(scale_to(crop(raw("crystal_switch")), 2)), 16, 24)
    warm = lambda x, y, c: _hsv(c)[1] > 0.25 and (_hsv(c)[0] < 0.17 or _hsv(c)[0] > 0.95)  # noqa: E731
    blue = recolor(cs, warm, lambda c: _rgb(0.60 - (_hsv(c)[0] if _hsv(c)[0] < 0.5 else 0) * 0.3,
                                            _hsv(c)[1] * 0.9, min(1, _hsv(c)[2] * 1.02)))
    save_sheet("obj_crystal_switch_orange", [("idle", [cs])], 16, 24)
    save_sheet("obj_crystal_switch_blue", [("idle", [blue])], 16, 24)
    # barrier pegs
    pu = fit_im(raw("peg_block"), 24, 24, base=0, maxw=24, maxh=24)
    pb = recolor(pu, lambda x, y, c: _hsv(c)[1] > 0.2,
                 lambda c: _rgb(0.60 + (_hsv(c)[0] - 0.08) * 0.5, _hsv(c)[1] * 0.85, _hsv(c)[2] * 0.95))
    save_sheet("obj_block_orange_up", [("idle", [pu])], 24, 24)
    save_sheet("obj_block_blue_up", [("idle", [pb])], 24, 24)
    save_sheet("obj_block_orange_down", [("idle", [peg_down(pu)])], 24, 24)
    save_sheet("obj_block_blue_down", [("idle", [peg_down(pb)])], 24, 24)
    for e in ELEM:
        save_sheet(f"obj_crystal_{e}", [("idle", [elem_crystal(e, False)]), ("lit", [elem_crystal(e, True)])], 16, 28)
    save_sheet("obj_ice_block", [("idle", [fit_im(raw("ice_block"), 24, 24, base=0, maxw=24, maxh=24)])], 24, 24)
    save_sheet("obj_lore_tablet", [("idle", [place(crop(scale_to(crop(raw("lore_tablet")), 2)), 18, 24)])], 18, 24)
    for name, key, tag in (("obj_lock_door_small", "lock_door_small", "b"), ("obj_lock_door_big", "lock_door_big", "a")):
        d = crop(raw(key, tag))
        d = crop(scale_to(d, d.height / 24))
        save_sheet(name, [("idle", [place(widen(d, 48), 48, 24, base=0)])], 48, 24)
    # terrain overlays
    save_sheet("tile_pit", [("idle", [pit_tile()])], 24, 24)
    save_sheet("tile_lava", [("idle", lava_frames())], 24, 24, fps={"idle": 4})
    save_sheet("tile_thorns", [("idle", [fit_im(raw("thorns", "b"), 24, 24, base=0, maxw=24, maxh=24)])], 24, 24)


def build():
    build_items()
    build_objects()


def preview():
    m = json.loads(MANIFEST.read_text())["sprites"]
    mm = json.loads((SHEETS / "manifest.json").read_text())["sprites"]["mage_fire"]
    hero = Image.open(SHEETS / "mage_fire.png").convert("RGBA").crop((0, 0, *mm["cell"]))
    tiles = []
    for name, e in m.items():
        sh = Image.open(SHEETS / e["file"]).convert("RGBA")
        cw, ch = e["cell"]
        frames = []
        for rn, a in e["anims"].items():
            for i in range(a["frames"]):
                frames.append(sh.crop((i * cw, a["row"] * ch, (i + 1) * cw, (a["row"] + 1) * ch)))
        flat = name.startswith("tile_") or "_down" in name or "switch_" in name and "floor" in name
        W = len(frames) * (cw + 4) + 4
        if flat:
            bg = floor_patch(5, ((W + 23) // 24) * 24 + 24, ((ch + 8 + 23) // 24) * 24)
        else:
            bg = checker(W, ch + 8)
        for i, f in enumerate(frames):
            bg.alpha_composite(f, (4 + i * (cw + 4), 4))
        label = name if len(e["anims"]) == 1 else name + " (" + "/".join(e["anims"]) + ")"
        tiles.append((label, bg.resize((bg.width * 2, bg.height * 2), Image.NEAREST)))
    # scale reference: mage on the dungeon floor next to the big chest and a block
    ref = floor_patch(5, 120, 48)
    ref.alpha_composite(hero, (6, 48 - mm["cell"][1] - 2))
    for n, x in (("obj_big_chest_closed", 34), ("obj_block_orange_up", 78)):
        e = m[n]
        f = Image.open(SHEETS / e["file"]).convert("RGBA").crop((0, 0, *e["cell"]))
        ref.alpha_composite(f, (x, 48 - e["cell"][1] - (2 if "chest" in n else 0)))
    tiles.insert(0, ("mage_fire for scale", ref.resize((240, 96), Image.NEAREST)))
    W, x, y, rowh, pos = 1400, 0, 0, 0, []
    for name, t in tiles:
        w = max(t.width, len(name) * 6 + 4)
        if x + w > W:
            x, y, rowh = 0, y + rowh + 22, 0
        pos.append((name, t, x, y))
        x += w + 12
        rowh = max(rowh, t.height)
    out = Image.new("RGBA", (W, y + rowh + 22), (32, 32, 40, 255))
    d = ImageDraw.Draw(out)
    for name, t, x, y in pos:
        out.alpha_composite(t, (x, y + 14))
        d.text((x + 2, y), name, fill=(240, 240, 240, 255))
    out.save(GEN / "preview_relics_all.png")
    print("wrote preview", out.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen":
        gen_many(a[1].split(","), a[2] if len(a) > 2 else "a")
    elif a[0] == "build":
        build()
    elif a[0] == "preview":
        preview()

"""World structure / object art for Elemental Legends (uses pixellab.py; never touches the key).

python objects.py gen <name> <tag> [method]   -> generated/obj_<name>/<tag>.png (one generation)
python objects.py pack <name> <tag>[,<tag>...] -> sheets/<name>.png + sheets/manifest_objects.json entry
python objects.py preview                      -> generated/preview_objects_all.png
"""
import base64
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixellab import call, wait_job, download, save_b64, find_urls, find_b64, GEN  # noqa: E402

ART = GEN.parent
PAL = GEN / "palettes"
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest_objects.json"
STYLE = "SNES Zelda A Link to the Past style, rich natural colors, not neon"
NEG = "background, ground, grass, floor tiles, text, frame, border, neon colors, blurry"
USAGE = GEN / "objects_usage.log"

# name: (description, gen_w, gen_h, palette, cell_w, cell_h, scale)
# gen size is ~2x the on-screen target; scale = downscale factor applied with NEAREST.
BLD = "fantasy dungeon entrance building, front view facing the camera, a dark open doorway at the bottom centre, whole building visible"
CAVE = ("cave entrance in a wide low rocky hillside mound, top-down three-quarter view, the whole mound visible, "
        "a large dark black arched cave mouth opening at the bottom centre of the mound, front facing the camera")
OBJ = {
    "bld_1": (f"overgrown shrine temple, {BLD}, mossy green-grey stone blocks covered in leafy ivy vines and tree roots, small stepped roof, {STYLE}",
              192, 240, "theme4_wall", 96, 120, 2),
    "bld_2": (f"underground crypt mausoleum, {BLD}, grey stone mausoleum with a carved skull relief above the doorway, stone stairs leading down into the dark doorway, {STYLE}",
              192, 232, "theme5_wall", 96, 116, 2),
    "bld_3": (f"ruined castle keep, {BLD}, wide square ruined castle keep of tan sandstone blocks, broken crenellated battlements on top, one crumbled corner, a tattered red banner hanging above the doorway, no cast shadow, {STYLE}",
              192, 256, "theme6_wall", 96, 128, 2),
    "bld_4": (f"dragon fortress, {BLD}, black and dark red volcanic stone fortress with sharp black spikes on the roof, glowing orange lava-lit windows, {STYLE}",
              192, 256, "theme7_wall", 96, 128, 2),
    "bld_5": (f"forgotten sanctuary temple, {BLD}, blue-white marble temple with white columns at the front and a pale blue dome roof, {STYLE}",
              192, 248, "theme8_wall", 96, 124, 2),
    "bld_6": (f"dark wizard tower, {BLD}, tall narrow purple-black stone spire with a pointed roof, small glowing violet windows, {STYLE}",
              192, 300, "theme9_wall", 96, 150, 2),
    "obj_monolith": (f"tall ancient grey stone monolith obelisk with carved runes, weathered, not glowing, standing upright, {STYLE}",
                     96, 192, "theme1_deco", 48, 96, 2),
    "obj_standing_stone": (f"small weathered grey standing stone with green moss patches, upright menhir, {STYLE}",
                           48, 68, "theme1_deco", 24, 34, 2),
    "obj_cottage": (f"cosy small merchant cottage house, front view, cream plaster walls with wooden beams, red tiled roof, wooden front door at the bottom centre, a small window, {STYLE}",
                    192, 160, "cottage", 96, 80, 2),
    "obj_inn": (f"cosy one-storey village inn tavern, front view, wide low building, grey fieldstone base wall with dark timber frame and cream plaster above, golden-brown thatched straw roof, warm glowing yellow lit windows, wooden front door at the bottom centre, a wooden sign with a beer mug hanging from a bracket beside the door, {STYLE}",
                192, 160, "cottage", 96, 80, 2),
    "obj_cave_0": (f"{CAVE}, mossy grey-green boulders, green ferns and grass tufts growing on top of the hill, {STYLE}",
                   192, 144, "theme0_deco", 96, 72, 2),
    "obj_cave_1": (f"{CAVE}, big rounded hill of piled cold grey stone boulders, the arched cave mouth is small, only one third of the hill width, a few scattered white bones and a skull on the ground in front of the entrance, a twisted leafless dead tree root creeping over the rocks on top, {STYLE}",
                   192, 144, "theme1_deco", 96, 72, 2),
    "obj_cave_2": (f"{CAVE}, muddy brown swamp rock, dripping green hanging moss over the entrance, clumps of swamp reeds at the base, {STYLE}",
                   192, 144, "theme2_deco", 96, 72, 2),
    "obj_cave_3": (f"{CAVE}, rocky hill made of many jagged dark grey basalt boulders and hexagonal rock columns with bright grey highlights on their top faces, a few thin glowing orange lava cracks between the rocks, the arched cave mouth is small, only one third of the hill width, black inside with a soft orange glow at the back, {STYLE}",
                   192, 144, "theme3_deco", 96, 72, 2),
    "obj_chest_closed": (f"classic Zelda treasure chest, closed, top-down three-quarter view seen slightly from above, rich brown wooden planks, bright shiny gold brass metal bands along the edges and a big gold lock plate on the front, curved lid, bold thick black outline, {STYLE}",
                         52, 44, "none", 26, 26, 2),
    "obj_chest_open": (f"open empty-looking treasure chest with its lid flipped fully open and standing upright behind the box, the inside of the box visible and filled with shining gold coins glowing warm yellow, top-down three-quarter view seen slightly from above, rich brown wooden planks, bright shiny gold brass metal bands, warm golden glow and gold coins inside the open chest, bold thick black outline, {STYLE}",
                       52, 44, "none", 26, 26, 2),
    "obj_notice_board": (f"wooden village notice board standing on two wooden posts, small roof plank on top, several pinned paper notes on the board, front view, {STYLE}",
                         60, 68, "cottage", 30, 34, 2),
    "obj_shrine_pedestal": (f"short carved grey stone pedestal pillar, wide square top slab and wide base, carved decorative band in the middle, empty flat top, light grey stone, {STYLE}",
                            48, 40, "theme1_deco", 24, 20, 2),
    "obj_fruit_tree": (f"round leafy apple tree with many red apples, short brown trunk, {STYLE}",
                       68, 80, "fruit", 34, 40, 2),
    "obj_fruit_tree_bare": (f"round leafy green tree without fruit, short brown trunk, {STYLE}",
                            68, 80, "theme0_deco", 34, 40, 2),
    "obj_tombstone": (f"weathered grey gravestone with a carved cross on it, rounded top, a little moss at the base, {STYLE}",
                      40, 52, "theme1_deco", 20, 26, 2),
    "obj_brazier": (f"cold extinguished grey stone brazier, wide stone bowl filled with dark grey ash and black charcoal lumps, on a short thick stone pedestal, completely unlit, dark grey stone, {STYLE}",
                    44, 48, "theme5_wall", 22, 24, 2),
    "obj_push_block": (f"square carved grey stone push block seen from above, a rune carved on top, heavy dungeon block, {STYLE}",
                       48, 48, "theme5_wall", 24, 24, 2),
    "obj_lever_off": (f"dungeon lever switch, small square dark iron base plate on the floor, a thick chunky wooden lever handle tilted diagonally up and to the left, with a big round iron ball at the top end of the handle, bold simple shape, {STYLE}",
                      40, 48, "lever", 20, 24, 2),
    "obj_lever_on": (f"dungeon floor lever, wooden handle tilted to the right, iron base plate, {STYLE}",
                     40, 48, "lever", 20, 24, 2),
}


def b64(path):
    return {"type": "base64", "base64": base64.b64encode(Path(path).read_bytes()).decode()}


def extra_palettes():
    """Palettes that are not in terrain_palette.py (written once, own files)."""
    from terrain_palette import swatch, GREY, WOOD, OUTLINE, CANOPY, GRASS, TAN, DIRT
    RED_ROOF = [(200, 72, 56), (160, 48, 40), (112, 32, 32)]
    PLASTER = [(240, 228, 196), (208, 192, 152)]
    APPLE = [(232, 64, 48), (176, 32, 32), (248, 160, 120)]
    sets = {
        "cottage": RED_ROOF + PLASTER + WOOD + GREY[1:4] + [(40, 36, 44), (16, 20, 24)] + DIRT[2:],
        "fruit": CANOPY + GRASS[2:5] + APPLE + WOOD + OUTLINE,
        "lever": GREY + WOOD + [(200, 176, 96), (40, 36, 44), (16, 20, 24)],
    }
    for k, cols in sets.items():
        p = PAL / f"{k}.png"
        if not p.exists():
            swatch(cols, p)


def gen(name, tag, method="map", view="high top-down", init="", strength="300"):
    """init: optional path (relative to generated/) of an image to start from (keeps a pair consistent)."""
    extra_palettes()
    desc, w, h, pal, *_ = OBJ[name]
    d = GEN / f"obj_{name}"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{tag}.png"
    if method == "map":
        body = {"description": desc, "image_size": {"width": w, "height": h}, "view": view,
                "outline": "single color outline" if name.startswith("obj_chest") else "selective outline",
                "shading": "medium shading", "detail": "medium detail",
                "color_image": b64(PAL / f"{pal}.png") if pal != "none" else None}
        if pal == "none" or "nopal" in tag:
            del body["color_image"]
        if init:
            body["init_image"] = b64(GEN / init)
            body["init_image_strength"] = int(strength)
        r = call("POST", "/map-objects", body)
        j = wait_job(r["background_job_id"]) if r.get("background_job_id") else r
        (d / f"{tag}.json").write_text(json.dumps(j, default=str)[:4000])
        imgs = list(find_b64(j))
        lr = j.get("last_response") or {}
        if isinstance(lr.get("image"), str):
            out.write_bytes(base64.b64decode(lr["image"]))
        elif isinstance(lr.get("image"), dict) and "base64" in lr["image"]:
            save_b64(lr["image"], out)
        elif imgs:
            save_b64(imgs[0][1], out)
        else:
            urls = list(find_urls(j))
            if not urls and r.get("object_id"):
                info = call("GET", f"/objects/{r['object_id']}")
                (d / f"{tag}_obj.json").write_text(json.dumps(info, default=str)[:4000])
                urls = list(find_urls(info))
                if not urls:
                    imgs = list(find_b64(info))
                    save_b64(imgs[0][1], out)
            if urls:
                download(urls[0][1], out)
    else:  # bitforge (max 200x200 area)
        body = {"description": desc, "negative_description": NEG, "image_size": {"width": w, "height": h},
                "no_background": True, "outline": "selective outline", "shading": "medium shading",
                "detail": "medium detail", "view": view, "color_image": b64(PAL / f"{pal}.png") if pal != "none" else None}
        r = call("POST", "/create-image-bitforge", body)
        save_b64(r["image"], out)
    with USAGE.open("a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {name} {tag} {method} {w}x{h}\n")
    print("saved", out, Image.open(out).size)


def _near(c, bg, tol):
    return c[3] == 255 and max(abs(c[0] - bg[0]), abs(c[1] - bg[1]), abs(c[2] - bg[2])) <= tol


def _components(W, H, pred):
    """Yield lists of (x, y) of 4-connected components of pixels where pred(x, y)."""
    seen = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            if seen[y * W + x] or not pred(x, y):
                continue
            comp, st = [], [(x, y)]
            seen[y * W + x] = 1
            while st:
                cx, cy = st.pop()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < W and 0 <= ny < H and not seen[ny * W + nx] and pred(nx, ny):
                        seen[ny * W + nx] = 1
                        st.append((nx, ny))
            yield comp


def clean(im, tol=14, min_speck=24):
    """Remove the flat (slightly noisy) opaque background map-objects returns, harden alpha,
    and drop tiny detached specks left over from background noise."""
    from collections import Counter
    im = im.convert("RGBA")
    px = im.load()
    W, H = im.size
    border = [px[x, y] for x in range(W) for y in (0, H - 1)] + [px[x, y] for y in range(H) for x in (0, W - 1)]
    bg, n = Counter(border).most_common(1)[0]
    if bg[3] == 255 and n > len(border) * 0.3:
        # background components touching the border, plus enclosed pockets of >= 6 px
        for comp in _components(W, H, lambda x, y: _near(px[x, y], bg, tol)):
            edge = any(x in (0, W - 1) or y in (0, H - 1) for x, y in comp)
            if edge or len(comp) >= 6:
                for x, y in comp:
                    px[x, y] = (0, 0, 0, 0)
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    comps = list(_components(W, H, lambda x, y: px[x, y][3] > 0))
    if comps:
        big = max(len(c) for c in comps)
        for c in comps:
            if len(c) < min_speck and len(c) < big:
                for x, y in c:
                    px[x, y] = (0, 0, 0, 0)
    return im


def remove_apples(im):
    """Paint red fruit pixels in the canopy with the surrounding leaf colours (bare tree variant)."""
    from collections import Counter
    im = im.copy()
    px = im.load()
    bb = im.getbbox()
    top = bb[1] + int((bb[3] - bb[1]) * 0.75)

    def red(c):
        r, g, b, a = c
        return a > 0 and r > 90 and r > g * 1.6 and r > b * 1.4
    todo = {(x, y) for y in range(bb[1], top) for x in range(im.width) if red(px[x, y])}
    while todo:
        done = set()
        for x, y in todo:
            nb = [px[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= x + dx < im.width and 0 <= y + dy < im.height and (x + dx, y + dy) not in todo]
            nb = [c for c in nb if c[3] > 0 and not red(c)]
            if nb:
                px[x, y] = Counter(nb).most_common(1)[0][0]
                done.add((x, y))
        if not done:
            break
        todo -= done
    return im


def add_glow(im, cx=48, cy=47, r=12):
    """Faint banded orange glow on the dark pixels deep in a cave mouth (obj_cave_3)."""
    im = im.copy()
    px = im.load()
    bands = [(72, 30, 20), (104, 44, 20), (140, 62, 24)]
    for y in range(max(0, cy - r), min(im.height, cy + r)):
        for x in range(max(0, cx - r), min(im.width, cx + r)):
            c = px[x, y]
            if c[3] == 0 or max(c[:3]) >= 40:
                continue
            d = ((x - cx) ** 2 + ((y - cy) * 1.4) ** 2) ** 0.5
            k = 3 - int(d / (r / 3)) - 1
            if k >= 0:
                px[x, y] = bands[k] + (255,)
    return im


def mode_downscale(im, tw, th):
    """Pixel-art friendly downscale to any size: each target pixel takes the most common
    colour of its source block (transparent if the block is mostly transparent)."""
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
            clear = sum(v for k, v in c.items() if k[3] == 0)
            total = sum(c.values())
            if clear * 2 > total:
                continue
            dst[x, y] = max(((v, k) for k, v in c.items() if k[3] > 0))[1]
    return out


def fit(name, tag, mirror=False, src=None):
    """Crop to content, downscale to fit the cell (integer NEAREST when the factor is ~integer,
    otherwise mode-downscale), place centred with the base 2 px above the cell bottom."""
    desc, w, h, pal, cw, ch, sc = OBJ[name]
    im = clean(Image.open(GEN / f"obj_{src or name}" / f"{tag}.png"))
    im = im.crop(im.getbbox())
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    f = max(im.width / cw, im.height / (ch - 2), 1.0)
    if abs(f - round(f)) < 0.08:
        f = round(f)
        im = im.resize((max(1, round(im.width / f)), max(1, round(im.height / f))), Image.NEAREST)
    else:
        im = mode_downscale(im, max(1, round(im.width / f)), max(1, round(im.height / f)))
    im = im.crop(im.getbbox())
    cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    cell.alpha_composite(im, ((cw - im.width) // 2, ch - 2 - im.height))
    return cell


def pack(name, tags):
    desc, w, h, pal, cw, ch, sc = OBJ[name]
    frames = []
    for t in tags:
        src, _, mod = t.partition(":")
        sn, _, st = src.rpartition("/")
        fr = fit(name, st, mirror=(mod == "mirror"), src=sn or None)
        if mod == "glow":
            fr = add_glow(fr)
        if mod == "bare":
            fr = remove_apples(fr)
        frames.append(fr)
    sheet = Image.new("RGBA", (cw * len(frames), ch), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, (i * cw, 0))
    SHEETS.mkdir(exist_ok=True)
    sheet.save(SHEETS / f"{name}.png")
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
    m["sprites"][name] = {"file": f"{name}.png", "cell": [cw, ch],
                          "anims": {"idle": {"row": 0, "frames": len(frames), "fps": 4}}}
    m["sprites"] = dict(sorted(m["sprites"].items()))
    MANIFEST.write_text(json.dumps(m, indent=2))
    print("packed", name, sheet.size)


def pack_chests():
    """Closed/open chest come from ONE generation (pair_nopal.png: closed left, open right) so they match.
    Both halves are cropped with the same window and scaled by the same 2x factor, so swapping never jumps."""
    im = clean(Image.open(GEN / "obj_obj_chest_closed" / "pair_nopal.png"))
    win = (6, 3, 58, 51)  # shared window inside each 64x56 half; chest bottoms are at y=51 in both
    for name, x0 in (("obj_chest_closed", 0), ("obj_chest_open", 64)):
        half = im.crop((x0 + win[0], win[1], x0 + win[2], win[3]))
        half = half.resize((half.width // 2, half.height // 2), Image.NEAREST)
        cw, ch = OBJ[name][4], OBJ[name][5]
        cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cell.alpha_composite(half, ((cw - half.width) // 2, ch - 2 - half.height))
        cell.save(SHEETS / f"{name}.png")
        m = json.loads(MANIFEST.read_text())
        m["sprites"][name] = {"file": f"{name}.png", "cell": [cw, ch],
                              "anims": {"idle": {"row": 0, "frames": 1, "fps": 4}}}
        m["sprites"] = dict(sorted(m["sprites"].items()))
        MANIFEST.write_text(json.dumps(m, indent=2))
        print("packed", name, cell.size, "content", cell.getbbox())


def checker(w, h, s=8):
    im = Image.new("RGBA", (w, h), (200, 200, 200, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=(160, 160, 160, 255))
    return im


def floor_patch(theme, w, h):
    t = Image.open(SHEETS / "terrain" / f"theme{theme}_wall.png").convert("RGBA").crop((0, 0, 24, 24))
    im = Image.new("RGBA", (w, h))
    for y in range(0, h, 24):
        for x in range(0, w, 24):
            im.paste(t, (x, y))
    return im


def preview():
    m = json.loads(MANIFEST.read_text())["sprites"]
    items = []
    for name, e in m.items():
        sh = Image.open(SHEETS / e["file"]).convert("RGBA")
        cw, ch = e["cell"]
        f = sh.crop((0, 0, cw, ch))
        if name.startswith("obj_chest"):
            # on grass (theme0) and on a dark dungeon floor (theme5), mage alongside for scale
            try:
                mm = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
                mcw, mch = mm["mage_fire"]["cell"]
                hero = Image.open(SHEETS / "mage_fire.png").convert("RGBA").crop((0, 0, mcw, mch))
            except Exception:
                hero, mcw, mch = None, 24, 40
            tile = Image.new("RGBA", (2 * 72 + 4, 48), (32, 32, 40, 255))
            for k, th in enumerate((0, 5)):
                bg = floor_patch(th, 72, 48)
                bg.alpha_composite(f, (8, 48 - ch - 2))
                if hero:
                    bg.alpha_composite(hero, (40, 48 - mch - 2))
                tile.alpha_composite(bg, (k * 76, 0))
            tile = tile.resize((tile.width * 2, tile.height * 2), Image.NEAREST)
            items.append((name, tile))
            continue
        if name.startswith("bld_") or name.startswith("obj_cave_"):
            n = int(name.split("_")[-1])
            bg = floor_patch(3 + n if name.startswith("bld_") else n, 144, ch + 60)
            bg.alpha_composite(f, (24, 12))
            mage = SHEETS / "mage_fire.png"
            if mage.exists():
                mg = Image.open(mage).convert("RGBA")
                mw = mg.width // 4 if mg.width >= 96 else mg.width
                # hero cell size from manifest if available
                try:
                    mm = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
                    key = next(k for k in mm if "mage" in k and "fire" in k)
                    mcw, mch = mm[key]["cell"]
                except Exception:
                    mcw = mch = 24
                hero = mg.crop((0, 0, mcw, mch))
                bg.alpha_composite(hero, (24 + 48 - mcw // 2, 12 + ch))
            tile = bg
        else:
            tile = checker(cw + 8, ch + 8)
            for i in range(e["anims"]["idle"]["frames"]):
                pass
            tile.alpha_composite(f, (4, 4))
        tile = tile.resize((tile.width * 2, tile.height * 2), Image.NEAREST)
        items.append((name, tile))
    W = 1400
    x = y = 0
    rowh = 0
    pos = []
    for name, t in items:
        if x + max(t.width, len(name) * 7) > W:
            x, y = 0, y + rowh + 20
            rowh = 0
        pos.append((name, t, x, y))
        x += max(t.width, len(name) * 7) + 12
        rowh = max(rowh, t.height)
    out = Image.new("RGBA", (W, y + rowh + 20), (32, 32, 40, 255))
    d = ImageDraw.Draw(out)
    for name, t, x, y in pos:
        out.alpha_composite(t, (x, y + 14))
        d.text((x + 2, y), name, fill=(240, 240, 240, 255))
    out.save(GEN / "preview_objects_all.png")
    print("wrote preview", out.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen":
        gen(a[1], a[2], *(a[3:]))
    elif a[0] == "pack":
        pack(a[1], a[2].split(","))
    elif a[0] == "chests":
        pack_chests()
    elif a[0] == "preview":
        preview()


"""Title screen, map icon and UI art for Elemental Legends (uses pixellab.py; never touches the key).

python title.py gen <key>[,<key>...] [tag]  -> generated/title_<key>/<tag>.png (1 generation each, <=6 parallel)
python title.py farfill [left,right,mid] [tag] -> inpaint hidden parts of the far layer (1 generation per tile)
python title.py build                       -> sheets/title_*.png, map_icons.png, ui_*.png + sheets/manifest_title.json
python title.py preview                     -> generated/preview_title.png

Raws live in generated/title_*; only sheets/manifest_title.json is written.
"""
import base64
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixellab import call, wait_job, save_b64, find_b64, find_urls, download, GEN  # noqa: E402

ART = GEN.parent
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest_title.json"
USAGE = GEN / "title_usage.log"
_lock = threading.Lock()

SNES = "16-bit SNES pixel art, Zelda A Link to the Past style, rich limited palette"
NIGHT = "night, soft blue moonlight, deep navy and teal colours"

# key: (method, description, w, h, opts)
SPEC = {
    "scene": ("pixen", f"wide panoramic fantasy landscape at {NIGHT}: a starry night sky with a big full moon on the upper left, "
              "distant blue mountain range on the horizon, dark pine forest treeline, a grassy forest clearing in the foreground, "
              "in the centre one tall ancient grey carved stone monolith obelisk with glowing blue runes, a ring of small mossy standing stones "
              f"around it, dark trees framing the left and right edges, side view, {SNES}", 480, 208, {}),
    "far": ("pixen", f"side view landscape layer: distant misty blue mountain range with snowy peaks and below it a dark blue pine forest treeline silhouette, "
            f"at {NIGHT}, empty plain background above the mountains, {SNES}", 480, 208, {"no_background": True}),
    "near": ("pixen", f"side view of a grassy forest clearing at {NIGHT} in the bottom half of the picture: in the centre a tall ancient grey carved stone monolith obelisk "
             "with faint glowing blue runes, a ring of small mossy grey standing stones around it on the grass, big dark oak trees on the far left and far right edges framing the scene, "
             f"ferns and bushes, empty plain background in the top, {SNES}", 480, 208, {"no_background": True}),
    "moon": ("bitforge", f"a big full moon, pale cream-blue with grey craters, soft round shape, {SNES}", 64, 64,
             {"no_background": True, "outline": "lineless", "shading": "medium shading", "detail": "medium detail"}),
    "logo": ("pixen", "game title logo text \"ELEMENTAL LEGENDS\" in two lines, chunky carved grey stone letters with gold trim and a thick dark outline, "
             f"four small glowing gems (red, blue, violet, green) set into the letters, fantasy RPG title, {SNES}", 240, 72, {"no_background": True}),
    "logo2": ("pixen", "game title logo, the words \"ELEMENTAL\" and \"LEGENDS\" in two lines of big bold capital letters, chunky carved grey stone letters "
              "with gold trim and a thick black outline, four big round glowing gems set between and around the letters: a red fire gem, "
              f"a blue ice gem, a violet storm gem and a green earth gem, fantasy RPG title logo, {SNES}", 240, 72, {"no_background": True}),
    "crest": ("map", "ornate fantasy title emblem crest: a wide horizontal carved gold and grey stone banner plaque with pointed ends, "
              "four small round faceted gems set evenly along it: a red gem, a blue gem, a violet gem and a green gem, "
              f"thick dark outline, empty flat centre, front view, {SNES}", 240, 72, {}),
}


def b64(path):
    return {"type": "base64", "base64": base64.b64encode(Path(path).read_bytes()).decode()}


def _save_job_image(j, out):
    lr = j.get("last_response") or {}
    if isinstance(lr.get("image"), dict) and "base64" in lr["image"]:
        save_b64(lr["image"], out)
        return
    if isinstance(lr.get("image"), str):
        out.write_bytes(base64.b64decode(lr["image"]))
        return
    imgs = list(find_b64(j))
    if imgs:
        save_b64(imgs[0][1], out)
        return
    urls = list(find_urls(j))
    download(urls[0][1], out)


def gen(key, tag="a", seed=None):
    method, desc, w, h, opts = SPEC[key]
    d = GEN / f"title_{key}"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{tag}.png"
    for attempt in range(6):
        try:
            if method == "pixen":
                body = {"description": desc, "image_size": {"width": w, "height": h}, "detail": "highly detailed",
                        "no_background": bool(opts.get("no_background", False))}
                if body["no_background"]:
                    body["background_removal_task"] = "remove_complex_background"
                if seed is not None:
                    body["seed"] = int(seed)
                r = call("POST", "/create-image-pixen", body)
                save_b64(r["image"], out)
            elif method == "bitforge":
                body = {"description": desc, "image_size": {"width": w, "height": h}}
                body.update(opts)
                r = call("POST", "/create-image-bitforge", body)
                save_b64(r["image"], out)
            elif method == "pixflux":
                body = {"description": desc, "image_size": {"width": w, "height": h}}
                body.update(opts)
                r = call("POST", "/create-image-pixflux", body)
                save_b64(r["image"], out)
            else:  # map-objects
                body = {"description": desc, "image_size": {"width": w, "height": h}, "view": "side",
                        "outline": "single color outline", "shading": "medium shading", "detail": "medium detail"}
                r = call("POST", "/map-objects", body)
                j = wait_job(r["background_job_id"]) if r.get("background_job_id") else r
                _save_job_image(j, out)
            break
        except SystemExit as e:  # pixellab.call exits on HTTP errors
            if "429" in str(e) and attempt < 5:
                time.sleep(20 + attempt * 10)
                continue
            print("FAILED", key, tag, str(e)[:300])
            return
    with _lock, USAGE.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {key} {tag} {method} {w}x{h}\n")
    print("saved", out, Image.open(out).size)


def cmd_gen(keys, tag="a", n="1"):
    jobs = [(k, f"{tag}{i}" if int(n) > 1 else tag) for k in keys.split(",") for i in range(int(n))]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda kt: gen(*kt), jobs))


# ---------------------------------------------------------------- scene layering
# The flattened painting (generated/title_scene/a0.png, one pixen generation) is split into
# sky / far / near by colour + geometry; hidden parts are rebuilt (sky locally, far by inpainting).
SKY, FAR, NEAR = 0, 1, 2
MOON_C, MOON_R = (161, 43), 46
MOONSET = {(197, 243, 249), (123, 187, 213), (75, 115, 155), (55, 65, 109), (86, 147, 178), (150, 209, 218),
           (132, 164, 187), (112, 199, 219), (68, 97, 144), (49, 59, 104), (32, 33, 59)}
HORIZON = ((86, 147, 178), (112, 199, 219))
FARSET = {(49, 59, 104), (65, 88, 137), (59, 77, 128), (79, 125, 163), (68, 97, 144), (123, 187, 213),
          (86, 147, 178), (112, 199, 219), (23, 22, 37), (55, 65, 109), (75, 115, 155), (150, 209, 218)}
GRASS = {(64, 123, 103), (91, 156, 139), (48, 89, 77)}


def _flood(W, H, seeds, ok, mark):
    st = [s for s in seeds if ok(*s) and not mark[s[1]][s[0]]]
    for x, y in st:
        mark[y][x] = True
    while st:
        cx, cy = st.pop()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < W and 0 <= ny < H and not mark[ny][nx] and ok(nx, ny):
                mark[ny][nx] = True
                st.append((nx, ny))


def _comp(W, H, x, y, ok, seen, cap=100000):
    comp, st = [], [(x, y)]
    seen.add((x, y))
    while st and len(comp) < cap:
        cx, cy = st.pop()
        comp.append((cx, cy))
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in seen and ok(nx, ny):
                seen.add((nx, ny))
                st.append((nx, ny))
    return comp


def sky_bands(im):
    """Row -> sky band colour, read from a clean strip of sky (x 262..298) above the mountains."""
    from collections import Counter
    px = im.load()
    band = {y: Counter(px[x, y] for x in range(262, 298)).most_common(1)[0][0] for y in range(0, 86)}
    for y in range(86, im.height):
        band[y] = HORIZON[0] if y < 98 else HORIZON[1]
    return band


def segment(im):
    im = im.convert("RGB")
    px = im.load()
    W, H = im.size
    band = sky_bands(im)

    def in_moon(x, y):
        return (x - MOON_C[0]) ** 2 + (y - MOON_C[1]) ** 2 <= MOON_R ** 2

    def bandlike(x, y):
        c = px[x, y]
        if y > 112:
            return False
        if c == band[y] or (82 <= y and c in HORIZON) or (in_moon(x, y) and c in MOONSET):
            return True
        # thin dithered lines between bands
        return y < 86 and (c == band.get(y - 1) or c == band.get(y + 1))

    B = [[bandlike(x, y) for x in range(W)] for y in range(H)]
    star = set()
    seen = set()
    for y in range(0, 100):
        for x in range(W):
            if B[y][x] or (x, y) in seen:
                continue
            comp = _comp(W, H, x, y, lambda a, b: not B[b][a], seen, cap=40)
            if len(comp) <= 6 and max(px[p][0] for p in comp) > 120:
                star.update(comp)
    sky = [[False] * W for _ in range(H)]
    ok = lambda x, y: B[y][x] or (x, y) in star  # noqa: E731
    _flood(W, H, [(x, 0) for x in range(W)], ok, sky)
    # enclosed sky pockets (between oak branches and pines): band-like components >= 10 px
    seen = set()
    for y in range(0, 112):
        for x in range(W):
            if B[y][x] and not sky[y][x] and (x, y) not in seen and not (186 <= x <= 254):
                comp = _comp(W, H, x, y, lambda a, b: ok(a, b) and not sky[b][a] and b < 112, seen)
                if len(comp) >= 10:
                    for a, b in comp:
                        sky[b][a] = True
    # far = mountains + distant treeline, flood-filled from seeds through FARSET colours above the grass
    g = ground_line(im)
    far = [[False] * W for _ in range(H)]
    okf = lambda x, y: (not sky[y][x]) and y < g[x] and px[x, y] in FARSET  # noqa: E731
    _flood(W, H, [(300, 100), (300, 135), (180, 115), (340, 130), (150, 112)], okf, far)
    lab = [[SKY if sky[y][x] else FAR if far[y][x] else NEAR for x in range(W)] for y in range(H)]
    # small NEAR specks (treeline outline pixels, dither lines) surrounded by SKY/FAR join their neighbours
    from collections import Counter
    seen = set()
    for y in range(0, max(g)):
        for x in range(W):
            if lab[y][x] != NEAR or (x, y) in seen:
                continue
            comp = _comp(W, H, x, y, lambda a, b: lab[b][a] == NEAR, seen, cap=200)
            if len(comp) > (150 if y < 90 else 40):
                continue
            cs = set(comp)
            nb = Counter(lab[b][a] for cx, cy in comp for a, b in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1))
                         if 0 <= a < W and 0 <= b < H and (a, b) not in cs)
            if nb and NEAR not in nb:
                v = nb.most_common(1)[0][0]
                for a, b in comp:
                    lab[b][a] = v
    return lab


RAW_SCENE = GEN / "title_scene" / "a0.png"
FAR_DIR = GEN / "title_farfill"
FAR_DESC = ("distant blue mountain range with pale snowy ridges and below it a dark navy pine forest treeline silhouette, "
            f"at {NIGHT}, matching the surrounding picture, {SNES}")


def _star_field(img, rows, avoid, seed=7, density=0.004):
    import random
    rnd = random.Random(seed)
    px = img.load()
    for y in range(*rows):
        for x in range(img.width):
            if avoid(x, y) or rnd.random() > density:
                continue
            c = rnd.choice([(150, 209, 218), (132, 164, 187), (132, 164, 187), (197, 243, 249)])
            px[x, y] = c + (255,)
            if c == (197, 243, 249) and rnd.random() < 0.3 and 1 <= x < img.width - 1 and 1 <= y:
                for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if not avoid(a, b):
                        px[a, b] = (123, 187, 213, 255)


def scene_parts():
    """Return (raw, labels, ground, band, sky_layer)."""
    raw = Image.open(RAW_SCENE).convert("RGB")
    lab = segment(raw)
    g = ground_line(raw)
    band = sky_bands(raw)
    W, H = raw.size
    rp = raw.load()
    sky = Image.new("RGBA", (W, H))
    sp = sky.load()
    for y in range(H):
        for x in range(W):
            sp[x, y] = (rp[x, y] if lab[y][x] == SKY else band[y]) + (255,)
    # stars where the original sky was hidden (behind the oak canopies / mountains)
    _star_field(sky, (2, 60), lambda x, y: not (0 <= x < W and 0 <= y < H) or lab[y][x] == SKY or
                (x - MOON_C[0]) ** 2 + (y - MOON_C[1]) ** 2 <= (MOON_R + 4) ** 2)
    return raw, lab, g, band, sky


def farfill_inputs():
    """Inpainting input for the far layer: sky + visible far, mask = near objects between y 58 and the grass."""
    raw, lab, g, band, sky = scene_parts()
    W, H = raw.size
    rp = raw.load()
    img = sky.copy()
    ip = img.load()
    mask = Image.new("RGB", (W, H), (0, 0, 0))
    mp = mask.load()
    for y in range(H):
        for x in range(W):
            if lab[y][x] == FAR:
                ip[x, y] = rp[x, y] + (255,)
            elif lab[y][x] == NEAR:
                if 58 <= y < g[x] + 3:
                    mp[x, y] = (255, 255, 255)
                if y >= 128:
                    ip[x, y] = (23, 22, 37, 255)
    FAR_DIR.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(FAR_DIR / "input.png")
    mask.save(FAR_DIR / "mask.png")
    return FAR_DIR / "input.png", FAR_DIR / "mask.png"


# inpainting tiles (/inpaint: max area 200x200); run in order, each sees the previous result
FAR_TILES = {"left": (0, 40, 200, 160), "right": (280, 40, 480, 160), "mid": (140, 40, 300, 160)}


def far_palette():
    p = FAR_DIR / "palette.png"
    cols = sorted(FARSET | {(19, 13, 27), (32, 33, 59), (26, 38, 42)})
    im = Image.new("RGB", (len(cols), 1))
    for i, c in enumerate(cols):
        im.putpixel((i, 0), c)
    im.save(p)
    return p


def gen_farfill(tiles="left,right,mid", tag="a"):
    """Inpaint the hidden parts of the far layer, tile by tile (1 generation per tile)."""
    work = FAR_DIR / f"work_{tag}.png"
    if not work.exists():
        inp, _ = farfill_inputs()
        Image.open(inp).save(work)
    mask_full = Image.open(FAR_DIR / "mask.png").convert("L")
    done = FAR_DIR / f"done_{tag}.txt"
    for t in (done.read_text().split() if done.exists() else ["left"]):
        mask_full.paste(0, FAR_TILES[t])
    pal = far_palette()
    for t in tiles.split(","):
        box = FAR_TILES[t]
        cur = Image.open(work).convert("RGB")
        tile = cur.crop(box)
        m = mask_full.crop(box)
        tp, mp_ = FAR_DIR / f"tile_{t}_in.png", FAR_DIR / f"tile_{t}_mask.png"
        tile.save(tp)
        m.save(mp_)
        w, h = tile.size
        body = {"description": FAR_DESC, "image_size": {"width": w, "height": h},
                "inpainting_image": b64(tp), "mask_image": b64(mp_), "color_image": b64(pal),
                "view": "side", "outline": "lineless", "shading": "medium shading", "detail": "medium detail"}
        r = call("POST", "/inpaint", body)
        out = FAR_DIR / f"tile_{t}_{tag}.png"
        save_b64(r["image"], out)
        res = Image.open(out).convert("RGB")
        cur.paste(Image.composite(res, tile, m), box[:2])
        cur.save(work)
        mask_full.paste(0, box)  # done: later overlapping tiles keep this result
        done = FAR_DIR / f"done_{tag}.txt"
        done.write_text((done.read_text() if done.exists() else "") + t + "\n")
        with _lock, USAGE.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} farfill {t} {tag} inpaint {w}x{h}\n")
        print("inpainted", t, box)


def _dist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def scene_layers(tag="a"):
    """-> dict name -> RGBA 480x208 image (title_sky, title_far, title_near, title_scene)."""
    raw, lab, g, band, sky = scene_parts()
    W, H = raw.size
    rp = raw.load()
    work = Image.open(FAR_DIR / f"work_{tag}.png").convert("RGB")
    wp = work.load()
    mask = Image.open(FAR_DIR / "mask.png").convert("L").load()
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fp = far.load()
    for y in range(H):
        for x in range(W):
            if lab[y][x] == FAR:
                fp[x, y] = rp[x, y] + (255,)
            elif y >= 128 and lab[y][x] == NEAR:
                fp[x, y] = wp[x, y] + (255,)  # treeline base (dark) hidden behind the clearing
            elif mask[x, y] > 0:
                c = wp[x, y]
                near_band = any(_dist(c, band[yy]) <= 18 for yy in (y - 1, y, y + 1) if yy in band)
                if not near_band:
                    fp[x, y] = c + (255,)
    # drop faint inpainting ghosts floating in the sky (detached small bits above the ridge)
    seen = set()
    for y in range(0, 128):
        for x in range(W):
            if fp[x, y][3] and (x, y) not in seen:
                comp = _comp(W, H, x, y, lambda a, b: fp[a, b][3] > 0, seen, cap=400)
                if len(comp) < 60:
                    for a, b in comp:
                        if lab[b][a] != FAR:
                            fp[a, b] = (0, 0, 0, 0)
    # close 1-2 px wide vertical slits in the treeline (pine-edge highlights that matched the horizon band)
    for y in range(96, H):
        for x in range(1, W - 1):
            if fp[x, y][3]:
                continue
            for gap in (1, 2):
                if x + gap < W and fp[x - 1, y][3] and fp[x + gap, y][3] and all(not fp[x + i, y][3] for i in range(gap)):
                    for i in range(gap):
                        fp[x + i, y] = fp[x - 1, y]
                    break
    near = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    npx = near.load()
    for y in range(H):
        for x in range(W):
            if lab[y][x] == NEAR:
                npx[x, y] = rp[x, y] + (255,)
    flat = sky.copy()
    flat.alpha_composite(far)
    flat.alpha_composite(near)
    return {"title_sky": sky, "title_far": far, "title_near": near, "title_scene": flat}


# ---------------------------------------------------------------- hand-pixelled map icons (12x12)
ICON_PAL = {
    "k": (20, 16, 28), "S": (176, 172, 168), "s": (112, 108, 116), "T": (224, 220, 212),
    "d": (44, 24, 40), "D": (24, 12, 24), "c": (120, 232, 255), "C": (232, 255, 255), "b": (56, 136, 232),
    "R": (152, 128, 104), "r": (100, 84, 72), "Q": (196, 172, 140),
    "o": (216, 64, 48), "O": (148, 36, 36), "W": (240, 228, 196), "w": (200, 180, 140), "n": (120, 72, 40),
    "y": (255, 224, 96), "G": (248, 196, 56), "g": (184, 128, 32), "B": (168, 96, 48), "h": (212, 136, 72),
    "v": (208, 176, 255), "V": (144, 96, 224), "N": (80, 48, 152), "X": (255, 255, 255),
    "e": (248, 72, 56), "E": (176, 24, 40), "F": (255, 168, 160), "Z": (232, 228, 216), "z": (160, 152, 148),
    "M": (88, 100, 120), "m": (60, 70, 88), "L": (96, 176, 255), "P": (255, 88, 56), "p": (184, 40, 40),
}
ICONS = {
    "lair": [
        ".kk.kkkk.kk.",
        ".kTkkTTkkSk.",
        ".kSSSSSSSsk.",
        ".kkkkkkkkkk.",
        "..kTSSSSsk..",
        "..kSSkkSsk..",
        "..kSkddksk..",
        "..kSkdDksk..",
        "..kSkdDksk..",
        ".kkSkdDkskk.",
        "kSSSkdDkssSk",
        "kkkkkkkkkkkk"],
    "lair_cleared": [
        ".kk.kkkk.kk.",
        ".kTkkTTkkSk.",
        ".kSSSSSSSsk.",
        ".kkkkkkkkkk.",
        "..kTSSSSsk..",
        "..kSSkkSsk..",
        "..kSkcCksk..",
        "..kSkCbksk..",
        "..kSkcCksk..",
        ".kkSkbcCskk.",
        "kSSSkcbksssk",
        "kkkkkkkkkkkk"],
    "cave": [
        "............",
        "....kkkk....",
        "..kkQQQRkk..",
        ".kQQRRRRRrk.",
        ".kQRkkkkRrk.",
        "kQRkDDDDkRrk",
        "kQkDDDDDDkrk",
        "kRkDDDDDDkrk",
        "kRkDDDDDDkrk",
        "kRkDDDDDDkrk",
        "kkkDDDDDDkkk",
        ".kkkkkkkkkk."],
    "cave_cleared": [
        "............",
        "....kkkk....",
        "..kkQQQRkk..",
        ".kQQRRRRRrk.",
        ".kQRkkkkRrk.",
        "kQRkbbbbkRrk",
        "kQkbbcCbbkrk",
        "kRkbcbbcbkrk",
        "kRkbbCcbbkrk",
        "kRkbcbbcbkrk",
        "kkkbbcCbbkkk",
        ".kkkkkkkkkk."],
    "village": [
        ".....kk.....",
        "....kook....",
        "...kooOOk...",
        "..kooooOOk..",
        ".kooooooOOk.",
        "kkkkkkkkkkkk",
        ".kWWWWWWWwk.",
        ".kWkkWWkkwk.",
        ".kWknkWkykw.",
        ".kWknkWkkwk.",
        ".kWknkWWWwk.",
        ".kkkkkkkkkk."],
    "monolith": [
        "....LkkL....",
        "...LkTSkL...",
        "...kTSSsk...",
        "..LkScSskL..",
        "...kScSsk...",
        "..LkSScskL..",
        "...kScSsk...",
        "...kSccsk...",
        "..kTSSSssk..",
        ".kTSSSSsssk.",
        ".kkkkkkkkkk.",
        "............"],
    "shrine": [
        "....kkkk....",
        "...kXvvvk...",
        "..kXvvvVVk..",
        "..kvvvVVVk..",
        "..kvvVVVNk..",
        "...kVVNNk...",
        "....kkkk....",
        "...kTSSsk...",
        "....kSsk....",
        "....kSsk....",
        "..kkTSSsskk.",
        "..kkkkkkkkk."],
    "chest": [
        "............",
        "............",
        ".kkkkkkkkkk.",
        "khhhhGGhhhBk",
        "kBBBBGGBBBBk",
        "kkkkkGGkkkkk",
        "kGBBkyykBBGk",
        "kGBBkGgkBBGk",
        "kGBBBkkBBBGk",
        "kGGGGGGGGGGk",
        "kkkkkkkkkkkk",
        "............"],
    "heart": [
        "............",
        "..kkk..kkk..",
        ".keeekkeeEk.",
        "keFeeeeeeeEk",
        "keFeeeeeeeEk",
        "keeeeeeeeeEk",
        ".keeeeeeeEk.",
        "..keeeeeEk..",
        "...keeeEk...",
        "....keEk....",
        ".....kk.....",
        "............"],
    "player": [
        "........kkk.",
        ".......kyXk.",
        "......kPPk..",
        ".....kPPpk..",
        "....kPPPpk..",
        "....kPPPpk..",
        "...kyyyyyyk.",
        ".kkPPPPPPpkk",
        "kPPXPPPPPPpk",
        "kPPPPPPPPppk",
        ".kppppppppk.",
        "..kkkkkkkk.."],
    "encounter": [
        ".....kk.....",
        "....keek....",
        "...keFeek...",
        "..keFeeeek..",
        ".keeeeeeeEk.",
        "keeeeeeeeEEk",
        "keeeeeeeEEEk",
        ".keeeeeEEEk.",
        "..keeeEEEk..",
        "...keEEEk...",
        "....kEEk....",
        ".....kk....."],
    "boss": [
        "............",
        "...kkkkkk...",
        "..kZZZZZZk..",
        ".kZZZZZZZzk.",
        ".kZkkZZkkzk.",
        ".kZkeZZkezk.",
        ".kZZZkkZZzk.",
        "..kZZZZZzk..",
        "...kZkZkk...",
        "...kZzZzk...",
        "...kkkkkk...",
        "............"],
}
ICON_ORDER = ["lair", "lair_cleared", "cave", "cave_cleared", "village", "monolith", "shrine", "chest",
              "heart", "player", "encounter", "boss"]


def draw_icon(rows):
    im = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        assert len(row) == 12, (row, len(row))
        for x, ch in enumerate(row):
            if ch != ".":
                im.putpixel((x, y), ICON_PAL[ch] + (255,))
    return im


# ---------------------------------------------------------------- UI pieces (hand-drawn)
UI = {"k": (12, 10, 20), "G": (252, 224, 120), "g": (216, 160, 48), "h": (140, 88, 32),
      "S": (150, 146, 160), "s": (96, 92, 112), "n": (24, 30, 72), "N": (36, 46, 104), "b": (72, 132, 232),
      "B": (160, 216, 255), "W": (255, 252, 220)}
# top edge profile (outside -> inside), 8 rows; one 8 px period along the edge (rivet on the stone band)
EDGE = ["kkkkkkkk",
        "GGGGGGGG",
        "gggggggg",
        "sSssSssS",
        "ssssssss",
        "hhhhhhhh",
        "kkkkkkkk",
        "NNNNNNNN"]
EDGE_RIVET = {(3, 3): "G", (4, 3): "g", (3, 4): "g", (4, 4): "h", (2, 3): "k", (5, 3): "k", (2, 4): "k", (5, 4): "k"}
CORNER_GEM = {(3, 3): "W", (4, 3): "B", (3, 4): "b", (4, 4): "b"}


def corner_px(x, y):
    """Top-left corner: the edge profile wrapped round a chamfered corner with a set blue gem."""
    if x + y < 2:
        return "."
    if x + y == 2:
        return "k"
    if (x, y) in CORNER_GEM:
        return CORNER_GEM[(x, y)]
    if 2 <= x <= 5 and 2 <= y <= 5:
        return "k" if (x, y) not in ((2, 2), (5, 5), (2, 5), (5, 2)) else "g"
    return EDGE[min(x, y)][0]


def ui_frame():
    """24x24 9-slice frame: 8 px corners/edges, the 8x8 centre and the edges tile."""
    im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    P = lambda x, y, ch: im.putpixel((x, y), UI[ch] + (255,)) if ch != "." else None  # noqa: E731
    top = [[EDGE_RIVET.get((x, y), EDGE[y][x]) for x in range(8)] for y in range(8)]
    for y in range(8):
        for x in range(8):
            ch = top[y][x]
            P(8 + x, y, ch)                 # top edge
            P(8 + x, 23 - y, ch)            # bottom edge (mirrored)
            P(y, 8 + x, ch)                 # left edge (transposed)
            P(23 - y, 8 + x, ch)            # right edge
            c = corner_px(x, y)
            P(x, y, c)
            P(23 - x, y, c)
            P(x, 23 - y, c)
            P(23 - x, 23 - y, c)
    for y in range(8, 16):
        for x in range(8, 16):
            P(x, y, "n")
    return im


def ui_slot():
    im = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    px = im.load()
    for y in range(20):
        for x in range(20):
            edge = min(x, y, 19 - x, 19 - y)
            if edge == 0:
                ch = "k" if (x, y) not in ((0, 0), (19, 0), (0, 19), (19, 19)) else None
            elif edge == 1:
                ch = "g" if (x <= y and x + y < 19) or (y <= x and x + y < 19) else "h"
                ch = "G" if (y == 1 or x == 1) and x + y < 19 else "h"
            elif edge == 2:
                ch = "k"
            elif edge == 3:
                ch = "k" if (y == 3 or x == 3) and x + y < 19 else "N"
            else:
                ch = "n"
            if ch:
                px[x, y] = UI[ch] + (255,)
    return im


def ui_cursor():
    """24x24 x 2 frames: gold corner brackets, the second frame bright and 1 px inset (blink)."""
    sheet = Image.new("RGBA", (48, 24), (0, 0, 0, 0))
    for f, (inset, fill) in enumerate(((0, "G"), (1, "W"))):
        fr = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        px = fr.load()
        L = 7
        pts = set()
        for i in range(L):
            for t in range(2):          # 2 px thick arms
                pts |= {(i, t), (t, i)}
        outl = set()
        for x, y in pts:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    outl.add((x + dx, y + dy))
        for mx in (False, True):
            for my in (False, True):
                def tr(x, y):
                    x, y = x + inset, y + inset
                    return (23 - x if mx else x, 23 - y if my else y)
                for x, y in outl:
                    if (x, y) not in pts and -1 <= x and -1 <= y:
                        X, Y = tr(x, y)
                        if 0 <= X < 24 and 0 <= Y < 24:
                            px[X, Y] = UI["k"] + (255,)
                for x, y in pts:
                    X, Y = tr(x, y)
                    shade = fill if (x == 0 or y == 0) else ("g" if fill == "G" else "G")
                    px[X, Y] = UI[shade] + (255,)
        sheet.alpha_composite(fr, (24 * f, 0))
    return sheet


# ---------------------------------------------------------------- logo
RAW_LOGO = GEN / "title_logo" / "a.png"
# (centre, colours light/mid/dark) for the four element gems already sitting in the letter counters
LOGO_GEMS = [((105, 22), ((255, 200, 180), (232, 48, 40), (136, 16, 24))),     # fire  (m)
             ((109, 50), ((200, 240, 255), (64, 160, 248), (24, 64, 160))),    # ice   (g)
             ((163, 50), ((248, 200, 255), (176, 88, 232), (88, 32, 144))),    # storm (d)
             ((149, 50), ((200, 255, 168), (72, 200, 72), (24, 104, 40)))]     # earth (n)
GEM = [".kkk.",
       "kHMMk",
       "kMMDk",
       "kMDDk",
       ".kkk."]


def logo():
    im = Image.open(RAW_LOGO).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    for (cx, cy), (hi, mid, dk) in LOGO_GEMS:
        for j, row in enumerate(GEM):
            for i, ch in enumerate(row):
                if ch == ".":
                    continue
                c = {"k": (24, 12, 16), "H": hi, "M": mid, "D": dk}[ch]
                px[cx - 2 + i, cy - 2 + j] = c + (255,)
        px[cx - 1, cy - 1] = (255, 255, 255, 255)
    return im


# ---------------------------------------------------------------- build / preview
def _manifest_entry(m, name, file, cell, anims):
    m["sprites"][name] = {"file": file, "cell": list(cell), "anims": anims}


def build():
    SHEETS.mkdir(exist_ok=True)
    m = {"sprites": {}}
    idle = lambda n=1, fps=1: {"idle": {"row": 0, "frames": n, "fps": fps}}  # noqa: E731
    lg = logo()
    lg.save(SHEETS / "title_logo.png")
    _manifest_entry(m, "title_logo", "title_logo.png", lg.size, idle())
    layers = scene_layers()
    raw = Image.open(RAW_SCENE).convert("RGBA")
    diff = sum(1 for a, b in zip(layers["title_scene"].getdata(), raw.getdata()) if a != b)
    print("flattened vs raw painting: differing pixels =", diff)
    for name, im in layers.items():
        im.save(SHEETS / f"{name}.png")
        _manifest_entry(m, name, f"{name}.png", im.size, idle())
    icons = Image.new("RGBA", (12, 12 * len(ICON_ORDER)), (0, 0, 0, 0))
    for i, n in enumerate(ICON_ORDER):
        icons.alpha_composite(draw_icon(ICONS[n]), (0, 12 * i))
    icons.save(SHEETS / "map_icons.png")
    _manifest_entry(m, "map_icons", "map_icons.png", (12, 12),
                    {n: {"row": i, "frames": 1, "fps": 1} for i, n in enumerate(ICON_ORDER)})
    fr = ui_frame()
    fr.save(SHEETS / "ui_frame.png")
    _manifest_entry(m, "ui_frame", "ui_frame.png", fr.size, idle())
    sl = ui_slot()
    sl.save(SHEETS / "ui_slot.png")
    _manifest_entry(m, "ui_slot", "ui_slot.png", sl.size, idle())
    cu = ui_cursor()
    cu.save(SHEETS / "ui_cursor.png")
    _manifest_entry(m, "ui_cursor", "ui_cursor.png", (24, 24), idle(2, 4))
    m["sprites"] = dict(sorted(m["sprites"].items()))
    MANIFEST.write_text(json.dumps(m, indent=2))
    print("wrote", MANIFEST, list(m["sprites"]))


def nine_slice(src, w, h, s=8):
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    W, H = src.size
    parts = lambda x0, x1, y0, y1: src.crop((x0, y0, x1, y1))  # noqa: E731
    for y in range(s, h - s, s):
        for x in range(s, w - s, s):
            out.paste(parts(s, 2 * s, s, 2 * s), (x, y))
    for x in range(s, w - s, s):
        out.paste(parts(s, 2 * s, 0, s), (x, 0))
        out.paste(parts(s, 2 * s, H - s, H), (x, h - s))
    for y in range(s, h - s, s):
        out.paste(parts(0, s, s, 2 * s), (0, y))
        out.paste(parts(W - s, W, s, 2 * s), (w - s, y))
    out.paste(parts(0, s, 0, s), (0, 0))
    out.paste(parts(W - s, W, 0, s), (w - s, 0))
    out.paste(parts(0, s, H - s, H), (0, h - s))
    out.paste(parts(W - s, W, H - s, H), (w - s, h - s))
    return out


def preview():
    from PIL import ImageDraw
    sh = lambda n: Image.open(SHEETS / f"{n}.png").convert("RGBA")  # noqa: E731
    # 320x240 screen: 32 px HUD strip on top, the 208 px scene below, logo over it
    HUD = 32

    def screen(pan):
        scr = Image.new("RGBA", (320, 240), (8, 8, 16, 255))
        for name, k in (("title_sky", 0.25), ("title_far", 0.5), ("title_near", 1.0)):
            lay = sh(name)
            scr.alpha_composite(lay.crop((int(pan * k), 0, int(pan * k) + 320, 208)), (0, HUD))
        lg = sh("title_logo")
        scr.alpha_composite(lg, ((320 - lg.width) // 2, HUD + 6))
        return scr

    shots = [screen(0), screen(80), screen(160)]
    flat = sh("title_scene")
    W = 3 * 320 + 4 * 8
    out = Image.new("RGBA", (W, 1500), (32, 32, 40, 255))
    d = ImageDraw.Draw(out)
    y = 4
    d.text((8, y), "title screen 320x240 (HUD gap 32 px) - pan 0 / 80 / 160 (sky x0.25, far x0.5, near x1)", fill=(240, 240, 240))
    y += 14
    for i, s in enumerate(shots):
        out.alpha_composite(s, (8 + i * 328, y))
    y += 248
    d.text((8, y), "title_scene (flattened 480x208) x2", fill=(240, 240, 240))
    out.alpha_composite(flat.resize((960, 416), Image.NEAREST), (8, y + 14))
    y += 14 + 424
    d.text((8, y), "layers: title_sky / title_far / title_near (on magenta)", fill=(240, 240, 240))
    y += 14
    for i, n in enumerate(("title_sky", "title_far", "title_near")):
        bg = Image.new("RGBA", (320, 139), (255, 0, 255, 255))
        bg.alpha_composite(sh(n).resize((320, 139), Image.NEAREST))
        out.alpha_composite(bg, (8 + i * 328, y))
    y += 148
    d.text((8, y), "map_icons x3 (on dark map / on grass) + names", fill=(240, 240, 240))
    y += 14
    icons = sh("map_icons")
    for i, n in enumerate(ICON_ORDER):
        ic = icons.crop((0, 12 * i, 12, 12 * i + 12))
        for k, bgc in enumerate(((40, 52, 80, 255), (88, 152, 72, 255))):
            t = Image.new("RGBA", (16, 16), bgc)
            t.alpha_composite(ic, (2, 2))
            out.alpha_composite(t.resize((48, 48), Image.NEAREST), (8 + i * 78, y + k * 52))
        d.text((8 + i * 78, y + 106), n, fill=(240, 240, 240))
    y += 124
    d.text((8, y), "ui_frame 24x24 x3, nine-sliced to 160x64 x3, ui_slot x3, ui_cursor frames x3 (over a slot)", fill=(240, 240, 240))
    y += 14
    fr = sh("ui_frame")
    out.alpha_composite(fr.resize((72, 72), Image.NEAREST), (8, y))
    big = nine_slice(fr, 160, 64)
    slot = sh("ui_slot")
    for i in range(4):
        big.alpha_composite(slot, (16 + i * 34, 22))
    out.alpha_composite(big.resize((480, 192), Image.NEAREST), (90, y))
    out.alpha_composite(slot.resize((60, 60), Image.NEAREST), (580, y))
    cur = sh("ui_cursor")
    for f in range(2):
        t = Image.new("RGBA", (24, 24), (24, 30, 72, 255))
        t.alpha_composite(slot, (2, 2))
        t.alpha_composite(cur.crop((24 * f, 0, 24 * f + 24, 24)))
        out.alpha_composite(t.resize((72, 72), Image.NEAREST), (650 + f * 80, y))
    y += 200
    out = out.crop((0, 0, W, y))
    out.save(GEN / "preview_title.png")
    # plain 320x240 shot of the title screen, 1:1
    shots[0].save(GEN / "preview_title_screen.png")
    print("wrote preview", out.size)


def ground_line(im):
    """Per column: first y >= 138 where the grass begins (median-smoothed)."""
    px = im.load()
    W, H = im.size
    g = []
    for x in range(W):
        y0 = next((y for y in range(138, H) if px[x, y] in GRASS), None)
        g.append(y0 if y0 is not None else 150)
    sm = []
    for x in range(W):
        win = sorted(g[max(0, x - 6):x + 7])
        sm.append(win[len(win) // 2])
    return sm


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen":
        cmd_gen(*a[1:])
    elif a[0] == "farfill":
        gen_farfill(*a[1:])
    elif a[0] == "farinputs":
        farfill_inputs()
    elif a[0] == "build":
        build()
    elif a[0] == "preview":
        preview()

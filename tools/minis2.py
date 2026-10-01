"""Mini-boss encounter art, batch 2 (uses pixellab.py helpers; the key is never printed).

python minis2.py gen <key> [<key> ...]   run the generation pipeline(s) (idempotent: skips existing raws)
python minis2.py build [<key> ...]       pack sheets -> sheets/*.png + sheets/manifest_minis2.json
python minis2.py preview                 -> generated/preview_minis2.png
python minis2.py spent                   generations logged in generated/mini2_usage.log

Raws land in generated/mini2_<key>/. Only sheets/manifest_minis2.json is written.
Keys: goblin ogre knight witch mimic raccoon fairy bear hive head banshee hut toad wisp
      salamander golem phoenix egg mushroom items (pixie, quicksand: code-drawn in build)
"""
import json
import math
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chars  # noqa: E402
import charpack  # noqa: E402
import chunky  # noqa: E402
import objects  # noqa: E402
import pixellab  # noqa: E402
from pixellab import GEN, save_b64, find_b64, find_urls, download  # noqa: E402

ART = GEN.parent
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest_minis2.json"
LOG = GEN / "mini2_usage.log"


def d_of(name):
    d = GEN / f"mini2_{name}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# route the shared helpers to this batch's dirs / log / manifest
chars.MYLOG = LOG
chars.d_of = d_of
chunky.d_of = d_of
charpack.MANIFEST = MANIFEST

SLOTS = threading.Semaphore(8)
STYLE = "SNES Zelda A Link to the Past style game sprite, bold black outline, rich natural colors, not neon"
NEG = "background, ground, floor, grass, shadow, text, frame, border, blurry, multiple creatures"


# ---------------------------------------------------------------- generation primitives
def bf(key, tag, desc, w, h, direction=None, init=None, strength=300, seed=0, view="low top-down"):
    out = d_of(key) / f"{tag}.png"
    if out.exists():
        return out
    body = {"description": f"{desc}, {STYLE}", "negative_description": NEG,
            "image_size": {"width": w, "height": h}, "no_background": True,
            "outline": "single color black outline", "shading": "basic shading",
            "detail": "low detail", "view": view}
    if direction:
        body["direction"] = direction
    if init:
        body["init_image"] = chars.b64(init)
        body["init_image_strength"] = int(strength)
    if seed:
        body["seed"] = seed
    with SLOTS:
        r = chars.call("POST", "/create-image-bitforge", body)
    chars.log_charge(f"mini2 {key} bitforge {tag}", r.get("usage"))
    save_b64(r["image"], out)
    print("saved", out.relative_to(ART), flush=True)
    return out


def mapobj(key, tag, desc, w, h, view="high top-down"):
    out = d_of(key) / f"{tag}.png"
    if out.exists():
        return out
    body = {"description": f"{desc}, {STYLE}", "image_size": {"width": w, "height": h}, "view": view,
            "outline": "selective outline", "shading": "medium shading", "detail": "medium detail"}
    with SLOTS:
        r = chars.call("POST", "/map-objects", body)
        j = chars.wait(r["background_job_id"], f"mini2 {key} map {tag}") if r.get("background_job_id") else r
    lr = j.get("last_response") or {}
    imgs = list(find_b64(j))
    if isinstance(lr.get("image"), dict) and "base64" in lr["image"]:
        save_b64(lr["image"], out)
    elif imgs:
        save_b64(imgs[0][1], out)
    else:
        urls = list(find_urls(j))
        if not urls and r.get("object_id"):
            urls = list(find_urls(pixellab.call("GET", f"/objects/{r['object_id']}")))
        download(urls[0][1], out)
    print("saved", out.relative_to(ART), flush=True)
    return out


def anim(key, base, prefix, action, frames=4):
    if (d_of(key) / f"{prefix}_1.png").exists():
        return
    with SLOTS:
        chars.animtext(key, str(d_of(key) / base), prefix, action, frames)


def chunky_char(key, size, props, desc, action="walking"):
    d = d_of(key)
    if not (d / "rotation_urls_south.png").exists():
        with SLOTS:
            chunky.character(key, desc, size, json.dumps(props))
    info = json.loads((d / "character.json").read_text())
    have = {dd["direction"] for a in info.get("animations", []) for dd in a["directions"] if len(dd["frames"]) >= 4}
    for dr in ("south", "north", "east"):
        if dr not in have:
            with SLOTS:
                chunky.animate(key, action, dr, 4)


CHUNK = {"head_size": 1.7, "legs_length": 0.5, "arms_length": 0.8, "shoulder_width": 1.2, "hip_width": 1.2}
PLUMP = {"head_size": 1.6, "legs_length": 0.5, "arms_length": 0.8, "shoulder_width": 1.3, "hip_width": 1.6}
BROAD = {"head_size": 1.6, "legs_length": 0.55, "arms_length": 0.85, "shoulder_width": 1.5, "hip_width": 1.3}
HEADLESS = {"head_size": 0.6, "legs_length": 0.55, "arms_length": 0.85, "shoulder_width": 1.5, "hip_width": 1.3}
OGRE = {"head_size": 1.3, "legs_length": 0.55, "arms_length": 0.9, "shoulder_width": 1.7, "hip_width": 1.6}

HUMANOIDS = {
    "goblin": (22, CHUNK, "small greedy treasure goblin with a big head, green skin, long pointy ears, big nose, wide "
               "greedy grin, ragged brown tunic, carrying a big bulging brown coin sack over its shoulder with gold "
               "coins spilling out, chunky SNES RPG enemy"),
    "ogre": (36, OGRE, "big friendly wandering merchant ogre, large stocky body, tan-green skin, small tusks, kind smile, "
             "simple brown vest and trousers, carrying a huge tall wooden-framed backpack stacked with wares, pots, "
             "rolled rugs and lanterns, chunky SNES RPG villager"),
    "knight": (30, HEADLESS, "headless knight, NO head, an empty dark armored neck collar with purple smoke rising from "
               "it, broad dark black-steel plate armor, tattered dark red cape, holding a sword and a round dark shield "
               "with a red emblem, chunky SNES RPG enemy"),
    "ogre2": (36, OGRE, "big friendly ogre monster merchant, huge bald head with bright green skin, two big white tusks "
              "jutting up from the lower jaw, pointy ears, big round belly, kind smile, simple brown vest, carrying a "
              "huge tall wooden-framed backpack stacked with wares, pots and rolled rugs, chunky SNES RPG villager"),
    "knight2": (36, BROAD, "big headless knight, NO head, an empty dark armored neck collar, broad dark black-steel "
                "plate armor with big pauldrons, tattered dark red cape, holding a sword in one hand and a round dark "
                "shield with a red emblem in the other, chunky SNES RPG enemy"),
    "witch": (24, CHUNK, "short old swamp bog witch hag with a big head, warty green skin, long crooked nose, stringy grey "
              "hair, tall crooked floppy brown pointed hat, ragged mossy green-brown robe, holding a long wooden "
              "cauldron spoon, chunky SNES RPG villager"),
}


# ---------------------------------------------------------------- pipelines
def p_humanoid(key):
    size, props, desc = HUMANOIDS[key]
    chunky_char(key, size, props, desc)


def p_mimic(k):
    bf(k, "open", "treasure chest mimic monster, a brown wooden treasure chest with shiny gold metal bands and a gold "
       "lock plate, its lid wide open like a mouth showing rows of sharp white teeth and a long red tongue hanging out, "
       "two small glowing eyes inside, top-down three-quarter view", 32, 32)
    anim(k, "open.png", "move", "treasure chest monster hopping forward and snapping its lid mouth shut and open, biting")


def p_raccoon(k):
    bf(k, "base", "masked bandit raccoon on all fours, grey fur, black bandit eye mask, striped ringed tail, carrying a "
       "tied red-and-white cloth loot bundle on its back, side view facing right", 32, 28, direction="east")
    anim(k, "base.png", "run", "raccoon running fast to the right on all fours, legs galloping, tail bouncing")


def p_fairy(k):
    bf(k, "base", "tiny regal fairy king, small man with a gold crown and a purple royal cape, green tunic, four "
       "translucent pale blue dragonfly wings, floating in the air, front view", 32, 40)
    anim(k, "base.png", "idle", "fairy hovering in place, dragonfly wings fluttering fast")


def p_bear(k):
    bf(k, "base", "huge brown honey bear walking on all fours, thick brown fur, lighter tan muzzle, side view facing "
       "right, big heavy body", 48, 44, direction="east")
    anim(k, "base.png", "walk", "big bear walking heavily to the right on all fours")
    anim(k, "base.png", "attack", "bear rearing up on its hind legs and swiping a big claw forward")


def p_hive(k):
    mapobj(k, "base", "a leafy green oak tree with a thick brown trunk and a big round golden beehive hanging from a "
           "branch, a few bees, whole tree visible, top-down three-quarter view", 80, 104)


def p_head(k):
    bf(k, "base", "a knight's dark black-steel closed helmet lying on its own on the ground, round helm with a visor "
       "slit, two glowing red eyes inside the slit, small red plume, no body", 28, 28)


def p_banshee(k):
    bf(k, "base", "banshee, a wailing ghost woman floating, very long flowing white hair, pale blue-white ghostly "
       "skin and tattered flowing gown, no legs, wispy fading tail, sad glowing eyes, front view", 32, 40)
    anim(k, "base.png", "idle", "ghost woman floating gently, hair and gown flowing and waving")
    anim(k, "base.png", "attack", "ghost woman screaming with mouth wide open, hair flaring outward, arms spread")


def p_hut(k):
    mapobj(k, "base", "a crooked ramshackle swamp witch hut standing on wooden stilts over murky water, mossy "
           "thatched slanted roof, crooked chimney with green smoke, a small wooden ladder, a black iron cauldron "
           "bubbling green on the ground in front, front view, whole building visible", 192, 160)


def p_toad(k):
    bf(k, "base", "giant swamp toad sitting, warty olive green and brown skin, big yellow eyes on top of its head, "
       "pale yellow throat and belly, wide mouth, front three-quarter view facing the viewer", 48, 44)
    anim(k, "base.png", "idle", "giant toad sitting still, its throat pouch puffing in and out slowly")
    anim(k, "base.png", "attack", "giant toad shooting its long sticky pink tongue straight out forward towards the "
         "viewer and pulling it back")
    bf(k, "full", "giant swamp toad bloated after swallowing something, swollen round fat belly, cheeks puffed, "
       "eyes squinting happily, warty olive green and brown skin, pale yellow belly, front three-quarter view",
       48, 44, init=d_of(k) / "base.png", strength=250)


def p_wisp(k):
    bf(k, "base", "will-o'-the-wisp, a small floating pale green-blue ghostly flame orb with a faint simple face "
       "with two dark eyes, soft glow, wispy flame tip", 32, 32)
    anim(k, "base.png", "idle", "ghostly flame orb flickering and bobbing gently in place")


def p_salamander(k):
    bf(k, "base", "regal fire salamander lizard queen, red-orange scaly lizard on four legs with a long tail, a crown "
       "of yellow flames on her head, golden belly, side view facing right", 48, 44, direction="east")
    anim(k, "base.png", "move", "salamander lizard crawling forward to the right, legs moving, tail swaying")
    anim(k, "base.png", "attack", "salamander lizard breathing a stream of fire forward to the right out of its mouth")


def p_golem(k):
    bf(k, "base", "molten lava golem, a hulking body of dark black-brown rock with glowing bright orange lava cracks, "
       "glowing orange eyes, big rocky fists, front view", 40, 40)
    anim(k, "base.png", "idle", "lava golem breathing slowly, lava cracks glowing brighter and dimmer")
    anim(k, "base.png", "move", "lava golem walking heavily forward, stomping")


def p_phoenix(k):
    bf(k, "base", "blazing phoenix firebird flying with wings spread wide, red orange and golden yellow fiery "
       "feathers, long flaming tail feathers, facing right", 48, 40, direction="east")
    anim(k, "base.png", "fly", "phoenix flying, flapping its fiery wings up and down")


def p_egg(k):
    bf(k, "base", "a glowing phoenix ember egg, oval egg with dark red shell and glowing orange-yellow ember cracks, "
       "standing upright, single object", 32, 40)


def p_mushroom(k):
    bf(k, "base", "a single red-capped toadstool mushroom with white spots and a thick white stem, single object", 32, 32)


def p_raccoon2(k="raccoon"):
    bf(k, "base2", "a chubby raccoon walking on all four legs, side view facing right, grey fur, black bandit mask "
       "around the eyes, bushy black-and-grey ringed tail, a small tied red cloth loot bundle strapped on its back, "
       "whole body visible, simple clean shape", 40, 32, direction="east")
    anim(k, "base2.png", "run2", "raccoon running fast to the right on all fours, legs galloping, tail bouncing")


def p_fairy2(k="fairy"):
    bf(k, "base2", "tiny fairy king floating, small bearded man with a gold crown, purple royal cape and green tunic, "
       "with four big transparent pale blue dragonfly wings spread out wide behind his back, front view, whole body "
       "visible", 32, 40)
    anim(k, "base2.png", "idle2", "tiny fairy king hovering in place, his dragonfly wings fluttering fast")


def p_salamander2(k="salamander"):
    bf(k, "base2", "a red salamander lizard queen walking on four short legs, side view facing right, long curled "
       "tail, yellow belly, black spots on her red back, a small gold crown with little yellow flames on her head, "
       "simple clean readable shape, whole body visible", 48, 40, direction="east")
    anim(k, "base2.png", "move2", "red salamander lizard crawling forward to the right, legs moving, tail swaying")
    anim(k, "base2.png", "attack2", "red salamander lizard opening its mouth and breathing a stream of orange fire "
         "forward to the right")


ITEMS = {
    "honey": "a small round clay honey pot full of golden honey dripping over the rim, a wooden honey dipper",
    "discount_card": "a small cream paper merchant coupon card with a red border and a shiny gold coin on it",
    "speed_charm": "a gold anklet ring with a small white feathered wing on its side",
    "mirror_charm": "a small round silver hand mirror amulet on a chain, shiny reflective glass",
    "stolen_sack": "a tied red-and-white cloth loot bundle sack with gold coins peeking out",
}
ICON = "game item icon, single object centred, bold black outline, simple readable shape, SNES Zelda item style"


def p_items(k):
    with ThreadPoolExecutor(5) as ex:
        list(ex.map(lambda it: bf(k, it[0], f"{it[1]}, {ICON}", 32, 32), ITEMS.items()))


PIPES = {"raccoon2": lambda k: p_raccoon2(), "fairy2": lambda k: p_fairy2(),
         "salamander2": lambda k: p_salamander2(), "knight2": p_humanoid, "ogre2": p_humanoid, "goblin": p_humanoid, "ogre": p_humanoid, "knight": p_humanoid, "witch": p_humanoid, "mimic": p_mimic,
         "raccoon": p_raccoon, "fairy": p_fairy, "bear": p_bear, "hive": p_hive, "head": p_head,
         "banshee": p_banshee, "hut": p_hut, "toad": p_toad, "wisp": p_wisp, "salamander": p_salamander,
         "golem": p_golem, "phoenix": p_phoenix, "egg": p_egg, "mushroom": p_mushroom, "items": p_items}


def gen(keys):
    def run(k):
        try:
            PIPES[k](k)
            print("DONE", k, flush=True)
        except Exception as e:  # keep the other pipelines going
            print("FAIL", k, repr(e)[:400], flush=True)
    ts = [threading.Thread(target=run, args=(k,)) for k in keys]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


# ---------------------------------------------------------------- image helpers
def load(p):
    return charpack.load(p)


def half(im):
    """2x pixel-art downscale (block mode), on an even canvas."""
    w, h = im.size
    return objects.mode_downscale(im, w // 2, h // 2)


def frames(key, prefix, pick=(1, 2, 3, 4)):
    return [load(d_of(key) / f"{prefix}_{i}.png") for i in pick]


def bob(im, dy):
    out = Image.new("RGBA", im.size)
    out.alpha_composite(im, (0, dy)) if dy >= 0 else out.alpha_composite(im.crop((0, -dy, im.width, im.height)), (0, 0))
    return out


def squash(im, rows=1):
    """Lift the upper part of a sprite by `rows` px (a breathing/stretch frame) keeping the base fixed."""
    bb = im.getbbox()
    mid = (bb[1] + bb[3]) // 2
    out = Image.new("RGBA", im.size)
    out.alpha_composite(im.crop((0, 0, im.width, mid)), (0, -rows))
    out.alpha_composite(im.crop((0, mid, im.width, im.height)), (0, mid))
    # fill the 1 px seam with the row just below it
    seam = im.crop((0, mid, im.width, mid + rows))
    out.alpha_composite(seam, (0, mid - rows))
    return out


def brighten(im, amt=1.25, warm=True):
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a and max(r, g, b) > 120:
                px[x, y] = (min(255, int(r * amt)), min(255, int(g * amt)), min(255, int(b * (amt if not warm else 1.05))), a)
    return out


def stone(im):
    """Grey stone recolour (keeps the value structure, slight blue-grey tint)."""
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a:
                v = int(0.35 * r + 0.5 * g + 0.15 * b)
                v = int(40 + v * 0.7)
                px[x, y] = (v, v, min(255, v + 8), a)
    return out


def ghostly(im, alpha=205):
    """Translucent body: everything except the dark outline gets partial alpha."""
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a and max(r, g, b) > 70:
                px[x, y] = (r, g, b, min(a, alpha))
    return out


def lid_breathe(im):
    """Closed chest 'breathing' frame: lift the lid (top ~45% of the chest) by 1 px and show a dark gap
    with two tooth pixels."""
    bb = im.getbbox()
    cut = bb[1] + int((bb[3] - bb[1]) * 0.45)
    out = Image.new("RGBA", im.size)
    out.alpha_composite(im.crop((0, cut, im.width, im.height)), (0, cut))
    out.alpha_composite(im.crop((0, 0, im.width, cut)), (0, -1))
    px = out.load()
    for x in range(bb[0] + 2, bb[2] - 2):
        if px[x, cut][3]:
            px[x, cut - 1] = (24, 12, 16, 255)
    for x in (bb[0] + 5, bb[2] - 6, (bb[0] + bb[2]) // 2):
        if px[x, cut - 1][3]:
            px[x, cut - 1] = (240, 236, 220, 255)
    return out


def behead(im, t=0):
    """Headless knight: remove the helmet above the shoulder line and draw an open neck collar with a
    purple smoke wisp (t = frame index, sways the wisp)."""
    im = im.copy()
    px = im.load()
    bb = im.getbbox()
    spans = {}
    for y in range(bb[1], bb[3]):
        xs = [x for x in range(im.width) if px[x, y][3]]
        spans[y] = (min(xs), max(xs)) if xs else None
    widths = {y: (s[1] - s[0] + 1) if s else 0 for y, s in spans.items()}
    # neck = the narrowest-row plateau in the 25-50 % band of the sprite height; cut just below it
    hgt = bb[3] - bb[1]
    band = range(bb[1] + hgt // 4, bb[1] + hgt // 2 + 1)
    wmin = min(widths[y] for y in band if widths[y])
    ys = [y for y in band if widths[y] == wmin]
    sh = ys[0]
    while widths.get(sh + 1, 0) == wmin:
        sh += 1
    sh += 1
    hx0, hx1 = spans[sh - 1] if spans.get(sh - 1) else spans[sh]
    if hx1 - hx0 > 7:
        c = (hx0 + hx1) // 2
        hx0, hx1 = c - 3, c + 2
    cx = (hx0 + hx1 + 1) // 2
    for y in range(0, sh):
        for x in range(im.width):
            px[x, y] = (0, 0, 0, 0)
    O, rim, hole = (16, 12, 20, 255), (92, 92, 108, 255), (60, 20, 70, 255)
    w = max(4, min(6, hx1 - hx0 + 1))
    x0 = cx - w // 2
    for x in range(x0, x0 + w):
        px[x, sh - 1] = O
        px[x, sh] = hole if x0 < x < x0 + w - 1 else rim
    px[x0 - 1, sh] = O
    px[x0 + w, sh] = O
    smoke = [(150, 60, 170, 255), (190, 110, 210, 255)]
    sway = (0, 1, 0, -1)[t % 4]
    for i, (dx, dy) in enumerate(((0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2), (0, 3), (1, 3), (1, 4), (2, 4),
                                  (2, 5), (1, 6))):
        x, y = cx - 1 + dx + (sway if dy > 3 else 0), sh - dy - 1
        if 0 <= y < im.height:
            px[x, y] = smoke[i % 2]
    return im


def mimic_frame(chest, gap, lift=0, tongue=False, eyes=True, H=34, top=8):
    """Mimic built from the real obj_chest_closed pixels: the lid (rows < 15) lifts by `gap` px over a dark
    mouth with teeth (+ glowing eyes / tongue); the whole chest is raised by `lift` px (hop)."""
    SEAM = 15
    W = chest.width
    out = Image.new("RGBA", (W, H))
    y0 = top - lift
    out.alpha_composite(chest.crop((0, SEAM, W, chest.height)), (0, y0 + SEAM))
    if gap:
        cp = chest.load()
        cols = [x for x in range(W) if cp[x, SEAM][3]]
        x0, x1 = min(cols), max(cols)
        px = out.load()
        g0 = y0 + SEAM - gap  # first gap row
        for y in range(g0, y0 + SEAM):
            for x in range(x0, x1 + 1):
                px[x, y] = (16, 10, 14, 255) if x in (x0, x1) else (70, 14, 30, 255) if y == y0 + SEAM - 1 else (40, 8, 20, 255)
        T = (244, 240, 224, 255)
        for x in range(x0 + 2, x1 - 1, 2):  # upper teeth
            px[x, g0] = T
            if gap >= 4 and x % 4 == (x0 + 2) % 4:
                px[x, g0 + 1] = T
        if gap >= 3:
            for x in range(x0 + 3, x1 - 1, 2):  # lower teeth
                px[x, y0 + SEAM - 1] = T
        if eyes and gap >= 4:
            for ex in (x0 + 6, x0 + 12):
                px[ex, g0 + 2] = (255, 220, 60, 255)
                px[ex + 1, g0 + 2] = (255, 220, 60, 255)
        if tongue:
            R, Rl, O = (200, 40, 60, 255), (240, 110, 120, 255), (60, 10, 20, 255)
            tx = x0 + 8
            for i, (dx, dy, c) in enumerate(((0, -1, R), (1, -1, R), (2, -1, R), (0, 0, R), (1, 0, Rl), (2, 0, R),
                                              (0, 1, R), (1, 1, Rl), (2, 1, R), (1, 2, R), (0, 2, O), (2, 2, O),
                                              (1, 3, O), (-1, 0, O), (3, 0, O), (-1, 1, O), (3, 1, O))):
                y = y0 + SEAM + dy
                px[tx + dx, y] = c
    out.alpha_composite(chest.crop((0, 0, W, SEAM)), (0, y0 - gap))
    return out


def fit_to(im, w, h):
    """Crop to content and block-mode downscale to fit w x h (keeps aspect)."""
    im = im.crop(im.getbbox())
    f = max(im.width / w, im.height / h, 1.0)
    return objects.mode_downscale(im, max(1, round(im.width / f)), max(1, round(im.height / f)))


def add_bundle(im):
    """Paint a small tied red-and-white cloth loot bundle on the raccoon's back (sprite faces right)."""
    im = im.copy()
    px = im.load()
    bb = im.getbbox()
    cx = bb[0] + int((bb[2] - bb[0]) * 0.42)
    top = next(y for y in range(im.height) if px[cx, y][3])
    O, R, Rd, Wt = (24, 12, 16, 255), (200, 44, 44, 255), (140, 24, 32, 255), (240, 232, 216, 255)
    shape = ["..OOOO..", ".ORRWRO.", "ORWRRRRO", "ORRRRWdO", ".OddddO.", "..OOOO.."]
    y0 = top - 3
    for j, row in enumerate(shape):
        for i, ch in enumerate(row):
            if ch != ".":
                px[cx - 4 + i, y0 + j] = {"O": O, "R": R, "W": Wt, "d": Rd}[ch]
    for (dx, dy) in ((0, -1), (-1, -2), (1, -2)):  # knot
        px[cx + dx, y0 + dy] = Wt
    px[cx - 2, y0 - 2] = O
    px[cx + 2, y0 - 2] = O
    return im


def toad_tongue(im, length, mx=25, my=16):
    """Pink tongue shooting straight down (towards the viewer) from the mouth at (mx, my)."""
    im = im.copy()
    px = im.load()
    O, T, Td, Tl = (40, 16, 24, 255), (236, 112, 128, 255), (188, 64, 88, 255), (252, 176, 184, 255)
    for y in range(my, my + length):
        px[mx - 1, y], px[mx, y], px[mx + 1, y] = Td, T, Td
        px[mx - 2, y], px[mx + 2, y] = O, O
    ty = my + length
    for dx, dy, c in ((-2, 0, T), (-1, 0, Tl), (0, 0, T), (1, 0, T), (2, 0, Td), (-2, 1, T), (-1, 1, T), (0, 1, T),
                      (1, 1, T), (2, 1, Td), (-1, 2, Td), (0, 2, Td), (1, 2, Td)):
        px[mx + dx, ty + dy] = c
    for dx, dy in ((-3, 0), (3, 0), (-3, 1), (3, 1), (-2, 2), (2, 2), (-1, 3), (0, 3), (1, 3), (-2, -1), (2, -1)):
        if px[mx + dx, ty + dy][:3] not in (T[:3], Td[:3], Tl[:3]):
            px[mx + dx, ty + dy] = O
    return im


def bloat(im, y0=19, f=1.22):
    """Bloated belly: widen everything below y0 around the centre column."""
    bb = im.getbbox()
    cx = (bb[0] + bb[2]) / 2
    lower = im.crop((0, y0, im.width, im.height))
    w2 = round(im.width * f)
    lower = lower.resize((w2, lower.height), Image.NEAREST)
    out = Image.new("RGBA", (im.width + 8, im.height))
    off = 4
    out.alpha_composite(lower, (int(off + cx - cx * f), y0))
    out.alpha_composite(im.crop((0, 0, im.width, y0)), (off, 0))
    return out


def fire_breath(im, length, mx=43, my=23, W=72):
    """Widen the canvas to W (centred) and paint a flame cone from the mouth (mx, my) to the right."""
    out = pad(im, W, im.height)
    off = (W - im.width) // 2
    px = out.load()
    ox = mx + off
    O, Rr, Or, Yl, Wh = (60, 16, 8, 255), (220, 60, 20, 255), (252, 144, 36, 255), (255, 220, 96, 255), (255, 248, 200, 255)
    for i in range(length):
        x = ox + i
        h = 1 + int(i * 0.45)  # half-height grows with distance
        flick = (i * 7) % 3 - 1
        for dy in range(-h - 1, h + 2):
            y = my + dy + (flick if i > 3 else 0)
            if not (0 <= x < W and 0 <= y < out.height):
                continue
            a = abs(dy)
            c = O if a == h + 1 else Rr if a == h else Or if a >= h * 0.5 else (Wh if i < length * 0.4 else Yl)
            if c == O and i > length - 2:
                continue
            px[x, y] = c
    return out


def pad(im, w, h):
    out = Image.new("RGBA", (w, h))
    out.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


# ---------------------------------------------------------------- code-drawn sprites
PIXIE_BODY = [
    "............",
    "....OOOO....",
    "...OhhhhO...",
    "...OhpphO...",
    "...OpEEpO...",
    "....OppO....",
    "...OddddO...",
    "....OddO....",
    ".....OO.....",
    "............",
    "............",
    "............",
]
WING_UP = [
    "OO........OO",
    "OwbO....ObwO",
    "ObbbO..ObbbO",
    ".ObbO..ObbO.",
    "..OO....OO..",
]
WING_MID = [
    "............",
    "OOO......OOO",
    "ObwbO..ObwbO",
    ".OObO..ObOO.",
    "...O....O...",
]
WING_DN = [
    "............",
    "............",
    "..OO....OO..",
    ".ObbO..ObbO.",
    "OwbbO..ObbwO",
    ".OOO....OOO.",
]
PIXIE_COL = {"O": (48, 24, 56), "h": (96, 160, 240), "p": (252, 196, 220), "E": (48, 24, 56),
             "d": (240, 110, 180), "b": (150, 214, 252), "w": (232, 248, 255)}


def _stamp(px, rows, dy=0):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != "." and 0 <= y + dy < 12:
                px[x, y + dy] = (*PIXIE_COL[ch], 255)


def draw_pixie():
    """10x10 pink/blue pixie (12x12 canvas), 4-frame wing flutter with a 1 px bob and a sparkle."""
    out = []
    for f, (wing, dy) in enumerate(((WING_UP, 0), (WING_MID, 1), (WING_DN, 2), (WING_MID, 1))):
        im = Image.new("RGBA", (12, 12))
        px = im.load()
        _stamp(px, wing, dy + 1)
        _stamp(px, PIXIE_BODY, dy + 1)
        sx, sy = ((0, 10), (11, 9), (1, 0), (10, 1))[f]
        if px[sx, sy][3] == 0:
            px[sx, sy] = (255, 248, 190, 255)
        out.append(im)
    return out


def draw_quicksand():
    """24x24 seamless bubbling bog mud (toroidal spiral swirls), 2 frames."""
    ramp = [(70, 50, 30), (88, 66, 38), (104, 80, 48), (122, 96, 60)]
    hi = (168, 140, 92)
    W = 24
    centres = [(6, 6, 1), (18, 15, -1), (17, 3, 1), (4, 18, -1)]
    frames_ = []
    for f in range(2):
        im = Image.new("RGBA", (W, W))
        px = im.load()
        for y in range(W):
            for x in range(W):
                best = None
                for cx, cy, s in centres:
                    dx = (x - cx + W / 2) % W - W / 2
                    dy = (y - cy + W / 2) % W - W / 2
                    d = math.hypot(dx, dy)
                    if best is None or d < best[0]:
                        best = (d, math.atan2(dy, dx), s)
                d, a, s = best
                v = math.sin(d * 0.8 - s * a + f * 0.9)
                k = 0 if v < -0.75 else 1 if v < 0.1 else 2 if v < 0.8 else 3
                if d < 1.5:
                    k = 1
                px[x, y] = (*ramp[k], 255)
        for i, (bx, by) in enumerate([(11, 9), (21, 21), (2, 12), (13, 20), (9, 1)]):
            if (i + f) % 2 == 0:  # bubble: ring with a highlight
                for ox, oy in ((0, -1), (1, -1), (-1, 0), (2, 0), (-1, 1), (2, 1), (0, 2), (1, 2)):
                    px[(bx + ox) % W, (by + oy) % W] = (50, 34, 20, 255)
                for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    px[(bx + ox) % W, (by + oy) % W] = (*ramp[3], 255)
                px[bx % W, by % W] = (*hi, 255)
            else:  # popped: small dark pit
                px[bx % W, by % W] = (50, 34, 20, 255)
                px[(bx + 1) % W, by % W] = (50, 34, 20, 255)
        frames_.append(im)
    return frames_


# ---------------------------------------------------------------- packing
SPRITES = {}


def put(name, rows, cell=None, post=None):
    """rows: [(anim, [imgs], fps)] -> sheets/<name>.png + manifest entry (feet 2 px above the cell bottom)."""
    cell = cell or charpack.fit_cell(rows)
    sh, anims = charpack.place(cell, rows)
    if post:
        sh = post(sh)
    sh.save(SHEETS / f"{name}.png")
    SPRITES[name] = {"file": f"{name}.png", "cell": list(cell), "anims": anims}
    print("packed", name, "cell", cell, {a: (v["frames"], v["fps"]) for a, v in anims.items()})


def save_manifest():
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
    m.setdefault("sprites", {}).update(SPRITES)
    m["sprites"] = dict(sorted(m["sprites"].items()))
    MANIFEST.write_text(json.dumps(m, indent=2))


def b_chunky(key, sheet, fix=None):
    chunky.pack(key, sheet, fix=fix)  # writes the entry via charpack.update_manifest (patched to manifest_minis2.json)


def b_mimic():
    k = "mimic"
    c = load(SHEETS / "obj_chest_closed.png")
    idle = [mimic_frame(c, 0), mimic_frame(c, 1, eyes=False)]
    move = [mimic_frame(c, 2), mimic_frame(c, 5, lift=3, tongue=True), mimic_frame(c, 4, lift=4, tongue=True),
            mimic_frame(c, 1, lift=1)]
    put("enemy_mimic", [("idle", idle, 2), ("move", move, 8)])


def b_raccoon():
    k = "raccoon"
    fl = lambda im: add_bundle(im.transpose(Image.FLIP_LEFT_RIGHT))  # base2 came out facing left
    base = fl(load(d_of(k) / "base2.png"))
    run = [bob(fl(f), dy) for f, dy in zip(frames(k, "run2"), (0, -1, 0, -1))]
    put("enemy_raccoon", [("idle", [base, squash(base)], 2), ("move", run, 10)])


def b_fairy():
    k = "fairy"
    fr = [half(f) for f in frames(k, "idle2")]
    put("enemy_fairy_king", [("idle", fr, 8)])
    put("enemy_pixie", [("idle", draw_pixie(), 8)])


def b_bear():
    k = "bear"
    put("enemy_bear", [("move", frames(k, "walk"), 6), ("attack", frames(k, "attack2"), 8)])
    im = fit_to(objects.clean(Image.open(d_of("hive") / "base.png")), 40, 50)
    put("obj_hive_tree", [("idle", [pad(im, 40, 52)], 1)], cell=(40, 52))


def b_head():
    im = fit_to(load(d_of("head") / "base.png"), 13, 13)
    im = pad(im, 14, 14)
    rolls = [im, im.rotate(-90), im.rotate(180), im.rotate(90)]
    put("enemy_knight_head", [("move", rolls, 8)], cell=(16, 16))


def b_banshee():
    k = "banshee"
    put("enemy_banshee", [("idle", frames(k, "idle"), 6), ("attack", frames(k, "attack"), 8)], post=ghostly)


def b_hut():
    im = fit_to(objects.clean(Image.open(d_of("hut") / "base.png")), 94, 78)
    put("obj_witch_hut", [("idle", [pad(im, 96, 80)], 1)], cell=(96, 80))


def b_toad():
    k = "toad"
    base = load(d_of(k) / "base2.png")  # front-view retry; idle pulse, tongue and bloat are local edits
    attack = [pad(toad_tongue(base, n), 56, 44) for n in (4, 11, 19, 8)]
    full = bloat(base)
    full = pad(full, 56, 44)
    put("enemy_toad", [("idle", [pad(base, 56, 44), pad(squash(base), 56, 44)], 2), ("attack", attack, 10),
                       ("full", [full, squash(full)], 2)])


def b_wisp():
    fr = [half(f) for f in frames("wisp", "idle")]
    put("enemy_wisp", [("idle", fr, 8)])
    put("tile_quicksand", [("idle", draw_quicksand(), 2)], cell=(24, 24)) if False else None
    q = draw_quicksand()
    sheet = Image.new("RGBA", (48, 24))
    for i, f in enumerate(q):
        sheet.alpha_composite(f, (i * 24, 0))
    sheet.save(SHEETS / "tile_quicksand.png")
    SPRITES["tile_quicksand"] = {"file": "tile_quicksand.png", "cell": [24, 24],
                                 "anims": {"idle": {"row": 0, "frames": 2, "fps": 2}}}
    print("packed tile_quicksand cell (24, 24)")


def b_salamander():
    k = "salamander"
    put("enemy_salamander_queen", [("move", frames(k, "move3"), 8), ("attack", [fire_breath(f, n) if n else pad(f, 72, f.height) for f, n in
                                   zip(frames(k, "attack3", (1, 2, 3, 2)), (0, 9, 18, 13))], 8),
                                   ("stone", [stone(load(d_of(k) / "base3.png"))], 1)])


def b_golem():
    k = "golem"
    idle = frames(k, "idle")
    put("enemy_lava_golem", [("idle", [idle[0], idle[2]], 2), ("move", frames(k, "move"), 6)])


def b_phoenix():
    put("enemy_phoenix", [("move", frames("phoenix", "fly"), 8)])
    im = pad(fit_to(load(d_of("egg") / "base.png"), 14, 18), 16, 20)
    put("obj_phoenix_egg", [("idle", [im, brighten(im)], 2)], cell=(16, 20))


def b_mushroom():
    im = load(d_of("mushroom") / "base.png")
    put("obj_mushroom", [("idle", [pad(fit_to(im, 15, 14), 16, 16)], 1)], cell=(16, 16))


def b_items():
    import itempack
    rows = []
    for it in ITEMS:
        im = itempack.cellify(itempack.shrink(Image.open(d_of("items") / f"{it}.png").convert("RGBA")))
        rows.append((it, [im], 1))
    sheet = Image.new("RGBA", (16, 16 * len(rows)))
    anims = {}
    for i, (a, [im], fps) in enumerate(rows):
        sheet.alpha_composite(im, (0, i * 16))
        anims[a] = {"row": i, "frames": 1, "fps": 1}
    sheet.save(SHEETS / "mini2_items.png")
    SPRITES["mini2_items"] = {"file": "mini2_items.png", "cell": [16, 16], "anims": anims}
    print("packed mini2_items")


BUILDS = {"goblin": lambda: b_chunky("goblin", "enemy_goblin"), "ogre": lambda: b_chunky("ogre2", "npc_ogre"),
          "knight": lambda: b_chunky("knight2", "enemy_knight_body", fix=_behead_fix()), "witch": lambda: b_chunky("witch", "npc_bog_witch"),
          "mimic": b_mimic, "raccoon": b_raccoon, "fairy": b_fairy, "bear": b_bear, "head": b_head,
          "banshee": b_banshee, "hut": b_hut, "toad": b_toad, "wisp": b_wisp, "salamander": b_salamander,
          "golem": b_golem, "phoenix": b_phoenix, "mushroom": b_mushroom, "items": b_items}


def _behead_fix():
    n = {"i": 0}

    def fix(anim_name, im):
        n["i"] += 1
        return behead(im, n["i"])
    return fix


def build(keys):
    for k in keys or BUILDS:
        try:
            BUILDS[k]()
        except Exception as e:
            print("BUILD FAIL", k, repr(e)[:300])
    save_manifest()


# ---------------------------------------------------------------- preview
def preview(only=None):
    m = json.loads(MANIFEST.read_text())["sprites"]
    mm = json.loads((SHEETS / "manifest.json").read_text())["sprites"]
    mcw, mch = mm["mage_fire"]["cell"]
    mage = Image.open(SHEETS / "mage_fire.png").convert("RGBA").crop((0, 0, mcw, mch))
    tiles = []
    for name, e in m.items():
        if only and name not in only:
            continue
        sh = Image.open(SHEETS / e["file"]).convert("RGBA")
        cw, ch = e["cell"]
        rows = sorted(e["anims"].items(), key=lambda kv: kv[1]["row"])
        cols = max(v["frames"] for _, v in rows)
        lab = 84
        h = max(len(rows) * (ch + 4), mch + 4)
        W = lab + cols * (cw + 4) + mcw + 8
        t = objects.checker(W, h + 4, 4)
        d = ImageDraw.Draw(t)
        for ri, (a, v) in enumerate(rows):
            y = 2 + ri * (ch + 4)
            for fi in range(v["frames"]):
                t.alpha_composite(sh.crop((fi * cw, v["row"] * ch, (fi + 1) * cw, (v["row"] + 1) * ch)),
                                  (lab + fi * (cw + 4), y))
            d.rectangle([0, y, lab - 4, y + 9], fill=(32, 32, 40, 255))
            d.text((1, y - 1), f"{a[:10]} {v['frames']}@{v['fps']}", fill=(240, 240, 240, 255))
        t.alpha_composite(mage, (W - mcw - 4, 2 + max(0, ch - mch)))
        t = t.resize((t.width * 2, t.height * 2), Image.NEAREST)
        tiles.append((f"{name} cell {cw}x{ch}", t))
    WMAX = 1600
    x = y = rowh = 0
    pos = []
    for lab_, t in tiles:
        if x and x + t.width > WMAX:
            x, y, rowh = 0, y + rowh + 22, 0
        pos.append((lab_, t, x, y))
        x += t.width + 12
        rowh = max(rowh, t.height)
    out = Image.new("RGBA", (WMAX, y + rowh + 22), (32, 32, 40, 255))
    d = ImageDraw.Draw(out)
    for lab_, t, x, y in pos:
        d.text((x + 2, y + 2), lab_, fill=(255, 230, 140, 255))
        out.alpha_composite(t, (x, y + 16))
    name = "preview_minis2.png" if not only else "preview_minis2_partial.png"
    out.save(GEN / name)
    print("wrote", GEN / name, out.size)


def spent():
    tot = 0.0
    for line in LOG.read_text().splitlines() if LOG.exists() else []:
        if "{" in line:
            try:
                u = json.loads(line[line.index("{"):])
            except ValueError:
                continue
            if u and u.get("type") == "generations":
                tot += u.get("generations", 0)
    print("generations logged by minis2:", tot)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen":
        gen(a[1:])
    elif a[0] == "build":
        build(a[1:])
    elif a[0] == "preview":
        preview(a[1:] or None)
    elif a[0] == "spent":
        spent()

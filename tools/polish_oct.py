"""October polish pass: redo enemy_toad / enemy_bear / enemy_salamander_queen + CAVE terrain theme 11.

python polish_oct.py paint                 rough PIL designs -> generated/polish_oct/paint_*.png (free)
python polish_oct.py gen <job> [<job>...]  PixelLab bitforge variants: toad toad2 toad3 bear bear2 bear3 sal sal2 sal3
python polish_oct.py anim <name> [...]     animate-with-text-v3: bear_move bear_attack sal_move sal_attack sal_move2
python polish_oct.py full | decos | decos2 toad_full bitforge (unused) / cave decos (first try, rock retry)
python polish_oct.py bases                 local fixes of the chosen variants -> base_*.png (free)
python polish_oct.py build                 sheets + manifest_minis2.json entries + terrain theme 11 (free)
(cave wall/water tilesets were made with pixellab.py tileset; see CAVE prompts and TW_RAW/TWATER_RAW)
python polish_oct.py preview               generated/preview_polish_oct.png
Raws and logs live in generated/polish_oct/.
"""
import json
import math
import random
import sys
import threading
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chars  # noqa: E402
import charpack  # noqa: E402
import pixellab  # noqa: E402
from pixellab import GEN, save_b64  # noqa: E402

ART = GEN.parent
SHEETS = ART / "sheets"
D = GEN / "polish_oct"
D.mkdir(parents=True, exist_ok=True)
chars.MYLOG = D / "usage.log"
chars.d_of = lambda name: D  # animtext saves frames here
SLOTS = threading.Semaphore(8)
STYLE = "SNES Zelda A Link to the Past style game sprite, crisp bold dark outline, rich natural colors, not neon"
NEG = "background, ground, floor, grass, shadow, text, frame, border, blurry, soft outline, multiple creatures, cartoon"


# ---------------------------------------------------------------- generation primitives
def bf(tag, desc, w, h, init=None, strength=350, seed=0, color=None, direction=None, neg=NEG):
    out = D / f"{tag}.png"
    if out.exists():
        return out
    body = {"description": f"{desc}, {STYLE}", "negative_description": neg,
            "image_size": {"width": w, "height": h}, "no_background": True,
            "outline": "single color black outline", "shading": "basic shading",
            "detail": "low detail", "view": "low top-down"}
    if direction:
        body["direction"] = direction
    if init:
        body["init_image"] = chars.b64(init)
        body["init_image_strength"] = int(strength)
    if color:
        body["color_image"] = chars.b64(color)
    if seed:
        body["seed"] = seed
    with SLOTS:
        r = chars.call("POST", "/create-image-bitforge", body)
    chars.log_charge(f"polish bitforge {tag}", r.get("usage"))
    save_b64(r["image"], out)
    print("saved", out.relative_to(ART), flush=True)
    return out


def animtext(first, prefix, action, frames=4):
    if (D / f"{prefix}_1.png").exists():
        return
    with SLOTS:
        chars.animtext("polish", str(first), prefix, action, frames)


# ---------------------------------------------------------------- painting helpers
def outline(im, col=(30, 20, 16, 255)):
    """Add a 1 px dark outline around the opaque mask (outside)."""
    out = im.copy()
    px, op = im.load(), out.load()
    W, H = im.size
    for y in range(H):
        for x in range(W):
            if px[x, y][3]:
                continue
            if any(0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy][3]
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                op[x, y] = col
    return out


def ell(d, cx, cy, rx, ry, c):
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=c)


TOAD = dict(o=(34, 26, 18, 255), d=(72, 62, 34, 255), m=(108, 96, 52, 255), l=(142, 128, 70, 255),
            w=(88, 70, 40, 255), wl=(164, 148, 86, 255), b=(206, 186, 116, 255), bd=(170, 148, 84, 255),
            e=(232, 188, 56, 255), k=(20, 14, 10, 255), mo=(60, 30, 26, 255))


def paint_toad(bloated=False):
    c = TOAD
    im = Image.new("RGBA", (48, 44))
    d = ImageDraw.Draw(im)
    # hind legs (folded lumps at the sides)
    for sx in (-1, 1):
        ell(d, 24 + sx * 17, 31, 6, 7, c["d"])
        ell(d, 24 + sx * 17, 30, 5, 5, c["m"])
        d.rectangle([24 + sx * 17 - 4, 37, 24 + sx * 17 + 4, 39], fill=c["d"])
    # body
    bw = 21 if bloated else 18
    ell(d, 24, 26, bw, 12 if bloated else 11, c["d"])
    ell(d, 24, 24, bw - 1, 10, c["m"])
    ell(d, 24, 21, bw - 6, 6, c["l"])
    # belly / throat
    ell(d, 24, 32 if bloated else 31, 13 if bloated else 10, 8 if bloated else 6, c["bd"])
    ell(d, 24, 31 if bloated else 30, 11 if bloated else 8, 6 if bloated else 4, c["b"])
    # front legs + toes
    for sx in (-1, 1):
        x = 24 + sx * 10
        d.rectangle([x - 2, 33, x + 2, 39], fill=c["m"])
        d.rectangle([x - 2 + (1 if sx > 0 else 0), 33, x - 1 + (1 if sx > 0 else 0), 39], fill=c["d"])
        for t in (-3, 0, 3):
            d.rectangle([x + t - 1, 39, x + t, 40], fill=c["l"])
    # eye bumps
    for sx in (-1, 1):
        ex = 24 + sx * 9
        ell(d, ex, 13, 5, 4, c["m"])
        ell(d, ex, 12, 4, 3, c["l"])
        ell(d, ex, 13, 3, 2, c["e"])
        d.rectangle([ex - 2, 13, ex + 2, 13], fill=c["k"])
    # mouth
    d.line([(9, 22), (14, 24), (24, 25), (34, 24), (39, 22)], fill=c["mo"], width=1)
    # warts
    rnd = random.Random(7)
    for _ in range(26):
        x, y = rnd.randint(8, 40), rnd.randint(14, 30)
        if im.getpixel((x, y))[:3] in (c["m"][:3], c["l"][:3], c["d"][:3]):
            im.putpixel((x, y), c["w"])
            im.putpixel((x - 1, y - 1), c["wl"]) if im.getpixel((x - 1, y - 1))[3] else None
    return outline(im, c["o"])


BEAR = dict(o=(26, 16, 12, 255), d=(54, 32, 20, 255), m=(86, 52, 30, 255), l=(118, 76, 44, 255),
            mz=(176, 138, 96, 255), mzd=(140, 104, 70, 255), n=(20, 12, 10, 255), cl=(220, 210, 190, 255))


def paint_bear():
    c = BEAR
    im = Image.new("RGBA", (48, 44))
    d = ImageDraw.Draw(im)
    # far legs (darker)
    d.rectangle([12, 30, 16, 40], fill=c["d"])
    d.rectangle([30, 30, 34, 40], fill=c["d"])
    # body + shoulder hump
    ell(d, 21, 25, 17, 11, c["m"])
    ell(d, 29, 19, 9, 8, c["m"])
    ell(d, 20, 20, 13, 5, c["l"])
    ell(d, 29, 15, 6, 3, c["l"])
    ell(d, 21, 32, 14, 3, c["d"])
    # near legs
    d.rectangle([6, 30, 11, 41], fill=c["m"])
    d.rectangle([33, 30, 38, 41], fill=c["m"])
    for x in (6, 33):
        d.rectangle([x, 40, x + 6, 41], fill=c["d"])
        for t in (2, 4, 6):
            im.putpixel((x + t, 41), c["cl"])
    # head
    ell(d, 39, 21, 6, 6, c["m"])
    ell(d, 38, 18, 4, 3, c["l"])
    ell(d, 36, 14, 2, 2, c["d"])  # ear
    ell(d, 43, 24, 4, 3, c["mz"])  # muzzle
    d.rectangle([40, 26, 45, 26], fill=c["mzd"])
    d.rectangle([46, 22, 47, 23], fill=c["n"])
    im.putpixel((40, 20), c["n"])  # eye
    return outline(im, c["o"])


SAL = dict(o=(30, 10, 12, 255), d=(92, 18, 24, 255), m=(150, 32, 30, 255), l=(196, 64, 40, 255),
           k=(40, 14, 18, 255), b=(250, 150, 40, 255), bl=(255, 210, 100, 255), g=(236, 184, 56, 255),
           gd=(170, 112, 30, 255), e=(255, 230, 80, 255))


def paint_salamander():
    c = SAL
    im = Image.new("RGBA", (48, 40))
    d = ImageDraw.Draw(im)
    # tail (curling up behind)
    pts = [(14, 26), (9, 27), (5, 26), (3, 23), (3, 20), (5, 18)]
    d.line(pts, fill=c["m"], width=4)
    d.line(pts[3:], fill=c["m"], width=2)
    # far legs
    for x in (15, 30):
        d.line([(x, 28), (x - 2, 33), (x - 3, 34)], fill=c["d"], width=2)
    # body
    ell(d, 23, 25, 12, 5, c["m"])
    ell(d, 23, 23, 10, 2, c["l"])
    d.rectangle([13, 28, 33, 29], fill=c["b"])
    d.rectangle([16, 29, 30, 29], fill=c["bl"])
    # dark spots
    for x, y in ((17, 23), (22, 22), (27, 23), (10, 25)):
        d.rectangle([x, y, x + 1, y], fill=c["k"])
    # neck + head
    ell(d, 35, 22, 5, 4, c["m"])
    d.polygon([(36, 18), (45, 21), (46, 24), (37, 26)], fill=c["m"])
    d.line([(38, 25), (45, 24)], fill=c["b"], width=1)  # glowing jaw
    im.putpixel((40, 20), c["e"])
    im.putpixel((41, 20), c["k"])
    # crown crest
    for i, (x, h) in enumerate(((34, 4), (36, 6), (38, 7), (40, 5))):
        d.line([(x, 19), (x, 19 - h)], fill=c["g"], width=1)
        im.putpixel((x, 19 - h), c["bl"])
    d.rectangle([33, 18, 41, 19], fill=c["gd"])
    # near legs
    for x in (18, 33):
        d.line([(x, 28), (x + 1, 33), (x + 3, 34)], fill=c["m"], width=2)
        im.putpixel((x + 4, 34), c["gd"])
    return outline(im, c["o"])


def palette_img(cols, name):
    im = Image.new("RGBA", (64, 64))
    dr = ImageDraw.Draw(im)
    for i in range(64):
        cc = cols[i % len(cols)]
        x, y = (i % 8) * 8, (i // 8) * 8
        dr.rectangle([x, y, x + 7, y + 7], fill=tuple(cc[:3]) + (255,))
    im.save(D / name)
    return D / name


def paint():
    paint_toad().save(D / "paint_toad.png")
    paint_toad(True).save(D / "paint_toad_full.png")
    paint_bear().save(D / "paint_bear.png")
    paint_salamander().save(D / "paint_salamander.png")
    palette_img(list(TOAD.values()), "pal_toad.png")
    palette_img(list(BEAR.values()), "pal_bear.png")
    palette_img(list(SAL.values()), "pal_salamander.png")
    big = Image.new("RGBA", (48 * 4 * 4, 44 * 4), (90, 110, 90, 255))
    for i, n in enumerate(("toad", "toad_full", "bear", "salamander")):
        im = Image.open(D / f"paint_{n}.png")
        big.alpha_composite(im.resize((im.width * 4, im.height * 4), Image.NEAREST), (i * 192, 0))
    big.save(D / "paint_preview.png")


# ---------------------------------------------------------------- jobs
TOAD_DESC = ("giant warty toad boss, huge wide flat heavy squat body, bumpy brown and olive skin covered in dark "
             "warts, two big golden eyes on top of its head, very wide mouth, pale yellowish belly and throat, "
             "thick front legs, sitting, front view facing the viewer, not a frog")
BEAR_DESC = ("huge grizzly bear walking on all fours, rich dark brown fur, lighter tan muzzle, black nose, big "
             "shoulder hump, heavy body, side view facing right")
SAL_DESC = ("regal menacing fire salamander queen, long crimson red lizard on four splayed legs, dark red scales "
            "with black spots, glowing orange belly, a golden crown-like crest of spikes on her head, long tail, "
            "side view facing right")


def job(name):
    if name.startswith("toad"):
        s = {"toad": 101, "toad2": 202, "toad3": 303}[name]
        bf(name, TOAD_DESC, 48, 44, init=D / "paint_toad.png", strength=350, seed=s, color=D / "pal_toad.png")
    elif name.startswith("bear"):
        s = {"bear": 111, "bear2": 222, "bear3": 333}[name]
        bf(name, BEAR_DESC, 48, 44, init=D / "paint_bear.png", strength=350, seed=s, color=D / "pal_bear.png",
           direction="east")
    elif name.startswith("sal"):
        s = {"sal": 121, "sal2": 232, "sal3": 343}[name]
        bf(name, SAL_DESC, 48, 40, init=D / "paint_salamander.png", strength=350, seed=s,
           color=D / "pal_salamander.png", direction="east")
    else:
        raise SystemExit(f"unknown job {name}")


def gen(names):
    def run(n):
        try:
            job(n)
            print("DONE", n, flush=True)
        except BaseException as e:  # keep the other jobs going
            print("FAIL", n, repr(e)[:400], flush=True)
    ts = [threading.Thread(target=run, args=(n,)) for n in names]
    for t in ts:
        t.start()
    for t in ts:
        t.join()




# ---------------------------------------------------------------- local edits of the chosen generations
def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def edit_bases():
    """Chosen variants: toad3, bear2, sal3 (cleaned) + small local fixes -> base_*.png."""
    toad = charpack.clean(Image.open(D / "toad3.png").convert("RGBA"))
    # browner, warmer olive (task asks brown/olive, not frog green)
    px = toad.load()
    for y in range(toad.height):
        for x in range(toad.width):
            r, g, b, a = px[x, y]
            if a and lum((r, g, b)) > 40 and not (r > 180 and g > 130 and b < 90):  # keep the golden eyes
                px[x, y] = (min(255, int(r * 1.0 + 3)), int(g * 0.94), int(b * 0.92), a)
    toad.save(D / "base_toad.png")

    bear = charpack.clean(Image.open(D / "bear2.png").convert("RGBA"))
    px = bear.load()
    for y in range(bear.height):
        for x in range(36, bear.width):
            r, g, b, a = px[x, y]
            if a and lum((r, g, b)) > 185:  # white blotch on the snout -> tan muzzle
                px[x, y] = (186, 146, 102, 255) if lum((r, g, b)) > 205 else (160, 120, 82, 255)
    bear.save(D / "base_bear.png")

    sal = charpack.clean(Image.open(D / "sal3.png").convert("RGBA"))
    px = sal.load()
    W, H = sal.size
    red = lambda c: c[3] and c[0] > 110 and c[1] < 90 and c[0] > c[1] * 1.6
    belly = []
    for y in range(22, H - 1):
        for x in range(8, 40):
            c, below, above = px[x, y], px[x, y + 1], px[x, y - 1]
            if red(c) and (below[3] == 0 or lum(below) < 45) and red(above):
                belly.append((x, y))
    for x, y in belly:
        px[x, y] = (250, 150, 40, 255)
        if red(px[x, y - 1]) and x % 3 != 0:
            px[x, y - 1] = (255, 196, 86, 255)
    # eye: glowing yellow with a dark slit
    px[43, 22] = (255, 230, 80, 255)
    px[44, 22] = (40, 14, 18, 255)
    sal.save(D / "base_sal.png")


def padded(src, w, h, dx=0):
    im = Image.open(src).convert("RGBA")
    out = Image.new("RGBA", (w, h))
    out.alpha_composite(im, ((w - im.width) // 2 + dx, h - im.height))
    p = D / f"{Path(src).stem}_{w}x{h}.png"
    out.save(p)
    return p


ANIMS = {
    "bear_move": ("base_bear.png", (64, 56, 0), "big heavy grizzly bear walking slowly to the right on all fours, "
                  "lumbering, legs stepping, head bobbing"),
    "bear_attack": ("base_bear.png", (64, 64, -4), "grizzly bear rears up high on its hind legs with both front "
                    "paws raised and claws out, then swipes its claws down hard in front of it"),
    "sal_move": ("base_sal.png", (56, 48, 0), "fire salamander lizard crawling forward to the right, legs "
                 "stepping, body and tail swaying side to side"),
    "sal_attack": ("base_sal.png", (64, 48, -6), "fire salamander lizard rears its head back then opens its "
                   "jaws wide and breathes a short burst of orange fire to the right"),
    "toad_idle": ("base_toad.png", (56, 48, 0), "giant toad sitting still, breathing, its throat puffing in and "
                  "out slowly"),
}


def gen_anim(name):
    src, (w, h, dx), action = ANIMS[name]
    animtext(padded(D / src, w, h, dx), name, action)
ANIMS["sal_move2"] = ("base_sal.png", (56, 48, 0), "the same dark red salamander lizard crawling forward to the "
                      "right, legs stepping in turn, tail swaying, keep its dark red colours and golden crest")


def bloat_toad():
    """Locally bloated toad (belly widened and lowered) -> paint for a bitforge clean-up."""
    im = Image.open(D / "base_toad.png").convert("RGBA")
    bb = im.getbbox()
    y0 = 20
    top = im.crop((0, 0, im.width, y0))
    low = im.crop((0, y0, im.width, im.height))
    f = 1.18
    low = low.resize((round(low.width * f), low.height + 1), Image.NEAREST)
    out = Image.new("RGBA", (im.width + 8, im.height + 1))
    out.alpha_composite(low, ((out.width - low.width) // 2, y0))
    out.alpha_composite(top, (4, 1))
    out = out.crop(((out.width - 48) // 2, out.height - 44, (out.width - 48) // 2 + 48, out.height))
    out.save(D / "paint_toad_full2.png")
    return D / "paint_toad_full2.png"


def gen_full():
    bf("toad_full", "the same giant warty toad boss, now bloated after swallowing something, swollen huge round "
       "fat belly, cheeks puffed, eyes squinting, " + TOAD_DESC.split(", ", 1)[1], 48, 44,
       init=bloat_toad(), strength=420, seed=404, color=D / "pal_toad.png")


def bulge(im, cx, cy, rx, ry, k=0.55, W=56, H=46):
    """Inflate the region around (cx, cy) (elliptical radius rx, ry) on a bigger canvas: nearest sampling of
    src = c + (p - c) * (r ** k) for normalised r < 1 keeps the outline and texture."""
    ox, oy = (W - im.width) // 2, H - im.height
    src = Image.new("RGBA", (W, H))
    src.alpha_composite(im, (ox, oy))
    cx, cy = cx + ox, cy + oy
    sp = src.load()
    out = Image.new("RGBA", (W, H))
    op = out.load()
    for y in range(H):
        for x in range(W):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            r = math.hypot(dx, dy)
            if r < 1 and r > 0:
                s = r ** k / r
                sx, sy = cx + dx * s * rx, cy + dy * s * ry
            else:
                sx, sy = x, y
            sx, sy = int(round(sx)), int(round(sy))
            if 0 <= sx < W and 0 <= sy < H:
                op[x, y] = sp[sx, sy]
    return out


# ---------------------------------------------------------------- build
import minis2  # noqa: E402  (pure helpers: toad_tongue, stone, squash, pad; also SPRITES/save_manifest)

chars.MYLOG = D / "usage.log"  # minis2 re-routes these on import; route them back
chars.d_of = lambda name: D


def ld(name):
    return charpack.load(D / name)


def shift(im, dx, W=None, H=None):
    W, H = W or im.width, H or im.height
    out = Image.new("RGBA", (W, H))
    out.alpha_composite(im, ((W - im.width) // 2 + dx, H - im.height))
    return out


def open_mouth(im, my=25, x0=17, x1=31):
    """Dark open mouth band with a pink inside, centred on the mouth line."""
    im = im.copy()
    px = im.load()
    for x in range(x0, x1 + 1):
        depth = 1 if x in (x0, x1) else 2 if x in (x0 + 1, x1 - 1) else 3
        for dy in range(depth):
            px[x, my + dy] = (60, 22, 26, 255) if dy < depth - 1 or depth == 1 else (150, 60, 72, 255)
    return im


def fire(im, mx, my, length, W):
    """Short flame cone to the right from the mouth (mx, my) on a canvas of width W (body kept in place)."""
    out = Image.new("RGBA", (W, im.height))
    out.alpha_composite(im, (0, 0))
    px = out.load()
    O, Rr, Or, Yl, Wh = (70, 18, 8, 255), (214, 58, 22, 255), (250, 142, 36, 255), (255, 214, 90, 255), (255, 246, 196, 255)
    for i in range(length):
        x = mx + i
        h = int(i * 0.5)
        flick = ((i * 5) % 3 - 1) if i > 3 else 0
        for dy in range(-h - 1, h + 2):
            y = my + dy + flick
            if not (0 <= x < W and 0 <= y < out.height):
                continue
            a = abs(dy)
            c = O if a == h + 1 else Rr if a == h else Or if a >= h * 0.5 else (Wh if i < length * 0.45 else Yl)
            if c == O and (i > length - 2 or i < 1):
                continue
            if px[x, y][3] and i < 2:
                continue
            px[x, y] = c
    for j, (dx, dy) in enumerate(((length, -1), (length + 1, 1), (length - 1, -int(length * 0.5) - 2))):
        if 0 <= mx + dx < W and 0 <= my + dy < out.height and j < (1 + length // 5):
            px[mx + dx, my + dy] = Yl if j % 2 == 0 else Or
    return out


def mouth_of(im, y0=14, y1=34, x_min=36):
    """(x, y) of the gap between the open jaws: the row with the least reach between two reaching rows."""
    px = im.load()
    reach = {}
    for y in range(y0, y1):
        xs = [x for x in range(x_min, im.width) if px[x, y][3]]
        reach[y] = max(xs) if xs else 0
    ys = sorted(reach)
    best = None
    for y in ys[1:-1]:
        up = max(reach[v] for v in ys if v < y)
        dn = max(reach[v] for v in ys if v > y)
        dip = min(up, dn) - reach[y]
        if dip >= 2 and (best is None or dip > best[0]):
            best = (dip, reach[y] + 1, y)
    if best:
        return best[1], best[2]
    y = max(reach, key=reach.get)
    return reach[y] + 1, y


def toad_rows():
    base = ld("base_toad.png")
    W, H = 60, 46
    b = shift(base, 0, W, H)
    puff = bulge(base, 24, 30, 14, 7, 1.8, W, H)  # throat swells
    mouth = open_mouth(base)
    attack = [shift(minis2.toad_tongue(mouth, n, mx=24, my=26), 0, W, H) for n in (3, 8, 12, 6)]
    full = [bulge(base, 24, 32, 30, 16, 1.7, W, H), bulge(base, 24, 32, 30, 16, 1.85, W, H)]
    return [("idle", [b, puff], 2), ("attack", attack, 10), ("full", full, 2)]


def slash(im):
    """Claw-swipe arcs (three short white/grey curved streaks) in front of the paws of the swipe frame."""
    im = im.copy()
    px = im.load()
    bb = im.getbbox()
    x0 = bb[2] - 6
    rows = [y for y in range(bb[1], bb[3]) if any(px[x, y][3] for x in range(bb[2] - 3, bb[2]))]
    yc = (rows[0] + rows[-1]) // 2 if rows else (bb[1] + bb[3]) // 2
    for k, off in enumerate((-4, 0, 4)):
        for t in range(9):
            a = -0.9 + t * 0.2
            x = int(round(x0 + 5 + off * 0.3 + 6 * math.cos(a)))
            y = int(round(yc + off + 7 * math.sin(a)))
            if 0 <= x < im.width and 0 <= y < im.height and not px[x, y][3]:
                px[x, y] = (250, 250, 240, 255) if 2 <= t <= 6 else (176, 176, 188, 255)
    return im


def bear_rows():
    move = [ld(f"bear_move_{i}.png") for i in (1, 2, 3, 4)]
    attack = [shift(ld(f"bear_attack_{i}.png"), 4) for i in (1, 2, 3, 4)]
    return [("move", move, 6), ("attack", attack, 8)]


SAL_OFF = 6  # body sits SAL_OFF px left of the cell centre in every row (keeps the flame from doubling the cell)


def sal_rows():
    W = 64
    move = [shift(ld(f"sal_move2_{i}.png"), -SAL_OFF + 0, W, 48) for i in (1, 2, 3, 4)]
    # attack frames were generated 6 px left of centre on a 64 canvas
    a0 = shift(ld("sal_move2_1.png"), -SAL_OFF, W, 48)
    a3, a4 = (shift(ld(f"sal_attack_{i}.png"), 6 - SAL_OFF) for i in (3, 4))
    m3, m4 = mouth_of(a3), mouth_of(a4)
    attack = [a0, fire(a3, *m3, 6, W), fire(a3, *m3, 12, W), fire(a4, *m4, 9, W)]
    st = minis2.stone(shift(ld("base_sal.png"), -SAL_OFF, W, 48))
    print("sal mouths", m3, m4)
    return [("move", move, 8), ("attack", attack, 8), ("stone", [st], 1)]


def build_sprites():
    minis2.SPRITES.clear()
    minis2.put("enemy_toad", toad_rows())
    minis2.put("enemy_bear", bear_rows())
    minis2.put("enemy_salamander_queen", sal_rows())
    minis2.save_manifest()


# ---------------------------------------------------------------- CAVE terrain (theme 11)
import colorsys  # noqa: E402
import shutil  # noqa: E402

THEME = 11
TW_RAW = GEN / "tiles_11_cave_wall_try3"   # chosen PixelLab wall set (organic rock lumps, no palette image)
TWATER_RAW = GEN / "tiles_11_cave_water"   # water set chained to TW_RAW's floor terrain id
TW = GEN / "tiles_11_cave_wall_final"
TWATER = GEN / "tiles_11_cave_water_recol"
CAVE = dict(
    floor="uneven natural cave ground of packed brown earth with irregular darker dirt patches and a few small "
          "scattered round grey pebbles, organic, no pattern, no tiles, SNES Zelda A Link to the Past style cave floor",
    wall="craggy natural cave rock mass seen from above, large irregular rounded brown-grey rock lumps with light "
         "tops and bluish-grey shadowed cracks between them, organic boulder shapes, no bricks, no tiles, no grid, "
         "SNES Zelda A Link to the Past style cave",
    wall_tr="dark bluish-grey shadow and rough rock edge at the foot of the cave wall",
    water="dark still underground cave pool water, deep blue-black water with faint teal ripple highlights, clearly "
          "liquid, SNES Zelda A Link to the Past style water, not neon",
    water_tr="wet dark rock bank edge around the pool",
)


def hsv(c):
    h, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
    return h * 360, s, v


def scale(c, f):
    return tuple(max(0, min(255, int(round(x * f)))) for x in c)


def floor_texture(n=32, seed=11):
    """Seamless (period n) packed-dirt cave floor with soft blotches and a few small pebbles."""
    rnd = random.Random(seed)
    base, dk, lt = (84, 71, 59), (74, 62, 52), (93, 79, 65)
    # wrapped value noise from a few random blobs
    val = [[0.0] * n for _ in range(n)]
    for _ in range(14):
        cx, cy, r, s = rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(2.5, 6), rnd.choice((-1, 1))
        for y in range(n):
            for x in range(n):
                dx = min(abs(x - cx), n - abs(x - cx))
                dy = min(abs(y - cy), n - abs(y - cy))
                d = math.hypot(dx * 0.8, dy)
                if d < r:
                    val[y][x] += s * (1 - d / r)
    im = Image.new("RGBA", (n, n))
    px = im.load()
    for y in range(n):
        for x in range(n):
            v = val[y][x] + rnd.uniform(-0.25, 0.25)
            px[x, y] = (*(dk if v < -0.45 else lt if v > 0.55 else base), 255)
    # pebbles: (dx, dy, colour) stamps; light top-left, dark bottom shadow (bluish)
    peb = [((0, 0), (140, 130, 118)), ((1, 0), (118, 110, 102)), ((0, 1), (118, 110, 102)), ((1, 1), (104, 96, 90)),
           ((0, 2), (58, 56, 64)), ((1, 2), (58, 56, 64))]
    small = [((0, 0), (126, 118, 108)), ((0, 1), (62, 58, 66))]
    spots = [(3, 5), (19, 3), (11, 14), (26, 18), (6, 24), (17, 27), (29, 9)]
    for i, (x, y) in enumerate(spots):
        for (dx, dy), c in (peb if i % 2 == 0 else small):
            px[(x + dx) % n, (y + dy) % n] = (*c, 255)
    for _ in range(10):  # single dark specks / tiny cracks
        x, y = rnd.randrange(n), rnd.randrange(n)
        px[x, y] = (62, 54, 48, 255)
    return im


def map_wall_colour(c):
    h, s, v = hsv(c)
    if v < 0.06:
        return (16, 14, 20)
    if v < 0.13:
        return (26, 24, 30)
    if 30 <= h <= 50 and s > 0.6:
        return None  # floor -> texture
    if 25 <= h <= 40 and s > 0.5 and v < 0.2:
        return (52, 46, 44)
    if v > 0.85:
        return (172, 158, 134)  # ledge rim highlight
    if s < 0.2 and 30 <= h <= 60:
        return scale((128, 120, 110), v / 0.51)
    if 50 <= h <= 65:
        return scale((150, 132, 108), v / 0.62)  # rock tops
    if 240 <= h <= 290 and v > 0.25:
        return scale((96, 82, 72), v / 0.44)  # rock body
    if 180 <= h <= 210 and v > 0.3:
        return scale((70, 72, 86), v / 0.38)  # cliff face, bluish grey
    if 210 <= h <= 250:
        return (38, 40, 52)  # deep shadow
    if s < 0.15:
        return scale((100, 90, 84), v / 0.42)
    return scale((84, 78, 64), v / 0.37)


WATER_RAMP = [(0.07, (12, 18, 30)), (0.12, (16, 24, 40)), (0.17, (20, 32, 50)), (0.3, (28, 46, 66)),
              (0.5, (40, 68, 88)), (0.7, (62, 100, 118)), (2.0, (108, 148, 160))]
BANK_RAMP = [(0.2, (52, 46, 44)), (0.3, (64, 54, 46)), (0.34, (74, 62, 52)), (0.4, (84, 71, 59)),
             (0.5, (98, 84, 70)), (0.6, (112, 98, 84)), (0.7, (128, 116, 100)), (2.0, (150, 138, 118))]


def ramp(r, v):
    return next(c for lim, c in r if v < lim)


def map_water_colour(c):
    h, s, v = hsv(c)
    if v < 0.05:
        return (14, 14, 20)
    if 140 <= h <= 245:
        return ramp(WATER_RAMP, v)
    if h < 35 or h > 320:
        return ramp(BANK_RAMP, v)
    return ramp(BANK_RAMP, v)


def tiles_of(d):
    info = json.loads((d / "tileset.json").read_text())
    return info, [d / f"tileset_tiles_{i}_image.png" for i in range(len(info["tileset"]["tiles"]))]


def build_cave_sets():
    import floorswap
    tex = floor_texture()
    tp = tex.load()
    for src, dst, fn in ((TW_RAW, TW, map_wall_colour), (TWATER_RAW, TWATER, map_water_colour)):
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        shutil.copy(src / "tileset.json", dst / "tileset.json")
        _, files = tiles_of(src)
        for f in files:
            im = Image.open(f).convert("RGBA")
            px = im.load()
            for y in range(im.height):
                for x in range(im.width):
                    c = px[x, y]
                    if not c[3]:
                        continue
                    m = fn(c[:3])
                    px[x, y] = tp[x % 32, y % 32] if m is None else (*m, 255)
            im.save(dst / f.name)
    fixed = floorswap.swap(TW, TWATER, GEN / "tiles_11_cave_water_fixed")
    return fixed


DECOS = {
    "stalagmite": "single brown-grey rock stalagmite cone rising from the cave floor, rounded pointed tip, a few small "
                  "rocks at its base, muted earthy colors, single object",
    "crystals": "small cluster of three glowing pale blue crystal shards growing out of a small dark rock, soft blue "
                "glow, single object",
    "pebbles": "small loose cluster of four round grey-brown pebbles and small stones lying on the ground, muted "
               "colors, single object",
}
DECO_NEG = "neon colors, background, ground, grass floor, text, frame, border"


def gen_decos(seeds=(51, 52)):
    def run(n, s, i):
        try:
            bf(f"deco_{n}_{i}", DECOS[n], 48, 48, seed=s, color=D / "pal_deco.png", neg=DECO_NEG)
        except BaseException as e:
            print("FAIL", n, repr(e)[:300], flush=True)
    ts = [threading.Thread(target=run, args=(n, s, i)) for n in DECOS for i, s in enumerate(seeds)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def gen_decos_retry():
    """Second try for the rock decos with a rock-only palette (the first palette's white came out as snow)."""
    palette_img([(42, 36, 40), (70, 58, 52), (96, 82, 72), (122, 106, 90), (150, 132, 110), (62, 64, 80),
                 (28, 24, 30), (110, 100, 94)], "pal_rock.png")
    DECOS["stalagmite"] = ("single tall cave stalagmite, a pointed cone of brown-grey rock rising from the ground, "
                           "rounded lumpy sides, lighter tip, darker base, muted earthy colors, single object")
    DECOS["pebbles"] = ("three or four small separate round grey-brown pebbles lying on the ground, small and sparse, "
                        "muted earthy colors")

    def run(n, s, i):
        try:
            bf(f"deco_{n}_{i}", DECOS[n], 48, 48, seed=s, color=D / "pal_rock.png", neg=DECO_NEG + ", snow, white")
        except BaseException as e:
            print("FAIL", n, repr(e)[:300], flush=True)
    ts = [threading.Thread(target=run, args=(n, s, i)) for n in ("stalagmite", "pebbles") for i, s in ((2, 61), (3, 62))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


ROCK_RAMP = [(0.16, (30, 26, 32)), (0.26, (54, 46, 46)), (0.36, (78, 66, 58)), (0.48, (100, 86, 74)),
             (0.62, (124, 108, 92)), (0.8, (148, 132, 110)), (2.0, (170, 156, 132))]
DECO_PICK = {"stalagmite": ("deco_stalagmite_0.png", True), "crystals": ("deco_crystals_1.png", False),
             "pebbles": ("deco_pebbles_0.png", True)}


def rock_recolour(im):
    im = im.copy()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            c = px[x, y]
            if c[3]:
                px[x, y] = (*ramp(ROCK_RAMP, hsv(c[:3])[2]), 255)
    return im


def deco_24(name):
    import objects
    f, rock = DECO_PICK[name]
    im = charpack.clean(Image.open(D / f).convert("RGBA"))
    if rock:
        im = rock_recolour(im)
    im = objects.mode_downscale(im, 22, 22)
    im = outline(im, (26, 22, 28, 255))
    # sit the object on the tile: bottom 2 px above the tile bottom, centred
    bb = im.getbbox()
    obj = im.crop(bb)
    out = Image.new("RGBA", (24, 24))
    out.alpha_composite(obj, ((24 - obj.width) // 2, 22 - obj.height))
    return out


RK = dict(o=(26, 22, 28, 255), l=(156, 140, 116, 255), h=(178, 164, 140, 255), m=(118, 102, 86, 255),
          d=(84, 72, 64, 255), s=(58, 56, 70, 255))


def draw_cone(px, cx, base, top, half):
    """Shaded rock cone: rows from top to base, width grows; lit from the upper left."""
    for y in range(top, base + 1):
        t = (y - top) / max(1, base - top)
        w = max(0.6, half * (t ** 0.8)) + (0.6 if (y * 7) % 5 == 0 else 0)  # lumpy sides
        x0, x1 = int(round(cx - w)), int(round(cx + w))
        for x in range(x0, x1 + 1):
            u = (x - x0) / max(1, x1 - x0)
            c = RK["h"] if u < 0.2 and t < 0.5 else RK["l"] if u < 0.35 else RK["m"] if u < 0.72 else RK["d"]
            if (x + y * 3) % 7 == 0 and RK["m"] == c:
                c = RK["d"]
            px[x, y] = c


def draw_stalagmite():
    im = Image.new("RGBA", (24, 24))
    px = im.load()
    for x in range(5, 20):  # bluish contact shadow
        if 4 <= x <= 19:
            px[x, 22] = RK["s"]
    draw_cone(px, 13, 21, 2, 5.5)
    draw_cone(px, 7, 21, 12, 2.6)  # small side spire
    for x, y in ((17, 20), (18, 20), (18, 21), (4, 21), (5, 21)):  # rubble
        px[x, y] = RK["m"]
    return outline(im, RK["o"])


def draw_pebbles():
    im = Image.new("RGBA", (24, 24))
    px = im.load()
    stones = [(5, 14, 4, 3), (12, 17, 5, 3), (15, 11, 3, 2), (7, 19, 2, 2), (18, 16, 2, 2)]
    for x0, y0, w, h in stones:
        for x in range(x0, x0 + w):
            px[x, y0 + h] = RK["s"]
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if w >= 3 and h >= 3 and x in (x0, x0 + w - 1) and y in (y0, y0 + h - 1):
                    continue  # round the corners
                c = RK["m"]
                if y == y0 or x == x0:
                    c = RK["l"]
                if y == y0 + h - 1 and x > x0:
                    c = RK["d"]
                px[x, y] = c
        px[x0 + 1, y0 + (1 if h >= 3 else 0)] = RK["h"]
    return outline(im, RK["o"])


def deco_final(name):
    if name == "stalagmite":
        return draw_stalagmite()
    if name == "pebbles":
        return draw_pebbles()
    return deco_24(name)


def build_terrain():
    from atlas import atlas
    out = SHEETS / "terrain"
    fixed = build_cave_sets()
    wall = atlas(TW, 24)
    water = atlas(fixed, 24)
    assert list(wall.crop((0, 0, 24, 24)).get_flattened_data()) == list(water.crop((72, 72, 96, 96)).get_flattened_data())
    wall.save(out / f"theme{THEME}_wall.png")
    water.save(out / f"theme{THEME}_water.png")
    decos = {}
    for n in ("stalagmite", "crystals", "pebbles"):
        f = f"theme{THEME}_deco_{n}.png"
        deco_final(n).save(out / f)
        how = {"stalagmite": "code-drawn (tools/polish_oct.py draw_stalagmite)",
               "pebbles": "code-drawn (tools/polish_oct.py draw_pebbles)"}.get(n)
        decos[n] = {"file": f, "prompt": DECOS[n]} if not how else {"file": f, "prompt": DECOS[n], "source": how}
    entry = {
        "index": THEME,
        "name": "CAVE",
        "wall": {"file": f"theme{THEME}_wall.png", "lower": "floor (walkable)", "upper": "wall (solid)",
                 "lower_prompt": CAVE["floor"], "upper_prompt": CAVE["wall"], "transition_prompt": CAVE["wall_tr"],
                 "floor_tile_index": 0, "wall_tile_index": 15,
                 "postprocess": "colours remapped to an earthy brown-grey cave palette and floor pixels replaced by a "
                                "seamless code-drawn packed-dirt/pebble texture (tools/polish_oct.py build_cave_sets)"},
        "water": {"file": f"theme{THEME}_water.png", "lower": "water (not walkable)", "upper": "floor (walkable)",
                  "lower_prompt": CAVE["water"], "upper_prompt": CAVE["floor"], "transition_prompt": CAVE["water_tr"],
                  "liquid_tile_index": 0, "floor_tile_index": 15,
                  "postprocess": "colours remapped to dark underground-pool blues, then tools/floorswap.py"},
        "decos": decos,
        "palette_images": {"wall": "generated/polish_oct/pal_wall.png", "deco": "generated/polish_oct/pal_deco.png"},
    }
    p = out / "terrain.json"
    doc = json.loads(p.read_text())
    doc["themes"] = [t for t in doc["themes"] if t["index"] != THEME] + [entry]
    p.write_text(json.dumps(doc, indent=2))
    print("terrain theme", THEME, "built")


# ---------------------------------------------------------------- preview
WALLS = ["11111111111",
         "11111111111",
         "11000000111",
         "11000000011",
         "11000000001",
         "11100000001",
         "11110000011",
         "11111111111",
         "11111111111"]
POOL = ["11111111111",
        "11111111111",
        "11111111111",
        "11111001111",
        "11110001111",
        "11111011111",
        "11111111111",
        "11111111111",
        "11111111111"]
DECO_AT = {(2, 2): "stalagmite", (7, 3): "crystals", (2, 3): "pebbles", (8, 4): "stalagmite", (6, 5): "pebbles",
           (3, 2): "crystals"}


def room():
    out = SHEETS / "terrain"
    wall = Image.open(out / f"theme{THEME}_wall.png").convert("RGBA")
    water = Image.open(out / f"theme{THEME}_water.png").convert("RGBA")
    T = 24
    img = Image.new("RGBA", (10 * T, 8 * T))
    tile = lambda a, k: a.crop(((k % 4) * T, (k // 4) * T, (k % 4) * T + T, (k // 4) * T + T))
    for r in range(8):
        for c in range(10):
            corner = lambda g: [int(g[r][c]), int(g[r][c + 1]), int(g[r + 1][c]), int(g[r + 1][c + 1])]
            wk = sum(v << s for v, s in zip(corner(WALLS), (3, 2, 1, 0)))
            pk = sum(v << s for v, s in zip(corner(POOL), (3, 2, 1, 0)))
            assert wk == 0 or pk == 15, (c, r)
            img.alpha_composite(tile(wall, wk) if pk == 15 else tile(water, pk), (c * T, r * T))
            if (c, r) in DECO_AT:
                assert wk == 0 and pk == 15, (c, r)
                img.alpha_composite(Image.open(out / f"theme{THEME}_deco_{DECO_AT[(c, r)]}.png").convert("RGBA"),
                                    (c * T, r * T))
    return img


def checker(w, h, s=8):
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=(72, 72, 84, 255) if (x // s + y // s) % 2 else (96, 96, 110, 255))
    return im


def preview():
    Z = 2
    pairs = [(n, Image.open(D / f"old_{n}.png").convert("RGBA"), Image.open(SHEETS / f"{n}.png").convert("RGBA"))
             for n in ("enemy_toad", "enemy_bear", "enemy_salamander_queen")]
    m = json.loads((SHEETS / "manifest_minis2.json").read_text())["sprites"]
    rm = room().resize((240 * Z, 192 * Z), Image.NEAREST)
    pad, lab = 12, 14
    colw = max(o.width for _, o, _ in pairs) * Z
    neww = max(n.width for _, _, n in pairs) * Z
    W = max(pad * 3 + colw + neww, pad * 2 + rm.width)
    H = pad + sum(lab + max(o.height, n.height) * Z + pad for _, o, n in pairs) + lab + rm.height + pad
    sheet = Image.new("RGBA", (W, H), (36, 36, 44, 255))
    d = ImageDraw.Draw(sheet)
    y = pad
    for name, old, new in pairs:
        cell = m[name]["cell"]
        anims = ", ".join(f"{a} x{v['frames']}" for a, v in m[name]["anims"].items())
        d.text((pad, y), f"{name}  OLD", fill=(230, 200, 200, 255))
        d.text((pad * 2 + colw, y), f"NEW  cell {cell[0]}x{cell[1]}  rows: {anims}", fill=(200, 240, 200, 255))
        y += lab
        for x0, im in ((pad, old), (pad * 2 + colw, new)):
            big = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
            bg = checker(big.width, big.height)
            bg.alpha_composite(big)
            sheet.alpha_composite(bg, (x0, y))
        y += max(old.height, new.height) * Z + pad
    d.text((pad, y), "theme 11 CAVE: sample 10x8-tile room (wall atlas + pool from water atlas + decos), x2",
           fill=(230, 230, 230, 255))
    y += lab
    sheet.alpha_composite(rm, (pad, y))
    sheet.convert("RGB").save(GEN / "preview_polish_oct.png")
    print("preview", GEN / "preview_polish_oct.png", sheet.size)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "paint":
        paint()
    elif cmd == "gen":
        gen(a[1:])
    elif cmd == "anim":
        for n in a[1:]:
            gen_anim(n)
    elif cmd == "full":
        gen_full()
    elif cmd == "decos":
        gen_decos()
    elif cmd == "decos2":
        gen_decos_retry()
    elif cmd == "bases":
        edit_bases()
    elif cmd == "build":
        build_sprites()
        build_terrain()
    elif cmd == "preview":
        preview()
    else:
        sys.exit(__doc__)

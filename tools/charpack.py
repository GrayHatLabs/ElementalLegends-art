"""Pack generated character/creature/item frames into game sheets + manifest entries.

python charpack.py <kind> [<kind> ...]   (kinds are listed in KINDS below)
python charpack.py all

Sheet contract: transparent PNG, fixed cell, one ROW per animation, frames left to
right, side rows face RIGHT. Every frame is anchored by its canvas centre (x) and
the row's lowest opaque pixel (y) so the feet sit 2 px above the cell bottom
without jitter. Element kinds get 5 sheets (fire/ice/storm/earth/neutral) made by
recolouring a masked part of the sprite (cloth, body) onto element ramps.
"""
import colorsys
import json
import sys
from pathlib import Path
from PIL import Image

ART = Path(__file__).resolve().parent.parent
GEN = ART / "generated"
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest.json"

RAMPS = {  # dark, mid, light (same as recolor.py) + neutral
    "fire": [(88, 16, 8), (200, 40, 0), (252, 152, 56)],
    "ice": [(8, 40, 120), (0, 112, 236), (164, 228, 252)],
    "storm": [(56, 16, 96), (128, 48, 200), (200, 150, 240)],
    "earth": [(16, 60, 8), (32, 124, 16), (152, 216, 88)],
    "neutral": [(44, 44, 56), (116, 116, 132), (200, 200, 212)],
}
ELEMENTS = ("fire", "ice", "storm", "earth", "neutral")


def load(p):
    return clean(Image.open(p).convert("RGBA"))


def clean(im, tol=18):
    """Remove an opaque flat background (flood fill from the border) and stray specks/lines
    that are not part of the main figure."""
    im = im.copy()
    px = im.load()
    W, H = im.size
    corners = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    if all(c[3] > 0 for c in corners):
        bg = corners[0]
        close = lambda c: c[3] > 0 and sum(abs(c[i] - bg[i]) for i in range(3)) <= tol
        stack = [(x, y) for x in range(W) for y in (0, H - 1)] + [(x, y) for y in range(H) for x in (0, W - 1)]
        seen = set()
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or not (0 <= x < W and 0 <= y < H):
                continue
            seen.add((x, y))
            if close(px[x, y]):
                px[x, y] = (0, 0, 0, 0)
                stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    # connected components (8-connectivity)
    comp = {}
    comps = []
    for y in range(H):
        for x in range(W):
            if px[x, y][3] == 0 or (x, y) in comp:
                continue
            cid = len(comps)
            pts = []
            stack = [(x, y)]
            comp[(x, y)] = cid
            while stack:
                cx, cy = stack.pop()
                pts.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in comp and px[nx, ny][3] > 0:
                            comp[(nx, ny)] = cid
                            stack.append((nx, ny))
            comps.append(pts)
    if len(comps) > 1:
        main = max(comps, key=len)
        xs = [p[0] for p in main]
        ys = [p[1] for p in main]
        bx0, bx1, by0, by1 = min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3
        for pts in comps:
            if pts is main:
                continue
            inside = all(bx0 <= x <= bx1 and by0 <= y <= by1 for x, y in pts)
            if len(pts) < 3 or not inside:
                for x, y in pts:
                    px[x, y] = (0, 0, 0, 0)
    return im


# ---------------------------------------------------------------- frame sources
def char_rows(name):
    """Rows for a 4-direction character in generated/char_<name>/ (walk = first 4-frame anim)."""
    d = GEN / f"char_{name}"
    info = json.loads((d / "character.json").read_text())
    walk = {}
    for ai, anim in enumerate(info.get("animations", [])):
        for di, dd in enumerate(anim.get("directions", [])):
            n = len(dd.get("frames", []))
            files = [d / f"animations_{ai}_directions_{di}_frames_{f}.png" for f in range(n)]
            walk.setdefault(dd["direction"], files)
    return [
        ("idle_down", [load(d / "rotation_urls_south.png")], 2),
        ("idle_up", [load(d / "rotation_urls_north.png")], 2),
        ("idle_side", [load(d / "rotation_urls_east.png")], 2),
        ("walk_down", [load(p) for p in walk["south"]], 8),
        ("walk_up", [load(p) for p in walk["north"]], 8),
        ("walk_side", [load(p) for p in walk["east"]], 8),
    ]


def frame_rows(name, spec):
    """spec: list of (anim, [file names in char_<name>/], fps)."""
    d = GEN / f"char_{name}"
    return [(a, [load(d / f) for f in files], fps) for a, files, fps in spec]


# ---------------------------------------------------------------- packing
def fit_cell(rows, pad_top=1):
    """Smallest even cell that holds every frame when centred on its canvas centre."""
    half = 0
    height = 0
    for _, imgs, _ in rows:
        bottom = max(im.getbbox()[3] for im in imgs)
        for im in imgs:
            l, t, r, b = im.getbbox()
            cx = im.width / 2
            half = max(half, cx - l, r - cx)
            height = max(height, bottom - t)
    w = int(half * 2 + 0.999) + 2
    w += w % 2
    h = height + 2 + pad_top
    h += h % 2
    return w, h


def place(cell, rows):
    cw, ch = cell
    cols = max(len(r[1]) for r in rows)
    sheet = Image.new("RGBA", (cw * cols, ch * len(rows)))
    anims = {}
    for ri, (aname, imgs, fps) in enumerate(rows):
        bottom = max(im.getbbox()[3] for im in imgs)
        for fi, im in enumerate(imgs):
            # crop a cell-sized window around the canvas centre / row bottom
            left = im.width // 2 - cw // 2
            top = bottom - (ch - 2)
            win = Image.new("RGBA", (cw, ch))
            win.alpha_composite(im.crop((left, top, left + cw, top + ch)))
            sheet.alpha_composite(win, (fi * cw, ri * ch))
        anims[aname] = {"row": ri, "frames": len(imgs), "fps": fps}
    return sheet, anims


# ---------------------------------------------------------------- recolouring
def hsv(px):
    r, g, b = px[:3]
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s, v


def make_mask(sheet, rule):
    if isinstance(rule, list):
        out = set()
        for r in rule:
            out |= make_mask(sheet, r)
        return out
    return _mask1(sheet, rule)


def _mask1(sheet, rule):
    """rule: ("grey", smax, vmin, vmax) or ("hue", [(h0, h1), ...], smin, vmin)."""
    px = sheet.load()
    m = set()
    for y in range(sheet.height):
        for x in range(sheet.width):
            p = px[x, y]
            if p[3] == 0:
                continue
            h, s, v = hsv(p)
            if rule[0] == "grey":
                ok = s < rule[1] and rule[2] < v < rule[3]
            else:
                ok = s >= rule[2] and v >= rule[3] and any(
                    (h0 <= h <= h1) if h0 <= h1 else (h >= h0 or h <= h1) for h0, h1 in rule[1])
            if ok:
                m.add((x, y))
    return m


def lerp(c0, c1, t):
    return tuple(int(round(c0[i] + (c1[i] - c0[i]) * t)) for i in range(3))


def ramp_at(rp, t):
    t = min(max(t, 0.0), 1.0)
    return lerp(rp[0], rp[1], t / 0.5) if t < 0.5 else lerp(rp[1], rp[2], (t - 0.5) / 0.5)


def recolor(sheet, mask, rp, lo=0.08, hi=0.92):
    px = sheet.load()
    vs = [hsv(px[x, y])[2] for x, y in mask]
    if not vs:
        return sheet.copy()
    vs.sort()
    vmin, vmax = vs[int(len(vs) * 0.02)], vs[int(len(vs) * 0.98) - 1]
    out = sheet.copy()
    op = out.load()
    for x, y in mask:
        p = px[x, y]
        v = hsv(p)[2]
        t = (v - vmin) / max(vmax - vmin, 1e-6)
        op[x, y] = (*ramp_at(rp, lo + (hi - lo) * t), p[3])
    return out


# ---------------------------------------------------------------- manifest
def update_manifest(entries):
    SHEETS.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
    m.setdefault("sprites", {}).update(entries)
    MANIFEST.write_text(json.dumps(m, indent=2))


def build(kind):
    cfg = KINDS[kind]
    rows = cfg["rows"]()
    cell = cfg.get("cell") or fit_cell(rows)
    sheet, anims = place(cell, rows)
    d = GEN / f"char_{kind}"
    sheet.save(d / "sheet_raw.png")
    entries = {}
    if cfg.get("mask"):
        mask = make_mask(sheet, cfg["mask"])
        for el in ELEMENTS:
            name = f"{cfg['sheet']}_{el}"
            out = sheet if (el == "neutral" and cfg.get("neutral_keep", True)) else recolor(sheet, mask, RAMPS[el])
            out.save(SHEETS / f"{name}.png")
            entries[name] = {"file": f"{name}.png", "cell": list(cell), "anims": anims}
    else:
        name = cfg["sheet"]
        sheet.save(SHEETS / f"{name}.png")
        entries[name] = {"file": f"{name}.png", "cell": list(cell), "anims": anims}
    update_manifest(entries)
    print(kind, "cell", cell, "->", ", ".join(entries))
    return entries


def anim_rows(name, spec):
    """spec: list of (anim, file prefix, fps); uses generated frames 1..4 (frame 0 is the input)."""
    d = GEN / f"char_{name}"
    rows = []
    for a, pre, fps in spec:
        files = sorted(d.glob(f"{pre}_*.png"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        use = files[1:5] if len(files) >= 5 else files
        rows.append((a, [load(p) for p in use], fps))
    return rows


KINDS = {
    "skeleton": {"sheet": "enemy_skeleton", "rows": lambda: char_rows("skeleton"),
                 "mask": ("hue", [(330, 25)], 0.35, 0.2), "neutral_keep": False},
    "zombie": {"sheet": "enemy_zombie", "rows": lambda: char_rows("zombie")},
    "dryad": {"sheet": "npc_dryad", "rows": lambda: char_rows("dryad")},
    "merchant": {"sheet": "npc_merchant", "rows": lambda: char_rows("merchant")},
    "gravelord": {"sheet": "enemy_gravelord", "rows": lambda: char_rows("gravelord")},
    "imp": {"sheet": "enemy_imp", "rows": lambda: char_rows("imp"),
            "mask": ("hue", [(200, 300)], 0.08, 0.2)},
    "bat": {"sheet": "enemy_bat", "rows": lambda: anim_rows("bat", [("idle", "fly", 8), ("move", "fly", 10)]),
            "mask": ("grey", 0.25, 0.2, 0.9)},
    "slime": {"sheet": "enemy_slime", "rows": lambda: anim_rows("slime", [("idle", "draw_idle", 6), ("move", "draw_move", 8)]),
              "mask": ("grey", 0.3, 0.2, 0.93)},
    "ghost": {"sheet": "enemy_ghost", "rows": lambda: anim_rows("ghost", [("idle", "idle", 6), ("move", "move", 8)]),
              "mask": ("grey", 0.3, 0.3, 1.01)},
    "golem": {"sheet": "enemy_golem", "rows": lambda: anim_rows("golem", [("idle", "idle", 4), ("move", "move", 6)]),
              "mask": [("grey", 0.35, 0.2, 1.01), ("hue", [(235, 300)], 0.15, 0.2)], "neutral_keep": False},
    "generator": {"sheet": "enemy_generator", "rows": lambda: anim_rows("generator", [("idle", "idle", 6)])},
    "treant": {"sheet": "enemy_treant", "rows": lambda: anim_rows("treant", [("idle", "idle", 4), ("move", "move", 6)])},
    "hoarddragon": {"sheet": "enemy_hoarddragon",
                    "rows": lambda: anim_rows("hoarddragon", [("idle", "idle", 3), ("awake", "awake", 6)])},
}


if __name__ == "__main__":
    ks = sys.argv[1:]
    if ks == ["all"]:
        ks = list(KINDS)
    for k in ks:
        build(k)

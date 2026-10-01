"""Chunky SNES-proportion character regeneration (uses chars.py helpers).

python chunky.py character <name> "<desc>" <size> <proportions-json-or-preset> [seed]
python chunky.py animate <name> "<action>" <dirs> [frames]
python chunky.py fetch <name>

Everything lands in generated/chunky_<name>/. Charges are logged to generated/char_usage.log
via chars.log_charge (tag prefixed with 'chunky').
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chars  # noqa: E402
import pixellab  # noqa: E402
from pixellab import GEN, download, find_urls  # noqa: E402


def d_of(name):
    d = GEN / f"chunky_{name}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state(name, upd=None):
    p = d_of(name) / "state.json"
    s = json.loads(p.read_text()) if p.exists() else {}
    if upd:
        s.update(upd)
        p.write_text(json.dumps(s, indent=2))
    return s


def fetch(name):
    s = state(name)
    d = d_of(name)
    info = pixellab.call("GET", f"/characters/{s['character_id']}")
    (d / "character.json").write_text(json.dumps(info, indent=2))
    for path, url in find_urls(info):
        download(url, d / (path.replace(".", "_") + ".png"))
    print("fetched", name)


def parse_props(p):
    if p.strip().startswith("{"):
        d = json.loads(p)
        d.setdefault("type", "custom")
        return d
    return {"type": "preset", "name": p}


def character(name, desc, size, props="chibi", seed="0"):
    size = int(size)
    body = {
        "description": desc,
        "image_size": {"width": size, "height": size},
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "low detail",
        "view": "low top-down",
        "proportions": parse_props(props),
    }
    if int(seed):
        body["seed"] = int(seed)
    r = chars.call("POST", "/create-character-with-4-directions", body)
    cid = r["character_id"]
    state(name, {"character_id": cid, "description": desc, "size": size, "proportions": body["proportions"]})
    print("character", cid)
    if r.get("background_job_id"):
        chars.wait(r["background_job_id"], f"chunky {name} character")
    fetch(name)


def animate(name, action, dirs="south,north,east", frames=4):
    s = state(name)
    body = {
        "character_id": s["character_id"],
        "action_description": action,
        "animation_name": action,
        "mode": "v3",
        "frame_count": int(frames),
        "keep_first_frame": False,
        "directions": dirs.split(","),
    }
    r = chars.call("POST", "/animate-character", body)
    print(name, "animate response", json.dumps({k: v for k, v in r.items() if k != "usage"})[:400], flush=True)
    for jid in r.get("background_job_ids") or []:
        chars.wait(jid, f"chunky {name} animate")
    fetch(name)


# ---------------------------------------------------------------- packing
import colorsys  # noqa: E402
import charpack  # noqa: E402
from PIL import Image  # noqa: E402

SHEETS = charpack.SHEETS


def rows_of(name, walk_anim=None):
    """Rows from generated/chunky_<name>/ (walk = first 4-frame anim per direction, or the
    animation index walk_anim[direction] if given)."""
    d = d_of(name)
    info = json.loads((d / "character.json").read_text())
    walk = {}
    for ai, anim in enumerate(info.get("animations", [])):
        for di, dd in enumerate(anim.get("directions", [])):
            n = len(dd.get("frames", []))
            files = [d / f"animations_{ai}_directions_{di}_frames_{f}.png" for f in range(n)]
            if walk_anim and walk_anim.get(dd["direction"]) is not None:
                if walk_anim[dd["direction"]] == ai:
                    walk[dd["direction"]] = files
            else:
                walk.setdefault(dd["direction"], files)
    L = charpack.load
    return [
        ("idle_down", [L(d / "rotation_urls_south.png")], 2),
        ("idle_up", [L(d / "rotation_urls_north.png")], 2),
        ("idle_side", [L(d / "rotation_urls_east.png")], 2),
        ("walk_down", [L(p) for p in walk["south"]], 8),
        ("walk_up", [L(p) for p in walk["north"]], 8),
        ("walk_side", [L(p) for p in walk["east"]], 8),
    ]


def mage_recolor(sheet, rp):
    """recolor.py's fixed-scale ramp mapping, with a mask widened to the lavender-grey robe."""
    out = sheet.copy()
    px, op = sheet.load(), out.load()
    lo, hi = 0.2, 0.72
    for y in range(sheet.height):
        for x in range(sheet.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            h *= 360
            if (s < 0.25 or (215 <= h <= 290 and s < 0.45)) and 0.18 < v < 0.76:
                v = 0.451 + (v - 0.612) * 0.6  # match the old grey robe values (0.45 main)
                t =min(max((v - lo) / (hi - lo), 0), 1)
                op[x, y] = (*charpack.ramp_at(rp, 0.1 + 0.75 * t), a)
    return out


def mage_fix(anim, im):
    """North rows: the white hair under the hat reads as a faceless beard; darken it to
    grey hair (recoloured with the robe, like the old sheet's dark back-of-head)."""
    if not anim.endswith("_up"):
        return im
    im = im.copy()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and min(r, g, b) > 200 and max(r, g, b) - min(r, g, b) < 30:
                px[x, y] = (84, 80, 104, a)
            elif a and min(r, g, b) > 150 and max(r, g, b) - min(r, g, b) < 40:
                px[x, y] = (70, 66, 90, a)
    return im


def clip_row_strays(rows, slack=1):
    """Remove pixels hanging below the row's median foot line (e.g. a sword tip swung below the
    feet in one frame) so every frame in the row keeps the same baseline."""
    out = []
    for a, imgs, fps in rows:
        bottoms = sorted(im.getbbox()[3] for im in imgs)
        limit = bottoms[len(bottoms) // 2] + slack
        new = []
        for im in imgs:
            if im.getbbox()[3] > limit:
                im = im.copy()
                im.paste((0, 0, 0, 0), (0, limit, im.width, im.height))
                im = charpack.clean(im)
            new.append(im)
        out.append((a, new, fps))
    return out


def visible_heights(rows):
    return [im.getbbox()[3] - im.getbbox()[1] for _, imgs, _ in rows for im in imgs]


def pack(name, sheet, variants=None, mask=None, neutral_keep=True, cell=None, walk_anim=None, fix=None):
    """variants: None (single sheet), 'mage' (4 element sheets via mage_recolor) or
    'elements' (5 sheets via charpack.recolor on mask)."""
    rows = rows_of(name, walk_anim)
    if fix:
        rows = [(a, [fix(a, im) for im in imgs], fps) for a, imgs, fps in rows]
    rows = clip_row_strays(rows)
    cell = cell or charpack.fit_cell(rows)
    sh, anims = charpack.place(cell, rows)
    sh.save(d_of(name) / "sheet_raw.png")
    entries = {}
    if variants == "mage":
        for el in ("fire", "ice", "storm", "earth"):
            n = f"{sheet}_{el}"
            mage_recolor(sh, charpack.RAMPS[el]).save(SHEETS / f"{n}.png")
            entries[n] = {"file": f"{n}.png", "cell": list(cell), "anims": anims}
    elif variants == "elements":
        m = charpack.make_mask(sh, mask)
        for el in charpack.ELEMENTS:
            n = f"{sheet}_{el}"
            out = sh if (el == "neutral" and neutral_keep) else charpack.recolor(sh, m, charpack.RAMPS[el])
            out.save(SHEETS / f"{n}.png")
            entries[n] = {"file": f"{n}.png", "cell": list(cell), "anims": anims}
    else:
        sh.save(SHEETS / f"{sheet}.png")
        entries[sheet] = {"file": f"{sheet}.png", "cell": list(cell), "anims": anims}
    charpack.update_manifest(entries)
    hs = visible_heights(rows)
    print(name, "cell", cell, "visible h", min(hs), "-", max(hs), "->", ", ".join(entries))
    return entries


if __name__ == "__main__":
    a = sys.argv[1:]
    {"character": character, "animate": animate, "fetch": fetch}[a[0]](*a[1:])

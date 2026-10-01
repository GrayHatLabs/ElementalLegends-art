"""Character/creature/item generation helpers for Elemental Legends (uses pixellab.py).

python chars.py character <name> "<desc>" <size> [proportions] [template]
python chars.py walk <name> [dirs]                   (animate walk, 4 frames)
python chars.py animate <name> "<action>" <dirs> [frames]
python chars.py bitforge <name> <outfile> "<desc>" <w> <h> [style_strength] [seed] [negative]
python chars.py animtext <name> <first_frame.png> <outprefix> "<action>" [frames]
python chars.py fetch <name>
python chars.py spent                                (sum of this script's charges)

Everything lands in generated/char_<name>/. Charges are also logged per job in
generated/char_usage.log so this task's spend can be separated from other agents'.
The API key is handled by pixellab.py and never printed.
"""
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixellab  # noqa: E402
from pixellab import GEN, download, find_urls, find_b64, save_b64  # noqa: E402

ART = GEN.parent
MAGE = GEN / "mage" / "rotation_urls_south.png"
MYLOG = GEN / "char_usage.log"


def call(method, path, body=None, tag=""):
    """pixellab.call with retry while the account is at its concurrent-job limit (HTTP 429)."""
    for _ in range(120):
        try:
            return pixellab.call(method, path, body)
        except SystemExit as e:
            if "HTTP 429" not in str(e):
                raise
            time.sleep(20)
    raise RuntimeError("still rate limited")


def log_charge(tag, usage):
    with MYLOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {tag} {json.dumps(usage)}\n")


def wait(job_id, tag):
    t0 = time.time()
    while time.time() - t0 < 3600:
        j = pixellab.call("GET", f"/background-jobs/{job_id}")
        st = j.get("status")
        if st in ("completed", "failed"):
            log_charge(f"{tag} job={job_id} status={st}", j.get("usage"))
            if st == "failed":
                raise RuntimeError(f"job failed: {json.dumps(j.get('last_response'))[:600]}")
            return j
        time.sleep(5)
    raise RuntimeError("timeout")


def b64(path):
    return {"type": "base64", "base64": base64.b64encode(Path(path).read_bytes()).decode()}


def d_of(name):
    d = GEN / f"char_{name}"
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


def character(name, desc, size, proportions="chibi", template=""):
    size = int(size)
    body = {
        "description": desc,
        "image_size": {"width": size, "height": size},
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "low detail",
        "view": "low top-down",
        "proportions": {"type": "preset", "name": proportions},
    }
    if template:
        body["template_id"] = template
    r = call("POST", "/create-character-with-4-directions", body)
    cid = r["character_id"]
    state(name, {"character_id": cid, "description": desc, "size": size, "proportions": proportions})
    print("character", cid)
    if r.get("background_job_id"):
        wait(r["background_job_id"], f"{name} character")
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
    r = call("POST", "/animate-character", body)
    for jid in r.get("background_job_ids") or []:
        wait(jid, f"{name} animate")
    fetch(name)


def walk(name, dirs="south,north,east"):
    animate(name, "walking", dirs, 4)


def style_img(w, h):
    """The wizard pasted (or centre-cropped) onto a w x h transparent canvas."""
    import io
    from PIL import Image
    im = Image.open(MAGE).convert("RGBA")
    im = im.crop(im.getbbox())
    canvas = Image.new("RGBA", (w, h))
    if im.width > w or im.height > h:
        l = max(0, (im.width - w) // 2)
        t = max(0, (im.height - h) // 2)
        im = im.crop((l, t, l + min(w, im.width), t + min(h, im.height)))
    canvas.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    buf = io.BytesIO()
    canvas.save(buf, "PNG")
    return {"type": "base64", "base64": base64.b64encode(buf.getvalue()).decode()}


def bitforge(name, outfile, desc, w, h, strength=40, seed=0, negative=""):
    body = {
        "description": desc,
        "image_size": {"width": int(w), "height": int(h)},
        "no_background": True,
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "low detail",
        "view": "low top-down",
    }
    if float(strength) > 0:
        body["style_image"] = style_img(int(w), int(h))
        body["style_strength"] = float(strength)
    if int(seed):
        body["seed"] = int(seed)
    if negative:
        body["negative_description"] = negative
    r = pixellab.call("POST", "/create-image-bitforge", body)
    log_charge(f"{name} bitforge {outfile}", r.get("usage"))
    save_b64(r["image"], d_of(name) / outfile)
    print("saved", d_of(name) / outfile)


def animtext(name, first, outprefix, action, frames=4):
    body = {
        "first_frame": b64(first),
        "action": action,
        "frame_count": int(frames),
        "no_background": True,
    }
    r = call("POST", "/animate-with-text-v3", body)
    j = wait(r["background_job_id"], f"{name} animtext {outprefix}")
    d = d_of(name)
    imgs = list(find_b64(j.get("last_response") or {}))
    if not imgs:
        for i, (p, url) in enumerate(find_urls(j.get("last_response") or {})):
            download(url, d / f"{outprefix}_{i}.png")
        print("saved url frames", outprefix)
        return
    for i, (p, img) in enumerate(imgs):
        save_b64(img, d / f"{outprefix}_{i}.png")
    print("saved", len(imgs), "frames", outprefix)


def spent():
    tot = 0.0
    seen = set()
    if MYLOG.exists():
        for line in MYLOG.read_text().splitlines():
            parts = line.split(" ", 2)
            try:
                u = json.loads(line[line.index("{"):]) if "{" in line else None
            except ValueError:
                u = None
            if u and u.get("type") == "generations":
                tot += u.get("generations", 0)
    print("generations spent by chars.py:", tot)


if __name__ == "__main__":
    a = sys.argv[1:]
    cmds = {"character": character, "walk": walk, "animate": animate, "bitforge": bitforge,
            "animtext": animtext, "fetch": fetch, "spent": spent}
    cmds[a[0]](*a[1:])

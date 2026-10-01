"""Small PixelLab API client for Elemental Legends art.

The API key is read from the PIXELLAB_API_KEY environment variable, or from the
Windows user environment (registry) if this process started before it was set.
The key is never printed or written to disk.

Usage:
  python pixellab.py balance
  python pixellab.py character <name> "<description>" [size]
  python pixellab.py animate <name> "<action>" [frames]
  python pixellab.py image <name> "<description>" [w] [h] [color_png] [negative]
  python pixellab.py tileset <name> "<lower>" "<upper>" [size] [transition] [color_png] [transition_size] [lower_base_id] [upper_base_id]
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.pixellab.ai/v2"
ART = Path(__file__).resolve().parent.parent
GEN = ART / "generated"
LOG = GEN / "usage.log"


def api_key():
    key = os.environ.get("PIXELLAB_API_KEY")
    if not key and sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "PIXELLAB_API_KEY")[0]
        except OSError:
            key = None
    if not key:
        sys.exit("PIXELLAB_API_KEY is not set")
    return key.strip()


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + api_key())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read().decode(errors='replace')[:800]}")
    if isinstance(out, dict) and out.get("usage"):
        GEN.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {path} {json.dumps(out['usage'])}\n")
    return out


def wait_job(job_id, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = call("GET", f"/background-jobs/{job_id}")
        if j.get("status") == "completed":
            return j
        if j.get("status") == "failed":
            sys.exit(f"job {job_id} failed: {json.dumps(j.get('last_response'))[:800]}")
        time.sleep(5)
    sys.exit(f"job {job_id} timed out")


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ElementalLegends art tool)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def save_b64(img, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(img["base64"]))


def save_state(name, state):
    d = GEN / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(json.dumps(state, indent=2))


def load_state(name):
    p = GEN / name / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def find_urls(obj, prefix=""):
    """Yield (path, url) for every image URL in a nested response."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from find_urls(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find_urls(v, f"{prefix}{i}.")
    elif isinstance(obj, str) and obj.startswith("http") and ".png" in obj.split("?")[0]:
        yield prefix.rstrip("."), obj


def cmd_fetch(name):
    """Re-download all images of an already generated character (free)."""
    st = load_state(name)
    info = call("GET", f"/characters/{st['character_id']}")
    (GEN / name / "character.json").write_text(json.dumps(info, indent=2))
    for path, url in find_urls(info):
        download(url, GEN / name / (path.replace(".", "_") + ".png"))
        print("saved", path)


def cmd_balance():
    print(json.dumps(call("GET", "/balance"), indent=2))


def cmd_character(name, desc, size=32):
    body = {
        "description": desc,
        "image_size": {"width": size, "height": size},
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "low detail",
        "view": "low top-down",
        "proportions": {"type": "preset", "name": "chibi"},
    }
    r = call("POST", "/create-character-with-4-directions", body)
    cid = r["character_id"]
    save_state(name, {"character_id": cid, "description": desc, "size": size})
    print("character", cid, "job", r.get("background_job_id"))
    if r.get("background_job_id"):
        wait_job(r["background_job_id"])
    info = call("GET", f"/characters/{cid}")
    (GEN / name / "character.json").write_text(json.dumps(info, indent=2))
    for path, url in find_urls(info):
        download(url, GEN / name / (path.replace(".", "_") + ".png"))
        print("saved", path)


def cmd_animate(name, action, frames=4, dirs="south,north,east,west"):
    st = load_state(name)
    body = {
        "character_id": st["character_id"],
        "action_description": action,
        "animation_name": action,
        "mode": "v3",
        "frame_count": int(frames),
        "keep_first_frame": False,
        "directions": dirs.split(","),
    }
    r = call("POST", "/animate-character", body)
    print("animation jobs", r.get("background_job_ids"))
    for jid in r.get("background_job_ids") or []:
        wait_job(jid)
    info = call("GET", f"/characters/{st['character_id']}")
    (GEN / name / "character.json").write_text(json.dumps(info, indent=2))
    for path, url in find_urls(info):
        download(url, GEN / name / (path.replace(".", "_") + ".png"))
    print("saved animation frames for", name)


def b64img(path):
    return {"type": "base64", "base64": base64.b64encode(Path(path).read_bytes()).decode()}


def cmd_image(name, desc, w=32, h=32, color="", negative=""):
    body = {
        "description": desc,
        "image_size": {"width": int(w), "height": int(h)},
        "no_background": True,
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "low detail",
        "view": "low top-down",
    }
    if color:
        body["color_image"] = b64img(color)
    if negative:
        body["negative_description"] = negative
    r = call("POST", "/create-image-bitforge", body)
    save_b64(r["image"], GEN / name / "image.png")
    print("saved", GEN / name / "image.png")


def find_b64(obj, prefix=""):
    """Yield (path, base64-image-dict) for every inline image in a nested response."""
    if isinstance(obj, dict):
        if obj.get("type") == "base64" and "base64" in obj:
            yield prefix.rstrip("."), obj
            return
        for k, v in obj.items():
            yield from find_b64(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find_b64(v, f"{prefix}{i}.")


def cmd_tileset(name, lower, upper, size=32, transition="", color="", tsize="0.25", lower_base="", upper_base=""):
    """Top-down Wang tileset (async). Saves the raw response and every tile image."""
    body = {
        "lower_description": lower,
        "upper_description": upper,
        "transition_description": transition,
        "tile_size": {"width": int(size), "height": int(size)},
        "view": "high top-down",
        "outline": "selective outline",
        "shading": "medium shading",
        "detail": "medium detail",
        "transition_size": float(tsize),
    }
    if color:
        body["color_image"] = b64img(color)
    if lower_base:
        body["lower_base_tile_id"] = lower_base
    if upper_base:
        body["upper_base_tile_id"] = upper_base
    r = call("POST", "/create-tileset", body)
    d = GEN / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "create.json").write_text(json.dumps(r, indent=2)[:20000])
    tid = r.get("tileset_id") or r.get("id")
    if r.get("background_job_id"):
        wait_job(r["background_job_id"])
    info = call("GET", f"/tilesets/{tid}") if tid else r
    (d / "tileset.json").write_text(json.dumps(info, indent=2))
    n = 0
    for path, url in find_urls(info):
        download(url, d / (path.replace(".", "_") + ".png"))
        n += 1
    for path, img in find_b64(info):
        save_b64(img, d / (path.replace(".", "_") + ".png"))
        n += 1
    save_state(name, {"tileset_id": tid, "lower": lower, "upper": upper, "size": size,
                      "transition": transition, "color_image": color, "transition_size": tsize,
                      "lower_base": lower_base, "upper_base": upper_base})
    print("tileset", tid, "saved", n, "images")


def cmd_resize(src, dest, w, h, desc="pixel art"):
    """PixelLab's pixel-art-aware resize of a local image."""
    from PIL import Image

    sw, sh = Image.open(src).size
    body = {
        "description": desc,
        "reference_image": {"type": "base64", "base64": base64.b64encode(Path(src).read_bytes()).decode()},
        "reference_image_size": {"width": sw, "height": sh},
        "target_size": {"width": int(w), "height": int(h)},
        "no_background": True,
    }
    r = call("POST", "/resize", body)
    save_b64(r["image"], Path(dest))
    print("saved", dest)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmds = {"balance": cmd_balance, "fetch": cmd_fetch, "character": cmd_character, "animate": cmd_animate,
            "image": cmd_image, "tileset": cmd_tileset, "resize": cmd_resize}
    cmds[a[0]](*a[1:])



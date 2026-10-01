"""Boss art generation for Elemental Legends (uses pixellab.py; never touches its files).

python bosses.py base <boss> <outfile> "<desc>" <w> <h> [style_strength] [seed] [detail]
python bosses.py anim <boss> <first.png> <outprefix> "<action>" [frames] [last.png]
python bosses.py pack <boss> <idle_prefix> <attack_prefix> [hurt_files,comma,sep] [idle_idx] [attack_idx]
python bosses.py preview
python bosses.py spent

Raw files land in generated/boss_<boss>/. Each charged job is logged once in
generated/boss_usage.log. Sheets -> sheets/boss_<boss>.png, entries -> sheets/manifest_bosses.json.
The API key is handled by pixellab.py and never printed.
"""
import base64
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixellab import call, download, find_b64, find_urls, save_b64, GEN  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

ART = GEN.parent
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest_bosses.json"
MAGE = GEN / "mage" / "rotation_urls_south.png"
MYLOG = GEN / "boss_usage.log"
BOSSES = ["treant", "guardian", "golem", "dragon", "sorcerer", "darksorcerer"]


def log_charge(tag, usage):
    with MYLOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {tag} {json.dumps(usage)}\n")


def d_of(boss):
    d = GEN / f"boss_{boss}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def b64(path):
    return {"type": "base64", "base64": base64.b64encode(Path(path).read_bytes()).decode()}


def style_img(w, h):
    im = Image.open(MAGE).convert("RGBA")
    im = im.crop(im.getbbox())
    canvas = Image.new("RGBA", (w, h))
    canvas.alpha_composite(im, ((w - im.width) // 2, h - im.height - 2))
    buf = io.BytesIO()
    canvas.save(buf, "PNG")
    return {"type": "base64", "base64": base64.b64encode(buf.getvalue()).decode()}


def base(boss, outfile, desc, w, h, strength=30, seed=0, detail="medium detail", init="", init_strength=300):
    body = {
        "description": desc,
        "image_size": {"width": int(w), "height": int(h)},
        "no_background": True,
        "outline": "single color black outline",
        "shading": "medium shading",
        "detail": detail,
        "view": "low top-down",
        "direction": "south",
        "negative_description": "cute, chibi, cartoon, childish, big eyes, neon colors, text, background, ground, shadow blob",
    }
    if float(strength) > 0:
        body["style_image"] = style_img(int(w), int(h))
        body["style_strength"] = int(float(strength))
    if int(seed):
        body["seed"] = int(seed)
    if init:
        body["init_image"] = b64(d_of(boss) / init)
        body["init_image_strength"] = int(init_strength)
    r = call("POST", "/create-image-bitforge", body)
    log_charge(f"{boss} base {outfile}", r.get("usage"))
    save_b64(r["image"], d_of(boss) / outfile)
    print("saved", d_of(boss) / outfile)


def anim(boss, first, outprefix, action, frames=4, last=""):
    d = d_of(boss)
    first = d / first if not Path(first).is_absolute() else Path(first)
    body = {"first_frame": b64(first), "action": action, "frame_count": int(frames), "no_background": True}
    if last:
        body["last_frame"] = b64(d / last)
    for _ in range(60):  # the account allows few concurrent jobs, shared with other generators
        try:
            r = call("POST", "/animate-with-text-v3", body)
            break
        except SystemExit as e:
            if "429" not in str(e):
                raise
            print("busy (429), retrying in 30 s", flush=True)
            time.sleep(30)
    else:
        sys.exit("gave up after repeated 429")
    jid = r["background_job_id"]
    print("job", jid, flush=True)
    t0 = time.time()
    while True:
        j = call("GET", f"/background-jobs/{jid}")
        st = j.get("status")
        if st in ("completed", "failed"):
            log_charge(f"{boss} anim {outprefix} job={jid} status={st}", j.get("usage") or r.get("usage"))
            if st == "failed":
                sys.exit(f"job failed: {json.dumps(j.get('last_response'))[:600]}")
            break
        if time.time() - t0 > 2400:
            sys.exit("timeout")
        time.sleep(5)
    lr = j.get("last_response") or {}
    imgs = list(find_b64(lr))
    if imgs:
        for i, (_, img) in enumerate(imgs):
            save_b64(img, d / f"{outprefix}_{i}.png")
        print("saved", len(imgs), "frames", outprefix)
    else:
        urls = list(find_urls(lr))
        for i, (_, url) in enumerate(urls):
            download(url, d / f"{outprefix}_{i}.png")
        print("saved", len(urls), "url frames", outprefix)


def clean(im):
    """Drop faint alpha noise so bboxes are tight."""
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][3] < 40:
                px[x, y] = (0, 0, 0, 0)
            elif px[x, y][3] < 255:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 255)
    return im


def frames_of(boss, prefix, idx):
    d = d_of(boss)
    return [clean(Image.open(d / f"{prefix}_{i}.png")) for i in idx]


def pack(boss, idle_prefix, attack_prefix, hurt="", idle_idx="0,1,2,3", attack_idx="0,1,2,3"):
    rows = [("idle", frames_of(boss, idle_prefix, [int(i) for i in idle_idx.split(",")]), 6),
            ("attack", frames_of(boss, attack_prefix, [int(i) for i in attack_idx.split(",")]), 8)]
    if hurt:
        rows.append(("hurt", [clean(Image.open(d_of(boss) / f)) for f in hurt.split(",")], 6))
    # Crop every frame to its content, keep x relative to canvas centre.
    bw = bh = 0
    crops = []
    # All rows come from the same base canvas: one shared baseline keeps rows aligned too.
    bottom = max(im.getbbox()[3] for _, imgs, _ in rows for im in imgs)
    top = min(im.getbbox()[1] for _, imgs, _ in rows for im in imgs)
    for name, imgs, fps in rows:
        row = []
        for im in imgs:
            l, t, r, b = im.getbbox()
            cx = im.width / 2
            half = max(cx - l, r - cx)
            bw = max(bw, int(2 * half + 0.999))
            bh = max(bh, bottom - top)
            row.append(im)
        crops.append((name, row, fps, top, bottom))
    cw = bw + 6
    ch = bh + 6
    cw += cw % 2
    cols = max(len(r[1]) for r in crops)
    sheet = Image.new("RGBA", (cw * cols, ch * len(crops)))
    anims = {}
    for ri, (name, imgs, fps, top, bottom) in enumerate(crops):
        for fi, im in enumerate(imgs):
            x = fi * cw + cw // 2 - im.width // 2
            y = ri * ch + (ch - 2) - bottom
            sheet.alpha_composite(im, (x, y))
        anims[name] = {"row": ri, "frames": len(imgs), "fps": fps}
    SHEETS.mkdir(exist_ok=True)
    sheet.save(SHEETS / f"boss_{boss}.png")
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
    m["sprites"][f"boss_{boss}"] = {"file": f"boss_{boss}.png", "cell": [cw, ch], "anims": anims}
    MANIFEST.write_text(json.dumps(m, indent=2))
    print("packed", boss, "cell", cw, ch, {k: v["frames"] for k, v in anims.items()})


def checker(w, h, s=8):
    im = Image.new("RGBA", (w, h), (200, 200, 200, 255))
    dr = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                dr.rectangle([x, y, x + s - 1, y + s - 1], fill=(160, 160, 160, 255))
    return im


def preview(out="preview_bosses_all.png", only=""):
    m = json.loads(MANIFEST.read_text())["sprites"]
    names = [b for b in BOSSES if f"boss_{b}" in m and (not only or b in only.split(","))]
    mage = Image.open(MAGE).convert("RGBA")
    mage = mage.crop(mage.getbbox())
    S = 2
    blocks = []
    for b in names:
        e = m[f"boss_{b}"]
        sheet = Image.open(SHEETS / e["file"]).convert("RGBA")
        cw, ch = e["cell"]
        cols = max(a["frames"] for a in e["anims"].values())
        rows = len(e["anims"])
        mw = mage.width + 8
        W = (cw * cols + mw) * S + 10
        H = ch * rows * S + 18
        blk = checker(W, H)
        dr = ImageDraw.Draw(blk)
        dr.rectangle([0, 0, W, 14], fill=(30, 30, 40, 255))
        dr.text((4, 2), f"boss_{b}  cell {cw}x{ch}  " + ", ".join(f"{k}:{v['frames']}" for k, v in e["anims"].items()), fill=(255, 255, 255, 255))
        big = sheet.resize((sheet.width * S, sheet.height * S), Image.NEAREST)
        blk.alpha_composite(big, (4, 16))
        for r in range(rows):
            mg = mage.resize((mage.width * S, mage.height * S), Image.NEAREST)
            blk.alpha_composite(mg, (4 + cw * cols * S + 4, 16 + (r + 1) * ch * S - 2 * S - mg.height))
        blocks.append(blk)
    W = max(b.width for b in blocks)
    H = sum(b.height + 6 for b in blocks)
    out_im = Image.new("RGBA", (W, H), (40, 40, 50, 255))
    y = 0
    for blk in blocks:
        out_im.alpha_composite(blk, (0, y))
        y += blk.height + 6
    out_im.save(GEN / out)
    print("preview", GEN / out, out_im.size)


def view(boss, files, out, scale=3):
    """Scratch viewer: files side by side on a checkerboard, enlarged, with the wizard."""
    d = d_of(boss)
    ims = [Image.open(d / f).convert("RGBA") for f in files.split(",")]
    mage = Image.open(MAGE).convert("RGBA")
    ims.append(mage)
    W = sum(i.width for i in ims) + 4 * len(ims)
    H = max(i.height for i in ims)
    c = checker(W, H, 4)
    x = 0
    for i in ims:
        c.alpha_composite(i, (x, H - i.height))
        x += i.width + 4
    c.resize((W * int(scale), H * int(scale)), Image.NEAREST).save(out)
    print("view", out)


def hurt(boss, src, out="hurt_0.png"):
    """Free hurt frame: the source frame tinted towards red with bright highlights (no API call)."""
    im = clean(Image.open(d_of(boss) / src))
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a:
                lum = (r * 3 + g * 6 + b) // 10
                if lum < 45:  # keep the dark outline
                    continue
                px[x, y] = ((r + 255) // 2, (g + 90) // 2 + lum // 6, (b + 90) // 2 + lum // 6, a)
    im.save(d_of(boss) / out)
    print("hurt", d_of(boss) / out)


def spent():
    tot = 0.0
    for line in MYLOG.read_text().splitlines() if MYLOG.exists() else []:
        if "{" in line:
            try:
                u = json.loads(line[line.index("{"):])
            except ValueError:
                continue
            if u and u.get("type") == "generations":
                tot += u.get("generations", 0)
    print("generations spent by bosses.py:", tot)


if __name__ == "__main__":
    a = sys.argv[1:]
    cmds = {"base": base, "anim": anim, "pack": pack, "preview": preview, "view": view, "hurt": hurt, "spent": spent}
    cmds[a[0]](*a[1:])


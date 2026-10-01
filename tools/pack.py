"""Pack generated frames into game sheets + manifest.json (agreed art contract).

Sheet format: transparent PNG, fixed cell size, one ROW per animation, frames
left to right. Side animations face RIGHT (the game flips them for left).
Frames are anchored by canvas centre (x) and the row's lowest pixel (feet, y)
so animations don't jitter.

python pack.py mage
"""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image

ART = Path(__file__).resolve().parent.parent
GEN = ART / "generated"
SHEETS = ART / "sheets"
MANIFEST = SHEETS / "manifest.json"
TOOLS = Path(__file__).resolve().parent


def anim_files(name):
    """{direction: [frame paths]} for the first animation found per direction."""
    info = json.loads((GEN / name / "character.json").read_text())
    out = {}
    for ai, anim in enumerate(info.get("animations", [])):
        for di, d in enumerate(anim.get("directions", [])):
            n = len(d.get("frames", []))
            files = [GEN / name / f"animations_{ai}_directions_{di}_frames_{f}.png" for f in range(n)]
            out.setdefault(d["direction"], files)
    return out


def place(cell, rows):
    """rows: list of (anim_name, [images]). Returns sheet and anim table."""
    cw, ch = cell
    cols = max(len(r[1]) for r in rows)
    sheet = Image.new("RGBA", (cw * cols, ch * len(rows)))
    anims = {}
    for ri, (aname, imgs) in enumerate(rows):
        bottom = max(im.getbbox()[3] for im in imgs)
        for fi, im in enumerate(imgs):
            x = fi * cw + cw // 2 - im.width // 2
            y = ri * ch + (ch - 2) - bottom
            sheet.alpha_composite(im, (x, y))
        anims[aname] = {"row": ri, "frames": len(imgs), "fps": 8 if "walk" in aname else 2}
    return sheet, anims


def update_manifest(entries):
    SHEETS.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"sprites": {}}
    m["sprites"].update(entries)
    MANIFEST.write_text(json.dumps(m, indent=2))


def pack_mage():
    d = GEN / "mage"
    load = lambda p: Image.open(p).convert("RGBA")
    walk = anim_files("mage")
    rows = [
        ("idle_down", [load(d / "rotation_urls_south.png")]),
        ("idle_up", [load(d / "rotation_urls_north.png")]),
        ("idle_side", [load(d / "rotation_urls_east.png")]),
        ("walk_down", [load(p) for p in walk["south"]]),
        ("walk_up", [load(p) for p in walk["north"]]),
        ("walk_side", [load(p) for p in walk["east"]]),
    ]
    cell = (24, 40)
    sheet, anims = place(cell, rows)
    grey = GEN / "mage" / "sheet_grey.png"
    sheet.save(grey)
    # One recolored sheet per element.
    subprocess.run([sys.executable, str(TOOLS / "recolor.py"), str(grey), str(SHEETS / "mage")], check=True)
    update_manifest(
        {f"mage_{e}": {"file": f"mage_{e}.png", "cell": list(cell), "anims": anims} for e in ("fire", "ice", "storm", "earth")}
    )
    print("packed mage sheets", sheet.size)


if __name__ == "__main__":
    {"mage": pack_mage}[sys.argv[1]]()

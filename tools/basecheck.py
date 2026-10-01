"""Check that each theme's water set reuses the wall set's floor tile: python basecheck.py"""
import json, sys
from pathlib import Path
from PIL import Image, ImageChops
G = Path(__file__).resolve().parent.parent / "generated"
def tile(d, idx):
    info = json.loads((d / "tileset.json").read_text())
    for i, t in enumerate(info["tileset"]["tiles"]):
        c = t["corners"]; k = (c["NW"]=="upper")*8+(c["NE"]=="upper")*4+(c["SW"]=="upper")*2+(c["SE"]=="upper")
        if k == idx: return Image.open(d / f"tileset_tiles_{i}_image.png").convert("RGB")
for w in sorted(G.glob("tiles_*_wall")):
    wa = w.with_name(w.name[:-4] + "water")
    if not (wa / "tileset.json").exists() or not (w / "tileset.json").exists(): continue
    st = json.loads((wa / "state.json").read_text())
    wid = json.loads((w / "tileset.json").read_text())["metadata"]["terrain_ids"]["lower"]
    wtid = json.loads((wa / "tileset.json").read_text())["metadata"]["terrain_ids"]["upper"]
    print(w.name, "same_floor_tile:", ImageChops.difference(tile(w, 0), tile(wa, 15)).getbbox() is None, "requested", st.get("upper_base") == wid, "ids", wid[:8], wtid[:8])


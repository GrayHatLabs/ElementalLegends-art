"""Generate terrain tilesets/decos for Elemental Legends themes (uses pixellab.py).

python terrain_gen.py <theme> [wall|water|deco|all]
Skips anything already generated. The water set is chained to the wall set's floor tile
(upper_base_tile_id = wall set's lower terrain id) so the floor is pixel-identical in both.
"""
import json
import subprocess
import sys
from pathlib import Path

ART = Path(__file__).resolve().parent.parent
GEN = ART / "generated"
PAL = GEN / "palettes"
STYLE = "SNES Zelda A Link to the Past style"
WATER_BLUE = f"clear calm blue water with gentle wave highlights, {STYLE} water, not neon"
LAVA = f"glowing molten orange lava with bright yellow hot spots and darker red crust swirls, {STYLE} lava"

THEMES = {
    0: dict(name="GREENWOOD", short="greenwood",
            floor="rich medium green grass field with scattered short darker green grass tufts, gentle shading, SNES Zelda A Link to the Past overworld grass, not pale, not neon",
            wall="thick forest of large round tree crowns seen from directly above, big fluffy leaf clusters, bright green highlights on top, darker green shading underneath, SNES Zelda A Link to the Past trees",
            wall_tr="tree crown shadow falling on the grass",
            water="clear calm blue pond water with gentle wave highlights, SNES Zelda A Link to the Past water, not neon",
            water_tr="grassy bank edge with a thin darker shoreline",
            decos={"tree": "single round leafy green tree with short brown trunk, SNES Zelda A Link to the Past style overworld tree, muted rich greens",
                   "bush": "small round green leafy bush, SNES Zelda A Link to the Past style liftable bush, muted rich greens",
                   "flowers": "small patch of white and yellow and red flowers with a few green leaves, SNES Zelda A Link to the Past style flowers"}),
    1: dict(name="OLD CRYPT", short="crypt",
            floor=f"overgrown graveyard ground, packed brown dirt with scattered grey cobblestones and small patches of dull green moss, gentle shading, {STYLE}, not neon",
            wall=f"crumbling grey stone wall seen from above, thick top of rough stacked grey stone blocks with cracks and a little moss, {STYLE}",
            wall_tr="dark shadow at the base of the stone wall",
            water=WATER_BLUE, water_tr="muddy stone-lined bank edge",
            decos={"tombstone": f"single weathered grey rounded tombstone with a crack, {STYLE} graveyard, muted colors",
                   "deadtree": f"small leafless dead tree with twisted grey-brown branches, {STYLE}, muted colors",
                   "cross": f"single old grey stone cross grave marker with moss at the base, {STYLE}, muted colors"}),
    2: dict(name="MIREFEN", short="mirefen",
            floor=f"murky swamp ground, dark olive-brown mud with patches of dull green moss and small puddle spots, gentle shading, {STYLE}, not neon",
            wall=f"raised mass of big round grey stone boulders heavily covered in bright green moss, seen from above, strong light tops and dark shadowed gaps between boulders, clearly lighter than the mud ground, {STYLE}",
            wall_tr="damp dark shadow around the mossy boulders",
            water=f"dark murky green-brown swamp water, clearly liquid, with pale green reflection ripples and a few floating lily pads, {STYLE}, not neon",
            water_tr="muddy mossy swamp bank",
            decos={"reeds": f"clump of tall swamp reeds and cattails, olive green and brown, {STYLE}, muted colors",
                   "mushrooms": f"cluster of three toadstool mushrooms with round red-brown caps with pale spots and short cream stems, {STYLE}, muted colors",
                   "stump": f"rotting dead tree stump with moss, dark brown wood, {STYLE}, muted colors"}),
    3: dict(name="EMBERPEAK", short="emberpeak",
            floor=f"dark grey volcanic rock ground with a few thin faint glowing orange cracks, gentle shading, {STYLE}, not neon",
            wall=f"raised jagged black basalt rock plateau seen from above, angular dark grey columns with sharp highlights, {STYLE}",
            wall_tr="dark shadow at the foot of the basalt rocks",
            water=LAVA, water_tr="cooling black rock crust edge glowing orange",
            decos={"lavarock": f"single dark volcanic boulder with glowing orange cracks, {STYLE}, muted colors",
                   "obsidian": f"cluster of three jagged black volcanic glass rock shards pointing up from the ground, glossy dark purple highlights, no handle, {STYLE}",
                   "charredtree": f"small burnt charred black dead tree with a few glowing embers, {STYLE}"}),
    4: dict(name="OVERGROWN SHRINE", short="shrine",
            floor=f"dungeon floor of mostly grey square stone flagstones with small tufts of green moss in the cracks, simple and calm, gentle shading, {STYLE} dungeon, not neon",
            wall=f"raised wall top of big light grey stone bricks overgrown with leafy green ivy vines, bright leaf highlights, seen from above, {STYLE} dungeon",
            wall_tr="dark shadow at the base of the vine-covered wall",
            water=WATER_BLUE, water_tr="stone pool edge with moss"),
    5: dict(name="UNDERGROUND CRYPT", short="undercrypt",
            floor=f"dungeon floor of dark grey square stone flagstones with thin dark mortar lines, gentle shading, {STYLE} dungeon, not neon",
            wall=f"raised dungeon wall of grey stone bricks seen from above, thick solid brick wall top, {STYLE} dungeon",
            wall_tr="dark shadow at the base of the brick wall",
            water=WATER_BLUE, water_tr="grey stone pool edge"),
    6: dict(name="RUINED CASTLE", short="castle",
            floor=f"castle dungeon floor of worn tan and light brown stone tiles with small cracks, gentle shading, {STYLE} dungeon, not neon",
            wall=f"raised castle wall of large sandstone blocks seen from above, warm tan and brown, {STYLE} dungeon",
            wall_tr="dark shadow at the base of the sandstone wall",
            water=WATER_BLUE, water_tr="tan stone moat edge"),
    7: dict(name="DRAGON FORTRESS", short="dragon",
            floor=f"fortress dungeon floor of large simple dark charcoal-red square stone tiles with a few small glowing orange lava cracks, calm, gentle shading, {STYLE} dungeon, not neon",
            wall=f"tall raised fortress wall of charred black bricks with lighter grey-brown brick tops and a strong dark shadow, clearly different from the red floor, seen from above, {STYLE} dungeon",
            wall_tr="dark soot shadow at the base of the charred wall",
            water=LAVA, water_tr="dark red stone edge glowing hot orange"),
    8: dict(name="FORGOTTEN SANCTUARY", short="sanctuary",
            floor=f"sanctuary floor of polished pale blue marble tiles with soft white veins, gentle shading, {STYLE} dungeon, not neon",
            wall=f"raised wall of large blue-grey marble blocks seen from above, smooth carved edges, {STYLE} dungeon",
            wall_tr="soft dark blue shadow at the base of the marble wall",
            water=f"deep clear medium blue water, darker and more saturated than the pale marble, gentle white wave highlights, {STYLE} water, not neon", water_tr="blue marble pool edge"),
    9: dict(name="DARK TOWER", short="darktower",
            floor=f"tower floor of glossy purple-black obsidian tiles with faint violet highlights, gentle shading, {STYLE} dungeon, not neon",
            wall=f"raised tower wall of dark purple stone bricks seen from above, {STYLE} dungeon",
            wall_tr="deep dark shadow at the base of the purple brick wall",
            water=WATER_BLUE, water_tr="obsidian pool edge"),
}
NEG = "neon colors, background, ground, grass floor, text, frame"


def run(*args):
    print(">>", " ".join(str(a) for a in args[:3]), flush=True)
    subprocess.run([sys.executable, str(ART / "tools" / "pixellab.py"), *map(str, args)], check=True)


def tdir(t, kind):
    return GEN / f"tiles_{t}_{THEMES[t]['short']}_{kind}"


def gen_wall(t):
    th = THEMES[t]
    if not (tdir(t, "wall") / "tileset.json").exists():
        run("tileset", tdir(t, "wall").name, th["floor"], th["wall"], 32, th["wall_tr"], PAL / f"theme{t}_wall.png", "0.25")


def gen_water(t):
    th = THEMES[t]
    if (tdir(t, "water") / "tileset.json").exists():
        return
    info = json.loads((tdir(t, "wall") / "tileset.json").read_text())
    floor_id = info["metadata"]["terrain_ids"]["lower"]
    run("tileset", tdir(t, "water").name, th["water"], th["floor"], 32, th["water_tr"], PAL / f"theme{t}_water.png", "0.25", "", floor_id)


def gen_deco(t):
    for n, desc in THEMES[t].get("decos", {}).items():
        d = GEN / f"deco_{t}_{n}"
        if not (d / "image.png").exists():
            run("image", d.name, desc, 32, 32, PAL / f"theme{t}_deco.png", NEG)


if __name__ == "__main__":
    t = int(sys.argv[1])
    what = sys.argv[2] if len(sys.argv) > 2 else "all"
    if what in ("wall", "all"):
        gen_wall(t)
    if what in ("water", "all"):
        gen_water(t)
    if what in ("deco", "all"):
        gen_deco(t)
    for k in ("wall", "water"):
        if (tdir(t, k) / "tileset.json").exists():
            subprocess.run([sys.executable, str(ART / "tools" / "wang_demo.py"), str(tdir(t, k)), str(tdir(t, k) / "demo24.png"), "24", "3"], check=True)

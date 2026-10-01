"""Batch driver for chunky characters: python chunky_batch.py create|walk <name> [<name>...]"""
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chunky  # noqa: E402

CHUNK = {"head_size": 1.7, "legs_length": 0.5, "arms_length": 0.8, "shoulder_width": 1.2, "hip_width": 1.2}
PLUMP = {"head_size": 1.6, "legs_length": 0.5, "arms_length": 0.8, "shoulder_width": 1.3, "hip_width": 1.6}
BROAD = {"head_size": 1.6, "legs_length": 0.55, "arms_length": 0.85, "shoulder_width": 1.5, "hip_width": 1.3}

SPECS = {
    "skeleton": (24, CHUNK, "short stocky skeleton warrior with a big skull head, white bones, wearing a plain grey "
                 "tattered tunic and grey iron helmet, holding a small grey rusty sword, chunky SNES RPG enemy"),
    "merchant": (24, PLUMP, "short plump friendly village merchant shopkeeper with a big head, round belly, brown apron "
                 "over a white shirt, small mustache, brown cap, chunky SNES RPG villager"),
    "imp": (22, CHUNK, "small imp demon with a big head, plain grey skin, two small horns, little bat wings, pointy "
            "tail, mischievous grin, chunky SNES RPG enemy"),
    "zombie": (24, CHUNK, "short stocky shambling zombie with a big head, pale green skin, torn brown peasant clothes, "
               "arms reaching forward, chunky SNES RPG enemy"),
    "dryad": (24, CHUNK, "short cute dryad girl with a big head, long flowing green hair decorated with leaves and a pink "
              "flower, wearing a long green leaf gown, bare feet, elf-like forest spirit, chunky SNES RPG villager"),
    "gravelord": (30, BROAD, "stocky undead knight king boss with a big skull head with glowing eyes and a golden crown, "
                  "broad dark iron plate armor, tattered purple cape, big sword, chunky SNES RPG boss"),
    "innkeeper": (24, CHUNK, "short friendly innkeeper woman with a big head, brown hair in a bun, cream blouse, brown "
                  "dress with a white apron, holding a wooden mug of ale, warm browns and cream, chunky SNES RPG villager"),
    "scholar": (24, CHUNK, "short old scholar with a big head, white hair, round spectacles, long blue-grey robe, "
                "holding an open book, chunky SNES RPG villager"),
}
# second attempts (a/b variants of the ones that lost design features)
SPECS.update({
    "skeleton2": (24, CHUNK, "short stocky skeleton warrior with a big white skull, white bones, wearing a torn red cloth "
                  "tunic, holding a small rusty sword in one hand, chunky SNES RPG enemy"),
    "merchant2": (24, PLUMP, "short fat merchant shopkeeper with a big head and a big round belly, brown flat cap, small "
                  "black mustache, white shirt, long brown apron, brown trousers, chunky SNES RPG villager"),
    "gravelord2": (30, BROAD, "stocky undead king boss, big dark grey skull head wearing a large golden crown, glowing "
                   "red eyes, broad black iron plate armor, long purple cape, big silver sword, chunky SNES RPG boss"),
    "scholar2": (24, CHUNK, "short old scholar with a big head, white hair and white beard, round glasses, long light "
                 "blue-grey robe, holding an open brown book, chunky SNES RPG villager"),
})
SPECS["skeleton3"] = SPECS["skeleton2"]
SPECS["merchant3"] = SPECS["merchant2"]
SPECS["gravelord3"] = (32, BROAD, SPECS["gravelord2"][2])
SPECS["scholar3"] = SPECS["scholar2"]


def create(n):
    size, props, desc = SPECS[n]
    chunky.character(n, desc, size, json.dumps(props))


def walk(n):
    action = "slow steady shambling walk with arms reaching forward" if n.startswith("zombie") else "walking"
    chunky.animate(n, action, "south,north,east", 4)


def fill(n):
    """Animate only the walk directions that are still missing (one direction per request)."""
    info = json.loads((chunky.d_of(n) / "character.json").read_text())
    have = {d["direction"] for a in info.get("animations", []) for d in a["directions"] if len(d["frames"]) >= 4}
    action = "slow steady shambling walk with arms reaching forward" if n.startswith("zombie") else "walking"
    for d in ("south", "north", "east"):
        if d not in have:
            chunky.animate(n, action, d, 4)


if __name__ == "__main__":
    fn = {"create": create, "walk": walk, "fill": fill}[sys.argv[1]]
    ts = [threading.Thread(target=fn, args=(n,)) for n in sys.argv[2:]]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

import sys
sys.argv = ["x"]
import chars
items = {
 "coin": "a single shiny gold coin, front view, simple, game item icon",
 "gem": "a single sparkling blue-cyan cut gemstone, game item icon",
 "apple": "a single shiny red apple with a green leaf, game item icon",
 "golden_apple": "a single shiny golden apple with a green leaf, glowing, game item icon",
 "bread": "a single loaf of golden brown bread, game item icon",
 "meat": "a roast meat drumstick on a bone, game item icon",
 "mana_potion": "a small round glass potion bottle filled with glowing blue liquid, cork stopper, game item icon",
 "antidote": "a small round glass potion bottle filled with bright green liquid, cork stopper, game item icon",
 "heart": "a small simple red heart, game pickup icon, Zelda style",
 "heart_container": "a big shiny red heart container with a golden rim, Zelda style heart piece, game item icon",
 "key": "a single small golden key, game item icon",
 "chest_closed": "a closed wooden treasure chest with gold trim and lock, game item, front view",
 "chest_open": "an open wooden treasure chest with gold trim, lid open, empty inside, game item, front view",
 "gold_pile": "a small pile of gold coins, treasure hoard, game item",
}
only = set(sys.argv_only) if hasattr(sys, "argv_only") else None
import os
for k, desc in items.items():
    if os.path.exists(chars.d_of("items") / f"{k}.png"):
        continue
    try:
        chars.bitforge("items", f"{k}.png", desc + ", black outline, simple readable shape", 32, 32, 0)
    except SystemExit as e:
        print("fail", k, e)

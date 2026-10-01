import sys
sys.argv = ["x"]
import os
import chars
G = chars.GEN
jobs = [
 ("slime", "base2.png", "idle", "slime squishing and wobbling in place, breathing"),
 ("slime", "base2.png", "move", "slime hopping forward, squashing and stretching"),
 ("ghost", "base4.png", "idle", "ghost floating gently bobbing up and down in place"),
 ("ghost", "base4.png", "move", "ghost floating forward, wispy tail waving"),
 ("golem", "base2.png", "idle", "stone golem breathing slowly, shoulders rising and falling"),
 ("golem", "base2.png", "move", "stone golem walking heavily forward, stomping"),
 ("generator", "base2.png", "idle", "glowing eye sockets pulsing brighter and dimmer, dark magic flickering"),
 ("treant", "base.png", "idle", "angry tree monster swaying its branches, leaves rustling"),
 ("treant", "base.png", "move", "tree monster walking forward on its root legs"),
 ("hoarddragon", "base.png", "idle", "dragon sleeping, slow breathing, body gently rising and falling"),
 ("hoarddragon", "base.png", "awake", "dragon waking up, rearing its head up and roaring"),
 ("items", "coin.png", "coin_spin", "gold coin spinning around its vertical axis"),
]
for name, base, pre, action in jobs:
    if os.path.exists(G / f"char_{name}" / f"{pre}_1.png"):
        continue
    try:
        chars.animtext(name, str(G / f"char_{name}" / base), pre, action, 4)
    except Exception as e:
        print("FAIL", name, pre, e, flush=True)

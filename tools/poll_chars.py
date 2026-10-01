import sys, time, json
sys.argv = ["x"]
import chars
names = ["dryad", "merchant", "gravelord"]
t0 = time.time()
while time.time() - t0 < 1500:
    done = True
    for n in names:
        chars.fetch(n)
        d = json.loads((chars.GEN / f"char_{n}" / "character.json").read_text())
        dirs = {x["direction"] for a in d["animations"] for x in a["directions"]}
        print(n, sorted(dirs), flush=True)
        if not {"south", "north", "east"} <= dirs:
            done = False
    if done:
        print("ALLDONE")
        break
    time.sleep(60)

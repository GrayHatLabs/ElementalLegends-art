"""Procedurally pixel-draw the slime (grey, recolourable) because the AI slimes came out noisy.

python slime_draw.py  -> generated/char_slime/draw_idle_0..4.png, draw_move_0..4.png (frame 0 = copy of 1)
Canvas 32x32, dome-shaped jelly, 1 px dark outline, 3-tone shading, white shine, two eyes.
"""
from pathlib import Path
from PIL import Image

D = Path(__file__).resolve().parent.parent / "generated" / "char_slime"
OUT = (24, 22, 30, 255)
DARK = (104, 104, 120, 255)
MID = (150, 150, 166, 255)
LIGHT = (196, 196, 208, 255)
SHINE = (246, 246, 250, 255)
EYE = (20, 18, 26, 255)


def slime(w, h, lift=0, eye_dx=0):
    im = Image.new("RGBA", (32, 32))
    px = im.load()
    cx = 16
    base = 29 - lift  # bottom row y
    a = w / 2
    b = h
    inside = set()
    for y in range(base - h + 1, base + 1):
        for x in range(32):
            dx = (x + 0.5 - cx) / a
            dy = (base + 1 - (y + 0.5)) / b  # 0 at bottom, 1 at top
            # dome: wide flat bottom, rounded top
            top = (abs(dx) ** 2.2 + max(dy, 0) ** 2.2) <= 1.0
            bottom_round = not (dy < 0.12 and abs(dx) > 0.92)
            if top and bottom_round:
                inside.add((x, y))
    for (x, y) in inside:
        edge = any((x + ox, y + oy) not in inside for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            px[x, y] = OUT
            continue
        dx = (x + 0.5 - cx) / a
        dy = (base + 1 - (y + 0.5)) / b
        light = 0.55 * dy - 0.35 * dx  # lit from top-left
        px[x, y] = LIGHT if light > 0.38 else MID if light > 0.02 else DARK
    # shine
    top_y = base - h + 1
    sx, sy = cx - int(a * 0.45), top_y + max(2, h // 4)
    for p in ((sx, sy), (sx + 1, sy), (sx, sy + 1)):
        if p in inside:
            px[p] = SHINE
    # eyes
    ey = base - int(h * 0.45)
    for ex in (cx - 3 + eye_dx, cx + 2 + eye_dx):
        for p in ((ex, ey), (ex, ey + 1)):
            if p in inside:
                px[p] = EYE
    return im


def main():
    D.mkdir(parents=True, exist_ok=True)
    idle = [slime(18, 13), slime(19, 12), slime(20, 11), slime(19, 12)]
    move = [slime(20, 11), slime(16, 15, lift=1), slime(17, 13, lift=3), slime(18, 12, lift=1)]
    for pre, frames in (("draw_idle", idle), ("draw_move", move)):
        frames = [frames[0]] + frames
        for i, im in enumerate(frames):
            im.save(D / f"{pre}_{i}.png")
    print("drew slime frames")


if __name__ == "__main__":
    main()

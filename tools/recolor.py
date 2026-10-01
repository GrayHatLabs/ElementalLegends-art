"""Recolor the grey robe/hat of a sprite into element colors (free, local).

python recolor.py in.png out_prefix
Writes <out_prefix>_fire.png, _ice.png, _storm.png, _earth.png.
Only low-saturation mid-tone pixels (the grey cloth) are recolored; outlines,
the white beard, skin and the glowing gem are kept.
"""
import colorsys
import sys
from PIL import Image

# (dark, mid, light) ramps per element, matching the game's EL_MAIN / EL_LIGHT.
RAMPS = {
    "fire": [(88, 16, 8), (200, 40, 0), (252, 152, 56)],
    "ice": [(8, 40, 120), (0, 112, 236), (164, 228, 252)],
    "storm": [(56, 16, 96), (128, 48, 200), (200, 150, 240)],
    "earth": [(16, 60, 8), (32, 124, 16), (152, 216, 88)],
}


def lerp(c0, c1, t):
    return tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))


def shade(r, v):
    """v: 0..1 brightness of the original grey -> color on the element ramp."""
    if v < 0.5:
        return lerp(r[0], r[1], v / 0.5)
    return lerp(r[1], r[2], (v - 0.5) / 0.5)


def main(src, prefix):
    im = Image.open(src).convert("RGBA")
    px = im.load()
    greys = []
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if a > 0 and s < 0.25 and 0.2 < v < 0.72:
                greys.append(v)
    lo, hi = 0.2, 0.72  # fixed scale so every direction/frame gets identical colors
    for name, rp in RAMPS.items():
        out = im.copy()
        op = out.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if a > 0 and s < 0.25 and 0.2 < v < 0.72:
                    t = (v - lo) / max(hi - lo, 1e-6)
                    op[x, y] = (*shade(rp, 0.1 + 0.75 * t), a)
        out.save(f"{prefix}_{name}.png")
    print("recolored", src)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])


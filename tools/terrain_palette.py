"""Curated SNES-style (A Link to the Past look) palettes per terrain theme.

python terrain_palette.py            -> writes generated/palettes/theme<N>_<kind>.png swatch images
Used both as the PixelLab `color_image` (palette reference) and for the optional
local remap step (remap.py) so every theme stays in the same muted-but-rich family.
"""
from pathlib import Path
from PIL import Image

OUTLINE = [(16, 20, 24), (40, 36, 44)]

GRASS = [(152, 200, 96), (112, 176, 72), (80, 148, 56), (56, 120, 48), (40, 92, 40), (28, 68, 36)]
CANOPY = [(64, 128, 64), (40, 100, 52), (28, 76, 44), (20, 52, 36), (120, 168, 80)]
DIRT = [(200, 168, 112), (168, 128, 80), (128, 92, 56), (88, 60, 40)]
WATER = [(184, 224, 240), (112, 176, 224), (64, 128, 200), (40, 88, 160), (24, 56, 112)]
GREY = [(200, 200, 192), (160, 160, 156), (120, 120, 120), (84, 84, 92), (56, 56, 64)]
MUD = [(104, 96, 64), (80, 72, 48), (60, 56, 40), (44, 40, 32)]
MOSS = [(128, 144, 72), (96, 116, 56), (68, 88, 48), (48, 64, 40)]
MURK = [(120, 136, 88), (88, 108, 72), (60, 80, 60), (40, 56, 48)]
VOLC = [(104, 92, 92), (76, 68, 72), (52, 46, 52), (34, 30, 36)]
LAVA = [(252, 236, 136), (248, 184, 56), (232, 112, 24), (184, 56, 16), (112, 24, 16)]
GLOW = [(240, 136, 40), (176, 64, 24)]
TAN = [(224, 200, 152), (192, 160, 112), (152, 120, 80), (112, 84, 56), (76, 56, 40)]
SAND = [(232, 208, 144), (200, 172, 112), (160, 132, 84), (116, 92, 60)]
REDBLK = [(120, 56, 48), (88, 40, 40), (60, 28, 32), (40, 20, 24)]
CHAR = [(92, 76, 72), (64, 52, 52), (44, 36, 40), (28, 24, 28)]
BLUE_MARBLE = [(200, 216, 240), (152, 176, 224), (104, 132, 196), (72, 96, 160), (48, 64, 116)]
BLUEGREY = [(176, 188, 204), (136, 148, 172), (100, 110, 136), (68, 76, 100), (44, 50, 70)]
OBSID = [(96, 72, 128), (68, 48, 96), (46, 32, 68), (30, 22, 44)]
PURPLE_BRICK = [(128, 96, 160), (96, 68, 128), (70, 48, 100), (48, 32, 72)]
FLOWERS = [(240, 232, 208), (240, 208, 88), (224, 104, 104)]
WOOD = [(136, 100, 64), (96, 68, 44), (64, 44, 32)]
CYAN_GLINT = [(176, 232, 248)]

THEMES = {
    0: {"wall": GRASS + CANOPY + OUTLINE, "water": GRASS + WATER + OUTLINE, "deco": GRASS + CANOPY + FLOWERS + WOOD + OUTLINE},
    1: {"wall": DIRT[1:] + GREY + MOSS[1:] + OUTLINE, "water": DIRT[1:] + GREY[2:] + WATER + MOSS[2:] + OUTLINE,
        "deco": GREY + WOOD + MOSS[1:] + OUTLINE},
    2: {"wall": MUD + MOSS + GREY[2:] + WOOD[1:] + OUTLINE, "water": MUD + MOSS + MURK + OUTLINE,
        "deco": MOSS + MUD + WOOD + [(200, 184, 140), (176, 96, 72)] + OUTLINE},
    3: {"wall": VOLC + GLOW + CHAR + OUTLINE, "water": VOLC + LAVA + OUTLINE, "deco": VOLC + LAVA[1:4] + CHAR + OBSID[1:] + OUTLINE},
    4: {"wall": MOSS + GREY[1:] + CANOPY[1:4] + OUTLINE, "water": MOSS + GREY[1:4] + WATER + OUTLINE},
    5: {"wall": GREY + [(96, 96, 104), (72, 72, 80)] + OUTLINE, "water": GREY + WATER + OUTLINE},
    6: {"wall": TAN + SAND + OUTLINE, "water": TAN + WATER + OUTLINE},
    7: {"wall": REDBLK + CHAR + GLOW + OUTLINE, "water": REDBLK + LAVA + OUTLINE},
    8: {"wall": BLUE_MARBLE + BLUEGREY + OUTLINE, "water": BLUE_MARBLE + BLUEGREY[2:] + WATER + [(40, 120, 200), (24, 80, 168)] + OUTLINE},
    9: {"wall": OBSID + PURPLE_BRICK + OUTLINE + [(160, 120, 200)], "water": OBSID + WATER + OUTLINE + [(160, 120, 200)]},
}


def palette(theme, kind):
    seen, out = set(), []
    for c in THEMES[theme][kind]:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def swatch(cols, path, size=64, cell=8):
    """64x64 image (size PixelLab expects for color_image); colours repeat to fill it."""
    per = size // cell
    im = Image.new("RGBA", (size, size))
    for i in range(per * per):
        c = cols[i % len(cols)]
        x, y = (i % per) * cell, (i // per) * cell
        im.paste(c + (255,), (x, y, x + cell, y + cell))
    im.save(path)


if __name__ == "__main__":
    d = Path(__file__).resolve().parent.parent / "generated" / "palettes"
    d.mkdir(parents=True, exist_ok=True)
    for t, kinds in THEMES.items():
        for k in kinds:
            swatch(palette(t, k), d / f"theme{t}_{k}.png")
    print("wrote", d)

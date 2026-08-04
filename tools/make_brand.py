#!/usr/bin/env python3
"""Generate the NetWorth Routine mark: SVG + PNG app icons.

Design: an unbroken ring of 16 segments (the day divided into slots; a closed,
unbroken loop = consistency), with a bright gold arc marking the streak. Inside,
a rising two-peak zigzag echoing the NetWorth NN mark — a repeating rhythm that
climbs = discipline.
"""
import math, os
from PIL import Image, ImageDraw

NAVY       = "#223870"
NAVY_DEEP  = "#16255a"
GOLD       = "#B1870F"
GOLD_BRIGHT= "#E3B33F"
WHITE      = "#FFFFFF"

OUT = os.path.expanduser("~/daily-routine/assets")
os.makedirs(OUT, exist_ok=True)

SEGS       = 16          # slots in the ring
STREAK     = 6           # how many read as "done" (bright gold)
R_IN, R_OUT= 168, 212    # ring radii
SEG_W      = 26          # segment thickness
C          = 256         # centre of a 512 box

def seg_points(i):
    """Inner and outer endpoint of ring segment i, starting at 12 o'clock."""
    a = math.radians(-90 + i * (360 / SEGS))
    return ((C + R_IN * math.cos(a),  C + R_IN * math.sin(a)),
            (C + R_OUT * math.cos(a), C + R_OUT * math.sin(a)))

# The rising zigzag: down-up-down-up, second peak higher than the first.
ZIG_A = [(142, 330), (204, 202), (256, 300)]   # navy / white stroke
ZIG_B = [(256, 300), (310, 156), (370, 250)]   # gold stroke
ZIG_W = 36
GOLD_DIM   = "#8A6A12"   # unlit ring segments

# ---------------------------------------------------------------- SVG (transparent)
def write_svg(path, ring_dim, ring_lit, zig_a, zig_b):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
         f'width="512" height="512" role="img" aria-label="NetWorth Routine">']
    for i in range(SEGS):
        (x1, y1), (x2, y2) = seg_points(i)
        col = ring_lit if i < STREAK else ring_dim
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{col}" stroke-width="{SEG_W}" stroke-linecap="round"/>')
    for pts, col in ((ZIG_A, zig_a), (ZIG_B, zig_b)):
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        p.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{ZIG_W}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    p.append('</svg>')
    open(path, "w").write("\n".join(p))

# on dark surfaces (the app header)
write_svg(f"{OUT}/mark-dark.svg", "#7a5f14", GOLD_BRIGHT, WHITE, GOLD_BRIGHT)
# on light surfaces
write_svg(f"{OUT}/mark-light.svg", "#c9cfe0", GOLD, NAVY, GOLD)

# ---------------------------------------------------------------- PNG icons
SS = 4  # supersample

def thick_line(d, pts, colour, width):
    """Polyline with round caps and joins — Pillow has no native round cap."""
    w = width * SS
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        d.line([(x1*SS, y1*SS), (x2*SS, y2*SS)], fill=colour, width=w)
    for x, y in pts:
        r = w / 2
        d.ellipse([x*SS-r, y*SS-r, x*SS+r, y*SS+r], fill=colour)

def render(size, tile=True, pad=0.0):
    n = 512 * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tile:
        # vertical navy gradient tile
        top, bot = (0x22, 0x38, 0x70), (0x14, 0x21, 0x50)
        for y in range(n):
            t = y / n
            d.line([(0, y), (n, y)],
                   fill=tuple(int(top[c] + (bot[c]-top[c])*t) for c in range(3)) + (255,))
        mask = Image.new("L", (n, n), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, n-1, n-1], radius=int(n*0.22), fill=255)
        img.putalpha(mask)
        d = ImageDraw.Draw(img)

    for i in range(SEGS):
        a, b = seg_points(i)
        col = GOLD_BRIGHT if i < STREAK else (GOLD_DIM if tile else "#c9cfe0")
        thick_line(d, [a, b], col, SEG_W)
    thick_line(d, ZIG_A, WHITE if tile else NAVY, ZIG_W)
    thick_line(d, ZIG_B, GOLD_BRIGHT, ZIG_W)

    if pad:  # breathing room for maskable icons
        s = int(n * (1 - pad))
        small = img.resize((s, s), Image.LANCZOS)
        canvas = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        canvas.paste(small, ((n-s)//2, (n-s)//2), small)
        img = canvas
    return img.resize((size, size), Image.LANCZOS)

for size, name in [(512, "icon-512.png"), (192, "icon-192.png"),
                   (180, "apple-touch-icon.png"), (32, "favicon-32.png")]:
    render(size).save(f"{OUT}/{name}")
render(512, pad=0.22).save(f"{OUT}/icon-maskable-512.png")
render(1024).save(f"{OUT}/icon-1024.png")

print("wrote:", ", ".join(sorted(os.listdir(OUT))))

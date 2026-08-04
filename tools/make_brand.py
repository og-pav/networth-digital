#!/usr/bin/env python3
"""Build every NetWorth Routine brand asset from one source of truth.

Source is the supplied "NW Routine - Standard" lockup: the NetWorth NN mark plus
the growth arrow, with a flame as the Routine symbol — the streak you don't break.

Two defects in the supplied file are corrected here:
  * the flame was clipped — content ran to y=269.3, the viewBox stopped at 260.12
  * it hung 16 units below the baseline; both NN strokes end exactly at y=253.1

and the integration is tightened: the flame's axis is rotated from 18 to 27
degrees so it leans with the diagonal strokes instead of standing upright
against them.

Rasterising uses macOS qlmanage + sips, so there is nothing to pip install.
Run:  python3 tools/make_brand.py
"""
import os, shutil, subprocess, tempfile

OUT  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
NAVY, GOLD = "#223870", "#b1870f"

# ---------------------------------------------------------------- source paths
MARK = '''<path fill="#b1870f" d="M181.15,78.19c-.1-.12-1.09-1.24-3.44-3.51-2.63-2.54-5.91-4.28-6.04-4.35l-5.38-2.84v42.84l16.54-30.22-1.67-1.93Z"/>
<path fill="#b1870f" d="M377.63,73.17c-17.12,8.64-31.04,22.1-40.25,38.93l-46.21,84.41v-126.6h-3.67c-18.16,0-40.23,19.85-49.04,37.76l-45.25,86.62v-35.16l-26.92,49.18v44.8h3.67c11.47,0,22.75-8.63,31.17-19.02,3.4-4.2,6.26-8.81,8.76-13.6l54.34-104.03s0,0,.02,0v136.64h3.67c11.23,0,20.96-7.74,29.55-17.23,5.02-5.54,9.26-11.75,12.85-18.31l83.54-152.61-16.24,8.2Z"/>
<path fill="#223870" d="M224.54,69.9c-15.11,0-29.01,8.23-36.26,21.49l-61.04,111.51V69.9h-3.67c-16.31,0-33.68,14.32-41.05,28.17L0,253.12h6.11c13.16,0,23.83-5.9,32.33-16.63,2.12-2.68,3.89-5.61,5.5-8.63l56.37-105.92v131.18h3.67c15.68,0,30.9-12.02,40.69-26.47,1.1-1.62,2.07-3.32,3.01-5.03l83.05-151.71h-6.2Z"/>
<path fill="#b1870f" d="M418.81,92.15l-1.14-15.92c-.02-.33-2.24-30.87-5.93-45.36-10.04,4.59-47.71,22.65-77.4,47.85,0,0,34.75-39.43,64.56-62.18,10.08-7.69,21.09-14.58,21.2-14.65l3.04-1.9.66,3.52c.29,1.54,6.97,38.19-1.31,73.1l-3.69,15.53Z"/>'''

# Flame drawn in a 24x24 box. The outer path is evenodd, so on its own it carries
# a real transparent hole — that is what lets the navy tile show through on icons.
FLAME_OUTER = '<path fill="{gold}" fill-rule="evenodd" d="M13.5.67s.74,2.65.74,4.8c0,2.06-1.35,3.73-3.41,3.73-2.07,0-3.63-1.67-3.63-3.73l.03-.36C5.21,7.51,4,10.62,4,14c0,4.42,3.58,8,8,8s8-3.58,8-8C20,8.61,17.41,3.8,13.5.67ZM11.71,19c-1.78,0-3.22-1.4-3.22-3.14,0-1.62,1.05-2.76,2.81-3.12,1.77-.36,3.6-1.21,4.62-2.58.39,1.29.59,2.65.59,4.04,0,2.65-2.15,4.8-4.8,4.8Z"/>'
FLAME_INNER = '<path fill="{navy}" d="M11.71,19c-1.78,0-3.22-1.4-3.22-3.14,0-1.62,1.05-2.76,2.81-3.12,1.77-.36,3.6-1.21,4.62-2.58.39,1.29.59,2.65.59,4.04,0,2.65-2.15,4.8-4.8,4.8Z"/>'

# Corrected placement: up onto the baseline (237 not 253) and leaning with the strokes.
FLAME_TF = "translate(357 237) rotate(27) scale(6.6) translate(-12 -22)"
VIEWBOX  = "-6 -6 480 273"          # measured tight bounds + even margin, nothing clipped

def lockup(reverse=False):
    """reverse=True: NN goes white and the flame's centre becomes a true hole,
    so it sits on any dark colour, not only NetWorth navy."""
    mark = MARK.replace(NAVY, "#ffffff") if reverse else MARK
    flame = FLAME_OUTER.format(gold=GOLD)
    if not reverse:
        flame += "\n" + FLAME_INNER.format(navy=NAVY)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" '
            f'role="img" aria-label="NetWorth Routine">\n{mark}\n'
            f'<g transform="{FLAME_TF}">{flame}</g>\n</svg>\n')

def flame_only(gold=GOLD, navy=None):
    inner = "\n" + FLAME_INNER.format(navy=navy) if navy else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="3 0 18 23" '
            f'role="img" aria-label="NetWorth Routine">\n{FLAME_OUTER.format(gold=gold)}{inner}\n</svg>\n')

def icon_svg(pad=0.0):
    """Square app icon: gold flame knocked out of a navy tile."""
    inset = 512 * pad
    h = 300 * (1 - pad * 1.6)                 # flame height on a 512 tile
    s = h / 21.33                             # flame is 21.33 units tall in its box
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#26407f"/><stop offset="1" stop-color="#152252"/>
</linearGradient></defs>
<rect x="{inset}" y="{inset}" width="{512-inset*2}" height="{512-inset*2}" rx="{112*(1-pad)}" fill="url(#g)"/>
<g transform="translate(256 268) scale({s:.4f}) translate(-12 -11.335)">{FLAME_OUTER.format(gold="#E3B33F")}</g>
</svg>
'''

# ---------------------------------------------------------------- write vectors
os.makedirs(OUT, exist_ok=True)
for name, body in {
    "logo-lockup.svg":          lockup(),
    "logo-lockup-reverse.svg":  lockup(reverse=True),
    "flame.svg":                flame_only(navy=NAVY),
    "flame-gold.svg":           flame_only(gold="#E3B33F"),
    "icon.svg":                 icon_svg(),
}.items():
    open(os.path.join(OUT, name), "w").write(body)

# ---------------------------------------------------------------- rasterise
def png_from_svg(svg_text, out_path, size, render=1024):
    """qlmanage renders the SVG through WebKit; sips resizes to the exact size."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.svg")
        open(src, "w").write(svg_text)
        subprocess.run(["qlmanage", "-t", "-s", str(render), "-o", tmp, src],
                       capture_output=True, check=True)
        made = os.path.join(tmp, "in.svg.png")
        if not os.path.exists(made):
            raise RuntimeError(f"qlmanage produced nothing for {out_path}")
        subprocess.run(["sips", "-z", str(size), str(size), made, "--out", out_path],
                       capture_output=True, check=True)

for size, name in [(1024, "icon-1024.png"), (512, "icon-512.png"), (192, "icon-192.png"),
                   (180, "apple-touch-icon.png"), (32, "favicon-32.png")]:
    png_from_svg(icon_svg(), os.path.join(OUT, name), size)
png_from_svg(icon_svg(pad=0.14), os.path.join(OUT, "icon-maskable-512.png"), 512)

# a transparent PNG of the full lockup, for decks, emails and GHL
with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "l.svg"); open(src, "w").write(lockup())
    subprocess.run(["qlmanage", "-t", "-s", "2048", "-o", tmp, src], capture_output=True, check=True)
    shutil.copy(os.path.join(tmp, "l.svg.png"), os.path.join(OUT, "logo-lockup-2048.png"))

print("wrote:\n  " + "\n  ".join(sorted(os.listdir(OUT))))

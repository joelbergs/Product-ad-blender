"""Draws the silhouette of the logo on the phone's back as a grey mask (white = logo) -> assets/phone/apple_logo_mask.png.
The glyph is the real product mark (a bitten apple with a leaf) as a single smooth Bezier outline (24x24 icon grid), rasterised with
4x supersampling. The previous hand-built circle version looked lumpy.  python3 make_logo_mask.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from svgpathtools import parse_path
from paths import p, assert_writable

D = ("M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 "
     "3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415"
     "-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09z "
     "M15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701z")
S, SS = 1024, 3
path = parse_path(D)
subs = path.continuous_subpaths()
pts = [[(seg.point(t / 60.0)) for seg in sp for t in range(60)] for sp in subs]
allp = np.array([[q.real, q.imag] for sp in pts for q in sp])
x0, y0 = allp.min(0); x1, y1 = allp.max(0)
scale = S * SS * 0.84 / max(x1 - x0, y1 - y0)                       # glyph spans 84 % of the square, centred
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
im = Image.new("L", (S * SS, S * SS), 0)
d = ImageDraw.Draw(im)
for sp in pts:                                                     # even-odd is not needed: two disjoint outlines (body, leaf)
    d.polygon([((q.real - cx) * scale + S * SS / 2, (q.imag - cy) * scale + S * SS / 2) for q in sp], fill=255)
im = im.resize((S, S), Image.LANCZOS)
im = ImageOps.mirror(im)                 # the rear glass UVs are mirrored: seen from behind the logo then reads the right way round
out = assert_writable(p("assets", "phone", "apple_logo_mask.png"))
os.makedirs(os.path.dirname(out), exist_ok=True)
im.save(out)
print("wrote", out, "bbox", (x1 - x0, y1 - y0))

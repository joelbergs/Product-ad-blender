"""Draws the silhouette of the logo that sits on the phone's back as a soft grey mask (white = logo) -> assets/phone/apple_logo_mask.png.
The logo is part of the real product the film shows; it is drawn here from simple primitives (circles + a leaf) and smoothed.
python3 make_logo_mask.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from paths import p, assert_writable

S = 2048                      # working size; glyph height ~ 0.84 * S
def pt(x, y):                 # unit coords (y up, 1.0 = glyph height) -> pixels
    return (S / 2 + x * S * 0.84, S / 2 - y * S * 0.84)

def shape(circles=(), polys=(), blur=0):
    im = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(im)
    for (cx, cy, r) in circles:
        x, y = pt(cx, cy); rr = r * S * 0.84
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    for poly in polys:
        d.polygon([pt(*q) for q in poly], fill=255)
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im

body = shape(circles=[(-0.170, 0.050, 0.262), (0.170, 0.050, 0.262), (0.0, -0.02, 0.30),
                      (-0.115, -0.30, 0.200), (0.115, -0.30, 0.200), (-0.20, -0.17, 0.235), (0.20, -0.17, 0.235), (0.0, -0.22, 0.28)])
body = body.filter(ImageFilter.GaussianBlur(34)).point(lambda v: 255 if v > 118 else 0)
cut_dip = shape(circles=[(0.0, 0.335, 0.105)])                      # dip between the lobes at the top
cut_bite = shape(circles=[(0.405, 0.035, 0.165), (0.0, -0.505, 0.055)])      # the bite on the right, a small notch at the bottom
arr = np.array(body, dtype=np.float32)
arr[np.array(cut_dip) > 0] = 0
arr[np.array(cut_bite) > 0] = 0
body = Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: 255 if v > 128 else 0)

# leaf: pointed ellipse rotated up to the right
import math
leaf = []
for k in range(120):
    t = 2 * math.pi * k / 120
    a, b = 0.190, 0.072
    x, y = a * math.cos(t), b * math.sin(t) * (1.0 - 0.35 * math.cos(t))   # slightly pointed at both ends
    ang = math.radians(33)
    leaf.append((0.075 + x * math.cos(ang) - y * math.sin(ang), 0.395 + x * math.sin(ang) + y * math.cos(ang)))
leaf_im = shape(polys=[leaf]).filter(ImageFilter.GaussianBlur(5)).point(lambda v: 255 if v > 128 else 0)

logo = Image.fromarray(np.maximum(np.array(body), np.array(leaf_im)))
logo = logo.resize((1024, 1024), Image.LANCZOS)
out = assert_writable(p("assets", "phone", "apple_logo_mask.png"))
os.makedirs(os.path.dirname(out), exist_ok=True)
logo.save(out)
print("wrote", out)

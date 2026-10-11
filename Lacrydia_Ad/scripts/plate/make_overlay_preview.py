#!/usr/bin/env python3
"""Composite overlays over a dark gradient for visual QA -> ROOT/renders/previews/. Also prints margin/size measurements."""
import os, sys, argparse
from PIL import Image, ImageDraw
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ap = argparse.ArgumentParser(); ap.add_argument("--width", type=int, default=1920); ap.add_argument("--height", type=int, default=1080)
ap.add_argument("--crop", action="store_true", help="also write a native-res crop of the lockup block")
a = ap.parse_args(); W, H = a.width, a.height
d = os.path.join(ROOT, "renders", f"overlays_{W}x{H}"); pv = os.path.join(ROOT, "renders", "previews")
os.makedirs(pv, exist_ok=True)
x = np.linspace(0, 1, W)[None, :, None]; y = np.linspace(0, 1, H)[:, None, None]
base = np.array([10, 10, 11.]) + (np.array([34, 30, 40.]) - np.array([10, 10, 11.])) * (0.55 * x + 0.35 * (1 - y))
bg = Image.fromarray(np.clip(base * np.ones((H, W, 1)), 0, 255).astype(np.uint8), "RGB").convert("RGBA")
# stand-in for the phone in the right third (plain rounded rect, NOT app UI)
dr = ImageDraw.Draw(bg); dr.rounded_rectangle((W * 0.64, H * 0.08, W * 0.9, H * 0.92), radius=int(H * 0.04), outline=(90, 90, 96, 255), width=2)
def comp(names, out):
    im = bg.copy()
    for n in names: im.alpha_composite(Image.open(os.path.join(d, f"overlay_{n}.png")))
    im.convert("RGB").save(os.path.join(pv, out)); return im
comp(["tagline_1", "tagline_2"], f"overlay_taglines_{W}x{H}.png")
im = comp(["endcard_lockup", "endcard_status", "endcard_url"], f"overlay_endcard_{W}x{H}.png")
for n in ["tagline_1", "tagline_2", "endcard_lockup", "endcard_status", "endcard_url"]:
    bb = Image.open(os.path.join(d, f"overlay_{n}.png")).getchannel("A").getbbox()
    print(f"{n:16s} ink bbox {bb}  left {bb[0]/W:.3f}W right {bb[2]/W:.3f}W top {bb[1]/H:.3f}H bottom {bb[3]/H:.3f}H")
if a.crop:
    bb = Image.open(os.path.join(d, "overlay_endcard_lockup.png")).getchannel("A").getbbox()
    pad = int(H * 0.03); im.crop((bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)).convert("RGB").save(os.path.join(pv, f"overlay_lockup_crop_{W}x{H}.png"))

#!/usr/bin/env python3
"""Contact sheet of representative plate frames (before / during / after each swipe) -> ROOT/renders/previews/."""
import json, os, sys
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "assets", "lacrydia", "screen_plate")
m = json.load(open(os.path.join(P, "plate_manifest.json")))
cfg = json.load(open(os.path.join(ROOT, "config", "production.json")))["screen"]
fps, t0, sd = m["fps"], m["plate_t0"], cfg["swipe_dur"]
cw = 220; ch = round(cw * m["height"] / m["width"]); pad = 8; lab = 16
taus = [-0.1, 0.1, 0.3, 0.5, 0.7, 0.9, 1.15]
starts = [p["swipe_out_t"] for p in cfg["pages"] if p["swipe_out_t"] is not None]
sheet = Image.new("RGB", (pad + len(taus) * (cw + pad), pad + len(starts) * (ch + lab + pad)), (60, 60, 64))
d = ImageDraw.Draw(sheet)
for r, s in enumerate(starts):
    for c, tau in enumerate(taus):
        i = min(max(int(round((s + tau * sd - t0) * fps)), 0), m["num_frames"] - 1)
        im = Image.open(os.path.join(P, m["frames"][i])).resize((cw, ch), Image.LANCZOS)
        x, y = pad + c * (cw + pad), pad + r * (ch + lab + pad)
        sheet.paste(im, (x, y + lab))
        d.text((x, y), f"swipe {r+1}  f{i}  t={t0+i/fps:.2f}  tau={tau:+.2f}", fill=(230, 230, 230))
out = os.path.join(ROOT, "renders", "previews", "screen_plate_contact_sheet.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
sheet.save(out); print(out, sheet.size)

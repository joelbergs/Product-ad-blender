"""Spectrogram + short-term loudness with cue markers.   python3 viz.py ../../final/audio_mix.wav ../../final/audio_cues.json out.png"""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
import dsp as D
wavp, cuep, outp = sys.argv[1:4]
x, sr = D.read_wav(wavp)
m = x.mean(axis=1)
win, hop = 4096, 1024
w = np.hanning(win)
nfr = (len(m) - win) // hop
S = np.abs(np.fft.rfft(np.stack([m[i * hop:i * hop + win] * w for i in range(nfr)]), axis=1)).T
fr = np.fft.rfftfreq(win, 1 / sr)
H, W = 360, 1800
fmin, fmax = 30, 16000
rows = np.geomspace(fmin, fmax, H)
img = np.zeros((H, W))
cols = np.linspace(0, nfr - 1, W).astype(int)
for r, f in enumerate(rows):
    idx = int(np.searchsorted(fr, f))
    img[H - 1 - r] = 20 * np.log10(S[idx, cols] + 1e-9)
img = np.clip((img + 110) / 70, 0, 1)
rgb = np.stack([img ** 1.6, img ** 1.1 * 0.9, 0.35 + 0.65 * img], axis=-1)
im = Image.fromarray((rgb * 255).astype(np.uint8)).resize((W, H))
canvas = Image.new("RGB", (W, H + 150), (8, 8, 12))
canvas.paste(im, (0, 0))
d = ImageDraw.Draw(canvas)
dur = len(m) / sr
cues = json.load(open(cuep))["cues"]
for c in cues:
    px = int(c["t"] / dur * W)
    d.line([(px, 0), (px, H)], fill=(255, 220, 90), width=1)
# short-term RMS (dBFS)
blk = int(0.4 * sr)
r = [10 * np.log10(np.mean(m[i:i + blk] ** 2) + 1e-12) for i in range(0, len(m) - blk, blk // 2)]
for i, v in enumerate(r):
    px = int(i * (blk // 2) / len(m) * W); h = int(np.clip((v + 60) / 40, 0, 1) * 120)
    d.rectangle([px, H + 140 - h, px + 4, H + 140], fill=(90, 190, 255))
for s in range(0, int(dur) + 1, 5):
    px = int(s / dur * W); d.line([(px, H), (px, H + 150)], fill=(60, 60, 70)); d.text((px + 3, H + 2), f"{s}s", fill=(200, 200, 210))
canvas.save(outp)
print("peak dBFS", 20 * np.log10(np.max(np.abs(x))), "rms by 5s:", [round(10 * np.log10(np.mean(m[i * sr:(i + 5) * sr] ** 2) + 1e-12), 1) for i in range(0, int(dur), 5)])

"""PIL/numpy-only visualisations for the sync QA: spectrogram with event markers, envelope timeline per layer."""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from dsp_common import ROOT, SR, assert_writable, cfg

FONT_PATH = os.path.join(ROOT, "assets", "fonts", "Inter-Regular.otf")


def font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _lut():
    stops = [(0.0, (6, 6, 14)), (0.25, (40, 20, 90)), (0.5, (150, 40, 110)), (0.75, (240, 130, 40)), (1.0, (255, 245, 200))]
    xs = np.linspace(0, 1, 256)
    lut = np.zeros((256, 3), np.uint8)
    for c in range(3):
        lut[:, c] = np.interp(xs, [s[0] for s in stops], [s[1][c] for s in stops])
    return lut


def spectrogram(x, win=4096, hop=512):
    """returns (dB array [bins, frames], freqs, times) from mono x."""
    w = np.hanning(win)
    n = (len(x) - win) // hop + 1
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * w, axis=1)) / (win / 4)
    return 20 * np.log10(S.T + 1e-9), np.fft.rfftfreq(win, 1.0 / SR), (np.arange(n) * hop + win / 2) / SR


def spec_image(x, path, ev_lines=None, scenes=None, dur=None, fmin=30, fmax=18000, size=(1800, 640),
               dbrange=(-110, -30), title=""):
    """log-frequency spectrogram PNG with event markers (ev_lines: [(t, label)])."""
    assert_writable(path)
    if x.ndim == 2:
        x = x.mean(axis=1)
    dur = dur or len(x) / SR
    S, f, t = spectrogram(x)
    W, H = size
    left, top, bot = 70, 40, 30
    pw, ph = W - left - 10, H - top - bot
    # map pixel columns -> frames, rows -> log freq
    cols = np.clip(np.searchsorted(t, np.arange(pw) / pw * dur), 0, S.shape[1] - 1)
    fr = np.exp(np.linspace(np.log(fmax), np.log(fmin), ph))
    rows = np.clip(np.searchsorted(f, fr), 0, S.shape[0] - 1)
    img = S[rows][:, cols]
    img = np.clip((img - dbrange[0]) / (dbrange[1] - dbrange[0]), 0, 1)
    rgb = _lut()[(img * 255).astype(np.uint8)]
    canvas = Image.new("RGB", (W, H), (14, 14, 16))
    canvas.paste(Image.fromarray(rgb), (left, top))
    d = ImageDraw.Draw(canvas)
    ft, fs = font(13), font(11)
    d.text((left, 8), title, fill=(230, 230, 230), font=font(15))
    for fq in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
        if fmin < fq < fmax:
            y = top + ph * (np.log(fmax) - np.log(fq)) / (np.log(fmax) - np.log(fmin))
            d.line([(left, y), (left + pw, y)], fill=(255, 255, 255, 40), width=1)
            d.text((6, y - 7), f"{fq/1000:g}k" if fq >= 1000 else f"{fq}", fill=(190, 190, 190), font=fs)
    for s in range(0, int(dur) + 1, 2):
        x0 = left + pw * s / dur
        d.text((x0 - 6, H - 22), f"{s}s", fill=(190, 190, 190), font=fs)
    if scenes:
        for sc in scenes:
            x0 = left + pw * sc["t0"] / dur
            d.line([(x0, top), (x0, top + 10)], fill=(120, 200, 255), width=2)
    for i, (te, lab) in enumerate(ev_lines or []):
        x0 = left + pw * te / dur
        d.line([(x0, top), (x0, top + ph)], fill=(80, 255, 200), width=1)
        yy = top + 12 + (i % 6) * 13
        d.text((x0 + 2, yy), lab, fill=(80, 255, 200), font=fs)
    canvas.save(path)


def timeline_image(stems, mix, path, ev_lines, scenes=None, dur=30.0, size=(1800, 760), win_s=0.05, title=""):
    """per-layer RMS envelope (dBFS, 50 ms) stacked rows + master, with event lines. stems: {name: (n,2)}."""
    assert_writable(path)
    names = list(stems.keys()) + ["MIX"]
    arrs = list(stems.values()) + [mix]
    W, H = size
    left, top, bot = 100, 44, 26
    ph_row = (H - top - bot) / len(names)
    pw = W - left - 12
    canvas = Image.new("RGB", (W, H), (14, 14, 16))
    d = ImageDraw.Draw(canvas)
    ft, fs = font(13), font(11)
    d.text((left, 10), title, fill=(230, 230, 230), font=font(15))
    colors = [(255, 166, 43), (120, 200, 255), (255, 120, 150), (150, 255, 160), (210, 170, 255), (255, 235, 120),
              (170, 255, 255), (255, 255, 255)]
    w = int(win_s * SR)
    for ri, (nm, a) in enumerate(zip(names, arrs)):
        y0 = top + ri * ph_row
        d.rectangle([left, y0, left + pw, y0 + ph_row - 2], fill=(22, 22, 25))
        d.text((6, y0 + ph_row / 2 - 8), nm, fill=colors[ri % len(colors)], font=ft)
        m = a.mean(axis=1) if a.ndim == 2 else a
        nfr = len(m) // w
        r = np.sqrt(np.mean(m[: nfr * w].reshape(nfr, w) ** 2, axis=1) + 1e-14)
        rdb = 20 * np.log10(r)
        lo, hi = -80.0, -10.0
        xs = left + pw * (np.arange(nfr) * win_s) / dur
        ys = y0 + (ph_row - 4) * (1 - np.clip((rdb - lo) / (hi - lo), 0, 1)) + 1
        for gdb in (-70, -50, -30):
            gy = y0 + (ph_row - 4) * (1 - (gdb - lo) / (hi - lo)) + 1
            d.line([(left, gy), (left + pw, gy)], fill=(48, 48, 54), width=1)
            d.text((left + pw - 28, gy - 11), f"{gdb}", fill=(90, 90, 100), font=fs)
        pts = list(zip(xs, ys)) + [(xs[-1], y0 + ph_row - 3), (xs[0], y0 + ph_row - 3)]
        d.polygon(pts, fill=tuple(int(c * 0.45) for c in colors[ri % len(colors)]))
        d.line(list(zip(xs, ys)), fill=colors[ri % len(colors)], width=1)
    for sc in scenes or []:
        x0 = left + pw * sc["t0"] / dur
        d.line([(x0, top - 8), (x0, top)], fill=(120, 200, 255), width=2)
        d.text((x0 + 2, top - 22), sc["id"][-2:], fill=(120, 200, 255), font=fs)
    for i, (te, lab) in enumerate(ev_lines):
        x0 = left + pw * te / dur
        d.line([(x0, top), (x0, H - bot)], fill=(80, 255, 200), width=1)
        d.text((x0 + 2, top + 2 + (i % 8) * 12), lab, fill=(80, 255, 200), font=fs)
    for s in range(0, int(dur) + 1, 2):
        x0 = left + pw * s / dur
        d.text((x0 - 6, H - 20), f"{s}s", fill=(190, 190, 190), font=fs)
    canvas.save(path)

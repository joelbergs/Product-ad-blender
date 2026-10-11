#!/usr/bin/env python3
"""Build the screen plate for the Lacrydia film.

Input : ROOT/assets/lacrydia/screens/1..5.png (REAL app screenshots, read only)
        ROOT/config/production.json  (screen.pages, screen.swipe_dur, screen.plate_t0, fps)
Output: ROOT/assets/lacrydia/screen_plate/  unique frames + plate_manifest.json

Plate frame i  <->  film time t = plate_t0 + i / fps  (i = 0 .. round((30 - plate_t0) * fps), inclusive).

What is composed (everything else is untouched screenshot pixels):
  * the pager slide between two pages (integer pixel offsets, no resampling -> no blur/jitter)
  * the status-bar strip (top 160 px, feathered to 220 px) stays fixed from page A while the
    pages slide and cross-fades to page B's strip in the second half of the swipe
  * the Dynamic Island pill (pure black, geometry measured from 4.png), toggle with --no-island

Usage:  python3 make_screen_plate.py [--no-island] [--out DIR] [--png-level N]
"""
import argparse, json, math, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W, H = 1206, 2622

# Dynamic Island geometry measured on the real 4.png (sub-pixel edges from AA coverage), native px
ISLAND = dict(x0=460.77, x1=745.23, y0=41.74, y1=152.28)
STRIP_FULL, STRIP_END = 160, 220          # status strip: fully fixed above, feathered to page body below


def bezier_ease(x1, y1, x2, y2):
    """CSS-style cubic-bezier easing function."""
    def f(x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(60):
            t = (lo + hi) / 2
            bx = 3*(1-t)**2*t*x1 + 3*(1-t)*t**2*x2 + t**3
            if bx < x: lo = t
            else: hi = t
        t = (lo + hi) / 2
        return 3*(1-t)**2*t*y1 + 3*(1-t)*t**2*y2 + t**3
    return f

# iOS-pager feel: quick but soft start, long soft deceleration tail (the "settle"); monotonic, no overshoot,
# because overshoot of a full-bleed pager would expose empty space at the right edge.
EASE = bezier_ease(0.38, 0.0, 0.10, 1.0)


def smoothstep(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u*u*(3 - 2*u)


def island_overlay(ss=8):
    """RGBA (H,W) float coverage mask of the island pill, supersampled."""
    g = ISLAND
    x0, x1, y0, y1 = g["x0"], g["x1"], g["y0"], g["y1"]
    r = (y1 - y0) / 2
    # work on a cropped box for speed
    bx0, bx1, by0, by1 = int(x0) - 2, int(x1) + 3, int(y0) - 2, int(y1) + 3
    ys = (np.arange((by1 - by0) * ss) + 0.5) / ss + by0
    xs = (np.arange((bx1 - bx0) * ss) + 0.5) / ss + bx0
    X, Y = np.meshgrid(xs, ys)
    cy = (y0 + y1) / 2
    cxl, cxr = x0 + r, x1 - r
    dx = np.maximum(np.maximum(cxl - X, X - cxr), 0)
    inside = (dx**2 + (Y - cy)**2) <= r*r
    cov = inside.reshape(by1 - by0, ss, bx1 - bx0, ss).mean(axis=(1, 3))
    full = np.zeros((H, W), np.float32)
    full[by0:by1, bx0:bx1] = cov
    return full


def apply_island(img, cov):
    """img uint8 (H,W,3); paint black pill by coverage."""
    ys, xs = np.nonzero(cov)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = img[y0:y1, x0:x1].astype(np.float32)
    c = cov[y0:y1, x0:x1, None]
    img[y0:y1, x0:x1] = np.rint(sub * (1 - c)).astype(np.uint8)
    return img


def compose_swipe(A, B, tau):
    """A,B uint8 (H,W,3); tau in (0,1) linear time progress."""
    e = EASE(tau)
    d = int(round(W * e))
    d = min(max(d, 0), W)
    out = np.empty_like(A)
    out[:, :W - d] = A[:, d:]
    out[:, W - d:] = B[:, :d]
    # status strip: A's strip stays, cross-fades to B's strip late in the swipe
    k = smoothstep(0.55, 0.95, tau)
    ramp = np.ones(H, np.float32)
    ramp[STRIP_FULL:STRIP_END] = 1 - np.array([smoothstep(STRIP_FULL, STRIP_END, y) for y in range(STRIP_FULL, STRIP_END)], np.float32)
    ramp[STRIP_END:] = 0
    ramp = ramp[:STRIP_END, None, None]
    strip = A[:STRIP_END].astype(np.float32) * (1 - k) + B[:STRIP_END].astype(np.float32) * k
    body = out[:STRIP_END].astype(np.float32)
    out[:STRIP_END] = np.rint(strip * ramp + body * (1 - ramp)).astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "production.json"))
    ap.add_argument("--screens", default=os.path.join(ROOT, "assets", "lacrydia", "screens"))
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "lacrydia", "screen_plate"))
    ap.add_argument("--island", action=argparse.BooleanOptionalAction, default=True,
                    help="overlay the Dynamic Island pill on every frame (default on; --no-island to disable)")
    ap.add_argument("--png-level", type=int, default=3)
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    if not (out + os.sep).startswith(ROOT + os.sep):
        sys.exit("refusing to write outside ROOT: " + out)
    if os.path.abspath(a.screens) == out:
        sys.exit("output dir must differ from the screens dir")
    os.makedirs(out, exist_ok=True)

    cfg = json.load(open(a.config))
    fps = cfg["fps"]; t_end = cfg["duration_s"]
    sc = cfg["screen"]; pages = sc["pages"]; sdur = sc["swipe_dur"]; t0 = sc["plate_t0"]
    n = int(round((t_end - t0) * fps)) + 1

    imgs = [np.array(Image.open(os.path.join(a.screens, p["file"])).convert("RGB")) for p in pages]
    for im in imgs:
        assert im.shape == (H, W, 3), im.shape
    cov = island_overlay() if a.island else None

    def save(arr, name):
        arr = arr.copy()
        if cov is not None:
            apply_island(arr, cov)
        Image.fromarray(arr, "RGB").save(os.path.join(out, name), compress_level=a.png_level)
        return name

    static_names = {}
    frames = []
    eps = 1e-6
    swipes_written = {}
    for i in range(n):
        t = t0 + i / fps
        # find state
        # page k+1's "show_t" equals page k's "swipe_out_t": that is the moment the swipe STARTS; the incoming
        # page is fully settled swipe_dur later.
        state = None
        for k, p in enumerate(pages):
            settled = p["show_t"] + (sdur if k > 0 else 0.0)
            s0 = p["swipe_out_t"]
            if s0 is None:
                if t >= settled - eps: state = ("static", k)
                continue
            if settled - eps <= t < s0 - eps: state = ("static", k)
            elif s0 + eps < t < s0 + sdur - eps: state = ("swipe", k, (t - s0) / sdur)
            elif abs(t - s0) <= eps: state = ("static", k)   # tau == 0 is identical to the static page
        if state is None:  # t before first page (not expected) or after last swipe end handled above
            state = ("static", 0)
        if state[0] == "static":
            k = state[1]
            if k not in static_names:
                static_names[k] = save(imgs[k], f"page{k+1}_static.png")
            frames.append(static_names[k])
        else:
            k, tau = state[1], state[2]
            if int(round(W * EASE(tau))) >= W:      # slide numerically complete -> identical to static page k+1
                if k + 1 not in static_names:
                    static_names[k + 1] = save(imgs[k + 1], f"page{k+2}_static.png")
                frames.append(static_names[k + 1]); continue
            name = f"swipe{k+1}to{k+2}_f{i:04d}.png"
            save(compose_swipe(imgs[k], imgs[k + 1], tau), name)
            frames.append(name)

    # run-length form
    runs = []
    for i, f in enumerate(frames):
        if runs and runs[-1]["file"] == f:
            runs[-1]["count"] += 1
        else:
            runs.append({"file": f, "start": i, "count": 1})
    manifest = {
        "fps": fps, "plate_t0": t0, "width": W, "height": H,
        "num_frames": len(frames), "t_end": t0 + (len(frames) - 1) / fps,
        "island": bool(a.island),
        "path_base": ".",          # file names are relative to this manifest's directory
        "frames": frames,
        "runs": runs,
    }
    with open(os.path.join(out, "plate_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    if a.island:  # standalone island overlay (RGBA) for compositing elsewhere if wanted
        rgba = np.zeros((H, W, 4), np.uint8); rgba[..., 3] = np.rint(cov * 255).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").save(os.path.join(out, "island_overlay_rgba.png"))
    uniq = sorted(set(frames))
    print(f"{len(frames)} plate frames, {len(uniq)} unique files in {out}")


if __name__ == "__main__":
    main()

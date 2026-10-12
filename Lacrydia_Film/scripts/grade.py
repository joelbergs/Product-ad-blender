"""Look pipeline: scene-linear -> display. One place defines the film's look (used by previews and the final finish).

 * exposure (stops) -> filmic S-curve (deep, rich blacks; highlights roll off instead of clipping to flat white)
 * midnight-blue shadow tint, cool-silver highlights, neutral mids (skin tones are left alone)
 * very light halation/bloom (physically motivated, not a glow filter) and fine luminance grain are added by finish.py
"""
import os
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
import cv2
import numpy as np


def read_exr(path):
    import OpenEXR
    ch = OpenEXR.File(path).channels()
    return np.asarray(ch["RGB"].pixels, dtype=np.float32)


def _curve(x):
    """Narkowicz-style filmic fit (ACES-like), slightly toe-lifted free: black stays black."""
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0)


def srgb_oetf(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def tonemap(lin, exposure=0.0, shadow_tint=(0.00006, 0.00022, 0.00100), silver=0.04, contrast=1.0):
    x = lin * (2.0 ** exposure)
    luma = (0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])[..., None]
    # shadows: add a trace of midnight blue where the picture is darkest (never touches mids/skin)
    sh = np.exp(-luma * 60.0)
    x = x + sh * np.array(shadow_tint, np.float32)
    y = _curve(x)
    if contrast != 1.0:
        y = np.clip(0.5 + (y - 0.5) * contrast, 0, 1)
    # highlights go cool silver instead of neutral/yellow: very gentle
    hl = np.clip((y - 0.75) / 0.25, 0, 1) ** 2
    y = y + hl * np.array([-0.5, 0.0, 0.5], np.float32) * silver * 0.5
    return srgb_oetf(np.clip(y, 0, 1)).astype(np.float32)


def to_png(lin, path, **kw):
    out = (tonemap(lin, **kw) * 255 + 0.5).astype(np.uint8)
    cv2.imwrite(path, out[..., ::-1])


if __name__ == "__main__":
    import sys
    exp = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    to_png(read_exr(sys.argv[1]), sys.argv[2], exposure=exp)

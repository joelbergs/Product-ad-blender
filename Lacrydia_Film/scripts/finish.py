"""Finishing: EXR plates -> graded, typeset, encoded film.

   python finish.py --tag animatic --w 640 --out ../final/animatic          (quick check)
   python finish.py --tag final --w 1920 --encode                           (master + MP4)

 * in-between frames come from DIS optical flow with a forward-backward confidence mask (never across a shot cut)
 * look: soft bloom on over-range highlights, filmic curve + midnight shadows / silver highlights (grade.py), mild vignette,
   fine luminance grain and 1-LSB triangular dither (no banding in the long black gradients)
 * typography is composited here from the real Inter Display face and the real brand wordmark artwork (never generated)
"""
import argparse, bisect, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import grade
from lib import motion

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="final")
ap.add_argument("--w", type=int, default=1920)
ap.add_argument("--out", default=None)
ap.add_argument("--frames", default=None, help="film frames a-b (inclusive)")
ap.add_argument("--only", default=None, help="comma list of film frames to write as PNG (QC)")
ap.add_argument("--encode", action="store_true")
ap.add_argument("--audio", default=os.path.join(ROOT, "final", "audio_mix.wav"))
ap.add_argument("--exposure", type=float, default=0.0)
a = ap.parse_args()

FILM = json.load(open(os.path.join(ROOT, "config", "film.json")))
FPS = FILM["fps"]
W = a.w; H = W * 9 // 16
S = W / 1920.0
RDIR = os.path.join(ROOT, "renders", a.tag)
SRC_W = None
NFR = int(round(FILM["duration"] * FPS))
FONT_DIR = "/usr/share/fonts/opentype/inter"
BRAND = os.path.join(ROOT, "assets", "lacrydia", "logo")


# ------------------------------------------------------------------------------------------------ plates + interpolation
_avail = {}
def avail(mod):
    if mod not in _avail:
        d = os.path.join(RDIR, mod)
        _avail[mod] = sorted(int(f.split("_")[1][:4]) for f in os.listdir(d) if f.endswith(".exr")) if os.path.isdir(d) else []
    return _avail[mod]

_cache = {}
def load(mod, f):
    k = (mod, f)
    if k not in _cache:
        if len(_cache) > 8:
            _cache.pop(next(iter(_cache)))
        _cache[k] = grade.read_exr(os.path.join(RDIR, mod, f"{mod}_{f:04d}.exr"))
    return _cache[k]

_dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
_fcache = {}
def flow(mod, f0, f1):
    k = (mod, f0, f1)
    if k not in _fcache:
        if len(_fcache) > 6:
            _fcache.pop(next(iter(_fcache)))
        A, B = load(mod, f0), load(mod, f1)
        sm = lambda im: cv2.cvtColor(cv2.resize((np.clip(im, 0, 1) ** 0.45 * 255).astype(np.uint8), (im.shape[1] // 2, im.shape[0] // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        ga, gb = sm(A), sm(B)
        fab, fba = _dis.calc(ga, gb, None), _dis.calc(gb, ga, None)
        h2, w2 = fab.shape[:2]
        gx, gy = np.meshgrid(np.arange(w2, dtype=np.float32), np.arange(h2, dtype=np.float32))
        back = cv2.remap(fba, gx + fab[..., 0], gy + fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        err = np.linalg.norm(fab + back, axis=2)
        conf = np.exp(-(cv2.GaussianBlur(err, (0, 0), 2.0) / 1.2) ** 2).astype(np.float32)
        _fcache[k] = (fab, fba, conf)
    return _fcache[k]

def warp(img, fl, k):
    h_, w_ = img.shape[:2]
    f = cv2.resize(fl, (w_, h_), interpolation=cv2.INTER_LINEAR) * 2.0 * k
    gx, gy = np.meshgrid(np.arange(w_, dtype=np.float32), np.arange(h_, dtype=np.float32))
    return cv2.remap(img, gx - f[..., 0], gy - f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def plate(mod, f, lo, hi):
    """linear plate for module frame f (float ok), clamped to rendered frames inside [lo, hi] (a shot / segment)"""
    ids = [i for i in avail(mod) if lo <= i <= hi]
    if not ids:
        return None
    f = min(max(f, ids[0]), ids[-1])
    j = bisect.bisect_right(ids, f + 1e-6) - 1
    n0 = ids[j]
    if abs(f - n0) < 1e-3 or j + 1 >= len(ids):
        return load(mod, n0)
    n1 = ids[j + 1]
    k = (f - n0) / (n1 - n0)
    A, B = load(mod, n0), load(mod, n1)
    fab, fba, conf = flow(mod, n0, n1)
    warped = warp(A, fba, k) * (1 - k) + warp(B, fab, 1 - k) * k
    cf = cv2.resize(conf, (A.shape[1], A.shape[0]), interpolation=cv2.INTER_LINEAR)[..., None]
    return warped * cf + (A * (1 - k) + B * k) * (1 - cf)


# ------------------------------------------------------------------------------------------------ shots
SEGMENTS = {"TABLE": [(0, 155), (156, 239), (240, 443)]}      # camera cuts inside the table take (local frames)
def seg_range(mod, f):
    for lo, hi in SEGMENTS.get(mod, []):
        if lo <= f <= hi:
            return lo, hi
    return 0, 10 ** 6

def shot_at(t):
    for s in FILM["shots"]:
        if s["start"] - 1e-9 <= t < s["start"] + s["dur"] - 1e-9:
            return s
    return FILM["shots"][-1]

def linear_frame(i):
    t = i / FPS
    s = shot_at(t)
    lt = t - s["start"]
    f = (s.get("t0", 0.0) + lt) * FPS
    lo, hi = seg_range(s["module"], int(round(f)))
    img = plate(s["module"], f, lo, hi)
    if img is None:
        img = np.zeros((H, W, 3), np.float32)
    if img.shape[1] != W:
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA if img.shape[1] > W else cv2.INTER_CUBIC)
    # shot fades (in linear light = exposure ramps, so the picture emerges from / dissolves into darkness like lighting does)
    fi = motion.ramp(lt, 0.0, s.get("fade_in", 0.0), "inout") if s.get("fade_in", 0) > 0 else 1.0
    fo = 1.0 - motion.ramp(lt, s["dur"] - s.get("fade_out", 0.0), s["dur"], "inout") if s.get("fade_out", 0) > 0 else 1.0
    return img * fi * fo, s, lt


# ------------------------------------------------------------------------------------------------ look
def bloom(lin):
    hi = np.maximum(lin - 0.9, 0.0)
    if hi.max() <= 0:
        return lin
    b1 = cv2.GaussianBlur(hi, (0, 0), 0.006 * W)
    b2 = cv2.GaussianBlur(hi, (0, 0), 0.025 * W)
    return lin + 0.09 * b1 + 0.06 * b2

_vig = None
def vignette():
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        xx = xx / W - 0.5; yy = yy / H - 0.5
        v = 1.0 - 0.16 * ((xx * 1.0) ** 2 + (yy * 1.7) ** 2) ** 0.9 * 2.0
        _vig = cv2.resize(v, (W, H), interpolation=cv2.INTER_LINEAR)[..., None].astype(np.float32)
    return _vig


# ------------------------------------------------------------------------------------------------ typography
_fonts = {}
def font(px, weight="Medium"):
    k = (px, weight)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(f"{FONT_DIR}/InterDisplay-{weight}.otf", max(8, int(px)))
    return _fonts[k]

_txt = {}
def text_layer(text, size, weight="Medium", track=0.0, color=(238, 241, 247)):
    k = (text, size, weight, track, color, W)
    if k in _txt:
        return _txt[k]
    f = font(size * S, weight)
    adv = [f.getlength(c) + track * size * S for c in text]
    tw = int(sum(adv)) + int(size * S * 1.2); th = int(size * S * 1.9)
    im = Image.new("L", (tw, th), 0); d = ImageDraw.Draw(im)
    x = size * S * 0.6
    for c, w_ in zip(text, adv):
        d.text((x, size * S * 0.35), c, font=f, fill=255); x += w_
    arr = np.asarray(im, np.float32) / 255.0
    _txt[k] = (arr, np.array(color, np.float32) / 255.0)
    return _txt[k]

def put_text(canvas, text, cx, cy, alpha, size=44, weight="Medium", track=0.02, rise=0.0, blur=0.0, color=(238, 241, 247), anchor="center"):
    if alpha <= 0.002:
        return
    arr, col = text_layer(text, size, weight, track, color)
    th, tw = arr.shape
    a_ = arr
    if blur > 0.3:
        a_ = cv2.GaussianBlur(arr, (0, 0), blur * S)
    x0 = int(cx - (tw / 2 if anchor == "center" else 0)); y0 = int(cy - th / 2 + rise * S)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + tw), min(H, y0 + th)
    if xb <= xa or yb <= ya:
        return
    m = a_[ya - y0:yb - y0, xa - x0:xb - x0, None] * alpha
    canvas[ya:yb, xa:xb] = canvas[ya:yb, xa:xb] * (1 - m) + col * m

def statement(canvas, t, text, t_in, t_out, cx, cy, size=44, weight="Medium", anchor="center", track=0.025):
    """in: fade + 7 px rise + blur-focus over 1.0 s; out: fade over 0.7 s. All eased from the film's own curve family."""
    a_in = motion.ramp(t, t_in, t_in + 1.0, "out"); a_out = 1.0 - motion.ramp(t, t_out, t_out + 0.7, "inout")
    al = a_in * a_out
    put_text(canvas, text, cx, cy, al, size, weight, track, rise=(1 - a_in) * 9, blur=(1 - a_in) * 5, anchor=anchor)

_wm = {}
def wordmark(width_px):
    if width_px not in _wm:
        im = Image.open(os.path.join(BRAND, "..", "logo", "wordmark-on-ink.png")) if False else None
        p = os.path.join(ROOT, "assets", "lacrydia", "logo", "wordmark-on-ink.png")
        im = np.asarray(Image.open(p).convert("L"), np.float32)
        ys, xs = np.where(im > 128)
        crop = im[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]
        crop = np.clip((crop - 10.0) / 235.0, 0, 1)          # ink #0A0A0B -> alpha 0
        h = int(round(crop.shape[0] * width_px / crop.shape[1]))
        _wm[width_px] = cv2.resize(crop, (int(width_px), h), interpolation=cv2.INTER_AREA)
    return _wm[width_px]

def brand_end(canvas, t):
    # stacked lockup proportions from the brand's own file: wordmark 1164 wide, mark above (see documentation)
    wm_w = int(0.485 * W)
    arr = wordmark(wm_w)
    th, tw = arr.shape
    cx, cy = W / 2, H * 0.735
    u = motion.ramp(t, 41.95 + 0.3, 41.95 + 1.9, "out")           # wordmark rises into place, lit by a soft sweep
    al = u
    x0 = int(cx - tw / 2); y0 = int(cy - th / 2 + (1 - u) * 12 * S)
    sweep_x = motion.ramp(t, 41.95 + 0.3, 41.95 + 2.1, "inout") * (tw + 0.5 * tw) - 0.25 * tw
    xs = np.arange(tw, dtype=np.float32)
    lit = 1.0 + 0.55 * np.exp(-((xs - sweep_x) / (0.06 * tw)) ** 2)
    m = arr * al
    col = np.array([0.93, 0.945, 0.975], np.float32)
    layer = (m * lit[None, :])[..., None]
    sub = canvas[y0:y0 + th, x0:x0 + tw]
    canvas[y0:y0 + th, x0:x0 + tw] = sub * (1 - np.clip(m[..., None], 0, 1)) + col * layer
    # tagline
    ta = motion.ramp(t, 43.0, 44.1, "out")
    put_text(canvas, "Your images. Your world.", W / 2, H * 0.835, ta * 0.78, size=27, weight="Medium", track=0.12, rise=(1 - ta) * 6, color=(190, 196, 208))


def overlay(canvas, t):
    s = lambda v: v * S
    # D: the pile
    statement(canvas, t, "A camera roll is a pile.", 17.15, 21.2, W / 2, H * 0.915, size=40)
    # F: the place
    statement(canvas, t, "Lacrydia is a place.", 31.55, 33.75, W / 2, H * 0.915, size=40)
    # G: privacy + sharing (true to the app: private by default; share with friends or everyone)
    statement(canvas, t, "Private by default.", 34.9, 36.9, W * 0.16, H * 0.47, size=42, anchor="left", track=0.015)
    statement(canvas, t, "Shared with the people you choose.", 37.0, 38.3, W * 0.16, H * 0.47, size=42, anchor="left", track=0.015)
    # H: brand
    brand_end(canvas, t)


# ------------------------------------------------------------------------------------------------ frame
def render_frame(i):
    lin, s, lt = linear_frame(i)
    t = i / FPS
    lin = bloom(lin)
    disp = grade.tonemap(lin, exposure=a.exposure) * vignette()
    rg = np.random.default_rng(i * 7919 + 13)
    lum = disp.mean(axis=2, keepdims=True)
    grain = rg.normal(0, 1, (H, W, 1)).astype(np.float32) * (0.0030 + 0.0045 * (1 - np.clip(lum * 2.0, 0, 1)))
    disp = disp + grain
    overlay_canvas = disp
    overlay(overlay_canvas, t)
    # triangular dither (+-1 LSB at 10 bit output) so deep gradients never band
    tri = (rg.random((H, W, 1)).astype(np.float32) - rg.random((H, W, 1)).astype(np.float32)) / 1023.0
    return np.clip(overlay_canvas + tri, 0, 1)


def encoders(out_dir, w, h):
    os.makedirs(out_dir, exist_ok=True)
    master = os.path.join(out_dir, "lacrydia_film_master_prores422hq.mov")
    video = os.path.join(out_dir, "_video_h264.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le", "-c:v", "prores_ks", "-profile:v", "3",
           "-vendor", "apl0", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", master,
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "12",
           "-tune", "film", "-profile:v", "high", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-movflags", "+faststart", video]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE), master, video


if __name__ == "__main__":
    out_dir = a.out or os.path.join(ROOT, "final", a.tag)
    os.makedirs(out_dir, exist_ok=True)
    if a.only:
        for i in [int(x) for x in a.only.split(",")]:
            img = render_frame(i)
            cv2.imwrite(os.path.join(out_dir, f"qc_{i:04d}.png"), (img[..., ::-1] * 255 + 0.5).astype(np.uint8))
        sys.exit(0)
    f0, f1 = (0, NFR - 1) if not a.frames else map(int, a.frames.split("-"))
    enc = None
    if a.encode:
        enc, master, video = encoders(out_dir, W, H)
    t0 = time.time()
    for i in range(f0, f1 + 1):
        img = render_frame(i)
        if enc:
            enc.stdin.write((img * 65535 + 0.5).astype("<u2").tobytes())
        else:
            cv2.imwrite(os.path.join(out_dir, f"f{i:04d}.png"), (img[..., ::-1] * 255 + 0.5).astype(np.uint8))
        if i % 24 == 0:
            print(f"frame {i}/{NFR}  {time.time() - t0:.0f}s", flush=True)
    if enc:
        enc.stdin.close(); enc.wait()
        final = os.path.join(out_dir, "lacrydia_film.mp4")
        if os.path.exists(a.audio):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", a.audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
                            "-ar", "48000", "-shortest", "-movflags", "+faststart", final], check=True)
            os.remove(video)
        else:
            os.replace(video, final)
        print("wrote", final, master)

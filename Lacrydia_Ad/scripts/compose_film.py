"""Composes the whole 30 s film (900 frames @ 30 fps) as PNG frames:
   0.0 - 10.0 s  3D hero: four shots (Cycles renders of the burgundy phone, scripts/render_hero.py) + typography
   10.0 - 25 s   the real Lacrydia app (deterministic recordings from capture/seq) on a virtual 3D device, moving virtual camera, depth of
                 field, glass sheen, bloom, floating photographs, typography
   25  - 30  s   brand end card
The virtual camera uses the same pinhole model as the Blender camera (85 mm on a 36 mm sensor), so the 2D device lands exactly where the
3D phone's display was in the last hero frame (hand-over).
   python3 compose_film.py --w 1920 --out renders/film_1080 [--frames 0-899] [--step 1] [--only 210,300]"""
import argparse, json, math, os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import p, assert_writable
from timeline import curve

ap = argparse.ArgumentParser()
ap.add_argument("--w", type=int, default=1920)
ap.add_argument("--out", required=True)
ap.add_argument("--frames", default="0-899")
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--only", default=None)
ap.add_argument("--hero", default="renders/hero_review")
a = ap.parse_args()

W = a.w; H = W * 9 // 16; S = W / 1920.0
FPS = 30; NF = 900; HERO_END = 10.0
FOCAL_MM = 85.0
FX = W * FOCAL_MM / 36.0
JOURNEY = p("capture", "seq", "journey_a"); TABS = p("capture", "seq", "tabs_b")
FONT = lambda sz, wt="Medium": ImageFont.truetype(p("assets", "fonts", f"InterDisplay-{wt}.otf"), int(sz * S))
CTX = np.array([0.0, 0.0, 0.0])

# ============================================================================================================ small helpers
def ss(x):                      # smoothstep
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def seg(t, t0, t1):             # 0..1 progress with smoothstep
    return ss((t - t0) / (t1 - t0))
def lerp(a_, b_, k): return a_ + (b_ - a_) * k

_cache = {}
def load_rgb(path):
    if path not in _cache:
        if len(_cache) > 40: _cache.pop(next(iter(_cache)))
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        im = im[:, :, :3].astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)
        _cache[path] = im[:, :, ::-1].copy()                      # RGB float 0..1
    return _cache[path]

def seq_frame(dirp, x):         # fractional frame index -> blended RGB float image
    n = len([f for f in os.listdir(dirp) if f.endswith(".jpg")])
    x = min(max(x, 0.0), n - 1.0); i = int(math.floor(x)); k = x - i
    A = load_rgb(os.path.join(dirp, f"f{i:04d}.jpg"))
    if k < 1e-3 or i + 1 >= n: return A
    return A * (1 - k) + load_rgb(os.path.join(dirp, f"f{i+1:04d}.jpg")) * k

# ============================================================================================================ recording time maps
J_MAP = curve([(10.0, 0), (10.5, 24), (12.6, 93), (13.1, 117), (13.4, 123), (13.8, 140), (15.2, 226), (15.6, 244), (15.9, 262), (16.9, 322), (17.1, 340), (30, 372)])
T_MAP = curve([(17.0, 0), (17.15, 6), (18.5, 95), (18.65, 102), (19.9, 190), (20.05, 200), (21.4, 249), (30, 268)])

# ============================================================================================================ assets
def rrect(size, r, ss_=3):
    w_, h_ = size
    m = Image.new("L", (w_ * ss_, h_ * ss_), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w_ * ss_ - 1, h_ * ss_ - 1], radius=r * ss_, fill=255)
    return np.asarray(m.resize((w_, h_), Image.LANCZOS), np.float32) / 255.0

SCR_W_CM = 6.775; SCR_PX = (1206, 2622); PXCM = SCR_PX[0] / SCR_W_CM
MARGIN = 0.20; MPX = int(round(MARGIN * PXCM))
BODY_PX = (SCR_PX[0] + 2 * MPX, SCR_PX[1] + 2 * MPX)
BODY_CM = (BODY_PX[0] / PXCM, BODY_PX[1] / PXCM)
R_SCR = int(0.89 * PXCM); R_BODY = R_SCR + MPX; GLASS = int(0.10 * PXCM)

def device_base():
    """Burgundy metal rim + black glass bezel; the screen window is cut by a mask at composite time."""
    h_, w_ = BODY_PX[1], BODY_PX[0]
    yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
    u, v = xx / w_, yy / h_
    rim = (0.20 + 0.55 * np.clip(1.3 - 2.2 * (u + 0.35 * v), 0, 1) + 0.25 * np.clip(2.4 * (u - 0.78), 0, 1))[..., None]
    col = np.array([0.46, 0.13, 0.20], np.float32) * rim * 1.6
    body = rrect(BODY_PX, R_BODY); glass_m = rrect((w_ - 2 * GLASS, h_ - 2 * GLASS), R_BODY - GLASS)
    glass = np.zeros((h_, w_), np.float32); glass[GLASS:h_ - GLASS, GLASS:w_ - GLASS] = glass_m
    img = col * (1 - glass[..., None]) + np.array([0.012, 0.012, 0.014], np.float32) * glass[..., None]
    ring = np.clip(body - glass, 0, 1)
    return img, body, col, ring
BASE_RGB, BODY_A, RIM_RGB, RIM_RING = device_base()
RIM_SLICE_D = None
RIM_SLICE = np.dstack([np.broadcast_to(RIM_RGB, BASE_RGB.shape) * 0.9, BODY_A])
SCR_MASK = np.zeros(BODY_A.shape, np.float32); SCR_MASK[MPX:MPX + SCR_PX[1], MPX:MPX + SCR_PX[0]] = rrect(SCR_PX, R_SCR)

def side_texture(length_px, along):
    """Brushed burgundy metal strip for a device side face (1 px high gradient across thickness, light streak along the length)."""
    th_ = 64; xs = np.linspace(0, 1, th_, dtype=np.float32)[None, :, None]
    ys = np.linspace(0, 1, length_px, dtype=np.float32)[:, None, None]
    base = np.array([0.40, 0.11, 0.17], np.float32)
    shade = 0.35 + 0.9 * np.exp(-((xs - 0.35) / 0.22) ** 2) + 0.25 * np.exp(-((ys - along) / 0.18) ** 2)
    img = np.broadcast_to(base * shade, (length_px, th_, 3)).copy()
    return np.dstack([np.clip(img, 0, 1), np.ones((length_px, th_), np.float32)])
RIM_SLICE_D = cv2.resize(RIM_SLICE, (BODY_PX[0] // 2, BODY_PX[1] // 2), interpolation=cv2.INTER_AREA)
SIDE_TEX = {"v": side_texture(512, 0.3), "h": side_texture(256, 0.5)}

def rim_light_map(pos):
    """Specular streak that travels around the metal rim (0..1), drawn at quarter resolution."""
    h_, w_ = BODY_PX[1], BODY_PX[0]
    yy, xx = np.mgrid[0:h_:4, 0:w_:4].astype(np.float32)
    d = (xx / w_ + 0.45 * yy / h_) - pos * 2.2 + 0.4
    hl = np.exp(-(d / 0.10) ** 2) + 0.25
    return cv2.resize(hl, (w_, h_), interpolation=cv2.INTER_LINEAR)

def device_texture(screen_rgb, sheen=None, rimlight=None):
    img = BASE_RGB.copy()
    if rimlight is not None:
        img = img + (RIM_RING * rimlight)[..., None] * np.array([1.0, 0.82, 0.88], np.float32) * 0.9
    win = np.zeros_like(img); win[MPX:MPX + SCR_PX[1], MPX:MPX + SCR_PX[0]] = screen_rgb
    m = SCR_MASK[..., None]
    img = img * (1 - m) + win * m
    if sheen is not None:                                              # glass reflection over screen + bezel
        g = np.clip(sheen, 0, 1)[..., None]; img = img + g * (0.55 * (1 - m * 0.0))
    return np.dstack([img, BODY_A])                                    # RGBA, straight alpha

def sheen_map(pos, strength):
    """Soft diagonal reflection band across the device glass; pos 0..1 moves it across."""
    h_, w_ = BODY_PX[1], BODY_PX[0]
    yy, xx = np.mgrid[0:h_:4, 0:w_:4].astype(np.float32)
    d = (xx / w_ * 0.55 + yy / h_ * 0.45) - (pos * 1.6 - 0.3)
    band = np.exp(-(d / 0.07) ** 2) * 0.55 + np.exp(-(d / 0.30) ** 2) * 0.20
    return cv2.resize(band * strength, (w_, h_), interpolation=cv2.INTER_LINEAR)

# photographs for floating cards: p3,p6,p8,p18,p17,p21 (the app's own demo photos)
PH = {}
for pid in ["p3", "p6", "p8", "p18", "p17", "p21"]:
    f = p("assets", "lacrydia", "photos", pid + ".jpg")
    if os.path.exists(f):
        im = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        h_, w_ = im.shape[:2]; m = rrect((w_, h_), int(w_ * 0.07))
        PH[pid] = np.dstack([im, m])

# ============================================================================================================ virtual camera + quads
class Cam:
    def __init__(s, pos, tgt, focal=FOCAL_MM, shift=(0.0, 0.0), roll=0.0):
        s.pos = np.array(pos, float); f = np.array(tgt, float) - s.pos; s.f = f / np.linalg.norm(f)
        r = np.cross(s.f, [0, 0, 1.0]); s.r = r / np.linalg.norm(r); s.u = np.cross(s.r, s.f)
        if roll:
            c_, n_ = math.cos(math.radians(roll)), math.sin(math.radians(roll)); r0, u0 = s.r.copy(), s.u.copy()
            s.r = r0 * c_ + u0 * n_; s.u = -r0 * n_ + u0 * c_
        s.fx = W * focal / 36.0; s.shift = shift
    def project(s, P):
        v = np.asarray(P, float) - s.pos; z = v @ s.f
        return np.array([W / 2 + s.shift[0] * W + s.fx * (v @ s.r) / z, H / 2 + s.shift[1] * W - s.fx * (v @ s.u) / z]), z

def rot(yaw, pitch, roll):
    cy, sy, cp, sp, cr, sr = [fn(math.radians(v)) for v in (yaw, pitch, roll) for fn in (math.cos, math.sin)]
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]); Ry = np.array([[cr, 0, sr], [0, 1, 0], [-sr, 0, cr]])
    return Rz @ Rx @ Ry

def quad_corners(center, size_cm, yaw=0, pitch=0, roll=0):
    w_, h_ = size_cm; R = rot(yaw, pitch, roll)
    loc = [(-w_ / 2, 0, h_ / 2), (w_ / 2, 0, h_ / 2), (w_ / 2, 0, -h_ / 2), (-w_ / 2, 0, -h_ / 2)]
    return [np.asarray(center, float) + R @ np.array(c) for c in loc]

def warp_quad(cam, tex, corners, canvas_size):
    """Perspective-project an RGBA texture; returns (RGBA layer premultiplied, mean depth)."""
    pr = [cam.project(c) for c in corners]; dst = np.array([q[0] for q in pr], np.float32); zs = [q[1] for q in pr]
    if min(zs) < 1.0: return None, None
    th, tw = tex.shape[:2]
    tgt_w = max(np.linalg.norm(dst[1] - dst[0]), np.linalg.norm(dst[2] - dst[3])); tgt_h = max(np.linalg.norm(dst[3] - dst[0]), np.linalg.norm(dst[2] - dst[1]))
    k = min(1.0, 1.6 * max(tgt_w / tw, tgt_h / th))
    if k < 1.0: tex = cv2.resize(tex, (max(2, int(tw * k)), max(2, int(th * k))), interpolation=cv2.INTER_AREA); th, tw = tex.shape[:2]
    src = np.array([[0, 0], [tw, 0], [tw, th], [0, th]], np.float32)
    x0, y0 = np.floor(dst.min(0)).astype(int) - 2; x1, y1 = np.ceil(dst.max(0)).astype(int) + 2
    if x1 < 0 or y1 < 0 or x0 > canvas_size[0] or y0 > canvas_size[1]: return None, None
    pm = np.dstack([tex[..., :3] * tex[..., 3:4], tex[..., 3:4]])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(pm, M, canvas_size, flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0)), float(np.mean(zs))

def over(canvas, layer):          # layer premultiplied RGBA
    canvas[:] = layer[..., :3] + canvas * (1 - layer[..., 3:4])

# ============================================================================================================ background, particles
def background(t, center=None, amber=0.0):
    """Coal black with a very soft pool of light behind the subject (and, on the end card, a faint amber glow)."""
    cx, cy = (center if center is not None else (W / 2, H / 2))
    yy, xx = np.mgrid[0:H:8, 0:W:8].astype(np.float32)
    r2 = ((xx - cx) / (0.30 * W)) ** 2 + ((yy - cy) / (0.62 * H)) ** 2
    pool = np.exp(-r2) * 0.030                                              # cool white pool behind the device
    top = np.clip(1 - yy / H * 1.2, 0, 1) ** 2 * 0.006                       # a hint of overhead light
    img = np.dstack([pool * 0.92 + top, pool * 0.97 + top, pool * 1.10 + top]) + 0.0015
    if amber > 0:
        ra = ((xx - W / 2) / (0.34 * W)) ** 2 + ((yy - H * 0.58) / (0.40 * H)) ** 2
        g = np.exp(-ra) * 0.050 * amber
        img = img + np.dstack([g * 1.0, g * 0.55, g * 0.12])
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)

rng = np.random.default_rng(11)
PARTS = [dict(x=rng.uniform(-60, 60), z=rng.uniform(-30, 30), y=rng.uniform(10, 90), r=rng.uniform(0.25, 1.1), ph=rng.uniform(0, 6.28), sp=rng.uniform(0.15, 0.5)) for _ in range(46)]
def particles(canvas, cam, t, amount):
    if amount <= 0: return
    lay = np.zeros((H, W, 3), np.float32)
    for q in PARTS:
        P = np.array([q["x"] + 2.5 * math.sin(t * q["sp"] + q["ph"]), q["y"], q["z"] + 3 * math.cos(t * q["sp"] * 0.8 + q["ph"]) + t * 0.3 % 60 - 30])
        pt, z = cam.project(P)
        if z < 5 or not (0 <= pt[0] < W and 0 <= pt[1] < H): continue
        rad = max(1.5, q["r"] * cam.fx / z * 0.9)
        cv2.circle(lay, (int(pt[0]), int(pt[1])), int(rad), (0.55, 0.30, 0.38), -1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 1.6 * S)
    canvas += lay * 0.22 * amount

# ============================================================================================================ typography
_txt = {}
def text_img(lines, size, weight="Medium", align="left", track=0.0, color=(244, 244, 246), line_gap=1.12):
    key = (tuple(lines), size, weight, align, track)
    if key in _txt: return _txt[key]
    f = FONT(size, weight); pad = int(size * S * 0.6)
    ws = []
    for ln in lines:
        wsum = sum(f.getlength(ch) + track * size * S for ch in ln) if track else f.getlength(ln); ws.append(wsum)
    tw = int(max(ws)) + 2 * pad; lh = int(size * S * line_gap); th = lh * len(lines) + 2 * pad
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        x = pad if align == "left" else (tw - ws[i]) / 2 if align == "center" else tw - pad - ws[i]
        y = pad + i * lh
        if track:
            for ch in ln: d.text((x, y), ch, font=f, fill=color + (255,)); x += f.getlength(ch) + track * size * S
        else: d.text((x, y), ln, font=f, fill=color + (255,))
    arr = np.asarray(im, np.float32) / 255.0; _txt[key] = arr; return arr

def draw_text(canvas, arr, cx, cy, alpha, rise=0.0, blur=0.0, anchor="left", gain=1.0):
    """Premultiplied composite of a text image; anchor: left edge at cx, or centre."""
    if alpha <= 0.002: return
    th, tw = arr.shape[:2]
    x0 = int(cx - (0 if anchor == "left" else tw / 2)); y0 = int(cy - th / 2 + rise)
    lay = np.dstack([arr[..., :3] * arr[..., 3:4], arr[..., 3:4]]) * alpha
    if blur > 0.3: lay = cv2.GaussianBlur(lay, (0, 0), blur)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + tw), min(H, y0 + th)
    if xb <= xa or yb <= ya: return
    sub = lay[ya - y0:yb - y0, xa - x0:xb - x0]
    canvas[ya:yb, xa:xb] = sub[..., :3] * gain + canvas[ya:yb, xa:xb] * (1 - sub[..., 3:4])

def reveal(t, t0, dur=0.7):       # eased 0..1
    return ss((t - t0) / dur)
def line_anim(t, t_in, t_out, fade=0.35):
    a_in = reveal(t, t_in, 0.55); a_out = 1.0 - ss((t - t_out) / fade)
    return a_in * a_out, (1 - a_in) * 22 * S, (1 - a_in) * 4.0 * S

def logo_mark(h_px, color=(255, 255, 255)):
    from svgpathtools import parse_path
    d = open(p("assets", "lacrydia", "logo", "ikon-09-white.svg")).read().split(' d="')[1].split('"')[0]
    sc = 4; im = Image.new("L", (600 * sc, 600 * sc), 0); dr = ImageDraw.Draw(im)
    for sp in parse_path(d).continuous_subpaths():
        dr.polygon([(seg_.start.real * sc, (seg_.start.imag - 6) * sc) for seg_ in sp], fill=255)
    bb = im.getbbox(); im = im.crop(bb); r = h_px / im.height
    im = im.resize((max(2, int(im.width * r)), int(h_px)), Image.LANCZOS)
    al = np.asarray(im, np.float32) / 255.0
    return np.dstack([np.ones_like(al) * color[0] / 255, np.ones_like(al) * color[1] / 255, np.ones_like(al) * color[2] / 255, al])

# ============================================================================================================ camera + device choreography
# device side per scene (+1 device left of centre / text right, -1 device right / text left)
def cam_state(t):
    """(azimuth deg, elevation deg, distance cm, target x, target z, roll deg). Alternating sides, swinging orbit, push-ins."""
    az = curve([(0, 0), (10.35, 0), (11.6, -14), (13.2, -6), (14.0, 15), (15.4, 21), (16.0, -15), (17.1, -20), (17.6, 12), (18.9, 16), (19.6, -14), (20.8, -18), (21.8, 12), (22.5, 4), (25, 14), (30, 14)])
    el = curve([(0, 0), (10.35, 0), (11.7, 4), (13.4, -3), (15.0, 5), (16.5, -4), (18.0, 4), (19.6, -3), (21.2, 5), (22.5, 3), (25, 9), (30, 9)])
    dist = curve([(0, 66), (10.0, 66), (11.6, 68), (13.2, 70), (14.8, 68), (16.4, 70), (18.0, 68), (19.8, 70), (21.4, 68), (22.4, 72), (23.4, 88), (25, 116), (30, 124)])
    tx = curve([(0, 0), (10.35, 0), (11.3, -4.6), (13.0, -4.6), (13.9, 4.6), (15.4, 4.6), (16.2, -4.6), (17.0, -4.6), (17.6, 4.6), (18.7, 4.6), (19.2, -4.6), (20.2, -4.6), (20.9, 4.6), (22.0, 4.6), (22.9, 0.0), (30, 0)])
    tz = curve([(0, 0), (10.0, 0), (12, 0.6), (17, -0.4), (22, 0.0), (25, -0.6), (30, -0.6)])
    ro = curve([(0, 0), (10.35, 0), (11.6, -2.5), (13.3, 1.5), (14.8, 3.0), (16.0, -2.5), (17.4, 2.0), (19.0, 2.5), (20.0, -2.0), (21.6, 2.0), (22.8, 0.0), (30, 0)])
    return az(t), el(t), dist(t), tx(t), tz(t), ro(t)

def make_cam(t):
    az, el, d, tx, tz, ro = cam_state(t)
    tgt = np.array([tx, 0.0, tz]); azr, elr = math.radians(az), math.radians(el)
    pos = tgt + d * np.array([math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)])
    return Cam(pos, tgt, FOCAL_MM, roll=ro)

SIDE_YAW = 20.0
def side_device_x(t):             # flanking devices slide in for the "complete experience" shot
    return 1.0 - seg(t, 22.5, 24.0)
def brand_fade(t): return seg(t, 25.0, 26.3)

# floating photographs: (id, x, y(depth behind device), z, yaw, size_h, in, out)
CARDS = []        # floating photographs were removed (they read as blurry blobs on the coal-black background)

# ============================================================================================================ the frame
HERO_DIR = p(a.hero)
_hero_ids = sorted(int(f[1:5]) for f in os.listdir(HERO_DIR) if f.startswith("f") and f.endswith(".png")) if os.path.isdir(HERO_DIR) else []
_flow_cache = {}
_dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)

def _flow(n0, n1):
    """Dense flow n0 -> n1 and n1 -> n0 at half resolution (cached)."""
    key = (n0, n1)
    if key not in _flow_cache:
        if len(_flow_cache) > 6: _flow_cache.pop(next(iter(_flow_cache)))
        A, B = load_rgb(os.path.join(HERO_DIR, f"f{n0:04d}.png")), load_rgb(os.path.join(HERO_DIR, f"f{n1:04d}.png"))
        sm = lambda im: cv2.cvtColor(cv2.resize((np.clip(im, 0, 1) ** 0.55 * 255).astype(np.uint8), (im.shape[1] // 2, im.shape[0] // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        ga, gb = sm(A), sm(B)
        fab, fba = _dis.calc(ga, gb, None), _dis.calc(gb, ga, None)
        h2, w2 = fab.shape[:2]
        gx, gy = np.meshgrid(np.arange(w2, dtype=np.float32), np.arange(h2, dtype=np.float32))
        back = cv2.remap(fba, gx + fab[..., 0], gy + fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        err = np.linalg.norm(fab + back, axis=2)                      # forward-backward consistency: large where the flow is unreliable
        conf = np.exp(-(cv2.GaussianBlur(err, (0, 0), 2.0) / 1.2) ** 2).astype(np.float32)
        _flow_cache[key] = (fab, fba, conf)
    return _flow_cache[key]

def _warp(img, flow, k):
    """Backward-warp img by k * flow (flow given at half resolution)."""
    h_, w_ = img.shape[:2]
    fl = cv2.resize(flow, (w_, h_), interpolation=cv2.INTER_LINEAR) * 2.0 * k
    gx, gy = np.meshgrid(np.arange(w_, dtype=np.float32), np.arange(h_, dtype=np.float32))
    return cv2.remap(img, gx - fl[..., 0], gy - fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def hero_frame(t):
    """The 3D hero at film time t. Cycles frames exist every 2-3 frames; in-betweens come from optical-flow interpolation."""
    f = min(t * FPS + 1, _hero_ids[-1] if _hero_ids else 1)
    if not _hero_ids: return np.zeros((H, W, 3), np.float32)
    import bisect
    j = bisect.bisect_right(_hero_ids, f + 1e-6) - 1; n0 = _hero_ids[max(j, 0)]
    if abs(f - n0) < 1e-3 or j + 1 >= len(_hero_ids): out = load_rgb(os.path.join(HERO_DIR, f"f{n0:04d}.png"))
    else:
        n1 = _hero_ids[j + 1]; k = (f - n0) / (n1 - n0)
        A, B = load_rgb(os.path.join(HERO_DIR, f"f{n0:04d}.png")), load_rgb(os.path.join(HERO_DIR, f"f{n1:04d}.png"))
        fab, fba, conf = _flow(n0, n1)
        warped = _warp(A, fba, k) * (1 - k) + _warp(B, fab, 1 - k) * k    # each frame is pulled towards the time between them
        cf = cv2.resize(conf, (A.shape[1], A.shape[0]), interpolation=cv2.INTER_LINEAR)[..., None]
        out = warped * cf + (A * (1 - k) + B * k) * (1 - cf)              # plain cross-fade wherever the flow cannot be trusted
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_AREA if out.shape[1] > W else cv2.INTER_CUBIC)

def screen_for(t, which="main"):
    if which == "main":
        if t < 17.0: return seq_frame(JOURNEY, J_MAP(t))
        return seq_frame(TABS, T_MAP(t))
    if which == "left": return seq_frame(JOURNEY, 100)
    return seq_frame(JOURNEY, 296 + 0.0)

def render_frame(i):
    t = i / FPS
    canvas = np.zeros((H, W, 3), np.float32)
    # 0 - 7.5 s: the 3D hero is the picture
    plate_a = 1.0 - seg(t, HERO_END, HERO_END + 0.3)
    hero = hero_frame(min(t, HERO_END)) if t < HERO_END + 0.35 else None
    cam = make_cam(t)
    cen_px = cam.project(np.array([0.0, 0.0, 0.0]))[0]
    canvas[:] = background(t, (cen_px[0], cen_px[1]), seg(t, 25.4, 27.0))
    if hero is not None: canvas = canvas * (1 - plate_a) + hero * plate_a
    if t < HERO_END:
        hero_text(canvas, t)
        return finish(canvas, t)
    # --- 2D app on a virtual device -------------------------------------------------------------------------
    bf = brand_fade(t)
    dev_alpha = 1.0 - bf
    layers = []
    # floating photographs (behind the device)
    for pid, x, y, z, yaw, hh, tin, tout in CARDS:
        if pid not in PH: continue
        al = reveal(t, tin, 1.4) * (1 - seg(t, 24.0, 25.0))
        if al <= 0.01: continue
        w_ = hh * PH[pid].shape[1] / PH[pid].shape[0]
        drift = np.array([1.4 * math.sin(t * 0.5 + x), 0, 1.0 * math.cos(t * 0.4 + z)])
        cr = quad_corners(np.array([x, y, z]) + drift, (w_, hh), yaw + 3 * math.sin(t * 0.3 + x), 3 * math.sin(t * 0.25 + z), 0)
        lay, zc = warp_quad(cam, PH[pid], cr, (W, H))
        if lay is not None: layers.append((zc, lay * (al * 0.30), "card"))
    # devices
    dev_specs = [("main", np.array([0.0, 0.0, 0.0]), 0.0, 1.0)]
    sd = side_device_x(t)
    if t > 22.4:
        dev_specs.append(("left", np.array([-9.6 - 6 * sd, 4.0 + 6 * sd, -0.4]), SIDE_YAW, 1 - sd))
        dev_specs.append(("right", np.array([9.6 + 6 * sd, 4.0 + 6 * sd, -0.4]), -SIDE_YAW, 1 - sd))
    sheen_pos = ((t * 0.18) % 1.8) / 1.8
    for name, cen, yaw, al in dev_specs:
        scr = screen_for(t, name)
        if name == "main":
            yaw = yaw
        tex = device_texture(scr, sheen_map(sheen_pos if name == "main" else 0.2, 0.34), rim_light_map(((t * 0.22 + (0.0 if name == 'main' else 0.37)) % 1.4) / 1.4) * 0.9)
        cr = quad_corners(cen, BODY_CM, yaw)
        depth = rot(yaw, 0, 0) @ np.array([0.0, 0.875, 0.0])                  # body thickness, away from the viewer
        nsl = 9                                                                 # the metal body: rounded slices from back to front (no square corners)
        for k in range(1, nsl + 1):
            fr = k / nsl
            sl, sz = warp_quad(cam, RIM_SLICE_D, [c + depth * fr for c in cr], (W, H))
            if sl is not None: layers.append((sz + 0.05 * fr, sl * ((1.0 - 0.60 * fr) * al * dev_alpha), "side"))
        lay, zc = warp_quad(cam, tex, cr, (W, H))
        if lay is not None: layers.append((zc, lay * (al * dev_alpha), name))
        if t > 22.0:                                   # glossy floor: mirrored device, fading with distance from the floor line
            fa = seg(t, 22.0, 23.4)
            zf_ = cen[2] - BODY_CM[1] / 2 - 0.15
            mc = [np.array([c[0], c[1], 2 * zf_ - c[2]]) for c in cr]
            rt = tex.copy(); rows = np.linspace(0, 1, rt.shape[0], dtype=np.float32)[:, None]
            rt[..., 3] *= (0.34 * rows ** 2.4)
            rl, rz = warp_quad(cam, rt, [mc[3], mc[2], mc[1], mc[0]][::-1] if False else [mc[0], mc[1], mc[2], mc[3]], (W, H))
            if rl is not None: layers.append((rz + 0.5, rl * (al * dev_alpha * fa), "reflection"))
    layers.sort(key=lambda q: -q[0])
    zf = np.linalg.norm(cam.pos - CTX)
    dev_glow = np.zeros((H // 4, W // 4, 3), np.float32)
    for zc, lay, kind in layers:
        if kind == "card":
            sg = min(22.0 * S, 2.4 * S * abs(zc - zf) / 6.0)
            if sg > 0.4: lay = cv2.GaussianBlur(lay, (0, 0), sg)
        over(canvas, lay)
        if kind in ("main", "left", "right"):
            small = cv2.resize(lay[..., :3], (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            dev_glow += small
    # bloom: the display lights its surroundings
    gl = cv2.GaussianBlur(dev_glow, (0, 0), 28 * S / 4)
    gl = cv2.resize(gl, (W, H), interpolation=cv2.INTER_CUBIC)
    canvas += gl * np.array([0.20, 0.22, 0.28], np.float32) * 0.40 * (1 - bf)
    # typography
    txt = typography(canvas, t)
    return finish(canvas, t)

def hero_text(canvas, t):
    """Titles over the 3D shots (Apple-style big white sans, enters with a soft blur-in)."""
    def line(txt, t_in, t_out, x, y, size=74, anchor="left", wt="Medium"):
        arr = text_img([txt], size, "SemiBold", "left" if anchor == "left" else "center")
        al, rise, bl = line_anim(t, t_in, t_out); pad = int(size * S * 0.6)
        draw_text(canvas, arr, (x - pad) if anchor == "left" else x, y + rise * 0.0, al, rise, bl, anchor=anchor)
    line("Meet Lacrydia.", 3.1, 4.9, W * 0.075, H * 0.80, 92)
    line("Your images.", 5.6, 7.45, W * 0.075, H * 0.50, 92)
    line("Your world.", 8.1, 9.75, W * 0.075, H * 0.50, 92)

def typography(canvas, t):
    L, R = W * 0.075, W * 0.925; cy = H * 0.5
    big = 86; med = 86
    def head(lines, t_in, t_out, side="left", dy=0.0, size=big):
        arr = text_img(lines, size, "SemiBold", "left" if side == "left" else "right")
        al, rise, bl = line_anim(t, t_in, t_out); pad = int(size * S * 0.6)
        x = L - pad if side == "left" else R - arr.shape[1] + pad
        draw_text(canvas, arr, x, cy + dy * H, al, rise, bl, anchor="left")
    sub = lambda lines, t_in, t_out, side="left", dy=0.0: head(lines, t_in, t_out, side, dy, 30)
    # app scenes: the text sits opposite the device (sides alternate, see cam_state)
    head(["Your life,"], 10.45, 12.9, "left", -0.05); head(["branch by branch."], 11.0, 12.9, "left", 0.05)
    head(["Every memory,"], 14.0, 15.3, "right", -0.05); head(["in its place."], 14.35, 15.3, "right", 0.05)
    head(["Private"], 16.3, 17.0, "left", -0.05); head(["by default."], 16.55, 17.0, "left", 0.05)
    head(["Share."], 17.7, 18.5, "right"); head(["Discover."], 19.3, 20.0, "left"); head(["Collect."], 21.1, 22.4, "right")
    # scene 5: complete experience
    arr = text_img(["All of it. In one place."], 64, "SemiBold", "center")
    al, rise, bl = line_anim(t, 23.3, 25.0); draw_text(canvas, arr, W / 2, H * 0.14, al, rise, bl, anchor="center")
    # brand end card
    bf = seg(t, 25.4, 26.2)
    if t > 25.2:
        mk = logo_mark(150 * S); a_ = reveal(t, 26.25, 0.9)
        cx = W / 2; cyy = H * 0.40 + (1 - a_) * 20 * S
        if a_ > 0.002:
            sub_ = np.dstack([mk[..., :3] * mk[..., 3:4], mk[..., 3:4]]) * a_
            h_, w_ = mk.shape[:2]; x0, y0 = int(cx - w_ / 2), int(cyy - h_ / 2)
            canvas[y0:y0 + h_, x0:x0 + w_] = sub_[..., :3] + canvas[y0:y0 + h_, x0:x0 + w_] * (1 - sub_[..., 3:4])
        word = text_img(["LACRYDIA"], 52, "SemiBold", "center", track=0.34)
        al, rise, bl = line_anim(t, 26.55, 99); draw_text(canvas, word, W / 2, H * 0.58, al, rise, bl, anchor="center")
        s1 = text_img(["YOUR IMAGES.  YOUR WORLD."], 30, "Medium", "center", track=0.22, color=(190, 190, 195))
        al, rise, bl = line_anim(t, 27.7, 99); draw_text(canvas, s1, W / 2, H * 0.70, al * 0.9, rise, bl, anchor="center")

def finish(canvas, t):
    yy, xx = np.mgrid[0:H:8, 0:W:8].astype(np.float32); xx = xx / W - 0.5; yy = yy / H - 0.5
    vig = cv2.resize(1.0 - 0.55 * (xx ** 2 * 1.2 + yy ** 2 * 1.6) ** 0.9, (W, H), interpolation=cv2.INTER_LINEAR)
    out = canvas * vig[..., None]
    rg = np.random.default_rng(int(t * 997) + 5)
    out += rg.normal(0, 0.012, (H, W, 1)).astype(np.float32)             # fine film grain
    fade = seg(t, 0.0, 0.5) * (1 - seg(t, 29.2, 30.0))
    out *= fade
    return np.clip(out, 0, 1)

# ============================================================================================================ main
if __name__ == "__main__":
    out_dir = assert_writable(p(a.out)); os.makedirs(out_dir, exist_ok=True)
    if a.only: idx = [int(x) for x in a.only.split(",")]
    else:
        s0, s1 = [int(x) for x in a.frames.split("-")]; idx = list(range(s0, s1 + 1, a.step))
    for i in idx:
        fp = os.path.join(out_dir, f"c{i:04d}.png")
        if os.path.exists(fp) and not a.only: continue
        img = render_frame(i)
        cv2.imwrite(fp, (img[:, :, ::-1] * 255 + 0.5).astype(np.uint8))
        if i % 30 == 0: print("frame", i, flush=True)

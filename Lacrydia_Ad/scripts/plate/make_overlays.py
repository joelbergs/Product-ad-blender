#!/usr/bin/env python3
"""Typography / end-card overlays for the Lacrydia film (transparent RGBA PNGs, full-frame size).

    python3 make_overlays.py --width 1920 --height 1080 [--out DIR]

Default DIR = ROOT/renders/overlays_<W>x<H>/.  Everything scales from H (text sizes, gaps, positions);
the left margin is 7 % of W (title safe).  Text/mark are rasterised at 4x/16x supersampling into an alpha mask
(no dark fringes) and positioned with sub-pixel precision; fonts are laid out with HarfBuzz (kerning) via Pillow/raqm.

Files: overlay_tagline_1.png  overlay_tagline_2.png  overlay_endcard_lockup.png
       overlay_endcard_status.png  overlay_endcard_url.png
Layout/copy come from ROOT/config/production.json ("copy", "brand"); timing lives in config/overlay_timing.json.
"""
import argparse, json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
SVG_MARK = os.path.join(ROOT, "assets", "lacrydia", "logo", "ikon-09-accent.svg")
MARK_VIEWBOX = (150, 162, 300, 288)       # x, y, w, h of the artwork inside the 600x600 SVG (the translate(0,-6) is irrelevant for the crop)
CAP = 0.7275                               # Inter cap height / font size
SS_TEXT, SS_MARK = 4, 16

# ---- layout constants (fractions of H unless noted) ----
MARGIN_X_OF_W = 0.07
TAG_CAP = 0.065
TAG_TRACK = -0.02            # em
TAG_LINE = 1.12              # baseline spacing in em
TAG_OPACITY = (0.72, 1.00)   # line 1, line 2
MARK_H = 0.085               # mark height of the end-card lockup
GAP_LOCKUP_STATUS = 0.062
GAP_STATUS_URL = 0.024
STATUS_FS = 0.029
URL_FS = 0.029
STATUS_OPACITY = 0.70
URL_OPACITY = 1.0


def hex_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def load_polys(svg):
    d = re.search(r'\bd="([^"]+)"', open(svg).read()).group(1)
    polys = []
    for sub in d.split("Z"):
        pts = re.findall(r"[ML]\s*(-?[\d.]+)\s+(-?[\d.]+)", sub)
        if pts: polys.append([(float(x), float(y)) for x, y in pts])
    fill = re.search(r'fill="(#[0-9A-Fa-f]{6})"', open(svg).read()).group(1)
    return polys, fill


class Font:
    """Metric font at 1000 px (kerning-aware) + real font at any size."""
    def __init__(self, fname):
        self.path = os.path.join(FONTS, fname)
        self.m = ImageFont.truetype(self.path, 1000, layout_engine=ImageFont.Layout.RAQM)
    def layout(self, text, size, track_em):
        """-> list of (char, x_offset_px) at `size`, and total advance (without trailing tracking)."""
        k = size / 1000.0; pos = []
        for i, ch in enumerate(text):
            x = (self.m.getlength(text[:i + 1]) - self.m.getlength(ch)) * k + i * track_em * size
            pos.append((ch, x))
        total = self.m.getlength(text) * k + (len(text) - 1) * track_em * size
        return pos, total
    def left_bearing(self, ch, size):
        return self.m.getbbox(ch, anchor="ls")[0] * size / 1000.0
    def right_ink(self, text, size, track_em):
        pos, _ = self.layout(text, size, track_em)
        ch, x = pos[-1]
        return x + self.m.getbbox(ch, anchor="ls")[2] * size / 1000.0


class Canvas:
    """Frame-sized RGBA output assembled from supersampled alpha masks drawn in local boxes."""
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.items = []     # (mask_L_fullsize_cropbox, box, rgb, opacity)

    def draw_masked(self, box, ss, painter, rgb, opacity):
        """box = (x0,y0,x1,y1) integer frame px; painter(draw, ss, ox, oy) draws white on an L image whose
        pixel (0,0) is frame point (ox,oy)."""
        x0, y0, x1, y1 = box
        m = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
        painter(ImageDraw.Draw(m), ss, x0, y0)
        m = m.resize((x1 - x0, y1 - y0), Image.BOX)
        self.items.append((m, (x0, y0), rgb, opacity))

    def render(self):
        out = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        # items never overlap in these layouts, so paste each as solid colour with its alpha*opacity
        for m, (x, y), rgb, op in self.items:
            a = m.point(lambda v: int(round(v * op)))
            layer = Image.new("RGBA", m.size, rgb + (0,)); layer.putalpha(a)
            out.alpha_composite(layer, (x, y))
        return out


def text_box(font, text, size, track, x_ink, base_y, pad):
    """Integer crop box and the draw origin x so that the ink-left edge sits at x_ink."""
    pos, _ = font.layout(text, size, track)
    ox = x_ink - font.left_bearing(text[0], size)
    right = ox + font.right_ink(text, size, track)
    asc, desc = 1.0 * size, 0.35 * size
    box = (int(ox) - pad, int(base_y - asc) - pad, int(right) + pad + 2, int(base_y + desc) + pad)
    return pos, ox, box


def draw_text(cv, font_name, text, size, track, x_ink, base_y, rgb, opacity, fcache):
    font = fcache.setdefault(font_name, Font(font_name))
    pad = max(4, int(size * 0.08))
    pos, ox, box = text_box(font, text, size, track, x_ink, base_y, pad)
    def painter(d, ss, bx, by):
        f = ImageFont.truetype(font.path, size * ss, layout_engine=ImageFont.Layout.RAQM)
        for ch, x in pos:
            if ch == " ": continue
            d.text(((ox + x - bx) * ss, (base_y - by) * ss), ch, font=f, fill=255, anchor="ls")
    cv.draw_masked(box, SS_TEXT, painter, rgb, opacity)
    return box


def draw_mark(cv, polys, x_left, y_top, mark_h, rgb):
    vx, vy, vw, vh = MARK_VIEWBOX
    s = mark_h / vh
    pad = 3
    box = (int(x_left) - pad, int(y_top) - pad, int(x_left + vw * s) + pad + 1, int(y_top + mark_h) + pad + 1)
    def painter(d, ss, bx, by):
        for poly in polys:
            pts = [((x_left + (x - vx) * s - bx) * SS_MARK, (y_top + (y - vy) * s - by) * SS_MARK) for x, y in poly]
            d.polygon(pts, fill=255)
    # mark uses its own (higher) supersampling
    cv.draw_masked(box, SS_MARK, painter, rgb, 1.0)
    return x_left + vw * s


def build(W, H, out_dir):
    cfg = json.load(open(os.path.join(ROOT, "config", "production.json")))
    brand, copy = cfg["brand"], cfg["copy"]
    paper, ink = hex_rgb(brand["paper"]), hex_rgb(brand["ink"])
    polys, svg_fill = load_polys(SVG_MARK)
    amber = hex_rgb(brand["amber"])
    assert svg_fill.upper() == brand["amber"].upper(), (svg_fill, brand["amber"])
    wm = brand["wordmark"]
    fc = {}
    x0 = MARGIN_X_OF_W * W
    os.makedirs(out_dir, exist_ok=True)
    info = {}

    # ---- taglines ----
    fs = TAG_CAP * H / CAP
    cap = CAP * fs
    block_h = cap + TAG_LINE * fs                     # cap-top of line 1 -> baseline of line 2
    top = H / 2 - block_h / 2
    base1 = top + cap; base2 = base1 + TAG_LINE * fs
    for n, (txt, base, op) in enumerate([(copy["tagline_line1"], base1, TAG_OPACITY[0]),
                                         (copy["tagline_line2"], base2, TAG_OPACITY[1])], 1):
        cv = Canvas(W, H)
        box = draw_text(cv, "InterDisplay-SemiBold.otf", txt, fs, TAG_TRACK, x0, base, paper, op, fc)
        name = f"overlay_tagline_{n}.png"; cv.render().save(os.path.join(out_dir, name), compress_level=6)
        info[name] = box

    # ---- end card ----
    M = MARK_H * H
    wfs = 0.4 * M / CAP                                # guideline ratio: wordmark cap = 0.4 x mark height (64 px mark -> 35.19 px font)
    sfs, ufs = STATUS_FS * H, URL_FS * H
    # block: lockup (height M) / gap / status cap / gap / url cap
    blk = M + GAP_LOCKUP_STATUS * H + CAP * sfs + GAP_STATUS_URL * H + CAP * ufs
    ytop = H / 2 - blk / 2
    cv = Canvas(W, H)
    mark_w = draw_mark(cv, polys, x0, ytop, M, amber)
    gap = wm["mark_gap_of_mark_height"] * M
    cap_w = CAP * wfs
    base_w = ytop + M / 2 + cap_w / 2                  # cap-height centred on the mark's centre
    # wordmark ink-left sits one 'gap' to the right of the mark
    draw_text(cv, "Inter-SemiBold.otf", "LACRYDIA", wfs, wm["tracking_em"], mark_w + gap, base_w, paper, 1.0, fc)
    cv.render().save(os.path.join(out_dir, "overlay_endcard_lockup.png"), compress_level=6)
    ybase_s = ytop + M + GAP_LOCKUP_STATUS * H + CAP * sfs
    cv = Canvas(W, H)
    draw_text(cv, "Inter-Regular.otf", copy["status_line"], sfs, 0.005, x0, ybase_s, paper, STATUS_OPACITY, fc)
    cv.render().save(os.path.join(out_dir, "overlay_endcard_status.png"), compress_level=6)
    ybase_u = ybase_s + GAP_STATUS_URL * H + CAP * ufs
    cv = Canvas(W, H)
    draw_text(cv, "Inter-Regular.otf", copy["url"], ufs, 0.005, x0, ybase_u, paper, URL_OPACITY, fc)
    cv.render().save(os.path.join(out_dir, "overlay_endcard_url.png"), compress_level=6)
    return out_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = os.path.abspath(a.out or os.path.join(ROOT, "renders", f"overlays_{a.width}x{a.height}"))
    if not (out + os.sep).startswith(ROOT + os.sep):
        sys.exit("refusing to write outside ROOT: " + out)
    build(a.width, a.height, out)
    for f in sorted(os.listdir(out)):
        if f.startswith("overlay_"): print(os.path.join(out, f), Image.open(os.path.join(out, f)).size)


if __name__ == "__main__":
    main()

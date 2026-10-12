"""The real Lacrydia mark (ikon-09, the L cut into nine slits), parsed from the brand SVG. Pure python (no bpy needed)."""
import re
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "lacrydia", "logo", "ikon-09-white.svg")


def polygons(svg_path=SVG):
    """Nine slit polygons in SVG units (y down), centred on the mark's bounding box. Returns (polys, (w, h))."""
    txt = open(svg_path).read()
    dy = 0.0
    m = re.search(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)", txt)
    if m:
        dy = float(m.group(2))
    d = re.search(r'<path[^>]* d="([^"]+)"', txt).group(1)
    polys = []
    for sub in re.split(r"[Zz]", d):
        nums = re.findall(r"[-\d.]+", sub)
        if len(nums) < 6:
            continue
        pts = [(float(nums[i]), float(nums[i + 1]) + dy) for i in range(0, len(nums) - 1, 2)]
        polys.append(pts)
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    polys = [[(x - cx, y - cy) for (x, y) in poly] for poly in polys]
    return polys, (x1 - x0, y1 - y0)


def draw_mask(path, size_px, centre_uv, height_uv, aspect, supersample=3):
    """Write a greyscale mask (white = mark) for a panel of given aspect (w/h). centre_uv/height_uv are in panel UV."""
    from PIL import Image, ImageDraw
    polys, (mw, mh) = polygons()
    W = size_px
    H = int(round(size_px / aspect))
    S = supersample
    im = Image.new("L", (W * S, H * S), 0)
    dr = ImageDraw.Draw(im)
    scale = (height_uv * H * S) / mh
    for poly in polys:
        pts = [(centre_uv[0] * W * S + x * scale, (1 - centre_uv[1]) * H * S + y * scale) for (x, y) in poly]
        dr.polygon(pts, fill=255)
    im = im.resize((W, H), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return path

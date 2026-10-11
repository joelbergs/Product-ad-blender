"""Labelled contact sheet for any folder of PNGs: python3 sheet_dir.py <dir> <glob> <cols> <out.png>"""
import glob, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import assert_writable
d, pat, cols, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
files = sorted(glob.glob(os.path.join(d, pat)))
W = 640
ims = []
for f in files:
    im = Image.open(f).convert("RGB"); im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
    ImageDraw.Draw(im).text((8, 6), os.path.basename(f), fill=(255, 166, 43)); ims.append(im)
rows = (len(ims) + cols - 1) // cols; H = ims[0].height
sheet = Image.new("RGB", (cols * W + (cols + 1) * 6, rows * H + (rows + 1) * 6), (30, 30, 30))
for i, im in enumerate(ims):
    sheet.paste(im, (6 + (i % cols) * (W + 6), 6 + (i // cols) * (H + 6)))
sheet.save(assert_writable(out)); print(out, sheet.size, len(files), "images")

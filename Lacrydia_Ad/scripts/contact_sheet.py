"""Contact sheet of PNGs with labels: python3 contact_sheet.py <dir> [cols] [out.png]"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from paths import p, assert_writable
d = sys.argv[1]
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3
files = sorted(glob.glob(os.path.join(p("renders", d), "*.png")))
if not files:
    sys.exit("no pngs")
W = 640
ims = []
for f in files:
    im = Image.open(f).convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
    ImageDraw.Draw(im).text((8, 6), os.path.basename(f), fill=(255, 166, 43))
    ims.append(im)
rows = (len(ims) + cols - 1) // cols
H = ims[0].height
sheet = Image.new("RGB", (cols * W + (cols + 1) * 6, rows * H + (rows + 1) * 6), (30, 30, 30))
for i, im in enumerate(ims):
    sheet.paste(im, (6 + (i % cols) * (W + 6), 6 + (i // cols) * (H + 6)))
out = assert_writable(sys.argv[3] if len(sys.argv) > 3 else p("renders", d, "_sheet.png"))
sheet.save(out)
print(out, sheet.size)

"""python sheet.py out.jpg a.png b.png ...   -> tiled preview sheet (2 columns)."""
import sys
from PIL import Image
out, fs = sys.argv[1], sys.argv[2:]
ims = [Image.open(f).convert("RGB") for f in fs]
w = 960
ims = [i.resize((w, int(w * i.height / i.width))) for i in ims]
cols = 2 if len(ims) > 1 else 1
rows = (len(ims) + cols - 1) // cols
h = max(i.height for i in ims)
sh = Image.new("RGB", (w * cols, h * rows))
for k, i in enumerate(ims):
    sh.paste(i, ((k % cols) * w, (k // cols) * h))
sh.save(out, quality=90)

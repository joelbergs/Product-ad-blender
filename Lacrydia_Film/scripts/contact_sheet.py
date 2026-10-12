"""python contact_sheet.py VIDEO OUT.jpg [--cols 4] [--times t1,t2,...|--every 3.5] [--w 480]"""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--cols", type=int, default=4); ap.add_argument("--w", type=int, default=480)
ap.add_argument("--times", default=""); ap.add_argument("--every", type=float, default=3.5)
a = ap.parse_args()
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout)
times = [float(x) for x in a.times.split(",")] if a.times else [i * a.every for i in range(int(dur / a.every) + 1) if i * a.every < dur - 0.05]
tmp = tempfile.mkdtemp()
ims = []
for k, t in enumerate(times):
    p = os.path.join(tmp, f"{k}.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1", "-vf", f"scale={a.w}:-2", p], check=True)
    ims.append((t, Image.open(p).convert("RGB")))
h = ims[0][1].height
rows = (len(ims) + a.cols - 1) // a.cols
sheet = Image.new("RGB", (a.cols * a.w + (a.cols + 1) * 6, rows * (h + 22) + 6), (14, 14, 18))
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 13)
for k, (t, im) in enumerate(ims):
    x = 6 + (k % a.cols) * (a.w + 6); y = 6 + (k // a.cols) * (h + 22)
    sheet.paste(im, (x, y)); d.text((x, y + h + 3), f"{t:5.1f} s", fill=(210, 214, 224), font=f)
sheet.save(a.out, quality=90)
print(a.out, len(ims), "frames")

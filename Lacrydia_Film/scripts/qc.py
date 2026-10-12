"""Automated QC of the finished film.   python qc.py ../final/final/lacrydia_film.mp4 [--out ../documentation/qc_report.md]

Checks: container/streams (codec, resolution, fps, duration, audio), black frames outside the planned dips, freezes,
frame-to-frame luminance jumps/flicker, loudness (EBU R128) and true peak, A/V duration match. Writes a Markdown report and a plot."""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--out", default=None); ap.add_argument("--plot", default=None)
a = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
film = json.load(open(os.path.join(ROOT, "config", "film.json")))

def probe():
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", a.video], capture_output=True, text=True)
    return json.loads(r.stdout)
P = probe()
v = [s for s in P["streams"] if s["codec_type"] == "video"][0]
au = [s for s in P["streams"] if s["codec_type"] == "audio"]
fps = eval(v["avg_frame_rate"])
dur_v = float(v.get("duration", P["format"]["duration"]))
dur_a = float(au[0]["duration"]) if au else 0.0

# decode small gray frames
W, H = 320, 180
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32) / 255.0
n = len(fr)
lum = fr.mean(axis=(1, 2))
diff = np.r_[0, np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))]
t = np.arange(n) / fps

# planned dark moments: shot fades (+-0.1 s around the start/end of faded shots) and the very first/last frames
planned = []
for s in film["shots"]:
    if s.get("fade_in", 0) > 0: planned.append((s["start"], s["start"] + s["fade_in"] * 0.6))
    if s.get("fade_out", 0) > 0: planned.append((s["start"] + s["dur"] - s["fade_out"] * 0.6, s["start"] + s["dur"]))
planned.append((0, 1.6)); planned.append((15.5, 16.2)); planned.append((38.5, 40.0))
def is_planned(tt): return any(a_ <= tt <= b_ for a_, b_ in planned)
black = [i for i in range(n) if lum[i] < 0.004 and not is_planned(t[i])]
# freezes: runs of >= 12 frames with near-zero difference outside the planned final hold
freeze_runs = []; run = 0
for i in range(1, n):
    if diff[i] < 0.00015: run += 1
    else:
        if run >= 12: freeze_runs.append((round(t[i - run], 2), round(t[i - 1], 2)))
        run = 0
if run >= 12: freeze_runs.append((round(t[n - run], 2), round(t[n - 1], 2)))
# luminance jumps (flicker / unplanned cuts): large frame diff relative to neighbourhood
med = np.median(diff[1:])
cuts = [round(float(t[i]), 2) for i in range(2, n - 1) if diff[i] > max(0.05, 6 * np.mean(diff[max(0, i - 6):i]))]
d2 = np.abs(np.diff(lum, 2))
starts = [sh['start'] for sh in film['shots']]
flick = [round(float(t[i + 1]), 2) for i in range(len(d2)) if d2[i] > 0.02 and not is_planned(t[i + 1]) and min(abs(t[i + 1] - x) for x in starts) > 0.12]

# audio
loud = {}
if au:
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", a.video, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary"):]
    for line in tail.splitlines():
        line = line.strip()
        for k in ("I:", "LRA:", "Peak:"):
            if line.startswith(k): loud[k.strip(":")] = line

ok = lambda c: "PASS" if c else "FAIL"
rep = []
rep.append(f"# QC report\n\nFile: `{os.path.basename(a.video)}`\n")
rep.append("| Check | Result | Detail |\n|---|---|---|")
rep.append(f"| Video stream | {ok(v['codec_name'] in ('h264','prores'))} | {v['codec_name']} {v.get('profile','')} {v['width']}x{v['height']} {fps:.3f} fps, {v.get('pix_fmt')} |")
rep.append(f"| Duration | {ok(abs(dur_v - film['duration']) < 0.1)} | video {dur_v:.3f} s (planned {film['duration']} s) |")
rep.append(f"| Audio stream | {ok(bool(au))} | {au[0]['codec_name']+' '+au[0].get('sample_rate','')+' Hz '+str(au[0].get('channels'))+' ch' if au else 'none'}; audio {dur_a:.3f} s |")
rep.append(f"| A/V length match | {ok(abs(dur_v - dur_a) < 0.1)} | |")
rep.append(f"| Black frames (unplanned) | {ok(len(black)==0)} | {len(black)} frames {('at ' + ', '.join(f'{x/fps:.2f}s' for x in black[:8])) if black else ''} |")
rep.append(f"| Freezes (>=0.5 s) | {ok(all(b >= film['duration']-1.6 for a_, b in freeze_runs))} | {freeze_runs if freeze_runs else 'none'} (the final brand hold is intentional) |")
rep.append(f"| Unplanned cuts / jumps | INFO | {cuts if cuts else 'none'} (hard cuts D->E->F are planned: 22.0 s, 25.5 s) |")
rep.append(f"| Luminance flicker | {ok(len(flick)==0)} | {flick if flick else 'none'} |")
for k, line in loud.items():
    rep.append(f"| Audio {k} | INFO | {line} |")
md = "\n".join(rep)
print(md)
if a.out:
    open(a.out, "w").write(md + "\n")
if a.plot:
    Wp, Hp = 1500, 260
    im = Image.new("RGB", (Wp, Hp), (12, 12, 16)); d = ImageDraw.Draw(im)
    for i in range(n - 1):
        x0 = int(i / n * Wp); x1 = int((i + 1) / n * Wp)
        d.line([(x0, Hp - 20 - lum[i] * (Hp - 40) * 2), (x1, Hp - 20 - lum[i + 1] * (Hp - 40) * 2)], fill=(90, 190, 255))
        d.line([(x0, Hp - 20 - min(diff[i] * 6, 1) * (Hp - 40)), (x1, Hp - 20 - min(diff[i + 1] * 6, 1) * (Hp - 40))], fill=(255, 190, 80))
    for s in film["shots"]:
        x = int(s["start"] / film["duration"] * Wp); d.line([(x, 0), (x, Hp)], fill=(70, 70, 80)); d.text((x + 3, 3), s["id"], fill=(220, 220, 230))
    im.save(a.plot)

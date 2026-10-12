"""Render the whole film (every shot module), resumable.
   python render_all.py --res 640x360 --samples 12 --step 4 --out ../renders/animatic
   python render_all.py --res 1920x1080 --samples 96 --step 2 --out ../renders/final --only A,B"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument("--res", default="640x360"); ap.add_argument("--samples", type=int, default=12)
ap.add_argument("--step", type=int, default=4); ap.add_argument("--out", required=True)
ap.add_argument("--only", default=""); ap.add_argument("--py", default=sys.executable)
a = ap.parse_args()
film = json.load(open(os.path.join(ROOT, "config", "film.json")))
fps = film["fps"]
# one render per scene module (TABLE covers D, E, F in one go)
jobs = {}
for s in film["shots"]:
    m = s["module"]
    t0 = s.get("t0", 0.0)
    f0, f1 = int(round(t0 * fps)), int(round((t0 + s["dur"]) * fps)) - 1
    j = jobs.setdefault(m, [f0, f1]); j[0] = min(j[0], f0); j[1] = max(j[1], f1)
only = [x for x in a.only.split(",") if x]
for m, (f0, f1) in jobs.items():
    if only and m not in only:
        continue
    out = os.path.join(a.out, m)
    cmd = [a.py, os.path.join(HERE, "render.py"), "--shot", m, "--frames", f"{f0}-{f1}", "--step", str(a.step), "--res", a.res,
           "--samples", str(a.samples), "--fps", str(fps), "--out", out]
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

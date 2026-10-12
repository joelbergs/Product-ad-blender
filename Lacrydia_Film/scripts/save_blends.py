"""Save one .blend per shot module (baked animation included for A, B, C, G, H) into ../project/.
Run AFTER (or instead of) the renders: frames that already exist in --out are skipped, so this only builds + bakes + saves.
   python save_blends.py --out ../renders/final"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "renders", "final"))
a = ap.parse_args()
film = json.load(open(os.path.join(ROOT, "config", "film.json"))); fps = film["fps"]
jobs = {}
for s in film["shots"]:
    t0 = s.get("t0", 0.0); f0, f1 = int(round(t0 * fps)), int(round((t0 + s["dur"]) * fps)) - 1
    j = jobs.setdefault(s["module"], [f0, f1]); j[0] = min(j[0], f0); j[1] = max(j[1], f1)
os.makedirs(os.path.join(ROOT, "project"), exist_ok=True)
for m, (f0, f1) in jobs.items():
    out = os.path.join(ROOT, "project", f"lacrydia_shot_{m}.blend")
    subprocess.run([sys.executable, os.path.join(HERE, "render.py"), "--shot", m, "--frames", f"{f0}-{f1}", "--step", "2", "--res", "1920x1080",
                    "--samples", "56", "--fps", str(fps), "--out", os.path.join(a.out, m), "--save-blend", out], check=True)
    print("saved", out)

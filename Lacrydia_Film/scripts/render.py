"""Render driver.   python render.py --shot B --frame 60 --res 960x540 --samples 32 --out /path/still.png
                    python render.py --shot B --frames 0-194 --step 2 --res 1920x1080 --samples 96 --out DIR"""
import argparse, importlib, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from lib import rig
from lib.anim import K

ap = argparse.ArgumentParser()
ap.add_argument("--shot", required=True)
ap.add_argument("--frame", type=int)
ap.add_argument("--frames")
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--res", default="960x540")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--out", required=True)
ap.add_argument("--no-blur", action="store_true")
ap.add_argument("--save-blend")
ap.add_argument("--exposure", type=float, default=0.0)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

mod = importlib.import_module(f"shots.shot_{a.shot.lower()}")
sc = rig.fresh_scene(a.fps)
w, h = map(int, a.res.lower().split("x"))
S = mod.build(sc)
if hasattr(mod, "receivers"):
    rig.link_receivers(rig.emitters(sc), mod.receivers(S))
rig.configure_render(sc, w, h, samples=a.samples, motion_blur=not a.no_blur and a.frames is not None)
n = int(round(mod.DURATION * a.fps))
sc.frame_start, sc.frame_end = 1, n
sc.render.fps = a.fps
BAKE = getattr(mod, "BAKE", True)
if a.frames:
    f0, f1 = map(int, a.frames.split("-"))
    if BAKE:
        K.baking = True
        for f in range(max(0, f0 - 1), min(n - 1, f1 + 1) + 1):
            K.frame = f + 1
            sc.frame_set(f + 1)
            mod.apply(f / a.fps, S)
        K.finish()
        K.baking = False
    else:
        sc.render.use_motion_blur = False
    os.makedirs(a.out, exist_ok=True)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    t0 = time.time()
    for f in range(f0, f1 + 1, a.step):
        p = os.path.join(a.out, f"{a.shot}_{f:04d}.exr")
        if os.path.exists(p):
            continue
        sc.frame_set(f + 1)
        if not BAKE:
            mod.apply(f / a.fps, S)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print(f"[{a.shot}] frame {f} done  {time.time() - t0:.0f}s", flush=True)
else:
    f = a.frame or 0
    sc.frame_set(f + 1)
    mod.apply(f / a.fps, S)
    sc.render.filepath = a.out
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[{a.shot}] still frame {f} -> {a.out}  {time.time() - t0:.1f}s")
    if a.out.endswith(".exr") or True:
        import grade
        grade.to_png(grade.read_exr(a.out), a.out.replace(".exr", ".png"), exposure=a.exposure)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)

"""Quick look: render chosen film times as stills, then make a labelled contact sheet.
   python3 render_still.py --profile thumb --times 1,2.5,4,6 --out previews/look1 [--finish silver]"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from paths import p, assert_writable
import timeline as T
from build_scene import build_scene
from animate_scenes import animate
from screen_driver import set_screen_image

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="thumb")
ap.add_argument("--times", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--finish", default=None)
ap.add_argument("--samples", type=int, default=None)
a = ap.parse_args()

sc = build_scene(a.profile, a.finish)
if a.samples:
    sc.cycles.samples = a.samples
out = assert_writable(p("renders", a.out))
os.makedirs(out, exist_ok=True)
times = [float(x) for x in a.times.split(",")]
frames = sorted({T.t_to_frame(t) for t in times})
# keyframe a small window around each requested frame so motion blur has neighbours
win = sorted({f + d for f in frames for d in (-1, 0, 1) if 1 <= f + d <= T.N_FRAMES})
animate(win)
for f in frames:
    t0 = time.time()
    sc.frame_set(f)
    set_screen_image(T.frame_to_t(f))
    sc.render.filepath = os.path.join(out, f"t{T.frame_to_t(f):06.2f}.png")
    bpy.ops.render.render(write_still=True)
    print(f"frame {f} t={T.frame_to_t(f):.2f}s  {time.time()-t0:.1f}s", flush=True)

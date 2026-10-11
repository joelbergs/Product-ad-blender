"""Renders the 3D hero part of the film (0 - HERO_END s) with Cycles. Resumable: existing frames are skipped.
   python3 render_hero.py --profile review --step 2 --out renders/hero_review            (every 2nd frame, 15 fps; the compositor blends to 30)
   python3 render_hero.py --profile thumb --times 0.5,2,4,5.5,6.8,7.5 --out renders/hero_test
The screen shows the first frame of the real Tree recording (same pixels the 2D part starts with)."""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from paths import p, assert_writable
import timeline as T
from build_scene import build_scene
from animate_scenes import animate

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="review")
ap.add_argument("--out", required=True)
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--times", default=None)
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--device", default="CPU")
ap.add_argument("--part", default=None, help="i/n: render only every n-th chunk, e.g. 0/2")
a = ap.parse_args()

sc = build_scene(a.profile, "burgundy", device=a.device)
if a.samples:
    sc.cycles.samples = a.samples
out = assert_writable(p(a.out))
os.makedirs(out, exist_ok=True)
node = bpy.data.materials["PHONE_Screen_MAT"].node_tree.nodes["SCREEN_IMAGE"]
img = bpy.data.images.load(p("capture", "seq", "journey_a", "f0000.jpg"), check_existing=True)
img.colorspace_settings.name = "sRGB"; img.alpha_mode = "NONE"; node.image = img

if a.times:
    frames = sorted({T.t_to_frame(float(x)) for x in a.times.split(",")})
else:
    last = T.t_to_frame(T.HERO_END)
    frames = list(range(1, last + 1, a.step))
    if frames[-1] != last:
        frames.append(last)
if a.part:
    i, n = map(int, a.part.split("/")); frames = frames[i::n]
win = sorted({f + d for f in frames for d in (-1, 0, 1) if 1 <= f + d <= T.N_FRAMES})
animate(win)
for f in frames:
    fp = os.path.join(out, f"f{f:04d}.png")
    if os.path.exists(fp):
        continue
    t0 = time.time(); sc.frame_set(f); sc.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    print(f"frame {f} t={T.frame_to_t(f):.2f}s  {time.time()-t0:.1f}s", flush=True)

# hand-over geometry: where the display's four corners land in the last hero frame (pixels), for the 2D compositor
if not a.times:
    import json
    from bpy_extras.object_utils import world_to_camera_view
    sc.frame_set(T.t_to_frame(T.HERO_END)); bpy.context.view_layer.update()
    scr = bpy.data.objects.get("PHONE_Screen")
    if scr:
        W, H = sc.render.resolution_x, sc.render.resolution_y
        xs = [scr.matrix_world @ v.co for v in scr.data.vertices]
        pts = [world_to_camera_view(sc, sc.camera, c) for c in xs]
        px = [(q.x * W, (1 - q.y) * H) for q in pts]
        json.dump({"W": W, "H": H, "min": [min(x for x, _ in px), min(y for _, y in px)], "max": [max(x for x, _ in px), max(y for _, y in px)]},
                  open(os.path.join(out, "handoff.json"), "w"))

"""Model quality-control renders in a neutral product-photography studio (static phone, many views).
   python3 render_phone_qc.py --version v05 [--profile qc] [--views ...] [--finish burgundy] [--device CPU] [--samples N] [--out previews/iphone18pro]
Files are named <version>_<view>.png and never overwritten (a new --version per pass)."""
import argparse, math, os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from paths import p, assert_writable, ROOT
from build_scene import build_scene
import screen_driver

# rz = phone yaw (deg); camera az/el (deg) around target; d (cm); f (mm); fs f-stop; tl = target in PHONE-local cm; ortho = visible height in cm
VIEWS = {
    "01_front_ortho":     dict(rz=0,   az=0,  el=0,   d=120, f=85,  fs=16, tl=(0, 0, 0),      ortho=17.0),
    "02_rear_ortho":      dict(rz=180, az=0,  el=0,   d=120, f=85,  fs=16, tl=(0, 0, 0),      ortho=17.0),
    "03_left_side":       dict(rz=90,  az=0,  el=0,   d=120, f=85,  fs=16, tl=(0, 0, 0),      ortho=17.0),
    "04_right_side":      dict(rz=-90, az=0,  el=0,   d=120, f=85,  fs=16, tl=(0, 0, 0),      ortho=17.0),
    "05_top_edge":        dict(rz=0,   az=0,  el=86,  d=26,  f=85,  fs=11, tl=(0, 0, 7.5)),
    "06_bottom_edge":     dict(rz=0,   az=0,  el=-86, d=26,  f=85,  fs=11, tl=(0, 0, -7.5)),
    "07_front_34":        dict(rz=-32, az=0,  el=9,   d=75,  f=100, fs=11, tl=(0, 0, 0)),
    "08_rear_34":         dict(rz=148, az=0,  el=14,  d=75,  f=100, fs=11, tl=(0, 0, 0)),
    "09_camera_macro":    dict(rz=156, az=-6, el=20,  d=34,  f=100, fs=8,  tl=(0.9, 0.3, 5.4)),
    "10_frame_button_macro": dict(rz=72, az=0, el=14, d=26,  f=120, fs=8,  tl=(-3.6, 0, 3.4)),
    "11_rear_glass_logo": dict(rz=172, az=12, el=12,  d=36,  f=100, fs=8,  tl=(0, 0, -1.6)),
    "12_hero":            dict(rz=146, az=-8, el=11,  d=78,  f=100, fs=9,  tl=(0.4, 0, 0.6)),
    # framed like Apple's film frames (27.75 s plateau straight on, 27.0 s main-lens macro) for side-by-side comparison
    "13_match_apple_plateau": dict(rz=180, az=0, el=-2, d=34, f=100, fs=11, tl=(0.0, 0.3, 5.0)),
    "14_match_apple_lens":    dict(rz=180, az=0, el=0,  d=9.5, f=100, fs=5.6, tl=(2.27, 0.35, 6.09)),
    # phone lying back-up, plateau to the left, camera low (12 deg) on the right side: like Apple's 8.4 s frame (protrusion, seams, buttons)
    "15_match_apple_side":    dict(rot=(90, 0, -90), rz=0, az=0, el=12, d=64, f=100, fs=11, tl=(0, 0, 0)),
}

ap = argparse.ArgumentParser()
ap.add_argument("--version", required=True)
ap.add_argument("--profile", default="qc")
ap.add_argument("--out", default="previews/iphone18pro")
ap.add_argument("--views", default=",".join(VIEWS))
ap.add_argument("--finish", default=None)
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--device", default="CPU")
ap.add_argument("--screen", default="on", choices=["on", "off"])
a = ap.parse_args()

sc = build_scene(a.profile, a.finish, studio="qc", device=a.device)
sc.render.use_motion_blur = False
if a.samples:
    sc.cycles.samples = a.samples
out = assert_writable(os.path.join(ROOT, a.out))
os.makedirs(out, exist_ok=True)
root, cam, tgt = bpy.data.objects["PHONE_Root"], bpy.data.objects["CAM_Main"], bpy.data.objects["CAM_Target"]
bpy.data.materials["PHONE_Screen_MAT"].node_tree.nodes["SCREEN_GAIN"].inputs[1].default_value = 1.9 if a.screen == "on" else 0.0
screen_driver.set_screen_image(21.0)
# which device actually renders
prefs = bpy.context.preferences.addons["cycles"].preferences
dev_info = dict(requested=a.device, scene_device=sc.cycles.device, compute_backend=prefs.compute_device_type,
                blender=bpy.app.version_string)
print("RENDER_DEVICE", json.dumps(dev_info), flush=True)

for name in a.views.split(","):
    v = VIEWS[name]
    root.rotation_euler = tuple(math.radians(r) for r in v["rot"]) if "rot" in v else (0, 0, math.radians(v["rz"]))
    bpy.context.view_layer.update()
    target = root.matrix_world @ Vector(v["tl"])
    az, el = math.radians(v["az"]), math.radians(v["el"])
    pos = target + Vector((v["d"] * math.sin(az) * math.cos(el), -v["d"] * math.cos(az) * math.cos(el), v["d"] * math.sin(el)))
    tgt.location, cam.location = target, pos
    cd = cam.data
    if "ortho" in v:
        cd.type, cd.ortho_scale = "ORTHO", v["ortho"] * 16 / 9
        cd.dof.use_dof = False
    else:
        cd.type, cd.lens = "PERSP", v["f"]
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = v["fs"]
        cd.dof.focus_distance = (pos - target).length
    t0 = time.time()
    sc.render.filepath = os.path.join(out, f"{a.version}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"{name}  {time.time()-t0:.1f}s", flush=True)

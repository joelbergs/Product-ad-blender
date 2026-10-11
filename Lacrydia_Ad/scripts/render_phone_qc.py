"""Dedicated model quality-control renders: neutral product-photography studio, static phone, many views.
   python3 render_phone_qc.py --profile thumb --out previews/qc_a [--views 01_front,09_macro_camera] [--finish silver] [--device CPU]"""
import argparse, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from paths import p, assert_writable
from build_scene import build_scene
import screen_driver

VIEWS = {   # rz = phone yaw (deg), camera az/el (deg) around target, d (cm), focal (mm), f-stop, target in PHONE-local cm
    "01_front":        dict(rz=0,   az=0,  el=0,   d=78, f=85,  fs=16, tl=(0, 0, 0)),
    "02_rear":         dict(rz=180, az=0,  el=0,   d=78, f=85,  fs=16, tl=(0, 0, 0)),
    "03_left_side":    dict(rz=90,  az=0,  el=0,   d=78, f=85,  fs=16, tl=(0, 0, 0)),
    "04_right_side":   dict(rz=-90, az=0,  el=0,   d=78, f=85,  fs=16, tl=(0, 0, 0)),
    "05_top_edge":     dict(rz=0,   az=0,  el=72,  d=60, f=100, fs=11, tl=(0, 0, 7.0)),
    "06_bottom_edge":  dict(rz=0,   az=0,  el=-72, d=60, f=100, fs=11, tl=(0, 0, -7.0)),
    "07_front_34":     dict(rz=-32, az=0,  el=9,   d=72, f=85,  fs=11, tl=(0, 0, 0)),
    "08_rear_34":      dict(rz=148, az=0,  el=14,  d=72, f=85,  fs=11, tl=(0, 0, 0)),
    "09_macro_camera": dict(rz=165, az=16, el=24,  d=26, f=135, fs=4,  tl=(0.4, 0.3, 5.2)),
    "10_macro_frame":  dict(rz=70,  az=0,  el=16,  d=26, f=120, fs=5,  tl=(-3.5, 0, 5.4)),
    "11_macro_corner": dict(rz=-35, az=0,  el=22,  d=24, f=120, fs=5,  tl=(3.0, -0.4, 6.6)),
    # framed like the supplied burgundy reference image (rear shoulder with the three lenses; front top corner with the island)
    "12_ref_rear":     dict(rz=150, az=-8, el=18,  d=42, f=100, fs=8,  tl=(-0.5, 0, 4.0)),
    "13_ref_front":    dict(rz=-26, az=0,  el=12,  d=38, f=100, fs=8,  tl=(1.2, -0.3, 4.6)),
}

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="thumb")
ap.add_argument("--out", required=True)
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
out = assert_writable(p("renders", a.out))
os.makedirs(out, exist_ok=True)
root, cam, tgt = bpy.data.objects["PHONE_Root"], bpy.data.objects["CAM_Main"], bpy.data.objects["CAM_Target"]
gain = bpy.data.materials["PHONE_Screen_MAT"].node_tree.nodes["SCREEN_GAIN"]
gain.inputs[1].default_value = 1.9 if a.screen == "on" else 0.0
screen_driver.set_screen_image(21.0)          # page 4 ("Together"): real screenshot + island overlay if the plate exists

for name in a.views.split(","):
    v = VIEWS[name]
    root.rotation_euler = (0, 0, math.radians(v["rz"]))
    bpy.context.view_layer.update()
    target = root.matrix_world @ Vector(v["tl"])
    az, el = math.radians(v["az"]), math.radians(v["el"])
    pos = target + Vector((v["d"] * math.sin(az) * math.cos(el), -v["d"] * math.cos(az) * math.cos(el), v["d"] * math.sin(el)))
    tgt.location, cam.location = target, pos
    cam.data.lens = v["f"]
    cam.data.dof.aperture_fstop = v["fs"]
    cam.data.dof.focus_distance = (pos - target).length
    t0 = time.time()
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
    print(f"{name}  {time.time()-t0:.1f}s", flush=True)

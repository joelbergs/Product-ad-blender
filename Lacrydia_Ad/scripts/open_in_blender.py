"""Open the whole commercial in Blender and follow / edit it live.

    blender --python Lacrydia_Ad/scripts/open_in_blender.py -- [--finish burgundy] [--profile preview] [--frame 200] [--viewport rendered|material|solid] [--save]

Builds the scene (phone, lights, camera, world), keyframes the full 900-frame film from timeline.py, and registers a frame-change handler
so the phone's screen image follows the timeline while you scrub. Then: scrub the timeline, orbit, move lights, change CAM_Main, and re-render a still (F12).
Timing / camera / light curves live in scripts/timeline.py; the model in scripts/phone.py (edit, re-run this script).
Screen content: Lacrydia_Ad/assets/lacrydia/screens (see scripts/setup_local_assets.py) -> plate in assets/lacrydia/screen_plate.
Tested with Blender 5.2.x (the bpy 5.2.2 used for production); other versions may differ.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from paths import p, assert_writable
import timeline as T
from build_scene import build_scene
from animate_scenes import animate
import screen_driver

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--finish", default=None)
ap.add_argument("--profile", default="preview")
ap.add_argument("--frame", type=int, default=200)
ap.add_argument("--viewport", default="rendered", choices=["rendered", "material", "solid"])
ap.add_argument("--device", default="CPU", help="CPU, or GPU (Metal on Apple Silicon: Preferences > System > Cycles Render Devices)")
ap.add_argument("--save", action="store_true", help="also save Lacrydia_Ad/project/lacrydia_master.blend")
a = ap.parse_args(argv)

sc = build_scene(a.profile, a.finish, device=a.device)
animate()                                           # one key per frame for everything that moves


def _screen_follow(scene, *_):
    screen_driver.set_screen_image(T.frame_to_t(scene.frame_current))


for h in list(bpy.app.handlers.frame_change_pre):
    if getattr(h, "__name__", "") == "_screen_follow":
        bpy.app.handlers.frame_change_pre.remove(h)
bpy.app.handlers.frame_change_pre.append(_screen_follow)
sc.frame_set(a.frame)
_screen_follow(sc)

if bpy.context.window:                              # GUI only: camera view + shading
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces[0]
            sp.shading.type = {"rendered": "RENDERED", "material": "MATERIAL", "solid": "SOLID"}[a.viewport]
            sp.region_3d.view_perspective = "CAMERA"
if a.save:
    path = assert_writable(p("project", "lacrydia_master.blend"))
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("saved", path)
print(f"Ready: scene {sc.name}, frames {sc.frame_start}-{sc.frame_end} @ {sc.render.fps} fps, current frame {sc.frame_current} (t={T.frame_to_t(sc.frame_current):.2f}s)")

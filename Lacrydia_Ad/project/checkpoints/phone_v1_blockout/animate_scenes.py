"""Keyframes the whole film from timeline.py: phone, camera (incl. DOF focus), lights, screen wake. One key per frame, linear
interpolation between keys, so motion blur and renders are exactly the curves in timeline.py (no hidden Bezier handles)."""
import math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T
from build_scene import LIGHTS, SOFTBOXES

SCREEN_BRIGHTNESS = 1.9     # linear emission peak for white UI pixels, calibrated by test renders


def cam_pos(t):
    az, el, d = math.radians(T.cam_az(t)), math.radians(T.cam_el(t)), T.cam_dist(t)
    pz = T.phone_z(t) + T.phone_bob(t)
    tgt = Vector((T.tgt_x(t), 0.0, pz + T.tgt_z(t)))
    pos = tgt + Vector((d * math.sin(az) * math.cos(el), -d * math.cos(az) * math.cos(el), d * math.sin(el)))
    return pos, tgt


def animate(frames=None):
    sc = bpy.context.scene
    root = bpy.data.objects["PHONE_Root"]
    cam, tgt = bpy.data.objects["CAM_Main"], bpy.data.objects["CAM_Target"]
    gain_node = bpy.data.materials["PHONE_Screen_MAT"].node_tree.nodes["SCREEN_GAIN"]
    frames = frames or range(sc.frame_start, sc.frame_end + 1)
    for f in frames:
        t = T.frame_to_t(f)
        pz = T.phone_z(t) + T.phone_bob(t)
        root.location = (0.0, 0.0, pz)
        root.rotation_euler = (0.0, 0.0, math.radians(T.phone_rotz(t)))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)

        pos, tg = cam_pos(t)
        cam.location, tgt.location = pos, tg
        cam.keyframe_insert("location", frame=f)
        tgt.keyframe_insert("location", frame=f)
        cd = cam.data
        cd.lens, cd.shift_x = T.cam_focal(t), T.cam_shift_x(t)
        cd.dof.aperture_fstop = T.cam_fstop(t)
        cd.dof.focus_distance = (pos - tg).length
        cd.keyframe_insert("lens", frame=f)
        cd.keyframe_insert("shift_x", frame=f)
        cd.dof.keyframe_insert("aperture_fstop", frame=f)
        cd.dof.keyframe_insert("focus_distance", frame=f)

        for name, base in LIGHTS.items():
            lo = bpy.data.objects[name]
            lo.data.energy = base["power"] * T.light_gain[name](t)
            lo.data.keyframe_insert("energy", frame=f)
            if name == "LGT_Sweep":
                lo.location = (T.sweep_x(t), base["loc"][1], base["loc"][2])
                lo.keyframe_insert("location", frame=f)

        for name in SOFTBOXES:
            g = bpy.data.objects[name].data.materials[0].node_tree.nodes["SOFTBOX_GAIN"].outputs[0]
            g.default_value = T.light_gain[name](t)
            g.keyframe_insert("default_value", frame=f)

        gain_node.inputs[1].default_value = T.screen_gain(t) * SCREEN_BRIGHTNESS
        gain_node.inputs[1].keyframe_insert("default_value", frame=f)

"""Scene, studio rig and camera (bpy)."""
import math
import numpy as np
import bpy
from mathutils import Vector, Matrix
from .anim import K


def fresh_scene(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.unit_settings.system = "METRIC"
    return sc


def set_world(sc, color=(0.00018, 0.00026, 0.00060), strength=1.0):
    w = bpy.data.worlds.new("Studio")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    sc.world = w
    return w


def look_rot(pos, target, roll=0.0):
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat("-Z", "Y")
    m = q.to_matrix().to_4x4()
    if roll:
        m = m @ Matrix.Rotation(roll, 4, "Z")
    return m.to_euler()


def area_light(name, size, energy, color=(1, 1, 1), pos=(0, 0, 1), target=(0, 0, 0), shape="RECTANGLE", spread=None,
               camera_visible=False, collection=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size = size[0]
    if shape == "RECTANGLE":
        ld.size_y = size[1]
    ld.energy = energy
    ld.color = color
    if spread is not None:
        ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld)
    ob.location = pos
    ob.rotation_euler = look_rot(pos, target)
    ob.visible_camera = camera_visible
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def aim(ob, pos, target, roll=0.0):
    ob.location = pos
    ob.rotation_euler = look_rot(pos, target, roll)


def make_camera(sc, name="Camera", sensor=36.0):
    cd = bpy.data.cameras.new(name)
    cd.sensor_width = sensor
    cd.sensor_fit = "HORIZONTAL"
    cd.dof.use_dof = True
    cd.clip_start = 0.002
    cd.clip_end = 80
    ob = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(ob)
    sc.camera = ob
    return ob


def set_camera(cam, pos, target, focal, fstop, focus=None, roll=0.0):
    """Look-at camera. focus: distance in m (default = distance to target)."""
    cam.location = pos
    cam.rotation_euler = look_rot(pos, target, roll)
    cd = cam.data
    cd.lens = focal
    cd.dof.aperture_fstop = fstop
    cd.dof.focus_distance = focus if focus is not None else (Vector(target) - Vector(pos)).length
    if K.baking:                                   # lens / aperture / focus must be animated too, or every frame gets the last one
        cd.keyframe_insert("lens", frame=K.frame)
        cd.dof.keyframe_insert("aperture_fstop", frame=K.frame)
        cd.dof.keyframe_insert("focus_distance", frame=K.frame)


def configure_render(sc, w, h, samples=64, denoise=True, adaptive=0.015, motion_blur=True, shutter=0.5, view="AgX",
                     look="None", exposure=1.0):
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.image_settings.file_format = "OPEN_EXR"
    r.image_settings.color_depth = "16"
    r.image_settings.exr_codec = "ZIP"
    r.image_settings.color_mode = "RGB"
    c = sc.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_adaptive_sampling = adaptive > 0
    c.adaptive_threshold = adaptive
    c.adaptive_min_samples = 8
    c.use_denoising = denoise
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    c.denoising_prefilter = "ACCURATE"
    c.max_bounces = 10
    c.diffuse_bounces = 3
    c.glossy_bounces = 6
    c.transmission_bounces = 8
    c.transparent_max_bounces = 8
    c.volume_bounces = 0
    c.sample_clamp_indirect = 4.0
    c.sample_clamp_direct = 0.0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.film_exposure = exposure
    c.pixel_filter_type = "BLACKMAN_HARRIS"
    c.filter_width = 1.4
    r.use_persistent_data = True
    r.use_motion_blur = motion_blur
    r.motion_blur_shutter = shutter
    r.film_transparent = False
    vs = sc.view_settings
    vs.view_transform = view
    vs.look = look
    vs.exposure = 0.0
    vs.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    sc.render.threads_mode = "AUTO"


def link_receivers(lights, objects, name="LinkRecv"):
    """Light linking: these lights illuminate only `objects` (they still show up in mirror reflections)."""
    col = bpy.data.collections.new(name)
    for o in objects:
        col.objects.link(o)
    for l in lights:
        l.light_linking.receiver_collection = col
    return col


def emitters(sc=None):
    """every light and every emissive helper mesh flagged ob['emitter']"""
    sc = sc or bpy.context.scene
    return [o for o in sc.objects if o.type == "LIGHT" or o.get("emitter")]

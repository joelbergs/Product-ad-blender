"""Builds the Lacrydia product-film scene (collections, phone, lights, camera, world, render settings).

Usage:  python3 build_scene.py [--profile review] [--finish silver] [--save]
Import: from build_scene import build_scene
Everything is named (PHONE_*, CAM_*, LGT_*) so animate_scenes.py / render_scenes.py can find it again.
"""
import argparse, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import addon_utils
import bpy
from mathutils import Vector
from paths import cfg, p, assert_writable
import phone as phone_mod

# area-light power (W) for each rig light, calibrated by test renders (see documentation/render_settings.md)
LIGHTS = {
    "LGT_Edge":     dict(loc=(14, -35, 0),   size=(3, 32),  power=14000, color=(1.00, 1.00, 1.00)),
    "LGT_StripL":   dict(loc=(-40, 8, 2),    size=(5, 48),  power=16000, color=(0.94, 0.96, 1.00)),
    "LGT_StripR":   dict(loc=(40, 8, 2),     size=(5, 48),  power=16000, color=(0.94, 0.96, 1.00)),
    "LGT_BackRimL": dict(loc=(-30, 42, 0),   size=(4, 44),  power=20000, color=(0.90, 0.94, 1.00)),
    "LGT_BackRimR": dict(loc=(30, 42, 0),    size=(4, 44),  power=20000, color=(0.90, 0.94, 1.00)),
    "LGT_Sweep":    dict(loc=(0, -30, 4),    size=(5, 50),  power=30000, color=(1.00, 1.00, 1.00)),
    "LGT_Amber":    dict(loc=(38, 26, -6),   size=(4, 40),  power=14000, color=(1.00, 0.63, 0.20)),   # brand amber #FFA62B, used once
}


# gradient softboxes (emissive meshes): radiance strength, colour, bright edge at +Y(local) fading to `low`
SOFTBOXES = {
    "LGT_Top":  dict(loc=(-8, -18, 46),  size=(70, 40), strength=3.2, color=(1.0, 1.0, 1.0),    low=0.08),
    "LGT_Key":  dict(loc=(-38, -40, 30), size=(40, 40), strength=2.2, color=(1.0, 0.99, 0.97),  low=0.10),
    "LGT_Fill": dict(loc=(0, -60, 10),   size=(60, 40), strength=0.5, color=(0.92, 0.95, 1.0),  low=0.30),
}


def make_softbox(name, d, col):
    import bmesh
    bm = bmesh.new()
    sx, sy = d["size"][0] / 2, d["size"][1] / 2
    vs = [bm.verts.new(v) for v in ((-sx, -sy, 0), (sx, -sy, 0), (sx, sy, 0), (-sx, sy, 0))]
    f = bm.faces.new(vs[::-1])                       # normal along -Z so the emitting side faces the target
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new(name + "_MAT")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = -sy, sy
    ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = d["low"], 1.0
    gain = nt.nodes.new("ShaderNodeValue")
    gain.name = "SOFTBOX_GAIN"
    gain.outputs[0].default_value = 0.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = d["strength"]
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Value"])
    nt.links.new(ramp.outputs["Result"], mul.inputs[0])
    nt.links.new(gain.outputs[0], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], em.inputs["Strength"])
    em.inputs["Color"].default_value = (*d["color"], 1.0)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(m)
    ob.location = d["loc"]
    ob.visible_camera = False
    ob.visible_shadow = False
    c2 = ob.constraints.new("TRACK_TO")
    c2.target, c2.track_axis, c2.up_axis = bpy.data.objects["LGT_Target"], "TRACK_NEGATIVE_Z", "UP_Y"
    col.objects.link(ob)
    return ob


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def apply_profile(sc, profile):
    C = cfg()
    pr = C["profiles"][profile]
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = pr["width"], pr["height"], 100
    r.fps, r.fps_base = C["fps"], 1.0
    sc.frame_start, sc.frame_end = 1, int(round(C["fps"] * C["duration_s"]))
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = pr["samples"]
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.adaptive_min_samples = 16
    cy.use_denoising = pr["denoise"]
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 6
    cy.transmission_bounces, cy.volume_bounces, cy.transparent_max_bounces = 4, 0, 4
    cy.caustics_reflective = cy.caustics_refractive = False
    cy.sample_clamp_indirect = 6.0
    cy.sample_clamp_direct = 0.0
    cy.filter_width = 1.4
    cy.use_light_tree = True
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.45
    r.motion_blur_position = "CENTER"
    r.use_persistent_data = True
    # colour pipeline: scene-linear -> sRGB (Rec.709 primaries) SDR, tone-mapped for highlight roll-off
    sc.display_settings.display_device = "sRGB"
    sc.view_settings.view_transform = "Khronos PBR Neutral"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.sequencer_colorspace_settings.name = "sRGB"
    im = r.image_settings
    im.file_format, im.color_mode, im.color_depth, im.compression = "PNG", "RGB", "16", 15
    r.film_transparent = False


def build_world(sc):
    w = bpy.data.worlds.new("LACRYDIA_World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-0.5, -0.5, 0)
    mp.inputs["Scale"].default_value = (1.7, 1.7, 1.0)
    gr = nt.nodes.new("ShaderNodeTexGradient")
    gr.gradient_type = "SPHERICAL"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    # a quiet studio: near-black at the edges, a faint cool lift behind the product (ink #0A0A0B family)
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.0, 0.0, 0.0, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 1.0, (0.0060, 0.0072, 0.0105, 1)
    ramp.color_ramp.interpolation = "EASE"
    nt.links.new(tc.outputs["Window"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], gr.inputs["Vector"])
    nt.links.new(gr.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def build_scene(profile="review", finish=None, fresh=True):
    addon_utils.enable("cycles", default_set=True)
    if fresh:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    C = cfg()
    sc = bpy.context.scene
    sc.name = "LACRYDIA_AD"
    apply_profile(sc, profile)
    build_world(sc)

    col_prod = collection("PRODUCT")
    col_cam = collection("CAMERAS")
    col_lgt = collection("LIGHTS")

    root, screen, geo = phone_mod.build_phone(col_prod, finish or C["phone"]["finish"], C["phone"]["size_cm"])

    # look-at target + camera
    tgt = bpy.data.objects.new("CAM_Target", None)
    tgt.empty_display_type, tgt.empty_display_size = "PLAIN_AXES", 1.0
    col_cam.objects.link(tgt)
    cam_d = bpy.data.cameras.new("CAM_Main")
    cam_d.sensor_fit, cam_d.sensor_width = "HORIZONTAL", 36.0
    cam_d.clip_start, cam_d.clip_end = 1.0, 2000.0
    cam_d.dof.use_dof = True
    cam_d.dof.focus_object = None
    cam = bpy.data.objects.new("CAM_Main", cam_d)
    col_cam.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam

    # light rig
    ltgt = bpy.data.objects.new("LGT_Target", None)
    col_lgt.objects.link(ltgt)
    for name, d in LIGHTS.items():
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape, ld.size, ld.size_y = "RECTANGLE", d["size"][0], d["size"][1]
        ld.energy, ld.color = d["power"], d["color"]
        ld.use_shadow = True
        ld.spread = math.radians(180)
        lo = bpy.data.objects.new(name, ld)
        lo.location = d["loc"]
        lo.visible_camera = False          # strips show up in reflections, never directly in frame
        c2 = lo.constraints.new("TRACK_TO")
        c2.target, c2.track_axis, c2.up_axis = ltgt, "TRACK_NEGATIVE_Z", "UP_Y"
        col_lgt.objects.link(lo)

    for name, d in SOFTBOXES.items():
        make_softbox(name, d, col_lgt)

    # scene markers = named shots
    for s in C["scenes"]:
        m = sc.timeline_markers.new(f'{s["id"]}_{s["name"]}', frame=int(round(s["t0"] * C["fps"])) + 1)
    return sc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="review")
    ap.add_argument("--finish", default=None)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    sc = build_scene(a.profile, a.finish)
    print("built:", sc.name, [o.name for o in bpy.data.objects][:8], "...", len(bpy.data.objects), "objects")
    if a.save:
        path = assert_writable(p("project", "lacrydia_master.blend"))
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print("saved", path)

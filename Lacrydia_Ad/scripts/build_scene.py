"""Builds the Lacrydia product-film scene (collections, phone, light rig, camera, world, render settings).

Usage:  python3 build_scene.py [--profile review] [--finish silver] [--save]
Import: from build_scene import build_scene
Everything is named (PHONE_*, CAM_*, LGT_*) so animate_scenes.py / render_scenes.py can find it again.

Lighting = emissive gradient softboxes with feathered edges (visible to reflection rays, invisible to the camera). Metals and glass
can only look real if they have something soft to reflect; hard uniform rectangles read as CG, hence gradient + feather.
"""
import argparse, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import addon_utils
from paths import cfg, p, assert_writable
import phone as phone_mod

# film rig: name -> loc, size (w, h), radiance strength, colour, `low` = brightness at the bottom edge (0..1), feather = soft edge fraction.
# Gains over time live in timeline.light_gain (0 = off), so the whole film is lit by animating these.
RIG = {
    "LGT_Edge":     dict(loc=(14, -35, 0),   size=(3, 34),  strength=26, color=(1.00, 1.00, 1.00), low=0.55, feather=0.45),
    "LGT_StripL":   dict(loc=(-40, 8, 2),    size=(7, 62),  strength=9,  color=(0.94, 0.96, 1.00), low=0.45, feather=0.35),
    "LGT_StripR":   dict(loc=(40, 8, 2),     size=(7, 62),  strength=9,  color=(0.94, 0.96, 1.00), low=0.45, feather=0.35),
    "LGT_Top":      dict(loc=(-8, -18, 46),  size=(80, 45), strength=3.0, color=(1.00, 1.00, 1.00), low=0.10, feather=0.30),
    "LGT_Key":      dict(loc=(-38, -40, 30), size=(45, 45), strength=2.2, color=(1.00, 0.99, 0.97), low=0.12, feather=0.30),
    "LGT_BackRimL": dict(loc=(-30, 42, 0),   size=(6, 52),  strength=13, color=(0.90, 0.94, 1.00), low=0.5,  feather=0.35),
    "LGT_BackRimR": dict(loc=(30, 42, 0),    size=(6, 52),  strength=13, color=(0.90, 0.94, 1.00), low=0.5,  feather=0.35),
    "LGT_Sweep":    dict(loc=(0, -30, 4),    size=(7, 62),  strength=17, color=(1.00, 1.00, 1.00), low=0.6,  feather=0.45),
    "LGT_Amber":    dict(loc=(38, 26, -6),   size=(6, 48),  strength=11, color=(1.00, 0.63, 0.20), low=0.5,  feather=0.35),  # brand amber #FFA62B, used once
    "LGT_Fill":     dict(loc=(0, -60, 10),   size=(70, 45), strength=0.5, color=(0.92, 0.95, 1.00), low=0.30, feather=0.30),
}

# neutral product-photography rig for model QC / colour evaluation (static, all on). Names follow the studio brief.
RIG_QC = {
    "KEY_SOFTBOX":         dict(loc=(-48, -62, 40),  size=(80, 55),   strength=2.0,  color=(1.00, 1.00, 1.00), low=0.25, feather=0.35),
    "TOP_STRIP":           dict(loc=(0, -18, 78),    size=(130, 34),  strength=3.2,  color=(1.00, 1.00, 1.00), low=0.30, feather=0.35),
    "LEFT_EDGE_LIGHT":     dict(loc=(-64, -14, 4),   size=(12, 130),  strength=13.0,  color=(1.00, 1.00, 1.00), low=0.40, feather=0.35),
    "RIGHT_EDGE_LIGHT":    dict(loc=(64, -14, 4),    size=(12, 130),  strength=13.0,  color=(1.00, 1.00, 1.00), low=0.40, feather=0.35),
    "CAMERA_GLASS_LIGHT":  dict(loc=(-24, -58, 20),  size=(24, 16),   strength=7.0,  color=(1.00, 1.00, 1.00), low=0.60, feather=0.40),
    "REAR_RIM_LIGHT_L":    dict(loc=(-52, 64, 4),    size=(12, 110),  strength=9.0,  color=(0.95, 0.97, 1.00), low=0.5,  feather=0.35),
    "REAR_RIM_LIGHT_R":    dict(loc=(52, 64, 4),     size=(12, 110),  strength=9.0,  color=(0.95, 0.97, 1.00), low=0.5,  feather=0.35),
    "LOW_FILL":            dict(loc=(0, -85, -34),   size=(110, 30),  strength=0.45, color=(1.00, 1.00, 1.00), low=0.30, feather=0.35),
    # background card behind the phone: the only light that is visible directly to the camera (a faint gradient, never a flat black void)
    "BACKGROUND_LIGHT":    dict(loc=(0, 140, 4),     size=(420, 280), strength=0.040, color=(0.92, 0.95, 1.00), low=0.35, feather=0.90, camera=True),
}
# dark flags (negative fill): black cards visible only in reflections, they keep contrast on the metal
FLAGS_QC = {
    "NEG_FILL_L": dict(loc=(-46, -40, 2), size=(16, 70)),
    "NEG_FILL_R": dict(loc=(46, -40, 2),  size=(16, 70)),
}


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def apply_profile(sc, profile, device="CPU"):
    C = cfg()
    pr = C["profiles"][profile]
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = pr["width"], pr["height"], 100
    r.fps, r.fps_base = C["fps"], 1.0
    sc.frame_start, sc.frame_end = 1, int(round(C["fps"] * C["duration_s"]))
    cy = sc.cycles
    cy.device = device                       # "CPU" here; "GPU" with the Metal backend on Apple Silicon (see probe_devices.py)
    if device == "GPU":                      # enable every available GPU backend device (Metal on a Mac, OptiX/CUDA/HIP elsewhere)
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                devs = [d for d in prefs.devices if d.type == kind]
                if devs:
                    for d in prefs.devices:
                        d.use = d.type in (kind, "CPU") if kind == "METAL" else d.type == kind
                    print("Cycles GPU backend:", kind, [d.name for d in devs])
                    break
            except Exception:
                continue
        else:
            print("WARNING: no GPU backend found, Cycles falls back to CPU")
    cy.samples = pr["samples"]
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.015
    cy.adaptive_min_samples = 16
    cy.use_denoising = pr["denoise"]
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 10, 3, 8
    cy.transmission_bounces, cy.volume_bounces, cy.transparent_max_bounces = 8, 0, 8
    cy.caustics_reflective = cy.caustics_refractive = False
    cy.sample_clamp_indirect = 8.0
    cy.sample_clamp_direct = 0.0
    cy.filter_width = 1.3
    cy.use_light_tree = True
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.45
    r.motion_blur_position = "CENTER"
    r.use_persistent_data = True
    # colour pipeline: scene-linear -> sRGB (Rec.709 primaries) SDR with highlight roll-off that keeps hues
    sc.display_settings.display_device = "sRGB"
    sc.view_settings.view_transform = "Standard"   # PBR Neutral crushes dark saturated colours (measured: G 4/255), so Standard (sRGB / Rec.709) it is
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    im = r.image_settings
    im.file_format, im.color_mode, im.color_depth, im.compression = "PNG", "RGB", "16", 15
    r.film_transparent = False


def build_world(sc, studio="film"):
    w = bpy.data.worlds.new("LACRYDIA_World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    if studio == "qc":
        bg.inputs["Color"].default_value = (0.010, 0.010, 0.011, 1)
        bg.inputs["Strength"].default_value = 1.0
    else:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (-0.5, -0.5, 0)
        mp.inputs["Scale"].default_value = (1.7, 1.7, 1.0)
        gr = nt.nodes.new("ShaderNodeTexGradient")
        gr.gradient_type = "SPHERICAL"
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.0, 0.0, 0.0, 1)
        ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 1.0, (0.0060, 0.0072, 0.0105, 1)
        ramp.color_ramp.interpolation = "EASE"
        nt.links.new(tc.outputs["Window"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], gr.inputs["Vector"])
        nt.links.new(gr.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_softbox(name, d, col, target):
    import bmesh
    bm = bmesh.new()
    sx, sy = d["size"][0] / 2, d["size"][1] / 2
    vs = [bm.verts.new(v) for v in ((-sx, -sy, 0), (sx, -sy, 0), (sx, sy, 0), (-sx, sy, 0))]
    bm.faces.new(vs[::-1])                           # normal along -Z so the emitting side faces the target
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
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])

    def edge(axis, half):                            # 1 inside, smoothly -> 0 at the border
        ab = nt.nodes.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        nt.links.new(sep.outputs[axis], ab.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = half * (1 - d["feather"]), half
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
        nt.links.new(ab.outputs[0], mr.inputs["Value"])
        return mr.outputs["Result"]
    ex, ey = edge("X", sx), edge("Y", sy)
    grad = nt.nodes.new("ShaderNodeMapRange")        # vertical gradient low..1
    grad.inputs["From Min"].default_value, grad.inputs["From Max"].default_value = -sy, sy
    grad.inputs["To Min"].default_value, grad.inputs["To Max"].default_value = d["low"], 1.0
    nt.links.new(sep.outputs["Y"], grad.inputs["Value"])
    gain = nt.nodes.new("ShaderNodeValue")
    gain.name = "SOFTBOX_GAIN"
    gain.outputs[0].default_value = 1.0
    chain = grad.outputs["Result"]
    for other in (ex, ey, gain.outputs[0]):
        mu = nt.nodes.new("ShaderNodeMath")
        mu.operation = "MULTIPLY"
        nt.links.new(chain, mu.inputs[0])
        nt.links.new(other, mu.inputs[1])
        chain = mu.outputs[0]
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY"
    st.inputs[1].default_value = d["strength"]
    nt.links.new(chain, st.inputs[0])
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    em.inputs["Color"].default_value = (*d["color"], 1.0)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(m)
    ob.location = d["loc"]
    ob.visible_camera = bool(d.get("camera", False))
    ob.visible_shadow = False
    c2 = ob.constraints.new("TRACK_TO")
    c2.target, c2.track_axis, c2.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    col.objects.link(ob)
    return ob


def make_flag(name, d, col, target):
    import bmesh
    bm = bmesh.new()
    sx, sy = d["size"][0] / 2, d["size"][1] / 2
    bm.faces.new([bm.verts.new(v) for v in ((-sx, -sy, 0), (sx, -sy, 0), (sx, sy, 0), (-sx, sy, 0))][::-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new(name + "_MAT")
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    pb.inputs["Base Color"].default_value = (0, 0, 0, 1)
    pb.inputs["Roughness"].default_value = 0.9
    pb.inputs["Specular IOR Level"].default_value = 0.0
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(m)
    ob.location = d["loc"]
    ob.visible_camera = False
    c2 = ob.constraints.new("TRACK_TO")
    c2.target, c2.track_axis, c2.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    col.objects.link(ob)
    return ob


def build_scene(profile="review", finish=None, fresh=True, studio="film", device="CPU"):
    addon_utils.enable("cycles", default_set=True)
    if fresh:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    C = cfg()
    sc = bpy.context.scene
    sc.name = "LACRYDIA_AD"
    apply_profile(sc, profile, device)
    build_world(sc, studio)

    col_prod, col_cam, col_lgt = collection("PRODUCT"), collection("CAMERAS"), collection("LIGHTS")
    root, screen, geo = phone_mod.build_phone(col_prod, finish or C["phone"]["finish"], C["phone"]["size_cm"])

    tgt = bpy.data.objects.new("CAM_Target", None)
    tgt.empty_display_type, tgt.empty_display_size = "PLAIN_AXES", 1.0
    col_cam.objects.link(tgt)
    cam_d = bpy.data.cameras.new("CAM_Main")
    cam_d.sensor_fit, cam_d.sensor_width = "HORIZONTAL", 36.0
    cam_d.clip_start, cam_d.clip_end = 1.0, 2000.0
    cam_d.dof.use_dof = True
    cam = bpy.data.objects.new("CAM_Main", cam_d)
    col_cam.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam

    ltgt = bpy.data.objects.new("LGT_Target", None)
    col_lgt.objects.link(ltgt)
    for name, d in (RIG_QC if studio == "qc" else RIG).items():
        make_softbox(name, d, col_lgt, ltgt)
    if studio == "qc":
        for name, d in FLAGS_QC.items():
            make_flag(name, d, col_lgt, ltgt)

    if studio == "film":
        for s in C["scenes"]:
            sc.timeline_markers.new(f'{s["id"]}_{s["name"]}', frame=int(round(s["t0"] * C["fps"])) + 1)
    return sc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="review")
    ap.add_argument("--finish", default=None)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    sc = build_scene(a.profile, a.finish)
    print("built:", sc.name, len(bpy.data.objects), "objects")
    if a.save:
        path = assert_writable(p("project", "lacrydia_master.blend"))
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print("saved", path)

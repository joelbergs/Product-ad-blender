"""Reusable sets: the obsidian studio and the hero glass photograph panel."""
import math
import bpy
from mathutils import Vector
from . import geo, mat, rig

PHOTOS = "/home/user/Product-ad-blender/Lacrydia_Film/assets/lacrydia/photos"

# hero panel (metres): a 3:4 glass photograph, 8 mm front pane, photo sunk behind it, black-glass back plate
W, H = 0.15, 0.20
FLOAT = 0.045            # clear space under the panel


def studio_floor(sc, size=14.0, name="Obsidian", **kw):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(mat.obsidian(**kw))
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


def hero_panel(sc, photo="p8.jpg", name="Hero", w=W, h=H, z0=FLOAT, mark_mask=None, emit=0.9):
    """Returns dict(root, glass, photo_obj, photo_mat, back)."""
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    g = mat.etched_glass(name + "_glass", mark_mask) if mark_mask else mat.glass(shadow_transparent=True)
    gm = mat.glass(name="GlassEdge", shadow_transparent=True)
    bg = mat.dark_glass()
    pm = mat.photo_print(name + "_print", f"{PHOTOS}/{photo}", rough=0.5, coat=0.0, emit=emit, exposure=0.55, diffuse=0.0, spec=0.0)
    front = geo.make_slab(name + "_front", w, h, 0.013, 0.012, 0.0045, (g, gm, g))
    front.location = (0, 0, 0.0070)
    back = geo.make_slab(name + "_back", w, h, 0.004, 0.012, 0.0015, (bg, bg, bg), seg_edge=4)
    back.location = (0, 0, -0.0035)
    inset = 0.004
    pr = geo.make_slab(name + "_photo", w - inset, h - inset, 0.0008, 0.010, 0.0002, (pm, bg, bg), seg_edge=2)
    pr.location = (0, 0, -0.0007)
    for ob in (front, back, pr):
        ob.parent = root
    root.rotation_euler = (math.radians(90), 0, 0)
    root.location = (0, 0, z0 + h / 2)
    return dict(root=root, glass=front, back=back, photo=pr, photo_mat=pm, glass_mat=g)


def shape_lights_not_photo(lights, floor, hero):
    """Softboxes/strips shape reflections on glass + floor; the print itself is self-lit like a backlit transparency."""
    from . import rig
    rig.link_receivers(rig.emitters(), [floor, hero["glass"], hero["back"]])


def reflection_card(sc, name, pos, target, size=(2.2, 1.3), peak=1.2, tint=(1, 0.99, 0.97), stops=((0.0, 0.0), (0.45, 0.0), (1.0, 1.0)), down_only=False, soft_y=0.0):
    """Large camera-invisible gradient flag: its reflection sweeps across the glass as the camera moves."""
    from . import geo
    ob = geo.make_plane(name, size[0], size[1], mat.gradient_card(name, peak, tint, stops=stops, down_only=down_only, soft_y=soft_y), sc.collection)
    rig.aim(ob, pos, target)
    ob.visible_camera = False
    ob["emitter"] = True
    return ob


def strip_light(sc, name, pos, target, size, strength, color=(0.88, 0.94, 1.0), end_fade=0.3, edge_soft=0.5, roll=0.0, no_upward=True):
    """Emissive strip card (camera-invisible): illuminates AND reflects as a soft streak."""
    from . import geo
    ob = geo.make_plane(name, size[0], size[1], mat.strip_emitter(name, color, strength, end_fade, edge_soft, no_upward), sc.collection)
    ob.rotation_euler = rig.look_rot(pos, target, roll)
    ob.location = pos
    ob.visible_camera = False
    ob["emitter"] = True
    ob["strength_node"] = ob.data.materials[0]["peak_node"]
    return ob


def set_strip(ob, strength):
    """animate a strip's brightness"""
    from .anim import K
    n = ob.data.materials[0].node_tree.nodes[ob["strength_node"]].inputs[1]
    K.sock(n, strength)


def sheen_flag(sc, name="SHEEN_flag", y=-1.0, z=0.05, width=3.4, height=0.30, peak=3.0, center=(0, 0, 0.145)):
    """Low, wide gradient flag between the subject and the camera (camera-invisible). The camera looks slightly down onto the
    panel, so its face mirrors this strip: a soft sheen that slides across the glass as the camera orbits."""
    return reflection_card(sc, name, (0.0, y, z), center, (width, height), peak, (1.0, 0.99, 0.97),
                           stops=((0.0, 0.0), (0.30, 0.04), (0.5, 1.0), (0.70, 0.04), (1.0, 0.0)), down_only=True, soft_y=0.5)


def hero_lights(sc, center=(0, 0, 0.145)):
    """Studio rig around the panel. Soft key + top + cool fill are area lights; the rim and sweep strips are gradient
    emitters (so their reflections are refined streaks). Returns dict by role."""
    c = Vector(center)
    L = {}
    L["key"] = rig.area_light("KEY_softbox", (0.9, 0.55), 1.6, (1.0, 0.985, 0.965), (-0.62, -0.55, 0.85), c)
    L["top"] = rig.area_light("TOP_strip", (0.05, 0.6), 4, (1.0, 1.0, 1.0), (0.0, -0.10, 0.75), c)
    L["fill"] = rig.area_light("FILL_cool", (0.7, 0.7), 1.2, (0.55, 0.70, 1.0), (0.75, -0.80, 0.30), c)
    L["rim_l"] = strip_light(sc, "RIM_strip_L", (-0.55, 0.55, 0.42), center, (0.040, 0.75), 520, (0.88, 0.94, 1.0))
    L["rim_r"] = strip_light(sc, "RIM_strip_R", (0.55, 0.50, 0.42), center, (0.040, 0.75), 400, (0.88, 0.94, 1.0))
    L["sweep"] = strip_light(sc, "SWEEP_strip", (-0.5, -0.30, 0.45), center, (0.035, 0.6), 400, (1.0, 0.99, 0.97))
    return L


def set_energy(L, key, value):
    """energy for either an area light or a strip emitter"""
    from .anim import K
    o = L[key]
    if o.type == "LIGHT":
        K.set(o.data, "energy", value)
    else:
        set_strip(o, value)


def link_all(L, receivers):
    """light-link every emitter in the scene (lights, strip emitters, reflection cards) to `receivers` only"""
    from . import rig as _r
    _r.link_receivers(_r.emitters(), receivers)


def dist_for(height_m, lens_mm, fill=0.6):
    """camera distance so that an object of `height_m` fills `fill` of the frame height (36 mm sensor width, 16:9)."""
    return (height_m / fill) * lens_mm / 20.25


def reveal_node(panel):
    pm = panel["photo_mat"]
    return pm.node_tree.nodes[pm["reveal_node"]].outputs[0]


# --- the app device: a bezel-less glass slab carrying the REAL app screens ------------------------------------------
DW, DH = 0.0785, 0.1706          # 1206 x 2622 px aspect


def device_panel(sc, screens, name="Device", z0=0.045):
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    g = mat.glass(name="DevGlass", shadow_transparent=True)
    ge = mat.glass(name="DevGlassEdge", shadow_transparent=True)
    bg = mat.dark_glass("DevBack", 0.05)
    front = geo.make_slab(name + "_front", DW, DH, 0.0065, 0.0125, 0.0026, (g, ge, g))
    front.location = (0, 0, 0.0036)
    back = geo.make_slab(name + "_back", DW, DH, 0.0035, 0.0125, 0.0014, (bg, bg, bg), seg_edge=4)
    back.location = (0, 0, -0.0028)
    scr = []
    clr = mat.clear("ScreenClear")
    for i, path in enumerate(screens):
        m = mat.screen(name + f"_screen{i}", path, 1.0)
        o = geo.make_slab(name + f"_screen{i}", DW - 0.0032, DH - 0.0032, 0.0002, 0.0105, 0.00005, (m, clr, clr), seg_corner=12, seg_edge=1)
        o.location = (0, 0, -0.0004 - 0.0007 * i)
        scr.append((o, m.node_tree.nodes[m["vis_node"]].outputs[0]))
    for ob in [front, back] + [o for o, _ in scr]:
        ob.parent = root
    root.rotation_euler = (math.radians(90), 0, 0)
    root.location = (0, 0, z0 + DH / 2)
    return dict(root=root, front=front, back=back, screens=scr)


# the engraved brand mark lives in the panel's lower-left corner (UV 0..1 across the face)
MARK_UV = (0.17, 0.115)
MARK_H_UV = 0.085


def mark_mask_path():
    import os
    from . import logo
    p = "/home/user/Product-ad-blender/Lacrydia_Film/assets/generated/panel_mark_mask.png"
    if not os.path.exists(p):
        logo.draw_mask(p, 2048, MARK_UV, MARK_H_UV, W / H)
    return p

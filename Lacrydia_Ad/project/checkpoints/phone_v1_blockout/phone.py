"""Procedural phone model (bpy). 1 unit = 1 cm.

Local axes: +X = viewer's right when looking at the FRONT, +Z = up, front glass faces -Y, back faces +Y.
Dimensions approximate a current-generation Pro phone (approx. 150 x 71.9 x 8.75 mm); this is NOT an
exact manufacturer model (see documentation/production_plan.md). Only what the camera can see is modelled.

Everything lives under one empty, "PHONE_ROOT"; the screen is a separate object ("PHONE_Screen") whose
image texture is swapped per frame, so the screen content is exchangeable without touching the model.
"""
import math
import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------------------------- finishes
FINISHES = {
    # frame (metal) colour, back glass colour, back roughness, plateau roughness, metal roughness
    "silver":        dict(metal=(0.80, 0.80, 0.82), back=(0.74, 0.74, 0.76), back_r=0.42, plateau_r=0.16, metal_r=0.30),
    "deep_blue":     dict(metal=(0.16, 0.20, 0.30), back=(0.10, 0.13, 0.21), back_r=0.40, plateau_r=0.14, metal_r=0.32),
    "cosmic_orange": dict(metal=(0.80, 0.36, 0.16), back=(0.72, 0.30, 0.12), back_r=0.42, plateau_r=0.16, metal_r=0.32),
}


# ---------------------------------------------------------------------------------------------- helpers
def rrect(w, h, r, seg=14):
    """Rounded-rectangle outline in the XZ plane (counter-clockwise), returns [(x, z)]."""
    pts = []
    cx, cz = w / 2 - r, h / 2 - r
    for (ccx, ccz, a0) in ((cx, cz, 0), (-cx, cz, 90), (-cx, -cz, 180), (cx, -cz, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    return pts


def _mesh_obj(name, bm, mat=None, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.collection).objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def prism(name, pts, y0, y1, mat, collection, offset=(0, 0), bevel=0.0, bevel_seg=3):
    """Extrude an XZ outline along Y from y0 to y1."""
    bm = bmesh.new()
    ox, oz = offset
    v0 = [bm.verts.new((x + ox, y0, z + oz)) for x, z in pts]
    face = bm.faces.new(v0)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, y1 - y0, 0), verts=verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _mesh_obj(name, bm, mat, collection)
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel
        m.segments = bevel_seg
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(35)
        m.harden_normals = True
        wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
    return ob


def disc(name, radius, y0, y1, mat, collection, center=(0, 0), seg=64, bevel=0.0):
    """Cylinder along +Y between y0 and y1, centred at (x, z)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=radius, radius2=radius, depth=abs(y1 - y0))
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(-90), 4, "X"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(center[0], (y0 + y1) / 2, center[1]), verts=bm.verts)
    ob = _mesh_obj(name, bm, mat, collection)
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel
        m.segments = 3
        m.limit_method = "ANGLE"
        wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
    return ob


# ---------------------------------------------------------------------------------------------- materials
def _principled(nt):
    return next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def _set(node, **kw):
    for k, v in kw.items():
        if k in node.inputs:
            node.inputs[k].default_value = v


def mat_metal(name, color, rough, brushed=0.035):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (*color, 1), "Metallic": 1.0, "Roughness": rough})
    if brushed:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 600
        tex.inputs["Detail"].default_value = 6
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.0, 0.04, 1.0)   # streaks along Y (around the frame)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = brushed
        bump.inputs["Distance"].default_value = 0.01
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_lens_window(name="PHONE_LensWindow_MAT"):
    """Transmissive lens cover glass with a faint thin-film (anti-reflective coating) tint, so the lens tiers behind it show."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _principled(m.node_tree)
    _set(b, **{"Base Color": (1, 1, 1, 1), "Roughness": 0.012, "Metallic": 0.0, "IOR": 1.52, "Transmission Weight": 1.0,
               "Coat Weight": 0.0, "Specular IOR Level": 0.5, "Thin Film Thickness": 320.0, "Thin Film IOR": 1.7})
    return m


def mat_glass(name, color, rough, coat=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _principled(m.node_tree)
    _set(b, **{"Base Color": (*color, 1), "Roughness": rough, "Metallic": 0.0,
               "Coat Weight": coat, "Coat Roughness": 0.02, "Specular IOR Level": spec, "IOR": 1.5})
    return m


def mat_screen(name="PHONE_Screen_MAT"):
    """Display: black glass + emission from an exchangeable image. Nodes are looked up by name from scripts."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (0.0, 0.0, 0.0, 1), "Roughness": 0.06, "Coat Weight": 0.25, "Coat Roughness": 0.03,
               "Specular IOR Level": 0.6, "Emission Strength": 1.0})
    img = nt.nodes.new("ShaderNodeTexImage")
    img.name = "SCREEN_IMAGE"
    img.interpolation = "Cubic"
    img.extension = "EXTEND"
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    nt.links.new(uv.outputs["UV"], img.inputs["Vector"])
    gain = nt.nodes.new("ShaderNodeMath")
    gain.name = "SCREEN_GAIN"          # animated: wake-up factor (0..1) * brightness
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = 0.0
    mix = nt.nodes.new("ShaderNodeVectorMath")
    mix.operation = "SCALE"
    nt.links.new(img.outputs["Color"], mix.inputs[0])
    nt.links.new(gain.outputs["Value"], mix.inputs["Scale"])
    gain.inputs[0].default_value = 1.0
    nt.links.new(mix.outputs["Vector"], b.inputs["Emission Color"])
    return m


# ---------------------------------------------------------------------------------------------- the phone
def build_phone(collection, finish="silver", size=None):
    size = size or dict(w=7.19, h=15.0, t=0.875)
    W, H, T = size["w"], size["h"], size["t"]
    F = FINISHES[finish]
    R = 1.08                      # outer corner radius
    inset = 0.20                  # glass inset from the outline (matches the frame bevel)

    root = bpy.data.objects.new("PHONE_Root", None)
    collection.objects.link(root)

    metal = mat_metal("PHONE_Frame_MAT", F["metal"], F["metal_r"])
    metal_polished = mat_metal("PHONE_LensRing_MAT", tuple(min(1, c * 1.05) for c in F["metal"]), 0.16, brushed=0.0)
    back = mat_glass("PHONE_BackGlass_MAT", F["back"], F["back_r"] * 0.35, coat=0.5, spec=0.6)
    plateau = mat_metal("PHONE_Plateau_MAT", F["metal"], F["metal_r"] * 0.8)
    black_glass = mat_glass("PHONE_FrontGlass_MAT", (0.004, 0.004, 0.005), 0.04, coat=0.5, spec=0.7)
    lens_glass = mat_glass("PHONE_LensGlass_MAT", (0.003, 0.004, 0.008), 0.02, coat=1.0, spec=0.9)
    lens_inner = mat_metal("PHONE_LensInner_MAT", (0.05, 0.05, 0.06), 0.25, brushed=0.0)
    lens_core = mat_glass("PHONE_LensCore_MAT", (0.004, 0.006, 0.02), 0.03, coat=1.0, spec=1.0)
    dark = mat_glass("PHONE_DarkDetail_MAT", (0.002, 0.002, 0.003), 0.35)

    parts = []
    outline = rrect(W, H, R)
    parts.append(prism("PHONE_Frame", outline, -T / 2, T / 2, metal, collection, bevel=0.2, bevel_seg=7))

    g_out = rrect(W - 2 * inset, H - 2 * inset, R - inset)
    parts.append(prism("PHONE_FrontGlass", g_out, -T / 2 - 0.012, -T / 2 + 0.02, black_glass, collection, bevel=0.006, bevel_seg=2))

    # --- back: aluminium unibody (the frame prism) + a glass panel on the lower back + a full-width camera plateau
    ph = 4.25
    pz = (H / 2 - inset) - ph / 2
    z_top = pz - ph / 2 - 0.30
    z_bot = -H / 2 + 0.50
    panel = rrect(W - 0.95, z_top - z_bot, 0.80)
    parts.append(prism("PHONE_BackGlassPanel", panel, T / 2 - 0.012, T / 2 + 0.007, back, collection,
                       offset=(0, (z_top + z_bot) / 2), bevel=0.012, bevel_seg=3))
    p_out = rrect(W - 2 * inset, ph, R - inset)
    pl_top = T / 2 + 0.012 + 0.26
    parts.append(prism("PHONE_Plateau", p_out, T / 2 - 0.01, pl_top, plateau, collection, offset=(0, pz), bevel=0.075, bevel_seg=6))

    # lenses: polished ring, satin step, transmissive window, tiered lens elements behind the glass
    lens_pos = [(1.95, pz + 0.83), (1.95, pz - 0.77), (0.42, pz + 0.03)]
    window = mat_lens_window()
    tier_mats = [mat_metal("PHONE_LensTier1_MAT", (0.03, 0.03, 0.035), 0.20, brushed=0.0),
                 mat_metal("PHONE_LensTier2_MAT", (0.16, 0.16, 0.18), 0.12, brushed=0.0),
                 mat_metal("PHONE_LensTier3_MAT", (0.015, 0.015, 0.02), 0.18, brushed=0.0),
                 mat_glass("PHONE_LensCore_MAT", (0.006, 0.010, 0.040), 0.02, coat=1.0, spec=1.0)]
    for i, (lx, lz) in enumerate(lens_pos, 1):
        base = pl_top + 0.02
        parts.append(disc(f"PHONE_Lens{i}_Ring", 0.745, pl_top - 0.02, pl_top + 0.17, metal_polished, collection, (lx, lz), bevel=0.035))
        parts.append(disc(f"PHONE_Lens{i}_Step", 0.625, pl_top + 0.10, pl_top + 0.178, lens_inner, collection, (lx, lz), bevel=0.012))
        parts.append(disc(f"PHONE_Lens{i}_Window", 0.555, base, pl_top + 0.145, window, collection, (lx, lz), seg=96))
        for k, (rad, h) in enumerate(((0.50, 0.020), (0.40, 0.040), (0.30, 0.060), (0.20, 0.072))):
            parts.append(disc(f"PHONE_Lens{i}_Tier{k+1}", rad, base + 0.002, base + h, tier_mats[k], collection, (lx, lz), seg=64))
    parts.append(disc("PHONE_Flash", 0.29, pl_top - 0.01, pl_top + 0.02, mat_glass("PHONE_Flash_MAT", (0.88, 0.85, 0.74), 0.35), collection, (-1.95, pz + 0.83)))
    parts.append(disc("PHONE_FlashRing", 0.34, pl_top - 0.012, pl_top + 0.012, metal_polished, collection, (-1.95, pz + 0.83), bevel=0.01))
    parts.append(disc("PHONE_Lidar", 0.37, pl_top - 0.01, pl_top + 0.024, dark, collection, (-1.95, pz - 0.77)))
    parts.append(disc("PHONE_LidarRing", 0.42, pl_top - 0.012, pl_top + 0.012, metal_polished, collection, (-1.95, pz - 0.77), bevel=0.01))
    parts.append(disc("PHONE_Mic", 0.07, pl_top - 0.01, pl_top + 0.022, dark, collection, (-0.95, pz + 1.55)))

    # hardware buttons (left = action + volume, right = side button + camera control)
    def button(name, x_side, z0, z1, thick=0.46, out=0.05):
        sgn = 1 if x_side > 0 else -1
        x0, x1 = sgn * (W / 2 - 0.10), sgn * (W / 2 + out)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        sx, sy, sz = abs(x1 - x0), thick, abs(z1 - z0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bmesh.ops.translate(bm, vec=((x0 + x1) / 2, 0, (z0 + z1) / 2), verts=bm.verts)
        ob = _mesh_obj(name, bm, metal, collection)
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = 0.04
        m.segments = 3
        ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL").keep_sharp = True
        return ob
    parts.append(button("PHONE_ActionButton", -1, 5.55, 6.15))
    parts.append(button("PHONE_VolUp", -1, 3.55, 4.75))
    parts.append(button("PHONE_VolDown", -1, 2.00, 3.20))
    parts.append(button("PHONE_SideButton", +1, 3.20, 5.30, out=0.04))
    parts.append(button("PHONE_CameraControl", +1, -2.90, -1.70, out=0.0))

    # bottom face: USB-C slot + speaker/mic holes (flat dark discs just proud of the frame face)
    def bottom_capsule(name, cx, wd, ht, depth=0.002):
        pts = []
        for k in range(24):
            a = 2 * math.pi * k / 24
            pts.append((cx + wd / 2 * math.cos(a), ht / 2 * math.sin(a)))
        bm = bmesh.new()
        vs = [bm.verts.new((x, y, -H / 2 - depth)) for x, y in pts]
        bm.faces.new(vs)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return _mesh_obj(name, bm, dark, collection)
    parts.append(bottom_capsule("PHONE_USBC", 0.0, 0.85, 0.25))
    for k in range(5):
        parts.append(bottom_capsule(f"PHONE_SpkL{k}", -1.45 - 0.17 * k, 0.07, 0.07))
        parts.append(bottom_capsule(f"PHONE_SpkR{k}", +1.45 + 0.17 * k, 0.07, 0.07))

    # the display, a separate object with UVs
    d_out = rrect(W - 0.60, H - 0.60, R - 0.30, seg=16)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    dw, dh = W - 0.60, H - 0.60
    vs = [bm.verts.new((x, -T / 2 - 0.0125 - 0.0015, z)) for x, z in d_out]
    f = bm.faces.new(vs[::-1])          # normal towards -Y
    for lp in f.loops:
        co = lp.vert.co
        lp[uv_layer].uv = ((co.x + dw / 2) / dw, (co.z + dh / 2) / dh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    screen = _mesh_obj("PHONE_Screen", bm, mat_screen(), collection)
    # smooth quad fan so that UVs interpolate on the n-gon: triangulate
    tri = screen.modifiers.new("Triangulate", "TRIANGULATE")
    parts.append(screen)

    for ob in parts:
        ob.parent = root
    return root, screen, dict(W=W, H=H, T=T, plateau_z=pz, lens=lens_pos)

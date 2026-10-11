"""Procedural phone model (bpy), v2. 1 unit = 1 cm.

Local axes: +X = viewer's right when looking at the FRONT, +Z = up, front glass faces -Y, back faces +Y.

REFERENCE / HONESTY NOTE
  Modelled on the publicly documented iPhone 17 Pro layout (150.0 x 71.9 x 8.75 mm; aluminium unibody, full-width
  camera plateau, glass panel on the lower back, three rear lenses in a triangle at the left, flash / LiDAR / mic at the
  right, action button + two volume buttons on the left, side button + camera control on the right, USB-C + speaker holes
  at the bottom). The project's own simulator is called "iPhone 18 Pro", whose exact industrial design this model does NOT
  claim to reproduce: see documentation/phone_model.md for what is verified, what is assumed and what needs reference photos.
  No manufacturer logo or regulatory text is modelled (trademark; not visible at film distance).

The screen is a separate object ("PHONE_Screen") whose image texture is swapped per frame, so the screen content is
exchangeable without touching the model. Everything lives under one empty, "PHONE_Root".
"""
import math
import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------------------------- finishes
# metal = aluminium albedo, back = glass panel tint, *_r = roughness
FINISHES = {
    # reference finish (all-new burgundy, per Apple's product imagery: frame, plateau, lens rings and back glass colour-matched,
    # muted wine red with a slight purple cast; matte blasted aluminium, satin glass panel). Values estimated from the reference render.
    "burgundy":      dict(metal=(0.42, 0.125, 0.185), back=(0.20, 0.050, 0.085), metal_r=0.40, back_r=0.16),
    "silver":        dict(metal=(0.86, 0.86, 0.87), back=(0.80, 0.80, 0.82), metal_r=0.36, back_r=0.06),
    "deep_blue":     dict(metal=(0.26, 0.33, 0.48), back=(0.14, 0.19, 0.31), metal_r=0.36, back_r=0.06),
    "cosmic_orange": dict(metal=(0.86, 0.43, 0.20), back=(0.78, 0.36, 0.15), metal_r=0.36, back_r=0.06),
}

# dimensions (cm)
W, H, T = 7.19, 15.00, 0.875
R_OUT = 1.12            # outer corner radius
BEVEL = 0.14            # frame edge radius (front/back)
GLASS_INSET = 0.115     # front glass starts where the frame bevel ends
BEZEL = 0.115           # black border between glass edge and the lit display
PLATEAU_H = 4.35        # camera plateau height (full width)
LENS_R = 0.79           # outer radius of a lens ring


# ---------------------------------------------------------------------------------------------- geometry helpers
def rrect(w, h, r, seg=18):
    """Rounded-rectangle outline in the XZ plane (counter-clockwise), returns [(x, z)]."""
    pts = []
    cx, cz = w / 2 - r, h / 2 - r
    for (ccx, ccz, a0) in ((cx, cz, 0), (-cx, cz, 90), (-cx, -cz, 180), (cx, -cz, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    return pts


def rrect2(w, h, r_top, r_bot, seg=18):
    """Rounded rectangle with different radii on the top and bottom corners (XZ plane, CCW)."""
    pts = []
    for (sx, sz, a0, r) in ((1, 1, 0, r_top), (-1, 1, 90, r_top), (-1, -1, 180, r_bot), (1, -1, 270, r_bot)):
        ccx, ccz = sx * (w / 2 - r), sz * (h / 2 - r)
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    return pts


def _link(name, bm, mat, collection, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def _finish_normals(ob, bevel=None, seg=3, edge_split=None):
    if bevel:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, seg
        m.limit_method, m.angle_limit = "ANGLE", math.radians(35)
        m.harden_normals = True
        wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        wn.keep_sharp, wn.weight = True, 50
    if edge_split:
        es = ob.modifiers.new("EdgeSplit", "EDGE_SPLIT")
        es.split_angle = math.radians(edge_split)


def prism(name, pts, y0, y1, mat, collection, offset=(0, 0), bevel=0.0, bevel_seg=3):
    """Extrude an XZ outline along Y from y0 to y1."""
    bm = bmesh.new()
    ox, oz = offset
    face = bm.faces.new([bm.verts.new((x + ox, y0, z + oz)) for x, z in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, y1 - y0, 0), verts=verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _link(name, bm, mat, collection)
    _finish_normals(ob, bevel, bevel_seg)
    return ob


def lathe(name, profile, mat, collection, center, y_base=0.0, seg=96, edge_split=30):
    """Solid of revolution around +Y. `profile` = closed polygon [(radius, y)], y relative to y_base; centre = (x, z)."""
    bm = bmesh.new()
    vs = [bm.verts.new((r, y + y_base, 0)) for r, y in profile]
    for i in range(len(vs)):
        bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 1, 0),
                   angle=2 * math.pi, steps=seg, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.translate(bm, vec=(center[0], 0, center[1]), verts=bm.verts[:])
    ob = _link(name, bm, mat, collection)
    _finish_normals(ob, edge_split=edge_split)
    return ob


def dome(name, radius, height, y_center, mat, collection, center, seg=96):
    """Flattened sphere (lens cover glass): horizontal radius `radius`, vertical semi-axis `height`."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    bmesh.ops.scale(bm, vec=(radius, radius, height), verts=bm.verts[:])
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(-90), 4, "X"), verts=bm.verts[:])
    bmesh.ops.translate(bm, vec=(center[0], y_center, center[1]), verts=bm.verts[:])
    return _link(name, bm, mat, collection)


# ---------------------------------------------------------------------------------------------- materials
def _principled(nt):
    return next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def _set(node, **kw):
    for k, v in kw.items():
        if k in node.inputs:
            node.inputs[k].default_value = v


def mat_aluminium(name, color, rough, bump=0.05):
    """Bead-blasted anodised aluminium: metallic, with fine isotropic micro-texture breaking up the reflection."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (*color, 1), "Metallic": 1.0, "Roughness": rough})
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value, n1.inputs["Detail"].default_value = 1400.0, 3.0
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value, bm.inputs["Distance"].default_value = bump, 0.004
    nt.links.new(n1.outputs["Fac"], bm.inputs["Height"])
    nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    # tiny roughness variation = soft sparkle of blasted metal
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 90.0
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = max(0.0, rough - 0.05), rough + 0.05
    nt.links.new(n2.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_polished(name, color, rough=0.10):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    _set(_principled(m.node_tree), **{"Base Color": (*color, 1), "Metallic": 1.0, "Roughness": rough})
    return m


def mat_glass_opaque(name, color, rough, coat=0.0, spec=0.5, film=0.0):
    """Glossy dielectric (back glass, front glass, lens elements). `film` = thin-film thickness in nm for AR-coating tint."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    kw = {"Base Color": (*color, 1), "Roughness": rough, "Metallic": 0.0, "Coat Weight": coat, "Coat Roughness": 0.02,
          "Specular IOR Level": spec, "IOR": 1.52}
    if film:
        kw.update({"Thin Film Thickness": film, "Thin Film IOR": 1.9})
    _set(_principled(m.node_tree), **kw)
    return m


def mat_lens_cover(name="PHONE_LensCover_MAT"):
    """Transmissive cover glass: clear, with a faint AR-coating thin-film so highlights pick up a purple/blue sheen."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    _set(_principled(m.node_tree), **{"Base Color": (1, 1, 1, 1), "Roughness": 0.01, "Metallic": 0.0, "IOR": 1.52,
                                      "Transmission Weight": 1.0, "Specular IOR Level": 0.5})
    return m


def mat_screen(name="PHONE_Screen_MAT"):
    """Display: black glass + emission from an exchangeable image. Nodes are looked up by name from scripts."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (0.0, 0.0, 0.0, 1), "Roughness": 0.05, "Coat Weight": 0.3, "Coat Roughness": 0.02,
               "Specular IOR Level": 0.6, "Emission Strength": 1.0})
    img = nt.nodes.new("ShaderNodeTexImage")
    img.name = "SCREEN_IMAGE"
    img.interpolation, img.extension = "Cubic", "EXTEND"
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    nt.links.new(uv.outputs["UV"], img.inputs["Vector"])
    gain = nt.nodes.new("ShaderNodeMath")
    gain.name = "SCREEN_GAIN"          # animated: wake-up factor (0..1) * brightness
    gain.operation = "MULTIPLY"
    gain.inputs[0].default_value, gain.inputs[1].default_value = 1.0, 0.0
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(img.outputs["Color"], sc.inputs[0])
    nt.links.new(gain.outputs["Value"], sc.inputs["Scale"])
    nt.links.new(sc.outputs["Vector"], b.inputs["Emission Color"])
    return m


# ---------------------------------------------------------------------------------------------- camera lens module
def build_lens(i, center, plateau_top, col, mats):
    """One rear lens: polished ring (lathe, chamfered, with inner ledge), black gasket, domed cover glass, stepped barrel."""
    parts = []
    y0 = plateau_top
    ring = [(0.64, -0.03), (0.840, -0.03), (0.840, 0.170), (0.820, 0.195), (0.790, 0.205), (0.730, 0.205),
            (0.710, 0.195), (0.695, 0.170), (0.695, 0.075), (0.650, 0.075)]
    parts.append(lathe(f"PHONE_Lens{i}_Ring", ring, mats["ring"], col, center, y0))
    gasket = [(0.57, -0.01), (0.697, -0.01), (0.697, 0.100), (0.57, 0.100)]
    parts.append(lathe(f"PHONE_Lens{i}_Gasket", gasket, mats["gasket"], col, center, y0))
    barrel = [(0.0, 0.0), (0.54, 0.0), (0.54, 0.018), (0.46, 0.018), (0.46, 0.034), (0.38, 0.034), (0.38, 0.050),
              (0.29, 0.050), (0.29, 0.062), (0.0, 0.062)]
    parts.append(lathe(f"PHONE_Lens{i}_Barrel", barrel, mats["barrel"], col, center, y0 + 0.01))
    band = [(0.468, 0.0), (0.495, 0.0), (0.495, 0.0), (0.468, 0.0)]  # placeholder removed below
    core = [(0.0, 0.0), (0.21, 0.0), (0.21, 0.012), (0.0, 0.012)]
    parts.append(lathe(f"PHONE_Lens{i}_Core", core, mats["core"], col, center, y0 + 0.072))
    parts.append(dome(f"PHONE_Lens{i}_Cover", 0.625, 0.072, y0 + 0.108, mats["cover"], col, center))
    return parts


# ---------------------------------------------------------------------------------------------- the phone
def build_phone(collection, finish="silver", size=None):
    F = FINISHES[finish]
    root = bpy.data.objects.new("PHONE_Root", None)
    collection.objects.link(root)

    alu = mat_aluminium("PHONE_Frame_MAT", F["metal"], F["metal_r"])
    alu_plateau = mat_aluminium("PHONE_Plateau_MAT", F["metal"], F["metal_r"] * 0.85, bump=0.035)
    back = mat_glass_opaque("PHONE_BackGlass_MAT", F["back"], F["back_r"], coat=0.35, spec=0.6)
    front = mat_glass_opaque("PHONE_FrontGlass_MAT", (0.004, 0.004, 0.005), 0.035, coat=0.5, spec=0.7)
    ring_m = mat_polished("PHONE_LensRing_MAT", tuple(min(1.0, c * 1.02) for c in F["metal"]), 0.11)
    gasket_m = mat_glass_opaque("PHONE_LensGasket_MAT", (0.004, 0.004, 0.005), 0.45)
    barrel_m = mat_polished("PHONE_LensBarrel_MAT", (0.05, 0.05, 0.06), 0.16)
    core_m = mat_glass_opaque("PHONE_LensCore_MAT", (0.010, 0.012, 0.050), 0.025, coat=1.0, spec=1.0, film=230.0)
    cover_m = mat_lens_cover()
    dark = mat_glass_opaque("PHONE_DarkDetail_MAT", (0.002, 0.002, 0.003), 0.30)
    lens_mats = dict(ring=ring_m, gasket=gasket_m, barrel=barrel_m, core=core_m, cover=cover_m)

    parts = []
    parts.append(prism("PHONE_Frame", rrect(W, H, R_OUT), -T / 2, T / 2, alu, collection, bevel=BEVEL, bevel_seg=10))

    g_out = rrect(W - 2 * GLASS_INSET, H - 2 * GLASS_INSET, R_OUT - GLASS_INSET)
    parts.append(prism("PHONE_FrontGlass", g_out, -T / 2 - 0.010, -T / 2 + 0.02, front, collection, bevel=0.005, bevel_seg=2))

    # back: aluminium unibody (frame prism) + glass panel on the lower back + full-width camera plateau
    PL_FULL = PLATEAU_H + BEVEL                      # the plateau reaches the very top edge of the body
    pz = H / 2 - PL_FULL / 2
    z_top = pz - PL_FULL / 2 - 0.30
    z_bot = -H / 2 + 0.50
    panel = rrect(W - 0.95, z_top - z_bot, 0.80)
    parts.append(prism("PHONE_BackGlassPanel", panel, T / 2 - 0.012, T / 2 + 0.008, back, collection,
                       offset=(0, (z_top + z_bot) / 2), bevel=0.012, bevel_seg=3))
    p_out = rrect2(W - 0.004, PL_FULL - 0.002, R_OUT - 0.002, 0.95)
    pl_top = T / 2 + 0.262
    parts.append(prism("PHONE_Plateau", p_out, T / 2 - 0.01, pl_top, alu_plateau, collection, offset=(0, pz - 0.001), bevel=0.11, bevel_seg=9))

    # lenses (viewed from the back: two at the viewer's left = local +X, one in the middle) + flash / LiDAR / mic
    lens_pos = [(1.95, pz + 0.90), (1.95, pz - 0.90), (0.30, pz + 0.0)]
    for i, c in enumerate(lens_pos, 1):
        parts += build_lens(i, c, pl_top, collection, lens_mats)
    flash_c, lidar_c = (-1.95, pz + 0.90), (-1.95, pz - 0.90)
    parts.append(lathe("PHONE_FlashRing", [(0.25, -0.02), (0.345, -0.02), (0.345, 0.030), (0.33, 0.040), (0.25, 0.040)], ring_m, collection, flash_c, pl_top))
    parts.append(lathe("PHONE_Flash", [(0.0, -0.02), (0.26, -0.02), (0.26, 0.026), (0.0, 0.034)],
                       mat_glass_opaque("PHONE_Flash_MAT", (0.90, 0.88, 0.80), 0.30, spec=0.4), collection, flash_c, pl_top))
    parts.append(lathe("PHONE_LidarRing", [(0.34, -0.02), (0.43, -0.02), (0.43, 0.030), (0.415, 0.040), (0.34, 0.040)], ring_m, collection, lidar_c, pl_top))
    parts.append(lathe("PHONE_Lidar", [(0.0, -0.02), (0.345, -0.02), (0.345, 0.030), (0.0, 0.038)],
                       mat_glass_opaque("PHONE_Lidar_MAT", (0.006, 0.005, 0.014), 0.04, coat=0.8, spec=0.9, film=300.0), collection, lidar_c, pl_top))
    parts.append(lathe("PHONE_Mic", [(0.0, -0.02), (0.075, -0.02), (0.075, 0.020), (0.0, 0.020)], dark, collection, (-0.95, pz + 1.62), pl_top))

    # hardware buttons (left = action + volume, right = side button + camera control)
    def button(name, side, z0, z1, thick=0.46, out=0.045):
        sgn = 1 if side > 0 else -1
        x0, x1 = sgn * (W / 2 - 0.10), sgn * (W / 2 + out)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(abs(x1 - x0), thick, abs(z1 - z0)), verts=bm.verts[:])
        bmesh.ops.translate(bm, vec=((x0 + x1) / 2, 0, (z0 + z1) / 2), verts=bm.verts[:])
        ob = _link(name, bm, alu, collection)
        _finish_normals(ob, 0.04, 4)
        return ob
    parts.append(button("PHONE_ActionButton", -1, 5.55, 6.15))
    parts.append(button("PHONE_VolUp", -1, 3.55, 4.75))
    parts.append(button("PHONE_VolDown", -1, 2.00, 3.20))
    parts.append(button("PHONE_SideButton", +1, 3.20, 5.30, out=0.04))
    cc = button("PHONE_CameraControl", +1, -2.90, -1.70, out=0.012)
    cc.data.materials.clear()
    cc.data.materials.append(mat_glass_opaque("PHONE_CameraControl_MAT", (0.01, 0.01, 0.012), 0.05, coat=0.4, spec=0.8))
    cc.modifiers["Bevel"].width, cc.modifiers["Bevel"].segments = 0.14, 6
    parts.append(cc)

    # bottom face: USB-C slot + speaker/mic holes
    def bottom_capsule(name, cx, wd, ht, depth=0.002):
        pts = [(cx + wd / 2 * math.cos(2 * math.pi * k / 24), ht / 2 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
        bm = bmesh.new()
        bm.faces.new([bm.verts.new((x, y, -H / 2 - depth)) for x, y in pts])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return _link(name, bm, dark, collection)
    parts.append(bottom_capsule("PHONE_USBC", 0.0, 0.85, 0.25))
    for k in range(5):
        parts.append(bottom_capsule(f"PHONE_SpkL{k}", -1.45 - 0.17 * k, 0.07, 0.07))
        parts.append(bottom_capsule(f"PHONE_SpkR{k}", +1.45 + 0.17 * k, 0.07, 0.07))

    # the display (separate object with UVs); lit area starts BEZEL inside the glass edge
    inset = GLASS_INSET + BEZEL
    dw, dh = W - 2 * inset, H - 2 * inset
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    d_out = rrect(dw, dh, R_OUT - inset, seg=18)
    vs = [bm.verts.new((x, -T / 2 - 0.0105 - 0.0015, z)) for x, z in d_out]
    f = bm.faces.new(vs[::-1])
    for lp in f.loops:
        co = lp.vert.co
        lp[uv_layer].uv = ((co.x + dw / 2) / dw, (co.z + dh / 2) / dh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    screen = _link("PHONE_Screen", bm, mat_screen(), collection)
    screen.modifiers.new("Triangulate", "TRIANGULATE")
    parts.append(screen)

    for ob in parts:
        ob.parent = root
    return root, screen, dict(W=W, H=H, T=T, plateau_z=pz, lens=lens_pos, display=(dw, dh))

"""Procedural phone model (bpy), v5. 1 unit = 1 cm.

Local axes: +X = viewer's right when looking at the FRONT, +Z = up, front glass faces -Y, back faces +Y.

REFERENCE / HONESTY NOTE (see documentation/phone_model.md for the full table)
  Layout and proportions are read from supplied burgundy iPhone 18 Pro product imagery (4 images) and the verified facts that the
  plateau is unchanged from the iPhone 17 Pro, the body is 150.0 x 71.9 x 8.75 mm (third-party/Wikipedia figures), the enclosure is aluminium with
  colour-matched back glass, and the display is 6.3 in, 1206 x 2622 px. Everything that could not be measured is marked ASSUMED below.
  "Burgundy" is the creative direction required for this film; Apple's own pages (per search results) list it among the 18 Pro finishes.

Objects (all under PHONE_Root): PHONE_Frame, PHONE_FrontGlass, PHONE_Screen, PHONE_RearGlass, PHONE_Plateau, PHONE_PlateauFace,
PHONE_Lens{A,B,C}_{Ring,Gasket,Barrel,Core,Cover}, PHONE_Flash(+Ring), PHONE_LiDAR(+Ring), PHONE_Mic, PHONE_Btn_*, PHONE_Openings (cutters baked into the frame).
The screen is a separate object whose image texture is swapped per frame (exchangeable screen content).
"""
import math, os
import bpy
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------------------------------------- finishes
# metal = aluminium albedo (F0), back = rear-glass base colour, *_r = roughness.   "burgundy" is tuned against neutral-studio renders
# (documentation/phone_model.md, colour section).
FINISHES = {
    "burgundy":      dict(metal=(0.520, 0.145, 0.205), back=(0.290, 0.060, 0.118), metal_r=0.40, back_r=0.30),
    "silver":        dict(metal=(0.86, 0.86, 0.87), back=(0.80, 0.80, 0.82), metal_r=0.36, back_r=0.20),
    "deep_blue":     dict(metal=(0.26, 0.33, 0.48), back=(0.14, 0.19, 0.31), metal_r=0.36, back_r=0.20),
}

# dimensions (cm)
W, H, T = 7.19, 15.00, 0.875          # body: published figures for the Pro-size body
R_OUT = 1.12                          # ASSUMED outer corner radius (measured visually against the references)
R_BACK, R_FRONT = 0.22, 0.10          # frame edge radii (back is softer, per references)
GLASS_INSET = 0.10                    # front glass starts where the front edge radius ends
BEZEL = 0.13                          # black border to the lit display: display inset 2.3 mm (6.3 in / 1206x2622 -> 66.9 x 145.4 mm)
PL_H = 4.45                           # camera plateau height: ~4.3 cm measured, raised so lens B clears the lower rim (checked by layout_margins())
PL_RB = 0.60                          # plateau lower corner radius (small, like Apple's frame; a large one cut into lens B)
FACE_INSET = (0.40, 0.40, 0.16)       # recessed face boundary: (side, top, bottom) inset from the plateau outline
PL_RISE = 0.28                        # ASSUMED plateau height above the back surface (about 2.8 mm, from reference close-ups)
LENS_R = 0.87                         # lens ring outer radius (measured 0.875 cm in Apple's film macro frame)


# ---------------------------------------------------------------------------------------------- geometry helpers
def rrect2(w, h, r_top, r_bot, seg=20):
    """Rounded rectangle with different radii on the top and bottom corners (XZ plane, CCW)."""
    pts = []
    for (sx, sz, a0, r) in ((1, 1, 0, r_top), (-1, 1, 90, r_top), (-1, -1, 180, r_bot), (1, -1, 270, r_bot)):
        ccx, ccz = sx * (w / 2 - r), sz * (h / 2 - r)
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    return pts


def rrect(w, h, r, seg=20):
    return rrect2(w, h, r, r, seg)


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


def _modifiers(ob, bevel=None, seg=3, edge_split=None, weighted=True):
    if bevel:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, seg
        m.limit_method, m.angle_limit = "ANGLE", math.radians(35)
        m.harden_normals = True
        if weighted:
            wn = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
            wn.keep_sharp, wn.weight = True, 50
    if edge_split:
        ob.modifiers.new("EdgeSplit", "EDGE_SPLIT").split_angle = math.radians(edge_split)


def loft(name, w, h, rt, rb, profile, mat, collection, offset=(0.0, 0.0), seg=20):
    """Sweep a cross-section along a rounded-rectangle outline.
    `profile` = [(d, y)]: d = inward offset from the outline, y = height; the first and last rings become flat caps (closed solid).
    Offsetting a rounded rectangle by d gives a rounded rectangle with radii r-d, so the sweep is exact."""
    bm = bmesh.new()
    rings = []
    for item in profile:
        if len(item) == 2:
            d, y = item
            dx = dt = db = d
        else:
            dx, dt, db, y = item
        hh = h - dt - db
        zc = (db - dt) / 2.0                                  # centre shift when the top and bottom insets differ
        pts = rrect2(w - 2 * dx, hh, max(0.05, rt - 0.5 * (dx + dt)), max(0.05, rb - 0.5 * (dx + db)), seg)
        rings.append([bm.verts.new((x + offset[0], y, z + offset[1] + zc)) for x, z in pts])
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    caps = [bm.faces.new(rings[0]), bm.faces.new(rings[-1][::-1])]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _link(name, bm, mat, collection)
    for c in caps:                                   # caps stay flat-shaded
        pass
    return ob


def arc(d0, y0, r, a_from, a_to, steps, kind):
    """Quarter-round profile points. kind: 'back' (flat top -> side wall) or 'front' (side wall -> flat bottom)."""
    out = []
    for i in range(steps + 1):
        a = math.radians(a_from + (a_to - a_from) * i / steps)
        if kind == "back":        # centre (d=r, y=y0): from top flat start (a=0) to side (a=90)
            out.append((r * (1 - math.sin(a)), y0 + r * math.cos(a)))
        else:                     # centre (d=r, y=y0): from side (a=0) to front flat (a=90)
            out.append((r * (1 - math.cos(a)), y0 - r * math.sin(a)))
    return out


def lathe(name, profile, mat, collection, center, y_base=0.0, seg=96, edge_split=30):
    """Solid of revolution around +Y. profile = closed polygon [(radius, y)] (y relative to y_base); centre = (x, z)."""
    bm = bmesh.new()
    vs = [bm.verts.new((r, y + y_base, 0)) for r, y in profile]
    for i in range(len(vs)):
        bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 1, 0), angle=2 * math.pi, steps=seg, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.translate(bm, vec=(center[0], 0, center[1]), verts=bm.verts[:])
    ob = _link(name, bm, mat, collection)
    _modifiers(ob, edge_split=edge_split)
    return ob


def dome(name, radius, height, y_center, mat, collection, center, seg=96):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    bmesh.ops.scale(bm, vec=(radius, radius, height), verts=bm.verts[:])
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(-90), 4, "X"), verts=bm.verts[:])
    bmesh.ops.translate(bm, vec=(center[0], y_center, center[1]), verts=bm.verts[:])
    return _link(name, bm, mat, collection)


def pill(name, x0, x1, z0, z1, thick, mat, collection, bevel):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(abs(x1 - x0), thick, abs(z1 - z0)), verts=bm.verts[:])
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, 0, (z0 + z1) / 2), verts=bm.verts[:])
    ob = _link(name, bm, mat, collection)
    _modifiers(ob, bevel, 6)
    return ob


def planar_uv(ob, cx, cz, pw, ph):
    me = ob.data
    uv = me.uv_layers.new(name="UVMap")
    for lp in me.loops:
        co = me.vertices[lp.vertex_index].co
        uv.data[lp.index].uv = ((co.x - cx) / pw + 0.5, (co.z - cz) / ph + 0.5)


def apply_boolean_cut(target, cutter, mat_slot_dark):
    """Bake `cutter` out of `target` (Exact solver) so openings are real recesses, inner walls take the cutter's dark material."""
    target.data.materials.append(mat_slot_dark)
    m = target.modifiers.new("Openings", "BOOLEAN")
    m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", cutter
    m.material_mode = "TRANSFER"
    dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg)
    new_me = bpy.data.meshes.new_from_object(ev)
    old = target.data
    target.modifiers.remove(m)
    target.data = new_me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)


# ---------------------------------------------------------------------------------------------- materials
def _principled(nt):
    return next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def _set(node, **kw):
    for k, v in kw.items():
        if k in node.inputs:
            node.inputs[k].default_value = v


def mat_aluminium(name, color, rough, bump=0.20, streak=False):
    """Anodised, bead-blasted aluminium: metallic, fine micro-texture, faint roughness variation (soft sparkle)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (*color, 1), "Metallic": 1.0, "Roughness": rough})
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value, n1.inputs["Detail"].default_value = 170.0, 2.0       # blasted grain ~0.06 mm (Apple macro frame)
    if streak:                                                                                # fine directional brushing along the plateau's length
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.0, 1.0, 0.08)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    else:
        nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value, bm.inputs["Distance"].default_value = bump, 0.0016
    nt.links.new(n1.outputs["Fac"], bm.inputs["Height"])
    nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 40.0
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = max(0.0, rough - 0.04), rough + 0.04
    nt.links.new(n2.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_satin_metal(name, color, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    _set(_principled(m.node_tree), **{"Base Color": (*color, 1), "Metallic": 1.0, "Roughness": rough})
    return m


def mat_dielectric(name, color, rough, coat=0.0, spec=0.5, film=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    kw = {"Base Color": (*color, 1), "Roughness": rough, "Metallic": 0.0, "Coat Weight": coat, "Coat Roughness": 0.03,
          "Specular IOR Level": spec, "IOR": 1.52}
    if film:
        kw.update({"Thin Film Thickness": film, "Thin Film IOR": 1.9})
    _set(_principled(m.node_tree), **kw)
    return m


def mat_flash(name="PHONE_Flash_MAT"):
    """Frosted white flash diffuser with concentric fresnel-like rings."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (0.42, 0.41, 0.39, 1), "Roughness": 0.34, "Metallic": 0.0, "Specular IOR Level": 0.5})
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type, wv.bands_direction, wv.rings_direction = "RINGS", "X", "Z"
    wv.inputs["Scale"].default_value, wv.inputs["Distortion"].default_value = 28.0, 0.0
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value, bp.inputs["Distance"].default_value = 0.6, 0.004
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_lens_cover(name="PHONE_LensCover_MAT"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    _set(_principled(m.node_tree), **{"Base Color": (1, 1, 1, 1), "Roughness": 0.008, "Metallic": 0.0, "IOR": 1.52,
                                      "Transmission Weight": 1.0, "Specular IOR Level": 0.5})
    return m


def mat_rear_glass(name, color, rough, mask_path):
    """Colour-matched satin glass; the logo area is the same glass polished (lower roughness, a touch lighter). Mask is a grey PNG (white = logo)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = _principled(nt)
    _set(b, **{"Base Color": (*color, 1), "Roughness": rough, "Metallic": 0.0, "Coat Weight": 0.10, "Coat Roughness": 0.25,
               "Specular IOR Level": 0.40, "IOR": 1.52})
    if mask_path and os.path.exists(mask_path):
        uv = nt.nodes.new("ShaderNodeUVMap")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.name = "LOGO_MAPPING"
        img = nt.nodes.new("ShaderNodeTexImage")
        img.name = "LOGO_MASK"
        img.image = bpy.data.images.load(mask_path, check_existing=True)
        img.image.colorspace_settings.name = "Non-Color"
        img.extension, img.interpolation = "CLIP", "Linear"
        nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough, 0.06
        nt.links.new(img.outputs["Color"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*color, 1)
        mix.inputs["B"].default_value = tuple(min(1.0, c * 1.9) for c in color) + (1,)
        nt.links.new(img.outputs["Color"], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def mat_screen(name="PHONE_Screen_MAT"):
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
    nt.links.new(uv.outputs["UV"], img.inputs["Vector"])
    gain = nt.nodes.new("ShaderNodeMath")
    gain.name = "SCREEN_GAIN"
    gain.operation = "MULTIPLY"
    gain.inputs[0].default_value, gain.inputs[1].default_value = 1.0, 0.0
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(img.outputs["Color"], sc.inputs[0])
    nt.links.new(gain.outputs["Value"], sc.inputs["Scale"])
    nt.links.new(sc.outputs["Vector"], b.inputs["Emission Color"])
    return m


# ---------------------------------------------------------------------------------------------- camera lens module
def hex_ring(name, r_out, r_in, y0, y1, mat, collection, center):
    """Hexagonal aperture frame (six blades) seen through the cover glass of the main camera."""
    bm = bmesh.new()
    def pts(r, y):
        return [bm.verts.new((center[0] + r * math.cos(math.radians(60 * k + 30)), y, center[1] + r * math.sin(math.radians(60 * k + 30)))) for k in range(6)]
    o0, o1, i0, i1 = pts(r_out, y0), pts(r_out, y1), pts(r_in, y0), pts(r_in, y1)
    for k in range(6):
        j = (k + 1) % 6
        bm.faces.new((o0[k], o0[j], o1[j], o1[k]))      # outer wall
        bm.faces.new((o1[k], o1[j], i1[j], i1[k]))      # top
        bm.faces.new((i1[k], i1[j], i0[j], i0[k]))      # inner wall
        bm.faces.new((i0[k], i0[j], o0[j], o0[k]))      # bottom
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _link(name, bm, mat, collection, smooth=False)
    return ob


def build_lens(tag, center, y0, col, mats, hex_aperture=False):
    """One rear lens (R 0.87 ring from Apple's macro frame): wide rounded satin ring, thin recess groove around it, flat black cover glass
    with a fine edge line, stepped dark barrel, coated core; the main camera also shows its hexagonal aperture."""
    ring = [(0.700, -0.03), (0.870, -0.03), (0.870, 0.120), (0.862, 0.158), (0.840, 0.184), (0.800, 0.196),
            (0.760, 0.190), (0.735, 0.170), (0.722, 0.140), (0.722, 0.060), (0.690, 0.060)]
    parts = [lathe(f"PHONE_Lens{tag}_Ring", ring, mats["ring"], col, center, y0)]
    parts.append(lathe(f"PHONE_Lens{tag}_Groove", [(0.868, -0.004), (0.905, -0.004), (0.905, 0.004), (0.868, 0.004)], mats["groove"], col, center, y0))
    parts.append(lathe(f"PHONE_Lens{tag}_Gasket", [(0.60, -0.01), (0.726, -0.01), (0.726, 0.085), (0.60, 0.085)], mats["gasket"], col, center, y0))
    barrel = [(0.0, 0.0), (0.60, 0.0), (0.60, 0.016), (0.50, 0.016), (0.50, 0.030), (0.41, 0.030), (0.41, 0.044), (0.0, 0.044)]
    parts.append(lathe(f"PHONE_Lens{tag}_Barrel", barrel, mats["barrel"], col, center, y0 + 0.01))
    if hex_aperture:
        parts.append(hex_ring(f"PHONE_Lens{tag}_Aperture", 0.42, 0.25, y0 + 0.056, y0 + 0.074, mats["barrel"], col, center))
    parts.append(lathe(f"PHONE_Lens{tag}_Core", [(0.0, 0.0), (0.19, 0.0), (0.19, 0.012), (0.0, 0.012)], mats["core"], col, center, y0 + 0.062))
    parts.append(dome(f"PHONE_Lens{tag}_Cover", 0.700, 0.026, y0 + 0.120, mats["cover"], col, center))
    return parts


# ---------------------------------------------------------------------------------------------- the phone
def build_phone(collection, finish="burgundy", size=None):
    F = FINISHES[finish]
    root = bpy.data.objects.new("PHONE_Root", None)
    collection.objects.link(root)
    logo_path = os.path.join(ROOT, "assets", "phone", "apple_logo_mask.png")

    alu = mat_aluminium("PHONE_Frame_MAT", F["metal"], F["metal_r"])
    alu_rim = mat_aluminium("PHONE_PlateauRim_MAT", F["metal"], F["metal_r"] * 0.9, bump=0.16)
    alu_face = mat_aluminium("PHONE_PlateauFace_MAT", tuple(c * 0.92 for c in F["metal"]), min(0.62, F["metal_r"] * 1.25), bump=0.22, streak=True)
    rear = mat_rear_glass("PHONE_RearGlass_MAT", F["back"], F["back_r"], logo_path)
    front = mat_dielectric("PHONE_FrontGlass_MAT", (0.004, 0.004, 0.005), 0.035, coat=0.5, spec=0.7)
    ring_m = mat_aluminium("PHONE_LensRing_MAT", tuple(min(1.0, c * 1.04) for c in F["metal"]), 0.44, bump=0.20)
    gasket_m = mat_dielectric("PHONE_LensGasket_MAT", (0.004, 0.004, 0.005), 0.45)
    barrel_m = mat_satin_metal("PHONE_LensBarrel_MAT", (0.26, 0.26, 0.29), 0.30)
    core_m = mat_dielectric("PHONE_LensCore_MAT", (0.020, 0.024, 0.085), 0.025, coat=1.0, spec=1.0, film=230.0)
    cover_m = mat_lens_cover()
    dark = mat_dielectric("PHONE_Recess_MAT", (0.002, 0.002, 0.003), 0.55)
    button_m = mat_aluminium("PHONE_Button_MAT", tuple(c * 1.06 for c in F["metal"]), F["metal_r"] * 0.85, bump=0.14)
    groove_m = mat_aluminium("PHONE_LensGroove_MAT", tuple(c * 0.30 for c in F["metal"]), 0.55, bump=0.10)
    lens_mats = dict(ring=ring_m, gasket=gasket_m, barrel=barrel_m, core=core_m, cover=cover_m, groove=groove_m)
    parts = []

    # --- frame (swept profile: soft back edge, tighter front edge)
    prof = arc(0, T / 2 - R_BACK, R_BACK, 0, 90, 10, "back") + arc(0, -T / 2 + R_FRONT, R_FRONT, 0, 90, 6, "front")
    frame = loft("PHONE_Frame", W, H, R_OUT, R_OUT, prof, alu, collection)
    parts.append(frame)

    # --- front glass + display
    parts.append(_prism_glass("PHONE_FrontGlass", W - 2 * GLASS_INSET, H - 2 * GLASS_INSET, R_OUT - GLASS_INSET,
                              -T / 2 - 0.010, -T / 2 + 0.02, front, collection))
    inset = GLASS_INSET + BEZEL
    dw, dh = W - 2 * inset, H - 2 * inset
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new((x, -T / 2 - 0.0115, z)) for x, z in rrect(dw, dh, R_OUT - inset, 20)]
    f = bm.faces.new(vs[::-1])
    for lp in f.loops:
        co = lp.vert.co
        lp[uvl].uv = ((co.x + dw / 2) / dw, (co.z + dh / 2) / dh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    screen = _link("PHONE_Screen", bm, mat_screen(), collection)
    screen.modifiers.new("Triangulate", "TRIANGULATE")
    parts.append(screen)

    # --- camera plateau: full-width raised block of the unibody, soft rim, recessed face with a small step
    pz = H / 2 - PL_H / 2
    ytop = T / 2 + PL_RISE
    yf = ytop - 0.05                                  # recessed face level (also the lens base plane)
    pprof = [(FACE_INSET[0] + 0.05, FACE_INSET[1] + 0.05, FACE_INSET[2] + 0.04, yf), (*FACE_INSET, yf), (FACE_INSET[0] - 0.04, FACE_INSET[1] - 0.04, FACE_INSET[2] - 0.02, ytop)] + [(d, y) for d, y in arc(0, ytop - 0.30, 0.30, 0, 90, 10, "back")] + [(0.0, T / 2 - 0.24)]
    # arc() starts at d=0.30 (flat) -> d=0 (wall); insert flat rim between d=0.40 and 0.30 is implicit (straight segment)
    plateau = loft("PHONE_Plateau", W - 0.004, PL_H, R_OUT - 0.002, PL_RB, pprof, alu_rim, collection, offset=(0, pz))
    # recessed face gets its own (matte) material: faces whose centre lies inside the recess ring
    plateau.data.materials.append(alu_face)
    for poly in plateau.data.polygons:
        if poly.center.y < yf + 1e-4 and poly.center.y > yf - 1e-4 and poly.normal.y > 0.9:
            poly.material_index = 1
    parts.append(plateau)

    # --- rear glass panel (colour-matched satin glass with the polished logo), recessed flush into the aluminium
    z_top = pz - PL_H / 2 - 0.35
    z_bot = -H / 2 + 0.50
    pw_, ph_ = W - 0.90, z_top - z_bot
    pc = (z_top + z_bot) / 2
    panel = _prism_glass("PHONE_RearGlass", pw_, ph_, 1.05, T / 2 - 0.012, T / 2 + 0.004, rear, collection, offset=(0, pc), bevel=0.01)
    planar_uv(panel, 0.0, pc, pw_, ph_)
    logo_w, logo_cz = 2.50, -1.60                     # logo mask square = 2.5 cm; centre below mid-body (ref. image 3)
    mp = rear.node_tree.nodes.get("LOGO_MAPPING")
    if mp:
        sx, sy = pw_ / logo_w, ph_ / logo_w
        v_c = (logo_cz - pc) / ph_ + 0.5
        mp.inputs["Scale"].default_value = (sx, sy, 1.0)
        mp.inputs["Location"].default_value = (0.5 - 0.5 * sx, 0.5 - v_c * sy, 0.0)
    parts.append(panel)

    # --- lenses A (top-left), B (bottom-left), C (right-middle), as seen from the back (viewer-left = local +X)
    # absolute local positions measured in Apple's burgundy plateau frame (z from the top edge at +7.5 cm). ASSUMED: lens A = main camera (hex aperture)
    lens_c = {"A": (2.27, 6.09), "B": (2.28, 4.14), "C": (0.37, 5.16)}
    for tag, c in lens_c.items():
        parts += build_lens(tag, c, yf, collection, lens_mats, hex_aperture=(tag == "A"))
    flash_c, mic_c, lidar_c = (-2.22, 6.14), (-2.22, 5.11), (-2.22, 4.10)
    parts.append(lathe("PHONE_FlashRing", [(0.31, -0.02), (0.365, -0.02), (0.365, 0.030), (0.350, 0.040), (0.31, 0.040)], ring_m, collection, flash_c, yf))
    parts.append(lathe("PHONE_Flash", [(0.0, -0.02), (0.315, -0.02), (0.315, 0.028), (0.0, 0.034)], mat_flash(), collection, flash_c, yf))
    parts.append(lathe("PHONE_LiDAR", [(0.0, -0.02), (0.345, -0.02), (0.345, 0.012), (0.0, 0.016)],
                       mat_dielectric("PHONE_LiDAR_MAT", (0.004, 0.004, 0.008), 0.12, coat=0.6, spec=0.6, film=300.0), collection, lidar_c, yf))
    parts.append(lathe("PHONE_Mic", [(0.0, -0.02), (0.06, -0.02), (0.06, 0.020), (0.0, 0.020)], dark, collection, mic_c, yf))

    # --- buttons (z ranges read from the reference images; ASSUMED lengths): left = action + volume, right = side button + camera control
    def button(name, side, z0, z1, thick=0.40, out=0.05, bevel=0.10):
        sgn = 1 if side > 0 else -1
        return pill(name, sgn * (W / 2 - 0.12), sgn * (W / 2 + out), z0, z1, thick, button_m, collection, bevel)
    parts.append(button("PHONE_Btn_Action", -1, 4.00, 4.90, thick=0.36))
    parts.append(button("PHONE_Btn_VolUp", -1, 2.35, 3.50))
    parts.append(button("PHONE_Btn_VolDown", -1, 1.15, 2.30))
    parts.append(button("PHONE_Btn_Side", +1, 2.10, 3.60, out=0.05))
    parts.append(button("PHONE_Btn_CameraControl", +1, -3.55, -1.95, thick=0.34, out=0.03, bevel=0.12))

    seam_m = mat_satin_metal("PHONE_SeamBand_MAT", tuple(min(1.0, c * 0.80) for c in F["metal"]), 0.16)
    for sgn, nm in ((-1, "L"), (1, "R")):
        parts.append(pill(f"PHONE_SeamBand_{nm}", sgn * (W / 2 - 0.05), sgn * (W / 2 + 0.006), 5.82, 5.89, 0.62, seam_m, collection, 0.012))

    # --- openings on the bottom face: USB-C + speaker/microphone holes, cut as real recesses
    cut = bmesh.new()
    def cutter_cyl(cx, r, depth, cy=0.0):
        bmesh.ops.create_cone(cut, cap_ends=True, segments=16, radius1=r, radius2=r, depth=depth,
                              matrix=Matrix.Translation((cx, cy, -H / 2 + depth / 2 - 0.02)) @ Matrix.Rotation(math.radians(90), 4, "X"))
    # USB-C: capsule 0.86 x 0.26, depth 0.6
    cap_w, cap_h, depth = 0.86, 0.26, 0.60
    cutter_cyl(-(cap_w - cap_h) / 2, cap_h / 2, depth)
    cutter_cyl((cap_w - cap_h) / 2, cap_h / 2, depth)
    bmesh.ops.create_cube(cut, size=1.0, matrix=Matrix.Translation((0, 0, -H / 2 + depth / 2 - 0.02)) @ Matrix.Diagonal((cap_w - cap_h, cap_h, depth, 1.0)))
    for k in range(6):                                # ASSUMED: one row of 6 holes per side
        cutter_cyl(-1.55 - 0.175 * k, 0.045, 0.45)
        cutter_cyl(+1.55 + 0.175 * k, 0.045, 0.45)
    cutter = _link("PHONE_Openings", cut, dark, collection)
    cutter.data.materials.clear(); cutter.data.materials.append(dark)
    apply_boolean_cut(frame, cutter, dark)

    for ob in parts:
        ob.parent = root
    return root, screen, dict(W=W, H=H, T=T, plateau_z=pz, lens=lens_c, display=(dw, dh))


def _prism_glass(name, w, h, r, y0, y1, mat, collection, offset=(0, 0), bevel=0.006):
    bm = bmesh.new()
    ox, oz = offset
    face = bm.faces.new([bm.verts.new((x + ox, y0, z + oz)) for x, z in rrect(w, h, r, 20)])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, y1 - y0, 0), verts=verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _link(name, bm, mat, collection)
    _modifiers(ob, bevel, 2)
    return ob


# ---------------------------------------------------------------------------------------------- layout self-check
LENS_CENTERS = {"A": (2.27, 6.09), "B": (2.28, 4.14), "C": (0.37, 5.16)}


def _sd_rrect(px, pz, cx, cz, w, h, rt, rb):
    """Signed distance (negative inside) to a rounded rectangle whose top and bottom corner radii differ."""
    qz0 = pz - cz
    r = rt if qz0 > 0 else rb
    qx, qz = abs(px - cx) - (w / 2 - r), abs(qz0) - (h / 2 - r)
    return math.hypot(max(qx, 0.0), max(qz, 0.0)) + min(max(qx, qz), 0.0) - r


def layout_margins():
    """Clearance (cm) between each lens ring and the edge of the recessed plateau face, sampled around the ring; must be > 0 for a lens to sit inside."""
    pz = H / 2 - PL_H / 2
    sx, st, sb = FACE_INSET
    w, h = W - 0.004 - 2 * sx, PL_H - st - sb
    cz = pz + (sb - st) / 2.0
    rt = max(0.05, R_OUT - 0.002 - 0.5 * (sx + st))
    rb = max(0.05, PL_RB - 0.5 * (sx + sb))
    out = {}
    for tag, (lx, lz) in LENS_CENTERS.items():
        worst = 9.0
        for k in range(180):
            a = 2 * math.pi * k / 180
            worst = min(worst, -_sd_rrect(lx + LENS_R * math.cos(a), lz + LENS_R * math.sin(a), 0.0, cz, w, h, rt, rb))
        out[tag] = round(worst, 3)
    return out

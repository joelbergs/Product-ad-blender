"""Geometry helpers (bpy): precision slabs, photo cards, drawn-on tubes, extruded logo."""
import math
import bpy
import bmesh
from mathutils import Vector


def _outline(w, h, r, seg):
    """Rounded-rectangle outline, CCW. Returns [(point(x,y), outward_normal(nx,ny))]."""
    pts = []
    cx, cy = w / 2 - r, h / 2 - r
    for k, (sx, sy, a0) in enumerate([(1, 1, 0.0), (-1, 1, 90.0), (-1, -1, 180.0), (1, -1, 270.0)]):
        for i in range(seg + 1):
            a = math.radians(a0 + 90.0 * i / seg)
            nx, ny = math.cos(a), math.sin(a)
            pts.append((((sx * cx) + r * nx, (sy * cy) + r * ny), (nx, ny)))
    return pts


def _profile(t, re, seg):
    """(inset u, z) from the top-face boundary round the bullnose edge to the bottom-face boundary."""
    prof = []
    for i in range(seg + 1):
        a = math.radians(90.0 * i / seg)
        prof.append((re * (1 - math.sin(a)), (t / 2 - re) + re * math.cos(a)))
    if t > 2 * re + 1e-9:
        pass  # straight flank is the quad between the two arcs
    for i in range(seg + 1):
        a = math.radians(90.0 * i / seg)
        # mirror: from (u=0, z=-(t/2-re)) to (u=re, z=-t/2)
        prof.append((re * (1 - math.cos(a)), -(t / 2 - re) - re * math.sin(a)))
    return prof


def make_slab(name, w, h, t, r_corner, r_edge, mats, seg_corner=16, seg_edge=7, collection=None):
    """Rounded slab centred on the origin, thickness along +-Z/2.
    mats = (front, edge, back) materials. Front cap carries UVs 0..1 across the full w x h."""
    r_edge = min(r_edge, t / 2 - 1e-6, r_corner - 1e-6)
    out = _outline(w, h, r_corner, seg_corner)
    prof = _profile(t, r_edge, seg_edge)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    ring = []
    for (u, z) in prof:
        row = []
        for (p, n) in out:
            row.append(bm.verts.new((p[0] - n[0] * u, p[1] - n[1] * u, z)))
        ring.append(row)
    N = len(out)
    for j in range(len(prof) - 1):
        for i in range(N):
            i2 = (i + 1) % N
            f = bm.faces.new((ring[j][i], ring[j][i2], ring[j + 1][i2], ring[j + 1][i]))
            f.material_index = 1
            f.smooth = True
    # caps from duplicated vertices (flat shading, no normal bleed)
    for which, (row, z_sign) in enumerate([(ring[0], +1), (ring[-1], -1)]):
        vs = [bm.verts.new(v.co) for v in row]
        cap = bm.faces.new(vs if which == 0 else vs[::-1])
        cap.material_index = 0 if which == 0 else 2
        cap.smooth = False
        for loop in cap.loops:
            x, y = loop.vert.co.x, loop.vert.co.y
            u_ = x / w + 0.5
            if which == 1:
                u_ = 1.0 - u_
            loop[uvl].uv = (u_, y / h + 0.5)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    for m in mats:
        me.materials.append(m)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def make_plane(name, w, h, mat, collection=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for loop, (u, v) in zip(me.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = (u, v)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def make_tube(name, points, radius, mat, collection=None, resolution=12):
    """Smooth tube through points (list of xyz). Draw-on = `bevel_factor_end` 0..1 (animatable)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS" if False else "BEZIER")
    sp.bezier_points.add(len(points) - 1)
    pts = [Vector(p) for p in points]
    for i, bp in enumerate(sp.bezier_points):
        bp.co = pts[i]
        prev = pts[max(i - 1, 0)]
        nxt = pts[min(i + 1, len(pts) - 1)]
        tan = (nxt - prev) * 0.5
        bp.handle_left_type = bp.handle_right_type = "FREE"
        bp.handle_left = pts[i] - tan / 3.0
        bp.handle_right = pts[i] + tan / 3.0
    cu.materials.append(mat)
    cu.bevel_factor_start = 0.0
    cu.bevel_factor_end = 0.0
    ob = bpy.data.objects.new(name, cu)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def import_logo_bars(svg_path, depth, bevel, mat, collection=None, name="LogoBar"):
    """Import the brand mark SVG as curves and return one extruded mesh object per slit (nine bars), centred.
    Units: the SVG viewBox is 600 units; scaling is left to the caller via the returned parent empty."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=svg_path)
    new = [o for o in bpy.data.objects if o not in before]
    bars = []
    for ob in new:
        if ob.type != "CURVE":
            continue
        ob.data.dimensions = "2D"
        ob.data.extrude = depth / 2
        ob.data.bevel_depth = bevel
        ob.data.bevel_resolution = 3
        ob.data.fill_mode = "BOTH"
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        bars.append(ob)
    return bars


def make_text(name, text, size, mat, font_path, collection=None, align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = align
    cu.align_y = "TOP"
    cu.extrude = 0.0
    cu.resolution_u = 6
    try:
        cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    except Exception:
        pass
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob

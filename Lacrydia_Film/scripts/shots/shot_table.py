"""TABLE sequence = shots D (overhead pile), E (extreme detail) and F (the Tree) as ONE continuous physical space.

T (seconds, local):  D 0.0-6.5 | E 6.5-10.0 | F 10.0-18.5
 D  a scanning light travels across the obsidian; photographs emerge as it reaches them (a camera roll is a pile)
 E  macro on the root photograph; a thin line of light leaves its edge
 F  photographs glide into place, lines draw on and pulse, the camera pulls back and rises: a place, not a pile
"""
import math
import numpy as np
from mathutils import Vector
from lib import rig, sets, motion, geo, mat, tree
from lib.anim import K

NAME = "TABLE"
DURATION = 18.5
BAKE = False
SEG = dict(D=(0.0, 6.5), E=(6.5, 10.0), F=(10.0, 18.5))
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"
PH = "/home/user/Product-ad-blender/Lacrydia_Film/assets/lacrydia/photos"
THICK = 0.0025

# --- choreography (shared with the sound design: lib/choreo.py) ------------------------------------------------------
from lib.choreo import SCAN, GLIDE, START, LINE_T, LINE_START
from lib.choreo import scan_x as _scan_x, reveal_time as _reveal_time


def build(sc):
    S = {}
    rig.set_world(sc)
    S["floor"] = sets.studio_floor(sc)
    S["scatter"] = tree.scatter_poses()
    S["cards"] = {}
    black_edge = mat.dark_glass("CardEdge", 0.05)
    for n in tree.NODES:
        asp = tree.photo_aspect(n["photo"])
        w = n["w"]
        h = w / asp
        pm = mat.photo_print("print_" + n["id"], f"{PH}/{n['photo']}", rough=0.30, coat=0.55, emit=0.07, exposure=0.9,
                             diffuse=1.0, spec=0.5)
        ob = geo.make_slab("card_" + n["id"], w, h, THICK, min(0.005, w * 0.07), 0.0010, (pm, black_edge, black_edge),
                           seg_corner=8, seg_edge=3)
        S["cards"][n["id"]] = dict(ob=ob, w=w, h=h, mat=pm, rev=pm.node_tree.nodes[pm["reveal_node"]].outputs[0],
                                   emit=pm.node_tree.nodes[pm["bsdf_node"]].inputs["Emission Strength"])
    # reveal times follow the scanner
    S["rev_t"] = {nid: _reveal_time(S["scatter"][nid]["xy"][0]) for nid in S["cards"]}
    # lines (drawn from parent to child) and their pulse
    line_m = mat.emission("Line", (0.90, 0.94, 1.0), 2.0)
    pulse_m = mat.emission("LinePulse", (1.0, 1.0, 1.0), 9.0)
    S["lines"] = {}
    for n in tree.NODES:
        if not n["parent"]:
            continue
        base = geo.make_tube("line_" + n["id"], [(0, 0, 0), (0.1, 0.1, 0)], 0.00042 if n["level"] == 1 else 0.00032, line_m, resolution=12)
        pulse = geo.make_tube("pulse_" + n["id"], [(0, 0, 0), (0.1, 0.1, 0)], 0.00085, pulse_m, resolution=12)
        S["lines"][n["id"]] = dict(base=base, pulse=pulse)
    # labels
    S["labels"] = {}
    lab_m = {}
    for n in tree.NODES:
        if n.get("label"):
            m = mat.emission("label_" + n["id"], (0.86, 0.90, 0.97), 0.0)
            ob = geo.make_text("label_" + n["id"], n["label"], 0.0068 if n["level"] else 0.0085, m, FONT)
            S["labels"][n["id"]] = dict(ob=ob, node=m.node_tree.nodes[m["emit_node"]].inputs["Strength"])
    # lights
    L = {}
    L["top"] = rig.area_light("TOP_softbox", (1.5, 1.0), 1.6, (1.0, 0.985, 0.96), (-0.25, -0.35, 1.4), (0, 0, 0))
    L["scan"] = sets.strip_light(sc, "SCAN_strip", (-0.62, 0.0, 0.45), (-0.62, 0.0, 0.0), (0.05, 1.0), 0.0, (1.0, 0.99, 0.97), end_fade=0.22, edge_soft=0.5, roll=0.0)
    L["rim_l"] = sets.strip_light(sc, "RIM_L", (-0.95, 0.80, 0.30), (0, 0, 0.01), (0.05, 1.0), 90, (0.88, 0.94, 1.0))
    L["rim_r"] = sets.strip_light(sc, "RIM_R", (0.95, 0.75, 0.30), (0, 0, 0.01), (0.05, 1.0), 70, (0.88, 0.94, 1.0))
    L["fill"] = rig.area_light("FILL_cool", (1.4, 1.4), 0.9, (0.55, 0.70, 1.0), (0.4, -1.1, 0.5), (0, 0, 0))
    S["L"] = L
    S["refl"] = [
        sets.reflection_card(sc, "REFL_far", (0.0, 2.2, 0.9), (0, 0.2, 0.0), (3.2, 1.2), 0.30, (0.92, 0.96, 1.0),
                             stops=((0.0, 0.0), (0.4, 0.2), (1.0, 1.0))),
        sets.reflection_card(sc, "REFL_side", (-2.0, 0.2, 0.9), (0, 0.1, 0.0), (2.4, 1.0), 0.18, (1.0, 0.98, 0.95)),
    ]
    S["cam"] = rig.make_camera(sc)
    # ---- camera channels (local spline paths) ----
    c = tree.BY_ID["root"]["xy"]
    S["D"] = dict(
        px=motion.Channel([(0.0, 0.03), (6.5, -0.01)]),
        py=motion.Channel([(0.0, -0.05), (6.5, -0.02)]),
        pz=motion.Channel([(0.0, 1.14), (6.5, 0.99)]),
        tx=motion.Channel([(0.0, 0.02), (6.5, 0.0)]),
        ty=motion.Channel([(0.0, 0.02), (6.5, 0.02)]),
        roll=motion.Channel([(0.0, math.radians(1.5)), (6.5, math.radians(-1.0))]),
    )
    S["E"] = dict(
        px=motion.Channel([(6.5, c[0] + 0.070), (10.0, c[0] + 0.036)]),
        py=motion.Channel([(6.5, c[1] - 0.095), (10.0, c[1] - 0.115)]),
        pz=motion.Channel([(6.5, 0.042), (10.0, 0.034)]),
        tx=motion.Channel([(6.5, c[0] - 0.004), (10.0, c[0] - 0.018)]),
        ty=motion.Channel([(6.5, c[1] + 0.020), (10.0, c[1] + 0.052)]),
        foc=motion.Channel([(6.5, 0.118), (8.3, 0.126), (10.0, 0.150)]),
    )
    S["F"] = dict(
        tx=motion.Channel([(10.0, c[0]), (13.0, c[0] - 0.01), (18.5, 0.0)]),
        ty=motion.Channel([(10.0, c[1] + 0.035), (13.0, c[1] + 0.12), (18.5, 0.055)]),
        dist=motion.Channel([(10.0, 0.30), (14.0, 0.85), (18.5, 1.42)]),
        el=motion.Channel([(10.0, 20.0), (14.0, 40.0), (18.5, 71.0)]),
        az=motion.Channel([(10.0, -14.0), (18.5, 0.0)]),
        lens=motion.Channel([(10.0, 62.0), (18.5, 38.0)]),
        fst=motion.Channel([(10.0, 2.4), (13.0, 3.2), (18.5, 6.0)]),
    )
    return S


# ---------------------------------------------------------------------------------------------------------------
def _pose(nid, T, S):
    n = tree.BY_ID[nid]
    sp = S["scatter"][nid]
    s = motion.ramp(T, START[nid], START[nid] + GLIDE, "soft") if nid != "root" else 1.0
    x = motion.lerp(sp["xy"][0], n["xy"][0], s)
    y = motion.lerp(sp["xy"][1], n["xy"][1], s)
    yaw = motion.lerp(sp["yaw"], n["yaw"], s)
    z = motion.lerp(sp["z"], n["z"], s) + 0.012 * math.sin(math.pi * s) * (nid != "root")
    return (x, y), yaw, z, s


def _edge_point(c, d, yaw_deg, w, h, gap=0.0025):
    """Point on the card's outline (plus gap) where the ray from its centre along direction d leaves it."""
    a = math.radians(yaw_deg)
    ca, sa = math.cos(a), math.sin(a)
    lx = d[0] * ca + d[1] * sa            # world -> card local
    ly = -d[0] * sa + d[1] * ca
    hw, hh = w / 2 + gap, h / 2 + gap
    k = min(hw / abs(lx) if abs(lx) > 1e-9 else 1e9, hh / abs(ly) if abs(ly) > 1e-9 else 1e9)
    px, py = lx * k, ly * k
    return (c[0] + px * ca - py * sa, c[1] + px * sa + py * ca)


def _line_geometry(pid, cid, T, S):
    pc, pyaw, pz, _ = _pose(pid, T, S)
    cc, cyaw, cz, _ = _pose(cid, T, S)
    pw, ph = S["cards"][pid]["w"], S["cards"][pid]["h"]
    cw, ch = S["cards"][cid]["w"], S["cards"][cid]["h"]
    d = (cc[0] - pc[0], cc[1] - pc[1])
    dist = math.hypot(*d) + 1e-9
    dh = (d[0] / dist, d[1] / dist)
    a = _edge_point(pc, dh, pyaw, pw, ph)
    b = _edge_point(cc, (-dh[0], -dh[1]), cyaw, cw, ch)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    up = (0.0, 1.0)
    t0 = np.array([dh[0] * 0.55 + up[0] * 0.65, dh[1] * 0.55 + up[1] * 0.65]); t0 /= np.linalg.norm(t0)
    t1 = np.array([dh[0] * 0.92 + up[0] * 0.22, dh[1] * 0.92 + up[1] * 0.22]); t1 /= np.linalg.norm(t1)
    h0 = L * 0.40
    za, zb = pz + THICK * 0.5 + 0.0006, cz + THICK * 0.5 + 0.0006
    return (a, b, t0 * h0, t1 * h0, za, zb)


def _set_curve(ob, geom):
    a, b, t0, t1, za, zb = geom
    sp = ob.data.splines[0]
    p0, p1 = sp.bezier_points[0], sp.bezier_points[1]
    p0.co = (a[0], a[1], za)
    p0.handle_right = (a[0] + t0[0], a[1] + t0[1], za)
    p0.handle_left = (a[0] - t0[0], a[1] - t0[1], za)
    p1.co = (b[0], b[1], zb)
    p1.handle_left = (b[0] - t1[0], b[1] - t1[1], zb)
    p1.handle_right = (b[0] + t1[0], b[1] + t1[1], zb)


def apply(T, S):
    cam = S["cam"]
    L = S["L"]
    # ---- cards ----
    for nid, c in S["cards"].items():
        (x, y), yaw, z, s = _pose(nid, T, S)
        rv = motion.ramp(T, S["rev_t"][nid] - 0.35, S["rev_t"][nid] + 1.3, "out")
        if nid == "root":
            rv = motion.ramp(T, S["rev_t"][nid] - 0.35, S["rev_t"][nid] + 1.3, "out")
        c["rev"].default_value = rv
        c["emit"].default_value = 0.07 + 0.18 * s * rv
        c["ob"].location = (x, y, z + (1 - rv) * 0.006 + THICK / 2)
        c["ob"].rotation_euler = (0, 0, math.radians(yaw))
    # ---- lines + pulses ----
    for cid, ln in S["lines"].items():
        pid = tree.BY_ID[cid]["parent"]
        geom = _line_geometry(pid, cid, T, S)
        _set_curve(ln["base"], geom)
        _set_curve(ln["pulse"], geom)
        d = motion.ramp(T, LINE_START[cid], LINE_START[cid] + LINE_T, "inout")
        ln["base"].data.bevel_factor_end = d
        # pulse: a short bright segment runs parent -> child once the line is complete
        pu = motion.prog(T, LINE_START[cid] + LINE_T - 0.1, LINE_START[cid] + LINE_T + 1.1)
        pe = motion.ease("inout", pu)
        a0 = max(0.0, pe - 0.16)
        ln["pulse"].data.bevel_factor_start = a0 if 0 < pu < 1 else 1.0
        ln["pulse"].data.bevel_factor_end = pe if 0 < pu < 1 else 1.0
    # ---- labels (settle under the card they name) ----
    for nid, lb in S["labels"].items():
        (x, y), yaw, z, s = _pose(nid, T, S)
        c = S["cards"][nid]
        lb["ob"].location = (x, y - c["h"] / 2 - 0.010, z + THICK + 0.0005)
        lb["ob"].rotation_euler = (0, 0, 0)
        on = motion.ramp(T, START[nid] + GLIDE - 0.5, START[nid] + GLIDE + 0.8, "out") if nid != "root" else motion.ramp(T, 14.0, 15.2, "out")
        lb["node"].default_value = 1.6 * on
    # ---- lights ----
    sx = _scan_x(T)
    L["scan"].location = (sx, 0.0, 0.45)
    L["scan"].rotation_euler = rig.look_rot((sx, 0.0, 0.45), (sx, 0.0, 0.0), roll=0.0)
    sets.set_energy(L, "scan", 26.0 * motion.pulse(T, 0.4, 1.4, 6.6))
    # the low rim strips belong to the Tree (F); they are off for the pile and for the grazing macro
    rim = 1.0 * motion.ramp(T, 11.0, 14.5, "inout")
    sets.set_energy(L, "rim_l", 90.0 * rim)
    sets.set_energy(L, "rim_r", 70.0 * rim)
    # overhead softbox lights the pile (D); it fades out for the grazing macro (E) and returns softly for the Tree (F)
    L["top"].data.energy = 1.6 * motion.ramp(T, 0.2, 6.0, "in") * (1 - motion.ramp(T, 6.4, 6.8, "inout")) + 0.9 * motion.ramp(T, 11.0, 14.0, "inout")
    # ---- camera ----
    if T < SEG["E"][0]:
        D = S["D"]
        rig.set_camera(cam, (D["px"](T), D["py"](T), D["pz"](T)), (D["tx"](T), D["ty"](T), 0.0), 40.0, 4.0, roll=D["roll"](T))
    elif T < SEG["F"][0]:
        E = S["E"]
        rig.set_camera(cam, (E["px"](T), E["py"](T), E["pz"](T)), (E["tx"](T), E["ty"](T), 0.004), 100.0, 2.0, focus=E["foc"](T))
    else:
        F = S["F"]
        el, az, d = math.radians(F["el"](T)), math.radians(F["az"](T)), F["dist"](T)
        tg = Vector((F["tx"](T), F["ty"](T), 0.0))
        pos = tg + Vector((d * math.sin(az) * math.cos(el), -d * math.cos(az) * math.cos(el), d * math.sin(el)))
        rig.set_camera(cam, tuple(pos), tuple(tg), F["lens"](T), F["fst"](T))

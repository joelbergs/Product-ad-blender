"""SHOT H - BRAND. The nine slits of the mark slide in one after another (the brand's own motion rule), lit by a descending
light; the camera settles and holds. Wordmark + line are composited in finish.py from the real brand artwork."""
import math
import numpy as np
import bpy
from mathutils import Vector
from lib import rig, sets, motion, mat, logo
from lib.anim import K

NAME = "H"
DURATION = 6.0
MARK_H = 0.15                        # metres, height of the 3D mark
Z0 = 0.050                           # bottom of the mark above the obsidian
DEPTH = 0.010
CENTER = (0.0, 0.0, Z0 + MARK_H / 2)
STEP = 0.17                          # seconds between slits
T0 = 0.9


def build(sc):
    S = {}
    rig.set_world(sc)
    S["floor"] = sets.studio_floor(sc)
    polys, (mw, mh) = logo.polygons()
    sc_ = MARK_H / mh
    ceramic = mat.white_ceramic()
    bars = []
    for i, poly in enumerate(polys):
        cu = bpy.data.curves.new(f"bar{i}", "CURVE")
        cu.dimensions = "2D"
        sp = cu.splines.new("POLY")
        sp.points.add(len(poly) - 1)
        for pt, (x, y) in zip(sp.points, poly):
            pt.co = (x * sc_, -y * sc_, 0.0, 1.0)          # svg y is down
        sp.use_cyclic_u = True
        cu.extrude = DEPTH / 2
        cu.bevel_depth = 0.0009
        cu.bevel_resolution = 2
        cu.fill_mode = "BOTH"
        cu.materials.append(ceramic)
        ob = bpy.data.objects.new(f"bar{i}", cu)
        sc.collection.objects.link(ob)
        ob.rotation_euler = (math.radians(90), 0, 0)         # stand upright facing -Y
        bars.append(ob)
    S["bars"] = bars
    S["mw"], S["mh"], S["scale"] = mw, mh, sc_
    S["L"] = sets.hero_lights(sc, CENTER)
    S["cards"] = [sets.reflection_card(sc, "REFL_card_warm", (-1.5, -1.9, 0.55), (0, -0.1, 0.2), (2.4, 1.1), 0.30),
                  sets.reflection_card(sc, "REFL_card_cool", (1.7, -1.2, 0.65), (0, -0.1, 0.2), (1.6, 0.9), 0.12, (0.78, 0.88, 1.0),
                                       stops=((0.0, 1.0), (0.5, 0.0), (1.0, 0.0)))]
    S["cam"] = rig.make_camera(sc)
    lens = 85.0
    S["lens"] = lens
    S["cam"].data.shift_y = -0.0578                      # the mark sits in the upper half: the wordmark goes below (brand's stacked lockup)
    S["rad"] = motion.Channel([(0.0, sets.dist_for(MARK_H, lens, 0.46)), (3.7, sets.dist_for(MARK_H, lens, 0.344)), (DURATION, sets.dist_for(MARK_H, lens, 0.344))])
    S["az"] = motion.Channel([(0.0, -16.0), (3.7, 0.0), (DURATION, 0.0)])
    S["el"] = motion.Channel([(0.0, 3.0), (3.7, 1.0), (DURATION, 1.0)])
    return S


def apply(t, S):
    az = math.radians(S["az"](t)); el = math.radians(S["el"](t)); r = S["rad"](t)
    c = Vector(CENTER)
    pos = c + Vector((r * math.sin(az) * math.cos(el), -r * math.cos(az) * math.cos(el), r * math.sin(el)))
    cam = S["cam"]
    rig.set_camera(cam, tuple(pos), CENTER, S["lens"], 5.6)
    K.loc(cam, tuple(cam.location)); K.rot(cam, tuple(cam.rotation_euler)); K.set(cam.data.dof, "focus_distance", cam.data.dof.focus_distance)
    polys, _ = logo.polygons()
    sc_ = S["scale"]
    for i, ob in enumerate(S["bars"]):
        cx = sum(p[0] for p in polys[i]) / len(polys[i])
        cy = sum(p[1] for p in polys[i]) / len(polys[i])
        ti = T0 + i * STEP
        u = motion.ramp(t, ti, ti + 1.1, "out")
        slide = (1 - u) * -0.040                               # slits slide in from the left, ease-out
        ob.location = (slide, DEPTH / 2 * 0, CENTER[2])
        ob.scale = (1, 1, 1 if u > 0.003 else 0.0001)
        K.loc(ob, ob.location); K.scl(ob, tuple(ob.scale))
    L = S["L"]
    sets.set_energy(L, "sweep", 0.0)
    for key, (t0, t1, base) in dict(rim_l=(0.2, 1.8, 170), rim_r=(0.6, 2.2, 130), top=(0.8, 2.4, 3), key=(0.8, 2.4, 1.8)).items():
        sets.set_energy(L, key, base * motion.ramp(t, t0, t1, "in"))
    ceramic = S["bars"][0].data.materials[0]
    K.sock(ceramic.node_tree.nodes[ceramic["bsdf_node"]].inputs["Emission Strength"], 0.30)


def receivers(S):
    return [S["floor"]] + S["bars"]

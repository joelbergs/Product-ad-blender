"""SHOT G - THE REAL APP. A bezel-less glass device carries genuine screens recorded from the app (Tree, then sharing)."""
import math
import numpy as np
from mathutils import Vector
from lib import rig, sets, motion
from lib.anim import K

NAME = "G"
DURATION = 4.5
SCREENS = "/home/user/Product-ad-blender/Lacrydia_Film/assets/lacrydia/screens"
CENTER = (0.0, 0.0, 0.045 + sets.DH / 2)


def build(sc):
    S = {}
    rig.set_world(sc)
    S["floor"] = sets.studio_floor(sc, pools=((0.0, 0.0, 0.25, 0.60),))
    S["dev"] = sets.device_panel(sc, [f"{SCREENS}/2.png", f"{SCREENS}/4.png"])
    S["L"] = sets.hero_lights(sc, CENTER)
    d = S["dev"]
    S["cards"] = [sets.reflection_card(sc, "REFL_card_warm", (-1.5, -1.9, 0.55), (0, -0.1, 0.2), (2.4, 1.1), 0.30),
                  sets.reflection_card(sc, "REFL_card_cool", (1.7, -1.2, 0.65), (0, -0.1, 0.2), (1.6, 0.9), 0.12, (0.78, 0.88, 1.0),
                                       stops=((0.0, 1.0), (0.5, 0.0), (1.0, 0.0)))]
    S["sheen"] = sets.sheen_flag(sc, peak=0.28, center=CENTER, z=0.05, height=0.22)
    S["cam"] = rig.make_camera(sc)
    lens = 90.0
    S["az"] = motion.Channel([(0.0, -34.0), (DURATION, -3.0)])
    S["el"] = motion.Channel([(0.0, 3.0), (DURATION, 1.5)])
    S["rad"] = motion.Channel([(0.0, sets.dist_for(sets.DH, lens, 0.74)), (DURATION, sets.dist_for(sets.DH, lens, 0.92))])
    S["lens"] = lens
    return S


def apply(t, S):
    az = math.radians(S["az"](t)); el = math.radians(S["el"](t)); r = S["rad"](t)
    c = Vector(CENTER)
    pos = c + Vector((r * math.sin(az) * math.cos(el), -r * math.cos(az) * math.cos(el), r * math.sin(el)))
    cam = S["cam"]
    rig.set_camera(cam, tuple(pos), CENTER, S["lens"], 4.5)
    K.loc(cam, tuple(cam.location)); K.rot(cam, tuple(cam.rotation_euler)); K.set(cam.data.dof, "focus_distance", cam.data.dof.focus_distance)
    d = S["dev"]
    (_, e0), (_, e1) = d["screens"]
    # screen wakes (0.5-1.7 s), the Tree stays, then crossfades to the sharing screen (2.7-3.5 s)
    wake = motion.ramp(t, 0.5, 1.8, "out")
    k = motion.ramp(t, 2.7, 3.6, "inout")
    K.sock(e0, wake * (1 - k)); K.sock(e1, wake * k)
    L = S["L"]
    sets.set_energy(L, "sweep", 0.0)
    for key, (t0, t1, base) in dict(rim_l=(0.0, 1.2, 160), rim_r=(0.4, 1.6, 120), top=(0.6, 2.0, 3), key=(0.6, 2.0, 1.4)).items():
        sets.set_energy(L, key, base * motion.ramp(t, t0, t1, "in"))


def receivers(S):
    return [S["floor"], S["dev"]["front"], S["dev"]["back"]]

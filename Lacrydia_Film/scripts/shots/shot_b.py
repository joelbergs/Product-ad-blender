"""SHOT B - three-quarter orbit around the glass photograph panel."""
import math
import numpy as np
from mathutils import Vector
from lib import rig, sets, motion
from lib.anim import K

NAME = "B"
DURATION = 6.5
CENTER = (0.0, 0.0, 0.145)


def build(sc):
    S = {}
    rig.set_world(sc)
    S["floor"] = sets.studio_floor(sc)
    S["hero"] = sets.hero_panel(sc, "p16.jpg")
    S["L"] = sets.hero_lights(sc, CENTER)
    S["sheen"] = sets.sheen_flag(sc, peak=3.0)
    S["cam"] = rig.make_camera(sc)
    S["az"] = motion.Channel([(0, -54), (DURATION, 28)])             # degrees, camera azimuth around the panel
    S["el"] = motion.Channel([(0, 4), (2.8, 8), (DURATION, 5)])
    S["lens"] = motion.Channel([(0, 85), (DURATION, 110)])
    S["fill"] = motion.Channel([(0, 0.44), (DURATION, 0.66)])           # how much of the frame height the panel fills
    S["sweep"] = motion.Channel([(0.0, -0.60), (3.0, 0.60)])            # x of the sweep strip (behind the panel)
    return S


def apply(t, S):
    az = math.radians(S["az"](t)); el = math.radians(S["el"](t)); r = sets.dist_for(sets.H, S["lens"](t), S["fill"](t))
    c = Vector(CENTER)
    pos = c + Vector((r * math.sin(az) * math.cos(el), -r * math.cos(az) * math.cos(el), r * math.sin(el)))
    cam = S["cam"]
    rig.set_camera(cam, tuple(pos), CENTER, S["lens"](t), 4.0)
    L = S["L"]
    sp = (S["sweep"](t), 0.45, 0.50)
    L["sweep"].location = sp
    L["sweep"].rotation_euler = rig.look_rot(sp, CENTER)
    K.loc(L["sweep"], sp); K.rot(L["sweep"], L["sweep"].rotation_euler)
    sets.set_energy(L, "sweep", 900 * motion.pulse(t, 0.0, 1.5, 3.2))
    K.sock(sets.reveal_node(S["hero"]), motion.ramp(t, 0.5, 2.8, "out"))
    K.loc(cam, tuple(cam.location)); K.rot(cam, tuple(cam.rotation_euler))


def receivers(S):
    return [S["floor"], S["hero"]["glass"], S["hero"]["back"]]

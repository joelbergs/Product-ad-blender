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
    S["card_w"] = sets.reflection_card(sc, "REFL_card_warm", (-1.5, -1.9, 0.55), (0, -0.1, 0.2), (2.4, 1.1), 0.9)
    S["card_c"] = sets.reflection_card(sc, "REFL_card_cool", (1.7, -1.2, 0.65), (0, -0.1, 0.2), (1.6, 0.9), 0.35, (0.78, 0.88, 1.0), stops=((0.0, 1.0), (0.5, 0.0), (1.0, 0.0)))
    S["cam"] = rig.make_camera(sc)
    S["az"] = motion.Channel([(0, -48), (DURATION, 22)])            # degrees, camera azimuth around the panel
    S["el"] = motion.Channel([(0, 5), (3.2, 9), (DURATION, 6)])
    S["rad"] = motion.Channel([(0, 1.75), (DURATION, 1.45)])
    S["lens"] = motion.Channel([(0, 85), (DURATION, 100)])
    S["sweep"] = motion.Channel([(0.0, -0.55), (2.6, 0.45)])       # x of the sweep strip
    return S


def apply(t, S):
    az = math.radians(S["az"](t)); el = math.radians(S["el"](t)); r = S["rad"](t)
    c = Vector(CENTER)
    pos = c + Vector((r * math.sin(az) * math.cos(el), -r * math.cos(az) * math.cos(el), r * math.sin(el)))
    cam = S["cam"]
    rig.set_camera(cam, tuple(pos), CENTER, S["lens"](t), 4.0)
    L = S["L"]
    K.loc(L["sweep"], (S["sweep"](t), -0.30, 0.30))
    L["sweep"].rotation_euler = rig.look_rot(L["sweep"].location, CENTER)
    K.rot(L["sweep"], L["sweep"].rotation_euler)
    sets.set_energy(L, "sweep", 380 * motion.pulse(t, 0.2, 1.4, 3.0))
    K.sock(sets.reveal_node(S["hero"]), motion.ramp(t, 0.8, 3.2, "out"))
    K.loc(cam, tuple(cam.location)); K.rot(cam, tuple(cam.rotation_euler))


def receivers(S):
    return [S["floor"], S["hero"]["glass"], S["hero"]["back"]]

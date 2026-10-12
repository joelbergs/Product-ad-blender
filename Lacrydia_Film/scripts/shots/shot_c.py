"""SHOT C - LOW ANGLE HERO. The camera sits just above the obsidian and looks up at the panel: monumental, rim-lit.
Two more photographs wake in the depth behind it; focus travels from the first memory to the next."""
import math
import numpy as np
from mathutils import Vector
from lib import rig, sets, motion
from lib.anim import K

NAME = "C"
DURATION = 4.0
CENTER = (0.0, 0.0, 0.145)


def build(sc):
    S = {}
    rig.set_world(sc)
    S["floor"] = sets.studio_floor(sc, pools=((0.0, 0.0, 0.32, 0.70), (0.26, 0.36, 0.25, 0.55), (-0.36, 0.86, 0.25, 0.55)))
    S["hero"] = sets.hero_panel(sc, "p16.jpg", name="Hero")
    S["p2"] = sets.hero_panel(sc, "p9.jpg", name="P2", w=0.12, h=0.16, z0=0.045)
    S["p3"] = sets.hero_panel(sc, "p17.jpg", name="P3", w=0.12, h=0.16, z0=0.045)
    S["hero"]["root"].rotation_euler = (math.radians(90), 0, math.radians(-7))
    S["p2"]["root"].location = (0.26, 0.36, 0.045 + 0.08)
    S["p2"]["root"].rotation_euler = (math.radians(90), 0, math.radians(-20))
    S["p3"]["root"].location = (-0.36, 0.86, 0.045 + 0.08)
    S["p3"]["root"].rotation_euler = (math.radians(90), 0, math.radians(18))
    S["L"] = sets.hero_lights(sc, CENTER)
    S["cards"] = [sets.reflection_card(sc, "REFL_card_warm", (-1.5, -1.9, 0.55), (0, -0.1, 0.2), (2.4, 1.1), 0.35),
                  sets.reflection_card(sc, "REFL_card_cool", (1.7, -1.2, 0.65), (0, -0.1, 0.2), (1.6, 0.9), 0.15, (0.78, 0.88, 1.0),
                                       stops=((0.0, 1.0), (0.5, 0.0), (1.0, 0.0)))]
    S["cam"] = rig.make_camera(sc)
    S["cx"] = motion.Channel([(0.0, -0.17), (DURATION, 0.10)])
    S["cy"] = motion.Channel([(0.0, -0.34), (DURATION, -0.40)])
    S["cz"] = motion.Channel([(0.0, 0.026), (DURATION, 0.050)])
    S["tx"] = motion.Channel([(0.0, 0.0), (DURATION, 0.09)])
    S["tz"] = motion.Channel([(0.0, 0.165), (DURATION, 0.150)])
    S["foc"] = motion.Channel([(0.0, 0.36), (1.7, 0.36), (3.2, 0.95), (DURATION, 0.95)])
    return S


def apply(t, S):
    cam = S["cam"]
    pos = (S["cx"](t), S["cy"](t), S["cz"](t))
    rig.set_camera(cam, pos, (S["tx"](t), 0.0, S["tz"](t)), 24.0, 2.8, focus=S["foc"](t))
    K.loc(cam, tuple(cam.location)); K.rot(cam, tuple(cam.rotation_euler))
    K.set(cam.data.dof, "focus_distance", S["foc"](t))
    L = S["L"]
    # sweep strip crosses behind-left → right once (it outlines the panel's silhouette)
    sx = -0.55 + 1.1 * motion.ease("inout", motion.prog(t, 0.0, 3.2))
    L["sweep"].location = (sx, 0.30, 0.40)
    L["sweep"].rotation_euler = rig.look_rot((sx, 0.30, 0.40), CENTER)
    K.loc(L["sweep"], (sx, 0.30, 0.40)); K.rot(L["sweep"], tuple(L["sweep"].rotation_euler))
    sets.set_energy(L, "sweep", 700 * motion.pulse(t, 0.0, 1.2, 3.6))
    # photographs: hero already awake (it continues from shot B); the others wake in depth
    K.sock(sets.reveal_node(S["hero"]), 1.0)
    K.sock(sets.reveal_node(S["p2"]), motion.ramp(t, 1.0, 2.4, "out"))
    K.sock(sets.reveal_node(S["p3"]), motion.ramp(t, 1.9, 3.4, "out"))


def receivers(S):
    return [S["floor"]] + [P[k] for P in (S["hero"], S["p2"], S["p3"]) for k in ("glass", "back")]

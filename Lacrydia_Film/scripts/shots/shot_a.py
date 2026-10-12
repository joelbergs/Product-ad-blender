"""SHOT A - EXTREME MACRO. A light line travels down the polished bevel of the glass panel; the engraved mark emerges.
Camera: 100 mm macro, f/2.8, slides down the left edge and settles on the lower-left corner."""
import math
import numpy as np
from mathutils import Vector
from lib import rig, sets, motion
from lib.anim import K

NAME = "A"
DURATION = 5.0
PANEL_C = (0.0, 0.0, 0.045 + 0.10)         # panel centre (matches sets.FLOAT + H/2)
EDGE_X = -0.075                            # left edge of the panel
Z_TOP, Z_BOT = 0.20, 0.074                 # camera travel along the edge (world z)


def build(sc):
    S = {}
    rig.set_world(sc)
    S["floor"] = sets.studio_floor(sc)
    S["hero"] = sets.hero_panel(sc, "p16.jpg", mark_mask=sets.mark_mask_path())
    S["L"] = sets.hero_lights(sc, PANEL_C)
    S["cards"] = [sets.reflection_card(sc, "REFL_card_warm", (-1.5, -1.9, 0.55), (0, -0.1, 0.2), (2.4, 1.1), 0.03), sets.reflection_card(sc, "REFL_card_cool", (1.7, -1.2, 0.65), (0, -0.1, 0.2), (1.6, 0.9), 0.02, (0.78, 0.88, 1.0), stops=((0.0, 1.0), (0.5, 0.0), (1.0, 0.0)))]
    S["cam"] = rig.make_camera(sc)
    # camera: slides down the edge (clamped spline = soft start, soft landing), slight pull-back at the end
    S["cz"] = motion.Channel([(0.0, Z_TOP), (1.2, Z_TOP - 0.008), (3.5, Z_BOT + 0.016), (DURATION, Z_BOT)])
    S["cx"] = motion.Channel([(0.0, -0.205), (DURATION, -0.185)])
    S["cy"] = motion.Channel([(0.0, -0.255), (DURATION, -0.235)])
    S["tx"] = motion.Channel([(0.0, EDGE_X + 0.003), (DURATION, EDGE_X + 0.032)])
    S["sweep"] = motion.Channel([(0.7, 0.26), (3.8, 0.06)])       # z of the horizontal sweep strip: travels down the edge
    return S


def apply(t, S):
    cam = S["cam"]
    pos = (S["cx"](t), S["cy"](t), S["cz"](t))
    tgt = (S["tx"](t), -0.005, S["cz"](t) - 0.004)
    rig.set_camera(cam, pos, tgt, 100.0, 2.8)
    K.loc(cam, tuple(cam.location)); K.rot(cam, tuple(cam.rotation_euler))
    L = S["L"]
    # everything dark at first; rims fade up very slowly (light is the character)
    for k, (t0, t1, base) in dict(rim_l=(1.2, 4.6, 170), rim_r=(2.0, 5.0, 130), top=(2.2, 5.0, 3), key=(2.4, 5.0, 1.2), fill=(0, 1, 0.25)).items():
        sets.set_energy(L, k, base * motion.ramp(t, t0, t1, "in"))
    # sweep: a horizontal strip descends past the edge; brightness has its own envelope (it is the hero)
    sw = L["sweep"]
    sw.rotation_euler = rig.look_rot((-0.35, -0.25, S["sweep"](t)), (EDGE_X, 0, S["sweep"](t) - 0.01), roll=math.radians(90))
    K.loc(sw, (-0.35, -0.25, S["sweep"](t))); K.rot(sw, tuple(sw.rotation_euler))
    sets.set_energy(L, "sweep", 700 * motion.pulse(t, 0.6, 2.0, 4.2))
    # the engraving fades in after the light has passed it
    amt = S["hero"]["glass_mat"].node_tree.nodes[S["hero"]["glass_mat"]["amount_node"]].inputs[1]
    K.sock(amt, 1.0)
    pm = S["hero"]["photo_mat"].node_tree.nodes[S["hero"]["photo_mat"]["bsdf_node"]].inputs["Emission Strength"]
    K.sock(pm, 0.0)       # the photograph stays dark in the macro (it wakes in shot B)


def receivers(S):
    return [S["floor"], S["hero"]["glass"], S["hero"]["back"]]

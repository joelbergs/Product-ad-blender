"""Timing of the whole film as pure data: the single source of truth for both the 3D animation and the sound design.
All times in seconds. 'T' = local time inside a shot module; film time = shot start + T (see config/film.json)."""
import json
import os
from . import motion, tree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILM = json.load(open(os.path.join(ROOT, "config", "film.json")))
START_OF = {s["id"]: s["start"] for s in FILM["shots"]}

# ---- TABLE (D/E/F) ---------------------------------------------------------------------------------------------
SCAN = (0.8, 6.0, -0.62, 0.62)               # scanner: t0, t1, x0, x1
GLIDE = 2.4
START = dict(root=0, travel=10.5, nature=12.0, friends=13.5, cars=15.0,
             t1=16.0, t2=16.35, t3=16.7, n1=16.9, n2=17.25, n3=17.6, f1=17.0, f2=17.35, f3=17.7, c1=17.9, c2=18.05)
LINE_T = 1.7
LINE_START = dict(travel=8.4)
for _k in tree.BY_ID:
    if _k != "root":
        LINE_START.setdefault(_k, START[_k] + 0.3)
TABLE_FILM0 = START_OF["D"]                   # film time at which TABLE local T=0


def scan_x(T):
    t0, t1, x0, x1 = SCAN
    return x0 + (x1 - x0) * motion.ease("inout", motion.prog(T, t0, t1))


def reveal_time(x):
    t0, t1, x0, x1 = SCAN
    u = (x - x0) / (x1 - x0)
    lo, hi = 0.0, 1.0
    for _ in range(30):
        m = 0.5 * (lo + hi)
        if motion.ease("inout", m) < u:
            lo = m
        else:
            hi = m
    return t0 + (t1 - t0) * 0.5 * (lo + hi)


def card_events():
    """[(film_t, id, x_position)] when the scanner reveals each photograph (D)."""
    sp = tree.scatter_poses()
    return sorted((TABLE_FILM0 + reveal_time(sp[n["id"]]["xy"][0]), n["id"], sp[n["id"]]["xy"][0]) for n in tree.NODES)


def line_events():
    """[(film_t_start, film_t_end, child_id, level)] connection line draw windows (E/F)."""
    out = []
    for n in tree.NODES:
        if n["parent"]:
            t0 = TABLE_FILM0 + LINE_START[n["id"]]
            out.append((t0, t0 + LINE_T, n["id"], n["level"]))
    return sorted(out)


def glide_events():
    return sorted((TABLE_FILM0 + START[n["id"]], n["id"]) for n in tree.NODES if n["id"] != "root")


# ---- other shots (local times from the shot modules) ---------------------------------------------------------------
H_T0, H_STEP = 0.9, 0.17                      # logo slits (shot H)
B_WAKE = (0.5, 2.8)                           # hero photo wakes (B)
C_WAKE = dict(p2=(1.0, 2.4), p3=(1.9, 3.4))   # panels wake in depth (C)
G_WAKE, G_SWAP = (0.5, 1.8), (2.7, 3.6)       # device screen wakes / crossfades to the sharing screen (G)
A_SWEEP = (0.6, 2.0, 4.2)                     # sweep light envelope in A (rise, peak, end)

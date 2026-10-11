"""All motion of the film as smooth curves of time (seconds). One source of truth for the 3D scene.

Coordinates: 1 unit = 1 cm. Phone: front faces -Y at rotZ=0 (rotZ is degrees, positive = counter-clockwise from above).
Camera orbits a look-at target: azimuth 0 = camera in front of the phone (at -Y); positive azimuth moves it towards +X.
Facing maths (used when tuning): front normal azimuth = rotZ, back normal azimuth = rotZ-180; a face is visible when
its normal is within 90 deg of the camera azimuth.
"""
import numpy as np
from paths import cfg

C = cfg()
FPS = C["fps"]
DURATION = C["duration_s"]
N_FRAMES = int(round(FPS * DURATION))          # 900 (frames numbered 1..900, frame f is at t=(f-1)/FPS)
END = DURATION


def frame_to_t(frame):
    return (frame - 1) / FPS


def t_to_frame(t):
    return int(round(t * FPS)) + 1


def curve(keys):
    """Monotone cubic (PCHIP) through (t, v) keys with zero slope at both ends: smooth, no overshoot."""
    t = np.array([k[0] for k in keys], float)
    v = np.array([k[1] for k in keys], float)
    h = np.diff(t)
    d = np.diff(v) / h
    m = np.zeros(len(t))
    for i in range(1, len(t) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= t[0]:
            return float(v[0])
        if x >= t[-1]:
            return float(v[-1])
        i = int(np.searchsorted(t, x)) - 1
        s = (x - t[i]) / h[i]
        return float((2 * s**3 - 3 * s**2 + 1) * v[i] + (s**3 - 2 * s**2 + s) * h[i] * m[i]
                     + (-2 * s**3 + 3 * s**2) * v[i + 1] + (s**3 - s**2) * h[i] * m[i + 1])
    return f


E = END
# ------------------------------------------------------------------------------------------------ HERO (0 - 7.5 s, 3D phone)
# Beat grid 96 BPM: 1 beat = 0.625 s, 1 bar = 2.5 s.  After HERO_END the camera holds the straight-on front view; the film continues in
# 2D compositing (scripts/compose_film.py) with the real app recordings, handed over at HERO_END.
HERO_END = 7.5
phone_z = curve([(0, -1.6), (2.5, -0.4), (4.4, 0.0), (E, 0.0)])
phone_rotz = curve([(0, 196), (1.25, 190), (2.5, 181), (3.75, 150), (5.0, 84), (6.25, 14), (7.0, 2), (7.5, 0), (E, 0)])


def phone_bob(t):
    """Very small float motion while the phone turns; settles to zero at the hand-over so the 2D panel matches exactly."""
    k = np.clip((t - 1.5) / 2.0, 0, 1) * np.clip((7.0 - t) / 1.5, 0, 1)
    return 0.10 * k * np.sin(2 * np.pi * t / 3.1) + 0.04 * k * np.sin(2 * np.pi * t / 1.9 + 1.0)


# ------------------------------------------------------------------------------------------------ camera
cam_az = curve([(0, -24), (1.25, -20), (2.5, -14), (3.75, 6), (5.0, 18), (6.25, 7), (7.0, 1), (7.5, 0), (E, 0)])
cam_el = curve([(0, 3), (2.5, 6), (3.75, 12), (5.0, 15), (6.25, 6), (7.5, 0), (E, 0)])
cam_dist = curve([(0, 40), (2.0, 44), (3.0, 58), (3.75, 72), (5.0, 78), (6.25, 72), (7.5, 66), (E, 66)])
cam_focal = curve([(0, 105), (2.5, 100), (3.75, 95), (5.0, 90), (6.25, 85), (7.5, 85), (E, 85)])
cam_fstop = curve([(0, 3.2), (2.5, 4.0), (5.0, 3.2), (6.5, 5.6), (7.5, 8.0), (E, 8.0)])
tgt_x = curve([(0, 1.4), (2.5, 0.8), (3.75, 0.0), (5.0, -0.6), (6.25, 0.0), (E, 0)])
tgt_z = curve([(0, 3.6), (2.5, 3.0), (3.75, 1.8), (5.0, 1.0), (6.25, 0.4), (7.5, 0.0), (E, 0)])
cam_shift_x = curve([(0, 0), (E, 0)])

# ------------------------------------------------------------------------------------------------ screen
_wake = 5.0
screen_gain = curve([(_wake - 0.01, 0.0), (_wake + 0.9, 1.0), (E, 1.0)])

# ------------------------------------------------------------------------------------------------ lights (gain 0..1)
light_gain = {
    "LGT_Edge":      curve([(0, 0), (0.8, 0), (2.0, 0.5), (4.0, 0.5), (6, 0.25), (E, 0.2)]),
    "LGT_StripL":    curve([(0, 0), (2.4, 0), (3.8, 0.8), (6, 1.0), (E, 0.8)]),
    "LGT_StripR":    curve([(0, 0), (3.0, 0), (4.6, 0.8), (6.5, 1.0), (E, 0.8)]),
    "LGT_Top":       curve([(0, 0), (2.8, 0), (4.5, 0.6), (6.5, 1.0), (E, 0.9)]),
    "LGT_Key":       curve([(0, 0), (3.2, 0), (5.0, 0.6), (7.0, 1.0), (E, 0.9)]),
    "LGT_BackRimL":  curve([(0, 0), (0.4, 0), (1.6, 0.55), (4.0, 0.7), (6.0, 0.4), (E, 0.3)]),
    "LGT_BackRimR":  curve([(0, 0), (0.6, 0), (1.9, 0.55), (4.0, 0.7), (6.0, 0.4), (E, 0.3)]),
    "LGT_Sweep":     curve([(1.0, 0), (1.5, 0.45), (2.2, 0.45), (2.8, 0), (E, 0)]),
    "LGT_Amber":     curve([(0, 0), (E, 0)]),
    "LGT_Fill":      curve([(0, 0), (3, 0.05), (E, 0.08)]),
}
sweep_x = curve([(1.0, -55), (2.8, 55)])      # a light strip travels across the phone's back, picking out the logo and the glass

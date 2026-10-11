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
# ------------------------------------------------------------------------------------------------ HERO (0 - 10 s, 3D phone, four shots)
# Beat grid 96 BPM: 1 beat = 0.625 s, 1 bar = 2.5 s. Shots change on bar lines:
#   A 0.0-2.5  EDGE   : grazing macro along the burgundy edge of the camera plateau, a strip of light travels with the camera
#   B 2.5-5.0  LENSES : low sweep across the three lenses, rack focus, slight dutch roll
#   C 5.0-7.5  REVEAL : fast dolly-out and rise: logo, then the whole back, light sweep across the glass
#   D 7.5-10.0 TURN   : the phone spins to its front under a low hero angle, the display wakes, camera settles straight-on (hand-over)
# After HERO_END the camera holds the straight-on front view; the film continues in 2D compositing with the real app recordings.
HERO_END = 10.0
phone_z = curve([(0, -0.6), (5.0, 0.0), (7.5, 0.3), (9.0, 0.5), (10.0, 0.0), (E, 0.0)])
phone_rotz = curve([(0, 184), (2.5, 184), (5.0, 182), (7.0, 178), (7.9, 164), (8.7, 110), (9.4, 34), (9.85, 4), (10.0, 0), (E, 0)])


def phone_bob(t):
    """Very small float motion; settles to zero at the hand-over so the 2D panel matches exactly."""
    k = np.clip((t - 4.0) / 2.0, 0, 1) * np.clip((9.4 - t) / 1.4, 0, 1)
    return 0.12 * k * np.sin(2 * np.pi * t / 3.1) + 0.05 * k * np.sin(2 * np.pi * t / 1.9 + 1.0)


# ------------------------------------------------------------------------------------------------ camera (orbit around a moving target; roll in degrees)
cam_az = curve([(0, -62), (2.5, -48), (2.5001, -34), (3.6, -8), (5.0, 22), (5.8, 24), (7.5, -28), (8.6, -20), (9.3, 8), (10.0, 0), (E, 0)])
cam_el = curve([(0, 5), (2.5, 3), (2.5001, 16), (3.8, 5), (5.0, -6), (5.6, 8), (7.5, 24), (8.6, -9), (9.3, -3), (10.0, 0), (E, 0)])
cam_dist = curve([(0, 9.5), (2.5, 10.5), (2.5001, 13.0), (5.0, 9.0), (5.9, 22), (6.7, 44), (7.5, 66), (8.6, 74), (9.4, 70), (10.0, 66), (E, 66)])
cam_focal = curve([(0, 105), (2.5, 105), (5.0, 100), (6.2, 80), (7.5, 62), (8.6, 70), (10.0, 85), (E, 85)])
cam_fstop = curve([(0, 1.8), (2.5, 2.0), (5.0, 1.8), (6.4, 3.2), (7.5, 5.6), (10.0, 8.0), (E, 8.0)])
cam_roll = curve([(0, 3.0), (2.5, -2.0), (2.5001, -6.0), (4.0, 2.0), (5.0, 4.0), (6.0, 0.0), (7.5, -3.0), (8.6, 3.0), (9.5, 0.0), (10.0, 0), (E, 0)])
focus_off = curve([(0, 0.0), (2.5, 0.0), (2.5001, -1.6), (3.5, -1.6), (4.3, 1.6), (5.0, 0.4), (6.0, 0.0), (E, 0.0)])   # rack focus (cm)
tgt_x = curve([(0, 0.4), (2.5, 3.0), (2.5001, -2.0), (5.0, -2.1), (6.0, -1.3), (7.5, 0.0), (E, 0)])
tgt_y = curve([(0, -0.55), (2.5, -0.55), (2.5001, -0.7), (5.0, -0.7), (6.5, -0.2), (7.5, 0.0), (E, 0)])
tgt_z = curve([(0, 6.5), (2.5, 6.3), (2.5001, 5.1), (5.0, 5.1), (6.0, 3.6), (7.5, 0.5), (9.0, 0.2), (10.0, 0.0), (E, 0)])
cam_shift_x = curve([(0, 0), (E, 0)])

# ------------------------------------------------------------------------------------------------ screen
_wake = 8.3
screen_gain = curve([(_wake - 0.01, 0.0), (_wake + 1.1, 1.0), (E, 1.0)])

# ------------------------------------------------------------------------------------------------ lights (gain 0..1)
light_gain = {
    "LGT_Edge":      curve([(0, 0), (0.4, 0.14), (1.6, 0.30), (2.4, 0.22), (3.2, 0.2), (5.0, 0.3), (7.5, 0.5), (9.0, 0.3), (E, 0.2)]),
    "LGT_StripL":    curve([(0, 0), (2.5, 0), (3.2, 0.6), (5.0, 0.4), (7.0, 0.7), (8.4, 1.0), (E, 0.8)]),
    "LGT_StripR":    curve([(0, 0), (4.4, 0), (5.2, 0.7), (7.5, 0.8), (E, 0.8)]),
    "LGT_Top":       curve([(0, 0), (5.0, 0), (6.5, 0.5), (8.0, 0.8), (E, 0.9)]),
    "LGT_Key":       curve([(0, 0), (6.0, 0), (7.6, 0.5), (9.0, 1.0), (E, 0.9)]),
    "LGT_BackRimL":  curve([(0, 0), (0.5, 0.15), (2.5, 0.28), (5.0, 0.8), (7.0, 0.7), (8.6, 0.4), (E, 0.3)]),
    "LGT_BackRimR":  curve([(0, 0), (2.5, 0.0), (3.0, 0.8), (5.0, 0.7), (7.0, 0.6), (8.6, 0.4), (E, 0.3)]),
    "LGT_Sweep":     curve([(0.0, 0.0), (0.5, 0.45), (2.3, 0.55), (2.6, 0.0), (5.9, 0.0), (6.2, 0.55), (7.3, 0.55), (7.8, 0.0), (E, 0)]),
    "LGT_Amber":     curve([(0, 0), (2.6, 0.0), (3.4, 0.9), (4.8, 0.9), (5.4, 0.0), (E, 0)]),
    "LGT_Fill":      curve([(0, 0), (6, 0.04), (E, 0.08)]),
}
sweep_x = curve([(0.0, -36), (2.4, 30), (5.9, -50), (7.8, 50), (E, 50)])   # the strip rides with / across the phone

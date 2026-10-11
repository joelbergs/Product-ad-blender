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
# ------------------------------------------------------------------------------------------------ phone
phone_z = curve([(0, -1.5), (3.0, -1.5), (7.0, 0.0), (22, 0.0), (25, 1.2), (E, 1.2)])
phone_rotz = curve([(0, 90), (3, 100), (7.0, 178), (8.6, 172), (10.0, 112), (11.4, 40), (12.8, 6), (13.8, 0),
                    (17, 2), (19, -3), (22, 0), (25, -34), (28, -34), (E, -34)])


def phone_bob(t):
    """Very small float motion once the phone has settled (keeps it from feeling nailed in space)."""
    k = np.clip((t - 5.0) / 3.0, 0, 1)
    return 0.10 * k * np.sin(2 * np.pi * t / 5.3) + 0.04 * k * np.sin(2 * np.pi * t / 2.9 + 1.0)


# ------------------------------------------------------------------------------------------------ camera
cam_az = curve([(0, -22), (3, -16), (7, 6), (8.6, 22), (10, 26), (11.4, 14), (12.8, 4), (13.8, 0),
                (17, -2), (19, 3), (22, 0), (25, -4), (28, -6), (E, -6)])
cam_el = curve([(0, 2), (3, 3), (7, 8), (8.6, 26), (10, 30), (11.4, 16), (12.8, 5), (13.8, 2),
                (22, 1), (25, 6), (28, 5), (E, 5)])
cam_dist = curve([(0, 46), (3, 44), (7, 70), (8.6, 28), (10, 25), (11.4, 50), (12.8, 74), (13.8, 78),
                  (17, 46), (19, 48), (22, 48), (25, 118), (28, 122), (E, 120)])
cam_focal = curve([(0, 100), (3, 100), (7, 85), (8.6, 135), (10, 135), (11.4, 110), (13.8, 85), (E, 85)])
cam_fstop = curve([(0, 4.0), (7, 5.6), (8.2, 2.0), (10, 2.0), (11.4, 4.0), (13.8, 5.6), (E, 5.6)])
tgt_x = curve([(0, 0.6), (3, 0.3), (7, 0), (8.6, -1.2), (10, -1.6), (11.4, 0), (E, 0)])
tgt_z = curve([(0, 3.0), (3, 3.0), (7, 1.0), (8.6, 5.0), (10, 6.3), (11.4, 3.5), (12.8, 1.0), (13.8, 0.5),
               (17, 2.0), (19, 1.5), (22, 1.0), (25, 0), (E, 0)])
cam_shift_x = curve([(0, 0), (22.5, 0), (25.5, -0.17), (E, -0.17)])     # lens shift: phone to the right third

# ------------------------------------------------------------------------------------------------ screen
screen_gain = curve([(C["screen"]["wake_t"] - 0.01, 0.0), (C["screen"]["wake_t"] + C["screen"]["wake_dur"], 1.0), (E, 1.0)])

# ------------------------------------------------------------------------------------------------ lights (gain 0..1)
light_gain = {
    "LGT_Edge":      curve([(0, 0), (1.9, 0), (2.8, 1.0), (5.5, 0.6), (7, 0.2), (10, 0.2), (12, 0.1), (E, 0.1)]),
    "LGT_StripL":    curve([(0, 0), (3.0, 0), (4.5, 0.8), (8, 1.0), (14, 0.7), (E, 0.6)]),
    "LGT_StripR":    curve([(0, 0), (4.0, 0), (6.0, 0.8), (12, 1.0), (E, 0.7)]),
    "LGT_Top":       curve([(0, 0), (3.5, 0), (5.5, 0.5), (9, 0.8), (12, 1.0), (E, 0.9)]),
    "LGT_Key":       curve([(0, 0), (4.6, 0), (7.0, 0.6), (11, 1.0), (E, 0.9)]),
    "LGT_BackRimL":  curve([(0, 0), (3.2, 0), (4.6, 0.9), (E, 0.8)]),
    "LGT_BackRimR":  curve([(0, 0), (3.2, 0), (4.6, 0.9), (E, 0.8)]),
    "LGT_Sweep":     curve([(9.0, 0), (9.6, 1.0), (10.0, 1.0), (10.6, 0), (E, 0)]),
    "LGT_Amber":     curve([(0, 0), (22, 0), (25, 0.8), (E, 0.8)]),
    "LGT_Fill":      curve([(0, 0), (5, 0.05), (E, 0.08)]),
}
sweep_x = curve([(9.0, -55), (10.6, 55)])      # the sweeping strip passes across the front of the phone

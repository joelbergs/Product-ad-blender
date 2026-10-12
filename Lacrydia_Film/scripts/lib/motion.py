"""Motion system shared by every shot (pure python/numpy, no bpy).

One vocabulary for the whole film:
  * Every move is a `Channel`: a clamped cubic spline through (t, value) keys, zero velocity at both ends, so cameras and
    lights always accelerate gently out of rest and decelerate into rest (no robotic linear moves, no jerks).
  * One-shot reveals (opacity, light, draw-on) use `ease()` curves from the same family (cubic-bezier, Apple-like).
  * `prog(t, t0, t1)` is the normalised progress of a time window.
"""
import numpy as np
from scipy.interpolate import CubicSpline


def prog(t, t0, t1):
    """0..1 progress of t inside [t0, t1] (clamped)."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return float(min(1.0, max(0.0, (t - t0) / (t1 - t0))))


def _bezier_solver(x1, y1, x2, y2):
    def f(x):
        x = min(1.0, max(0.0, x))
        lo, hi = 0.0, 1.0
        for _ in range(40):
            m = 0.5 * (lo + hi)
            bx = 3 * (1 - m) ** 2 * m * x1 + 3 * (1 - m) * m * m * x2 + m ** 3
            if bx < x:
                lo = m
            else:
                hi = m
        m = 0.5 * (lo + hi)
        return 3 * (1 - m) ** 2 * m * y1 + 3 * (1 - m) * m * m * y2 + m ** 3
    return f


# the film's easing family (all start and end at rest or arrive softly)
EASE = {
    "inout": _bezier_solver(0.65, 0.0, 0.35, 1.0),      # symmetrical, calm
    "out":   _bezier_solver(0.16, 1.0, 0.30, 1.0),      # fast start, long soft landing (reveals, settles)
    "in":    _bezier_solver(0.55, 0.0, 0.85, 0.35),     # slow start, gathering (light building)
    "apple": _bezier_solver(0.25, 0.10, 0.25, 1.0),
    "soft":  _bezier_solver(0.45, 0.05, 0.25, 1.0),     # long, gentle settle for cards
}


def ease(kind, x):
    return EASE[kind](x)


def ramp(t, t0, t1, kind="inout"):
    """eased 0..1 across the window"""
    return ease(kind, prog(t, t0, t1))


def pulse(t, t0, t_peak, t1, kind_in="out", kind_out="inout"):
    """0 -> 1 -> 0"""
    if t <= t_peak:
        return ease(kind_in, prog(t, t0, t_peak))
    return 1.0 - ease(kind_out, prog(t, t_peak, t1))


class Channel:
    """Clamped cubic spline through (t, value) keys. Value may be a scalar or a vector (tuple)."""

    def __init__(self, keys, bc="clamped"):
        keys = sorted(keys, key=lambda k: k[0])
        self.t0, self.t1 = keys[0][0], keys[-1][0]
        ts = np.array([k[0] for k in keys], float)
        vs = np.array([k[1] for k in keys], float)
        self.scalar = vs.ndim == 1
        if len(keys) == 1:
            self._const = vs[0]
            self.cs = None
        else:
            self.cs = CubicSpline(ts, vs, bc_type=bc)

    def __call__(self, t):
        if self.cs is None:
            return self._const if self.scalar else np.array(self._const)
        tt = min(max(t, self.t0), self.t1)
        v = self.cs(tt)
        return float(v) if self.scalar else np.asarray(v)


def lerp(a, b, x):
    return a + (b - a) * x


def vlerp(a, b, x):
    return tuple(lerp(np.array(a, float), np.array(b, float), x))

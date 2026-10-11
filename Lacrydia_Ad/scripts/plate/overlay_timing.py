"""Reference evaluation of config/overlay_timing.json.

    from overlay_timing import overlay_state
    opacity, dy_frac = overlay_state("overlay_tagline_1", t)   # opacity 0..1 envelope, dy in fractions of frame height (+ = down)
"""
import json, math, os
_P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "overlay_timing.json")
_cfg = {}
_E = {"easeOutCubic": lambda x: 1 - (1 - x) ** 3, "easeInOutSine": lambda x: 0.5 - 0.5 * math.cos(math.pi * x)}


def overlay_state(name, t):
    if not _cfg:
        _cfg.update(json.load(open(_P)))
    o = _cfg["overlays"][name]
    u = min(1.0, max(0.0, (t - o["appear_t"]) / o["fade_in"])) if o["fade_in"] > 0 else float(t >= o["appear_t"])
    a = _E[o["ease_in"]](u); op = a; dy = o["drift_in_h"] * (1 - a)
    if o.get("disappear_t") is not None and t > o["disappear_t"]:
        v = min(1.0, (t - o["disappear_t"]) / o["fade_out"]) if o["fade_out"] > 0 else 1.0
        b = _E[o["ease_out"]](v); op = a * (1 - b); dy = o["drift_out_h"] * b
    return op, dy


if __name__ == "__main__":
    for n in ["overlay_tagline_1", "overlay_tagline_2", "overlay_endcard_lockup", "overlay_endcard_status", "overlay_endcard_url"]:
        print(n, [tuple(round(x, 3) for x in overlay_state(n, t)) for t in (25.0, 25.8, 26.4, 27.9, 28.2, 28.4, 28.7, 29.4, 30.0)])

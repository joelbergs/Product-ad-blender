"""Mix plan: which sound sits where, at what level, with which fades. Pure python/numpy (no bpy).

The same plan drives (a) the Blender VSE timeline (build_audio_timeline.apply_audio) and (b) the numpy re-render used
for stems, QA overlays and as a documented fallback mixdown.

FRAME CONVENTION (Blender): the timeline starts at frame 1 == t 0.000 s, 30 fps.
    frame = round(t * 30) + 1          t = (frame - 1) / 30
A sound file whose event 'lands' `anchor_s` seconds into the file (manifest.json) is placed so that
    start_frame = round((t_event - anchor_s) * 30) + 1
(anchors are whole frames by construction, so the placement is frame-exact and -- because 1 frame = 1600 samples at
48 kHz -- also sample-exact).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from paths import ROOT, cfg  # noqa: E402

SR = 48000
FPS = 30
SPF = SR // FPS                 # samples per frame (1600)
MANIFEST = os.path.join(ROOT, "assets", "audio", "manifest.json")

# Track order == Blender channel order (bottom -> top). Extra lanes are added automatically when two strips overlap.
LAYERS = ["MUSIC", "ATMOSPHERE", "IMPACTS", "WHOOSH", "MATERIAL", "INTERFACE", "LOGO"]
LAYER_COLOR = {"MUSIC": "COLOR_05", "ATMOSPHERE": "COLOR_04", "IMPACTS": "COLOR_01", "WHOOSH": "COLOR_06",
               "MATERIAL": "COLOR_03", "INTERFACE": "COLOR_02", "LOGO": "COLOR_07"}

# Static trim applied to every strip (calibrated by qa_audio.py so the full mix lands at the loudness target).
MASTER_TRIM_DB = 0.2

# name, layer, file, event, base level (dB re file), fade_in (s), fade_out (s)
# 'film_start' is the pseudo event t=0 (scene_01 t0).
ENTRIES = [
    ("MUSIC_score",            "MUSIC",      "assets/audio/music/lacrydia_score_v1.wav", "film_start",      +0.0, 0.00, 0.00),
    ("ATMOSPHERE_room_tone",   "ATMOSPHERE", "assets/audio/sfx/atmos_room_tone.wav",     "film_start",     -46.0, 0.00, 0.60),
    ("ATMOSPHERE_low_tone",    "ATMOSPHERE", "assets/audio/sfx/atmos_low_tone.wav",      "atmos_in",       -29.0, 0.00, 0.60),
    ("IMPACTS_emerge_swell",   "IMPACTS",    "assets/audio/sfx/impact_emerge_swell.wav", "emerge_swell",   -17.0, 0.00, 0.40),
    ("IMPACTS_screen_wake",    "IMPACTS",    "assets/audio/sfx/impact_screen_wake_sub.wav", "screen_wake", -15.0, 0.00, 0.40),
    ("IMPACTS_pull_back",      "IMPACTS",    "assets/audio/sfx/impact_pull_back_sub.wav", "pull_back",     -16.0, 0.00, 0.40),
    ("WHOOSH_rotate_1",        "WHOOSH",     "assets/audio/sfx/whoosh_rotate_01.wav",    "rotate_whoosh_1", -11.0, 0.03, 0.30),
    ("WHOOSH_macro_cut_air",   "WHOOSH",     "assets/audio/sfx/whoosh_macro_air_01.wav", "macro_cut_air",  -11.0, 0.03, 0.30),
    ("WHOOSH_light_sweep",     "WHOOSH",     "assets/audio/sfx/whoosh_light_sweep_01.wav", "light_sweep",   -9.0, 0.03, 0.30),
    ("WHOOSH_turn_2",          "WHOOSH",     "assets/audio/sfx/whoosh_turn_02.wav",      "turn_whoosh_2",   -9.0, 0.03, 0.30),
    ("WHOOSH_push_in",         "WHOOSH",     "assets/audio/sfx/whoosh_push_in_01.wav",   "push_in",         -8.0, 0.03, 0.40),
    ("WHOOSH_pull_back",       "WHOOSH",     "assets/audio/sfx/whoosh_pull_back_01.wav", "pull_back",       -9.0, 0.03, 0.40),
    ("MATERIAL_first_light",   "MATERIAL",   "assets/audio/sfx/material_first_light.wav", "first_light",   -14.0, 0.00, 0.40),
    ("MATERIAL_lens_glint",    "MATERIAL",   "assets/audio/sfx/material_lens_glint.wav", "lens_glint",     -11.0, 0.00, 0.40),
    ("INTERFACE_screen_wake",  "INTERFACE",  "assets/audio/sfx/ui_screen_wake.wav",      "screen_wake",     -8.0, 0.00, 0.40),
    ("INTERFACE_swipe_1",      "INTERFACE",  "assets/audio/sfx/ui_swipe_01.wav",         "swipe_1",         -6.0, 0.00, 0.15),
    ("INTERFACE_swipe_2",      "INTERFACE",  "assets/audio/sfx/ui_swipe_02.wav",         "swipe_2",         -8.0, 0.00, 0.15),
    ("INTERFACE_swipe_3",      "INTERFACE",  "assets/audio/sfx/ui_swipe_03.wav",         "swipe_3",         -6.0, 0.00, 0.15),
    ("INTERFACE_swipe_4",      "INTERFACE",  "assets/audio/sfx/ui_swipe_04.wav",         "swipe_4",         -5.0, 0.00, 0.15),
    ("LOGO_signature",         "LOGO",       "assets/audio/sfx/logo_signature.wav",      "logo_signature",  -2.0, 0.00, 0.00),
]

# gentle music ducking under the biggest low-frequency moments: (name, [(event, offset_s, dB), ...]) piecewise linear
MUSIC_DUCKS = [("emerge_swell", -0.9, 0.0), ("emerge_swell", -0.3, -1.2), ("emerge_swell", 0.9, -1.2), ("emerge_swell", 1.8, 0.0),
               ("screen_wake", -0.2, 0.0), ("screen_wake", 0.2, -1.5), ("screen_wake", 1.0, -1.5), ("screen_wake", 2.0, 0.0)]


def load_manifest():
    with open(MANIFEST) as f:
        return json.load(f)["files"]


def event_times(conf=None):
    conf = conf or cfg()
    ev = {e["id"]: e["t"] for e in conf["events"]}
    ev["film_start"] = conf["scenes"][0]["t0"]
    return ev


def t_to_frame(t, fps=FPS):
    return int(round(t * fps)) + 1


def frame_to_t(frame, fps=FPS):
    return (frame - 1) / fps


def _sin2(u):
    return np.sin(0.5 * np.pi * np.clip(u, 0, 1)) ** 2


def make_keys(start_frame, dur_frames, gain, fade_in_s, fade_out_s, extra_points=None, fps=FPS, nfade=8):
    """Piecewise-linear volume keys [(frame, linear gain)] for a strip: sin^2 fades (equal-power-like, smooth) times a
    flat gain times optional duck points [(frame, linear_gain_multiplier)]."""
    end = start_frame + dur_frames
    fi, fo = fade_in_s * fps, fade_out_s * fps
    frames = {start_frame, end}
    if fi > 0:
        frames.update(start_frame + fi * np.arange(nfade + 1) / nfade)
    if fo > 0:
        frames.update(end - fo * np.arange(nfade + 1) / nfade)
    if extra_points:
        frames.update(f for f, _ in extra_points if start_frame < f < end)
    fr = np.array(sorted(frames), float)
    g = np.full(len(fr), gain)
    if fi > 0:
        g = g * np.where(fr < start_frame + fi, _sin2((fr - start_frame) / fi), 1.0)
    if fo > 0:
        g = g * np.where(fr > end - fo, _sin2((end - fr) / fo), 1.0)
    if extra_points:
        ef = np.array([p[0] for p in extra_points], float)
        eg = np.array([p[1] for p in extra_points], float)
        g = g * np.interp(fr, ef, eg)
    return [(float(a), float(b)) for a, b in zip(fr, g)]


def build_plan(conf=None, ev=None, master_trim_db=None, time_offset_s=0.0, entries=None, drop=()):
    """Resolve ENTRIES against the config events + manifest. Returns list of dicts (JSON-serialisable)."""
    conf = conf or cfg()
    fps = conf["fps"]
    assert fps == FPS
    ev = ev or event_times(conf)
    man = load_manifest()
    trim = MASTER_TRIM_DB if master_trim_db is None else master_trim_db
    plan = []
    for name, layer, rel, event, vol_db, fi, fo in (entries or ENTRIES):
        if name in drop:
            continue
        m = man[rel]
        t_ev = ev[event] + time_offset_s
        start_frame = int(round((t_ev - m["anchor_s"]) * fps)) + 1
        if start_frame < 1 and name != "ATMOSPHERE_room_tone":
            raise ValueError(f"{name}: would start before frame 1")
        dur_frames = int(round(m["duration_s"] * fps))
        gain = 10 ** ((vol_db + trim) / 20.0)
        extra = None
        if name == "MUSIC_score":
            extra = [(t_to_frame(ev[e] + o + time_offset_s), 10 ** (d / 20.0)) for e, o, d in MUSIC_DUCKS if e in ev]
            extra = sorted(extra)
        plan.append(dict(name=name, layer=layer, file=rel, event=event, t_event=round(t_ev, 4),
                         anchor_frames=m["anchor_frames"], start_frame=start_frame, dur_frames=dur_frames,
                         end_frame=start_frame + dur_frames, t_start=round(frame_to_t(start_frame), 4),
                         vol_db=vol_db + trim, fade_in_s=fi, fade_out_s=fo,
                         keys=make_keys(start_frame, dur_frames, gain, fi, fo, extra)))
    assign_lanes(plan)
    return plan


def assign_lanes(plan):
    """Allocate Blender channels: one named track per layer, extra lanes (named '<LAYER> 2' ...) only where strips overlap."""
    lanes = {}
    for layer in LAYERS:
        items = sorted([p for p in plan if p["layer"] == layer], key=lambda p: p["start_frame"])
        lane_ends = []
        for p in items:
            for li, e in enumerate(lane_ends):
                if p["start_frame"] >= e:
                    lane_ends[li] = p["end_frame"]
                    p["lane"] = li
                    break
            else:
                lane_ends.append(p["end_frame"])
                p["lane"] = len(lane_ends) - 1
        lanes[layer] = max(1, len(lane_ends))
    ch = 1
    layout = []
    for layer in LAYERS:
        for li in range(lanes[layer]):
            layout.append((ch, layer if li == 0 else f"{layer} {li + 1}", layer, li))
            ch += 1
    cmap = {(l, li): c for c, _, l, li in layout}
    for p in plan:
        p["lane_index"] = p["lane"]
        p["channel_rel"] = cmap[(p["layer"], p["lane"])]
    return layout


def channel_layout(plan):
    seen = {}
    for p in plan:
        seen[p["channel_rel"]] = p["layer"] if p["lane"] == 0 else f"{p['layer']} {p['lane'] + 1}"
    return dict(sorted(seen.items()))


# ------------------------------------------------------------------ numpy re-render of the same plan (fallback + stems)
def _read(path):
    sys.path.insert(0, HERE)
    from dsp_common import read_wav
    x, sr = read_wav(path)
    assert sr == SR
    return x


def render_plan(plan, total_s=30.0, keep_stems=True):
    """Sample-exact numpy rendering of the plan. Returns (mix (n,2), stems {layer: (n,2)})."""
    n = int(round(total_s * SR))
    mix = np.zeros((n, 2))
    stems = {}
    cache = {}
    for p in plan:
        if p["file"] not in cache:
            cache[p["file"]] = _read(os.path.join(ROOT, p["file"]))
        x = cache[p["file"]]
        s0 = (p["start_frame"] - 1) * SPF
        L = min(len(x), p["dur_frames"] * SPF)
        fr = p["start_frame"] + np.arange(L) / SPF
        kf = np.array([k[0] for k in p["keys"]])
        kg = np.array([k[1] for k in p["keys"]])
        g = np.interp(fr, kf, kg)
        seg = x[:L] * g[:, None]
        e = min(n, s0 + L)
        if e <= s0:
            continue
        mix[s0:e] += seg[: e - s0]
        if keep_stems:
            st = stems.setdefault(p["layer"], np.zeros((n, 2)))
            st[s0:e] += seg[: e - s0]
    return mix, stems


if __name__ == "__main__":
    pl = build_plan()
    print(f"{'name':24s} {'layer':11s} {'event':16s} {'t_ev':>6s} {'start_fr':>8s} {'end_fr':>6s} {'ch':>3s} {'dB':>6s}")
    for p in pl:
        print(f"{p['name']:24s} {p['layer']:11s} {p['event']:16s} {p['t_event']:6.2f} {p['start_frame']:8d} "
              f"{p['end_frame']:6d} {p['channel_rel']:3d} {p['vol_db']:6.1f}")
    print(channel_layout(pl))

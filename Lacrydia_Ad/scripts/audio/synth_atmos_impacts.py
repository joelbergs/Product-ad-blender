"""ATMOSPHERE + IMPACTS layers (original synthesis, deterministic).

ATMOSPHERE: (a) a dark room tone for the opening that fades under the score, (b) a very low D tone that wakes at
            atmos_in (t=1.2) and dissolves into the music.
IMPACTS:    soft, round sub impulses / swells - sine bodies with explicit 2nd/3rd harmonics (so they also read on
            phone speakers that cannot reproduce < 120 Hz). No clipping, no distortion stage: peak normalised.
Run: python3 synth_atmos_impacts.py
"""
import numpy as np
from dsp_common import *  # noqa: F401,F403

NM = "synth_atmos_impacts.py"


def room_tone(dur=16.0, seed=2001):
    n = nsamp(dur)
    t = np.arange(n) / SR
    # dark body: brown noise, low-passed
    body = lowpass(brown(n, seed), 420, order=2)
    body = body / np.std(body)
    # soft mid air (barely there)
    mid = bandpass(pink(n, seed + 1), 250, 2400, order=1)
    mid = mid / np.std(mid) * float(db(-17)) * (1 + 0.25 * slow_noise(n, seed + 2, 0.15))
    # room modes: very narrow noise resonances around D (73/110/147 Hz) drifting slowly
    modes = np.zeros(n)
    for i, f in enumerate([73.4, 110.0, 146.8, 220.0]):
        m = bandpass(white(n, seed + 10 + i), f * 0.985, f * 1.015, order=2)
        m = m / (np.std(m) + 1e-12) * (1 + 0.5 * slow_noise(n, seed + 20 + i, 0.1)) / (1 + i * 0.5)
        modes += m
    modes = modes / np.std(modes) * float(db(-9))
    # extremely faint high air
    air = highpass(white(n, seed + 30), 6500, order=1)
    air = air / np.std(air) * float(db(-34)) * (0.6 + 0.4 * slow_noise(n, seed + 31, 0.2))
    mono_c = body + mid + modes
    L = mono_c + 0.4 * lowpass(brown(n, seed + 40), 350) / 1.0 * 0 + air
    # width: separate decorrelated low-level components per channel
    wl = bandpass(pink(n, seed + 50), 200, 1800, order=1)
    wr = bandpass(pink(n, seed + 51), 200, 1800, order=1)
    wl, wr = wl / np.std(wl) * float(db(-15)), wr / np.std(wr) * float(db(-15))
    out = np.stack([mono_c + wl + air, mono_c + wr + air * 0.8], axis=1)
    # relative envelope: present from frame 0 (never digital silence), slow bloom, then dissolves under the score
    env = db_curve([(0, -9), (3.0, 0), (7.0, -1), (11.0, -9), (14.0, -26), (dur, -60)], n=n)
    return out * env[:, None]


def low_tone(dur=14.0, seed=2002):
    """the 'barely there' low tone waking at atmos_in. D1/D2/A2 + faint D3, slow beating = width."""
    n = nsamp(dur)
    t = np.arange(n) / SR
    drift = 1 + 0.0012 * slow_noise(n, seed, 0.15)
    parts = [(36.708, 0.30, 0.0), (73.416, 1.0, 0.07), (110.0, 0.30, -0.05), (146.83, 0.14, 0.11), (220.0, 0.05, -0.08)]
    L = np.zeros(n)
    R = np.zeros(n)
    r = rng(seed)
    for f, a, det in parts:
        ph = r.uniform(0, 6.28, 2)
        L += a * sine(f * drift + det, n, ph[0])
        R += a * sine(f * drift - det, n, ph[1])
    trem = 1 + 0.10 * np.sin(2 * np.pi * 0.11 * t + 1.0) + 0.05 * np.sin(2 * np.pi * 0.27 * t)
    env = db_curve([(0, -80), (0.6, -40), (2.0, -20), (4.5, -8), (7.0, 0), (9.0, -3), (11.5, -16), (dur, -70)], n=n)
    out = np.stack([L, R], axis=1) * (trem * env)[:, None]
    return lowpass(out, 400, order=2)


def swell(dur, crest, rise_shape=1.0, fundamentals=((36.708, 1.0), (73.416, 0.75), (110.0, 0.28), (146.83, 0.16),
                                                    (220.0, 0.07)), seed=1):
    """pad-like low swell: raised cosine rise to `crest`, longer cosine release."""
    n = nsamp(dur)
    t = np.arange(n) / SR
    env = np.where(t < crest, cos_fade(t / crest), 1 - cos_fade((t - crest) / (dur - crest)))
    L = np.zeros(n)
    R = np.zeros(n)
    r = rng(seed)
    for f, a in fundamentals:
        p = r.uniform(0, 6.28, 2)
        L += a * sine(f * 1.0007, n, p[0])
        R += a * sine(f * 0.9993, n, p[1])
    return np.stack([L, R], axis=1) * env[:, None], env


def soft_pulse(dur, f_start, f_end, glide_tau, attack, decay_tau, harm=(1.0, 0.45, 0.22, 0.08)):
    n = nsamp(dur)
    t = np.arange(n) / SR
    f = f_end + (f_start - f_end) * np.exp(-t / glide_tau)
    env = cos_fade(t / attack) * np.exp(-t / decay_tau)
    y = np.zeros(n)
    for k, a in enumerate(harm, start=1):
        y += a * sine(f * k, n)
    return y * env


def build():
    ev = events()
    print("ATMOSPHERE + IMPACTS layers")

    # ---- ATMOSPHERE
    x = room_tone()
    save_asset(SFX_DIR, "atmos_room_tone.wav", x, "ATMOSPHERE", "scene_01 (Darkness) / atmos_in", 0.0,
               f"{NM}: brown+pink noise bodies, 4 narrow drifting room-mode resonances (73/110/147/220 Hz), "
               "faint air; opens near-silent, blooms to 3 s, dissolves by 14 s",
               pan_note="stereo (decorrelated mid noise), centred", peak_target_db=-3.0, seed=2001,
               edge=(1.0, 40.0), description="dark room tone for the opening; strip volume sets it ~-60 dBFS")

    x = low_tone()
    save_asset(SFX_DIR, "atmos_low_tone.wav", x, "ATMOSPHERE", "atmos_in", 0.0,
               f"{NM}: D1/D2/A2/D3 sines with +-0.1 Hz L/R detune (slow beating width), 0.11 Hz tremolo; wakes slowly",
               pan_note="stereo via L/R detune beating (~0.1-0.2 Hz); centred",
               peak_target_db=-3.0, seed=2002, edge=(2.0, 40.0),
               description="barely-there low tone waking at t=1.2, dissolves under the score by ~13 s")

    # ---- IMPACTS
    # emerge swell: starts 1.2 s before the crest. crest lands on emerge_swell (3.4)
    crest = 1.2
    sw, env = swell(3.6, crest, seed=3001)
    n = len(sw)
    t = np.arange(n) / SR
    pulse = soft_pulse(2.4, 66.0, 41.0, 0.18, 0.045, 0.42)
    pulse_st = np.stack([pulse, pulse], axis=1)
    out = sw * 0.62
    s = nsamp(crest - 0.02)
    out[s:s + len(pulse_st)] += pulse_st[: n - s] * 0.85
    rumble = bandpass(brown(n, 3002), 35, 160, order=1)
    rumble = rumble / np.std(rumble) * 0.10
    out += np.stack([rumble, np.roll(rumble, 40)], axis=1) * env[:, None]
    air = bandpass(white(n, 3003), 500, 2600, order=1)
    air = air / np.std(air) * 0.035
    out += np.stack([air, np.roll(air, 77)], axis=1) * (env ** 2)[:, None]
    out = reverb(out, wet=0.16, dry=1.0, tail_keep=False, rt60=1.8, hf_damp=2.0, seed=3004)
    save_asset(SFX_DIR, "impact_emerge_swell.wav", out, "IMPACTS", "emerge / emerge_swell", crest,
               f"{NM}: D1-D2-A2 harmonic sine swell (raised cosine, crest at 1.2 s) + soft sine pulse 66->41 Hz "
               "(45 ms attack) + brown-noise rumble; small room; no distortion stage",
               pan_note="centre, narrow L/R detune", peak_target_db=-3.0, seed=3001, edge=(5.0, 40.0),
               description="soft deep swell; crest (anchor 1.2 s) lands on emerge_swell t=3.4, starts at 2.2 s with first_light")

    # screen wake sub pulse (lands with the bloom)
    p = soft_pulse(2.6, 92.0, 73.42, 0.22, 0.09, 0.62, harm=(1.0, 0.5, 0.25, 0.1))
    a2 = 0.28 * soft_pulse(2.6, 110.0, 110.0, 1.0, 0.12, 0.5, harm=(1.0, 0.3))
    p = p + a2
    out = np.stack([p, np.roll(p, 24)], axis=1)
    out = reverb(out, wet=0.18, rt60=1.6, hf_damp=2.0, tail_keep=False, seed=3011)
    save_asset(SFX_DIR, "impact_screen_wake_sub.wav", out, "IMPACTS", "screen_wake", 0.0,
               f"{NM}: D2 sine pulse 92->73 Hz (90 ms attack, 0.62 s decay) + A2 + harmonics; small room",
               pan_note="centre", peak_target_db=-3.0, seed=3011, edge=(5.0, 40.0),
               description="soft sub bloom under the display wake at t=11.6")

    # pull back: very soft low swell, warm
    sw, env = swell(3.4, 0.9, fundamentals=((73.416, 1.0), (110.0, 0.55), (146.83, 0.30), (220.0, 0.12), (293.66, 0.05)),
                    seed=3021)
    t = np.arange(len(sw)) / SR
    glide = 1.0
    out = reverb(sw, wet=0.22, rt60=2.0, hf_damp=2.0, tail_keep=False, seed=3022)
    save_asset(SFX_DIR, "impact_pull_back_sub.wav", out, "IMPACTS", "pull_back", 0.0,
               f"{NM}: D2/A2/D3/A3 sine swell, raised-cosine 0.9 s rise, long release",
               pan_note="centre, narrow", peak_target_db=-3.0, seed=3021, edge=(5.0, 50.0),
               description="subtle warm sub swell as the camera pulls back at t=22.0")


if __name__ == "__main__":
    build()

"""WHOOSH layer: soft air sweeps shaped to each camera/object move in config/production.json.

Method (all original): white noise -> STFT band mask whose centre frequency / bandwidth follow the motion
(rise/fall, narrow/wide), independent-noise fraction for stereo width, equal-power pan automation for the
direction of travel, a very quiet D-based harmonic 'air whistle' (sine partials that follow the sweep by a few
percent only, so it never turns into a laser), a low body of filtered noise, then a small synthetic-IR room.
Deterministic (fixed seeds). Run:  python3 synth_whoosh.py
"""
import numpy as np
from dsp_common import *  # noqa: F401,F403

# (event id, file, start event, end of motion (s), description)
D = lambda m: float(midi_hz(m))


def cfn(points):
    """callable curve of time (array in s)."""
    pts = sorted(points)
    ts = np.array([p[0] for p in pts], float)
    vs = np.array([p[1] for p in pts], float)

    def f(t):
        t = np.asarray(t, float)
        idx = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 2)
        u = np.clip((t - ts[idx]) / np.maximum(ts[idx + 1] - ts[idx], 1e-9), 0, 1)
        w = 0.5 - 0.5 * np.cos(np.pi * u)
        return vs[idx] + (vs[idx + 1] - vs[idx]) * w
    return f


def whoosh(dur, fc_pts, bw_pts, env_db_pts, pan_pts, indep_pts, seed, tail=0.6, tonal=(), tonal_db=-22.0,
           body=None, room=dict(rt60=1.1, hf_damp=1.5, predelay=0.012), wet=0.22, hp=60.0, lp=14000.0):
    total = dur + tail
    n = nsamp(total)
    fc_fn, bw_fn = cfn(fc_pts), cfn(bw_pts)
    mask = sweep_mask(fc_fn, bw_fn, floor=0.0)
    common = stft_shape(white(n, seed), mask)
    indL = stft_shape(white(n, seed + 1), mask)
    indR = stft_shape(white(n, seed + 2), mask)
    for a in (common, indL, indR):
        a /= (np.std(a) + 1e-12)
    ind = curve(indep_pts, n=n)
    L = np.sqrt(1 - ind) * common + np.sqrt(ind) * indL
    R = np.sqrt(1 - ind) * common + np.sqrt(ind) * indR
    env = db_curve(env_db_pts, n=n)
    pan = curve(pan_pts, n=n)
    gl, gr = pan_gains(pan)
    out = np.stack([L * gl, R * gr], axis=1) * np.sqrt(2.0)

    t = np.arange(n) / SR
    fc_t = fc_fn(t)
    if tonal:                                   # quiet harmonic air, follows the sweep only by ~+-15 %
        ref = fc_t[np.argmax(env)] if np.max(env) > 0 else fc_t[0]
        glide = 1.0 + 0.30 * np.clip(np.log2(fc_t / ref), -1, 1) * 0.5
        tone = np.zeros(n)
        r = rng(seed + 7)
        for i, f0 in enumerate(tonal):
            drift = 1.0 + 0.002 * slow_noise(n, seed + 20 + i, 0.4)
            tone += sine(f0 * glide * drift, n, phase=r.uniform(0, 6.28)) / (1 + 0.6 * i)
        tone = tone / (np.max(np.abs(tone)) + 1e-9) * float(db(tonal_db))
        # tonal part is slightly decorrelated between L/R through a 0.6 ms delay
        d = nsamp(0.0006)
        tone_st = np.stack([tone * gl, np.roll(tone, d) * gr], axis=1) * np.sqrt(2.0)
        out += tone_st * np.max(np.abs(out)) * 1.0
    if body:                                    # displaced-air body (low rumble band), mono-centred
        bf, bdb = body
        b = lowpass(highpass(brown(n, seed + 40), bf * 0.45), bf)
        b = b / (np.std(b) + 1e-9) * float(db(bdb)) * np.std(out)
        out += np.stack([b, b], axis=1) * 0.7
    out = out * env[:, None]
    out = highpass(out, hp, order=2)
    out = lowpass(out, lp, order=1)
    if wet > 0:
        out = reverb(out, wet=wet, dry=1.0, tail_keep=False, seed=seed + 5, **room)
    return out


def build():
    ev = events()
    nm = "synth_whoosh.py"
    print("WHOOSH layer")
    jobs = []

    # 1. rotate_whoosh_1  4.4 -> 6.8  (2.4 s): phone turns towards its back. L -> R, rises then falls, widest in the middle
    jobs.append(dict(
        file="whoosh_rotate_01.wav", event="rotate_whoosh_1", dur=2.4, tail=0.7, seed=1101, target=-3.0,
        fc=[(0, 330), (0.9, 1000), (1.35, 1750), (2.4, 560)], bw=[(0, 1.6), (1.3, 1.15), (2.4, 1.7)],
        env=[(0, -70), (0.35, -26), (1.25, -4), (1.4, 0), (2.0, -12), (2.45, -38), (3.1, -80)],
        pan=[(0, -0.75), (2.4, 0.75)], ind=[(0, 0.55), (1.4, 0.7), (2.4, 0.5)],
        tonal=[D(74), D(81), D(86)], tonal_db=-24, body=(180, -20),
        pan_note="L->R: -0.75 -> +0.75 over 2.4 s (rotation direction); widest mid-move",
        desc="soft air sweep, centre 330 Hz -> 1.75 kHz (peak at 55 % of move) -> 560 Hz"))

    # 2. macro_cut_air 6.9 -> 7.6 (0.7 s): camera glides into macro. short inhale, stereo field narrows (focus)
    jobs.append(dict(
        file="whoosh_macro_air_01.wav", event="macro_cut_air", dur=0.7, tail=0.7, seed=1102, target=-6.0,
        fc=[(0, 800), (0.38, 2800), (0.7, 1500)], bw=[(0, 1.3), (0.7, 1.0)],
        env=[(0, -70), (0.12, -16), (0.3, 0), (0.62, -14), (1.0, -44), (1.4, -80)],
        pan=[(0, 0.0), (0.7, 0.18)], ind=[(0, 0.7), (0.7, 0.12)],
        tonal=[D(86), D(90)], tonal_db=-26, body=None,
        pan_note="centre -> +0.18; stereo width collapses 0.7 -> 0.12 (focus into macro)",
        desc="short air inhale 0.8 -> 2.8 kHz -> 1.5 kHz, narrowing image"))

    # 3. light_sweep 9.5 -> 10.4 (0.9 s): reflection crossing the frame. fast L -> R, bright, narrow band
    jobs.append(dict(
        file="whoosh_light_sweep_01.wav", event="light_sweep", dur=0.9, tail=0.6, seed=1103, target=-7.0,
        fc=[(0, 2300), (0.9, 9000)], bw=[(0, 0.8), (0.45, 0.6), (0.9, 0.9)],
        env=[(0, -70), (0.2, -18), (0.45, 0), (0.75, -10), (1.0, -34), (1.5, -80)],
        pan=[(0, -0.92), (0.9, 0.92)], ind=[(0, 0.35), (0.9, 0.35)],
        tonal=[D(98), D(105)], tonal_db=-28, body=None, hp=900.0, wet=0.28,
        pan_note="L->R fast: -0.92 -> +0.92 over 0.9 s (matches reflection travelling across the frame)",
        desc="bright narrow-band air 2.3 -> 9 kHz with faint glassy partials; acts as transition"))

    # 4. turn_whoosh_2 10.2 -> 12.4 (2.2 s): phone turns to the screen. R -> L (reverse of whoosh 1), softer
    jobs.append(dict(
        file="whoosh_turn_02.wav", event="turn_whoosh_2", dur=2.2, tail=0.8, seed=1104, target=-4.0,
        fc=[(0, 300), (1.0, 1200), (2.2, 520)], bw=[(0, 1.6), (1.0, 1.2), (2.2, 1.7)],
        env=[(0, -70), (0.4, -24), (1.0, -3), (1.1, 0), (1.7, -10), (2.2, -30), (3.0, -80)],
        pan=[(0, 0.7), (2.2, -0.7)], ind=[(0, 0.5), (1.1, 0.7), (2.2, 0.5)],
        tonal=[D(69), D(74), D(81)], tonal_db=-24, body=(160, -22),
        pan_note="R->L: +0.7 -> -0.7 over 2.2 s (mirror of rotate_01: turning back towards the viewer)",
        desc="softer air sweep 300 Hz -> 1.2 kHz -> 520 Hz; settles as the screen wakes"))

    # 5. push_in 13.8 -> 17.0 (3.2 s): camera moves in. slow build, low-mid air, image narrows to the centre
    jobs.append(dict(
        file="whoosh_push_in_01.wav", event="push_in", dur=3.2, tail=0.8, seed=1105, target=-5.0,
        fc=[(0, 240), (1.5, 650), (2.8, 1500), (3.2, 900)], bw=[(0, 1.8), (2.8, 1.3), (3.2, 1.6)],
        env=[(0, -70), (1.2, -20), (2.4, -4), (2.8, 0), (3.3, -14), (4.0, -80)],
        pan=[(0, 0.0), (3.2, 0.0)], ind=[(0, 0.8), (3.2, 0.2)],
        tonal=[D(62), D(69), D(74)], tonal_db=-22, body=(140, -21),
        pan_note="centre; stereo width narrows 0.8 -> 0.2 (camera approaches, image focuses)",
        desc="slow air swell 240 Hz -> 1.5 kHz, long build and soft landing"))

    # 6. pull_back 22.0 -> 25.0 (3.0 s): camera pulls back. falling centre freq, image opens wide
    jobs.append(dict(
        file="whoosh_pull_back_01.wav", event="pull_back", dur=3.0, tail=1.0, seed=1106, target=-4.0,
        fc=[(0, 2600), (1.2, 1300), (3.0, 420)], bw=[(0, 1.2), (3.0, 1.8)],
        env=[(0, -70), (0.35, -12), (0.8, 0), (1.8, -9), (3.0, -26), (4.0, -80)],
        pan=[(0, 0.0), (3.0, 0.0)], ind=[(0, 0.2), (3.0, 0.9)],
        tonal=[D(74), D(81), D(66)], tonal_db=-24, body=(150, -22), wet=0.3,
        pan_note="centre; stereo width opens 0.2 -> 0.9 (space opens up as the camera retreats)",
        desc="airy fall 2.6 kHz -> 420 Hz, widening; warm settle into the typography"))

    for j in jobs:
        x = whoosh(j["dur"], j["fc"], j["bw"], j["env"], j["pan"], j["ind"], j["seed"], tail=j["tail"],
                   tonal=j["tonal"], tonal_db=j["tonal_db"], body=j["body"],
                   **({"hp": j["hp"]} if "hp" in j else {}), **({"wet": j["wet"]} if "wet" in j else {}))
        save_asset(SFX_DIR, j["file"], x, "WHOOSH", j["event"], 0.0,
                   f"{nm}: STFT band-masked noise ({j['desc']}); event {j['event']} t={ev[j['event']]} s, "
                   f"motion {j['dur']} s", pan_note=j["pan_note"], peak_target_db=j["target"], seed=j["seed"],
                   edge=(4.0, 30.0), description=j["desc"])


if __name__ == "__main__":
    build()

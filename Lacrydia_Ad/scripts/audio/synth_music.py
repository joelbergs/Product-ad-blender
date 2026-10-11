"""MUSIC layer: restrained original ambient score, 30.000 s, key of D (Dsus2 -> ... -> Dadd9 resolution).

Instruments (all synthesised here, nothing sampled):
  * warm pad      - band-limited additive saw stacks (2 detuned voices L/R), slow cosine envelopes, a brightness
                    (low-pass) automation that opens when the screen wakes;
  * felt keys     - additive piano-like voice: slightly stretched partials, per-partial decay, soft hammer noise;
  * sub           - D2 sine + 2nd/3rd harmonic, used only at three moments (screen wake, warm pull-back, resolution);
  * space         - synthetic stereo impulse responses (decaying band-split noise) convolved by FFT.
Every harmony/motif time is derived from config/production.json events. The A-D-F#-E motif is stated on the
screen wake; E and F# land on the two tagline lines; the logo (synth_logo.py) answers with A5 -> D6.
No risers, braams, drums or constant bass. Run: python3 synth_music.py
"""
import numpy as np
from dsp_common import *  # noqa: F401,F403
from synth_whoosh import cfn

NM = "synth_music.py"
DUR = 30.0
N = nsamp(DUR)
TAIL = 4.0                      # render length beyond 30 s so reverb tails exist before the final cut
NT = nsamp(DUR + TAIL)

E = events()


# ------------------------------------------------------------------ brightness (pad low-pass cutoff in Hz) over the film
def brightness():
    return cfn([(0, 600), (2.5, 750), (3.75, 950), (5.0, 1100), (6.4, 3300),             # the lift when the screen wakes
                (7.5, 3000), (12.5, 2800), (22.4, 2800), (23.7, 3800),                     # warm accent opens up at the pull-back
                (25.0, 3000), (25.625, 2100), (26.25, 3600), (27.25, 2300), (DUR + TAIL, 1500)])


def pad_note(buf, midi, t_on, t_off, att, rel, amp_db, fc_fn, seed, detune_cents=4.5, kmax=18):
    t_a = max(0.0, t_on - att / 2)
    t_b = min(DUR + TAIL, t_off + rel / 2)
    n = nsamp(t_b - t_a)
    tt = t_a + np.arange(n) / SR
    rise = cos_fade((tt - (t_on - att / 2)) / att)
    fall = 1 - cos_fade((tt - (t_off - rel / 2)) / rel)
    env = rise * fall * float(db(amp_db))
    f0 = float(midi_hz(midi))
    step = 240
    tc = tt[::step]
    fc_c = fc_fn(tc)
    r = rng(seed)
    left = np.zeros(n)
    right = np.zeros(n)
    drift = 1 + 0.0009 * slow_noise(n, seed + 100, 0.12)         # ~1.5 cents slow wander
    for v, (sgn, tgt) in enumerate(((-1, "L"), (+1, "R"))):
        f = f0 * 2 ** (sgn * detune_cents / 1200.0)
        sig = np.zeros(n)
        for k in range(1, kmax + 1):
            fk = f * k
            if fk > 9500:
                break
            g_c = 1.0 / np.sqrt(1.0 + (fk / fc_c) ** 4)
            g = np.interp(np.arange(n), np.arange(len(tc)) * step, g_c)
            sig += (k ** -1.25) * g * np.sin(2 * np.pi * fk * drift * tt + r.uniform(0, 6.2832))
        if tgt == "L":
            left += sig
        else:
            right += sig
    l = left * 0.85 + right * 0.30
    rr = right * 0.85 + left * 0.30
    i0 = nsamp(t_a)
    buf[i0:i0 + n, 0] += l * env
    buf[i0:i0 + n, 1] += rr * env


def key_note(buf, midi, t0, vel, seed, pan=0.0, T0=5.0, bell=0.0):
    f0 = float(midi_hz(midi))
    dur = min(8.0, DUR + TAIL - t0)
    n = nsamp(dur)
    tt = np.arange(n) / SR
    r = rng(seed)
    B = 0.00012 + 0.0007 * bell
    out = np.zeros((n, 2))
    gl, gr = pan_gains(pan)
    T_base = T0 * (1.0 - 0.012 * (midi - 60))            # higher notes ring a little shorter
    for k in range(1, 15):
        fk = f0 * k * np.sqrt(1 + B * k * k)
        if fk > 11000:
            break
        a = (k ** -0.95) * np.exp(-(k - 1) * 0.30 * (1.2 - vel))
        T60 = max(0.25, T_base / (1 + 0.65 * (k - 1)))
        dec = np.exp(-6.9078 * tt / T60)
        ph = r.uniform(0, 6.2832)
        s1 = np.sin(2 * np.pi * fk * 0.9996 * tt + ph) * dec          # two slightly detuned strings
        s2 = np.sin(2 * np.pi * fk * 1.0004 * tt + ph * 0.7) * dec
        out[:, 0] += a * (s1 * 0.6 + s2 * 0.4)
        out[:, 1] += a * (s1 * 0.4 + s2 * 0.6)
    # felt hammer: tiny low-passed noise burst
    h = lowpass(white(n, seed + 9), min(2.2 * f0 + 800, 5000), order=1) * np.exp(-tt / 0.006) * 0.05 * vel
    out[:, 0] += h
    out[:, 1] += h * 0.9
    out *= np.minimum(1.0, tt / 0.004)[:, None]
    out *= vel * 0.5
    out[:, 0] *= gl * 1.41
    out[:, 1] *= gr * 1.41
    i0 = nsamp(t0)
    m = min(n, buf.shape[0] - i0)
    buf[i0:i0 + m] += out[:m]


def sub_note(buf, midi, t0, dur, att, rel, amp_db):
    f0 = float(midi_hz(midi))
    n = nsamp(dur)
    tt = np.arange(n) / SR
    env = cos_fade(tt / att) * (1 - cos_fade((tt - (dur - rel)) / rel)) * float(db(amp_db))
    y = (np.sin(2 * np.pi * f0 * tt) + 0.42 * np.sin(2 * np.pi * 2 * f0 * tt + 0.4)
         + 0.16 * np.sin(2 * np.pi * 3 * f0 * tt + 1.1)) * env
    i0 = nsamp(t0)
    m = min(n, buf.shape[0] - i0)
    buf[i0:i0 + m, 0] += y[:m]
    buf[i0:i0 + m, 1] += y[:m]


# ------------------------------------------------------------------ the arrangement
BEAT = 60.0 / 96.0              # 96 BPM: beat 0.625 s, bar 2.5 s


def chords():
    """(name, t_on, t_off, midi notes, amp_db per note). One chord change per bar or two (bar = 2.5 s); logo on bar 11 beat 3."""
    e = E
    return [
        ("D drone",       1.0,                 3.6,                  [38 + 12, 45 + 12, 50 + 12], -19.0),
        ("Dsus2",         2.5,                 3.75,                 [50, 57, 64, 69, 74],        -18.0),
        ("Bm11",          3.75,                5.0,                  [47, 54, 57, 62, 64],        -17.5),
        ("Dadd9 (wake)",  e["screen_wake"],    7.5,                  [50, 57, 62, 64, 66, 69],     -8.5),
        ("Bm9",           7.5,                 10.0,                 [47, 54, 57, 61, 62, 66],     -9.0),
        ("Gmaj9",         10.0,                12.5,                 [43, 50, 59, 62, 66, 69],     -9.0),
        ("Dmaj9",         12.5,                15.0,                 [50, 54, 57, 61, 64, 69],     -8.5),
        ("Bm9 b",         15.0,                17.5,                 [47, 54, 57, 61, 62, 66],     -9.0),
        ("Gmaj9 b",       17.5,                20.0,                 [43, 50, 59, 62, 66, 69],     -9.0),
        ("Em11",          20.0,                22.5,                 [40, 52, 59, 62, 67, 69],     -9.0),
        ("Dmaj9 (warm)",  22.5,                25.0,                 [50, 54, 57, 61, 64, 69],     -7.5),
        ("Gadd9",         25.0,                25.625,               [43, 50, 57, 59, 62, 66],    -10.0),
        ("Asus4",         25.625,              e["logo_signature"],  [45, 52, 57, 62, 64],        -10.0),
        ("Dadd9 (logo)",  e["logo_signature"], DUR + 1.5,            [50, 57, 62, 64, 66, 69, 74], -7.0),
    ]


ARP_BARS = [(7.5, [66, 69, 73, 74], 0.17), (10.0, [66, 71, 74, 78], 0.17), (12.5, [69, 73, 76, 78], 0.19), (15.0, [66, 69, 73, 76], 0.19),
            (17.5, [67, 71, 74, 78], 0.20), (20.0, [67, 71, 74, 79], 0.20), (22.5, [66, 69, 73, 78], 0.22)]


def keys_events():
    e = E
    ev = []

    def add(t, m, v, pan=0.0, bell=0.0):
        ev.append((t, m, v, pan, bell))
    # hero (bars 1-3): sparse notes while the light travels across the back of the phone and the phone turns
    add(1.9, 69, 0.26, -0.2); add(3.2, 76, 0.24, 0.2); add(4.0, 74, 0.20, -0.1); add(4.4, 78, 0.22, 0.25)
    # screen wakes: the motif A - D - F# - E
    t = e["screen_wake"]
    add(t + 0.15, 69, 0.42, -0.15); add(t + 0.60, 74, 0.44, 0.0); add(t + 1.25, 78, 0.40, 0.15); add(t + 1.85, 76, 0.34, 0.05)
    # the app (bars 4-9): a soft eighth-note arpeggio carries the picture; accents on the beats
    for t0, notes, vel in ARP_BARS:
        for k in range(8):
            tt = t0 + k * BEAT / 2
            if tt >= 25.0: break
            m = notes[[0, 1, 2, 3, 2, 1, 2, 3][k]]
            add(tt + 0.01 * ((k * 7) % 3), m, vel * (1.25 if k % 4 == 0 else 0.8), -0.25 if k % 2 == 0 else 0.25)
    # pull back (bar 10): warm lift, a longer melody note
    t = e["pull_back"]
    add(t + 0.35, 74, 0.36, 0.0); add(t + 1.2, 69, 0.30, -0.2); add(t + 1.8, 78, 0.32, 0.2)
    # bar 11-12: E then F# land on the logo and the slogan
    add(e["logo_signature"] + 0.0, 76, 0.40, -0.1); add(e["text_2"], 78, 0.46, 0.1, 0.2); add(28.7, 74, 0.30, 0.0)
    return ev


def render():
    pad = np.zeros((NT, 2))
    keys = np.zeros((NT, 2))
    sub = np.zeros((NT, 2))
    fc_fn = brightness()
    seed = 7000
    for ci, (name, t_on, t_off, notes, amp) in enumerate(chords()):
        long_att = 2.2 if ci in (0, 1) else 1.6
        rel = 2.2 if ci in (0, 1, 10) else 1.5
        if name.startswith("Asus4"):
            long_att, rel = 0.35, 0.5
        if name.startswith("Dadd9 (logo)"):
            long_att, rel = 0.45, 2.0
        norm = 1.0 / np.sqrt(len(notes))
        for ni, m in enumerate(notes):
            lowcut_db = -3.5 if m < 50 else (-1.5 if m < 55 else 0.0)          # keep the pad bass soft
            pad_note(pad, m, t_on, t_off, long_att, rel, amp + 20 * np.log10(norm) + 3.0 + lowcut_db, fc_fn, seed + ci * 31 + ni)
    # keys
    for i, (t, m, v, p, bell) in enumerate(keys_events()):
        key_note(keys, m, t, v, 7500 + i, pan=p, bell=bell)
    # sub: only three moments
    sub_note(sub, 38, E["screen_wake"], 3.4, 0.7, 1.6, -22.0)
    sub_note(sub, 38, E["pull_back"] + 0.2, 3.6, 0.9, 1.8, -23.0)
    sub_note(sub, 38, E["logo_signature"] + 0.2, 1.9, 0.12, 1.2, -24.0)

    pad_wet = reverb(pad, wet=0.40, dry=1.0, tail_keep=False, rt60=4.2, hf_damp=1.7, predelay=0.03, seed=7901)
    keys_wet = reverb(keys, wet=0.55, dry=1.0, tail_keep=False, rt60=3.3, hf_damp=1.3, predelay=0.022, seed=7902)
    mix = pad_wet * 1.0 + keys_wet * 1.0 + sub * 1.0

    t = np.arange(NT) / SR
    # opening: almost silent for ~1.2 s, then a slow bloom of the score
    open_env = db_curve([(0, -120), (0.8, -75), (1.6, -42), (3.0, -14), (4.6, 0)], n=NT)
    # ending: natural ring-out, then a raised-cosine finish that is exactly zero at 30.0 s
    uu = np.clip((t - 28.95) / (DUR - 28.95), 0, 1)
    end_env = (0.5 + 0.5 * np.cos(np.pi * uu)) ** 2
    end_env = np.where(t >= DUR, 0.0, end_env)
    mix = mix * (open_env * end_env)[:, None]
    # bus glue: gentle 3:1 peak-driven compression (zero-phase look-ahead) keeps the crest factor low, so the finished
    # mix can reach the loudness target with true-peak headroom and without any master limiting
    cs = np.cumsum(np.mean(mix[:N] ** 2, axis=1))
    st = np.sqrt((cs[SR:] - cs[:-SR]) / SR)                       # 1 s running RMS
    ref_db = 20 * np.log10(np.percentile(st[SR * 5:SR * 27], 85) + 1e-9)
    mix = compress(mix, ref_db + 5.0, ratio=2.5, smooth_ms=110.0)
    mix = shelf_lo(mix, 180.0, -3.0, width_oct=1.0)
    mix = highpass(mix, 28.0, order=2)
    mix = mix[:N]
    return mix


def build():
    print("MUSIC layer")
    x = render()
    save_asset(MUSIC_DIR, "lacrydia_score_v1.wav", x, "MUSIC", "whole film (all scenes)", 0.0,
               f"{NM}: additive warm pads (detuned saw stacks, automated low-pass), felt-piano additive keys, soft D2 sub "
               "at 3 moments, synthetic-IR FFT reverbs (pad rt60 4.2 s / keys 3.3 s); chord changes on config events; "
               "resolves to Dadd9 at logo_signature and rings out to a cosine finish at 30.000 s",
               pan_note="wide stereo pads (+-4.5 cent detune, 0.85/0.30 cross-feed); keys panned +-0.25",
               peak_target_db=-6.0, seed=7000, edge=(0.0, 1.0),
               description="30.000 s score; arc: near-silence -> pads -> sparse keys -> lift at screen_wake -> warm lift at pull_back -> resolve at logo")


if __name__ == "__main__":
    build()

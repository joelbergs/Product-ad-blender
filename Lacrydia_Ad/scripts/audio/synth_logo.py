"""LOGO layer: the Lacrydia sound signature (2.0 s file, the first note lands at 0.4 s == event logo_signature 28.4).

Design: a soft breath-in (0.0-0.4 s) -> two glass-bell notes A5 -> D6 (a rising perfect fourth: open, unresolved ->
resolved, the same A-D cell the score states earlier on the piano) -> a Dadd9 glass bloom (D5 A5 E6 F#6) over a very
soft D2/D3 sub. Everything rings out naturally in a small bright room and a final raised-cosine fade guarantees the
file reaches digital zero exactly at its end (t = 30.0 s), with the last 0.4 s already below -60 dB relative.
Original modal/additive synthesis, deterministic. Run: python3 synth_logo.py
"""
import numpy as np
from dsp_common import *  # noqa: F401,F403
from synth_whoosh import cfn

NM = "synth_logo.py"
H = lambda m: float(midi_hz(m))
DUR = 2.0
ANCHOR = 0.4


def bell(f0, t_start, amp, t60_scale=1.0, seed=0, dur=DUR):
    ratios = [1.0, 2.0, 2.99, 4.17, 5.43, 6.8]                # tubular-chime-like, slightly stretched
    amps = [1.0, 0.42, 0.26, 0.13, 0.07, 0.03]
    t60 = [1.5, 1.0, 0.65, 0.40, 0.25, 0.15]
    y = modal([f0 * r for r in ratios], [a * amp for a in amps], [t * t60_scale for t in t60], dur - t_start, seed=seed,
              attack_ms=1.2)
    return np.concatenate([np.zeros(nsamp(t_start)), y])[: nsamp(dur)]


def build_signature():
    n = nsamp(DUR)
    t = np.arange(n) / SR
    seed = 6001
    # 1) breath-in: airy swell 0 -> 0.4 s that stops just before the first note
    mask = sweep_mask(cfn([(0, 2800), (0.4, 7800), (DUR, 7800)]), cfn([(0, 0.8), (DUR, 0.8)]))
    b1 = stft_shape(white(n, seed), mask)
    b2 = stft_shape(white(n, seed + 1), mask)
    benv = np.where(t < ANCHOR, cos_fade(t / ANCHOR) ** 2, np.exp(-(t - ANCHOR) / 0.12)) * 0.5
    breath = np.stack([b1 / np.std(b1), b2 / np.std(b2)], axis=1) * benv[:, None] * 0.06
    # soft pad swell into the hit: A4 + E5 sines
    swell_env = np.where(t < ANCHOR, cos_fade(t / ANCHOR), np.exp(-(t - ANCHOR) / 0.25))
    pre = (sine(H(69), n) + 0.7 * sine(H(76), n)) * swell_env * 0.05
    out = breath + np.stack([pre, pre], axis=1)

    # 2) the two notes (A5 at 0.40 s, D6 at 0.62 s) - slight L/R weighting, A5 left-of-centre, D6 right-of-centre
    nA = bell(H(81), 0.40, 0.55, 0.8, seed=seed + 2)
    nD = bell(H(86), 0.62, 1.00, 1.15, seed=seed + 3)
    out += to_stereo(nA, -0.18) + to_stereo(nD, 0.14)

    # 3) Dadd9 glass bloom starting with the D6 (attack 0.18 s), detuned pairs for shimmer
    bloom = np.zeros((n, 2))
    r = rng(seed + 4)
    tt = np.clip(t - 0.62, 0, None)
    benv2 = cos_fade(tt / 0.18) * np.exp(-tt / 0.55) * (t >= 0.62)
    for m, a in [(74, 0.5), (81, 0.40), (88, 0.26), (90, 0.22), (86, 0.18)]:      # D5 A5 E6 F#6 D6
        f = H(m)
        bloom[:, 0] += a * sine(f * 0.9990, n, r.uniform(0, 6.28))
        bloom[:, 1] += a * sine(f * 1.0010, n, r.uniform(0, 6.28))
    out += bloom * benv2[:, None] * 0.30

    # 4) sub warmth: D2 + D3 (2nd harmonic) - soft attack, 0.6 s decay
    ts = np.clip(t - 0.58, 0, None)
    senv = cos_fade(ts / 0.07) * np.exp(-ts / 0.55) * (t >= 0.58)
    sub = (sine(H(38), n) + 0.5 * sine(H(50), n) + 0.18 * sine(H(57), n)) * senv * 0.26
    out += np.stack([sub, sub], axis=1)

    # 5) bright small room, then a guaranteed natural-sounding finish
    out = lowpass(out, 13500, order=1)
    out = reverb(out, wet=0.38, dry=1.0, tail_keep=False, rt60=1.5, hf_damp=1.5, predelay=0.014, seed=seed + 5)
    fin = db_curve([(0, 0), (1.15, -3), (1.6, -22), (1.85, -46), (2.0, -110)], n=n)     # shaped on top of natural decay
    tail = 1 - cos_fade((t - 1.55) / 0.45)
    out = out * (fin * np.where(t > 1.55, tail, 1.0))[:, None]
    return out


def build():
    print("LOGO layer")
    ev = events()
    x = build_signature()
    save_asset(SFX_DIR, "logo_signature.wav", x, "LOGO", "logo_signature", ANCHOR,
               f"{NM}: breath-in 0-0.4 s, glass-bell modal notes A5@0.40 s and D6@0.62 s (rising 4th), Dadd9 sine bloom "
               "(D5 A5 E6 F#6, +-0.1 % L/R detune), soft D2/D3 sub, bright 1.5 s room, final raised-cosine fade to zero at 2.0 s",
               pan_note="A5 left-of-centre (-0.18), D6 right (+0.14), bloom wide by +-10 cent detune; mono-safe",
               peak_target_db=-3.0, seed=6001, edge=(0.5, 5.0),
               description="logo signature; file starts at 28.0 (end_card), first note lands at 28.4; silent at 30.0")


if __name__ == "__main__":
    build()

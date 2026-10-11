"""MATERIAL (lens glint, first light) + INTERFACE (screen wake, 4 page swipes) layers.
Original synthesis only: modal synthesis (inharmonic, individually decaying partials), additive blooms, band-passed
noise. Deterministic. Run: python3 synth_material_ui.py
"""
import numpy as np
from dsp_common import *  # noqa: F401,F403
from synth_whoosh import cfn

NM = "synth_material_ui.py"
H = lambda m: float(midi_hz(m))


def stereo_pair(x, p_l, p_r=None):
    return to_stereo(x, p_l)


def lens_glint(seed=5001):
    """Two lens rings catching the light: glass-bowl-like modal partials, second ring a little later/softer."""
    r_ = [1.0, 2.76, 5.40, 8.93, 13.34]            # bowl/bar-like inharmonic ratios
    a_ = [1.0, 0.55, 0.34, 0.18, 0.08]
    T_ = [1.7, 1.05, 0.60, 0.32, 0.16]
    n = nsamp(3.0)
    f1 = H(86)                                      # D6-based ring (1174.7 Hz fundamental of the family)
    ring1 = modal([f1 * k for k in r_], a_, T_, 3.0, seed=seed, attack_ms=1.5)
    f2 = H(81) * 1.502                              # slightly detuned fifth above A5 -> an inharmonic, metallic partner
    ring2 = modal([f2 * k for k in r_[:4]], [0.7 * a for a in a_[:4]], [t * 0.85 for t in T_[:4]], 3.0, seed=seed + 1, attack_ms=1.5)
    ring2 = np.concatenate([np.zeros(nsamp(0.15)), ring2])[:n]
    tick = bandpass(white(n, seed + 2), 3500, 9000, order=1)
    tick = tick * np.exp(-np.arange(n) / SR / 0.0025) * 0.35
    tick = np.where(np.arange(n) / SR < 0.02, tick, 0)
    out = np.stack([ring1 * 0.9 + ring2 * 0.25 + tick, ring1 * 0.7 + ring2 * 0.45 + tick * 0.8], axis=1)
    out = lowpass(out, 12500, order=1)
    out = reverb(out, wet=0.28, rt60=1.6, hf_damp=1.4, tail_keep=False, seed=seed + 3, predelay=0.008)
    return out


def first_light(seed=5101):
    """A narrow strip of light grazing the frame edge: a thin high-frequency air glint, slowly rising then fading."""
    dur = 3.2
    n = nsamp(dur)
    fc = cfn([(0, 4200), (1.6, 7600), (dur, 5600)])
    mask = sweep_mask(fc, cfn([(0, 0.35), (dur, 0.45)]))
    a = stft_shape(white(n, seed), mask)
    b = stft_shape(white(n, seed + 1), mask)
    a, b = a / np.std(a), b / np.std(b)
    env = db_curve([(0, -80), (0.7, -22), (1.5, 0), (2.2, -10), (dur, -70)], n=n)
    air = np.stack([a, b], axis=1) * env[:, None]
    # one very faint modal ring where the light 'lands' on the edge
    ring = modal([H(93) * k for k in (1.0, 2.76, 5.4)], [1.0, 0.5, 0.2], [1.4, 0.8, 0.4], 2.0, seed=seed + 2)
    ring = np.concatenate([np.zeros(nsamp(1.3)), ring])[:n] * 0.18
    out = air * 0.25 + np.stack([ring * 0.8, ring * 1.0], axis=1)
    return reverb(out, wet=0.3, rt60=2.0, hf_damp=1.3, tail_keep=False, seed=seed + 3)


def screen_wake(seed=5201):
    """Soft digital bloom: upward-settling glass cluster, airy lift, a few 'pixel' grains. No beeps, no arcade."""
    dur = 2.4
    n = nsamp(dur)
    t = np.arange(n) / SR
    glide = 0.965 + 0.035 * smoothstep(t / 0.45)
    att = cos_fade(t / 0.5)
    dec = np.exp(-np.maximum(t - 0.55, 0) / 0.45)
    env = att * dec
    notes = [(74, 1.0), (81, 0.82), (86, 0.60), (90, 0.42), (93, 0.22)]       # D5 A5 D6 F#6 A6
    L = np.zeros(n)
    R = np.zeros(n)
    r = rng(seed)
    for m, a in notes:
        f = H(m)
        shimmer = 1 + 0.06 * np.sin(2 * np.pi * r.uniform(4.5, 7) * t + r.uniform(0, 6.28))
        L += a * sine(f * glide * 0.9988, n, r.uniform(0, 6.28)) * shimmer
        R += a * sine(f * glide * 1.0012, n, r.uniform(0, 6.28)) * shimmer
    cl = np.stack([L, R], axis=1) * env[:, None] * 0.5
    # warm body (D4 + A4) with slower attack
    body = (sine(H(62) * glide, n) + 0.7 * sine(H(69) * glide, n)) * cos_fade(t / 0.4) * np.exp(-np.maximum(t - 0.5, 0) / 0.4)
    cl += np.stack([body, body], axis=1) * 0.17
    # airy lift
    mask = sweep_mask(cfn([(0, 3500), (0.5, 7500), (dur, 6000)]), cfn([(0, 0.6), (dur, 0.7)]))
    a1 = stft_shape(white(n, seed + 1), mask)
    a2 = stft_shape(white(n, seed + 2), mask)
    aenv = db_curve([(0, -80), (0.2, -20), (0.5, 0), (1.1, -16), (dur, -70)], n=n)
    air = np.stack([a1 / np.std(a1), a2 / np.std(a2)], axis=1) * aenv[:, None] * 0.035
    # pixel grains: a handful of tiny sine grains 3-9 kHz between 0.12 and 0.9 s (pixels lighting up)
    px = np.zeros((n, 2))
    for k in range(34):
        t0 = r.uniform(0.12, 0.95)
        f = r.uniform(3000, 9000)
        g = int(0.004 * SR)
        w = np.hanning(g) * np.sin(2 * np.pi * f * np.arange(g) / SR + r.uniform(0, 6.28))
        amp = r.uniform(0.012, 0.04) * (1 - 0.5 * (t0 / 0.95))
        pan = r.uniform(-0.8, 0.8)
        gl, gr = pan_gains(pan)
        i = nsamp(t0)
        px[i:i + g, 0] += w * amp * gl
        px[i:i + g, 1] += w * amp * gr
    out = cl + air + px
    out = lowpass(out, 13500, order=1)
    return reverb(out, wet=0.30, rt60=1.9, hf_damp=1.3, tail_keep=False, seed=seed + 3, predelay=0.015)


def swipe(idx, f_tick, seed):
    """Very soft airy page swipe (0.55 s) + a tiny tuned tick when the page lands. Travels R -> L like the gesture."""
    dur = 1.0
    n = nsamp(dur)
    mask = sweep_mask(cfn([(0, 1300), (0.5, 3800)]), cfn([(0, 1.4), (0.5, 1.1)]))
    a = stft_shape(white(n, seed), mask)
    b = stft_shape(white(n, seed + 1), mask)
    c = stft_shape(white(n, seed + 2), mask)
    a, b, c = a / np.std(a), b / np.std(b), c / np.std(c)
    ind = 0.45
    com = c
    L = np.sqrt(1 - ind) * com + np.sqrt(ind) * a
    R = np.sqrt(1 - ind) * com + np.sqrt(ind) * b
    env = db_curve([(0, -70), (0.10, -13), (0.22, 0), (0.42, -9), (0.52, -26), (0.70, -60)], n=n)
    pan = curve([(0, 0.32), (0.55, -0.32)], n=n)
    gl, gr = pan_gains(pan)
    sw = np.stack([L * gl, R * gr], axis=1) * np.sqrt(2) * env[:, None]
    sw = highpass(sw, 600, order=2)
    sw = sw / np.max(np.abs(sw)) * 0.5
    # tick: filtered click + tiny tuned tink (page lands)
    t_tick = 0.47
    tk = np.zeros(n)
    i = nsamp(t_tick)
    m = n - i
    tt = np.arange(m) / SR
    click = bandpass(white(m, seed + 5), 2200, 7500, order=1) * np.exp(-tt / 0.0016)
    click = click / (np.max(np.abs(click)) + 1e-9) * 0.30
    tink = (np.sin(2 * np.pi * f_tick * tt) + 0.35 * np.sin(2 * np.pi * f_tick * 2.76 * tt + 1.0)) * np.exp(-tt / 0.045)
    tink *= np.minimum(1, tt / 0.0006) * 0.22
    tk[i:] = click + tink
    out = sw + to_stereo(tk, -0.3)
    out = reverb(out, wet=0.16, rt60=1.0, hf_damp=1.8, tail_keep=False, seed=seed + 6, predelay=0.006)
    return out


def build():
    ev = events()
    print("MATERIAL + INTERFACE layers")
    x = first_light()
    save_asset(SFX_DIR, "material_first_light.wav", x, "MATERIAL", "first_light", 0.0,
               f"{NM}: STFT band-limited noise 4.2->7.6->5.6 kHz (0.35 oct) + one faint modal ring, small room",
               pan_note="stereo, centred", peak_target_db=-6.0, seed=5101, edge=(5.0, 60.0),
               description="thin high air glint as the strip of light grazes the frame edge (t=2.3)")
    x = lens_glint()
    save_asset(SFX_DIR, "material_lens_glint.wav", x, "MATERIAL", "lens_glint", 0.0,
               f"{NM}: modal synthesis, 5 inharmonic partials (ratios 1/2.76/5.4/8.93/13.34, T60 1.7..0.16 s) + 2nd ring "
               "0.15 s later + 2 ms noise tick; small room",
               pan_note="ring 1 slightly left, ring 2 slightly right (L/R weights 0.9/0.7 and 0.25/0.45)",
               peak_target_db=-6.0, seed=5001, edge=(0.5, 80.0), description="single glass/metal accent at t=8.3")
    x = screen_wake()
    save_asset(SFX_DIR, "ui_screen_wake.wav", x, "INTERFACE", "screen_wake", 0.0,
               f"{NM}: D5-A5-D6-F#6-A6 sine bloom (glide -3.5 % -> 0 over 0.45 s, 0.5 s attack) + D4/A4 body + "
               "band-passed air + 34 random 4 ms sine 'pixel' grains + room",
               pan_note="stereo +-12 cents L/R detune; pixel grains random pan", peak_target_db=-4.0, seed=5201,
               edge=(3.0, 80.0), description="soft digital bloom when the display wakes (t=11.6, dur 0.8)")
    ticks = [H(86), H(88), H(90), H(93)]   # D6 E6 F#6 A6
    for i, (key, ft) in enumerate(zip(("swipe_1", "swipe_2", "swipe_3", "swipe_4"), ticks), start=1):
        x = swipe(i, ft, 4000 + i * 10)
        save_asset(SFX_DIR, f"ui_swipe_{i:02d}.wav", x, "INTERFACE", key, 0.0,
                   f"{NM}: band-passed noise 1.3->3.8 kHz (0.55 s, peak 0.22 s), R->L pan +0.32 -> -0.32, "
                   f"tick at 0.47 s: 2 ms noise click + tuned tink {ft:.0f} Hz ({['D6','E6','F#6','A6'][i-1]}), room 1 s",
                   pan_note="R->L subtle (+0.32 -> -0.32), matches a leftward swipe", peak_target_db=-6.0,
                   seed=4000 + i * 10, edge=(2.0, 50.0),
                   description=f"page swipe {i}: airy swish + tiny tick ({['D6','E6','F#6','A6'][i-1]})")


if __name__ == "__main__":
    build()

"""Original sound design + score for the Lacrydia film. Pure numpy synthesis (no samples, no third-party audio).

    python3 sound.py [--out ../../final] [--lufs -16]

Every cue is placed from the same timing tables that drive the animation (lib/choreo.py), so picture and sound stay in
sync by construction:  film start  --  A (macro glass) | B (orbit) | C (low hero) | D (pile) | E (detail) | F (Tree) | G (app) | H (mark)
"""
import argparse, json, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import dsp as D
from lib import choreo, tree

SR = D.SR
FILM = choreo.FILM
DUR = float(FILM["duration"])
N = D.nsamp(DUR)
S0 = choreo.START_OF

# ---- pitch material: D major / Lydian colour (Dsus2 -> Bm -> Gmaj7 -> Em9 -> Dmaj9) ----------------------------------
NOTE = {"D1": 36.71, "A1": 55.0, "D2": 73.42, "E2": 82.41, "G2": 98.0, "A2": 110.0, "B2": 123.47, "D3": 146.83, "E3": 164.81,
        "F#3": 185.0, "G3": 196.0, "A3": 220.0, "B3": 246.94, "C#4": 277.18, "D4": 293.66, "E4": 329.63, "F#4": 369.99,
        "G4": 392.0, "A4": 440.0, "B4": 493.88, "C#5": 554.37, "D5": 587.33, "E5": 659.25, "F#5": 739.99, "G5": 783.99,
        "A5": 880.0, "B5": 987.77, "D6": 1174.66}
f = NOTE.__getitem__
GLASS = ([1.0, 2.32, 4.25, 6.63, 9.38], [1.0, 0.50, 0.28, 0.14, 0.07], [1.0, 0.62, 0.40, 0.25, 0.16])
BELL = ([1.0, 2.0, 3.01, 4.2], [1.0, 0.30, 0.12, 0.05], [1.0, 0.5, 0.3, 0.18])


def stereo(x, pan=0.0):
    return D.to_stereo(x, pan)


def put(bus, x, t, gain_db=0.0):
    D.mix_into(bus, x, t, D.db(gain_db))


def modal_voice(freq, base_t60, partials=GLASS, attack_ms=2.0, seed=1, dur=None, pan=0.0):
    r, a, t6 = partials
    dur = dur or base_t60 * 1.3
    y = D.modal([freq * k for k in r], a, [base_t60 * k for k in t6], dur, seed=seed, attack_ms=attack_ms)
    return stereo(y, pan)


def tick(dur_ms=7, lo=2200, hi=7000, seed=3, level_db=-30):
    n = D.nsamp(dur_ms / 1000)
    x = D.bandpass(D.white(n + 400, seed)[: n + 400], lo, hi, order=1)[:n]
    x *= np.hanning(n * 2)[n:] ** 2 if n > 0 else 1
    return x / (np.max(np.abs(x)) + 1e-9) * D.db(level_db)


# ---- individual cues -----------------------------------------------------------------------------------------------
def swell(dur, peak_at, f_low=41.2, seed=5, air_level=-34):
    """deep, almost imperceptible low swell: sub-sine pair + dark brown noise, raised-cosine envelope."""
    n = D.nsamp(dur)
    t = np.arange(n) / SR
    env = np.where(t < peak_at, D.cos_fade(t / peak_at), 1 - D.cos_fade((t - peak_at) / max(dur - peak_at, 1e-6))) ** 1.6
    sub = np.sin(2 * np.pi * f_low * t) * 0.8 + np.sin(2 * np.pi * f_low * 2.005 * t) * 0.25
    air = D.lowpass(D.brown(n, seed), 260, order=2) * 0.12
    air_hi = D.bandpass(D.pink(n, seed + 1), 700, 3200, order=1) * D.db(air_level)
    x = (sub * 0.5 + air) * env + air_hi * env ** 2
    return stereo(x * 0.5)


def swoosh(dur, pan0, pan1, level_db=-30, seed=7, lo=400, hi=3800):
    """restrained stereo air that follows a camera orbit"""
    n = D.nsamp(dur)
    t = np.arange(n) / SR
    x = D.pink(n, seed)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    mask = D.sweep_mask(lambda tc: lo * (hi / lo) ** np.clip(tc / dur, 0, 1) ** 0.8, lambda tc: 0.9 + 0 * tc)
    y = D.stft_shape(x, mask) * env
    pan = np.linspace(pan0, pan1, n)
    return D.to_stereo(y / (np.max(np.abs(y)) + 1e-9) * D.db(level_db), pan)


def glass_resonance(freq, t60=3.4, attack_ms=140, pan=0.0, seed=2):
    """a bowed-glass bloom: soft attack so it feels like the highlight excites the object rather than strikes it"""
    y = modal_voice(freq, t60, GLASS, attack_ms=attack_ms, seed=seed, pan=pan)
    return y


def photo_accent(freq, pan=0.0, seed=1, level_db=0.0, t60=1.9):
    """soft, precise tonal accent as a photograph enters: pure bell + a barely audible tactile tap"""
    y = modal_voice(freq, t60, BELL, attack_ms=3.0, seed=seed, pan=pan)
    tp = stereo(tick(9, 1800, 6000, seed + 40, -26), pan)
    y[: len(tp)] += tp[: len(y)]
    return y * D.db(level_db)


def line_draw(f0, dur=1.7, pan=0.0, level_db=-24, seed=11):
    """harmonic pulse as a connection line draws: two sines (root + fifth) with a gently rising glide and a breathing amplitude"""
    n = D.nsamp(dur)
    t = np.arange(n) / SR
    u = np.clip(t / dur, 0, 1)
    glide = 1.0 + 0.012 * D.cos_fade(u)
    env = np.sin(np.pi * u) ** 2.2
    breathe = 0.78 + 0.22 * np.sin(2 * np.pi * 3.2 * t * (0.5 + 0.5 * u))
    y = (np.sin(2 * np.pi * f0 * np.cumsum(glide) / SR) + 0.5 * np.sin(2 * np.pi * f0 * 1.5 * np.cumsum(glide) / SR)
         + 0.18 * np.sin(2 * np.pi * f0 * 2.0 * t)) * env * breathe
    return stereo(y * D.db(level_db) * 0.5, pan)


def settle(level_db=-22):
    """tactile low 'settle' (soft thump, 0.5 s) used when the Tree reaches its final composition"""
    n = D.nsamp(0.7)
    t = np.arange(n) / SR
    fr = 92 * np.exp(-t * 4.0) + 48
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 6.5)
    y += D.lowpass(D.white(n, 31), 900, 1) * np.exp(-t * 28) * 0.18
    return stereo(y * D.db(level_db))


def chord_bloom(notes, t60=4.5, pan_spread=0.5, level_db=-26, seed=20, stagger=0.045):
    n = D.nsamp(t60 * 1.3 + 0.5)
    out = np.zeros((n, 2))
    for i, nm in enumerate(notes):
        y = modal_voice(f(nm), t60, GLASS, attack_ms=12, seed=seed + i, pan=(i / max(len(notes) - 1, 1) - 0.5) * 2 * pan_spread)
        D.mix_into(out, y, i * stagger)
    return out * D.db(level_db)


def screen_on(level_db=-26):
    n = D.nsamp(1.5)
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / 1.5, 0, 1)) ** 2
    fr = 300 * (1200 / 300) ** np.clip(t / 1.4, 0, 1) ** 1.5
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * env * 0.5 + D.bandpass(D.pink(n, 41), 1200, 7000, 1) * env * 0.12
    return stereo(y * D.db(level_db))


# ---- music ---------------------------------------------------------------------------------------------------------
def pad(notes, dur, seed, bright=0.5):
    """a slow, wide pad: detuned partial stacks with slow independent drift"""
    n = D.nsamp(dur)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    r = D.rng(seed)
    for i, nm in enumerate(notes):
        fr = f(nm)
        voice = np.zeros(n)
        for d in (-4.0, 0.0, 3.5):                                   # cents
            ff = fr * 2 ** (d / 1200.0)
            ph = r.uniform(0, 6.28)
            voice += np.sin(2 * np.pi * ff * t + ph)
            voice += 0.30 * bright * np.sin(2 * np.pi * ff * 2 * t + ph * 1.3)
            voice += 0.12 * bright * np.sin(2 * np.pi * ff * 3 * t + ph * 0.7)
        lfo = 0.80 + 0.20 * np.sin(2 * np.pi * (0.05 + 0.03 * i) * t + r.uniform(0, 6.28))
        voice *= lfo / 3.0
        pan = (-0.45 + 0.9 * (i / max(len(notes) - 1, 1))) * (0.6 if fr > 150 else 0.15)
        out += D.to_stereo(voice, pan) / np.sqrt(len(notes))
    return out


CHORDS = [   # (t0, t1, notes, level_db)   crossfaded
    (0.0, 6.5, ["D2", "A2"], -25.5),                                                    # A: just the foundation
    (4.0, 12.5, ["D2", "A2", "D3", "E3", "A3", "E4"], -20.5),                           # Dsus2: B
    (11.0, 16.5, ["B2", "F#3", "A3", "D4", "C#5"], -20.5),                              # Bm9: C
    (15.0, 23.0, ["G2", "D3", "F#3", "B3", "D4", "A4"], -19.5),                         # Gmaj7: D (the pile)
    (21.5, 26.5, ["E2", "B2", "D3", "F#3", "G3", "B3"], -20.5),                         # Em9: E (detail)
    (25.0, 30.5, ["G2", "D3", "F#3", "B3", "D4", "A4"], -18.5),                         # F: Tree starts to grow
    (29.0, 33.0, ["B2", "F#3", "A3", "D4", "C#5", "F#5"], -18.0),                     # Bm9: connections
    (31.5, 35.5, ["D2", "A2", "F#3", "A3", "C#4", "E4", "A4"], -17.5),                  # Dmaj9: the place
    (34.5, 39.5, ["D2", "A2", "D3", "F#3", "A3", "C#4", "E4"], -18.0),                # G: app, resolved
    (38.0, 46.0, ["D2", "A2", "D3", "E3", "A3", "D4", "F#4", "A4"], -17.5),             # H: final
]


def music_bed():
    bed = np.zeros((N, 2))
    xf = 1.4
    for k, (t0, t1, notes, lvl) in enumerate(CHORDS):
        dur = min(t1, DUR + 0.5) - t0
        y = pad(notes, dur, seed=100 + k, bright=0.4 + 0.07 * k)
        n = len(y)
        t = np.arange(n) / SR
        env = D.cos_fade(t / xf) * (1 - D.cos_fade((t - (dur - xf)) / xf))
        y *= env[:, None] * D.db(lvl)
        D.mix_into(bed, y, t0)
    # warm dark filter that opens as the film grows (700 Hz -> 4.5 kHz), done with STFT so it is smooth
    def fc(tc):
        return 650.0 * (4800.0 / 650.0) ** np.clip((tc - 3.0) / 34.0, 0, 1) ** 0.9
    for ch in range(2):
        bed[:, ch] = D.stft_shape(bed[:, ch], lambda tc, fr: 1.0 / (1.0 + (fr[None, :] / fc(tc)[:, None]) ** 4))
    # sub foundation: D1 breathing underneath, but never boomy
    t = np.arange(N) / SR
    sub = np.sin(2 * np.pi * NOTE["D1"] * t) * D.curve([(0, 0), (1.5, 0.35), (8, 0.5), (36, 0.55), (40, 0.5), (DUR, 0.0)], n=N)
    sub *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t) ** 2
    bed += stereo(sub * D.db(-30))
    return bed


def pulse_layer(t0, t1, bpm=85.0, level_db=-33):
    """a restrained rhythmic element: soft filtered ticks on off-beats, fading in/out (Tree section only)"""
    out = np.zeros((N, 2))
    beat = 60.0 / bpm
    k = 0
    tt = t0
    while tt < t1:
        env = D.cos_fade((tt - t0) / 3.0) * (1 - D.cos_fade((tt - (t1 - 3.0)) / 3.0)) if t1 - t0 > 6 else 1.0
        if k % 2 == 1:
            y = tick(14, 3000, 8000, seed=300 + k, level_db=-6) * 1.0
            y2 = tick(60, 90, 220, seed=500 + k, level_db=-14)
            m = max(len(y), len(y2)); z = np.zeros(m); z[: len(y)] += y; z[: len(y2)] += y2 * 0.0
            D.mix_into(out, stereo(z, -0.25 + 0.5 * ((k // 2) % 2)), tt, D.db(level_db + 20 * np.log10(max(env, 1e-4))))
        else:
            thump = np.sin(2 * np.pi * np.cumsum(60 + 70 * np.exp(-np.arange(D.nsamp(0.35)) / SR * 22)) / SR) * np.exp(-np.arange(D.nsamp(0.35)) / SR * 9)
            D.mix_into(out, stereo(thump * 0.8), tt, D.db(level_db - 4 + 20 * np.log10(max(env, 1e-4))))
        tt += beat * 0.5
        k += 1
    return out


# ---- the cue sheet: (film time, name, builder) ---------------------------------------------------------------------
def build_cues():
    cues = []
    add = lambda t, name, y, gain=0.0: cues.append(dict(t=float(t), name=name, y=y, gain=gain))
    # ---- A: macro edge (0-5)
    add(0.25, "A_swell", swell(4.6, 2.6, 41.2, seed=5), -9.0)
    add(0.55 + (1.3), "A_glass_resonance_1", glass_resonance(f("D5"), 3.8, 160, -0.35), -17)       # as the highlight enters the edge
    add(2.55, "A_glass_resonance_2", glass_resonance(f("A5"), 3.0, 120, -0.25), -23)
    add(3.62, "A_mark_emerges", chord_bloom(["D4", "A4", "D5"], 3.2, 0.3, -20, 8), 0.0)            # the engraved mark catches the light
    add(3.88, "A_mark_tick", stereo(tick(12, 2500, 9000, 9, -28), -0.2), 0.0)
    # ---- B: orbit (5-11.5), hero photograph wakes
    add(S0["B"] + 0.2, "B_orbit_air", swoosh(6.2, -0.55, 0.55, -31, 7), 0.0)
    add(S0["B"] + choreo.B_WAKE[0] + 0.45, "B_photo_enters", photo_accent(f("A4"), 0.0, 3, 0.0), -15)
    add(S0["B"] + choreo.B_WAKE[0] + 1.1, "B_photo_enters_hi", photo_accent(f("E5"), 0.12, 4, 0.0, 1.4), -24)
    # ---- C: low hero (11.5-15.5): two more photographs wake in depth
    add(S0["C"] + 1.2, "C_photo2", photo_accent(f("F#4"), 0.45, 5, 0.0), -18)
    add(S0["C"] + 2.1, "C_photo3", photo_accent(f("B4"), -0.5, 6, 0.0), -19)
    add(S0["C"] + 0.0, "C_air", swoosh(3.8, 0.4, -0.4, -34, 8), 0.0)
    # ---- D: the scanner reveals the pile (each card its own note, pitch follows position left -> right)
    scale = ["D4", "E4", "F#4", "A4", "B4", "C#5", "D5", "E5", "F#5", "A5", "B5", "D6"]
    ev = choreo.card_events()
    for k, (t, nid, x) in enumerate(ev):
        u = np.clip((x + 0.5) / 1.0, 0, 0.999)
        note = scale[int(u * len(scale))]
        add(t + 0.18, f"D_card_{nid}", photo_accent(f(note), float(np.clip(x * 1.6, -0.8, 0.8)), 30 + k, 0.0, 1.5), -22 - (0 if k % 3 else 2))
    add(S0["D"] + 0.45, "D_scanner_air", swoosh(5.4, -0.8, 0.8, -30, 12), 0.0)
    # ---- E: detail, the first line leaves the card
    add(S0["E"] + 0.0, "E_swell", swell(3.4, 2.4, 55.0, seed=15), -4)
    le = choreo.line_events()
    first = le[0]
    add(first[0] - 0.1, "E_line_first", line_draw(f("D4"), 1.9, -0.1, -22), 0.0)
    # ---- F: the Tree
    lines = {c: (a, b, lv) for a, b, c, lv in le}
    base = dict(travel="E4", nature="F#4", friends="A4", cars="B4")
    for c, (a, b, lv) in lines.items():
        if c == "travel":
            pass
        parent = tree.BY_ID[c]["parent"]
        if lv == 1:
            add(a - 0.05 if c != "travel" else b - 0.2, f"F_line_{c}", line_draw(f(base[c]), choreo.LINE_T, 0.0, -27), 0.0)
            add(b + 0.55, f"F_node_{c}", photo_accent(f(base[c].replace("4", "5")), float(np.clip(tree.BY_ID[c]["xy"][0] * 1.6, -0.7, 0.7)), 60, 0.0, 2.2), -24)
        else:
            note = ["E5", "F#5", "A5", "B5", "C#5", "D5"][(abs(hash(c)) % 6)]
            add(b + 0.1, f"F_leaf_{c}", photo_accent(f(note), float(np.clip(tree.BY_ID[c]["xy"][0] * 1.6, -0.8, 0.8)), 70 + len(c), 0.0, 1.2), -30)
    add(S0["F"] + 7.75, "F_settle", settle(-24), 0.0)
    add(S0["F"] + 7.7, "F_final_bloom", chord_bloom(["D3", "A3", "F#4", "A4", "C#5", "E5"], 5.0, 0.55, -21, 40), 0.0)
    add(S0["F"] + 0.3, "F_air", swoosh(8.0, 0.0, 0.0, -35, 17, 300, 2600), 0.0)
    # ---- G: the app screen
    add(S0["G"] + choreo.G_WAKE[0], "G_screen_on", screen_on(-22), 0.0)
    add(S0["G"] + choreo.G_WAKE[1] - 0.15, "G_screen_chord", chord_bloom(["D4", "A4", "F#5"], 3.4, 0.25, -23, 50), 0.0)
    add(S0["G"] + choreo.G_SWAP[0], "G_swap", photo_accent(f("E5"), 0.1, 51, 0.0, 1.3), -22)
    # ---- H: the nine slits, then the resolution
    slit_notes = ["D4", "E4", "F#4", "A4", "B4", "C#5", "D5", "F#5", "A5"]
    for i, nm in enumerate(slit_notes):
        t = S0["H"] + choreo.H_T0 + i * choreo.H_STEP
        add(t + 0.05, f"H_slit_{i+1}", modal_voice(f(nm), 2.4 + 0.1 * i, GLASS, 1.5, seed=80 + i, pan=-0.35 + 0.7 * i / 8), -22 + 0.5 * i)
    t_res = S0["H"] + choreo.H_T0 + 8 * choreo.H_STEP + 0.55
    add(t_res, "H_logo_resolution", chord_bloom(["D2", "A2", "D3", "F#3", "A3", "E4", "D5"], 5.5, 0.5, -15, 90, 0.06), 0.0)
    add(t_res + 0.05, "H_resolution_low", settle(-26), 0.0)
    return cues


# long-form dynamics: begin almost silent, grow through the Tree, breathe at the app, bloom on the mark, fall away
GAIN_CURVE = [(0, -9), (3.5, -6), (5.5, -2), (12, -1.5), (15.5, -2.5), (22, -3), (25.5, -1.5), (31, +1.5), (34, 0.5), (36, -1.5),
              (39, -0.5), (41.8, +1.5), (44.5, -3)]


def master(x, target_lufs):
    x = x.copy()
    g_t = D.db_curve(GAIN_CURVE, n=len(x))
    x *= g_t[:, None]
    x = D.highpass(x, 24.0, order=1)
    x = D.compress(x, -11.0, 2.2, 140.0)
    x = D.compress(x, -13.0, 10.0, 18.0)                      # fast peak catcher: bell transients must not set the overall level
    # fade-in/out at the extremes
    t = np.arange(len(x)) / SR
    g = D.cos_fade(t / 0.6) * (1 - D.cos_fade((t - (DUR - 1.6)) / 1.5))
    x *= g[:, None]
    wav = os.path.join(HERE, "..", "..", "build", "_tmp_master.wav")
    os.makedirs(os.path.dirname(wav), exist_ok=True)
    D.write_wav24(wav, x / max(1.0, np.max(np.abs(x)) * 1.001))
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", wav, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    lufs = float([l for l in r.stderr.splitlines() if " I:" in l][-1].split("I:")[1].split("LUFS")[0])
    gain = target_lufs - lufs
    return x * 10 ** (gain / 20), lufs, gain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "final"))
    ap.add_argument("--stems", default=os.path.join(HERE, "..", "..", "assets", "audio"))
    ap.add_argument("--lufs", type=float, default=-16.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); os.makedirs(a.stems, exist_ok=True)
    print("music bed ...", flush=True)
    bed = music_bed()
    bed += pulse_layer(S0["F"] + 1.0, S0["G"] + 0.2, 85.0, -22)
    cues = build_cues()
    fx_dry = np.zeros((N + SR * 6, 2))
    print(f"{len(cues)} cues ...", flush=True)
    for c in cues:
        put(fx_dry, c["y"], c["t"], c["gain"])
    fx_dry = fx_dry[:N + SR * 4]
    # shared spaces: a close warm room (0.9 s) and a long dark hall (5 s) fed in parallel
    print("reverb ...", flush=True)
    hall = D.make_ir(rt60=4.8, predelay=0.03, hf_damp=1.6, seed=3)
    room = D.make_ir(rt60=1.2, predelay=0.008, hf_damp=1.2, seed=4)
    wet_h = D.convolve_fft(fx_dry, hall)[:N]
    wet_r = D.convolve_fft(fx_dry, room)[:N]
    fx = fx_dry[:N] * D.db(-1.0) + wet_h * D.db(5.5) + wet_r * D.db(1.0)
    bed_wet = D.convolve_fft(bed, hall)[:N]
    music = bed + bed_wet * D.db(-4.0)
    mix = music * D.db(0.0) + fx
    mix, lufs_raw, gain = master(mix, a.lufs)
    peak = float(np.max(np.abs(mix)))
    if peak > 0.84:                                   # keep true-peak safe (-1 dBFS)
        mix *= 0.84 / peak
    print(f"raw {lufs_raw:.1f} LUFS, gain {gain:+.1f} dB, peak {20*np.log10(np.max(np.abs(mix))):.2f} dBFS", flush=True)
    D.write_wav24(os.path.join(a.out, "audio_mix.wav"), mix)
    D.write_wav24(os.path.join(a.stems, "music_bed.wav"), np.clip(music * D.db(gain), -1, 1) * 0.84 / max(1.0, 1))
    D.write_wav24(os.path.join(a.stems, "fx_events.wav"), np.clip(fx * D.db(gain), -1, 1) * 0.84)
    # individual cue stems (each fully rendered with its own tail) for editing / licensing documentation
    cdir = os.path.join(a.stems, "cues"); os.makedirs(cdir, exist_ok=True)
    cue_log = []
    for c in cues:
        y = c["y"] * D.db(c["gain"])
        y = y / max(1.0, np.max(np.abs(y)) * 1.05)
        D.write_wav24(os.path.join(cdir, c["name"] + ".wav"), y)
        cue_log.append(dict(t=round(c["t"], 3), name=c["name"], gain_db=c["gain"], length_s=round(len(c["y"]) / SR, 2)))
    json.dump(dict(duration=DUR, sample_rate=SR, target_lufs=a.lufs, cues=cue_log), open(os.path.join(a.out, "audio_cues.json"), "w"), indent=1)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(a.out, "audio_mix.wav"), "-c:a", "aac", "-b:a", "320k",
                    os.path.join(a.out, "audio_mix.m4a")], check=True)
    print("done ->", a.out)


if __name__ == "__main__":
    main()

"""Shared DSP + I/O helpers for the Lacrydia sound design (numpy only, deterministic).

Everything here is original code; no third-party samples are used anywhere in the audio chain.
Convention: audio is float64 numpy, shape (n,) mono or (n, 2) stereo, sample rate 48 kHz.
"""
import json
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # ROOT/scripts  (paths.py)
from paths import ROOT, assert_writable, cfg        # noqa: E402

SR = 48000
FPS = 30
SFX_DIR = os.path.join(ROOT, "assets", "audio", "sfx")
MUSIC_DIR = os.path.join(ROOT, "assets", "audio", "music")
MANIFEST = os.path.join(ROOT, "assets", "audio", "manifest.json")


# --------------------------------------------------------------------------- basics
def events():
    """config events as {id: t_seconds}."""
    return {e["id"]: e["t"] for e in cfg()["events"]}


def t_to_frame(t, fps=FPS):
    """Blender frame number (timeline starts at frame 1 == t 0.0)."""
    return int(round(t * fps)) + 1


def frame_to_t(frame, fps=FPS):
    return (frame - 1) / fps


def db(x):
    return 10.0 ** (np.asarray(x, dtype=float) / 20.0)


def to_db(x, floor=-200.0):
    return 20.0 * np.log10(np.maximum(np.abs(x), 10 ** (floor / 20)))


def nsamp(sec):
    return int(round(sec * SR))


def taxis(sec):
    return np.arange(nsamp(sec)) / SR


def midi_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def rng(seed):
    return np.random.default_rng(seed)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def cos_fade(x):
    """0..1 -> 0..1 raised-cosine ramp."""
    x = np.clip(x, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def curve(points, n=None, sec=None, kind="cos"):
    """Piecewise smooth curve through (t_sec, value) points sampled at SR.
    kind 'cos' = cosine interpolation between knots (zero slope at knots), 'lin' = linear."""
    pts = sorted(points)
    ts = np.array([p[0] for p in pts], dtype=float)
    vs = np.array([p[1] for p in pts], dtype=float)
    if n is None:
        n = nsamp(sec if sec is not None else ts[-1])
    t = np.arange(n) / SR
    if kind == "lin":
        return np.interp(t, ts, vs)
    idx = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 2)
    t0, t1 = ts[idx], ts[idx + 1]
    u = np.clip((t - t0) / np.maximum(t1 - t0, 1e-9), 0, 1)
    w = 0.5 - 0.5 * np.cos(np.pi * u)
    out = vs[idx] + (vs[idx + 1] - vs[idx]) * w
    out = np.where(t < ts[0], vs[0], out)
    out = np.where(t > ts[-1], vs[-1], out)
    return out


def db_curve(points, n=None, sec=None):
    """Curve specified in dB (use -120 for 'silence'), returned as linear gain, interpolated in dB."""
    return db(curve(points, n=n, sec=sec))


def adsr(n, a, d, s, r, curve_pow=1.0):
    """simple raised-cosine ADSR for n samples (times in seconds, s = sustain level)."""
    A, D, R = nsamp(a), nsamp(d), nsamp(r)
    env = np.ones(n) * s
    A = min(A, n)
    env[:A] = cos_fade(np.arange(A) / max(A, 1))
    if D > 0 and A < n:
        D = min(D, n - A)
        env[A:A + D] = s + (1 - s) * (1 - cos_fade(np.arange(D) / D))
    if R > 0:
        R = min(R, n)
        env[n - R:] *= 1 - cos_fade(np.arange(R) / R)
    return env ** curve_pow


def edge_fade(x, in_ms=3.0, out_ms=12.0):
    """guarantee start/end at zero (no clicks)."""
    x = np.array(x, dtype=float, copy=True)
    n = len(x)
    a, b = min(nsamp(in_ms / 1000), n), min(nsamp(out_ms / 1000), n)
    if a:
        r = cos_fade(np.arange(a) / a)
        x[:a] *= r if x.ndim == 1 else r[:, None]
    if b:
        r = 1 - cos_fade(np.arange(b) / b)
        x[n - b:] *= r if x.ndim == 1 else r[:, None]
    return x


def pad_to(x, n):
    if len(x) >= n:
        return x[:n]
    shp = (n - len(x),) + x.shape[1:]
    return np.concatenate([x, np.zeros(shp)])


def mix_into(dst, src, start_sec, gain=1.0):
    s = nsamp(start_sec)
    if s >= len(dst):
        return
    e = min(len(dst), s + len(src))
    dst[s:e] += src[: e - s] * gain


def pan_gains(p):
    """equal-power pan law, p in [-1 (L), +1 (R)] (scalar or per-sample)."""
    p = np.clip(np.asarray(p, dtype=float), -1, 1)
    ang = (p + 1.0) * np.pi / 4.0
    return np.cos(ang), np.sin(ang)


def to_stereo(x, p=0.0):
    gl, gr = pan_gains(p)
    return np.stack([x * gl, x * gr], axis=1)


# --------------------------------------------------------------------------- filters (FFT, zero phase)
def _fft_apply(x, resp_fn):
    x = np.asarray(x, dtype=float)
    n = x.shape[0]
    N = 1 << int(np.ceil(np.log2(n * 2 + 8)))
    X = np.fft.rfft(x, n=N, axis=0)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    H = resp_fn(f)
    if x.ndim == 2:
        H = H[:, None]
    return np.fft.irfft(X * H, n=N, axis=0)[:n]


def lowpass(x, fc, order=2):
    """zero-phase Butterworth-magnitude low-pass (|H|^2 of order*2 pole -> order*2 effective slope)."""
    return _fft_apply(x, lambda f: 1.0 / (1.0 + (f / fc) ** (2 * order * 2)))


def highpass(x, fc, order=2):
    def r(f):
        with np.errstate(divide="ignore", invalid="ignore"):
            h = 1.0 / (1.0 + (fc / np.maximum(f, 1e-6)) ** (2 * order * 2))
        h[0] = 0.0
        return h
    return _fft_apply(x, r)


def bandpass(x, f1, f2, order=2):
    def r(f):
        with np.errstate(divide="ignore", invalid="ignore"):
            hp = 1.0 / (1.0 + (f1 / np.maximum(f, 1e-6)) ** (2 * order * 2))
        lp = 1.0 / (1.0 + (f / f2) ** (2 * order * 2))
        h = hp * lp
        h[0] = 0.0
        return h
    return _fft_apply(x, r)


def peak_eq(x, f0, gain_db, q=1.0):
    """smooth bell EQ in the frequency domain (log-frequency gaussian)."""
    def r(f):
        with np.errstate(divide="ignore"):
            lf = np.log2(np.maximum(f, 1.0) / f0)
        return 10 ** (gain_db / 20.0 * np.exp(-0.5 * (lf * q * 2.0) ** 2))
    return _fft_apply(x, r)


def shelf_hi(x, f0, gain_db, width_oct=1.0):
    def r(f):
        with np.errstate(divide="ignore"):
            lf = np.log2(np.maximum(f, 1.0) / f0)
        w = 0.5 * (1 + np.tanh(lf / width_oct * 2))
        return 10 ** (gain_db * w / 20.0)
    return _fft_apply(x, r)


def shelf_lo(x, f0, gain_db, width_oct=1.0):
    def r(f):
        with np.errstate(divide="ignore"):
            lf = np.log2(np.maximum(f, 1.0) / f0)
        w = 0.5 * (1 - np.tanh(lf / width_oct * 2))
        return 10 ** (gain_db * w / 20.0)
    return _fft_apply(x, r)


# --------------------------------------------------------------------------- STFT time-varying band shaping
def stft_shape(x, mask_fn, win=2048, hop=512):
    """Apply a time/frequency magnitude mask to mono x. mask_fn(t_centres[s], freqs[Hz]) -> (frames, bins)."""
    n = len(x)
    w = np.hanning(win + 1)[:-1]
    xp = np.concatenate([np.zeros(win), x, np.zeros(win + hop)])
    nfr = (len(xp) - win) // hop + 1
    idx = np.arange(win)[None, :] + hop * np.arange(nfr)[:, None]
    S = np.fft.rfft(xp[idx] * w, axis=1)
    centres = (hop * np.arange(nfr) + win / 2 - win) / SR
    freqs = np.fft.rfftfreq(win, 1.0 / SR)
    S = S * mask_fn(centres, freqs)
    fr = np.fft.irfft(S, n=win, axis=1) * w
    y = np.zeros(len(xp))
    ws = np.zeros(len(xp))
    w2 = w * w
    for i in range(nfr):
        y[i * hop:i * hop + win] += fr[i]
        ws[i * hop:i * hop + win] += w2
    y = y / np.maximum(ws, 1e-6)
    return y[win:win + n]


def sweep_mask(fc_fn, bw_fn, floor=0.0):
    """Gaussian band (in octaves) around a moving centre frequency. fc_fn/bw_fn: callables of time (s)."""
    def m(tc, f):
        fc = np.asarray(fc_fn(tc))[:, None]
        bw = np.asarray(bw_fn(tc))[:, None]
        lf = np.log2(np.maximum(f[None, :], 1.0) / fc)
        g = np.exp(-0.5 * (lf / bw) ** 2)
        return floor + (1 - floor) * g
    return m


# --------------------------------------------------------------------------- noise
def white(n, seed):
    return rng(seed).standard_normal(n)


def pink(n, seed):
    """FFT-shaped 1/f noise, normalised to unit std."""
    x = white(n, seed)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    X[1:] /= np.sqrt(f[1:])
    X[0] = 0
    y = np.fft.irfft(X, n=n)
    return y / (np.std(y) + 1e-12)


def brown(n, seed):
    x = white(n, seed)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    X[1:] /= f[1:]
    X[0] = 0
    y = np.fft.irfft(X, n=n)
    return y / (np.std(y) + 1e-12)


def slow_noise(n, seed, rate_hz=0.2):
    """smooth random control signal in [-1, 1] with ~rate_hz bandwidth."""
    x = white(n, seed)
    y = lowpass(x, rate_hz, order=1)
    y /= (np.max(np.abs(y)) + 1e-12)
    return y


# --------------------------------------------------------------------------- reverb (synthetic impulse response + FFT convolution)
def make_ir(rt60=3.0, predelay=0.02, hf_damp=1.0, seed=1, early=True, length=None, lowcut=90.0):
    """Stereo synthetic reverb IR: decaying band-split noise (highs decay faster) + sparse early reflections.
    hf_damp: 1 = normal, >1 darker/faster HF decay. Returns (n,2), unit energy per channel."""
    L = length if length is not None else rt60 * 1.15
    n = nsamp(L)
    t = np.arange(n) / SR
    bands = [(0, 250, 1.15), (250, 1500, 1.0), (1500, 5000, 0.62 / hf_damp), (5000, 20000, 0.32 / hf_damp)]
    out = np.zeros((n, 2))
    for ch in range(2):
        r = rng(seed * 10 + ch)
        base = r.standard_normal(n)
        acc = np.zeros(n)
        for lo, hi, mult in bands:
            if lo == 0:
                b = lowpass(base, hi, order=1)
            elif hi >= 20000:
                b = highpass(base, lo, order=1)
            else:
                b = bandpass(base, lo, hi, order=1)
            acc += b * np.exp(-6.9078 * t / (rt60 * mult))
        # soft onset
        acc *= np.minimum(1.0, t / 0.012)
        if early:
            for k in range(10):
                d = r.uniform(0.004, 0.070)
                i = int(d * SR)
                if i < n:
                    acc[i] += r.choice([-1, 1]) * r.uniform(0.6, 1.4) * np.exp(-d / 0.05) * np.std(acc[:4000] + 1e-9) * 6
        acc = highpass(acc, lowcut, order=1)
        pd = nsamp(predelay + ch * 0.0007)
        out[pd:, ch] = acc[: n - pd]
    out /= np.sqrt(np.sum(out ** 2, axis=0, keepdims=True)) + 1e-12
    return out


def convolve_fft(x, ir):
    """FFT convolution; x (n,) or (n,2), ir (m,2). Returns stereo of length n+m-1."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n, m = len(x), len(ir)
    N = 1 << int(np.ceil(np.log2(n + m)))
    X = np.fft.rfft(x, n=N, axis=0)
    H = np.fft.rfft(ir, n=N, axis=0)
    y = np.fft.irfft(X * H, n=N, axis=0)[: n + m - 1]
    return y


def reverb(x, wet=0.3, dry=1.0, tail_keep=True, **ir_kw):
    ir = make_ir(**ir_kw)
    w = convolve_fft(x, ir)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = len(w) if tail_keep else len(x)
    out = np.zeros((n, 2))
    out[: len(x)] += x * dry
    out += pad_to(w, n) * wet
    return out


# --------------------------------------------------------------------------- oscillators / modal synthesis
def sine(freq, n, phase=0.0):
    """freq scalar or per-sample array in Hz."""
    if np.isscalar(freq):
        return np.sin(2 * np.pi * freq * np.arange(n) / SR + phase)
    ph = 2 * np.pi * np.cumsum(freq[:n]) / SR + phase
    return np.sin(ph)


def modal(freqs, amps, t60s, dur, seed=0, attack_ms=0.8, rand_phase=True):
    """Modal synthesis of a struck object: inharmonic partials with individual exponential decays."""
    n = nsamp(dur)
    t = np.arange(n) / SR
    r = rng(seed)
    y = np.zeros(n)
    for f, a, T in zip(freqs, amps, t60s):
        if f >= SR / 2 * 0.95:
            continue
        ph = r.uniform(0, 2 * np.pi) if rand_phase else 0.0
        y += a * np.sin(2 * np.pi * f * t + ph) * np.exp(-6.9078 * t / T)
    y *= np.minimum(1.0, t / (attack_ms / 1000))
    return y


# --------------------------------------------------------------------------- level tools
def peak_db(x):
    return float(20 * np.log10(np.max(np.abs(x)) + 1e-12))


def rms_db(x):
    return float(10 * np.log10(np.mean(np.square(x)) + 1e-18))


def normalize_peak(x, target_db=-3.0):
    p = np.max(np.abs(x)) + 1e-12
    return x * (db(target_db) / p)


def dc_block(x, fc=25.0):
    return highpass(x, fc, order=1)


# --------------------------------------------------------------------------- I/O
def write_wav24(path, x):
    """Write 24-bit PCM WAV, 48 kHz. x float (n,) or (n,2), |x| <= 1."""
    assert_writable(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    if np.max(np.abs(x)) > 1.0:
        raise ValueError(f"{path}: clipping before write (peak {np.max(np.abs(x)):.3f})")
    v = np.round(x * 8388607.0).astype(np.int32)
    b = np.empty((v.shape[0], v.shape[1], 3), dtype=np.uint8)
    b[..., 0] = v & 0xFF
    b[..., 1] = (v >> 8) & 0xFF
    b[..., 2] = (v >> 16) & 0xFF
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b.tobytes())


def read_wav(path):
    """Read PCM 16/24/32-bit WAV written by this toolkit or by Blender (S24); returns (n,2) float."""
    with wave.open(path, "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 3:
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v / 8388608.0
    elif sw == 2:
        x = np.frombuffer(raw, dtype="<i2") / 32768.0
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<i4") / 2147483648.0
    else:
        raise ValueError(sw)
    x = x.reshape(-1, ch)
    if ch == 1:
        x = np.repeat(x, 2, axis=1)
    return x, sr


def read_any(path, scratch=None):
    """Read any audio (incl. float WAV from Blender) as float64 (n,2) @48k via ffmpeg."""
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64).reshape(-1, 2)


def _load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"sample_rate": SR, "channels": 2, "format": "24-bit PCM WAV", "fps": FPS,
            "frame_convention": "frame = round(t*fps)+1 ; t = (frame-1)/fps", "files": {}}


def save_asset(folder, name, x, layer, event, anchor_s, method, pan_note="", peak_target_db=-3.0,
               normalize=True, seed=None, edge=(2.0, 15.0), description=""):
    """Declick, normalise, write a stereo asset and register it in the manifest.
    anchor_s = time inside the file at which the event 'lands' (must be a whole number of frames)."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = dc_block(x, 20.0)
    x = edge_fade(x, *edge)
    if normalize:
        x = normalize_peak(x, peak_target_db)
    x = np.clip(x, -0.999, 0.999)
    path = os.path.join(folder, name)
    write_wav24(path, x)
    anchor_frames = int(round(anchor_s * FPS))
    assert abs(anchor_frames / FPS - anchor_s) < 1e-9, f"{name}: anchor {anchor_s}s is not a whole number of frames"
    m = _load_manifest()
    rel = os.path.relpath(path, ROOT)
    m["files"][rel] = {
        "layer": layer, "event": event, "anchor_s": anchor_s, "anchor_frames": anchor_frames,
        "duration_s": round(len(x) / SR, 4), "samples": int(len(x)),
        "peak_dbfs": round(peak_db(x), 2), "rms_dbfs": round(rms_db(x), 2),
        "method": method, "pan": pan_note, "seed": seed, "description": description,
    }
    assert_writable(MANIFEST)
    with open(MANIFEST, "w") as f:
        json.dump(m, f, indent=2, sort_keys=True)
    print(f"  wrote {rel:48s} {len(x)/SR:6.2f}s  peak {peak_db(x):6.1f} dBFS")
    return x


# --------------------------------------------------------------------------- gentle look-ahead compressor (zero-phase gain smoothing)
def compress(x, thresh_db, ratio=3.0, smooth_ms=90.0, block=48):
    """Peak-driven soft compressor for a master/bus: block peaks -> gain reduction (dB) -> min-hold -> Hann smoothing
    (symmetric, i.e. perfect look-ahead; no overshoot at attacks) -> linear interpolation to samples."""
    x = np.asarray(x, dtype=float)
    mono = np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)
    nb = len(mono) // block + 1
    pad = np.zeros(nb * block)
    pad[: len(mono)] = mono
    pk = pad.reshape(nb, block).max(axis=1)
    lvl = 20 * np.log10(pk + 1e-9)
    gr = -np.maximum(lvl - thresh_db, 0.0) * (1.0 - 1.0 / ratio)          # dB, <= 0
    k = max(3, int(smooth_ms / 1000 * SR / block) | 1)
    # min-hold over the window so a peak is fully covered, then smooth
    pad_gr = np.pad(gr, (k // 2, k // 2), mode="edge")
    idx = np.arange(k)[None, :] + np.arange(nb)[:, None]
    held = pad_gr[idx].min(axis=1)
    win = np.hanning(k + 2)[1:-1]
    win /= win.sum()
    sm = np.convolve(np.pad(held, (k // 2, k // 2), mode="edge"), win, mode="valid")[:nb]
    g = 10 ** (sm / 20.0)
    gs = np.interp(np.arange(len(mono)), (np.arange(nb) + 0.5) * block, g)
    return x * (gs[:, None] if x.ndim == 2 else gs)

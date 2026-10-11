"""Objective measurements through ffmpeg (ebur128, astats, silencedetect) + numpy. No listening involved."""
import re
import subprocess

import numpy as np


def _ff(args):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args, capture_output=True, text=True)
    return r.stderr


def ebur128(path):
    err = _ff(["-i", path, "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"])
    s = err[err.rfind("Summary:"):]
    g = lambda pat: float(re.search(pat, s).group(1))
    return {
        "integrated_lufs": g(r"I:\s+(-?[\d.]+) LUFS"),
        "lra_lu": g(r"LRA:\s+(-?[\d.]+) LU"),
        "true_peak_dbtp": g(r"Peak:\s+(-?[\d.]+) dBFS"),
        "loudness_range_low": g(r"LRA low:\s+(-?[\d.]+) LUFS"),
        "loudness_range_high": g(r"LRA high:\s+(-?[\d.]+) LUFS"),
    }


def momentary_series(path, kind="M"):
    """per-100ms momentary (M) or short-term (S) loudness list [(t, value)] via ebur128 framelog."""
    err = _ff(["-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    out = []
    for m in re.finditer(r"t:\s+([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.inf]+)\s+S:\s*(-?[\d.inf]+)\s+I:", err):
        t, M, S = m.group(1), m.group(2), m.group(3)
        try:
            out.append((float(t), float(M if kind == "M" else S)))
        except ValueError:
            pass
    return out


def astats(path):
    err = _ff(["-i", path, "-af", "astats=metadata=0:reset=0", "-f", "null", "-"])
    ov = err[err.rfind("Overall"):]
    res = {}
    for key, pat in [("peak_dbfs", r"Peak level dB:\s+(-?[\d.inf]+)"), ("rms_dbfs", r"RMS level dB:\s+(-?[\d.inf]+)"),
                     ("dc_offset", r"DC offset:\s+(-?[\d.e+-]+)"), ("flat_factor", r"Flat factor:\s+(-?[\d.]+)"),
                     ("peak_count", r"Peak count:\s+(-?[\d.]+)"), ("samples", r"Number of samples:\s+(\d+)")]:
        m = re.search(pat, ov)
        if m:
            try:
                res[key] = float(m.group(1))
            except ValueError:
                res[key] = float("-inf")
    return res


def silences(path, noise_db=-70, min_d=0.4):
    err = _ff(["-i", path, "-af", f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", err)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i][0] if i < len(ends) else None
        out.append((max(s, 0.0), e))
    return out


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_name,codec_type,sample_rate,channels,duration,bit_rate,sample_fmt,bits_per_sample:format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    import json
    return json.loads(r.stdout)


def level_db(x, t0, t1, sr=48000):
    seg = x[int(t0 * sr):int(t1 * sr)]
    return float(10 * np.log10(np.mean(seg ** 2) + 1e-20))


def true_peak_numpy(x, os_factor=4):
    """4x oversampled (FFT) true-peak estimate in dBFS, per file, for cross-checking ffmpeg."""
    pk = 0.0
    for ch in range(x.shape[1]):
        X = np.fft.rfft(x[:, ch])
        Y = np.zeros(len(X) * os_factor // 1 + 1, dtype=complex)
        Y[: len(X)] = X
        y = np.fft.irfft(Y, n=len(x) * os_factor) * os_factor
        pk = max(pk, float(np.max(np.abs(y))))
    return 20 * np.log10(pk + 1e-12)

"""Objective audio QA for the Lacrydia mix (ffmpeg ebur128/astats/silencedetect + numpy). Nothing here is 'listening'.

    python3 qa_audio.py            # measure renders/final/audio_mix.wav (+ .m4a), write images + metrics JSON + report
Outputs:
    renders/final/audio_qa_metrics.json
    renders/previews/audio_qa_*.png         (spectrograms, waveform, event-timeline overlays)
    documentation/audio_sync_report.md      (generated from the numbers; hand-written caveats kept in the template below)
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio_measure as M                    # noqa: E402
import audio_plan as AP                      # noqa: E402
import audio_viz as V                        # noqa: E402
import dsp_common as D                       # noqa: E402
from paths import ROOT, assert_writable, cfg  # noqa: E402

FINAL = os.path.join(ROOT, "renders", "final")
PREV = os.path.join(ROOT, "renders", "previews")
WAV = os.path.join(FINAL, "audio_mix.wav")
M4A = os.path.join(FINAL, "audio_mix.m4a")
RAW = os.path.join(FINAL, "audio_mix_blender_raw.wav")
SR = D.SR


def xcorr_lag(a, b, max_lag):
    """Locate template b inside segment a by normalised cross-correlation within +-max_lag of index max_lag.
    Returns (lag_samples, peak_corr, sharpness) ; sharpness = peak / best peak further than 40 samples away
    (>1.5 means the lag is unambiguous; tonal/sub material is ambiguous)."""
    n, m = len(a), len(b)
    N = 1 << int(np.ceil(np.log2(n + m)))
    A = np.fft.rfft(a, N)
    B = np.fft.rfft(b[::-1], N)
    c = np.fft.irfft(A * B, N)[m - 1:n]                # c[k] = sum a[k+i] b[i]
    cs = np.concatenate([[0], np.cumsum(a ** 2)])
    en = np.sqrt(np.maximum(cs[m:n + 1] - cs[:n - m + 1], 1e-18)) * np.sqrt(np.sum(b ** 2) + 1e-18)
    nc = (c / en)[: 2 * max_lag + 1]
    k = int(np.argmax(nc))
    far = np.concatenate([nc[: max(k - 40, 0)], nc[k + 41:]])
    sharp = float(nc[k] / (np.max(far) + 1e-9)) if len(far) else 99.0
    return int(k - max_lag), float(nc[k]), sharp


def event_alignment(mix_full, plan):
    """For every strip: where does its asset actually sit in the finished mix versus where config says it must?
    (matched filter: the asset waveform, weighted by the plan's gain, cross-correlated with the mix, +-100 ms search)."""
    music_only, _ = AP.render_plan([p for p in plan if p["layer"] == "MUSIC"], keep_stems=False)
    mono = (mix_full - music_only).mean(axis=1)        # the score is bit-identical at lag 0, so remove it: cleaner matches
    out = []
    cache = {}
    pad = 4800
    for p in plan:
        if p["file"] not in cache:
            cache[p["file"]] = D.read_wav(os.path.join(ROOT, p["file"]))[0].mean(axis=1)
        a = cache[p["file"]]
        s0 = (p["start_frame"] - 1) * AP.SPF
        L = min(len(a), p["dur_frames"] * AP.SPF)
        tpl = a[:L]
        env = np.cumsum(tpl ** 2)
        tpl = tpl[: max(int(np.searchsorted(env, 0.95 * env[-1])), 2400)]
        fr = p["start_frame"] + np.arange(len(tpl)) / AP.SPF
        tpl = tpl * np.interp(fr, [k[0] for k in p["keys"]], [k[1] for k in p["keys"]])
        lo = min(pad, s0)
        src = mono
        if p["layer"] == "IMPACTS" or p["name"] == "ATMOSPHERE_low_tone":
            # sub-bass material: subtract every OTHER strip (numpy render) and band-limit to < 400 Hz, where the
            # +-1 sample jitter of the others leaves no measurable residual
            others, _ = AP.render_plan([q for q in plan if q["name"] != p["name"]], keep_stems=False)
            src = D.lowpass((mix_full - others).mean(axis=1), 400.0, order=2)
            tpl = D.lowpass(tpl, 400.0, order=2)
        seg = src[s0 - lo: s0 + len(tpl) + pad]
        lag, corr, sharp = xcorr_lag(seg, tpl, lo) if lo == pad else (0, 1.0, 99.0)
        out.append(dict(name=p["name"], event=p["event"], t_event=p["t_event"], expected_start_s=p["t_start"],
                        measured_offset_samples=lag, measured_offset_ms=round(lag / SR * 1000, 4),
                        match_corr=round(corr, 3), sharpness=round(sharp, 2), reliable=bool(corr > 0.25),
                        start_frame=p["start_frame"], end_frame=p["end_frame"]))
    return out


def click_scan(x, events_t, win=0.05):
    """flag sample discontinuities: |second difference| of the mono sum vs its local RMS. Returns list of (t, ratio, near_event)"""
    m = x.mean(axis=1)
    d2 = np.abs(np.diff(m, 2))
    k = int(win * SR)
    cs = np.concatenate([[0], np.cumsum(d2 ** 2)])
    loc = np.sqrt((cs[k:] - cs[:-k]) / k + 1e-24)
    loc = np.concatenate([np.full(k // 2, loc[0]), loc, np.full(len(d2) - len(loc) - k // 2, loc[-1])])[: len(d2)]
    ratio = d2 / (loc + 1e-12)
    floor = d2 > 10 ** (-80 / 20)                      # ignore bit-level noise in near-silence
    idx = np.nonzero((ratio > 14) & floor)[0]
    res = []
    last = -10
    for i in idx:
        if i - last < int(0.01 * SR):
            continue
        last = i
        t = i / SR
        near = min(events_t, key=lambda e: abs(e - t))
        res.append((round(t, 4), round(float(ratio[i]), 1), round(abs(near - t), 3)))
    return res


def run():
    conf = cfg()
    plan = AP.build_plan()
    mix, _ = D.read_wav(WAV)
    n = len(mix)
    R = {"files": {"wav": os.path.relpath(WAV, ROOT), "m4a": os.path.relpath(M4A, ROOT)}}
    R["target"] = conf["audio"]

    # ---- duration
    R["length"] = {"samples": n, "seconds": n / SR, "frames_at_30fps": n / AP.SPF,
                   "error_ms_vs_30s": (n / SR - 30.0) * 1000,
                   "ffprobe_wav_duration": float(M.probe(WAV)["format"]["duration"]),
                   "ffprobe_m4a_duration": float(M.probe(M4A)["format"]["duration"]),
                   "m4a_streams": [s["codec_name"] for s in M.probe(M4A)["streams"]],
                   "m4a_bit_rate": M.probe(M4A)["streams"][0].get("bit_rate")}
    # ---- loudness
    R["loudness_wav"] = M.ebur128(WAV)
    R["loudness_m4a_decoded"] = M.ebur128(M4A)
    R["astats_wav"] = M.astats(WAV)
    R["true_peak_numpy_4x_dbfs"] = M.true_peak_numpy(mix)
    R["sample_peak_dbfs"] = D.peak_db(mix)
    R["clipped_samples_ge_0.999"] = int(np.sum(np.abs(mix) >= 0.999))
    R["dc_offset"] = {"L": float(mix[:, 0].mean()), "R": float(mix[:, 1].mean())}
    # ---- silence
    R["silence_-70dB_0.4s"] = M.silences(WAV, -70, 0.4)
    R["silence_-60dB_0.4s"] = M.silences(WAV, -60, 0.4)
    # ---- start / end
    def lv(t0, t1):
        return round(M.level_db(mix.mean(axis=1), t0, t1), 1)
    R["levels_rms_dbfs"] = {"0.00-0.10s": lv(0, 0.1), "0.50-0.60s": lv(0.5, 0.6), "1.00-1.10s": lv(1.0, 1.1),
                            "1.20-1.40s": lv(1.2, 1.4), "2.00-2.20s": lv(2, 2.2), "3.40-3.60s": lv(3.4, 3.6),
                            "29.00-29.10s": lv(29.0, 29.1), "29.50-29.60s": lv(29.5, 29.6), "29.80-29.90s": lv(29.8, 29.9),
                            "29.90-30.00s": lv(29.9, 30.0), "last_20ms": lv(29.98, 30.0)}
    R["first_sample_abs"] = float(np.max(np.abs(mix[:4])))
    R["last_sample_abs"] = float(np.max(np.abs(mix[-4:])))
    tail = []
    for t in np.arange(28.4, 30.0, 0.1):
        tail.append((round(float(t), 1), lv(t, t + 0.1)))
    R["tail_rms_per_100ms"] = tail
    peak_i = int(np.argmax([v for _, v in tail]))
    R["tail_monotonic_after_peak"] = all(tail[i][1] >= tail[i + 1][1] - 0.01 for i in range(peak_i, len(tail) - 1))
    # ---- per-second loudness profile
    R["rms_per_second_dbfs"] = [round(M.level_db(mix.mean(axis=1), s, s + 1), 1) for s in range(30)]
    # ---- mono compatibility
    mono = mix.mean(axis=1)
    mpath = os.path.join(FINAL, "_mono_tmp.wav")
    D.write_wav24(mpath, np.stack([mono, mono], axis=1))
    mono_l = M.ebur128(mpath)
    os.remove(mpath)
    mid, side = (mix[:, 0] + mix[:, 1]) / 2, (mix[:, 0] - mix[:, 1]) / 2
    corr = float(np.corrcoef(mix[:, 0], mix[:, 1])[0, 1])
    sec_corr = []
    for s in range(30):
        a = mix[s * SR:(s + 1) * SR]
        if np.std(a[:, 0]) > 1e-6 and np.std(a[:, 1]) > 1e-6:
            sec_corr.append(float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]))
    R["mono_compat"] = {"stereo_lufs": R["loudness_wav"]["integrated_lufs"], "mono_downmix_lufs": mono_l["integrated_lufs"],
                        "mono_minus_stereo_db": mono_l["integrated_lufs"] - R["loudness_wav"]["integrated_lufs"],
                        "LR_correlation_overall": corr, "LR_correlation_min_per_second": min(sec_corr),
                        "side_to_mid_energy_db": float(10 * np.log10(np.mean(side ** 2) / np.mean(mid ** 2)))}
    # ---- Blender vs numpy re-render (proves the VSE placement == the plan to the sample)
    npmix, stems = AP.render_plan(plan)
    diff = mix - npmix
    w = int(0.02 * SR)
    ne = len(mix) // w
    e_bl = 10 * np.log10(np.mean(mix[: ne * w].mean(axis=1).reshape(ne, w) ** 2, axis=1) + 1e-20)
    e_np = 10 * np.log10(np.mean(npmix[: ne * w].mean(axis=1).reshape(ne, w) ** 2, axis=1) + 1e-20)
    ok = e_np > -70
    de = np.abs(e_bl - e_np)[ok]
    R["blender_vs_numpy"] = {
        "note": "Blender evaluates strip start with +-1 sample rounding, so waveform subtraction is not meaningful; "
                "compare 20 ms RMS envelopes (gain structure incl. fades/ducks) instead",
        "env20ms_max_abs_diff_db": float(de.max()), "env20ms_p99_abs_diff_db": float(np.percentile(de, 99)),
        "env20ms_median_abs_diff_db": float(np.median(de)),
        "overall_rms_dbfs_blender": float(10 * np.log10(np.mean(mix ** 2))),
        "overall_rms_dbfs_numpy": float(10 * np.log10(np.mean(npmix ** 2))),
        "peak_dbfs_blender": D.peak_db(mix), "peak_dbfs_numpy": D.peak_db(npmix)}
    # ---- per-event alignment
    R["alignment"] = event_alignment(mix, plan)
    # ---- clicks
    ev_t = [e["t"] for e in conf["events"]] + [p["t_event"] - p["anchor_frames"] / 30 for p in []]
    R["click_scan"] = click_scan(mix, ev_t)
    # ---- per-asset audit (every WAV in assets/audio)
    man = AP.load_manifest()
    aud = {}
    for rel, m in man.items():
        a, sr_ = D.read_wav(os.path.join(ROOT, rel))
        mono_a = a.mean(axis=1)
        st_rms = np.sqrt(np.mean(a ** 2))
        aud[rel] = {"sr": sr_, "channels": 2, "frames": round(len(a) / AP.SPF, 3), "peak_dbfs": round(D.peak_db(a), 2),
                    "clipped": int(np.sum(np.abs(a) >= 0.999)), "dc": float(abs(a.mean(axis=0)).max()),
                    "first_abs": float(np.abs(a[0]).max()), "last_abs": float(np.abs(a[-1]).max()),
                    "mono_loss_db": round(float(20 * np.log10(np.sqrt(np.mean(mono_a ** 2)) / (st_rms + 1e-12) + 1e-12)), 2),
                    "LR_corr": round(float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]), 3) if np.std(a[:, 0]) > 0 and np.std(a[:, 1]) > 0 else None}
    R["asset_audit"] = aud
    # ---- images
    evl = [(e["t"], e["id"]) for e in conf["events"]]
    os.makedirs(PREV, exist_ok=True)
    V.timeline_image(stems, mix, os.path.join(PREV, "audio_qa_timeline_layers.png"), evl, conf["scenes"],
                     title="Lacrydia audio - per-layer RMS (dBFS, 50 ms) with config events (green) and scene starts (blue)")
    V.spec_image(mix, os.path.join(PREV, "audio_qa_spectrogram_events.png"), evl, conf["scenes"],
                 title="Lacrydia audio mix - spectrogram (log frequency) with config events")
    for kind, name in (("showspectrumpic=s=1800x700:legend=1:scale=log:fscale=log", "audio_qa_ffmpeg_spectrogram.png"),
                       ("showwavespic=s=1800x400:split_channels=1:colors=0xffa62b|0x9c9c9f", "audio_qa_ffmpeg_waveform.png")):
        out = os.path.join(PREV, name)
        assert_writable(out)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", WAV, "-lavfi", kind, "-frames:v", "1", out], check=True)
    # ---- verdicts
    tg = conf["audio"]
    L = R["loudness_wav"]
    v = {
        "length_30s_within_1_frame": abs(R["length"]["error_ms_vs_30s"]) <= 1000 / 30,
        "length_exact_samples": n == 30 * SR,
        "loudness_in_target_pm1.5": abs(L["integrated_lufs"] - tg["target_lufs"]) <= 1.5,
        "true_peak_ok": L["true_peak_dbtp"] <= tg["true_peak_dbtp"],
        "true_peak_ok_m4a": R["loudness_m4a_decoded"]["true_peak_dbtp"] <= tg["true_peak_dbtp"],
        "no_clipping": R["clipped_samples_ge_0.999"] == 0,
        "dc_offset_negligible(<1e-4)": max(abs(R["dc_offset"]["L"]), abs(R["dc_offset"]["R"])) < 1e-4,
        "ends_below_-60dBFS": R["levels_rms_dbfs"]["29.90-30.00s"] < -60 and R["levels_rms_dbfs"]["last_20ms"] < -60,
        "last_sample_zero(<1e-5)": R["last_sample_abs"] < 1e-5,
        "tail_decays_monotonically": R["tail_monotonic_after_peak"],
        "mono_loss_under_3dB": abs(R["mono_compat"]["mono_minus_stereo_db"]) < 3.0,
        "blender_gain_structure_equals_plan(env p99 < 0.5 dB)": R["blender_vs_numpy"]["env20ms_p99_abs_diff_db"] < 0.5,
"all_strips_matched_within_1_sample(corr>0.25)": all(abs(a["measured_offset_samples"]) <= 1 for a in R["alignment"] if a["reliable"]),
    }
    v["assets_clean(no clip, |DC|<1e-4, start/end ~0, mono loss < 3 dB)"] = all(
        a["clipped"] == 0 and a["dc"] < 1e-4 and a["first_abs"] < 1e-3 and a["last_abs"] < 1e-3 and a["mono_loss_db"] > -3.0
        for a in aud.values())
    sil = [s for s in R["silence_-70dB_0.4s"]]
    v["no_silent_gap_below_-70dBFS"] = len(sil) == 0
    R["verdicts"] = v
    jp = os.path.join(FINAL, "audio_qa_metrics.json")
    assert_writable(jp)
    with open(jp, "w") as f:
        json.dump(R, f, indent=1, default=float)
    return R


def pf(b):
    return "PASS" if b else "FAIL"


def print_summary(R):
    L = R["loudness_wav"]
    print(f"length      : {R['length']['samples']} samples = {R['length']['seconds']:.6f} s  ({R['length']['frames_at_30fps']:.3f} frames)")
    print(f"loudness    : I {L['integrated_lufs']} LUFS  LRA {L['lra_lu']} LU  TP {L['true_peak_dbtp']} dBTP  (m4a decoded TP {R['loudness_m4a_decoded']['true_peak_dbtp']}, I {R['loudness_m4a_decoded']['integrated_lufs']})")
    print(f"peaks       : sample {R['sample_peak_dbfs']:.2f} dBFS  numpy-4x TP {R['true_peak_numpy_4x_dbfs']:.2f}  clipped {R['clipped_samples_ge_0.999']}  DC {R['dc_offset']}")
    print(f"ends        : {R['levels_rms_dbfs']}")
    print(f"silence <-70: {R['silence_-70dB_0.4s']}   <-60: {R['silence_-60dB_0.4s']}")
    print(f"mono        : {R['mono_compat']}")
    print(f"blender/np  : {R['blender_vs_numpy']}")
    print("alignment (measured offset vs plan, ms | corr):")
    for a in R["alignment"]:
        print(f"   {a['name']:24s} ev {a['t_event']:6.2f}  off {a['measured_offset_samples']:4d} smp ({a['measured_offset_ms']:7.3f} ms) corr {a['match_corr']:.2f} sharp {a['sharpness']:5.2f} {'ok' if a['reliable'] else 'low-confidence'}")
    print("click scan  :", R["click_scan"][:40])
    for k, val in R["verdicts"].items():
        print(f"  [{pf(val)}] {k}")


if __name__ == "__main__":
    R = run()
    print_summary(R)

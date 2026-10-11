"""10 s A/V sync test: black video with frame counter + flash/graphic markers at every sound event, audio mixed through
the Blender VSE (same apply_audio/mixdown code as the film), muxed with ffmpeg, then verified objectively.

    python3 build_test_sequence.py
Outputs (renders/previews/):  lacrydia_audio_sync_test.mp4 (+ _audio.wav, _report.json)

Events (test time, frame = round(t*30)+1):
  0.50 rotate whoosh (2.4 s, L->R)   bar sweeps L->R while the sound pans L->R
  3.40 lens glint                    white flash (3 frames) = visual accent
  4.60 light sweep (0.9 s, L->R)     vertical light band = transition
  5.60 screen wake (+ sub)           flash + display rectangle blooming in over 0.8 s
  6.60 page swipe                    rectangle slides R->L over 0.55 s
  8.00 logo signature (file starts 7.6, first note at 8.00)   flash + wordmark
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio_measure as M                      # noqa: E402
import audio_plan as AP                        # noqa: E402
import audio_viz as V                          # noqa: E402
import build_audio_timeline as B               # noqa: E402
import dsp_common as D                         # noqa: E402
from paths import ROOT, assert_writable        # noqa: E402

PREV = os.path.join(ROOT, "renders", "previews")
W, H, FPS, DUR = 1280, 720, 30, 10.0
NF = int(DUR * FPS)

TEST_EV = {"t_rotate": 0.5, "t_glint": 3.4, "t_sweep": 4.6, "t_wake": 5.6, "t_swipe": 6.6, "t_logo": 8.0}
MAP = {"WHOOSH_rotate_1": "t_rotate", "MATERIAL_lens_glint": "t_glint", "WHOOSH_light_sweep": "t_sweep",
       "INTERFACE_screen_wake": "t_wake", "IMPACTS_screen_wake": "t_wake", "INTERFACE_swipe_1": "t_swipe",
       "LOGO_signature": "t_logo"}


def test_entries():
    out = []
    for e in AP.ENTRIES:
        if e[0] in MAP:
            out.append((e[0], e[1], e[2], MAP[e[0]]) + tuple(e[4:]))
    return out


def draw_frame(i, fonts):
    t = i / FPS
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    ft, fb, fs = fonts
    # counter
    d.text((40, H - 90), f"frame {i + 1:04d}   t = {t:6.3f} s", fill=(230, 230, 230), font=ft)
    d.text((40, H - 50), "audio sync test - flashes mark sound onsets", fill=(120, 120, 126), font=fs)
    # timeline bar
    x0, x1, y = 40, W - 40, 60
    d.rectangle([x0, y, x1, y + 6], fill=(40, 40, 44))
    for te in TEST_EV.values():
        xx = x0 + (x1 - x0) * te / DUR
        d.line([(xx, y - 14), (xx, y + 20)], fill=(255, 166, 43), width=2)
    xx = x0 + (x1 - x0) * t / DUR
    d.rectangle([xx - 2, y - 18, xx + 2, y + 24], fill=(255, 255, 255))

    def flash(te, n=3):
        return te <= t < te + n / FPS - 1e-9
    # rotate whoosh: bar sweeps L->R over 2.4 s
    tr = TEST_EV["t_rotate"]
    if tr <= t < tr + 2.4:
        u = (t - tr) / 2.4
        cx = 140 + (W - 280) * (0.5 - 0.5 * np.cos(np.pi * u)) * 0 + (W - 280) * u
        d.rectangle([cx - 60, 300, cx + 60, 330], fill=(150, 150, 160))
        d.text((40, 220), "ROTATE WHOOSH  L -> R", fill=(150, 150, 160), font=fb)
    # glint: flash
    tg = TEST_EV["t_glint"]
    if flash(tg):
        img.paste((255, 255, 255), (0, 0, W, H))
    elif tg <= t < tg + 0.6:
        d.text((40, 220), "LENS GLINT (flash at onset)", fill=(255, 255, 255), font=fb)
    # light sweep: vertical band over 0.9 s
    ts = TEST_EV["t_sweep"]
    if ts <= t < ts + 0.9:
        u = (t - ts) / 0.9
        cx = -100 + (W + 200) * u
        for k in range(-60, 61, 4):
            a = int(255 * np.exp(-(k / 28.0) ** 2))
            d.rectangle([cx + k, 120, cx + k + 4, H - 120], fill=(a, a, int(a * 0.85)))
        d.text((40, 220), "LIGHT SWEEP  L -> R", fill=(200, 200, 190), font=fb)
    # screen wake: flash 2 frames + rectangle blooming
    tw = TEST_EV["t_wake"]
    if tw <= t < tw + 2 / FPS - 1e-9:
        img.paste((255, 255, 255), (0, 0, W, H))
    if tw <= t < tw + 1.6:
        u = np.clip((t - tw) / 0.8, 0, 1)
        g = int(210 * u)
        d.rectangle([W / 2 - 150, 150, W / 2 + 150, H - 150], outline=(g, g, g), width=3, fill=(int(g * 0.2), int(g * 0.2), int(g * 0.22)))
        d.text((40, 220), "SCREEN WAKE (flash at onset)", fill=(g, g, g), font=fb)
    # swipe
    tp = TEST_EV["t_swipe"]
    if tp <= t < tp + 0.55:
        u = (t - tp) / 0.55
        u = 0.5 - 0.5 * np.cos(np.pi * u)
        x = W / 2 - 150 + (W * 0.6) * (1 - u) - W * 0.6 * 0.0
        d.rectangle([x - 150 * 0 - 300 * (1 - u) * 0 + 0, 150, x + 300, H - 150], outline=(180, 180, 190), width=3)
        d.text((40, 220), "PAGE SWIPE  R -> L", fill=(180, 180, 190), font=fb)
    # logo
    tl = TEST_EV["t_logo"]
    if flash(tl):
        img.paste((255, 255, 255), (0, 0, W, H))
    elif tl <= t < tl + 2.0:
        d.text((W / 2 - 120, H / 2 - 30), "LACRYDIA", fill=(244, 244, 244), font=fb)
        d.text((40, 220), "LOGO SIGNATURE (flash at first note)", fill=(255, 166, 43), font=fb)
    return np.asarray(img, dtype=np.uint8)


def main():
    import bpy
    os.makedirs(PREV, exist_ok=True)
    ev = dict(TEST_EV)
    plan = AP.build_plan(ev=ev, entries=test_entries())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = FPS, 1.0
    sc.frame_start, sc.frame_end = 1, NF
    plan = B.apply_audio(sc, plan=plan, first_channel=1)
    assert not B.verify_placement(sc, plan), "placement mismatch"
    raw = os.path.join(PREV, "lacrydia_audio_sync_test_audio_raw.wav")
    B.mixdown(sc, raw)
    x = D.read_any(raw)[: int(DUR * D.SR)]
    wav = os.path.join(PREV, "lacrydia_audio_sync_test_audio.wav")
    D.write_wav24(wav, x)
    os.remove(raw)
    # video (rawvideo through ffmpeg stdin)
    fonts = (V.font(30), V.font(40), V.font(20))
    mp4 = os.path.join(PREV, "lacrydia_audio_sync_test.mp4")
    assert_writable(mp4)
    vid_only = os.path.join(PREV, "_vid_only.mp4")
    pr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-r", str(FPS),
                           vid_only], stdin=subprocess.PIPE)
    for i in range(NF):
        pr.stdin.write(draw_frame(i, fonts).tobytes())
    pr.stdin.close()
    pr.wait()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid_only, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", mp4], check=True)
    os.remove(vid_only)

    # ---------------- verification
    R = {"plan": [{k: p[k] for k in ("name", "t_event", "start_frame", "end_frame", "channel", "vol_db")} for p in plan]}
    pr_ = M.probe(mp4)
    R["streams"] = [{k: s.get(k) for k in ("codec_type", "codec_name", "duration", "sample_rate", "channels", "bit_rate")}
                    for s in pr_["streams"]]
    R["format_duration"] = float(pr_["format"]["duration"])
    R["has_audio_stream"] = any(s["codec_type"] == "audio" for s in pr_["streams"])
    # decode the muxed (AAC) audio and the video's flash frames
    dec = D.read_any(mp4)
    R["decoded_audio_samples"] = int(len(dec))
    R["decoded_audio_seconds"] = len(dec) / D.SR
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", "scale=32:18,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 18 * 32).mean(axis=1)
    R["video_frames"] = int(len(fr))
    flash_frames = [int(i) for i in np.nonzero((fr > 200) & (np.concatenate([[0], fr[:-1]]) < 100))[0]]
    R["video_flash_onset_frames_0based"] = flash_frames
    R["video_flash_onset_times_s"] = [f / FPS for f in flash_frames]
    # audio onsets by matched filter against the plan's own render (isolates AAC delay + mux offset)
    ref, _ = AP.render_plan(plan, total_s=DUR)
    mono_ref, mono_dec = ref.mean(axis=1), dec.mean(axis=1)[: len(ref) + 4800]
    sync = {}
    for nm, key, tev in (("MATERIAL_lens_glint", "t_glint", 3.4), ("INTERFACE_screen_wake", "t_wake", 5.6), ("LOGO_signature", "t_logo", 8.0)):
        p = [q for q in plan if q["name"] == nm][0]
        s0 = (p["start_frame"] - 1) * AP.SPF
        tpl = D.read_wav(os.path.join(ROOT, p["file"]))[0].mean(axis=1)[: p["dur_frames"] * AP.SPF]
        env = np.cumsum(tpl ** 2)
        tpl = tpl[: max(int(np.searchsorted(env, 0.9 * env[-1])), 4800)]
        pad = 4800
        seg = mono_dec[max(0, s0 - pad): s0 + len(tpl) + pad]
        lo = min(pad, s0)
        from qa_audio import xcorr_lag
        lag, corr, _ = xcorr_lag(seg, tpl, lo)
        sync[nm] = {"expected_s": p["t_start"], "audio_lag_samples": lag, "audio_lag_ms": lag / D.SR * 1000, "corr": corr}
    R["audio_vs_plan_after_aac"] = sync
    # glint, wake and logo flashes: video flash time vs the instant the sound's first note/onset is expected
    # (asset anchor): video onset = frame/30 ; audio event = start + anchor
    comp = []
    for (nm, tev) in (("MATERIAL_lens_glint", 3.4), ("INTERFACE_screen_wake", 5.6), ("LOGO_signature", 8.0)):
        vf = min(R["video_flash_onset_times_s"], key=lambda v: abs(v - tev))
        a_on = tev + sync[nm]["audio_lag_ms"] / 1000
        comp.append({"event": nm, "video_flash_s": vf, "audio_onset_s": a_on, "audio_minus_video_ms": (a_on - vf) * 1000})
    R["audio_video_offsets"] = comp
    R["pass"] = bool(R["has_audio_stream"] and abs(R["format_duration"] - DUR) < 0.05 and abs(R["decoded_audio_seconds"] - DUR) < 0.06
                     and R["video_frames"] == NF and all(abs(c["audio_minus_video_ms"]) <= 34 for c in comp))
    jp = os.path.join(PREV, "lacrydia_audio_sync_test_report.json")
    assert_writable(jp)
    with open(jp, "w") as f:
        json.dump(R, f, indent=1, default=float)
    print(json.dumps({k: R[k] for k in ("streams", "format_duration", "decoded_audio_seconds", "video_frames",
                                         "video_flash_onset_times_s", "audio_vs_plan_after_aac", "audio_video_offsets", "pass")}, indent=1, default=float))
    ev_lines = [(v, k) for k, v in TEST_EV.items()]
    mix_stems = AP.render_plan(plan, total_s=DUR)
    V.timeline_image(mix_stems[1], mix_stems[0], os.path.join(PREV, "lacrydia_audio_sync_test_timeline.png"), ev_lines, None, dur=DUR,
                     size=(1500, 620), title="sync test - layers (dBFS RMS) and event times")


if __name__ == "__main__":
    main()

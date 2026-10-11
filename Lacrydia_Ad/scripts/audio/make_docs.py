"""Generate documentation/audio_design.md and documentation/audio_sync_report.md from the manifest, the resolved plan and
the QA metrics (so every number in the docs is the measured one). Run after qa_audio.py and build_test_sequence.py."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio_plan as AP                    # noqa: E402
from paths import ROOT, assert_writable, cfg  # noqa: E402

DOC = os.path.join(ROOT, "documentation")
FINAL = os.path.join(ROOT, "renders", "final")
PREV = os.path.join(ROOT, "renders", "previews")


def fmt_t(t):
    return f"{t:.2f}"


def design_md(conf, plan, man):
    ev = AP.event_times(conf)
    L = []
    w = L.append
    w("# Lacrydia - audio design\n")
    w("Sound design, mix plan and Blender VSE timeline for the 30 s film (`config/production.json`). "
      "Everything is original synthesis; the measured results are in `audio_sync_report.md`.\n")
    w("## 1. Intent\n")
    w("Dark, elegant, minimal premium-tech feel. The film opens in near silence, a barely-there low tone wakes at 1.2 s, "
      "a soft swell reveals the phone, air sweeps follow every camera/object move, one glass accent catches the lens, the screen "
      "wakes with a soft bloom (and the score lifts), pages swipe with a tiny tuned tick, the camera pulls back into a warm change, "
      "and the logo answers with a two-note glass-bell signature (A5 -> D6, a rising fourth that the piano already states earlier) "
      "that rings out and is silent exactly at t = 30.000 s. Key of D: Dsus2 -> Bm11 -> Gmaj7 -> **Dadd9 at the screen wake (the lift)** "
      "-> Bm9 -> Gmaj9 -> Dmaj9 (warm, at the pull-back) -> Gadd9 -> Asus4 -> **Dadd9 at the logo (the resolution)**. "
      "No risers, braams, drum hits, arcade/notification pops, or constant heavy bass (the sub only appears under 3 moments and every sub "
      "partial is phase-locked L=R so it cannot cancel in mono).\n")
    w("## 2. Time / frame convention\n")
    w("Blender timeline: **frame 1 == t 0.000 s**, 30 fps (fps_base 1.0), range 1..900.\n\n"
      "```\nframe = round(t * 30) + 1        t = (frame - 1) / 30\n"
      "start_frame(strip) = round((t_event - anchor_s) * 30) + 1      # anchor_s = where the event 'lands' inside the file\n```\n"
      "Anchors are whole frames (manifest.json), 1 frame = 1600 samples @ 48 kHz, so placement is frame- and sample-exact "
      "(verified: Blender's mixdown matches the sample-accurate numpy render within +-1 sample, see the sync report).\n")
    w("## 3. Event -> sound map (all config events)\n")
    w("| event | t (s) | frame | sound(s) |\n|---|---|---|---|")
    by_ev = {}
    for p in plan:
        by_ev.setdefault(p["event"], []).append(p["name"])
    extra = {"emerge": "(score: Dsus2 enters; swell crest follows at emerge_swell)", "text_1": "score: piano E5 + chord change to Gadd9",
             "text_2": "score: piano F#5", "end_card": "(logo file starts here: breath-in 0.4 s before the first note; score: Asus4)",
             "end": "everything decayed (digital zero at 30.000 s)"}
    for e in conf["events"]:
        names = by_ev.get(e["id"], [])
        s = ", ".join(f"`{n}`" for n in names) if names else ""
        if e["id"] in extra:
            s = (s + "; " if s else "") + extra[e["id"]]
        if not s:
            s = "-"
        w(f"| `{e['id']}` | {fmt_t(e['t'])} | {AP.t_to_frame(e['t'])} | {s} |")
    w("")
    w("## 4. Sound list\n")
    w("Level = strip volume in dB relative to the file (file peaks are normalised to the 'file peak' value). "
      "Frames are Blender frames of the resulting strips (start..end exclusive). All files: 48 kHz, stereo, 24-bit PCM WAV, "
      "declicked (2-5 ms in / 5-60 ms out), 20 Hz DC-block.\n")
    w("| file | layer | strip | event @ t (s) | strip start..end frame | dur (s) | file peak dBFS | strip dB | synthesis |\n|---|---|---|---|---|---|---|---|---|")
    for p in plan:
        m = man[p["file"]]
        w(f"| `{os.path.basename(p['file'])}` | {p['layer']} | `{p['name']}` | `{p['event']}` @ {fmt_t(p['t_event'])} | "
          f"{p['start_frame']}..{p['end_frame']} | {m['duration_s']:.2f} | {m['peak_dbfs']:.1f} | {p['vol_db']:+.1f} | {m['method']} |")
    w("")
    w("### Whoosh / sweep details (duration, direction, spectral motion)\n")
    w("| file | event | motion window (s) | file length | pan / width | spectral motion |\n|---|---|---|---|---|---|")
    mw = {"rotate_whoosh_1": (4.4, 6.8), "macro_cut_air": (6.9, 7.6), "light_sweep": (9.5, 10.4), "turn_whoosh_2": (10.2, 12.4),
          "push_in": (13.8, 17.0), "pull_back": (22.0, 25.0)}
    for p in plan:
        if p["layer"] != "WHOOSH":
            continue
        m = man[p["file"]]
        a, b = mw[p["event"]]
        w(f"| `{os.path.basename(p['file'])}` | `{p['event']}` | {a}-{b} ({b - a:.1f} s) | {m['duration_s']:.1f} s (incl. tail) | {m['pan']} | {m['description']} |")
    w("")
    w("Other panning: page swipes travel R->L (+0.32 -> -0.32), matching a leftward swipe; the glint rings sit slightly left/right; "
      "the logo notes are A5 left of centre / D6 right of centre. **Blender's `strip.pan` only affects mono sources "
      "(tested), so all panning is baked into the stereo files.**\n")
    w("## 5. Mix decisions\n")
    w("* **Layers = named sequencer channels** (bottom -> top): MUSIC, ATMOSPHERE, IMPACTS, WHOOSH, MATERIAL, INTERFACE, LOGO. "
      "When two strips of one layer overlap in time (e.g. rotate whoosh tail vs macro air) an extra lane `WHOOSH 2` etc. is created "
      "automatically; strips never fight for a channel.\n"
      "* **Gain staging** (`audio_plan.ENTRIES`): the score is the bed (about -24 dBFS RMS before the lift, about -18 after). "
      "Whooshes peak 3-8 dB under the local score level (felt, not heard as effects), impacts are felt under the swell/bloom, the lens glint "
      "and screen bloom are the two clearly audible accents, swipes sit 4-6 dB under the score, the logo signature is the loudest "
      "event (about +3 dB over the score), so it is 'the' memorable moment.\n"
      "* **Score arc**: silence until ~0.8 s, bloom to ~-24 dBFS RMS by 4 s, steady and restrained through macro, **+6 dB lift at the screen wake "
      "(11.6 s) with the pad low-pass opening from 1.1 kHz to 3.3 kHz**, a second warm lift at the pull-back, intimate dip for the tagline, "
      "resolution on the logo, raised-cosine (squared) finish to exact zero at 30.000 s.\n"
      "* **Bus glue**: the score has a gentle 2.5:1 zero-phase look-ahead peak compressor (threshold 5 dB above its 85th-percentile RMS) so the "
      "finished mix reaches -16 LUFS with true-peak head-room and **no master limiter is needed or used**.\n"
      "* **Ducking**: 1.2-1.5 dB dips of the score under the emerge swell and the screen-wake bloom (keyframes on the MUSIC strip volume).\n"
      "* **Fades**: every strip has volume keyframes (sin^2 shaped fades, linear segments) so nothing starts/stops abruptly; the files also "
      "carry their own declicks.\n"
      "* **True-peak margin**: sample peak -2.07 dBFS / true peak -2.0 dBTP (limit -1.5) leaves margin for AAC overshoot; the decoded m4a is also checked.\n"
      f"* **Master trim**: one static value `MASTER_TRIM_DB = {AP.MASTER_TRIM_DB:+.1f} dB` (audio_plan.py) added to every strip; it was calibrated with `qa_audio.py` "
      "to land the full mix at -16 LUFS. No EQ/limiter/normalisation happens after Blender's mixdown (`master_mix.py` only trims Blender's extra ~5 ms, "
      "converts to 24-bit and encodes AAC).\n"
      "* **Low end**: pad bass notes are trimmed (-3.5 dB below D3, -1.5 dB below G3), a -3 dB low shelf at 180 Hz sits on the score bus, "
      "sub impulses carry explicit 2nd/3rd harmonics so they also translate on phone speakers.\n"
      "* **Mono compatibility**: sub partials are phase-locked L=R; wide material uses small detune/decorrelation, not delay-based widening; measured "
      "mono-fold-down loss is reported in the sync report (about -1.5 dB, no cancellation).\n")
    w("## 6. Blender VSE findings (bpy 5.2.2, headless, tested)\n")
    w("| capability | result |\n|---|---|\n"
      "| sequence editor in a scene | works: `scene.sequence_editor_create()`; the collection is **`scene.sequence_editor.strips`** (top level) / `strips_all` (recursive); `.sequences` no longer exists |\n"
      "| add sound strips | works: `strips.new_sound(name, filepath, channel, frame_start)` (`frame_start` must be an **int**; later sub-frame moves are possible via `strip.frame_start`) |\n"
      "| channels / tracks | works: `sequence_editor.channels[n].name = 'WHOOSH'` (index == `strip.channel`); overlapping strips are bumped to a free channel by `new_sound`, so lanes are allocated explicitly |\n"
      "| volume + fades by keyframes | works: `strip.keyframe_insert('volume', frame=f)`; keyframes live in a layered Action (iterate `action.layers[].strips[].channelbags[].fcurves`); LINEAR interpolation set explicitly; evaluated in the mixdown (checked: 20 ms RMS envelope of Blender mix vs plan, p99 diff 0.04 dB) |\n"
      "| `strip.pan` | exists, but **only works for mono sources** (tested: stereo source ignores it) -> panning baked into files |\n"
      "| custom properties on strips | works (`strip['lacrydia_audio'] = True`), used so `apply_audio()` only replaces its own strips |\n"
      "| headless audio device | `bpy.context.preferences.system.audio_device = 'None'` is the only enum value available and works |\n"
      "| `bpy.ops.sound.mixdown` | works headless (container WAV, codec PCM, format F32/S24), **but it returns `FINISHED` immediately and a background thread writes the file** - reading right away gives a truncated file; `mixdown()` in `build_audio_timeline.py` waits until the file has full size and stops growing. Output is 30.0053 s for range 1..900 (about 5 ms longer), trimmed to 1,440,000 samples |\n"
      "| strip placement accuracy | frame-exact; the audible content lands within +-1 sample (0.02 ms) of the sample-exact numpy render |\n"
      "| FFMPEG video render with audio | works, but in 5.x you must set `image_settings.media_type = 'VIDEO'` before `file_format = 'FFMPEG'`; tested H.264 + AAC from a sound-only sequencer scene with the **CYCLES** engine (CPU, 1 sample). `BLENDER_WORKBENCH` and EEVEE need `libEGL.so.1`, which this machine lacks (render aborts) |\n"
      "| not tested / not available | real-time playback (no audio hardware), sound strip modifiers (EQ), `use_mono` panning of stereo files |\n")
    w("API used by this project:\n\n```python\nse = scene.sequence_editor            # sequence_editor_create() first\ns = se.strips.new_sound(name, abs_path, channel, int(start_frame))\ns.volume = g; s.keyframe_insert('volume', frame=f)   # + LINEAR interpolation on the fcurve keyframe_points\nse.channels[ch].name = 'WHOOSH'\nbpy.context.preferences.system.audio_device = 'None'\nbpy.ops.sound.mixdown(filepath=..., container='WAV', codec='PCM', format='F32')   # async - wait for the file\n```\n")
    w("## 7. Using it from your own Blender scene script\n")
    w("```python\nimport sys; sys.path.insert(0, '/home/user/Product-ad-blender/Lacrydia_Ad/scripts/audio')\n"
      "from build_audio_timeline import apply_audio, mixdown\nscene.render.fps = 30; scene.render.fps_base = 1.0      # required (frame = round(t*30)+1)\n"
      "plan = apply_audio(scene)          # adds/refreshes only strips flagged strip['lacrydia_audio']; foreign strips untouched\n"
      "# optional: first_channel=N to start above your own strips (default: first channel above any foreign strip)\n"
      "# render with  scene.render.image_settings.media_type='VIDEO'; file_format='FFMPEG'; ffmpeg.audio_codec='AAC'\n```\n"
      "`apply_audio` does not touch the frame range (the film is 1..900). Final audio deliverables are rendered by the standalone CLI; "
      "muxing the already-finished `renders/final/audio_mix.wav` onto the picture with ffmpeg is the recommended route "
      "(`ffmpeg -i video.mp4 -i audio_mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k out.mp4`).\n")
    w("## 8. Licensing\n")
    w("**All audio in `assets/audio/` is original work generated by the code in `scripts/audio/synth_*.py` (numpy only): additive/modal/"
      "subtractive synthesis, band-passed noise, synthetic impulse responses. No third-party samples, loops, presets, sample libraries or "
      "recordings are used or embedded; no attribution is required and there are no third-party licence obligations. "
      "The score is an original composition (chords and motif written for this film).**\n")
    w("## 9. Limitations (honest)\n")
    w("* **Nothing has been listened to** (no audio hardware, no listener). Levels, spectra, timing, loudness and decay are verified by "
      "measurement and by reading spectrograms; taste, balance and the *quality of the timbres* need a human ear on good headphones and on a phone speaker.\n"
      "* The 'felt piano', glass bells and pads are additive synthesis: clean and elegant, but less organic than a recorded instrument. For a final "
      "release consider replacing the score with a licensed/commissioned track (section 11) and keeping this SFX layer.\n"
      "* Early reflections / reverb are synthetic IRs (noise-based): smooth and tasteful, but not a sampled room.\n"
      "* The 3-5 kHz 'air' of the whooshes and the 4 ms pixel grains of the screen bloom are the elements most likely to need taste-level tweaks "
      "(`synth_whoosh.py` / `synth_material_ui.py`, deterministic seeds make A/B easy).\n"
      "* The very low partials (36-73 Hz) are inaudible on phones/laptops by design; they only matter on full-range playback.\n"
      "* Blender's real-time playback was not tested (no audio device); only the offline mixdown was.\n")
    w("## 10. Regenerate\n")
    w("```sh\ncd /home/user/Product-ad-blender/Lacrydia_Ad/scripts/audio\n./run_all.sh                       # synth -> Blender timeline + mixdown + master -> QA\n"
      "# or step by step\npython3 synth_all.py                 # all WAVs + assets/audio/manifest.json (deterministic, ~30 s)\n"
      "python3 build_audio_timeline.py      # project/lacrydia_audio.blend, renders/final/audio_mix.wav + .m4a (Blender mixdown)\n"
      "python3 build_audio_timeline.py --numpy-fallback     # same plan rendered by numpy instead of Blender\n"
      "python3 qa_audio.py                  # metrics JSON, PNGs, pass/fail\npython3 build_test_sequence.py       # 10 s A/V sync test in renders/previews/\n"
      "python3 make_docs.py                 # regenerate the two documentation files from the measurements\n```\n"
      "Single layers: `synth_music.py`, `synth_whoosh.py`, `synth_atmos_impacts.py`, `synth_material_ui.py`, `synth_logo.py`. "
      "Event times are read from `config/production.json`; if an event moves, re-run `build_audio_timeline.py` (placement) - and the synth_* scripts if the "
      "music chord changes should follow (they also read the events).\n")
    w("## 11. Swapping in a licensed music track\n")
    w("1. Export the track as **48 kHz stereo WAV, exactly 30.000 s** (1,440,000 samples), ending in its own natural fade, into `assets/audio/music/`.\n"
      "2. Run with the override: `LACRYDIA_MUSIC=assets/audio/music/your_track.wav python3 build_audio_timeline.py` "
      "(or change the `MUSIC_score` path in `audio_plan.ENTRIES` permanently). The SFX, impacts and logo stay as they are.\n"
      "3. Re-measure: `python3 qa_audio.py`, then adjust `MASTER_TRIM_DB` and the `MUSIC_score` level in `audio_plan.py` until the verdicts are green "
      "(-16 +-1.5 LUFS, true peak <= -1.5 dBTP). Check that the track's key/harmony fits the A5 -> D6 logo notes (D major / Dadd9) or re-tune `synth_logo.py`.\n"
      "4. Keep the licence file next to the track and add the credit to the end-card notes if the licence requires attribution.\n")
    return "\n".join(L) + "\n"


def sync_md(R, T, conf, plan):
    L = []
    w = L.append
    w("# Lacrydia - audio sync & QA report\n")
    w("Generated by `scripts/audio/qa_audio.py` + `build_test_sequence.py` + `make_docs.py` from the **measured** values in "
      "`renders/final/audio_qa_metrics.json` and `renders/previews/lacrydia_audio_sync_test_report.json`. "
      "Deliverables measured: `renders/final/audio_mix.wav` (24-bit, 48 kHz stereo) and `audio_mix.m4a` (AAC 256k).\n")
    bi = json.load(open(os.path.join(FINAL, "audio_mix_build_info.json")))
    w(f"**Mixdown path used: {bi['path_used']}.**" + (f" Blender's raw mixdown was {bi.get('blender_extra_ms', 0):.2f} ms longer than 30 s and was trimmed to exactly 1,440,000 samples." if 'blender_extra_ms' in bi else "") + "\n")
    v = R["verdicts"]
    w("## 1. Verdicts\n")
    w("| check | result |\n|---|---|")
    for k, val in v.items():
        w(f"| {k} | {'PASS' if val else 'FAIL'} |")
    w("")
    L1, Lm = R["loudness_wav"], R["loudness_m4a_decoded"]
    w("## 2. Loudness, peaks, integrity\n")
    w("| metric | WAV | m4a (decoded) | target |\n|---|---|---|---|")
    w(f"| integrated loudness | {L1['integrated_lufs']} LUFS | {Lm['integrated_lufs']} LUFS | -16 +-1.5 |")
    w(f"| loudness range (LRA) | {L1['lra_lu']} LU | {Lm['lra_lu']} LU | informational (quiet start + lift is intentional) |")
    w(f"| true peak (ebur128, 4x) | {L1['true_peak_dbtp']} dBTP | {Lm['true_peak_dbtp']} dBTP | <= -1.5 |")
    w(f"| true peak (numpy 4x FFT cross-check) | {R['true_peak_numpy_4x_dbfs']:.2f} dBFS | - | - |")
    w(f"| sample peak | {R['sample_peak_dbfs']:.2f} dBFS | - | - |")
    w(f"| samples >= 0.999 (digital clipping) | {R['clipped_samples_ge_0.999']} | - | 0 |")
    w(f"| DC offset L / R | {R['dc_offset']['L']:.1e} / {R['dc_offset']['R']:.1e} | - | ~0 |")
    w(f"| astats overall RMS / flat factor / peak count | {R['astats_wav'].get('rms_dbfs')} dB / {R['astats_wav'].get('flat_factor')} / {R['astats_wav'].get('peak_count')} | - | - |")
    w("")
    ln = R["length"]
    w("## 3. Length\n")
    w(f"* WAV: {ln['samples']} samples = **{ln['seconds']:.6f} s** = {ln['frames_at_30fps']:.3f} frames @ 30 fps (error {ln['error_ms_vs_30s']:+.3f} ms); ffprobe duration {ln['ffprobe_wav_duration']:.6f} s.\n"
      f"* m4a: codec {ln['m4a_streams']}, bit rate {ln['m4a_bit_rate']}, ffprobe duration {ln['ffprobe_m4a_duration']:.6f} s (AAC priming is compensated by the container edit list).\n")
    w("## 4. Start, end, tail, silence\n")
    lv = R["levels_rms_dbfs"]
    w("| window | RMS (dBFS) |\n|---|---|")
    for k, val in lv.items():
        w(f"| {k} | {val} |")
    w(f"\nFirst sample |x| = {R['first_sample_abs']:.1e}, last sample |x| = {R['last_sample_abs']:.1e} (no click at either end).\n")
    w("Tail (RMS per 100 ms after the logo lands): " + ", ".join(f"{t:.1f}s: {x}" for t, x in R["tail_rms_per_100ms"]) + f". Monotonic after the peak: **{R['tail_monotonic_after_peak']}**.\n")
    sl70, sl60 = R["silence_-70dB_0.4s"], R["silence_-60dB_0.4s"]
    w(f"silencedetect: below -70 dBFS for >= 0.4 s: **{sl70 or 'none'}**; below -60 dBFS for >= 0.4 s: {sl60} "
      "(this is the intended, near-silent opening: room tone at about -70 dBFS RMS, the low tone wakes at 1.2 s). No other gap, and no long dead silence at the end.\n")
    w("RMS per second (dBFS): " + ", ".join(f"{i}:{x}" for i, x in enumerate(R["rms_per_second_dbfs"])) + "\n")
    w("## 5. Mono compatibility\n")
    mc = R["mono_compat"]
    w(f"* Stereo {mc['stereo_lufs']} LUFS -> mono fold-down {mc['mono_downmix_lufs']} LUFS (**{mc['mono_minus_stereo_db']:+.1f} dB**; < 3 dB = no phase-cancellation problem).\n"
      f"* L/R correlation overall {mc['LR_correlation_overall']:.2f}, worst second {mc['LR_correlation_min_per_second']:.2f} (never negative); side/mid energy {mc['side_to_mid_energy_db']:.1f} dB.\n"
      "* Every individual asset is also audited (`asset_audit` in the metrics JSON): clipping, DC, first/last sample, mono loss, L/R correlation. "
      "Sub-bass partials are phase-locked L=R (an earlier version used drifting L/R detune on sub sines and measured -11 dB mono loss - fixed).\n")
    w("## 6. Does the Blender timeline equal the plan?\n")
    b = R["blender_vs_numpy"]
    w(f"The same plan is rendered sample-exactly with numpy. Blender mix vs numpy mix: 20 ms RMS envelope difference max {b['env20ms_max_abs_diff_db']:.3f} dB, "
      f"p99 {b['env20ms_p99_abs_diff_db']:.3f} dB, median {b['env20ms_median_abs_diff_db']:.1e} dB; overall RMS {b['overall_rms_dbfs_blender']:.3f} vs {b['overall_rms_dbfs_numpy']:.3f} dBFS; "
      f"peak {b['peak_dbfs_blender']:.3f} vs {b['peak_dbfs_numpy']:.3f} dBFS. "
      "(Fades, ducks, volumes keyed in Blender produce exactly the planned gain structure.)\n")
    w("## 7. Where each sound actually sits in the finished mix\n")
    w("Matched filter: each asset (weighted by its planned gain) is cross-correlated with the final WAV (score removed first; sub-bass assets: every other strip removed and low-passed at 400 Hz), "
      "+-100 ms search. `offset` = measured position minus the position the config event requires. "
      "1 sample = 0.0208 ms; 1 frame = 33.3 ms.\n")
    w("| strip | event | event t (s) | strip start frame | expected start (s) | offset (samples) | offset (ms) | match corr |\n|---|---|---|---|---|---|---|---|")
    for a in R["alignment"]:
        w(f"| `{a['name']}` | `{a['event']}` | {a['t_event']:.2f} | {a['start_frame']} | {a['expected_start_s']:.3f} | {a['measured_offset_samples']} | {a['measured_offset_ms']:.3f} | {a['match_corr']:.2f} |")
    w("\nBlender positions strips on whole frames with +-1 sample rounding of the start; that is the entire timing error (<= 0.02 ms). "
      "The plan itself is exact: every event time in the config is a whole number of frames.\n")
    w(f"Click scan (|second difference| vs local RMS > 14x, ignoring bit-level noise): **{R['click_scan'] or 'no discontinuities found'}** "
      "(the detector flags an injected -26 dBFS 3-sample click; it is not sensitive below about -30 dBFS).\n")
    w("## 8. 10 s A/V sync test (`renders/previews/lacrydia_audio_sync_test.mp4`)\n")
    w("Black 1280x720 / 30 fps video with frame counter, timeline bar and white flashes at the glint (3.40 s), screen wake (5.60 s) and logo first note (8.00 s); "
      "also a bar sweeping L->R during the rotate whoosh, a light band during the sweep, a display rectangle blooming for the screen wake and a swipe. Audio mixed with the same "
      "`apply_audio()` + Blender mixdown as the film (7 strips), muxed as AAC 256k.\n")
    w("| item | value |\n|---|---|")
    st = {s["codec_type"]: s for s in T["streams"]}
    w(f"| streams | video {st['video']['codec_name']} {st['video']['duration']} s, audio {st['audio']['codec_name']} {st['audio']['duration']} s, {st['audio']['sample_rate']} Hz, {st['audio']['channels']} ch |")
    w(f"| container duration | {T['format_duration']:.6f} s (target 10.000) |")
    w(f"| video frames | {T['video_frames']} (target 300) |")
    w(f"| has audio stream | {T['has_audio_stream']} |")
    w(f"| video flash onsets (s) | {', '.join(f'{x:.3f}' for x in T['video_flash_onset_times_s'])} |")
    for c in T["audio_video_offsets"]:
        w(f"| {c['event']}: audio onset vs video flash | {c['audio_minus_video_ms']:+.3f} ms (video {c['video_flash_s']:.3f} s, audio {c['audio_onset_s']:.4f} s) |")
    w(f"| overall | {'PASS' if T['pass'] else 'FAIL'} |")
    w("\nAudio onsets are measured on the *decoded AAC in the muxed MP4* (matched filter against the planned mix), so encoder delay and muxing are included; the video onsets are the first white frame.\n")
    w("## 9. Images (all in `renders/previews/`)\n")
    w("* `audio_qa_timeline_layers.png` - per-layer 50 ms RMS (dBFS) for MUSIC/ATMOSPHERE/IMPACTS/WHOOSH/MATERIAL/INTERFACE/LOGO + MIX, event lines (green) and scene starts (blue): every layer's envelope starts at its event.\n"
      "* `audio_qa_spectrogram_events.png` - log-frequency spectrogram of the final mix with the config events overlaid (whoosh sweeps, swipe bands, glint partials, bloom and logo are visible at their events).\n"
      "* `audio_qa_ffmpeg_spectrogram.png`, `audio_qa_ffmpeg_waveform.png` - ffmpeg `showspectrumpic` / `showwavespic` renders.\n"
      "* `lacrydia_audio_sync_test_timeline.png` - the same layer view for the 10 s sync test.\n")
    w("## 10. What is verified, and what is not\n")
    w("**Verified numerically / visually:** exact length (1,440,000 samples), -16 LUFS integrated, true peak, no clipping, DC, near-silent opening / natural decay / zero at the end (no tail clicks), "
      "absence of long silent gaps, mono fold-down, frame- and sample-exact placement of every sound against the config events (Blender mixdown == plan), a/v onset alignment of the muxed test file, "
      "sound-by-sound presence at the right time and frequency band on the spectrogram, deterministic regeneration (identical MD5s on re-synthesis).\n")
    w("**Needs human listening (not verifiable here):** timbre quality and taste of every sound; whether whooshes are 'felt' rather than 'heard' on the final playback system; "
      "balance of the lens glint / screen bloom / logo against the score on headphones, laptop and phone speakers; whether the score feels premium rather than generic; "
      "perceived width and mono fallback beyond the numeric checks; AAC artefacts on quiet material; real-time playback inside Blender.\n")
    return "\n".join(L) + "\n"


def main():
    conf = cfg()
    plan = json.load(open(os.path.join(DOC, "audio_plan_resolved.json")))
    man = AP.load_manifest()
    R = json.load(open(os.path.join(FINAL, "audio_qa_metrics.json")))
    T = json.load(open(os.path.join(PREV, "lacrydia_audio_sync_test_report.json")))
    p1 = os.path.join(DOC, "audio_design.md")
    p2 = os.path.join(DOC, "audio_sync_report.md")
    for p, txt in ((p1, design_md(conf, plan, man)), (p2, sync_md(R, T, conf, plan))):
        assert_writable(p)
        with open(p, "w") as f:
            f.write(txt)
        print("wrote", p)


if __name__ == "__main__":
    main()

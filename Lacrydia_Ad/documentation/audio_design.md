# Lacrydia - audio design

Sound design, mix plan and Blender VSE timeline for the 30 s film (`config/production.json`). Everything is original synthesis; the measured results are in `audio_sync_report.md`.

## 1. Intent

Dark, elegant, minimal premium-tech feel. The film opens in near silence, a barely-there low tone wakes at 1.2 s, a soft swell reveals the phone, air sweeps follow every camera/object move, one glass accent catches the lens, the screen wakes with a soft bloom (and the score lifts), pages swipe with a tiny tuned tick, the camera pulls back into a warm change, and the logo answers with a two-note glass-bell signature (A5 -> D6, a rising fourth that the piano already states earlier) that rings out and is silent exactly at t = 30.000 s. Key of D: Dsus2 -> Bm11 -> Gmaj7 -> **Dadd9 at the screen wake (the lift)** -> Bm9 -> Gmaj9 -> Dmaj9 (warm, at the pull-back) -> Gadd9 -> Asus4 -> **Dadd9 at the logo (the resolution)**. No risers, braams, drum hits, arcade/notification pops, or constant heavy bass (the sub only appears under 3 moments and every sub partial is phase-locked L=R so it cannot cancel in mono).

## 2. Time / frame convention

Blender timeline: **frame 1 == t 0.000 s**, 30 fps (fps_base 1.0), range 1..900.

```
frame = round(t * 30) + 1        t = (frame - 1) / 30
start_frame(strip) = round((t_event - anchor_s) * 30) + 1      # anchor_s = where the event 'lands' inside the file
```
Anchors are whole frames (manifest.json), 1 frame = 1600 samples @ 48 kHz, so placement is frame- and sample-exact (verified: Blender's mixdown matches the sample-accurate numpy render within +-1 sample, see the sync report).

## 3. Event -> sound map (all config events)

| event | t (s) | frame | sound(s) |
|---|---|---|---|
| `atmos_in` | 1.20 | 37 | `ATMOSPHERE_low_tone` |
| `first_light` | 2.30 | 70 | `MATERIAL_first_light` |
| `emerge` | 3.00 | 91 | (score: Dsus2 enters; swell crest follows at emerge_swell) |
| `emerge_swell` | 3.40 | 103 | `IMPACTS_emerge_swell` |
| `rotate_whoosh_1` | 4.40 | 133 | `WHOOSH_rotate_1` |
| `macro_cut_air` | 6.90 | 208 | `WHOOSH_macro_cut_air` |
| `lens_glint` | 8.30 | 250 | `MATERIAL_lens_glint` |
| `light_sweep` | 9.50 | 286 | `WHOOSH_light_sweep` |
| `turn_whoosh_2` | 10.20 | 307 | `WHOOSH_turn_2` |
| `screen_wake` | 11.60 | 349 | `IMPACTS_screen_wake`, `INTERFACE_screen_wake` |
| `push_in` | 13.80 | 415 | `WHOOSH_push_in` |
| `swipe_1` | 14.60 | 439 | `INTERFACE_swipe_1` |
| `swipe_2` | 18.00 | 541 | `INTERFACE_swipe_2` |
| `swipe_3` | 20.00 | 601 | `INTERFACE_swipe_3` |
| `swipe_4` | 22.80 | 685 | `INTERFACE_swipe_4` |
| `pull_back` | 22.00 | 661 | `IMPACTS_pull_back`, `WHOOSH_pull_back` |
| `text_1` | 25.30 | 760 | score: piano E5 + chord change to Gadd9 |
| `text_2` | 26.30 | 790 | score: piano F#5 |
| `end_card` | 28.00 | 841 | (logo file starts here: breath-in 0.4 s before the first note; score: Asus4) |
| `logo_signature` | 28.40 | 853 | `LOGO_signature` |
| `end` | 30.00 | 901 | everything decayed (digital zero at 30.000 s) |

## 4. Sound list

Level = strip volume in dB relative to the file (file peaks are normalised to the 'file peak' value). Frames are Blender frames of the resulting strips (start..end exclusive). All files: 48 kHz, stereo, 24-bit PCM WAV, declicked (2-5 ms in / 5-60 ms out), 20 Hz DC-block.

| file | layer | strip | event @ t (s) | strip start..end frame | dur (s) | file peak dBFS | strip dB | synthesis |
|---|---|---|---|---|---|---|---|---|
| `lacrydia_score_v1.wav` | MUSIC | `MUSIC_score` | `film_start` @ 0.00 | 1..901 | 30.00 | -6.0 | +0.2 | synth_music.py: additive warm pads (detuned saw stacks, automated low-pass), felt-piano additive keys, soft D2 sub at 3 moments, synthetic-IR FFT reverbs (pad rt60 4.2 s / keys 3.3 s); chord changes on config events; resolves to Dadd9 at logo_signature and rings out to a cosine finish at 30.000 s |
| `atmos_room_tone.wav` | ATMOSPHERE | `ATMOSPHERE_room_tone` | `film_start` @ 0.00 | 1..481 | 16.00 | -3.0 | -45.8 | synth_atmos_impacts.py: brown+pink noise bodies, 4 narrow drifting room-mode resonances (73/110/147/220 Hz), faint air; opens near-silent, blooms to 3 s, dissolves by 14 s |
| `atmos_low_tone.wav` | ATMOSPHERE | `ATMOSPHERE_low_tone` | `atmos_in` @ 1.20 | 37..457 | 14.00 | -3.0 | -28.8 | synth_atmos_impacts.py: D1/D2/A2 sines phase-locked L=R (mono-safe) + D3/A3 with +-0.1 Hz L/R detune (slow width), 0.11 Hz tremolo; wakes slowly |
| `impact_emerge_swell.wav` | IMPACTS | `IMPACTS_emerge_swell` | `emerge_swell` @ 3.40 | 67..175 | 3.60 | -3.0 | -16.8 | synth_atmos_impacts.py: D1-D2-A2 harmonic sine swell (raised cosine, crest at 1.2 s) + soft sine pulse 66->41 Hz (45 ms attack) + brown-noise rumble; small room; no distortion stage |
| `impact_screen_wake_sub.wav` | IMPACTS | `IMPACTS_screen_wake` | `screen_wake` @ 11.60 | 349..427 | 2.60 | -3.0 | -14.8 | synth_atmos_impacts.py: D2 sine pulse 92->73 Hz (90 ms attack, 0.62 s decay) + A2 + harmonics; small room |
| `impact_pull_back_sub.wav` | IMPACTS | `IMPACTS_pull_back` | `pull_back` @ 22.00 | 661..763 | 3.40 | -3.0 | -15.8 | synth_atmos_impacts.py: D2/A2/D3/A3 sine swell, raised-cosine 0.9 s rise, long release |
| `whoosh_rotate_01.wav` | WHOOSH | `WHOOSH_rotate_1` | `rotate_whoosh_1` @ 4.40 | 133..226 | 3.10 | -3.0 | -10.8 | synth_whoosh.py: STFT band-masked noise (soft air sweep, centre 330 Hz -> 1.75 kHz (peak at 55 % of move) -> 560 Hz); event rotate_whoosh_1 t=4.4 s, motion 2.4 s |
| `whoosh_macro_air_01.wav` | WHOOSH | `WHOOSH_macro_cut_air` | `macro_cut_air` @ 6.90 | 208..250 | 1.40 | -6.0 | -10.8 | synth_whoosh.py: STFT band-masked noise (short air inhale 0.8 -> 2.8 kHz -> 1.5 kHz, narrowing image); event macro_cut_air t=6.9 s, motion 0.7 s |
| `whoosh_light_sweep_01.wav` | WHOOSH | `WHOOSH_light_sweep` | `light_sweep` @ 9.50 | 286..331 | 1.50 | -7.0 | -8.8 | synth_whoosh.py: STFT band-masked noise (bright narrow-band air 2.3 -> 9 kHz with faint glassy partials; acts as transition); event light_sweep t=9.5 s, motion 0.9 s |
| `whoosh_turn_02.wav` | WHOOSH | `WHOOSH_turn_2` | `turn_whoosh_2` @ 10.20 | 307..397 | 3.00 | -4.0 | -8.8 | synth_whoosh.py: STFT band-masked noise (softer air sweep 300 Hz -> 1.2 kHz -> 520 Hz; settles as the screen wakes); event turn_whoosh_2 t=10.2 s, motion 2.2 s |
| `whoosh_push_in_01.wav` | WHOOSH | `WHOOSH_push_in` | `push_in` @ 13.80 | 415..535 | 4.00 | -5.0 | -7.8 | synth_whoosh.py: STFT band-masked noise (slow air swell 240 Hz -> 1.5 kHz, long build and soft landing); event push_in t=13.8 s, motion 3.2 s |
| `whoosh_pull_back_01.wav` | WHOOSH | `WHOOSH_pull_back` | `pull_back` @ 22.00 | 661..781 | 4.00 | -4.0 | -8.8 | synth_whoosh.py: STFT band-masked noise (airy fall 2.6 kHz -> 420 Hz, widening; warm settle into the typography); event pull_back t=22.0 s, motion 3.0 s |
| `material_first_light.wav` | MATERIAL | `MATERIAL_first_light` | `first_light` @ 2.30 | 70..166 | 3.20 | -6.0 | -13.8 | synth_material_ui.py: STFT band-limited noise 4.2->7.6->5.6 kHz (0.35 oct) + one faint modal ring, small room |
| `material_lens_glint.wav` | MATERIAL | `MATERIAL_lens_glint` | `lens_glint` @ 8.30 | 250..340 | 3.00 | -6.0 | -10.8 | synth_material_ui.py: modal synthesis, 5 inharmonic partials (ratios 1/2.76/5.4/8.93/13.34, T60 1.7..0.16 s) + 2nd ring 0.15 s later + 2 ms noise tick; small room |
| `ui_screen_wake.wav` | INTERFACE | `INTERFACE_screen_wake` | `screen_wake` @ 11.60 | 349..421 | 2.40 | -4.0 | -7.8 | synth_material_ui.py: D5-A5-D6-F#6-A6 sine bloom (glide -3.5 % -> 0 over 0.45 s, 0.5 s attack) + D4/A4 body + band-passed air + 34 random 4 ms sine 'pixel' grains + room |
| `ui_swipe_01.wav` | INTERFACE | `INTERFACE_swipe_1` | `swipe_1` @ 14.60 | 439..469 | 1.00 | -6.0 | -5.8 | synth_material_ui.py: band-passed noise 1.3->3.8 kHz (0.55 s, peak 0.22 s), R->L pan +0.32 -> -0.32, tick at 0.47 s: 2 ms noise click + tuned tink 1175 Hz (D6), room 1 s |
| `ui_swipe_02.wav` | INTERFACE | `INTERFACE_swipe_2` | `swipe_2` @ 18.00 | 541..571 | 1.00 | -6.0 | -7.8 | synth_material_ui.py: band-passed noise 1.3->3.8 kHz (0.55 s, peak 0.22 s), R->L pan +0.32 -> -0.32, tick at 0.47 s: 2 ms noise click + tuned tink 1319 Hz (E6), room 1 s |
| `ui_swipe_03.wav` | INTERFACE | `INTERFACE_swipe_3` | `swipe_3` @ 20.00 | 601..631 | 1.00 | -6.0 | -5.8 | synth_material_ui.py: band-passed noise 1.3->3.8 kHz (0.55 s, peak 0.22 s), R->L pan +0.32 -> -0.32, tick at 0.47 s: 2 ms noise click + tuned tink 1480 Hz (F#6), room 1 s |
| `ui_swipe_04.wav` | INTERFACE | `INTERFACE_swipe_4` | `swipe_4` @ 22.80 | 685..715 | 1.00 | -6.0 | -4.8 | synth_material_ui.py: band-passed noise 1.3->3.8 kHz (0.55 s, peak 0.22 s), R->L pan +0.32 -> -0.32, tick at 0.47 s: 2 ms noise click + tuned tink 1760 Hz (A6), room 1 s |
| `logo_signature.wav` | LOGO | `LOGO_signature` | `logo_signature` @ 28.40 | 841..901 | 2.00 | -3.0 | -1.8 | synth_logo.py: breath-in 0-0.4 s, glass-bell modal notes A5@0.40 s and D6@0.62 s (rising 4th), Dadd9 sine bloom (D5 A5 E6 F#6, +-0.1 % L/R detune), soft D2/D3 sub, bright 1.5 s room, final raised-cosine fade to zero at 2.0 s |

### Whoosh / sweep details (duration, direction, spectral motion)

| file | event | motion window (s) | file length | pan / width | spectral motion |
|---|---|---|---|---|---|
| `whoosh_rotate_01.wav` | `rotate_whoosh_1` | 4.4-6.8 (2.4 s) | 3.1 s (incl. tail) | L->R: -0.75 -> +0.75 over 2.4 s (rotation direction); widest mid-move | soft air sweep, centre 330 Hz -> 1.75 kHz (peak at 55 % of move) -> 560 Hz |
| `whoosh_macro_air_01.wav` | `macro_cut_air` | 6.9-7.6 (0.7 s) | 1.4 s (incl. tail) | centre -> +0.18; stereo width collapses 0.7 -> 0.12 (focus into macro) | short air inhale 0.8 -> 2.8 kHz -> 1.5 kHz, narrowing image |
| `whoosh_light_sweep_01.wav` | `light_sweep` | 9.5-10.4 (0.9 s) | 1.5 s (incl. tail) | L->R fast: -0.92 -> +0.92 over 0.9 s (matches reflection travelling across the frame) | bright narrow-band air 2.3 -> 9 kHz with faint glassy partials; acts as transition |
| `whoosh_turn_02.wav` | `turn_whoosh_2` | 10.2-12.4 (2.2 s) | 3.0 s (incl. tail) | R->L: +0.7 -> -0.7 over 2.2 s (mirror of rotate_01: turning back towards the viewer) | softer air sweep 300 Hz -> 1.2 kHz -> 520 Hz; settles as the screen wakes |
| `whoosh_push_in_01.wav` | `push_in` | 13.8-17.0 (3.2 s) | 4.0 s (incl. tail) | centre; stereo width narrows 0.8 -> 0.2 (camera approaches, image focuses) | slow air swell 240 Hz -> 1.5 kHz, long build and soft landing |
| `whoosh_pull_back_01.wav` | `pull_back` | 22.0-25.0 (3.0 s) | 4.0 s (incl. tail) | centre; stereo width opens 0.2 -> 0.9 (space opens up as the camera retreats) | airy fall 2.6 kHz -> 420 Hz, widening; warm settle into the typography |

Other panning: page swipes travel R->L (+0.32 -> -0.32), matching a leftward swipe; the glint rings sit slightly left/right; the logo notes are A5 left of centre / D6 right of centre. **Blender's `strip.pan` only affects mono sources (tested), so all panning is baked into the stereo files.**

## 5. Mix decisions

* **Layers = named sequencer channels** (bottom -> top): MUSIC, ATMOSPHERE, IMPACTS, WHOOSH, MATERIAL, INTERFACE, LOGO. When two strips of one layer overlap in time (e.g. rotate whoosh tail vs macro air) an extra lane `WHOOSH 2` etc. is created automatically; strips never fight for a channel.
* **Gain staging** (`audio_plan.ENTRIES`): the score is the bed (about -24 dBFS RMS before the lift, about -18 after). Whooshes peak 3-8 dB under the local score level (felt, not heard as effects), impacts are felt under the swell/bloom, the lens glint and screen bloom are the two clearly audible accents, swipes sit 4-6 dB under the score, the logo signature is the loudest event (about +3 dB over the score), so it is 'the' memorable moment.
* **Score arc**: silence until ~0.8 s, bloom to ~-24 dBFS RMS by 4 s, steady and restrained through macro, **+6 dB lift at the screen wake (11.6 s) with the pad low-pass opening from 1.1 kHz to 3.3 kHz**, a second warm lift at the pull-back, intimate dip for the tagline, resolution on the logo, raised-cosine (squared) finish to exact zero at 30.000 s.
* **Bus glue**: the score has a gentle 2.5:1 zero-phase look-ahead peak compressor (threshold 5 dB above its 85th-percentile RMS) so the finished mix reaches -16 LUFS with true-peak head-room and **no master limiter is needed or used**.
* **Ducking**: 1.2-1.5 dB dips of the score under the emerge swell and the screen-wake bloom (keyframes on the MUSIC strip volume).
* **Fades**: every strip has volume keyframes (sin^2 shaped fades, linear segments) so nothing starts/stops abruptly; the files also carry their own declicks.
* **True-peak margin**: sample peak -2.07 dBFS / true peak -2.0 dBTP (limit -1.5) leaves margin for AAC overshoot; the decoded m4a is also checked.
* **Master trim**: one static value `MASTER_TRIM_DB = +0.2 dB` (audio_plan.py) added to every strip; it was calibrated with `qa_audio.py` to land the full mix at -16 LUFS. No EQ/limiter/normalisation happens after Blender's mixdown (`master_mix.py` only trims Blender's extra ~5 ms, converts to 24-bit and encodes AAC).
* **Low end**: pad bass notes are trimmed (-3.5 dB below D3, -1.5 dB below G3), a -3 dB low shelf at 180 Hz sits on the score bus, sub impulses carry explicit 2nd/3rd harmonics so they also translate on phone speakers.
* **Mono compatibility**: sub partials are phase-locked L=R; wide material uses small detune/decorrelation, not delay-based widening; measured mono-fold-down loss is reported in the sync report (about -1.5 dB, no cancellation).

## 6. Blender VSE findings (bpy 5.2.2, headless, tested)

| capability | result |
|---|---|
| sequence editor in a scene | works: `scene.sequence_editor_create()`; the collection is **`scene.sequence_editor.strips`** (top level) / `strips_all` (recursive); `.sequences` no longer exists |
| add sound strips | works: `strips.new_sound(name, filepath, channel, frame_start)` (`frame_start` must be an **int**; later sub-frame moves are possible via `strip.frame_start`) |
| channels / tracks | works: `sequence_editor.channels[n].name = 'WHOOSH'` (index == `strip.channel`); overlapping strips are bumped to a free channel by `new_sound`, so lanes are allocated explicitly |
| volume + fades by keyframes | works: `strip.keyframe_insert('volume', frame=f)`; keyframes live in a layered Action (iterate `action.layers[].strips[].channelbags[].fcurves`); LINEAR interpolation set explicitly; evaluated in the mixdown (checked: 20 ms RMS envelope of Blender mix vs plan, p99 diff 0.04 dB) |
| `strip.pan` | exists, but **only works for mono sources** (tested: stereo source ignores it) -> panning baked into files |
| custom properties on strips | works (`strip['lacrydia_audio'] = True`), used so `apply_audio()` only replaces its own strips |
| headless audio device | `bpy.context.preferences.system.audio_device = 'None'` is the only enum value available and works |
| `bpy.ops.sound.mixdown` | works headless (container WAV, codec PCM, format F32/S24), **but it returns `FINISHED` immediately and a background thread writes the file** - reading right away gives a truncated file; `mixdown()` in `build_audio_timeline.py` waits until the file has full size and stops growing. Output is 30.0053 s for range 1..900 (about 5 ms longer), trimmed to 1,440,000 samples |
| strip placement accuracy | frame-exact; the audible content lands within +-1 sample (0.02 ms) of the sample-exact numpy render |
| FFMPEG video render with audio | works, but in 5.x you must set `image_settings.media_type = 'VIDEO'` before `file_format = 'FFMPEG'`; tested H.264 + AAC from a sound-only sequencer scene with the **CYCLES** engine (CPU, 1 sample). `BLENDER_WORKBENCH` and EEVEE need `libEGL.so.1`, which this machine lacks (render aborts) |
| not tested / not available | real-time playback (no audio hardware), sound strip modifiers (EQ), `use_mono` panning of stereo files |

API used by this project:

```python
se = scene.sequence_editor            # sequence_editor_create() first
s = se.strips.new_sound(name, abs_path, channel, int(start_frame))
s.volume = g; s.keyframe_insert('volume', frame=f)   # + LINEAR interpolation on the fcurve keyframe_points
se.channels[ch].name = 'WHOOSH'
bpy.context.preferences.system.audio_device = 'None'
bpy.ops.sound.mixdown(filepath=..., container='WAV', codec='PCM', format='F32')   # async - wait for the file
```

## 7. Using it from your own Blender scene script

```python
import sys; sys.path.insert(0, '/home/user/Product-ad-blender/Lacrydia_Ad/scripts/audio')
from build_audio_timeline import apply_audio, mixdown
scene.render.fps = 30; scene.render.fps_base = 1.0      # required (frame = round(t*30)+1)
plan = apply_audio(scene)          # adds/refreshes only strips flagged strip['lacrydia_audio']; foreign strips untouched
# optional: first_channel=N to start above your own strips (default: first channel above any foreign strip)
# render with  scene.render.image_settings.media_type='VIDEO'; file_format='FFMPEG'; ffmpeg.audio_codec='AAC'
```
`apply_audio` does not touch the frame range (the film is 1..900). Final audio deliverables are rendered by the standalone CLI; muxing the already-finished `renders/final/audio_mix.wav` onto the picture with ffmpeg is the recommended route (`ffmpeg -i video.mp4 -i audio_mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k out.mp4`).

## 8. Licensing

**All audio in `assets/audio/` is original work generated by the code in `scripts/audio/synth_*.py` (numpy only): additive/modal/subtractive synthesis, band-passed noise, synthetic impulse responses. No third-party samples, loops, presets, sample libraries or recordings are used or embedded; no attribution is required and there are no third-party licence obligations. The score is an original composition (chords and motif written for this film).**

## 9. Limitations (honest)

* **Nothing has been listened to** (no audio hardware, no listener). Levels, spectra, timing, loudness and decay are verified by measurement and by reading spectrograms; taste, balance and the *quality of the timbres* need a human ear on good headphones and on a phone speaker.
* The 'felt piano', glass bells and pads are additive synthesis: clean and elegant, but less organic than a recorded instrument. For a final release consider replacing the score with a licensed/commissioned track (section 11) and keeping this SFX layer.
* Early reflections / reverb are synthetic IRs (noise-based): smooth and tasteful, but not a sampled room.
* The 3-5 kHz 'air' of the whooshes and the 4 ms pixel grains of the screen bloom are the elements most likely to need taste-level tweaks (`synth_whoosh.py` / `synth_material_ui.py`, deterministic seeds make A/B easy).
* The very low partials (36-73 Hz) are inaudible on phones/laptops by design; they only matter on full-range playback.
* Blender's real-time playback was not tested (no audio device); only the offline mixdown was.

## 10. Regenerate

```sh
cd /home/user/Product-ad-blender/Lacrydia_Ad/scripts/audio
./run_all.sh                       # synth -> Blender timeline + mixdown + master -> QA
# or step by step
python3 synth_all.py                 # all WAVs + assets/audio/manifest.json (deterministic, ~30 s)
python3 build_audio_timeline.py      # project/lacrydia_audio.blend, renders/final/audio_mix.wav + .m4a (Blender mixdown)
python3 build_audio_timeline.py --numpy-fallback     # same plan rendered by numpy instead of Blender
python3 qa_audio.py                  # metrics JSON, PNGs, pass/fail
python3 build_test_sequence.py       # 10 s A/V sync test in renders/previews/
python3 make_docs.py                 # regenerate the two documentation files from the measurements
```
Single layers: `synth_music.py`, `synth_whoosh.py`, `synth_atmos_impacts.py`, `synth_material_ui.py`, `synth_logo.py`. Event times are read from `config/production.json`; if an event moves, re-run `build_audio_timeline.py` (placement) - and the synth_* scripts if the music chord changes should follow (they also read the events).

## 11. Swapping in a licensed music track

1. Export the track as **48 kHz stereo WAV, exactly 30.000 s** (1,440,000 samples), ending in its own natural fade, into `assets/audio/music/`.
2. Run with the override: `LACRYDIA_MUSIC=assets/audio/music/your_track.wav python3 build_audio_timeline.py` (or change the `MUSIC_score` path in `audio_plan.ENTRIES` permanently). The SFX, impacts and logo stay as they are.
3. Re-measure: `python3 qa_audio.py`, then adjust `MASTER_TRIM_DB` and the `MUSIC_score` level in `audio_plan.py` until the verdicts are green (-16 +-1.5 LUFS, true peak <= -1.5 dBTP). Check that the track's key/harmony fits the A5 -> D6 logo notes (D major / Dadd9) or re-tune `synth_logo.py`.
4. Keep the licence file next to the track and add the credit to the end-card notes if the licence requires attribution.


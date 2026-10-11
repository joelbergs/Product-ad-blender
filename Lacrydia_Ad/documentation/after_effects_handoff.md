# After Effects hand-off (finish tomorrow)

All paths relative to `Lacrydia_Ad/`. The renders and recordings are git-ignored (large); they live in this working folder / the Mac copy.

## Ready-made master (reference cut)
* `renders/final/lacrydia_film_1080.mp4` – the complete 30 s film (1920×1080, 30 fps, H.264, 48 kHz stereo). Use it as the timing reference.
* `renders/final/audio_mix.wav` – mastered mix (−15.0 LUFS, −1.1 dBTP) and `audio_mix.m4a`.

## Layers to rebuild the film in AE (comp 1920×1080 or 3840×2160, 30 fps, 30.0 s)
| Layer | Source | Notes |
|---|---|---|
| 3D hero, 0–10 s | `renders/hero_v2/f####.png` (16-bit PNG, Cycles, 1080p). Frame number = t·30+1; frames exist every 2–3 frames | In AE use *Timewarp (Pixel Motion)* or Twixtor to fill to 30 fps – the compositor used optical flow the same way. |
| Display content | `capture/seq/journey_a/f####.jpg` (373 frames, Tree → Travel → Open → viewer → Like) and `capture/seq/tabs_b/f####.jpg` (269 frames, Home → Explore → Playlists); both 1206×2622 @ 30 fps, real app | Time mapping used in the film: `J_MAP`/`T_MAP` in `scripts/compose_film.py` |
| Final cut (everything composited) | `renders/film_1080/c0000..c0899.png` | One flat image sequence; use for grading/finishing if no re-comp is wanted |
| Typography | Inter Display Medium/SemiBold (`assets/fonts/`), tracking +0.22/+0.34 em for the lockup | Timings and words are listed in `compose_film.py` (`hero_text`, `typography`) |
| Logo | `assets/lacrydia/logo/ikon-09-white.svg` (+ `-accent`, `-ink`) | Brand colours: ink #0A0A0B, paper #F4F4F4, amber #FFA62B |
| Audio stems | `renders/final/` (mix) and `assets/audio/music|sfx/*.wav`; cue sheet `documentation/audio_design.md` + `audio_sync_report.md` | VSE project: `project/lacrydia_audio.blend` (every strip on a named channel, frame-exact) |

## Beat grid
96 BPM, 1 bar = 2.5 s. Shot cuts: 2.5 (bar 2), 5.0, 7.5, 10.0 (hand-over to the app), 22.5 (three devices), 25.0 (brand). Logo hit 26.25 s (bar 11 beat 3).

## Suggested AE finishing
Colour (S-curve, slightly cooler blacks), film grain, lens-flare/streak on the light sweeps (1.0–2.4 s and 5.9–7.8 s), glow on the display, subtle chromatic aberration on the macro shots, richer shadow/reflections under the devices, text animation presets (blur + tracking), a final limiter check on the audio.

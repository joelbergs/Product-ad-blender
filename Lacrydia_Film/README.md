# Lacrydia - cinematic product film

A 44.5 s, 24 fps product film for **Lacrydia** (the photo app built around the *Tree*): one glass photograph panel, a
pile of photographs that settles into the Tree, the real app on a glass device, and the nine slits of the brand mark.
Everything is built from scripts: Blender (Cycles, `bpy` module) for all pictures, numpy for all sound, OpenCV/Pillow +
ffmpeg for finishing. Nothing is hand-keyed; every shot is a deterministic function of time.

> Central idea: *A camera roll is a pile. Lacrydia is a place.* (the product's own line), with the people you share with at
> the end of it: "Private by default. Shared with the people you choose."

## Deliverables (in `final/`, git-ignored; the app is unreleased and the repo public)
| File | What |
|---|---|
| `lacrydia_film_1080p_web.mp4` | **Delivery cut**: 1920x1080, 24 fps, H.264 (12 Mbps), AAC 256k, -16 LUFS |
| `film_1080/lacrydia_film_master_prores422hq.mov` | Master for further editing (ProRes 422 HQ, 10-bit, BT.709) |
| `film_1080/lacrydia_film.mp4` | High-bitrate H.264 master (CRF 12) |
| `lacrydia_film_2160p_UPSCALED_from_1080.mp4` | 3840x2160 convenience encode, **upscaled** from the 1080p master |
| `contact_sheet.jpg`, `qc_plot.png` | Contact sheet of the finished film; luminance / frame-difference plot |
| `audio_mix.wav`, `assets/audio/` | Final mix, music bed, FX bus and every cue as its own WAV (original, synthesised) |

## Layout

```
Lacrydia_Film/
  config/film.json            shot list, start times, fades (single source of truth for the edit)
  scripts/
    setup_assets.py           copy photos / real app screens / logo from the (private) Lacrydia repo into assets/lacrydia/
    lib/                      motion system, geometry (precision glass slabs), materials, studio rig, choreography tables
    shots/shot_*.py           one scene module per shot (A, B, C, TABLE = D+E+F, G, H)
    render.py / render_all.py Cycles driver (still, frame range, resumable)
    grade.py                  the film's look (filmic curve, midnight shadows, silver highlights)
    finish.py                 interpolation, bloom, grade, grain, typography, fades, ProRes + H.264 encode
    audio/sound.py            the whole score and every sound effect (numpy), timed from the same choreography tables
    contact_sheet.py          contact sheets from any video
  documentation/              shot list, creative direction, technical notes, licences, QC report
  project/                    saved .blend scenes (one per shot module)
  final/                      outputs (git-ignored): MP4, ProRes master, audio, contact sheet
```

## Reproduce

```bash
python3 -m venv --system-site-packages .venv && .venv/bin/pip install bpy==5.2.2 numpy scipy opencv-python-headless OpenEXR pillow
python3 scripts/setup_assets.py /path/to/lacrydia-social              # needs access to the private app repo
cd scripts
../.venv/bin/python render_all.py --res 1920x1080 --samples 64 --step 2 --out ../renders/final   # resumable, CPU
../.venv/bin/python audio/sound.py                                                                  # ~20 s
../.venv/bin/python finish.py --tag final --w 1920 --encode                                         # master + MP4
../.venv/bin/python contact_sheet.py ../final/final/lacrydia_film.mp4 ../final/contact_sheet.jpg
```

A single frame of any shot: `python render.py --shot B --frame 80 --res 960x540 --samples 32 --out ../previews/B_80.exr`
(also writes a tone-mapped PNG next to it).

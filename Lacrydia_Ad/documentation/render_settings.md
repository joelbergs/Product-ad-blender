# Render settings
* **3D hero (0–7.5 s):** Blender 5.2.2 (`bpy` module), Cycles CPU + OpenImageDenoise (Metal/GPU not available in this environment), 1920×1080, 40 samples,
  "Standard" view transform, motion blur on, 16-bit PNG; every 2nd frame (15 fps) – the compositor blends neighbours to 30 fps.
  `python3 scripts/render_hero.py --profile review --samples 40 --step 2 --out renders/hero_review` (resumable). ≈ 65–80 s/frame on 4 vCPU.
* **4K path:** `--profile final` (3840×2160, 160 spl) is configured but was not rendered here (≈ 8× the cost). On the Mac mini M4 run
  `python3 scripts/render_hero.py --profile final --device GPU --step 1 --out renders/hero_final` (Metal untested), then `compose_film.py --w 3840`.
  The app recordings are 1206×2622 (DPR 3), enough for a 4K composite.
* **2D part (7.5–30 s):** `python3 scripts/compose_film.py --w 1920 --out renders/film_1080 --frames 226-899` (numpy/OpenCV, perspective warps of the
  recordings, DOF blur by depth, bloom, vignette, grain). Same pinhole model as the Blender camera (85 mm / 36 mm).
* **App recordings:** Chromium begin-frame control + frozen virtual time, 30 fps, 1206×2622 px (`capture/rec_journey.mjs`, `rec_tabs.mjs`).
* **Encode:** `scripts/make_film.sh` – H.264 High, CRF 14, yuv420p, BT.709 tags, AAC 256 kbit/s 48 kHz.
* **Audio:** `scripts/audio/run_all.sh` (synth → Blender VSE → mixdown → master → QA). Measured −14.7 LUFS, −1.1 dBTP.

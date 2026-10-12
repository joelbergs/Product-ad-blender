# 4K render on your Mac (Apple Silicon)

I (Claude) run in a cloud container and cannot reach your Mac, so this is a one-command workflow for you to run. Everything is resumable.
The Metal path was **not tested** (the container has no GPU) – step 2 measures it before you commit to the full render.

## What you need
* Blender 5.x installed in /Applications (the scripts call Blender's own Python, `Blender -b -P ...`)
* Python 3.11+ (the script creates `.venv-mac` and installs numpy, opencv-python-headless, pillow, svgpathtools)
* ffmpeg (`brew install ffmpeg`)

## Steps
1. `git pull` this branch (`claude/intelligent-wozniak-upuu7i`), then unzip the asset package (sent separately, ~25 MB) **inside `Lacrydia_Ad/`**.
   It holds what is deliberately not in the public repo: the app recordings (`capture/seq_video/*.mp4`, unpacked to frames automatically), the app's demo photos/logos/fonts (`assets/`) and the mastered audio (`renders/final/audio_mix.wav`).
2. `cd Lacrydia_Ad && scripts/mac/render_4k.sh test` – renders one 3840×2160 hero frame; look at the printed `real` seconds.
   Full hero = about 140 frames: multiply. If too slow, lower quality: `SAMPLES=32 scripts/mac/render_4k.sh hero`.
3. `scripts/mac/render_4k.sh hero` (3D opening 0–10 s, writes `renders/hero_4k/`), then `compose` (900 frames, `renders/film_4k/`), then `encode`
   → `renders/final/lacrydia_film_4k.mp4` (H.264, 3840×2160, 30 fps, 48 kHz AAC). Or just `all`.

## Notes
* The app section is recorded at 1206×2622 (DPR 3) and the 2D composite works at any size; the 4K composite was tested here (2 frames).
* The compositor uses optical flow to fill hero frames between the Cycles frames (as in the 1080p cut), so the 4K hero frames use the plan in `render_4k.sh` (`PLAN`).
* If Blender cannot find a GPU it prints `WARNING: no GPU backend found` and renders on the CPU (slow).

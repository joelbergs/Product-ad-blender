# Technical notes

## Toolchain actually used (checked in this environment, not assumed)
Linux container, 4 vCPU, 15 GB RAM, **no GPU**. Blender 5.2.2 as the `bpy` Python module (installed from PyPI), Cycles on CPU with
OpenImageDenoise; numpy / scipy / OpenCV / Pillow / OpenEXR; ffmpeg (libx264, ProRes). No After Effects, no DaVinci, no Apple Silicon.
Hence every stage is script-driven (the brief's preferred route).

## Pipeline
`config/film.json` -> `scripts/shots/shot_*.py` (a deterministic function of time per scene) -> `render.py` (Cycles, linear 16-bit
EXR) -> `finish.py` (flow interpolation, bloom, grade, grain/dither, typography, fades, ProRes + H.264) <- `audio/sound.py`.

* **Light**: area softboxes for fill/top, gradient *emissive strip cards* for rims and the sweep (soft ends, refined reflections),
  gradient reflection flags, light linking so softboxes shape reflections without lighting the self-lit prints, a low "sheen flag"
  that mirrors across the glass face as the camera orbits, a reflective-pool obsidian that fades into the black void so strips never
  print as blobs on the floor, and per-ray emission masks (strips emit only to near-horizontal rays: glass bevels keep their glints,
  the floor does not mirror them).
* **Glass**: modelled as bullnose-profile slabs (`lib/geo.py`) with explicit smooth edge normals and flat caps; Principled glass
  (IOR 1.52) with a shadow-ray pass-through trick instead of caustics; the acid-etched mark is a roughness mask on the front pane.
* **Photographs**: thin rounded slabs with a clear coat; a *reveal* node makes each print emerge from darkness (no opacity fades).
* **Tree**: bezier tubes, endpoints recomputed every frame from the cards' poses, draw-on via bevel factor, plus a second brighter tube
  segment that travels along it ("pulse"). Cards glide from the scattered state to the tree layout with a soft ease and a small lift.
* **Interpolation**: Cycles frames are rendered every 2nd frame (12 fps keys); in-betweens come from DIS optical flow with a
  forward-backward confidence mask (plain cross-fade where flow is unreliable), never across a shot cut.
* **Look**: scene-linear EXR -> exposure -> filmic curve -> midnight-shadow / silver-highlight tint -> mild vignette -> film grain +
  1-LSB triangular dither (no banding in the long black gradients). Typography composited at output resolution.

## Where this differs from the brief's ideal, and why
| Brief | Delivered | Why |
|---|---|---|
| 3840x2160 @ 60 fps | **1920x1080 @ 24 fps** master (+ a 3840x2160 *upscaled* convenience encode, clearly labelled) | CPU-only Cycles (about 20-70 s per 1080p frame). 4K/60 would be ~16x the pixel-time and ~2.5x the frames: not feasible here. 24 fps is the cinematic standard, and slow, deliberate camera moves are served by it. `render_all.py --res 3840x2160` reproduces a native 4K render on a machine with a GPU. |
| Spatial audio | Stereo only | A normal stereo mix was required to be excellent first; stereo movement follows the orbits. |
| After Effects project | Not produced | Not installed; the finishing is scripted (`finish.py`). |

## Honest limitations
* In-between frames are optical-flow interpolated (every 2nd frame is a true Cycles render).
* The photographs are the app's bundled demo photos: **usage rights must be confirmed** before publication (see `assets_and_licenses.md`).
* The app is unreleased; the film shows its real onboarding screens: publish only with the owner's approval.

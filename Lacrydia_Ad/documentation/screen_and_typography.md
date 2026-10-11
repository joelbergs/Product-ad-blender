# Screen plate and typography overlays

## What is authentic, what is composed

| Item | Status |
|---|---|
| Every UI pixel (pages 1 to 5: Welcome, The Tree, Privacy, Together, Ready) | Authentic: `assets/lacrydia/screens/1..5.png`, read only, never modified. Static frames equal the source exactly (verified byte-for-byte with `--no-island`). |
| Page-swipe transition | Composed. Page A slides left, page B in from the right, same speed, no gap, no shadow, integer-pixel offsets (no resampling, so text stays crisp and there is no half-pixel jitter). Ease: cubic-bezier(0.38, 0, 0.10, 1), 0.55 s, long soft deceleration as the "settle"; monotonic, with no overshoot (an overshoot of a full-bleed pager would expose empty space). |
| Header row (logo, "Lacrydia", "Close"), page dots, Continue/Done button | Authentic and move with the page. Nothing in the screenshots needed pinning. |
| Status bar (time, signal, battery) | Authentic. Top 160 px stay fixed from page A during the swipe (feathered into the page body over 160 to 220 px, where no UI content exists on any page); cross-fades to page B's strip between 55 % and 95 % of the swipe. Glyph rows are y 76 to 118, header row y 248 to 294, so there is no overlap. |
| Dynamic Island pill | Composed hardware overlay, pure black, geometry measured from the real island in `4.png` (x 460.77 to 745.23, y 41.74 to 152.28 at 1206x2622; fully rounded). Added to all frames; `--no-island` disables it. On page 4 it coincides with the baked island (max edge difference 15/255). `island_overlay_rgba.png` holds the same pill as a separate RGBA layer. |
| Taglines, wordmark, status line, URL | Composed typography, copy from `config/production.json` ("copy"). |
| Mark | `ikon-09-accent.svg` polygons rasterised directly (cairosvg's native lib is not installed; polygons are filled with PIL at 16x supersampling). Checked against `ios-icon-dark.png`: after sub-pixel alignment 0 pixels differ by more than 40/255 (max 21). |

## Timeline of the plate

Plate frame `i` is film time `t = plate_t0 + i/fps` (`plate_t0` = 11.6, fps 30), 553 frames (i = 0 to 552, t up to 30.0).
In `production.json`, a page's `show_t` equals the previous page's `swipe_out_t`: that is the moment the swipe **starts**; the new page is settled `swipe_dur` later.
Swipes: 14.60 to 15.15, 18.00 to 18.55, 20.00 to 20.55, 22.80 to 23.35. Page 5 is static from 23.35 to the end.
Output: 65 unique PNG files (5 static pages + 60 swipe frames), 1206x2622 RGB, lossless on purpose (the dark gradients would band as JPEG), plus `plate_manifest.json`.

## Use in Blender

```python
import sys; sys.path.insert(0, ".../Lacrydia_Ad/scripts/plate")
from plate_lookup import plate_file_for_time      # absolute path; a list lookup, no image work
img.filepath = plate_file_for_time(frame / 30.0)
```
Only reload the image when the returned path changes (page 1 is the same file for 91 frames, etc.). Times before `plate_t0` return frame 0, after the end the last frame.
`plate_index_for_time(t)` returns the frame index. Env var `LACRYDIA_PLATE_MANIFEST` or `set_manifest(path)` points the lookup at another manifest.

## Manifest schema

`{"fps":30, "plate_t0":11.6, "width":1206, "height":2622, "num_frames":553, "t_end":30.0, "island":true, "path_base":".", "frames":[file per frame index], "runs":[{"file","start","count"}]}`
File names are relative to the manifest folder (+ `path_base`). `frames` (or only `runs`) may be used; the lookup accepts both.

## Swapping in real screen recordings later

1. `mkdir -p assets/lacrydia/screen_rec && ffmpeg -i recording.mov -vf fps=30,scale=1206:2622 assets/lacrydia/screen_rec/f_%04d.png` (start the recording at the film moment `plate_t0`, or trim it so frame 1 is that moment).
2. Write a manifest with the same schema in that folder (`frames` = `["f_0001.png", ...]`, one entry per 30 fps frame up to t = 30.0; repeat the last file if the recording is shorter), e.g. with a 5-line Python script.
3. Set `LACRYDIA_PLATE_MANIFEST=.../screen_rec/plate_manifest.json` for the Blender run. No other code changes. (Real recordings already contain the Dynamic Island, so do not add the overlay.)

## Changing copy or timing

* Copy: edit `config/production.json` ("copy", "brand") and re-run `make_overlays.py` (taglines, status, URL, brand colours). The wordmark text is fixed (LACRYDIA).
* Timing: edit `config/overlay_timing.json`. `scripts/plate/overlay_timing.py: overlay_state(name, t)` returns `(opacity_envelope, dy_fraction_of_H)` and is the reference for the Blender driver. The overlay PNGs bake their own opacity (tagline 1 = 72 %, status = 70 %); the envelope multiplies it.
* Swipe times and duration: `production.json` "screen"; regenerate the plate.
* Layout constants (cap height 6.5 % H, left margin 7 % W, tracking, line spacing 1.12 em, mark height 8.5 % H) are at the top of `make_overlays.py`.

## Regeneration

```
cd Lacrydia_Ad/scripts/plate
python3 make_screen_plate.py [--no-island]                  # -> assets/lacrydia/screen_plate/
python3 make_plate_preview.py                               # -> renders/previews/screen_plate_contact_sheet.png
python3 make_overlays.py --width 1920 --height 1080         # -> renders/overlays_1920x1080/
python3 make_overlay_preview.py --width 1920 --height 1080 [--crop]   # composite QA over a dark gradient
```
All scripts refuse to write outside `Lacrydia_Ad`.

## Limitations and notes

* The photographs inside the screenshots have undocumented provenance in the app repository (licence/consent not recorded); clear them before any public release.
* The swipe is composed, not recorded; real iOS has no shadow either, but its spring and finger tracking differ in detail.
* The screenshots show 12:18 (pages 1 to 4) and 12:19 (page 5); only 4.png has a Dynamic Island. The strip cross-fade turns 12:18 into 12:19 at the last swipe; in a real device the clock would not tick during a 3 s walkthrough, which is invisible at film scale.
* The in-app welcome headline reads "Your photos. Your world."; the film tagline is "Your images. / Your world." (owner decision pending per `production.json`). Both are visible in the film, so settle the wording before release.
* Tagline line 1 reaches 34.9 % of frame width (slightly past a strict third) at the specified 6.5 % cap height; the phone must stay in the right third.
* No blur-in is applied to overlays (optional, skipped); fades and 1.2 % H drift only.

# Lacrydia – 30 s commercial: creative brief

**Product:** Lacrydia (iOS app, project `lacrydia-social`). **Slogan:** YOUR IMAGES. YOUR WORLD.
**Format:** 16:9, 30 fps, 30.0 s (900 frames), H.264 MP4, 48 kHz stereo AAC. Reviewed at 1920×1080; 3840×2160 path documented in `render_settings.md`.

## Idea
A burgundy phone emerges from darkness; light travels across its back and the camera finds the logo and lenses. The phone turns, the
display wakes and the camera glides into the screen. From there the **app is the hero**: real recordings of Lacrydia on a floating glass device,
a moving virtual camera, depth of field, soft bloom and a few words of typography. The film ends on the brand.

## Structure (96 BPM, one bar = 2.5 s)
| Time | Scene | What the viewer sees |
|---|---|---|
| 0.0 – 7.5 | 1. Reveal (3D, Blender/Cycles) | burgundy phone with logo, light sweep, lens glints, turn from back to front, screen wakes with the Tree |
| 7.5 – 12.5 | 2. The Tree | "Your life, branch by branch." – tree overview, fly-in to the *Travel* branch |
| 12.5 – 17.5 | 3. Private | "Private by default." – branch page, photo viewer ("Travel · Private") |
| 17.5 – 22.5 | 4. Share · Discover · Collect | Home feed, Explore, Playlists |
| 22.5 – 25.0 | 5. All of it | three devices, camera pulls back – "All of it. In one place." |
| 25.0 – 30.0 | 6. Brand | mark + LACRYDIA + YOUR IMAGES. YOUR WORLD. (logo hit on bar 11 beat 3 = 26.25 s) |

## Rules followed
* Only the app's real UI (recorded from the real code in an isolated copy, guest/dev mode, offline placeholder environment). No invented screens or features.
  Copy claims are limited to things visible in the recordings (Private label, Share, Explore, Playlists, branches).
* The photographs are the app's own bundled demo photos. Their provenance is undocumented in the app – confirm usage rights before publishing.
* Phone colour: burgundy, as requested; not claimed to be an official product colour. The phone is a procedural model, not Apple CAD.
* Music: original, synthesised for this film (`scripts/audio`). No third-party music.
* The original app repositories were never modified (see `capture/README.md`, `scripts/paths.py::assert_writable`).

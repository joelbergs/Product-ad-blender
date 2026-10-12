# Assets and licensing

| Item | Source | Status |
|---|---|---|
| Lacrydia mark (ikon-09), wordmark | `design/brand/LOGGA`, `design/brand/logos` in the Lacrydia repo | own brand; used unmodified (mark rebuilt as 3D from the SVG polygons, wordmark composited from the brand PNG) |
| Photographs (34 images: `app/assets/tour`, `app/assets/travel`) | the app's own bundled demo photos | **provenance is not documented in the app repo**: confirm usage rights before publishing the film |
| App screens (`docs/screens/tour/2.png`, `4.png`) | genuine screenshots of the app (onboarding tour) | real UI, unmodified. The app is unreleased: do not publish the film before the owner approves |
| Typeface | Inter / Inter Display (SIL Open Font License 1.1) | licensed for commercial use |
| Music and every sound effect | synthesised from scratch by `scripts/audio/sound.py` (numpy) | original; no samples, no third-party audio, no generated-AI audio. Free for commercial use by the project owner |
| Blender / Cycles / OpenImageDenoise | `bpy` 5.2.2 (GPL, tools only; output is not encumbered) | n/a |

Private source assets (photos, screens, logo files) are copied into `assets/lacrydia/` by `scripts/setup_assets.py` and are
git-ignored: the repository is public and the app is not released. Rendered frames and the finished film are also git-ignored.

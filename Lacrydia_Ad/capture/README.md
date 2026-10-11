# Capture harness (scripts only)
Deterministic 30 fps recording of the real Lacrydia app (web build of an isolated copy in `capture/app`, never the original repo).
Chromium begin-frame control + frozen virtual time; app runs in its own dev guest mode with offline placeholder env values (no secrets).
`rec_journey.mjs <outdir> <dpr>` records Tree -> Travel -> Open -> photo viewer -> Like. App copy, frames and shots are git-ignored.

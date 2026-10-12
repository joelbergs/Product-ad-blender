#!/bin/bash
# Renders the Lacrydia film in 3840x2160 on a Mac (Apple Silicon, Metal) from this repository + the asset package.
#   scripts/mac/render_4k.sh test      -> renders ONE hero frame at 4K and prints how long it took (do this first)
#   scripts/mac/render_4k.sh hero      -> 3D hero (0-10 s), resumable: run again after an interruption and it continues
#   scripts/mac/render_4k.sh compose   -> 2D/app part + typography + hero blend, 900 frames at 3840x2160 (resumable)
#   scripts/mac/render_4k.sh encode    -> H.264 4K MP4 with the mastered audio  (renders/final/lacrydia_film_4k.mp4)
#   scripts/mac/render_4k.sh all       -> hero, compose, encode
# Environment: BLENDER (default /Applications/Blender.app/Contents/MacOS/Blender, Blender 5.x), SAMPLES (default 64), PY (python with numpy/opencv/pillow/svgpathtools)
set -euo pipefail
cd "$(dirname "$0")/../.."                      # Lacrydia_Ad/
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
SAMPLES="${SAMPLES:-64}"
PY="${PY:-.venv-mac/bin/python}"
PLAN="0-2.4:3,2.4-2.6:1,2.6-10:2"               # hero frame plan: every 3rd frame in the macro opening, every 2nd after, all around the 2.5 s cut

setup() {
  [ -x "$BLENDER" ] || { echo "Blender not found at $BLENDER (set BLENDER=...)"; exit 1; }
  if [ ! -x "$PY" ]; then
    python3 -m venv .venv-mac && .venv-mac/bin/pip install -q numpy opencv-python-headless pillow svgpathtools
  fi
  for f in capture/seq/journey_a/f0000.jpg capture/seq/tabs_b/f0000.jpg assets/fonts/InterDisplay-SemiBold.otf assets/lacrydia/logo/ikon-09-white.svg renders/final/audio_mix.wav; do
    [ -f "$f" ] || { echo "missing $f - unzip the asset package into Lacrydia_Ad/ first (see scripts/mac/README_MAC_4K.md)"; exit 1; }
  done
  [ -f assets/phone/apple_logo_mask.png ] || "$PY" scripts/make_logo_mask.py
  command -v ffmpeg >/dev/null || { echo "ffmpeg missing (brew install ffmpeg)"; exit 1; }
}

hero() {
  "$BLENDER" -b -P scripts/render_hero.py -- --profile final --samples "$SAMPLES" --device GPU --plan "$PLAN" --out renders/hero_4k
}

case "${1:-}" in
  test)    setup; /usr/bin/time -p "$BLENDER" -b -P scripts/render_hero.py -- --profile final --samples "$SAMPLES" --device GPU --times 3.3 --out renders/hero_4k_test ;;
  hero)    setup; hero ;;
  compose) setup; "$PY" scripts/compose_film.py --w 3840 --out renders/film_4k --frames 0-899 --hero renders/hero_4k ;;
  encode)  setup; mkdir -p renders/final
           ffmpeg -y -framerate 30 -i renders/film_4k/c%04d.png -i renders/final/audio_mix.wav \
             -c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -r 30 \
             -c:a aac -b:a 256k -ar 48000 -ac 2 -t 30 -movflags +faststart renders/final/lacrydia_film_4k.mp4
           ls -la renders/final/lacrydia_film_4k.mp4 ;;
  all)     setup; hero; "$PY" scripts/compose_film.py --w 3840 --out renders/film_4k --frames 0-899 --hero renders/hero_4k; "$0" encode ;;
  *) sed -n 2,10p "$0"; exit 1 ;;
esac

#!/bin/sh
# Encodes composed frames (renders/<dir>/c0000..c0899.png) + the mastered audio into the film.  usage: make_film.sh renders/film_1080 renders/final/lacrydia_film_1080.mp4
set -e
cd "$(dirname "$0")/.."
FR=${1:-renders/film_1080}; OUT=${2:-renders/final/lacrydia_film_1080.mp4}
ffmpeg -y -loglevel error -framerate 30 -i "$FR/c%04d.png" -i renders/final/audio_mix.wav \
  -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -r 30 \
  -c:a aac -b:a 256k -ar 48000 -ac 2 -t 30 -movflags +faststart "$OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of default=nw=1 "$OUT"

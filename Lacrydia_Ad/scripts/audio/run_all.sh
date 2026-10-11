#!/bin/sh
# Full audio pipeline: synthesize -> Blender VSE timeline + mixdown + master step -> QA -> sync test -> docs
set -e
cd "$(dirname "$0")"
python3 synth_all.py
python3 build_audio_timeline.py          # add --numpy-fallback to bypass Blender's mixdown
python3 qa_audio.py
python3 build_test_sequence.py
python3 make_docs.py

"""Final stage: take the Blender mixdown (or the numpy re-render of the same plan), make it exactly 30.000 s,
write ROOT/renders/final/audio_mix.wav (24-bit, 48 kHz stereo) and audio_mix.m4a (AAC 256k).

No gain, EQ, limiting or fades are applied here: loudness is set by MASTER_TRIM_DB in audio_plan.py (calibrated with
qa_audio.py), so what Blender mixes is what is delivered. This step only trims Blender's few extra ms, converts the
float mixdown to 24-bit and encodes the AAC. Run standalone (numpy path): python3 master_mix.py [--blender-raw FILE]
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio_plan as AP                              # noqa: E402
import dsp_common as D                               # noqa: E402
from paths import ROOT, assert_writable              # noqa: E402

FINAL = os.path.join(ROOT, "renders", "final")
TARGET_SAMPLES = 30 * D.SR                           # 1_440_000 = 900 frames x 1600


def run(plan=None, blender_raw=None, force_numpy=False, out_dir=FINAL):
    plan = plan or AP.build_plan()
    os.makedirs(out_dir, exist_ok=True)
    info = {}
    if blender_raw and os.path.exists(blender_raw) and not force_numpy:
        x = D.read_any(blender_raw)
        info["path_used"] = "Blender VSE mixdown (bpy.ops.sound.mixdown)"
        info["blender_raw_samples"] = int(len(x))
        info["blender_extra_ms"] = round((len(x) - TARGET_SAMPLES) / D.SR * 1000, 3)
    else:
        x, _ = AP.render_plan(plan, keep_stems=False)
        info["path_used"] = "numpy re-render of the same plan (documented fallback)"
    x = x[:TARGET_SAMPLES] if len(x) >= TARGET_SAMPLES else np.concatenate([x, np.zeros((TARGET_SAMPLES - len(x), 2))])
    peak = float(np.max(np.abs(x)))
    if peak >= 1.0:
        raise RuntimeError(f"mix clips ({peak:.3f}); lower MASTER_TRIM_DB")
    wav = os.path.join(out_dir, "audio_mix.wav")
    m4a = os.path.join(out_dir, "audio_mix.m4a")
    D.write_wav24(wav, x)
    assert_writable(m4a)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", m4a], check=True)
    info.update(wav=wav, m4a=m4a, samples=int(len(x)), peak_dbfs=round(20 * np.log10(peak), 2))
    print("[master_mix]", json.dumps(info))
    jp = os.path.join(out_dir, "audio_mix_build_info.json")
    assert_writable(jp)
    with open(jp, "w") as f:
        json.dump(info, f, indent=1)
    return info


if __name__ == "__main__":
    raw = None
    if "--blender-raw" in sys.argv:
        raw = sys.argv[sys.argv.index("--blender-raw") + 1]
    run(blender_raw=raw, force_numpy=("--numpy" in sys.argv))

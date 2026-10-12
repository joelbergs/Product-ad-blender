"""Equivalence test: a frame rendered by direct evaluation must equal the same frame rendered through the baked animation
(catches any property that is set but never keyed). usage: python verify_bake.py A:30,90 B:50 ..."""
import os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import grade
py = sys.executable
tmp = "/tmp/vb"; os.makedirs(tmp, exist_ok=True)
bad = 0
for spec in sys.argv[1:]:
    shot, frames = spec.split(":")
    for f in [int(x) for x in frames.split(",")]:
        d = f"{tmp}/{shot}_{f}_direct.exr"; b = f"{tmp}/{shot}_b/{shot}_{f:04d}.exr"
        common = ["--shot", shot, "--res", "480x270", "--samples", "24", "--fps", "24"]
        subprocess.run([py, f"{HERE}/render.py", *common, "--frame", str(f), "--out", d], capture_output=True, check=True)
        subprocess.run([py, f"{HERE}/render.py", *common, "--frames", f"{f}-{f}", "--out", f"{tmp}/{shot}_b"], capture_output=True, check=True)
        A, B = grade.read_exr(d), grade.read_exr(b)
        ta, tb = grade.tonemap(A), grade.tonemap(B)
        err = float(np.mean(np.abs(ta - tb))); mx = float(np.percentile(np.abs(ta - tb), 99.9))
        flag = "OK " if err < 0.004 else "DIFF"
        bad += flag == "DIFF"
        print(f"{flag} {shot} frame {f:4d}  mean|d|={err:.4f}  p99.9={mx:.3f}", flush=True)
sys.exit(1 if bad else 0)

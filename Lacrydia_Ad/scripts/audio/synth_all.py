"""Regenerate every original sound asset (deterministic). Usage: python3 synth_all.py"""
import json, os, time
import dsp_common as D
import synth_whoosh, synth_atmos_impacts, synth_material_ui, synth_logo, synth_music

if __name__ == "__main__":
    t0 = time.time()
    if os.path.exists(D.MANIFEST):
        D.assert_writable(D.MANIFEST)
        os.remove(D.MANIFEST)           # rebuilt below, so stale entries never survive
    for m in (synth_atmos_impacts, synth_whoosh, synth_material_ui, synth_logo, synth_music):
        m.build()
    print(f"done in {time.time()-t0:.1f}s; manifest: {D.MANIFEST}")

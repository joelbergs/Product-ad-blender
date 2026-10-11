"""Blender VSE audio timeline for the Lacrydia film (bpy 5.2.2, tested headless).

Import from another bpy script:

    import sys; sys.path.insert(0, "/home/user/Product-ad-blender/Lacrydia_Ad/scripts/audio")
    from build_audio_timeline import apply_audio, mixdown
    apply_audio(bpy.context.scene)                       # adds/refreshes ONLY the strips this module owns
    mixdown(bpy.context.scene, "/abs/path/audio_mix_raw.wav")   # optional, needs frame range 1..900

Standalone (creates ROOT/project/lacrydia_audio.blend, mixes down through Blender, then masters/validates):

    python3 build_audio_timeline.py            # blend + Blender mixdown + master step (audio_mix.wav / .m4a)
    python3 build_audio_timeline.py --no-mixdown
    python3 build_audio_timeline.py --numpy-fallback   # skip bpy mixdown, render the identical plan with numpy

API notes for Blender 5.2.2 (found by test, see documentation/audio_design.md):
  * scene.sequence_editor.strips (top level)  -- NOT .sequences (removed);  strips_all for lookups/data paths
  * strips.new_sound(name, filepath, channel, frame_start)  (frame_start must be int)
  * strip.volume (animatable, keyframe_insert('volume', frame=...)); keyframes live in a layered Action
  * strip.pan only works for MONO sources in Blender -> panning is baked into the stereo files
  * scene.sequence_editor.channels[n].name  to name a track;   strip.channel == n
  * bpy.context.preferences.system.audio_device = 'None'  (headless);  bpy.ops.sound.mixdown(...)
Frame convention: frame = round(t*30)+1, t = (frame-1)/30  (frame 1 == 0.000 s).
Strips created here carry the custom property  strip["lacrydia_audio"] = True ; apply_audio() removes/recreates only
those, so strips from other scripts are never touched.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import audio_plan as AP                      # noqa: E402
from paths import ROOT, assert_writable      # noqa: E402

OWNER_PROP = "lacrydia_audio"


def _strips(se):
    return se.strips if hasattr(se, "strips") else se.sequences        # 5.x: strips ; <=4.x: sequences


def _strips_all(se):
    return se.strips_all if hasattr(se, "strips_all") else se.sequences_all


def _iter_fcurves(scene):
    ad = scene.animation_data
    act = ad.action if ad else None
    if act is None:
        return
    if hasattr(act, "layers"):                                     # layered actions (4.4+/5.x)
        for layer in act.layers:
            for st in layer.strips:
                for cb in st.channelbags:
                    for fc in list(cb.fcurves):
                        yield cb, fc
    elif hasattr(act, "fcurves"):
        for fc in list(act.fcurves):
            yield act.fcurves, fc


def _remove_owned(scene):
    """Remove only strips created by this module (custom property), plus their orphaned volume fcurves."""
    se = scene.sequence_editor
    removed = []
    for s in list(_strips_all(se)):
        if s.get(OWNER_PROP):
            removed.append(s.name)
            (s.parent_meta.strips if s.parent_meta is not None else _strips(se)).remove(s)
    alive = {s.name for s in _strips_all(se)}
    for holder, fc in list(_iter_fcurves(scene)):
        dp = fc.data_path
        if "strips_all[" in dp or "sequences_all[" in dp:
            nm = dp.split('["', 1)[1].split('"]', 1)[0]
            if nm not in alive:
                try:
                    holder.remove(fc)
                except Exception:
                    pass
    return removed


def _first_free_channel(scene):
    se = scene.sequence_editor
    chans = [s.channel for s in _strips_all(se) if not s.get(OWNER_PROP)]
    return (max(chans) + 1) if chans else 1


def apply_audio(scene, plan=None, first_channel=None, check_fps=True, master_trim_db=None, verbose=True):
    """Create/refresh the Lacrydia sound strips in `scene`'s sequencer. Returns the plan with the created strip names.

    scene          bpy scene (fps must be 30 / base 1.0, frame 1 == t 0)
    plan           optional custom plan (audio_plan.build_plan(...)); default = the full 30 s film
    first_channel  first sequencer channel to use (default: first channel above any foreign strip, else 1)
    Only strips carrying strip["lacrydia_audio"] are replaced; foreign strips are untouched. Does not change the
    scene frame range (the film is 1..900).
    """
    import bpy
    if check_fps and (scene.render.fps != AP.FPS or abs(scene.render.fps_base - 1.0) > 1e-6):
        raise ValueError(f"scene fps is {scene.render.fps}/{scene.render.fps_base}, audio plan is built for {AP.FPS}/1.0 "
                         "(frame = round(t*30)+1). Set scene.render.fps=30 first, or pass check_fps=False.")
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    se = scene.sequence_editor
    plan = plan if plan is not None else AP.build_plan(master_trim_db=master_trim_db)
    _remove_owned(scene)
    base = (first_channel if first_channel is not None else _first_free_channel(scene)) - 1   # channel = rel + base
    layout = AP.channel_layout(plan)
    for rel, nm in layout.items():
        se.channels[rel + base].name = nm
    for p in plan:
        path = os.path.join(ROOT, p["file"])
        ch = p["channel_rel"] + base
        s = _strips(se).new_sound(p["name"], path, ch, int(p["start_frame"]))
        if s.channel != ch or int(s.frame_final_start) != int(p["start_frame"]):
            raise RuntimeError(f"{p['name']}: placed at channel {s.channel} frame {s.frame_final_start}, wanted {ch}/{p['start_frame']} "
                               "(overlap with a foreign strip? choose another first_channel)")
        s[OWNER_PROP] = True
        s.sound.use_mono = False
        s.color_tag = AP.LAYER_COLOR.get(p["layer"], "NONE")
        s.show_waveform = True
        s.volume = p["keys"][0][1]
        for fr, g in p["keys"]:
            s.volume = g
            s.keyframe_insert("volume", frame=fr)
        p["strip_name"] = s.name
        p["channel"] = ch
        p["blender_frame_start"] = int(s.frame_final_start)
        p["blender_frame_end"] = int(s.frame_final_end)
    # linear interpolation so Blender evaluates exactly the piecewise-linear gain used by the numpy re-render
    for holder, fc in _iter_fcurves(scene):
        if fc.data_path.endswith(".volume"):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.update()
    if verbose:
        print(f"[apply_audio] {len(plan)} strips on channels {min(p['channel'] for p in plan)}..{max(p['channel'] for p in plan)}")
    return plan


def setup_scene_for_audio(scene):
    scene.render.fps = AP.FPS
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = 900


def mixdown(scene, filepath, sample_format="F32"):
    """Headless mixdown of the scene's sequencer audio through Blender (no audio device needed)."""
    import bpy
    assert_writable(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        bpy.context.preferences.system.audio_device = "None"
    except TypeError:
        bpy.context.preferences.system.audio_device = "NONE"
    with bpy.context.temp_override(scene=scene):
        r = bpy.ops.sound.mixdown(filepath=filepath, check_existing=False, relative_path=False, container="WAV",
                                  codec="PCM", format=sample_format, split_channels=False)
    if "FINISHED" not in r:
        raise RuntimeError(f"mixdown returned {r}")
    # FINDING (5.2.2 headless): the operator returns immediately and the file is written by a background thread.
    # Reading it right away yields a truncated file, so wait until it exists, has full size, and stops growing.
    import time
    bytes_per_frame = {"F32": 8, "S24": 6, "S16": 4}.get(sample_format, 8) * (48000 // scene.render.fps)
    wanted = (scene.frame_end - scene.frame_start + 1) * bytes_per_frame
    last, stable, t0 = -1, 0, time.time()
    while time.time() - t0 < 120:
        time.sleep(0.2)
        sz = os.path.getsize(filepath) if os.path.exists(filepath) else -1
        stable = stable + 1 if (sz == last and sz >= wanted) else 0
        last = sz
        if stable >= 3:
            return filepath
    raise RuntimeError(f"mixdown did not complete: {last} bytes, expected >= {wanted}")


def verify_placement(scene, plan):
    """Compare what Blender holds against the plan. Returns list of problems (empty == frame-exact)."""
    se = scene.sequence_editor
    problems = []
    for p in plan:
        s = _strips_all(se).get(p.get("strip_name", p["name"]))
        if s is None:
            problems.append(f"{p['name']}: missing")
            continue
        if int(s.frame_final_start) != p["start_frame"]:
            problems.append(f"{p['name']}: start {s.frame_final_start} != {p['start_frame']}")
        if int(s.frame_final_end) != p["end_frame"]:
            problems.append(f"{p['name']}: end {s.frame_final_end} != {p['end_frame']}")
    return problems


def _cli():
    import argparse
    import bpy
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mixdown", action="store_true")
    ap.add_argument("--numpy-fallback", action="store_true", help="skip Blender mixdown; render the plan with numpy")
    ap.add_argument("--blend", default=os.path.join(ROOT, "project", "lacrydia_audio.blend"))
    ap.add_argument("--raw", default=os.path.join(ROOT, "renders", "final", "audio_mix_blender_raw.wav"))
    args = ap.parse_args(sys.argv[1:])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Lacrydia_Audio"
    setup_scene_for_audio(scene)
    plan = apply_audio(scene)
    probs = verify_placement(scene, plan)
    print("placement problems:", probs or "none")
    assert not probs, probs
    assert_writable(args.blend)
    os.makedirs(os.path.dirname(args.blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=args.blend, check_existing=False)
    print("saved", args.blend)
    import json
    plan_path = os.path.join(ROOT, "documentation", "audio_plan_resolved.json")
    assert_writable(plan_path)
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=1)
    path_used = "none"
    if not args.no_mixdown and not args.numpy_fallback:
        mixdown(scene, args.raw)
        path_used = "blender"
        print("Blender mixdown ->", args.raw)
    import master_mix
    master_mix.run(plan, blender_raw=(args.raw if path_used == "blender" else None), force_numpy=args.numpy_fallback)


if __name__ == "__main__":
    _cli()

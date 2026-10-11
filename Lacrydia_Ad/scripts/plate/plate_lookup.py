"""Fast film-time -> plate image lookup (no image processing).

    from plate_lookup import plate_file_for_time
    path = plate_file_for_time(t)          # absolute path of the screen image for film time t (seconds)

Plate frame i <-> t = plate_t0 + i/fps. Times before plate_t0 return frame 0, after the last frame the last one.
A different plate (e.g. real screen-recording frames) can be used by pointing the env var
LACRYDIA_PLATE_MANIFEST at another manifest of the same schema, or by calling set_manifest(path).
"""
import json, math, os

_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "assets", "lacrydia", "screen_plate", "plate_manifest.json")
_state = {}


def set_manifest(path=None):
    path = os.path.abspath(path or os.environ.get("LACRYDIA_PLATE_MANIFEST") or _DEFAULT)
    with open(path) as fh:
        m = json.load(fh)
    base = os.path.join(os.path.dirname(path), m.get("path_base", "."))
    if "frames" in m:
        names = m["frames"]
    else:  # run-length form
        names = []
        for r in m["runs"]:
            names.extend([r["file"]] * r["count"])
    _state.update(fps=float(m["fps"]), t0=float(m["plate_t0"]),
                  paths=[os.path.abspath(os.path.join(base, f)) for f in names], manifest=path)
    return _state["paths"]


def plate_index_for_time(t):
    if not _state:
        set_manifest()
    i = int(math.floor((t - _state["t0"]) * _state["fps"] + 1e-4))
    return min(max(i, 0), len(_state["paths"]) - 1)


def plate_file_for_time(t):
    if not _state:
        set_manifest()
    return _state["paths"][plate_index_for_time(t)]


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:] or ["11.6", "14.6", "14.8", "30.0"]:
        print(a, plate_file_for_time(float(a)))

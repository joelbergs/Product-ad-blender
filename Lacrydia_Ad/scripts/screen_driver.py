"""Swaps the image on the phone's display per frame (exchangeable screen content).

Source of truth: the screen plate manifest (scripts/plate/plate_lookup.py) if present, otherwise a plain page-per-time fallback built
from config/production.json (hard cuts, no swipe), so previews work before the plate exists.
"""
import os, sys
import bpy
from paths import cfg, p

_cache = {"path": None}
_C = cfg()


def _fallback_path(t):
    page = _C["screen"]["pages"][0]
    for pg in _C["screen"]["pages"]:
        if t >= pg["show_t"]:
            page = pg
    return p("assets", "lacrydia", "screens", page["file"])


def path_for_time(t):
    try:
        sys.path.insert(0, p("scripts", "plate"))
        import plate_lookup
        fp = plate_lookup.plate_file_for_time(t)
        if fp and os.path.exists(fp):
            return fp
    except Exception:
        pass
    return _fallback_path(t)


def set_screen_image(t):
    node = bpy.data.materials["PHONE_Screen_MAT"].node_tree.nodes["SCREEN_IMAGE"]
    path = path_for_time(t)
    if _cache["path"] == path and node.image:
        return path
    old = node.image
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB"
    img.alpha_mode = "NONE"
    node.image = img
    if old and old != img and old.users == 0:
        bpy.data.images.remove(old)
    _cache["path"] = path
    return path

"""Keyer: shots set every animated value through K.set(). When baking, each set also inserts a keyframe, so the same
analytic functions drive both stills and the (motion-blurred) animation, and the .blend carries real animation data."""
import bpy


class Keyer:
    def __init__(self):
        self.baking = False
        self.frame = 1

    def set(self, holder, prop, value, index=-1):
        if index >= 0:
            cur = list(getattr(holder, prop))
            cur[index] = value
            setattr(holder, prop, cur)
        else:
            setattr(holder, prop, value)
        if self.baking:
            holder.keyframe_insert(prop, frame=self.frame)

    def loc(self, ob, v):
        self.set(ob, "location", tuple(float(x) for x in v))

    def rot(self, ob, v):
        self.set(ob, "rotation_euler", tuple(float(x) for x in v))

    def scl(self, ob, v):
        self.set(ob, "scale", tuple(float(x) for x in v) if hasattr(v, "__len__") else (v, v, v))

    def sock(self, socket, value):
        self.set(socket, "default_value", value)

    def finish(self):
        """Linear interpolation between the dense per-frame keys (the curves are already smooth)."""
        for act in bpy.data.actions:
            for fc in iter_fcurves(act):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def iter_fcurves(act):
    if hasattr(act, "fcurves"):
        yield from act.fcurves
        return
    # Blender 5 layered actions
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield from cb.fcurves


K = Keyer()

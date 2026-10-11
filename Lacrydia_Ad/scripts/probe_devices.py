"""Which Cycles render devices does THIS Blender process actually see? (CPU/GPU, backends, threads)
   python3 probe_devices.py          -> prints a report (also useful on the Mac mini to confirm Metal)"""
import platform, os
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True)
prefs = bpy.context.preferences.addons["cycles"].preferences
print("platform :", platform.platform(), "| cpu threads:", os.cpu_count())
print("blender  :", bpy.app.version_string)
for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI", "NONE"):
    try:
        prefs.compute_device_type = backend
        prefs.refresh_devices() if hasattr(prefs, "refresh_devices") else None
        devs = [(d.name, d.type) for d in prefs.get_devices_for_type(backend)] if hasattr(prefs, "get_devices_for_type") else []
        print(f"backend {backend:7s}: {devs if devs else '-'}")
    except Exception as e:
        print(f"backend {backend:7s}: not available ({str(e)[:50]})")
prefs.compute_device_type = "NONE"
print("=> Rendering device used by these scripts: CPU (scene.cycles.device='CPU'). On Apple Silicon set --device GPU (Metal) in render scripts.")

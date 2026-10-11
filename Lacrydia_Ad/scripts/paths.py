"""Single source of truth for paths + the write guard that protects the existing app projects."""
import json, os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # .../Lacrydia_Ad
REPO = os.path.dirname(ROOT)                                                 # the commercial's own repo
CFG_PATH = os.path.join(ROOT, "config", "production.json")
READONLY_APP_CLONES = ["/home/user/lacrydia-swiftui", "/home/user/lacrydia-social"]

def cfg():
    with open(CFG_PATH) as f:
        return json.load(f)

def p(*parts):
    """Path inside the production folder."""
    return os.path.join(ROOT, *parts)

def assert_writable(path):
    """Refuse to write anywhere outside Lacrydia_Ad (and never inside the app clones)."""
    real = os.path.realpath(path)
    for ro in READONLY_APP_CLONES:
        if real == ro or real.startswith(ro + os.sep):
            raise PermissionError(f"refusing to write inside read-only app project: {path}")
    if not (real == ROOT or real.startswith(ROOT + os.sep)):
        raise PermissionError(f"refusing to write outside the production folder: {path}")
    return path

def app_clones_clean():
    """True if the existing app clones have zero local changes."""
    out = {}
    for ro in READONLY_APP_CLONES:
        if os.path.isdir(ro):
            r = subprocess.run(["git", "-C", ro, "status", "--porcelain"], capture_output=True, text=True)
            out[ro] = (r.returncode == 0 and r.stdout.strip() == "")
    return out

"""Copy the source assets (photos, real app screens, logo) from the PRIVATE Lacrydia repo into assets/ (git-ignored).

usage: python3 scripts/setup_assets.py [/path/to/lacrydia-social]
The repo is public, the app is unreleased: nothing copied here is ever committed (see ../.gitignore).
Read-only on the app repo.
"""
import os, shutil, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = sys.argv[1] if len(sys.argv) > 1 else "/home/user/lacrydia-social"
A = os.path.join(ROOT, "assets", "lacrydia")

def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)

n = 0
for f in glob.glob(f"{SRC}/app/assets/tour/*.jpg") + glob.glob(f"{SRC}/app/assets/travel/*.jpg"):
    cp(f, os.path.join(A, "photos", os.path.basename(f))); n += 1
for f in glob.glob(f"{SRC}/docs/screens/tour/*.png"):
    cp(f, os.path.join(A, "screens", os.path.basename(f))); n += 1
for name in ("ikon-09-white.svg", "ikon-09-accent.svg", "ikon-09-ink.svg"):
    cp(f"{SRC}/design/brand/LOGGA/svg/{name}", os.path.join(A, "logo", name)); n += 1
for name in ("wordmark-on-ink.svg", "wordmark-on-ink.png", "lockup-stacked-on-ink.png", "lockup-stacked-on-ink.svg"):
    cp(f"{SRC}/design/brand/logos/{name}", os.path.join(A, "logo", name)); n += 1
print(f"copied {n} files into {A}")

"""Copy the Lacrydia material this film needs from YOUR OWN local checkouts into Lacrydia_Ad/assets/lacrydia (read-only on the sources).
   python3 setup_local_assets.py --social ~/path/to/lacrydia-social
Then build the screen plate:  python3 plate/make_screen_plate.py"""
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import p, assert_writable
ap = argparse.ArgumentParser()
ap.add_argument("--social", required=True, help="path to your lacrydia-social checkout")
a = ap.parse_args()
pairs = [(f"docs/screens/tour/{i}.png", f"screens/{i}.png") for i in range(1, 6)] + \
        [(f"design/brand/LOGGA/svg/ikon-09-{c}.svg", f"logo/ikon-09-{c}.svg") for c in ("white", "accent", "ink")] + \
        [("app/assets/ios-icon-dark.png", "logo/ios-icon-dark.png")]
for src, dst in pairs:
    s, d = os.path.join(a.social, src), assert_writable(p("assets", "lacrydia", dst))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(s, d)           # copy, never move: originals stay untouched
    print("copied", src, "->", os.path.relpath(d, p()))

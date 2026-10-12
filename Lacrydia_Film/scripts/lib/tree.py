"""The photo table / Tree layout (pure data, no bpy): shared by the 3D shots, the typography and the audio timing.

Coordinates in metres on the obsidian table, +x right, +y 'up' on the camera's screen when looking straight down.
The layout mirrors the real app's Tree screen (root 'My Life' at the bottom, branches Travel / Nature / Friends / Cars)
using the same photographs the app's own onboarding uses.
"""
import random

# id, photo, width(m), role, parent, tree xy, tree yaw(deg), hover z
NODES = [
    # root
    dict(id="root", photo="p2.jpg", w=0.100, level=0, parent=None, xy=(0.00, -0.215), yaw=0.0, z=0.000, label="My Life"),
    # branches
    dict(id="nature", photo="p16.jpg", w=0.070, level=1, parent="root", xy=(-0.350, -0.030), yaw=3.0, z=0.010, label="Nature"),
    dict(id="travel", photo="p4.jpg", w=0.070, level=1, parent="root", xy=(-0.095, 0.150), yaw=-2.0, z=0.012, label="Travel"),
    dict(id="friends", photo="p9.jpg", w=0.076, level=1, parent="root", xy=(0.215, 0.105), yaw=2.5, z=0.010, label="Friends"),
    dict(id="cars", photo="p7.jpg", w=0.066, level=1, parent="root", xy=(0.405, -0.105), yaw=-3.0, z=0.011, label="Cars"),
    # nature
    dict(id="n1", photo="p17.jpg", w=0.046, level=2, parent="nature", xy=(-0.505, 0.115), yaw=-4.0, z=0.024),
    dict(id="n2", photo="p28.jpg", w=0.046, level=2, parent="nature", xy=(-0.470, -0.165), yaw=5.0, z=0.020),
    dict(id="n3", photo="v5.jpg", w=0.042, level=2, parent="nature", xy=(-0.285, 0.130), yaw=2.0, z=0.026),
    # travel
    dict(id="t1", photo="v1.jpg", w=0.042, level=2, parent="travel", xy=(-0.200, 0.305), yaw=3.5, z=0.025),
    dict(id="t2", photo="v7.jpg", w=0.044, level=2, parent="travel", xy=(0.020, 0.300), yaw=-3.0, z=0.022),
    dict(id="t3", photo="p3.jpg", w=0.044, level=2, parent="travel", xy=(-0.300, 0.250), yaw=-5.0, z=0.028),
    # friends
    dict(id="f1", photo="v2.jpg", w=0.044, level=2, parent="friends", xy=(0.185, 0.290), yaw=-2.5, z=0.026),
    dict(id="f2", photo="v6.jpg", w=0.042, level=2, parent="friends", xy=(0.345, 0.235), yaw=4.0, z=0.022),
    dict(id="f3", photo="v3.jpg", w=0.062, level=2, parent="friends", xy=(0.390, 0.065), yaw=-3.5, z=0.027),
    # cars
    dict(id="c1", photo="p8.jpg", w=0.044, level=2, parent="cars", xy=(0.545, 0.000), yaw=2.0, z=0.024),
    dict(id="c2", photo="p1.jpg", w=0.044, level=2, parent="cars", xy=(0.530, -0.225), yaw=-4.0, z=0.021),
]
BY_ID = {n["id"]: n for n in NODES}


def photo_aspect(photo, root="/home/user/Product-ad-blender/Lacrydia_Film/assets/lacrydia/photos"):
    from PIL import Image
    with Image.open(f"{root}/{photo}") as im:
        return im.width / im.height


def scatter_poses(seed=11, region=(-0.50, 0.50, -0.28, 0.30)):
    """Deterministic 'camera roll is a pile' arrangement: loosely overlapping, rotated, slightly stacked."""
    rnd = random.Random(seed)
    poses = {}
    placed = []
    order = [n["id"] for n in NODES]
    for nid in order:
        n = BY_ID[nid]
        if nid == "root":
            poses[nid] = dict(xy=n["xy"], yaw=0.0, z=0.0)       # the root never moves: it is where the tree grows from
            placed.append((n["xy"], n["w"]))
            continue
        for _ in range(400):
            x = rnd.uniform(region[0], region[1])
            y = rnd.uniform(region[2], region[3])
            if all(((x - px) ** 2 + (y - py) ** 2) ** 0.5 > 0.55 * (n["w"] + pw) + 0.02 for (px, py), pw in placed):
                break
        poses[nid] = dict(xy=(x, y), yaw=rnd.uniform(-38, 38), z=rnd.uniform(0.0, 0.012))
        placed.append(((x, y), n["w"]))
    return poses

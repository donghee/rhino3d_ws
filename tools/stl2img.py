#!/usr/bin/env python3
"""Render an STL file to a PNG image with f3d (offscreen, no window).

  stl2img.py <file.stl> [--view V] [--size N] [--color R,G,B] [--out file.png]

  --view   front (default) | back | left | right | top | iso | all
           all = front + iso + right
  --size   image size in pixels, square (default 900)
  --color  model color, 0-1 each (default 0.6,0.42,0.28 = monkey fur brown)
  --out    output path (only with one view)

Default output: next to the STL, <name>_stl.png for front, <name>_stl_<view>.png
for the other views (e.g. monkey_v002_stl.png, monkey_v002_stl_iso.png).
Rhino models are Z-up and face -Y, so the views are set for that.

Needs: f3d (`sudo apt install f3d`).
"""
import os, shutil, subprocess, sys

# camera direction = where the camera looks (Z-up, the model faces -Y), as Rhino's named views.
# top: f3d ignores --camera-view-up there, so the scene up is set to +Y instead (face at the bottom).
VIEWS = {
    "front": ["--up=+Z", "--camera-direction=+Y"],
    "back":  ["--up=+Z", "--camera-direction=-Y"],
    "left":  ["--up=+Z", "--camera-direction=+X"],
    "right": ["--up=+Z", "--camera-direction=-X"],
    "top":   ["--up=+Y", "--camera-direction=-Z"],
    "iso":   ["--up=+Z", "--camera-direction=+Y", "--camera-azimuth-angle=-35", "--camera-elevation-angle=25"],
}


def out_path(stl, view):
    stem = os.path.splitext(stl)[0]
    return f"{stem}_stl.png" if view == "front" else f"{stem}_stl_{view}.png"


def render(stl, view, out, size, color):
    cmd = ["f3d", stl, f"--output={out}", f"--resolution={size},{size}",
           f"--color={color}", "--verbose=quiet", *VIEWS[view]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit(f"f3d failed ({view}): {r.stderr.strip() or r.stdout.strip()}")
    print(out)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 1
    if not shutil.which("f3d"):
        raise SystemExit("f3d not found: sudo apt install f3d")
    stl = os.path.abspath(argv[0])
    if not os.path.isfile(stl):
        raise SystemExit(f"no such file: {stl}")
    opt = {"--view": "front", "--size": "900", "--color": "0.6,0.42,0.28", "--out": None}
    rest = argv[1:]
    for i in range(0, len(rest), 2):
        if rest[i] not in opt or i + 1 >= len(rest):
            raise SystemExit(f"bad option: {rest[i]}\n{__doc__}")
        opt[rest[i]] = rest[i + 1]
    views = ["front", "iso", "right"] if opt["--view"] == "all" else [opt["--view"]]
    for v in views:
        if v not in VIEWS:
            raise SystemExit(f"unknown view {v}: {', '.join(VIEWS)} or all")
    if opt["--out"] and len(views) > 1:
        raise SystemExit("--out works with one view only")
    for v in views:
        render(stl, v, opt["--out"] or out_path(stl, v), opt["--size"], opt["--color"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

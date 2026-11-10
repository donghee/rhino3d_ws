#!/usr/bin/env python3
"""Rhino MCP helper (calls http://norang.lan:10501/ via JSON-RPC).

  rmcp.py call <tool> ['<json args>']     call any MCP tool
  rmcp.py run <script.py>                 run a Python script in Rhino (run_python)
  rmcp.py shot <out.jpg> [view] [mode]    capture viewport (default perspective/Rendered)
  rmcp.py save <model> [script.py]        save next version: <project>/<project>_vNNN.{3dm,jpg,py}
  rmcp.py next <model>                    print next version number
  rmcp.py preview <project> [N]           capture Top/Perspective/Front/Right from Rhino into one PNG named after
                                          the latest saved version (or version N): <project>/<project>_vNNN.png
  rmcp.py stl <model>                     export the open document as <project>_vNNN.stl (NNN = latest saved version)

Linux project path : /home/donghee/mnt/norang/rhino3d_ws
Rhino PC path      : D:/rhino3d_ws  (same folder, CIFS share //norang.lan/d)
"""
import base64, json, os, re, shutil, sys, urllib.request

URL = "http://norang.lan:10501/"
LINUX_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN_ROOT = "D:/rhino3d_ws"


def call(name, args=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args or {}}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    if "error" in r:
        raise SystemExit(f"MCP error: {r['error']}")
    return r["result"].get("content", [])


def texts(content):
    return "\n".join(c.get("text", "") for c in content if c["type"] == "text")


BBOX_PY = """
import json
doc = __rhino_doc__
doc.Objects.UnselectAll()
bb = None
for o in doc.Objects:
    if o.IsDeleted or not o.Visible: continue
    b = o.Geometry.GetBoundingBox(True)
    if bb is None: bb = b
    else: bb.Union(b)
doc.Views.Redraw()
print(json.dumps(None if bb is None else [list(bb.Min), list(bb.Max)]))
"""


def shot(out, view="perspective", mode="Rendered", w=960, h=720):
    """Capture viewport framed on all visible objects (selection cleared)."""
    args = {"width": w, "height": h, "view": view, "displayMode": mode}
    res = json.loads(texts(call("run_python", {"script": BBOX_PY})))
    bb = json.loads(res["stdout"]) if isinstance(res, dict) else None
    if bb:
        args["boxMin"] = dict(zip("xyz", bb[0]))
        args["boxMax"] = dict(zip("xyz", bb[1]))
    for c in call("get_viewport_image", args):
        if c["type"] == "image":
            open(out, "wb").write(base64.b64decode(c["data"]))
            return out
    raise SystemExit("no image returned")


# Rhino's four default viewports, in their usual places: Top | Perspective / Front | Right
FOUR_VIEWS = [("top", "Top"), ("perspective", "Perspective"), ("front", "Front"), ("right", "Right")]


def preview4(model, version=None, w=640, h=480, mode="Rendered"):
    """Capture the open Rhino document in four views and tile them into one PNG,
    named after the latest saved version (<model>_vNNN.png, rewritten on each run)."""
    import io
    from PIL import Image, ImageDraw
    d = os.path.join(LINUX_ROOT, model)
    os.makedirs(d, exist_ok=True)
    sheet = Image.new("RGB", (w * 2, h * 2), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (view, label) in enumerate(FOUR_VIEWS):
        buf = shot_bytes(view, mode, w, h)
        im = Image.open(io.BytesIO(buf)).convert("RGB").resize((w, h))
        x, y = (i % 2) * w, (i // 2) * h
        sheet.paste(im, (x, y))
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(150, 150, 150))
        draw.text((x + 10, y + 8), label, fill=(40, 40, 40))
    n = int(version) if version else next_version(model) - 1
    if n < 1:
        raise SystemExit(f"no saved version of {model} yet: save first (rmcp.py save {model})")
    out = os.path.join(d, f"{model}_v{n:03d}.png")
    sheet.save(out)
    print(out)
    return out


def shot_bytes(view, mode, w, h):
    """One framed viewport capture, as image bytes."""
    args = {"width": w, "height": h, "view": view, "displayMode": mode}
    res = json.loads(texts(call("run_python", {"script": BBOX_PY})))
    bb = json.loads(res["stdout"]) if isinstance(res, dict) else None
    if bb:
        args["boxMin"] = dict(zip("xyz", bb[0]))
        args["boxMax"] = dict(zip("xyz", bb[1]))
    for c in call("get_viewport_image", args):
        if c["type"] == "image":
            return base64.b64decode(c["data"])
    raise SystemExit(f"no image returned for {view}")


def next_version(model):
    d = os.path.join(LINUX_ROOT, model)
    nums = [int(m.group(1)) for f in (os.listdir(d) if os.path.isdir(d) else [])
            if (m := re.fullmatch(rf"{re.escape(model)}_v(\d{{3}})\.3dm", f))]
    return max(nums, default=0) + 1


def save(model, script=None):
    n = next_version(model)
    base = f"{model}_v{n:03d}"
    d = os.path.join(LINUX_ROOT, model)
    os.makedirs(d, exist_ok=True)
    win = f"{WIN_ROOT}/{model}/{base}.3dm"
    if os.path.exists(os.path.join(d, base + ".3dm")):
        raise SystemExit(f"refusing to overwrite {base}.3dm")
    print(texts(call("save_doc", {"path": win})))
    shot(os.path.join(d, base + ".jpg"))
    if script:
        shutil.copy(script, os.path.join(d, base + ".py"))
    print(f"saved {d}/{base}.3dm (+ .jpg{' + .py' if script else ''})")
    return base


STL_PY = """
def main():
    import struct
    import Rhino
    from Rhino.Geometry import Mesh, MeshingParameters, Vector3d
    doc = __rhino_doc__
    out = OUT_PATH
    mp = MeshingParameters.QualityRenderMesh
    big = Mesh(); parts = 0
    for o in doc.Objects:
        if o.IsDeleted: continue
        g = o.Geometry
        if isinstance(g, Rhino.Geometry.Brep):
            for m in Mesh.CreateFromBrep(g, mp) or []:
                big.Append(m); parts += 1
        elif isinstance(g, Mesh):
            big.Append(g); parts += 1
    big.Faces.ConvertQuadsToTriangles(); big.Compact()
    V = big.Vertices; F = big.Faces
    with open(out, "wb") as f:
        f.write(NAME.encode().ljust(80, b" ")); f.write(struct.pack("<I", F.Count))
        for i in range(F.Count):
            fc = F[i]; a, b, c = V[fc.A], V[fc.B], V[fc.C]
            n = Vector3d.CrossProduct(Vector3d(b.X-a.X, b.Y-a.Y, b.Z-a.Z), Vector3d(c.X-a.X, c.Y-a.Y, c.Z-a.Z)); n.Unitize()
            f.write(struct.pack("<12fH", n.X, n.Y, n.Z, a.X, a.Y, a.Z, b.X, b.Y, b.Z, c.X, c.Y, c.Z, 0))
    print(parts, F.Count, str(doc.ModelUnitSystem))
main()
"""


def export_stl(model):
    """Write the open Rhino document as <model>_vNNN.stl for the latest saved version."""
    n = next_version(model) - 1
    if n < 1:
        raise SystemExit(f"no saved version of {model} yet")
    base = f"{model}_v{n:03d}"
    local = os.path.join(LINUX_ROOT, model, base + ".stl")
    if os.path.exists(local):
        raise SystemExit(f"refusing to overwrite {local}")
    script = STL_PY.replace("OUT_PATH", repr(f"{WIN_ROOT}/{model}/{base}.stl")).replace("NAME", repr(base))
    res = json.loads(texts(call("run_python", {"script": script})))
    if res.get("stderr"):
        raise SystemExit(res["stderr"])
    parts, tris, units = res["stdout"].split()
    print(f"saved {local}: {tris} triangles from {parts} meshes, units {units}")
    print("note: exported from the document open in Rhino now; check it is that version")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    cmd = a[0]
    if cmd == "call":
        print(texts(call(a[1], json.loads(a[2]) if len(a) > 2 else {})))
    elif cmd == "run":
        print(texts(call("run_python", {"script": open(a[1], encoding="utf-8").read()})))
    elif cmd == "shot":
        print(shot(a[1], *(a[2:4])))
    elif cmd == "save":
        save(a[1], a[2] if len(a) > 2 else None)
    elif cmd == "preview":
        preview4(a[1], a[2] if len(a) > 2 else None)
    elif cmd == "stl":
        export_stl(a[1])
    elif cmd == "next":
        print(f"{a[1]}_v{next_version(a[1]):03d}")
    else:
        print(__doc__); sys.exit(1)

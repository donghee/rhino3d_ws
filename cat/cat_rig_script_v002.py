"""Cat rig (Grasshopper Python 3). Poses the parts of cat_vNNN.3dm from slider inputs.
Rest pose is read from the .3dm file (src). Outputs G (geometry) and C (colours) for Custom Preview.
Left/Right are the cat's own sides: the cat faces -Y, so its left is +X."""
import os, math
import System
import Rhino
import Rhino.Geometry as rg
import Grasshopper
from System.Drawing import Color

DEFAULT_SRC = "D:/rhino3d_ws/cat/cat_v002.3dm"
HEAD = {"Head", "Cheek", "WhiskerPad", "Chin", "NoseBridge", "Nose", "Philtrum", "Mouth", "Eye", "Pupil", "Highlight", "Ear", "EarInner", "Whisker"}
LASER = {"LaserCore", "LaserGlow", "EyeFlare", "EyeFlareGlow", "Impact", "ImpactGlow", "Scorch"}
TAIL_PTS = [(0, 13.5, 3.5), (6, 13, 2.3), (11, 7, 2.0), (11.8, -1, 2.0), (10.5, -7.5, 2.0), (8.5, -12, 2.2)]
NECK = rg.Point3d(0, -5, 28)
_CACHE = {}


def load(path):
    key = (path, os.path.getmtime(path))
    if _CACHE.get("key") != key:
        f = Rhino.FileIO.File3dm.Read(path)
        colors = {L.Name: L.Color for L in f.AllLayers}
        parts = []
        for o in f.Objects:
            lname = f.AllLayers.FindIndex(o.Attributes.LayerIndex).Name
            parts.append((o.Attributes.Name or "", lname, o.Geometry.Duplicate()))
        _CACHE.update(key=key, parts=parts, colors=colors)
    return _CACHE["parts"], _CACHE["colors"]


def ell(c, rx, ry, rz):
    s = rg.Sphere(rg.Point3d.Origin, 1).ToNurbsSurface()
    s.Transform(rg.Transform.Scale(rg.Plane.WorldXY, rx, ry, rz))
    s.Transform(rg.Transform.Translation(rg.Vector3d(c[0], c[1], c[2])))
    return s.ToBrep()


def pipe(crv, r0, r1):
    b = rg.Brep.CreatePipe(crv, [crv.Domain.T0, crv.Domain.T1], [r0, r1], True, rg.PipeCapMode.Round, True, 0.01, 0.01)
    if not b:
        b = rg.Brep.CreatePipe(crv, r0, False, rg.PipeCapMode.Round, True, 0.01, 0.01)
    return b[0] if b else None


class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, src, head_yaw, head_nod, head_tilt, ear_l, ear_r, pupil, paw_l, paw_r, tail_unwrap, tail_lift, breath, whisker_lift, whisker_spread, laser, hide_doc):
        val = lambda x, d: d if x is None else float(x)
        rad = math.radians
        path = (str(src).strip() if src else "") or DEFAULT_SRC
        if not os.path.exists(path):
            raise Exception("rest pose file not found: " + path)
        parts, colors = load(path)
        X, Y, Z = rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # head: yaw (+ = turn to cat's left), nod (+ = look down), tilt (+ = tilt to cat's left)
        H = rg.Transform.Rotation(rad(val(head_yaw, 0)), Z, NECK) * rg.Transform.Rotation(rad(val(head_nod, 0)), X, NECK) * rg.Transform.Rotation(rad(val(head_tilt, 0)), -Y, NECK)
        G, C = [], []

        def out(g, c):
            if g is not None:
                G.append(g)
                C.append(c)

        for name, lname, g0 in parts:
            if name in LASER or lname in LASER or name == "Tail":
                continue
            g = g0.Duplicate()
            ctr = g.GetBoundingBox(True).Center
            sx = 1 if ctr.X > 0 else -1          # +1 = cat's left
            if name in ("Ear", "EarInner"):       # ear: + = flatten outward
                a = val(ear_l, 0) if sx > 0 else val(ear_r, 0)
                g.Transform(rg.Transform.Rotation(sx * rad(a), Y, rg.Point3d(sx * 5.8, -4.8, 38.6)))
            if name == "Whisker":                 # whisker: lift (+ = tips up), spread (+ = fan apart), degrees
                k = round((ctr.Z - 30.0) / 1.35)  # +1 top, 0 middle, -1 bottom
                a = val(whisker_lift, 0) + k * val(whisker_spread, 0)
                g.Transform(rg.Transform.Rotation(rad(a), -sx * Y, rg.Point3d(sx * 2.4, -15.0, 29.9 + 0.45 * k)))
            if name == "Pupil":                   # pupil width factor
                g.Transform(rg.Transform.Scale(rg.Plane(ctr, X, Y), val(pupil, 1), 1, 1))
            if name in HEAD:
                g.Transform(H)
            if name in ("FrontLeg", "FrontPaw"):  # paw lift: degrees forward/up
                a = val(paw_l, 0) if sx > 0 else val(paw_r, 0)
                g.Transform(rg.Transform.Rotation(-rad(a), X, rg.Point3d(sx * 4.0, -8.5, 19.0)))
            if name in ("Chest", "Ruff", "Haunch"):
                s = 1 + 0.05 * val(breath, 0)
                g.Transform(rg.Transform.Scale(ctr, s))
            out(g, colors.get(lname, Color.Gray))

        # tail: progressive rotation about its root (+ = unwrap away from the body), tip lift in mm
        base = rg.Point3d(*TAIL_PTS[0])
        n = len(TAIL_PTS)
        pts = []
        for i, p in enumerate(TAIL_PTS):
            u = i / float(n - 1)
            q = rg.Transform.Rotation(rad(val(tail_unwrap, 0)) * u, Z, base) * rg.Point3d(*p)
            pts.append(rg.Point3d(q.X, q.Y, q.Z + val(tail_lift, 0) * u ** 1.5))
        out(pipe(rg.Curve.CreateInterpolatedCurve(pts, 3), 2.6, 2.1), colors.get("Fur", Color.Gray))

        # laser: follows the head; both beams converge where the gaze hits the floor
        if laser is None or bool(laser):
            core = colors.get("LaserCore", Color.White)
            glow = Color.FromArgb(110, colors.get("LaserGlow", Color.Red))
            eyes = [H * rg.Point3d(sx * 3.75, -14.15, 34.6) for sx in (-1, 1)]
            M = rg.Point3d((eyes[0].X + eyes[1].X) / 2, (eyes[0].Y + eyes[1].Y) / 2, (eyes[0].Z + eyes[1].Z) / 2)
            D = H * rg.Vector3d(0, -37.85, -34.6)
            D = D / D.Length
            t = -(M.Z - 0.15) / D.Z if D.Z < -0.02 else 1e9
            ground = t < 150
            ends = [M + D * t] * 2 if ground else [e + D * 120 for e in eyes]
            for e, end in zip(eyes, ends):
                ln = rg.LineCurve(e, end)
                out(pipe(ln, 0.18, 0.18), core)
                out(pipe(ln, 0.45, 0.75), glow)
            for sx in (-1, 1):
                f1 = ell((sx * 3.75, -14.25, 34.6), 0.9, 0.5, 0.9); f1.Transform(H); out(f1, core)
                f2 = ell((sx * 3.75, -14.35, 34.6), 1.6, 0.7, 1.6); f2.Transform(H); out(f2, glow)
            if ground:
                h = ends[0]
                out(ell((h.X, h.Y, 0.3), 1.4, 1.4, 0.8), core)
                out(ell((h.X, h.Y, 0.4), 3.2, 3.2, 1.6), glow)
                out(ell((h.X, h.Y, 0.02), 5.5, 5.5, 0.05), colors.get("Scorch", Color.Black))

        # hide the static cat in the Rhino document so only the posed preview shows
        rdoc = Rhino.RhinoDoc.ActiveDoc
        li = rdoc.Layers.FindByFullPath("Cat", -1) if rdoc else -1
        if li >= 0:
            vis = not (True if hide_doc is None else bool(hide_doc))
            L = rdoc.Layers[li]
            if L.IsVisible != vis:
                L.IsVisible = vis
                L.SetPersistentVisibility(vis)
                rdoc.Views.Redraw()
        return G, C

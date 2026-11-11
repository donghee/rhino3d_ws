# Flightory STALLION (V2) RC plane - Rhino model
# v002: FC bay + hatch lid, spar/boom/wire holes, split into Prusa MK3 (250x210x210) printable parts
# Sources: flightory.com/product/stallion, STALLION-MANUALV2.pdf (p.3 top-view drawing measured: 1px = 1.112 mm)
# Axes: X = span (right +X), Y = aft (nose at -Y, model front faces -Y), Z = up. Units mm.
# s = distance aft of nose tip; world y = s - 340 (CG ~ y = -9).
def main():
    import math, time
    import Rhino, System
    from System.Collections.Generic import List
    from System.Drawing import Color
    from Rhino.Geometry import (Point3d, Vector3d, Plane, Transform, Brep, Curve, NurbsSurface, LineCurve,
        Circle, Cylinder, Box, Interval, BoundingBox, LoftType, PipeCapMode, Surface, GeometryBase, TextEntity)
    from Rhino.Geometry.Intersect import Intersection
    doc = __rhino_doc__
    tol = doc.ModelAbsoluteTolerance
    atol = doc.ModelAngleToleranceRadians
    t0 = time.time(); log = []

    # ---------- stop Grasshopper preview (cat rig) so it does not show in captures ----------
    try:
        import Grasshopper
        from Grasshopper.Kernel import GH_PreviewMode
        for gd in Grasshopper.Instances.DocumentServer:
            gd.Enabled = False
            gd.PreviewMode = GH_PreviewMode.Disabled
    except Exception as e:
        log.append("gh preview: %s" % e)

    # ---------- empty document ----------
    for o in list(doc.Objects): doc.Objects.Purge(o)
    di = doc.Layers.FindByFullPath("Default", -1)
    if di < 0:
        L = Rhino.DocObjects.Layer(); L.Name = "Default"; di = doc.Layers.Add(L)
    doc.Layers.SetCurrentLayerIndex(di, True)
    for _ in range(4):
        for L in list(doc.Layers):
            if L.Index != di and not L.IsDeleted: doc.Layers.Purge(L.Index, True)

    def layer(name, c, shine=0.0, transp=0.0):
        p = doc.Layers.FindByFullPath("Stallion", -1)
        if p < 0:
            L = Rhino.DocObjects.Layer(); L.Name = "Stallion"; p = doc.Layers.Add(L)
        L = Rhino.DocObjects.Layer(); L.Name = name; L.Color = c; L.ParentLayerId = doc.Layers[p].Id
        i = doc.Layers.Add(L)
        m = Rhino.DocObjects.Material(); m.DiffuseColor = c; m.Name = "Stallion_" + name
        m.Shine = shine * Rhino.DocObjects.Material.MaxShine; m.Transparency = transp
        mi = doc.Materials.Add(m); L = doc.Layers[i]; L.RenderMaterialIndex = mi; doc.Layers.Modify(L, i, True)
        return i
    LY = {
        "Fuselage": layer("Fuselage", Color.FromArgb(198, 202, 207), 0.25),
        "NoseCap": layer("NoseCap", Color.FromArgb(82, 94, 114), 0.3),
        "Wing": layer("Wing", Color.FromArgb(198, 202, 207), 0.25),
        "ControlSurface": layer("ControlSurface", Color.FromArgb(188, 192, 198), 0.25),
        "Tail": layer("Tail", Color.FromArgb(198, 202, 207), 0.25),
        "Hardware": layer("Hardware", Color.FromArgb(68, 71, 76), 0.35),
        "MotorMount": layer("MotorMount", Color.FromArgb(214, 216, 219), 0.3),
        "Carbon": layer("Carbon", Color.FromArgb(24, 24, 27), 0.8),
        "Motor": layer("Motor", Color.FromArgb(32, 32, 36), 0.6),
        "MotorMetal": layer("MotorMetal", Color.FromArgb(176, 179, 184), 0.9),
        "Prop": layer("Prop", Color.FromArgb(20, 20, 22), 0.5),
        "Camera": layer("Camera", Color.FromArgb(14, 14, 16), 0.7),
        "Lens": layer("Lens", Color.FromArgb(28, 44, 72), 1.0),
        "Grille": layer("Grille", Color.FromArgb(34, 36, 40), 0.2),
        "Antenna": layer("Antenna", Color.FromArgb(26, 26, 28), 0.4),
        "PanelLine": layer("PanelLine", Color.FromArgb(118, 122, 128), 0.1),
        "Decal": layer("Decal", Color.FromArgb(22, 22, 24), 0.1),
    }
    count = [0]
    def add(geo, ly, name):
        if geo is None: log.append("missing " + name); return None
        a = Rhino.DocObjects.ObjectAttributes(); a.LayerIndex = LY[ly]; a.Name = name
        count[0] += 1
        return doc.Objects.AddBrep(geo, a) if isinstance(geo, Brep) else doc.Objects.Add(geo, a)

    # ---------- helpers ----------
    def P(x, s, z): return Point3d(x, s - 340.0, z)
    def plist(pts):
        L = List[Point3d]()
        for p in pts: L.Add(p)
        return L
    def cpcurve(pts, deg=3): return Curve.CreateControlPointCurve(plist(pts), deg)
    def loft(curves, end=None, start=None, cap=True):
        L = List[Curve]()
        for c in curves: L.Add(c)
        r = Brep.CreateFromLoft(L, start if start else Point3d.Unset, end if end else Point3d.Unset, LoftType.Normal, False)
        if not r: return None
        b = r[0]
        if cap:
            c2 = b.CapPlanarHoles(tol)
            if c2: b = c2
        if b.IsSolid and b.SolidOrientation == Rhino.Geometry.BrepSolidOrientation.Inward: b.Flip()
        return b
    def cyl(p0, axis, r, length, caps=True):
        a = Vector3d(axis); a.Unitize()
        c = Cylinder(Circle(Plane(p0, a), r), length)
        return c.ToBrep(caps, caps)
    def pipe(curve, r, cap=PipeCapMode.Round):
        try:
            res = Brep.CreatePipe(curve, r, False, cap, True, tol, atol)
            return res[0] if res else None
        except Exception as e:
            log.append("pipe: %s" % e); return None
    def boxb(plane, dx, dy, dz):
        return Box(plane, Interval(-dx / 2, dx / 2), Interval(-dy / 2, dy / 2), Interval(-dz / 2, dz / 2)).ToBrep()
    def xform(geo, T):
        g = geo.DuplicateBrep() if isinstance(geo, Brep) else geo.Duplicate()
        g.Transform(T); return g
    MIR = Transform.Mirror(Plane.WorldYZ)
    def smax(a, b, r):
        h = max(0.0, min(1.0, 0.5 + 0.5 * (a - b) / r))
        return b * (1 - h) + a * h + r * h * (1 - h)
    def smin(a, b, r): return -smax(-a, -b, r)
    def pchip(T):
        xs = [a for a, _ in T]; ys = [b for _, b in T]; n = len(xs)
        h = [xs[i + 1] - xs[i] for i in range(n - 1)]
        d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
        m = [0.0] * n; m[0] = d[0]; m[-1] = d[-1]
        for i in range(1, n - 1):
            if d[i - 1] * d[i] <= 0: m[i] = 0.0
            else:
                w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        def f(x):
            if x <= xs[0]: return ys[0]
            if x >= xs[-1]: return ys[-1]
            lo, hi = 0, n - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if xs[mid] <= x: lo = mid
                else: hi = mid
            i = lo; t = (x - xs[i]) / h[i]
            h00 = 2 * t**3 - 3 * t**2 + 1; h10 = t**3 - 2 * t**2 + t; h01 = -2 * t**3 + 3 * t**2; h11 = t**3 - t**2
            return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
        return f
    def hit(breps, origin, direction):
        """first intersection of a ray with breps -> (point, outward normal) or None"""
        d = Vector3d(direction); d.Unitize()
        lc = LineCurve(origin, origin + d * 2000.0)
        best = None
        for b in breps:
            ok, oc, pts = Intersection.CurveBrep(lc, b, tol)
            if not ok or pts is None: continue
            for p in pts:
                t = (p - origin) * d
                if best is None or t < best[0]: best = (t, p, b)
        if best is None: return None
        p, b = best[1], best[2]
        rc = b.ClosestPoint(p, 1.0)
        n = rc[5] if len(rc) > 5 else -d
        n = Vector3d(n); n.Unitize()
        if n * d > 0: n = -n
        return p, n

    # ---------- airfoils ----------
    E205 = [(1.000000, 0.000000), (0.996550, 0.000390), (0.986490, 0.001740), (0.970490, 0.004270), (0.949160, 0.007780), (0.922850, 0.011960), (0.891750, 0.016680), (0.856240, 0.021990), (0.816840, 0.027860), (0.774120, 0.034190), (0.728660, 0.040880), (0.681080, 0.047770), (0.632040, 0.054700), (0.582180, 0.061470), (0.532170, 0.067820), (0.482650, 0.073420), (0.434100, 0.077850), (0.386800, 0.080810), (0.341010, 0.082140), (0.296990, 0.081770), (0.254960, 0.079700), (0.215080, 0.076060), (0.177640, 0.071110), (0.143020, 0.065070), (0.111570, 0.058110), (0.083600, 0.050400), (0.059370, 0.042110), (0.039090, 0.033440), (0.022920, 0.024610), (0.010970, 0.015890), (0.003310, 0.007660), (0.000020, 0.000550), (0.002330, -0.005060), (0.010650, -0.009880), (0.024190, -0.014200), (0.042910, -0.017760), (0.066690, -0.020530), (0.095340, -0.022520), (0.128640, -0.023780), (0.166270, -0.024360), (0.207830, -0.024350), (0.252900, -0.023840), (0.300970, -0.022920), (0.351490, -0.021680), (0.403880, -0.020210), (0.457510, -0.018590), (0.511740, -0.016890), (0.565910, -0.015160), (0.619380, -0.013450), (0.671490, -0.011800), (0.721600, -0.010230), (0.769110, -0.008760), (0.813430, -0.007400), (0.854000, -0.006140), (0.890340, -0.004970), (0.921950, -0.003800), (0.948600, -0.002520), (0.970170, -0.001250), (0.986350, -0.000360), (0.996510, -0.000030), (1.000000, 0.000000)]
    ile = min(range(len(E205)), key=lambda i: E205[i][0])
    UP = sorted(E205[:ile + 1]); LO = sorted(E205[ile:])
    def lin(arr, x):
        if x <= arr[0][0]: return arr[0][1]
        for (x0, y0), (x1, y1) in zip(arr, arr[1:]):
            if x <= x1: return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y0
        return arr[-1][1]
    def fu(t): return lin(UP, t)
    def fl(t): return lin(LO, t)
    def n00(th):
        def yt(t): return 5 * th * (0.2969 * math.sqrt(max(t, 0)) - 0.1260 * t - 0.3516 * t**2 + 0.2843 * t**3 - 0.1036 * t**4)
        return (lambda t: yt(t)), (lambda t: -yt(t))
    def foil2d(fuu, fll, n=40):
        ts = [0.5 * (1 - math.cos(math.pi * i / n)) for i in range(n + 1)]
        pts = [(t, fuu(t)) for t in reversed(ts)] + [(t, fll(t)) for t in ts[1:]]
        pts[-1] = pts[0]
        return pts
    FOIL = foil2d(fu, fl)
    TAILF = foil2d(*n00(0.09))
    def section(le, dvec, nvec, chord, pts2d):
        return cpcurve([le + dvec * (u * chord) + nvec * (v * chord) for u, v in pts2d])

    # ================= FUSELAGE (blended body + centre wing + fillets) =================
    bfun = pchip([(0, 0), (0.5, 5.2), (1, 7.3), (2, 10.5), (4, 14.5), (8, 19.5), (13, 23), (24, 32), (36, 40), (47, 46),
                  (58, 50), (69, 53), (80, 57), (102, 62), (125, 66), (147, 70), (169, 73), (191, 76), (214, 78), (240, 79),
                  (300, 79), (360, 77), (420, 72), (470, 64), (510, 56), (550, 44), (580, 31), (600, 22), (620, 16), (640, 13)])
    ztf = pchip([(0, -15), (0.5, -10), (1, -8), (2, -5), (4, -1), (8, 4), (13, 9), (25, 17), (50, 30), (80, 40), (120, 48),
                 (170, 53), (230, 56), (300, 56), (370, 54), (430, 48), (490, 36), (540, 20), (590, 2), (620, -10), (640, -17)])
    zbf = pchip([(0, -15), (0.5, -20), (1, -22.5), (2, -26), (4, -31), (8, -37), (13, -42), (25, -51), (50, -63), (80, -73),
                 (120, -80), (170, -85), (230, -88), (300, -88), (370, -86), (430, -80), (490, -70), (540, -58), (590, -47),
                 (620, -43), (640, -43)])
    # planform edge of the LE / TE fillets (measured)
    wff = pchip([(190, 0), (214, 80), (225, 89), (236, 95), (247, 103), (258, 114), (265, 125), (269, 138), (271, 150),
                 (501, 150), (503, 142), (507, 120), (513, 100), (524, 80), (538, 60), (552, 45), (566, 0)])
    def Wp(s):
        w = wff(s) if 190 <= s <= 566 else 0.0
        return max(bfun(s), w)
    WLE, WTE = 271.0, 501.0           # centre-section chord at x = 150 (230 mm)
    KF, TE = 0.22, 0.8
    def kfac(s):
        if s <= WLE: return KF
        if s < 330: return KF * (330 - s) / (330 - WLE)
        if s < 440: return 0.0
        if s < WTE: return KF * (s - 440) / (WTE - 440)
        return KF
    def body_uz(x, s):
        bb = bfun(s)
        if bb < 1e-6 or abs(x) >= bb: return None
        zt, zb = ztf(s), zbf(s); zc = 0.5 * (zt + zb); h = 0.5 * (zt - zb)
        qu = (1 - (abs(x) / bb) ** 2.3) ** (1 / 2.3)
        ql = (1 - (abs(x) / bb) ** 2.2) ** (1 / 2.2)
        return zc + h * qu, zc - h * ql
    def skin(x, s, W):
        if W <= bfun(s) + 0.3: return None
        ax = min(abs(x), W)
        d = W - ax
        wedge = TE + kfac(s) * d + 4.5 * (1 - math.exp(-d / 7.0)) * min(1.0, (W - bfun(s)) / 25.0)  # rounded fillet edge
        su, sl = 0.6 * wedge, -0.4 * wedge
        if WLE <= s <= WTE:
            t = (s - WLE) / (WTE - WLE); c = WTE - WLE
            su = smax(c * fu(t), su, 3.0); sl = smin(c * fl(t), sl, 3.0)
        return su, sl
    RF = 16.0
    def zul(x, s, W):
        bz = body_uz(x, s); sk = skin(x, s, W)
        if bz is None and sk is None:
            zt, zb = ztf(s), zbf(s); zc = 0.5 * (zt + zb); return zc, zc
        if sk is None: return bz
        if bz is None: return sk
        return smax(bz[0], sk[0], RF), smin(bz[1], sk[1], RF)
    M = 200
    def body_row(s):
        W = Wp(s); y = s - 340.0
        if W < 1e-6:
            z = ztf(s); return [Point3d(0, y, z)] * (M + 1)
        n = 220
        xs = [W * math.cos(math.pi * i / n) for i in range(n + 1)]            # +W -> -W
        upper = [(x, zul(x, s, W)[0]) for x in xs]
        lower = [(x, zul(x, s, W)[1]) for x in reversed(xs)]                  # -W -> +W
        half = n // 2
        loop = lower[half:] + upper + lower[:half + 1]                        # start/end at bottom centre
        L = [0.0]
        for (x0, z0), (x1, z1) in zip(loop, loop[1:]): L.append(L[-1] + math.hypot(x1 - x0, z1 - z0))
        tot = L[-1]; out = []; j = 0
        for k in range(M + 1):
            tl = tot * k / M
            while j < len(L) - 2 and L[j + 1] < tl: j += 1
            seg = L[j + 1] - L[j]; f = (tl - L[j]) / seg if seg > 1e-12 else 0.0
            x = loop[j][0] + (loop[j + 1][0] - loop[j][0]) * f; z = loop[j][1] + (loop[j + 1][1] - loop[j][1]) * f
            out.append(Point3d(x, y, z))
        out[-1] = out[0]
        return out
    SN = 85.0  # nose cap joint
    st = [0, 0.25, 0.6, 1.2, 2, 3, 4.5, 6.5, 9, 12, 16, 21, 27, 34, 42, 51, 61, 72, SN]
    st += [SN + (220 - SN) * i / 18 for i in range(1, 19)]
    st += [220 + 4 * i for i in range(1, 86)]
    st += [560 + 5 * i for i in range(1, 17)]
    def surf(stations):
        rows = [body_row(s) for s in stations]
        pts = plist([p for r in rows for p in r])
        return NurbsSurface.CreateFromPoints(pts, len(stations), M + 1, 3, 3)
    i85 = st.index(SN)
    nose_srf = surf(st[:i85 + 1]); body_srf = surf(st[i85:])
    nose_b = nose_srf.ToBrep() if nose_srf else None
    body_b = body_srf.ToBrep() if body_srf else None
    if body_b:
        cb = body_b.CapPlanarHoles(tol)
        if cb: body_b = cb
    add(nose_b, "NoseCap", "Nose cap")
    add(body_b, "Fuselage", "Fuselage + centre wing")
    BODY = [b for b in (nose_b, body_b) if b]
    log.append("body %.1fs" % (time.time() - t0))
    # nose joint groove
    ok, crvs, _ = Intersection.BrepPlane(body_b, Plane(P(0, SN + 0.3, 0), Vector3d(0, 1, 0)), tol)
    if ok and crvs:
        for c in crvs: add(pipe(c, 0.55), "PanelLine", "Nose joint")

    # ================= OUTER WING PANELS =================
    DIH = math.radians(1.0)
    XS, R_TIP, TH_TIP = 595.0, 80.0, math.radians(65.0)
    def sLE(x): return 271.0 + 0.06 * (x - 150.0)
    def sTE(x): return 501.0 - 0.096 * (x - 150.0)
    def zstr(x): return (x - 150.0) * math.tan(DIH)
    c0 = sTE(XS) - sLE(XS); mid0 = sLE(XS) + 0.45 * c0
    def wing_station_x(x):
        n = Vector3d(-math.sin(DIH), 0, math.cos(DIH))
        return P(x, sLE(x), zstr(x)), Vector3d(0, 1, 0), n, sTE(x) - sLE(x)
    zA = zstr(XS)
    cx_, cz_ = XS - R_TIP * math.sin(DIH), zA + R_TIP * math.cos(DIH)
    def arc_pt(f):
        a = DIH + TH_TIP * f
        return cx_ + R_TIP * math.sin(a), cz_ - R_TIP * math.cos(a), a
    def wing_station_f(f):
        x, z, a = arc_pt(f)
        chord = c0 * math.sqrt(max(0.0, 1 - f ** 1.5)); mid = mid0 + 30.0 * f * f
        return P(x, mid - 0.45 * chord, z), Vector3d(0, 1, 0), Vector3d(-math.sin(a), 0, math.cos(a)), chord
    SEAMS_X = [308.0, 444.0, 580.0]
    wx = [150, 175, 205, 240, 275, 308, 340, 380, 420, 444, 480, 520, 558, 580, XS]
    secs = [section(*wing_station_x(x), FOIL) for x in wx]
    secs += [section(*wing_station_f(f), FOIL) for f in (0.12, 0.25, 0.38, 0.5, 0.62, 0.72, 0.81, 0.88, 0.94, 0.975)]
    tx, tz, _ = arc_pt(1.0)
    wingR = loft(secs, end=P(tx, mid0 + 30.0, tz))
    log.append("wing solid=%s" % (wingR.IsSolid if wingR else None))
    # aileron: x 310..558, hinge line s 430 -> 416 (measured), 0.8 mm gap
    def prism(poly_xs, z0=-40.0, h=110.0):
        pl = Rhino.Geometry.PolylineCurve(plist([Point3d(a, b, z0) for a, b in poly_xs] + [Point3d(poly_xs[0][0], poly_xs[0][1], z0)]))
        srf = Surface.CreateExtrusion(pl, Vector3d(0, 0, h))
        b = srf.ToBrep(); c = b.CapPlanarHoles(tol)
        if c is None: return None
        if c.SolidOrientation == Rhino.Geometry.BrepSolidOrientation.Inward: c.Flip()
        return c
    def hinge(x): return 430.0 - (x - 310.0) * 14.0 / 248.0
    def ail_poly(g):
        x0, x1 = 310.0 - g, 558.0 + g
        return [(x0, hinge(x0) - g - 340), (x1, hinge(x1) - g - 340), (x1, 540 - 340), (x0, 540 - 340)]
    wing_main, aileron = wingR, None
    try:
        outer = prism(ail_poly(0.8)); inner = prism(ail_poly(-0.8))
        d = Brep.CreateBooleanDifference(wingR, outer, tol)
        it = Brep.CreateBooleanIntersection(wingR, inner, tol)
        if d and it:
            wing_main = max(d, key=lambda b: b.GetBoundingBox(True).Diagonal.Length); aileron = it[0]
        else: log.append("aileron boolean failed")
    except Exception as e:
        log.append("aileron: %s" % e)
    seam_curves = [section(*wing_station_x(x), FOIL) for x in SEAMS_X]
    for side, T in (("R", Transform.Identity), ("L", MIR)):
        add(xform(wing_main, T), "Wing", "Wing panel " + side)
        if aileron: add(xform(aileron, T), "ControlSurface", "Aileron " + side)
        for c, x in zip(seam_curves, SEAMS_X):
            pb = pipe(c, 0.35)
            if pb: add(xform(pb, T), "PanelLine", "Wing seam %s x%d" % (side, x))
    WINGS = [wing_main, xform(wing_main, MIR)]
    log.append("wing %.1fs" % (time.time() - t0))

    # ================= MOTOR NACELLES, MOTORS, PROPS (right, then mirror) =================
    MX = 308.0; MZ = zstr(MX) + 3.0
    def rsec(xc, s, zc, a, b, n=4.0, N=40):
        pts = []
        for i in range(N + 1):
            ph = -math.pi / 2 + 2 * math.pi * i / N
            c, sn = math.cos(ph), math.sin(ph)
            pts.append(P(xc + a * math.copysign(abs(c) ** (2 / n), c), s, zc + b * math.copysign(abs(sn) ** (2 / n), sn)))
        pts[-1] = pts[0]
        return cpcurve(pts)
    mount = loft([rsec(MX, s, MZ, a, b, n) for s, a, b, n in
                  ((246, 14, 13.5, 2.2), (252, 13.8, 13, 2.8), (262, 13.2, 11.5, 3.5), (285, 12.5, 10, 3.8), (305, 12, 9, 3.8))])
    ax = Vector3d(0, -1, 0)
    def mc(s0, s1, r, ly, nm):
        return (cyl(P(MX, s1, MZ), ax, r, s1 - s0), ly, nm)
    motor = [(mount, "MotorMount", "Motor mount"),
             mc(240, 246, 13.5, "Motor", "Motor base"),
             mc(223, 240, 14.0, "Motor", "Motor bell"),
             mc(231, 234.5, 14.25, "MotorMetal", "Motor bell ring"),
             mc(215, 223, 4.0, "MotorMetal", "Prop adapter"),
             mc(216.5, 222.5, 7.0, "Prop", "Prop hub")]
    try:
        cone = Rhino.Geometry.Cone(Plane(P(MX, 209, MZ), Vector3d(0, 1, 0)), 7.0, 4.5)
        motor.append((cone.ToBrep(True), "MotorMetal", "Prop nut"))
    except Exception as e: log.append("cone: %s" % e)
    # 7x4 prop: R = 88.9, pitch 101.6
    PR, PITCH, SP = 88.9, 101.6, 219.5
    hubc = P(MX, SP, MZ); fwd = Vector3d(0, -1, 0)
    def blade(alpha):
        er = Vector3d(math.cos(alpha), 0, math.sin(alpha)); et = Vector3d(-math.sin(alpha), 0, math.cos(alpha))
        def yt(u): return 0.6 * (0.2969 * math.sqrt(u) - 0.126 * u - 0.3516 * u**2 + 0.2843 * u**3 - 0.1036 * u**4)
        prof = [(u, 0.04 * math.sin(math.pi * u) + yt(u)) for u in [0.5 * (1 - math.cos(math.pi * i / 16)) for i in range(17)][::-1]]
        prof += [(u, 0.04 * math.sin(math.pi * u) - yt(u)) for u in [0.5 * (1 - math.cos(math.pi * i / 16)) for i in range(1, 17)]]
        prof[-1] = prof[0]
        cs = []
        for r, c in ((6.5, 9.0), (10, 12.5), (16, 15.5), (24, 17.0), (34, 17.0), (46, 15.8), (58, 14.0), (70, 11.8), (79, 9.2), (85, 6.2)):
            beta = math.atan(PITCH / (2 * math.pi * r))
            cd = et * math.cos(beta) + fwd * math.sin(beta)          # LE direction
            nv = fwd * math.cos(beta) - et * math.sin(beta)          # suction side (forward)
            ctr = hubc + er * r
            cs.append(cpcurve([ctr + cd * ((0.35 - u) * c) + nv * (v * c) for u, v in prof]))
        return loft(cs, end=hubc + er * PR)
    b1 = blade(math.radians(28)); b2 = blade(math.radians(208))
    motor += [(b1, "Prop", "Prop blade 1"), (b2, "Prop", "Prop blade 2")]
    for side, T in (("R", Transform.Identity), ("L", MIR)):
        for g, ly, nm in motor:
            if g: add(xform(g, T), ly, "%s %s" % (nm, side))
    log.append("motors %.1fs" % (time.time() - t0))

    # ================= TAIL BOOM, KNOB, POD =================
    BZ = -30.0
    add(cyl(P(0, 520, BZ), Vector3d(0, 1, 0), 8.0, 300.0), "Carbon", "Tail boom 16x430")
    add(cyl(P(0, 617, BZ), Vector3d(0, 1, 0), 13.6, 26.0), "Hardware", "Boom knob")
    for k in range(18):   # knurl ribs on the knob
        a = 2 * math.pi * k / 18
        rib = cyl(P(13.4 * math.cos(a), 619, BZ + 13.4 * math.sin(a)), Vector3d(0, 1, 0), 1.0, 22.0)
        add(rib, "Hardware", "Boom knob rib %d" % k)
    add(cyl(P(0, 750, BZ), Vector3d(0, 1, 0), 10.5, 12.0), "Hardware", "Boom tail insert")
    def esec(s, a, zt, zb, n=2.3, N=40):
        zc = 0.5 * (zt + zb); h = 0.5 * (zt - zb); pts = []
        for i in range(N + 1):
            ph = -math.pi / 2 + 2 * math.pi * i / N
            c, sn = math.cos(ph), math.sin(ph)
            pts.append(P(a * math.copysign(abs(c) ** (2 / n), c), s, zc + h * math.copysign(abs(sn) ** (2 / n), sn)))
        pts[-1] = pts[0]
        return cpcurve(pts)
    pod = loft([esec(*r) for r in ((760, 10.5, -19.5, -40.5), (770, 13.5, -17, -46), (786, 15, -16, -52), (820, 15.5, -16, -54),
                                   (900, 15.5, -16, -54), (940, 14, -18, -52), (965, 11, -23, -47), (980, 6, -29, -41))],
               end=P(0, 986, -35))
    add(pod, "Tail", "Tail pod")

    # ================= V-TAIL (35 deg, NACA0009) =================
    VD = math.radians(35.0); TR = (10.0, -18.0)
    def tLE(p): return 816.0 + 0.47 * (p - 15.0) + (18.0 * ((p - 200.0) / 26.0) ** 2 if p > 200 else 0.0)
    def tTE(p): return 956.0 + 0.157 * (p - 15.0) - (10.0 * ((p - 215.0) / 11.0) ** 2 if p > 215 else 0.0)
    def rr(p): return (p - TR[0]) / math.cos(VD)
    # build flat in local frame (span = +X from root, chord = +Y, thickness = +Z), then rotate/translate
    tsecs = []
    for p in (10, 30, 60, 100, 120, 140, 180, 200, 212, 220, 226):
        le = Point3d(rr(p), tLE(p) - 340.0, 0); tsecs.append(section(le, Vector3d(0, 1, 0), Vector3d(0, 0, 1), tTE(p) - tLE(p), TAILF))
    vt = loft(tsecs)
    def rhinge(p): return 920.0 + (p - 24.0) * 33.0 / 186.0
    def rv_poly(g):
        p0, p1 = 24.0 - g * math.cos(VD), 210.0 + g * math.cos(VD)
        return [(rr(p0), rhinge(p0) - g - 340), (rr(p1), rhinge(p1) - g - 340), (rr(p1), 1010 - 340), (rr(p0), 1010 - 340)]
    vt_main, rvator = vt, None
    try:
        o = prism(rv_poly(0.7), -20, 40); i_ = prism(rv_poly(-0.7), -20, 40)
        d = Brep.CreateBooleanDifference(vt, o, tol); it = Brep.CreateBooleanIntersection(vt, i_, tol)
        if d and it:
            vt_main = max(d, key=lambda b: b.GetBoundingBox(True).Diagonal.Length); rvator = it[0]
        else: log.append("ruddervator boolean failed")
    except Exception as e: log.append("ruddervator: %s" % e)
    vseam = section(Point3d(rr(120), tLE(120) - 340, 0), Vector3d(0, 1, 0), Vector3d(0, 0, 1), tTE(120) - tLE(120), TAILF)
    TV = Transform.Translation(Vector3d(TR[0], 0, TR[1])) * Transform.Rotation(-VD, Vector3d(0, 1, 0), Point3d.Origin)
    for side, T in (("R", TV), ("L", MIR * TV)):
        add(xform(vt_main, T), "Tail", "V-tail " + side)
        if rvator: add(xform(rvator, T), "ControlSurface", "Ruddervator " + side)
        pb = pipe(vseam, 0.3)
        if pb: add(xform(pb, T), "PanelLine", "V-tail seam " + side)
    # tail servos (black blocks at the pod sides, s 858-882)
    for side, sg in (("R", 1), ("L", -1)):
        add(boxb(Plane(P(sg * 20.0, 870, -22.0), Vector3d(1, 0, 0), Vector3d(0, 1, 0)), 16, 24, 12), "Camera", "Tail servo " + side)
        add(boxb(Plane(P(sg * 29.0, 872, -22.0), Vector3d(1, 0, 0), Vector3d(0, 1, 0)), 2, 16, 4), "Hardware", "Servo horn " + side)
    log.append("tail %.1fs" % (time.time() - t0))

    # ================= NOSE DETAILS =================
    ALL = BODY
    # vent grille: 9 vertical slots on the upper front of the nose cap
    for i, x in enumerate([-20 + 5 * k for k in range(9)]):
        h1 = hit([nose_b], P(x, -200, 3.0), Vector3d(0, 1, 0)); h2 = hit([nose_b], P(x, -200, 16.0), Vector3d(0, 1, 0))
        if h1 and h2:
            c = LineCurve(h1[0] + h1[1] * 0.2, h2[0] + h2[1] * 0.2)
            add(pipe(c, 1.15), "Grille", "Nose vent slot %d" % i)
    # chin camera window (squircle patch following the nose surface) + lens
    gi, gj = 14, 9; pts = []
    for i in range(gi):
        for j in range(gj):
            u = -1 + 2.0 * i / (gi - 1); v = -1 + 2.0 * j / (gj - 1)
            X = u * math.sqrt(1 - v * v / 2); Z = v * math.sqrt(1 - u * u / 2)
            h = hit([nose_b], P(33.0 * X, -200, -34.0 + 14.0 * Z), Vector3d(0, 1, 0))
            pts.append(h[0] + h[1] * 0.35 if h else P(33.0 * X, 10, -34.0 + 14.0 * Z))
    win = NurbsSurface.CreateFromPoints(plist(pts), gi, gj, 3, 3)
    if win: add(win.ToBrep(), "Camera", "Camera window")
    hc = hit([nose_b], P(0, -200, -34.0), Vector3d(0, 1, 0))
    if hc:
        pc, nc = hc
        add(cyl(pc - nc * 2.0, nc, 8.0, 6.0), "Camera", "FPV camera 19x19 lens barrel")
        add(cyl(pc + nc * 3.9, nc, 6.2, 0.6), "Lens", "FPV camera lens")
    # two nav-light posts on the nose top + whip antenna + hatch buttons
    for side, x in (("R", 11.0), ("L", -11.0)):
        h = hit(ALL, P(x, 70, 200), Vector3d(0, 0, -1))
        if h:
            base = h[0]; up = Vector3d(0, -0.17, 1); up.Unitize()
            add(cyl(base - up * 2, up, 1.6, 17), "Antenna", "Nav light stalk " + side)
            add(cyl(base + up * 14, up, 6.2, 11), "Antenna", "Nav light " + side)
    h = hit(ALL, P(0, 118, 200), Vector3d(0, 0, -1))
    if h:
        up = Vector3d(0, math.sin(math.radians(14)), math.cos(math.radians(14)))
        add(cyl(h[0] - up * 2, up, 2.3, 7), "Antenna", "Antenna base")
        add(cyl(h[0] + up * 4, up, 1.0, 52), "Antenna", "Whip antenna")
    for k, s in enumerate((300.0, 440.0)):
        h = hit(ALL, P(0, s, 200), Vector3d(0, 0, -1))
        if h: add(boxb(Plane(h[0] + h[1] * 2.0, Vector3d(1, 0, 0), Vector3d(0, 1, 0)), 8, 12, 8), "Hardware", "Hatch latch %d" % k)
    # hatch outlines projected on the top
    def hatch(s0, s1, w0, w1, nexp=3.0, N=72):
        c = 0.5 * (s0 + s1); L = 0.5 * (s1 - s0); pts = []
        for i in range(N + 1):
            a = 2 * math.pi * i / N; ca, sa = math.cos(a), math.sin(a)
            s = c + L * math.copysign(abs(sa) ** (2 / nexp), sa)
            w = w0 + (w1 - w0) * (s - s0) / (s1 - s0)
            pts.append(P(w * math.copysign(abs(ca) ** (2 / nexp), ca), s, 200))
        pts[-1] = pts[0]
        return Curve.CreateInterpolatedCurve(plist(pts), 3)
    for nm, (s0, s1, w0, w1) in (("Front hatch", (97, 275, 36, 46)), ("Rear hatch", (314, 477, 46, 32))):
        cr = hatch(s0, s1, w0, w1)
        for b in BODY:
            pr = Curve.ProjectToBrep(cr, b, Vector3d(0, 0, -1), tol)
            if pr:
                for c in pr:
                    if c.PointAtStart.Z > 0: add(pipe(c, 0.45), "PanelLine", nm + " outline")
    # wing locks (PETG) on top of the centre section, x 130..149
    for side, sg in (("R", 1), ("L", -1)):
        for k, s in enumerate((297.0, 433.0)):
            h = hit(ALL, P(sg * 140.0, s, 200), Vector3d(0, 0, -1))
            if h:
                n = h[1]; xa = Vector3d(1, 0, 0); ya = Vector3d.CrossProduct(n, xa); ya.Unitize(); xa = Vector3d.CrossProduct(ya, n)
                add(boxb(Plane(h[0], xa, ya), 19, 16, 2.4), "Hardware", "Wing lock %s %d" % (side, k))
    # servo covers + aileron horns under the wing
    for side, sg in (("R", 1), ("L", -1)):
        W2 = [WINGS[0]] if sg > 0 else [WINGS[1]]
        h = hit(W2, P(sg * 420.0, 392, -200), Vector3d(0, 0, 1))
        if h:
            n = h[1]; xa = Vector3d(1, 0, 0); ya = Vector3d.CrossProduct(n, xa); ya.Unitize(); xa = Vector3d.CrossProduct(ya, n)
            add(boxb(Plane(h[0], xa, ya), 26, 36, 1.4), "Hardware", "Aileron servo cover " + side)
        ha = hit([aileron if sg > 0 else xform(aileron, MIR)] if aileron else W2, P(sg * 330.0, 445, -200), Vector3d(0, 0, 1))
        if ha: add(boxb(Plane(ha[0] - Vector3d(0, 0, 3.5), Vector3d(1, 0, 0), Vector3d(0, 1, 0)), 2, 13, 9), "Hardware", "Aileron horn " + side)
    log.append("details %.1fs" % (time.time() - t0))

    # ================= "STALLION by FLIGHTORY" decals =================
    def glyphs(text, height):
        ds = doc.DimStyles.Current
        te = TextEntity.Create(text, Plane.WorldXY, ds, False, 0, 0)
        try: te.Font = Rhino.DocObjects.Font.FromQuartetProperties("Arial", True, False)
        except Exception: pass
        te.TextHeight = height
        bs = list(te.CreateSurfaces(ds, 1.0, 0.0) or [])
        if not bs: return []
        bb = BoundingBox.Empty
        for b in bs: bb.Union(b.GetBoundingBox(True))
        sc = height / max(bb.Max.Y - bb.Min.Y, 1e-6)
        T = Transform.Scale(Point3d(bb.Min.X, bb.Min.Y, 0), sc)
        out = []
        for b in bs:
            b.Transform(T); out.append(b)
        return out
    try:
        TXT = []
        for text, h, s0, z0 in (("STALLION", 11.0, 98.0, -21.0), ("FLIGHTORY", 3.4, 176.0, -21.0)):
            gs = glyphs(text, h)
            gbb = BoundingBox.Empty
            for g in gs: gbb.Union(g.GetBoundingBox(True))
            TXT.append((text, h, s0, z0, gs, gbb.Max.X))
        B0 = TXT[0][2]; B1 = max(t[2] + t[5] for t in TXT)     # text block s-range; left side reads the other way
        for text, h, s0, z0, gs, tl in TXT:
            for side, sg in (("R", 1), ("L", -1)):
                for k, g in enumerate(gs):
                    gb = g.GetBoundingBox(True); u = 0.5 * (gb.Min.X + gb.Max.X)
                    s = s0 + u if sg > 0 else B0 + B1 - (s0 + u); hh = hit(ALL, P(sg * 200, s, z0 + h * 0.5), Vector3d(-sg, 0, 0))
                    if not hh: continue
                    n = hh[1]; ref = Vector3d(0, sg, 0)
                    xa = ref - n * (n * ref); xa.Unitize(); ya = Vector3d.CrossProduct(n, xa); ya.Unitize()
                    org = hh[0] + n * 0.3 - ya * (h * 0.5)
                    T = Transform.PlaneToPlane(Plane(Point3d(u, 0, 0), Vector3d(1, 0, 0), Vector3d(0, 1, 0)), Plane(org, xa, ya))
                    add(xform(g, T), "Decal", "Decal %s %s %d" % (text, side, k))
    except Exception as e:
        log.append("decal: %s" % e)

    # ================= v002: FC bay, hatch lid, spar/boom/wire holes, split into Prusa MK3 parts =================
    # Prusa MK3/MK3S build volume 250 x 210 x 210 mm. Printable parts get user text "print" = part name.
    BED = (250.0, 210.0, 210.0)
    def dims(b):
        bb = b.GetBoundingBox(True)
        return sorted([bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y, bb.Max.Z - bb.Min.Z], reverse=True)
    def fits(b):
        d = dims(b); return all(d[i] <= BED[i] for i in range(3))
    PRINT = []
    def addp(geo, ly, name):
        if geo is None: log.append("missing " + name); return None
        a = Rhino.DocObjects.ObjectAttributes(); a.LayerIndex = LY[ly]; a.Name = name
        a.SetUserString("print", name)
        count[0] += 1
        PRINT.append((name, geo))
        return doc.Objects.AddBrep(geo, a)
    def kill(names):
        for o in list(doc.Objects):
            nm = o.Attributes.Name or ""
            if any(nm == n or (n.endswith("*") and nm.startswith(n[:-1])) for n in names):
                doc.Objects.Delete(o, True); count[0] -= 1
    def BL(bs):
        L = List[Brep]()
        for b in bs: L.Add(b)
        return L
    def solid(b):
        if b is None: return None
        if not b.IsSolid:
            c = b.CapPlanarHoles(tol)
            if c: b = c
        if b.IsSolid and b.SolidOrientation == Rhino.Geometry.BrepSolidOrientation.Inward: b.Flip()
        return b
    def big(rs):
        return max(rs, key=lambda b: b.GetBoundingBox(True).Diagonal.Length) if rs else None
    def bdiff(a, cutters, nm):
        cur = a
        for k, c in enumerate(cutters):
            if c is None: continue
            try:
                r = Brep.CreateBooleanDifference(cur, c, tol)
                if r: cur = big(list(r))
                else: log.append("diff failed %s #%d" % (nm, k))
            except Exception as e: log.append("diff %s #%d: %s" % (nm, k, e))
        return cur
    def bunion(a, adds, nm):
        try:
            r = Brep.CreateBooleanUnion(BL([a] + [b for b in adds if b]), tol)
            if r: return big(list(r))
        except Exception as e: log.append("union %s: %s" % (nm, e))
        log.append("union failed " + nm); return a
    def bint(a, c):
        try:
            r = Brep.CreateBooleanIntersection(a, c, tol)
            return [b for b in r] if r else []
        except Exception as e:
            log.append("int: %s" % e); return []
    def bbox(x0, x1, y0, y1, z0, z1):
        return Box(BoundingBox(Point3d(x0, y0, z0), Point3d(x1, y1, z1))).ToBrep()
    def seg(p0, p1, r):
        v = p1 - p0; return cyl(p0, v, r, v.Length)

    nose_p = solid(nose_b.DuplicateBrep()) if nose_b else None
    body_p = solid(body_b.DuplicateBrep())
    log.append("body solid=%s nose solid=%s" % (body_p.IsSolid, nose_p.IsSolid if nose_p else None))

    # ---- FC bay under the front hatch (s 97..275) ----
    ZC = 25.0                        # hatch lid cut plane
    BAY = (-32.0, 32.0, 112.0, 262.0, -58.0)   # x0, x1, s0, s1, floor z
    FC_S = 190.0                     # FC mounting pattern centre (s)
    bay = bbox(BAY[0], BAY[1], BAY[2] - 340, BAY[3] - 340, BAY[4], ZC + 1.0)
    def hatch_c(s0, s1, w0, w1, z, g=0.0, nexp=3.0, N=96):
        c = 0.5 * (s0 + s1); L = 0.5 * (s1 - s0) - g; pts = []
        for i in range(N + 1):
            a = 2 * math.pi * i / N; ca, sa = math.cos(a), math.sin(a)
            s = c + L * math.copysign(abs(sa) ** (2 / nexp), sa)
            w = w0 + (w1 - w0) * (s - s0) / (s1 - s0) - g
            pts.append(P(w * math.copysign(abs(ca) ** (2 / nexp), ca), s, z))
        pts[-1] = pts[0]
        return Curve.CreateInterpolatedCurve(plist(pts), 3)
    def cprism(curve, h):
        b = Surface.CreateExtrusion(curve, Vector3d(0, 0, h)).ToBrep()
        return solid(b)
    FH = (97.0, 275.0, 36.0, 46.0)
    hole_pr = cprism(hatch_c(*FH, z=ZC), 100.0)
    lid_pr = cprism(hatch_c(*FH, z=ZC, g=0.3), 100.0)            # 0.3 mm gap all round
    plug = bint(cprism(hatch_c(*FH, z=ZC - 5.0, g=0.3), 6.0),
                bbox(BAY[0] + 0.3, BAY[1] - 0.3, BAY[2] - 340 + 0.3, BAY[3] - 340 - 0.3, ZC - 5.0, ZC + 1.0))
    lid = big(bint(body_p, lid_pr))
    if lid and plug: lid = bunion(lid, plug, "lid plug")

    # ---- spar tubes (carbon 10x800 main, 8x600 rear), servo/ESC wire channel, tunnel from the bay ----
    def camz(x, s):
        xx = max(x, 150.0); c = sTE(xx) - sLE(xx); t = (s - sLE(xx)) / c
        return zstr(xx) + c * 0.5 * (fu(t) + fl(t))
    HOLES = []   # (s, half length, radius)
    for s, L, r in ((330.0, 400.0, 5.2), (405.0, 300.0, 4.2), (368.0, 300.0, 3.5)):
        for sg in (1, -1):
            HOLES.append(seg(P(0, s, camz(0, s)), P(sg * L, s, camz(L, s)), r))
    tunnel = seg(P(0, BAY[3] - 8, camz(0, 368)), P(0, 373, camz(0, 368)), 5.0)
    boom_h = seg(P(0, 515, BZ), P(0, 830, BZ), 8.15)                  # 16 mm tube + 0.3 clearance

    # FC standoffs: 30.5x30.5 (M3) and 20x20 (M2) patterns
    FZ = BAY[4]
    stand, sholes = [], []
    for half, od, hd in ((15.25, 6.5, 2.6), (10.0, 5.0, 1.7)):
        for sx in (1, -1):
            for sy in (1, -1):
                c0 = P(sx * half, FC_S + sy * half, FZ - 1.5)
                stand.append(cyl(c0, Vector3d(0, 0, 1), od / 2, 7.5))         # 6 mm above the floor
                sholes.append(cyl(P(sx * half, FC_S + sy * half, FZ - 8), Vector3d(0, 0, 1), hd / 2, 15.0))

    body_p = bdiff(body_p, [hole_pr, bay, tunnel, boom_h] + HOLES, "fuselage")  # hatch first: fully enclosed cutters fail
    body_p = bunion(body_p, stand, "standoffs")
    body_p = bdiff(body_p, sholes, "standoff holes")
    log.append("cuts %.1fs" % (time.time() - t0))

    # FC board placeholder (not printed)
    LY["Electronics"] = layer("Electronics", Color.FromArgb(30, 110, 60), 0.3)
    add(boxb(Plane(P(0, FC_S, FZ + 6.0 + 0.8), Vector3d(1, 0, 0), Vector3d(0, 1, 0)), 36, 36, 1.6), "Electronics", "FC board 36x36 (30.5 mount)")
    LY["Hatch"] = layer("Hatch", Color.FromArgb(205, 209, 214), 0.25)

    # ---- outer wing panel: spar/wire holes, motor mount pocket ----
    wing_p = bdiff(wing_main, [h for h in HOLES[0::2]] + [mount], "wing")
    ail_p = aileron
    # ---- tail pod, knob, insert: boom holes ----
    pod_p = bdiff(solid(pod), [boom_h], "pod")
    knob = bunion(cyl(P(0, 617, BZ), Vector3d(0, 1, 0), 13.6, 26.0),
                  [cyl(P(13.4 * math.cos(2 * math.pi * k / 18), 619, BZ + 13.4 * math.sin(2 * math.pi * k / 18)), Vector3d(0, 1, 0), 1.0, 22.0) for k in range(18)], "knob")
    knob = bdiff(knob, [boom_h], "knob")
    insert = bdiff(cyl(P(0, 750, BZ), Vector3d(0, 1, 0), 10.5, 12.0), [boom_h], "insert")

    # ---- remove the v001 display solids that are replaced by printable pieces ----
    kill(["Fuselage + centre wing", "Nose cap", "Wing panel R", "Wing panel L", "Aileron R", "Aileron L",
          "V-tail R", "V-tail L", "Ruddervator R", "Ruddervator L", "Tail pod", "Boom knob", "Boom knob rib*", "Boom tail insert"])

    # ---- split into cells ----
    BIG = 2000.0
    def split(b, xcuts=None, ycuts=None):
        xs = [-BIG] + (xcuts or []) + [BIG]; ys = [-BIG] + (ycuts or []) + [BIG]
        out = []
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                for pc in bint(b, bbox(xs[i], xs[i + 1], ys[j], ys[j + 1], -BIG, BIG)):
                    if pc.GetVolume() > 50.0: out.append(((i, j), pc))
        return out
    # fuselage: x +-104 (centre body keeps the FC bay whole), s 290 / 490 (between the hatches, behind the rear hatch)
    FX = [-104.0, 104.0]; FS = [290.0 - 340, 490.0 - 340]
    sname = {0: "front", 1: "mid", 2: "rear"}
    for (i, j), pc in split(body_p, FX, FS):
        if i == 1: addp(pc, "Fuselage", "F%dC fuselage %s centre" % (j + 1, sname[j]))
    # wing-root fillets (|x| > 104) are cut once at s 380 so no small slivers are left
    for xi, side in ((0, "L"), (2, "R")):
        root = bint(body_p, bbox(-BIG if xi == 0 else FX[1], FX[0] if xi == 0 else BIG, -BIG, BIG, -BIG, BIG))
        for rb in root:
            for (i, j), pc in split(rb, None, [380.0 - 340]):
                addp(pc, "Fuselage", "R%d%s wing root %s %s" % (j + 1, side, side, ("front", "rear")[j]))
    if nose_p: addp(nose_p, "NoseCap", "F0 nose cap")
    if lid: addp(lid, "Hatch", "F1H front hatch lid")
    # outer wing: seams at x 308 / 444 / 580
    WX = [308.0, 444.0, 580.0]
    for (i, j), pc in split(wing_p, WX):
        for side, T in (("R", Transform.Identity), ("L", MIR)):
            addp(xform(pc, T), "Wing", "W%d%s wing panel %s" % (i + 1, side, side))
    if ail_p:
        for (i, j), pc in split(ail_p, [444.0]):
            for side, T in (("R", Transform.Identity), ("L", MIR)):
                addp(xform(pc, T), "ControlSurface", "A%d%s aileron %s" % (i + 1, side, side))
    # V-tail: split in the flat local frame at the seam (p = 120), then place
    for (i, j), pc in split(vt_main, [rr(120)]):
        for side, T in (("R", TV), ("L", MIR * TV)):
            addp(xform(pc, T), "Tail", "V%d%s V-tail %s" % (i + 1, side, side))
    if rvator:
        for side, T in (("R", TV), ("L", MIR * TV)):
            addp(xform(rvator, T), "ControlSurface", "RV%s ruddervator %s" % (side, side))
    if pod_p: addp(pod_p, "Tail", "T1 tail pod")
    addp(knob, "Hardware", "H1 boom knob")
    addp(insert, "Hardware", "H2 boom tail insert")
    # small parts already in the document: tag them printable
    for o in list(doc.Objects):
        nm = o.Attributes.Name or ""
        if nm.startswith(("Motor mount", "Wing lock", "Hatch latch", "Aileron servo cover", "Aileron horn")):
            a = o.Attributes.Duplicate(); a.SetUserString("print", nm); doc.Objects.ModifyAttributes(o, a, True)
            PRINT.append((nm, o.Geometry))
    bad = []
    for nm, g in PRINT:
        if not fits(g): bad.append("%s %s" % (nm, ["%.0f" % d for d in dims(g)]))
        if isinstance(g, Brep) and not g.IsSolid: bad.append("%s not solid" % nm)
    log.append("print parts %d, problems: %s" % (len(PRINT), "; ".join(bad) if bad else "none"))
    log.append("split %.1fs" % (time.time() - t0))

    # ---------- report ----------
    bb = BoundingBox.Empty
    for o in doc.Objects: bb.Union(o.Geometry.GetBoundingBox(True))
    log.append("objects %d, bbox X %.0f..%.0f  Y %.0f..%.0f  Z %.0f..%.0f" % (count[0], bb.Min.X, bb.Max.X, bb.Min.Y, bb.Max.Y, bb.Min.Z, bb.Max.Z))
    log.append("span %.0f  length %.0f  time %.1fs" % (bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y, time.time() - t0))
    doc.Views.Redraw()
    print("\n".join(log))
main()

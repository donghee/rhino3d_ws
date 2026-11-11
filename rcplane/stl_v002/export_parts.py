def main():
    import os, re, struct
    import Rhino
    from Rhino.Geometry import Mesh, MeshingParameters, Vector3d
    doc = __rhino_doc__
    out_dir = "D:/rhino3d_ws/rcplane/stl_v002"
    if not os.path.isdir(out_dir): os.makedirs(out_dir)
    mp = MeshingParameters.QualityRenderMesh
    mp.Tolerance = 0.05; mp.MinimumEdgeLength = 0.0001; mp.JaggedSeams = False; mp.ClosedObjectPostProcess = True
    rows = []
    for o in doc.Objects:
        nm = o.Attributes.GetUserString("print")
        if not nm or o.IsDeleted: continue
        m = Mesh()
        for part in Mesh.CreateFromBrep(o.Geometry, mp) or []: m.Append(part)
        m.Weld(3.14159); m.Faces.ConvertQuadsToTriangles(); m.Compact()
        fn = re.sub(r"[^A-Za-z0-9]+", "_", nm).strip("_") + ".stl"
        V = m.Vertices; F = m.Faces
        with open(out_dir + "/" + fn, "wb") as f:
            f.write(("rcplane_v002 " + nm).encode()[:80].ljust(80, b" ")); f.write(struct.pack("<I", F.Count))
            for i in range(F.Count):
                fc = F[i]; a, b, c = V[fc.A], V[fc.B], V[fc.C]
                n = Vector3d.CrossProduct(Vector3d(b.X-a.X, b.Y-a.Y, b.Z-a.Z), Vector3d(c.X-a.X, c.Y-a.Y, c.Z-a.Z)); n.Unitize()
                f.write(struct.pack("<12fH", n.X, n.Y, n.Z, a.X, a.Y, a.Z, b.X, b.Y, b.Z, c.X, c.Y, c.Z, 0))
        rows.append("%s\t%d\t%s" % (fn, F.Count, m.IsClosed))
    print("\n".join(sorted(rows)))
main()

import Rhino, System, math
def main():
    from Rhino.Geometry import Point3d,Vector3d,Sphere,Transform,Plane,Brep,Curve,PipeCapMode,Cone
    from System.Drawing import Color
    import math
    doc=__rhino_doc__
    # --- start from an empty document ---
    for o in list(doc.Objects): doc.Objects.Purge(o)
    di=doc.Layers.FindByFullPath("Default",-1)
    if di<0:
        L=Rhino.DocObjects.Layer(); L.Name="Default"; di=doc.Layers.Add(L)
    doc.Layers.SetCurrentLayerIndex(di,True)
    for _ in range(4):
        for L in list(doc.Layers):
            if L.Index!=di and not L.IsDeleted: doc.Layers.Purge(L.Index,True)
    def layer(name,c,shine=0.0):
        p=doc.Layers.FindByFullPath("Cat",-1)
        if p<0:
            L=Rhino.DocObjects.Layer(); L.Name="Cat"; p=doc.Layers.Add(L)
        L=Rhino.DocObjects.Layer(); L.Name=name; L.Color=c; L.ParentLayerId=doc.Layers[p].Id
        i=doc.Layers.Add(L)
        m=Rhino.DocObjects.Material(); m.DiffuseColor=c; m.Name="Cat_"+name
        m.Shine=shine*Rhino.DocObjects.Material.MaxShine
        mi=doc.Materials.Add(m); L=doc.Layers[i]; L.RenderMaterialIndex=mi; doc.Layers.Modify(L,i,True)
        return i
    LY={"Fur":layer("Fur",Color.FromArgb(158,168,184)),
        "Eye":layer("Eye",Color.FromArgb(238,152,38),0.9),
        "Pupil":layer("Pupil",Color.FromArgb(15,15,18),0.9),
        "Highlight":layer("Highlight",Color.White,0.9),
        "Nose":layer("Nose",Color.FromArgb(84,88,102),0.4),
        "EarInner":layer("EarInner",Color.FromArgb(222,178,182)),
        "Mouth":layer("Mouth",Color.FromArgb(60,60,70)),
        "Whisker":layer("Whisker",Color.FromArgb(245,245,245))}
    def add(geo,ly,name):
        a=Rhino.DocObjects.ObjectAttributes(); a.LayerIndex=LY[ly]; a.Name=name
        return doc.Objects.AddBrep(geo,a) if isinstance(geo,Brep) else doc.Objects.Add(geo,a)
    def ell(c,rx,ry,rz,rot=None):
        s=Sphere(Point3d.Origin,1).ToNurbsSurface()
        s.Transform(Transform.Scale(Plane.WorldXY,rx,ry,rz))
        if rot:
            for ang,axis in rot: s.Transform(Transform.Rotation(ang,axis,Point3d.Origin))
        s.Transform(Transform.Translation(Vector3d(c[0],c[1],c[2])))
        return s.ToBrep()
    def pipe(pts,r,rend=None,cap=True):
        crv=Curve.CreateInterpolatedCurve([Point3d(*p) for p in pts],3)
        t0,t1=crv.Domain.T0,crv.Domain.T1
        cm=PipeCapMode.Round if cap else PipeCapMode.Flat
        b=Brep.CreatePipe(crv,[t0,t1],[r,rend or r],True,cm,True,0.01,0.01)
        if not b: b=Brep.CreatePipe(crv,r,False,cm,True,0.01,0.01)
        if not b: b=Brep.CreatePipe(crv,r,False,PipeCapMode.Flat,True,0.01,0.01)
        return b[0]
    def ear(base,r,h,flat,tilt_y,tilt_x):
        # revolved ear with a rounded tip, pointing +Z; flattened in Y, tilted outward
        from Rhino.Geometry import RevSurface,Line
        prof=Curve.CreateInterpolatedCurve([Point3d(r,0,0),Point3d(r*0.78,0,h*0.45),Point3d(r*0.38,0,h*0.85),Point3d(0,0,h)],3)
        b=RevSurface.Create(prof,Line(Point3d(0,0,0),Point3d(0,0,h))).ToNurbsSurface().ToBrep()
        b.Transform(Transform.Scale(Plane.WorldXY,1,flat,1))
        b.Transform(Transform.Rotation(tilt_x,Vector3d.XAxis,Point3d.Origin))
        b.Transform(Transform.Rotation(tilt_y,Vector3d.YAxis,Point3d.Origin))
        b.Transform(Transform.Translation(Vector3d(*base)))
        return b
    d=math.radians
    # ---- sitting British Shorthair, face toward -Y, ~45 mm tall ----
    # body: haunches + chest + neck
    add(ell((0,3,10.5),10.5,11,10.5),"Fur","Haunch")
    add(ell((0,-4.0,18.5),8.9,7.6,11.5,[(d(-12),Vector3d.XAxis)]),"Fur","Chest")
    add(ell((0,-6.2,26.5),8.4,6.8,5.2),"Fur","Ruff")
    for sx in(-1,1):
        add(ell((sx*7.8,4,8),4.2,8.5,7.2),"Fur","Thigh")
        add(ell((sx*6.6,-5.2,1.6),2.7,4.6,1.7),"Fur","HindFoot")
        add(pipe([(sx*4.0,-9.0,18),(sx*4.3,-10.8,10),(sx*4.3,-11.4,3)],2.5,2.3),"Fur","FrontLeg")
        add(ell((sx*4.3,-12.6,1.6),2.8,3.4,1.7),"Fur","FrontPaw")
    # head: wide, round, chubby cheeks
    H=(0,-6,33)
    add(ell(H,9.6,8.4,8.4),"Fur","Head")
    for sx in(-1,1):
        add(ell((sx*4.8,-10.6,30.2),5.0,4.2,4.0),"Fur","Cheek")
        add(ell((sx*1.7,-14.0,29.8),2.1,1.6,1.6),"Fur","WhiskerPad")
    add(ell((0,-12.8,27.9),2.3,2.0,1.5),"Fur","Chin")
    add(ell((0,-13.6,32.4),1.8,1.6,1.6),"Fur","NoseBridge")
    # nose + mouth
    add(ell((0,-15.15,31.5),1.05,0.55,0.7),"Nose","Nose")
    add(pipe([(0,-15.45,31.0),(0,-15.55,30.0)],0.12),"Mouth","Philtrum")
    for sx in(-1,1):
        add(pipe([(0,-15.55,30.0),(sx*0.8,-15.5,29.6),(sx*1.7,-15.15,29.9)],0.12),"Mouth","Mouth")
    # eyes: big, round, copper
    for sx in(-1,1):
        ex=sx*3.7
        add(ell((ex,-12.7,34.6),2.35,1.35,2.35),"Eye","Eye")
        add(ell((sx*3.75,-13.85,34.6),0.75,0.4,1.75),"Pupil","Pupil")
        add(ell((sx*3.25,-14.25,35.4),0.35,0.15,0.35),"Highlight","Highlight")
    # ears: small, rounded, set wide
    for sx in(-1,1):
        add(ear((sx*5.8,-4.6,38.6),3.6,5.2,0.5,sx*d(32),d(-8)),"Fur","Ear")
        add(ear((sx*5.75,-5.45,39.0),2.4,4.0,0.3,sx*d(32),d(-8)),"EarInner","EarInner")
    # whiskers
    for sx in(-1,1):
        for k,(dz,dy) in enumerate(((0.9,0.0),(0.0,0.3),(-0.9,0.6))):
            p0=(sx*2.4,-15.0,29.9+dz*0.5)
            pts=[p0,(sx*6.5,-14.6+dy,30.0+dz*1.4),(sx*11.5,-13.0+dy*2,30.2+dz*2.6)]
            add(pipe(pts,0.09,0.05),"Whisker","Whisker")
    # tail: thick, wrapped around the right side toward the front paws
    add(pipe([(0,13.5,3.5),(6,13,2.3),(11,7,2.0),(11.8,-1,2.0),(10.5,-7.5,2.0),(8.5,-12,2.2)],2.6,2.1),"Fur","Tail")
    doc.Views.Redraw()
    print("objects:",len(list(doc.Objects)))
main()

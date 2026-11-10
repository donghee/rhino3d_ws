import Rhino, System, math
def main():
    from Rhino.Geometry import Point3d,Vector3d,Sphere,Transform,Plane,Brep,Curve,PipeCapMode
    from System.Drawing import Color
    import math
    doc=__rhino_doc__
    def layer(name,c):
        i=doc.Layers.FindByFullPath("Monkey::"+name,-1)
        if i>=0: return i
        p=doc.Layers.FindByFullPath("Monkey",-1)
        if p<0:
            L=Rhino.DocObjects.Layer(); L.Name="Monkey"; p=doc.Layers.Add(L)
        L=Rhino.DocObjects.Layer(); L.Name=name; L.Color=c; L.ParentLayerId=doc.Layers[p].Id
        i=doc.Layers.Add(L)
        m=Rhino.DocObjects.Material(); m.DiffuseColor=c; m.Name="Monkey_"+name
        if name in("Eye","Pupil"): m.Shine=0.8*Rhino.DocObjects.Material.MaxShine
        mi=doc.Materials.Add(m); L=doc.Layers[i]; L.RenderMaterialIndex=mi; doc.Layers.Modify(L,i,True)
        return i
    LY={"Fur":layer("Fur",Color.FromArgb(120,72,40)),"Skin":layer("Skin",Color.FromArgb(235,190,150)),
        "Eye":layer("Eye",Color.White),"Pupil":layer("Pupil",Color.FromArgb(20,20,20)),"Mouth":layer("Mouth",Color.FromArgb(150,40,40))}
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
        print("pipe",len(b) if b else 0)
        return b[0]
    d=math.radians
    # head (face points -Y)
    H=(0,0,34)
    add(ell(H,10,9.5,9.5),"Fur","Head")
    # face: two eye patches + muzzle
    for sx in(-1,1):
        add(ell((sx*3.6,-6.2,36.2),4.0,3.2,4.2),"Skin","EyePatch")
    add(ell((0,-6.8,30.2),6.6,4.2,4.4),"Skin","Muzzle")
    # eyes
    for sx in(-1,1):
        add(ell((sx*3.5,-9.0,36.8),1.9,1.0,2.2),"Eye","Eye")
        add(ell((sx*3.3,-9.95,36.6),0.9,0.4,1.1),"Pupil","Pupil")
        add(ell((sx*3.0,-10.25,37.2),0.25,0.1,0.25),"Eye","Highlight")
    # nostrils
    for sx in(-1,1): add(ell((sx*1.0,-10.8,31.8),0.45,0.3,0.3),"Pupil","Nostril")
    # smile
    add(pipe([(-3.4,-10.0,29.8),(-1.8,-10.9,28.6),(0,-11.1,28.2),(1.8,-10.9,28.6),(3.4,-10.0,29.8)],0.35),"Mouth","Smile")
    # brow
    add(ell((0,-7.6,40.0),6.0,2.0,1.4),"Fur","Brow")
    # ears
    for sx in(-1,1):
        add(ell((sx*10.8,-0.5,35),2.0,4.2,4.6),"Fur","Ear")
        add(ell((sx*11.3,-1.6,35),1.2,3.0,3.4),"Skin","EarInner")
    # body
    add(ell((0,0.8,15.5),8.2,7.2,10.5),"Fur","Body")
    add(ell((0,-4.4,15.0),5.6,3.2,7.6),"Skin","Belly")
    # arms
    for sx in(-1,1):
        add(pipe([(sx*6.5,0,21),(sx*11,-1.5,17),(sx*13.5,-3,10),(sx*12.5,-5,4.5)],1.9,1.6),"Fur","Arm")
        add(ell((sx*12.3,-5.4,3.4),2.2,2.0,2.4),"Skin","Hand")
    # legs
    for sx in(-1,1):
        add(pipe([(sx*4.5,0,8),(sx*6.5,-2.5,4),(sx*6.5,-3.5,1.5)],2.3,2.1),"Fur","Leg")
        add(ell((sx*6.8,-6.0,1.3),2.6,4.0,1.3),"Skin","Foot")
    # tail (curly, behind)
    pts=[]
    for i in range(26):
        t=i/25.0
        if t<0.55:
            u=t/0.55; pts.append((0, 7.5+u*6, 10-u*6+ (u*u)*14))
        else:
            u=(t-0.55)/0.45; a=u*1.6*math.pi; r=4*(1-0.55*u)
            pts.append((0, 13.5+r*math.sin(a) , 18+ r*(1-math.cos(a))*0.0 + r*math.cos(a)-4+4))
    add(pipe(pts,1.1,0.6),"Fur","Tail")
    doc.Views.Redraw()
    print("objects:",doc.Objects.Count)
main()
import Rhino, System, math
def main():
    from Rhino.Geometry import Point3d,Vector3d,Sphere,Transform,Plane,Brep,Curve,PipeCapMode
    from System.Drawing import Color
    import math
    doc=__rhino_doc__
    def layer(name,c,parent="Monkey"):
        i=doc.Layers.FindByFullPath(parent+"::"+name,-1)
        if i>=0: return i
        p=doc.Layers.FindByFullPath(parent,-1)
        if p<0:
            L=Rhino.DocObjects.Layer(); L.Name=parent; p=doc.Layers.Add(L)
        L=Rhino.DocObjects.Layer(); L.Name=name; L.Color=c; L.ParentLayerId=doc.Layers[p].Id
        i=doc.Layers.Add(L)
        m=Rhino.DocObjects.Material(); m.DiffuseColor=c; m.Name=parent+"_"+name
        if name in("Eye","Pupil"): m.Shine=0.8*Rhino.DocObjects.Material.MaxShine
        mi=doc.Materials.Add(m); L=doc.Layers[i]; L.RenderMaterialIndex=mi; doc.Layers.Modify(L,i,True)
        return i
    LY={"Fur":layer("Fur",Color.FromArgb(120,72,40)),"Skin":layer("Skin",Color.FromArgb(235,190,150)),
        "Eye":layer("Eye",Color.White),"Pupil":layer("Pupil",Color.FromArgb(20,20,20)),"Mouth":layer("Mouth",Color.FromArgb(150,40,40)),
        "Bark":layer("Bark",Color.FromArgb(95,65,40),"Tree"),"Leaves":layer("Leaves",Color.FromArgb(70,140,60),"Tree")}
    built=[]
    def add(geo,ly,name):
        a=Rhino.DocObjects.ObjectAttributes(); a.LayerIndex=LY[ly]; a.Name=name
        oid=doc.Objects.AddBrep(geo,a) if isinstance(geo,Brep) else doc.Objects.Add(geo,a)
        built.append(oid)
        return oid
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
    # brows (v002): two thin arches raised above the eyes, sitting on the head surface
    def on_head(x,z,off):
        # y on the front of the head ellipsoid (center 0,0,34; radii 10, 9.5, 9.5), pushed out by off
        k=1-(x/10.0)**2-((z-34)/9.5)**2
        return -9.5*math.sqrt(max(k,0.0))-off
    for sx in(-1,1):
        pts=[]
        for x,z in((1.6,41.3),(2.6,41.9),(3.7,42.1),(4.8,41.8),(5.7,41.1)):
            pts.append((sx*x,on_head(x,z,0.15),z))
        add(pipe(pts,0.42,0.3),"Fur","Brow")
    # ears
    for sx in(-1,1):
        add(ell((sx*10.8,-0.5,35),2.0,4.2,4.6),"Fur","Ear")
        add(ell((sx*11.3,-1.6,35),1.2,3.0,3.4),"Skin","EarInner")
    # body
    add(ell((0,0.8,15.5),8.2,7.2,10.5),"Fur","Body")
    add(ell((0,-4.4,15.0),5.6,3.2,7.6),"Skin","Belly")
    # legs
    for sx in(-1,1):
        add(pipe([(sx*4.5,0,8),(sx*6.5,-2.5,4),(sx*6.5,-3.5,1.5)],2.3,2.1),"Fur","Leg")
        add(ell((sx*6.8,-6.0,1.3),2.6,4.0,1.3),"Skin","Foot")
    # v003: hang upside down. Flip the standing body 180 degrees about the Y axis through z=25
    # (x -> -x, z -> 50 - z; the face still looks toward -Y, the head is now at the bottom).
    flip=Transform.Rotation(math.pi,Vector3d(0,1,0),Point3d(0,0,25))
    for oid in built: doc.Objects.Transform(oid,flip,True)
    del built[:]
    # arms dangle down past the head (final coordinates)
    for sx in(-1,1):
        add(pipe([(sx*6.5,0,29),(sx*11,-1,25.5),(sx*14.2,-2,19.5),(sx*15.2,-3,12.5)],1.9,1.6),"Fur","Arm")
        add(ell((sx*15.3,-3.4,10.6),2.2,2.0,2.4),"Skin","Hand")
    # tree: trunk on the left, a branch over the monkey, leaves
    BY,BZ,BR=8.0,60.0,2.5   # branch axis (y, z) and radius at the monkey
    add(pipe([(-26,BY,0),(-26.5,BY,25),(-25.5,BY,50),(-26,BY,78)],3.6,2.6),"Bark","Trunk")
    add(pipe([(-26,BY,BZ-3),(-13,BY,BZ-0.3),(0,BY,BZ),(12,BY,BZ+0.4),(26,BY,BZ+2.5)],BR+0.4,BR-1.0),"Bark","Branch")
    for c,r in(((-26,BY,82),(9,8,7)),((-18,BY+3,78),(6,5,5)),((-33,BY-2,77),(6,5,5)),
               ((28,BY,65),(7,6,5.5)),((22,BY-3,68),(5,4,4)),((33,BY+2,63),(5,4.5,4))):
        add(ell(c,*r),"Leaves","Leaves")
    # tail: up from the back, then wrapped one and a half turns around the branch
    R=BR+1.3
    pts=[(0,7.5,40),(0,9.8,44.5),(0,11.6,50),(0,11.4,54.5)]
    n=16
    for i in range(n+1):
        t=i/float(n)
        a=math.radians(-55+t*470)          # from behind-below, over the top, around
        pts.append((t*3.2, BY+R*math.cos(a), BZ+R*math.sin(a)))
    add(pipe(pts,1.1,0.7),"Fur","Tail")
    doc.Views.Redraw()
    print("objects:",doc.Objects.Count)
main()
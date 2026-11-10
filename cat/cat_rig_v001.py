# Builds cat_rig_v001.gh: sliders/toggles -> Python 3 rig component -> Custom Preview.
def main():
    import System, Grasshopper
    from System.Drawing import PointF
    from Grasshopper.Kernel.Special import GH_NumberSlider, GH_BooleanToggle, GH_Panel
    from Grasshopper.GUI.Base import GH_SliderAccuracy
    ROOT = "D:/rhino3d_ws/cat/"
    code = System.IO.File.ReadAllText(ROOT + "cat_rig_script_v001.py")
    doc = Grasshopper.Kernel.GH_Document()
    Grasshopper.Instances.DocumentServer.AddDocument(doc)
    Grasshopper.Instances.ActiveCanvas.Document = doc
    srv = Grasshopper.Instances.ComponentServer

    comp = srv.EmitObject(System.Guid("719467e6-7cf5-4848-99b0-c5dd57e5442c"))
    comp.CreateAttributes()
    comp.Attributes.Pivot = PointF(420, 260)
    comp.NickName = "CatRig"
    doc.AddObject(comp, False)
    from Grasshopper.Kernel import GH_ParameterSide as Side
    IN = ["src", "head_yaw", "head_nod", "head_tilt", "ear_l", "ear_r", "pupil",
          "paw_l", "paw_r", "tail_unwrap", "tail_lift", "breath", "laser", "hide_doc"]
    for prm in list(comp.Params.Input): comp.Params.UnregisterInputParameter(prm)
    for prm in list(comp.Params.Output):
        if prm.NickName != "out": comp.Params.UnregisterOutputParameter(prm)
    for i, nm in enumerate(IN):
        prm = comp.CreateParameter(Side.Input, i)
        prm.Name = prm.NickName = nm
        comp.Params.RegisterInputParam(prm, i)
    for nm in ("G", "C"):
        k = comp.Params.Output.Count
        prm = comp.CreateParameter(Side.Output, k)
        prm.Name = prm.NickName = nm
        comp.Params.RegisterOutputParam(prm, k)
    comp.VariableParameterMaintenance()
    comp.Params.OnParametersChanged()
    comp.SetSource(code)
    ok, txt = comp.TryGetSource()
    print("source set:", ok, len(txt or ""))
    ins = {p.NickName: p for p in comp.Params.Input}
    outs = {p.NickName: p for p in comp.Params.Output}
    print("inputs:", list(ins.keys()))
    print("outputs:", list(outs.keys()))

    y = [20]
    def put(obj, h=26):
        obj.CreateAttributes()
        obj.Attributes.Pivot = PointF(40, y[0])
        doc.AddObject(obj, False)
        y[0] += h
        return obj
    def slider(nick, mn, v, mx, dec=0):
        s = GH_NumberSlider()
        s.Slider.Type = GH_SliderAccuracy.Float if dec else GH_SliderAccuracy.Integer
        s.Slider.DecimalPlaces = dec
        s.Slider.Minimum = System.Decimal.Parse(str(mn))
        s.Slider.Maximum = System.Decimal.Parse(str(mx))
        s.Slider.Value = System.Decimal.Parse(str(v))
        s.NickName = nick
        put(s)
        ins[nick].AddSource(s)
    def toggle(nick, v):
        t = GH_BooleanToggle(); t.Value = v; t.NickName = nick
        put(t); ins[nick].AddSource(t)

    p = GH_Panel(); p.NickName = "src"; p.UserText = ROOT + "cat_v002.3dm"
    put(p, 50); ins["src"].AddSource(p)
    slider("head_yaw", -45, 0, 45)
    slider("head_nod", -30, 0, 30)
    slider("head_tilt", -25, 0, 25)
    slider("ear_l", -15, 0, 45)
    slider("ear_r", -15, 0, 45)
    slider("pupil", 0.3, 1.0, 2.5, 2)
    slider("paw_l", 0, 0, 90)
    slider("paw_r", 0, 0, 90)
    slider("tail_unwrap", -20, 0, 90)
    slider("tail_lift", 0, 0, 25)
    slider("breath", 0, 0, 1, 2)
    toggle("laser", True)
    toggle("hide_doc", True)

    prev = srv.EmitObject(System.Guid("537b0419-bbc2-4ff4-bf08-afe526367b2c"))
    prev.CreateAttributes(); prev.Attributes.Pivot = PointF(640, 260)
    doc.AddObject(prev, False)
    prev.Params.Input[0].AddSource(outs["G"])
    prev.Params.Input[1].AddSource(outs["C"])
    comp.Hidden = True   # only the Custom Preview draws
    doc.NewSolution(False)
    for m in comp.RuntimeMessages(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error): print("ERR", m)
    for m in comp.RuntimeMessages(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning): print("WARN", m)
    print("G count:", outs["G"].VolatileDataCount, "C count:", outs["C"].VolatileDataCount)
    for d in list(Grasshopper.Instances.DocumentServer):
        if d is not doc and d.ObjectCount == 0: Grasshopper.Instances.DocumentServer.RemoveDocument(d)
    io = Grasshopper.Kernel.GH_DocumentIO(doc)
    print("saved:", io.SaveQuiet(ROOT + "cat_rig_v001.gh"))
main()

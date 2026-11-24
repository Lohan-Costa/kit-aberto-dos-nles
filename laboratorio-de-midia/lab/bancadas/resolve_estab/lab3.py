from quadros import *
import time
r = resolve(); p = r.GetProjectManager().GetCurrentProject(); assert p.GetName() == "DLPC LAB ESTAB 21"
mp = p.GetMediaPool()
clip = [c for c in mp.GetRootFolder().GetClipList() if c.GetName() == "B19_TREMIDO.mov"][0]
tl = None
for i in range(1, p.GetTimelineCount() + 1):
    if p.GetTimelineByIndex(i).GetName() == "ESTAB_APARADO": tl = p.GetTimelineByIndex(i)
if not tl:
    tl = mp.CreateEmptyTimeline("ESTAB_APARADO")
    p.SetCurrentTimeline(tl)
    mp.AppendToTimeline([{"mediaPoolItem": clip, "startFrame": 30, "endFrame": 109}])
p.SetCurrentTimeline(tl)
it = tl.GetItemListInTrack("video", 1)[0]
print(it.GetName(), "start", it.GetStart(), "dur", it.GetDuration(), "src", it.GetSourceStartFrame(), it.GetSourceEndFrame())
print("Stabilize", it.Stabilize())
print("export", tl.Export(AQUI + "/lab3.drt", r.EXPORT_DRT))
import zipfile
z = zipfile.ZipFile(AQUI + "/lab3.drt")
for n in z.namelist():
    if n.startswith("SeqContainer"):
        x = z.read(n).decode()
        for b in re.findall(r"<Body>([0-9a-f]+)</Body>", x):
            d = dec(bytes.fromhex(b))
            E = entradas(d)
            if E: print("entradas", len(E), "q:", [q for q, _ in E[:3]], "…", [q for q, _ in E[-2:]])

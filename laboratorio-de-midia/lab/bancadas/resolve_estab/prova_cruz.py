from comum import *
import time, re, json
r = resolve(); p = r.GetProjectManager().GetCurrentProject(); assert p.GetName() == "DLPC PRODA 21 MAC ESTAB"
tl = p.GetCurrentTimeline(); ini = tl.GetStartFrame()
TR, Q0 = int(sys.argv[1]), int(sys.argv[2])
it = next(i for i in tl.GetItemListInTrack("video", TR) if i.GetStart() - ini == Q0)
a, b = it.GetStart(), it.GetEnd()
print(it.GetName(), a, b, "src", it.GetSourceStartFrame(), it.GetMediaPoolItem().GetClipProperty("File Path"))
cobre = []
for t in range(1, tl.GetTrackCount("video") + 1):
    if t == TR: continue
    for o in tl.GetItemListInTrack("video", t) or []:
        if o.GetStart() < b and o.GetEnd() > a and tl.GetIsTrackEnabled("video", t):
            cobre.append((t, o.GetName()))
print("por cima/baixo, ligadas:", cobre)
desl = sorted({t for t, _ in cobre})
for t in desl: tl.SetTrackEnable("video", t, False)
r.OpenPage("color")
J0, N = int(sys.argv[3]), int(sys.argv[4])
pasta = AQUI + f"/cruz_V{TR}"; os.makedirs(pasta, exist_ok=True)
fps = 24
for j in range(J0, J0 + N):
    f = a + j
    tl.SetCurrentTimecode(f"{f//(3600*fps):02d}:{f//(60*fps)%60:02d}:{f//fps%60:02d}:{f%fps:02d}"); time.sleep(0.25)
    p.ExportCurrentFrameAsStill(pasta + f"/{j:04d}.png")
for t in desl: tl.SetTrackEnable("video", t, True)
r.OpenPage("edit")
json.dump({"src": it.GetSourceStartFrame(), "arquivo": it.GetMediaPoolItem().GetClipProperty("File Path"), "j0": J0, "n": N}, open(pasta + "/info.json", "w"))

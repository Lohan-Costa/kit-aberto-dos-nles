from comum import *
import time
r = resolve()
pm = r.GetProjectManager()
cur = pm.GetCurrentProject()
print("atual", cur.GetName())
if cur.GetName() != "DLPC LAB ESTAB 21":
    pm.SaveProject()
    p = pm.LoadProject("DLPC LAB ESTAB 21") or pm.CreateProject("DLPC LAB ESTAB 21")
else:
    p = cur
p.SetSetting("timelineFrameRate", "23.976")
p.SetSetting("timelineResolutionWidth", "1920"); p.SetSetting("timelineResolutionHeight", "1080")
mp = p.GetMediaPool()
tl = p.GetTimelineByIndex(1) if p.GetTimelineCount() else None
if not tl:
    clips = mp.ImportMedia([TREM])
    tl = mp.CreateTimelineFromClips("ESTAB_LAB", clips)
p.SetCurrentTimeline(tl)
it = tl.GetItemListInTrack("video", 1)[0]
print(it.GetName(), it.GetStart(), it.GetDuration(), tl.GetStartFrame())
t = time.time(); print("Stabilize", it.Stabilize(), round(time.time() - t, 2))
ok = tl.Export(AQUI + "/lab1.drt", r.EXPORT_DRT)
print("export", ok)

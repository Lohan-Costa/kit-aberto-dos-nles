"""uso: injetar.py VARIANTE  (A: H = T(+u/1,5) · B: T(−u/1,5))  [minimo]"""
from quadros import *
import json, re, time
from tools.inspect_drp import pb_encode
VAR = sys.argv[1]; MINIMO = len(sys.argv) > 2
drx = open(AQUI + "/drx/lab_1.1.1.drx", encoding="utf-8").read()
corpos = re.findall(r"<Body>([0-9a-f]+)</Body>", drx)
d = dec(bytes.fromhex(corpos[0]))
d_drt = dec(body_do_xml(AQUI + "/" + [f for f in os.listdir(AQUI) if f == "lab1"][0] + "/SeqContainer/" + os.listdir(AQUI + "/lab1/SeqContainer")[0])[0])
print("drx == drt:", d == d_drt, len(d), len(d_drt))
QUADROS = (5, 20, 40, 72, 100, 130)
U = json.load(open(LAB + "/lab/bancadas/avid_estab/render_medido_100.json"))
Z = 1.0604091292619704
fs = pb_decode(d)
def troca(fs):
    for no in acha(fs, [3, 9, 1, 6, 2]):
        for lista in acha(no, [4]):
            for e in [f for f in lista if f["field"] == 1]:
                q = next((x["value"] for x in e["value"] if x["field"] == 1), 0)
                k = q // 2
                for p in [x for x in e["value"] if x["field"] == 2]:
                    pid = next(x["value"] for x in p["value"] if x["field"] == 1)
                    if pid != 0x10300015: continue
                    v = next(x for x in p["value"] if x["field"] == 2)["value"][0]
                    w = list(struct.unpack("<20f", v["value"]))
                    ux, uy = U[k]["ux"], U[k]["uy"]
                    s = 1 if VAR == "A" else -1
                    w[10] = 1 / Z
                    w[11:20] = [1, 0, s * ux / 1.5, 0, 1, s * uy / 1.5, 0, 0, 1]
                    v["value"] = v["value"][:40] + struct.pack("<10f", *w[10:20])
if VAR != "R": troca(fs)
novo = pb_encode(fs)
blob = (b"\x81" + zstandard.ZstdCompressor().compress(novo)).hex()
saida = drx.replace(corpos[0], blob, 1)
if MINIMO:
    saida = re.sub(r"\s*<pTrackVer>.*?</pTrackVer>", "", saida, flags=re.S)
    saida = re.sub(r"\s*<Vsr>.*?</Vsr>", "", saida, flags=re.S)
arq = AQUI + f"/drx/inj_{VAR}{'_min' if MINIMO else ''}.drx"
open(arq, "w", encoding="utf-8").write(saida)
r = resolve(); p = r.GetProjectManager().GetCurrentProject(); tl = p.GetCurrentTimeline()
assert p.GetName() == "DLPC LAB ESTAB 21"
it = tl.GetItemListInTrack("video", 1)[0]
t = time.time()
g = it.GetNodeGraph()
print("graph", g, "timeline tem:", hasattr(tl, "ApplyGradeFromDRX"))
if VAR != "R": print("apply", g.ApplyGradeFromDRX(arq, 0), round(time.time() - t, 2))
os.makedirs(AQUI + f"/quadros_{VAR}", exist_ok=True)
r.OpenPage("color")
def tc(f):
    h0 = tl.GetStartTimecode(); a = [int(x) for x in re.split("[:;]", h0)]
    f += ((a[0] * 60 + a[1]) * 60 + a[2]) * 24 + a[3]
    return f"{f // 86400:02d}:{f // 1440 % 60:02d}:{f // 24 % 60:02d}:{f % 24:02d}"
for k in QUADROS:
    tl.SetCurrentTimecode(tc(k)); time.sleep(0.4)
    print(k, p.ExportCurrentFrameAsStill(AQUI + f"/quadros_{VAR}/{k:03d}.png"))
r.OpenPage("edit")

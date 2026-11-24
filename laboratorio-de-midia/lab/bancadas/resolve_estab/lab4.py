from quadros import *
import json, time, zipfile, uuid
from tools.inspect_drp import pb_encode
U = json.load(open(LAB + "/lab/bancadas/avid_estab/render_medido_100.json")); Z = 1.0604091292619704
z = zipfile.ZipFile(AQUI + "/lab3.drt")
b = [bb for n in z.namelist() if n.startswith("SeqContainer") for bb in re.findall(r"<Body>([0-9a-f]+)</Body>", z.read(n).decode())
     if entradas(dec(bytes.fromhex(bb)))][0]
fs = pb_decode(dec(bytes.fromhex(b)))
for no in acha(fs, [3, 9, 1, 6, 2]):
    for lista in acha(no, [4]):
        for e in [f for f in lista if f["field"] == 1]:
            q = next((x["value"] for x in e["value"] if x["field"] == 1), 0)
            for pp in [x for x in e["value"] if x["field"] == 2]:
                if next(x["value"] for x in pp["value"] if x["field"] == 1) != 0x10300015: continue
                v = next(x for x in pp["value"] if x["field"] == 2)["value"][0]
                w = list(struct.unpack("<20f", v["value"]))
                ux, uy = U[q // 2]["ux"], U[q // 2]["uy"]
                w[10:20] = [1 / Z, 1, 0, ux / 1.5, 0, 1, uy / 1.5, 0, 0, 1]
                v["value"] = v["value"][:40] + struct.pack("<10f", *w[10:20])
blob = (b"\x81" + zstandard.ZstdCompressor().compress(pb_encode(fs))).hex()
xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Gallery::GyStill DbId="{uuid.uuid4()}">
 <pClipFullVer>
  <ListMgt::LmVersion DbId="{uuid.uuid4()}">
   <FieldsBlob/>
   <Name/>
   <HasCorrection>false</HasCorrection>
   <VerType>0</VerType>
   <ImplVersion>1</ImplVersion>
   <Body>{blob}</Body>
  </ListMgt::LmVersion>
 </pClipFullVer>
</Gallery::GyStill>
'''
arq = AQUI + "/drx/min_aparado.drx"; open(arq, "w").write(xml)
r = resolve(); p = r.GetProjectManager().GetCurrentProject(); tl = p.GetCurrentTimeline(); assert tl.GetName() == "ESTAB_APARADO"
it = tl.GetItemListInTrack("video", 1)[0]
print("apply", it.GetNodeGraph().ApplyGradeFromDRX(arq, 0))
os.makedirs(AQUI + "/quadros_M", exist_ok=True)
r.OpenPage("color")
h0 = tl.GetStartTimecode(); a = [int(x) for x in re.split("[:;]", h0)]; base = ((a[0]*60+a[1])*60+a[2])*24+a[3]
for j in (0, 10, 42, 70, 78):
    f = base + j
    tl.SetCurrentTimecode(f"{f//86400:02d}:{f//1440%60:02d}:{f//24%60:02d}:{f%24:02d}"); time.sleep(0.4)
    p.ExportCurrentFrameAsStill(AQUI + f"/quadros_M/{30 + j:03d}.png")
r.OpenPage("edit")

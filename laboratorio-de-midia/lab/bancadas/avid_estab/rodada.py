"""python rodada.py <sufixo> — fecha o Effect Editor, grava a bin, lê o filtro, reabre e exporta B19_MC_ESTAB_<sufixo>."""
import ctypes, json, os, sys, time
sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\piloto"); sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia")
from piloto import olhos, apps, maos
from lab.bancadas import avid as A
import avb
exe = apps.processo("avid")
NOME = "DLPC LAB ESTABILIZADOR"
BIN = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", NOME, NOME + " Bin.avb")
OUT = r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia\saida\bancadas\avid\estab_mc"
est = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado.json")))
ee = next((j["hwnd"] for j in olhos.janelas(exe) if j["titulo"] == "Effect Editor"), None)
if ee:
    assert maos.frente(ee); time.sleep(0.4)
    assert ctypes.windll.user32.GetForegroundWindow() == ee
    maos.tecla(0x57, 0x11); time.sleep(2)
print("janelas", [j["titulo"] for j in olhos.janelas(exe)])
with A.mc() as m:
    m.fechar_bin(BIN)
time.sleep(3)
with avb.open(BIN) as f:
    for i in range(len(f.object_positions)):
        try:
            o = f.read_object(i)
        except Exception:
            continue
        if type(o).__name__ == "TrackEffect" and "STABIL" in str(o.property_data.get("effect_id", "")):
            td = list(o.property_data["trackman"].data_slots.tracker_data)[0]
            print("obj", i, "filtro", td.filter_amount, "jitter", td.jitter_removal, "smoothing", td.smoothing,
                  "pos_x", [p.property_data.get("value") for p in o.property_data["param_list"]][6:8])
with A.mc() as m:
    m.abrir_bin(BIN)
time.sleep(3)
print(A.exportar(est["seq"], OUT, "B19_MC_ESTAB_" + sys.argv[1], preset="DLPC_LAB_DNXLB"))

"""passo 'gravar': fecha o Effect Editor, grava a bin, lê o tracker, reabre. passo 'export': instala o preset 50 e chama
o ExportFile (sem esperar). passo 'ver': confere o arquivo (tamanho) — uma chamada de no máximo 55 s."""
import ctypes, glob, json, os, sys, time
sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\piloto"); sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia")
from piloto import olhos, apps, maos
from lab.bancadas import avid as A
import avb
exe = apps.processo("avid")
NOME = "DLPC LAB ESTABILIZADOR 50P"
BIN = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", NOME, NOME + " Bin.avb")
OUT = r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia\saida\bancadas\avid\estab_mc"
AQUI = os.path.dirname(os.path.abspath(__file__))
est = json.load(open(os.path.join(AQUI, "estado50.json")))
p = sys.argv[1]
if p == "gravar":
    ee = next((j["hwnd"] for j in olhos.janelas(exe) if j["titulo"] == "Effect Editor"), None)
    if ee:
        assert maos.frente(ee); time.sleep(0.4)
        assert ctypes.windll.user32.GetForegroundWindow() == ee
        maos.tecla(0x57, 0x11); time.sleep(2)
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
                print("obj", i, "len", o.property_data.get("length"), "pontos", len(list(td.clips)[0].control_points),
                      "filtro", td.filter_amount, "rate", o.property_data.get("edit_rate"))
                est["obj"] = i
    with A.mc() as m:
        m.abrir_bin(BIN)
elif p == "export":
    pre = A.instalar_preset("50")
    for v in glob.glob(os.path.join(OUT, "B19_MC_ESTAB_50P.*")):
        os.remove(v)
    with A.mc() as m:
        print(m._chamar("ExportFile", _timeout=50, mob_id=est["seq"], file_name="B19_MC_ESTAB_50P",
                        export_settings_name=pre, destination_path=OUT))
elif p == "ver":
    t0 = time.time(); ult = None
    while time.time() - t0 < 50:
        fs = [(os.path.basename(f), os.path.getsize(f)) for f in glob.glob(os.path.join(OUT, "B19_MC_ESTAB_50P.*"))]
        prog = [j["titulo"] for j in olhos.janelas(exe) if j["titulo"] == "AvidMediaComposer"]
        print(round(time.time() - t0), "s", fs, "progresso" if prog else "")
        if fs and fs == ult and not prog:
            print("ESTÁVEL"); break
        ult = fs; time.sleep(8)
print("janelas", [j["titulo"] for j in olhos.janelas(exe)])
json.dump(est, open(os.path.join(AQUI, "estado50.json"), "w"))

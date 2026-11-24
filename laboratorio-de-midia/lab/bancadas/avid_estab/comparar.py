# ⚠️ REGISTRO HISTÓRICO — script de UMA rodada, na máquina do autor: os caminhos abaixo são os do SSD de trabalho
# dele e não existem noutra máquina. O que se mediu está registrado no banco (bancodedadosnles). Para repetir,
# peça ao Claude para adaptar: achar o laboratório SUBINDO de pasta e gerar a mídia por uma receita
# (skill ciclo-laboratorio) — nunca com o material de uma produção.
import json, sys
import numpy as np
import avb
B = r"%USERPROFILE%\Documents\Avid Projects\DLPC LAB ESTABILIZADOR\DLPC LAB ESTABILIZADOR Bin.avb"
V = json.load(open(r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia\saida\base\B19_ESTABILIZADOR\verdade.json"))
with avb.open(B) as f:
    o = f.read_object(130)
    td = list(o.property_data["trackman"].data_slots.tracker_data)[0]
    cl = list(td.clips)
    xs = np.array([cp.value for cp in cl[0].control_points]); ys = np.array([cp.value for cp in cl[1].control_points])
    print("settings", bytes(td.settings).hex())
    for i, c in enumerate(cl):
        v = [cp.value for cp in c.control_points]
        print(i, len(v), round(min(v), 5), round(max(v), 5), [round(x, 5) for x in v[:3]])
    from avb.parameter_uuids import PARAMETER_UUIDS
    for p in o.property_data["param_list"]:
        n = PARAMETER_UUIDS.get(str(p.property_data.get("uuid")))
        if n and ("POS" in n or "SCALE" in n or "Auto" in n): print(" ", n, p.property_data.get("value"))
q = V["quadros"] if isinstance(V, dict) and "quadros" in V else V
print(type(V), list(V)[:5] if isinstance(V, dict) else V[:2])
dx = np.array([k["dx"] for k in V["quadros"]]); dy = np.array([k["dy"] for k in V["quadros"]]); ang = np.array([k["ang"] for k in V["quadros"]])
n = min(len(dx), len(xs)); dx, dy, ang, xs, ys = dx[:n], dy[:n], ang[:n], xs[:n], ys[:n]
X, Y = xs * 1920, ys * 1080
for nome, a, b in (("X px × dx", X, dx), ("Y px × dy", Y, dy)):
    r = np.corrcoef(a, b)[0, 1]; k, c = np.polyfit(b, a, 1)
    print(f"{nome}: corr {r:+.4f}  X = {k:+.4f}·d + {c:.1f}  resíduo rms {np.std(a - (k*b + c)):.2f} px")
# com a rotação: o ponto (px,py) rel. ao centro gira; modelo completo da imagem: p = R(-ang)(p0 - d) aprox
P0 = np.array([X[0] + dx[0], Y[0] + dy[0]])

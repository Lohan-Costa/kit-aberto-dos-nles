"""O CC real da PRODA (Sat 87,5 + curva) no Resolve: 2 nós em série × 1 nó; e a Sat forte com curva (a ordem)."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia")
import numpy as np
from lab.bancadas import resolve as rb, resolve_cor as rc
from lab import cor_b24_modelo as M

cur = [x["_curva"] for x in json.load(open(r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia\resultados\B24_COR_MC\varredura_curva.json", encoding="utf-8")) if "_curva" in x]
C1, C2, MET = cur[10], cur[11], [[0, 0], [1, 0.5]]


def dois(sat, P):
    return [rc.no(1, [rc.p_f32(rc.SAT, sat / 100)], "MC Master"), rc.no(2, rc.curvas_rgb(rc.curva_do_mc(P)), "MC Curva")]


def um(sat, P):
    return [rc.no(1, [rc.p_f32(rc.SAT, sat / 100)] + rc.curvas_rgb(rc.curva_do_mc(P)), "MC")]


CASOS = [("neutro", None, None, None),
         ("cruz1 2nos", dois(87.5, C1), 87.5, C1), ("cruz1 1no", um(87.5, C1), 87.5, C1),
         ("cruz2 2nos", dois(87.5, C2), 87.5, C2), ("cruz2 1no", um(87.5, C2), 87.5, C2),
         ("sat150 metade 2nos", dois(150, MET), 150, MET), ("sat150 metade 1no", um(150, MET), 150, MET)]
TL = sys.argv[1]
r = rb.conectar()
itens = rc.preparar(r, TL, len(CASOS))
p = rc.projeto(r)
tl = rc.achar_timeline(p, TL)
r.OpenPage("edit")
for (nome, nos, _, _), it in zip(CASOS, itens):
    if nos:
        print(nome, rc.aplicar(tl, it, rc.body(nos), f"{TL}_{nome}"), it.GetNumNodes())
rc.salvar(r)
arq = rc.renderizar(r, TL, TL.replace(" ", "_"))
med = rc.medir(arq, len(CASOS))
json.dump({"casos": [c[0] for c in CASOS], "medidas": med}, open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"))
base = med[0]
areas = [a for a in base if not a.startswith("_")]
for (nome, nos, sat, P), m in zip(CASOS, med):
    if not nos:
        continue
    for ordem in ("sat→curva", "curva→sat"):
        e = []
        for k in areas:
            y, cb, cr = base[k]
            if ordem == "sat→curva":
                q = M.curva(P, *M.aplicar("Mas Sat", sat, y, cb, cr))
            else:
                q = M.aplicar("Mas Sat", sat, *M.curva(P, y, cb, cr))
            q = M.de_rgb(*[min(235.0, max(16.0, c)) for c in M.para_rgb(*q)])   # o corte do Resolve
            e.append(max(abs(a - b) for a, b in zip(q, m[k])))
        e = np.array(e)
        print(f"{nome:20s} {ordem}: média %.2f máx %.2f" % (e.mean(), e.max()))

"""Calibração no Resolve: Sat e a curva Custom escritas pelo Body, renderizadas e medidas na carta."""
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia")
from lab.bancadas import resolve as rb, resolve_cor as rc

cur = [x["_curva"] for x in json.load(open(r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia\resultados\B24_COR_MC\varredura_curva.json", encoding="utf-8")) if "_curva" in x]
IDENT = [(0, 0), (1 / 3, 1 / 3), (2 / 3, 2 / 3), (1, 1)]
METADE = [(0, 0), (1 / 3, 1 / 6), (2 / 3, 1 / 3), (1, 0.5)]
CASOS = [
    ("neutro", None),
    ("sat 0", [rc.p_f32(rc.SAT, 0.0)]),
    ("sat 0.5", [rc.p_f32(rc.SAT, 0.5)]),
    ("sat 0.875", [rc.p_f32(rc.SAT, 0.875), rc.p_f32(rc.LUM_MIX, 0.0)]),
    ("sat 2", [rc.p_f32(rc.SAT, 2.0)]),
    ("sat 2 lummix0", [rc.p_f32(rc.SAT, 2.0), rc.p_f32(rc.LUM_MIX, 0.0)]),
    ("curva identidade", rc.curvas_rgb(IDENT)),
    ("curva reta metade", rc.curvas_rgb(METADE)),
    ("mc 0.5-0.75", rc.curvas_rgb(rc.curva_do_mc(cur[4]))),
    ("mc cruz 1", rc.curvas_rgb(rc.curva_do_mc(cur[10]))),
    ("mc cruz 2", rc.curvas_rgb(rc.curva_do_mc(cur[11]))),
    ("mc nao monotona", rc.curvas_rgb(rc.curva_do_mc(cur[8]))),
]
TL = sys.argv[1] if len(sys.argv) > 1 else "TL CALIBRA 1"
r = rb.conectar()
itens = rc.preparar(r, TL, len(CASOS))
print(len(itens), [i.GetDuration() for i in itens][:3])
p = rc.projeto(r)
tl = rc.achar_timeline(p, TL)
r.OpenPage("edit")
res = []
for (nome, params), it in zip(CASOS, itens):
    if params is None:
        res.append((nome, None)); continue
    ok = rc.aplicar(tl, it, rc.body([rc.no(1, params, "MC")]), f"{TL}_{nome}")
    res.append((nome, ok))
    print(nome, ok, it.GetNumNodes() if hasattr(it, "GetNumNodes") else "")
rc.salvar(r)
arq = rc.renderizar(r, TL, TL.replace(" ", "_"))
print("render", arq)
m = rc.medir(arq, len(CASOS))
json.dump({"casos": [c[0] for c in CASOS], "aplicado": res, "medidas": m},
          open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok")

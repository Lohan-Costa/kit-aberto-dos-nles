"""B24_COR_MC no Premiere: o CC real da PRODA (ProcAmp Sat → Lumetri curva RGB mestra) e curvas do MC sozinhas, na
carta, contra o modelo do MC. Premiere aberto com a ponte do laboratório.

    py lab/cor_b24_premiere_cruz.py "LAB COR PREMIERE 3"
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab import cor_b24_modelo as M
from lab.bancadas import premiere_cor_mc as pc

CUR = [x["_curva"] for x in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                         "resultados", "B24_COR_MC", "varredura_curva.json"), encoding="utf-8")) if "_curva" in x]
C1, C2 = CUR[10], CUR[11]
L, PA = ["Lumetri Color", {}], lambda s: ["ProcAmp", {"Saturation": s}]
CASOS = [("neutro", [], None, None), ("cruz1", [PA(87.5), L], 87.5, C1), ("cruz2", [PA(87.5), L], 87.5, C2),
         ("curva cruz1", [L], None, C1), ("curva 0.5-0.75", [L], None, CUR[4]), ("curva nao monotona", [L], None, CUR[8]),
         ("curva pontas dentro", [L], None, CUR[9])]


def sat601(y, cb, cr, s):
    r, g, b = M.para_rgb(y, cb, cr)
    y6 = 0.299 * r + 0.587 * g + 0.114 * b
    return M.de_rgb(*[y6 + s / 100 * (c - y6) for c in (r, g, b)])


BLOCOS = (1, 2, 3)   # R, G, B — a mestra preserva o matiz e o MC não


def main(nome: str) -> None:
    v = pc.p.executar("app.version")
    pc.TRABALHO = os.path.join(pc.RAIZ, "saida", "bancadas", f"premiere-{v}", "B24_COR_MC")
    ano = {"27": "2027", "26": "2026", "25": "2025", "23": "2023"}.get(v.split(".")[0], "2026")
    print("Premiere", v, "→", pc.TRABALHO)
    try:
        pc.fechar_projeto()
    except Exception:  # noqa: BLE001
        pass
    r = pc.montar_efeitos(nome, [c[1] for c in CASOS])
    proj = r["projeto"]
    pc.fechar_projeto()
    curvas, papel = {}, {}
    for k, (_, _, _, P) in enumerate(CASOS):
        if P is not None:
            curvas[k], papel[k] = pc.curva_lumetri_do_mc(P)
    print("curvas escritas:", pc.curvas_no_projeto(proj, curvas, BLOCOS), {k: round(v, 3) for k, v in papel.items()})
    pc.abrir_projeto(proj)
    arq = pc.exportar(proj, ano)
    med = pc.medir(arq, len(CASOS))
    json.dump({"casos": [c[0] for c in CASOS], "medidas": med}, open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"))
    base = med[0]
    areas = [a for a in base if not a.startswith("_")]
    for (nome_c, _, s, P), m in list(zip(CASOS, med))[1:]:
        for rotulo, sat in (("MC", lambda y, cb, cr: M.aplicar("Mas Sat", s, y, cb, cr)), ("ProcAmp 601", lambda y, cb, cr: sat601(y, cb, cr, s))):
            if s is None and rotulo != "MC":
                continue
            dentro, fora = [], []
            for a in areas:
                q = base[a] if s is None else sat(*base[a])
                q = M.curva(P, *q)
                er = max(abs(x - y) for x, y in zip([M.cortar(c) for c in q], m[a]))
                (dentro if all(15.5 <= c <= 235.5 for c in M.para_rgb(*q)) else fora).append(er)
            print(f"{nome_c:22s} previsto pelo {rotulo:12s} dentro {len(dentro):3d}: média %.2f máx %.2f | fora {len(fora):3d}: média %.2f máx %.2f"
                  % (np.mean(dentro), np.max(dentro), np.mean(fora) if fora else 0, np.max(fora) if fora else 0))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LAB COR PREMIERE 3")

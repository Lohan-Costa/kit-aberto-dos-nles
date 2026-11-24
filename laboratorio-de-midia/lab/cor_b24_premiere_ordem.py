"""B24_COR_MC no Premiere: a ORDEM ProcAmp × Lumetri (pedido do autor, 2026-11-20).

O QE põe o efeito novo ACIMA dos anteriores: chamar ProcAmp e depois Lumetri dá a cadeia Lumetri → ProcAmp (a curva
ANTES da Sat), o inverso do MC (Sat → curva) — e foi isso que a bancada da PRODA mediu (0,45 / 1,46). Aqui as DUAS
ordens, lidas do arquivo salvo (nunca supostas), nos CC da PRODA e com Sat 50 e 150 (onde a ordem pesa mais), contra
o modelo do MC (Sat → curva) e contra o modelo invertido (curva → Sat).

    py lab/cor_b24_premiere_ordem.py "LAB COR PREMIERE ORDEM"     (Premiere aberto com a ponte do laboratório)
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab import cor_b24_modelo as M
from lab.bancadas import premiere_cor_mc as pc
from lab.cor_b24_premiere_cruz import BLOCOS, C1, C2, sat601

L, PA = ["Lumetri Color", {}], lambda s: ["ProcAmp", {"Saturation": s}]
#: (nome, efeitos NA ORDEM DE CHAMADA, Sat, curva)
CASOS = [("neutro", [], None, None)]
for nome_c, s, P in (("cruz1", 87.5, C1), ("cruz2", 87.5, C2), ("sat50+c1", 50.0, C1), ("sat150+c1", 150.0, C1)):
    CASOS += [(f"{nome_c} chamada PA,L", [PA(s), L], s, P), (f"{nome_c} chamada L,PA", [L, PA(s)], s, P)]


def ordem_no_arquivo(proj: str) -> list[list[str]]:
    """A cadeia de cada clipe da V1 (na ordem do tempo), pelo MatchName — o que o Premiere de fato gravou."""
    xml = pc.ler_xml(proj)
    out = []
    for m in re.finditer(r'<VideoClipTrackItem ObjectID="\d+"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S):
        ini = re.search(r"<Start>(-?\d+)</Start>", m.group(1))
        comps = re.search(r'<Components ObjectRef="(\d+)"/>', m.group(1))
        cad = pc._obj(xml, comps.group(1)) if comps else None
        nomes = []
        for ref in re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', cad.group(0) if cad else ""):
            c = pc._obj(xml, ref)
            mn = re.search(r"<MatchName>([^<]+)</MatchName>", c.group(0)) if c else None
            if mn and mn.group(1) in ("AE.ADBE Lumetri", "AE.ADBE ProcAmp"):
                nomes.append(mn.group(1).split()[-1])
        out.append((int(ini.group(1)) if ini else 0, nomes))
    return [n for _, n in sorted(out)]


def main(nome: str) -> None:
    v = pc.p.executar("app.version")
    pc.TRABALHO = os.path.join(pc.RAIZ, "saida", "bancadas", f"premiere-{v}", "B24_COR_MC")
    ano = {"27": "2027", "26": "2026", "25": "2025", "23": "2023"}.get(v.split(".")[0], "2026")
    print("Premiere", v, "→", pc.TRABALHO, flush=True)
    try:
        pc.fechar_projeto()
    except Exception:  # noqa: BLE001
        pass
    r = pc.montar_efeitos(nome, [c[1] for c in CASOS])
    proj = r["projeto"]
    pc.fechar_projeto()
    ordens = ordem_no_arquivo(proj)
    curvas = {k: pc.curva_lumetri_do_mc(P)[0] for k, (_, _, _, P) in enumerate(CASOS) if P is not None}
    pc.curvas_no_projeto(proj, curvas, BLOCOS)
    pc.abrir_projeto(proj)
    arq = pc.exportar(proj, ano)
    med = pc.medir(arq, len(CASOS))
    base = med[0]
    areas = [a for a in base if not a.startswith("_")]
    linhas = []
    for (nome_c, _, s, P), m, ordem in list(zip(CASOS, med, ordens))[1:]:
        res = {"caso": nome_c, "cadeia": " → ".join(ordem)}
        for rotulo, primeiro_sat, conta in (("MC Sat→curva", True, "709"), ("Sat→curva 601", True, "601"),
                                            ("curva→Sat 601", False, "601")):
            dentro = []
            for a in areas:
                q = base[a]
                sat = (lambda y, cb, cr: M.aplicar("Mas Sat", s, y, cb, cr)) if conta == "709" else \
                      (lambda y, cb, cr: sat601(y, cb, cr, s))
                q = M.curva(P, *sat(*q)) if primeiro_sat else sat(*M.curva(P, *q))
                if all(15.5 <= c <= 235.5 for c in M.para_rgb(*q)):
                    dentro.append(max(abs(x - y) for x, y in zip([M.cortar(c) for c in q], m[a])))
            res[rotulo] = [round(float(np.mean(dentro)), 2), round(float(np.max(dentro)), 2), len(dentro)]
        linhas.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    json.dump({"casos": [c[0] for c in CASOS], "ordens": ordens, "medidas": med, "resumo": linhas},
              open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LAB COR PREMIERE ORDEM")

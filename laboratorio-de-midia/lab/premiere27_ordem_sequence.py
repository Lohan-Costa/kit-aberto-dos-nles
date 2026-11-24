"""A página Color do Premiere 2027: a ORDEM Sequence × Clip, pelo pixel (pedido do autor, 2026-11-20).

Do `LAB COR 27 SEQ UI` (a camada "Sequence Adjust 1" criada pelo "+" da interface): Contrast 0,5 / Pivot 0 NA SEQUÊNCIA.
Os clipes já têm, no nível Clip: 0 nada (página neutra) · 1 Exposure +1 · 2 Contrast 0,5 · 3 Exposure → Contrast ·
4 Contrast → Exposure. A base NEUTRA vem do `LAB COR 27 CAMADAS` (o clipe 0 dele: a mesma carta no mesmo Premiere) — a
sequência pega todos os clipes. Previsão: o modelo do kernel com a camada da sequência DEPOIS e ANTES das do clipe.

    python lab/premiere27_ordem_sequence.py       (Premiere 2027 aberto, ponte do laboratório)
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
from lab.bancadas import premiere_pagina_cor as pg
from lab.premiere27_ordem_camadas import CON, EXP, PASTA, prever

ORIGEM = os.path.join(PASTA, "LAB COR 27 SEQ UI.prproj")
DESTINO = os.path.join(PASTA, "LAB COR 27 SEQ ORDEM.prproj")
BASE = os.path.join(PASTA, "LAB COR 27 CAMADAS_medidas.json")
SEQ = CON
CLIPES = [("só a sequência", []), ("clipe Exposure", [EXP]), ("clipe Contrast", [CON]),
          ("clipe Exposure → Contrast", [EXP, CON]), ("clipe Contrast → Exposure", [CON, EXP])]


def gerar() -> None:
    xml = pg.ler_xml(ORIGEM)
    a = pg.Arvore(xml)
    camada = next(o for o, (_, c) in a.obj.items() if "<InstanceName>Sequence Adjust 1</InstanceName>" in c)
    dono = re.search(r'<Components ObjectRef="(\d+)"/>', a.obj[camada][1]).group(1)
    cc = next(f for f in a._cadeia(dono) if "<MatchName>AE.ADBE Color And Contrast</MatchName>" in a.obj[f][1])
    feitos = set()
    for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', a.obj[cc][1]):
        nome = (a._campo(a.obj[ref][1], "Name") or "").strip()
        if nome in SEQ and nome not in feitos:            # o 1º de cada nome = o global (as zonas repetem os nomes)
            feitos.add(nome)
            corpo = a.obj[ref][1]
            xml = xml.replace(corpo, re.sub(r"<StartKeyframe>([^,<]*),[^,<]*",
                                            lambda m: "<StartKeyframe>%s,%r" % (m.group(1), SEQ[nome]), corpo, 1), 1)
    assert feitos == set(SEQ), feitos
    pc.gravar_xml(DESTINO, xml)
    print("sequência:", SEQ, "· clipes:", [c[0] for c in CLIPES], flush=True)


def main() -> None:
    gerar()
    v = pc.p.executar("app.version")
    print("Premiere", v, flush=True)
    pc.fechar_projeto()
    pc.abrir_projeto(DESTINO)
    arq = pc.exportar(DESTINO, "2027")
    med = pc.medir(arq, len(CLIPES))
    base = json.load(open(BASE, encoding="utf-8"))["medidas"][0]
    areas = [x for x in base if not x.startswith("_")]
    resumo = []
    for (nome, clipe), m in zip(CLIPES, med):
        res = {"caso": nome}
        for rot, ordem in (("Clip → Sequence", clipe + [SEQ]), ("Sequence → Clip", [SEQ] + clipe)):
            erros = []
            for x in areas:
                q = prever(ordem, base[x])
                if all(16 <= c <= 235 for c in M.para_rgb(*q)):
                    erros.append(max(abs(a - b) for a, b in zip([M.cortar(c) for c in q], m[x])))
            res[rot] = [round(float(np.mean(erros)), 2), round(float(np.max(erros)), 2), len(erros)]
            if not clipe:
                break
        resumo.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    json.dump({"sequencia": SEQ, "casos": [c[0] for c in CLIPES], "medidas": med, "resumo": resumo},
              open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()

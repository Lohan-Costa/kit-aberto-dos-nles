"""A página Color do Premiere 2027: a STYLE pelo pixel (pedido do autor, 2026-11-20).

Medido no arquivo (`LAB COR 27 STYLE A`, salvo pela ponte do estado que o autor montou à mão): escolher o módulo
"Color / Contrast" numa Style grava na cadeia da Style (65540) um `AE.ADBE Color And Contrast` COMUM, neutro — o mesmo
efeito da camada Adjustment. Aqui: Exposure +1 no CC da "Sequence Style 1", a "Sequence Adjust 1" segue com Contrast
0,5 / Pivot 0, e a camada LUT da sequência sai da cadeia (o pixel dela é outra medida). Os 5 primeiros clipes têm a
grade de clipe do lab de ordem (nada · Exposure · Contrast · Exposure → Contrast · Contrast → Exposure).
Previsão: clipe → Style → Adjust (a ordem do arquivo) contra clipe → Adjust → Style.

    python lab/premiere27_style.py       (Premiere 2027 aberto, ponte do laboratório)
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
from lab.premiere27_ordem_sequence import CLIPES

ORIGEM = os.path.join(PASTA, "LAB COR 27 STYLE A.prproj")
DESTINO = os.path.join(PASTA, "LAB COR 27 STYLE PIXEL.prproj")
BASE = os.path.join(PASTA, "LAB COR 27 CAMADAS_medidas.json")
STYLE = EXP


def _escrever_cc(xml: str, a: "pg.Arvore", camada_nome: str, valores: dict) -> str:
    camada = next(o for o, (_, c) in a.obj.items() if "<InstanceName>%s</InstanceName>" % camada_nome in c)
    dono = re.search(r'<Components ObjectRef="(\d+)"/>', a.obj[camada][1]).group(1)
    cc = next(f for f in a._cadeia(dono) if "<MatchName>AE.ADBE Color And Contrast</MatchName>" in a.obj[f][1])
    feitos = set()
    for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', a.obj[cc][1]):
        nome = (a._campo(a.obj[ref][1], "Name") or "").strip()
        if nome in valores and nome not in feitos:        # o 1º de cada nome = o global (as zonas repetem os nomes)
            feitos.add(nome)
            corpo = a.obj[ref][1]
            xml = xml.replace(corpo, re.sub(r"<StartKeyframe>([^,<]*),[^,<]*",
                                            lambda m: "<StartKeyframe>%s,%r" % (m.group(1), valores[nome]), corpo, 1), 1)
    assert feitos == set(valores), feitos
    return xml


def gerar() -> None:
    xml = pc.ler_xml(ORIGEM)
    a = pg.Arvore(xml)
    xml = _escrever_cc(xml, a, "Sequence Style 1", STYLE)
    # a camada LUT da sequência sai da cadeia do contêiner da sequência (é a última: os índices não mudam)
    lut = next(o for o, (_, c) in a.obj.items() if "<MatchName>AE.ADBE LUT Transform</MatchName>" in c)
    linha = re.search(r'\s*<Component Index="\d+" ObjectRef="%s"/>' % lut, xml)
    xml = xml[:linha.start()] + xml[linha.end():]
    pc.gravar_xml(DESTINO, xml)
    print("Style:", STYLE, "· Adjust:", CON, "· sem a LUT", flush=True)


def main() -> None:
    gerar()
    print("Premiere", pc.p.executar("app.version"), flush=True)
    pc.fechar_projeto()
    pc.abrir_projeto(DESTINO)
    arq = pc.exportar(DESTINO, "2027")
    med = pc.medir(arq, len(CLIPES))
    base = json.load(open(BASE, encoding="utf-8"))["medidas"][0]
    areas = [x for x in base if not x.startswith("_")]
    resumo = []
    for (nome, clipe), m in zip(CLIPES, med):
        res = {"caso": nome}
        for rot, ordem in (("clipe → Style → Adjust", clipe + [STYLE, CON]),
                           ("clipe → Adjust → Style", clipe + [CON, STYLE]),
                           ("sem a Style", clipe + [CON])):
            erros = []
            for x in areas:
                q = prever(ordem, base[x])
                if all(16 <= c <= 235 for c in M.para_rgb(*q)):
                    erros.append(max(abs(a - b) for a, b in zip([M.cortar(c) for c in q], m[x])))
            res[rot] = [round(float(np.mean(erros)), 2), round(float(np.max(erros)), 2), len(erros)]
        resumo.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    json.dump({"style": STYLE, "adjust": CON, "casos": [c[0] for c in CLIPES], "medidas": med, "resumo": resumo},
              open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()

"""A página Color do Premiere 2027: a ORDEM entre DUAS camadas Adjustment no MESMO nível (Clip) — pedido do autor,
2026-11-20. (Clip × Grupo já está medido: o Clip antes, banco `prproj/estruturas.md` §Premiere 2027.)

Do `LAB COR 27 ESCALAS` (a carta B24 em cópias de 12 quadros, uma página Color por clipe): a camada "Adjust 1" de cada
um dos 5 primeiros clipes zerada; nos clipes 3 e 4 uma 2ª camada ("Adjust 2", CLONE da 1ª, pendurada DEPOIS dela na
cadeia do nível Clip). Exposure +1 e Contrast 0,5 (Pivot 0) não comutam:
    0 neutro · 1 Exposure 1 · 2 Contrast 0,5 · 3 [Adjust 1 Exposure, Adjust 2 Contrast] · 4 [Adjust 1 Contrast, Adjust 2 Exposure]
Previsão: o modelo do kernel (`premiere_pagina_cor.color_and_contrast`) nas duas ordens, sobre o neutro MEDIDO.

    python lab/premiere27_ordem_camadas.py      (Premiere 2027 aberto no projeto gerado, ponte do laboratório)
    python lab/premiere27_ordem_camadas.py --so-gerar   (só o arquivo) · --so-medir (o projeto já aberto)
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

PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saida", "bancadas", "premiere-27.0.0",
                     "B24_COR_MC")
ORIGEM = os.path.join(PASTA, "LAB COR 27 ESCALAS.prproj")
DESTINO = os.path.join(PASTA, "LAB COR 27 CAMADAS.prproj")
EXP, CON = {"Exposure": 1.0}, {"Contrast": 0.5, "Pivot": 0.0}
CASOS = [("neutro", [{}]), ("Exposure", [EXP]), ("Contrast", [CON]),
         ("Adjust1 Exposure, Adjust2 Contrast", [EXP, CON]), ("Adjust1 Contrast, Adjust2 Exposure", [CON, EXP])]
ZERAR = {"Exposure": "0.", "Contrast": "1.", "Pivot": "-3.", "Temperature": "0.", "Tint": "0.", "Saturation": "1.",
         "Black": "0."}


def _itens(xml):
    a = pg.Arvore(xml)
    return a, sorted(((int(a._campo(m.group(2), "Start") or 0), m.group(1), m.group(2)) for m in
                      re.finditer(r'<VideoClipTrackItem ObjectID="(\d+)"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S)))


def segunda_camada(xml: str, clipe: int) -> str:
    """Clona a camada "Adjust 1" (o 65538 e tudo que ela alcança) do nível Clip do `clipe`, com ObjectIDs novos e o nome
    "Adjust 2", e a pendura DEPOIS dela na cadeia do nível Clip (como o "+" › Add Clip Adjustment)."""
    a, itens = _itens(xml)
    cad = re.search(r'<Components ObjectRef="(\d+)"/>', itens[clipe][2]).group(1)

    def desce(oid, tipo):
        corpo = a.obj[oid][1]
        dono = re.search(r'<Components ObjectRef="(\d+)"/>', corpo).group(1)
        return dono, next(f for f in a._cadeia(dono) if pg.COMPOUND in a.obj[f][1][:200]
                          and int(a._campo(a.obj[f][1], "CompoundComponentType") or 0) == tipo)
    cont = next(o for o in a._cadeia(cad) if pg.COMPOUND in a.obj[o][1][:200])
    _, nivel = desce(cont, 65541)
    cadeia_nivel, camada = desce(nivel, 65538)
    alc, fila = [], [camada]
    while fila:
        o = fila.pop()
        if o in alc or o not in a.obj:
            continue
        alc.append(o)
        fila += re.findall(r'ObjectRef="(\d+)"', a.obj[o][1])
    prox = max(int(o) for o in a.obj) + 1
    mapa = {o: str(prox + i) for i, o in enumerate(alc)}
    novos = []
    for o in alc:
        corpo = a.obj[o][1]
        corpo = re.sub(r'ObjectID="(\d+)"', lambda m: 'ObjectID="%s"' % mapa.get(m.group(1), m.group(1)), corpo, 1)
        corpo = re.sub(r'ObjectRef="(\d+)"', lambda m: 'ObjectRef="%s"' % mapa.get(m.group(1), m.group(1)), corpo)
        if o == camada:
            corpo = corpo.replace("<InstanceName>Adjust 1</InstanceName>", "<InstanceName>Adjust 2</InstanceName>", 1)
            corpo = re.sub(r"<ID>\d+</ID>", "<ID>2</ID>", corpo, 1)
        novos.append(corpo)
    corpo_c = a.obj[cadeia_nivel][1]
    n = len(re.findall(r"<Component Index=", corpo_c))
    corpo_n = corpo_c.replace("</Components>", '\t<Component Index="%d" ObjectRef="%s"/>\n\t\t\t</Components>'
                              % (n, mapa[camada]), 1)
    xml = xml.replace(corpo_c, corpo_n, 1)
    fim = xml.rfind("</PremiereData>")
    return xml[:fim] + "\n".join("\t" + x for x in novos) + "\n" + xml[fim:]


def gerar() -> str:
    xml = pg.ler_xml(ORIGEM)
    for k, (_, camadas) in enumerate(CASOS):
        for nome, v in ZERAR.items():
            xml = pg.escrever(xml, k, ["nível Clip", "Adjust 1"], "AE.ADBE Color And Contrast", nome, v)
        if len(camadas) == 2:
            xml = segunda_camada(xml, k)
        for i, p in enumerate(camadas):
            for nome, v in p.items():
                xml = pg.escrever(xml, k, ["nível Clip", f"Adjust {i + 1}"], "AE.ADBE Color And Contrast", nome, repr(v))
    pc.gravar_xml(DESTINO, xml)
    # confere o que ficou escrito, pelo leitor da árvore
    clipes = pg.Arvore(xml).clipes()[:len(CASOS)]
    for (nome, _), c in zip(CASOS, clipes):
        nivel = c["componentes"][0]["filhos"][0]
        print(nome, "→", [(cam["nome"], {k: v for k, v in cam["filhos"][0]["params"].items()
                                         if k.split(":")[0] in ("2", "4", "5")}) for cam in nivel["filhos"]], flush=True)
    return DESTINO


def prever(camadas, ycc):
    v = [(c - 16) / 219 for c in M.para_rgb(*ycc)]
    for p in camadas:
        v = list(pg.color_and_contrast(np.array(v), p)) if p else v
    return M.de_rgb(*[16 + 219 * float(c) for c in v])


def main() -> None:
    if "--so-medir" not in sys.argv:          # com o projeto aberto no Premiere, não regravar
        gerar()
    if "--so-gerar" in sys.argv:
        return
    v = pc.p.executar("app.version")
    print("Premiere", v, flush=True)
    arq = pc.exportar(DESTINO, "2027")
    med = pc.medir(arq, len(CASOS))
    base = med[0]
    areas = [a for a in base if not a.startswith("_")]
    resumo = []
    for (nome, camadas), m in list(zip(CASOS, med))[1:]:
        res = {"caso": nome}
        for rot, ordem in (("na ordem do arquivo", camadas), ("na ordem inversa", list(reversed(camadas)))):
            erros = []
            for a in areas:
                q = prever(ordem, base[a])
                if all(16 <= c <= 235 for c in M.para_rgb(*q)):
                    erros.append(max(abs(x - y) for x, y in zip([M.cortar(c) for c in q], m[a])))
            res[rot] = [round(float(np.mean(erros)), 2), round(float(np.max(erros)), 2), len(erros)]
            if len(camadas) == 1:
                break
        resumo.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    json.dump({"casos": [c[0] for c in CASOS], "medidas": med, "resumo": resumo},
              open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()

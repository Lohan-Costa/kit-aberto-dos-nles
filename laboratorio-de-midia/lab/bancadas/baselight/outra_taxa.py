"""BL09, o render da cor de OUTRA TAXA voltando (Ciclo Assist, 2026-11-23): os planos do BL08 cujo original não é da taxa
da timeline (A002C001 29,97 DF e B001C005 59,94, numa timeline de 23,976) renderizados pelo Baselight da scene
"BL08 PRODUTO APP" (`render_scene.py`, RENDER_FAIXA 528,576 e 192,240 → `RENDER_OUTRA_TAXA/*_COR.mov`).

Medido: o render sai na taxa da TIMELINE (23,976, 48 quadros) e grava o TC de fonte no contador cru do `tmcd`, na base
do ORIGINAL (nframes 30 + DF / 60), com o reel = o nome do arquivo do original COM a extensão. O ffprobe converte o de 60
por tempo e recusa o de 30 DF.

    <assist>/.venv/bin/python outra_taxa.py preparar     # o xmeml da montagem (um plano normal + os dois renders)
    <assist>/.venv/bin/python outra_taxa.py produto      # casador do Premiere → entrega → Baselight (sem levar cor)

A verdade (o quadro de fonte do original no in do plano, pelo tempo): A002C001 (11,9786 + 4/23,976) × 29,97 = 364;
B001C005 (1,9686 + 4/23,976) × 59,94 = 128; o B001C007 normal, 47.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import quote

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atualizar_corte as B  # noqa: E402

LAB = B.LAB
ORIG08 = os.path.join(LAB, "saida", "baselight", "BL08_CASAMENTO", "ORIGINAIS")
RENDER = os.path.join(B.SAIDA, "RENDER_OUTRA_TAXA")
XML = os.path.join(B.SAIDA, "BL09_OUTRA_TAXA.xml")
JOB = B.JOB
#: (arquivo, TC que o xmeml diz, quadros do arquivo, in, duração, reel)
PLANOS = [
    (os.path.join(ORIG08, "DIA01/B001/B001C007.mov"), "13:00:00:00", 288, 47, 48, "B001C007"),
    (os.path.join(RENDER, "A002C001_COR.mov"), "16:59:01:23", 48, 4, 40, "A002C001.mov"),
    (os.path.join(RENDER, "B001C005_COR.mov"), "12:00:01:23", 48, 4, 40, "B001C005.mov"),
]
VERDADE = {"B001C007.mov": 47, "A002C001.mov": 364, "B001C005.mov": 128}


def preparar() -> None:
    R = B.RATE
    itens, t = [], 0
    for i, (arq, tc, quadros, ini, dur, reel) in enumerate(PLANOS, 1):
        nome = os.path.basename(arq)
        f = (f'<file id="file-{i}"><name>{nome}</name><pathurl>file://localhost{quote(arq)}</pathurl>{R}'
             f'<duration>{quadros}</duration><timecode>{R}<string>{tc}</string><frame>{B.tc_q(tc)}</frame>'
             f'<displayformat>NDF</displayformat><reel><name>{reel}</name></reel></timecode><media><video>'
             f'<samplecharacteristics>{R}<width>1920</width><height>1080</height></samplecharacteristics></video>'
             f'</media></file>')
        itens.append(f'<clipitem id="clipitem-{i}"><name>{nome}</name><enabled>TRUE</enabled><duration>{quadros}'
                     f'</duration>{R}<start>{t}</start><end>{t + dur}</end><in>{ini}</in><out>{ini + dur}</out>{f}'
                     f'</clipitem>')
        t += dur
    x = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="sequence-1">'
         f'<duration>{t}</duration>{R}<name>BL09 OUTRA TAXA</name><timecode>{R}<string>01:00:00:00</string>'
         f'<frame>{B.tc_q("01:00:00:00")}</frame><displayformat>NDF</displayformat></timecode><media><video><format>'
         f'<samplecharacteristics>{R}<width>1920</width><height>1080</height></samplecharacteristics></format>'
         f'<track>{"".join(itens)}</track></video></media></sequence></xmeml>\n')
    with open(XML, "w", encoding="utf-8") as fh:
        fh.write(x)
    print(XML)


def produto(base: str = "BL09 outra taxa") -> None:
    p = AQUI
    while not os.path.isdir(os.path.join(p, "2 ATIVOS")):
        p = os.path.dirname(p)
    raiz = os.path.join(p, "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar")
    sys.path[:0] = [os.path.join(raiz, "motor"), os.path.join(raiz, "plugins", "media-composer", "servico"), raiz]
    import subprocess

    from baselight import entrega as E
    from baselight import enviar as EV
    from baselight import xmeml as X
    from prproj.originais import casar, indexar
    leitura = X.ler(XML)
    casamento = casar([s for s in leitura["segmentos"] if not s.get("disabled")], [ORIG08], indice=indexar([ORIG08]))
    decisao = {}
    for k, v in casamento.items():
        print(" casador:", os.path.basename(k), "→", v.get("estado"), os.path.basename(v.get("original") or ""),
              (v.get("motivo") or (v.get("trecho") or {}).get("motivo") or "")[:150])
        o = v.get("original") if v.get("estado") in ("original", "proprio") else None
        decisao[k] = (E.descrever(o, EV._sondar(E.como_o_disco_lista(o)), fps_sequencia=leitura["fps"],
                                  trecho=v.get("trecho")) if o and os.path.isfile(o) else None)
    r = EV.entregar_xmeml(XML, decisao, JOB, base, [ORIG08], os.path.join(B.SAIDA, "trabalho"),
                          andamento=lambda e, t, **k: print("  ·", t))
    print(f"scene {r['scene']}: {r['planos']} planos {r['contagem']}")
    for x in r.get("problemas", []):
        print("  problema:", x)
    saida = subprocess.run([os.path.join(B.BIN, "bl-shots"), "-inputrange", "-outputrange",
                            f"{B.HOST}:{JOB}:{r['scene']}"], capture_output=True, text=True).stdout
    certos = 0
    for linha in saida.splitlines():
        a, _b, _c, _d, arq = linha.split("\t", 4)
        nome = os.path.basename(arq)
        ok = VERDADE.get(nome) == int(a)
        certos += ok
        print(f"  {nome:14} fonte {a:>4} (verdade {VERDADE.get(nome)}) {'✓' if ok else '✗'}")
    print(f"no ponto: {certos}/{len(VERDADE)}")


if __name__ == "__main__":
    {"preparar": preparar, "produto": produto}[sys.argv[1]](*sys.argv[2:])

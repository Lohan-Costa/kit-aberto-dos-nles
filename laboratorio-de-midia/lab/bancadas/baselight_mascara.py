"""BL07 no Baselight — a MÁSCARA de opacidade (a B14) levada ao Baselight (missão Baselight, plano
`2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-21-baselight-mascara-e-entrega.md`).

    python3 -m lab.bancadas.baselight_mascara xml        # o xmeml de duas trilhas (só a montagem, sem máscara)
    python3 -m lab.bancadas.baselight_mascara medir <render.mov> [rótulo]   # a borda por segmento × a do Premiere

A verdade: `saida/base/B14_MASCARA/verdade.json` (a borda de cada segmento) e a medida do render do Premiere 23.2
(`saida/bancadas/premiere/B14_MASCARA/medida_premiere.json`). Ficam de fora por ora os segmentos com zoom (Z200_*) e o
de 100 qps (ANIM_100).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse

from .. import mascara_b14 as m
from ..gerar import RAIZ

BASE = os.path.join(RAIZ, "saida", "base", "B14_MASCARA")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "baselight_mascara")
XML = os.path.join(TRAB, "BL07_MASCARA.xml")
FORA = ("Z200_F201", "Z200_F50", "ANIM_100")


def segmentos() -> list[dict]:
    return [dict(s, inicio=m.inicio(i), indice=i) for i, s in enumerate(m.PLANO) if s["rotulo"] not in FORA]


def _arquivo(fid: str, nome: str, dur: int, primeira: bool) -> str:
    if not primeira:
        return f'<file id="{fid}"/>'
    url = "file://localhost" + urllib.parse.quote(os.path.join(BASE, nome))
    return (f'<file id="{fid}"><name>{nome}</name><pathurl>{url}</pathurl>'
            f'<rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate><duration>{dur}</duration>'
            f'<timecode><rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate><string>00:00:00:00</string><frame>0</frame>'
            f'<displayformat>NDF</displayformat></timecode>'
            f'<media><video><samplecharacteristics><rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate>'
            f'<width>1920</width><height>1080</height></samplecharacteristics></video></media></file>')


def _item(n: int, nome: str, fid: str, ini: int, fim: int, entrada: int, dur: int, primeira: bool) -> str:
    return (f'<clipitem id="clipitem-{n}"><name>{nome}</name><enabled>TRUE</enabled><duration>{dur}</duration>'
            f'<rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate><start>{ini}</start><end>{fim}</end>'
            f'<in>{entrada}</in><out>{entrada + fim - ini}</out>{_arquivo(fid, nome + ".mov" if not nome.endswith(".mov") else nome, dur, primeira)}'
            f'</clipitem>')


def xml() -> str:
    os.makedirs(TRAB, exist_ok=True)
    segs = segmentos()
    total = max(s["inicio"] + s["quadros"] for s in segs)
    v1 = _item(1, "B14_FUNDO", "file-fundo", 0, total, 0, 12 * 24, True)
    v2, primeira = [], True
    for n, s in enumerate(segs, start=2):
        v2.append(_item(n, "B14_FRENTE", "file-frente", s["inicio"], s["inicio"] + s["quadros"], 0, 6 * 24, primeira)
                  .replace("<name>B14_FRENTE</name>", f"<name>{s['rotulo']}</name>", 1))
        primeira = False
    corpo = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="sequence-1">'
             f'<duration>{total}</duration><rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate><name>BL07 MASCARA</name>'
             f'<media><video><format><samplecharacteristics><rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate>'
             f'<width>1920</width><height>1080</height></samplecharacteristics></format>'
             f'<track>{v1}</track><track>{"".join(v2)}</track></video></media>'
             f'<timecode><rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate><string>01:00:00:00</string>'
             f'<frame>86400</frame><displayformat>NDF</displayformat></timecode></sequence></xmeml>\n')
    with open(XML, "w", encoding="utf-8") as f:
        f.write(corpo)
    print(XML, len(segs), "segmentos na V2, total", total, "quadros")
    return XML


if __name__ == "__main__":
    {"xml": xml}[sys.argv[1]](*sys.argv[2:])

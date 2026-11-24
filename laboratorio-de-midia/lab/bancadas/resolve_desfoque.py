"""Bancada B20_DESFOQUE no Resolve — o Blur do Fusion (o mesmo plano que o De Lá Pra Cá escreve) em vários XBlurSize sobre
o degrau; render e largura 10–90 % por clipe.

    py -m lab.bancadas.resolve_desfoque          (Resolve Studio aberto; projeto atual)
"""
from __future__ import annotations

import json
import os
import sys
import time

from .. import desfoque_b20 as m
from ..gerar import RAIZ

R19 = r"C:\Users\USUARI~1\AppData\Local\Temp\claude\r19"
APP = r"D:\PROGRAMAS COM CLAUDE\2 ATIVOS\_DeLaPraCa\motor"
TRAB = os.path.join(RAIZ, "saida", "bancadas", "resolve", "B20_DESFOQUE")


def main() -> int:
    sys.path[:0] = [R19, APP]
    from rapi import resolve
    from drp import fusion_clipe
    os.makedirs(TRAB, exist_ok=True)
    r = resolve(); pr = r.GetProjectManager().GetCurrentProject(); mp = pr.GetMediaPool()
    arq = m.gerar(os.path.join(RAIZ, "saida", "base", "B20_DESFOQUE"))
    item = mp.ImportMedia([arq])[0]
    nome = "B20_DESFOQUE_" + time.strftime("%H%M%S")
    tl = mp.CreateEmptyTimeline(nome); pr.SetCurrentTimeline(tl)
    mp.AppendToTimeline([{"mediaPoolItem": item, "startFrame": 0, "endFrame": 11} for _ in m.VALORES_FUSION])
    itens = tl.GetItemListInTrack("video", 1)
    for it, v in zip(itens, m.VALORES_FUSION):
        pl = {"nos": [{"id": "Blur1", "tipo": "Blur", "entradas": {"XBlurSize": float(v)}}],
              "ligacoes": [["Blur1", "Input", "MediaIn1"], ["MediaOut1", "Input", "Blur1"]]}
        print(v, fusion_clipe.executar(it, pl))
    r.OpenPage("deliver"); time.sleep(1)
    pr.SetCurrentRenderFormatAndCodec("mov", "ProRes4444")
    pr.SetRenderSettings({"SelectAllFrames": True, "TargetDir": TRAB, "CustomName": "B20_RESOLVE", "ExportVideo": True,
                          "ExportAudio": False, "FormatWidth": 1920, "FormatHeight": 1080})
    job = pr.AddRenderJob(); pr.StartRendering(job)
    while pr.IsRenderingInProgress():
        time.sleep(2)
    pr.DeleteRenderJob(job); r.OpenPage("edit")
    saida = os.path.join(TRAB, "B20_RESOLVE.mov")
    res = [(v, round(m.medir(saida, quadro=i * 12 + 5), 2)) for i, v in enumerate(m.VALORES_FUSION)]
    print("XBlurSize → largura 10–90 % (px):", res)
    with open(os.path.join(TRAB, "medida.json"), "w", encoding="utf-8") as f:
        json.dump(res, f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

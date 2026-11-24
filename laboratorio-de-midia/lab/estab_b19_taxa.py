"""B19 em OUTRA taxa (2026-10-23): o mesmo tremor do `estab_b19` (definido em SEGUNDOS) gravado a `fps`, para separar
"σ em quadros" de "σ em segundos" no Stabilize do MC.   python -m lab.estab_b19_taxa 50"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from . import estab_b19 as B
from . import ffmpeg as ff


def gerar(fps_txt: str, saida: str) -> dict:
    num, den = (fps_txt.split("/") + ["1"])[:2]
    fps = int(num) / int(den)
    os.makedirs(saida, exist_ok=True)
    exe = ff.achar("ffmpeg")
    still = os.path.join(os.path.dirname(saida), "B19_ESTABILIZADOR", "B19_FONTE.png")
    nome = f"B19_TREMIDO_{fps_txt.replace('/', '_')}.mov"
    arq = os.path.join(saida, nome)
    ex = "(30*sin(2*PI*1.3*t)+12*sin(2*PI*3.1*t+1))"
    ey = "(20*sin(2*PI*0.8*t+0.5)+8*sin(2*PI*2.7*t))"
    ea = "(0.02*sin(2*PI*0.9*t+0.3))"
    filtro = (f"rotate=a='{ea}':fillcolor=black,"
              f"crop={B.W}:{B.H}:x='(iw-{B.W})/2+{ex}':y='(ih-{B.H})/2+{ey}'")
    if not os.path.exists(arq):
        subprocess.run([exe, "-v", "error", "-y", "-loop", "1", "-framerate", fps_txt, "-i", still,
                        "-t", str(B.SEGUNDOS), "-vf", filtro, "-c:v", "prores_ks", "-profile:v", "2",
                        "-pix_fmt", "yuv422p10le", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        arq], check=True)
    n = round(B.SEGUNDOS * fps)
    verdade = {"caso": "B19_ESTABILIZADOR", "fps": fps, "raster": [B.W, B.H], "arquivo": nome,
               "convencao": "a câmera: o recorte anda +dx/+dy px (a imagem vai para −dx/−dy) e gira ang rad (rotate do ffmpeg)",
               "quadros": [{"k": k, "dx": B.dx(k / fps), "dy": B.dy(k / fps), "ang": B.ang(k / fps)} for k in range(n)]}
    with open(os.path.join(saida, f"verdade_{fps_txt.replace('/', '_')}.json"), "w", encoding="utf-8") as f:
        json.dump(verdade, f, ensure_ascii=False, indent=1)
    return verdade


if __name__ == "__main__":
    from .gerar import RAIZ
    v = gerar(sys.argv[1] if len(sys.argv) > 1 else "50", os.path.join(RAIZ, "saida", "base", "B19_ESTABILIZADOR_TAXA"))
    print(v["arquivo"], len(v["quadros"]), "quadros")

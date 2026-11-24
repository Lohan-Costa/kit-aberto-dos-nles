"""B19_ESTABILIZADOR — o Warp Stabilizer do Premiere: o que ele grava no projeto, para levar ao Resolve.

Um quadro REAL (detalhe para o rastreamento) ampliado 1,5× e filmado por uma "câmera" que treme com movimento CONHECIDO:
deslocamento em x/y (duas senoides cada) e rotação (uma senoide), 1920×1080 a 23,976, 6 s. A verdade de cada quadro vai no
`verdade.json` — o estabilizador perfeito ("No Motion") desfaz exatamente isso.

    python -m lab.estab_b19          (gera o clipe e a verdade)
"""
from __future__ import annotations

import json
import math
import os
import subprocess

from . import ffmpeg as ff

FPS = 24000 / 1001
SEGUNDOS = 6
W, H = 1920, 1080
FONTE = os.path.join("D:/", "MIDIAS DE TESTES", "3 CONJUNTOS DOS APPS", "_CICLO ASSIST", "conformar", "03 CASOS", "REAL", "R04 PRODUCAO-C",
                     "ISOLADO", "MIDIA", "01_FOOTAGE", "DAY_1", "PRJ-0006-147-A1-1C4F.mov")
QUADRO_FONTE = 4736


def dx(t: float) -> float:
    return 30 * math.sin(2 * math.pi * 1.3 * t) + 12 * math.sin(2 * math.pi * 3.1 * t + 1)


def dy(t: float) -> float:
    return 20 * math.sin(2 * math.pi * 0.8 * t + 0.5) + 8 * math.sin(2 * math.pi * 2.7 * t)


def ang(t: float) -> float:
    """Rotação da câmera em radianos (~±1,1°)."""
    return 0.02 * math.sin(2 * math.pi * 0.9 * t + 0.3)


def gerar(saida: str) -> dict:
    os.makedirs(saida, exist_ok=True)
    exe = ff.achar("ffmpeg")
    still = os.path.join(saida, "B19_FONTE.png")
    if not os.path.exists(still):
        subprocess.run([exe, "-v", "error", "-y", "-i", FONTE, "-vf", rf"select=eq(n\,{QUADRO_FONTE}),scale=2880:1620",
                        "-frames:v", "1", still], check=True)
    arq = os.path.join(saida, "B19_TREMIDO.mov")
    # o mesmo movimento nas expressões do ffmpeg (t = tempo do quadro): gira em torno do centro e recorta o 1920×1080 do meio
    ex = "(30*sin(2*PI*1.3*t)+12*sin(2*PI*3.1*t+1))"
    ey = "(20*sin(2*PI*0.8*t+0.5)+8*sin(2*PI*2.7*t))"
    ea = "(0.02*sin(2*PI*0.9*t+0.3))"
    filtro = (f"rotate=a='{ea}':fillcolor=black,"
              f"crop={W}:{H}:x='(iw-{W})/2+{ex}':y='(ih-{H})/2+{ey}'")
    if not os.path.exists(arq):
        subprocess.run([exe, "-v", "error", "-y", "-loop", "1", "-framerate", "24000/1001", "-i", still,
                        "-t", str(SEGUNDOS), "-vf", filtro, "-c:v", "prores_ks", "-profile:v", "2",
                        "-pix_fmt", "yuv422p10le", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        arq], check=True)
    n = round(SEGUNDOS * FPS)
    verdade = {"caso": "B19_ESTABILIZADOR", "fps": FPS, "raster": [W, H], "arquivo": os.path.basename(arq),
               "convencao": "a câmera: o recorte anda +dx/+dy px (a imagem vai para −dx/−dy) e gira ang rad (rotate do ffmpeg)",
               "quadros": [{"k": k, "dx": dx(k / FPS), "dy": dy(k / FPS), "ang": ang(k / FPS)} for k in range(n)]}
    with open(os.path.join(saida, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(verdade, f, ensure_ascii=False, indent=1)
    return verdade


def main() -> int:
    from .gerar import RAIZ
    v = gerar(os.path.join(RAIZ, "saida", "base", "B19_ESTABILIZADOR"))
    print(v["arquivo"], len(v["quadros"]), "quadros")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

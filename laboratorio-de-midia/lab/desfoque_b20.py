"""B20_DESFOQUE — o Gaussian Blur do Premiere × o Blur do Fusion: quanto vale cada "Blurriness".

Uma placa 1920×1080 com um degrau vertical nítido (preto | branco) no meio e um horizontal: a largura da transição
(10–90 %) no render diz o tamanho do desfoque. O Premiere renderiza o efeito em vários valores; o Resolve, o Blur do
Fusion em vários XBlurSize; a razão entre os dois é o `BLUR_POR_PX` do De Lá Pra Cá (hoje 0,2, de um caso só).

    python -m lab.desfoque_b20          (gera a placa)
"""
from __future__ import annotations

import os
import subprocess

import numpy as np

from . import ffmpeg as ff

W, H = 1920, 1080
VALORES_PREMIERE = [5, 10, 20, 40, 60, 100]
VALORES_FUSION = [1, 2, 4, 8, 12, 16, 24]


def gerar(saida: str) -> str:
    os.makedirs(saida, exist_ok=True)
    arq = os.path.join(saida, "B20_DEGRAU.mov")
    if not os.path.exists(arq):
        # metade esquerda preta, direita branca; faixa horizontal branca no terço de cima (o degrau vertical também)
        filtro = (f"color=c=black:s={W}x{H}:r=24000/1001:d=2[a];color=c=white:s={W // 2}x{H}:r=24000/1001:d=2[b];"
                  f"[a][b]overlay=x={W // 2}:y=0[c];color=c=gray:s={W}x{H // 6}:r=24000/1001:d=2[d];[c][d]overlay=x=0:y={H // 3}")
        subprocess.run([ff.achar("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", filtro, "-c:v", "prores_ks", "-profile:v", "4",
                        "-pix_fmt", "yuv444p10le", arq], check=True)
    return arq


def largura(linha: np.ndarray) -> float:
    """Largura 10–90 % do degrau numa linha de luma (o degrau do meio, preto → branco)."""
    v = linha.astype(float)
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    t10, t90 = lo + 0.1 * (hi - lo), lo + 0.9 * (hi - lo)
    meio = len(v) // 2
    janela = v[meio - 400:meio + 400]
    i10 = np.argmax(janela >= t10); i90 = np.argmax(janela >= t90)
    def frac(i, t):          # interpolação entre i−1 e i
        a, b = janela[i - 1], janela[i]
        return i - 1 + (t - a) / (b - a) if b != a else float(i)
    return frac(i90, t90) - frac(i10, t10)


def medir(arq: str, quadro: int = 10, y: int = 900) -> float:
    d = subprocess.run([ff.achar("ffmpeg"), "-v", "error", "-i", arq, "-vf", rf"select=eq(n\,{quadro})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray16le", "-"], capture_output=True, check=True).stdout
    img = np.frombuffer(d, "<u2").reshape(H, W)
    return largura(img[y])


def main() -> int:
    from .gerar import RAIZ
    arq = gerar(os.path.join(RAIZ, "saida", "base", "B20_DESFOQUE"))
    print(arq, "largura do degrau sem desfoque: %.2f px" % medir(arq))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

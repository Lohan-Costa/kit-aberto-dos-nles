"""B24_COR_MC — medir: a média de Y'CbCr (8 bits, como o arquivo está) no MIOLO de cada área da carta.

    python -m lab.cor_b24_medir <arquivo> [quadro]   → JSON {id: [Y, Cb, Cr], …} + o degradê (Y por coluna)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

from . import ffmpeg as ff
from .cor_b24 import SAIDA, W, H


def quadro_yuv(arquivo: str, n: int = 24) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """O quadro `n` em Y'CbCr 4:4:4 de 16 bits (sem conversão de cor; o croma 4:2:2 só duplicado)."""
    cmd = [ff.achar("ffmpeg"), "-v", "error", "-i", arquivo, "-vf", rf"select=eq(n\,{n}),format=yuv444p16le",
           "-frames:v", "1", "-f", "rawvideo", "-"]
    b = subprocess.run(cmd, capture_output=True, check=True, **ff.SEM_JANELA).stdout
    a = np.frombuffer(b, dtype="<u2").reshape(3, H, W).astype(np.float64) / 256.0   # escala de 8 bits
    return a[0], a[1], a[2]


def medir(arquivo: str, n: int = 24) -> dict:
    with open(os.path.join(SAIDA, "verdade.json"), encoding="utf-8") as f:
        v = json.load(f)
    y, cb, cr = quadro_yuv(arquivo, n)
    out = {}
    for ar in v["areas"]:
        x0, y0, x1, y1 = ar["ret"]
        mx, my = (x1 - x0) // 5, (y1 - y0) // 5
        sl = (slice(y0 + my, y1 - my), slice(x0 + mx, x1 - mx))
        out[ar["id"]] = [round(float(c[sl].mean()), 3) for c in (y, cb, cr)]
    x0, y0, x1, y1 = v["degrade"]["ret"]
    out["_degrade_Y"] = [round(float(c), 3) for c in y[y0 + 20:y1 - 20, x0:x1].mean(axis=0)]
    return out


if __name__ == "__main__":
    print(json.dumps(medir(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 24)))

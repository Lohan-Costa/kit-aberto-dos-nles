"""PRODUCAO-H LAB — a medida: o still COM a grade × o still SEM a grade (mesma timeline duplicada, grades zeradas).

Mesma geometria e mesma gestão de cor nas duas: a diferença por pixel é só a grade do colorista. Por clipe (o quadro do
meio), separa:
- **força**: |com − sem| médio e p95, em código de 8 bits;
- **global**: uma LUT 3D (17³) ajustada pelos próprios pares de pixels (o `sem` → a média do `com` em cada célula) — o
  que um Lumetri/LUT reproduziria;
- **espacial**: o resíduo |com − LUT(sem)| — o que NENHUMA LUT reproduz (janela, Halation, NR, qualificador com blur).
  Resíduo alto ⇒ a tradução precisa de máscara/efeito, não só de cor.

    python -m lab.bancadas.resolve_felipe_ret_medir
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

from .resolve_felipe_ret import STILLS, TRABALHO

N = 17


def ler_png(caminho: str) -> np.ndarray:
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True).stdout
    w, h = (int(x) for x in subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", caminho],
        capture_output=True, text=True, check=True).stdout.strip().split(","))
    return np.frombuffer(b, np.uint8).reshape(h, w, 3).astype(np.float32)


def medir_par(com: np.ndarray, sem: np.ndarray) -> dict:
    d = np.abs(com - sem).max(axis=2)
    s = sem.reshape(-1, 3)
    c = com.reshape(-1, 3)
    idx = np.clip((s / 255 * (N - 1)).round().astype(int), 0, N - 1)
    chave = (idx[:, 0] * N + idx[:, 1]) * N + idx[:, 2]
    soma = np.zeros((N ** 3, 3))
    cont = np.bincount(chave, minlength=N ** 3).astype(float)
    for k in range(3):
        soma[:, k] = np.bincount(chave, weights=c[:, k], minlength=N ** 3)
    lut = soma / np.maximum(cont, 1)[:, None]
    resid = np.abs(c - lut[chave]).max(axis=1).reshape(com.shape[:2])
    return {"forca_media": round(float(d.mean()), 2), "forca_p95": round(float(np.percentile(d, 95)), 1),
            "espacial_media": round(float(resid.mean()), 2), "espacial_p95": round(float(np.percentile(resid, 95)), 1),
            "espacial_area_5": round(float((resid > 5).mean()), 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    quadros = json.load(open(os.path.join(TRABALHO, "quadros.json"), encoding="utf-8"))
    grades = {}
    gpath = os.path.join(TRABALHO, "grades_v01_v05.json")
    if os.path.exists(gpath):
        grades = json.load(open(gpath, encoding="utf-8"))
    res = {}
    for tl in ("20260224_MTFR_CORTE_03_COLOR_v05", "20260224_MTFR_CORTE_03_CONFORM_OK"):
        linhas = []
        for q in quadros[tl]:
            f = f"{q['frame']:06d}.png"
            a, b = os.path.join(STILLS, tl, f), os.path.join(STILLS, tl + " SEM COR", f)
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            m = medir_par(ler_png(a), ler_png(b))
            linhas.append({"frame": q["frame"], "trilha": q["trilha"], "nome": q["nome"], **m})
        res[tl] = linhas
        fm = np.array([l["forca_media"] for l in linhas])
        em = np.array([l["espacial_media"] for l in linhas])
        print(f"{tl[23:]}: {len(linhas)} quadros · força média {fm.mean():.1f} (p50 {np.median(fm):.1f}) · "
              f"espacial média {em.mean():.2f} · quadros com espacial > 2: {(em > 2).sum()}", flush=True)
    with open(os.path.join(TRABALHO, "medidas.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

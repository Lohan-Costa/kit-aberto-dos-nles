"""B24_COR_MC — a CARTA de cor para medir o Color Correction do Media Composer (2026-11-20, pedido do autor).

Um quadro parado (1920×1080, 23,976, 5 s) com áreas de cor CONHECIDA, para medir o que cada controle do Color
Correction faz ao pixel (a entrada é a área, a saída é a mesma área depois do efeito):

- linha A: 33 degraus de cinza, de 0 a 255 (RGB cheio);
- linhas B e C: 24 matizes a cada 15°, saturação 0,5 e 0,25 (valor 0,6 e 0,8) — o Hue e o Sat se medem aqui;
- linha D: as 6 primárias/secundárias a 75 % e a 40 %;
- linha E: um degradê cinza contínuo de 0 a 1 na largura toda (a curva sem degrau).

O .mov é ProRes 422 HQ (10 bits, BT.709, faixa de vídeo): o MC importa e converte ao formato do projeto. A verdade
(`verdade.json`) traz o retângulo e o RGB de cada área; a medição usa o MIOLO (60 %) de cada uma.

    python -m lab.cor_b24          (gera em saida/base/B24_COR_MC)
"""
from __future__ import annotations

import colorsys
import json
import os
import subprocess

import numpy as np

from . import ffmpeg as ff

W, H = 1920, 1080
FPS = "24000/1001"
SEGUNDOS = 5
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "saida", "base", "B24_COR_MC")
NOME = "B24_CARTA_COR.mov"


def _areas() -> list[dict]:
    a = []
    # A: 33 degraus de cinza, 56 px cada
    for i in range(33):
        v = round(i * 255 / 32)
        x0 = 36 + i * 56
        a.append({"id": f"cinza_{i:02d}", "linha": "A", "ret": [x0, 60, x0 + 52, 200], "rgb": [v, v, v]})
    # B, C: 24 matizes
    for linha, (s, val), y0 in (("B", (0.5, 0.6), 240), ("C", (0.25, 0.8), 400)):
        for i in range(24):
            r, g, b = colorsys.hsv_to_rgb(i / 24, s, val)
            x0 = 36 + i * 77
            a.append({"id": f"matiz{linha}_{i * 15:03d}", "linha": linha, "ret": [x0, y0, x0 + 72, y0 + 120],
                      "hsv": [i * 15, s, val], "rgb": [round(r * 255), round(g * 255), round(b * 255)]})
    # D: primárias e secundárias a 75 % e 40 %
    cores = {"R": (1, 0, 0), "Y": (1, 1, 0), "G": (0, 1, 0), "C": (0, 1, 1), "B": (0, 0, 1), "M": (1, 0, 1)}
    k = 0
    for nivel in (0.75, 0.40):
        for nome, (r, g, b) in cores.items():
            x0 = 36 + k * 154
            a.append({"id": f"{nome}{round(nivel * 100)}", "linha": "D", "ret": [x0, 560, x0 + 146, 700],
                      "rgb": [round(r * nivel * 255), round(g * nivel * 255), round(b * nivel * 255)]})
            k += 1
    return a


DEGRADE = [36, 760, 1884, 1040]   # linha E: 0 em x0, 1 em x1 (RGB cheio)


def quadro() -> np.ndarray:
    """O quadro em RGB 16 bits (fundo cinza 18 %, 46 de 255)."""
    img = np.full((H, W, 3), 46 * 257, dtype=np.uint16)
    for ar in _areas():
        x0, y0, x1, y1 = ar["ret"]
        img[y0:y1, x0:x1] = np.array(ar["rgb"], dtype=np.uint16) * 257
    x0, y0, x1, y1 = DEGRADE
    rampa = np.linspace(0, 65535, x1 - x0).round().astype(np.uint16)
    img[y0:y1, x0:x1] = rampa[None, :, None]
    return img


def gerar() -> str:
    os.makedirs(SAIDA, exist_ok=True)
    saida = os.path.join(SAIDA, NOME)
    cmd = [ff.achar("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}", "-r", FPS, "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le",
           "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
           "-timecode", "01:00:00:00", "-t", str(SEGUNDOS), saida]
    q = quadro().tobytes()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, **ff.SEM_JANELA)
    n = round(SEGUNDOS * 24000 / 1001) + 1
    for _ in range(n):
        p.stdin.write(q)
    p.stdin.close()
    err = p.stderr.read().decode("utf-8", "replace")
    if p.wait() != 0:
        raise RuntimeError(err)
    verdade = {"caso": "B24_COR_MC", "arquivo": NOME, "w": W, "h": H, "fps": FPS, "fundo_rgb": [46, 46, 46],
               "codificacao": "ProRes 422 HQ, yuv422p10le, BT.709, faixa de vídeo (RGB cheio 0-255 → Y 64-940)",
               "areas": _areas(), "degrade": {"ret": DEGRADE, "de": 0.0, "ate": 1.0}}
    with open(os.path.join(SAIDA, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(verdade, f, ensure_ascii=False, indent=1)
    return saida


if __name__ == "__main__":
    print(gerar())

"""Charts NO LUGAR da mídia de um projeto real (2026-11-20, pedido do autor: medir a cor do PRODUCAO-H sem as mídias).

Para cada mídia do projeto, um chart com o MESMO formato (resolução, PAR, taxa, TC de início, duração ou trecho): a
carta B24 (`lab/cor_b24.py`: 33 cinzas, 24 matizes em duas saturações, primárias a 75/40 %, degradê) escalada ao
quadro, e o NÚMERO DO QUADRO DA FONTE num código de barras de 20 bits (o ffmpeg do Mac não tem `drawtext`): cada bit
é uma caixa acesa (RGB 255) ou apagada (o fundo, 46), da direita para a esquerda, com uma caixa sempre acesa e uma
sempre preta antes, para o limiar. `ler_quadro()` lê o número de volta de um quadro renderizado.

    python -m lab.cor_charts_reais NOME W H FPS TC_INICIO PRIMEIRO N SAIDA.mov [--par 1.0] [--codec prores|hevc]

PRIMEIRO = o quadro da FONTE que o chart começa (0 = o início do arquivo original); o TC do chart = TC_INICIO + PRIMEIRO.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from fractions import Fraction

import numpy as np

from . import cor_b24
from . import ffmpeg as ff
from . import fonte_pixel

BITS = 20
NTSC = {"23.976": "24000/1001", "29.97": "30000/1001", "59.94": "60000/1001", "47.952": "48000/1001"}
FAIXA = (705, 755)          # a faixa vazia entre a linha D e a E da carta B24, em px de 1080


def _tc_para_quadros(tc: str, fps: Fraction) -> int:
    h, m, s, f = (int(x) for x in tc.replace(";", ":").split(":"))
    base = round(fps)
    return ((h * 60 + m) * 60 + s) * base + f


def _quadros_para_tc(n: int, fps: Fraction) -> str:
    base = round(fps)
    f = n % base
    s = n // base
    return f"{s // 3600 % 24:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"


def caixas(w: int, h: int) -> dict:
    """Onde ficam as caixas do código (px do quadro w×h): a de referência acesa, a preta e os BITS bits."""
    y0, y1 = round(FAIXA[0] * h / 1080), round(FAIXA[1] * h / 1080)
    lado = max(4, round((y1 - y0)))
    passo = round(lado * 1.25)
    x_fim = round(1884 * w / 1920)
    bits = [(x_fim - (k + 1) * passo, y0, lado, lado) for k in range(BITS)]
    x_ref = bits[-1][0] - 3 * passo
    return {"aceso": (x_ref, y0, lado, lado), "preto": (x_ref + passo, y0, lado, lado), "bits": bits}


def quadro(w: int, h: int, rotulo: str) -> np.ndarray:
    """A carta B24 escalada ao quadro w×h (RGB 16 bits), com o rótulo e as caixas de referência."""
    base = cor_b24.quadro()
    ys = np.minimum((np.arange(h) * 1080 / h).astype(int), 1079)
    xs = np.minimum((np.arange(w) * 1920 / w).astype(int), 1919)
    img = base[ys][:, xs].copy()
    # o degradê recalculado na largura nova (sem degrau do vizinho mais próximo)
    x0, y0, x1, y1 = cor_b24.DEGRADE
    X0, X1 = round(x0 * w / 1920), round(x1 * w / 1920)
    Y0, Y1 = round(y0 * h / 1080), round(y1 * h / 1080)
    img[Y0:Y1, X0:X1] = np.linspace(0, 65535, X1 - X0).round().astype(np.uint16)[None, :, None]
    cx = caixas(w, h)
    x, y, l, a = cx["aceso"]
    img[y:y + a, x:x + l] = 65535
    x, y, l, a = cx["preto"]
    img[y:y + a, x:x + l] = 0
    esc = max(1, round(2 * h / 1080))
    texto = "".join(c for c in rotulo.upper() if c in fonte_pixel._GLIFOS or c == " ")[:30]
    for rx, ry, rl, ra in fonte_pixel.retangulos(texto, round(36 * w / 1920), round(FAIXA[0] * h / 1080), esc):
        img[ry:ry + ra, rx:rx + rl] = 50000
    return img


def _filtro_bits(w: int, h: int, primeiro: int) -> str:
    fs = []
    for k, (x, y, l, a) in enumerate(caixas(w, h)["bits"]):
        fs.append(f"drawbox=x={x}:y={y}:w={l}:h={a}:color=white:t=fill:"
                  f"enable='eq(mod(floor((n+{primeiro})/{2 ** k}),2),1)'")
    return ",".join(fs)


def gerar(nome: str, w: int, h: int, fps: str, tc_inicio: str, primeiro: int, n: int, saida: str,
          par: float = 1.0, codec: str = "prores") -> dict:
    fr = Fraction(NTSC.get(str(fps), str(fps)))
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    png = saida + ".quadro.png"
    raw = quadro(w, h, nome)
    subprocess.run([ff.achar("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
                    "-pix_fmt", "rgb48le", "-s", f"{w}x{h}", "-i", "-", png],
                   input=raw.tobytes(), check=True, **ff.SEM_JANELA)
    tc = _quadros_para_tc(_tc_para_quadros(tc_inicio, fr) + primeiro, fr)
    sar = Fraction(par).limit_denominator(10000)
    if codec == "hevc":
        # o PNG decodificado UMA vez e repetido no filtro; HEVC 10 bits 4:2:2 pelo VideoToolbox (Mac): um quadro
        # parado quase não ocupa (6K: 480 quadros ~10 MB, 38 qps num M4). O Resolve casa a troca pelo TC.
        vf = (f"scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le,loop=loop={n - 1}:size=1,"
              f"setpts=N/({fr.numerator}/{fr.denominator})/TB,{_filtro_bits(w, h, primeiro)},"
              f"setsar={sar.numerator}/{sar.denominator},format=p210le")
        enc = ["-c:v", "hevc_videotoolbox", "-profile:v", "main42210", "-b:v", "40M", "-tag:v", "hvc1"]
        entrada = ["-framerate", str(fr), "-i", png]
    else:
        vf = (f"{_filtro_bits(w, h, primeiro)},setsar={sar.numerator}/{sar.denominator},"
              "scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le")
        enc = ["-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0"]
        entrada = ["-loop", "1", "-framerate", str(fr), "-i", png, "-frames:v", str(n)]
    script = saida + ".filtro.txt"
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(vf)
    cmd = [ff.achar("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", *entrada, "-filter_script:v", script, *enc,
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
           "-timecode", tc, "-r", str(fr), saida]
    subprocess.run(cmd, check=True, **ff.SEM_JANELA)
    os.remove(png)
    os.remove(script)
    v = {"nome": nome, "arquivo": os.path.basename(saida), "w": w, "h": h, "fps": str(fr), "par": par,
         "tc_inicio_original": tc_inicio, "primeiro": primeiro, "n": n, "tc_do_chart": tc,
         "caixas": caixas(w, h), "carta": "lab/cor_b24.py escalada (areas em px de 1920x1080 × w/1920, h/1080)"}
    with open(saida + ".verdade.json", "w", encoding="utf-8") as fh:
        json.dump(v, fh, ensure_ascii=False, indent=1)
    return v


def ler_quadro(img: np.ndarray, w: int | None = None, h: int | None = None) -> int | None:
    """O número do quadro da fonte num quadro renderizado (array H×W×3, qualquer profundidade). None se ilegível.
    `w`/`h` = o formato do CHART (onde estão as caixas); sem eles, o do próprio quadro."""
    H, W = img.shape[:2]
    w, h = w or W, h or H
    sx, sy = W / w, H / h

    def miolo(c):
        x, y, l, a = c
        x0, y0 = int((x + l * 0.3) * sx), int((y + a * 0.3) * sy)
        x1, y1 = max(x0 + 1, int((x + l * 0.7) * sx)), max(y0 + 1, int((y + a * 0.7) * sy))
        return float(img[y0:y1, x0:x1].mean())

    cx = caixas(w, h)
    alto, baixo = miolo(cx["aceso"]), miolo(cx["preto"])
    if alto - baixo < 1e-6:
        return None
    lim = (alto + baixo) / 2
    return sum((1 << k) for k, c in enumerate(cx["bits"]) if miolo(c) > lim)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    for a in ("nome", "w", "h", "fps", "tc_inicio", "primeiro", "n", "saida"):
        ap.add_argument(a)
    ap.add_argument("--par", type=float, default=1.0)
    ap.add_argument("--codec", default="prores")
    a = ap.parse_args()
    print(json.dumps(gerar(a.nome, int(a.w), int(a.h), a.fps, a.tc_inicio, int(a.primeiro), int(a.n), a.saida,
                           a.par, a.codec), ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()

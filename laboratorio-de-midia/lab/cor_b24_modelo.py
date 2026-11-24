"""B24_COR_MC — o MODELO do Color Correction do MC (Base HSL, Master), ajustado às medidas da varredura.

Tudo em Y'CbCr de 8 bits (códigos 0–255, preto 16, branco 235, croma centrado em 128), BT.709. Cada controle é uma
função (y, cb, cr) → (y, cb, cr); o resultado final é cortado em 0–255 (medido: o MC não corta em RGB nem em 16–235).
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

KR, KB = 0.2126, 0.0722
KG = 1 - KR - KB


def para_rgb(y, cb, cr):
    r = y + 2 * (1 - KR) * (cr - 128)
    b = y + 2 * (1 - KB) * (cb - 128)
    g = (y - KR * r - KB * b) / KG
    return r, g, b


def de_rgb(r, g, b):
    y = KR * r + KG * g + KB * b
    return y, 128 + (b - y) / (2 * (1 - KB)), 128 + (r - y) / (2 * (1 - KR))


def aplicar(nome, v, y, cb, cr, k=None):
    k = k or {}
    if nome == "Mas Sat":
        s = v / 100
        return y, 128 + (cb - 128) * s, 128 + (cr - 128) * s
    if nome == "Mas Hue":
        a = math.radians(-v)
        x, z = cb - 128, cr - 128
        return y, 128 + x * math.cos(a) - z * math.sin(a), 128 + x * math.sin(a) + z * math.cos(a)
    if nome == "Mas Brt":
        return y + v * k.get("brt", 1.0), cb, cr
    if nome == "Mas Setup":
        return y + v * k.get("setup", 1.0), cb, cr
    if nome == "Mas Gain":
        g = v / 100
        return 16 + (y - 16) * g, 128 + (cb - 128) * g, 128 + (cr - 128) * g
    if nome == "Mas Contrast":
        s = math.tan(math.pi / 4 * (1 + v / 100))
        p = k.get("pivo", 125.5)
        return p + (y - p) * s, 128 + (cb - 128) * s, 128 + (cr - 128) * s
    if nome == "Mas Gamma":
        r, g, b = para_rgb(y, cb, cr)
        def gm(c):
            t = (c - 16) / 219
            return 16 + 219 * math.copysign(abs(t) ** (1 / v), t)
        return de_rgb(gm(r), gm(g), gm(b))
    raise KeyError(nome)


def cortar(c):
    return min(255.0, max(0.0, c))


def avaliar(medidas, k=None, mostrar=False):
    base = medidas[0]["medida"]
    por = {}
    for r in medidas[1:-1]:
        (nome, v), = r["caso"].items()
        erros = []
        for area, val in base.items():
            if area.startswith("_"):
                continue
            y, cb, cr = val
            prev = [cortar(c) for c in aplicar(nome, v, y, cb, cr, k)]
            med = r["medida"][area]
            erros.append(max(abs(a - b) for a, b in zip(prev, med)))
        e = np.array(erros)
        por.setdefault(nome, []).append((v, round(float(e.mean()), 2), round(float(e.max()), 2)))
    if mostrar:
        for n, l in por.items():
            print(f"{n:13s}", "  ".join(f"{v}: média {m} máx {x}" for v, m, x in l))
    return por


if __name__ == "__main__":
    med = json.load(open(sys.argv[1], encoding="utf-8"))
    # ajuste dos 3 números livres (brilho, setup, pivô) por varredura simples
    melhor = {}
    for chave, nome, faixa in (("brt", "Mas Brt", np.arange(1.0, 1.3, 0.001)),
                               ("setup", "Mas Setup", np.arange(0.9, 1.1, 0.001)),
                               ("pivo", "Mas Contrast", np.arange(120, 132, 0.05))):
        def custo(x):
            return sum(m for v, m, _ in avaliar(med, {chave: x})[nome])
        x = min(faixa, key=custo)
        melhor[chave] = round(float(x), 3)
    print("ajuste:", melhor)
    avaliar(med, melhor, mostrar=True)


# ── a CURVA (Curves › Master), medida em 2026-11-20 (`COR_CURVA`, `COR_ORDEM`) ────────────────────────────────────────
#: o blob `Curves Master` (CFUserParam) = 16 pares (x, y) em double LE; vale o `Num Master Curve Keys`. 256 = 0, 766 = 1.
CURVA_0, CURVA_1 = 256.0, 766.0


def pontos_do_blob(dados: bytes, n: int) -> list[tuple[float, float]]:
    import struct
    v = struct.unpack("<32d", bytes(dados)[:256])
    return [((v[2 * i] - CURVA_0) / (CURVA_1 - CURVA_0), (v[2 * i + 1] - CURVA_0) / (CURVA_1 - CURVA_0)) for i in range(n)]


def curva(pontos, y, cb, cr):
    """A curva Master: em CADA canal R'G'B', no domínio do CÓDIGO inteiro (t = c/255, não 16–235), interpolada por
    Catmull-Rom (tangente = secante dos vizinhos; nas pontas, a do segmento), plana fora das pontas."""
    from .cor_curva import catmull, linear
    f = catmull(pontos) if len(pontos) > 2 else linear(pontos)
    return de_rgb(*[float(255 * f(min(1.0, max(0.0, c / 255)))) for c in para_rgb(y, cb, cr)])

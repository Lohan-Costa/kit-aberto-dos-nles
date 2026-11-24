"""O quadro que se identifica sozinho (organograma aprovado em 2026-10-06).

- **Faixa de cima:** o número do quadro NO ARQUIVO, contado a partir de 0 na ordem de decodificação,
  em 24 bits (bit 0 à esquerda; aceso = branco). Mesmo princípio do `gerar_taxas.py` do De Lá Pra Cá.
- **Faixa de baixo:** o TC em quadros desde a meia-noite, 24 bits (24 h a 60 q/s = 5.184.000 < 2²⁴).
- **Fundo na cor da câmera**, grade, cantos, cruz e círculo: denunciam escala, posição, recorte e
  distorção (o círculo vira elipse num Stretch). O quadrado cheio no canto de cima à esquerda denuncia
  espelhamento e rotação.
- **Texto:** câmera e take, o TC e o número do quadro em dígitos de 7 segmentos (mudam a cada quadro),
  taxa, raster, caso e perfil — tudo em `drawbox` (ver `fonte_pixel.py`: o ffmpeg do Mac não tem
  `drawtext`).

Tudo é feito pelo ffmpeg num passe só, no `filter_complex`; o `n` do `enable` é o número do quadro.
"""
from __future__ import annotations

from fractions import Fraction

from . import fonte_pixel

BITS = 24

#: CAM 1 azul, CAM 2 âmbar, CAM 3 verde, CAM 4 magenta — escuras o bastante para o texto branco
#: passar no piso de contraste (branco sobre elas ≥ 4,5:1).
CORES_CAMERA = {1: "0x1F3F7A", 2: "0x7A4A00", 3: "0x1E5E2E", 4: "0x6E1F5E"}
COR_APAGADO = "0x202020"
COR_ACESO = "white"


def unidade(w: int, h: int) -> float:
    """Tamanhos seguem o lado MENOR: no 9:16 o texto cabe na largura."""
    return min(w, h) / 1080


def faixas(w: int, h: int) -> dict:
    """Onde ficam as duas faixas de código — o leitor (`ler.py`) usa a mesma conta."""
    alt = max(8, round(80 * unidade(w, h)))
    celulas = [(round(b * w / BITS), round((b + 1) * w / BITS)) for b in range(BITS)]
    return {"altura": alt, "celulas": celulas, "y_quadro": (0, alt), "y_tc": (h - alt, h)}


def _esc(expr: str) -> str:
    """Expressão dentro de opção de filtro: vírgula escapada e tudo entre aspas simples."""
    return "'" + expr.replace(",", "\\,") + "'"


def _box(x, y, w, h, cor, enable: str | None = None) -> str:
    s = f"drawbox=x={int(x)}:y={int(y)}:w={max(1, int(w))}:h={max(1, int(h))}:color={cor}:t=fill"
    return s + (f":enable={_esc(enable)}" if enable else "")


def _faixa(w: int, h: int, y0: int, y1: int, valor: str) -> list[str]:
    f = faixas(w, h)
    partes = [_box(0, y0, w, y1 - y0, COR_APAGADO)]
    for b, (x0, x1) in enumerate(f["celulas"]):
        partes.append(_box(x0, y0, x1 - x0, y1 - y0, COR_ACESO, f"mod(floor(({valor})/{2 ** b}),2)"))
    return partes


# segmentos acesos por algarismo (a b c d e f g)
_SEGMENTOS = {
    "a": (0, 2, 3, 5, 6, 7, 8, 9), "b": (0, 1, 2, 3, 4, 7, 8, 9), "c": (0, 1, 3, 4, 5, 6, 7, 8, 9),
    "d": (0, 2, 3, 5, 6, 8, 9), "e": (0, 2, 6, 8), "f": (0, 4, 5, 6, 8, 9), "g": (2, 3, 4, 5, 6, 8, 9),
}


def _digito(x: int, y: int, w: int, h: int, valor: str) -> list[str]:
    """Um algarismo de 7 segmentos que mostra `valor` (expressão 0–9). Apagados ficam visíveis, fracos,
    como num display de TC."""
    k = max(2, round(w * 0.2))
    meia = h // 2
    v = (meia - k - k // 2)
    geo = {"a": (x + k, y, w - 2 * k, k), "b": (x + w - k, y + k, k, v), "c": (x + w - k, y + meia + k // 2, k, v),
           "d": (x + k, y + h - k, w - 2 * k, k), "e": (x, y + meia + k // 2, k, v), "f": (x, y + k, k, v),
           "g": (x + k, y + meia - k // 2, w - 2 * k, k)}
    partes = [_box(*geo[s], "white@0.10") for s in "abcdefg"]
    for s, acesos in _SEGMENTOS.items():
        cond = "+".join(f"eq({valor},{d})" for d in acesos)
        partes.append(_box(*geo[s], COR_ACESO, cond))
    return partes


def _dois_pontos(x: int, y: int, w: int, h: int) -> list[str]:
    k = max(2, round(w * 0.5))
    cx = x + (w - k) // 2
    return [_box(cx, y + h * 3 // 10 - k // 2, k, k, COR_ACESO), _box(cx, y + h * 7 // 10 - k // 2, k, k, COR_ACESO)]


def _texto(texto: str, x: int, y: int, escala: int) -> list[str]:
    return [_box(rx, ry, rw, rh, COR_ACESO) for rx, ry, rw, rh in fonte_pixel.retangulos(texto, x, y, escala)]


def _texto_centrado(texto: str, w: int, y: int, escala: int) -> list[str]:
    return _texto(texto, (w - fonte_pixel.largura(texto, escala)) // 2, y, escala)


def _ponto_e_virgula(x: int, y: int, w: int, h: int) -> list[str]:
    """O separador do drop-frame (`;`): o ponto de cima e, embaixo, ponto com rabicho."""
    k = max(2, round(w * 0.5))
    cx = x + (w - k) // 2
    return [_box(cx, y + h * 3 // 10 - k // 2, k, k, COR_ACESO), _box(cx, y + h * 7 // 10 - k // 2, k, k, COR_ACESO),
            _box(cx + k // 3, y + h * 7 // 10 + k // 2, k * 2 // 3, k, COR_ACESO)]


def filtro(*, w: int, h: int, fps: Fraction, quadros: int, tc_inicio_q: int, base: int,
           camera: int, take: int, linhas: list[str], pix_fmt: str, saida: str = "v", df: bool = False,
           sar: str | None = None) -> str:
    """O `filter_complex` do vídeo, terminando em `[saida]`. `linhas` = o texto fixo de baixo
    (taxa e raster, caso e perfil). `tc_inicio_q` é a contagem REAL desde a meia-noite (com `df`, a do
    drop-frame); o que se desenha é o RÓTULO (`tc.rotulo`), que no drop-frame pula números."""
    from . import tc as _tc
    u = unidade(w, h)
    cor = CORES_CAMERA[camera]
    T = _tc.rotulo_ffmpeg(f"({tc_inicio_q}+n)", base, df)

    # fundo fixo: um quadro só com o círculo (geq é lento; feito uma vez e repetido pelo loop)
    raio, esp = round(0.30 * h if h <= w else 0.30 * w), max(2, round(3 * u))
    anel = f"between(hypot(X-{w / 2},Y-{h / 2}),{raio - esp},{raio + esp})"
    cadeia = [
        f"color=c={cor}:s={w}x{h}:r={fps.numerator}/{fps.denominator}", "trim=end_frame=1", "format=yuv444p",
        f"geq=lum={_esc(f'if({anel},235,lum(X,Y))')}:cb={_esc('cb(X,Y)')}:cr={_esc('cr(X,Y)')}",
        f"loop=loop={quadros - 1}:size=1:start=0", f"setpts=N/({fps.numerator}/{fps.denominator})/TB",
    ]
    passo = max(8, round(120 * u))
    cadeia.append(f"drawgrid=x={(w // 2) % passo}:y={(h // 2) % passo}:w={passo}:h={passo}"
                  f":t={max(1, round(2 * u))}:c=white@0.25")

    f = faixas(w, h)
    alt = f["altura"]
    # cantos (em L) dentro da área útil, quadrado cheio só no de cima à esquerda; cruz no centro
    L, t = round(70 * u), max(2, round(6 * u))
    m = round(16 * u)
    for cx, cy, sx, sy in ((m, alt + m, 1, 1), (w - m, alt + m, -1, 1), (m, h - alt - m, 1, -1), (w - m, h - alt - m, -1, -1)):
        x0 = cx if sx > 0 else cx - L
        y0 = cy if sy > 0 else cy - t
        cadeia.append(_box(x0, y0, L, t, COR_ACESO))
        x1 = cx if sx > 0 else cx - t
        y1 = cy if sy > 0 else cy - L
        cadeia.append(_box(x1, y1, t, L, COR_ACESO))
    q = round(28 * u)
    cadeia.append(_box(m + t + round(8 * u), alt + m + t + round(8 * u), q, q, COR_ACESO))
    c = round(30 * u)
    cadeia += [_box(w // 2 - c, h // 2 - 1, 2 * c, 2, COR_ACESO), _box(w // 2 - 1, h // 2 - c, 2, 2 * c, COR_ACESO)]

    # o bloco de texto, centrado, sobre um painel escuro translúcido
    esc_cam, esc_info = max(2, round(7 * u)), max(2, round(4 * u))
    dig_w, dig_h, gap, dp = round(80 * u), round(160 * u), round(22 * u), round(36 * u)
    fq_w, fq_h, fq_gap = round(40 * u), round(80 * u), round(12 * u)
    esp_l = round(30 * u)
    alturas = [7 * esc_cam, dig_h, fq_h] + [7 * esc_info] * len(linhas)
    total = sum(alturas) + esp_l * (len(alturas) - 1)
    y = (h - total) // 2
    larg_tc = 8 * dig_w + 10 * gap + 3 * dp
    painel_w = min(w - 2 * m, larg_tc + round(120 * u))
    cadeia.append(_box((w - painel_w) // 2, y - round(30 * u), painel_w, total + round(60 * u), "black@0.45"))

    cadeia += _texto_centrado(f"CAM {camera} · TAKE {take}", w, y, esc_cam)
    y += 7 * esc_cam + esp_l

    hh = f"mod(floor({T}/{base * 3600}),24)"
    mm = f"mod(floor({T}/{base * 60}),60)"
    ss = f"mod(floor({T}/{base}),60)"
    ff = f"mod({T},{base})"
    x = (w - larg_tc) // 2
    for i, campo in enumerate((hh, mm, ss, ff)):
        for valor in (f"floor({campo}/10)", f"mod({campo},10)"):
            cadeia += _digito(x, y, dig_w, dig_h, valor)
            x += dig_w + gap
        if i < 3:
            cadeia += (_ponto_e_virgula if (df and i == 2) else _dois_pontos)(x, y, dp, dig_h)
            x += dp + gap
    y += dig_h + esp_l

    rotulo = "QUADRO"
    larg_rot = fonte_pixel.largura(rotulo, esc_info)
    n_dig = 6
    larg_fq = larg_rot + round(30 * u) + n_dig * fq_w + (n_dig - 1) * fq_gap
    x = (w - larg_fq) // 2
    cadeia += _texto(rotulo, x, y + (fq_h - 7 * esc_info) // 2, esc_info)
    x += larg_rot + round(30 * u)
    for k in range(n_dig - 1, -1, -1):
        cadeia += _digito(x, y, fq_w, fq_h, f"mod(floor(n/{10 ** k}),10)")
        x += fq_w + fq_gap
    y += fq_h + esp_l

    for linha in linhas:
        cadeia += _texto_centrado(linha, w, y, esc_info)
        y += 7 * esc_info + esp_l

    # as faixas de código por último: nada as cobre
    cadeia += _faixa(w, h, *f["y_quadro"], "n")
    cadeia += _faixa(w, h, *f["y_tc"], T)
    cadeia.append(f"format={pix_fmt}")
    if sar:
        # anamórfico: o quadro é desenhado nos pixels GUARDADOS (círculo no arquivo) e o container diz a
        # proporção do pixel — o NLE que respeita o PAR desespreme, e o círculo vira elipse LARGA (2:1). Isso
        # prova o desespremer; melhoria anotada: desenhar o círculo já espremido, para ele voltar círculo.
        # ⛔ "2/1", nunca "2:1": dentro do filtro o ":" separa opções e o setsar=2:1 grava 1:1 CALADO
        # (medido 2026-10-06: pasp 1:1 no mov, e o NLE mostrou "Square")
        cadeia.append(f"setsar={sar.replace(':', '/')}")
    return ",".join(cadeia) + f"[{saida}]"

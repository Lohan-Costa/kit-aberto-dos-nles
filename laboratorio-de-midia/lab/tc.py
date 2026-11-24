"""Taxas e timecode: a conta que o gerador, a verdade e o verificador fazem igual.

O TC é guardado como **quadros desde a meia-noite** (é o que a faixa de baixo do código de barras
grava). A base de contagem é a taxa NOMINAL arredondada (23,976 conta em 24, 29,97 em 30); o
drop-frame pula os números :00 e :01 (29,97) ou :00–:03 (59,94) no início de cada minuto, exceto nos
múltiplos de 10 — os quadros não somem, só os NÚMEROS.
"""
from __future__ import annotations

from fractions import Fraction

#: nome usado nas receitas → taxa exata
TAXAS = {"23.976": Fraction(24000, 1001), "24": Fraction(24), "25": Fraction(25),
         "29.97": Fraction(30000, 1001), "30": Fraction(30), "50": Fraction(50),
         "59.94": Fraction(60000, 1001), "60": Fraction(60)}


def taxa(nome: str) -> Fraction:
    try:
        return TAXAS[str(nome)]
    except KeyError:
        raise ValueError(f"taxa desconhecida {nome!r}; use uma de {sorted(TAXAS)}") from None


def base(fps: Fraction) -> int:
    """A base de contagem do TC: 23,976 → 24, 29,97 → 30."""
    return int(round(fps))


def _quadros_dropados_por_minuto(b: int) -> int:
    if b not in (30, 60):
        raise ValueError("drop-frame só existe em 29,97 e 59,94")
    return 2 if b == 30 else 4


def tc_para_quadros(tc: str, b: int, df: bool = False) -> int:
    """'01:00:00:00' → 90000 (b=25). Aceita ';' como separador do drop-frame."""
    hh, mm, ss, ff = (int(x) for x in tc.replace(";", ":").split(":"))
    if ff >= b or ss > 59 or mm > 59 or hh > 23:
        raise ValueError(f"TC inválido para base {b}: {tc}")
    total = ((hh * 60 + mm) * 60 + ss) * b + ff
    if df:
        d = _quadros_dropados_por_minuto(b)
        minutos = hh * 60 + mm
        if ss == 0 and ff < d and mm % 10:
            raise ValueError(f"{tc} não existe em drop-frame")
        total -= d * (minutos - minutos // 10)
    return total


def quadros_para_tc(q: int, b: int, df: bool = False) -> str:
    """90000 → '01:00:00:00' (b=25). Volta a zero em 24 h, como o TC de verdade."""
    if df:
        d = _quadros_dropados_por_minuto(b)
        por_10min = b * 600 - d * 9
        por_min = b * 60 - d
        q %= por_10min * 6 * 24
        dez, resto = divmod(q, por_10min)
        extra = 0 if resto < d else d * ((resto - d) // por_min)
        q += d * 9 * dez + extra
    else:
        q %= b * 86400
    ff = q % b
    ss = (q // b) % 60
    mm = (q // (b * 60)) % 60
    hh = (q // (b * 3600)) % 24
    sep = ";" if df else ":"
    return f"{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"


def rotulo(q: int, b: int, df: bool = False) -> int:
    """O RÓTULO do quadro `q` (contagem real desde a meia-noite) como número: HH·3600·b + MM·60·b + SS·b + FF.
    É o que a faixa de baixo do código de barras grava. Sem drop-frame é o próprio `q`; com drop-frame é
    maior (os números pulados contam), e é o que se compara com o TC que o NLE mostra."""
    return tc_para_quadros(quadros_para_tc(q, b, df), b, df=False)


def rotulo_ffmpeg(q_expr: str, b: int, df: bool) -> str:
    """A mesma conta do `rotulo`, como expressão do ffmpeg (`q_expr` = contagem real; ex.: `(107892+n)`)."""
    if not df:
        return f"mod({q_expr},{b * 86400})"
    d = _quadros_dropados_por_minuto(b)
    p10, pm = b * 600 - d * 9, b * 60 - d
    q = f"mod({q_expr},{p10 * 144})"
    m = f"mod({q},{p10})"
    return f"({q}+{d * 9}*floor({q}/{p10})+if(gte({m},{d}),{d}*floor(({m}-{d})/{pm}),0))"

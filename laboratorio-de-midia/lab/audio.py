"""O que cada canal toca (organograma aprovado em 2026-10-06).

Um tom por canal e por fonte, a −20 dBFS: f = 300 + 1700·(fonte−1) + 100·(canal−1) Hz.
CAM 1 canal 1 = 300 Hz, canal 16 = 1800 Hz; CAM 2 começa em 2000 Hz; o som direto (fonte 4) em 5400 Hz.
Uma FFT (aqui, Goertzel) diz de qual fonte e de qual canal veio o som, mesmo com canais trocados.

Claque: 1 ms a cada segundo INTEIRO de TC, comum a todas as fontes — mede o sync entre câmeras, som
direto e imagem. No instante da claque o quadro mostrado tem FF = 00.
"""
from __future__ import annotations

from fractions import Fraction

AMPLITUDE = 0.1          # −20 dBFS
CLAQUE_S = 0.001
CLAQUE_AMPLITUDE = 0.9
AMOSTRAGEM = 48000


def hz(fonte: int, canal: int) -> int:
    if not (1 <= fonte <= 4 and 1 <= canal <= 16):
        raise ValueError(f"fonte 1–4 e canal 1–16 (veio fonte {fonte}, canal {canal})")
    return 300 + 1700 * (fonte - 1) + 100 * (canal - 1)


def primeira_claque(tc_inicio_q: int, b: int, fps: Fraction) -> Fraction:
    """Segundos desde o início do arquivo até o primeiro segundo inteiro de TC (quadro com FF=00)."""
    return Fraction((-tc_inicio_q) % b) / fps


def periodo_claque(b: int, fps: Fraction) -> Fraction:
    """Um segundo de TC em segundos reais: 1 s a 25; 1,001 s a 23,976 e 29,97."""
    return Fraction(b) / fps


def instantes_claque(tc_inicio_q: int, b: int, df: bool, fps: Fraction, quadros: int) -> list[Fraction]:
    """Onde cai cada claque: no PRIMEIRO QUADRO de cada segundo de TC. Sem drop-frame é o FF=00; no minuto
    em que o drop-frame pula 00 e 01, o segundo começa no ;02 (é ali a claque)."""
    from . import tc
    saida = []
    anterior = tc.rotulo(tc_inicio_q - 1, b, df) // b     # o quadro de ANTES do arquivo decide o quadro 0
    for k in range(quadros):
        seg = tc.rotulo(tc_inicio_q + k, b, df) // b
        if seg != anterior:
            saida.append(Fraction(k) / fps)
        anterior = seg
    return saida


def expressao_lista(freq: int | None, instantes: list[Fraction]) -> str:
    """Como `expressao`, com as claques numa LISTA de instantes (drop-frame: não são periódicas)."""
    if freq is None:
        return "0"
    if not instantes:
        return f"{AMPLITUDE}*sin(2*PI*{freq}*t)"
    cond = "+".join(f"between(t,{float(i):.9f},{float(i) + CLAQUE_S - 1e-9:.9f})" for i in instantes)
    return f"if({cond},{CLAQUE_AMPLITUDE},{AMPLITUDE}*sin(2*PI*{freq}*t))"


def expressao(freq: int | None, t0: Fraction, periodo: Fraction) -> str:
    """Expressão do `aevalsrc` para um canal. `freq=None` = canal em silêncio (sem claque)."""
    if freq is None:
        return "0"
    # mod de número negativo não é o que se espera: soma-se um múltiplo grande do período
    deslocado = f"t-{float(t0):.9f}+{float(periodo * 100000):.9f}"
    return (f"if(lt(mod({deslocado},{float(periodo):.9f}),{CLAQUE_S}),{CLAQUE_AMPLITUDE},"
            f"{AMPLITUDE}*sin(2*PI*{freq}*t))")

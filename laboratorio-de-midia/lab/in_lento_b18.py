"""B18_IN_LENTO — o encaixe do in de um clipe SOLTO com velocidade, medido pelo número do quadro desenhado.

Pergunta (caso real R04, 2026-10-10): o Premiere começa o clipe acelerado em piso(In ÷ passo) × passo (8 clipes de 1,1× a 10×,
todos exatos) e o JUL_7672 a 50 % também; o JUL_7671 a 50 % (100 qps, In ÷ passo = 767,16) sai UM PASSO à frente. Este caso
varre a fração do in a 50 % (e controles a 2× e 4×) e repete os ins EXATOS dos dois clipes do R04, em duas posições da
timeline, sobre uma placa de 100 qps que diz o próprio quadro.

    python -m lab.in_lento_b18           (gera a placa)
"""
from __future__ import annotations

import math
import os
import subprocess

from . import ffmpeg as ff
from . import mascara_b14 as b14

TPS = 254016000000
TPF = TPS * 1001 // 24000                 # um quadro da timeline de 23,976 em ticks
TPM = TPS // 100                          # um quadro da placa de 100 qps
QUADROS = 12                              # cada segmento
REAL = {n: os.path.join("D:/", "MIDIAS DE TESTES", "3 CONJUNTOS DOS APPS", "_CICLO ASSIST", "conformar", "03 CASOS", "REAL",
                        "R04 PRODUCAO-C", "ISOLADO", "MIDIA", "01_FOOTAGE", "DAY_4", n + ".mov") for n in ("JUL_7671", "JUL_7672")}
PLACA = {"cor": b14.COR_FRENTE, "fps": "100", "segundos": 45, "digitos": "cima"}


def placa(fps: int) -> str:
    """A placa numerada na taxa pedida (a de 100 é a `B18_PLACA_100.mp4`)."""
    from .gerar import RAIZ
    return os.path.join(RAIZ, "saida", "base", "B18_IN_LENTO", f"B18_PLACA_{fps}.mp4")


def _in_por_fracao(v: float, base: int, frac: float) -> int:
    """In (ticks da mídia) com In ÷ (v × quadro) = base + frac, em ticks EXATOS — fora da grade da mídia, como os ins do R04
    (o JUL_7671 começa em 1599,848 quadros do arquivo)."""
    return round((base + frac) * v * TPF)


def _plano() -> list[dict]:
    pl = []
    for frac in (0.0, 0.08, 0.16, 0.25, 0.33, 0.40, 0.48, 0.50, 0.52, 0.60, 0.67, 0.75, 0.84, 0.92):
        pl.append({"rotulo": f"V050_F{round(frac * 100):02d}", "vel": 0.5, "in_ticks": _in_por_fracao(0.5, 700, frac)})
    for v, base in ((2.0, 300), (4.0, 150)):
        for frac in (0.16, 0.48, 0.84):
            pl.append({"rotulo": f"V{round(v * 100):03d}_F{round(frac * 100):02d}", "vel": v, "in_ticks": _in_por_fracao(v, base, frac)})
    # os ins EXATOS do R04 (ticks do XML), duas vezes cada — a posição na timeline muda
    for rep in ("A", "B"):
        pl.append({"rotulo": f"R04_7671_{rep}", "vel": 0.5, "in_ticks": 4063869684000})
        pl.append({"rotulo": f"R04_7672_{rep}", "vel": 0.5, "in_ticks": 9055612188000})
    # RODADA 2 (2026-10-11): a 1× com mídia de OUTRA taxa (o apontamento da revisão de código) e a 4× com 25/60 qps (a
    # contradição: placa de 100 qps a 4× deu TETO; o R04, 25 qps a 4×, piso)
    for fps in (25, 60, 100):
        for v in (1.0, 4.0):
            for frac in (0.16, 0.48, 0.84):
                pl.append({"rotulo": f"P{fps}_V{round(v * 100):03d}_F{round(frac * 100):02d}", "vel": v, "fps_m": fps,
                           "in_ticks": _in_por_fracao(v, 200 if v == 1 else 60, frac), "midia": placa(fps)})
    # a MÍDIA REAL do R04 com os mesmos ins (o render do próprio projeto do R04 dá o JUL_7671 um passo à frente; a placa,
    # não): o que é da mídia (timecode de início, contêiner) e o que é do projeto
    for nome, in_t in (("JUL_7671", 4063869684000), ("JUL_7672", 9055612188000)):
        pl.append({"rotulo": f"MIDIA_{nome}", "vel": 0.5, "in_ticks": in_t, "midia": REAL[nome]})
    return pl


PLANO = _plano()


def inicio(i: int) -> int:
    return i * QUADROS


def tpm(seg: dict) -> int:
    return TPS // int(seg.get("fps_m", 100))


def previsto(seg: dict, k: int, modo: str) -> int:
    """O quadro da placa no quadro `k` do segmento: `piso`/`teto`/`exato` do In na grade do clipe (passo = v × quadro)."""
    passo = seg["vel"] * TPF
    q = seg["in_ticks"] / passo
    e = {"piso": math.floor(q + 1e-9), "teto": math.ceil(q - 1e-9), "exato": q}[modo] * passo
    return math.floor((e + k * passo) / tpm(seg) + 1e-6)


def gerar(saida: str) -> str:
    os.makedirs(saida, exist_ok=True)
    for fps in (100, 25, 60):
        arq = os.path.join(saida, f"B18_PLACA_{fps}.mp4")
        if not os.path.exists(arq):            # aberta no Premiere, o Windows trava o arquivo
            subprocess.run([ff.achar("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"color=c={b14._hex(PLACA['cor'])}:s={b14.W}x{b14.H}:r={fps}:d={PLACA['segundos']}",
                            "-vf", b14._filtro(f"B18 {fps}", PLACA), "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", arq], check=True)
    return os.path.join(saida, "B18_PLACA_100.mp4")


def main(argv=None) -> int:
    from .gerar import RAIZ
    print(gerar(os.path.join(RAIZ, "saida", "base", "B18_IN_LENTO")))
    for s in PLANO:
        print(s["rotulo"], s["vel"], "In ÷ passo = %.4f" % (s["in_ticks"] / (s["vel"] * TPF)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""A régua do pacote DERIVA: quanto um som anda a mais que outro, medido pelo CONTEÚDO (a cena que os dois gravaram).

    py -m lab.medir_deriva <referencia> <alvo> [--canal-ref N] [--canal-alvo N] [--janelas 24]
    py -m lab.medir_deriva saida/deriva/D02_GRAVADOR_50PPM            (a pasta de um caso: câmera × som direto)

A referência é o som guia da câmera (o relógio da imagem); o alvo é o som direto — ou as duas trilhas de um RENDER
do NLE (`--canal-ref`/`--canal-alvo` no mesmo arquivo). Em cada janela ao longo da referência acha-se onde o mesmo
trecho da cena está no alvo; os atrasos formam uma reta: a inclinação é a deriva (ppm), o resíduo diz se é relógio
(reta) ou outra coisa (VFR, corte, taxa trocada).

Como mede (só biblioteca padrão + ffmpeg, a regra do laboratório):
1. o ffmpeg decodifica cada som em mono 8 kHz (passa-faixa 200–3500 Hz) — a fase fina;
2. o envelope (média do |valor| a cada 10 ms) acha o lugar grosso: a 1ª janela por FFT numa busca larga, as
   seguintes perto da reta prevista pelas anteriores;
3. a correlação normalizada a 8 kHz numa janela de 1 s, ±20 ms do lugar grosso, com interpolação parabólica do
   pico (precisão de microssegundos num som limpo).
"""
from __future__ import annotations

import argparse
import array
import cmath
import json
import math
import os
import subprocess
import sys

from . import ffmpeg

TAXA = 8000
PASSO_ENV = 80                       # 10 ms a 8 kHz
TAXA_ENV = TAXA // PASSO_ENV


def ler(arquivo: str, canal: int | None = None) -> array.array:
    """O som inteiro em mono 8 kHz (int16). `canal` (1, 2, …): só aquele canal; sem ele, a soma."""
    mix = f"pan=mono|c0=c{canal - 1}," if canal else ""
    p = subprocess.run([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-i", arquivo, "-map", "0:a:0",
                        "-af", f"{mix}aresample={TAXA}:resampler=soxr,highpass=f=200,lowpass=f=3500",
                        "-ac", "1", "-f", "s16le", "-acodec", "pcm_s16le", "-"], capture_output=True, check=True)
    a = array.array("h")
    a.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return a


def envelope(a: array.array) -> list[float]:
    return [sum(map(abs, a[i:i + PASSO_ENV])) / PASSO_ENV for i in range(0, len(a) - PASSO_ENV + 1, PASSO_ENV)]


def _fft(x: list[complex], inv: bool = False) -> list[complex]:
    n = len(x)
    j = 0
    x = list(x)
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            x[i], x[j] = x[j], x[i]
    m = 2
    sinal = 1 if inv else -1
    while m <= n:
        w_m = cmath.exp(sinal * 2j * math.pi / m)
        meio = m // 2
        for k in range(0, n, m):
            w = 1
            for t in range(meio):
                u, v = x[k + t], x[k + t + meio] * w
                x[k + t], x[k + t + meio] = u + v, u - v
                w *= w_m
        m <<= 1
    if inv:
        x = [v / n for v in x]
    return x


def _centrar(v: list[float]) -> list[float]:
    m = sum(v) / len(v) if v else 0.0
    return [x - m for x in v]


def grosso_fft(ref: list[float], alvo: list[float]) -> int:
    """O deslocamento (em amostras do envelope) em que `ref` cabe melhor dentro de `alvo` (alvo ≥ ref)."""
    n = 1
    while n < len(alvo) + len(ref):
        n <<= 1
    r = _centrar(ref)
    a = _centrar(alvo)
    fr = _fft([complex(v) for v in r] + [0j] * (n - len(r)))
    fa = _fft([complex(v) for v in a] + [0j] * (n - len(a)))
    c = _fft([x * y.conjugate() for x, y in zip(fa, fr)], inv=True)
    lim = len(alvo) - len(ref) + 1
    return max(range(max(1, lim)), key=lambda k: c[k].real)


def grosso_direto(ref: list[float], alvo: list[float]) -> int:
    r = _centrar(ref)
    melhor, onde = -math.inf, 0
    for k in range(len(alvo) - len(ref) + 1):
        seg = alvo[k:k + len(ref)]
        m = sum(seg) / len(seg)
        s = sum(x * (y - m) for x, y in zip(r, seg))
        if s > melhor:
            melhor, onde = s, k
    return onde


def fino(ref: array.array, alvo: array.array, i_ref: int, i_alvo: int, n: int, raio: int,
         inclinacao: float = 0.0) -> tuple[float, float]:
    """(deslocamento fino em amostras de 8 kHz, correlação normalizada no pico) de ref[i_ref:i_ref+n] em
    alvo[i_alvo − raio … i_alvo + raio]. `inclinacao` (a deriva já estimada): o trecho do alvo é lido esticado na
    mesma proporção — a 1000 ppm, 1 s de janela escorrega 8 amostras e a correlação caía para 0,2–0,6."""
    idx = [k + round(k * inclinacao) for k in range(n)]
    span = idx[-1] + 1
    r = ref[i_ref:i_ref + n]
    mr = sum(r) / n
    r = [x - mr for x in r]
    er = math.sqrt(sum(x * x for x in r)) or 1.0
    cs = []
    for d in range(-raio, raio + 1):
        a0 = i_alvo + d
        if a0 < 0 or a0 + span > len(alvo):
            cs.append(-2.0)
            continue
        seg = [alvo[a0 + k] for k in idx] if inclinacao else alvo[a0:a0 + n]
        ma = sum(seg) / n
        num = sum(x * (y - ma) for x, y in zip(r, seg))
        ea = math.sqrt(sum((y - ma) ** 2 for y in seg)) or 1.0
        cs.append(num / (er * ea))
    k = max(range(len(cs)), key=cs.__getitem__)
    frac = 0.0
    if 0 < k < len(cs) - 1:
        y0, y1, y2 = cs[k - 1], cs[k], cs[k + 1]
        den = y0 - 2 * y1 + y2
        if den:
            frac = 0.5 * (y0 - y2) / den
    return (k - raio) + frac, cs[k]


def _reta(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return my - b * mx, b


def medir(ref_arq: str, alvo_arq: str, canal_ref: int | None = None, canal_alvo: int | None = None,
          janelas: int = 24, busca_s: float = 120.0, ignorar_s: float = 1.0) -> dict:
    ref = ler(ref_arq, canal_ref)
    alvo = ler(alvo_arq, canal_alvo)
    er, ea = envelope(ref), envelope(alvo)
    dur = len(ref) / TAXA
    jan_env = 20 * TAXA_ENV                       # 20 s de envelope
    n_fino = TAXA                                 # 1 s
    raio = int(0.020 * TAXA)
    fim = dur - 22
    if fim <= ignorar_s + 2:
        raise ValueError(f"referência curta demais ({dur:.1f} s)")
    # perto do começo em passos crescentes (a reta ainda não existe), depois espalhadas até o fim
    pos = [t for t in (ignorar_s + 1, 10, 30, 90) if t < fim]
    resto = max(1, janelas - len(pos))
    pos = sorted(set(pos + [ignorar_s + 1 + (fim - ignorar_s - 1) * (k + 1) / resto for k in range(resto)]))
    pontos = []
    a, b = None, 0.0
    for t in pos:
        i0 = int(t * TAXA_ENV)
        r = er[i0:i0 + jan_env]
        if a is None:
            ini = max(0, i0 - int(busca_s * TAXA_ENV))
            seg = ea[ini:i0 + jan_env + int(busca_s * TAXA_ENV)]
            k = ini + grosso_fft(r, seg)
        else:
            prev = int(round((t + a + b * t) * TAXA_ENV))
            folga = int(2.0 * TAXA_ENV) if len(pontos) >= 2 else int(10.0 * TAXA_ENV)
            ini = max(0, prev - folga)
            seg = ea[ini:prev + jan_env + folga]
            if len(seg) < len(r):
                break
            k = ini + grosso_direto(r, seg)
        grosso_s = (k - i0) / TAXA_ENV            # alvo − referência, em segundos
        # fase fina no meio da janela
        tm = t + 10.0
        i_ref = int(tm * TAXA)
        d, c = fino(ref, alvo, i_ref, int(round((tm + grosso_s) * TAXA)), n_fino, raio, b)
        desloc = grosso_s + (int(round((tm + grosso_s) * TAXA)) - (tm + grosso_s) * TAXA + d) / TAXA
        pontos.append({"t_ref_s": round(tm, 3), "atraso_s": round(desloc, 7), "correlacao": round(c, 4)})
        xs = [p["t_ref_s"] for p in pontos]
        ys = [p["atraso_s"] for p in pontos]
        a, b = (ys[0], 0.0) if len(pontos) == 1 else _reta(xs, ys)
    # válida = pico claro E perto da reta das outras (1ª reta com todas acima de 0,2; depois só as que distam < 2 ms)
    bons = [p for p in pontos if p["correlacao"] >= 0.2]
    if len(bons) >= 3:
        a, b = _reta([p["t_ref_s"] for p in bons], [p["atraso_s"] for p in bons])
        bons = [p for p in bons if abs(p["atraso_s"] - (a + b * p["t_ref_s"])) < 0.002]
    xs = [p["t_ref_s"] for p in bons]
    ys = [p["atraso_s"] for p in bons]
    a, b = _reta(xs, ys) if len(bons) >= 2 else (ys[0] if ys else 0.0, 0.0)
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    return {
        "referencia": ref_arq, "alvo": alvo_arq, "canal_ref": canal_ref, "canal_alvo": canal_alvo,
        "duracao_ref_s": round(dur, 3),
        "deriva_ppm": round(b * 1e6, 3),
        "velocidade_de_correcao": 1 + b,
        "atraso_no_inicio_ms": round((a + b * xs[0]) * 1000, 3) if xs else None,
        "atraso_no_fim_ms": round((a + b * xs[-1]) * 1000, 3) if xs else None,
        "variacao_ms": round((b * (xs[-1] - xs[0])) * 1000, 3) if xs else None,
        "residuo_max_ms": round(max(map(abs, res)) * 1000, 4) if res else None,
        "janelas_validas": len(bons), "janelas": len(pontos),
        "pontos": pontos,
    }


def _caso(pasta: str) -> tuple[str, str, dict]:
    with open(os.path.join(pasta, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    cam = next(a for a in v["arquivos"] if a["papel"] == "camera")
    som = next(a for a in v["arquivos"] if a["papel"] == "som")
    return os.path.join(pasta, cam["arquivo"]), os.path.join(pasta, som["arquivo"]), v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mede a deriva entre dois sons pela cena gravada.")
    ap.add_argument("referencia", help="som de referência (ou a pasta de um caso DERIVA)")
    ap.add_argument("alvo", nargs="?")
    ap.add_argument("--canal-ref", type=int)
    ap.add_argument("--canal-alvo", type=int)
    ap.add_argument("--janelas", type=int, default=24)
    ap.add_argument("--json", help="grava o resultado aqui")
    a = ap.parse_args(argv)
    verdade = None
    if os.path.isdir(a.referencia):
        ref, alvo, verdade = _caso(a.referencia)
    else:
        ref, alvo = a.referencia, a.alvo or a.referencia
    r = medir(ref, alvo, a.canal_ref, a.canal_alvo, a.janelas)
    if verdade:
        r["verdade_ppm"] = verdade["deriva_ppm"]
        r["erro_ppm"] = round(r["deriva_ppm"] - verdade["deriva_ppm"], 3)
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    pts = r.pop("pontos")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print("pontos (t ref → atraso ms, correlação):",
          ", ".join(f"{p['t_ref_s']:.0f}s→{p['atraso_s'] * 1000:.2f} ({p['correlacao']:.2f})" for p in pts))
    return 0


if __name__ == "__main__":
    sys.exit(main())

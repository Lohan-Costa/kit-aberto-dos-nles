"""Ler de volta o que a mídia diz: o código de barras do quadro e o tom/claque de cada canal.

Só biblioteca padrão: o quadro sai do ffmpeg em cinza cru (`rawvideo`, 1 byte por pixel) e o áudio
em `f32le`. Assim o verificador roda em qualquer máquina com ffmpeg, sem numpy/Pillow.

⛔ Quadro por posição: **nunca** `-ss` (busca). No MPEG-2 OP-Atom do Avid a busca cai no quadro N/2,
e decodificar sem `passthrough` descarta quadros (banco: `protocolos/mxf/README.md`, 2026-09-17).
Aqui é `select=eq(n,N)` com `-fps_mode passthrough`: decodifica em ordem, exato.
"""
from __future__ import annotations

import math
from array import array

from . import audio, ffmpeg, video


def quadros_cinza(caminho: str, indices: list[int], w: int, h: int) -> dict[int, bytes]:
    indices = sorted(set(indices))
    sel = "+".join(f"eq(n\\,{i})" for i in indices)
    # -noautorotate: o arquivo com metadado de rotação/flip (B12) é lido nos pixels GUARDADOS, como foi desenhado
    bruto = ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-noautorotate", "-i", "file:" + caminho,
                          "-map", "0:v:0", "-vf", f"select={sel}", "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-"], binario=True)
    tam = w * h
    if len(bruto) != tam * len(indices):
        raise RuntimeError(f"pedi {len(indices)} quadros e vieram {len(bruto) / tam:g}")
    return {i: bruto[k * tam:(k + 1) * tam] for k, i in enumerate(indices)}


def _media(img: bytes, w: int, x: int, y: int, r: int = 4) -> float:
    soma = n = 0
    for yy in range(y - r, y + r + 1):
        linha = yy * w
        for xx in range(x - r, x + r + 1):
            soma += img[linha + xx]
            n += 1
    return soma / n


def ler_faixas(img: bytes, w: int, h: int) -> tuple[int, int]:
    """(número do quadro no arquivo, TC em quadros desde a meia-noite)."""
    f = video.faixas(w, h)
    valores = []
    for y0, y1 in (f["y_quadro"], f["y_tc"]):
        y = (y0 + y1) // 2
        v = 0
        for b, (x0, x1) in enumerate(f["celulas"]):
            if _media(img, w, (x0 + x1) // 2, y) > 128:
                v |= 1 << b
        valores.append(v)
    return valores[0], valores[1]


def amostras(caminho: str, trilha: int, inicio_s: float, dur_s: float) -> tuple[list[array], int]:
    """Os canais (cada um um `array('f')`) da trilha de áudio `trilha` (0 = a primeira)."""
    import json
    info = json.loads(ffmpeg.rodar([ffmpeg.achar("ffprobe"), "-v", "error", "-select_streams", f"a:{trilha}",
                                    "-show_entries", "stream=channels,sample_rate", "-of", "json",
                                    "file:" + caminho]))["streams"][0]
    canais, sr = int(info["channels"]), int(info["sample_rate"])
    bruto = ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-i", "file:" + caminho,
                          "-map", f"0:a:{trilha}", "-ss", f"{inicio_s:.6f}", "-t", f"{dur_s:.6f}",
                          "-f", "f32le", "-acodec", "pcm_f32le", "-"], binario=True)
    tudo = array("f")
    tudo.frombytes(bruto[: len(bruto) // 4 * 4])
    return [tudo[c::canais] for c in range(canais)], sr


def goertzel(x, sr: int, freq: float) -> float:
    """Amplitude (0–1) da senoide de `freq` em `x`."""
    k = 2 * math.cos(2 * math.pi * freq / sr)
    s1 = s2 = 0.0
    for v in x:
        s1, s2 = v + k * s1 - s2, s1
    pot = s1 * s1 + s2 * s2 - k * s1 * s2
    return 2 * math.sqrt(max(pot, 0.0)) / len(x)


#: todas as frequências que o laboratório usa → (fonte, canal)
GRADE = {audio.hz(f, c): (f, c) for f in range(1, 5) for c in range(1, 17)}


def identificar_tom(x, sr: int) -> tuple[int | None, float]:
    """(Hz da grade mais forte, amplitude). `None` se o canal está em silêncio (< −40 dBFS)."""
    melhor, amp = None, 0.0
    for freq in GRADE:
        a = goertzel(x, sr, freq)
        if a > amp:
            melhor, amp = freq, a
    return (melhor if amp >= 0.01 else None), amp


def claques(x, sr: int, limiar: float = 0.5) -> list[float]:
    """Instantes (s, relativos ao começo de `x`) em que começa cada claque."""
    saida, dentro = [], False
    for i, v in enumerate(x):
        alto = abs(v) > limiar
        if alto and not dentro:
            saida.append(i / sr)
        dentro = alto
    # o AAC espalha a claque em vários picos: junta os que estão a menos de 20 ms
    juntos = []
    for t in saida:
        if not juntos or t - juntos[-1] > 0.02:
            juntos.append(t)
    return juntos


def tons_presentes(x, sr: int, limiar: float = 0.01) -> list[int]:
    """Todas as frequências da grade acima de −40 dBFS — para saber o que uma MIXAGEM juntou num canal."""
    return sorted(f for f in GRADE if goertzel(x, sr, f) >= limiar)


def ler_imagem(caminho: str) -> tuple[bytes, int, int]:
    """Uma imagem (PNG/TIFF/JPG, ex.: o still de um NLE) em cinza cru, com a largura e a altura dela."""
    import json
    s = json.loads(ffmpeg.rodar([ffmpeg.achar("ffprobe"), "-v", "error", "-select_streams", "v:0",
                                 "-show_entries", "stream=width,height", "-of", "json", "file:" + caminho]))["streams"][0]
    w, h = int(s["width"]), int(s["height"])
    bruto = ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-noautorotate", "-i", "file:" + caminho,
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], binario=True)
    return bruto, w, h


def trechos_do_tom(x, sr: int, freq: int, passo_s: float = 0.005, limiar: float = 0.02) -> list[tuple[float, float]]:
    """Os trechos (início, fim em s) em que `freq` está presente — janelas de `passo_s`. Mede onde um som
    começa e acaba numa mixagem (ex.: o som direto sincronizado por TC tem de acabar num instante certo)."""
    n = max(1, int(passo_s * sr))
    trechos, dentro, ini = [], False, 0.0
    for i in range(0, len(x) - n + 1, n):
        janela = x[i:i + n]
        # sem as claques: elas são banda larga e acenderiam qualquer frequência
        if max(abs(v) for v in janela) > 0.85:
            continue
        on = goertzel(janela, sr, freq) >= limiar
        if on and not dentro:
            ini, dentro = i / sr, True
        elif not on and dentro:
            trechos.append((round(ini, 3), round(i / sr, 3)))
            dentro = False
    if dentro:
        trechos.append((round(ini, 3), round(len(x) / sr, 3)))
    return trechos


def area_util(img: bytes, w: int, h: int, limiar: int = 20) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) — x1/y1 exclusivos — da parte NÃO preta da imagem: onde o NLE pôs o quadro dentro
    de um raster maior (letterbox, pillarbox). O fundo do quadro sintético nunca é preto (a faixa apagada
    é cinza 0x20, a câmera é colorida)."""
    linhas = [y for y in range(h) if max(img[y * w:(y + 1) * w:4]) > limiar]
    colunas = [x for x in range(w) if max(img[x:w * h:w * 4]) > limiar]
    if not linhas or not colunas:
        return (0, 0, 0, 0)
    return (colunas[0], linhas[0], colunas[-1] + 1, linhas[-1] + 1)

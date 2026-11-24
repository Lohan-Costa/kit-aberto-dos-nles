"""Conferir um plano com GEOMETRIA (Resize, PIP, 3D Warp) contra o vid ref: o quadro do original com a transformação
aplicada pelo ffmpeg × o quadro do ref, no quadro certo e nos VIZINHOS. O código de barras sai do lugar quando a imagem
é escalada ou girada, então a leitura exata não serve; a diferença de imagem diz se o quadro de fonte é o certo.

Só biblioteca padrão + ffmpeg (a regra do laboratório): o quadro entra cru em cinza e a transformação é
`scale` → `rotate` → `overlay` sobre preto, no raster da timeline.

A transformação neutra: `escala` (1 = 100 %), `dx`/`dy` em PIXELS da timeline (+x direita, +y para BAIXO), `rot` em
graus no sentido do ffmpeg (positivo = horário na tela). `do_avid` traduz os parâmetros do AAF do MC.
"""
from __future__ import annotations

import subprocess

from . import ffmpeg

W_TL, H_TL = 1920, 1080          # o raster da timeline (o vid ref)
W_CMP, H_CMP = 480, 270          # o raster da comparação
LIMIAR_IMAGEM = 8.0              # diferença média da imagem inteira acima disso = a transformação não confere


def do_avid(nome: str, p: dict, w: int = W_TL, h: int = H_TL) -> dict:
    """Os parâmetros do AAF do MC (`aaf.parser`: PaintResize_v2, SBlend_v2 = 3D Warp, PIP) → a transformação neutra.
    Unidades MEDIDAS no MC 25.12 Mac (laboratório BL04, 2026-11-21): posição em MILÉSIMOS da largura (x) e da
    altura (y), +Y para CIMA; rotação Z positiva = horário na tela (o 3D Warp com rot_z −10 gira anti-horário)."""
    return {"escala": float(p.get("scale_x", 1.0) or 1.0),
            "escala_y": float(p.get("scale_y", p.get("scale_x", 1.0)) or 1.0),
            "dx": float(p.get("pos_x", 0.0) or 0.0) / 1000.0 * w,
            "dy": -float(p.get("pos_y", 0.0) or 0.0) / 1000.0 * h,
            "rot": float(p.get("rot_z", 0.0) or 0.0)}


def transformar(cru: bytes, t: dict, w: int = W_CMP, h: int = H_CMP) -> bytes:
    """`cru` = quadro cinza W_TL×H_TL → o quadro transformado em w×h (cinza)."""
    sx, sy = t.get("escala", 1.0), t.get("escala_y", t.get("escala", 1.0))
    a = f"({t.get('rot', 0.0)})*PI/180"
    filtro = (f"[0:v]scale=iw*{sx}:ih*{sy},format=gray,rotate={a}:ow=rotw({a}):oh=roth({a}):c=black[fg];"
              f"color=black:s={W_TL}x{H_TL},format=gray[bg];"
              f"[bg][fg]overlay=x=(W-w)/2+{t.get('dx', 0.0)}:y=(H-h)/2+{t.get('dy', 0.0)}:shortest=1,"
              f"scale={w}:{h},format=gray")
    r = subprocess.run([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray",
                        "-s", f"{W_TL}x{H_TL}", "-i", "-", "-filter_complex", filtro, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], input=cru, capture_output=True, **ffmpeg.SEM_JANELA)
    if r.returncode != 0 or len(r.stdout) != w * h:
        raise RuntimeError(f"ffmpeg (transformar): {r.stderr.decode('utf-8', 'replace')[-800:]}")
    return r.stdout


def reduzir(cru: bytes, w: int = W_CMP, h: int = H_CMP) -> bytes:
    return transformar(cru, {}, w, h)


def diferenca(a: bytes, b: bytes) -> float:
    """Diferença média de cinza (0–255), pixel a pixel."""
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def ajustar(cru: bytes, ref: bytes, t0: dict, passos=(16.0, 8.0, 4.0, 2.0, 1.0)) -> tuple[dict, float]:
    """Procura em volta de `t0` (dx, dy; e a escala e a rotação em passos finos) a transformação que mais aproxima o
    quadro do ref — só para MEDIR as unidades de um efeito novo, nunca na conferência (que usa a do AAF)."""
    melhor, d = dict(t0), diferenca(transformar(cru, t0), ref)
    for p in passos:
        mudou = True
        while mudou:
            mudou = False
            for chave, delta in (("dx", p), ("dy", p), ("escala", p / 400.0), ("rot", p / 8.0)):
                for sinal in (1, -1):
                    c = dict(melhor)
                    c[chave] = c.get(chave, 1.0 if chave == "escala" else 0.0) + sinal * delta
                    if chave == "escala":
                        c["escala_y"] = c["escala"]
                    dc = diferenca(transformar(cru, c), ref)
                    if dc < d - 1e-6:
                        melhor, d, mudou = c, dc, True
    return melhor, d


def onde_muda(candidatos: dict, limiar: int = 40) -> list[int]:
    """Os pixels em que os quadros candidatos (já transformados) diferem entre si: os dígitos e a barra. Fora deles
    os vizinhos são iguais e a diferença de imagem só dilui (3D Warp: certo 2,38 × seguinte 2,55 na imagem inteira)."""
    qs = list(candidatos.values())
    return [i for i in range(len(qs[0])) if max(q[i] for q in qs) - min(q[i] for q in qs) > limiar]


def diferenca_em(a: bytes, b: bytes, pixels: list[int]) -> float:
    return sum(abs(a[i] - b[i]) for i in pixels) / len(pixels) if pixels else 0.0


def conferir_quadro(ref_cru: bytes, originais: dict, certo: int, t: dict) -> dict:
    """O quadro `certo` do original × os vizinhos em `originais` ({quadro: cru}), todos com a transformação `t`,
    contra o quadro do ref. `exato` = o certo é o MAIS próximo nos pixels que mudam, com folga (metade do vizinho), E a
    imagem inteira perto (`geometria_ok`: a transformação confere). Medido na BL04 R2: certa 1,6–2,4; giro com o sinal
    trocado 35, sem giro 34, posição Y trocada 27."""
    ref = reduzir(ref_cru)
    tr = {q: transformar(c, t) for q, c in originais.items()}
    px = onde_muda(tr)
    d = {q: round(diferenca_em(ref, x, px), 2) for q, x in tr.items()}
    viz = min(v for q, v in d.items() if q != certo)
    return {"dif": d[certo], "dif_vizinho": viz, "dif_imagem": round(diferenca(ref, tr[certo]), 2),
            "pixels": len(px), "geometria_ok": diferenca(ref, tr[certo]) < LIMIAR_IMAGEM,
            "exato": d[certo] * 2 < viz and diferenca(ref, tr[certo]) < LIMIAR_IMAGEM, "por_quadro": d}

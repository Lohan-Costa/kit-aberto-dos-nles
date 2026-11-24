"""Leitor do .prmf — a MÁSCARA DE OBJETO do Premiere 2026 (rotoscopia automática), guardada fora do projeto, em
"<projeto> Masks/<guid>.prmf" (o guid está no parâmetro 24 "Controlador" da `AE.ADBE AEMask2` com Type 4).

Formato (decifrado no laboratório, 2026-10-07, Premiere 26.0.2; `confirmado` contra a máscara perfeita do B10):
- cabeçalho de 32 bytes: 'prmf', versão (u32 = 2), posição do ÍNDICE (u64), tamanho do índice (u64), 32 (u64: onde
  começam os dados);
- os dados: um bloco por quadro, cada um um TileStream **GDeflate** (`lab/gdeflate.py`);
- o índice: **FlatBuffers** — raiz {versão, opções, vetor de quadros}; cada quadro: marcador (u32), CAIXA (x, y, largura,
  altura em px do quadro inteiro), tamanho do quadro (1920, 1080), TEMPO (u64, ticks do Premiere = 1/254016000000 s, no
  tempo da MÍDIA), posição e tamanho do bloco. Quadro sem máscara: caixa = o quadro inteiro e bloco de 1 byte.
- o bloco descomprimido: a máscara da CAIXA em MEIA resolução, 4 bits por pixel (16 níveis de opacidade), dois pixels por
  byte (o da ESQUERDA no nibble ALTO — medido: os bits 4–7 seguem as colunas da esquerda), linha de ceil(ceil(largura/2)/2)
  bytes, ceil(altura/2) linhas. Contra a máscara perfeita do B10: IoU 0,954 ampliando 2× (o Premiere renderiza 0,985 porque
  REFINA a borda com a imagem na hora — "ObjectMaskRefiner" no binário: o arquivo guarda só a máscara grossa).

    python3 -m lab.prmf arquivo.prmf            # resumo dos quadros
"""
from __future__ import annotations

import struct
import sys

from . import gdeflate

TICKS_POR_SEGUNDO = 254016000000


def _u32(b, o): return struct.unpack_from("<I", b, o)[0]
def _i32(b, o): return struct.unpack_from("<i", b, o)[0]
def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _u64(b, o): return struct.unpack_from("<Q", b, o)[0]


def _campos(b, t):
    vt = t - _i32(b, t)
    return [_u16(b, vt + 4 + 2 * k) for k in range((_u16(b, vt) - 4) // 2)]


def ler(caminho: str) -> list[dict]:
    """Os quadros do .prmf (sem descomprimir): tempo, caixa, onde está o bloco."""
    with open(caminho, "rb") as fh:
        d = fh.read()
    if d[:4] != b"prmf":
        raise ValueError("não é .prmf")
    pos_ind, tam_ind = _u64(d, 8), _u64(d, 16)
    b = d[pos_ind:pos_ind + tam_ind]
    vec = 20 + _u32(b, 20)
    quadros = []
    for i in range(_u32(b, vec)):
        t = vec + 4 + 4 * i + _u32(b, vec + 4 + 4 * i)
        c = _campos(b, t)
        caixa = [_u32(b, t + c[3] + 4 * j) for j in range(4)] if c[3] else None
        quadros.append({"ticks": _u64(b, t + c[1]) if c[1] else 0, "caixa": caixa,
                        "quadro_inteiro": (_u32(b, t + c[4]), _u32(b, t + c[4] + 4)) if c[4] else None,
                        "pos": _u64(b, t + c[2]) if c[2] else None, "tam": _u32(b, t + c[6]) if len(c) > 6 and c[6] else None})
    quadros.sort(key=lambda q: q["ticks"])
    for q in quadros:
        q["segundos"] = q["ticks"] / TICKS_POR_SEGUNDO
        q["_arquivo"] = caminho
    return quadros


def mascara(q: dict, dados: bytes | None = None) -> tuple[list, int, int] | None:
    """A máscara do quadro em MEIA resolução: (linhas de valores 0..15, largura, altura). None = quadro vazio."""
    if not q["caixa"] or not q["tam"] or q["tam"] < 16:
        return None
    if dados is None:
        with open(q["_arquivo"], "rb") as fh:
            fh.seek(q["pos"]); dados = fh.read(q["tam"])
    cru = gdeflate.descomprimir(dados)
    w2, h2 = (q["caixa"][2] + 1) // 2, (q["caixa"][3] + 1) // 2
    passo = (w2 + 1) // 2
    if passo * h2 != len(cru):
        raise ValueError(f"tamanho inesperado: {len(cru)} bytes para {w2}×{h2}")
    linhas = []
    for y in range(h2):
        lin = cru[y * passo:(y + 1) * passo]
        vals = []
        for byte in lin:
            vals.append(byte >> 4); vals.append(byte & 15)
        linhas.append(vals[:w2])
    return linhas, w2, h2


def alfa_quadro_inteiro(q: dict, largura: int = 1920, altura: int = 1080) -> bytearray:
    """A máscara no quadro inteiro, 1 byte por pixel (0..255), ampliando 2× a meia resolução (vizinho mais próximo)."""
    out = bytearray(largura * altura)
    m = mascara(q)
    if m is None:
        return out
    linhas, w2, h2 = m
    x0, y0, w, h = q["caixa"]
    for y in range(h):
        yy = y0 + y
        if not 0 <= yy < altura:
            continue
        src = linhas[y // 2]
        base = yy * largura
        for x in range(w):
            xx = x0 + x
            if 0 <= xx < largura:
                out[base + xx] = src[x // 2] * 17
    return out


def exportar_matte(caminho_prmf: str, saida: str, fps: float = 25, quadros: int | None = None,
                   largura: int = 1920, altura: int = 1080, tc: str | None = None) -> dict:
    """A máscara de objeto como VÍDEO DE MATTE (branco = objeto, ProRes 422 HQ), quadro a quadro no tempo da mídia — a
    camada de tradução: no Premiere 2023 vira Track Matte Key; no Resolve / After Effects, um matte externo."""
    import subprocess
    from .ffmpeg import achar
    qs = ler(caminho_prmf)
    por_quadro = {round(q["segundos"] * fps): q for q in qs}
    total = quadros or (max(por_quadro) + 1 if por_quadro else 0)
    cmd = [achar("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{largura}x{altura}",
           "-framerate", str(fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"]
    if tc:
        cmd += ["-timecode", tc]
    proc = subprocess.Popen(cmd + [saida], stdin=subprocess.PIPE)
    vazio = bytes(largura * altura)
    cheios = 0
    for n in range(total):
        q = por_quadro.get(n)
        if q is not None and q["caixa"] and (q["tam"] or 0) > 16:
            proc.stdin.write(alfa_quadro_inteiro(q, largura, altura)); cheios += 1
        else:
            proc.stdin.write(vazio)
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("o ffmpeg falhou")
    return {"saida": saida, "quadros": total, "com_mascara": cheios}


def main(argv=None) -> int:
    for arq in (argv or sys.argv[1:]):
        qs = ler(arq)
        cheios = [q for q in qs if q["caixa"] and (q["tam"] or 0) > 16]
        print(f"{arq}: {len(qs)} quadros ({len(cheios)} com máscara), de {qs[0]['segundos']:.2f} s a {qs[-1]['segundos']:.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

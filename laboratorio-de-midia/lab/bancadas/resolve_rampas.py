"""Bancada B22 com o RESOLVE como ORIGEM (2026-10-12; autor: completar o Resolve antes de corrigir o app de uma vez).

A forma da rampa NATIVA do Resolve vem do gabarito feito na interface dele (`03 CASOS/TEMPO/V01 RAMPAS DE VELOCIDADE/
TL COM VELOCIDADES EXEMPLOS parecido com aaf 01.drt`): `MediaTimemapBA` com keyframes lineares (`interp 0`) e, na
transição SUAVE, um keyframe `interp 1` com alças alinhadas às retas vizinhas (inclinação da alça de entrada = a
velocidade de antes; da de saída = a de depois). Aqui essa forma vai para a placa B02 23,976 (o quadro em código de
barras), nos três clipes do DRT do B22:
  A — 1,2× → keyframe Bézier no quadro 20 (alças de 8 quadros) → 1,9×           (in 0)
  B — 2× → Bézier no quadro 10 (alças de 8) → 0,6×; o IN no quadro 8, DENTRO da curva
  C — 50 % constante
O Resolve renderiza (a referência) e o LEITOR (`posicoes`) calcula a curva em cada quadro: a hipótese — Bézier cúbica
entre keyframes, P1 = kf + (XOut, YOut) e P2 = kf seguinte − (XIn, YIn) só onde `interp 1` — é medida contra o render.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import subprocess
import sys
import zipfile

from ..gerar import RAIZ

DLPC_MOTOR = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_DeLaPraCa", "motor")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "resolve", "B22")
MOLDE = os.path.join(RAIZ, "saida", "bancadas", "resolve", "molde_timemap_resolve.hex")
BASE = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B22_RAMPAS", "B22_PREMIERE_exato.drt")
DRT = os.path.join(TRAB, "B22_RESOLVE_ORIGEM.drt")
F = 24000 / 1001
NB = 240                                          # quadros da placa
N = 48


def _kf(x, y, interp=0, xin=0.0, yin=0.0, xout=0.0, yout=0.0):
    return {"X": x, "Y": y, "interp": interp, "XIn": xin, "YIn": yin, "XOut": xout, "YOut": yout}


def _suave(x, y, v_in, v_out, h):
    """O keyframe da transição suave, como o Resolve grava: alças de comprimento `h` em X, alinhadas às retas."""
    return _kf(x, y, 1, h, h * v_in, h, h * v_out)


def caso_A():
    """Em QUADROS (X da timeline, Y da fonte)."""
    y1 = 1.2 * 20
    x3 = 20 + (NB - 1 - y1) / 1.9
    return [_kf(0, 0), _suave(20, y1, 1.2, 1.9, 8), _kf(x3, NB - 1)], 0


def caso_B():
    y1 = 2 * 10
    x3 = 10 + (NB - 1 - y1) / 0.6
    return [_kf(0, 0), _suave(10, y1, 2, 0.6, 8), _kf(x3, NB - 1)], 8


def caso_C():
    return [_kf(0, 0), _kf((NB - 1) / 0.5, NB - 1)], 0


CASOS = {"RAMPA_A": caso_A, "RAMPA_B": caso_B, "RAMPA_C": caso_C}


def timemap(kfs_q: list[dict]) -> str:
    """O `MediaTimemapBA` no formato do gabarito (QHash de N keyframes; N precisa ter header conhecido — 2, 4, 6…)."""
    sys.path.insert(0, DLPC_MOTOR)
    from tools.inspect_drp import timemap_decode, timemap_encode, _pad_to_header_n
    d = timemap_decode(open(MOLDE).read().strip())
    kb = next(it for it in d["items"] if it["key"] == "KeyframesBA")
    modelo = kb["value"]["entries"][0]
    # completa até um N com header conhecido com pontos COLINEARES nos trechos lineares (não mexe na curva)
    pts = [(k["X"], k["Y"]) for k in kfs_q]
    cheio = _pad_to_header_n(pts) if len(pts) not in (4,) else pts
    kfs = []
    for x, y in cheio:
        orig = next((k for k in kfs_q if abs(k["X"] - x) < 1e-9), None)
        kfs.append(orig or _kf(x, y))
    if len(kfs) != 4:
        raise RuntimeError(f"{len(kfs)} keyframes: só o header do molde (4) foi preparado aqui")
    ents = []
    for i, k in enumerate(sorted(kfs, key=lambda k: k["X"])):
        e = copy.deepcopy(modelo)
        e["key"] = str(i)
        for c in e["value"]["entries"]:
            if c["key"] == "interp":
                c["value"]["int"] = int(k["interp"])
            else:
                c["value"]["dbl"] = float(k[c["key"]]) / F
        ents.append(e)
    kb["value"]["entries"] = list(reversed(ents))          # o gabarito guarda do último para o primeiro
    xmax = max(k["X"] for k in kfs) / F
    for it in d["items"]:
        if it["key"] in ("YMax", "LastValidYOffset"):
            it["value"]["dbl"] = (NB - 1) / F
        elif it["key"] == "XMax":
            it["value"]["dbl"] = xmax
        elif it["key"] == "UniqueId":
            import uuid
            it["value"]["str"] = str(uuid.uuid4())
    return timemap_encode(d)


def _quatro(kfs):
    """Os casos têm 3 (A, B) ou 2 (C) keyframes: completa até 4 com pontos colineares no trecho final (linear)."""
    kfs = list(kfs)
    while len(kfs) < 4:
        a, b = kfs[-2], kfs[-1]
        kfs.insert(-1, _kf((a["X"] + b["X"]) / 2 if a["interp"] == 0 else a["X"] + (b["X"] - a["X"]) * 0.75,
                           None))
        m = kfs[-2]
        m["Y"] = a["Y"] + (b["Y"] - a["Y"]) * (m["X"] - a["X"]) / (b["X"] - a["X"]) if a["interp"] == 0 else None
        if m["Y"] is None:                                   # depois de um Bézier: na reta de saída do trecho final
            m["Y"] = b["Y"] - (b["X"] - m["X"]) * (b["Y"] - a["Y"]) / (b["X"] - a["X"])
    return kfs


def montar() -> str:
    os.makedirs(TRAB, exist_ok=True)
    zin = zipfile.ZipFile(BASE)
    nomes = zin.namelist()
    seq = next(n for n in nomes if n.startswith("SeqContainer"))
    x = zin.read(seq).decode("utf-8")
    blocos = list(re.finditer(r"<Sm2TiVideoClip DbId=.*?</Sm2TiVideoClip>", x, re.S))
    blocos.sort(key=lambda m: int(re.search(r"<Start>(\d+)</Start>", m.group(0)).group(1)))
    if len(blocos) != 3:
        raise RuntimeError(f"{len(blocos)} clipes de vídeo no DRT base")
    novo = x
    for m, (nome, f) in zip(blocos, CASOS.items()):
        kfs, inq = f()
        b = m.group(0)
        b2 = re.sub(r"<MediaTimemapBA>[0-9a-f]+</MediaTimemapBA>",
                    lambda _m: f"<MediaTimemapBA>{timemap(_quatro(kfs))}</MediaTimemapBA>", b, count=1)
        b2 = re.sub(r"<In>.*?</In>|<In/>", lambda _m: f"<In>{inq}</In>" if inq else "<In/>", b2, count=1)
        novo = novo.replace(b, b2, 1)
    with zipfile.ZipFile(DRT, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in nomes:
            zout.writestr(n, novo.encode("utf-8") if n == seq else zin.read(n))
    return DRT


# ── o LEITOR (o lado Resolve da tradução): a posição da fonte em cada quadro ──
def _bez(p0, p1, p2, p3, u):
    a = 1 - u
    return a * a * a * p0 + 3 * a * a * u * p1 + 3 * a * u * u * p2 + u * u * u * p3


def avaliar(kfs: list[dict], x: float) -> float:
    kfs = sorted(kfs, key=lambda k: k["X"])
    for a, b in zip(kfs, kfs[1:]):
        if a["X"] <= x <= b["X"]:
            x1, y1 = (a["X"] + a["XOut"], a["Y"] + a["YOut"]) if a["interp"] == 1 else (a["X"], a["Y"])
            x2, y2 = (b["X"] - b["XIn"], b["Y"] - b["YIn"]) if b["interp"] == 1 else (b["X"], b["Y"])
            lo, hi = 0.0, 1.0
            for _ in range(60):
                u = (lo + hi) / 2
                if _bez(a["X"], x1, x2, b["X"], u) < x:
                    lo = u
                else:
                    hi = u
            return _bez(a["Y"], y1, y2, b["Y"], (lo + hi) / 2)
    return kfs[-1]["Y"]


def posicoes() -> dict:
    out = {}
    for nome, f in CASOS.items():
        kfs, inq = f()
        out[nome] = [avaliar(kfs, inq + k) for k in range(N)]
    return out


def medir(arq: str) -> dict:
    from lab import ler
    W, H = 1920, 1080
    g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-frames:v", "144", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    pos = posicoes()
    out = {}
    for i, nome in enumerate(CASOS):
        linhas = []
        for k in range(N):
            n = i * N + k
            lido = ler.ler_faixas(g[n * W * H:(n + 1) * W * H], W, H)[0]
            p = pos[nome][k]
            linhas.append((k, lido, round(p, 4), math.floor(p + 1e-6)))
        out[nome] = {"piso": sum(l[1] == l[3] for l in linhas), "n": len(linhas),
                     "fora": [l for l in linhas if l[1] != l[3]][:10], "linhas": linhas}
    with open(os.path.join(TRAB, "B22_RESOLVE_ORIGEM_medida.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0)
    return {k: {x: v[x] for x in ("piso", "n", "fora")} for k, v in out.items()}


# ⭐ MEDIDO (2026-10-12, B22, Resolve 19.0.0b Windows; 48/48 nos casos A e B): o keyframe `interp 1` NÃO passa pelo ponto
# gravado — ele ARREDONDA O CANTO: reta até a ponta da alça de entrada (kf − (XIn, YIn)), Bézier cúbica dela até a ponta
# da alça de saída (kf + (XOut, YOut)) com os DOIS controles internos no próprio keyframe, e reta de novo. A hipótese
# "Bézier entre keyframes com as alças como controles" (`avaliar`) errava perto do keyframe (até 2 quadros no B).
def avaliar_resolve(kfs: list[dict], x: float) -> float:
    kfs = sorted(kfs, key=lambda k: k["X"])
    for k in kfs:
        if k["interp"] == 1:
            xi, yi = k["X"] - k["XIn"], k["Y"] - k["YIn"]
            xo, yo = k["X"] + k["XOut"], k["Y"] + k["YOut"]
            if xi <= x <= xo:
                lo, hi = 0.0, 1.0
                for _ in range(60):
                    u = (lo + hi) / 2
                    if _bez(xi, k["X"], k["X"], xo, u) < x:
                        lo = u
                    else:
                        hi = u
                return _bez(yi, k["Y"], k["Y"], yo, (lo + hi) / 2)
    vs = []
    for k in kfs:
        if k["interp"] == 1:
            vs += [(k["X"] - k["XIn"], k["Y"] - k["YIn"]), (k["X"] + k["XOut"], k["Y"] + k["YOut"])]
        else:
            vs.append((k["X"], k["Y"]))
    vs.sort()
    for (x0, y0), (x1, y1) in zip(vs, vs[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return vs[-1][1]


def origem_json(arquivo_render: str) -> str:
    """As posições pelo leitor MEDIDO, no mesmo formato da origem do Avid (para os escritores de Premiere e Avid)."""
    segs = []
    for nome, f in CASOS.items():
        kfs, inq = f()
        pos = [avaliar_resolve(kfs, inq + k) for k in range(N)]
        segs.append({"in": 0, "render": 6 if nome == "RAMPA_C" else 2, "pos": pos})
    caminho = os.path.join(TRAB, "B22_RESOLVE_ORIGEM.json")
    json.dump({"nome": "B22_RESOLVE_ORIGEM", "arquivo": arquivo_render, "segmentos": segs}, open(caminho, "w"), indent=0)
    return caminho

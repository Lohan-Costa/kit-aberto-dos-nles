"""B10 ROTO — mídia sintética para MÁSCARA e TRACKING (rotoscopia): uma "pessoa" (silhueta com ciclo de caminhada) que
atravessa o quadro de um canto ao outro com movimento NÃO linear (curva em S, quase para no meio, encolhe com a
perspectiva, balança no passo) sobre um fundo com textura FIXA. Sai junto a MÁSCARA PERFEITA (branco = pessoa) e um
`verdade.json` com a posição, a escala e a caixa da pessoa em cada quadro — para medir por pixel a rotoscopia do NLE.

    python3 -m lab.roto receitas/base/B10_ROTO.json [--saida pasta] [--segundos N]

Só biblioteca padrão + ffmpeg (regra do laboratório). A pessoa é desenhada aqui (supersample 2×, bordas suaves) e
composta quadro a quadro; o ffmpeg só gera o fundo e codifica. Pedido do autor em 2026-10-07.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import subprocess
import sys

from . import ffmpeg as _ff

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CICLO = 12                       # quadros desenhados do ciclo de caminhada (um passo completo = 2 passadas)


# ── a pessoa ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _seg_dist2(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy or 1)))
    dx, dy = px - (ax + t * vx), py - (ay + t * vy)
    return dx * dx + dy * dy


def _desenhar(fase: float, h: int) -> tuple[int, int, list]:
    """Um quadro do ciclo: a pessoa de perfil andando para a DIREITA, altura `h` px (desenha em 2× e reduz)."""
    S = 2
    H = h * S
    W = int(H * 0.55)
    img = [[(0, 0, 0, 0)] * W for _ in range(H)]
    u = H / 100.0                                       # unidade: 1/100 da altura
    cx = W / 2
    quadril = (cx, 52 * u)
    ombro = (cx + 1.5 * u, 22 * u)
    ang_perna, ang_braco = math.radians(28) * math.sin(fase), math.radians(24) * math.sin(fase)
    joelho = max(0.0, math.sin(fase + math.pi / 2)) * math.radians(30)

    def perna(sinal, cor):
        a = sinal * ang_perna
        jx, jy = quadril[0] + math.sin(a) * 24 * u, quadril[1] + math.cos(a) * 24 * u
        b = a - (joelho if sinal > 0 else max(0.0, math.sin(fase - math.pi / 2)) * math.radians(30))
        px, py = jx + math.sin(b) * 23 * u, jy + math.cos(b) * 23 * u
        return [("seg", quadril, (jx, jy), 5.2 * u, cor), ("seg", (jx, jy), (px, py), 4.6 * u, cor),
                ("seg", (px, py), (px + 6 * u, py + 0.5 * u), 2.6 * u, (40, 30, 25))]       # pé

    def braco(sinal, cor):
        a = -sinal * ang_braco
        cotx, coty = ombro[0] + math.sin(a) * 16 * u, ombro[1] + math.cos(a) * 16 * u
        b = a + math.radians(18)
        mx, my = cotx + math.sin(b) * 15 * u, coty + math.cos(b) * 15 * u
        return [("seg", ombro, (cotx, coty), 3.6 * u, cor), ("seg", (cotx, coty), (mx, my), 3.0 * u, cor),
                ("circ", (mx, my), None, 2.8 * u, (205, 160, 125))]                          # mão

    partes = (perna(-1, (25, 35, 70)) + braco(-1, (150, 30, 35))                              # lado de trás, mais escuro
              + [("tronco", ombro, quadril, 9.5 * u, None)]
              + perna(1, (35, 50, 100))
              + [("circ", (cx + 3 * u, 11 * u), None, 7.5 * u, (215, 170, 135)),               # cabeça
                 ("cabelo", (cx + 1 * u, 8.5 * u), None, 7.8 * u, (45, 30, 20))]
              + braco(1, (200, 40, 45)))

    def cor_tronco(x, y):
        # camisa listrada (textura para o tracker) com um "logo" no peito (alvo para tracking planar)
        if abs(x - (cx + 4 * u)) < 4 * u and abs(y - 30 * u) < 4 * u:
            d = abs((x - (cx + 4 * u)) - (y - 30 * u)) < 1.1 * u or abs((x - (cx + 4 * u)) + (y - 30 * u)) < 1.1 * u
            return (20, 20, 20) if d else (250, 210, 30)
        return (225, 225, 225) if int((y - ombro[1]) / (3 * u)) % 2 == 0 else (190, 30, 40)

    for tipo, a, b, r, cor in partes:
        if tipo in ("seg", "tronco"):
            x0, x1 = int(min(a[0], b[0]) - r) - 1, int(max(a[0], b[0]) + r) + 2
            y0, y1 = int(min(a[1], b[1]) - r) - 1, int(max(a[1], b[1]) + r) + 2
        else:
            x0, x1, y0, y1 = int(a[0] - r) - 1, int(a[0] + r) + 2, int(a[1] - r) - 1, int(a[1] + r) + 2
        r2 = r * r
        for y in range(max(0, y0), min(H, y1)):
            linha = img[y]
            for x in range(max(0, x0), min(W, x1)):
                if tipo in ("seg", "tronco"):
                    dentro = _seg_dist2(x + .5, y + .5, a[0], a[1], b[0], b[1]) <= r2
                elif tipo == "cabelo":
                    dentro = (x + .5 - a[0]) ** 2 + (y + .5 - a[1]) ** 2 <= r2 and y + .5 < a[1] + 1.5 * u and x + .5 < a[0] + 5 * u
                else:
                    dentro = (x + .5 - a[0]) ** 2 + (y + .5 - a[1]) ** 2 <= r2
                if dentro:
                    c = cor_tronco(x, y) if tipo == "tronco" else cor
                    linha[x] = (c[0], c[1], c[2], 255)
    # reduz 2× (média): bordas suaves; cor pré-multiplicada para não escurecer a borda
    w, hh = W // S, H // S
    out = []
    for y in range(hh):
        linha = bytearray(w * 4)
        for x in range(w):
            sr = sg = sb = sa = 0
            for dy in range(S):
                for dx in range(S):
                    r_, g_, b_, a_ = img[y * S + dy][x * S + dx]
                    sr += r_ * a_; sg += g_ * a_; sb += b_ * a_; sa += a_
            if sa:
                linha[x * 4:x * 4 + 4] = bytes((sr // sa, sg // sa, sb // sa, sa // (S * S)))
        out.append(bytes(linha))
    return w, hh, out


# ── o trajeto ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _bezier(p, u):
    a, b, c, d = p
    m = 1 - u
    return (m ** 3 * a[0] + 3 * m * m * u * b[0] + 3 * m * u * u * c[0] + u ** 3 * d[0],
            m ** 3 * a[1] + 3 * m * m * u * b[1] + 3 * m * u * u * c[1] + u ** 3 * d[1])


def trajeto(r: dict, quadros: int) -> list[dict]:
    """Posição dos pés, escala e fase do passo em cada quadro. Velocidade NÃO constante: quase para em `pausa_no_meio`
    (gaussiana); o parâmetro da curva segue o comprimento de arco (sem isso a Bézier já acelera nas pontas)."""
    pz = r["pessoa"]
    pts = pz["trajeto_bezier"]
    amostras = [_bezier(pts, i / 2000) for i in range(2001)]
    arco = [0.0]
    for i in range(1, len(amostras)):
        arco.append(arco[-1] + math.dist(amostras[i - 1], amostras[i]))
    total = arco[-1]
    p = pz["pausa_no_meio"]
    vel = [1 - (1 - p["velocidade_minima"]) * math.exp(-(((i + .5) / quadros - p["em"]) / p["largura"]) ** 2) for i in range(quadros)]
    acum = [0.0]
    for v in vel:
        acum.append(acum[-1] + v)
    saida, fase, ultimo = [], 0.0, None
    for q in range(quadros):
        s = acum[q] / acum[-1] * total
        k = next(i for i in range(len(arco)) if arco[i] >= s) if s < total else len(arco) - 1
        x, y = amostras[k]
        u = k / (len(amostras) - 1)
        esc = 1 + (pz["escala_longe"] - 1) * u
        if ultimo is not None:
            fase += math.dist(ultimo, (x, y)) / (pz["passada_px"] * esc) * math.pi       # meia volta por passada
        ultimo = (x, y)
        saida.append({"quadro": q, "pes_x": round(x, 2), "pes_y": round(y, 2), "escala": round(esc, 4),
                      "fase": round(fase % (2 * math.pi), 4), "balanco": round(pz["balanco_px"] * esc * abs(math.sin(fase)), 2)})
    return saida


# ── o fundo ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _fundo(w: int, h: int, png: str) -> None:
    """Textura FIXA (piso xadrez + ruído determinístico + ondas) e alguns blocos de 'cenário': o tracker precisa de
    detalhe parado. Sem `drawtext` (regra do laboratório)."""
    ruido = "mod(abs(sin(X*12.9898+Y*78.233))*43758.5453\\,1)"
    xad = "mod(floor(X/96)+floor(Y/96)\\,2)"
    expr = {c: f"{base}+{amp}*{xad}+28*{ruido}+14*sin(X/37+{k})*sin(Y/53)" for c, base, amp, k in
            (("r", 70, 34, 0), ("g", 82, 30, 1), ("b", 96, 26, 2))}
    caixas = ["drawbox=x=120:y=90:w=260:h=180:color=0x2f6f4f:t=fill", "drawbox=x=1500:y=640:w=300:h=220:color=0x7a4a2a:t=fill",
              "drawbox=x=820:y=120:w=140:h=360:color=0x404070:t=fill", "drawbox=x=300:y=520:w=200:h=60:color=0xc0a040:t=fill",
              "drawbox=x=1300:y=80:w=420:h=40:color=0xd0d0d0:t=fill"]
    filtro = f"geq=r='{expr['r']}':g='{expr['g']}':b='{expr['b']}'," + ",".join(caixas)
    subprocess.run([_ff.achar("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=1,format=rgb24",
                    "-vf", filtro, "-frames:v", "1", png], check=True)


# ── gerar ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def gerar(caminho_receita: str, saida: str | None = None, segundos: float | None = None, avisar=print) -> str:
    with open(caminho_receita, encoding="utf-8") as fh:
        r = json.load(fh)
    W, H, fps = r["largura"], r["altura"], r["fps"]
    quadros = int(round((segundos or r["segundos"]) * fps))
    pasta = saida or os.path.join(RAIZ, "saida", "base", r["caso"])
    os.makedirs(pasta, exist_ok=True)
    avisar(f"{r['caso']}: desenhando o ciclo de caminhada ({CICLO} quadros)…")
    h0 = r["pessoa"]["altura_px_perto"]
    ciclo = [_desenhar(2 * math.pi * i / CICLO, h0) for i in range(CICLO)]
    caminho = trajeto(r, quadros)
    png = os.path.join(pasta, "_fundo.png")
    _fundo(W, H, png)
    img = os.path.join(pasta, r["saidas"]["imagem"])
    masc = os.path.join(pasta, r["saidas"]["mascara"])
    cmd = [_ff.achar("ffmpeg"), "-v", "error", "-y", "-loop", "1", "-framerate", str(fps), "-i", png,
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-framerate", str(fps), "-i", "-",
           "-filter_complex", "[1:v]split[p][q];[0:v][p]overlay=format=auto:shortest=1,format=yuv422p10le[img];"
                              "[q]alphaextract,format=yuv422p10le[m]",
           "-map", "[img]", "-c:v", "prores_ks", "-profile:v", "3", "-timecode", r["tc_inicio"], "-frames:v", str(quadros), img,
           "-map", "[m]", "-c:v", "prores_ks", "-profile:v", "3", "-timecode", r["tc_inicio"], "-frames:v", str(quadros), masc]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    vazio = bytes(W * 4)
    for q, pos in enumerate(caminho):
        cw, ch, linhas = ciclo[int(pos["fase"] / (2 * math.pi) * CICLO) % CICLO]
        esc = pos["escala"]
        tw, th = max(1, round(cw * esc)), max(1, round(ch * esc))
        x0 = round(pos["pes_x"] - tw / 2)
        y0 = round(pos["pes_y"] - th - pos["balanco"])
        quadro = bytearray(vazio * H)
        area = 0
        bx0 = by0 = 10 ** 9; bx1 = by1 = -1
        cols = [min(cw - 1, int((i + .5) * cw / tw)) for i in range(tw)]
        xa, xb = max(0, x0), min(W, x0 + tw)
        for j in range(th):
            y = y0 + j
            if y < 0 or y >= H or xa >= xb:
                continue
            src = linhas[min(ch - 1, int((j + .5) * ch / th))]
            linha = b"".join(src[c * 4:c * 4 + 4] for c in cols[xa - x0:xb - x0])
            quadro[(y * W + xa) * 4:(y * W + xb) * 4] = linha
            opacos = [k // 4 for k in range(3, len(linha), 4) if linha[k] >= 128]
            if opacos:
                area += len(opacos)
                bx0, bx1 = min(bx0, xa + opacos[0]), max(bx1, xa + opacos[-1] + 1)
                by0, by1 = min(by0, y), max(by1, y + 1)
        pos.update({"caixa": [bx0, by0, bx1, by1] if area else None,
                    "camada": [x0, y0, x0 + tw, y0 + th], "area_px": area,
                    "quadro_do_ciclo": int(pos["fase"] / (2 * math.pi) * CICLO) % CICLO})
        proc.stdin.write(quadro)
        if q % 50 == 0:
            avisar(f"  quadro {q}/{quadros}")
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("o ffmpeg falhou")
    os.remove(png)
    verdade = {"caso": r["caso"], "pergunta": r["pergunta"], "receita": "receitas/base/" + os.path.basename(caminho_receita),
               "gerado_em": datetime.date.today().isoformat(), "ffmpeg": _ff.versao()[0], "plataforma": sys.platform,
               "arquivos": {"imagem": os.path.basename(img), "mascara": os.path.basename(masc)},
               "formato": {"largura": W, "altura": H, "fps": fps, "quadros": quadros, "tc_inicio": r["tc_inicio"],
                           "codec": "ProRes 422 HQ (yuv422p10le)"},
               "convencoes": {"quadro": "a partir de 0", "pes": "o ponto entre os pés (base da pessoa), em px do quadro",
                              "caixa": "[x0, y0, x1, y1] justa da silhueta (alfa >= 50%) DENTRO do quadro; null = fora",
                              "camada": "[x0, y0, x1, y1] do desenho inteiro (com a sobra transparente), pode sair do quadro",
                              "area_px": "pixels com alfa >= 50% (a máscara binária tem esta área)",
                              "mascara": "branco = pessoa, preto = fundo, borda suave de 1 px (supersample 2×)"},
               "quadros": caminho}
    with open(os.path.join(pasta, "verdade.json"), "w", encoding="utf-8") as fh:
        json.dump(verdade, fh, ensure_ascii=False, indent=1)
    avisar(f"{r['caso']}: {img}\n  máscara: {masc}\n  verdade: {os.path.join(pasta, 'verdade.json')}")
    return pasta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("receita"); ap.add_argument("--saida"); ap.add_argument("--segundos", type=float)
    a = ap.parse_args(argv)
    gerar(a.receita, a.saida, a.segundos)
    return 0


if __name__ == "__main__":
    sys.exit(main())

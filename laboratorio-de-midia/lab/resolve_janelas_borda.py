"""A BORDA em px das Power Windows Polygon, Curve e Gradient (pedido do autor, 2026-11-20).

Parte do corrector CAPTURADO de cada tipo (gestos pilotados no 19.1.4, `resolve_janelas_tipos.py`) e troca só o valor
medido; a forma fica a padrão (Polygon: o retângulo ±480 × ±270; Curve: o mesmo retângulo escrito por nós como triplas
Bézier; Gradient: a linha no centro). Num quadro BRANCO, Gain 0 no Primaries ⇒ a janela fica PRETA. Mede o perfil
atravessando a borda: onde a máscara passa 10 / 50 / 90 %.

Pergunta da escrita (Curve): com só `…12/13` (Inside/Outside) e as curvas `…07/08` IGUAIS à forma, o Resolve recalcula
a borda? (Se não, quem escreve tem de calcular as curvas deslocadas.)

    python lab/resolve_janelas_borda.py <pasta com os .bin capturados>
"""
import copy
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab import resolve_janela as J
from lab.bancadas import resolve as R
from lab.bancadas import resolve_cor as C
from lab.resolve_janelas_tipos import corretores, no_com

POL_IN, POL_OUT = 0x08B00010, 0x08B00011
CUR_FORMA, CUR_DENTRO, CUR_FORA = 0x08D00006, 0x08D00007, 0x08D00008
CUR_IN, CUR_OUT, CUR_SOFT, CUR_PIVO_X, CUR_PIVO_Y = 0x08D00012, 0x08D00013, 0x08D00018, 0x08D00010, 0x08D00011
GRAD_SOFT = 0x08F0000B
#: valores ESCRITOS de propósito fora do padrão — os que a escala deve deixar de lado ficam no default capturado
ESCALAS = {0x08B00009: 1.0, 0x08B0000A: 1.0, 0x08D0000B: 1.0, 0x08D0000C: 1.0}


def _params(msg: list) -> list:
    """A lista de parâmetros (`6 → 2 → 3…`) de um corrector decodificado."""
    from lab.resolve_janelas_tipos import _dec
    m6 = _dec(next(c["value"] for c in msg if c["field"] == 6))
    return _dec(next(c["value"] for c in m6 if c["field"] == 2))


def com_valores(msg: list, valores: dict) -> list:
    """Cópia do corrector com cada `{id: valor}` posto: float → f32; lista de pontos → a lista Bézier (campo 9)."""
    from lab.resolve_janelas_tipos import _dec
    msg = copy.deepcopy(msg)
    m6 = _dec(next(c["value"] for c in msg if c["field"] == 6))
    m2 = _dec(next(c["value"] for c in m6 if c["field"] == 2))
    for pid, v in valores.items():
        novo = (C.p_f32(pid, v) if isinstance(v, float) else
                C._campo(3, C._msg((1, pid), (2, C._msg((9, [C._campo(1, [C._campo(1, float(x)), C._campo(2, float(y))])
                                                              for x, y in v]))))))
        for i, c in enumerate(m2):
            if c["field"] == 3 and next((x["value"] for x in _dec(c["value"]) if x["field"] == 1), None) == pid:
                m2[i] = novo
                break
        else:
            m2.append(novo)
    for c in m6:
        if c["field"] == 2:
            c["value"] = m2
    for c in msg:
        if c["field"] == 6:
            c["value"] = m6
    return msg


def retangulo_bezier(w: float, h: float) -> list:
    """O retângulo ±w × ±h como triplas Bézier (alças = o ponto: lados retos), fechado como a UI grava (13 pontos)."""
    cantos = [(-w, h), (w, h), (w, -h), (-w, -h)]
    pts = [p for c in cantos for p in (c, c, c)]
    return pts + [cantos[0]]


def borda(perfil: np.ndarray) -> dict:
    """Onde o perfil (0 fora → 1 dentro) cruza 10 / 50 / 90 % (a primeira subida, subpixel)."""
    out = {}
    for n in (0.1, 0.5, 0.9):
        i = int(np.argmax(perfil >= n))
        out[f"{int(n * 100)}"] = round(float(i - 1 + (n - perfil[i - 1]) / max(perfil[i] - perfil[i - 1], 1e-9)), 1) \
            if i > 0 else None
    return out


def main() -> None:
    pasta = sys.argv[1]
    cs_pol = dict(corretores(open(os.path.join(pasta, "pol_1.bin"), "rb").read()))[5]
    cs_grad = dict(corretores(open(os.path.join(pasta, "grad_2.bin"), "rb").read()))[18]
    cs_cur = dict(corretores(open(os.path.join(pasta, "curva.bin"), "rb").read()))[6]
    ret = retangulo_bezier(480.0, 270.0)
    cur_base = {CUR_FORMA: ret, CUR_DENTRO: ret, CUR_FORA: ret, CUR_PIVO_X: 0.0, CUR_PIVO_Y: 0.0,
                0x08D0000B: 1.0, 0x08D0000C: 1.0, 0x08D00009: 0.0, 0x08D0000A: 0.0, 0x08D00004: 0.0}
    casos = [
        ("Polygon In 0 Out 0", cs_pol, {}),
        ("Polygon In 10", cs_pol, {POL_IN: 0.4}),
        ("Polygon In 30", cs_pol, {POL_IN: 1.2}),
        ("Polygon Out 10", cs_pol, {POL_OUT: 0.4}),
        ("Polygon Out 30", cs_pol, {POL_OUT: 1.2}),
        ("Gradient Soft 2", cs_grad, {}),
        ("Gradient Soft 5", cs_grad, {GRAD_SOFT: 500.0}),
        ("Gradient Soft 10", cs_grad, {GRAD_SOFT: 1000.0}),
        ("Curve só os valores In 10 Out 20", cs_cur, {**cur_base, CUR_IN: 10.0, CUR_OUT: 60.0}),
        ("Curve Soft 1 = 10", cs_cur, {**cur_base, CUR_SOFT: 0.1}),
        ("Curve sem borda", cs_cur, cur_base),
        ("Gradient Soft 0", cs_grad, {GRAD_SOFT: 0.0}),
    ]
    r = R.conectar()
    p = C.projeto(r)
    tl = C.achar_timeline(p, J.TL)
    p.SetCurrentTimeline(tl)
    r.OpenPage("color")
    itens = sorted(tl.GetItemListInTrack("video", 1) or [], key=lambda it: it.GetStart())
    assert len(itens) >= len(casos), "a timeline MASCARA precisa de um clipe por caso"
    for (nome, base, vals), it in zip(casos, itens):
        b = C.body([no_com(com_valores(base, vals))])
        print(nome, "aplicado" if C.aplicar(tl, it, b, "borda_" + nome.replace(" ", "_")) else "FALHOU", flush=True)
    C.salvar(r)
    video = C.renderizar(r, J.TL, "JANELAS_BORDA")
    medidas = []
    for k, (nome, _, _) in enumerate(casos):
        q = J.quadro(video, k * C.QUADROS + C.MEIO)
        dentro = 1 - (q / max(q.max(), 1e-9)).clip(0, 1)
        np.save(video.replace(".mov", f"_{k}.npy"), dentro.astype(np.float32))
        if nome.startswith("Gradient"):
            perfil = dentro[:, 960][::-1]                 # de baixo para cima: 0 (fora) → 1 (dentro)
            m = {"perfil": "coluna 960, de baixo para cima", **borda(perfil)}
        else:
            perfil = dentro[540, :960]                    # da borda esquerda do quadro para o centro
            m = {"perfil": "linha 540, da esquerda para o centro (a borda da forma em x = 480)", **borda(perfil)}
        m["max"] = round(float(dentro.max()), 3)
        medidas.append({"caso": nome, **m})
        print(json.dumps(medidas[-1], ensure_ascii=False), flush=True)
    json.dump(medidas, open(video.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

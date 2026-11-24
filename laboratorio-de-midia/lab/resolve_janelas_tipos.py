"""As 5 POWER WINDOWS do Resolve ESCRITAS por `.drx` e renderizadas (pedido do autor, 2026-11-20: mapear as janelas).

Os correctors de janela foram capturados de gestos pilotados na paleta Window do 19.1.4 (um campo por vez → o `Body` da
cópia do `Project.db`). Aqui cada um é RE-ESCRITO num nó novo — o corrector Primaries (tipo 1) com Gain 0 + o corrector
da janela capturado — e aplicado a um quadro BRANCO: a janela (não invertida) fica PRETA. Prova que a escrita de cada
tipo funciona e dá a geometria em px. Tipos de corrector: 3 Linear · 4 Circular · 5 Polygon · 6 Curve · 18 Gradient.

    python lab/resolve_janelas_tipos.py <pasta com os .bin capturados>    (Resolve aberto no LAB COR RESOLVE)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab import resolve_janela as J
from lab.bancadas import resolve as R
from lab.bancadas import resolve_cor as C

TIPOS = {3: "Linear", 4: "Circular", 5: "Polygon", 6: "Curve", 18: "Gradient"}
#: o .bin capturado de cada tipo (o último estado da série pilotada)
CAPTURAS = [("lin_outside70.bin", 3), ("pol_outside20_1.bin", 5), ("grad_soft110_2.bin", 18), ("cur_opac60.bin", 6),
            ("lin.bin", 3), ("pol_1.bin", 5), ("grad_2.bin", 18)]


def _dec(v):
    _, dec, _ = C._motor()
    return v if isinstance(v, list) else dec(bytes(v))


def corretores(body: bytes) -> list:
    """Os correctors (os `9.1`) do 1º nó do Body capturado, já decodificados: [(tipo, mensagem), …]."""
    _, dec, _ = C._motor()
    g = _dec(dec(body)[0]["value"])
    no = next(x for x in g if x["field"] == 7)
    c9 = _dec(next(c["value"] for c in _dec(no["value"]) if c["field"] == 9))
    out = []
    for x in c9:
        if x["field"] == 1:
            m = _dec(x["value"])
            out.append((next(c["value"] for c in m if c["field"] == 1), m))
    return out


def no_com(corretor_janela: list) -> dict:
    """O nó: Primaries (Gain 0) + o corrector da janela capturado, como veio."""
    prim = (1, C._msg((1, 1), (3, 1), (6, C._msg((2, C._msg((1, 1)) + [C.p_f32(J.GAIN, 0.0)])))))
    campos = [(1, 1), (2, 1), (4, 190), (5, 180), (7, 1), (8, 44),
              (9, C._msg(prim) + [C._campo(1, corretor_janela)] + C._msg((2, bytes.fromhex("0304050612")))),
              (10, bytes.fromhex("0a0a08818080800c12021002"))]
    return C._campo(7, C._msg(*campos))


def main() -> None:
    pasta = sys.argv[1]
    r = R.conectar()
    p = C.projeto(r)
    tl = C.achar_timeline(p, J.TL)
    p.SetCurrentTimeline(tl)
    r.OpenPage("color")
    itens = sorted(tl.GetItemListInTrack("video", 1) or [], key=lambda it: it.GetStart())
    casos = []
    for (arq, tipo), it in zip(CAPTURAS, itens):
        cs = dict(corretores(open(os.path.join(pasta, arq), "rb").read()))
        b = C.body([no_com(cs[tipo])])
        ok = C.aplicar(tl, it, b, f"tipo_{tipo}_{arq[:-4]}")
        casos.append((arq, TIPOS[tipo], ok))
        print(TIPOS[tipo], arq, "aplicado" if ok else "FALHOU", flush=True)
    C.salvar(r)
    video = C.renderizar(r, J.TL, "JANELAS_TIPOS")
    medidas = []
    for k, (arq, nome, ok) in enumerate(casos):
        q = J.quadro(video, k * C.QUADROS + C.MEIO)
        q = q / max(q.max(), 1e-9)
        dentro = 1 - q.clip(0, 1)                     # a janela = o que ficou preto
        ys, xs = np.nonzero(dentro > 0.5)
        caixa = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None
        np.save(video.replace(".mov", f"_{k}.npy"), dentro.astype(np.float32))
        medidas.append({"caso": arq, "tipo": nome, "aplicado": ok, "caixa_50": caixa,
                        "area_50": int((dentro > 0.5).sum()), "max": round(float(dentro.max()), 3)})
        print(json.dumps(medidas[-1], ensure_ascii=False), flush=True)
    json.dump(medidas, open(video.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

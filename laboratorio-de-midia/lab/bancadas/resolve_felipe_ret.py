"""PRODUCAO-H LAB — os charts no lugar da mídia de um projeto real do Resolve (2026-11-20, pedido do autor).

O projeto do autor (PRODUCAO-H) foi exportado para `.drp` e importado como "PRODUCAO-H LAB" (pasta LABORATORIO do
Resolve); o original não é tocado. `inventario.json` (em `saida/bancadas/resolve_felipe_ret/`) tem, por mídia, as
propriedades do pool (resolução, taxa, TC, quadros, espaço de cor, PAR) e os trechos usados nas timelines CONFORM_OK
(a v01) e COLOR_v05.

    python -m lab.bancadas.resolve_felipe_ret charts      (gera os charts, 3 de uma vez)

Medido no 21.1 (A003_C023): `MediaPoolItem.ReplaceClip` casa o quadro pelo TC (o trecho 347–353 virou 47–53 de um
chart que começa no quadro 300), mantém os nós e VOLTA o espaço de cor de entrada para "Project" — repor depois.
Por isso cada chart cobre só do primeiro ao último quadro usado (± FOLGA), com o TC de origem.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import sys
import time


RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "resolve_felipe_ret")
CHARTS = os.path.join(TRABALHO, "charts")
FOLGA = 24


def _arquivo(nome: str) -> str:
    base = os.path.splitext(nome)[0]
    return re.sub(r"[^\w.\- ]", "_", base)[:80] + ".mov"


def planos() -> list[dict]:
    inv = json.load(open(os.path.join(TRABALHO, "inventario.json"), encoding="utf-8"))
    out = []
    for uid, d in inv.items():
        p = d["props"]
        if p.get("Type") == "Still" or not d["usos"]:
            continue
        w, h = (int(x) for x in p["Resolution"].split("x"))
        total = int(p["Frames"])
        lo = max(0, min(a for a, b in d["usos"]) - FOLGA)
        hi = min(total - 1, max(b for a, b in d["usos"]) + FOLGA)
        out.append({"uid": uid, "nome": d["nome"], "w": w, "h": h, "fps": str(p["FPS"]), "tc": p["Start TC"],
                    "primeiro": lo, "n": hi - lo + 1, "saida": os.path.join(CHARTS, _arquivo(d["nome"])),
                    "props": p})
    return out


def _um(pl: dict) -> tuple[str, float, str]:
    t = time.time()
    if os.path.exists(pl["saida"] + ".verdade.json"):
        return pl["nome"], 0.0, "ja existia"
    from .. import cor_charts_reais as cc      # numpy: fora do Python do Resolve (que só roda `trocar`)
    cc.gerar(pl["nome"], pl["w"], pl["h"], pl["fps"], pl["tc"], pl["primeiro"], pl["n"], pl["saida"], codec="hevc")
    return pl["nome"], time.time() - t, "ok"


def charts(paralelo: int = 3) -> None:
    pls = planos()
    os.makedirs(CHARTS, exist_ok=True)
    with open(os.path.join(TRABALHO, "planos.json"), "w", encoding="utf-8") as fh:
        json.dump(pls, fh, ensure_ascii=False, indent=1)
    pls.sort(key=lambda p: -p["w"] * p["h"] * p["n"])
    print(f"{len(pls)} charts, {sum(p['w'] * p['h'] * p['n'] for p in pls) / 1e9:.0f} Gpx", flush=True)
    with cf.ThreadPoolExecutor(paralelo) as ex:
        futs = {ex.submit(_um, p): p for p in pls}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                nome, s, st = f.result()
                print(f"[{i}/{len(pls)}] {st} {s:5.0f}s {nome}", flush=True)
            except Exception as e:  # noqa: BLE001 — um chart que falha não para os outros
                print(f"[{i}/{len(pls)}] FALHOU {futs[f]['nome']}: {e}", flush=True)


PROPS_DE_VOLTA = ("Input Color Space", "Input Gamma", "PAR")


def trocar(project, de: int = 0, ate: int | None = None, prazo_s: float = 45) -> dict:
    """Roda DENTRO do Resolve (MCP `run_script_unsafe`, projeto PRODUCAO-H LAB aberto): troca cada mídia pelo chart
    (`ReplaceClip`) e repõe o espaço de cor de entrada, a gama e o PAR do original (a troca os volta ao padrão).
    Em lotes (`de`/`ate`, índices de `planos.json`) para caber nos 60 s do MCP; para sozinha perto do `prazo_s`."""
    t0 = time.time()
    pls = json.load(open(os.path.join(TRABALHO, "planos.json"), encoding="utf-8"))[de:ate]
    itens = {}

    def varrer(pasta):
        # ⛔ o `GetUniqueId()` MUDA numa importação nova do .drp: casar pelo caminho ORIGINAL (e pelo nome)
        for c in pasta.GetClipList() or []:
            itens[c.GetUniqueId()] = c
            itens["caminho:" + (c.GetClipProperty("File Path") or "")] = c
            itens["nome:" + c.GetName()] = c
        for sub in pasta.GetSubFolderList() or []:
            varrer(sub)
    varrer(project.GetMediaPool().GetRootFolder())
    feitos, falhas, ultimo = [], [], de - 1
    for i, pl in enumerate(pls, de):
        if time.time() - t0 > prazo_s:
            break
        mp = (itens.get(pl["uid"]) or itens.get("caminho:" + pl["props"].get("File Path", ""))
              or itens.get("caminho:" + pl["saida"]) or itens.get("nome:" + pl["nome"]))
        if mp is None or not os.path.exists(pl["saida"] + ".verdade.json"):
            falhas.append([i, pl["nome"], "sem item" if mp is None else "sem chart"])
            ultimo = i
            continue
        if mp.GetClipProperty("File Path") != pl["saida"]:
            if not mp.ReplaceClip(pl["saida"]):
                falhas.append([i, pl["nome"], "ReplaceClip False"])
                ultimo = i
                continue
        volta = {k: mp.SetClipProperty(k, pl["props"][k]) for k in PROPS_DE_VOLTA if pl["props"].get(k)}
        lido = {k: mp.GetClipProperty(k) for k in PROPS_DE_VOLTA}
        errado = {k: (pl["props"][k], lido[k]) for k in volta if str(lido[k]) != str(pl["props"][k])}
        feitos.append([i, pl["nome"], errado] if errado else i)
        ultimo = i
    return {"feitos": feitos, "falhas": falhas, "proximo": ultimo + 1, "total": de + len(pls)}


STILLS = os.path.join(TRABALHO, "stills")


def _tc(frame: int, base: int = 24) -> str:
    f, s = frame % base, frame // base
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"


def _timeline(project, nome):
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t.GetName() == nome:
            return t
    raise KeyError(nome)


def quadros(project, nome: str) -> list[dict]:
    """O quadro do MEIO de cada clipe de vídeo da timeline `nome` (em quadros da timeline), com o item que está no
    topo ali — o still mostra o topo; um clipe coberto por outro não aparece."""
    tl = _timeline(project, nome)
    out = []
    for tr in range(1, tl.GetTrackCount("video") + 1):
        for it in tl.GetItemListInTrack("video", tr) or []:
            if it.GetMediaPoolItem() is None:
                continue
            out.append({"frame": (it.GetStart() + it.GetEnd()) // 2, "trilha": tr, "nome": it.GetName(),
                        "item": it.GetUniqueId()})
    return sorted(out, key=lambda d: d["frame"])


def stills(resolve, project, nome: str, lista: list[dict], de: int = 0, prazo_s: float = 45, pagina: str = "edit") -> dict:
    """Roda DENTRO do Resolve: um PNG por quadro de `lista` (`stills/<nome>/<frame>.png`), a partir de `de`."""
    t0 = time.time()
    tl = _timeline(project, nome)
    project.SetCurrentTimeline(tl)
    # ⛔ na página COLOR o Resolve 21.1 caiu (bad_alloc) com este projeto, 3 vezes; a Edit mostra a imagem já gradeada
    resolve.OpenPage(pagina)
    pasta = os.path.join(STILLS, nome)
    os.makedirs(pasta, exist_ok=True)
    feitos, i = [], de
    while i < len(lista) and time.time() - t0 < prazo_s:
        fr = lista[i]["frame"]
        alvo = os.path.join(pasta, f"{fr:06d}.png")
        if not os.path.exists(alvo):
            tl.SetCurrentTimecode(_tc(fr))
            topo = tl.GetCurrentVideoItem()
            ok = project.ExportCurrentFrameAsStill(alvo)
            feitos.append([fr, bool(ok), topo.GetUniqueId() if topo else None])
        i += 1
    return {"feitos": feitos, "proximo": i, "total": len(lista)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["charts"]:
        charts()

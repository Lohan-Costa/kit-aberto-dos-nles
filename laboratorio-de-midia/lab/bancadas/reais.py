"""Downgrade de PROJETOS REAIS (de produção, mídia offline): o que o rebaixado chega a mostrar no Premiere mais velho,
comparado com o que o original mostra na versão em que foi salvo. Os originais NUNCA são usados: as cópias moram em
`MIDIAS DE TESTES/1 PRODUCOES/<produção>/PROJETOS/` (autor, 2026-10-07: "não use os originais").

    python3 -m lab.bancadas.reais origem   <projeto.prproj>            # no Premiere da versão de origem
    python3 -m lab.bancadas.reais destino  <projeto.prproj> <versão>   # no Premiere da versão-alvo (rebaixa e abre)
    python3 -m lab.bancadas.reais comparar <projeto.prproj> <versão>

Trabalho em `saida/bancadas/reais/<nome>/` (fora do Git); o resultado em `resultados/REAIS/<nome>-<de>-para-<para>.json`.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

from . import premiere as p
from . import premiere_projeto as pp
from .. import prproj_downgrade

RAIZ = pp.RAIZ


def _trab(projeto: str) -> str:
    return os.path.join(RAIZ, "saida", "bancadas", "reais", os.path.splitext(os.path.basename(projeto))[0])


def _fechar_sem_salvar() -> None:
    # ANTES de copiar por cima: copiar o .prproj sobre o que está aberto fez o Premiere perguntar "Project Modified"
    # (diálogo SEM título, que o vigia não reconhece) — 2026-10-07
    p.executar("(function(){ try { if (app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return 1; })()")


def _abrir_e_retratar(caminho: str) -> dict:
    t0 = time.time()
    p.executar("app.openDocument(%s, true, true, true)" % pp._js(caminho), timeout=900)
    aberto = p.executar("(function(){ try { return app.project.path; } catch (e) { return ''; } })()")
    if aberto != caminho:
        return {"abriu": False, "path": aberto, "s": round(time.time() - t0, 1)}
    r = pp.retrato()
    r["abriu"] = True
    r["s_para_abrir"] = round(time.time() - t0, 1)
    # fecha SEM salvar: o retrato é do arquivo como chegou
    p.executar("(function(){ try { app.project.closeDocument(0, 0); } catch (e) {} return 1; })()")
    return r


def origem(projeto: str) -> dict:
    v = p.executar("app.version")
    d = os.path.join(_trab(projeto), f"{v}-origem")
    os.makedirs(d, exist_ok=True)
    _fechar_sem_salvar()
    copia = os.path.join(d, os.path.basename(projeto))
    shutil.copyfile(projeto, copia)
    r = _abrir_e_retratar(copia)
    with open(os.path.join(d, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)
    return r


def destino(projeto: str, para: str) -> dict:
    v = p.executar("app.version")
    if v != para:
        raise SystemExit(f"a ponte respondeu do Premiere {v}, não do {para}")
    d = os.path.join(_trab(projeto), f"rebaixado-para-{para}")
    os.makedirs(d, exist_ok=True)
    _fechar_sem_salvar()
    alvo = os.path.join(d, os.path.basename(projeto))
    rb = prproj_downgrade.rebaixar(projeto, alvo, para)
    shutil.copyfile(alvo, os.path.join(d, "rebaixado-antes-de-abrir.prproj"))
    r = _abrir_e_retratar(alvo)
    r["rebaixar"] = rb
    with open(os.path.join(d, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)
    return r


def sanidade(projeto: str, para: str) -> dict:
    """O rebaixado para `para` (uma versão que NÃO está nesta máquina, ex.: 23.2) aberto na versão ABERTA, que o
    converte: não prova que o `para` aceita, mas pega arquivo malformado — o projeto tem de vir igual ao original."""
    v = p.executar("app.version")
    origem_dir = os.path.join(_trab(projeto), f"rebaixado-para-{para}")
    d = os.path.join(_trab(projeto), f"rebaixado-para-{para}-aberto-no-{v}")
    os.makedirs(d, exist_ok=True)
    _fechar_sem_salvar()
    alvo = os.path.join(d, os.path.basename(projeto))
    shutil.copyfile(os.path.join(origem_dir, os.path.basename(projeto)), alvo)
    r = _abrir_e_retratar(alvo)
    with open(os.path.join(d, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)
    return r


def comparar(projeto: str, para: str, pasta: str | None = None) -> dict:
    base = _trab(projeto)
    orig = [x for x in os.listdir(base) if x.endswith("-origem")][0]
    with open(os.path.join(base, orig, "retrato.json"), encoding="utf-8") as fa, \
            open(os.path.join(base, pasta or f"rebaixado-para-{para}", "retrato.json"), encoding="utf-8") as fb:
        a, b = json.load(fa), json.load(fb)
    out = {"projeto": os.path.basename(projeto), "origem": a.get("versao"), "destino": b.get("versao"), "abriu": b.get("abriu"),
           "rebaixar": b.get("rebaixar"), "s_para_abrir": b.get("s_para_abrir")}
    if a.get("abriu") and b.get("abriu"):
        na, nb = pp.normalizar(a), pp.normalizar(b)
        out["sequencias"] = len(na["sequencias"])
        out["itens"] = sum(len(t) for s in na["sequencias"].values() for t in s["video"] + s["audio"])
        out["diferencas"] = pp.diferencas(na["sequencias"], nb["sequencias"])
        # os bins por CAMINHO (a ordem muda quando um bin tem nome que depende do idioma: "Clipes recuperados")
        def plano(lista, cam=""):
            for e in lista:
                c = cam + "/" + e["nome"]
                if e.get("filhos") is not None:
                    yield from plano(e["filhos"], c)
                if e["tipo"] != 2:
                    yield (c, e.get("tipo"), (e.get("midia") or ""), e.get("entrada"), e.get("saida"), e.get("rotulo"),
                           bool(e.get("merged")), bool(e.get("sequencia")))
        pa, pb = set(plano(na["bins"])), set(plano(nb["bins"]))
        out["itens_de_bin"] = [len(pa), len(pb)]
        out["bins_so_na_origem"] = sorted(pa - pb)
        out["bins_so_no_destino"] = sorted(pb - pa)
    dest = os.path.join(RAIZ, "resultados", "REAIS", f"{out['projeto'].rsplit('.', 1)[0]}-{out['origem']}-para-{para}.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    os.chdir(RAIZ)
    if argv[0] == "origem":
        r = origem(argv[1])
        print({k: r.get(k) for k in ("versao", "abriu", "s_para_abrir")}, "sequências:", len(r.get("sequencias", [])))
    elif argv[0] == "destino":
        r = destino(argv[1], argv[2])
        print({k: r.get(k) for k in ("versao", "abriu", "s_para_abrir")}, "sequências:", len(r.get("sequencias", [])))
    elif argv[0] == "sanidade":
        r = sanidade(argv[1], argv[2])
        print({k: r.get(k) for k in ("versao", "abriu", "s_para_abrir")}, "sequências:", len(r.get("sequencias", [])))
    elif argv[0] == "comparar":
        r = comparar(argv[1], argv[2], argv[3] if len(argv) > 3 else None)
        print({k: r.get(k) for k in ("projeto", "origem", "destino", "abriu", "sequencias", "itens", "itens_de_bin")},
              "diferenças nas sequências:", len(r.get("diferencas", [])), "| bins só na origem:", r.get("bins_so_na_origem", [])[:4],
              "| só no destino:", r.get("bins_so_no_destino", [])[:4])
        for x in r.get("diferencas", [])[:25]:
            print("  ", str(x)[:240])
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

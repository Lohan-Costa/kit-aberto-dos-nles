"""O teste de DOWNGRADE: o projeto que um Premiere mais novo salvou, rebaixado (`lab/prproj_downgrade.py`), aberto
no mais velho pela ponte e conferido como uma rodada normal.

    python3 -m lab.bancadas.downgrade_premiere 26.0.2 25.6.5               # os 6 casos (reabre o Premiere do destino)
    python3 -m lab.bancadas.downgrade_premiere 27.1.0 26.0.2 B05_RASTERS   # um caso, no destino já aberto

Por caso: (1) rebaixa `resultados/<caso>/prproj/premiere-<origem>-darwin.prproj`; (2) abre no destino; (3) compara
cada sequência, trilha e item com o que a origem tinha (`saida/bancadas/premiere-<origem>/<caso>/premiere.json`) ANTES
de a bancada tocar no projeto; (4) stills + renders + conferir contra a verdade, gravado como
`resultados/<caso>/premiere-<destino>-darwin-downgrade-<maior da origem>.json`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

from . import premiere as p
from .. import prproj_downgrade

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASOS = ["B01_FORMATOS", "B02_TAXAS", "B03_LAYOUTS_DE_AUDIO", "B04_TIMECODE", "B05_RASTERS", "B06_SOM_DIRETO"]
ANO = {"23": "2023", "25": "2025", "26": "2026", "27": "2027"}  # versão maior → como a bancada abre o app (o 27 era o Beta até 2026-11-15)


def _log(*a) -> None:
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def _inventario() -> dict:
    return p.executar(p._LIB + """(function(){ var it=_lab_itens(app.project.rootItem), midia=[], seqs={};
      for (var i=0;i<it.length;i++) if (it[i].getMediaPath()) midia.push(it[i].getMediaPath());
      for (var i=0;i<app.project.sequences.numSequences;i++) { var s=app.project.sequences[i]; seqs[s.name]=_lab_seqinfo(s); }
      return {midia: midia, sequencias: seqs}; })()""")


def _comparar(inv: dict, ref: dict) -> list[str]:
    """O que o destino leu do projeto rebaixado × o que a origem tinha gravado nele."""
    dif = []
    ref_midia = {c["File Path"] for c in ref["pool"]}
    if set(inv["midia"]) != ref_midia:
        dif.append(f"mídia: faltam {sorted(ref_midia - set(inv['midia']))}, sobram {sorted(set(inv['midia']) - ref_midia)}")
    for t in ref["timelines"]:
        s = inv["sequencias"].get(t["nome"])
        if not s:
            dif.append(f"{t['nome']}: sequência não veio")
            continue
        for campo, a, b in (("zero", s["zero"], t.get("zero_ticks", s["zero"])), ("timebase", int(s["timebase"]), t["timebase"]),
                            ("fim", int(s["fim"]) // int(s["timebase"]), t["fim_quadro"]),
                            ("resolução", [s["largura"], s["altura"]], t.get("resolucao", [s["largura"], s["altura"]]))):
            if a != b:
                dif.append(f"{t['nome']}: {campo} {a!r} ≠ {b!r} (origem)")
        for tipo in ("video", "audio"):
            a = [(x["trilha"], [(i["nome"], i["inicio"], i["fim"], i["entrada"]) for i in x["itens"]]) for x in s[tipo] if x["itens"]]
            b = [(x["trilha"], [(i["nome"], i["inicio"], i["fim"], i["entrada"]) for i in x["itens"]]) for x in t["trilhas"][tipo] if x["itens"]]
            if a != b:
                dif.append(f"{t['nome']}: trilhas de {tipo} diferem: destino {a} × origem {b}")
    return dif


def um_caso(nome: str, de: str, para: str) -> dict:
    caso = f"saida/base/{nome}"
    trab = f"saida/bancadas/downgrade-{de}-para-{para}/{nome}"
    proj = "LAB " + nome.replace("_", " ")
    os.makedirs(trab, exist_ok=True)
    alvo = os.path.abspath(os.path.join(trab, proj + ".prproj"))
    p.salvar_e_fechar()
    if os.path.exists(os.path.join(trab, "premiere.json")):
        os.remove(os.path.join(trab, "premiere.json"))
    origem = f"resultados/{nome}/prproj/premiere-{de}-darwin.prproj"
    r = prproj_downgrade.rebaixar(origem, alvo, para)
    shutil.copyfile(alvo, os.path.join(trab, "rebaixado-antes-de-abrir.prproj"))
    _log("rebaixado", r)
    aberto = p.executar("app.openDocument(%s, true, true, true)" % json.dumps(alvo), timeout=120)
    caminho = p.executar("(function(){ try { return app.project.path; } catch (e) { return ''; } })()")
    if caminho != alvo:
        return {"abriu": False, "openDocument": aberto, "path": caminho}
    with open(f"saida/bancadas/premiere-{de}/{nome}/premiere.json", encoding="utf-8") as fh:
        ref = json.load(fh)
    dif = _comparar(_inventario(), ref)
    _log(f"abriu; diferenças de estrutura contra o {de}:", dif or "nenhuma")
    p.preparar(caso, trab, proj)
    if nome == "B05_RASTERS":
        p.sequencias_hd(trab, os.path.abspath(f"{caso}/B05_HD_MOV-PRORES.mov"))
    if nome == "B06_SOM_DIRETO":
        p.sync_por_tc(trab, "B06_CAM_MOV-PRORES.mov", "B06_SOM_WAV-BWF.wav")
    st = p.stills(trab)
    if nome != "B05_RASTERS":
        p.renderizar(trab, ANO[para.split(".")[0]])
    dados = p._ler(trab)
    dados["variante"] = "downgrade-" + de.split(".")[0]
    dados["downgrade"] = {"origem": origem, "rebaixar": r, "diferencas_contra_a_origem": dif}
    p._gravar(trab, dados)
    c = subprocess.run([sys.executable, "-m", "lab.bancadas.conferir", trab, caso], capture_output=True, text=True)
    _log("conferir", c.returncode, c.stdout[-1200:], c.stderr[-800:])
    return {"abriu": True, "diferencas": dif, "stills_ok": all(all(v) for v in st.values()), "conferir": c.returncode}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    de, para, so = argv[0], argv[1], argv[2:]
    os.chdir(RAIZ)
    ano = ANO[para.split(".")[0]]
    if not so:
        p.reabrir_premiere(ano)
    p.esperar_ponte(240)
    v = p.executar("app.version")
    if v != para:
        raise SystemExit(f"a ponte respondeu do Premiere {v}, não do {para}")
    for nome in CASOS:
        if so and nome not in so:
            continue
        _log("==", nome)
        _log(um_caso(nome, de, para))
    p.salvar_e_fechar()
    _log("FIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

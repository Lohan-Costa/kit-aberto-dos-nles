"""O inventário da API de script de uma versão do Premiere, perguntado à PRÓPRIA API (`reflect` do ExtendScript):
os métodos e propriedades de cada objeto do DOM e do QE, num projeto do laboratório. Comparar versões mostra o que
nasce e o que some — antes de desenhar um caso que dependa de um verbo (multicam, cor, títulos, efeitos).

    python3 -m lab.bancadas.premiere_api                 # no Premiere aberto → resultados/API_PREMIERE/<versão>.json
    python3 -m lab.bancadas.premiere_api a.json b.json   # compara dois inventários
"""
from __future__ import annotations

import json
import os
import sys

from . import premiere as p

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Uma pergunta POR OBJETO, gravada antes da próxima: perguntar tudo numa chamada só DERRUBOU o 25.6.5 (2026-10-07,
# "Ocorreu um erro" + a ponte caiu). O que derrubar fica em `derrubou` e é pulado na próxima vez.
_FN = r"""function _lab_nomes(o) { var r = {metodos: [], propriedades: []};
    if (!o) return null;
    try { var m = o.reflect.methods; for (var i = 0; i < m.length; i++) r.metodos.push(String(m[i].name)); } catch (e) { r.erro_m = String(e); }
    try { var p = o.reflect.properties; for (var i = 0; i < p.length; i++) r.propriedades.push(String(p[i].name)); } catch (e) { r.erro_p = String(e); }
    r.metodos.sort(); r.propriedades.sort(); return r; }
function _lab_obj(nome) { var s = app.project.activeSequence, tv = s.videoTracks[0], ti = tv.clips[0];
  var it = _lab_itens(app.project.rootItem), clipe = null;
  for (var i = 0; i < it.length; i++) if (it[i].getMediaPath() && !clipe) clipe = it[i];
  switch (nome) {
    case "Application": return app; case "Project": return app.project; case "ProjectItem": return clipe;
    case "FootageInterpretation": return clipe.getFootageInterpretation();
    case "Sequence": return s; case "SequenceSettings": return s.getSettings(); case "Track": return tv;
    case "TrackItem": return ti; case "Component": return ti.components[0]; case "ComponentParam": return ti.components[0].properties[0];
    case "Encoder": return app.encoder; case "SourceMonitor": return app.sourceMonitor; case "Markers": return s.markers;
    case "Time": return s.getPlayerPosition(); }
  app.enableQE(); var qp = qe.project, qs = qp.getActiveSequence();
  switch (nome) {
    case "QE": return qe; case "QEProject": return qp; case "QESequence": return qs;
    case "QETrack": return qs.getVideoTrackAt(0); case "QETrackItem": return qs.getVideoTrackAt(0).getItemAt(0); }
  return null; }
"""
OBJETOS = ["Application", "Project", "ProjectItem", "FootageInterpretation", "Sequence", "SequenceSettings", "Track",
           "TrackItem", "Component", "ComponentParam", "Encoder", "SourceMonitor", "Markers", "Time",
           "QE", "QEProject", "QESequence", "QETrack", "QETrackItem"]
LISTAS = {"efeitos_de_video": "getVideoEffectList", "efeitos_de_audio": "getAudioEffectList",
          "transicoes_de_video": "getVideoTransitionList"}
_COMPONENTES = r"""(function(){ var s = app.project.activeSequence, ti = s.videoTracks[0].clips[0], o = [];
  for (var i = 0; i < ti.components.numItems; i++) { var c = ti.components[i], ps = [];
    for (var j = 0; j < c.properties.numItems; j++) ps.push(c.properties[j].displayName);
    o.push({nome: c.displayName, match: c.matchName, parametros: ps}); }
  return o; })()"""


def inventario(projeto: str, destino: str) -> dict:
    inv = {}
    if os.path.isfile(destino):
        with open(destino, encoding="utf-8") as fh:
            inv = json.load(fh)
    derrubou = set(inv.get("derrubou", []))

    def grava():
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(inv, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    p.salvar_e_fechar()
    p.executar("app.openDocument(%s, true, true, true)" % json.dumps(os.path.abspath(projeto)), timeout=120)
    p.executar("(function(){ var s = app.project.sequences[0]; app.project.openSequence(s.sequenceID); return 1; })()")
    inv["versao"] = p.executar("app.version")
    perguntas = [(o, p._LIB + _FN + "_lab_nomes(_lab_obj(%s))" % json.dumps(o)) for o in OBJETOS]
    perguntas += [(k, p._LIB + _FN + "(function(){ app.enableQE(); return qe.project.%s(); })()" % f) for k, f in LISTAS.items()]
    perguntas += [("componentes_do_clipe", _COMPONENTES)]
    for nome, js in perguntas:
        if nome in inv or nome in derrubou:
            continue
        inv["perguntando"] = nome
        grava()                      # se o Premiere cair aqui, o arquivo diz em quem
        valor = p.executar(js, timeout=120)
        if nome in LISTAS and isinstance(valor, str):
            valor = sorted(x for x in valor.split(";") if x)    # o QE devolve uma lista separada por ";"
        inv[nome] = valor
    inv.pop("perguntando", None)
    grava()
    p.salvar_e_fechar()
    return inv


def comparar(a: dict, b: dict) -> dict:
    out = {"versoes": [a.get("versao"), b.get("versao")]}
    for k in sorted(set(a) | set(b)):
        va, vb = a.get(k), b.get(k)
        if isinstance(va, dict) and isinstance(vb, dict) and "metodos" in va:
            d = {c: {"so_no_primeiro": sorted(set(va[c]) - set(vb[c])), "so_no_segundo": sorted(set(vb[c]) - set(va[c]))}
                 for c in ("metodos", "propriedades")}
            if any(x for c in d.values() for x in c.values()):
                out[k] = d
        elif isinstance(va, list) and isinstance(vb, list) and all(isinstance(x, str) for x in va + vb):
            if set(va) != set(vb):
                out[k] = {"so_no_primeiro": sorted(set(va) - set(vb)), "so_no_segundo": sorted(set(vb) - set(va))}
        elif k in ("versao", "perguntando", "derrubou"):
            continue
        elif va is None or vb is None:
            out[k] = {"so_no_primeiro" if vb is None else "so_no_segundo": True}
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2:
        with open(argv[0], encoding="utf-8") as fa, open(argv[1], encoding="utf-8") as fb:
            print(json.dumps(comparar(json.load(fa), json.load(fb)), ensure_ascii=False, indent=1))
        return 0
    v = p.executar("app.version")
    proj = os.path.join(RAIZ, "saida", "bancadas", f"premiere-{v}", "B06_SOM_DIRETO", "LAB B06 SOM DIRETO.prproj")
    destino = os.path.join(RAIZ, "resultados", "API_PREMIERE", f"premiere-{v}-{sys.platform}.json")
    if os.path.isfile(destino):          # a última vez caiu? quem estava sendo perguntado entra em `derrubou`
        with open(destino, encoding="utf-8") as fh:
            ant = json.load(fh)
        if ant.get("perguntando"):
            ant["derrubou"] = sorted(set(ant.get("derrubou", [])) | {ant.pop("perguntando")})
            with open(destino, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(ant, fh, ensure_ascii=False, indent=1)
    inv = inventario(proj, destino)
    print(destino, {k: len(x["metodos"]) for k, x in inv.items() if isinstance(x, dict) and "metodos" in x})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

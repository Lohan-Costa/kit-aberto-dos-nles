"""Bancada B20_DESFOQUE no Premiere — o Gaussian Blur em vários "Blurriness" sobre o degrau, render em ProRes 4444.

    python -m lab.bancadas.premiere_desfoque          (com o Premiere aberto e a ponte no ar)
"""
from __future__ import annotations

import json
import os
import sys

from . import premiere as p
from . import premiere_relink as r
from .. import desfoque_b20 as m
from ..gerar import RAIZ

CASO = os.path.join(RAIZ, "saida", "base", "B20_DESFOQUE")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B20_DESFOQUE")
PROJETO = os.path.join(TRAB, "B20 DESFOQUE.prproj")
J = p._js
TPF = 254016000000 * 1001 // 24000
N = 12


def x(codigo: str, timeout: float = 600):
    r.TRAB = TRAB
    return r.x(codigo, timeout)


def montar() -> object:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    if os.path.exists(PROJETO):
        os.remove(PROJETO)
    x("app.newProject(%s)" % J(PROJETO))
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J([m.gerar(CASO)]))
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), pi = null; for (var i = 0; i < it.length; i++) if (it[i].name == "B20_DEGRAU.mov") pi = it[i];
      var s = app.project.createNewSequenceFromClips("B20", [pi], app.project.rootItem); s.name = "B20";
      while (s.videoTracks[0].clips.numItems) s.videoTracks[0].clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      var vals = %(vals)s, o = [];
      var ti = new Time(), to = new Time(); ti.ticks = "0"; to.ticks = String(%(n)d * %(tpf)d); pi.setInPoint(ti, 4); pi.setOutPoint(to, 4);
      for (var i = 0; i < vals.length; i++) { var q = new Time(); q.ticks = String(i * %(n)d * %(tpf)d); s.videoTracks[0].overwriteClip(pi, q); }
      app.project.openSequence(s.sequenceID); app.enableQE(); qe.project.init();
      var qt = qe.project.getActiveSequence().getVideoTrackAt(0), k = 0;
      for (var j = 0; j < qt.numItems; j++) { var qi = qt.getItemAt(j); if (qi.type == "Empty") continue;
        qi.addVideoEffect(qe.project.getVideoEffectByName("Gaussian Blur")); k++; }
      var c = s.videoTracks[0].clips;
      for (var j = 0; j < c.numItems; j++) {
        var comp = null; for (var u = 0; u < c[j].components.numItems; u++) if (c[j].components[u].displayName == "Gaussian Blur") comp = c[j].components[u];
        for (var u = 0; u < comp.properties.numItems; u++) if (comp.properties[u].displayName == "Blurriness") comp.properties[u].setValue(vals[j], true);
        o.push([j, comp.matchName, vals[j]]);
      }
      app.project.save(); return o; })()""" % {"vals": json.dumps(m.VALORES_PREMIERE), "n": N, "tpf": TPF})


def renderizar() -> str:
    arq = os.path.join(TRAB, "renders", "B20_PREMIERE.mov")
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    if os.path.exists(arq):
        os.remove(arq)
    pre = os.path.join(os.path.dirname(p.preset_prores("2023")), "Match Source - Apple ProRes 4444.epr")
    print(x("app.project.activeSequence.exportAsMediaDirect(%s, %s, 0)" % (J(arq), J(pre)), timeout=900))
    return arq


def main(argv=None) -> int:
    p.esperar_ponte(120)
    print(montar())
    arq = renderizar()
    res = [(v, round(m.medir(arq, quadro=i * N + 5), 2)) for i, v in enumerate(m.VALORES_PREMIERE)]
    print("Blurriness → largura 10–90 % (px):", res)
    with open(os.path.join(TRAB, "medida.json"), "w", encoding="utf-8") as f:
        json.dump(res, f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

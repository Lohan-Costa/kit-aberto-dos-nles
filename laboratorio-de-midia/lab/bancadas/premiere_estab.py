"""Bancada B19_ESTABILIZADOR no Premiere — aplica o Warp Stabilizer no clipe tremido (`lab.estab_b19`), espera a análise,
ajusta o método/resultado, salva e renderiza.

    python -m lab.bancadas.premiere_estab montar          (projeto + efeito; a análise roda em segundo plano)
    python -m lab.bancadas.premiere_estab params          (os parâmetros do efeito, como a API os vê)
    python -m lab.bancadas.premiere_estab ajustar M R     (Method = M, Result = R pelos índices do menu)
    python -m lab.bancadas.premiere_estab render NOME     (salva e renderiza a sequência)
"""
from __future__ import annotations

import os
import sys

from . import premiere as p
from . import premiere_relink as r
from ..gerar import RAIZ

CASO = os.path.join(RAIZ, "saida", "base", "B19_ESTABILIZADOR")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B19_ESTABILIZADOR")
PROJETO = os.path.join(TRAB, "B19 ESTABILIZADOR.prproj")
J = p._js

ACHAR = r"""function _b19_comp() { var s = app.project.activeSequence, c = s.videoTracks[0].clips[0];
  for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName == "Warp Stabilizer") return c.components[k];
  return null; }"""


def x(codigo: str, timeout: float = 600):
    r.TRAB = TRAB
    return r.x(ACHAR + "\n" + codigo, timeout)


def montar() -> object:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    if os.path.exists(PROJETO):
        os.remove(PROJETO)
    x("app.newProject(%s)" % J(PROJETO))
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J([os.path.join(CASO, "B19_TREMIDO.mov")]))
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), pi = null; for (var i = 0; i < it.length; i++) if (it[i].name == "B19_TREMIDO.mov") pi = it[i];
      var s = app.project.createNewSequenceFromClips("B19", [pi], app.project.rootItem); s.name = "B19";
      app.project.openSequence(s.sequenceID); app.enableQE(); qe.project.init();
      var qc = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0);
      qc.addVideoEffect(qe.project.getVideoEffectByName("Warp Stabilizer"));
      app.project.save();
      return _b19_comp() ? "efeito aplicado" : "sem efeito"; })()""")


def params() -> object:
    return x(r"""(function(){ var c = _b19_comp(), o = [];
      for (var j = 0; j < c.properties.numItems; j++) { var pr = c.properties[j], v = null;
        try { v = pr.getValue(); } catch (e) { v = "?"; }
        o.push([j, pr.displayName, String(v).slice(0, 60)]); }
      return o; })()""")


def ajustar(nome_metodo: str, valor_metodo, nome_resultado: str, valor_resultado) -> object:
    return x(r"""(function(){ var c = _b19_comp(), o = [];
      for (var j = 0; j < c.properties.numItems; j++) { var pr = c.properties[j];
        if (pr.displayName == %s) { pr.setValue(%s, true); o.push(pr.displayName + "=" + pr.getValue()); }
        if (pr.displayName == %s) { pr.setValue(%s, true); o.push(pr.displayName + "=" + pr.getValue()); } }
      app.project.save(); return o; })()""" % (J(nome_metodo), J(valor_metodo), J(nome_resultado), J(valor_resultado)))


def renderizar(nome: str) -> object:
    arq = os.path.join(TRAB, "renders", nome + ".mov")
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    if os.path.exists(arq):
        os.remove(arq)
    return x("(function(){ app.project.save(); return app.project.activeSequence.exportAsMediaDirect(%s, %s, 0); })()"
             % (J(arq), J(p.preset_prores("2023"))), timeout=900)


def esperar(ate_s: float = 900) -> list:
    """Espera a análise E a estabilização: o rótulo do parâmetro 1 ("40% (frame 60 of 144)", "Stabilizing…") vazio e o
    AnalysisStatusCounter parado em 3 leituras seguidas (o Premiere processa em segundo plano; renderizar antes sai com
    parte dos quadros sem correção — medido 2026-10-10)."""
    import time
    hist, t0 = [], time.time()
    while time.time() - t0 < ate_s:
        pr = params()
        rotulo, cont = pr[1][1], next((v for _, n, v in pr if n == "AnalysisStatusCounter"), None)
        hist.append((rotulo, cont))
        if len(hist) >= 3 and all(r == "" for r, _ in hist[-3:]) and len({c for _, c in hist[-3:]}) == 1:
            return hist
        time.sleep(5)
    raise TimeoutError(hist[-5:])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    p.esperar_ponte(120)
    if argv[0] == "montar":
        print(montar())
    elif argv[0] == "params":
        for linha in params():
            print(linha)
    elif argv[0] == "ajustar":
        print(ajustar("Method", int(argv[1]), "Result", int(argv[2])))
    elif argv[0] == "esperar":
        print(esperar()[-3:])
    elif argv[0] == "render":
        print(renderizar(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

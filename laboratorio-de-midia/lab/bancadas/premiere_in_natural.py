"""B18, rodada 3 — o in NATURAL: marcado pela API num quadro inteiro da mídia (como o editor no monitor de fonte), clipe a
1× numa timeline de 23,976, SEM escrever no XML. Separa o comportamento de um projeto editado de verdade do projeto montado
à força (rodada 2: teto × R04: piso).

    python -m lab.bancadas.premiere_in_natural
"""
from __future__ import annotations

import json
import math
import os
import sys

from . import premiere as P
from . import premiere_in_lento as B
from .. import in_lento_b18 as m

CASOS = [(25, 208), (25, 209), (25, 211), (60, 503), (60, 505), (100, 833), (100, 838)]


def main() -> int:
    P.esperar_ponte(120)
    TPF, TPS = m.TPF, m.TPS
    proj = os.path.join(B.TRAB, "B18 NATURAL.prproj")
    B.x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    if os.path.exists(proj):
        os.remove(proj)
    B.x("app.newProject(%s)" % P._js(proj))
    B.x("app.project.importFiles(%s, true, app.project.rootItem, false)" % P._js([B.FUNDO, m.placa(25), m.placa(60), m.placa(100)]))
    r = B.x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), por = {}; for (var i = 0; i < it.length; i++) por[it[i].name] = it[i];
      var s = app.project.createNewSequenceFromClips("NAT", [por["B14_FUNDO.mov"]], app.project.rootItem); s.name = "NAT";
      while (s.videoTracks[0].clips.numItems) s.videoTracks[0].clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      var casos = %s, o = [];
      for (var i = 0; i < casos.length; i++) {
        var fps = casos[i][0], n = casos[i][1], pi = por["B18_PLACA_" + fps + ".mp4"], tpm = 254016000000 / fps;
        var ti = new Time(), to = new Time(); ti.ticks = String(n * tpm); to.ticks = String((n + 40) * tpm);
        pi.setInPoint(ti, 4); pi.setOutPoint(to, 4);
        var q = new Time(); q.ticks = String(i * 12 * %d); s.videoTracks[0].overwriteClip(pi, q);
        var c = s.videoTracks[0].clips, al = null;
        for (var j = 0; j < c.numItems; j++) if (Math.abs(c[j].start.ticks - i * 12 * %d) < 1000) al = c[j];
        var fim = new Time(); fim.ticks = String((i + 1) * 12 * %d); al.end = fim;
        o.push([fps, n, al.inPoint.ticks]);
      }
      app.project.save(); return o; })()""" % (json.dumps(CASOS), TPF, TPF, TPF))
    print("o que o Premiere guardou:", flush=True)
    for fps, n, t in r:
        t = int(t)
        print("  %3d qps in %d → inPoint %.4f quadros da mídia (%.4f da timeline)" % (fps, n, t / (TPS // fps), t / TPF), flush=True)
    arq = os.path.join(B.TRAB, "renders", "NAT.mov")
    if os.path.exists(arq):
        os.remove(arq)
    pre = os.path.join(os.path.dirname(P.preset_prores("2023")), "Match Source - Apple ProRes 4444.epr")
    print(B.x("app.project.activeSequence.exportAsMediaDirect(%s, %s, 0)" % (P._js(arq), P._js(pre)), timeout=900), flush=True)
    nums = B.ler(arq)
    saida = []
    for i, (fps, n, t) in enumerate(r):
        t, tpm = int(t), TPS // fps
        vis = nums[i * 12:i * 12 + 6]
        piso = [math.floor((math.floor(t / TPF + 1e-9) * TPF + k * TPF) / tpm + 1e-6) for k in range(6)]
        exato = [math.floor((t + k * TPF) / tpm + 1e-6) for k in range(6)]
        teto = [math.floor((math.ceil(t / TPF - 1e-9) * TPF + k * TPF) / tpm + 1e-6) for k in range(6)]
        print("  %3d qps in %d: visto %s | piso %s | exato %s | teto %s" % (fps, n, vis, piso, exato, teto), flush=True)
        saida.append({"fps": fps, "in": n, "visto": vis, "piso": piso, "exato": exato, "teto": teto})
    with open(os.path.join(B.TRAB, "medida_natural.json"), "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

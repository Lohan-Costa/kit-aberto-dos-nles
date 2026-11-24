"""Bancada B14_MASCARA no Premiere — a VERDADE da máscara de opacidade pelo RENDER (o `exportFramePNG` não desenha
máscara: caso R04, 2026-10-10).

    python -m lab.bancadas.premiere_mascara            (com o Premiere aberto e a ponte no ar)
    python -m lab.bancadas.premiere_mascara medir      (só lê o render já feito)

Monta pela API a sequência (FUNDO na V1, um clipe da FRENTE por segmento do `lab.mascara_b14.PLANO` na V2, Zoom nos
segmentos que pedem), salva, fecha, põe as máscaras no XML (`mascara_b14.aplicar`; a API não cria máscara), reabre,
renderiza (`exportAsMediaDirect`, ProRes) e mede o alfa por coluna em cada quadro. Grava em
`saida/bancadas/premiere/B14_MASCARA/` (projeto, render, `premiere.json`) e o resumo em `resultados/B14_MASCARA/`.
"""
from __future__ import annotations

import json
import os
import sys
import time

from . import premiere as p
from . import premiere_relink as r
from .. import mascara_b14 as m
from ..gerar import RAIZ

CASO = os.path.join(RAIZ, "saida", "base", "B14_MASCARA")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B14_MASCARA")
PROJETO = os.path.join(TRAB, "B14 MASCARA.prproj")
CRU = os.path.join(TRAB, "B14 MASCARA (sem mascaras).prproj")
RENDER = os.path.join(TRAB, "renders", "B14_RENDER.mov")
RENDERIZADOR = "Mercury Playback Engine Software Only"
ANO = "2023"
J = p._js


def x(codigo: str, timeout: float = 600):
    r.TRAB = TRAB
    return r.x(codigo, timeout)


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    for a in (CRU, PROJETO):
        if os.path.exists(a):
            os.remove(a)
    x("app.newProject(%s)" % J(CRU))
    x("(function(){ app.enableQE(); qe.project.init(); return qe.project.setRenderer(%s); })()" % J(RENDERIZADOR))
    arqs = [os.path.join(CASO, f"B14_{n}.mov") for n in m.CLIPES]
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J(arqs))
    # ⚠️ 23.2: o clipe que entra com out = N quadros sai com N − 1 (medido 2026-10-10) — o out vai 1 quadro adiante
    segs = [{"clipe": f"B14_{s['clipe']}.mov", "ini": m.inicio(i) * 1001 / 24000, "dur": (s["quadros"] + 1) * 1001 / 24000,
             "zoom": s.get("zoom")} for i, s in enumerate(m.PLANO)]
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), por = {}; for (var i = 0; i < it.length; i++) por[it[i].name] = it[i];
      var segs = %(segs)s;
      var s = app.project.createNewSequenceFromClips("B14", [por["B14_FUNDO.mov"]], app.project.rootItem); s.name = "B14";
      while (s.videoTracks[0].clips.numItems) s.videoTracks[0].clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      s.videoTracks[0].overwriteClip(por["B14_FUNDO.mov"], 0);
      var v2 = s.videoTracks[1];
      for (var i = 0; i < segs.length; i++) {
        var pi = por[segs[i].clipe]; pi.setInPoint(0, 4); pi.setOutPoint(segs[i].dur, 4);
        v2.overwriteClip(pi, segs[i].ini);
      }
      function comp(c, mn) { for (var k = 0; k < c.components.numItems; k++) if (c.components[k].matchName == mn) return c.components[k]; }
      function prop(k, n) { for (var j = 0; j < k.properties.numItems; j++) if (k.properties[j].displayName == n) return k.properties[j]; }
      var c = v2.clips, o = [];
      for (var i = 0; i < c.numItems; i++) {
        if (segs[i] && segs[i].zoom) prop(comp(c[i], "AE.ADBE Motion"), "Scale").setValue(segs[i].zoom, true);
        o.push(c[i].name + "@" + c[i].start.ticks + "-" + c[i].end.ticks);
      }
      var st = s.getSettings();
      app.project.save();
      return {v2: o, v1: s.videoTracks[0].clips.numItems, fps: st.videoFrameRate.seconds, w: st.videoFrameWidth, h: st.videoFrameHeight};
    })()""" % {"segs": json.dumps(segs)})


def mascaras() -> dict:
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    feitos = m.aplicar(CRU, PROJETO)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return {"mascaras": feitos, "abriu": x("app.project.path")}


def renderizar() -> dict:
    os.makedirs(os.path.dirname(RENDER), exist_ok=True)
    if os.path.exists(RENDER):
        os.remove(RENDER)
    t0 = time.time()
    res = x("""(function(){ var s = _lab_seq("B14"); app.project.openSequence(s.sequenceID);
      return app.project.activeSequence.exportAsMediaDirect(%s, %s, 0); })()""" % (J(RENDER), J(p.preset_prores(ANO))),
          timeout=900)
    return {"job": str(res), "s": round(time.time() - t0, 1), "existe": os.path.exists(RENDER)}


def medir_lista(ler, quadros: list[int]) -> list:
    """`ler(q)` → RGB do quadro q da timeline (render do Premiere ou still do Resolve). Por quadro: a borda medida (px da
    timeline) × a do contorno, e a largura 10–90 %."""
    out = []
    for i, s in enumerate(m.PLANO):
        for k in range(s["quadros"]):
            q = m.inicio(i) + k
            if q not in quadros:
                continue
            rgb = ler(q)
            if rgb is None:
                continue
            b = m.borda(m.perfil(rgb))
            zoom = (s.get("zoom") or 100) / 100
            esperado = m.W / 2 + (m.x_em(s, k) - 0.5) * m.W * zoom
            out.append({"rotulo": s["rotulo"], "quadro": q, "k": k, "contorno_px": round(esperado, 2),
                        **{c: (round(v, 2) if isinstance(v, float) else v) for c, v in b.items()}})
    return out


def medir(arquivo: str = RENDER, pular_meio: bool = False) -> list:
    qs = [m.inicio(i) + k for i, s in enumerate(m.PLANO) for k in range(s["quadros"])
          if not (pular_meio and "anim" not in s and k not in (0, s["quadros"] - 1))]
    return medir_lista(lambda q: m.ler_quadro(arquivo, q)[2], qs)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dados = {}
    if "medir" not in argv:
        p.esperar_ponte()
        dados["premiere"] = x("app.version")
        dados["montar"] = montar(); print("montado", dados["montar"], flush=True)
        dados["mascaras"] = mascaras(); print("máscaras", dados["mascaras"], flush=True)
        dados["render"] = renderizar(); print("render", dados["render"], flush=True)
    dados["medida"] = medir()
    os.makedirs(TRAB, exist_ok=True)
    with open(os.path.join(TRAB, "premiere.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    for d in dados["medida"]:
        print(d["rotulo"], d["quadro"], "contorno", d["contorno_px"], "meio", d["meio"], "largura", d["largura_10_90"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

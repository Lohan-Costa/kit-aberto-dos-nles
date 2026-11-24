"""Bancada B16_NEST_MASCARA no Premiere — a máscara de opacidade dentro/em cima de NEST e sobre PROXY X ≠ Y, com a VERDADE
pelo RENDER (como o B14: `lab/bancadas/premiere_mascara.py`).

    python -m lab.bancadas.premiere_mascara_nest            (com o Premiere aberto e a ponte no ar)
    python -m lab.bancadas.premiere_mascara_nest medir      (só lê o render já feito)

Monta pela API (os nests, a escala, o corte dentro do nest, o in do nest, o proxy com Uniform Scale desligado), dá ao
clipe-alvo de cada segmento o nome "B16_<rótulo>", salva, fecha, põe as máscaras no XML (`mascara_b14.aplicar` com os
alvos do `mascara_b16`), reabre, renderiza a sequência B16 e mede a borda em cada quadro.
"""
from __future__ import annotations

import json
import os
import sys
import time

from . import premiere as p
from . import premiere_mascara as b14b
from .. import mascara_b14 as b14
from .. import mascara_b16 as m
from ..gerar import RAIZ

BASE = os.path.join(RAIZ, "saida", "base", "B14_MASCARA")
CASO = os.path.join(RAIZ, "saida", "base", "B16_NEST_MASCARA")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B16_NEST_MASCARA")
PROJETO = os.path.join(TRAB, "B16 NEST MASCARA.prproj")
CRU = os.path.join(TRAB, "B16 NEST MASCARA (sem mascaras).prproj")
RENDER = os.path.join(TRAB, "renders", "B16_RENDER.mov")
J = p._js


def x(codigo: str, timeout: float = 600):
    from . import premiere_relink as r
    r.TRAB = TRAB
    return r.x(codigo, timeout)


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    for a in (CRU, PROJETO):
        if os.path.exists(a):
            os.remove(a)
    x("app.newProject(%s)" % J(CRU))
    x("(function(){ app.enableQE(); qe.project.init(); return qe.project.setRenderer(%s); })()" % J(b14b.RENDERIZADOR))
    arqs = [os.path.join(BASE, f"B14_{n}.mov") for n in b14.CLIPES] + [os.path.join(CASO, "B16_FRENTE_PROXY.mov")]
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J(arqs))
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), por = {}; for (var i = 0; i < it.length; i++) por[it[i].name] = it[i];
      var Q = 1001 / 24000, plano = %(plano)s;
      var ARQ = {"FRENTE": "B14_FRENTE.mov", "FRENTE_100": "B14_FRENTE_100.mov", "FRENTE_PROXY": "B16_FRENTE_PROXY.mov"};
      function limpar(s) { for (var t = 0; t < s.videoTracks.numTracks; t++) while (s.videoTracks[t].clips.numItems) s.videoTracks[t].clips[0].remove(false, false);
        for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false); }
      // in/out em TICKS exatos (objeto Time): em segundos o 23.2 arredonda por ponto flutuante e o clipe sai com N − 1 ou
      // N + 1 quadros conforme o N (B14/B16, 2026-10-10)
      function tk(qd) { var tm = new Time(); tm.ticks = String(qd * 10594584000); return tm; }
      function trecho(pi, ini, n) { pi.setInPoint(tk(ini), 4); pi.setOutPoint(tk(ini + n), 4); return pi; }
      function nest(nome) { var s = app.project.createNewSequenceFromClips(nome, [por["B14_FRENTE.mov"]], app.project.rootItem);
        s.name = nome; limpar(s); return s; }
      function comp(c, mn) { for (var k = 0; k < c.components.numItems; k++) if (c.components[k].matchName == mn) return c.components[k]; }
      function prop(k, n) { for (var j = 0; j < k.properties.numItems; j++) if (k.properties[j].displayName == n) return k.properties[j]; }
      function escala(c, v) { prop(comp(c, "AE.ADBE Motion"), "Scale").setValue(v, true); }
      function escalaXY(c, w, h) { var mo = comp(c, "AE.ADBE Motion"); prop(mo, "Uniform Scale").setValue(false, true);
        prop(mo, "Scale").setValue(h, true); prop(mo, "Scale Width").setValue(w, true); }
      // ⚠️ num clipe de MÍDIA o setSpeed acerta a velocidade só quando duração × v dá um número inteiro de quadros da mídia
      // (14 × 4,667 = 65,33 → o Premiere fez 4,0 ou 3,79; num nest, exata — 2026-10-10): a menor duração ≥ n + 2 que feche
      function dur_inteira(n, v) { for (var d = n + 2; d < n + 60; d++) if (Math.abs(d * v - Math.round(d * v)) < 1e-6) return d; return n + 2; }
      function poe(trilha, pi, q) { trilha.overwriteClip(pi, tk(q)); var c = trilha.clips, alvo = null;
        for (var i = 0; i < c.numItems; i++) if (Math.abs(c[i].start.seconds - q * Q) < Q / 2) alvo = c[i]; return alvo; }
      var conteudo = [];
      // 1) os nests (antes da sequência principal: o createNewSequenceFromClips abre cada um)
      for (var i = 0; i < plano.length; i++) {
        var sg = plano[i], n = sg.quadros, arq = por[ARQ[sg.clipe]], dentro = null, fora = null;
        if (sg.alvo == "SOLTO") continue;
        var ns = nest("NEST_" + sg.rotulo), v = ns.videoTracks[0];
        if (sg.alvo == "NEST_DE_NEST") {
          var ni = nest("NEST_DENTRO_" + sg.rotulo); poe(ni.videoTracks[0], trecho(arq, 0, n), 0);
          dentro = poe(v, trecho(ni.projectItem, 0, n), 0); dentro.name = "B16_" + sg.rotulo;
        } else if (sg.corte_100) {
          dentro = poe(v, trecho(arq, 0, sg.corte_100), 0);
          poe(v, trecho(por["B14_FRENTE_100.mov"], 0, n - sg.corte_100 + 1), sg.corte_100);   // +1: 6 quadros de 23,976 = 25,025 do de 100 qps
        } else {
          // ⚠️ o setSpeed SEM ripple mantém a DURAÇÃO: se a mídia não alcança in + duração × v, o Premiere BAIXA a velocidade
          // para caber (4,667 virou 2,94 e 4,11 — 2026-10-10). O clipe acelerado entra com a duração da timeline + folga.
          var dur = sg.dentro_vel ? dur_inteira(n, sg.dentro_vel) : Math.ceil(n * (sg.nest_vel || 1)) + (sg.nest_in || 0) * 2 + 2;
          dentro = poe(v, trecho(arq, sg.dentro_in || 0, dur), 0);
          if (sg.dentro_vel) {        // o clipe de DENTRO acelerado (o "poste"): pelo QE, na sequência do nest
            app.project.openSequence(ns.sequenceID); app.enableQE(); qe.project.init();
            var qt = qe.project.getActiveSequence().getVideoTrackAt(0);
            for (var j = 0; j < qt.numItems; j++) { var qi = qt.getItemAt(j); if (qi.type != "Empty") { qi.setSpeed(sg.dentro_vel, "", false, false, false); break; } }
            conteudo.push(sg.rotulo + " dentro: " + v.clips[0].getSpeed() + " in " + Math.round(v.clips[0].inPoint.seconds / Q * 1000) / 1000);
          }
        }
        if (sg.dentro_escala) escala(dentro, sg.dentro_escala);
        if (sg.escala_xy) escalaXY(dentro, sg.escala_xy[0], sg.escala_xy[1]);
        if (sg.alvo == "DENTRO") dentro.name = "B16_" + sg.rotulo;
        else if (sg.dentro_vel) dentro.name = "B16_" + sg.rotulo + "_DENTRO";      // o alvo do `forcar_vel`
        conteudo.push(sg.rotulo + ": " + v.clips.numItems + " clipe(s)");
        sg._nest = ns;
      }
      // 2) a principal: FUNDO na V1, um segmento por vez na V2
      var s = app.project.createNewSequenceFromClips("B16", [por["B14_FUNDO.mov"]], app.project.rootItem); s.name = "B16";
      limpar(s); s.videoTracks[0].overwriteClip(por["B14_FUNDO.mov"], tk(0));
      var v2 = s.videoTracks[1], q = 0, o = [];
      for (var i = 0; i < plano.length; i++) {
        var sg = plano[i], c;
        if (sg.alvo == "SOLTO" && sg.in_ticks) {      // in em ticks da MÍDIA (fora da grade da timeline)
          var pi = por[ARQ[sg.clipe]], ti = new Time(), to = new Time(); ti.ticks = String(sg.in_ticks);
          to.ticks = String(sg.in_ticks + (sg.quadros + 2) * 10594584000); pi.setInPoint(ti, 4); pi.setOutPoint(to, 4);
          c = poe(v2, pi, q); }
        else if (sg.alvo == "SOLTO") { c = poe(v2, trecho(por[ARQ[sg.clipe]], sg.solto_in || 0, sg.clipe_vel ? dur_inteira(sg.quadros, sg.clipe_vel) : sg.quadros + 2), q);
          if (sg.escala_xy) escalaXY(c, sg.escala_xy[0], sg.escala_xy[1]); }
        else c = poe(v2, trecho(sg._nest.projectItem, sg.nest_in || 0, sg.quadros), q);
        if (sg.nest_escala) escala(c, sg.nest_escala);
        if (sg.alvo == "FORA" || sg.alvo == "SOLTO") c.name = "B16_" + sg.rotulo;
        o.push(c.name + "@" + Math.round(c.start.seconds / Q) + "+" + Math.round((c.end.seconds - c.start.seconds) / Q));
        q += sg.quadros;
      }
      // a velocidade pelo QE (sem ripple: a duração fica) — no QE o getItemAt conta os vãos ("Empty"); a ordem é a do DOM.
      // Antes, o trecho do clipe solto foi encurtado para os 12 quadros da timeline: a velocidade sobra para o conteúdo.
      app.project.openSequence(s.sequenceID); app.enableQE(); qe.project.init();
      var qtr = qe.project.getActiveSequence().getVideoTrackAt(1), qs = [];
      for (var i = 0; i < qtr.numItems; i++) { var it2 = qtr.getItemAt(i); if (it2.type != "Empty") qs.push(it2); }
      var vel = [];
      for (var i = 0; i < plano.length; i++) {
        var f = plano[i].nest_vel || plano[i].clipe_vel; if (!f) continue;
        var ini = 0, idx = -1; for (var j = 0; j < i; j++) ini += plano[j].quadros;   // ExtendScript (ES3): sem reduce
        for (var j = 0; j < v2.clips.numItems; j++) if (Math.abs(v2.clips[j].start.seconds - ini * Q) < Q / 2) idx = j;
        qs[idx].setSpeed(f, "", false, false, false);
        var cj = v2.clips[idx];
        vel.push(plano[i].rotulo + ": " + cj.getSpeed() + " / " + Math.round((cj.end.seconds - cj.start.seconds) / Q) + " q");
      }
      app.project.save();
      return {v2: o, nests: conteudo, vel: vel};
    })()""" % {"plano": json.dumps(m.PLANO)})


def mascaras() -> dict:
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    feitos = b14.aplicar(CRU, PROJETO, alvos=m.alvos)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return {"mascaras": feitos}


def renderizar() -> dict:
    os.makedirs(os.path.dirname(RENDER), exist_ok=True)
    if os.path.exists(RENDER):
        os.remove(RENDER)
    t0 = time.time()
    res = x("""(function(){ var s = _lab_seq("B16"); app.project.openSequence(s.sequenceID);
      return app.project.activeSequence.exportAsMediaDirect(%s, %s, 0); })()""" % (J(RENDER), J(p.preset_prores(b14b.ANO))),
            timeout=900)
    return {"job": str(res), "s": round(time.time() - t0, 1), "existe": os.path.exists(RENDER)}


def medir_arquivo(ler, quadros_por_seg=None) -> list:
    """`ler(q)` → RGB do quadro q da timeline. Por segmento e quadro: a borda medida × a esperada, e a largura 10–90 %."""
    out = []
    for i, s in enumerate(m.PLANO):
        for k in (quadros_por_seg(s) if quadros_por_seg else range(s["quadros"])):
            q = m.inicio(i) + k
            rgb = ler(q)
            if rgb is None:
                continue
            b = b14.borda(b14.perfil(rgb))
            out.append({"rotulo": s["rotulo"], "quadro": q, "k": k, "esperado": round(m.borda_esperada(s, k), 2),
                        "largura_esperada": round(m.largura_esperada(s), 2),
                        **{c: (round(v, 2) if isinstance(v, float) else v) for c, v in b.items()}})
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dados = {}
    if "medir" not in argv:
        p.esperar_ponte()
        dados["premiere"] = x("app.version")
        dados["montar"] = montar(); print("montado", dados["montar"], flush=True)
        dados["mascaras"] = mascaras(); print("máscaras", dados["mascaras"], flush=True)
        dados["render"] = renderizar(); print("render", dados["render"], flush=True)
    dados["medida"] = medir_arquivo(lambda q: b14.ler_quadro(RENDER, q)[2])
    with open(os.path.join(TRAB, "medida_premiere.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    for d in dados["medida"]:
        print(d["rotulo"], d["k"], "esperado", d["esperado"], "meio", d["meio"], "largura", d["largura_10_90"],
              "(esperada", d["largura_esperada"], ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def forcar_in() -> list:
    """O in FORA da grade da timeline (o R04 tem: LOU_7310 a 100 qps com in em 2562,07 quadros) não se cria pela API — ela o
    encaixa (7 → 4,17 quadros do arquivo). Aqui o `InPoint`/`OutPoint` do clipe dos segmentos com `in_ticks` vão direto no
    XML, e o projeto é reaberto (2026-10-10)."""
    import re
    from . import premiere_relink as r
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    import gzip
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    feitos = []
    for s in m.PLANO:
        if not s.get("in_ticks"):
            continue
        sub = re.search(r'\n\t<SubClip ObjectID="(\d+)"[^>]*>(?:(?!\n\t</SubClip>).)*?<Name>B16_%s</Name>' % s["rotulo"], t, re.S)
        clip_id = re.search(r'<Clip ObjectRef="(\d+)"/>', t[sub.start():t.index("\n\t</SubClip>", sub.start())]).group(1)
        bloco = re.search(r'\n\t<VideoClip ObjectID="%s"[^>]*>.*?\n\t</VideoClip>' % clip_id, t, re.S)
        novo = re.sub(r"<InPoint>\d+</InPoint>", f"<InPoint>{s['in_ticks']}</InPoint>", bloco.group(0), count=1)
        novo = re.sub(r"<OutPoint>\d+</OutPoint>", f"<OutPoint>{s['in_ticks'] + (s['quadros'] + 2) * b14.TICKS_QUADRO}</OutPoint>",
                      novo, count=1)
        t = t.replace(bloco.group(0), novo, 1)
        feitos.append(s["rotulo"])
    r._gravar_prproj(PROJETO, t)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return feitos


def forcar_vel() -> list:
    """A velocidade EXATA dos clipes de mídia acelerados (o `setSpeed` do QE não a acerta num clipe de mídia com in: 4,667
    virou 4,0 / 3,69 / 3,79 — num nest, acerta): `PlaybackSpeed` (float32, como o Premiere grava) e `OutPoint` = In +
    duração × v direto no XML, e o projeto é reaberto (2026-10-10). ⚠️ Projeto "forçado", como o `forcar_in`."""
    import gzip
    import re
    import struct
    from . import premiere_relink as r
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    feitos = []
    for s in m.PLANO:
        v = s.get("dentro_vel") or (s.get("clipe_vel") if s["alvo"] == "SOLTO" else None)
        if not v or abs(v - round(v)) < 1e-9:
            continue
        nome = f"B16_{s['rotulo']}" if s["alvo"] == "SOLTO" else None
        if nome is None:                                   # o clipe de DENTRO do nest NEST_<rótulo>: o único da sequência
            seq = re.search(r'<Name>NEST_%s</Name>' % s["rotulo"], t)
            # o item de dentro não tem nome próprio: é o VideoClip cuja velocidade o QE gravou (≠ 1) na mídia da FRENTE
            alvo_v = None
        sub = None
        for mm in re.finditer(r'\n\t<VideoClipTrackItem ObjectID="(\d+)"[^>]*>.*?\n\t</VideoClipTrackItem>', t, re.S):
            sc = re.search(r'<SubClip ObjectRef="(\d+)"/>', mm.group(0)).group(1)
            sb = re.search(r'\n\t<SubClip ObjectID="%s"[^>]*>.*?\n\t</SubClip>' % sc, t, re.S).group(0)
            n_sub = re.search(r"<Name>([^<]*)</Name>", sb).group(1)
            if (nome and n_sub == nome) or (not nome and n_sub == f"B16_{s['rotulo']}_DENTRO"):
                sub = (mm.group(0), sb)
                break
        if sub is None:
            continue
        ini, fim = (int(re.search(rf"<{k}>(-?\d+)</{k}>", sub[0]).group(1)) for k in ("Start", "End"))
        cid = re.search(r'<Clip ObjectRef="(\d+)"/>', sub[1]).group(1)
        bloco = re.search(r'\n\t<VideoClip ObjectID="%s"[^>]*>.*?\n\t</VideoClip>' % cid, t, re.S).group(0)
        entrada = int(re.search(r"<InPoint>(-?\d+)</InPoint>", bloco).group(1))
        v32 = struct.unpack("f", struct.pack("f", v))[0]
        novo = re.sub(r"<PlaybackSpeed>[^<]*</PlaybackSpeed>", f"<PlaybackSpeed>{v32!r}</PlaybackSpeed>", bloco, count=1)
        novo = re.sub(r"<OutPoint>-?\d+</OutPoint>", f"<OutPoint>{round(entrada + (fim - ini) * v32)}</OutPoint>", novo, count=1)
        t = t.replace(bloco, novo, 1)
        feitos.append((s["rotulo"], v32))
    r._gravar_prproj(PROJETO, t)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return feitos

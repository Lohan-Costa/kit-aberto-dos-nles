"""Bancada B18_IN_LENTO no Premiere — o encaixe do in de clipe SOLTO com velocidade, pela placa que diz o próprio quadro.

    python -m lab.bancadas.premiere_in_lento          (com o Premiere aberto e a ponte no ar)
    python -m lab.bancadas.premiere_in_lento medir    (só lê o render já feito)

Monta pela API (sequência de 23,976 a partir da placa FUNDO do B14; um segmento de 12 quadros da placa de 100 qps por
linha do `lab.in_lento_b18.PLANO`, nomeado "B18_<rótulo>"), salva, fecha, põe a VELOCIDADE e o IN exatos no XML (a API
encaixa o in e o `setSpeed` do QE erra a velocidade num clipe de mídia — B16), reabre, renderiza e lê o número de cada
quadro (`mascara_b14.numero_da_placa`).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import struct
import subprocess
import sys

from . import premiere as p
from . import premiere_relink as r
from .. import ffmpeg as ff
from .. import in_lento_b18 as m
from .. import mascara_b14 as b14
from ..gerar import RAIZ

CASO = os.path.join(RAIZ, "saida", "base", "B18_IN_LENTO")
FUNDO = os.path.join(RAIZ, "saida", "base", "B14_MASCARA", "B14_FUNDO.mov")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B18_IN_LENTO")
PROJETO = os.path.join(TRAB, "B18 IN LENTO.prproj")
RENDER = os.path.join(TRAB, "renders", "B18_RENDER.mov")
J = p._js


def x(codigo: str, timeout: float = 600):
    r.TRAB = TRAB
    return r.x(codigo, timeout)


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    if os.path.exists(PROJETO):
        os.remove(PROJETO)
    x("app.newProject(%s)" % J(PROJETO))
    reais = sorted({sg["midia"] for sg in m.PLANO if sg.get("midia")})
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J([FUNDO, m.gerar(CASO)] + reais))
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), por = {}; for (var i = 0; i < it.length; i++) por[it[i].name] = it[i];
      var plano = %(plano)s, Q = 1001 / 24000;
      var s = app.project.createNewSequenceFromClips("B18", [por["B14_FUNDO.mov"]], app.project.rootItem); s.name = "B18";
      while (s.videoTracks[0].clips.numItems) s.videoTracks[0].clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      var pl = por["B18_PLACA_100.mp4"], o = [];
      for (var i = 0; i < plano.length; i++) {
        // in provisório em quadros INTEIROS da placa (o XML troca); o trecho com folga: a velocidade vem depois, no XML
        var pi = plano[i].midia_nome ? por[plano[i].midia_nome] : pl;
        var ti = new Time(), to = new Time(); ti.ticks = String(1000 * 2540160000); to.ticks = String((1000 + 40) * 2540160000);
        pi.setInPoint(ti, 4); pi.setOutPoint(to, 4); pl = pi;
        var q = new Time(); q.ticks = String(i * %(n)d * 10594584000);
        s.videoTracks[0].overwriteClip(pi, q); pl = por["B18_PLACA_100.mp4"];
        var c = s.videoTracks[0].clips, alvo = null;
        for (var j = 0; j < c.numItems; j++) if (Math.abs(c[j].start.seconds - i * %(n)d * Q) < Q / 2) alvo = c[j];
        // a duração da timeline: 12 quadros (o resto do trecho sai)
        var fim = new Time(); fim.ticks = String((i + 1) * %(n)d * 10594584000); alvo.end = fim;
        alvo.name = "B18_" + plano[i].rotulo;
        o.push(alvo.name + "@" + Math.round(alvo.start.seconds / Q) + "+" + Math.round((alvo.end.seconds - alvo.start.seconds) / Q));
      }
      app.project.save();
      return o;
    })()""" % {"plano": json.dumps([dict(sg, midia_nome=os.path.basename(sg["midia"])) if sg.get("midia") else sg
                                     for sg in m.PLANO]), "n": m.QUADROS})


def forcar() -> list:
    """`PlaybackSpeed` (float32, como o Premiere grava), `InPoint` = o do plano e `OutPoint` = In + duração × v, no XML."""
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    feitos = []
    for s in m.PLANO:
        nome = "B18_" + s["rotulo"]
        achou = None
        for mm in re.finditer(r'\n\t<VideoClipTrackItem ObjectID="(\d+)"[^>]*>.*?\n\t</VideoClipTrackItem>', t, re.S):
            sc = re.search(r'<SubClip ObjectRef="(\d+)"/>', mm.group(0)).group(1)
            sb = re.search(r'\n\t<SubClip ObjectID="%s"[^>]*>.*?\n\t</SubClip>' % sc, t, re.S).group(0)
            if re.search(r"<Name>([^<]*)</Name>", sb).group(1) == nome:
                achou = (mm.group(0), sb)
                break
        if achou is None:
            continue
        ini, fim = (int(re.search(rf"<{k}>(-?\d+)</{k}>", achou[0]).group(1)) for k in ("Start", "End"))
        cid = re.search(r'<Clip ObjectRef="(\d+)"/>', achou[1]).group(1)
        bloco = re.search(r'\n\t<VideoClip ObjectID="%s"[^>]*>.*?\n\t</VideoClip>' % cid, t, re.S).group(0)
        v32 = struct.unpack("f", struct.pack("f", s["vel"]))[0]
        novo = bloco
        if "<PlaybackSpeed>" in novo:
            novo = re.sub(r"<PlaybackSpeed>[^<]*</PlaybackSpeed>", f"<PlaybackSpeed>{v32!r}</PlaybackSpeed>", novo, count=1)
        else:
            novo = novo.replace("<InPoint>", f"<PlaybackSpeed>{v32!r}</PlaybackSpeed>\n\t\t\t<InPoint>", 1)
        novo = re.sub(r"<InPoint>-?\d+</InPoint>", f"<InPoint>{s['in_ticks']}</InPoint>", novo, count=1)
        novo = re.sub(r"<OutPoint>-?\d+</OutPoint>", f"<OutPoint>{round(s['in_ticks'] + (fim - ini) * v32)}</OutPoint>", novo, count=1)
        t = t.replace(bloco, novo, 1)
        feitos.append((s["rotulo"], ini // m.TPF, (fim - ini) // m.TPF))
    r._gravar_prproj(PROJETO, t)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return feitos


def conferir_xml() -> list:
    """O que o projeto reaberto guardou (velocidade e in) — o Premiere pode reescrever ao abrir."""
    return x(r"""(function(){ var s = null;
      for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name == "B18") s = app.project.sequences[i];
      var c = s.videoTracks[0].clips, o = [];
      for (var j = 0; j < c.numItems; j++) o.push([c[j].name, c[j].getSpeed(), c[j].inPoint.ticks, Math.round(c[j].start.ticks / 10594584000)]);
      return o; })()""")


def renderizar() -> str:
    os.makedirs(os.path.dirname(RENDER), exist_ok=True)
    if os.path.exists(RENDER):
        os.remove(RENDER)
    # ProRes 4444: o "Match Source – ProRes 422" faz smart rendering (copia quadros da fonte) — B19, 2026-10-11
    pre = os.path.join(os.path.dirname(p.preset_prores("2023")), "Match Source - Apple ProRes 4444.epr")
    print(x(r"""(function(){ var s = null;
      for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name == "B18") s = app.project.sequences[i];
      app.project.openSequence(s.sequenceID);
      return app.project.activeSequence.exportAsMediaDirect(%s, %s, 0); })()""" % (J(RENDER), J(pre)), timeout=900))
    return RENDER


def ler(arq: str) -> list:
    W, H = b14.W, b14.H
    d = subprocess.run([ff.achar("ffmpeg"), "-v", "error", "-i", arq, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True).stdout
    n = len(d) // (W * H * 3)
    return [b14.numero_da_placa(d[k * W * H * 3:(k + 1) * W * H * 3]) for k in range(n)]


def medir(arq: str = RENDER) -> list:
    nums = ler(arq)
    out = []
    for i, s in enumerate(m.PLANO):
        vistos = nums[m.inicio(i):m.inicio(i) + m.QUADROS]
        lin = {"rotulo": s["rotulo"], "vel": s["vel"], "in_div_passo": round(s["in_ticks"] / (s["vel"] * m.TPF), 4), "visto": vistos}
        for modo in ("piso", "teto"):
            lin[modo] = sum(1 for k, v in enumerate(vistos) if v == m.previsto(s, k, modo))
        lin["dif_piso"] = sorted({(v - m.previsto(s, k, "piso")) for k, v in enumerate(vistos) if v is not None})
        out.append(lin)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "medir":
        p.esperar_ponte(120)
        print(montar())
        print(forcar())
        print(conferir_xml())
        renderizar()
    res = medir()
    with open(os.path.join(TRAB, "medida.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for l in res:
        print("%-12s v %.2f  In÷passo %10.4f  piso %2d/12  teto %2d/12  dif×piso %s" % (
            l["rotulo"], l["vel"], l["in_div_passo"], l["piso"], l["teto"], l["dif_piso"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

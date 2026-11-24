"""Bancada B17_BEZIER no Premiere — a curva dos keyframes do Motion (pedido do autor, 2026-10-10: o R04 mostrou que a
Position Bézier segue o modelo do After Effects, mas a SCALE (parâmetro de um eixo) não: ~11 × a velocidade de entrada).

    python -m lab.bancadas.premiere_bezier            (Premiere aberto, ponte no ar)
    python -m lab.bancadas.premiere_bezier medir      (só lê o render)

A placa FRENTE (B14, laranja, tela cheia) sobre o FUNDO, com a Scale animada por keyframes criados pela API
(`addKey`/`setValueAtKey`/`setInterpolationTypeAtKey`), um tipo de interpolação por segmento. Com escala < 100 a placa
deixa o fundo à mostra: a borda DIREITA dá a escala exata em cada quadro (borda = 960 + 960 × escala/100). Grava o
projeto, o render (verdade), os campos de keyframe que o Premiere escreveu no XML e a escala medida por quadro.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys

from . import premiere as p
from . import premiere_mascara as b14b
from .. import mascara_b14 as b14
from ..gerar import RAIZ

BASE = os.path.join(RAIZ, "saida", "base", "B14_MASCARA")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B17_BEZIER")
PROJETO = os.path.join(TRAB, "B17 BEZIER.prproj")
RENDER = os.path.join(TRAB, "renders", "B17_RENDER.mov")
J = p._js
TQ = 10594584000
N = 12                                   # quadros por segmento
#: (rótulo, parâmetro, valores nos quadros, tipo de interpolação por keyframe)
PLANO = [
    ("LIN", "Scale", {0: 90, 8: 60}, {0: 0, 8: 0}),
    ("T4", "Scale", {0: 90, 8: 60}, {0: 4, 8: 4}),
    ("T5", "Scale", {0: 90, 8: 60}, {0: 5, 8: 5}),
    ("T6", "Scale", {0: 90, 8: 60}, {0: 6, 8: 6}),
    ("T7", "Scale", {0: 90, 8: 60}, {0: 7, 8: 7}),
    ("T5_SO_FIM", "Scale", {0: 90, 8: 60}, {0: 0, 8: 5}),
    ("T5_SO_INI", "Scale", {0: 90, 8: 60}, {0: 5, 8: 0}),
    ("T5_TRES", "Scale", {0: 90, 4: 80, 8: 60}, {0: 5, 4: 5, 8: 5}),
]


def x(codigo: str, timeout: float = 600):
    from . import premiere_relink as r
    r.TRAB = TRAB
    return r.x(codigo, timeout)


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    if os.path.exists(PROJETO):
        os.remove(PROJETO)
    x("app.newProject(%s)" % J(PROJETO))
    x("(function(){ app.enableQE(); qe.project.init(); return qe.project.setRenderer(%s); })()" % J(b14b.RENDERIZADOR))
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J([os.path.join(BASE, f"B14_{n}.mov") for n in ("FUNDO", "FRENTE")]))
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), por = {}; for (var i = 0; i < it.length; i++) por[it[i].name] = it[i];
      var plano = %(plano)s, N = %(n)d;
      function tk(q) { var t = new Time(); t.ticks = String(q * 10594584000); return t; }
      function limpar(s) { for (var t = 0; t < s.videoTracks.numTracks; t++) while (s.videoTracks[t].clips.numItems) s.videoTracks[t].clips[0].remove(false, false);
        for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false); }
      function comp(c, mn) { for (var k = 0; k < c.components.numItems; k++) if (c.components[k].matchName == mn) return c.components[k]; }
      function prop(k, n) { for (var j = 0; j < k.properties.numItems; j++) if (k.properties[j].displayName == n) return k.properties[j]; }
      var s = app.project.createNewSequenceFromClips("B17", [por["B14_FUNDO.mov"]], app.project.rootItem); s.name = "B17";
      limpar(s); s.videoTracks[0].overwriteClip(por["B14_FUNDO.mov"], tk(0));
      var fr = por["B14_FRENTE.mov"], v2 = s.videoTracks[1], o = [];
      for (var i = 0; i < plano.length; i++) {
        fr.setInPoint(tk(0), 4); fr.setOutPoint(tk(N), 4); v2.overwriteClip(fr, tk(i * N));
      }
      for (var i = 0; i < plano.length; i++) {
        var c = v2.clips[i], pr = prop(comp(c, "AE.ADBE Motion"), plano[i][1]), vals = plano[i][2], tipos = plano[i][3];
        c.name = "B17_" + plano[i][0];
        pr.setTimeVarying(true);
        for (var q in vals) { var t = tk(Number(q)); pr.addKey(t); pr.setValueAtKey(t, vals[q], true); }
        var r = [];
        for (var q in tipos) { try { pr.setInterpolationTypeAtKey(tk(Number(q)), tipos[q], true); r.push(q + ":" + tipos[q]); } catch (e) { r.push(q + ":ERRO " + e); } }
        o.push(c.name + " " + r.join(" "));
      }
      app.project.save();
      return o;
    })()""" % {"plano": json.dumps([[a, b, {str(k): v for k, v in c.items()}, {str(k): v for k, v in d.items()}]
                                      for a, b, c, d in PLANO]), "n": N})


def campos() -> dict:
    """Os keyframes que o Premiere gravou, por segmento (lidos do .prproj salvo)."""
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    out = {}
    for rot, nome, _v, _t in PLANO:
        sub = re.search(r'\n\t<SubClip ObjectID="(\d+)"[^>]*>(?:(?!\n\t</SubClip>).)*?<Name>B17_%s</Name>' % rot, t, re.S)
        ti = re.search(r'\n\t<VideoClipTrackItem ObjectID="\d+"[^>]*>(?:(?!\n\t</VideoClipTrackItem>).)*?<SubClip ObjectRef="%s"/>'
                       % sub.group(1), t, re.S).group(0)
        cad = re.search(r'<Components ObjectRef="(\d+)"/>', ti).group(1)
        bloco = re.search(r'\n\t<VideoComponentChain ObjectID="%s"[^>]*>.*?\n\t</VideoComponentChain>' % cad, t, re.S).group(0)
        for cid in re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', bloco):
            c = re.search(r'\n\t<VideoFilterComponent ObjectID="%s"[^>]*>.*?\n\t</VideoFilterComponent>' % cid, t, re.S)
            if not c or "AE.ADBE Motion" not in c.group(0):
                continue
            for pid in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', c.group(0)):
                prm = re.search(r'\n\t<\w+ ObjectID="%s"[^>]*>.*?\n\t</\w+>' % pid, t, re.S).group(0)
                if f"<Name>{nome}</Name>" in prm and "<Keyframes>" in prm:
                    kfs = re.search(r"<Keyframes>([^<]*)</Keyframes>", prm).group(1)
                    out[rot] = [k.split(",") for k in kfs.strip(";").split(";")]
    return out


def renderizar() -> dict:
    os.makedirs(os.path.dirname(RENDER), exist_ok=True)
    if os.path.exists(RENDER):
        os.remove(RENDER)
    r = x("""(function(){ var s = _lab_seq("B17"); app.project.openSequence(s.sequenceID);
      return app.project.activeSequence.exportAsMediaDirect(%s, %s, 0); })()""" % (J(RENDER), J(p.preset_prores(b14b.ANO))), timeout=900)
    return {"job": str(r), "existe": os.path.exists(RENDER)}


def medir() -> dict:
    out = {}
    for i, (rot, *_r) in enumerate(PLANO):
        esc = []
        for k in range(N):
            b = b14.borda(b14.perfil(b14.ler_quadro(RENDER, i * N + k)[2]))
            esc.append(round((b["meio"] - 960) / 960 * 100, 2) if b["meio"] else None)
        out[rot] = esc
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dados = {}
    if "medir" not in argv:
        p.esperar_ponte()
        dados["montar"] = montar(); print("montado", dados["montar"], flush=True)
        dados["render"] = renderizar(); print("render", dados["render"], flush=True)
    dados["campos"] = campos()
    dados["escala"] = medir()
    with open(os.path.join(TRAB, "premiere.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    for rot, esc in dados["escala"].items():
        print(rot, esc)
        for k in dados["campos"].get(rot, []):
            print("     kf", round(int(k[0]) / TQ, 3), k[1:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#: velocidade/influência de ENTRADA forçadas no XML no último keyframe (a API não as dá): o "ease" do R04
FORCAR = {"T5": (0.0, 1.0), "T6": (10.0, 1.0), "T5_SO_FIM": (30.0, 1.0), "T5_SO_INI": (0.0, 0.33333333333333331)}


def forcar_ease() -> list:
    from . import premiere_relink as r
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    feitos = []
    for rot, (vel, infl) in FORCAR.items():
        kfs = campos_texto(t, rot)
        if not kfs:
            continue
        velho, partes = kfs
        k = [x.split(",") for x in partes]
        k[-1][2] = "5"                       # tipo temporal Bézier no de chegada
        k[-1][4], k[-1][5] = repr(vel), repr(infl)
        novo = ";".join(",".join(x) for x in k) + ";"
        t = t.replace(f"<Keyframes>{velho}</Keyframes>", f"<Keyframes>{novo}</Keyframes>", 1)
        feitos.append((rot, novo[:120]))
    r._gravar_prproj(PROJETO, t)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return feitos


def campos_texto(t: str, rot: str):
    sub = re.search(r'\n\t<SubClip ObjectID="(\d+)"[^>]*>(?:(?!\n\t</SubClip>).)*?<Name>B17_%s</Name>' % rot, t, re.S)
    ti = re.search(r'\n\t<VideoClipTrackItem ObjectID="\d+"[^>]*>(?:(?!\n\t</VideoClipTrackItem>).)*?<SubClip ObjectRef="%s"/>'
                   % sub.group(1), t, re.S).group(0)
    cad = re.search(r'<Components ObjectRef="(\d+)"/>', ti).group(1)
    bloco = re.search(r'\n\t<VideoComponentChain ObjectID="%s"[^>]*>.*?\n\t</VideoComponentChain>' % cad, t, re.S).group(0)
    for cid in re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', bloco):
        c = re.search(r'\n\t<VideoFilterComponent ObjectID="%s"[^>]*>.*?\n\t</VideoFilterComponent>' % cid, t, re.S)
        if not c or "AE.ADBE Motion" not in c.group(0):
            continue
        for pid in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', c.group(0)):
            prm = re.search(r'\n\t<\w+ ObjectID="%s"[^>]*>.*?\n\t</\w+>' % pid, t, re.S).group(0)
            if "<Name>Scale</Name>" in prm and "<Keyframes>" in prm:
                kfs = re.search(r"<Keyframes>([^<]*)</Keyframes>", prm).group(1)
                return kfs, kfs.strip(";").split(";")
    return None

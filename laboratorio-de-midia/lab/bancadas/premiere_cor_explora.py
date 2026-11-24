"""Exploração da COR em cada versão do Premiere (antes de montar o B09): o que a versão diz dos arquivos de câmera
(espaço de cor, log, LUT embutida), as listas de espaço de trabalho / sobrescrita, e os parâmetros do Lumetri.

    python3 -m lab.bancadas.premiere_cor_explora    # no Premiere aberto → resultados/B09_COR/exploracao-<v>-darwin.json
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

from . import premiere as p
from . import premiere_projeto as pp

RAIZ = pp.RAIZ
COLETA = os.path.join(os.path.dirname(os.path.dirname(RAIZ)), "MIDIAS DE TESTES", "2 FORMATOS E CAMERAS")
SONY = os.path.join(COLETA, "SONY XOCN", "Scene1", "A002C041_22062469", "A002C041_22062469.mxf")
ARRI = sorted(x for x in glob.glob(os.path.join(COLETA, "ARRI", "F004C009_190925_MN99", "*.arx")) if not os.path.basename(x).startswith("._"))
MOV = pp.MOV
LUMETRI = ["Lumetri Color", "Cor de Lumetri"]

_INFO = r"""function _lab_obj(x) { if (x === null || x === undefined) return x; if (typeof x != "object") return x;
  if (x.length !== undefined && typeof x != "string") { var a = []; for (var q = 0; q < x.length; q++) a.push(_lab_obj(x[q])); return a; }
  var r = {}; for (var k in x) { try { var v = x[k]; if (typeof v != "function") r[k] = (typeof v == "object") ? String(v) : v; } catch (e) {} } return r; }
function _lab_cor(c) { var o = {nome: c.name};
  var f = ["getColorSpace", "getOriginalColorSpace", "getOverrideColorSpace", "isColorManagedMedia", "getEmbeddedLUTID", "getInputLUTID"];
  for (var i = 0; i < f.length; i++) { try { var v = c[f[i]](); o[f[i]] = (v && typeof v == "object") ? (function(x){ var r = {}; for (var k in x) { try { r[k] = String(x[k]); } catch (e) {} } return r; })(v) : v; } catch (e) { o[f[i]] = "ERRO " + e; } }
  try { o.overrideList = c.getOverrideColorSpaceList; } catch (e) {}
  try { var fi = c.getFootageInterpretation(); o.interp = {colorSpace: String(fi.colorSpace), inputLUTID: String(fi.inputLUTID), fps: fi.frameRate}; } catch (e) { o.interp = "ERRO " + e; }
  try { var md = c.getProjectMetadata(); var m = md.match(/Intrinsic\.(VideoInfo|MediaDuration)>([^<]*)</g); o.md = m; } catch (e) {}
  return o; }
"""


def explorar() -> dict:
    v = p.executar("app.version")
    trab = os.path.join(RAIZ, "saida", "bancadas", f"premiere-{v}", "B09_EXPLORA")
    p.salvar_e_fechar()
    if os.path.isdir(trab):
        os.rename(trab, trab + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(trab)
    out = {"versao": v, "arquivos": {"sony": SONY, "arri_primeiro": ARRI[0] if ARRI else None, "arri_quadros": len(ARRI)}}

    def js(nome, codigo, timeout=600):
        try:
            out[nome] = p.executar(pp._JS + _INFO + codigo, timeout=timeout)
        except Exception as e:                  # noqa: BLE001 — explorar: registrar e seguir
            out[nome] = f"ERRO {type(e).__name__}: {e}"
        print(time.strftime("%H:%M:%S"), nome, str(out[nome])[:300], flush=True)

    js("novo", "app.newProject(%s)" % pp._js(os.path.join(trab, "B09 EXPLORA.prproj")))
    js("projeto_cor", """(function(){ var o = {};
      try { o.lut_interp = app.project.getLUTInterpolationMethod(); } catch (e) { o.lut_interp = "ERRO " + e; }
      try { o.lut_interp_lista = app.project.getSupportedLUTInterpolationMethods(); } catch (e) {}
      try { o.branco_graficos = app.project.getGraphicsWhiteLuminance(); } catch (e) {}
      try { o.branco_graficos_lista = app.project.getSupportedGraphicsWhiteLuminances(); } catch (e) {}
      try { o.looks = _lab_obj(app.getLookInfo); } catch (e) { o.looks = "ERRO " + e; }
      try { var l = app.project.getAllLumetriPresetsList(); o.presets_lumetri = l ? l.length : l; } catch (e) { o.presets_lumetri = "ERRO " + e; }
      return o; })()""")
    js("importar", """(function(){ var r = [];
      r.push(app.project.importFiles([%s], true, app.project.rootItem, false));
      r.push(app.project.importFiles([%s], true, app.project.rootItem, false));
      r.push(app.project.importFiles([%s], true, app.project.rootItem, true));
      var it = _lab_itens(app.project.rootItem), o = []; for (var i = 0; i < it.length; i++) o.push([it[i].name, it[i].getMediaPath()]);
      return {devolveu: r, itens: o}; })()""" % (pp._js(MOV), pp._js(SONY), pp._js(ARRI[0])), timeout=900)
    js("cor_dos_clipes", """(function(){ var it = _lab_itens(app.project.rootItem), o = [];
      for (var i = 0; i < it.length; i++) if (it[i].getMediaPath()) o.push(_lab_cor(it[i])); return o; })()""")
    js("sequencias", """(function(){ var it = _lab_itens(app.project.rootItem), o = [];
      for (var i = 0; i < it.length; i++) { var c = it[i]; if (!c.getMediaPath()) continue;
        var s = app.project.createNewSequenceFromClips("SEQ " + c.name, [c], app.project.rootItem), st = s.getSettings(), x = {nome: s.name};
        var k = ["workingColorSpace", "workingColorSpaceList", "autoToneMapEnabled", "autoInputGamutCompressionEnabled", "gamutMappingControls", "compositeLinearColor", "videoFrameWidth", "videoFrameHeight", "videoFrameRate"];
        for (var j = 0; j < k.length; j++) { try { var v = st[k[j]]; x[k[j]] = (v && v.seconds !== undefined) ? v.seconds : _lab_obj(v); } catch (e) { x[k[j]] = "ERRO " + e; } }
        o.push(x); }
      return o; })()""")
    js("lumetri", """(function(){ var s = null; for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name.indexOf("SEQ " + %s) == 0) s = app.project.sequences[i]; app.project.openSequence(s.sequenceID); app.enableQE();
      var ti = s.videoTracks[0].clips[0], antes = _lab_matches(ti), fx = _lab_fx(%s);
      qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0).addVideoEffect(fx); var c = _lab_novo(ti, antes), ps = [];
      for (var i = 0; i < c.properties.numItems; i++) { var pr = c.properties[i], v = null; try { v = pr.getValue(); } catch (e) { v = "?"; } ps.push([i, pr.displayName, (v && typeof v == "object" && v.length !== undefined) ? "lista" : (function(t){ var r = ""; for (var n = 0; n < t.length && r.length < 60; n++) { var cc = t.charCodeAt(n); if (cc >= 32 && cc < 127) r += t.charAt(n); } return r; })(String(v))]); }
      return {efeito: fx.name, match: c.matchName, parametros: ps}; })()""" % (pp._js(os.path.splitext(os.path.basename(MOV))[0]), pp._js(LUMETRI)))
    p.executar("app.project.save()")
    dest = os.path.join(RAIZ, "resultados", "B09_COR", f"exploracao-{v}-{sys.platform}.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return out


if __name__ == "__main__":
    os.chdir(RAIZ)
    explorar()

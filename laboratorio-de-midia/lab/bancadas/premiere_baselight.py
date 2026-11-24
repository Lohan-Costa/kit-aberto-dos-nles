"""BL03 no Premiere (Mac) — o lado do Premiere da missão Baselight (`2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-21-baselight.md`):
os MESMOS dailies feitos fora (`saida/baselight/BL01_CONFORM/DAILIES_FORA/DIA01`) montados nos MESMOS cortes da BL02 do
MC (`avid_baselight.CORTE_SECO`/`DUAS_TRILHAS_*`) e o XML (xmeml, o que o Premiere manda à cor) de cada sequência.

    python3 -m lab.bancadas.premiere_baselight abrir      # instala a ponte e abre o Premiere 2027
    python3 -m lab.bancadas.premiere_baselight montar     # projeto, import, sequências, XML, salva
"""
from __future__ import annotations

import json
import os
import sys

from . import premiere as p
from .avid_baselight import CORTE_SECO, DUAS_TRILHAS_V1, DUAS_TRILHAS_V2, MIDIA, RAIZ

ANO = "2027"
DAILIES = os.path.join(MIDIA, "DAILIES_FORA", "DIA01")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere_baselight")
PROJETO = os.path.join(TRAB, "BL03 PREMIERE.prproj")
QUADRO = 10594584000            # ticks de um quadro a 23,976 (254016000000 · 1001 / 24000)
J = p._js


def abrir() -> dict:
    p.instalar()
    p.reabrir_premiere(ANO)
    return p.esperar_ponte(300)


def _arq(cam: str) -> str:
    return next(os.path.join(DAILIES, n) for n in sorted(os.listdir(DAILIES))
                if n.startswith(cam) and n.endswith(".mov") and not n.startswith("._"))


_JS = r"""
function _b_por() { var it = _lab_itens(app.project.rootItem), por = {};
  for (var i = 0; i < it.length; i++) if (it[i].getMediaPath()) por[it[i].getMediaPath()] = it[i]; return por; }
function _b_t(q) { var t = new Time(); t.ticks = String(q * %d); return t; }
function _b_poe(trilha, item, inq, durq, posq) {
  item.setInPoint(_b_t(inq), 4); item.setOutPoint(_b_t(inq + durq), 4);
  trilha.overwriteClip(item, _b_t(posq)); item.clearInPoint(); item.clearOutPoint(); }
function _b_seq(nome, item) { var s = _lab_seq(nome); if (s) app.project.deleteSequence(s);
  s = app.project.createNewSequenceFromClips(nome, [item], app.project.rootItem); s.name = nome;
  for (var t = 0; t < s.videoTracks.numTracks; t++) while (s.videoTracks[t].clips.numItems) s.videoTracks[t].clips[0].remove(false, false);
  for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
  return s; }
""" % QUADRO


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    aberto = p.executar(p._LIB + """(function(){ var alvo = %s, atual = '';
      try { atual = app.project.path; } catch (e) {}
      if (atual == alvo) return 'já aberto';
      if (new File(alvo).exists) return app.openDocument(alvo, true, true, true);
      return app.newProject(alvo); })()""" % J(PROJETO))
    print("projeto:", aberto)
    cams = sorted({c for c, _i, _d in CORTE_SECO} | {DUAS_TRILHAS_V1[0], DUAS_TRILHAS_V2[0]})
    arqs = {c: _arq(c) for c in cams}
    ja = p.executar(p._LIB + _JS + "(function(){ var o = [], por = _b_por(); for (var k in por) o.push(k); return o; })()") or []
    novos = [a for a in arqs.values() if a not in ja]
    if novos:
        p.executar("app.project.importFiles(%s, true, app.project.rootItem, false)" % J(novos))
    corte = [[arqs[c], i, d] for c, i, d in CORTE_SECO]
    c1, i1, d1 = DUAS_TRILHAS_V1
    c2, i2, d2, pos2 = DUAS_TRILHAS_V2
    res = p.executar(p._LIB + _JS + """(function(){ var por = _b_por(), corte = %s, out = {};
      var s = _b_seq("BL03 CORTE SECO", por[corte[0][0]]), pos = 0;
      for (var i = 0; i < corte.length; i++) { _b_poe(s.videoTracks[0], por[corte[i][0]], corte[i][1], corte[i][2], pos); pos += corte[i][2]; }
      out.corte = _lab_seqinfo(s);
      var d = _b_seq("BL03 DUAS TRILHAS", por[%s]);
      _b_poe(d.videoTracks[0], por[%s], %d, %d, 0);
      _b_poe(d.videoTracks[1], por[%s], %d, %d, %d);
      out.duas = _lab_seqinfo(d);
      app.project.save(); return out; })()""" % (J(corte), J(arqs[c1]), J(arqs[c1]), i1, d1, J(arqs[c2]), i2, d2, pos2))
    xml = {}
    for nome in ("BL03 CORTE SECO", "BL03 DUAS TRILHAS"):
        destino = os.path.join(TRAB, nome.replace(" ", "_") + ".xml")
        p.executar(p._LIB + "_lab_seq(%s).exportAsFinalCutProXML(%s, 1)" % (J(nome), J(destino)))
        xml[nome] = destino if os.path.exists(destino) else None
    res["xml"] = xml
    with open(os.path.join(TRAB, "premiere.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    for k in ("corte", "duas"):
        print(k, [[(c["nome"][:12], int(c["inicio"]) // QUADRO, int(c["entrada"]) // QUADRO) for c in t["itens"]]
                  for t in res[k]["video"]])
    print(xml)
    return res


ORIGINAIS = os.path.join(MIDIA, "ORIGINAIS_2398")
COPIA = os.path.join(TRAB, "BL03 PREMIERE ORIGINAIS.prproj")


def _originais() -> dict:
    """{nome sem extensão: caminho} dos originais (o casamento por NOME EXATO, como o Conformar fez no MC, 4/4)."""
    o = {}
    for raiz, _d, arqs in os.walk(ORIGINAIS):
        for n in arqs:
            if n.endswith(".mov") and not n.startswith("._"):
                o[os.path.splitext(n)[0]] = os.path.join(raiz, n)
    return o


def _xml_por_id(seq_id: str, destino: str) -> None:
    p.executar("""(function(){ for (var i = 0; i < app.project.sequences.numSequences; i++) {
      var s = app.project.sequences[i]; if (s.sequenceID == %s) return s.exportAsFinalCutProXML(%s, 1); }
      throw "sequência não achada"; })()""" % (J(seq_id), J(destino)))


def consertar_nomes() -> dict:
    """(uma vez, 2026-11-21) as importadas antes do conserto: a de clipes nos ORIGINAIS ganha o sufixo e sai o XML."""
    novas = p.executar(p._LIB + """(function(){ var o = [];
      for (var i = 0; i < app.project.sequences.numSequences; i++) { var s = app.project.sequences[i], c = s.videoTracks[0].clips;
        if (c.numItems && c[0].projectItem.getMediaPath().indexOf("ORIGINAIS_2398") >= 0) {
          if (s.name.indexOf(" ORIGINAIS") < 0) s.name = s.name + " ORIGINAIS"; o.push({nome: s.name, id: s.sequenceID}); } }
      app.project.save(); return o; })()""")
    for n in novas:
        _xml_por_id(n["id"], os.path.join(TRAB, n["nome"].replace(" ", "_").replace("_ORIGINAIS", "") + "_ORIGINAIS.xml"))
    print(novas)
    return novas


def religar() -> dict:
    """O editor online do PREMIERE pelas peças do Conformar (`motor/prproj/copia.gravar_copia`: a cópia do .prproj com
    cada <Media> no original, o FrameRect no raster novo) → `importSequences` das duas sequências no projeto aberto → a
    escala do original de outro raster (UHD numa sequência HD = 50, o que o `dlpcImportarCopia` do produto faz) → o XML
    das sequências NOVAS (o que vai à cor)."""
    import subprocess
    sys.path.insert(0, os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar", "motor"))
    from prproj.copia import gravar_copia
    p.executar("app.project.save()")
    orig = _originais()
    troca, raster = {}, {}
    for n in sorted(os.listdir(DAILIES)):
        if n.endswith(".mov") and not n.startswith("._"):
            o = orig[os.path.splitext(n)[0]]
            troca[os.path.join(DAILIES, n)] = o
            v = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height", "-of", "json", o], capture_output=True, text=True,
                                          check=True).stdout)["streams"][0]
            raster[o] = (v["width"], v["height"])
    conta = gravar_copia(PROJETO, COPIA, troca, raster)
    print("cópia:", conta)
    res = p.executar(p._LIB + """(function(){ var copia = %s, ids = [], out = {};
      var nomes = ["BL03 CORTE SECO", "BL03 DUAS TRILHAS"];
      for (var i = 0; i < nomes.length; i++) ids.push(_lab_seq(nomes[i]).sequenceID);
      var antes = app.project.sequences.numSequences;
      out.importou = app.project.importSequences(copia, ids);
      out.novas = [];
      for (var i = antes; i < app.project.sequences.numSequences; i++) { var s = app.project.sequences[i];
        var esc = 0;
        for (var t = 0; t < s.videoTracks.numTracks; t++) for (var j = 0; j < s.videoTracks[t].clips.numItems; j++) {
          var c = s.videoTracks[t].clips[j], pi = c.projectItem, md = pi ? pi.getProjectMetadata() : "";
          if (md.indexOf("3840 x 2160") >= 0) { for (var k = 0; k < c.components.numItems; k++) {
              var cp = c.components[k]; if (cp.matchName != "AE.ADBE Motion") continue;
              for (var q = 0; q < cp.properties.numItems; q++) if (cp.properties[q].displayName == "Scale") { cp.properties[q].setValue(50, true); esc++; } } } }
        s.name = s.name + " ORIGINAIS";                     // ⛔ o import vem com o MESMO nome: exportar por id
        var info = _lab_seqinfo(s); info.escalas = esc;
        info.caminhos = [];
        for (var t = 0; t < s.videoTracks.numTracks; t++) for (var j = 0; j < s.videoTracks[t].clips.numItems; j++)
          info.caminhos.push(s.videoTracks[t].clips[j].projectItem.getMediaPath());
        out.novas.push(info); }
      app.project.save(); return out; })()""" % J(COPIA))
    xml = {}
    for info in res["novas"]:
        destino = os.path.join(TRAB, info["nome"].replace(" ", "_") + "_ORIGINAIS.xml")
        _xml_por_id(info["id"], destino)
        xml[info["nome"]] = destino if os.path.exists(destino) else None
        print(info["nome"], "escalas", info["escalas"], [c.split("/")[-2] + "/" + c.split("/")[-1][:12] for c in info["caminhos"]])
    res["xml"] = xml
    with open(os.path.join(TRAB, "religado.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print(xml)
    return res


def vidref(nome: str = "BL03 CORTE SECO") -> str:
    """O vid ref da sequência OFFLINE do Premiere (nos dailies) pelo `exportAsMediaDirect` com o preset ProRes 422 da
    instalação — o que o editor anexa para a cor."""
    destino = os.path.join(TRAB, nome.replace(" ", "_") + "_REF.mov")
    if os.path.exists(destino):
        os.remove(destino)
    p.executar(p._LIB + "_lab_seq(%s).exportAsMediaDirect(%s, %s, 0)" % (J(nome), J(destino), J(p.preset_prores(ANO))),
               timeout=900)
    print(destino, os.path.getsize(destino))
    return destino


def segmentos_do_xml(xml: str) -> list[dict]:
    """Os clipes de IMAGEM do xmeml na forma que o `avid_baselight.conferir` usa (`_pos`, in, duração, arquivo, trilha).
    O `<file>` repetido vem só com o id: o caminho é o da 1ª aparição."""
    import urllib.parse
    import xml.etree.ElementTree as ET
    seq = ET.parse(xml).getroot().find(".//sequence")
    arquivos, out = {}, []
    for f in seq.iter("file"):
        if f.findtext("pathurl"):
            arquivos[f.get("id")] = urllib.parse.unquote(f.findtext("pathurl").replace("file://localhost", "").replace("file://", ""))
    for n, trilha in enumerate(seq.find("media/video").findall("track"), start=1):
        for ci in trilha.findall("clipitem"):
            ini, fim = int(ci.findtext("start")), int(ci.findtext("end"))
            out.append({"_pos": ini, "duration_frames": fim - ini, "source_start_frames": int(ci.findtext("in")),
                        "media_ref": {"local_path": arquivos[ci.find("file").get("id")]}, "track": n,
                        "clip_name": ci.findtext("name"), "is_audio": False, "is_gap": False})
    return out


def conferir(nome: str = "BL03 CORTE SECO") -> dict:
    from .avid_baselight import conferir as _conferir
    xml = os.path.join(TRAB, nome.replace(" ", "_") + "_ORIGINAIS.xml")
    return _conferir(xml.replace(".xml", ".aaf"), os.path.join(TRAB, nome.replace(" ", "_") + "_REF.mov"),
                     segmentos=segmentos_do_xml(xml))


# ── BL06: as RAMPAS do Premiere (a bancada B22, numa pasta própria) → render (a verdade) + XML (o que vai à cor) ──
TRAB_RAMPA = os.path.join(TRAB, "BL06_RAMPAS")


def rampas() -> dict:
    """Monta a B22 (RAMPA_A 1,2×→1,9×, RAMPA_B 2×→0,6× com o in na curva, RAMPA_C 50 %) no Premiere aberto, escreve o
    Time Remapping, renderiza (ProRes 4444), exporta o xmeml da sequência e lê cada quadro do render."""
    from . import premiere_rampas as R
    os.makedirs(TRAB_RAMPA, exist_ok=True)
    R.TRAB, R.ANO = TRAB_RAMPA, ANO
    R.PROJETO = os.path.join(TRAB_RAMPA, "BL06 RAMPAS.prproj")
    R.RENDER = os.path.join(TRAB_RAMPA, "BL06_RAMPAS_REF.mov")
    print("montar", R.montar())
    print("forcar", R.forcar())
    print("conferir", R.conferir())
    R.renderizar()
    xml = os.path.join(TRAB_RAMPA, "BL06_RAMPAS.xml")
    R.x("_lab_seq(%s).exportAsFinalCutProXML(%s, 1)" % (J("B22"), J(xml)))
    res = R.medir(R.RENDER)
    for nome, v in res.items():
        print(nome, {k: v[k] for k in ("piso", "perto", "ilegivel", "n")})
    print(xml, os.path.exists(xml))
    return res


if __name__ == "__main__":
    {"abrir": abrir, "montar": montar, "religar": religar, "consertar_nomes": consertar_nomes, "vidref": vidref, "conferir": conferir, "rampas": rampas}[sys.argv[1]]()

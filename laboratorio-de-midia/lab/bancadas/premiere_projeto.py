"""B07 PROJETO — um projeto de verdade montado pela ponte, para medir o que cada versão do Premiere grava e o que
sobrevive ao DOWNGRADE: bins e sub-bins, bin inteligente, subclipe, rótulo de cor, sequência com efeitos (Movimento,
Opacidade com keyframes, Recorte, Desfoque gaussiano, Preto e branco), transição, título .mogrt, legenda (.srt),
marcadores de sequência e de clipe, efeito de áudio e uma sequência ANINHADA.

    python3 -m lab.bancadas.premiere_projeto montar          # no Premiere aberto → saida/bancadas/premiere-<v>/B07_PROJETO
    python3 -m lab.bancadas.premiere_projeto retrato <prproj> # abre e descreve (o que o downgrade tem de preservar)

A mídia é a do laboratório (B01 mov 25p 1080, B06 câmera e som). Efeito e transição são achados pelo NOME, que sai
no idioma do app (banco, api-extendscript.md §Beta 27.1): cada um tem a lista dos nomes conhecidos.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

from . import premiere as p

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASO = "B07_PROJETO"
NOME = "LAB B07 PROJETO"
MOV = os.path.join(RAIZ, "saida", "base", "B01_FORMATOS", "B01_MOV-PRORES.mov")
CAM = os.path.join(RAIZ, "saida", "base", "B06_SOM_DIRETO", "B06_CAM_MOV-PRORES.mov")
SOM = os.path.join(RAIZ, "saida", "base", "B06_SOM_DIRETO", "B06_SOM_WAV-BWF.wav")
MOGRT_25 = "/Applications/Adobe Premiere Pro 2025/Adobe Premiere Pro 2025.app/Contents/Essential Graphics/Basic Title.mogrt"

# efeito/transição → nomes conhecidos, NA ORDEM de preferência (inglês do 25.6.5; português do 26.0.2 e do 27.1).
# ⚠️ O QE devolve um objeto até para nome que não existe (com `name` vazio) — e o nome pode ser de OUTRO efeito: no
# 26.0.2 em português, "Gaussian Blur" é o do plug-in FilmImpact (`AE.Impact_Blur_FX`) e o da Adobe virou
# "Desfoque Gaussiano (herdado)". Por isso a ordem, e o `matchName` conferido depois (MATCH).
NOMES = {
    "desfoque": ["Desfoque Gaussiano (herdado)", "Gaussian Blur", "Desfoque gaussiano"],
    "pb": ["Black & White", "Preto e branco"],
    "recorte": ["Crop", "Cortar", "Cortar (legado)"],
    "dissolve": ["Dissolução cruzada (herdada)", "Cross Dissolve", "Dissolução cruzada"],
    "amplificar": ["Amplify", "Amplificar"],
}
# os quadros do retrato (SEQ EFEITOS, 25 q/s). Até 6 s NÃO há texto: o título e as legendas começam em 6 s, porque o
# texto padrão do título sai no IDIOMA do app ("Your Title Here" × "Seu título fica aqui") e o 27.1 desenha a legenda
# no quadro exportado (o 25/26 não) — com texto, o PSNR mediria idioma, não o efeito. QUADROS_TEXTO só se olha.
QUADROS = [12, 37, 62, 100, 106, 137]          # A (Movimento, Recorte, Opacidade com keyframes), a dissolução, B (Desfoque, P&B)
QUADROS_TEXTO = [162, 187]                      # título + legenda

_JS = p._LIB + r"""
function _lab_bin(caminho) { var pai = app.project.rootItem, partes = caminho.split("/");
  for (var i = 0; i < partes.length; i++) { var achou = null;
    for (var j = 0; j < pai.children.numItems; j++) { var c = pai.children[j]; if (c.type == 2 && c.name == partes[i]) achou = c; }
    if (!achou) achou = pai.createBin(partes[i]);
    pai = achou; }
  return pai; }
function _lab_midia(caminho) { var it = _lab_itens(app.project.rootItem);
  for (var i = 0; i < it.length; i++) if (it[i].getMediaPath() == caminho) return it[i]; return null; }
function _lab_nome(nome) { var it = _lab_itens(app.project.rootItem);
  for (var i = 0; i < it.length; i++) if (it[i].name == nome) return it[i]; return null; }
function _lab_fx(nomes, audio) { app.enableQE();
  for (var i = 0; i < nomes.length; i++) { var e = audio ? qe.project.getAudioEffectByName(nomes[i]) : qe.project.getVideoEffectByName(nomes[i]);
    if (e && e.name) return e; } throw new Error("efeito não achado: " + nomes.join(" | ")); }
function _lab_tr(nomes) { app.enableQE();
  for (var i = 0; i < nomes.length; i++) { var e = qe.project.getVideoTransitionByName(nomes[i]); if (e && e.name) return e; }
  throw new Error("transição não achada: " + nomes.join(" | ")); }
function _lab_matches(ti) { var o = []; for (var i = 0; i < ti.components.numItems; i++) o.push(ti.components[i].matchName); return o; }
// o componente que o addVideoEffect/addAudioEffect acabou de pôr: o que não estava ANTES
function _lab_novo(ti, antes) { for (var i = 0; i < ti.components.numItems; i++) { var m = ti.components[i].matchName, ja = false;
    for (var j = 0; j < antes.length; j++) if (antes[j] == m) ja = true;
    if (!ja) return ti.components[i]; }
  throw new Error("o efeito não entrou (componentes: " + _lab_matches(ti).join(", ") + ")"); }
function _lab_comp(ti, match) { for (var i = 0; i < ti.components.numItems; i++) if (ti.components[i].matchName == match) return ti.components[i];
  return null; }
"""


def _js(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _srt(caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("1\n00:00:06,000 --> 00:00:06,800\nLEGENDA UM\n\n2\n00:00:07,000 --> 00:00:07,800\nLEGENDA DOIS\n")


def montar(trabalho: str) -> dict:
    """Monta o B07 do zero no Premiere aberto. Cada passo numa chamada (um diálogo ou uma queda diz em qual)."""
    trabalho = os.path.abspath(trabalho)
    p.salvar_e_fechar()                       # antes de apagar: o projeto pode ser o que está aberto
    if os.path.isdir(trabalho):
        # RENOMEIA, não apaga: o Premiere grava autossalvamento e cache DENTRO da pasta enquanto se apaga (2026-10-07:
        # "Directory not empty", e o diálogo "Projeto modificado" travou a ponte)
        os.rename(trabalho, trabalho + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.join(trabalho, "insumos"))
    projeto = os.path.join(trabalho, NOME + ".prproj")
    mogrt = os.path.join(trabalho, "insumos", "Basic Title.mogrt")
    shutil.copyfile(MOGRT_25, mogrt)          # o MESMO molde nas três versões: o do 25 (o mais velho)
    # numa subpasta ÚNICA por montagem: o Beta 27.1 aberto reaproveitou o .srt ANTIGO do mesmo caminho (cache por
    # caminho, 2026-10-07) — o nome do arquivo fica igual, para o retrato comparar
    srt = os.path.join(trabalho, "insumos", time.strftime("%Y%m%d-%H%M%S"), "B07 LEGENDAS.srt")
    os.makedirs(os.path.dirname(srt))
    _srt(srt)
    passos = []

    def passo(nome, js, timeout=300):
        t0 = time.time()
        try:
            r = p.executar(_JS + js, timeout=timeout)
            passos.append({"passo": nome, "ok": True, "valor": r, "s": round(time.time() - t0, 1)})
        except RuntimeError as e:
            passos.append({"passo": nome, "ok": False, "erro": str(e), "s": round(time.time() - t0, 1)})
        print(time.strftime("%H:%M:%S"), passos[-1], flush=True)
        return passos[-1]

    passo("novo projeto", "app.newProject(%s)" % _js(projeto))
    passo("bins", """(function(){ var o = [];
      var b = ["01 MIDIA/CAMERA", "01 MIDIA/SOM", "02 SUBCLIPES", "03 SEQUENCIAS", "04 GRAFICOS E LEGENDAS"];
      for (var i = 0; i < b.length; i++) o.push(_lab_bin(b[i]).name); return o; })()""")
    passo("importar", """(function(){
      app.project.importFiles([%s, %s], true, _lab_bin("01 MIDIA/CAMERA"), false);
      app.project.importFiles([%s], true, _lab_bin("01 MIDIA/SOM"), false);
      app.project.importFiles([%s], true, _lab_bin("04 GRAFICOS E LEGENDAS"), false);
      return [!!_lab_midia(%s), !!_lab_midia(%s), !!_lab_midia(%s), !!_lab_midia(%s)]; })()"""
          % (_js(MOV), _js(CAM), _js(SOM), _js(srt), _js(MOV), _js(CAM), _js(SOM), _js(srt)))
    passo("bin inteligente", """(function(){ return String(app.project.rootItem.createSmartBin("05 SO MOV", "MOV")); })()""")
    passo("rótulo de cor", """(function(){ _lab_midia(%s).setColorLabel(3); _lab_midia(%s).setColorLabel(5);
      return [_lab_midia(%s).getColorLabel(), _lab_midia(%s).getColorLabel()]; })()""" % (_js(MOV), _js(SOM), _js(MOV), _js(SOM)))
    # subclipe de 2 s a 6 s do mov (ticks), na bin própria
    passo("subclipe", """(function(){ var m = _lab_midia(%s), t = %d;
      var s = m.createSubClip("SUB B01 2s-6s", String(2 * t), String(6 * t), 1, 1, 1);
      s.moveBin(_lab_bin("02 SUBCLIPES")); return [s.name, s.getInPoint().seconds, s.getOutPoint().seconds]; })()""" % (_js(MOV), p.TICKS))
    passo("marcador de clipe", """(function(){ var m = _lab_midia(%s).getMarkers().createMarker(1);
      m.name = "MARCADOR DO CLIPE"; m.comments = "no clipe, 1 s"; return m.start.seconds; })()""" % _js(MOV))
    # SEQ EFEITOS: A = mov 0–4 s em 0; B = o subclipe (2–6 s) em 4 s
    passo("sequência", """(function(){ var m = _lab_midia(%s), sub = _lab_nome("SUB B01 2s-6s");
      var s = app.project.createNewSequenceFromClips("SEQ EFEITOS", [m], _lab_bin("03 SEQUENCIAS"));
      for (var k = s.videoTracks.numTracks - 1; k >= 0; k--) while (s.videoTracks[k].clips.numItems) s.videoTracks[k].clips[0].remove(false, false);
      for (var k = s.audioTracks.numTracks - 1; k >= 0; k--) while (s.audioTracks[k].clips.numItems) s.audioTracks[k].clips[0].remove(false, false);
      m.setInPoint(0, 4); m.setOutPoint(4, 4);
      s.videoTracks[0].overwriteClip(m, 0);
      m.clearInPoint(); m.clearOutPoint();
      s.videoTracks[0].overwriteClip(sub, 4);
      return _lab_seqinfo(s); })()""" % _js(MOV))
    passo("Movimento e Opacidade (keyframes)", """(function(){ var s = _lab_seq("SEQ EFEITOS"), a = s.videoTracks[0].clips[0];
      var mov = _lab_comp(a, "AE.ADBE Motion"), op = _lab_comp(a, "AE.ADBE Opacity");
      mov.properties[1].setValue(80, true); mov.properties[4].setValue(5, true);
      var o = op.properties[0]; o.setTimeVarying(true);
      o.addKey(0); o.setValueAtKey(0, 100, true); o.addKey(2); o.setValueAtKey(2, 50, true);
      return [mov.properties[1].getValue(), mov.properties[4].getValue(), o.getKeys().length]; })()""")
    passo("Recorte", """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID);
      var q = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0); app.enableQE();
      var a = s.videoTracks[0].clips[0], antes = _lab_matches(a), fx = _lab_fx(%s);
      q.addVideoEffect(fx); var c = _lab_novo(a, antes);
      c.properties[0].setValue(10, true); c.properties[2].setValue(10, true);
      return [fx.name, c.matchName, c.displayName, c.properties[0].getValue(), c.properties[2].getValue()]; })()""" % _js(NOMES["recorte"]))
    passo("Desfoque + Preto e branco", """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID); app.enableQE();
      var q = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(1);
      var b = s.videoTracks[0].clips[1], antes = _lab_matches(b), fx = _lab_fx(%s);
      q.addVideoEffect(fx); var d = _lab_novo(b, antes); d.properties[0].setValue(25, true);
      antes = _lab_matches(b); var fx2 = _lab_fx(%s); q.addVideoEffect(fx2); var pb = _lab_novo(b, antes);
      return [fx.name, d.matchName, d.properties[0].displayName, d.properties[0].getValue(), fx2.name, pb.matchName]; })()""" % (_js(NOMES["desfoque"]), _js(NOMES["pb"])))
    passo("transição", """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID); app.enableQE();
      var q = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(1);
      var tr = _lab_tr(%s); q.addTransition(tr, true, "00:00:01:00");
      var qt = qe.project.getActiveSequence().getVideoTrackAt(0), o = [tr.name];
      for (var n = 0; n < qt.numTransitions; n++) { var t = qt.getTransitionAt(n); if (t && t.name) o.push([t.name, t.start.timecode, t.end.timecode]); }
      return o; })()""" % _js(NOMES["dissolve"]))
    passo("efeito de áudio", """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID); app.enableQE();
      var q = qe.project.getActiveSequence().getAudioTrackAt(0).getItemAt(0);
      var a = s.audioTracks[0].clips[0], antes = _lab_matches(a), fx = _lab_fx(%s, true);
      q.addAudioEffect(fx); var c = _lab_novo(a, antes);
      return [fx.name, c.matchName, c.displayName]; })()""" % _js(NOMES["amplificar"]))
    passo("título .mogrt", """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID);
      s.importMGT(%s, String(6 * %d), 1, 0);
      // o importMGT põe o gráfico mas devolve null (26.0.2): o item se acha na V2
      var ti = s.videoTracks[1].clips.numItems ? s.videoTracks[1].clips[0] : null;
      if (!ti) throw new Error("o gráfico não entrou na V2");
      // o "Basic Title" é texto NATIVO (componentes Graphic Group + Text), não AE: o getMGTComponent volta null
      var g = ti.getMGTComponent(), cs = []; for (var i = 0; i < ti.components.numItems; i++) cs.push(ti.components[i].matchName);
      return [ti.name, ti.start.seconds, ti.end.seconds, !!g, cs]; })()""" % (_js(mogrt), p.TICKS))
    passo("legenda", """(function(){ var s = _lab_seq("SEQ EFEITOS"), srt = _lab_midia(%s);
      var r = s.createCaptionTrack(srt, 0, Sequence.CAPTION_FORMAT_SUBTITLE); return String(r); })()""" % _js(srt))
    passo("marcadores da sequência", """(function(){ var s = _lab_seq("SEQ EFEITOS"), o = [];
      var m1 = s.markers.createMarker(1); m1.name = "MARCADOR 1"; m1.comments = "comentário"; m1.setColorByIndex(2);
      var m2 = s.markers.createMarker(3); m2.name = "CAPÍTULO"; m2.setTypeAsChapter(); m2.end = 5;
      return [m1.start.seconds, m2.start.seconds, m2.end.seconds, m2.type]; })()""")
    # SEQ MASTER: a SEQ EFEITOS aninhada em 0 e a câmera do B06 depois dela
    passo("sequência aninhada", """(function(){ var ef = _lab_seq("SEQ EFEITOS"), cam = _lab_midia(%s), item = null;
      var it = _lab_itens(app.project.rootItem); for (var i = 0; i < it.length; i++) if (it[i].isSequence() && it[i].name == "SEQ EFEITOS") item = it[i];
      var s = app.project.createNewSequenceFromClips("SEQ MASTER", [item], _lab_bin("03 SEQUENCIAS"));
      s.videoTracks[0].overwriteClip(cam, ef.end / %d);
      return _lab_seqinfo(s); })()""" % (_js(CAM), p.TICKS))
    passo("salvar", "app.project.save()")
    with open(os.path.join(trabalho, "montagem.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"versao": p.executar("app.version"), "projeto": projeto, "passos": passos}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return {"projeto": projeto, "falharam": [x["passo"] for x in passos if not x["ok"]]}


_RETRATO_LIB = _JS + r"""
  // texto LONGO (Blob do Lumetri, curvas, máscara) ou com caractere de CONTROLE (o nulo do Lumetri corta a resposta da
  // ponte: "sem saída", CANAL-K COPA 2026-10-07) vira "#tamanho:soma" — basta para ver se mudou
  // binário guardado como texto: caractere de controle (o nulo) ou UTF-16 inválido (surrogate solto, 0xDE40 num
  // parâmetro do Lumetri) — a ponte não serializa
  function sujo(t) { for (var i = 0; i < t.length; i++) { var c = t.charCodeAt(i); if (c < 32 || (c >= 0xD800 && c <= 0xDFFF)) return true; } return false; }
  function resumo(t) { var h = 0; for (var i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) % 1000000007; return "#" + t.length + ":" + h; }
  function val(v) { try { if (v === undefined || v === null) return null; if (typeof v == "string" && (v.length > 120 || sujo(v))) return resumo(v); if (typeof v == "object" && v.length !== undefined) { var o = []; for (var i = 0; i < v.length; i++) o.push(val(v[i])); return o; } return v; } catch (e) { return String(e); } }
  function arvore(pasta) { var o = [];
    for (var i = 0; i < pasta.children.numItems; i++) { var c = pasta.children[i], e = {nome: c.name, tipo: c.type};
      if (c.type == 2) e.filhos = arvore(c);
      else { try { e.midia = c.getMediaPath(); } catch (x) {} try { e.sequencia = c.isSequence(); } catch (x) {}
        try { e.merged = c.isMergedClip(); e.multicam = c.isMulticamClip(); } catch (x) {}
        try { e.rotulo = c.getColorLabel(); } catch (x) {}
        try { e.entrada = c.getInPoint().seconds; e.saida = c.getOutPoint().seconds; } catch (x) {}
        try { var mk = c.getMarkers(), m = mk.getFirstMarker(), l = []; while (m) { l.push({nome: m.name, inicio: m.start.seconds, comentario: m.comments}); m = mk.getNextMarker(m); } e.marcadores = l; } catch (x) {} }
      o.push(e); }
    return o; }
  function comps(ti) { var o = [];
    for (var i = 0; i < ti.components.numItems; i++) { var c = ti.components[i], ps = [];
      for (var j = 0; j < c.properties.numItems; j++) { var pr = c.properties[j], e = {nome: pr.displayName};
        try { e.valor = val(pr.getValue()); } catch (x) { e.valor = null; }
        try { if (pr.isTimeVarying()) { var ks = pr.getKeys(), kl = []; for (var k = 0; k < ks.length; k++) kl.push([ks[k].seconds, val(pr.getValueAtKey(ks[k]))]); e.keys = kl; } } catch (x) {}
        ps.push(e); }
      o.push({match: c.matchName, nome: c.displayName, parametros: ps}); }
    return o; }
  function trilhas(col) { var o = [];
    for (var i = 0; i < col.numTracks; i++) { var t = col[i], it = [];
      for (var j = 0; j < t.clips.numItems; j++) { var c = t.clips[j], e = {nome: c.name, inicio: c.start.seconds, fim: c.end.seconds, entrada: c.inPoint.seconds};
        try { e.mgt = c.isMGT(); } catch (x) {}
        try { e.origem = c.projectItem ? c.projectItem.name : null; } catch (x) {}
        e.componentes = comps(c); it.push(e); }
      o.push({trilha: i + 1, nome: t.name, itens: it}); }
    return o; }

function _lab_seq_retrato(s) { var ml = [], mk = s.markers, m = mk.getFirstMarker();
    while (m) { ml.push({nome: m.name, inicio: m.start.seconds, fim: m.end.seconds, tipo: m.type, comentario: m.comments, cor: (function(){ try { return m.getColorByIndex(); } catch (x) { return null; } })()}); m = mk.getNextMarker(m); }
    app.project.openSequence(s.sequenceID); app.enableQE();
    var q = qe.project.getActiveSequence(), tr = [];
    for (var k = 0; k < q.numVideoTracks; k++) { var qt = q.getVideoTrackAt(k);
      // o QE lista também os VÃOS entre transições (nome vazio): só as que têm nome
      for (var n = 0; n < qt.numTransitions; n++) { var t = qt.getTransitionAt(n); if (t && t.name) tr.push({trilha: k + 1, nome: t.name, inicio: t.start.timecode, fim: t.end.timecode}); } }
    return {nome: s.name, fim: s.end, video: trilhas(s.videoTracks), audio: trilhas(s.audioTracks), marcadores: ml, transicoes: tr,
            trilhas_qe: {video: q.numVideoTracks, audio: q.numAudioTracks}}; }
"""


def retrato(stills_em: str | None = None) -> dict:
    """O projeto aberto descrito: a árvore de bins, cada sequência com trilhas, itens, componentes (match, nome,
    valor de cada parâmetro e keyframes), marcadores e transições. E, com `stills_em`, os quadros QUADROS da SEQ EFEITOS."""
    # em PARTES: a árvore de bins e cada sequência numa chamada (um projeto real — o CANAL-K COPA, 42 sequências, 138
    # Lumetri — não cabe numa resposta só da ponte: "sem saída")
    bins = p.executar(_RETRATO_LIB + "(function(){ return {versao: app.version, n: app.project.sequences.numSequences, bins: arvore(app.project.rootItem)}; })()", timeout=600)
    seqs = [p.executar(_RETRATO_LIB + "_lab_seq_retrato(app.project.sequences[%d])" % n, timeout=600) for n in range(bins["n"])]
    r = {"versao": bins["versao"], "bins": bins["bins"], "sequencias": seqs}
    if stills_em:
        stills_em = os.path.abspath(stills_em)     # o Premiere resolve caminho relativo pela pasta DELE
        os.makedirs(stills_em, exist_ok=True)
        feitos = {}
        for q in QUADROS + QUADROS_TEXTO:
            arq = os.path.join(stills_em, f"SEQ_EFEITOS_{q:04d}")
            p.executar(_JS + """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID); app.enableQE();
              s.setPlayerPosition(%s); var qs = qe.project.getActiveSequence(); return qs.exportFramePNG(qs.CTI.timecode, %s); })()"""
                       % (_js(str(q * p.TICKS // 25)), _js(arq)))
            limite = time.time() + 10
            while not os.path.exists(arq + ".png") and time.time() < limite:
                time.sleep(0.2)
            time.sleep(0.5)
            feitos[q] = os.path.exists(arq + ".png")
        r["stills"] = feitos
    return r


def renderizar(trabalho: str) -> dict:
    """A SEQ EFEITOS pelo render de verdade (`exportAsMediaDirect`, o preset ProRes 422 "Match Source" da própria
    versão): a legenda sai gravada na imagem ou não? (no preset das três versões, `ADBECaptionExportOption` = 0)"""
    v = p.executar("app.version")
    ano = {"23": "2023", "25": "2025", "26": "2026", "27": "2027"}.get(v.split(".")[0], "Beta")   # 27 oficial desde 2026-11-15
    preset = os.path.join(p._app(ano), p.PRESET_PRORES)
    destino = os.path.join(os.path.abspath(trabalho), "renders", "RENDER SEQ EFEITOS.mov")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    r = p.executar(_JS + """(function(){ var s = _lab_seq("SEQ EFEITOS"); app.project.openSequence(s.sequenceID);
      return s.exportAsMediaDirect(%s, %s, 0); })()""" % (_js(destino), _js(preset)), timeout=900)
    return {"job": r, "arquivo": destino, "preset": preset}


def normalizar(ret: dict) -> dict:
    """O retrato sem o que depende do IDIOMA do app (nome de trilha, de componente, de parâmetro, de transição) nem
    da máquina (caminho completo): o que o downgrade tem de preservar."""
    def bins(lista):
        o = []
        for e in lista:
            x = {k: e.get(k) for k in ("nome", "tipo", "sequencia", "merged", "multicam", "rotulo", "entrada", "saida")}
            x["midia"] = os.path.basename(e["midia"]) if e.get("midia") else None
            x["marcadores"] = [(m["nome"], m["inicio"], m["comentario"]) for m in e.get("marcadores") or []]
            if "filhos" in e:
                x["filhos"] = bins(e["filhos"])
            o.append(x)
        return sorted(o, key=lambda x: (x["nome"], x["tipo"]))

    def trilhas(lista):
        return [[{"inicio": i["inicio"], "fim": i["fim"], "entrada": i["entrada"], "mgt": i.get("mgt"),
                  "componentes": [{"match": c["match"], "valores": [pr.get("valor") for pr in c["parametros"]],
                                   "keys": [pr.get("keys") for pr in c["parametros"] if pr.get("keys")]} for c in i["componentes"]]}
                 for i in t["itens"]] for t in lista]

    seqs = {}
    for sq in ret["sequencias"]:
        seqs[sq["nome"]] = {"fim": sq["fim"], "video": trilhas(sq["video"]), "audio": trilhas(sq["audio"]),
                            "marcadores": [(m["nome"], m["inicio"], m["fim"], m["tipo"], m["comentario"], m.get("cor")) for m in sq["marcadores"]],
                            "transicoes": [(t["trilha"], t["inicio"], t["fim"]) for t in sq["transicoes"]]}
    return {"bins": bins(ret["bins"]), "sequencias": seqs}


def diferencas(a: dict, b: dict, caminho: str = "") -> list:
    """As folhas que diferem entre dois retratos normalizados."""
    if isinstance(a, dict) and isinstance(b, dict):
        o = []
        for k in sorted(set(a) | set(b), key=str):
            o += diferencas(a.get(k), b.get(k), f"{caminho}.{k}")
        return o
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
        o = []
        for n, (x, y) in enumerate(zip(a, b)):
            o += diferencas(x, y, f"{caminho}[{n}]")
        return o
    if isinstance(a, float) or isinstance(b, float):
        try:
            return [] if abs(float(a) - float(b)) < 1e-3 else [(caminho, a, b)]
        except (TypeError, ValueError):
            pass
    return [] if a == b else [(caminho, a, b)]


def psnr(a: str, b: str) -> float | None:
    """PSNR entre dois stills (dB; inf = idênticos), pelo ffmpeg do laboratório."""
    import re
    import subprocess
    from .. import ffmpeg
    r = subprocess.run([ffmpeg.achar("ffmpeg"), "-hide_banner", "-i", a, "-i", b, "-lavfi", "psnr", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"average:(\S+)", r.stderr)
    return None if not m else (float("inf") if m.group(1) == "inf" else float(m.group(1)))


def comparar(trab_a: str, trab_b: str) -> dict:
    """Dois trabalhos do B07 (cada um com retrato.json e stills/): o que difere no projeto e quanto os quadros diferem."""
    with open(os.path.join(trab_a, "retrato.json"), encoding="utf-8") as fa, open(os.path.join(trab_b, "retrato.json"), encoding="utf-8") as fb:
        ra, rb = json.load(fa), json.load(fb)
    dif = diferencas(normalizar(ra), normalizar(rb))
    quadros = {q: psnr(os.path.join(trab_a, "stills", f"SEQ_EFEITOS_{q:04d}.png"), os.path.join(trab_b, "stills", f"SEQ_EFEITOS_{q:04d}.png"))
               for q in QUADROS}
    return {"versoes": [ra["versao"], rb["versao"]], "diferencas": dif, "psnr_db": quadros}


def downgrade(de: str, para: str) -> dict:
    """O B07 que a versão `de` salvou, rebaixado e aberto na `para` (a que está aberta): o retrato comparado com o da
    ORIGEM (o projeto tem de chegar inteiro) e os quadros com os da `para` NATIVA (o destino tem de desenhar igual)."""
    from .. import prproj_downgrade
    v = p.executar("app.version")
    if v != para:
        raise SystemExit(f"a ponte respondeu do Premiere {v}, não do {para}")
    trab = os.path.abspath(os.path.join(RAIZ, "saida", "bancadas", f"downgrade-{de}-para-{para}", CASO))
    p.salvar_e_fechar()
    if os.path.isdir(trab):
        os.rename(trab, trab + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(trab)
    alvo = os.path.join(trab, NOME + ".prproj")
    r = prproj_downgrade.rebaixar(os.path.join(RAIZ, "resultados", CASO, "prproj", f"premiere-{de}-darwin.prproj"), alvo, para)
    shutil.copyfile(alvo, os.path.join(trab, "rebaixado-antes-de-abrir.prproj"))
    aberto = p.executar("app.openDocument(%s, true, true, true)" % _js(alvo), timeout=120)
    caminho = p.executar("(function(){ try { return app.project.path; } catch (e) { return ''; } })()")
    out = {"de": de, "para": para, "rebaixar": r, "openDocument": aberto, "abriu": caminho == alvo}
    if out["abriu"]:
        ret = retrato(os.path.join(trab, "stills"))
        with open(os.path.join(trab, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(ret, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        origem = os.path.join(RAIZ, "saida", "bancadas", f"premiere-{de}", CASO)
        nativo = os.path.join(RAIZ, "saida", "bancadas", f"premiere-{para}", CASO)
        out["contra_a_origem"] = comparar(origem, trab)
        out["contra_o_destino_nativo"] = comparar(nativo, trab)
        p.salvar_e_fechar()
    with open(os.path.join(RAIZ, "resultados", CASO, f"downgrade-{de}-para-{para}-darwin.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    os.chdir(RAIZ)
    if argv[0] == "montar":
        v = p.executar("app.version")
        trab = os.path.join("saida", "bancadas", f"premiere-{v}", CASO)
        r = montar(trab)
        print(r)
        # o retrato é do ARQUIVO: salvar, fechar e reabrir (logo depois da montagem o QE ainda não lista a transição)
        p.salvar_e_fechar()
        p.executar("app.openDocument(%s, true, true, true)" % _js(os.path.abspath(r["projeto"])), timeout=120)
        ret = retrato(os.path.join(trab, "stills"))
        ret["render"] = renderizar(trab)
        with open(os.path.join(trab, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(ret, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        p.executar("app.project.save()")
        return 0 if not r["falharam"] else 1
    if argv[0] == "downgrade":
        r = downgrade(argv[1], argv[2])
        print({k: r[k] for k in ("de", "para", "abriu")}, r["rebaixar"]["sobrou_versao_de_origem"])
        for k in ("contra_a_origem", "contra_o_destino_nativo"):
            if k in r:
                print(k, "psnr", r[k]["psnr_db"], "diferenças:", r[k]["diferencas"][:8])
        return 0
    if argv[0] == "comparar":
        print(json.dumps(comparar(argv[1], argv[2]), ensure_ascii=False, indent=1, default=str))
        return 0
    if argv[0] == "retrato":
        p.salvar_e_fechar()
        p.executar("app.openDocument(%s, true, true, true)" % _js(os.path.abspath(argv[1])), timeout=120)
        print(json.dumps(retrato(), ensure_ascii=False, indent=1))
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())

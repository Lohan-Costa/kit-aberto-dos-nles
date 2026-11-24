"""Bancada B13_MONTAGENS no Premiere — o relink da cópia (o caminho do De Lá Pra Cá) com MONTAGENS por cima da mídia.

O B11/B12 provaram o fator do conteúdo num clipe solto. Aqui a pergunta é o que o editor monta em volta: escala dentro
do nest e no próprio nest, nest dentro de nest, adjustment layer com Transform, Transform no clipe, Motion completo
(posição, rotação, âncora) e Crop. Os pares são os do B11 (FIT UHD → HD, fator 0,5; DCI_CORTE 4096 → HD cortado, 0,5).

    python -m lab.bancadas.premiere_montagens          (com o Premiere aberto e a ponte no ar)

⛔ A API do 23.2 não cria adjustment layer (nem o DOM nem o QE): a bancada cria um BLACK VIDEO e o vira adjustment
layer no XML (`IsAdjustmentLayer` no MasterClip, `AdjustmentLayer` no VideoClip — como num projeto real, cuja mídia é
um "Black Video" sintético). ⛔ Com Transparent Video + as mesmas marcas o 23.2 diz isAdjustmentLayer() = true e o
efeito NÃO age nas trilhas de baixo (2026-10-09).

Grava em `saida/bancadas/premiere/B13_MONTAGENS/`: o projeto, os quadros e `premiere.json`; a comparação dos quadros
é `python -m lab.bancadas.premiere_montagens comparar` (precisa de numpy e PIL).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time

from . import premiere as p
from . import premiere_relink as r
from ..gerar import RAIZ

CASO = os.path.join(RAIZ, "saida", "base", "B11_RELINK")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B13_MONTAGENS")
PROJETO = os.path.join(TRAB, "B13 MONTAGENS.prproj")
J = p._js
SEG = 4
RENDERIZADOR = "Mercury Playback Engine Software Only"
FIT, CORTE = "B11_FIT_MOV-PRORES.mov", "B11_DCI_CORTE_MOV-PRORES.mov"
FATOR = {FIT: 0.5, CORTE: 0.5}
# raster do convertido e do original (verdade.json do B11), para levar o Crop ao quadro do original
RASTER = {FIT: ((1920, 1080), (3840, 2160)), CORTE: ((1920, 1080), (4096, 2160))}

# plano: (nome, o que tem). A ordem é a da timeline, um a cada SEG segundos.
PLANOS = ["NEST_DENTRO", "NEST_FORA", "NEST_NEST", "AJUSTE", "TRANSFORM_CLIPE", "MOTION", "CROP", "CROP_ESCALA"]


def x(codigo: str, timeout: float = 600):
    r.TRAB = TRAB
    return r.x(codigo, timeout)


_JS = r"""
function _m_por() { var it = _lab_itens(app.project.rootItem), por = {}; for (var i = 0; i < it.length; i++) por[it[i].name] = it[i]; return por; }
function _m_comp(c, mn) { for (var i = 0; i < c.components.numItems; i++) if (c.components[i].matchName == mn) return c.components[i]; return null; }
function _m_prop(k, n) { for (var i = 0; i < k.properties.numItems; i++) if (k.properties[i].displayName == n) return k.properties[i]; return null; }
function _m_set(c, mn, vals) { var k = _m_comp(c, mn); for (var n in vals) _m_prop(k, n).setValue(vals[n], true); }
function _m_limpar(s) { for (var t = 0; t < s.videoTracks.numTracks; t++) while (s.videoTracks[t].clips.numItems) s.videoTracks[t].clips[0].remove(false, false);
  for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false); }
function _m_fx(s, trilha, idx, nome) { app.project.openSequence(s.sequenceID); app.enableQE(); qe.project.init();
  // ⚠️ no QE o getItemAt conta também os VÃOS da trilha (type "Empty"): o idx é o do DOM, só clipes
  var tr = qe.project.getActiveSequence().getVideoTrackAt(trilha), n = -1;
  for (var i = 0; i < tr.numItems; i++) { var it = tr.getItemAt(i); if (it.type == "Empty") continue;
    if (++n == idx) { it.addVideoEffect(qe.project.getVideoEffectByName(nome)); return; } } }
function _m_nest(nome, item) { var s = app.project.createNewSequenceFromClips(nome, [item], app.project.rootItem); s.name = nome; return s; }
"""


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")  # na tela inicial o app.project dá erro
    if os.path.exists(PROJETO):
        os.remove(PROJETO)
    x("app.newProject(%s)" % J(PROJETO))
    # o renderizador é do PROJETO: a 1ª rodada (2026-10-09) foi com a GPU (CUDA, RTX 4050), e o monitor preto que parou o
    # exportFramePNG coincidiu com o travamento da máquina; desde então, CPU ("Software Only")
    x("(function(){ app.enableQE(); qe.project.init(); return qe.project.setRenderer(%s); })()" % J(RENDERIZADOR))
    convs = [os.path.join(CASO, "CONVERTIDOS", n) for n in (FIT, CORTE)]
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J(convs))
    x("(function(){ app.enableQE(); qe.project.init(); return qe.project.newBlackVideo(1920, 1080, 1, 24, 0); })()")
    return x(_JS + r"""(function(){
      var por = _m_por(), fit = por[%(fit)s], corte = por[%(corte)s], aj = por["Black Video"], seg = %(seg)d;
      aj.name = "AJUSTE_LAB";
      fit.setInPoint(0.5, 4); fit.setOutPoint(3.5, 4); corte.setInPoint(0.5, 4); corte.setOutPoint(3.5, 4);
      // os nests (o conteúdo fica com o in/out do clipe: 3 s)
      var nd = _m_nest("NEST_DENTRO", fit); _m_set(nd.videoTracks[0].clips[0], "AE.ADBE Motion", {"Scale": 150, "Position": [0.42, 0.55]});
      var nf = _m_nest("NEST_FORA", fit);
      var nn = _m_nest("NEST_NEST", nd.projectItem); _m_set(nn.videoTracks[0].clips[0], "AE.ADBE Motion", {"Scale": 80});
      var s = app.project.createNewSequenceFromClips("ANTES", [fit], app.project.rootItem); s.name = "ANTES"; _m_limpar(s);
      var v1 = s.videoTracks[0], v2 = s.videoTracks[1];
      var fila = [nd.projectItem, nf.projectItem, nn.projectItem, fit, fit, fit, corte, corte];
      for (var i = 0; i < fila.length; i++) v1.overwriteClip(fila[i], i * seg);
      aj.setInPoint(0, 4); aj.setOutPoint(3, 4); v2.overwriteClip(aj, 3 * seg);
      var c = v1.clips;
      _m_set(c[1], "AE.ADBE Motion", {"Scale": 140, "Rotation": 8});
      _m_set(c[5], "AE.ADBE Motion", {"Scale": 120, "Position": [0.4, 0.6], "Rotation": 15, "Anchor Point": [0.45, 0.45]});
      _m_set(c[7], "AE.ADBE Motion", {"Scale": 130});
      _m_fx(s, 1, 0, "Transform"); _m_fx(s, 0, 4, "Transform"); _m_fx(s, 0, 6, "Crop"); _m_fx(s, 0, 7, "Crop");
      c = s.videoTracks[0].clips;
      _m_set(s.videoTracks[1].clips[0], "AE.ADBE Geometry", {"Uniform Scale": true, "Scale Height": 130, "Rotation": 10});
      _m_set(c[4], "AE.ADBE Geometry", {"Uniform Scale": true, "Scale Height": 130, "Position": [0.45, 0.55], "Rotation": 12});
      _m_set(c[6], "AE.ADBE AECrop", {"Left": 15, "Top": 10, "Right": 5});
      _m_set(c[7], "AE.ADBE AECrop", {"Left": 30});
      var o = []; for (var i = 0; i < c.numItems; i++) o.push(c[i].name + "@" + c[i].start.seconds);
      app.project.save();
      return {planos: o, v2: s.videoTracks[1].clips.numItems}; })()""" % {"fit": J(FIT), "corte": J(CORTE), "seg": SEG})


def virar_ajuste() -> dict:
    """Fecha, marca o Black Video como adjustment layer no XML e reabre."""
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    mc = re.search(r'<MasterClip ObjectUID="([^"]+)"[^>]*>(?:(?!</MasterClip>).)*?<Name>AJUSTE_LAB</Name>', t, re.S)
    bloco_mc = t[mc.start():t.index("</MasterClip>", mc.start())]
    novo_mc = bloco_mc.replace("<Name>AJUSTE_LAB</Name>", "<Name>AJUSTE_LAB</Name>\n\t\t<IsAdjustmentLayer>true</IsAdjustmentLayer>", 1)
    t = t.replace(bloco_mc, novo_mc, 1)
    # os VideoClips cujo Source é a mídia do Transparent Video: o Source de cada um aponta para um VideoMediaSource
    # cujo OriginalDuration/Media é o do AJUSTE_LAB — achar pelo Media do MasterClip
    ids_clip = re.findall(r'<Clip Index="\d+" ObjectRef="(\d+)"/>', bloco_mc)
    fontes = set()
    for cid in ids_clip:
        # ⚠️ o ObjectID NÃO é único entre tipos (um EditTextColumn 51 e um VideoClip 51 no mesmo arquivo): buscar o VideoClip
        b = re.search(r'<VideoClip ObjectID="%s"[^>]*>.*?<Source ObjectRef="(\d+)"/>' % cid, t, re.S)
        if b:
            fontes.add(b.group(1))
    marcados = 0

    def marcar(m):
        nonlocal marcados
        bloco = m.group(0)
        src = re.search(r'<Source ObjectRef="(\d+)"/>', bloco)
        if src and src.group(1) in fontes and "<AdjustmentLayer>" not in bloco:
            marcados += 1
            return bloco.replace("</Clip>\n\t\t</VideoClip>", "</Clip>\n\t\t<AdjustmentLayer>true</AdjustmentLayer>\n\t</VideoClip>") \
                if "</Clip>\n\t\t</VideoClip>" in bloco else re.sub(r"(</Clip>\s*)(</VideoClip>)", r"\1<AdjustmentLayer>true</AdjustmentLayer>\n\t\2", bloco, count=1)
        return bloco
    t = re.sub(r'<VideoClip ObjectID="\d+"[^>]*>.*?</VideoClip>', marcar, t, flags=re.S)
    r._gravar_prproj(PROJETO, t)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return {"fontes": sorted(fontes), "videoclips_marcados": marcados,
            **x(_JS + r"""(function(){ var a = _m_por()["AJUSTE_LAB"]; var s = _lab_seq("ANTES");
              return {isAdjustmentLayer: a.isAdjustmentLayer(), v2: s.videoTracks[1].clips.numItems}; })()""")}


def copia_relinkada(versao: str) -> tuple[str, str]:
    """Como `premiere_relink.copia_relinkada`: cada `Media` de convertido aponta para o original (e o raster dele)."""
    with open(os.path.join(CASO, "verdade.json"), encoding="utf-8") as fh:
        verdade = json.load(fh)
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    for nome in (FIT, CORTE):
        orig = os.path.join(CASO, "ORIGINAIS", nome)
        arq = next(a for a in verdade["arquivos"] if a["arquivo"] == "ORIGINAIS/" + nome)
        ow, oh = arq["video"]["raster"]
        m = next(m for m in re.finditer(r'<Media ObjectUID="[^"]+"[^>]*>.*?</Media>', t, re.S)
                 if f"<Title>{nome}</Title>" in m.group(0))
        b = m.group(0)
        n = b
        for campo in ("FilePath", "ActualMediaFilePath", "RelativePath"):
            n = re.sub(rf"<{campo}>[^<]*</{campo}>", lambda _m, campo=campo: f"<{campo}>{orig}</{campo}>", n)
        n = re.sub(r"\s*<OfflineReason>[^<]*</OfflineReason>", "", n)
        t = t.replace(b, n, 1)
        vs = re.search(r'<VideoStream ObjectRef="(\d+)"/>', n).group(1)
        t = re.sub(r'(<VideoStream ObjectID="%s"[^>]*>.*?<FrameRect>)[^<]*(</FrameRect>)' % vs,
                   lambda mm: mm.group(1) + f"0,0,{ow},{oh}" + mm.group(2), t, count=1, flags=re.S)
    seq = re.search(r'<Sequence ObjectUID="([^"]+)"[^>]*>(?:(?!</Sequence>).)*?<Name>ANTES</Name>', t, re.S).group(1)
    # ⛔ o Premiere 23.2 lembra o CAMINHO do .prproj já importado na sessão: importar de novo o mesmo caminho devolve
    # true e não cria nada (ou substituiu a importação anterior, na 1ª rodada) — 2026-10-09. Os UIDs iguais não
    # atrapalham: com o nome novo a mesma cópia importa. Cada cópia, um nome que nunca se repete.
    alvo = os.path.join(TRAB, f"copia_relinkada_{versao}_{time.strftime('%Y%m%d-%H%M%S')}.prproj")
    r._gravar_prproj(alvo, t)
    return alvo, seq


def importar(versao: str, nome: str) -> dict:
    """Uma importação por versão: o clone() dividiria os nests entre as versões (a correção de uma mexeria na outra).
    ⛔ 23.2 (2026-10-09): o importSequences logo depois de outro (8 s) devolveu true e NÃO criou nada; 2 min depois
    a seguinte importou. E o mesmo caminho importado de novo também não criou nada. Então: um arquivo novo a cada
    tentativa e, se em 20 s nenhuma sequência nova surgir, tentar de novo."""
    antes = x("(function(){ var o = []; for (var i = 0; i < app.project.sequences.numSequences; i++) o.push(app.project.sequences[i].sequenceID); return o; })()")
    tentativas = []
    for tentativa in range(5):
        copia, seq = copia_relinkada(f"{versao}_t{tentativa}")
        t0 = time.time()
        ok = x("app.project.importSequences(%s, [%s])" % (J(copia), J(seq)), timeout=300)
        limite = time.time() + 20
        while time.time() < limite and x("app.project.sequences.numSequences") <= len(antes):
            time.sleep(1.0)
        surgiu = x("app.project.sequences.numSequences") > len(antes)
        tentativas.append({"ok": ok, "surgiu": surgiu, "segundos": round(time.time() - t0, 1)})
        if surgiu:
            break
        time.sleep(10)
    time.sleep(2.0)
    return {"tentativas": tentativas, **x(r"""(function(){
      var antes = %s, novas = [], visto = {}; for (var i = 0; i < antes.length; i++) visto[antes[i]] = 1;
      for (var i = 0; i < app.project.sequences.numSequences; i++) { var q = app.project.sequences[i];
        if (!visto[q.sequenceID]) novas.push(q); }
      var topo = null; for (var i = 0; i < novas.length; i++) if (novas[i].name == "ANTES" || novas[i].projectItem.name == "ANTES") topo = novas[i];
      var o = []; for (var i = 0; i < novas.length; i++) { var q = novas[i];
        if (q === topo) q.projectItem.name = %s; else q.projectItem.name = %s + "__" + q.projectItem.name;
        o.push(q.projectItem.name); }
      return {novas: o}; })()""" % (J(antes), J(nome), J(nome)))}


def corrigir(nome: str, fatores: dict) -> list:
    """Motion Scale × f em todo clipe de mídia relinkada, descendo nos nests DESTA versão (o nest em si não muda:
    ele tem o raster da sequência)."""
    return x(_JS + r"""(function(){
      var F = %s, out = [], feitos = {};
      function seqDoItem(pi) { for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].projectItem.nodeId == pi.nodeId) return app.project.sequences[i]; return null; }
      function passar(s, nivel) {
        for (var t = 0; t < s.videoTracks.numTracks; t++) { var tr = s.videoTracks[t];
          for (var k = 0; k < tr.clips.numItems; k++) { var c = tr.clips[k], pi = c.projectItem; if (!pi) continue;
            if (pi.isSequence()) { var d = seqDoItem(pi); if (d && !feitos[d.sequenceID]) { feitos[d.sequenceID] = 1; passar(d, nivel + 1); } continue; }
            var nm = pi.getMediaPath().split("\\").pop(), f = F[nm]; if (f === undefined) continue;
            var sc = _m_prop(_m_comp(c, "AE.ADBE Motion"), "Scale"); sc.setValue(sc.getValue() * f, true);
            out.push({seq: s.name, nivel: nivel, clipe: nm, scale: sc.getValue()}); } } }
      passar(_lab_seq(%s), 0); return out; })()""" % (J(fatores), J(nome)))


def crop_no_original(nome: str, crop: dict) -> dict:
    """O Crop é percentual do quadro da FONTE: o convertido "crop to fill" perdeu as laterais do original, e 15 % dele
    não é 15 % do original. A parte do original que o convertido mostra: conv / fator, centrada; a margem é o que
    ficou de fora (negativa quando o convertido tem tarja). crop_orig = (crop_conv × visível + margem) / original."""
    (cw, ch), (ow, oh) = RASTER[nome]
    f = FATOR[nome]
    fx, fy = (f, f) if not isinstance(f, (list, tuple)) else f
    vis = {"x": cw / fx, "y": ch / fy}
    tam = {"x": ow, "y": oh}
    out = {}
    for lado, v in crop.items():
        e = "x" if lado in ("Left", "Right") else "y"
        margem = (tam[e] - vis[e]) / 2
        out[lado] = max(0.0, (v / 100 * vis[e] + margem) / tam[e] * 100)
    return out


def corrigir_crop(nome: str) -> list:
    """Remapeia o Crop de todo clipe relinkado (descendo nos nests), pelo `crop_no_original` (calculado aqui em Python
    a partir dos valores lidos)."""
    lidos = x(_JS + r"""(function(){
      var out = [];
      function seqDoItem(pi) { for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].projectItem.nodeId == pi.nodeId) return app.project.sequences[i]; return null; }
      function passar(s) { for (var t = 0; t < s.videoTracks.numTracks; t++) { var tr = s.videoTracks[t];
        for (var k = 0; k < tr.clips.numItems; k++) { var c = tr.clips[k], pi = c.projectItem; if (!pi) continue;
          if (pi.isSequence()) { var d = seqDoItem(pi); if (d) passar(d); continue; }
          var cr = _m_comp(c, "AE.ADBE AECrop"); if (!cr) continue;
          out.push({seq: s.sequenceID, trilha: t, k: k, clipe: pi.getMediaPath().split("\\").pop(),
                    v: {Left: _m_prop(cr, "Left").getValue(), Top: _m_prop(cr, "Top").getValue(),
                        Right: _m_prop(cr, "Right").getValue(), Bottom: _m_prop(cr, "Bottom").getValue()}}); } } }
      passar(_lab_seq(%s)); return out; })()""" % J(nome))
    feitos = []
    for item in lidos:
        if item["clipe"] not in RASTER:
            continue
        novo = crop_no_original(item["clipe"], item["v"])
        x(_JS + r"""(function(){ var s = null; for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].sequenceID == %s) s = app.project.sequences[i];
          _m_set(s.videoTracks[%d].clips[%d], "AE.ADBE AECrop", %s); return true; })()""" % (J(item["seq"]), item["trilha"], item["k"], J(novo)))
        feitos.append({"clipe": item["clipe"], "antes": item["v"], "depois": novo})
    return feitos


def quadros(seq: str, pontos: list) -> list:
    r.TRAB = TRAB
    return r.quadros(seq, pontos)


def comparar() -> dict:
    import numpy as np
    from PIL import Image
    pasta = os.path.join(TRAB, "quadros")
    dados = json.load(open(os.path.join(TRAB, "premiere.json"), encoding="utf-8"))
    out = {}

    def ler(f):
        return np.asarray(Image.open(f).convert("L"), dtype=np.float64)
    for i, plano in enumerate(PLANOS):
        q = dados["pontos"][i]
        a = ler(os.path.join(pasta, f"ANTES_{q}.png"))
        out[plano] = {}
        for v in dados["versoes"]:
            b = ler(os.path.join(pasta, f"{v}_{q}.png"))
            a0, b0 = a - a.mean(), b - b.mean()
            den = float(np.sqrt((a0 * a0).sum() * (b0 * b0).sum()))
            out[plano][v] = round(float((a0 * b0).sum() / den), 4) if den else 0.0
    with open(os.path.join(TRAB, "comparacao.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return out


def main() -> int:
    if sys.argv[1:] == ["comparar"]:
        print(json.dumps(comparar(), ensure_ascii=False, indent=1))
        return 0
    dados = {"premiere": p.executar("app.version"), "plataforma": sys.platform, "renderizador": RENDERIZADOR}
    dados["montar"] = montar()
    dados["ajuste"] = virar_ajuste()
    pontos = [i * SEG * 24 + 36 for i in range(len(PLANOS))]
    dados["pontos"] = pontos
    quadros("ANTES", pontos)
    # uma cópia (e um arquivo) por versão: o clone() dividiria os nests entre as versões
    dados["versoes"] = ["CRU", "CERTO", "CERTO_CROP"]
    dados["importar"] = {v: importar(v, v) for v in dados["versoes"]}
    dados["corrigir"] = {"CERTO": corrigir("CERTO", FATOR), "CERTO_CROP": corrigir("CERTO_CROP", FATOR)}
    dados["corrigir_crop"] = corrigir_crop("CERTO_CROP")
    for v in dados["versoes"]:
        quadros(v, pontos)
    x("app.project.save()")
    with open(os.path.join(TRAB, "premiere.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps(dados, ensure_ascii=False, indent=1)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

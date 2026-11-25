"""Bancada B11_RELINK no Premiere — relink do convertido para o original NUMA CÓPIA (o caminho do De Lá Pra Cá).

Medido primeiro com material real (PRODUCAO_B, 2026-10-09, banco `premiere-cep/api-extendscript.md`): copiar o
.prproj trocando os `Media` dos convertidos pelos originais e `importSequences` dá a sequência nova nos originais; a
escala se corrige pela API. Aqui a pergunta é QUAL fator: a regra das larguras (PRODUCAO-G) ou o fator do conteúdo
(`verdade.json` → `convertidos[].fator_relink`), em todo raster, tarja, recorte, stretch, vertical e PAR.

    python -m lab.bancadas.premiere_relink           (com o Premiere aberto e a ponte no ar)

Grava em `saida/bancadas/premiere/B11_RELINK/`: o projeto, os quadros (`quadros/<seq>_<quadro>.png`) e
`premiere.json`. A comparação dos quadros é do lado do app (precisa de numpy): ver `resultados/B11_RELINK/`.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import struct
import sys
import time
import zlib

from . import premiere as p
from ..gerar import RAIZ

NOME_CASO = "B11_RELINK"
CASO = os.path.join(RAIZ, "saida", "base", NOME_CASO)
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", NOME_CASO)


def usar_caso(nome: str) -> None:
    """A mesma bancada para o B11 e o B12 (python -m lab.bancadas.premiere_relink B12_RELINK_MAIS)."""
    global NOME_CASO, CASO, TRAB
    NOME_CASO = nome
    CASO = os.path.join(RAIZ, "saida", "base", nome)
    TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", nome)
J = p._js
SEG = 4                                            # um plano a cada 4 s; 3 s de cada convertido


def x(codigo: str, timeout: float = 600):
    """Pela ponte; no Windows sob o VIGIA (diálogo desconhecido = foto + DialogoAberto, nunca clique)."""
    def chamada():
        return p.executar(p._LIB + "\n" + codigo, timeout=timeout)
    if os.name != "nt":
        return chamada()
    from . import vigia_windows
    return vigia_windows.vigiar(chamada, os.path.join(TRAB, "dialogos"))


def _gravar_prproj(caminho: str, xml: str) -> None:
    """O cabeçalho que o Premiere escreve (FLG=0, sem FNAME) — banco prproj/relink-e-geometria §0."""
    dados = xml.encode("utf-8")
    co = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
    corpo = co.compress(dados) + co.flush()
    with open(caminho, "wb") as f:
        f.write(b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x13" + corpo
                + struct.pack("<II", zlib.crc32(dados) & 0xFFFFFFFF, len(dados) & 0xFFFFFFFF))


def montar(verdade: dict) -> dict:
    projeto = os.path.join(TRAB, "B11 RELINK.prproj")
    os.makedirs(TRAB, exist_ok=True)
    # ⛔ FECHAR SEM SALVAR antes de apagar: apagar o .prproj ABERTO e chamar o newProject abriu o modal "Project
    # Modified … Do you wish…" (o Premiere quis salvar o velho por cima) e travou a ponte (23.2 Windows, 2026-10-09)
    x("(function(){ if (app.project && app.project.path) app.project.closeDocument(0, 0); return true; })()")
    if os.path.exists(projeto):
        os.remove(projeto)
    convs = [os.path.join(CASO, c["arquivo"].replace("/", os.sep)) for c in verdade["convertidos"]]
    x("app.newProject(%s)" % J(projeto))
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J(convs))
    nomes = [os.path.basename(c) for c in convs]
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), por = {}, nomes = %s;
      for (var i = 0; i < it.length; i++) por[it[i].name] = it[i];
      var s = app.project.createNewSequenceFromClips("ANTES", [por[nomes[0]]], app.project.rootItem); s.name = "ANTES";
      var v = s.videoTracks[0];
      while (v.clips.numItems) v.clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      for (var i = 0; i < nomes.length; i++) { var c = por[nomes[i]]; c.setInPoint(0.5, 4); c.setOutPoint(3.5, 4); v.overwriteClip(c, i * %d); }
      var st = s.getSettings(), o = []; for (var i = 0; i < v.clips.numItems; i++) o.push(v.clips[i].name + "@" + v.clips[i].start.seconds);
      app.project.save();
      return {w: st.videoFrameWidth, h: st.videoFrameHeight, planos: o}; })()""" % (J(nomes), SEG))


def copia_relinkada(verdade: dict) -> tuple[str, str]:
    """O .prproj salvo com cada `Media` de convertido apontando para o original (e o raster do original)."""
    origem = os.path.join(TRAB, "B11 RELINK.prproj")
    t = gzip.open(origem, "rb").read().decode("utf-8")
    for c in verdade["convertidos"]:
        nome = os.path.basename(c["arquivo"])
        orig = os.path.join(CASO, c["derivado_de"].replace("/", os.sep))
        arq = next(a for a in verdade["arquivos"] if a["arquivo"] == c["derivado_de"])
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
    t = re.sub(r'(<Sequence ObjectUID="[^"]+"[^>]*>.*?<Name>)ANTES(</Name>)', lambda mm: mm.group(1) + "ONLINE" + mm.group(2),
               t, count=1, flags=re.S)
    seq = re.search(r'<Sequence ObjectUID="([^"]+)"', t).group(1)
    alvo = os.path.join(TRAB, "copia_relinkada.prproj")
    _gravar_prproj(alvo, t)
    return alvo, seq


def importar_e_versoes(copia: str, seq: str) -> dict:
    t = time.time()
    ok = x("app.project.importSequences(%s, [%s])" % (J(copia), J(seq)), timeout=300)
    return {"importSequences": ok, "segundos": round(time.time() - t, 1), **x(r"""(function(){
      var s = _lab_seq("ONLINE"); var out = {}; var nomes = ["CRU", "LARGURAS", "CERTO", "CERTO_TEMPO"];
      // ⚠️ o item da bin veio com o nome antigo ("ANTES": a cópia renomeou só a Sequence) e o clone() usa o
      // nome do ITEM ("ANTES Copy"): renomear o item primeiro (renomeia a sequência junto)
      s.projectItem.name = "ONLINE";
      var antes = {}; for (var i = 0; i < app.project.sequences.numSequences; i++) antes[app.project.sequences[i].sequenceID] = 1;
      for (var i = 0; i < nomes.length; i++) { s.clone(); }
      var k = 0; for (var i = 0; i < app.project.sequences.numSequences; i++) { var q = app.project.sequences[i];
        if (!antes[q.sequenceID] && k < nomes.length) { q.projectItem.name = nomes[k++]; } }
      var v = s.videoTracks[0], o = []; for (var i = 0; i < v.clips.numItems; i++) o.push(v.clips[i].projectItem.getMediaPath());
      return {arquivos_online: o, renomeadas: k}; })()""")}


def corrigir(seq: str, fatores: dict) -> list:
    """`fatores` = {nome do arquivo ORIGINAL: f | [fx, fy]}. Uniforme: Scale × f (keyframes inclusive). [fx, fy]:
    desliga Uniform Scale, Scale (altura) × fy e Scale Width × fx."""
    return x(r"""(function(){
      var s = _lab_seq(%s), v = s.videoTracks[0], F = %s, out = [];
      function mot(c) { for (var i = 0; i < c.components.numItems; i++) if (c.components[i].matchName == "AE.ADBE Motion") return c.components[i]; return null; }
      function prop(m, n) { for (var i = 0; i < m.properties.numItems; i++) if (m.properties[i].displayName == n) return m.properties[i]; return null; }
      function vezes(pr, f) { if (pr.isTimeVarying()) { var ks = pr.getKeys(); for (var i = 0; i < ks.length; i++) pr.setValueAtKey(ks[i], pr.getValueAtKey(ks[i]) * f, true); }
        else pr.setValue(pr.getValue() * f, true); }
      for (var k = 0; k < v.clips.numItems; k++) { var c = v.clips[k], nome = c.projectItem.getMediaPath().split("\\").pop(), f = F[nome], m = mot(c);
        if (f === undefined) { out.push({nome: nome, f: null}); continue; }
        if (f instanceof Array) { prop(m, "Uniform Scale").setValue(false, true); var sw = prop(m, "Scale Width");
          var base = prop(m, "Scale").getValue(); sw.setValue(base * f[0], true); prop(m, "Scale").setValue(base * f[1], true); }
        else vezes(prop(m, "Scale"), f);
        out.push({nome: nome, scale: prop(m, "Scale").getValue(), largura: prop(m, "Scale Width").getValue(), uniforme: prop(m, "Uniform Scale").getValue()}); }
      return out; })()""" % (J(seq), J(fatores)))


def deslizar(seq: str, segundos: dict) -> list:
    """`segundos` = {nome do arquivo ORIGINAL: s}: entrada e saída andam juntas (slip) — o convertido era um TRECHO
    do original (o "offline recortado" do RELINKER). A posição na timeline não muda (medido 23.2: in depois out)."""
    return x(r"""(function(){
      var s = _lab_seq(%s), v = s.videoTracks[0], D = %s, out = [];
      for (var k = 0; k < v.clips.numItems; k++) { var c = v.clips[k], nome = c.projectItem.getMediaPath().split("\\").pop(), d = D[nome];
        if (!d) continue;
        var ti = new Time(); ti.seconds = c.inPoint.seconds + d; c.inPoint = ti;
        var to = new Time(); to.seconds = c.outPoint.seconds + d; c.outPoint = to;
        out.push({nome: nome, s: d, entrada: c.inPoint.seconds, inicio: c.start.seconds}); }
      return out; })()""" % (J(seq), J(segundos)))


def quadros(seq: str, pontos: list) -> list:
    pasta = os.path.join(TRAB, "quadros")
    os.makedirs(pasta, exist_ok=True)
    r = x(r"""(function(){
      var s = _lab_seq(%s); app.project.openSequence(s.sequenceID); app.enableQE(); qe.project.init();
      var q = qe.project.getActiveSequence(), tb = Number(s.timebase), out = [], pts = %s;
      for (var i = 0; i < pts.length; i++) { s.setPlayerPosition(String(pts[i] * tb));
        q.exportFramePNG(q.CTI.timecode, %s + "\\" + %s + "_" + pts[i]); out.push(q.CTI.timecode); }
      return out; })()""" % (J(seq), J(pontos), J(pasta), J(seq)), timeout=900)
    # ⛔ o exportFramePNG do 23.2 devolve false e grava DEPOIS (banco, 2026-10-09): esperar os arquivos
    faltam = [os.path.join(pasta, f"{seq}_{q}.png") for q in pontos]
    limite = time.time() + 120
    while time.time() < limite and not all(os.path.exists(f) and os.path.getsize(f) > 0 for f in faltam):
        time.sleep(0.5)
    time.sleep(1.0)
    return r


def main() -> int:
    if len(sys.argv) > 1:
        usar_caso(sys.argv[1])
    with open(os.path.join(CASO, "verdade.json"), encoding="utf-8") as fh:
        verdade = json.load(fh)
    dados = {"premiere": p.executar("app.version"), "plataforma": sys.platform}
    dados["montar"] = montar(verdade)
    pontos = [i * SEG * 24 + 36 for i in range(len(verdade["convertidos"]))]     # 1,5 s dentro de cada plano
    dados["pontos"] = pontos
    quadros("ANTES", pontos)
    copia, seq = copia_relinkada(verdade)
    dados["importar"] = importar_e_versoes(copia, seq)
    larg, certo = {}, {}
    for c in verdade["convertidos"]:
        nome = os.path.basename(c["derivado_de"])
        larg[nome] = c["regra_das_larguras"]
        certo[nome] = c["fator_relink"]
    dados["corrigir"] = {"LARGURAS": corrigir("LARGURAS", larg), "CERTO": corrigir("CERTO", certo),
                         "CERTO_TEMPO": corrigir("CERTO_TEMPO", certo)}
    from fractions import Fraction
    from .. import tc as _tc
    desl = {}
    for c in verdade["convertidos"]:
        if c.get("deslocamento_quadros"):
            arq = next(a for a in verdade["arquivos"] if a["arquivo"] == c["derivado_de"])
            desl[os.path.basename(c["derivado_de"])] = float(Fraction(c["deslocamento_quadros"]) / _tc.taxa(arq["fps"]))
    dados["deslizar"] = deslizar("CERTO_TEMPO", desl) if desl else []
    for s in ("CRU", "LARGURAS", "CERTO", "CERTO_TEMPO"):
        quadros(s, pontos)
    x("app.project.save()")
    with open(os.path.join(TRAB, "premiere.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps(dados, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

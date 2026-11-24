"""B24_COR_MC no PREMIERE — o Color Correction do Media Composer na Lumetri, EDITÁVEL, medido na MESMA carta (decisão do
autor, 2026-11-20: controles editáveis com LUT de reserva).

Pela PONTE LIVRE do laboratório (`premiere.py`, Premiere aberto): projeto novo, a carta em N cópias de 12 quadros, uma
Lumetri em cada uma (menos a 1ª, o neutro); a Saturation pela API (`setValue`); a CURVA RGB (ParameterID 39, o blob de
4 × 520 bytes — banco `prproj` e `conformar/motor/prproj/leitura.py::_curvas_rgb`) pelo `.prproj`, com o projeto
fechado; reabre, exporta ProRes 422 (`exportAsMediaDirect`) e mede com o medidor do MC.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import re
import struct
import time

from . import premiere as p

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARTA = os.path.join(RAIZ, "saida", "base", "B24_COR_MC", "B24_CARTA_COR.mov")
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "premiere_cor_mc")
QUADROS, MEIO = 12, 6
FPS = 24000 / 1001


def _js(v) -> str:
    return json.dumps(v)


def montar(nome: str, sats: list[float | None]) -> dict:
    """Projeto `nome`.prproj com a sequência COR: `len(sats)` cópias; `None` = sem Lumetri; número = Lumetri com essa
    Saturation (100 = neutra). Salva."""
    os.makedirs(TRABALHO, exist_ok=True)
    proj = os.path.join(TRABALHO, nome + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    js = """(function(){
      var proj = %s, carta = %s, sats = %s, Q = %d, fps = %r;
      if (!app.newProject(proj)) return "newProject falhou";
      app.project.importFiles([carta], true, app.project.rootItem, false);
      var it = null;
      for (var i = 0; i < app.project.rootItem.children.numItems; i++) {
        var c = app.project.rootItem.children[i]; if (c.name.indexOf("B24_CARTA_COR") == 0) it = c; }
      if (!it) return "sem a carta";
      var seq = app.project.createNewSequenceFromClips("COR", [it], app.project.rootItem);
      var v1 = seq.videoTracks[0];
      while (v1.clips.numItems) v1.clips[0].remove(false, false);
      var TQ = 10594584000;                                  // ticks por quadro a 23,976
      var tin = new Time(); tin.ticks = "0"; var tout = new Time(); tout.ticks = String(Q * TQ);
      it.setInPoint(tin, 4); it.setOutPoint(tout, 4);
      for (var k = 0; k < sats.length; k++) { var tk = new Time(); tk.ticks = String(k * Q * TQ); v1.overwriteClip(it, tk); }
      app.enableQE();
      var qs = qe.project.getActiveSequence(), qv = qs.getVideoTrackAt(0);
      var ef = qe.project.getVideoEffectByName("Lumetri Color");
      var out = [], clipes = [];
      for (var i = 0; i < qv.numItems; i++) if (qv.getItemAt(i).type == "Clip") clipes.push(qv.getItemAt(i));
      out.push("qe " + clipes.length + "/" + qv.numItems);
      for (var k = 0; k < sats.length; k++) {
        if (sats[k] === null) continue;
        clipes[k].addVideoEffect(ef);
      }
      for (var k = 0; k < sats.length; k++) {
        if (sats[k] === null) continue;
        var ti = v1.clips[k], comp = null;
        for (var j = 0; j < ti.components.numItems; j++) if (ti.components[j].matchName == "AE.ADBE Lumetri") comp = ti.components[j];
        if (!comp) { out.push("sem lumetri " + k); continue; }
        for (var j = 0; j < comp.properties.numItems; j++) {
          if (comp.properties[j].displayName == "Saturation") { comp.properties[j].setValue(sats[k], true); out.push([k, comp.properties[j].getValue()]); break; }
        }
      }
      app.project.save();
      var ini = []; for (var k = 0; k < v1.clips.numItems; k++) ini.push(v1.clips[k].start.ticks + "/" + v1.clips[k].end.ticks);
      return {clipes: v1.clips.numItems, sat: out, ini: ini};
    })()""" % (_js(proj), _js(CARTA), _js(sats), QUADROS, FPS)
    r = p.executar(js)
    return {"projeto": proj, "resposta": r}


def fechar_projeto() -> None:
    p.executar("app.project.closeDocument(0, 0)")


def abrir_projeto(proj: str) -> None:
    p.executar("app.openDocument(%s, true, true, true, true)" % _js(proj))
    for _ in range(40):      # projeto grande demora: a exportação logo depois achou ZERO sequências (2026-11-20)
        time.sleep(1.5)
        if p.executar("app.project ? app.project.sequences.numSequences : 0"):
            return
    raise TimeoutError("o projeto não abriu: " + proj)


def exportar(proj: str, ano: str = "2026") -> str:
    alvo = proj.replace(".prproj", ".mov")
    if os.path.exists(alvo):
        os.remove(alvo)
    preset = p.preset_prores(ano)
    js = """(function(){ var s = null;
      for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name == "COR") s = app.project.sequences[i];
      app.project.openSequence(s.sequenceID);
      return s.exportAsMediaDirect(%s, %s, 0); })()""" % (_js(alvo), _js(preset))
    p.executar(js, timeout=600)
    return alvo


def medir(arquivo: str, n: int) -> list[dict]:
    from ..cor_b24_medir import medir as _medir
    return [_medir(arquivo, k * QUADROS + MEIO) for k in range(n)]


# ── a curva no .prproj ────────────────────────────────────────────────────────────────────────────────────────────────
def _bloco(pontos, tipo: int = 0) -> bytes:
    """Um bloco de 520 bytes da curva da Lumetri: `u32 tipo, u32 n` + 32 pares (x, y) em double (0–1)."""
    b = struct.pack("<II", tipo, len(pontos)) + b"".join(struct.pack("<dd", x, y) for x, y in pontos)
    return b + b"\0" * (520 - len(b))


def ler_xml(proj: str) -> str:
    with open(proj, "rb") as f:
        d = f.read()
    return (gzip.decompress(d) if d[:2] == b"\x1f\x8b" else d).decode("utf-8")


def gravar_xml(proj: str, xml: str) -> None:
    with open(proj, "wb") as f:
        f.write(gzip.compress(xml.encode("utf-8")))


def _obj(xml: str, oid: str) -> re.Match | None:
    return re.search(r'<(\w+) ObjectID="%s"[^>]*>.*?</\1>' % oid, xml, re.S)


def _hash(n: int) -> str:
    h = os.urandom(12) + struct.pack(">I", n + 12)
    x = h.hex()
    return f"{x[:8]}-{x[8:12]}-{x[12:16]}-{x[16:20]}-{x[20:]}"


def lumetri_por_clipe(xml: str) -> list[str | None]:
    """O ObjectID da Lumetri de cada clipe da V1, na ordem do tempo (None = sem Lumetri)."""
    itens = []
    for m in re.finditer(r'<VideoClipTrackItem ObjectID="\d+"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S):
        ini = re.search(r"<Start>(-?\d+)</Start>", m.group(1))
        comps = re.search(r'<Components ObjectRef="(\d+)"/>', m.group(1))
        lum = None
        cadeia = _obj(xml, comps.group(1)) if comps else None
        for ref in re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', cadeia.group(0) if cadeia else ""):
            c = _obj(xml, ref)
            if c and "<MatchName>AE.ADBE Lumetri</MatchName>" in c.group(0):
                lum = ref
        itens.append((int(ini.group(1)) if ini else 0, lum))
    return [lum for _, lum in sorted(itens)]


def curvas_no_projeto(proj: str, curvas: dict[int, list], blocos: tuple[int, ...] = (0,)) -> dict:
    """`curvas` = {k (o k-ésimo clipe da V1): pontos da curva MESTRA (0–1)}: troca o bloco 0 do param 39 da Lumetri do
    clipe (os blocos R/G/B ficam), com um BinaryHash novo (12 bytes + u32 BE tamanho + 12 — banco)."""
    xml = ler_xml(proj)
    # desfaz a DEDUPLICAÇÃO (banco `prproj/estruturas.md` §BinaryHash): o elemento vazio aponta o conteúdo de outro com o
    # mesmo hash — trocar aquele deixaria este órfão. Cada um passa a levar o seu (o Premiere lê as duas formas).
    conteudo = dict(re.findall(r'BinaryHash="([^"]+)">([^<]+)<', xml))
    xml = re.sub(r'<(\w+) Encoding="base64" BinaryHash="([^"]+)"/>',
                 lambda m: '<%s Encoding="base64" BinaryHash="%s">%s</%s>' % (m.group(1), m.group(2), conteudo[m.group(2)], m.group(1))
                 if m.group(2) in conteudo else m.group(0), xml)
    lum = lumetri_por_clipe(xml)
    feito = {}
    for k, pts in curvas.items():
        c = _obj(xml, lum[k])
        for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', c.group(0)):
            m = _obj(xml, ref)
            if not m or "<ParameterID>39</ParameterID>" not in m.group(0):
                continue
            v = re.search(r'<StartKeyframeValue Encoding="base64" BinaryHash="([^"]+)"(?:/>|>([^<]*)</StartKeyframeValue>)', m.group(0))
            atual = v.group(2)
            if not atual:      # deduplicado: o conteúdo mora no elemento de mesmo hash
                d = re.search(r'BinaryHash="%s">([^<]+)<' % re.escape(v.group(1)), xml)
                atual = d.group(1)
            velho = base64.b64decode(atual.strip())
            blob = bytearray(velho)
            for bl in blocos:     # 0 = a mestra (PRESERVA O MATIZ — medido), 1/2/3 = R/G/B (independentes)
                blob[bl * 520:(bl + 1) * 520] = _bloco(pts, struct.unpack("<I", velho[bl * 520:bl * 520 + 4])[0])
            blob = bytes(blob)
            novo = '<StartKeyframeValue Encoding="base64" BinaryHash="%s">%s</StartKeyframeValue>' % (
                _hash(len(blob)), base64.b64encode(blob).decode())
            corpo = m.group(0)[:v.start()] + novo + m.group(0)[v.end():]
            xml = xml[:m.start()] + corpo + xml[m.end():]
            feito[k] = ref
    gravar_xml(proj, xml)
    return feito


def montar_efeitos(nome: str, specs: list[list]) -> dict:
    """Como `montar`, mas cada clipe recebe uma lista de efeitos `[nome do efeito QE, {displayName: valor}]`, na ordem
    (o 1º aplicado primeiro). `[]` = sem efeito. Devolve os parâmetros lidos de volta."""
    os.makedirs(TRABALHO, exist_ok=True)
    proj = os.path.join(TRABALHO, nome + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    js = """(function(){
      var proj = %s, carta = %s, specs = %s, Q = %d;
      if (!app.newProject(proj)) return "newProject falhou";
      app.project.importFiles([carta], true, app.project.rootItem, false);
      var it = null;
      for (var i = 0; i < app.project.rootItem.children.numItems; i++) {
        var c = app.project.rootItem.children[i]; if (c.name.indexOf("B24_CARTA_COR") == 0) it = c; }
      var seq = app.project.createNewSequenceFromClips("COR", [it], app.project.rootItem);
      var v1 = seq.videoTracks[0];
      while (v1.clips.numItems) v1.clips[0].remove(false, false);
      var TQ = 10594584000;
      var tin = new Time(); tin.ticks = "0"; var tout = new Time(); tout.ticks = String(Q * TQ);
      it.setInPoint(tin, 4); it.setOutPoint(tout, 4);
      for (var k = 0; k < specs.length; k++) { var tk = new Time(); tk.ticks = String(k * Q * TQ); v1.overwriteClip(it, tk); }
      app.enableQE();
      var qv = qe.project.getActiveSequence().getVideoTrackAt(0), clipes = [];
      for (var i = 0; i < qv.numItems; i++) if (qv.getItemAt(i).type == "Clip") clipes.push(qv.getItemAt(i));
      for (var k = 0; k < specs.length; k++)
        for (var e = 0; e < specs[k].length; e++) clipes[k].addVideoEffect(qe.project.getVideoEffectByName(specs[k][e][0]));
      var out = [];
      for (var k = 0; k < specs.length; k++) {
        var ti = v1.clips[k], lidos = [];
        for (var e = 0; e < specs[k].length; e++) {
          var comp = null, vals = specs[k][e][1], nomes = [], feitos = {};
          for (var j = 0; j < ti.components.numItems; j++) if (ti.components[j].displayName == specs[k][e][0]) comp = ti.components[j];
          if (!comp) { lidos.push(["sem " + specs[k][e][0]]); continue; }
          for (var j = 0; j < comp.properties.numItems; j++) {
            var pr = comp.properties[j], dn = pr.displayName; nomes.push(dn);
            if (vals.hasOwnProperty(dn) && !feitos[dn]) { feitos[dn] = 1; pr.setValue(vals[dn], true); lidos.push([comp.displayName, dn, pr.getValue()]); }
          }
          
        }
        out.push(lidos);
      }
      app.project.save();
      return out;
    })()""" % (_js(proj), _js(CARTA), _js(specs), QUADROS)
    return {"projeto": proj, "resposta": p.executar(js)}


# ── a curva do MC na curva RGB mestra da Lumetri ──────────────────────────────────────────────────────────────────────
def _alvo_lumetri(pontos):
    """A curva do MC no eixo da Lumetri: u = (código − 16)/219 (MEDIDO, 26.5.2, 0,07–0,12 código), G(u) no mesmo eixo."""
    import numpy as np
    from ..cor_curva import catmull, linear
    P = sorted((float(x), float(y)) for x, y in pontos)
    f = catmull(P) if len(P) > 2 else linear(P)
    return lambda u: (255 * f(np.clip((16 + 219 * np.asarray(u, float)) / 255, 0, 1)) - 16) / 219


def curva_lumetri_do_mc(pontos, maximo: int = 32, tolerancia: float = 0.25) -> tuple[list[tuple[float, float]], float]:
    """A Lumetri interpola por SPLINE NATURAL (plana fora das pontas) — não reproduz a Catmull-Rom do MC com os mesmos
    pontos. Pontos em u: os nós do MC que caem em [0, 1] + as pontas, e mais pontos onde o erro é maior, até o erro
    (em códigos de 8 bits, no papel) ficar abaixo da `tolerancia` ou chegar a `maximo` (o blob guarda 32).
    Devolve (pontos, erro máximo no papel)."""
    import numpy as np
    from ..cor_curva import natural
    G = _alvo_lumetri(pontos)
    u = np.linspace(0, 1, 2001)
    alvo = G(u)
    xs = sorted({0.0, 1.0} | {round((255 * x - 16) / 219, 6) for x, _ in pontos if 0 < (255 * x - 16) / 219 < 1})
    while True:
        P = [(x, float(G(x))) for x in xs]
        f = natural(P) if len(P) > 2 else (lambda t, P=P: np.interp(t, [p[0] for p in P], [p[1] for p in P]))
        erro = np.abs(f(u) - alvo) * 219
        if erro.max() <= tolerancia or len(xs) >= maximo:
            return P, float(erro.max())
        novo = float(u[int(erro.argmax())])
        if any(abs(novo - x) < 1e-4 for x in xs):
            return P, float(erro.max())
        xs = sorted(xs + [novo])

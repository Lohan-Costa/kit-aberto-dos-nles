"""O INPUT SIZING do Resolve no Premiere: um efeito TRANSFORM separado (decisão do autor, 2026-11-21 — não competir com o
Motion), conferido pela imagem contra o still do Resolve do mesmo controle.

A tradução (banco `drt-drp/estruturas.md` §"O SIZING da página Color"; fonte e timeline 1920×1080):
- Pan p (px, + = direita) → Position x = (960 + p) / 1920 (a ponte usa a posição NORMALIZADA);
- Tilt t (px, + = CIMA) → Position y = (540 − t) / 1080;
- Zoom z → Scale z·100; Width/Height → Scale Width/Height (Uniform Scale desligado);
- Rotate r (graus, + = horário) → Rotation r (+ = horário no Premiere);
- Flip H/V → os efeitos Horizontal/Vertical Flip (o Transform não espelha).
Pitch/Yaw (perspectiva) ficam de fora nesta rodada.

    python -m lab.bancadas.premiere_sizing rodar [2027]
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys

import numpy as np

from . import premiere as p
from . import premiere_cor_mc as pc

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARTA = os.path.join(RAIZ, "saida", "base", "B24_COR_MC", "B24_CARTA_COR.mov")
STILLS_RESOLVE = os.path.join(RAIZ, "saida", "bancadas", "resolve_sizing")
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "premiere_sizing")
QUADROS, MEIO = 12, 6
W, H = 1920, 1080


def traduzir(sizing: dict) -> list:
    """O Input Sizing do Resolve (valores da UI) → a lista de efeitos do Premiere [[nome QE, {displayName: valor}]]."""
    efeitos = []
    t = {}
    pan, tilt = sizing.get("pan", 0.0), sizing.get("tilt", 0.0)
    if pan or tilt:
        t["Position"] = [(W / 2 + pan) / W, (H / 2 - tilt) / H]
    w, h, z = sizing.get("width", 1.0), sizing.get("height", 1.0), sizing.get("zoom", 1.0)
    if (w, h) != (1.0, 1.0):
        t["Uniform Scale"] = False
        t["Scale Height"] = 100 * z * h
        t["Scale Width"] = 100 * z * w
    elif z != 1.0:
        t["Uniform Scale"] = True
        t["Scale Height"] = 100 * z
    if sizing.get("rotate"):
        t["Rotation"] = sizing["rotate"]
    if t:
        efeitos.append(["Transform", t])
    if sizing.get("flip_h"):
        efeitos.append(["Horizontal Flip", {}])
    if sizing.get("flip_v"):
        efeitos.append(["Vertical Flip", {}])
    return efeitos


CASOS = [("01_neutro", {}), ("02_pan100", {"pan": 100}), ("03_tilt100", {"tilt": 100}), ("04_zoom1.5", {"zoom": 1.5}),
         ("05_rot10", {"rotate": 10}), ("06_width1.5", {"width": 1.5}), ("07_height1.5", {"height": 1.5}),
         ("10_flipH", {"flip_h": True}), ("11_flipV", {"flip_v": True})]


def montar(nome: str, specs: list[list]) -> dict:
    os.makedirs(TRABALHO, exist_ok=True)
    proj = os.path.join(TRABALHO, nome + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    js = """(function(){
      var proj = %s, carta = %s, specs = %s, Q = %d;
      try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {}
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
          var comp = null, vals = specs[k][e][1];
          for (var j = ti.components.numItems - 1; j >= 0; j--) if (ti.components[j].displayName == specs[k][e][0]) { comp = ti.components[j]; break; }
          if (!comp) { lidos.push("sem " + specs[k][e][0]); continue; }
          var ordem = ["Uniform Scale", "Scale Height", "Scale Width", "Position", "Rotation"];
          for (var o = 0; o < ordem.length; o++) {
            if (!vals.hasOwnProperty(ordem[o])) continue;
            for (var jj = 0; jj < comp.properties.numItems; jj++) {
              var pr = comp.properties[jj];
              if (pr.displayName == ordem[o]) { pr.setValue(vals[ordem[o]], true); lidos.push([ordem[o], pr.getValue()]); break; }
            }
          }
          lidos.push(comp.matchName);
        }
        out.push(lidos);
      }
      app.project.save();
      return {clipes: v1.clips.numItems, lidos: out, versao: app.version};
    })()""" % (pc._js(proj), pc._js(CARTA), pc._js(specs), QUADROS)
    r = p.executar(js)
    print("montar:", json.dumps(r, ensure_ascii=False)[:1500], flush=True)
    return {"projeto": proj, "resposta": r}


def quadro(arquivo: str, n: int) -> np.ndarray:
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32) / 255


def ler_png(caminho: str) -> np.ndarray:
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32) / 255


def comparar(a: np.ndarray, b: np.ndarray) -> dict:
    """Alinha `b` (Premiere) em `a` (Resolve) por ECC (homografia, partindo da identidade): se a tradução está certa,
    a homografia é a identidade. Devolve o desvio do centro e de um ponto a 500 px, e a escala/giro residuais."""
    import cv2
    w = np.eye(3, dtype=np.float32)
    try:
        s = 0.25
        a2, b2 = cv2.resize(a, None, fx=s, fy=s), cv2.resize(b, None, fx=s, fy=s)
        _, w = cv2.findTransformECC(a2, b2, w, cv2.MOTION_HOMOGRAPHY, (3, 200, 1e-6), None, 5)
        w[0:2, 2] /= s
        w[2, 0:2] *= s
        cc, w = cv2.findTransformECC(a, b, w, cv2.MOTION_HOMOGRAPHY, (3, 200, 1e-7), None, 5)
    except cv2.error as e:  # noqa: F841
        return {"falhou": True}
    hm = w / w[2, 2]

    def pt(x, y):
        v = hm @ np.array([x, y, 1.0])
        return v[:2] / v[2]
    c, e = pt(960, 540), pt(1460, 540)
    return {"cc": round(float(cc), 4), "centro_dx": round(float(c[0] - 960), 2), "centro_dy": round(float(c[1] - 540), 2),
            "escala": round(float(np.linalg.norm(e - c) / 500), 4),
            "giro": round(math.degrees(math.atan2(e[1] - c[1], e[0] - c[0])), 3),
            "canto_px": round(float(max(np.linalg.norm(pt(x, y) - np.array([x, y])) for x, y in
                                        ((0, 0), (1919, 0), (0, 1079), (1919, 1079)))), 2)}


K4 = os.path.join(RAIZ, "saida", "bancadas", "resolve_felipe_ret", "teste_troca", "TRECHO", "A003_C023_09060T_001.mov")
# (nome, fonte, escala do Motion = o "Scale to Fit" do Resolve, Input Sizing)
MONTAR_JS = """(function(){
      var proj = %s, specs = %s, Q = %d, TQ = 10594584000;
      try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {}
      if (!app.newProject(proj)) return "newProject falhou";
      var fontes = [];
      for (var k = 0; k < specs.length; k++) { var ja = false; for (var q = 0; q < fontes.length; q++) if (fontes[q] == specs[k][0]) ja = true; if (!ja) fontes.push(specs[k][0]); }
      app.project.importFiles(fontes, true, app.project.rootItem, false);
      function item(f) { var b = f.split("/").pop().split(".")[0];
        for (var i = 0; i < app.project.rootItem.children.numItems; i++) { var c = app.project.rootItem.children[i];
          if (c.name.indexOf(b) == 0 && c.type == 1) return c; } return null; }
      var carta = item(%s);
      var seq = app.project.createNewSequenceFromClips("COR", [carta], app.project.rootItem);
      var v1 = seq.videoTracks[0];
      while (v1.clips.numItems) v1.clips[0].remove(false, false);
      for (var k = 0; k < specs.length; k++) {
        var it = item(specs[k][0]);
        var tin = new Time(); tin.ticks = "0"; var tout = new Time(); tout.ticks = String(Q * TQ);
        it.setInPoint(tin, 4); it.setOutPoint(tout, 4);
        var tk = new Time(); tk.ticks = String(k * Q * TQ); v1.overwriteClip(it, tk); }
      app.enableQE();
      var qv = qe.project.getActiveSequence().getVideoTrackAt(0), clipes = [];
      for (var i = 0; i < qv.numItems; i++) if (qv.getItemAt(i).type == "Clip") clipes.push(qv.getItemAt(i));
      for (var k = 0; k < specs.length; k++)
        for (var e = 0; e < specs[k][2].length; e++) clipes[k].addVideoEffect(qe.project.getVideoEffectByName(specs[k][2][e][0]));
      var out = [];
      for (var k = 0; k < specs.length; k++) {
        var ti = v1.clips[k], lidos = [];
        for (var j = 0; j < ti.components.numItems; j++) if (ti.components[j].matchName == "AE.ADBE Motion")
          for (var jj = 0; jj < ti.components[j].properties.numItems; jj++)
            if (ti.components[j].properties[jj].displayName == "Scale") { ti.components[j].properties[jj].setValue(specs[k][1], true); lidos.push(["Motion Scale", ti.components[j].properties[jj].getValue()]); }
        for (var e = 0; e < specs[k][2].length; e++) {
          var comp = null, vals = specs[k][2][e][1];
          var nmesmo = 0; for (var e2 = 0; e2 < e; e2++) if (specs[k][2][e2][0] == specs[k][2][e][0]) nmesmo++;
          var achados = 0;
          for (var j = 0; j < ti.components.numItems; j++) if (ti.components[j].displayName == specs[k][2][e][0]) { if (achados == nmesmo) { comp = ti.components[j]; break; } achados++; }
          if (!comp) { lidos.push("sem " + specs[k][2][e][0]); continue; }
          var ordem = ["Uniform Scale", "Scale Height", "Scale Width"];
          for (var nn in vals) { var ja2 = false; for (var q = 0; q < ordem.length; q++) if (ordem[q] == nn) ja2 = true; if (!ja2) ordem.push(nn); }
          for (var o = 0; o < ordem.length; o++) { if (!vals.hasOwnProperty(ordem[o])) continue;
            for (var jj = 0; jj < comp.properties.numItems; jj++) { var pr = comp.properties[jj];
              if (pr.displayName == ordem[o]) { pr.setValue(vals[ordem[o]], true); lidos.push([ordem[o], pr.getValue()]); break; } } }
        }
        out.push([ti.name, lidos]);
      }
      app.project.save();
      return out;
    })()"""


CASOS2 = [("13_combo", CARTA, 100, {"pan": 100, "tilt": 50, "zoom": 1.3, "rotate": 10}),
          ("14_4k_pan100_zoom1.2", K4, 50, {"pan": 100, "zoom": 1.2}),
          ("15_4k_neutro", K4, 50, {})]


def montar_fontes(nome: str, casos: list) -> dict:
    """Como `montar`, mas cada clipe com a SUA fonte e a escala do Motion (o encaixe no quadro), e o Transform."""
    os.makedirs(TRABALHO, exist_ok=True)
    proj = os.path.join(TRABALHO, nome + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    specs = [[f, m, traduzir(sz)] for _, f, m, sz in casos]
    js = MONTAR_JS % (pc._js(proj), pc._js(specs), QUADROS, pc._js(CARTA))
    r = p.executar(js)
    print("montar_fontes:", json.dumps(r, ensure_ascii=False)[:1500], flush=True)
    return {"projeto": proj, "resposta": r}


def rodar2(ano: str = "2027") -> dict:
    p.esperar_ponte()
    r = montar_fontes("SIZING FONTES " + ano, CASOS2)
    mov = pc.exportar(r["projeto"], ano)
    res = {"ano": ano, "render": mov, "casos": {}}
    for k, (nome, _, motion, s) in enumerate(CASOS2):
        m = comparar(ler_png(os.path.join(STILLS_RESOLVE, nome + ".png")), quadro(mov, k * QUADROS + MEIO))
        res["casos"][nome] = {"resolve": s, "motion": motion, **m}
        print(nome, json.dumps(m), flush=True)
    with open(os.path.join(TRABALHO, f"medidas_fontes_{ano}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


def cantos_perspectiva(pitch: float = 0.0, yaw: float = 0.0, w: int = W, h: int = H) -> dict:
    """O Pitch/Yaw do Resolve como os 4 cantos do quadro (px), pelo modelo medido: cada ponto é dividido por
    s = 1 − pitch·y + yaw·x (x, y de −1 a +1 a partir do centro, y para BAIXO) — Pitch 0,2: topo ÷ 1,2, base ÷ 0,8."""
    out = {}
    for nome, (x, y) in (("Upper Left", (-1, -1)), ("Upper Right", (1, -1)), ("Lower Left", (-1, 1)), ("Lower Right", (1, 1))):
        s_ = 1 - pitch * y + yaw * x
        out[nome] = [(w / 2 + x * w / 2 / s_) / w, (h / 2 + y * h / 2 / s_) / h]
    return out


def rodar_perspectiva(ano: str = "2027") -> dict:
    """Pitch/Yaw 0,2 no Premiere: Corner Pin com os cantos do modelo × Basic 3D numa varredura de ângulos."""
    p.esperar_ponte()
    casos = [("08_pitch0.2", [["Corner Pin", cantos_perspectiva(pitch=0.2)]]),
             ("09_yaw0.2", [["Corner Pin", cantos_perspectiva(yaw=0.2)]])]
    for a in (6, 9, 11, 12, 13, 15, 18):
        casos.append(("08_pitch0.2", [["Basic 3D", {"Tilt": a}]]))
        casos.append(("09_yaw0.2", [["Basic 3D", {"Swivel": a}]]))
    for a in (-11, -12, -13):
        casos.append(("08_pitch0.2", [["Basic 3D", {"Tilt": a}]]))
        casos.append(("09_yaw0.2", [["Basic 3D", {"Swivel": a}]]))
    specs = [[CARTA, 100, ef] for _, ef in casos]
    os.makedirs(TRABALHO, exist_ok=True)
    proj = os.path.join(TRABALHO, "PERSPECTIVA " + ano + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    js = MONTAR_JS % (pc._js(proj), pc._js(specs), QUADROS, pc._js(CARTA))
    r = p.executar(js)
    print("montar:", json.dumps(r, ensure_ascii=False)[:1200], flush=True)
    mov = pc.exportar(proj, ano)
    res = {"ano": ano, "render": mov, "casos": []}
    for k, (nome, ef) in enumerate(casos):
        m = comparar(ler_png(os.path.join(STILLS_RESOLVE, nome + ".png")), quadro(mov, k * QUADROS + MEIO))
        res["casos"].append({"resolve": nome, "premiere": ef, **m})
        print(nome, json.dumps(ef), json.dumps(m), flush=True)
    with open(os.path.join(TRABALHO, f"medidas_perspectiva_{ano}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


def motion(sizing: dict) -> list:
    """O Input Sizing no MOTION (a entrada da rota Premiere → Avid do Conformar, que o vira 3D Warp/Resize/PIP no MC).
    Mesma tradução do Transform; os flips por efeito."""
    efeitos = []
    m = {}
    pan, tilt = sizing.get("pan", 0.0), sizing.get("tilt", 0.0)
    if pan or tilt:
        m["Position"] = [(W / 2 + pan) / W, (H / 2 - tilt) / H]
    w, h, z = sizing.get("width", 1.0), sizing.get("height", 1.0), sizing.get("zoom", 1.0)
    if (w, h) != (1.0, 1.0):
        m["Uniform Scale"] = False
        m["Scale"] = 100 * z * h
        m["Scale Width"] = 100 * z * w
    elif z != 1.0:
        m["Scale"] = 100 * z
    if sizing.get("rotate"):
        m["Rotation"] = sizing["rotate"]
    if sizing.get("flip_h"):
        efeitos.append(["Horizontal Flip", {}])
    if sizing.get("flip_v"):
        efeitos.append(["Vertical Flip", {}])
    return m, efeitos


CASOS_MC = CASOS + [("13_combo", {"pan": 100, "tilt": 50, "zoom": 1.3, "rotate": 10})]


def montar_motion(ano: str = "2027") -> str:
    """O .prproj "SIZING MC" (sequência COR): um clipe por caso, o Input Sizing no Motion."""
    p.esperar_ponte()
    proj = os.path.join(TRABALHO, "SIZING MC " + ano + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    specs = [[CARTA, 100, ef] for ef in (motion(s)[1] for _, s in CASOS_MC)]
    r = p.executar(MONTAR_JS % (pc._js(proj), pc._js(specs), QUADROS, pc._js(CARTA)))
    js = """(function(){ var s = app.project.activeSequence, mots = %s, out = [];
      var v1 = s.videoTracks[0];
      for (var k = 0; k < mots.length; k++) { var ti = v1.clips[k], comp = null, lidos = [];
        for (var j = 0; j < ti.components.numItems; j++) if (ti.components[j].matchName == "AE.ADBE Motion") comp = ti.components[j];
        var ordem = ["Uniform Scale", "Scale", "Scale Width", "Position", "Rotation"];
        for (var o = 0; o < ordem.length; o++) { if (!mots[k].hasOwnProperty(ordem[o])) continue;
          for (var jj = 0; jj < comp.properties.numItems; jj++) { var pr = comp.properties[jj];
            if (pr.displayName == ordem[o]) { pr.setValue(mots[k][ordem[o]], true); lidos.push([ordem[o], pr.getValue()]); break; } } }
        out.push(lidos); }
      app.project.save(); return out; })()""" % pc._js([motion(s)[0] for _, s in CASOS_MC])
    print("motion:", json.dumps(p.executar(js), ensure_ascii=False)[:1500], flush=True)
    return proj


def rodar_node(ano: str = "2027") -> dict:
    """O NODE SIZING = um SEGUNDO Transform DEPOIS do do Input Sizing (o nó age depois, em px de saída, no eixo da tela —
    medido no Resolve 21.1, banco `drt-drp/estruturas.md`). Os clipes 17 (Input Zoom 1,5 + Node Pan 100) e 18 (Input
    Rotate 10 + Node Pan 100) e o 16 (só Node: o combinado)."""
    casos = [("16_node_combo", [], {"pan": 100, "tilt": 50, "zoom": 1.3, "rotate": 10}),
             ("17_in_zoom1.5_node_pan100", {"zoom": 1.5}, {"pan": 100}),
             ("18_in_rot10_node_pan100", {"rotate": 10}, {"pan": 100})]
    p.instalar()
    if not p._premiere_vivo():
        p.abrir_premiere(ano)
    p.esperar_ponte()
    specs = [[CARTA, 100, (traduzir(i) if i else []) + traduzir(n)] for _, i, n in casos]
    proj = os.path.join(TRABALHO, "NODE SIZING " + ano + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    print("montar:", json.dumps(p.executar(MONTAR_JS % (pc._js(proj), pc._js(specs), QUADROS, pc._js(CARTA))),
                                ensure_ascii=False)[:900], flush=True)
    mov = pc.exportar(proj, ano)
    res = {"ano": ano, "render": mov, "casos": {}}
    for k, (nome, i, n) in enumerate(casos):
        m = comparar(ler_png(os.path.join(STILLS_RESOLVE, nome + ".png")), quadro(mov, k * QUADROS + MEIO))
        res["casos"][nome] = {"input": i, "node": n, **m}
        print(nome, json.dumps(m), flush=True)
    with open(os.path.join(TRABALHO, f"medidas_node_{ano}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


def rodar(ano: str = "2027") -> dict:
    p.instalar()
    if not p._premiere_vivo():
        p.abrir_premiere(ano)
    else:
        p.reabrir_premiere(ano)
    p.esperar_ponte()
    specs = [traduzir(s) for _, s in CASOS]
    r = montar("SIZING " + ano, specs)
    proj = r["projeto"]
    mov = pc.exportar(proj, ano)
    res = {"ano": ano, "render": mov, "casos": {}}
    for k, (nome, s) in enumerate(CASOS):
        pr = quadro(mov, k * QUADROS + MEIO)
        rs = ler_png(os.path.join(STILLS_RESOLVE, nome + ".png"))
        m = comparar(rs, pr)
        res["casos"][nome] = {"resolve": s, "premiere": specs[k], **m}
        print(nome, json.dumps(m), flush=True)
    with open(os.path.join(TRABALHO, f"medidas_{ano}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["rodar"]:
        rodar(*(sys.argv[2:3] or []))
    elif sys.argv[1:2] == ["node"]:
        rodar_node(*(sys.argv[2:3] or []))
    elif sys.argv[1:2] == ["motion"]:
        print(montar_motion(*(sys.argv[2:3] or [])))
    elif sys.argv[1:2] == ["perspectiva"]:
        rodar_perspectiva(*(sys.argv[2:3] or []))
    elif sys.argv[1:2] == ["fontes"]:
        rodar2(*(sys.argv[2:3] or []))

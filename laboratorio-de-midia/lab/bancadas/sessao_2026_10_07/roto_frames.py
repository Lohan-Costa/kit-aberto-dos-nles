# ⚠️ REGISTRO HISTÓRICO — script de UMA rodada, na máquina do autor: os caminhos abaixo são os do SSD de trabalho
# dele e não existem noutra máquina. O que se mediu está registrado no banco (bancodedadosnles). Para repetir,
# peça ao Claude para adaptar: achar o laboratório SUBINDO de pasta e gerar a mídia por uma receita
# (skill ciclo-laboratorio) — nunca com o material de uma produção.
"""Exporta, no Premiere 2026 do Mac, frames de cada clipe da sequência de rotoscopia do autor (cópia), a cada 12 quadros
da FONTE, e grava qual quadro da fonte cada PNG mostra."""
import json, os, sys, time
sys.path.insert(0, "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia")
from lab.bancadas import premiere as p

D = "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia/saida/bancadas/roto26"
PROJ = os.path.join(D, "rotoscopia_teste_premiere26.prproj")
OUT = os.path.join(D, "frames"); os.makedirs(OUT, exist_ok=True)
J = json.dumps
TPS = 254016000000
p.esperar_ponte(120)
print("versao", p.executar("app.version"))
p.executar("""(function(){ var a=''; try { a = app.project.path; } catch (e) {} if (a) app.project.closeDocument(0, 0); return a; })()""")
print("abrir", p.executar("app.openDocument(%s, true, true, true)" % J(PROJ), timeout=300)); time.sleep(8)
clipes = p.executar("""(function(){ var s = app.project.sequences[0], o = []; app.project.openSequence(s.sequenceID);
  for (var t = 0; t < s.videoTracks.numTracks; t++) { var tr = s.videoTracks[t];
    for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
      o.push({trilha: t, nome: c.name, inicio: c.start.ticks, fim: c.end.ticks, entrada: c.inPoint.ticks}); } }
  return {seq: s.name, clipes: o}; })()""")
print(clipes)
rel = []
for n, c in enumerate(clipes["clipes"]):
    ini, fim, ent = int(c["inicio"]), int(c["fim"]), int(c["entrada"])
    q0 = (ent + TPS // 50) // (TPS // 25)
    q = q0
    while True:
        t_seq = ini + q * (TPS // 25) - ent
        if t_seq >= fim - TPS // 25:
            break
        alvo = os.path.join(OUT, "c%d_q%03d" % (n + 1, q))
        if os.path.exists(alvo + ".png"):
            os.remove(alvo + ".png")
        p.executar("""(function(){ var s=app.project.activeSequence; s.setPlayerPosition(%s);
          app.enableQE(); var qs=qe.project.getActiveSequence(); qs.exportFramePNG(qs.CTI.timecode, %s); return 1; })()"""
                   % (J(str(t_seq)), J(alvo)), timeout=120)
        t = time.time()
        while not os.path.exists(alvo + ".png") and time.time() - t < 15:
            time.sleep(0.2)
        rel.append({"clipe": n + 1, "quadro_fonte": q, "png": os.path.basename(alvo) + ".png", "ok": os.path.exists(alvo + ".png")})
        q += 12
    print("clipe", n + 1, sum(1 for r in rel if r["clipe"] == n + 1), "frames")
json.dump({"clipes": clipes, "frames": rel}, open(os.path.join(OUT, "frames.json"), "w"), indent=1)
p.executar("app.project.closeDocument(0, 0)", timeout=60)

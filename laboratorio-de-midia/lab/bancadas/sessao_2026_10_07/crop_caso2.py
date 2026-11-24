"""Caso CROP: no Premiere 25.6.5 do Mac, 3 sequências com o crop do MOTION (+ posição/escala, + Transform na pilha),
frames de referência; o .prproj vai para a pasta compartilhada para ser rebaixado e conferido no 23.2 do Windows."""
import json, os, sys, time
sys.path.insert(0, "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia")
from lab.bancadas import premiere as p
from lab.bancadas import premiere_projeto as pp

B = "/Volumes/_transfer/LABORATORIO - TESTE PREMIERE 2023/CROP"
MIDIA = os.path.join(B, "midia", "B01_MOV-PRORES.mov")
PROJ = os.path.join(B, "CROP2 2025 - original.prproj")
REF = os.path.join(B, "ref-2025")
os.makedirs(REF, exist_ok=True)
J = json.dumps

p.esperar_ponte(60)
p.executar("""(function(){ var a=''; try { a = app.project.path; } catch (e) {} if (a) app.project.closeDocument(0, 0); return a; })()""")
if os.path.exists(PROJ):
    os.remove(PROJ)
print("novo", p.executar("app.newProject(%s)" % J(PROJ), timeout=120))
time.sleep(3)
print("importa", p.executar(pp._JS + "app.project.importFiles([%s], true, app.project.rootItem, false)" % J(MIDIA), timeout=120))

CASOS = {
    "SEQ C4 BLUR E CROP": ((30, 0, 0, 0), [0.6, 0.5], 100, ["Gaussian Blur", "Desfoque Gaussiano (herdado)"], "Blurriness", 40),
    "SEQ C5 LUMETRI E CROP": ((0, 15, 25, 0), [0.45, 0.5], 90, ["Lumetri Color", "Cor Lumetri"], "Exposure", 2),
}
for nome, (crop, pos, esc, fx, prm, val) in CASOS.items():
    js = pp._JS + """(function(){
      var m = _lab_midia(%s); var s = app.project.createNewSequenceFromClips(%s, [m], app.project.rootItem);
      var ti = s.videoTracks[0].clips[0], mo = _lab_comp(ti, "AE.ADBE Motion"), feitos = [];
      for (var i = 0; i < mo.properties.numItems; i++) { var pr = mo.properties[i], n = pr.displayName;
        if (n == "Crop Left") { pr.setValue(%s, true); feitos.push(n); }
        if (n == "Crop Top") { pr.setValue(%s, true); feitos.push(n); }
        if (n == "Crop Right") { pr.setValue(%s, true); feitos.push(n); }
        if (n == "Crop Bottom") { pr.setValue(%s, true); feitos.push(n); }
        if (n == "Position") { pr.setValue(%s, true); feitos.push(n); }
        if (n == "Scale") { pr.setValue(%s, true); feitos.push(n); } }
      app.enableQE(); var q = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0);
      var antes = _lab_matches(ti); q.addVideoEffect(_lab_fx(%s)); var c = _lab_novo(ti, antes), ok = false;
      for (var i = 0; i < c.properties.numItems; i++) if (c.properties[i].displayName == %s) { c.properties[i].setValue(%s, true); ok = true; }
      return {seq: s.name, feitos: feitos, efeito: c.matchName, parametro: ok, comps: _lab_matches(ti)}; })()""" % (
        J(MIDIA), J(nome), crop[0], crop[1], crop[2], crop[3], J(pos), esc, J(fx), J(prm), val)
    print(nome, p.executar(js, timeout=180))

# frames de referência: 1 s e 5 s de cada sequência
for nome in CASOS:
    for seg in (1, 5):
        arq = os.path.join(REF, "%s-%ds" % (nome.replace(" ", "_"), seg))
        r = p.executar("""(function(){ var q=null; for (var i=0;i<app.project.sequences.numSequences;i++)
            if (app.project.sequences[i].name==%s) q=app.project.sequences[i];
          app.project.openSequence(q.sequenceID); var s=app.project.activeSequence; s.setPlayerPosition(%s);
          app.enableQE(); var qs=qe.project.getActiveSequence(); return qs.exportFramePNG(qs.CTI.timecode, %s); })()"""
                       % (J(nome), J(str(seg * 254016000000)), J(arq)), timeout=120)
        t = time.time()
        while not os.path.exists(arq + ".png") and time.time() - t < 15:
            time.sleep(0.3)
        print(" frame", os.path.basename(arq), os.path.exists(arq + ".png"))
print("salvar", p.executar("app.project.save()", timeout=120))
time.sleep(2)
p.executar("app.project.closeDocument(0, 0)", timeout=60)
print("ok", os.path.getsize(PROJ))

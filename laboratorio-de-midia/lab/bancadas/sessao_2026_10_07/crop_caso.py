"""Caso CROP: no Premiere 25.6.5 do Mac, 3 sequências com o crop do MOTION (+ posição/escala, + Transform na pilha),
frames de referência; o .prproj vai para a pasta compartilhada para ser rebaixado e conferido no 23.2 do Windows."""
import json, os, sys, time
sys.path.insert(0, "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia")
from lab.bancadas import premiere as p
from lab.bancadas import premiere_projeto as pp

B = "/Volumes/_transfer/LABORATORIO - TESTE PREMIERE 2023/CROP"
MIDIA = os.path.join(B, "midia", "B01_MOV-PRORES.mov")
PROJ = os.path.join(B, "CROP 2025 - original.prproj")
REF = os.path.join(B, "ref-2025")
J = json.dumps

p.esperar_ponte(60)
p.executar("""(function(){ var a=''; try { a = app.project.path; } catch (e) {} if (a) app.project.closeDocument(0, 0); return a; })()""")
if os.path.exists(PROJ):
    os.remove(PROJ)
print("novo", p.executar("app.newProject(%s)" % J(PROJ), timeout=120))
time.sleep(3)
print("importa", p.executar(pp._JS + "app.project.importFiles([%s], true, app.project.rootItem, false)" % J(MIDIA), timeout=120))

CASOS = {
    # sequência: (crop L, T, R, B), posição, escala, Transform na pilha (posição dele)
    "SEQ C1 CROP50 POS": ((50, 0, 0, 0), [0.65, 0.5], 100, None),
    "SEQ C2 CROP MISTO ESCALA": ((25, 10, 0, 20), [0.4, 0.55], 80, None),
    "SEQ C3 TRANSFORM E CROP": ((0, 0, 30, 0), [0.5, 0.5], 100, [1200, 400]),
}
for nome, (crop, pos, esc, transf) in CASOS.items():
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
      var tr = null;
      if (%s) { app.enableQE(); var q = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0);
        var antes = _lab_matches(ti); q.addVideoEffect(_lab_fx(["Transform", "Transformar"])); var c = _lab_novo(ti, antes);
        for (var i = 0; i < c.properties.numItems; i++) if (c.properties[i].displayName == "Position") { c.properties[i].setValue(%s, true); }
        tr = c.matchName; }
      return {seq: s.name, feitos: feitos, transform: tr, comps: _lab_matches(ti)}; })()""" % (
        J(MIDIA), J(nome), crop[0], crop[1], crop[2], crop[3], J(pos), esc, "true" if transf else "false",
        J([transf[0] / 1920.0, transf[1] / 1080.0]) if transf else "null")
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

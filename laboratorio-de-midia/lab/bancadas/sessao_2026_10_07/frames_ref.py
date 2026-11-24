# ⚠️ REGISTRO HISTÓRICO — script de UMA rodada, na máquina do autor: os caminhos abaixo são os do SSD de trabalho
# dele e não existem noutra máquina. O que se mediu está registrado no banco (bancodedadosnles). Para repetir,
# peça ao Claude para adaptar: achar o laboratório SUBINDO de pasta e gerar a mídia por uma receita
# (skill ciclo-laboratorio) — nunca com o material de uma produção.
"""Frames de referência no Premiere 2026 do Mac: cada caso nativo do 26, cada sequência, a 10/50/90% da duração."""
import json, os, re, sys, time
sys.path.insert(0, "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia")
from lab.bancadas import premiere as p

NAT = "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia/saida/bancadas/lab26/nativo"
REF = "/Volumes/_transfer/LABORATORIO - TESTE PREMIERE 2023/LAB 26 PARA 23/ref-2026"
J = json.dumps
FRACOES = (0.1, 0.5, 0.9)


def nome_arq(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)


if "--abrir" in sys.argv:
    try:
        p.fechar_premiere("2025")
    except Exception as e:
        print("fechar 2025:", e)
    if os.path.exists(p.ARQ_PONTE):
        os.replace(p.ARQ_PONTE, p.ARQ_PONTE + ".anterior")
    p.abrir_premiere("2026")
p.esperar_ponte(300)
print("versao", p.executar("app.version"))
rel = {}
for arq in sorted(os.listdir(NAT)):
    if not arq.endswith(".prproj") or arq.startswith("._"):
        continue
    caso = arq[:-7]
    pasta = os.path.join(REF, caso)
    os.makedirs(pasta, exist_ok=True)
    p.executar("""(function(){ var a=''; try { a = app.project.path; } catch (e) {} if (a) app.project.closeDocument(0, 0); return a; })()""")
    print(caso, "abrir", p.executar("app.openDocument(%s, true, true, true)" % J(os.path.join(NAT, arq)), timeout=300))
    time.sleep(5)
    seqs = p.executar("""(function(){ var o=[]; for (var i=0;i<app.project.sequences.numSequences;i++) { var s=app.project.sequences[i];
        o.push({nome: s.name, fim: s.end}); } return o; })()""")
    rel[caso] = []
    for s in seqs:
        for f in FRACOES:
            ticks = str(int(int(s["fim"]) * f))
            alvo = os.path.join(pasta, "%s-%02d" % (nome_arq(s["nome"]), int(f * 100)))
            if os.path.exists(alvo + ".png"):
                os.remove(alvo + ".png")
            r = p.executar("""(function(){ var q=null; for (var i=0;i<app.project.sequences.numSequences;i++)
                  if (app.project.sequences[i].name==%s) q=app.project.sequences[i];
                app.project.openSequence(q.sequenceID); var s=app.project.activeSequence; s.setPlayerPosition(%s);
                app.enableQE(); var qs=qe.project.getActiveSequence(); qs.exportFramePNG(qs.CTI.timecode, %s); return qs.CTI.timecode; })()"""
                           % (J(s["nome"]), J(ticks), J(alvo)), timeout=180)
            t = time.time()
            while not os.path.exists(alvo + ".png") and time.time() - t < 20:
                time.sleep(0.3)
            rel[caso].append({"seq": s["nome"], "fracao": f, "ticks": ticks, "tc": r, "png": os.path.exists(alvo + ".png")})
    print(caso, len(seqs), "sequências,", sum(x["png"] for x in rel[caso]), "frames")
    p.executar("app.project.closeDocument(0, 0)", timeout=60)
with open(os.path.join(REF, "ref-2026.json"), "w") as fh:
    json.dump(rel, fh, ensure_ascii=False, indent=1)

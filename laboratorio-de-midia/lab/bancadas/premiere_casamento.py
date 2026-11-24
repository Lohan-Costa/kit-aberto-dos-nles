"""BL08, etapa 3 — a montagem do laboratório de CASAMENTO no Premiere 2027 (Mac), nos DAILIES da BL08, e o xmeml.

Plano: `2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-22-lab-casamento-baselight.md`. Mídia: `python3 -m lab.casamento gerar`.

    python3 -m lab.bancadas.premiere_casamento rodar     # abre o 2027, monta, exporta o XML, salva e FECHA o Premiere

Tudo num processo só: o vigia de diálogos sobe com mandato preso a ele e morre junto. 18 planos na V1, corte seco, 2 s
cada (48 quadros a 23,976). `MONTAGEM` diz de que daily sai cada plano e o original CERTO — a verdade da conferência.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unicodedata

from . import premiere as p
from ..casamento import SAIDA
from .avid_baselight import RAIZ

ANO = "2027"
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere_casamento")
PROJETO = os.path.join(TRAB, "BL08 CASAMENTO.prproj")
SEQ = "BL08 CASAMENTO"
TICKS_S = 254016000000
QUADRO = 10594584000                    # um quadro a 23,976 em ticks
DUR = 48                                 # 2 s na timeline

#: (evento, daily, in em SEGUNDOS da fonte, o que o plano prova)
MONTAGEM = [
    ("E01", "DAILIES/DIA01/CARTAO_A/A001C003.mov", 3.0, "P1: o in existe nos dois cartões"),
    ("E02", "DAILIES/DIA01/CARTAO_B/A001C003.mov", 5.0, "P1: o do cartão B"),
    ("E03", "DAILIES/DIA01/A002/A001C004.mov", 2.0, "P2: DIA01"),
    ("E04", "DAILIES/DIA02/A002/A001C004.mov", 4.0, "P2: DIA02 (mesmo nome, TC e duração)"),
    ("E05", "DAILIES/DIA01/B001/B001C005.mov", 2.0, "P3: proxy 23,976 de um 59,94"),
    ("E06", "DAILIES/DIA01/B001/CENA12_T3.mov", 2.0, "P4: o daily renomeado"),
    ("E07", "DAILIES/DIA01/B001/B001C008.mov", 2.0, "P4: o vizinho de nome certo"),
    ("E08", "DAILIES/DIA01/A003/a001c008.MOV", 2.0, "P5: caixa e extensão"),
    ("E09", "DAILIES/DIA01/A003/CORAÇÃO_01.mov", 2.0, "P5: acento"),
    ("E10", "DAILIES/DIA01/GRAFICOS/PLACA_298.mov", 1.0, "P6: número no fim do nome"),
    ("E11", "DAILIES/DIA01/GRAFICOS/PLACA_297.mov", 1.0, "P6: o 297 (a 'sequência' do 298)"),
    ("E12", "DAILIES/DIA02/A004/A002C001.mov", 12.0, "P7: depois do minuto (16:59:02;xx DF × NDF)"),
    ("E13", "DAILIES/DIA02/C001/C001C003.mov", 2.0, "P8: reel vazio no daily"),
    ("E14", "DAILIES/DIA02/C001/C001C004.mov", 2.0, "P8: o reel do C001C003 no daily do C001C004"),
    ("E15", "DAILIES/DIA01/C002/C001C002.mov", 2.0, "P9: cópia idêntica no BACKUP"),
    ("E16", "DAILIES/DIA02/A005/A003C001.mov", 1.0, "P10: o original é uma sequência DPX"),
    ("E17", "DAILIES/DIA01/CARTAO_A/A001C003.mov", 14.0, "P1: um in que só o cartão A tem (o B tem 12 s)"),
    ("E18", "DAILIES/DIA02/A004/A002C001.mov", 2.0, "P7: antes do minuto (o rótulo DF = NDF)"),
    ("E19", "DAILIES/DIA02/A006/A006C001.mov", 3.0, "P11: original com TC 20:00:00:00, a conversão com TC zerado"),
    ("E20", "DAILIES/DIA02/A006/A006C002.mov", 3.0, "P12: original com TC zerado, a conversão com TC 21:00:00:00"),
]


def _verdade() -> dict:
    with open(os.path.join(SAIDA, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    return {unicodedata.normalize("NFC", d["arquivo"]): d for d in v["dailies"]}


def _foto(nome: str) -> str:
    os.makedirs(os.path.join(TRAB, "prints"), exist_ok=True)
    arq = os.path.join(TRAB, "prints", f"{time.strftime('%H%M%S')}_{nome}.png")
    subprocess.run(["screencapture", "-x", arq], check=False)
    return arq


_JS = r"""
function _c_por() { var it = _lab_itens(app.project.rootItem), por = {};
  for (var i = 0; i < it.length; i++) if (it[i].getMediaPath()) por[it[i].getMediaPath()] = it[i]; return por; }
function _c_t(ticks) { var t = new Time(); t.ticks = String(ticks); return t; }
"""


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    verdade = _verdade()
    aberto = p.executar(p._LIB + """(function(){ var alvo = %s, atual = '';
      try { atual = app.project.path; } catch (e) {}
      if (atual == alvo) return 'já aberto';
      if (new File(alvo).exists) return app.openDocument(alvo, true, true, true);
      return app.newProject(alvo); })()""" % p._js(PROJETO))
    print("projeto:", aberto, flush=True)
    arqs = sorted({os.path.join(SAIDA, d) for _e, d, _i, _n in MONTAGEM})
    ja = p.executar(p._LIB + _JS + "(function(){ var o = [], por = _c_por(); for (var k in por) o.push(k); return o; })()") or []
    ja_nfc = {unicodedata.normalize("NFC", a) for a in ja}
    novos = [a for a in arqs if unicodedata.normalize("NFC", a) not in ja_nfc]
    if novos:
        p.executar("app.project.importFiles(%s, true, app.project.rootItem, false)" % p._js(novos), timeout=300)
    caminhos = p.executar(p._LIB + _JS + "(function(){ var o = [], por = _c_por(); for (var k in por) o.push(k); return o; })()")
    por_nfc = {unicodedata.normalize("NFC", c): c for c in caminhos}
    plano = []
    for ev, d, ins, nota in MONTAGEM:
        caminho = por_nfc[unicodedata.normalize("NFC", os.path.join(SAIDA, d))]
        plano.append([caminho, int(round(ins * TICKS_S)), DUR * QUADRO])
    res = p.executar(p._LIB + _JS + """(function(){ var por = _c_por(), plano = %s, nome = %s;
      var s = _lab_seq(nome); if (s) app.project.deleteSequence(s);
      s = app.project.createNewSequenceFromClips(nome, [por[plano[0][0]]], app.project.rootItem); s.name = nome;
      for (var t = 0; t < s.videoTracks.numTracks; t++) while (s.videoTracks[t].clips.numItems) s.videoTracks[t].clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      var pos = 0;
      for (var i = 0; i < plano.length; i++) { var it = por[plano[i][0]];
        it.setInPoint(_c_t(plano[i][1]), 4); it.setOutPoint(_c_t(plano[i][1] + plano[i][2]), 4);
        s.videoTracks[0].overwriteClip(it, _c_t(pos)); it.clearInPoint(); it.clearOutPoint(); pos += plano[i][2]; }
      var info = _lab_seqinfo(s); app.project.save(); return info; })()""" % (p._js(plano), p._js(SEQ)), timeout=300)
    xml = os.path.join(TRAB, "BL08_CASAMENTO.xml")
    if os.path.exists(xml):
        os.remove(xml)
    p.executar(p._LIB + "_lab_seq(%s).exportAsFinalCutProXML(%s, 1)" % (p._js(SEQ), p._js(xml)), timeout=120)
    eventos = []
    for (ev, d, ins, nota), c in zip(MONTAGEM, (res.get("video") or [{}])[0].get("itens", [])):
        v = verdade[unicodedata.normalize("NFC", d)]
        eventos.append({"evento": ev, "daily": d, "in_s": ins, "nota": nota, "pegadinha": v["pegadinha"],
                        "original_certo": v["original_certo"], "premiere": c})
    saida = {"projeto": PROJETO, "sequencia": SEQ, "xml": xml if os.path.exists(xml) else None,
             "premiere": res, "eventos": eventos, "planos_na_timeline": len((res.get("video") or [{}])[0].get("itens", []))}
    with open(os.path.join(TRAB, "montagem.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(saida, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return saida


def rodar() -> dict:
    from . import vigia_dialogos
    p.instalar()
    print(time.strftime("%H:%M:%S"), "abrindo o Premiere", ANO, flush=True)
    p.reabrir_premiere(ANO)
    try:
        with vigia_dialogos.pilotando("BL08 montagem no Premiere 2027"):
            info = p.esperar_ponte(300, vigia=False)
            print(time.strftime("%H:%M:%S"), "ponte:", info.get("premiere"), flush=True)
            print("foto:", _foto("ponte"), flush=True)
            s = montar()
            print(time.strftime("%H:%M:%S"), "planos na timeline:", s["planos_na_timeline"], "xml:", s["xml"], flush=True)
            print("foto:", _foto("montado"), flush=True)
            p.executar("app.project.save()")
            p.executar("app.project.closeDocument(0, 0)", timeout=60)
    finally:
        print(time.strftime("%H:%M:%S"), "fechando o Premiere:", p.fechar_premiere(ANO), flush=True)
    return s


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"rodar": rodar, "montar": montar}[sys.argv[1]]()

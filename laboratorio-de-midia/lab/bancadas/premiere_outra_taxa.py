"""BL09, o render da cor voltando pelo caminho Premiere → RESOLVE (Ciclo Assist, 2026-11-23): a montagem no Premiere 2027
com um plano normal, o render de mesma taxa (BL09) e os dois de OUTRA taxa (BL08: 29,97 DF e 59,94 numa timeline de
23,976), cada render usado do 4º quadro; o Conformar faz o DRT (`tools/prproj_para_drt`) e o Resolve o importa.

    python3 -m lab.bancadas.premiere_outra_taxa rodar     # abre o 2027, monta, salva e FECHA o Premiere
    <assist>/.venv/bin/python -m lab.bancadas.premiere_outra_taxa drt     # o DRT pelo Conformar (o caminho do painel)

A verdade (o quadro de fonte do ORIGINAL no in de cada plano): B001C007 47 · C001C003 64 · A002C001 364 · B001C005 128.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from . import premiere as p
from .avid_baselight import RAIZ

ANO = "2027"
BL = os.path.join(RAIZ, "saida", "baselight")
ORIG08 = os.path.join(BL, "BL08_CASAMENTO", "ORIGINAIS")
ORIG09 = os.path.join(BL, "BL09_ATUALIZAR", "ORIGINAIS")
TRAB = os.path.join(BL, "BL09_ATUALIZAR", "premiere_resolve")
PROJETO = os.path.join(TRAB, "BL09 RENDER RESOLVE.prproj")
SEQ = "BL09 RENDER RESOLVE"
TICKS_S = 254016000000
QUADRO = 10594584000                    # um quadro a 23,976 em ticks
#: (arquivo, in em quadros do PRÓPRIO arquivo a 23,976 — os renders são todos de 23,976 —, duração em quadros da timeline)
MONTAGEM = [
    (os.path.join(ORIG08, "DIA01/B001/B001C007.mov"), 47, 40),
    (os.path.join(BL, "BL09_ATUALIZAR/RENDER_DA_COR/C001C003_COR.mov"), 4, 40),
    (os.path.join(BL, "BL09_ATUALIZAR/RENDER_OUTRA_TAXA/A002C001_COR.mov"), 4, 40),
    (os.path.join(BL, "BL09_ATUALIZAR/RENDER_OUTRA_TAXA/B001C005_COR.mov"), 4, 40),
]
VERDADE = {"B001C007.mov": 47, "C001C003.mov": 64, "A002C001.mov": 364, "B001C005.mov": 128}

_JS = r"""
function _c_por() { var it = _lab_itens(app.project.rootItem), por = {};
  for (var i = 0; i < it.length; i++) if (it[i].getMediaPath()) por[it[i].getMediaPath()] = it[i]; return por; }
function _c_t(ticks) { var t = new Time(); t.ticks = String(ticks); return t; }
"""


def _foto(nome: str) -> str:
    os.makedirs(os.path.join(TRAB, "prints"), exist_ok=True)
    arq = os.path.join(TRAB, "prints", f"{time.strftime('%H%M%S')}_{nome}.png")
    subprocess.run(["screencapture", "-x", arq], check=False)
    return arq


def montar() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    print("projeto:", p.executar(p._LIB + """(function(){ var alvo = %s, atual = '';
      try { atual = app.project.path; } catch (e) {}
      if (atual == alvo) return 'já aberto';
      if (new File(alvo).exists) return app.openDocument(alvo, true, true, true);
      return app.newProject(alvo); })()""" % p._js(PROJETO)), flush=True)
    arqs = sorted({a for a, _i, _d in MONTAGEM})
    ja = p.executar(p._LIB + _JS + "(function(){ var o = [], por = _c_por(); for (var k in por) o.push(k); return o; })()") or []
    novos = [a for a in arqs if a not in ja]
    if novos:
        p.executar("app.project.importFiles(%s, true, app.project.rootItem, false)" % p._js(novos), timeout=300)
    plano = [[a, ins * QUADRO, dur * QUADRO] for a, ins, dur in MONTAGEM]
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
    with open(os.path.join(TRAB, "montagem.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    return res


def rodar() -> dict:
    from . import vigia_dialogos
    p.instalar()
    print(time.strftime("%H:%M:%S"), "abrindo o Premiere", ANO, flush=True)
    p.reabrir_premiere(ANO)
    s = {}
    try:
        with vigia_dialogos.pilotando("BL09 render → Resolve, montagem no Premiere 2027"):
            info = p.esperar_ponte(300, vigia=False)
            print(time.strftime("%H:%M:%S"), "ponte:", info.get("premiere"), flush=True)
            s = montar()
            itens = (s.get("video") or [{}])[0].get("itens", [])
            print(time.strftime("%H:%M:%S"), "planos na timeline:", len(itens), flush=True)
            for x in itens:
                print("  ", x)
            print("foto:", _foto("montado"), flush=True)
            p.executar("app.project.save()")
            p.executar("app.project.closeDocument(0, 0)", timeout=60)
    finally:
        print(time.strftime("%H:%M:%S"), "fechando o Premiere:", p.fechar_premiere(ANO), flush=True)
    return s


def drt() -> dict:
    """O caminho do painel do Conformar para o Resolve: `analisar` (o casador com as pastas dos originais) + `montar`."""
    assist = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar")
    sys.path[:0] = [os.path.join(assist, "motor"), os.path.join(assist, "plugins", "media-composer", "servico"), assist]
    from tools.prproj_para_drt import analisar, montar as montar_drt
    analise = analisar(PROJETO, SEQ, [ORIG08, ORIG09])
    for k, v in analise["casamento"].items():
        print(" casador:", os.path.basename(k), "→", v.get("estado"), os.path.basename(v.get("original") or ""),
              ((v.get("trecho") or {}).get("motivo") or "")[:110])
    saida = os.path.join(TRAB, "BL09_RENDER_RESOLVE.drt")
    r = montar_drt(PROJETO, SEQ, saida, [ORIG08, ORIG09], analise=analise, marcar=True, audio=False)
    print("drt:", saida, {k: r.get(k) for k in ("planos", "no_original", "marcas") if k in r})
    return r


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"rodar": rodar, "montar": montar, "drt": drt}[sys.argv[1]]()

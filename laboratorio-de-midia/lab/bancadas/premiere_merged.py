"""B08 MERGED — o merged clip (câmera + som direto como um clipe só), que a API do Premiere não sabe criar (banco,
plugins/premiere-cep/subclipe-e-merged-clip.md). Quem escreve é o construtor de .prproj do Órbita
(`2 ATIVOS/DRAMASYNC/src-python/prproj/builder.py`, `ExportOptions(merged_clips=True)`, validado no 23.2), chamado
SEM o sync dele: a tomada do laboratório já tem a verdade (B06: câmera 01:00:10:00, som direto BWF 01:00:08:00 → a
câmera entra 2 s = 50 quadros depois do som).

    python3 -m lab.bancadas.premiere_merged gerar     # escreve saida/bancadas/B08_MERGED/orbita/LAB B08 MERGED.prproj (formato do 25)
    python3 -m lab.bancadas.premiere_merged salvar    # no Premiere aberto: abre o do Órbita, salva como premiere-<v>/B08_MERGED,
                                                      # retrato + stills + render
    python3 -m lab.bancadas.premiere_merged downgrade <de> <para>

⚠️ Merged mal formado FECHA o Premiere na hora (banco, prproj/escrita.md §2) — o construtor do Órbita já respeita a regra.
O multicam está DESLIGADO no construtor (bug de áudio aberto lá): o B08 é só merged.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

from . import premiere as p
from . import premiere_projeto as pp

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASO = "B08_MERGED"
NOME = "LAB B08 MERGED"
CAM = os.path.join(RAIZ, "saida", "base", "B06_SOM_DIRETO", "B06_CAM_MOV-PRORES.mov")
SOM = os.path.join(RAIZ, "saida", "base", "B06_SOM_DIRETO", "B06_SOM_WAV-BWF.wav")
FPS = 25
QUADROS = [10, 60, 120, 199]          # na sequência do Órbita: só som (0–49) → câmera + som (50…)


def _orbita() -> str:
    """A pasta src-python do Órbita, achada SUBINDO até `PROGRAMAS COM CLAUDE` (nunca caminho fixo)."""
    d = RAIZ
    while d != os.path.dirname(d):
        for cand in (os.path.join(d, "2 ATIVOS", "DRAMASYNC", "src-python"), os.path.join(d, "DRAMASYNC", "src-python")):
            if os.path.isdir(cand):
                return cand
        d = os.path.dirname(d)
    raise FileNotFoundError("não achei DRAMASYNC/src-python subindo de " + RAIZ)


def gerar() -> str:
    sys.path.insert(0, _orbita())
    from pathlib import Path
    from prproj import builder as B
    from sync.model import CameraAngle, CameraGroup, Daily, Project, SoundClip, Take
    tpf = p.TICKS // FPS
    cam_tc = (3600 + 10) * FPS                    # 01:00:10:00
    cam = CameraAngle(path=Path(CAM), fps=FPS, duration_frames=250, timeline_start_frames=50, sync_offset_frames=50,
                      tc_start_frames=cam_tc, alternate_start_ticks=cam_tc * tpf, audio_channels=2, sync_source="timecode")
    som = SoundClip(path=Path(SOM), sample_rate=48000, duration_ms=8000.0, channels=4, timeline_start_frames=0,
                    tc_start_sec=3608.0, scene="B08", take="1")
    d = Daily(camera_groups=[CameraGroup(cameras=[cam], name="CAM A", id="CAM A")], takes=[Take(sound=som, cameras=[cam])],
              fps=float(FPS), name="B08", start_tc_frames=(3600 + 8) * FPS)
    saida = os.path.join(RAIZ, "saida", "bancadas", CASO, "orbita", NOME + ".prproj")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    B.build_prproj(Project(name=NOME, groups=[d]), Path(saida), B.ExportOptions(merged_clips=True, premiere_alvo="25"))
    return saida


def _stills(trab: str) -> dict:
    pasta = os.path.join(os.path.abspath(trab), "stills")
    os.makedirs(pasta, exist_ok=True)
    feitos = {}
    for q in QUADROS:
        arq = os.path.join(pasta, f"SEQ_{q:04d}")
        p.executar(pp._JS + """(function(){ var s = app.project.sequences[0];
          for (var i = 0; i < app.project.sequences.numSequences; i++) if (!app.project.sequences[i].projectItem.isMergedClip()) s = app.project.sequences[i];
          app.project.openSequence(s.sequenceID); app.enableQE();
          s.setPlayerPosition(%s); var qs = qe.project.getActiveSequence(); return qs.exportFramePNG(qs.CTI.timecode, %s); })()"""
                   % (pp._js(str(q * p.TICKS // FPS)), pp._js(arq)))
        limite = time.time() + 10
        while not os.path.exists(arq + ".png") and time.time() < limite:
            time.sleep(0.2)
        time.sleep(0.5)
        feitos[q] = os.path.exists(arq + ".png")
    return feitos


def _abrir_e_retratar(prproj: str, trab: str) -> dict:
    p.salvar_e_fechar()
    p.executar("app.openDocument(%s, true, true, true)" % pp._js(os.path.abspath(prproj)), timeout=120)
    r = pp.retrato()
    r["stills"] = _stills(trab)
    return r


def salvar() -> dict:
    """No Premiere aberto: o arquivo do Órbita aberto e salvo pela própria versão (é o 'nativo' dela), reaberto e descrito."""
    v = p.executar("app.version")
    trab = os.path.join(RAIZ, "saida", "bancadas", f"premiere-{v}", CASO)
    p.salvar_e_fechar()
    if os.path.isdir(trab):
        os.rename(trab, trab + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(trab)
    alvo = os.path.join(trab, NOME + ".prproj")
    shutil.copyfile(os.path.join(RAIZ, "saida", "bancadas", CASO, "orbita", NOME + ".prproj"), alvo)
    p.executar("app.openDocument(%s, true, true, true)" % pp._js(alvo), timeout=120)
    p.executar("app.project.save()")
    ret = _abrir_e_retratar(alvo, trab)
    with open(os.path.join(trab, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ret, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    p.salvar_e_fechar()
    destino = os.path.join(RAIZ, "resultados", CASO, "prproj", f"premiere-{v}-darwin.prproj")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copyfile(alvo, destino)
    from .. import prproj_estrutura
    imp = prproj_estrutura.impressao(destino)
    imp["arquivo"] = os.path.basename(destino)
    with open(destino.replace(".prproj", ".estrutura.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(imp, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return {"versao": v, "trab": trab, "stills": ret["stills"]}


def comparar(trab_a: str, trab_b: str) -> dict:
    with open(os.path.join(trab_a, "retrato.json"), encoding="utf-8") as fa, open(os.path.join(trab_b, "retrato.json"), encoding="utf-8") as fb:
        ra, rb = json.load(fa), json.load(fb)
    return {"versoes": [ra["versao"], rb["versao"]], "diferencas": pp.diferencas(pp.normalizar(ra), pp.normalizar(rb)),
            "psnr_db": {q: pp.psnr(os.path.join(trab_a, "stills", f"SEQ_{q:04d}.png"), os.path.join(trab_b, "stills", f"SEQ_{q:04d}.png"))
                        for q in QUADROS}}


def downgrade(de: str, para: str) -> dict:
    from .. import prproj_downgrade
    v = p.executar("app.version")
    if v != para:
        raise SystemExit(f"a ponte respondeu do Premiere {v}, não do {para}")
    trab = os.path.join(RAIZ, "saida", "bancadas", f"downgrade-{de}-para-{para}", CASO)
    p.salvar_e_fechar()
    if os.path.isdir(trab):
        os.rename(trab, trab + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(trab)
    alvo = os.path.join(trab, NOME + ".prproj")
    r = prproj_downgrade.rebaixar(os.path.join(RAIZ, "resultados", CASO, "prproj", f"premiere-{de}-darwin.prproj"), alvo, para)
    shutil.copyfile(alvo, os.path.join(trab, "rebaixado-antes-de-abrir.prproj"))
    ret = _abrir_e_retratar(alvo, trab)
    with open(os.path.join(trab, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ret, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    p.salvar_e_fechar()
    out = {"de": de, "para": para, "rebaixar": r,
           "contra_a_origem": comparar(os.path.join(RAIZ, "saida", "bancadas", f"premiere-{de}", CASO), trab),
           "contra_o_destino_nativo": comparar(os.path.join(RAIZ, "saida", "bancadas", f"premiere-{para}", CASO), trab)}
    with open(os.path.join(RAIZ, "resultados", CASO, f"downgrade-{de}-para-{para}-darwin.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    os.chdir(RAIZ)
    if argv[0] == "gerar":
        print(gerar())
    elif argv[0] == "salvar":
        print(salvar())
    elif argv[0] == "downgrade":
        r = downgrade(argv[1], argv[2])
        print({k: r[k] for k in ("de", "para")}, r["rebaixar"]["sobrou_versao_de_origem"])
        for k in ("contra_a_origem", "contra_o_destino_nativo"):
            print(k, "psnr", r[k]["psnr_db"], "diferenças:", r[k]["diferencas"][:8])
    elif argv[0] == "comparar":
        print(json.dumps(comparar(argv[1], argv[2]), ensure_ascii=False, indent=1, default=str))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

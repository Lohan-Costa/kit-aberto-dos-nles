"""A rodada completa B01–B06 numa versão do Premiere (Mac), uma versão por vez:

    python3 -m lab.bancadas.rodada_premiere 2025            # reabre o Premiere 2025 e roda os 6 casos
    python3 -m lab.bancadas.rodada_premiere 2026 B05_RASTERS # só um caso, no Premiere que já está aberto

Lê as preferências do arquivo antes (vão para cada resultado: `premiere.preferencias()`). ⚠️ As pontes de duas versões
abertas ao mesmo tempo gravam o MESMO arquivo da ponte: feche a outra versão antes (`premiere.fechar_premiere`).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from . import premiere as p

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASOS = ["B01_FORMATOS", "B02_TAXAS", "B03_LAYOUTS_DE_AUDIO", "B04_TIMECODE", "B05_RASTERS", "B06_SOM_DIRETO"]


def _log(*a) -> None:
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ano, so = argv[0], argv[1:] or None
    os.chdir(RAIZ)
    if not so:
        p.reabrir_premiere(ano)
    p.esperar_ponte(240)
    v = p.executar("app.version")
    if not v.startswith(p._maior(ano)):
        raise SystemExit(f"a ponte respondeu do Premiere {v}, não do {ano}: feche a outra versão")
    _log("versão", v, "preferências", json.dumps(p.preferencias(v), ensure_ascii=False))
    for nome in CASOS:
        if so and nome not in so:
            continue
        caso, trab, proj = f"saida/base/{nome}", f"saida/bancadas/premiere-{v}/{nome}", "LAB " + nome.replace("_", " ")
        t0 = time.time()
        _log("==", nome)
        if nome == "B05_RASTERS":
            _log(p.preparar(caso, trab, proj))
            _log(p.sequencias_hd(trab, os.path.abspath(f"{caso}/B05_HD_MOV-PRORES.mov")))
            _log("stills", all(all(x) for x in p.stills(trab).values()))
            _log(p.guardar_projeto(trab, nome))
        elif nome == "B06_SOM_DIRETO":
            _log(p.preparar(caso, trab, proj))
            _log(p.sync_por_tc(trab, "B06_CAM_MOV-PRORES.mov", "B06_SOM_WAV-BWF.wav"))
            _log("stills", all(all(x) for x in p.stills(trab).values()))
            _log(p.renderizar(trab, ano))
            _log(p.guardar_projeto(trab, nome))
        else:
            _log(p.rodada(caso, trab, proj, ano))
        c = subprocess.run([sys.executable, "-m", "lab.bancadas.conferir", trab, caso], capture_output=True, text=True)
        _log("conferir", c.returncode, c.stdout[-1500:], c.stderr[-1500:])
        _log("tempo", round(time.time() - t0), "s")
    p.salvar_e_fechar()
    _log("FIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

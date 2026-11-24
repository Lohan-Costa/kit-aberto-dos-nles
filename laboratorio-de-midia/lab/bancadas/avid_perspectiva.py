"""O Pitch/Yaw do Resolve no MC: o 3D Warp com rotação X/Y (perspectiva de câmera) alcança a perspectiva LINEAR do
Resolve? (2026-11-21, pedido do autor). No Premiere o Basic 3D, que tem o mesmo modelo, errou ~80–110 px nos cantos.

A rota Premiere → Avid do Conformar (`SIZING MC 2027.prproj`, 10 clipes) com o `_geo_premiere` TROCADO: o clipe k recebe
um 3D Warp só com `DVE_ROT_X` (k ímpar…) ou `DVE_ROT_Y` em `ANGULOS[k]`. Depois a agulha anda pela régua (o `SetPosition`
travou o MC — banco `avb/estruturas.md`), a foto do Record × o still Pitch 0,2 / Yaw 0,2 do Resolve.

    (MC aberto no projeto do laboratório, serviço do Ciclo Assist no ar)  <python com grpc> -m lab.bancadas.avid_perspectiva
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

from . import avid_sizing as A
from .premiere_sizing import STILLS_RESOLVE

PRPROJ = os.path.join(A.RAIZ, "saida", "bancadas", "premiere_sizing", "SIZING MC 2027.prproj")
CARTA_PASTA = os.path.join(A.RAIZ, "saida", "base", "B24_COR_MC")
# (eixo, graus, o still do Resolve a comparar)
ANGULOS = [None, ("x", 12, "08_pitch0.2"), ("x", 20, "08_pitch0.2"), ("x", -12, "08_pitch0.2"),
           ("x", -20, "08_pitch0.2"), ("y", 12, "09_yaw0.2"), ("y", 20, "09_yaw0.2"), ("y", -12, "09_yaw0.2"),
           ("y", -20, "09_yaw0.2"), ("x", 30, "08_pitch0.2")]
QUADROS = 12


def _quadros(tc) -> int:
    if isinstance(tc, (int, float)):
        return int(tc)
    h, m, s, f = (int(x) for x in str(tc).replace(";", ":").split(":"))
    return ((h * 60 + m) * 60 + s) * 24 + f


def montar() -> dict:
    sys.path[:0] = [os.path.join(A.CONFORMAR, "plugins", "media-composer", "servico"), os.path.join(A.CONFORMAR, "motor")]
    from avb_export import translate as T
    from avid.mcapi import MediaComposer
    from prproj_avid import montar as montar_rota
    from tools.prproj_para_drt import analisar

    inicio = {}

    def geo(s):
        q = _quadros(s.get("timeline_tc_in")) - inicio.setdefault("q0", _quadros(s.get("timeline_tc_in")))
        k = round(q / QUADROS)
        if k >= len(ANGULOS) or ANGULOS[k] is None:
            return None
        eixo, graus, _ = ANGULOS[k]
        p = {T.DVE_POS_ON: 1, T.DVE_POS_X: 0.0, T.DVE_POS_Y: 0.0, T.DVE_SCALE_ON: 1, T.DVE_SCALE_X: 100.0,
             T.DVE_SCALE_Y: 100.0, T.DVE_ROT_ON: 1, T.DVE_ROT_Z: 0.0, T.AFX_LOCK: 1,
             (T.DVE_ROT_X if eixo == "x" else T.DVE_ROT_Y): float(graus)}
        return "EFF2_SBLEND", p, {}

    T._geo_premiere = geo
    analise = analisar(PRPROJ, "COR", [CARTA_PASTA])
    for s in analise["leitura"]["segmentos"]:          # a ordem do tempo, para o q0 ser o 1º clipe
        inicio.setdefault("q0", _quadros(s.get("timeline_tc_in")))
        break
    with MediaComposer(timeout=60) as mc:
        projeto = (mc.projeto() or {}).get("path")
        r = montar_rota(mc, analise, projeto, tempfile.mkdtemp(prefix="lab_persp_"), "PERSPECTIVA 3DWARP", "COR",
                        lambda *a, **k: None)
    return {"falhas": r.get("falhas"), "sequencia": r.get("sequencia")}


def medir() -> dict:
    import cv2
    pid = int(subprocess.run(["pgrep", "-f", "AvidMediaComposer.app/Contents/MacOS/AvidMediaComposer$"],
                             capture_output=True, text=True).stdout.split()[0])
    if A.PILOTO not in sys.path:
        sys.path.insert(0, A.PILOTO)
    from piloto import maos
    MediaComposer = A._mc()
    os.makedirs(A.TRABALHO, exist_ok=True)
    fotos = []
    subprocess.run(["osascript", "-e", 'tell application "System Events" to set visible of (first process whose name is "Terminal") to false'])
    try:
        with MediaComposer(timeout=30) as mc:
            for k in range(len(ANGULOS)):
                q = k * QUADROS + 6
                subprocess.run(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'])
                time.sleep(0.5)
                frente = subprocess.run(["bash", "-c", 'lsappinfo info -only name "$(lsappinfo front)"'], capture_output=True, text=True).stdout
                if "Avid" not in frente:
                    raise RuntimeError("o app da frente não é o MC: " + frente)
                maos.clicar(A.REGUA_X0 + (q + 0.5) * A.REGUA_PX, A.REGUA_Y)
                time.sleep(1.2)
                lido = (mc.sequencia_no_record() or {}).get("quadro")
                f = os.path.join(A.TRABALHO, f"persp_{k:02d}.png")
                x, y, w, h = A.REGIAO
                subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{w},{h}", f], check=True)
                fotos.append((k, f, lido))
    finally:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to set visible of (first process whose name is "Terminal") to true'])
        maos.devolver_ao_terminal()
    mapa = np.array([[0.2370, 0, 19.47], [0, 0.2370, 102.8]], np.float32)
    y0, y1, x0, x1 = 106, 355, 23, 471
    res = []
    for k, f, lido in fotos:
        tela = A._cinza(f)
        alvos = ["01_neutro"] if ANGULOS[k] is None else [ANGULOS[k][2]]
        for alvo in alvos:
            rs = cv2.warpAffine(A._cinza(os.path.join(STILLS_RESOLVE, alvo + ".png")), mapa, (A.REGIAO[2], A.REGIAO[3]),
                                flags=cv2.INTER_AREA)
            m = A.comparar(rs[y0:y1, x0:x1], tela[y0:y1, x0:x1])
            m["dif_media"] = round(float(np.abs(rs[y0:y1, x0:x1] - tela[y0:y1, x0:x1]).mean() * 255), 1)
            linha = {"k": k, "quadro_lido": lido, "3dwarp": ANGULOS[k], "resolve": alvo, **m}
            res.append(linha)
            print(json.dumps(linha), flush=True)
    with open(os.path.join(A.TRABALHO, "perspectiva.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return {"casos": res}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["montar"]:
        print(json.dumps(montar(), ensure_ascii=False, default=str))
    elif sys.argv[1:2] == ["medir"]:
        medir()

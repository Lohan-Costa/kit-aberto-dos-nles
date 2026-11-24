"""O INPUT SIZING do Resolve no Media Composer (2026-11-21): a rota Premiere → Avid do Conformar (`SIZING MC 2027.prproj`,
o sizing no Motion) escreve 3D Warp / Resize / PIP na bin; aqui a sequência no RECORD é fotografada no quadro do meio de
cada clipe (`SetPosition` pela API, pelo serviço do Ciclo Assist) e comparada, por ECC, ao still do Resolve do mesmo
controle. A foto é do MONITOR (reduzido): o erro sai em px de 1920, com a precisão do monitor (~1 px a 400 de largura).

    (o MC aberto com a sequência COR no Record, o serviço do Ciclo Assist no ar)
    <python com grpc>  -m lab.bancadas.avid_sizing
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time

import numpy as np

from .premiere_sizing import CASOS_MC, STILLS_RESOLVE

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "avid_sizing")
CONFORMAR = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar")
REGIAO = (1370, 50, 500, 400)
#: a régua de TC da timeline (pontos da tela, medido na foto, a COR inteira no quadro): x do quadro 0 e px por quadro
REGUA_X0, REGUA_PX, REGUA_Y = 257.8, 13.165, 585
PILOTO = os.path.join(os.path.dirname(RAIZ), "piloto")        # onde procurar o monitor Record (pontos da tela 1920×1080, medido na foto)
QUADROS, MEIO = 12, 6


def _mc():
    for p in (os.path.join(CONFORMAR, "plugins", "media-composer", "servico"), os.path.join(CONFORMAR, "motor")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from avid.mcapi import MediaComposer
    return MediaComposer


def _foto(caminho: str, pid: int) -> None:
    subprocess.run(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'])
    time.sleep(0.6)
    x, y, w, h = REGIAO
    subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{w},{h}", caminho], check=True)


def _cinza(caminho: str) -> np.ndarray:
    import cv2
    return cv2.imread(caminho, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255


def caixa_do_monitor(neutro: np.ndarray) -> tuple[int, int, int, int]:
    """O retângulo da imagem dentro da foto: o chart neutro enche o quadro (o fundo do monitor é quase preto)."""
    m = neutro > 0.08
    lin, col = np.where(m.any(axis=1))[0], np.where(m.any(axis=0))[0]
    return int(col[0]), int(lin[0]), int(col[-1]) + 1, int(lin[-1]) + 1


def comparar(resolve: np.ndarray, avid: np.ndarray) -> dict:
    import cv2
    h, w = avid.shape
    r = cv2.resize(resolve, (w, h), interpolation=cv2.INTER_AREA)
    wm = np.eye(3, dtype=np.float32)
    try:
        cc, wm = cv2.findTransformECC(r, avid, wm, cv2.MOTION_HOMOGRAPHY, (3, 300, 1e-7), None, 3)
    except cv2.error:
        return {"falhou": True}
    hm = wm / wm[2, 2]
    k = 1920 / w

    def pt(x, y):
        v = hm @ np.array([x, y, 1.0])
        return v[:2] / v[2]
    c, e = pt(w / 2, h / 2), pt(w / 2 + w / 4, h / 2)
    return {"cc": round(float(cc), 4), "centro_dx_px1920": round(float(c[0] - w / 2) * k, 2),
            "centro_dy_px1920": round(float(c[1] - h / 2) * k, 2),
            "escala": round(float(np.linalg.norm(e - c) / (w / 4)), 4),
            "giro": round(math.degrees(math.atan2(e[1] - c[1], e[0] - c[0])), 3),
            "canto_px1920": round(max(float(np.linalg.norm(pt(x, y) - np.array([x, y]))) for x, y in
                                      ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))) * k, 2)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(TRABALHO, exist_ok=True)
    pid = int(subprocess.run(["pgrep", "-f", "AvidMediaComposer.app/Contents/MacOS/AvidMediaComposer$"],
                             capture_output=True, text=True).stdout.split()[0])
    MediaComposer = _mc()
    fotos = []
    # ⛔ NÃO o `SetPosition` da API: no MC 25.12 (Mac), chamado pelo serviço do Ciclo Assist, ele TRAVOU o MC inteiro
    #    (interface e API, 0 % de CPU; 2026-11-21) — a agulha anda por um CLIQUE na régua de TC (só move a agulha).
    if PILOTO not in sys.path:
        sys.path.insert(0, PILOTO)
    from piloto import maos
    subprocess.run(["osascript", "-e", 'tell application "System Events" to set visible of (first process whose name is "Terminal") to false'])
    try:
        with MediaComposer(timeout=30) as mc:
            for k, (nome, _) in enumerate(CASOS_MC):
                q = k * QUADROS + MEIO
                subprocess.run(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'])
                time.sleep(0.5)
                frente = subprocess.run(["bash", "-c", 'lsappinfo info -only name "$(lsappinfo front)"'], capture_output=True, text=True).stdout
                if "Avid" not in frente:
                    raise RuntimeError("o app da frente não é o MC: " + frente)
                maos.clicar(REGUA_X0 + (q + 0.5) * REGUA_PX, REGUA_Y)
                time.sleep(1.2)
                lido = (mc.sequencia_no_record() or {}).get("quadro")
                f = os.path.join(TRABALHO, f"{nome}.png")
                x, y, w, h = REGIAO
                subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{w},{h}", f], check=True)
                print(nome, "quadro pedido", q, "lido", lido, flush=True)
                fotos.append((nome, f))
    finally:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to set visible of (first process whose name is "Terminal") to true'])
        maos.devolver_ao_terminal()
    import cv2
    # o MAPA quadro 1920×1080 → foto: MEDIDO na foto do clipe neutro (os patches da carta B24: x 36→28 e 1884→466,
    # y 60→117 e 1040→349 na captura de REGIAO). ⚠️ O ajuste automático por ECC divergiu (o chart repetido engana):
    # remedir se o layout do MC mudar. ⚠️ Valores para o monitor Record do layout de 2026-11-21 (MC 25.12 Mac).
    canvas = (REGIAO[2], REGIAO[3])
    mapa = np.array([[0.2370, 0, 19.47], [0, 0.2370, 102.8]], np.float32)
    print("mapa 1920 → tela:", np.round(mapa, 4).tolist(), flush=True)
    res = {"mapa": mapa.tolist(), "casos": {}}
    for nome, f in fotos:
        tela = _cinza(f)
        rs = cv2.warpAffine(_cinza(os.path.join(STILLS_RESOLVE, nome + ".png")), mapa, canvas, flags=cv2.INTER_AREA)
        y0, y1, x0, x1 = 106, 355, 23, 471          # o miolo do monitor (2 px para dentro da borda)
        m = comparar(rs[y0:y1, x0:x1], tela[y0:y1, x0:x1])
        m["dif_media"] = round(float(np.abs(rs[y0:y1, x0:x1] - tela[y0:y1, x0:x1]).mean() * 255), 1)
        res["casos"][nome] = m
        print(nome, json.dumps(m), flush=True)
    with open(os.path.join(TRABALHO, "medidas.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

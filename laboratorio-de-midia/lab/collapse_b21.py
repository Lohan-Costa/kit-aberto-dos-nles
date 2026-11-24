"""B21 COLLAPSE — o Collapse do Media Composer (o equivalente do Nest do Premiere, decisão do autor em 2026-10-12: um
Collapse por ocorrência). Caso pedido pelo autor: dois clipes SEQUENCIAIS colapsados, e dois SIMULTÂNEOS num mosaico
(um à esquerda, outro à direita, com Crop e Position) colapsados num elemento só — um efeito aplicado no Collapse vale
para tudo dentro.

Mídia: as placas do B14 (FUNDO azul-escuro, FRENTE laranja) + a VERDE daqui, todas lisas e com o número do quadro do
ARQUIVO num canto (a VERDE em cima à DIREITA: é o lado que fica à mostra no mosaico).

    py -m lab.collapse_b21 gerar
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from . import ffmpeg as ff
from . import video
from .mascara_b14 import COR_FRENTE, COR_FUNDO, FPS, H, W, _hex

COR_VERDE = (0x20, 0x90, 0x40)
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saida", "base", "B21_COLLAPSE")
#: a timeline (144 quadros a 23,976): (trilha, nome da placa, in no arquivo, início na timeline, duração)
SEQUENCIAIS = [(2, "FRENTE", 0, 0, 24), (2, "VERDE", 24, 24, 24)]
MOSAICO = [(2, "FRENTE", 48, 48, 96), (3, "VERDE", 48, 48, 96)]


def _filtro_verde() -> str:
    alt, larg = 120, 66
    x0, y = W - 40 - 5 * (larg + 18), 40
    partes = []
    for i in range(5):
        partes += video._digito(x0 + (4 - i) * (larg + 18), y, larg, alt, f"mod(floor(n/{10 ** i}),10)")
    partes += video._texto("VERDE", x0, y + alt + 20, 5)
    return ",".join(partes)


def gerar(saida: str = SAIDA) -> dict:
    os.makedirs(saida, exist_ok=True)
    arq = os.path.join(saida, "B21_VERDE.mov")
    subprocess.run([ff.achar("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c={_hex(COR_VERDE)}:s={W}x{H}:r={FPS}:d=6", "-vf", _filtro_verde(),
                    "-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", arq], check=True)
    verdade = {"caso": "B21_COLLAPSE", "raster": [W, H], "fps_timeline": FPS,
               "cores": {"FUNDO": COR_FUNDO, "FRENTE": COR_FRENTE, "VERDE": COR_VERDE},
               "arquivos": {"FUNDO": "../B14_MASCARA/B14_FUNDO.mov", "FRENTE": "../B14_MASCARA/B14_FRENTE.mov",
                            "VERDE": "B21_VERDE.mov"},
               "sequenciais": SEQUENCIAIS, "mosaico": MOSAICO}
    with open(os.path.join(saida, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(verdade, f, ensure_ascii=False, indent=1)
    return verdade


if __name__ == "__main__":
    if sys.argv[1:2] == ["gerar"]:
        print(json.dumps(gerar(), ensure_ascii=False))

"""B31_EDL_SOM: grava no som direto o que um gravador grava e o gerador não — o iXML com o SOUND ROLL (TAPE), cena,
take e o NOME de cada microfone (TRACK_LIST). Sem isso a EDL de som não tem o que pôr no reel.

    python -m lab.edl_som rotular [pasta]     # padrão: saida/base/B31_EDL_SOM

Reescreve só os WAV do caso, em lugar (o bloco `iXML` antes do `data`; o `bext` e o áudio ficam idênticos).
"""
from __future__ import annotations

import os
import struct
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA = os.path.join(RAIZ, "saida", "base", "B31_EDL_SOM")
ROLL = "26Y11M25"
MICS = ["MIX L", "MIX R", "BOOM", "LAPELA ANA", "LAPELA BETO", "AMBIENTE"]
TAKES = {"26Y11M25_T001_WAV-BWF.wav": ("12", "1"), "26Y11M25_T002_WAV-BWF.wav": ("12", "2")}


def _blocos(dados: bytes) -> list[tuple[bytes, bytes]]:
    assert dados[:4] == b"RIFF" and dados[8:12] == b"WAVE"
    i, out = 12, []
    while i + 8 <= len(dados):
        nome, tam = dados[i:i + 4], struct.unpack("<I", dados[i + 4:i + 8])[0]
        out.append((nome, dados[i + 8:i + 8 + tam]))
        i += 8 + tam + (tam & 1)
    return out


def ixml(cena: str, take: str) -> bytes:
    trilhas = "".join(f"<TRACK><CHANNEL_INDEX>{k}</CHANNEL_INDEX><INTERLEAVE_INDEX>{k}</INTERLEAVE_INDEX>"
                      f"<NAME>{n}</NAME></TRACK>" for k, n in enumerate(MICS, 1))
    return (f'<?xml version="1.0" encoding="UTF-8"?><BWFXML><IXML_VERSION>1.5</IXML_VERSION><PROJECT>LAB EDL SOM</PROJECT>'
            f"<SCENE>{cena}</SCENE><TAKE>{take}</TAKE><TAPE>{ROLL}</TAPE>"
            f"<SPEED><TIMECODE_RATE>24000/1001</TIMECODE_RATE><TIMECODE_FLAG>NDF</TIMECODE_FLAG></SPEED>"
            f"<TRACK_LIST><TRACK_COUNT>{len(MICS)}</TRACK_COUNT>{trilhas}</TRACK_LIST></BWFXML>").encode("utf-8")


def rotular(pasta: str = PASTA) -> list[str]:
    feitos = []
    for nome, (cena, take) in TAKES.items():
        caminho = os.path.join(pasta, nome)
        with open(caminho, "rb") as f:
            blocos = [b for b in _blocos(f.read()) if b[0] != b"iXML"]
        x = ixml(cena, take)
        novos = []
        for b in blocos:
            if b[0] == b"data":
                novos.append((b"iXML", x))
            novos.append(b)
        corpo = b"".join(n + struct.pack("<I", len(d)) + d + (b"\0" if len(d) & 1 else b"") for n, d in novos)
        with open(caminho + ".tmp", "wb") as f:
            f.write(b"RIFF" + struct.pack("<I", 4 + len(corpo)) + b"WAVE" + corpo)
        os.replace(caminho + ".tmp", caminho)
        feitos.append(f"{nome}: TAPE {ROLL}, cena {cena}, take {take}, {len(MICS)} microfones")
    return feitos


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] != "rotular":
        print(__doc__)
        sys.exit(2)
    for linha in rotular(sys.argv[2] if len(sys.argv) > 2 else PASTA):
        print(linha)

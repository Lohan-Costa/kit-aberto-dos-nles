"""O NOME que o Media Composer dá ao master de um WAV no link, conforme os metadados (autor, 2026-10-25).

A pergunta: o MC nomeia o master de um BWF de gravador por CENA/TAKE (medido no PRODC: `faixa-w-C4/002`, sem a
extensão) — e quando NÃO há cena? A extensão vem ou não? O `;` vira `_` (o que o autor viu no PRODUCAO-A)? E na cena?

Cada WAV muda UMA coisa (1 s de tom de 1 kHz, 48 kHz, 24-bit, mono, a mesma essência). Gera em
`saida/bancadas/avid/nomes_audio/` e um `nomes_audio_casos.json` (ao lado) com o que cada um tem. O link é pelo Source Browser do MC (Tools ›
Source Browser › colar a pasta na barra › selecionar todos › Link › OK to All no diálogo da taxa do áudio); a leitura
da bin (o nome do master, o `_USER`, os nomes das fontes) é do `ler`.

Uso: `python -m lab.bancadas.avid.nomes_audio gerar`  ·  `python -m lab.bancadas.avid.nomes_audio ler <bin.avb>`
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SAIDA = os.path.join(RAIZ, "saida", "bancadas", "avid", "nomes_audio")

TR = 48000 * 3600 * 10            # time_reference de 10:00:00:00 (o diálogo da taxa vai aparecer, como num gravador)

# (arquivo, cena, take, onde a cena/take mora: "bext" | "ixml" | "" | None = sem bext nenhum, nota)
CASOS = [
    ("LAB_V01-A.WAV", "LAB-CENA", "001", "bext", "cena/take no bext (o MixPre)"),
    ("LAB_V02-A.WAV", "LAB-CENA2", "002", "ixml", "cena/take SÓ no iXML"),
    ("LAB_V03-A.WAV", None, None, "", "BWF sem cena/take (bext com time_reference)"),
    ("LAB_V04 plain.wav", None, None, None, "WAV simples, sem bext nem iXML"),
    ("LAB;V05;A.WAV", None, None, "", "; no NOME do arquivo, sem cena"),
    ("LAB_V06.WAV", "CENA;6", "001", "bext", "; na CENA"),
    ("LAB V07 ação.WAV", None, None, "", "espaço e acento no nome, sem cena"),
    ("LAB_V08.wav", None, None, "", "extensão minúscula, sem cena"),
    ("LAB_V09_UM_NOME_BEM_COMPRIDO_PARA_VER_SE_TRUNCA_0123456789.WAV", None, None, "", "nome longo, sem cena"),
    ("LAB_V10.WAV", "CENA10", "3A", "bext", "take com letra"),
    ("LAB_V11;X.WAV", "CENA11", "001", "bext", "; no nome do arquivo COM cena"),
]


def _wav(caminho: str, cena, take, onde) -> None:
    n = 48000
    dados = b"".join(struct.pack("<i", int(0.25 * 8388607 * math.sin(2 * math.pi * 1000 * i / 48000)))[:3]
                     for i in range(n))
    blocos = b""
    if onde is not None:
        desc = ""
        if onde == "bext" and cena:
            desc = (f"sTAKE={take}\r\nsSCENE={cena}\r\nsFILENAME={os.path.basename(caminho)}\r\n"
                    f"sTAPE=LABTAPE\r\nsCIRCLED=FALSE\r\nsTRK1=CANAL1\r\n")
        bext = (desc.encode("latin-1").ljust(256, b"\0") + b"LAB".ljust(32, b"\0") + b"LAB-REF".ljust(32, b"\0")
                + b"2026-10-25" + b"09:50:00" + struct.pack("<Q", TR) + struct.pack("<H", 1) + b"\0" * 64
                + b"\0" * 190)
        blocos += b"bext" + struct.pack("<I", len(bext)) + bext
    fmt = struct.pack("<HHIIHH", 1, 1, 48000, 48000 * 3, 3, 24)
    blocos += b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if onde == "ixml" and cena:
        x = (f"<?xml version=\"1.0\"?><BWFXML><PROJECT>LAB-PROD</PROJECT><SCENE>{cena}</SCENE><TAKE>{take}</TAKE>"
             f"<TAPE>LABTAPE</TAPE><TRACK_LIST><TRACK><CHANNEL_INDEX>1</CHANNEL_INDEX><NAME>CANAL1</NAME></TRACK>"
             f"</TRACK_LIST></BWFXML>").encode("utf-8")
        blocos += b"iXML" + struct.pack("<I", len(x)) + x + (b"\0" if len(x) & 1 else b"")
    blocos += b"data" + struct.pack("<I", len(dados)) + dados
    with open(caminho, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(blocos)) + b"WAVE" + blocos)


def gerar() -> str:
    os.makedirs(SAIDA, exist_ok=True)
    for nome, cena, take, onde, _nota in CASOS:
        _wav(os.path.join(SAIDA, nome), cena, take, onde)
    # fora da pasta dos WAV: o "selecionar todos" do Source Browser levaria o .json junto
    with open(SAIDA + "_casos.json", "w", encoding="utf-8") as f:
        json.dump([{"arquivo": a, "cena": c, "take": t, "onde": o, "nota": n} for a, c, t, o, n in CASOS], f,
                  ensure_ascii=False, indent=1)
    print(SAIDA)
    return SAIDA


def ler(bin_avb: str) -> list:
    """O que o MC gravou na bin para cada master de áudio: o nome, o `_USER` e os nomes das fontes da cadeia."""
    import avb

    fora = []
    with avb.open(bin_avb) as f:
        por = {m.mob_id: m for m in f.content.mobs}
        for m in f.content.mobs:
            if m.property_data.get("mob_type_id") != 2:
                continue
            a = m.property_data.get("attributes")
            user = dict(a.get("_USER") or {}) if a is not None else {}
            fontes = []
            for t in m.tracks[:1]:
                c = t.component
                for x in getattr(c, "components", [c]):
                    s = por.get(getattr(x, "mob_id", None))
                    if s is not None:
                        fontes.append(s.name)
                        for t2 in s.tracks[:1]:
                            for y in getattr(t2.component, "components", [t2.component]):
                                s2 = por.get(getattr(y, "mob_id", None))
                                if s2 is not None:
                                    fontes.append(s2.name)
            fora.append({"master": m.name, "user": user, "fontes": fontes})
    for x in fora:
        print(json.dumps(x, ensure_ascii=False, default=lambda b: "bytes:" + bytes(b).hex()))
    return fora


if __name__ == "__main__":
    if sys.argv[1:2] == ["gerar"]:
        gerar()
    elif sys.argv[1:2] == ["ler"]:
        ler(sys.argv[2])
    else:
        print(__doc__)

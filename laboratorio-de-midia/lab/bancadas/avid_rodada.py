"""Uma rodada completa da bancada do Media Composer, sem o autor (desenho aprovado em 2026-10-11, passos 3–8):
sequência escrita pelo laboratório na bin → referência exportada pelo MC (preset do lab) → DRT pelo caminho do painel
do De Lá Pra Cá → import e render no Resolve → quadro a quadro (o quadro do ORIGINAL que cada quadro mostra) e o som
(os tons da grade do laboratório em cada saída).

    py -m lab.bancadas.avid_rodada mc LAB_CORTES_01      (com o Media Composer)
    py -m lab.bancadas.avid_rodada resolve LAB_CORTES_01 (com o Resolve; o MC fechado)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

from . import avid as A
from . import avid_resolve as AR
from .. import ler

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAIDA = os.path.join(RAIZ, "saida", "bancadas", "avid")

#: as rodadas: projeto do MC, taxa, o original (importado se o master não estiver na bin) e os cortes [(in, duração)] —
#: o quadro esperado sai dos cortes. A bin é a do projeto ("<projeto> Bin.avb").
_CORTES = [(0, 48), (120, 48), (60, 36), (200, 40)]
_B02 = os.path.join(RAIZ, "saida", "base", "B02_TAXAS")
RODADAS = {
    "LAB_CORTES_01": {"projeto": "DLPC LAB 23.976", "fps": "23.976",
                      "original": os.path.join(_B02, "B02_2398_MOV-PRORES.mov"), "cortes": _CORTES},
    "LAB_CORTES_24": {"projeto": "DLPC LAB 24", "fps": "24",
                      "original": os.path.join(_B02, "B02_24_MOV-PRORES.mov"), "cortes": _CORTES},
    "LAB_CORTES_25": {"projeto": "DLPC LAB 25", "fps": "25",
                      "original": os.path.join(_B02, "B02_25_MOV-PRORES.mov"), "cortes": _CORTES},
    "LAB_CORTES_2997P": {"projeto": "DLPC LAB 29.97p", "fps": "29.97",
                         "original": os.path.join(_B02, "B02_2997ND_MOV-PRORES.mov"), "cortes": _CORTES},
    # 1080i/59.94 conta 29,97 quadros; o B02 em drop-frame testa o DF de quebra
    "LAB_CORTES_5994I": {"projeto": "DLPC LAB 59.94i", "fps": "29.97", "drop_frame": True,
                         "original": os.path.join(_B02, "B02_2997DF_MOV-PRORES.mov"), "cortes": _CORTES},
}


def _bin(R: dict) -> str:
    return os.path.join(A.PROJETOS, R["projeto"], R["projeto"] + " Bin.avb")


def _quadros(p: str, w: int = 480, h: int = 270) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def casar(arquivo: str, original: str, esperado: list[int]) -> dict:
    """Para cada quadro de `arquivo`, o quadro do original mais parecido; divergências contra `esperado`."""
    a, b = _quadros(arquivo), _quadros(original)
    achados = [int(((b - q) ** 2).mean(axis=(1, 2)).argmin()) for q in a]
    erros = [(i, j, esperado[i] if i < len(esperado) else None) for i, j in enumerate(achados)
             if i >= len(esperado) or j != esperado[i]]
    return {"quadros": len(a), "esperados": len(esperado), "divergencias": len(erros), "primeiras": erros[:10]}


def tons(arquivo: str) -> list[list[int]]:
    """Os tons da grade presentes em cada CANAL de áudio do arquivo (todas as trilhas, na ordem; uma trilha estéreo
    conta dois canais)."""
    saida = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=channels",
                            "-of", "csv=p=0", arquivo], capture_output=True, text=True).stdout.split()
    fora = []
    for k, n in enumerate(int(x) for x in saida):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-map", f"0:a:{k}", "-f", "f32le",
                              "-ar", "48000", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, np.float32).reshape(-1, n)
        fora += [ler.tons_presentes(x[:, c], 48000) for c in range(n)]
    return fora


def _estado(nome: str) -> str:
    return os.path.join(SAIDA, "rodadas", nome + ".json")


def fase_mc(nome: str) -> dict:
    """Tudo o que é do Media Composer: projeto → preset → import → sequência → referência → DRT. Grava o estado para a
    fase do Resolve (os dois NLEs não ficam abertos juntos: o notebook divide a memória — autor, 2026-10-11)."""
    R = RODADAS[nome]
    aberto = ""
    if A.rodando():
        A.sem_dialogos()
        try:
            with A.mc() as m:
                aberto = os.path.basename(os.path.normpath(m.projeto(recarregar=True).get("path") or ""))
        except Exception:                    # noqa: BLE001 — na Select Project não há projeto para responder
            pass
    if aberto != R["projeto"]:
        if aberto:
            A.voltar_a_select_project()
        A.abrir_projeto(R["projeto"])
    preset = A.instalar_preset(R["fps"])
    master = A.importar(R["original"], _bin(R))
    with A.mc() as m:
        existente = next((it.mob_id for it in m.itens_de(_bin(R), flags=("AllTypes",)) if it.name == nome), None)
    seq = existente or A.montar_sequencia(_bin(R), nome, [(master, i, d) for i, d in R["cortes"]])
    ref = A.exportar(seq, os.path.join(SAIDA, "export"), nome, preset=preset)
    drt = os.path.join(SAIDA, "dlpc", nome + ".drt")
    sessao = A.drt_pelo_dlpc(seq, drt)
    estado = {"sequencia": nome, "mob_id": seq, "referencia_mc": ref, "drt": drt,
              "sessao": {k: sessao.get(k) for k in ("fps", "tc_inicial", "eventos", "masters_na_gerenciada", "avisos")}}
    os.makedirs(os.path.dirname(_estado(nome)), exist_ok=True)
    with open(_estado(nome), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    return estado


def refazer_drt(nome: str) -> dict:
    """O DRT de novo, com o MC fechado (depois de mexer no writer do De Lá Pra Cá)."""
    with open(_estado(nome), encoding="utf-8") as f:
        estado = json.load(f)
    return A.drt_do_disco(_bin(RODADAS[nome]), estado["mob_id"], estado["drt"], nome)


def fase_resolve(nome: str) -> dict:
    """Resolve: import do DRT, render e a comparação (contra o original e a referência do MC)."""
    R = RODADAS[nome]
    with open(_estado(nome), encoding="utf-8") as f:
        estado = json.load(f)
    render = AR.importar_e_renderizar(estado["drt"], nome, "DLPC LAB AVID " + R["projeto"].split()[-1], R["fps"],
                                      os.path.join(SAIDA, "resolve"), drop_frame=R.get("drop_frame", False))
    esperado = [q for i, d in R["cortes"] for q in range(i, i + d)]
    estado.update({
        "conferencia_mc": {**casar(estado["referencia_mc"], R["original"], esperado), "tons": tons(estado["referencia_mc"])},
        "conferencia_resolve": {"arquivo": render, **casar(render, R["original"], esperado), "tons": tons(render)},
        "original_tons": tons(R["original"])})
    with open(_estado(nome), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    return estado


if __name__ == "__main__":
    # py -m lab.bancadas.avid_rodada mc|drt|resolve LAB_CORTES_24 LAB_CORTES_25 …
    fase, nomes = sys.argv[1], sys.argv[2:] or list(RODADAS)
    for n in nomes:
        f = {"mc": fase_mc, "resolve": fase_resolve, "drt": refazer_drt}[fase]
        print(json.dumps(f(n), ensure_ascii=False, indent=1, default=str), flush=True)

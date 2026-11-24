"""BL08, etapa 2 — o caminho B NO PAPEL: o casador do Conformar (o do Premiere, `motor/prproj/originais.casar`) diz o
que faria com cada daily da rodada, sem NLE e sem Baselight. Compara com a verdade (`original_certo`).

    <conformar>/.venv/bin/python -m lab.bancadas.casamento_papel [--nfc]

`--nfc` = os caminhos dos dailies em NFC (como um projeto do Premiere/MC costuma gravar); sem ele, como o exFAT
do Mac lista (NFD). Saída: `saida/bancadas/casamento_papel/papel[-nfc].json` + o placar no terminal.
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata

from ..casamento import SAIDA
from .avid_baselight import CONFORMAR, RAIZ

TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "casamento_papel")


def _nfc(p: str) -> str:
    return unicodedata.normalize("NFC", p)


def classificar(d: dict, r: dict) -> tuple[str, str]:
    """(nota, porquê): certo · alerta (o editor fica sabendo) · errado (calado)."""
    certo = _nfc(os.path.join(SAIDA, d["original_certo"]))
    estado, original = r.get("estado"), r.get("original")
    if d["pegadinha"] == "P9":       # cópias idênticas: qualquer uma serve
        validos = {certo, _nfc(os.path.join(SAIDA, "ORIGINAIS/BACKUP/DIA01/C002/C001C002.mov"))}
    else:
        validos = {certo}
    if original and _nfc(original) in validos:
        return "certo", estado
    if original:
        return "errado", f"{estado}: escolheu {os.path.relpath(_nfc(original), SAIDA)}"
    return "alerta", f"{estado} ({len(r.get('candidatos') or [])} candidatos)"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    nfc = "--nfc" in argv
    sys.path.insert(0, os.path.join(CONFORMAR, "motor"))
    from prproj import originais
    with open(os.path.join(SAIDA, "verdade.json"), encoding="utf-8") as fh:
        verdade = json.load(fh)
    raizes = [os.path.join(SAIDA, "ORIGINAIS")]
    segs = []
    for d in verdade["dailies"]:
        p = os.path.join(SAIDA, d["arquivo"])
        segs.append({"media_ref": {"local_path": _nfc(p) if nfc else unicodedata.normalize("NFD", p)}})
    res = originais.casar(segs, raizes)
    linhas, placar = [], {"certo": 0, "alerta": 0, "errado": 0}
    for d, s in zip(verdade["dailies"], segs):
        r = res[s["media_ref"]["local_path"]]
        nota, porque = classificar(d, r)
        placar[nota] += 1
        linhas.append({"pegadinha": d["pegadinha"], "daily": d["arquivo"], "certo": d["original_certo"], "nota": nota,
                       "porque": porque, "estado": r.get("estado"),
                       "original": os.path.relpath(_nfc(r["original"]), SAIDA) if r.get("original") else None,
                       "candidatos": [os.path.relpath(_nfc(c), SAIDA) for c in r.get("candidatos") or []],
                       "recusados": [[os.path.relpath(_nfc(c), SAIDA), m] for c, m in r.get("recusados") or []],
                       "copias": [os.path.relpath(_nfc(c), SAIDA) for c in r.get("copias") or []]})
    os.makedirs(TRABALHO, exist_ok=True)
    with open(os.path.join(TRABALHO, f"papel{'-nfc' if nfc else ''}.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"nfc": nfc, "placar": placar, "linhas": linhas}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for x in linhas:
        print(f"{x['pegadinha']:4} {x['nota']:7} {_nfc(x['daily']):42} → {x['original'] or '-'}  [{x['porque']}]")
        for c, m in x["recusados"]:
            print(f"       recusado {c}: {m}")
    print("placar:", placar)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

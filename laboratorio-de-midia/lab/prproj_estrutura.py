"""A impressão digital de um .prproj: a versão do formato e a versão de cada CLASSE.

Para o downgrade (salvar para uma versão mais velha do Premiere), o que importa é o que muda entre as
versões: `<Project Version>` (o Premiere recusa o maior que o dele — banco, prproj/escrita.md §11b) e a
`Version` de cada elemento. O laboratório salva o MESMO caso em cada versão (2023, 2025, 2026) e compara.

    python3 -m lab.prproj_estrutura projeto.prproj               # imprime o resumo
    python3 -m lab.prproj_estrutura a.prproj b.prproj            # compara as duas
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from collections import Counter, defaultdict


def ler_xml(caminho: str) -> str:
    with open(caminho, "rb") as fh:
        dados = fh.read()
    if dados[:2] == b"\x1f\x8b":
        dados = gzip.decompress(dados)
    return dados.decode("utf-8", "replace")


def impressao(caminho: str) -> dict:
    xml = ler_xml(caminho)
    raiz = re.search(r"<PremiereData[^>]*Version=\"(\d+)\"", xml)
    projeto = re.search(r"<Project [^>]*ClassID=\"[^\"]+\"[^>]*Version=\"(\d+)\"", xml)
    versoes: dict[str, Counter] = defaultdict(Counter)
    # cada elemento de objeto: <Nome ObjectID|ObjectUID=… ClassID=… Version="N">
    for nome, versao in re.findall(r"<(\w+) Object(?:ID|UID)=\"[^\"]+\" ClassID=\"[^\"]+\" Version=\"(\d+)\"", xml):
        versoes[nome][versao] += 1
    # e TODO elemento com Version (os internos também mudam: <Track Version="3"> no 25.6.5, "4" no 26.0.2)
    internos: dict[str, Counter] = defaultdict(Counter)
    for nome, versao in re.findall(r"<(\w+)(?: [^>]*)? Version=\"(\d+)\"", xml):
        internos[nome][versao] += 1
    build = re.search(r"<MZ\.BuildVersion\.(?:Modified|Created)>([^<]+)<", xml)
    return {"arquivo": caminho, "bytes_xml": len(xml), "PremiereData": raiz.group(1) if raiz else None,
            "Project": projeto.group(1) if projeto else None, "build": build.group(1) if build else None,
            "classes": {k: dict(v) for k, v in sorted(versoes.items())},
            "elementos": {k: dict(v) for k, v in sorted(internos.items())}}


def comparar(a: dict, b: dict) -> dict:
    """As classes cuja versão difere, as que só existem num dos dois."""
    ca, cb = a["classes"], b["classes"]
    dif = {k: [sorted(ca[k]), sorted(cb[k])] for k in ca.keys() & cb.keys() if set(ca[k]) != set(cb[k])}
    ea, eb = a.get("elementos", {}), b.get("elementos", {})
    dif_el = {k: [sorted(ea[k]), sorted(eb[k])] for k in ea.keys() & eb.keys() if set(ea[k]) != set(eb[k])}
    return {"elementos_versao_difere": dict(sorted(dif_el.items())), "Project": [a["Project"], b["Project"]], "PremiereData": [a["PremiereData"], b["PremiereData"]],
            "build": [a["build"], b["build"]], "versao_difere": dict(sorted(dif.items())),
            "so_no_primeiro": sorted(ca.keys() - cb.keys()), "so_no_segundo": sorted(cb.keys() - ca.keys())}


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(json.dumps(impressao(sys.argv[1]), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(comparar(impressao(sys.argv[1]), impressao(sys.argv[2])), ensure_ascii=False, indent=1))

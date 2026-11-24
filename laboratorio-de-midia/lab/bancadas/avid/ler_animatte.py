"""Despeja a estrutura da sequência LAB_ANIMATTE de uma cópia da bin (pyavb): cada objeto com todas as propriedades,
para aprender como o AniMatte guarda a forma (2026-10-12). Uso:
`py lab/bancadas/avid/ler_animatte.py saida/bancadas/avid/animatte_01_poligono.avb [NOME] [TRILHA]` — TRILHA = o
índice da trilha de imagem a despejar (padrão 2, a V2).

⚠️ Nada de "já visto" por `id()`: o pyavb cria os objetos sob demanda e o Python reusa o `id` de um objeto já
recolhido — a primeira versão pulou a V2 inteira achando que era a V1."""
from __future__ import annotations

import sys

import avb

MAX = 14


def _e_objeto(v) -> bool:
    if type(v).__name__ in ("AVBRefList", "AVBObjectList"):
        return False
    return hasattr(v, "propertydefs") or hasattr(v, "property_data")


def valor(v, nivel: int, saida: list) -> str:
    if _e_objeto(v):
        despejar(v, nivel + 1, saida)
        return f"<{type(v).__name__}>"
    if type(v).__name__ in ("AVBRefList", "AVBObjectList") or (isinstance(v, (list, tuple)) and v and _e_objeto(v[0])):
        lst = list(v)
        for i, x in enumerate(lst):
            saida.append("  " * (nivel + 1) + f"[{i}]")
            if _e_objeto(x):
                despejar(x, nivel + 2, saida)
            else:
                saida.append("  " * (nivel + 2) + repr(x)[:400])
        return f"<lista de {len(lst)}>"
    if type(v).__name__ == "Attributes":
        return repr(dict(v))[:3000]
    if isinstance(v, (bytes, bytearray)):
        return f"bytes[{len(v)}] {bytes(v)[:96].hex()}"
    return repr(v)[:3000]


def despejar(o, nivel: int, saida: list) -> None:
    if nivel > MAX:
        saida.append("  " * nivel + "…")
        return
    saida.append("  " * nivel + f"{type(o).__name__}")
    if type(o).__name__ == "Attributes":
        saida.append("  " * (nivel + 1) + repr(dict(o))[:3000])
        return
    nomes = [p.name for p in getattr(o, "propertydefs", [])] or list(getattr(o, "property_data", {}).keys())
    for n in nomes:
        if n not in getattr(o, "property_data", {n: 1}):
            continue                          # propriedade que este objeto não tem
        v = getattr(o, n)
        if v is None:
            continue
        linha = "  " * (nivel + 1) + f"{n} = "
        pos = len(saida)
        saida.append(linha)
        saida[pos] = linha + valor(v, nivel + 1, saida)


def main() -> None:
    caminho = sys.argv[1]
    nome = sys.argv[2] if len(sys.argv) > 2 else "LAB_ANIMATTE"
    trilha = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    with avb.open(caminho) as f:
        for mob in f.content.mobs:
            if mob.name == nome and mob.mob_type == "CompositionMob":
                for t in mob.tracks:
                    if t.index == trilha and getattr(t.component, "media_kind", None) == "picture":
                        saida: list[str] = []
                        despejar(t, 0, saida)
                        print("\n".join(saida))


if __name__ == "__main__":
    main()

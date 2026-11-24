"""Acha o PILOTO (a ferramenta da família, `PROGRAMAS COM CLAUDE/piloto/`) subindo de pasta — nunca caminho fixo — e
o põe no caminho do Python. As mãos e o vigia da bancada moram lá desde 2026-10-12 (autor: "oficializar como
ferramenta"); `interface_win.py` e `vigia_windows.py` daqui ficaram como adaptadores com os nomes antigos."""
from __future__ import annotations

import os
import sys


def _achar() -> str:
    p = os.path.dirname(os.path.abspath(__file__))
    while True:
        alvo = os.path.join(p, "piloto")
        if os.path.isfile(os.path.join(alvo, "piloto", "__init__.py")):
            return alvo
        pai = os.path.dirname(p)
        if pai == p:
            raise RuntimeError("não achei a pasta `piloto` acima do laboratório (ver CATALOGO.md da família)")
        p = pai


PILOTO = _achar()
if PILOTO not in sys.path:
    sys.path.insert(0, PILOTO)

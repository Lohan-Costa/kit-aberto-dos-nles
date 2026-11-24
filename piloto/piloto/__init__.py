"""PILOTO — o Claude operando o computador: MÃOS (mouse e teclado), OLHOS (janelas e fotos), VIGIA (prazo, queda e
diálogos) e PONTES (a API de cada app). Ferramenta da família (autor, 2026-10-12): serve a qualquer app e a qualquer
sessão; nasceu na bancada do laboratório de mídia.

Uso (a partir de qualquer pasta da família — achar o piloto SUBINDO de pasta, nunca caminho fixo):

    import os, sys
    p = os.path.abspath(__file__)
    while not os.path.isdir(os.path.join(p, "piloto", "piloto")):
        p = os.path.dirname(p)
    sys.path.insert(0, os.path.join(p, "piloto"))
    from piloto import maos, olhos, vigia, apps, pontes

As regras de operação estão na skill `/piloto` (bancodedadosnles/skills/piloto/SKILL.md).
"""
from __future__ import annotations

import sys

from . import apps, pontes

if sys.platform == "win32":
    from . import maos_windows as maos
    from . import olhos_windows as olhos
    from . import vigia_windows as vigia
else:                                                       # macOS (2026-10-14)
    from . import maos_macos as maos
    from . import olhos_macos as olhos
    from . import vigia_macos as vigia

__all__ = ["maos", "olhos", "vigia", "apps", "pontes"]

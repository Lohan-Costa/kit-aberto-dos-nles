"""Mouse e teclado no WINDOWS para as bancadas — desde 2026-10-12 é o PILOTO da família
(`PROGRAMAS COM CLAUDE/piloto/piloto/maos_windows.py`); este módulo só mantém os nomes que as bancadas usam e liga o
freio do laboratório (`saida/PARAR`, além do F12 e do `PARAR` do piloto)."""
from __future__ import annotations

import os

from . import _piloto  # noqa: F401 — põe o piloto no caminho
from piloto.maos_windows import (ALT, BACKSPACE, BAIXO, CIMA, CTRL, DELETE, DIREITA, ENTER, ESC, ESQUERDA, SHIFT,  # noqa: F401
                                 TAB, VK_FREIO, Parado, arrastar, checar_freio, clicar, digitar, frente, mover,
                                 registrar_freio, relativo, retangulo, tecla, user32)

ARQUIVO_PARAR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "saida", "PARAR")
registrar_freio(ARQUIVO_PARAR)

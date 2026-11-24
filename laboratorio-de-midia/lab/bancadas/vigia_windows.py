"""Vigia de diálogos e cão de guarda no WINDOWS — desde 2026-10-12 é o PILOTO da família
(`PROGRAMAS COM CLAUDE/piloto/piloto/olhos_windows.py` e `vigia_windows.py`); este módulo só mantém os nomes e os
padrões antigos das bancadas (o Premiere como app padrão, o EVENTLOG do MC ligado sozinho)."""
from __future__ import annotations

from . import _piloto  # noqa: F401 — põe o piloto no caminho
from . import interface_win  # noqa: F401 — liga o freio do laboratório
from piloto import apps as _apps
from piloto import olhos_windows as _O
from piloto import vigia_windows as _V
from piloto.olhos_windows import fotografar, foto_da_tela, gdi32, user32  # noqa: F401
from piloto.vigia_windows import (PROGRESSO, DialogoAberto, Travado, agir, carregar_catalogo, esc,  # noqa: F401
                                  reconhecer, varrer)

PREMIERE = _apps.APPS["premiere"]["windows"]
RESOLVE = _apps.APPS["resolve"]["windows"]
AVID = _apps.APPS["avid"]["windows"]
EVENTLOG = _apps.APPS["avid"]["eventlog_windows"]


def pids_do_premiere(imagem: str = PREMIERE) -> list[int]:
    return _O.pids(imagem)


def dialogos(imagem: str = PREMIERE) -> list[dict]:
    return _O.dialogos(imagem)


def _janela_principal(imagem: str) -> int | None:
    return _O.janela_principal(imagem)


def ultimas_do_eventlog(n: int = 10) -> list[str]:
    return _V.ultimas_do_eventlog(EVENTLOG, n)


def vigiar(chamada, pasta_fotos: str, intervalo: float = 2.0, fechar_conhecidos: tuple = (), esperar: tuple = PROGRESSO,
           imagem: str = PREMIERE):
    return _V.vigiar(chamada, pasta_fotos, imagem, intervalo, fechar_conhecidos, esperar)


def com_prazo(acao, prazo: float, imagem: str, pasta_fotos: str, catalogo: list[dict] | None = None,
              pronto=None, intervalo: float = 2.0, ignorar: tuple = ("Settings",), saude=None):
    return _V.com_prazo(acao, prazo, imagem, pasta_fotos, catalogo, pronto, intervalo, ignorar,
                        eventlog=EVENTLOG if imagem == AVID else None, saude=saude)

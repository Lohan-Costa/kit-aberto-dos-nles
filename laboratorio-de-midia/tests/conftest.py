"""Os testes que leem dados de produção real ou resultados de bancada, na CÓPIA PÚBLICA (o kit aberto).

A cópia pública do laboratório não leva tudo de `resultados/` (nem os moldes binários de produção): ali, um teste que tropeça
num arquivo que falta DENTRO do laboratório PULA dizendo qual — em vez de falhar como se o kit estivesse quebrado.
Na máquina do autor (`resultados/` existe), o mesmo tropeço continua sendo FALHA: nada se esconde onde os dados estão.
"""
from __future__ import annotations

import os

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: A marca que o exportador do kit grava na cópia pública (`publicar/exportar_publico.py::montar_kit`); sem ela, a falta de
#: `resultados/` também conta (a cópia pública de antes de 2026-11-24 não levava a pasta).
COPIA_PUBLICA = (os.path.isfile(os.path.join(RAIZ, ".copia-publica"))
                 or not os.path.isdir(os.path.join(RAIZ, "resultados")))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    rel = resultado.get_result()
    if not COPIA_PUBLICA or call.excinfo is None or not call.excinfo.errisinstance(FileNotFoundError):
        return
    falta = str(getattr(call.excinfo.value, "filename", "") or "")
    if falta and os.path.abspath(falta).startswith(RAIZ + os.sep):
        rel.outcome = "skipped"
        rel.longrepr = (str(item.path), (item.location[1] or 0) + 1,
                        f"cópia pública: falta {os.path.relpath(falta, RAIZ)} (dado real ou resultado de bancada, fora do Git)")

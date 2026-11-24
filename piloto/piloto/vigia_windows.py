"""VIGIA no Windows — o cão de guarda e os diálogos. O comum aos dois sistemas (catálogo por foto, `varrer`, `agir`,
`com_prazo`) mora em `vigia_comum.py` e é reexportado aqui; abaixo, só a variante "por título" do Premiere no Windows.
"""
from __future__ import annotations

import os
import threading
import time

from . import olhos_windows as O
from .vigia_comum import (DialogoAberto, Travado, agir, carregar_catalogo, com_prazo, reconhecer,  # noqa: F401
                          ultimas_do_eventlog, varrer)


# ── a variante "por título" (Premiere: o modal `#32770` tem título útil) ───────────────────────────────────────────
#: diálogos de PROGRESSO: só esperam (fotografar uma vez e seguir). Título terminado em "*" casa pelo prefixo.
PROGRESSO = ("Open Project", "Save Project", "Encoding *")


def esc(hwnd: int) -> bool:
    """Fecha com Esc (o Cancelar); sem foco, WM_CLOSE direto. Devolve se a janela sumiu."""
    O.user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    O.user32.keybd_event(0x1B, 0, 0, 0)
    O.user32.keybd_event(0x1B, 0, 2, 0)
    time.sleep(1.5)
    if O.user32.IsWindow(hwnd):
        # ⚠️ de um processo em segundo plano o SetForegroundWindow falha e o Esc vai para outra janela
        O.user32.PostMessageW(hwnd, 0x0010, 0, 0)
        time.sleep(1.5)
    return not O.user32.IsWindow(hwnd)


def vigiar(chamada, pasta_fotos: str, imagem: str, intervalo: float = 2.0, fechar_conhecidos: tuple = (),
           esperar: tuple = PROGRESSO):
    """Roda `chamada()` numa thread; diálogo durante a espera é fotografado. Título em `fechar_conhecidos` = Esc e
    segue; de progresso = segue; outro = `DialogoAberto` (a chamada fica pendurada até alguém fechar)."""
    resultado, erro = {}, {}

    def rodar():
        try:
            resultado["v"] = chamada()
        except BaseException as e:      # noqa: BLE001
            erro["e"] = e
    t = threading.Thread(target=rodar, daemon=True)
    t.start()
    vistos = set()
    while t.is_alive():
        t.join(intervalo)
        for d in O.dialogos(imagem):
            foto_de = lambda: O.fotografar(d["hwnd"], os.path.join(pasta_fotos, time.strftime("%H%M%S") + f"_{d['hwnd']}.bmp"))  # noqa: E731
            if any(d["titulo"] == e or (e.endswith("*") and d["titulo"].startswith(e[:-1])) for e in esperar):
                if d["hwnd"] not in vistos:
                    vistos.add(d["hwnd"])
                    foto_de()
                continue
            foto = foto_de()
            if d["titulo"] in fechar_conhecidos and esc(d["hwnd"]):
                continue
            raise DialogoAberto(d["titulo"], foto)
    if "e" in erro:
        raise erro["e"]
    return resultado.get("v")

"""Sonda — entrada POR MENSAGEM à janela do app, sem SendInput (Windows).

A ideia vem do cua-driver (o que o Hermes Agent usa): em vez de mover o mouse do sistema, mandar
WM_LBUTTONDOWN/UP, WM_KEYDOWN… direto ao HWND, com o ponto em coordenada do CLIENTE da janela.
O ganho que interessa à casa (autor, 2026-11-04) não é trabalhar junto com o agente: é precisão,
menos clique físico e não depender de monitor, posição de janela e arranjo de telas.

Medido no MC 2024.6 (Win 11, 2026-11-04), com o MC COBERTO pelo terminal e o cursor parado:
  ✅ clique na barra de menus (janela nativa própria) abre o menu
  ✅ Esc / ↓ ↓ Enter mandados ao popup fecham / disparam o item
  ⛔ CLIQUE num item do popup NÃO dispara — o Qt decide dentro/fora pelo cursor REAL
  ✅ aba de bin, arrasto da barra de rolagem, duplo clique no ícone (sequência no Record)
  ✅ Ctrl+O, só com AttachThreadInput + SetKeyboardState (o Ctrl marcado); sem isso, ignorado
  ✅ WM_COMMAND IDCANCEL fecha o diálogo padrão (#32770)
  ✅ PrintWindow(hwnd, 2) fotografa a principal coberta
  ✅ menu sem coordenada: Alt+F (WM_SYSKEYDOWN) à BARRA, depois a letra sublinhada ao popup
  ✅ só com o MC ATIVO: régua da timeline (agulha), Mark IN; ⛔ régua num ponto FORA da tela
  ⛔ laço da timeline e arrasto bin → Source: lêem o botão FÍSICO — só SendInput
  Premiere 26.0: menu nativo por ID (WM_COMMAND), diálogo de arquivo por WM_SETTEXT, painéis
  nativos, timeline e laço por mensagem com ele coberto. Resolve 19.1.4: a UIA (sondas/uia.ps1).
  ⬜ Mac

    py sondas/entrada_por_mensagem.py janelas         # a árvore de janelas nativas do MC
    py sondas/entrada_por_mensagem.py menu File       # abre o menu pela barra (não mexe no mouse)
    py sondas/entrada_por_mensagem.py foto saida/x.bmp

⛔ Envia entrada ao Media Composer: com o autor olhando, F12 não vale aqui (não passa por `maos`).
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

sys.stdout.reconfigure(encoding="utf-8")
ctypes.windll.shcore.SetProcessDpiAwareness(2)
u = ctypes.windll.user32
k = ctypes.windll.kernel32
u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_ENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

WM_KEYDOWN, WM_KEYUP, WM_COMMAND = 0x100, 0x101, 0x111
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x200, 0x201, 0x202, 0x203
MK_LBUTTON, IDCANCEL, VK_CONTROL, VK_LCONTROL = 1, 2, 0x11, 0xA2


def _lp(x: int, y: int) -> int:
    return (y & 0xFFFF) << 16 | (x & 0xFFFF)


def classe(h: int) -> str:
    b = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(h, b, 256)
    return b.value


def titulo(h: int) -> str:
    b = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(h, b, 256)
    return b.value


def cliente(h: int, x: int, y: int) -> tuple[int, int]:
    """Ponto da TELA → ponto do cliente da janela (o que a mensagem leva)."""
    pt = wintypes.POINT(x, y)
    u.ScreenToClient(h, ctypes.byref(pt))
    return pt.x, pt.y


def clicar(h: int, x: int, y: int, duplo: bool = False) -> None:
    """Clique no ponto do CLIENTE. ⛔ Não serve para item de popup (menu): ali o Qt olha o cursor real."""
    u.PostMessageW(h, WM_MOUSEMOVE, 0, _lp(x, y))
    time.sleep(0.05)
    u.PostMessageW(h, WM_LBUTTONDOWN, MK_LBUTTON, _lp(x, y))
    u.PostMessageW(h, WM_LBUTTONUP, 0, _lp(x, y))
    if duplo:
        time.sleep(0.05)
        u.PostMessageW(h, WM_LBUTTONDBLCLK, MK_LBUTTON, _lp(x, y))
        u.PostMessageW(h, WM_LBUTTONUP, 0, _lp(x, y))


def arrastar(h: int, x0: int, y0: int, x1: int, y1: int, passos: int = 20) -> None:
    """Arrasto INTERNO do Qt (barra, régua). Arrasto OLE (entre janelas) não medido."""
    u.PostMessageW(h, WM_MOUSEMOVE, 0, _lp(x0, y0))
    u.PostMessageW(h, WM_LBUTTONDOWN, MK_LBUTTON, _lp(x0, y0))
    for i in range(1, passos + 1):
        u.PostMessageW(h, WM_MOUSEMOVE, MK_LBUTTON, _lp(x0 + (x1 - x0) * i // passos, y0 + (y1 - y0) * i // passos))
        time.sleep(0.02)
    u.PostMessageW(h, WM_LBUTTONUP, 0, _lp(x1, y1))


def tecla(h: int, vk: int, ctrl: bool = False) -> None:
    """Tecla por mensagem. Com Ctrl, o estado de teclado da thread do app é marcado durante o gesto."""
    alvo = u.GetWindowThreadProcessId(h, None)
    eu = k.GetCurrentThreadId()
    est = (ctypes.c_ubyte * 256)()
    if ctrl:
        u.AttachThreadInput(eu, alvo, True)
        u.GetKeyboardState(est)
        est[VK_CONTROL] = est[VK_LCONTROL] = 0x80
        u.SetKeyboardState(est)
        u.PostMessageW(h, WM_KEYDOWN, VK_CONTROL, 1)
    try:
        u.PostMessageW(h, WM_KEYDOWN, vk, 1)
        time.sleep(0.05)
        u.PostMessageW(h, WM_KEYUP, vk, 0xC0000001)
        time.sleep(0.3)
    finally:
        if ctrl:
            est[VK_CONTROL] = est[VK_LCONTROL] = 0
            u.SetKeyboardState(est)
            u.PostMessageW(h, WM_KEYUP, VK_CONTROL, 0xC0000001)
            u.AttachThreadInput(eu, alvo, False)


def mais_funda(top: int, x_tela: int, y_tela: int) -> tuple[int, int, int]:
    """A janela-filha MAIS FUNDA sob o ponto (Premiere: o painel), e o ponto no cliente dela."""
    u.ChildWindowFromPointEx.restype = wintypes.HWND
    u.ChildWindowFromPointEx.argtypes = [wintypes.HWND, wintypes.POINT, ctypes.c_uint]
    h = top
    while True:
        pt = wintypes.POINT(x_tela, y_tela)
        u.ScreenToClient(h, ctypes.byref(pt))
        c = u.ChildWindowFromPointEx(h, pt, 1 | 2 | 4)
        if not c or c == h:
            return h, pt.x, pt.y
        h = c


def comando(hwnd: int, ident: int) -> None:
    """Item de menu NATIVO (Premiere) pelo id lido de GetMenu — sem tela, sem foco."""
    u.PostMessageW(hwnd, WM_COMMAND, ident, 0)


def caminho_no_dialogo(dialogo: int, caminho: str) -> None:
    """Diálogo de arquivo do Windows: o caminho no campo (combo 1148) e OK — sem teclado (ABNT2)."""
    u.GetDlgItem.restype = wintypes.HWND
    combo = u.GetDlgItem(dialogo, 1148)
    filhos: list[int] = []
    cb = _ENUM(lambda h, _: filhos.append(h) or True)
    u.EnumChildWindows(combo, cb, 0)
    edit = next(h for h in filhos if classe(h) == "Edit")
    envia = ctypes.windll.user32.SendMessageW
    envia.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPCWSTR]
    envia(edit, 0x0C, 0, caminho)
    u.PostMessageW(dialogo, WM_COMMAND, 1, 0)


def cancelar(dialogo: int) -> None:
    """Diálogo padrão do Windows (#32770): o Cancel sem procurar o botão."""
    u.PostMessageW(dialogo, WM_COMMAND, IDCANCEL, 0)


def _janelas_do_mc() -> list[int]:
    sys.path.insert(0, __file__.rsplit("sondas", 1)[0])
    from piloto import olhos
    pid = olhos.pids("AvidMediaComposer.exe")[0]
    out: list[int] = []

    def cada(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            out.append(h)
        return True
    cb = _ENUM(cada)
    u.EnumWindows(cb, 0)
    return out


def _principal() -> int:
    return next(h for h in _janelas_do_mc() if titulo(h).startswith("Avid Media Composer"))


def _barra(principal: int) -> int:
    filhos: list[int] = []
    cb = _ENUM(lambda h, _: filhos.append(h) or True)
    u.EnumChildWindows(principal, cb, 0)
    return next(h for h in filhos if classe(h).startswith("Qt") and titulo(h) == "AvidMediaComposer")


def main() -> int:
    acao = sys.argv[1] if len(sys.argv) > 1 else "janelas"
    p = _principal()
    if acao == "janelas":
        filhos: list[int] = []
        cb = _ENUM(lambda h, _: filhos.append(h) or True)
        u.EnumChildWindows(p, cb, 0)
        print(p, classe(p), titulo(p))
        for h in filhos:
            print("  ", h, classe(h), titulo(h))
    elif acao == "menu":
        # A posição do menu na barra se lê numa foto; "File" é o primeiro (x≈16 no 2024.6 a 125 %).
        clicar(_barra(p), 16, 11)
    elif acao == "foto":
        sys.path.insert(0, __file__.rsplit("sondas", 1)[0])
        from piloto import olhos
        print(olhos.fotografar(p, sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

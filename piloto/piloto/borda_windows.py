"""O processo da BORDA no Windows: a faixa colorida em volta de cada monitor e o ouvido do toque FÍSICO.

Roda sozinho (`pythonw -m piloto.borda_windows`), subido pelo piloto na primeira ação (`maos_windows._borda`), e sai
quando não há o que mostrar. Só biblioteca padrão (`ctypes` em user32/gdi32). O combinado com o piloto, os modos e
as cores estão em `borda_comum.py`.

Escolhas, cada uma por um motivo:
- ⛔ As janelas DEIXAM O CLIQUE PASSAR (`WS_EX_LAYERED | WS_EX_TRANSPARENT`) e NÃO PEGAM O FOCO
  (`WS_EX_NOACTIVATE`, mostradas com `SW_SHOWNOACTIVATE`): o piloto confere a janela da frente antes de digitar, e uma
  borda que pegasse o foco o faria recusar tudo — ou, pior, digitar nela.
- ⭐ FORA DAS FOTOS (`SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`, Windows 10 2004+): a borda é para o autor,
  não para o reconhecimento por foto, que compara a janela pelo pixel. `--na-foto` desliga isso, para conferir a
  borda por uma foto da tela.
- ⭐ Quatro faixas finas por monitor, e não uma janela do tamanho da tela com o meio transparente: nada cobre o meio
  da tela nem para o compositor.
- ⭐ O toque: ganchos de baixo nível de teclado e mouse (`WH_KEYBOARD_LL`, `WH_MOUSE_LL`). O sistema marca o que veio
  de `SendInput` (`LLKHF_INJECTED` / `LLMHF_INJECTED`): o piloto não se pausa sozinho com o próprio clique.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

from . import borda_comum as B

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)        # pixels REAIS, como as mãos do piloto
except (AttributeError, OSError):
    pass

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                     wintypes.LPARAM)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                   wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, MONITORENUMPROC, wintypes.LPARAM]
gdi32.CreateFontW.restype = wintypes.HFONT
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

WS_POPUP = 0x80000000
WS_EX = 0x00000008 | 0x00000080 | 0x08000000 | 0x00080000 | 0x00000020  # TOPMOST TOOLWINDOW NOACTIVATE LAYERED TRANSPARENT
WM_PAINT, WM_ERASEBKGND, WM_TIMER, WM_DESTROY = 0x000F, 0x0014, 0x0113, 0x0002
SW_HIDE, SW_SHOWNOACTIVATE = 0, 4
HWND_TOPMOST = wintypes.HWND(-1)
SWP_TOPO = 0x0001 | 0x0002 | 0x0010                                 # NOSIZE NOMOVE NOACTIVATE
WDA_EXCLUDEFROMCAPTURE = 0x11
WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
LLKHF_INJECTED, LLKHF_LOWER_IL_INJECTED = 0x10, 0x02
LLMHF_INJECTED, LLMHF_LOWER_IL_INJECTED = 0x01, 0x02
ERROR_ALREADY_EXISTS = 183
VK_F12 = 0x7B

ESPESSURA = 6         # px reais; a 125 % ainda se vê, sem cobrir a barra de título de janela maximizada
ETIQUETA = (560, 28)  # a plaquinha no topo do monitor principal
TIQUE_MS = 100


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", wintypes.HDC), ("fErase", wintypes.BOOL), ("rcPaint", wintypes.RECT),
                ("fRestore", wintypes.BOOL), ("fIncUpdate", wintypes.BOOL), ("rgbReserved", ctypes.c_byte * 32)]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HICON)]


class KBDLL(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MSLL(ctypes.Structure):
    _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


def _cor(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    return r | (g << 8) | (b << 16)


class Borda:
    def __init__(self, na_foto: bool = False):
        self.na_foto = na_foto
        self.modo: str | None = None
        self.texto = ""
        self.janelas: list[int] = []
        self.etiqueta: int | None = None
        self.monitores: list[tuple[int, int, int, int]] = []
        self.toque = (0.0, "")              # (quando, tipo) — o último toque FÍSICO, escrito em disco no tique
        self.toque_gravado = 0.0
        self.tecla = 0.0
        self.freio = False                  # F12 físico ouvido aqui; gravado no tique (o gancho tem de voltar rápido)
        self.freio_gravado = False
        self.sem_nada_desde: float | None = None
        self.tiques = 0
        self.inst = kernel32.GetModuleHandleW(None)
        self.fonte = gdi32.CreateFontW(-17, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 5, 0, "Segoe UI")
        # ⛔ as referências aos callbacks ficam vivas no objeto: coletadas pelo Python, o Windows chamaria memória solta
        self._wndproc = WNDPROC(self._janela)
        self._kb = HOOKPROC(self._teclado)
        self._ms = HOOKPROC(self._mouse)
        wc = WNDCLASSEXW(ctypes.sizeof(WNDCLASSEXW), 0, self._wndproc, 0, 0, self.inst, None,
                         user32.LoadCursorW(None, ctypes.c_void_p(32512)), None, None, "CicloPilotoBorda", None)
        if not user32.RegisterClassExW(ctypes.byref(wc)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.ganchos = [user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb, self.inst, 0),
                        user32.SetWindowsHookExW(WH_MOUSE_LL, self._ms, self.inst, 0)]

    # ── o toque ──────────────────────────────────────────────────────────────────────────────────────────────────
    def _teclado(self, n, wp, lp):
        if n >= 0:
            k = ctypes.cast(lp, ctypes.POINTER(KBDLL)).contents
            if not k.flags & (LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED):
                if k.vkCode == VK_F12 and wp in (0x0100, 0x0104):      # WM_KEYDOWN / WM_SYSKEYDOWN
                    self.freio = True
                elif k.vkCode == B.TECLA_DE_PAUSA and self.modo in ("ativo", "pausado"):
                    self.toque = (time.time(), "espaco")            # pausa, e NÃO conta como tecla na digitação
                    return 1                                          # engolida: não chega ao programa da frente
                else:
                    self.toque = (time.time(), "tecla")
                    self.tecla = self.toque[0]
        return user32.CallNextHookEx(None, n, wp, lp)

    def _mouse(self, n, wp, lp):
        if n >= 0:
            m = ctypes.cast(lp, ctypes.POINTER(MSLL)).contents
            if not m.flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED):
                self.toque = (time.time(), "mouse")
        return user32.CallNextHookEx(None, n, wp, lp)

    # ── as janelas ───────────────────────────────────────────────────────────────────────────────────────────────
    def _ler_monitores(self) -> list[tuple[int, int, int, int]]:
        achados: list[tuple[int, int, int, int]] = []

        def cada(_h, _dc, r, _l):
            achados.append((r.contents.left, r.contents.top, r.contents.right, r.contents.bottom))
            return True
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cada), 0)
        return achados

    def _criar(self, x, y, w, h) -> int:
        hwnd = user32.CreateWindowExW(WS_EX, "CicloPilotoBorda", "Piloto", WS_POPUP, x, y, w, h, None, None,
                                      self.inst, None)
        user32.SetLayeredWindowAttributes(hwnd, 0, 235, 2)          # LWA_ALPHA
        if not self.na_foto:
            user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        return hwnd

    def _montar(self) -> None:
        for h in self.janelas:
            user32.DestroyWindow(h)
        self.janelas, self.etiqueta = [], None
        e = ESPESSURA
        for (l, t, r, b) in self.monitores:
            for (x, y, w, h) in ((l, t, r - l, e), (l, b - e, r - l, e), (l, t, e, b - t), (r - e, t, e, b - t)):
                self.janelas.append(self._criar(x, y, w, h))
        principal = next((m for m in self.monitores if m[0] <= 0 < m[2] and m[1] <= 0 < m[3]), self.monitores[0])
        l, t, r, _b = principal
        w, h = ETIQUETA
        self.etiqueta = self._criar(l + (r - l - w) // 2, t + e, w, h)
        self.janelas.append(self.etiqueta)

    def _mostrar(self, modo: str | None, texto: str) -> None:
        mudou = (modo, texto) != (self.modo, self.texto)
        self.modo, self.texto = modo, texto
        for h in self.janelas:
            if modo is None:
                user32.ShowWindow(h, SW_HIDE)
            else:
                user32.ShowWindow(h, SW_SHOWNOACTIVATE)
                if mudou:
                    user32.InvalidateRect(h, None, True)

    def _janela(self, hwnd, msg, wp, lp):
        if msg == WM_ERASEBKGND:
            return 1
        if msg == WM_PAINT:
            ps = PAINTSTRUCT()
            dc = user32.BeginPaint(hwnd, ctypes.byref(ps))
            r = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(r))
            pincel = gdi32.CreateSolidBrush(_cor(B.CORES.get(self.modo or "ativo")))
            user32.FillRect(dc, ctypes.byref(r), pincel)
            gdi32.DeleteObject(pincel)
            if hwnd == self.etiqueta and self.texto:
                antiga = gdi32.SelectObject(dc, self.fonte)
                gdi32.SetBkMode(dc, 1)                                  # TRANSPARENT
                gdi32.SetTextColor(dc, 0x000000 if self.modo == "pausado" else 0xFFFFFF)
                user32.DrawTextW(dc, self.texto, -1, ctypes.byref(r), 0x1 | 0x4 | 0x20)  # CENTER VCENTER SINGLELINE
                gdi32.SelectObject(dc, antiga)
            user32.EndPaint(hwnd, ctypes.byref(ps))
            return 0
        if msg == WM_TIMER:
            self._tique()
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    # ── o relógio ────────────────────────────────────────────────────────────────────────────────────────────────
    def _tique(self) -> None:
        agora = time.time()
        self.tiques += 1
        B.bater_ponto(agora)
        quando, tipo = self.toque
        if quando > self.toque_gravado:
            B.gravar_toque(quando, tipo, self.tecla)
            self.toque_gravado = quando
        if self.tiques % 10 == 0:                       # monitor ligado/desligado, e outra janela "sempre no topo"
            mon = self._ler_monitores()
            if mon and mon != self.monitores:
                self.monitores = mon
                self._montar()
                self.modo = None                        # força redesenhar no modo atual
            for h in self.janelas:
                user32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0, SWP_TOPO)
        if self.freio and not self.freio_gravado:
            B.gravar_freio(agora)
            self.freio_gravado = True
        est = B.ler_estado()
        modo = B.o_que_mostrar(est, agora, self.toque[0], self.freio)
        if modo == "pausado":
            texto = B.texto_da_pausa(agora, self.toque[0])
        elif modo == est.get("modo"):
            texto = est.get("texto") or ""
        else:                               # a borda mudou de cor sozinha (toque ou F12): o texto é o do modo
            texto = B.TEXTOS["parado"] + "  ·  F12" if modo == "parado" else B.TEXTOS.get(modo or "", "")
        self._mostrar(modo, texto if modo else "")
        if self.freio and modo is None:     # o vermelho já ficou o seu tempo; sem piloto para ver, sai
            user32.PostQuitMessage(0)
            return
        if modo is None:
            self.sem_nada_desde = self.sem_nada_desde or agora
            if agora - self.sem_nada_desde > 1.0:
                user32.PostQuitMessage(0)
        else:
            self.sem_nada_desde = None

    def rodar(self) -> None:
        self.monitores = self._ler_monitores()
        self._montar()
        user32.SetTimer(self.janelas[0], 1, TIQUE_MS, None)
        self._tique()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        for g in self.ganchos:
            user32.UnhookWindowsHookEx(g)
        for h in self.janelas:
            user32.DestroyWindow(h)
        B.bater_ponto(0.0)                # saiu: o piloto não pode achar que ela está de pé e deixar de subi-la


def main() -> int:
    # uma borda só por sessão do Windows: dois piloto subindo juntos não podem abrir duas
    kernel32.CreateMutexW(None, False, "Local\\CicloPilotoBorda")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return 0
    Borda(na_foto="--na-foto" in sys.argv).rodar()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""MÃOS no Windows — mouse e teclado sintéticos (`SendInput`, só biblioteca padrão).

Nasceu na bancada do laboratório (2026-10-11/12: Effect Editor e AniMatte do Media Composer pilotados sem o autor) e
virou ferramenta da família a pedido do autor (2026-10-12). Mesmas funções em `maos_macos.py`.

Regras (as que custaram caro):
- ⛔ Tecla e clique vão para quem está na FRENTE: `frente(hwnd)` traz a janela e CONFERE; quem chama não age se ela
  não veio — o pior modo de falha é agir no programa errado calado.
- ⛔ Nunca a RODA do mouse sobre um controle deslizante do Qt: ela muda o VALOR (Effect Editor do MC, 2026-10-11).
  Rolar lista = clicar na faixa da barra de rolagem.
- Coordenadas em pixels REAIS da área de trabalho virtual (todas as telas). Com a escala do Windows (125 % no
  notebook) um processo sem ciência de DPI erra o lugar: este módulo se declara ciente por monitor ao ser importado.
- O FREIO (autor, 2026-10-11): F12 — que o piloto nunca usa — ou um arquivo `PARAR` (o do piloto e os registrados
  por quem usa). Checado em TODO clique e TODA tecla.
- ⭐ A BORDA e a PAUSA (autor, 2026-10-30; `borda_comum.py`): na primeira ação sobe uma faixa colorida em volta das
  telas — azul agindo, âmbar pausado, vermelho parou. Mexer no mouse/teclado de verdade PAUSA (o piloto espera
  `QUIETO_S` de sossego e segue); F12 continua sendo PARAR. `devolver_ao_terminal()` apaga a borda.
  `PILOTO_SEM_BORDA=1` desliga as duas coisas.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

from . import borda_comum as borda

user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x0002, 0x0004
MOUSEEVENTF_MOVE, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, MOUSEEVENTF_ABSOLUTE = 0x0001, 0x0002, 0x0004, 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000


class _MI(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _KI(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _U(ctypes.Union):
    # ⚠️ a união INTEIRA (com o MOUSEINPUT): só com o KEYBDINPUT o SendInput devolve 0 calado (banco, matriz F)
    _fields_ = [("mi", _MI), ("ki", _KI)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


# ── o freio ──────────────────────────────────────────────────────────────────────────────────────────────────────
VK_FREIO = 0x7B                                                        # F12
ARQUIVOS_PARAR = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PARAR")]


class Parado(KeyboardInterrupt):
    """O autor pediu para parar. Deriva de KeyboardInterrupt, NÃO de Exception: os laços que registram um erro e
    seguem (`except Exception`) não o engolem."""


# ⚠️ O bit 0x0001 do GetAsyncKeyState ("apertada desde a última consulta") vem SUJO na 1ª consulta de um processo novo:
# um F12 apertado minutos antes (o autor, para parar outra rodada) disparou o freio de uma rodada nova (2026-10-12).
# Consultar uma vez ao carregar zera o resíduo; daí em diante só conta o F12 apertado DEPOIS.
user32.GetAsyncKeyState(VK_FREIO)


def registrar_freio(caminho: str) -> None:
    """Mais um arquivo que, existindo, para o piloto (ex.: o `saida/PARAR` do laboratório)."""
    if caminho not in ARQUIVOS_PARAR:
        ARQUIVOS_PARAR.append(caminho)


def checar_freio() -> None:
    _freio()
    _borda("ativo")                       # o vigia checa o freio enquanto espera: esperar também é estar agindo


# ── a borda e a pausa ────────────────────────────────────────────────────────────────────────────────────────────
SEM_BORDA = os.environ.get("PILOTO_SEM_BORDA") == "1"
_b = {"modo": None, "escrito": 0.0, "subida": 0.0, "arrastando": False, "devolvendo": False,
      "digitando": 0.0}                                   # desde quando digita (0 = não está digitando)


def _subir_borda() -> None:
    if borda.borda_viva() or time.time() - _b["subida"] < 3.0:
        return
    _b["subida"] = time.time()
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    cmd = [pyw if os.path.isfile(pyw) else sys.executable, "-m", "piloto.borda_windows"]
    base = 0x00000008 | 0x00000200 | 0x08000000           # DETACHED_PROCESS, NEW_PROCESS_GROUP, NO_WINDOW
    # ⚠️ fora do JOB de quem chamou, quando ele deixa: a ferramenta que roda o comando pode matar a árvore ao terminar,
    # e a borda tem de ficar de pé ENTRE os comandos de uma tarefa (o prazo `TTL_S` a apaga se o piloto sumir)
    for flags in (base | 0x01000000, base):               # + CREATE_BREAKAWAY_FROM_JOB
        try:
            subprocess.Popen(cmd, cwd=borda.RAIZ, creationflags=flags, close_fds=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            continue


def _borda(modo: str, texto: str | None = None) -> None:
    """Escreve o modo para a borda (e a sobe, se preciso). Mesmo modo: no máximo a cada `RENOVAR_S`."""
    if SEM_BORDA:
        return
    agora = time.time()
    if modo == _b["modo"] and texto is None and agora - _b["escrito"] < borda.RENOVAR_S:
        return
    try:
        borda.escrever_estado(modo, texto, agora)
    except OSError:
        return                            # a borda é aviso: disco ocupado não pode derrubar a operação
    _b["modo"], _b["escrito"] = modo, agora
    if modo in ("ativo", "pausado"):
        _subir_borda()


def _parar(texto: str) -> None:
    _borda("parado", texto)


def ligar_borda(texto: str | None = None) -> None:
    """Acende a borda antes da primeira ação (ela também acende sozinha no primeiro clique ou tecla)."""
    _borda("ativo", texto)


def desligar_borda() -> None:
    """Fim da tarefa: a borda some e o F12 deixa de valer. `devolver_ao_terminal()` já chama."""
    _borda("livre")


def _esperar_quieto() -> None:
    """A PAUSA pelo toque: se o autor mexeu de verdade há menos de `QUIETO_S`, segura até ele sossegar.

    ⛔ Três casos viram PARADA, não pausa: o toque no meio de um ARRASTO (o botão está apertado e o ponteiro é dele);
    a janela da frente ter mudado durante a pausa (o piloto agiria noutro programa); e a pausa passar de
    `PAUSA_MAX_S` (ele está usando a máquina)."""
    if SEM_BORDA or _b["devolvendo"] or not borda.borda_viva():
        return
    if time.time() - borda.ultimo_toque() >= borda.QUIETO_S:
        return
    if _b["arrastando"]:
        _parar("PAROU  ·  você mexeu no meio de um arrasto")
        raise Parado("o autor mexeu no meio de um arrasto")
    if _b["digitando"] and borda.ultima_tecla() >= _b["digitando"]:
        _parar("PAROU  ·  você digitou no meio da digitação do piloto")
        raise Parado("o autor apertou uma tecla no meio de uma digitação: o texto pode ter uma letra dele")
    frente0 = user32.GetForegroundWindow()
    inicio = time.time()
    _borda("pausado")
    while time.time() - borda.ultimo_toque() < borda.QUIETO_S:
        _freio()
        if _b["digitando"] and borda.ultima_tecla() >= _b["digitando"]:
            _parar("PAROU  ·  você digitou no meio da digitação do piloto")
            raise Parado("o autor apertou uma tecla no meio de uma digitação: o texto pode ter uma letra dele")
        if time.time() - inicio > borda.PAUSA_MAX_S:
            _parar("PAROU  ·  você está usando a máquina")
            raise Parado(f"o autor usou a máquina por mais de {borda.PAUSA_MAX_S:.0f} s")
        time.sleep(0.1)
    if user32.GetForegroundWindow() != frente0:
        _parar("PAROU  ·  a janela da frente mudou na pausa")
        raise Parado("a janela da frente mudou durante a pausa")
    _borda("ativo")


def _freio() -> None:
    if _b["devolvendo"]:
        return
    if (user32.GetAsyncKeyState(VK_FREIO) & 0x8001 or any(os.path.exists(p) for p in ARQUIVOS_PARAR)
            or (not SEM_BORDA and borda.freio_apertado())):
        _parar("PAROU  ·  F12 ou arquivo PARAR")
        raise Parado("parado pelo autor (F12 ou arquivo PARAR)")


def _enviar(*entradas: _INPUT) -> None:
    _freio()
    _esperar_quieto()
    _borda("ativo")
    arr = (_INPUT * len(entradas))(*entradas)
    user32.SendInput(len(entradas), arr, ctypes.sizeof(_INPUT))


# ── janela na frente ─────────────────────────────────────────────────────────────────────────────────────────────
def frente(hwnd: int, tentativas: int = 5) -> bool:
    """Traz a janela para a frente e devolve se ela FICOU. Um processo em segundo plano não pode roubar o foco
    (proteção do Windows): um ALT solto antes libera o SetForegroundWindow."""
    for _ in range(tentativas):
        tecla(0x12)
        # ⛔ SW_RESTORE numa janela MAXIMIZADA a solta (2026-10-12: o MC saía de (−9, −9) para (5, 19) a cada frente e o
        # clique na paleta caía uma linha acima). Restaurar só a minimizada; a outra só aparece.
        user32.ShowWindow(hwnd, 9 if user32.IsIconic(hwnd) else 5)   # SW_RESTORE / SW_SHOW
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        if user32.GetForegroundWindow() == hwnd:
            return True
    return False


class _PE32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


def _ancestrais() -> list[int]:
    """Os pids de cima deste processo: pai, avô… (o Claude, o PowerShell, o terminal)."""
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k.CreateToolhelp32Snapshot(0x2, 0)                     # TH32CS_SNAPPROCESS
    pais, e = {}, _PE32()
    e.dwSize = ctypes.sizeof(_PE32)
    ok = k.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        pais[e.th32ProcessID] = e.th32ParentProcessID
        ok = k.Process32NextW(snap, ctypes.byref(e))
    k.CloseHandle(snap)
    fora, p = [], pais.get(os.getpid())
    while p and p not in fora and len(fora) < 20:
        fora.append(p)
        p = pais.get(p)
    return fora


def _janela_do_terminal() -> int | None:
    """A janela do TERMINAL desta sessão do Claude (onde o autor acompanha). Medido 2026-10-29, Windows 11: o PowerShell
    da sessão roda no Windows Terminal, e o console dele é uma `PseudoConsoleWindow` cujo DONO é a janela do Windows
    Terminal (`CASCADIA_HOSTING_WINDOW_CLASS`, título = o da sessão); no console clássico a própria janela do console.
    Achada pelo console de um processo de CIMA (o nosso, sob o Bash/PowerShell da ferramenta, é oculto ou nenhum)."""
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetConsoleWindow.restype = wintypes.HWND
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]

    def dono(h):
        if not h:
            return None
        r = user32.GetAncestor(h, 3) or h                              # GA_ROOTOWNER
        return r if user32.IsWindowVisible(r) else None

    proprio = dono(k.GetConsoleWindow())
    if proprio:
        return proprio
    for pid in _ancestrais():
        k.FreeConsole()
        if not k.AttachConsole(pid):
            continue
        h = dono(k.GetConsoleWindow())
        k.FreeConsole()
        if h:
            return h
    return None


def devolver_ao_terminal() -> bool:
    """FIM de toda tarefa pilotada (autor, 2026-10-29): o foco volta ao terminal da sessão — o autor acompanha por ele e,
    com o NLE em foco, o que ele digita vira atalho do NLE. Devolve se o terminal ficou na frente."""
    # ⛔ a borda se apaga POR ÚLTIMO: o `frente` usa as mãos (um Alt), e toda mão acende a borda de novo — desligada
    # antes, ela ficava azul depois do fim da tarefa (medido na 1ª rodada, 2026-10-30)
    # ⛔ e SEM freio: devolver o terminal é devolver o controle ao autor, o gesto que o F12 pede. Com o F12 guardado
    # pela borda, o Alt do `frente` levantava `Parado` e o terminal ficava atrás (medido, 2ª rodada no Resolve)
    _b["devolvendo"] = True
    try:
        h = _janela_do_terminal()
        if not h:
            return False
        return frente(h)
    finally:
        _b["devolvendo"] = False
        if _b["modo"] != "parado":       # o vermelho de um freio fica os seus segundos na tela
            desligar_borda()


def retangulo(hwnd: int) -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def relativo(hwnd: int, x: int, y: int) -> tuple[int, int]:
    """De uma posição DENTRO da janela (o que se mede na foto dela) para a tela."""
    esq, topo, _d, _b = retangulo(hwnd)
    return esq + x, topo + y


# ── mouse ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _ponto(x: float, y: float, bandeira: int) -> _INPUT:
    # coordenadas na ÁREA DE TRABALHO VIRTUAL (todas as telas): com o mapa só do principal, um clique numa janela da
    # outra tela cairia fora (o autor ligou um 2º monitor, 2026-10-11)
    vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    w, h = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
    ax, ay = int((x - vx) * 65535 / max(w - 1, 1)), int((y - vy) * 65535 / max(h - 1, 1))
    return _INPUT(INPUT_MOUSE, _U(mi=_MI(ax, ay, 0, bandeira | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 0, 0)))


def mover(x: int, y: int) -> None:
    _enviar(_ponto(x, y, MOUSEEVENTF_MOVE))


def clicar(x: int, y: int, duplo: bool = False) -> None:
    _enviar(_ponto(x, y, MOUSEEVENTF_MOVE))
    time.sleep(0.08)
    _enviar(_ponto(x, y, MOUSEEVENTF_LEFTDOWN), _ponto(x, y, MOUSEEVENTF_LEFTUP))
    if duplo:
        time.sleep(0.08)
        _enviar(_ponto(x, y, MOUSEEVENTF_LEFTDOWN), _ponto(x, y, MOUSEEVENTF_LEFTUP))


def arrastar(x0: int, y0: int, x1: int, y1: int, passos: int = 20, pausa: float = 0.02,
             modificadores: tuple[int, ...] = ()) -> None:
    """Botão esquerdo apertado em (x0, y0), andando em `passos` até (x1, y1), solto lá — desenhar uma forma no monitor,
    mover um objeto (AniMatte, 2026-10-12: o retângulo arrastado caiu a < 1 px do previsto).

    `modificadores` (CTRL, SHIFT, ALT) ficam apertados o gesto INTEIRO — o LAÇO da timeline do MC é arrastar com
    `(ALT,)` (sem ele o arrasto PEGA o clipe/filler de baixo, 2026-10-28; medido no Mac; ✅ Windows, MC 2024.6, 2026-11-04 — e SÓ por SendInput: por mensagem o laço não pega)."""
    _enviar(_ponto(x0, y0, MOUSEEVENTF_MOVE))
    time.sleep(0.1)
    _b["arrastando"] = True
    try:
        if modificadores:
            _enviar(*[_INPUT(INPUT_KEYBOARD, _U(ki=_KI(m, 0, 0, 0, 0))) for m in modificadores])
            time.sleep(0.05)
        _enviar(_ponto(x0, y0, MOUSEEVENTF_LEFTDOWN))
        time.sleep(0.1)
        for k in range(1, passos + 1):
            _enviar(_ponto(x0 + (x1 - x0) * k / passos, y0 + (y1 - y0) * k / passos, MOUSEEVENTF_MOVE))
            time.sleep(pausa)
        time.sleep(0.1)
    finally:
        _b["arrastando"] = False
        # soltar SEMPRE, inclusive parado: o botão preso seria um arrasto sem fim nas mãos do autor
        # (antes ia pelo `_enviar`, que checa o freio: o F12 no meio do arrasto deixava botão e modificadores presos)
        soltar = [_ponto(x1, y1, MOUSEEVENTF_LEFTUP)]
        soltar += [_INPUT(INPUT_KEYBOARD, _U(ki=_KI(m, 0, KEYEVENTF_KEYUP, 0, 0))) for m in reversed(modificadores)]
        arr = (_INPUT * len(soltar))(*soltar)
        user32.SendInput(len(soltar), arr, ctypes.sizeof(_INPUT))


def clicar_direito(x: int, y: int) -> None:
    """Botão DIREITO em (x, y): o menu de contexto (o do painel web do MC tem Reload — 2026-10-12)."""
    checar_freio()
    _enviar(_ponto(x, y, MOUSEEVENTF_MOVE))
    time.sleep(0.08)
    _enviar(_ponto(x, y, 0x0008), _ponto(x, y, 0x0010))         # RIGHTDOWN, RIGHTUP


def rolar(x: int, y: int, entalhes: int) -> None:
    """A RODA do mouse em (x, y): `entalhes` > 0 desce, < 0 sobe (120 por entalhe). ⛔ Só sobre página web ou lista —
    NUNCA sobre controle deslizante do Qt (muda o valor)."""
    checar_freio()
    _enviar(_ponto(x, y, MOUSEEVENTF_MOVE))
    time.sleep(0.08)
    roda = _ponto(x, y, 0x0800)                                   # MOUSEEVENTF_WHEEL
    roda.u.mi.mouseData = ctypes.c_uint32(-120 * entalhes).value
    _enviar(roda)


# ── teclado ──────────────────────────────────────────────────────────────────────────────────────────────────────
def tecla(vk: int, *modificadores: int) -> None:
    """Uma tecla (código virtual), com modificadores (CTRL, SHIFT, ALT) apertados antes e soltos depois."""
    seq = [_INPUT(INPUT_KEYBOARD, _U(ki=_KI(m, 0, 0, 0, 0))) for m in modificadores]
    seq += [_INPUT(INPUT_KEYBOARD, _U(ki=_KI(vk, 0, 0, 0, 0))), _INPUT(INPUT_KEYBOARD, _U(ki=_KI(vk, 0, KEYEVENTF_KEYUP, 0, 0)))]
    seq += [_INPUT(INPUT_KEYBOARD, _U(ki=_KI(m, 0, KEYEVENTF_KEYUP, 0, 0))) for m in reversed(modificadores)]
    _enviar(*seq)


def digitar(texto: str) -> None:
    """Texto por Unicode (não depende do layout do teclado do Windows)."""
    _b["digitando"] = time.time()
    try:
        _digitar(texto)
    finally:
        _b["digitando"] = 0.0


def _digitar(texto: str) -> None:
    for ch in texto:
        c = ord(ch)
        _enviar(_INPUT(INPUT_KEYBOARD, _U(ki=_KI(0, c, KEYEVENTF_UNICODE, 0, 0))),
                _INPUT(INPUT_KEYBOARD, _U(ki=_KI(0, c, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0))))
        time.sleep(0.01)


class ForaDeFoco(RuntimeError):
    """A janela que devia receber o teclado não é a da frente: nada foi digitado."""


def digitar_em(hwnd: int, texto: str = "", *teclas: int, intervalo: float = 0.01) -> None:
    """Texto (e depois teclas soltas, ex. ENTER) SÓ se `hwnd` for a janela da frente — conferido antes de cada envio.

    ⛔ 2026-10-13: um diálogo de arquivo demorou a abrir, o caminho digitado caiu no MC como ATALHOS (T = Mark Clip,
    Z = Lift…) e levantou a timeline inteira; o autor desfez à mão. Digitar "no que estiver na frente" é proibido:
    ache o diálogo pela janela (título/classe), `frente(hwnd)` e digite por aqui.
    """
    def conferir():
        checar_freio()
        if user32.GetForegroundWindow() != hwnd:
            raise ForaDeFoco(f"a janela da frente não é {hwnd:#x}: nada digitado")
    conferir()
    _b["digitando"] = time.time()
    try:
        _digitar_em(texto, conferir, intervalo)
    finally:
        _b["digitando"] = 0.0
    for vk in teclas:
        conferir()
        tecla(vk)


def _digitar_em(texto: str, conferir, intervalo: float) -> None:
    for ch in texto:
        conferir()
        c = ord(ch)
        _enviar(_INPUT(INPUT_KEYBOARD, _U(ki=_KI(0, c, KEYEVENTF_UNICODE, 0, 0))),
                _INPUT(INPUT_KEYBOARD, _U(ki=_KI(0, c, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0))))
        time.sleep(intervalo)


ENTER, ESC, TAB, BACKSPACE, DELETE = 0x0D, 0x1B, 0x09, 0x08, 0x2E
ESQUERDA, CIMA, DIREITA, BAIXO = 0x25, 0x26, 0x27, 0x28
CTRL, SHIFT, ALT = 0x11, 0x10, 0x12


# ── POR MENSAGEM: agir sem o mouse do sistema (spike 2026-11-04/05, o cua-driver/Hermes medido) ──────────────────────
# O ponto vai em coordenada do CLIENTE da janela (independe de monitor, posição e arranjo de telas) e o cursor não se
# move. ⛔ Tudo passa pelo MESMO portão do `_enviar` (F12, PARAR, pausa pelo toque, borda): agir sem mexer no mouse não
# pode ser agir sem freio. Só por SendInput (medido): laço da timeline do MC, arrasto entre painéis/apps, clique em item
# de menu Qt aberto (use setas/Enter ou a letra sublinhada). Matriz da família, seção F.
WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_SYSKEYDOWN, WM_SYSKEYUP, WM_SYSCHAR = 0x100, 0x101, 0x102, 0x104, 0x105, 0x106
WM_COMMAND, WM_INITMENUPOPUP, WM_SETTEXT = 0x111, 0x117, 0x0C
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK, WM_MOUSEWHEEL = 0x200, 0x201, 0x202, 0x203, 0x20A
MK_LBUTTON, MK_CONTROL = 0x1, 0x8
_u = ctypes.WinDLL("user32", use_last_error=True)          # cópia própria: argtypes daqui não mexem no `user32` de cima
_u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_u.SendMessageW.restype = ctypes.c_ssize_t
_u.ChildWindowFromPointEx.restype = wintypes.HWND
_u.ChildWindowFromPointEx.argtypes = [wintypes.HWND, wintypes.POINT, ctypes.c_uint]
_u.GetMenu.restype = wintypes.HMENU
_u.GetMenu.argtypes = [wintypes.HWND]
_u.GetSubMenu.restype = wintypes.HMENU
_u.GetSubMenu.argtypes = [wintypes.HMENU, ctypes.c_int]
_u.GetMenuItemID.restype = ctypes.c_uint
_u.GetMenuItemID.argtypes = [wintypes.HMENU, ctypes.c_int]
_u.GetMenuItemCount.argtypes = [wintypes.HMENU]
_u.GetMenuStringW.argtypes = [wintypes.HMENU, ctypes.c_uint, wintypes.LPWSTR, ctypes.c_int, ctypes.c_uint]
_u.GetMenuState.argtypes = [wintypes.HMENU, ctypes.c_uint, ctypes.c_uint]
_u.GetDlgItem.restype = wintypes.HWND
_u.GetDlgItem.argtypes = [wintypes.HWND, ctypes.c_int]


class ItemDesabilitado(RuntimeError):
    """O item de menu está cinza AGORA. ⛔ O `WM_COMMAND` pode furar a regra (Premiere 26.0: Merge Clips cinza com um
    clipe só, e o id abriu o diálogo assim mesmo — 2026-11-05): por isso o estado é conferido antes, e recusa-se."""


def _portao() -> None:
    _freio()
    _esperar_quieto()
    _borda("ativo")


def _lp(x: int, y: int) -> int:
    return (y & 0xFFFF) << 16 | (x & 0xFFFF)


def filha_sob(top: int, x_tela: int, y_tela: int) -> tuple[int, int, int]:
    """A janela-filha MAIS FUNDA sob o ponto de tela (no Premiere, o painel) e o ponto no cliente dela."""
    h = top
    while True:
        pt = wintypes.POINT(x_tela, y_tela)
        _u.ScreenToClient(h, ctypes.byref(pt))
        c = _u.ChildWindowFromPointEx(h, pt, 1 | 2 | 4)              # pula invisível, desabilitada e transparente
        if not c or c == h:
            return h, pt.x, pt.y
        h = c


class _modificadores:
    """Ctrl/Alt/Shift marcados no estado de teclado da thread do app durante o gesto (`AttachThreadInput` +
    `SetKeyboardState`): por mensagem, sem isso o app lê o modificador SOLTO e a letra chega sozinha (no MC, atalho)."""
    def __init__(self, hwnd: int, mods: tuple[int, ...]):
        self.hwnd, self.mods = hwnd, mods

    def __enter__(self):
        if self.mods:
            self.alvo = _u.GetWindowThreadProcessId(self.hwnd, None)
            self.eu = ctypes.windll.kernel32.GetCurrentThreadId()
            _u.AttachThreadInput(self.eu, self.alvo, True)
            self.est = (ctypes.c_ubyte * 256)()
            _u.GetKeyboardState(self.est)
            for m in self.mods:
                self.est[m] = 0x80
            _u.SetKeyboardState(self.est)
        return self

    def __exit__(self, *_):
        if self.mods:
            for m in self.mods:
                self.est[m] = 0
            _u.SetKeyboardState(self.est)
            _u.AttachThreadInput(self.eu, self.alvo, False)


def msg_clicar(top: int, x_tela: int, y_tela: int, duplo: bool = False, ctrl: bool = False) -> None:
    """Clique por MENSAGEM no ponto de tela (medido na foto da janela). Não move o cursor.
    ⚠️ A timeline do MC só aceita com o MC ATIVO e o ponto DENTRO da tela."""
    _portao()
    h, x, y = filha_sob(top, x_tela, y_tela)
    mk = MK_CONTROL if ctrl else 0
    with _modificadores(h, (CTRL,) if ctrl else ()):
        _u.PostMessageW(h, WM_MOUSEMOVE, mk, _lp(x, y))
        time.sleep(0.05)
        _u.PostMessageW(h, WM_LBUTTONDOWN, MK_LBUTTON | mk, _lp(x, y))
        _u.PostMessageW(h, WM_LBUTTONUP, mk, _lp(x, y))
        if duplo:
            time.sleep(0.05)
            _u.PostMessageW(h, WM_LBUTTONDBLCLK, MK_LBUTTON | mk, _lp(x, y))
            _u.PostMessageW(h, WM_LBUTTONUP, mk, _lp(x, y))
        time.sleep(0.3)


def msg_rolar(top: int, x_tela: int, y_tela: int, entalhes: int) -> None:
    """A roda por mensagem (`entalhes` > 0 desce). ⛔ Sobre controle deslizante Qt a roda muda o VALOR."""
    _portao()
    h, _, _ = filha_sob(top, x_tela, y_tela)
    passo = -120 if entalhes > 0 else 120
    for _ in range(abs(entalhes)):
        _u.PostMessageW(h, WM_MOUSEWHEEL, (passo & 0xFFFF) << 16, _lp(x_tela, y_tela))   # a roda leva ponto de TELA
        time.sleep(0.12)


def msg_tecla(hwnd: int, vk: int, *modificadores: int, char: str | None = None) -> None:
    """Tecla por mensagem para `hwnd`. Com ALT vira `WM_SYSKEYDOWN` (MC: Alt+F à BARRA de menus abre o File)."""
    _portao()
    sis = ALT in modificadores
    down, up = (WM_SYSKEYDOWN, WM_SYSKEYUP) if sis else (WM_KEYDOWN, WM_KEYUP)
    ctx = 0x20000000 if sis else 0
    with _modificadores(hwnd, modificadores):
        for m in modificadores:
            _u.PostMessageW(hwnd, down, m, 1 | ctx)
        _u.PostMessageW(hwnd, down, vk, 1 | ctx)
        if char:
            _u.PostMessageW(hwnd, WM_SYSCHAR if sis else WM_CHAR, ord(char), 1 | ctx)
        time.sleep(0.05)
        _u.PostMessageW(hwnd, up, vk, 0xC0000001 | ctx)
        for m in reversed(modificadores):
            _u.PostMessageW(hwnd, up, m, 0xC0000001 | ctx)
        time.sleep(0.3)


def _nome_do_item(menu: int, i: int) -> str:
    b = ctypes.create_unicode_buffer(256)
    _u.GetMenuStringW(menu, i, b, 256, 0x400)
    return b.value.split("\t")[0].replace("&", "").rstrip(".…").strip().lower()


def item_de_menu(hwnd: int, caminho: str) -> tuple[int, int, int]:
    """(menu, posição, id) do item `"File > New > Sequence From Clip"` no menu NATIVO da janela (Premiere no Windows).
    Pelo NOME, na hora: 25 de 337 ids mudaram entre o 23.2 e o 26.0 (os centrais não) — nunca gravar o número.
    ⚠️ O nome é do idioma da interface (só o inglês medido)."""
    partes = [p.strip().lower().rstrip(".…").strip() for p in caminho.split(">")]
    menu = _u.GetMenu(hwnd)
    if not menu:
        raise LookupError("esta janela não tem menu nativo (MC e Resolve: Qt)")
    for k, parte in enumerate(partes):
        for i in range(_u.GetMenuItemCount(menu)):
            if _nome_do_item(menu, i) == parte:
                if k == len(partes) - 1:
                    return menu, i, _u.GetMenuItemID(menu, i)
                sub = _u.GetSubMenu(menu, i)
                _u.SendMessageW(hwnd, WM_INITMENUPOPUP, sub, i)         # o app atualiza o estado dos itens
                menu = sub
                break
        else:
            raise LookupError(f"não achei '{parte}' em '{caminho}'")
    raise LookupError(caminho)


def comando_menu(hwnd: int, caminho: str) -> int:
    """Executa um item do menu NATIVO pelo caminho, sem tela e sem foco. Confere o estado REAL antes; item cinza
    levanta `ItemDesabilitado` em vez de mandar o id. Devolve o id mandado."""
    _portao()
    menu, i, ident = item_de_menu(hwnd, caminho)
    if _u.GetMenuState(menu, i, 0x400) & 0x3:                           # MF_GRAYED | MF_DISABLED
        raise ItemDesabilitado(f"'{caminho}' está cinza agora")
    _u.PostMessageW(hwnd, WM_COMMAND, ident, 0)
    return ident


def caminho_no_dialogo(dialogo: int, caminho: str) -> None:
    """Diálogo de ARQUIVO do Windows: o caminho direto no campo (combo 1148) e OK — sem teclado (o ABNT2 trocava
    caracteres). Vários arquivos: cada caminho entre aspas, separados por espaço (o Premiere deixa os importados
    SELECIONADOS). ⭐ Seletor de PASTA (`FOS_PICKFOLDERS`): o campo "Folder:" é um Edit SOLTO de id 1152, sem o combo
    1148 (medido 2026-11-18, Win 11) — tratado aqui também."""
    _portao()
    combo = _u.GetDlgItem(dialogo, 1148)
    edit = 0
    if combo:
        filhos: list[int] = []
        cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(lambda h, _: filhos.append(h) or True)
        _u.EnumChildWindows(combo, cb, 0)
        buf = ctypes.create_unicode_buffer(32)
        edit = next((h for h in filhos if _u.GetClassNameW(h, buf, 32) and buf.value == "Edit"), 0)
    edit = edit or _u.GetDlgItem(dialogo, 1152)
    if not edit:
        raise RuntimeError("o diálogo não tem o campo de caminho (nem o combo 1148, nem o Edit 1152)")
    envia = ctypes.WinDLL("user32").SendMessageW
    envia.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPCWSTR]
    envia(edit, WM_SETTEXT, 0, caminho)
    _u.PostMessageW(dialogo, WM_COMMAND, 1, 0)

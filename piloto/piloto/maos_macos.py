"""MÃOS no macOS — mouse e teclado sintéticos (Quartz `CGEvent` por `ctypes`, só biblioteca padrão). As mesmas funções
de `maos_windows.py`; o "hwnd" é o número da janela do macOS (ver `olhos_macos`).

Medido no Mac do autor (macOS 15.6.1, 2026-10-14):
- Exige a permissão de ACESSIBILIDADE do processo responsável (o Terminal que abriu o Claude): sem ela o `CGEventPost`
  some calado. `olhos.permissoes()` confere.
- Coordenadas em PONTOS da tela (origem no canto de cima à esquerda da tela principal). A foto sai em PIXELS: numa tela
  Retina divida por `olhos.escala()` — `relativo()` e `da_foto()` já dividem. No monitor 1920×1080 do autor, 1 × 1.
- Teclas: CÓDIGOS DE TECLA do Mac (não os VK do Windows) — use as constantes (ENTER, ESC, CMD…) ou uma letra
  (`tecla("s", CMD)`), que valem nos dois sistemas. ⚠️ No Mac o Ctrl do Windows costuma ser o CMD.
- O FREIO: F12 (o piloto nunca a usa), o arquivo `PARAR`, e — só no Mac — o AUTOR MEXER NO MOUSE: se o cursor não
  está onde o piloto o deixou, alguém mexeu → para (`FREIO_MOUSE = False` desliga). O F12 é vigiado por uma thread a
  cada 50 ms (o Mac não tem o "apertada desde a última consulta" do Windows).
- ⛔ Nunca a RODA do mouse sobre controle deslizante (Qt: muda o VALOR) — igual ao Windows.
"""
from __future__ import annotations

import ctypes
import os
import threading
import time

from . import olhos_macos as _O

_cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
_vp = ctypes.c_void_p


class _Pt(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _sig(nome, res, *args):
    f = getattr(_cg, nome)
    f.restype, f.argtypes = res, list(args)
    return f


_CGEventCreateMouseEvent = _sig("CGEventCreateMouseEvent", _vp, _vp, ctypes.c_uint32, _Pt, ctypes.c_uint32)
_CGEventCreateKeyboardEvent = _sig("CGEventCreateKeyboardEvent", _vp, _vp, ctypes.c_uint16, ctypes.c_bool)
_CGEventCreateScrollWheelEvent2 = _sig("CGEventCreateScrollWheelEvent2", _vp, _vp, ctypes.c_uint32, ctypes.c_uint32,
                                       ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)
_CGEventKeyboardSetUnicodeString = _sig("CGEventKeyboardSetUnicodeString", None, _vp, ctypes.c_ulong,
                                        ctypes.POINTER(ctypes.c_uint16))
_CGEventSetFlags = _sig("CGEventSetFlags", None, _vp, ctypes.c_uint64)
_CGEventSetIntegerValueField = _sig("CGEventSetIntegerValueField", None, _vp, ctypes.c_uint32, ctypes.c_int64)
_CGEventPost = _sig("CGEventPost", None, ctypes.c_uint32, _vp)
_CGEventCreate = _sig("CGEventCreate", _vp, _vp)
_CGEventGetLocation = _sig("CGEventGetLocation", _Pt, _vp)
_CGEventSourceKeyState = _sig("CGEventSourceKeyState", ctypes.c_bool, ctypes.c_int32, ctypes.c_uint16)
_CFRelease = _O._CFRelease

HID = 0                                                     # kCGHIDEventTap: como se viesse do teclado/mouse físico
MOVER, ESQ_DESCE, ESQ_SOBE, DIR_DESCE, DIR_SOBE, ESQ_ARRASTA = 5, 1, 2, 3, 4, 6

# ── teclas (códigos do Mac, teclado ANSI/ABNT: as letras estão no mesmo lugar) ────────────────────────────────────
ENTER, ESC, TAB, BACKSPACE, DELETE, ESPACO = 36, 53, 48, 51, 117, 49
ESQUERDA, DIREITA, BAIXO, CIMA = 123, 124, 125, 126
CMD, SHIFT, ALT, CTRL = 55, 56, 58, 59                      # ALT = Option
F12 = 111
_FLAG = {CMD: 0x100000, SHIFT: 0x20000, ALT: 0x80000, CTRL: 0x40000}
LETRAS = {"a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13,
          "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25,
          "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38,
          "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50}


def codigo(tecla_: int | str) -> int:
    """Código de tecla do Mac a partir de uma constante ou de UM caractere (`"s"`)."""
    return LETRAS[tecla_.lower()] if isinstance(tecla_, str) else tecla_


# ── o freio ──────────────────────────────────────────────────────────────────────────────────────────────────────
ARQUIVOS_PARAR = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PARAR")]
FREIO_MOUSE = True
_TOLERANCIA_MOUSE = 8                                       # pontos: o cursor não volta exato em toda tela/app
_estado = {"f12": False, "onde": None}


class Parado(KeyboardInterrupt):
    """O autor pediu para parar. Deriva de KeyboardInterrupt, NÃO de Exception: os laços que registram um erro e
    seguem (`except Exception`) não o engolem."""


def _vigiar_f12():
    while True:
        if _CGEventSourceKeyState(1, F12):                  # kCGEventSourceStateHIDSystemState: o teclado físico
            _estado["f12"] = True
        time.sleep(0.05)


threading.Thread(target=_vigiar_f12, daemon=True, name="freio-F12").start()


def registrar_freio(caminho: str) -> None:
    """Mais um arquivo que, existindo, para o piloto (ex.: o `saida/PARAR` do laboratório)."""
    if caminho not in ARQUIVOS_PARAR:
        ARQUIVOS_PARAR.append(caminho)


def cursor() -> tuple[float, float]:
    ev = _CGEventCreate(None)
    try:
        p = _CGEventGetLocation(ev)
        return p.x, p.y
    finally:
        _CFRelease(ev)


def checar_freio() -> None:
    if _estado["f12"] or any(os.path.exists(p) for p in ARQUIVOS_PARAR):
        raise Parado("parado pelo autor (F12 ou arquivo PARAR)")
    if FREIO_MOUSE and _estado["onde"] is not None:
        x, y = cursor()
        ox, oy = _estado["onde"]
        if abs(x - ox) > _TOLERANCIA_MOUSE or abs(y - oy) > _TOLERANCIA_MOUSE:
            _estado["onde"] = None
            raise Parado(f"o autor mexeu no mouse (o piloto o deixou em {ox:.0f},{oy:.0f}; está em {x:.0f},{y:.0f})")


def ligar_borda(texto: str | None = None) -> None:
    """⬜ PENDENTE no Mac: a borda colorida e a pausa pelo toque existem só no Windows (`borda_windows.py`, 2026-10-30).
    Aqui o toque no mouse já PARA (`FREIO_MOUSE`), não pausa. Mesmo nome para o código de quem usa não mudar."""


def desligar_borda() -> None:
    """⬜ PENDENTE no Mac (ver `ligar_borda`)."""


def soltar_freio() -> None:
    """Depois de um `Parado`, para operar de novo na mesma sessão: zera o F12 e esquece onde o cursor estava."""
    _estado["f12"], _estado["onde"] = False, None


def _post(ev) -> None:
    try:
        _CGEventPost(HID, ev)
    finally:
        _CFRelease(ev)


# ── janela na frente ─────────────────────────────────────────────────────────────────────────────────────────────
def frente(hwnd: int, tentativas: int = 5) -> bool:
    """Traz a janela (e o app dela) para a frente e devolve se ela FICOU com o teclado."""
    for _ in range(tentativas):
        _O.trazer(hwnd)
        time.sleep(0.3)
        if _O.janela_da_frente() == hwnd:
            return True
    return False


def devolver_ao_terminal() -> bool:
    """FIM de toda tarefa pilotada (autor, 2026-10-29): o app do TERMINAL desta sessão volta para a frente — o autor
    acompanha por ele e, com o NLE em foco, o que ele digita vira atalho do NLE. Sobe pelos pais deste processo e
    ativa o primeiro que é app de janela (Terminal, iTerm2…). ⏳ `pendente`: só medido no Windows."""
    import subprocess
    pid, vistos = os.getppid(), 0
    while pid > 1 and vistos < 20:
        vistos += 1
        r = subprocess.run(["osascript", "-e", 'tell application "System Events" to set frontmost of (first process '
                            f'whose unix id is {pid} and background only is false) to true'],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True
        pai = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        pid = int(pai) if pai.isdigit() else 0
    return False


def retangulo(hwnd: int) -> tuple[int, int, int, int]:
    return _O.retangulo(hwnd)


def da_foto(x: float, y: float) -> tuple[float, float]:
    """De pixels de uma foto da TELA para pontos (Retina ÷ 2)."""
    e = _O.escala()
    return x / e, y / e


def relativo(hwnd: int, x: float, y: float) -> tuple[float, float]:
    """De uma posição DENTRO da janela, medida em pixels na foto dela, para pontos da tela."""
    esq, topo, _d, _b = retangulo(hwnd)
    e = _O.escala()
    return esq + x / e, topo + y / e


# ── mouse ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _mouse(tipo: int, x: float, y: float, botao: int = 0, cliques: int = 1, bandeiras: int = 0) -> None:
    ev = _CGEventCreateMouseEvent(None, tipo, _Pt(x, y), botao)
    if cliques > 1:
        _CGEventSetIntegerValueField(ev, 1, cliques)        # kCGMouseEventClickState: o duplo clique
    if bandeiras:
        _CGEventSetFlags(ev, bandeiras)                     # o modificador do gesto (o Option do laço do MC)
    _post(ev)
    _estado["onde"] = (x, y)


def mover(x: float, y: float) -> None:
    checar_freio()
    _mouse(MOVER, x, y)


def clicar(x: float, y: float, duplo: bool = False) -> None:
    mover(x, y)
    time.sleep(0.08)
    checar_freio()
    _mouse(ESQ_DESCE, x, y)
    _mouse(ESQ_SOBE, x, y)
    if duplo:
        time.sleep(0.08)
        _mouse(ESQ_DESCE, x, y, cliques=2)
        _mouse(ESQ_SOBE, x, y, cliques=2)


def clicar_direito(x: float, y: float) -> None:
    mover(x, y)
    time.sleep(0.08)
    checar_freio()
    _mouse(DIR_DESCE, x, y, botao=1)
    _mouse(DIR_SOBE, x, y, botao=1)


def arrastar(x0: float, y0: float, x1: float, y1: float, passos: int = 20, pausa: float = 0.02,
             modificadores: tuple[int, ...] = ()) -> None:
    """Botão esquerdo apertado em (x0, y0), andando em `passos` até (x1, y1), solto lá. No Mac o movimento com o botão
    apertado é ARRASTO (evento próprio), não "mover".

    `modificadores` (CMD, SHIFT, ALT, CTRL) ficam apertados o gesto INTEIRO e vão em cada evento do mouse — o LAÇO da
    timeline do MC é arrastar com `(ALT,)` (Option; sem ele o arrasto PEGA o clipe/filler de baixo, 2026-10-28). Soltos
    no fim mesmo se o freio parar no meio."""
    bandeiras = 0
    for m in modificadores:
        bandeiras |= _FLAG[m]
    mover(x0, y0)
    time.sleep(0.1)
    checar_freio()
    apertadas = 0
    try:
        for m in modificadores:
            apertadas |= _FLAG[m]
            _tecla_crua(m, True, apertadas)
        time.sleep(0.05)
        _mouse(ESQ_DESCE, x0, y0, bandeiras=bandeiras)
        time.sleep(0.1)
        for k in range(1, passos + 1):
            checar_freio()
            _mouse(ESQ_ARRASTA, x0 + (x1 - x0) * k / passos, y0 + (y1 - y0) * k / passos, bandeiras=bandeiras)
            time.sleep(pausa)
        time.sleep(0.1)
    finally:
        _mouse(ESQ_SOBE, *_estado["onde"], bandeiras=bandeiras)
        for m in reversed(modificadores):
            apertadas &= ~_FLAG[m]
            _tecla_crua(m, False, apertadas)


def rolar(x: float, y: float, entalhes: int) -> None:
    """A RODA em (x, y): `entalhes` > 0 desce, < 0 sobe. ⛔ Só sobre página ou lista — NUNCA sobre controle
    deslizante do Qt (muda o valor)."""
    mover(x, y)
    time.sleep(0.08)
    checar_freio()
    _post(_CGEventCreateScrollWheelEvent2(None, 1, 1, -entalhes, 0, 0))   # 1 = linhas; positivo sobe no Mac


# ── teclado ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _tecla_crua(cod: int, desce: bool, bandeiras: int = 0) -> None:
    ev = _CGEventCreateKeyboardEvent(None, cod, desce)
    if bandeiras:
        _CGEventSetFlags(ev, bandeiras)
    _post(ev)


def tecla(t: int | str, *modificadores: int) -> None:
    """Uma tecla (constante ou caractere), com modificadores (CMD, SHIFT, ALT, CTRL) apertados antes e soltos depois."""
    checar_freio()
    cod = codigo(t)
    bandeiras = 0
    for m in modificadores:
        bandeiras |= _FLAG[m]
        _tecla_crua(m, True, bandeiras)
    _tecla_crua(cod, True, bandeiras)
    _tecla_crua(cod, False, bandeiras)
    for m in reversed(modificadores):
        bandeiras &= ~_FLAG[m]
        _tecla_crua(m, False, bandeiras)


def _caractere(ch: str) -> None:
    unidades = ch.encode("utf-16-le")
    n = len(unidades) // 2
    buf = (ctypes.c_uint16 * n).from_buffer_copy(unidades)
    for desce in (True, False):
        ev = _CGEventCreateKeyboardEvent(None, 0, desce)
        _CGEventKeyboardSetUnicodeString(ev, n, buf)
        _post(ev)


def digitar(texto: str) -> None:
    """Texto por Unicode (não depende do layout do teclado)."""
    for ch in texto:
        checar_freio()
        _caractere(ch)
        time.sleep(0.01)


class ForaDeFoco(RuntimeError):
    """A janela que devia receber o teclado não é a da frente: nada foi digitado."""


def digitar_em(hwnd: int, texto: str = "", *teclas: int | str, intervalo: float = 0.01) -> None:
    """Texto (e depois teclas soltas, ex. ENTER) SÓ se `hwnd` for a janela da frente — conferido antes de cada envio.
    ⛔ No Windows (2026-10-13) um caminho digitado com o diálogo atrasado caiu no MC como atalhos e levantou a
    timeline: digitar "no que estiver na frente" é proibido."""
    def conferir():
        checar_freio()
        if _O.janela_da_frente() != hwnd:
            raise ForaDeFoco(f"a janela da frente não é {hwnd}: nada digitado")
    conferir()
    for ch in texto:
        conferir()
        _caractere(ch)
        time.sleep(intervalo)
    for t in teclas:
        conferir()
        tecla(t)


# ── POR MENSAGEM (Windows medido em 2026-11-04/05; matriz, seção F) ── no Mac: PENDENTE ──────────────────────────────
# Candidatos: CGEventPostToPid (já usado para o Esc no Resolve) e o menu pelo NOME via System Events (já usado). Até
# medir, estas funções existem para o código ser o mesmo nos dois sistemas e dizem por que não agem.
class ItemDesabilitado(RuntimeError):
    pass


def _pendente(*_a, **_k):
    raise NotImplementedError("entrada por mensagem ainda não medida no Mac (matriz, seção F) — use as mãos de sempre")


def filha_sob(*a, **k):
    _pendente()


def msg_clicar(*a, **k):
    _pendente()


def msg_rolar(*a, **k):
    _pendente()


def msg_tecla(*a, **k):
    _pendente()


def item_de_menu(*a, **k):
    _pendente()


def comando_menu(*a, **k):
    _pendente()


def caminho_no_dialogo(*a, **k):
    _pendente()

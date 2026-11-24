"""OLHOS no macOS — processos, janelas e fotos. As mesmas funções de `olhos_windows.py`; só biblioteca padrão
(`ctypes` sobre CoreGraphics/ApplicationServices + o `screencapture` do sistema).

O "hwnd" daqui é o NÚMERO DA JANELA do macOS (CGWindowID): é ele que o `screencapture -l` fotografa e o que
`janelas()` devolve. Medido no Mac do autor (macOS 15.6.1, 2026-10-14) — ver a matriz de plataforma, seção F:
- Permissões: o processo RESPONSÁVEL (o Terminal que abriu o Claude) precisa de **Acessibilidade** (ler janelas e
  diálogos, mandar teclas) e **Gravação de Tela** (foto e título das janelas de outro app). Sem a segunda, o
  `kCGWindowName` vem vazio e a foto sai só com o papel de parede — `permissoes()` diz o que falta.
- Coordenadas: o macOS trabalha em PONTOS, a foto sai em PIXELS. Numa tela Retina pixel = 2 × ponto; no monitor
  1920×1080 do autor, 1 × 1. `escala()` dá o fator; `relativo()` (nas mãos) já divide.
- Diálogo: a acessibilidade diz o SUBROLE da janela (AXDialog, AXSystemDialog) e se ela é modal — é o equivalente da
  "janela com dono" do Windows. Janela travada: a acessibilidade não responde dentro do prazo (`respondendo`).
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import time

_cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
_cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
_ax = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")

_vp, _u32, _i64, _bool = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int64, ctypes.c_bool
UTF8 = 0x08000100
EXT_FOTO = ".png"


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class CGSize(ctypes.Structure):
    _fields_ = [("w", ctypes.c_double), ("h", ctypes.c_double)]


class CGRect(ctypes.Structure):
    _fields_ = [("origem", CGPoint), ("tam", CGSize)]


def _sig(lib, nome, res, *args):
    f = getattr(lib, nome)
    f.restype, f.argtypes = res, list(args)
    return f


_CFArrayGetCount = _sig(_cf, "CFArrayGetCount", ctypes.c_long, _vp)
_CFArrayGetValueAtIndex = _sig(_cf, "CFArrayGetValueAtIndex", _vp, _vp, ctypes.c_long)
_CFDictionaryGetValue = _sig(_cf, "CFDictionaryGetValue", _vp, _vp, _vp)
_CFNumberGetValue = _sig(_cf, "CFNumberGetValue", _bool, _vp, ctypes.c_int, _vp)
_CFStringGetLength = _sig(_cf, "CFStringGetLength", ctypes.c_long, _vp)
_CFStringGetCString = _sig(_cf, "CFStringGetCString", _bool, _vp, ctypes.c_char_p, ctypes.c_long, _u32)
_CFStringCreateWithCString = _sig(_cf, "CFStringCreateWithCString", _vp, _vp, ctypes.c_char_p, _u32)
_CFGetTypeID = _sig(_cf, "CFGetTypeID", ctypes.c_ulong, _vp)
_CFStringGetTypeID = _sig(_cf, "CFStringGetTypeID", ctypes.c_ulong)
_CFBooleanGetValue = _sig(_cf, "CFBooleanGetValue", _bool, _vp)
_CFRelease = _sig(_cf, "CFRelease", None, _vp)
_kCFBooleanTrue = _vp.in_dll(_cf, "kCFBooleanTrue")

_CGWindowListCopyWindowInfo = _sig(_cg, "CGWindowListCopyWindowInfo", _vp, _u32, _u32)
_CGRectMakeWithDictionaryRepresentation = _sig(_cg, "CGRectMakeWithDictionaryRepresentation", _bool, _vp,
                                               ctypes.POINTER(CGRect))
_CGMainDisplayID = _sig(_cg, "CGMainDisplayID", _u32)
_CGDisplayCopyDisplayMode = _sig(_cg, "CGDisplayCopyDisplayMode", _vp, _u32)
_CGDisplayModeGetWidth = _sig(_cg, "CGDisplayModeGetWidth", ctypes.c_size_t, _vp)
_CGDisplayModeGetPixelWidth = _sig(_cg, "CGDisplayModeGetPixelWidth", ctypes.c_size_t, _vp)
_CGDisplayModeRelease = _sig(_cg, "CGDisplayModeRelease", None, _vp)
_CGGetActiveDisplayList = _sig(_cg, "CGGetActiveDisplayList", ctypes.c_int32, _u32, ctypes.POINTER(_u32),
                               ctypes.POINTER(_u32))
_CGPreflightScreenCaptureAccess = _sig(_cg, "CGPreflightScreenCaptureAccess", _bool)
_CGPreflightPostEventAccess = _sig(_cg, "CGPreflightPostEventAccess", _bool)

_AXIsProcessTrusted = _sig(_ax, "AXIsProcessTrusted", _bool)
_AXUIElementCreateApplication = _sig(_ax, "AXUIElementCreateApplication", _vp, ctypes.c_int)
_AXUIElementCreateSystemWide = _sig(_ax, "AXUIElementCreateSystemWide", _vp)
_AXUIElementCopyAttributeValue = _sig(_ax, "AXUIElementCopyAttributeValue", ctypes.c_int32, _vp, _vp,
                                      ctypes.POINTER(_vp))
_AXUIElementSetAttributeValue = _sig(_ax, "AXUIElementSetAttributeValue", ctypes.c_int32, _vp, _vp, _vp)
_AXUIElementPerformAction = _sig(_ax, "AXUIElementPerformAction", ctypes.c_int32, _vp, _vp)
_AXUIElementSetMessagingTimeout = _sig(_ax, "AXUIElementSetMessagingTimeout", ctypes.c_int32, _vp, ctypes.c_float)
_AXUIElementGetPid = _sig(_ax, "AXUIElementGetPid", ctypes.c_int32, _vp, ctypes.POINTER(ctypes.c_int))
# privada, mas estável há mais de 10 anos (é o que todo gerenciador de janelas do Mac usa): AXUIElement → CGWindowID
_AXUIElementGetWindow = _sig(_ax, "_AXUIElementGetWindow", ctypes.c_int32, _vp, ctypes.POINTER(_u32))

_K = {k: _vp.in_dll(_cg, k) for k in ("kCGWindowNumber", "kCGWindowOwnerPID", "kCGWindowOwnerName", "kCGWindowName",
                                      "kCGWindowLayer", "kCGWindowBounds", "kCGWindowAlpha")}
AX_SEM_RESPOSTA = -25204                                    # kAXErrorCannotComplete: o app não respondeu no prazo
_CAMADAS_DE_JANELA = (0, 3, 8)                              # normal, flutuante, painel modal (o resto é menu, Dock…)


def _cfstr(texto: str):
    return _CFStringCreateWithCString(None, texto.encode("utf-8"), UTF8)


_ATRIB: dict[str, int] = {}


def _atrib(nome: str):
    """CFString de um atributo/ação de acessibilidade (criada uma vez, nunca solta)."""
    if nome not in _ATRIB:
        _ATRIB[nome] = _cfstr(nome)
    return _ATRIB[nome]


def _str(ref) -> str:
    if not ref or _CFGetTypeID(ref) != _CFStringGetTypeID():
        return ""
    n = _CFStringGetLength(ref) * 4 + 1
    b = ctypes.create_string_buffer(n)
    return b.value.decode("utf-8", "replace") if _CFStringGetCString(ref, b, n, UTF8) else ""


def _num(ref, tipo: int = 4) -> float:                      # 4 = SInt64, 13 = Double
    if not ref:
        return 0
    v = ctypes.c_double() if tipo == 13 else _i64()
    _CFNumberGetValue(ref, tipo, ctypes.byref(v))
    return v.value


# ── permissões e tela ────────────────────────────────────────────────────────────────────────────────────────────
def permissoes() -> dict:
    """O que o processo responsável (o Terminal) tem: acessibilidade, gravação de tela, mandar eventos."""
    return {"acessibilidade": bool(_AXIsProcessTrusted()), "gravacao_de_tela": bool(_CGPreflightScreenCaptureAccess()),
            "mandar_eventos": bool(_CGPreflightPostEventAccess())}


def escala(tela: int | None = None) -> float:
    """Pixels por ponto da tela (Retina 2,0; o monitor 1920×1080 do autor 1,0)."""
    modo = _CGDisplayCopyDisplayMode(tela or _CGMainDisplayID())
    try:
        return _CGDisplayModeGetPixelWidth(modo) / max(_CGDisplayModeGetWidth(modo), 1)
    finally:
        _CGDisplayModeRelease(modo)


def telas() -> list[int]:
    ids, n = (_u32 * 16)(), _u32()
    _CGGetActiveDisplayList(16, ids, ctypes.byref(n))
    return list(ids[:n.value])


# ── processos ────────────────────────────────────────────────────────────────────────────────────────────────────
def pids(processo: str) -> list[int]:
    """Os PIDs de um processo PELO NOME EXATO do executável (`"Resolve"`, `"AvidMediaComposer"`), ou por PREFIXO se o
    nome termina em "*" (`"Adobe Premiere Pro*"`: no Mac o executável leva o ano)."""
    # ⚠️ o `pgrep -x` acha o Resolve mas NÃO o Terminal (2026-10-14): comparar o nome do executável no `ps`
    saida = subprocess.run(["ps", "-axo", "pid=,comm="], capture_output=True, text=True).stdout
    prefixo = processo[:-1] if processo.endswith("*") else None
    achados = []
    for linha in saida.splitlines():
        pid, _, cmd = linha.strip().partition(" ")
        nome = os.path.basename(cmd.strip())
        if pid.isdigit() and (nome.startswith(prefixo) if prefixo is not None else nome == processo):
            achados.append(int(pid))
    return achados


def rodando(processo: str) -> bool:
    return bool(pids(processo))


# ── janelas ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _todas_cg(so_na_tela: bool = True) -> list[dict]:
    """As janelas do Window Server, DA FRENTE PARA TRÁS (é a ordem que ele devolve)."""
    arr = _CGWindowListCopyWindowInfo(1 | 16 if so_na_tela else 0, 0)      # OnScreenOnly | ExcludeDesktopElements
    if not arr:
        return []
    out = []
    try:
        for i in range(_CFArrayGetCount(arr)):
            d = _CFArrayGetValueAtIndex(arr, i)
            g = lambda k: _CFDictionaryGetValue(d, _K[k])  # noqa: E731
            r = CGRect()
            _CGRectMakeWithDictionaryRepresentation(g("kCGWindowBounds"), ctypes.byref(r))
            esq, topo = int(round(r.origem.x)), int(round(r.origem.y))
            out.append({"hwnd": int(_num(g("kCGWindowNumber"))), "titulo": _str(g("kCGWindowName")),
                        "dono": _str(g("kCGWindowOwnerName")), "pid": int(_num(g("kCGWindowOwnerPID"))),
                        "camada": int(_num(g("kCGWindowLayer"))), "alfa": _num(g("kCGWindowAlpha"), 13),
                        "ret": (esq, topo, esq + int(round(r.tam.w)), topo + int(round(r.tam.h)))})
    finally:
        _CFRelease(arr)
    return out


def _ax_valor(el, attr: str):
    v = _vp()
    erro = _AXUIElementCopyAttributeValue(el, _atrib(attr), ctypes.byref(v))
    return (v.value if erro == 0 else None), erro


def _ax_janelas(pid: int) -> dict[int, dict]:
    """{número da janela: {subrole, modal, titulo, el}} pela acessibilidade (a lista AXWindows do app)."""
    app = _AXUIElementCreateApplication(pid)
    _AXUIElementSetMessagingTimeout(app, 2.0)
    out = {}
    try:
        lista, _e = _ax_valor(app, "AXWindows")
        if not lista:
            return out
        for i in range(_CFArrayGetCount(lista)):
            el = _CFArrayGetValueAtIndex(lista, i)
            wid = _u32()
            if _AXUIElementGetWindow(el, ctypes.byref(wid)) != 0:
                continue
            sub, _e = _ax_valor(el, "AXSubrole")
            modal, _e = _ax_valor(el, "AXModal")
            tit, _e = _ax_valor(el, "AXTitle")
            out[wid.value] = {"subrole": _str(sub), "modal": bool(modal and _CFBooleanGetValue(modal)),
                              "titulo": _str(tit)}
            for ref in (sub, modal, tit):
                if ref:
                    _CFRelease(ref)
        _CFRelease(lista)
    finally:
        _CFRelease(app)
    return out


def janelas(processo: str | None = None) -> list[dict]:
    """As janelas VISÍVEIS (de um processo, ou todas): [{hwnd, titulo, classe, pid, tem_dono, ret, camada}] — da
    frente para trás. `classe` = o subrole da acessibilidade (AXStandardWindow, AXDialog…); `tem_dono` = é diálogo
    (subrole de diálogo ou modal), o equivalente da janela com dono do Windows."""
    alvo = set(pids(processo)) if processo else None
    cg = [j for j in _todas_cg() if j["camada"] in _CAMADAS_DE_JANELA and j["alfa"] > 0
          and (alvo is None or j["pid"] in alvo)]
    ax = {}
    for pid in {j["pid"] for j in cg}:
        if alvo is not None:
            ax.update(_ax_janelas(pid))
    maiores = {}
    for j in cg:
        if j["camada"] == 0:
            area = (j["ret"][2] - j["ret"][0]) * (j["ret"][3] - j["ret"][1])
            if area > maiores.get(j["pid"], (0, None))[0]:
                maiores[j["pid"]] = (area, j["hwnd"])
    for j in cg:
        a = ax.get(j["hwnd"], {})
        j["classe"] = a.get("subrole", "")
        j["tem_dono"] = a.get("subrole") in ("AXDialog", "AXSystemDialog") or a.get("modal", False)
        # ⚠️ o MC 25.12 no Mac declara TODAS as janelas AXDialog, a principal também (não modal, medido 2026-10-24): sem
        # isto `janela_principal` dava None e `saude_avid` dizia "fechado ou caído" com o MC aberto. A MAIOR janela do
        # processo só é diálogo se for MODAL.
        if a.get("subrole") in ("AXDialog", "AXSystemDialog") and not a.get("modal", False) \
                and maiores.get(j["pid"], (0, None))[1] == j["hwnd"]:
            j["tem_dono"] = False
        j["titulo"] = j["titulo"] or a.get("titulo", "")
    return cg


def titulo(hwnd: int) -> str:
    return next((j["titulo"] for j in _todas_cg(False) if j["hwnd"] == hwnd), "") if hwnd else ""


def retangulo(hwnd: int) -> tuple[int, int, int, int]:
    """(esq, topo, dir, baixo) em PONTOS."""
    return next((j["ret"] for j in _todas_cg(False) if j["hwnd"] == hwnd), (0, 0, 0, 0))


def pid_de(hwnd: int) -> int | None:
    return next((j["pid"] for j in _todas_cg(False) if j["hwnd"] == hwnd), None)


def janela_por_titulo(comeca_com: str) -> int | None:
    return next((j["hwnd"] for j in janelas() if j["titulo"].startswith(comeca_com)), None)


def janela_principal(processo: str) -> int | None:
    """A MAIOR janela visível do processo que não é diálogo."""
    todas = janelas(processo)
    soltas = [j for j in todas if not j["tem_dono"] and j["camada"] == 0]
    if not soltas:
        # a tela inicial do Premiere 2026 (Mac) é uma janela FLUTUANTE (camada 3, AXFloatingWindow), sem nenhuma de
        # camada 0 até abrir um projeto (medido 2026-10-24)
        soltas = [j for j in todas if not j["tem_dono"] and j["camada"] == 3]
    if not soltas:
        return None
    return max(soltas, key=lambda j: (j["ret"][2] - j["ret"][0]) * (j["ret"][3] - j["ret"][1]))["hwnd"]


def dialogos(processo: str) -> list[dict]:
    """Os modais visíveis do app: [{hwnd, titulo}] — janelas que a acessibilidade diz serem diálogo (AXDialog,
    AXSystemDialog) ou modais."""
    return [{"hwnd": j["hwnd"], "titulo": j["titulo"]} for j in janelas(processo) if j["tem_dono"]]


def _pid_da_frente() -> int | None:
    """O PID do app da frente pelo LaunchServices (`lsappinfo front`), sem a acessibilidade."""
    asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True).stdout.strip()
    if not asn:
        return None
    info = subprocess.run(["lsappinfo", "info", "-only", "pid", asn], capture_output=True, text=True).stdout
    _, _, num = info.partition("=")
    return int(num.strip()) if num.strip().isdigit() else None


def janela_da_frente() -> int | None:
    """A janela que recebe o TECLADO agora (a focada do app em foco, pela acessibilidade)."""
    sw = _AXUIElementCreateSystemWide()
    try:
        app, _e = _ax_valor(sw, "AXFocusedApplication")
        if not app:
            # ⚠️ com o Premiere 2026 na frente a acessibilidade não diz nem o app em foco (medido 2026-10-24): o app da
            # frente pelo `lsappinfo` do macOS e a janela de cima dele
            pid = _pid_da_frente()
            return next((j["hwnd"] for j in _todas_cg() if j["pid"] == pid and j["camada"] in (0, 3)), None) \
                if pid else None
        try:
            jan, _e = _ax_valor(app, "AXFocusedWindow")
            if not jan:
                # ⚠️ o Premiere 2026 no Mac não responde AXFocusedWindow (medido 2026-10-24): a janela de cima do app
                # em foco, pela ordem do Window Server
                pid = ctypes.c_int()
                if _AXUIElementGetPid(app, ctypes.byref(pid)) != 0:
                    return None
                return next((j["hwnd"] for j in _todas_cg() if j["pid"] == pid.value and j["camada"] in (0, 3)), None)
            wid = _u32()
            ok = _AXUIElementGetWindow(jan, ctypes.byref(wid)) == 0
            _CFRelease(jan)
            return wid.value if ok else None
        finally:
            _CFRelease(app)
    finally:
        _CFRelease(sw)


def trazer(hwnd: int) -> None:
    """Pede ao macOS: o app da janela vai para a frente e a janela sobe (AXFrontmost + AXRaise + AXMain). Quem confere
    se ficou é `maos.frente`."""
    pid = pid_de(hwnd)
    if pid is None:
        return
    app = _AXUIElementCreateApplication(pid)
    _AXUIElementSetMessagingTimeout(app, 2.0)
    try:
        _AXUIElementSetAttributeValue(app, _atrib("AXFrontmost"), _kCFBooleanTrue)
        lista, _e = _ax_valor(app, "AXWindows")
        if not lista:
            return
        for i in range(_CFArrayGetCount(lista)):
            el = _CFArrayGetValueAtIndex(lista, i)
            wid = _u32()
            if _AXUIElementGetWindow(el, ctypes.byref(wid)) == 0 and wid.value == hwnd:
                _AXUIElementPerformAction(el, _atrib("AXRaise"))
                _AXUIElementSetAttributeValue(el, _atrib("AXMain"), _kCFBooleanTrue)
                break
        _CFRelease(lista)
    finally:
        _CFRelease(app)


# ── fotos ────────────────────────────────────────────────────────────────────────────────────────────────────────
def fotografar(hwnd: int, caminho: str) -> str:
    """A janela inteira (com a barra de título, sem a sombra) — vale coberta por outra janela. Em PIXELS da tela.
    Formato pela extensão (.png, .bmp…)."""
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    tipo = os.path.splitext(caminho)[1].lstrip(".").lower() or "png"
    subprocess.run(["screencapture", "-x", "-o", "-l", str(hwnd), "-t", tipo, caminho], check=True, timeout=20)
    return caminho


def foto_da_tela(pasta: str, nome: str, todas: bool = True) -> str:
    """A tela em PNG — o que o autor veria. `pasta/HHMMSS_nome.png` (com mais de uma tela e `todas`, as outras saem
    como `…_nome_2.png`, `_3`…; devolve a da principal)."""
    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(pasta, f"{time.strftime('%H%M%S')}_{nome}")
    n = len(telas()) if todas else 1
    arqs = [base + ".png"] + [f"{base}_{k}.png" for k in range(2, n + 1)]
    subprocess.run(["screencapture", "-x", *arqs], check=True, timeout=20)
    return arqs[0]


# ── saúde ────────────────────────────────────────────────────────────────────────────────────────────────────────
def respondendo(hwnd: int, prazo: float = 3.0) -> bool:
    """Falso se o app da janela não responde à acessibilidade dentro do `prazo` (o equivalente do IsHungAppWindow:
    um app travado não atende o pedido)."""
    pid = pid_de(hwnd)
    if pid is None:
        return False
    app = _AXUIElementCreateApplication(pid)
    _AXUIElementSetMessagingTimeout(app, prazo)
    try:
        v, erro = _ax_valor(app, "AXRole")
        if v:
            _CFRelease(v)
        return erro != AX_SEM_RESPOSTA
    finally:
        _CFRelease(app)


def existe(hwnd: int) -> bool:
    return any(j["hwnd"] == hwnd for j in _todas_cg())


_CGEventCreateKeyboardEvent = _sig(_cg, "CGEventCreateKeyboardEvent", _vp, _vp, ctypes.c_uint16, _bool)
_CGEventPostToPid = _sig(_cg, "CGEventPostToPid", None, ctypes.c_int, _vp)


def _esc_no_processo(pid: int) -> None:
    """Esc entregue ao PROCESSO (não a quem está na frente): vai para a janela de teclado dele — o diálogo modal."""
    for desce in (True, False):
        ev = _CGEventCreateKeyboardEvent(None, 53, desce)
        _CGEventPostToPid(pid, ev)
        _CFRelease(ev)


def fechar(hwnd: int) -> None:
    """Fechar SEM foco (o WM_CLOSE do Windows): o botão de fechar ou o Cancelar da janela pela acessibilidade; se o app
    não os expõe (o Project Settings do Resolve 21, janela Qt, não expõe — 2026-10-14), Esc entregue ao processo."""
    pid = pid_de(hwnd)
    if pid is None:
        return
    _fechar_ax(pid, hwnd)
    time.sleep(0.5)
    if existe(hwnd):
        _esc_no_processo(pid)


def _fechar_ax(pid: int, hwnd: int) -> None:
    app = _AXUIElementCreateApplication(pid)
    _AXUIElementSetMessagingTimeout(app, 2.0)
    try:
        lista, _e = _ax_valor(app, "AXWindows")
        if not lista:
            return
        for i in range(_CFArrayGetCount(lista)):
            el = _CFArrayGetValueAtIndex(lista, i)
            wid = _u32()
            if _AXUIElementGetWindow(el, ctypes.byref(wid)) != 0 or wid.value != hwnd:
                continue
            for attr in ("AXCloseButton", "AXCancelButton"):
                botao, _e = _ax_valor(el, attr)
                if botao:
                    _AXUIElementPerformAction(botao, _atrib("AXPress"))
                    _CFRelease(botao)
                    break
            break
        _CFRelease(lista)
    finally:
        _CFRelease(app)

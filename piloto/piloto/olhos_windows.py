"""OLHOS no Windows — processos, janelas e fotos (só biblioteca padrão; a foto da tela inteira usa Pillow).

Medido nos NLEs (banco, plugins/avid-panel-sdk/windows.md e matriz de plataforma, seção F):
- O modal do Premiere é uma janela `#32770` do processo, desenhada pelo próprio app: a automação do Windows (UIA) não
  vê texto nem botões. O do MC e o do Resolve são janelas Qt (`Qt…QWindowIcon`) COM DONO (a principal não tem dono).
- Por isso o que funciona é: achar a janela por `EnumWindows`, fotografar por `PrintWindow` e reconhecer pela FOTO
  (`vigia_windows.reconhecer`).
"""
from __future__ import annotations

import ctypes
import os
import struct
import subprocess
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)        # pixels REAIS (ver maos_windows)
except (AttributeError, OSError):
    pass

EXT_FOTO = ".bmp"                                         # a extensão das fotos de janela (o Mac usa .png)

_CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def pids(imagem: str) -> list[int]:
    """Os PIDs de um executável (`"AvidMediaComposer.exe"`)."""
    saida = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {imagem}", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, creationflags=0x08000000).stdout
    achados = []
    for linha in saida.splitlines():
        partes = [p.strip('"') for p in linha.split('","')]
        if len(partes) > 1 and partes[1].isdigit():
            achados.append(int(partes[1]))
    return achados


def rodando(imagem: str) -> bool:
    return bool(pids(imagem))


def _texto(h) -> str:
    b = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, b, 256)
    return b.value


def _classe(h) -> str:
    b = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(h, b, 128)
    return b.value


def janelas(imagem: str | None = None) -> list[dict]:
    """As janelas VISÍVEIS (de um executável, ou todas): [{hwnd, titulo, classe, pid, tem_dono, ret}]."""
    alvo = set(pids(imagem)) if imagem else None
    achadas = []

    def cada(h, _l):
        if not user32.IsWindowVisible(h):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if alvo is None or pid.value in alvo:
            r = wintypes.RECT()
            user32.GetWindowRect(h, ctypes.byref(r))
            achadas.append({"hwnd": int(h), "titulo": _texto(h), "classe": _classe(h), "pid": pid.value,
                            "tem_dono": bool(user32.GetWindow(h, 4)), "ret": (r.left, r.top, r.right, r.bottom)})
        return True
    user32.EnumWindows(_CB(cada), 0)
    return achadas


def titulo(hwnd: int) -> str:
    return _texto(hwnd) if hwnd else ""


def janela_por_titulo(comeca_com: str) -> int | None:
    """A 1ª janela visível cujo título começa com o texto. ⚠️ Título é frágil: o do MC 25.6 é
    "Avid Media Composer  - <projeto>" com DOIS espaços (2026-10-12) — prefira `janela_principal`."""
    return next((j["hwnd"] for j in janelas() if j["titulo"].startswith(comeca_com)), None)


def janela_principal(imagem: str) -> int | None:
    """A MAIOR janela visível SEM dono do executável (a 1ª sem dono às vezes era um popup de 160×156 do MC,
    2026-10-11)."""
    soltas = [j for j in janelas(imagem) if not j["tem_dono"]]
    if not soltas:
        return None
    return max(soltas, key=lambda j: (j["ret"][2] - j["ret"][0]) * (j["ret"][3] - j["ret"][1]))["hwnd"]


def dialogos(imagem: str) -> list[dict]:
    """Os modais visíveis do app: [{hwnd, titulo}]. Premiere: janelas `#32770`; MC e Resolve (Qt): janelas Qt com
    dono."""
    qt = imagem.lower() in ("avidmediacomposer.exe", "resolve.exe")
    out = []
    for j in janelas(imagem):
        if (j["classe"].startswith("Qt") and j["tem_dono"]) if qt else j["classe"] == "#32770":
            out.append({"hwnd": j["hwnd"], "titulo": j["titulo"]})
    return out


def fotografar(hwnd: int, caminho: str) -> str:
    """A janela inteira em BMP (`PrintWindow` com PW_RENDERFULLCONTENT — vale coberta por outra janela, e com parte
    FORA da tela: medido no MC 2024.6, Premiere 26 e Resolve 19, 2026-11-04; ~18 ms numa janela de 1500×770).
    ⛔ O `PrintWindow` PEDE o desenho à janela e espera: numa janela que não responde ele trava PARA SEMPRE (medido no
    Premiere 23.2 caído, 2026-11-05). Por isso a pergunta com prazo antes — e o erro dito, em vez do piloto parado."""
    r_ = ctypes.c_size_t(0)
    user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                           wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
    if user32.IsHungAppWindow(hwnd) or not user32.SendMessageTimeoutW(hwnd, 0, 0, 0, 0x0002, 2000, ctypes.byref(r_)):
        raise TimeoutError(f"a janela {hwnd} não responde: a foto dela travaria (use foto_da_tela)")
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc_j = user32.GetWindowDC(hwnd)
    hdc = gdi32.CreateCompatibleDC(hdc_j)
    bmp = gdi32.CreateCompatibleBitmap(hdc_j, w, h)
    gdi32.SelectObject(hdc, bmp)
    user32.PrintWindow(hwnd, hdc, 2)

    class BMI(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    bmi = BMI(ctypes.sizeof(BMI), w, h, 1, 24, 0, 0, 0, 0, 0, 0)
    linha = (w * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(linha * h)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(hdc)
    user32.ReleaseDC(hwnd, hdc_j)
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", 54 + len(buf.raw), 0, 0, 54)
                + struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(buf.raw), 2835, 2835, 0, 0) + buf.raw)
    return caminho


def foto_da_tela(pasta: str, nome: str, todas: bool = True) -> str:
    """A tela (todas as telas) em PNG — o que o autor veria. `pasta/HHMMSS_nome.png`."""
    from PIL import ImageGrab
    os.makedirs(pasta, exist_ok=True)
    arq = os.path.join(pasta, f"{time.strftime('%H%M%S')}_{nome}.png")
    ImageGrab.grab(all_screens=todas).save(arq)
    return arq


def respondendo(hwnd: int) -> bool:
    """Falso se o Windows marca a janela como travada (`IsHungAppWindow`)."""
    return not user32.IsHungAppWindow(hwnd)


def existe(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd)) and bool(user32.IsWindowVisible(hwnd))


def fechar(hwnd: int) -> None:
    """Fechar SEM foco: WM_CLOSE direto (vale como o X da janela)."""
    user32.PostMessageW(hwnd, 0x0010, 0, 0)

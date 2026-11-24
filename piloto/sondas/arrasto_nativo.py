"""Sonda NATIVA de arrasto (Windows): o que um programa oferece de verdade quando se arrasta algo dele.

    python arrasto_nativo.py --rotulo resolve             # abre uma janela: arraste para ela
    python arrasto_nativo.py --rotulo resolve --x 2200     # a janela no 2º monitor (a principal maximizada cobre o 1º)
    python arrasto_nativo.py --rotulo resolve --clipboard  # despeja a área de transferência (depois de um Ctrl+C)

Precisa de `pywin32` (num venv descartável). Relatório e conteúdos em `piloto/saida/sondas/<rotulo>/`.

## Por que ela existe (o método que achou a chave no Premiere)

Um painel web (CEP, Electron do Resolve) só vê os sabores "web" do arrasto (arquivo, URL, texto): a ponte do navegador
DESCARTA o resto, e um arrasto que chega "vazio" no painel pode carregar um formato privado legível. Uma janela nativa
com `IDropTarget` vê o `IDataObject` INTEIRO. Foi assim que o `dynamiclinksourcelist` do Premiere apareceu (banco,
premiere-cep/arrastar-e-selecao.md §6). Nasceu em `DRAMASYNC/.dev/sonda-premiere/alvo_nativo.py`; aqui, genérica.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pythoncom
import pywintypes
import win32clipboard
import win32con
import win32gui

SAIDA = Path(__file__).resolve().parents[1] / "saida" / "sondas" / "arrasto"
LIMITE = 4 * 1024 * 1024     # não despeja formato maior que isto

PADRAO = {v: k for k, v in vars(win32con).items()
          if k.startswith("CF_") and isinstance(v, int)}

TYMEDS = [(pythoncom.TYMED_HGLOBAL, "HGLOBAL"), (pythoncom.TYMED_ISTREAM, "ISTREAM"),
          (pythoncom.TYMED_FILE, "FILE"), (pythoncom.TYMED_ISTORAGE, "ISTORAGE")]


def nome_do_formato(cf: int) -> str:
    if cf in PADRAO:
        return PADRAO[cf]
    try:
        return win32clipboard.GetClipboardFormatName(cf)
    except pywintypes.error:
        return f"cf_{cf}"


def legivel(dados: bytes) -> str:
    """Um trecho do conteúdo, no encoding que parecer certo."""
    if not dados:
        return "(vazio)"
    amostra = dados[:4000]
    zeros = amostra[1::2].count(0)
    tentativas = ["utf-16-le", "utf-8", "latin-1"] if zeros > len(amostra) / 4 else ["utf-8", "latin-1"]
    for enc in tentativas:
        try:
            texto = amostra.decode(enc)
            imprimiveis = sum(ch.isprintable() or ch in "\r\n\t" for ch in texto)
            if texto and imprimiveis / len(texto) > 0.85:
                return f"[{enc}] " + texto.replace("\x00", "∅")[:2000]
        except UnicodeDecodeError:
            continue
    return "[hex] " + amostra[:256].hex(" ")


class Relatorio:
    def __init__(self):
        SAIDA.mkdir(parents=True, exist_ok=True)
        self.caminho = SAIDA / "relatorio.txt"
        self.linhas: list[str] = []

    def escrever(self, texto: str = ""):
        print(texto)
        self.linhas.append(texto)
        self.caminho.write_text("\n".join(self.linhas), encoding="utf-8")

    def guardar(self, rotulo: str, nome: str, dados: bytes) -> Path:
        seguro = "".join(c if c.isalnum() or c in "-_." else "_" for c in nome)[:60]
        p = SAIDA / f"{rotulo}_{seguro}.bin"
        p.write_bytes(dados)
        return p


X, Y = 200, 200
#: ⚠️ o pywin32 atual NÃO traz `win32con.DROPEFFECT_*` (o DragEnter estourava calado depois do despejo e o Drop
#: nunca vinha — 2026-10-12): os valores do `oleidl.h`.
DROPEFFECT_NONE, DROPEFFECT_COPY, DROPEFFECT_MOVE, DROPEFFECT_LINK = 0, 1, 2, 4


def ler_medium(medium) -> bytes | None:
    dados = medium.data
    if isinstance(dados, (bytes, bytearray)):
        return bytes(dados)
    if isinstance(dados, str):
        return dados.encode("utf-16-le")
    # ISTREAM
    try:
        partes = []
        while True:
            pedaco = dados.Read(65536)
            if not pedaco:
                break
            partes.append(pedaco)
            if sum(map(len, partes)) > LIMITE:
                break
        return b"".join(partes)
    except Exception:  # noqa: BLE001
        return None


_CONTADOR = [0]


def despejar_data_object(obj, rotulo: str):
    # Cada evento ganha número: os arquivos de um arrasto não sobrescrevem o anterior.
    _CONTADOR[0] += 1
    rotulo = f"{_CONTADOR[0]:03d}_{rotulo}"
    R.escrever(f"===== {rotulo}  ({time.strftime('%H:%M:%S')}) =====")
    try:
        formatos = list(obj.EnumFormatEtc(pythoncom.DATADIR_GET))
    except pywintypes.com_error as e:
        R.escrever(f"EnumFormatEtc falhou: {e}")
        return
    R.escrever(f"formatos oferecidos: {len(formatos)}")
    for fmt in formatos:
        cf, _alvo, aspecto, indice, tymed = fmt
        nome = nome_do_formato(cf)
        meios = "|".join(n for t, n in TYMEDS if tymed & t) or str(tymed)
        R.escrever(f"- {nome}  (cf={cf}, tymed={meios})")
        for t, n in TYMEDS[:2]:
            if not tymed & t:
                continue
            try:
                medium = obj.GetData((cf, None, aspecto, indice, t))
            except pywintypes.com_error as e:
                R.escrever(f"    GetData({n}) falhou: {e.args[1] if len(e.args) > 1 else e}")
                continue
            dados = ler_medium(medium)
            if dados is None:
                R.escrever(f"    {n}: não deu para ler")
                continue
            arq = R.guardar(rotulo, nome, dados[:LIMITE])
            R.escrever(f"    {n}: {len(dados)} bytes → {arq.name}")
            R.escrever("    " + legivel(dados).replace("\n", "\n    "))
            if nome == "dynamiclinksourcelist":
                # ⭐ o formato do Premiere que interessa: cada <Source> é um item
                import re as _re
                texto = dados.decode("utf-8", "replace").rstrip("\x00")
                (SAIDA / f"{rotulo}_dynamiclink.xml").write_text(texto, encoding="utf-8")
                ids = _re.findall(r"<ID>([^<]+)</ID>", texto)
                R.escrever(f"    → {len(ids)} item(ns): " + ", ".join(ids))
            break
    R.escrever()


class AlvoDeArrasto:
    _public_methods_ = ["DragEnter", "DragOver", "DragLeave", "Drop"]
    _com_interfaces_ = [pythoncom.IID_IDropTarget]

    def DragEnter(self, obj, estado, ponto, efeito):
        R.escrever(f"(efeitos que a origem permite: {efeito})")
        despejar_data_object(obj, "dragenter")
        # Aceita o que a origem oferecer — o Premiere recusa COPY (cursor bloqueado).
        self.efeito = efeito & (DROPEFFECT_COPY | DROPEFFECT_LINK
                                | DROPEFFECT_MOVE)
        return self.efeito

    def DragOver(self, estado, ponto, efeito):
        return getattr(self, "efeito", DROPEFFECT_COPY)

    def DragLeave(self):
        R.escrever("(dragleave)")

    def Drop(self, obj, estado, ponto, efeito):
        despejar_data_object(obj, "drop")
        R.escrever(f"relatório: {R.caminho}")
        # ⚠️ Devolver NENHUM efeito: um MOVE aceito poderia fazer a origem apagar o item.
        return DROPEFFECT_NONE


def janela():
    from win32com.server.util import wrap

    pythoncom.OleInitialize()
    wc = win32gui.WNDCLASS()
    wc.lpszClassName = "PilotoSondaArrasto"
    wc.hbrBackground = win32con.COLOR_WINDOW + 1
    wc.lpfnWndProc = {win32con.WM_DESTROY: lambda h, m, w, l: win32gui.PostQuitMessage(0)}
    win32gui.RegisterClass(wc)
    hwnd = win32gui.CreateWindowEx(
        win32con.WS_EX_TOPMOST, wc.lpszClassName,
        "piloto · sonda de arrasto — solte aqui",
        win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
        X, Y, 560, 300, 0, 0, 0, None)
    alvo = wrap(AlvoDeArrasto(), pythoncom.IID_IDropTarget)
    pythoncom.RegisterDragDrop(hwnd, alvo)
    R.escrever(f"janela aberta (hwnd {hwnd}) — arraste para ela. Relatório em {R.caminho}")
    win32gui.PumpMessages()
    pythoncom.RevokeDragDrop(hwnd)


def area_de_transferencia():
    obj = pythoncom.OleGetClipboard()
    despejar_data_object(obj, "clipboard")
    R.escrever(f"relatório: {R.caminho}")


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("esta sonda é só para Windows (OLE)")
    ap = argparse.ArgumentParser()
    ap.add_argument("--clipboard", action="store_true")
    ap.add_argument("--rotulo", default="arrasto")
    ap.add_argument("--x", type=int, default=200)
    ap.add_argument("--y", type=int, default=200)
    a = ap.parse_args()
    SAIDA = SAIDA.parent / a.rotulo
    R = Relatorio()
    X, Y = a.x, a.y
    area_de_transferencia() if a.clipboard else janela()

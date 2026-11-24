"""As FALHAS que o sistema registrou: o piloto confere depois de abrir e de fechar um programa, e DIZ (autor, 2026-11-22:
"isso pode ser ruim se no uso da ferramenta criarmos essas mensagens, mesmo que inofensivas pro usuário algo está errado").

Medido no Mac (2026-11-22, BL08): o MC abortou 8 s depois de abrir (títulos/Deko), o `AvidIdentityHandler` foi morto pelo
próprio MC em aberturas feitas pelo terminal, e o Baselight caiu AO SAIR com a FLAPI ainda conectada. O macOS mostrou o
"Relatório de Problemas" na tela do autor e ninguém do nosso lado viu.

    marca = falhas.agora()
    … abrir / operar / fechar …
    for f in falhas.desde(marca):          # [] = nada caiu
        print(falhas.frase(f))

- Mac: `~/Library/Logs/DiagnosticReports/*.ips` (1ª linha = cabeçalho JSON; o resto = o relatório). `confirmado`.
- Windows: o arquivo do WER (`ReportArchive`/`ReportQueue`, pastas `AppCrash_<exe>_…`, com `Report.wer`). `pendente`
  (não medido nesta máquina).
"""
from __future__ import annotations

import json
import os
import sys
import time

SISTEMA = "macos" if sys.platform == "darwin" else "windows"


def _pastas() -> list[str]:
    if SISTEMA == "macos":
        return [os.path.expanduser("~/Library/Logs/DiagnosticReports")]
    base = os.environ.get("ProgramData", r"C:\ProgramData")
    locais = os.environ.get("LOCALAPPDATA", "")
    return [os.path.join(base, r"Microsoft\Windows\WER", p) for p in ("ReportArchive", "ReportQueue")] + \
           ([os.path.join(locais, r"Microsoft\Windows\WER", p) for p in ("ReportArchive", "ReportQueue")] if locais else [])


def agora() -> float:
    """A marca de tempo para `desde` (com 1 s de folga para trás: o relógio do arquivo tem resolução grossa)."""
    return time.time() - 1.0


def _ler_ips(caminho: str) -> dict:
    with open(caminho, encoding="utf-8", errors="replace") as fh:
        cab = json.loads(fh.readline() or "{}")
        try:
            corpo = json.loads(fh.read() or "{}")
        except ValueError:
            corpo = {}
    exc = corpo.get("exception") or {}
    term = corpo.get("termination") or {}
    motivo = exc.get("signal") or exc.get("type") or term.get("indicator") or cab.get("bug_type") or "?"
    return {"app": cab.get("app_name") or os.path.basename(caminho).split("-")[0], "motivo": motivo,
            "por": term.get("byProc"), "versao": cab.get("app_version")}


def _ler_wer(pasta: str) -> dict:
    nome = os.path.basename(pasta)
    partes = nome.split("_")
    app = partes[1] if len(partes) > 1 else nome
    motivo = partes[0]
    wer = os.path.join(pasta, "Report.wer")
    if os.path.exists(wer):
        try:
            with open(wer, encoding="utf-16", errors="replace") as fh:
                for linha in fh:
                    if linha.startswith("AppName="):
                        app = linha.split("=", 1)[1].strip()
                    elif linha.startswith("EventType="):
                        motivo = linha.split("=", 1)[1].strip()
        except OSError:
            pass
    return {"app": app, "motivo": motivo, "por": None, "versao": None}


def desde(marca: float, apps: list[str] | None = None) -> list[dict]:
    """As falhas registradas depois de `marca` (de `agora()`), as mais antigas primeiro. `apps` filtra pelo nome (parte
    do nome, sem diferença de maiúsculas): `["Avid", "Baselight"]`. Cada uma: {arquivo, quando, app, motivo, por, versao}."""
    achadas = []
    for pasta in _pastas():
        try:
            nomes = os.listdir(pasta)
        except OSError:
            continue
        for n in nomes:
            c = os.path.join(pasta, n)
            try:
                quando = os.path.getmtime(c)
            except OSError:
                continue
            if quando < marca:
                continue
            if SISTEMA == "macos":
                if not n.endswith(".ips"):
                    continue
                try:
                    info = _ler_ips(c)
                except (OSError, ValueError):
                    info = {"app": n.split("-")[0], "motivo": "?", "por": None, "versao": None}
            else:
                if not os.path.isdir(c) or not n.lower().startswith(("appcrash", "apphang", "bex")):
                    continue
                info = _ler_wer(c)
            if apps and not any(a.lower() in (info["app"] or "").lower() for a in apps):
                continue
            achadas.append({"arquivo": c, "quando": quando, **info})
    return sorted(achadas, key=lambda f: f["quando"])


def frase(f: dict) -> str:
    """Uma linha para o editor (e o log): o quê, quando, por quê."""
    hora = time.strftime("%H:%M:%S", time.localtime(f["quando"]))
    por = f" (encerrado por {f['por']})" if f.get("por") and f["por"] != f["app"] else ""
    return f"⚠️ {f['app']} caiu às {hora}: {f['motivo']}{por} — relatório em {f['arquivo']}"

"""Perfis dos apps que o piloto conhece: executável por sistema, onde ficam os diálogos conhecidos (catálogo de fotos)
e sinais de queda. App novo = uma entrada aqui + a pasta `catalogos/<chave>/` (pode começar vazia)."""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGOS = os.path.join(RAIZ, "catalogos")
SAIDA = os.path.join(RAIZ, "saida")                         # fotos do vigia e das rodadas (fora do Git)

APPS = {
    "avid": {
        "nome": "Media Composer",
        "windows": "AvidMediaComposer.exe",
        "macos": "AvidMediaComposer",                      # conferido 2026-10-14 (…/AvidMediaComposer.app/Contents/MacOS)
        # o texto das janelas de erro do MC não aparece para a automação: ele o grava aqui (banco, windows.md)
        "eventlog_windows": r"C:\Users\Public\Documents\Avid Media Composer\Avid FatalErrorReports\EVENTLOG.LOG",
        "eventlog_macos": "/Users/Shared/AvidMediaComposer/Avid FatalErrorReports/EVENTLOG.LOG",
        # janelas do MC que NÃO são modais: a "Settings", a "Select Project", as bins soltas ("Bins", "Bins.1"… — a "Bins" é o
        # contêiner de bins solto que o projeto pode reabrir, visto 2026-10-12) e os PAINÉIS soltos do menu Tools (o do De Lá Pra
        # Cá virou janela própria com o título dele — o vigia o tomou por diálogo, 2026-10-13)
        "nao_modais": ("Settings", "Select Project", "Motion Effect Editor", "Effect Editor", "Bins",
                       "De Lá Pra Cá", "Órbita", "Promo Entrega", "Ciclo Assist") + tuple(f"Bins.{n}" for n in range(1, 10)),
        # ⚠️ a "Select Project" só é normal ABRINDO o MC. No meio de um trabalho ela quer dizer que o projeto fechou (o
        # MC caiu e foi reaberto, 2026-10-12): o título da principal fica SEM o projeto ("Avid Media Composer  - <projeto>"
        # → "Avid Media Composer") — ver `saude_avid`
        "titulo_sem_projeto": "Avid Media Composer",
        # ⚠️ TELA DE TRIAL (MC trial, visto no 23.8.2 em 2026-10-17): ao abrir, a JANELA PRINCIPAL (sem dono) tem o
        # título "Avid Media Composer Activation" e espera parada (não some sozinha). NÃO é diálogo com dono → o
        # vigia.varrer/dialogos NÃO a pega. Trate por título na rotina de abertura: frente(h) + maos.ENTER — "Trial
        # Mode" já vem marcado e o botão Continue está em foco → continua o trial. Foto no catálogo: ativacao_trial.png.
        "titulo_ativacao": "Avid Media Composer Activation",
    },
    "premiere": {
        "nome": "Premiere Pro",
        "windows": "Adobe Premiere Pro.exe",
        # no Mac o executável leva o ANO ("Adobe Premiere Pro 2026", medido 2026-10-24; a 2025 e a Beta convivem) —
        # o "*" final é prefixo em `olhos.pids`. ⚠️ O dono das janelas é "Adobe Premiere", não o nome do processo.
        "macos": "Adobe Premiere Pro*",
        "nao_modais": (),
    },
    "resolve": {
        "nome": "DaVinci Resolve",
        "windows": "Resolve.exe",
        "macos": "Resolve",
        "nao_modais": (),
    },
}


SISTEMA = "windows" if sys.platform == "win32" else "macos"


def processo(chave: str) -> str:
    """O nome do executável do app NESTE sistema (`imagem` do vigia): "Resolve.exe" no Windows, "Resolve" no Mac."""
    return APPS[chave][SISTEMA]


def eventlog(chave: str) -> str | None:
    """O log de falhas do app NESTE sistema (só o MC tem), para `vigia.com_prazo(eventlog=…)`."""
    return APPS[chave].get(f"eventlog_{SISTEMA}")


def saude_avid() -> str | None:
    """Para `vigia.com_prazo(saude=…)` no MC: um motivo se ele não está num projeto aberto, None se está."""
    from . import olhos as O
    h = O.janela_principal(processo("avid"))
    if not h:
        return "o Media Composer não tem janela principal (fechado ou caído)"
    if O.titulo(h).strip() == APPS["avid"]["titulo_sem_projeto"]:
        return "o Media Composer está SEM projeto aberto (voltou à tela Select Project — caiu e foi reaberto?)"
    return None


APLICATIVOS_MACOS = {                                       # o .app que `abrir` usa no Mac (conferido 2026-10-24)
    "avid": "/Applications/Avid Media Composer/AvidMediaComposer.app",
    "premiere": "/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app",
    "resolve": "/Applications/DaVinci Resolve/DaVinci Resolve.app",
}


def abrir(chave: str, ambiente_extra: dict | None = None) -> None:
    """Abre o app no Mac como o Dock abriria: SEM o `LANG`/`LC_*` da sessão do terminal. ⛔ O MC 25.12 aberto por
    `open -a` com `LANG=pt_BR.UTF-8` herdado ABORTA na abertura (DekoLibrary `k_double`, medido 2026-10-24; banco,
    matriz de plataforma seção B). `ambiente_extra` vai por `open --env` (ex. o gadget do Frida:
    `{"DYLD_INSERT_LIBRARIES": ".../frida-gadget.dylib"}`)."""
    import subprocess
    if SISTEMA != "macos":
        raise NotImplementedError("abrir: só o Mac por enquanto (no Windows a sessão não injeta LANG — pendente)")
    env = {k: v for k, v in os.environ.items() if k != "LANG" and not k.startswith("LC_")}
    cmd = ["open"]
    for k, v in (ambiente_extra or {}).items():
        cmd += ["--env", f"{k}={v}"]
    subprocess.run(cmd + ["-a", APLICATIVOS_MACOS[chave]], env=env, check=True)


def app(chave: str) -> dict:
    return APPS[chave]


def catalogo(chave: str) -> str:
    """A pasta das fotos de diálogos conhecidos do app."""
    return os.path.join(CATALOGOS, chave)

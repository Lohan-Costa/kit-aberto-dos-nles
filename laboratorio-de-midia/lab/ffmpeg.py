"""Achar e chamar o ffmpeg/ffprobe nas duas plataformas.

Regras da matriz de plataforma do banco (`transversal/matriz-de-plataforma.md`) aplicadas aqui:
- **PATH herdado não basta** (regra 5): processo lançado pelo Finder/launchd nasce com
  `/usr/bin:/bin:/usr/sbin:/sbin` e não acha o Homebrew — o De Lá Pra Cá perdeu a timeline inteira
  assim em 2026-10-04. Procuramos também onde os instaladores põem, e dizemos ONDE procuramos.
- **`shutil.which` não**: no Windows ele inclui a pasta atual (binary planting). Varremos o PATH à mão.
- **Sem janela piscando no Windows** (`CREATE_NO_WINDOW`) e **stderr lido como UTF-8** (no Windows
  viria cp1252); processo que falha é ERRO com o stderr mostrado (regra 6), nunca silêncio.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from functools import lru_cache

SEM_JANELA = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}


def pasta_propria() -> str:
    """O ffmpeg DO LABORATÓRIO (o 8.1.2 do release de vendor do De Lá Pra Cá, conferido por hash:
    `_DeLaPraCa/tools/baixar_ffmpeg.py <alvo> <esta pasta>`). Procurado ANTES do PATH. ⛔ Medido 2026-10-09
    (Windows): o `C:\\ffmpeg` da máquina (git N-116931, 2024-09) gravava o .mov SEM a faixa de timecode e com
    quadros a menos — o B01 falhava 3/19; com o 8.1.2, 19/19."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/Library/Application Support")
    return os.path.join(base, "laboratorio-de-midia", "ffmpeg")


def _pastas_candidatas() -> list[str]:
    pastas = [pasta_propria()] + [p for p in os.environ.get("PATH", "").split(os.pathsep) if p and p != "."]
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        pastas += [os.path.join(local, "Microsoft", "WinGet", "Links"), r"C:\ffmpeg\bin",
                   r"C:\ProgramData\chocolatey\bin", os.path.expanduser(r"~\scoop\shims")]
    else:
        pastas += ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"]
    vistas, unicas = set(), []
    for p in pastas:
        chave = os.path.normcase(os.path.abspath(p))
        if chave not in vistas:
            vistas.add(chave)
            unicas.append(p)
    return unicas


@lru_cache(maxsize=None)
def achar(nome: str) -> str:
    """Caminho absoluto do `ffmpeg`/`ffprobe`. A variável `LAB_FFMPEG_DIR` força uma pasta."""
    exe = nome + (".exe" if os.name == "nt" else "")
    forcada = os.environ.get("LAB_FFMPEG_DIR")
    pastas = [forcada] if forcada else _pastas_candidatas()
    for pasta in pastas:
        caminho = os.path.join(pasta, exe)
        if os.path.isfile(caminho) and os.access(caminho, os.X_OK):
            return caminho
    raise FileNotFoundError(f"{exe} não encontrado. Procurei em: " + "; ".join(pastas))


def rodar(args: list[str], cwd: str | None = None, binario: bool = False):
    """Roda e devolve o stdout (texto, ou bytes com `binario=True`). Falha = exceção com o stderr."""
    r = subprocess.run(args, cwd=cwd, capture_output=True, **SEM_JANELA)
    if r.returncode != 0:
        erro = r.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{os.path.basename(args[0])} saiu com {r.returncode}:\n{erro[-3000:]}")
    return r.stdout if binario else r.stdout.decode("utf-8", "replace")


@lru_cache(maxsize=None)
def versao() -> tuple[str, int]:
    """('8.1.1', 8). Build de git (`N-12345-g…-AAAAMMDD`) pela DATA: antes de 2025 conta como 7 (o
    `N-116931-…-20240908` do Windows não é "o mais novo" — 2026-10-09); sem data, como o mais novo."""
    linha = rodar([achar("ffmpeg"), "-hide_banner", "-version"]).splitlines()[0]
    m = re.search(r"version (\S+)", linha)
    texto = m.group(1) if m else "?"
    m2 = re.match(r"n?(\d+)\.", texto)
    if m2:
        return texto, int(m2.group(1))
    data = re.search(r"-(20\d{6})$", texto)
    if data:
        return texto, 7 if data.group(1) < "20250101" else 8
    return texto, 99


def opcao_script_de_filtro(caminho: str) -> list[str]:
    """`-filter_complex_script` saiu de cena no ffmpeg 7.1 (vira `-/filter_complex <arquivo>`); o do
    Windows pode ser mais velho. O script em arquivo evita o limite de linha de comando do Windows
    (~32 mil caracteres) e as aspas do shell."""
    return ["-/filter_complex", caminho] if versao()[1] >= 7 else ["-filter_complex_script", caminho]


def sondar(caminho: str, contar_pacotes: bool = False) -> dict:
    """`ffprobe` em JSON: formato + streams (com tags). `contar_pacotes` conta os pacotes de cada
    stream sem decodificar (`nb_read_packets`) — rápido, e não cai na busca torta do MPEG-2."""
    args = [achar("ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams"]
    if contar_pacotes:
        args.append("-count_packets")
    return json.loads(rodar(args + ["file:" + caminho]))


if __name__ == "__main__":
    print(achar("ffmpeg"), versao()[0], file=sys.stderr)

"""varredura.py — o portão de segurança do KIT ABERTO DOS NLEs (o mesmo na máquina de quem usa e no GitHub).

    python3 ferramentas/varredura.py                     # o que está preparado para o commit (git add)
    python3 ferramentas/varredura.py <pasta ou arquivo>  # o que estiver ali
    python3 ferramentas/varredura.py --pr <base>         # um pull request: o que mudou desde <base> + a quarentena

Procura, em cada arquivo: SEGREDO (chave, token), CAMINHO PESSOAL (/Users/<nome>, C:\\Users\\<nome>, /home/<nome>),
E-MAIL, MÍDIA ou PROJETO de NLE (que não vão: o laboratório gera o sintético) e arquivo GRANDE (> 1 MB).
No modo `--pr`, a QUARENTENA: um pull request de contribuição só pode criar ou mudar arquivos em `contribuicoes/`.

Sai 0 se nada foi achado, 1 se achou (cada achado com o arquivo, a linha e o motivo). Só a biblioteca padrão do Python.
⚠️ Ela não conhece nomes de clientes, produções e pessoas: isso é a pessoa que confere, lendo o que vai sair
(skill `ciclo-contribuir`).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEGREDOS = [r"sk-ant-[A-Za-z0-9_-]{16,}", r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{30,}", r"gho_[A-Za-z0-9]{30,}",
            r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"xox[abp]-[A-Za-z0-9-]{10,}",
            r"AIza[0-9A-Za-z_-]{35}", r"sk-[A-Za-z0-9]{40,}"]
#: o que parece caminho de uma pessoa (os genéricos de exemplo passam)
CAMINHO = re.compile(r"(/Users/|/home/|[A-Za-z]:\\\\?Users\\\\?)(?!(?i:<|\$|%|\{|\.\.\.|voce|você|usuari|usuário|nome|seu|exemplo|shared|public|runner|guest|default|admin))"
                     r"([A-Za-z0-9._-]{2,})")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
EMAIL_OK = ("noreply@anthropic.com", "git@github.com", "users.noreply.github.com", "@exemplo.", "@example.")
MIDIA = {".mov", ".mp4", ".mxf", ".mts", ".m4v", ".avi", ".mkv", ".braw", ".r3d", ".ari", ".arx", ".crm", ".dng",
         ".wav", ".aif", ".aiff", ".bwf", ".mp3", ".m4a", ".aaf", ".avb", ".avp", ".mdb", ".pmr", ".prproj", ".drp",
         ".drt", ".fcpxml", ".blscene", ".otio"}
GRANDE = 1_000_000
QUARENTENA = "contribuicoes/"
DOC = re.compile(r"^(ferramentas/varredura\.py|.*\.md)$")   # onde exemplos de caminho são texto, não vazamento


def git(*args: str) -> list[str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} falhou: {r.stderr.strip()[-300:]}")
    return [x for x in r.stdout.splitlines() if x.strip()]


def arquivos(alvos: list[str]) -> list[str]:
    out = []
    for a in alvos:
        if os.path.isdir(a):
            for raiz, pastas, nomes in os.walk(a):
                pastas[:] = [p for p in pastas if p not in (".git", "__pycache__", ".venv", "node_modules")]
                out += [os.path.join(raiz, n) for n in nomes]
        elif os.path.isfile(a):
            out.append(a)
    return out


def varrer(caminho: str) -> list[tuple[str, int, str]]:
    achados: list[tuple[str, int, str]] = []
    rel = caminho.replace(os.sep, "/").lstrip("./")
    if os.path.splitext(caminho)[1].lower() in MIDIA:
        achados.append((rel, 0, "mídia ou projeto de NLE: não vai (gere o caso com uma receita do laboratório)"))
    if os.path.getsize(caminho) > GRANDE:
        achados.append((rel, 0, f"arquivo grande ({os.path.getsize(caminho) // 1024} KB)"))
    with open(caminho, "rb") as fh:
        bruto = fh.read()
    texto = bruto.decode("utf-8", errors="replace")
    for n, linha in enumerate(texto.splitlines(), 1):
        for p in SEGREDOS:
            if re.search(p, linha):
                achados.append((rel, n, "SEGREDO (chave ou token)"))
        if not DOC.match(rel):
            m = CAMINHO.search(linha)
            if m:
                achados.append((rel, n, f"caminho pessoal: {m.group(0)}…"))
        for m in EMAIL.finditer(linha):
            if not any(ok in m.group(0) for ok in EMAIL_OK):
                achados.append((rel, n, f"e-mail: {m.group(0)}"))
    return achados


def main() -> int:
    args = sys.argv[1:]
    quarentena = []
    if args[:1] == ["--pr"]:
        if len(args) < 2:
            raise SystemExit("uso: varredura.py --pr <base>")
        mudados = git("diff", "--name-only", "--diff-filter=ACMR", f"{args[1]}...HEAD")
        apagados = git("diff", "--name-only", "--diff-filter=D", f"{args[1]}...HEAD")
        quarentena = [f for f in mudados + apagados if not f.startswith(QUARENTENA)]
        lista = [f for f in mudados if os.path.isfile(f)]
    elif args:
        lista = arquivos(args)
    else:
        lista = [f for f in git("diff", "--cached", "--name-only", "--diff-filter=ACMR") if os.path.isfile(f)]
    achados = [a for f in lista for a in varrer(f)]
    for f in quarentena:
        achados.append((f, 0, f"fora da quarentena: uma contribuição só cria ou muda arquivos em {QUARENTENA}"))
    for arq, n, motivo in achados:
        print(f"{arq}{':' + str(n) if n else ''}  {motivo}")
    print(f"\n{len(lista)} arquivo(s) varrido(s); {len(achados)} achado(s).")
    return 1 if achados else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
verificar_plataforma.py — onde, num repositório, o código encosta numa variável de plataforma.

Lê `transversal/matriz-de-plataforma.json` e procura, em cada arquivo de código, a regex
`busca` de cada linha da matriz. Para cada ocorrência mostra a armadilha e o que vale no
Windows e no macOS; quando a regex `tratado` aparece a até 6 linhas, marca "parece tratado".

⚠️ **É um guia de revisão, não um portão.** Uma ocorrência não é um defeito: é um lugar que
precisa ter os DOIS lados pensados. Por isso sai com código 0 — salvo com `--falhar`, que
falha quando sobra ocorrência sem sinal de tratamento.

Uso (stdlib pura, Python 3.9+; no Mac é `python3`, no Windows `py`):
    python3 verificar_plataforma.py <repositório>              # relatório por linha da matriz
    python3 verificar_plataforma.py <repo> --resumo            # só as contagens
    python3 verificar_plataforma.py <repo> --so-pendentes      # esconde o que parece tratado
    python3 verificar_plataforma.py <repo> --sem-testes        # sem tests/ e spikes/
    python3 verificar_plataforma.py <repo> --entrada appledouble
    python3 verificar_plataforma.py <repo> --json              # para outra ferramenta ler

Regra master: transversal/matriz-de-plataforma.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
MATRIZ = RAIZ / "transversal" / "matriz-de-plataforma.json"

#: O que é código nosso. Texto de documentação fica de fora: citar `LOCALAPPDATA` num .md
#: não é usar.
EXTENSOES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs", ".go", ".lua",
             ".ps1", ".psm1", ".sh", ".bash", ".zsh", ".command", ".bat", ".cmd", ".vbs",
             ".html", ".swift", ".cs", ".cpp", ".c", ".h", ".jsx"}

#: Pastas que não são código do repositório (e varrê-las custa minutos num SSD exFAT).
IGNORAR = {".git", "node_modules", "__pycache__", ".venv", ".venv-win", ".venv-mac", "venv",
           "dist", "build", "target", ".pytest_cache", ".mypy_cache", ".tox", "site-packages",
           "vendor", ".next", "coverage", "proto"}

#: `--sem-testes`: onde caminho de outra plataforma é DADO de teste, não uso.
PASTAS_DE_TESTE = {"tests", "test", "__tests__", "spikes", "spike", "fixtures"}

#: Linha de comentário não é uso. Docstring continua contando — é barato de revisar.
COMENTARIO = re.compile(r"^\s*(#|//|/\*|\*|--|REM\b|::|<!--)", re.IGNORECASE)

JANELA = 6
MAX_BYTES = 2 * 1024 * 1024


def carregar() -> dict:
    return json.loads(MATRIZ.read_text(encoding="utf-8"))


def arquivos(repo: Path, sem_testes: bool = False):
    fora = IGNORAR | (PASTAS_DE_TESTE if sem_testes else set())
    for raiz, pastas, nomes in os.walk(repo):
        # ⚠️ A própria matriz, regra 4: ocultas e sombras do macOS fora.
        pastas[:] = sorted(p for p in pastas if p not in fora and not p.startswith("."))
        for nome in sorted(nomes):
            if nome.startswith("._"):
                continue
            caminho = Path(raiz) / nome
            if caminho.suffix.lower() in EXTENSOES:
                yield caminho


def varrer(repo: Path, entradas: dict, sem_testes: bool = False) -> dict[str, list[dict]]:
    regras = {k: (re.compile(v["busca"]), re.compile(v["tratado"]) if v.get("tratado") else None)
              for k, v in entradas.items() if v.get("busca")}
    achados: dict[str, list[dict]] = {k: [] for k in regras}
    for arq in arquivos(repo, sem_testes):
        try:
            if arq.stat().st_size > MAX_BYTES:
                continue
            linhas = arq.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = arq.relative_to(repo).as_posix()
        for i, linha in enumerate(linhas):
            if COMENTARIO.match(linha):
                continue
            for chave, (busca, tratado) in regras.items():
                if not busca.search(linha):
                    continue
                perto = "\n".join(linhas[max(0, i - JANELA): i + JANELA + 1])
                achados[chave].append({
                    "arquivo": rel, "linha": i + 1, "texto": linha.strip()[:160],
                    "parece_tratado": bool(tratado and tratado.search(perto)),
                })
    return {k: v for k, v in achados.items() if v}


def lado(valor) -> str:
    if valor is None:
        return "pendente"
    if isinstance(valor, list):
        return " · ".join(valor)
    return str(valor)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console cp1252 (matriz E)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--resumo", action="store_true")
    ap.add_argument("--so-pendentes", action="store_true")
    ap.add_argument("--sem-testes", action="store_true")
    ap.add_argument("--entrada", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--falhar", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"não é uma pasta: {repo}", file=sys.stderr)
        return 2
    matriz = carregar()
    entradas = matriz["entries"]
    if args.entrada:
        faltam = [e for e in args.entrada if e not in entradas]
        if faltam:
            print(f"entrada desconhecida: {', '.join(faltam)}", file=sys.stderr)
            return 2
        entradas = {k: entradas[k] for k in args.entrada}

    achados = varrer(repo, entradas, args.sem_testes)
    if args.so_pendentes:
        achados = {k: [o for o in v if not o["parece_tratado"]] for k, v in achados.items()}
        achados = {k: v for k, v in achados.items() if v}
    pendentes = sum(1 for v in achados.values() for o in v if not o["parece_tratado"])

    if args.json:
        print(json.dumps({"repo": str(repo), "atualizado_matriz": matriz["_meta"]["atualizado"],
                          "achados": achados}, ensure_ascii=False, indent=2))
    else:
        print(f"Matriz de plataforma ({matriz['_meta']['atualizado']}) sobre {repo}\n")
        for chave in sorted(achados, key=lambda k: (entradas[k]["categoria"], k)):
            ocorr = achados[chave]
            e = entradas[chave]
            tratadas = sum(o["parece_tratado"] for o in ocorr)
            print(f"■ {chave}  [{e['categoria']}]  {len(ocorr)} ocorrência(s), "
                  f"{tratadas} parecem tratadas")
            if args.resumo:
                continue
            print(f"  Windows: {lado(e.get('windows'))}")
            print(f"  macOS:   {lado(e.get('macos'))}")
            print(f"  ⚠ {e['armadilha']}")
            if e.get("regra"):
                print(f"  → {e['regra']}")
            for o in ocorr:
                marca = "✓?" if o["parece_tratado"] else "  "
                print(f"   {marca} {o['arquivo']}:{o['linha']}  {o['texto']}")
            print()
        print(f"{len(achados)} linha(s) da matriz tocadas · {pendentes} ocorrência(s) sem sinal "
              f"de tratamento. Revise cada uma contra transversal/matriz-de-plataforma.md.")
    return 1 if (args.falhar and pendentes) else 0


if __name__ == "__main__":
    raise SystemExit(main())

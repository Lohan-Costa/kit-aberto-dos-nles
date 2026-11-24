"""instalar.py — liga as skills do KIT ABERTO DOS NLEs ao Claude Code DESTA máquina.

    python3 instalar.py             # macOS e Linux   (no Windows: py instalar.py)
    python3 instalar.py --conferir  # só diz o que está ligado

O que faz (e só isto): para cada pasta com um SKILL.md em `skills/` e em `bancodedadosnles/skills/`, cria em
`~/.claude/skills/<nome>` um ATALHO para a pasta do kit — assim a skill segue o kit sem cópia: atualizou o kit, a
próxima sessão já lê a skill nova. No macOS é um symlink; no Windows, uma junção (`mklink /J`), que não exige
administrador. Não baixa nada, não instala programa, não mexe fora de `~/.claude/skills/`. Se já existir ali uma pasta
de verdade com o mesmo nome, ela NÃO é tocada (o script avisa).

A lógica do atalho é a do banco (`bancodedadosnles/skills/instalar.py`, medida nos dois sistemas).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = Path(__file__).resolve().parent
ORIGENS = (KIT / "skills", KIT / "bancodedadosnles" / "skills")


def _banco():
    spec = importlib.util.spec_from_file_location("instalar_do_banco", KIT / "bancodedadosnles" / "skills" / "instalar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def skills() -> list[Path]:
    achadas = []
    for origem in ORIGENS:
        if origem.is_dir():
            achadas += sorted(p for p in origem.iterdir()
                              if p.is_dir() and not p.name.startswith((".", "_")) and (p / "SKILL.md").is_file())
    return achadas


def main() -> int:
    b = _banco()
    conferir = "--conferir" in sys.argv
    achadas = skills()
    if not achadas:
        print(f"nenhuma skill achada em {', '.join(map(str, ORIGENS))}")
        return 1
    ruim = False
    for skill in achadas:
        link = b.DESTINO / skill.name
        if conferir:
            alvo = b.aponta_para(link)
            estado = "ligada" if alvo == Path(os.path.realpath(skill)) else (
                f"aponta para OUTRO lugar: {alvo}" if alvo else "não ligada")
        else:
            estado = b.ligar(skill)
        ruim |= estado.startswith(("⛔", "aponta")) or estado == "não ligada"
        print(f"{skill.name:20s} {estado}")
    if not conferir:
        print("\nAbra uma sessão NOVA do Claude Code: as skills são lidas quando ela começa.")
    return 1 if ruim else 0


if __name__ == "__main__":
    raise SystemExit(main())

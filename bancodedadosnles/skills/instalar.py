"""
instalar.py — liga as skills do banco ao Claude Code DESTA máquina.

    python3 skills/instalar.py            # macOS  (no Windows: py skills\\instalar.py)
    python3 skills/instalar.py --conferir # só diz o que está ligado

Cria `~/.claude/skills/<skill>` apontando para `bancodedadosnles/skills/<skill>`, para a skill
seguir o banco sem cópia: mudou o SKILL.md no SSD, a próxima sessão já lê o novo.

⛔ **Por máquina, e não um atalho dentro do SSD.** Skill de projeto só é procurada até a raiz
do repositório, e cada app é um repositório. E atalho criado no macOS dentro de um disco exFAT
vira um arquivo `XSym` de 1 KB que o Windows não segue — a armadilha registrada em
`transversal/matriz-de-plataforma.md` (seção C). Por isso o link mora no disco da máquina:

- macOS: symlink (APFS).
- Windows: **junction** (`mklink /J`), que não exige administrador nem Modo Desenvolvedor —
  symlink de diretório exige.

⚠️ A letra do SSD no Windows pode mudar entre sessões: se a skill sumir, rode de novo.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ORIGEM = Path(__file__).resolve().parent
DESTINO = Path.home() / ".claude" / "skills"


def skills() -> list[Path]:
    return sorted(p for p in ORIGEM.iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_")) and (p / "SKILL.md").is_file())


def aponta_para(link: Path) -> Path | None:
    try:
        return Path(os.path.realpath(link)) if link.exists() or link.is_symlink() else None
    except OSError:
        return None


def ligar(skill: Path) -> str:
    link = DESTINO / skill.name
    alvo_atual = aponta_para(link)
    if alvo_atual is not None and alvo_atual == Path(os.path.realpath(skill)):
        return "já ligada"
    if link.exists() or link.is_symlink():
        if not (link.is_symlink() or _e_junction(link)):
            return f"⛔ {link} existe e é uma pasta de verdade — não mexi. Apague-a se for velha."
        link.unlink() if link.is_symlink() else os.rmdir(link)   # rmdir remove só a junction
    DESTINO.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(skill)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return f"⛔ mklink falhou: {(r.stderr or r.stdout).strip()}"
    else:
        link.symlink_to(skill, target_is_directory=True)
    # ⭐ Cheque se FUNCIONA, não se EXISTE (matriz, regra 7): o SKILL.md tem de ser legível pelo link.
    if not (link / "SKILL.md").is_file():
        return "⛔ o link foi criado mas o SKILL.md não é legível por ele"
    return "ligada"


def _e_junction(p: Path) -> bool:
    try:
        return os.name == "nt" and bool(os.readlink(p))
    except OSError:
        return False


def main() -> int:
    conferir = "--conferir" in sys.argv
    achadas = skills()
    if not achadas:
        print(f"nenhuma skill em {ORIGEM}")
        return 1
    ruim = False
    for skill in achadas:
        link = DESTINO / skill.name
        if conferir:
            alvo = aponta_para(link)
            estado = "ligada" if alvo == Path(os.path.realpath(skill)) else (
                f"aponta para OUTRO lugar: {alvo}" if alvo else "não ligada")
        else:
            estado = ligar(skill)
        ruim |= estado.startswith("⛔") or estado.startswith("aponta") or estado == "não ligada"
        print(f"{skill.name:24s} {estado}\n{'':24s} {link} → {skill}")
    if not conferir:
        print("\nAbra uma sessão NOVA do Claude Code: as skills são lidas na partida.")
    return 1 if ruim else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Gancho PreToolUse do Claude Code: antes de rodar, diz o que o banco já sabe da operação (autor, 2026-10-31).

Lê `transversal/operacoes.md` (a tabela é a fonte única: um humano lê a mesma linha que o gancho usa), procura os
gatilhos no comando (Bash/PowerShell) ou no código que vai ser escrito (Write/Edit) e devolve o aviso como contexto
adicional. Uma vez por sessão para cada linha. Nunca bloqueia: qualquer falha aqui sai calada com 0 — um gancho que
quebra não pode parar o trabalho.

Configuração (settings.json do usuário):
    "hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell|Write|Edit",
        "hooks": [{"type": "command", "command": "py -3 \\"D:/PROGRAMAS COM CLAUDE/bancodedadosnles/ganchos/operacoes_conhecidas.py\\""}]}]}
    (no Mac: python3 "/Volumes/<SSD>/PROGRAMAS COM CLAUDE/bancodedadosnles/ganchos/operacoes_conhecidas.py" — pendente)
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

INDICE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transversal", "operacoes.md")


def linhas_do_indice(caminho: str = INDICE) -> list[tuple[list[str], str, str]]:
    """[(gatilhos, aviso, onde)] das linhas da tabela cuja 1ª coluna tem gatilhos entre crases."""
    out = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            if not linha.startswith("| `"):
                continue
            cols = [c.strip() for c in linha.strip().strip("|").split(" | ")]
            if len(cols) < 3:
                continue
            gatilhos = re.findall(r"`([^`]+)`", cols[0])
            out.append((gatilhos, cols[1], cols[2]))
    return out


def texto_da_chamada(entrada: dict) -> str:
    ti = entrada.get("tool_input") or {}
    partes = [ti.get(k) or "" for k in ("command", "content", "new_string")]
    for e in ti.get("edits") or []:
        partes.append(e.get("new_string") or "")
    return "\n".join(p for p in partes if isinstance(p, str))


def avisos(texto: str, indice, ja_ditos: set[int]) -> list[tuple[int, str]]:
    baixo = texto.lower()
    out = []
    for i, (gatilhos, aviso, onde) in enumerate(indice):
        if i in ja_ditos:
            continue
        achados = [g for g in gatilhos if g.lower() in baixo]
        if achados:
            out.append((i, f"• {', '.join(achados)} — {aviso} (banco: {onde})"))
    return out


def main() -> int:
    try:
        bruto = sys.stdin.buffer.read()
        # UTF-8 com ou sem BOM (o pipe do PowerShell 5 manda BOM); o Claude Code manda UTF-8 puro
        entrada = json.loads(bruto.decode("utf-8-sig", errors="replace") or "{}")
        texto = texto_da_chamada(entrada)
        if not texto:
            return 0
        sessao = re.sub(r"[^A-Za-z0-9_-]", "", str(entrada.get("session_id") or "sem"))[:64]
        estado = os.path.join(tempfile.gettempdir(), f"ciclo_operacoes_{sessao}.json")
        try:
            ja = set(json.load(open(estado, encoding="utf-8")))
        except (OSError, ValueError):
            ja = set()
        novos = avisos(texto, linhas_do_indice(), ja)
        if not novos:
            return 0
        json.dump(sorted(ja | {i for i, _ in novos}), open(estado, "w", encoding="utf-8"))
        msg = ("⭐ O BANCO JÁ SABE desta operação (bancodedadosnles/transversal/operacoes.md). "
               "Leia antes de seguir; se o que você ia fazer contradiz isto, pare e reveja:\n"
               + "\n".join(a for _, a in novos))
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}},
                         ensure_ascii=False))
    except Exception:  # noqa: BLE001 — gancho nunca derruba a ferramenta
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

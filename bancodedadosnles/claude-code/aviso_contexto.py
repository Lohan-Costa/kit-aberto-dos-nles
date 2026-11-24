"""Gancho PostToolUse: aviso de CONTEXTO (pedido do autor, 2026-10-11).

A linha de status (statusline.ps1) grava em ~/.claude/state/ctx_<sessão>.txt o percentual de contexto ocupado.
A partir de 85 % este gancho devolve um `additionalContext` pedindo: terminar a tarefa em curso (sem cortá-la no
meio), fazer o CHECKPOINT (handoff, banco de NLEs, commit) e não começar tarefa nova. Para não repetir a cada
ferramenta, avisa de novo só a cada +3 pontos (85, 88, 91…). Silencioso abaixo do limite ou sem o arquivo.
"""
import json
import os
import sys

LIMITE, PASSO = 85, 3

try:
    entrada = json.load(sys.stdin)
except Exception:
    sys.exit(0)
sid = entrada.get("session_id") or ""
estado = os.path.join(os.path.expanduser("~"), ".claude", "state")
try:
    with open(os.path.join(estado, f"ctx_{sid}.txt"), encoding="ascii") as f:
        pct = int(float(f.read().strip() or 0))
except (OSError, ValueError):
    sys.exit(0)
if pct < LIMITE:
    sys.exit(0)
marca = os.path.join(estado, f"ctx_{sid}_avisado.txt")
try:
    with open(marca, encoding="ascii") as f:
        ultimo = int(f.read().strip() or 0)
except (OSError, ValueError):
    ultimo = 0
if ultimo and pct < ultimo + PASSO:
    sys.exit(0)
try:
    with open(marca, "w", encoding="ascii") as f:
        f.write(str(pct))
except OSError:
    pass
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": (
    f"⚠️ CONTEXTO EM {pct}% (limite do autor: 85%). Termine a tarefa que está em andamento sem cortá-la no meio; "
    "depois faça o CHECKPOINT: atualizar o handoff do projeto (.dev/HANDOFF.md), registrar no bancodedadosnles o que "
    "foi descoberto, commitar, e então PARAR de puxar tarefa nova. Diga ao autor que o contexto chegou ao limite e que "
    "a sessão está pronta para o /clear (ou, num revezamento autorizado, encerre a rodada).")}}, ensure_ascii=True))

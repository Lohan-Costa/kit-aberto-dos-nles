#!/usr/bin/env bash
# Linha de status do Claude Code no macOS (o par do windows/statusline.ps1) — instalada por claude-code/instalar.py.
#   Opus 5.5  ctx ███░░░░░░░ 31%   5h ██░░░░░░░░ 18%  resets in 3h12m
# - ctx: quanto da janela de contexto da sessão está ocupado. Aos 85 % o gancho aviso_contexto.py pede o checkpoint.
# - 5h:  quanto do limite de uso da janela de 5 horas do plano já foi gasto, e quanto falta para zerar.
# Cores iguais às do Windows: verde < 70 %, amarelo 70–89 %, vermelho ≥ 90 %.
# ⭐ Grava o percentual do contexto em ~/.claude/state/ctx_<sessão>.txt: sem isso o gancho do aviso fica mudo
# (era o caso da linha antiga do Mac, ~/.claude/statusline-command.sh, até 2026-11-06).
input=$(cat)

j() { printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null; }
model=$(j '.model.display_name'); [ -n "$model" ] || model="?"
sid=$(j '.session_id')
ctx=$(j '.context_window.used_percentage')
five=$(j '.rate_limits.five_hour.used_percentage')
resets=$(j '.rate_limits.five_hour.resets_at')

ESC=$'\033'; GREEN="$ESC[32m"; YELLOW="$ESC[33m"; RED="$ESC[31m"; CYAN="$ESC[36m"; DIM="$ESC[2m"; RESET="$ESC[0m"
export LC_NUMERIC=C

inteiro() { printf '%s' "$1" | awk '{printf "%d", $1}'; }
barra() { awk -v p="$1" 'BEGIN{n=10; f=int(p*n/100); if(f<0)f=0; if(f>n)f=n; s=""; for(i=0;i<f;i++)s=s"█"; for(i=f;i<n;i++)s=s"░"; printf "%s", s}'; }
cor() { if [ "$1" -ge 90 ]; then printf '%s' "$RED"; elif [ "$1" -ge 70 ]; then printf '%s' "$YELLOW"; else printf '%s' "$GREEN"; fi; }

if [ -n "$ctx" ]; then
  c=$(inteiro "$ctx")
  if [ -n "$sid" ]; then
    mkdir -p "$HOME/.claude/state" 2>/dev/null && printf '%s' "$c" > "$HOME/.claude/state/ctx_$sid.txt" 2>/dev/null
  fi
  linha="${CYAN}${model}${RESET}  ctx $(cor "$c")$(barra "$c")${RESET} ${c}%"
else
  linha="${CYAN}${model}${RESET}  ctx ${DIM}░░░░░░░░░░ --%${RESET}"
fi

if [ -n "$five" ]; then
  f=$(inteiro "$five")
  linha="$linha   5h $(cor "$f")$(barra "$f")${RESET} ${f}%"
  if [ -n "$resets" ]; then
    falta=$(( $(inteiro "$resets") - $(date +%s) ))
    if [ "$falta" -gt 0 ]; then
      linha="$linha  ${DIM}resets in $((falta / 3600))h$(((falta % 3600) / 60))m${RESET}"
    fi
  fi
fi

printf '%s' "$linha"

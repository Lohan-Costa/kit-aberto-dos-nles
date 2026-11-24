#!/bin/bash
# reload.sh — mata o gateway do Panel SDK para forçar um registro limpo dos
# plugins no próximo boot do Media Composer.
#
# POR QUE: o avid-api-gateway NÃO morre junto com o MC — vira órfão (PPID=1) e
# continua escutando 4920/4930. No boot seguinte o MC REUTILIZA esse órfão (com
# estado de registro velho) em vez de subir um limpo, e os plugins novos/atualizados
# não registram (some do menu Extensions). O 'panelsdk reinit' seria o jeito oficial,
# mas está quebrado nesta build (disca IPv4 contra gateway IPv6-only).
#
# FLUXO recomendado para recarregar um .avpi atualizado:
#   1) Feche o Media Composer (Cmd+Q)
#   2) ./reload.sh
#   3) Reabra o Media Composer  ->  Extensions > Test Panel
#
# Rodar com o MC ABERTO tambem mata o gateway, mas o MC provavelmente sobe outro
# na hora e NAO re-registra -> por isso o fluxo pede MC fechado.

GW=$(pgrep -f "avid-api-gateway" || true)
MC=$(pgrep -f "MacOS/AvidMediaComposer" | while read p; do
       # ignora o proprio gateway (que casa o padrao acima parcialmente)
       ps -p "$p" -o command= | grep -q "MacOS/AvidMediaComposer$" && echo "$p"
     done)

if [ -n "$MC" ]; then
  echo "AVISO: Media Composer parece ABERTO (pid $MC)."
  echo "Para recarregar de forma confiavel, feche o MC ANTES de rodar isto."
  echo "Vou matar o gateway mesmo assim, mas talvez o MC suba outro sem re-registrar."
  echo
fi

if [ -z "$GW" ]; then
  echo "gateway: nenhum processo rodando (nada a matar). Slate ja limpo."
else
  echo "matando gateway: $GW"
  kill $GW 2>/dev/null || true
  sleep 1
  GW2=$(pgrep -f "avid-api-gateway" || true)
  if [ -n "$GW2" ]; then
    echo "ainda vivo, SIGKILL: $GW2"
    kill -9 $GW2 2>/dev/null || true
    sleep 1
  fi
fi

# confirmar portas livres
if lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -qE ":(4920|4930|910[0-9]|9110) "; then
  echo "ATENCAO: ainda ha algo escutando nas portas do Panel SDK:"
  lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E ":(4920|4930|910[0-9]|9110) " | awk '{print "  ",$1,$2,$9}'
else
  echo "OK: portas 4920/4930/9100-9110 livres. Pode abrir o Media Composer."
fi

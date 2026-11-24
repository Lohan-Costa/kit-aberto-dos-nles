#!/bin/bash
# Duplo clique (Mac): gera os casos do pacote Base e confere cada arquivo.
# A mídia sai em saida/base/<caso>/ (pode apagar: este arquivo refaz).
cd "$(dirname "$0")" || exit 1
export PYTHONPYCACHEPREFIX="$HOME/Library/Caches/laboratorio-de-midia/pyc"
falhou=0
for receita in receitas/base/*.json; do
  python3 -m lab.gerar "$receita" --verificar || falhou=1
done
echo
if [ $falhou = 0 ]; then echo "Tudo gerado e conferido. A mídia está em saida/base."; else echo "ALGO NÃO CONFERIU — veja acima."; fi
read -n 1 -s -r -p "Aperte qualquer tecla para fechar."

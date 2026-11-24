# CLAUDE.md

A regra de trabalho deste kit está no `AGENTS.md` (o padrão que outras IAs também leem). Ela vale inteira aqui:

@AGENTS.md

## Só para o Claude Code

- **As skills:** se `ciclo-media-dev`, `piloto` ou as `ciclo-*` não aparecerem na lista de skills desta máquina, mostre
  à pessoa o que o `instalar.py` faz e, com o ok dela, rode `python3 instalar.py` (no Windows, `py instalar.py`).
- **A memória do Claude é presa ao caminho da pasta.** Se a pessoa mover o kit de lugar, a próxima sessão começa sem a
  memória: antes de mover, combine com ela (a memória fica em `~/.claude/projects/<caminho da pasta>`).
- **Contexto cheio:** ao chegar perto do limite, termine a tarefa em curso, atualize o `local/HANDOFF.md`, registre o
  que descobriu e avise a pessoa que a sessão está pronta para recomeçar (`/clear`) a partir do handoff.

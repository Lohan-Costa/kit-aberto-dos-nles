---
name: ciclo-seguranca
description: Proteger os dados de quem usa o KIT ABERTO DOS NLEs e a máquina dela — segredos e dados de cliente fora do Git, a varredura antes de todo commit, ler código antes de rodar, e o teste de segurança do próprio app (portas locais, a rota do MCP, o Claude restrito).
when_to_use: Antes de qualquer commit ou envio; ao instalar ou atualizar o kit ou o app; antes de rodar um script que veio de fora (contribuicoes/, uma atualização, a internet); quando a pessoa perguntar se é seguro; para revisar o Ciclo Assist instalado nesta máquina.
---

# Segurança: o que é da pessoa fica com ela

## Sempre

- **Antes de todo commit** no kit ou no app: `python3 ferramentas/varredura.py` (o que vai ao Git) e resolva cada
  apontamento. Segredo (`.env`, chave, token) nunca vai — nem "só por um commit": o histórico guarda.
- **Ler antes de rodar**: instalador, atualização, script de `contribuicoes/` ou da internet. Diga à pessoa o que o
  código faz (que arquivos toca, que rede usa, o que instala) antes de executar.
- **Dados de cliente** (nomes, caminhos, mídia, projetos, fotos de tela) ficam em `local/` ou nas pastas da pessoa;
  nunca no banco público, nunca num relato sem anonimizar.
- **Menor permissão:** não peça administrador se não precisar; não mude configuração global do sistema sem perguntar.

## O teste de segurança do app (Ciclo Assist), quando a pessoa pedir

Com o app instalado nesta máquina, confira e relate (sem atacar nada fora da máquina dela):
1. **As portas locais** que o app abre: só em `127.0.0.1`/`::1`, nunca na rede (`lsof -iTCP -sTCP:LISTEN -P` no macOS;
   `netstat -ano` no Windows).
2. **As rotas**: as que mudam algo exigem a mesma origem; a rota do MCP só responde com o segredo no caminho.
3. **O Claude que o app chama** (`claude -p`): com `--strict-mcp-config`, `--restricted` e `--tools ""` — sem as três, a
   caixa de chat do app teria acesso ao computador. O que o app expõe ao modelo são só as ferramentas dele.
4. **O que fica em disco** (a pasta de dados do app): nenhum segredo legível por outros usuários.
Registre o achado em `local/` e, se for defeito do app, proponha contribuir (sem detalhes que sirvam de ataque).

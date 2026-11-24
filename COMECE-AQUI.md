# COMECE AQUI — instruções para o Claude

Você (Claude — o recomendado e testado —, ou outra IA com funções agênticas, que vai precisar se recalibrar por conta e risco de quem a usa) recebeu este link de uma pessoa que trabalha com pós-produção de vídeo. Este é o **KIT ABERTO
DOS NLEs**: um banco do que já se mediu sobre os programas de edição (Avid Media Composer, Adobe Premiere Pro, DaVinci
Resolve, Baselight), um piloto para operar a máquina onde a API do programa não alcança, um laboratório que gera mídia
sintética para testar, e um app aberto (Ciclo Assist) para sincronizar e conformar. A ideia: **scripts e apps que rodam
sem IA para o que é mecânico, e você orquestrando** — no ambiente DESSA pessoa, aprendendo com ele.

Fale com a pessoa em português, em linguagem de quem edita, sem jargão de programação. Ofereça gestos simples (um
clique, um "pode seguir"), nunca comandos soltos para ela colar.

## Passo 0 — onde você está?

Antes de qualquer coisa, veja se você consegue **rodar comandos e ler arquivos no computador dessa pessoa**.

**Não consegue** (você está no navegador ou no celular, em claude.ai, ou numa sessão na nuvem que não enxerga o
computador dela): não finja. Diga, em poucas linhas, que o kit precisa de um Claude que trabalhe no computador onde ficam
os programas de edição, e ofereça os dois caminhos:

1. **O app Claude** no computador, Mac ou Windows (https://claude.ai/download), com o **Claude Code** dentro dele — o caminho
   mais simples para quem não é técnico.
2. **O Claude Code no terminal** (macOS) ou no **PowerShell** (Windows) — a melhor experiência. A instalação está na
   página oficial: https://code.claude.com/docs

Depois de instalado, ela abre o Claude Code numa pasta de trabalho e **manda este mesmo link de novo**. Você pode
resumir o que o kit faz (as seções abaixo), mas não tente executar nada daqui.

**Consegue**: siga.

## Passo 1 — combinar com a pessoa

- Explique em três linhas o que vai fazer: baixar o kit numa pasta, ler as instruções dele e fazer um diagnóstico da
  máquina (sistema, programas de edição e versões). Nada sai do computador dela sem o "pode" dela.
- Pergunte **onde guardar o kit** (sugira uma pasta própria, fora de pastas de projetos de clientes).

## Passo 2 — baixar o kit

- Com o Git: `git clone https://github.com/Lohan-Costa/kit-aberto-dos-nles.git` na pasta combinada.
- Sem o Git: baixe o `.zip` de https://github.com/Lohan-Costa/kit-aberto-dos-nles/archive/refs/heads/main.zip e
  descompacte.
- ⚠️ Se a raiz do kit ainda não tiver o `AGENTS.md`, o kit está **em preparação** (por enquanto só esta porta de
  entrada e a página estão publicadas): diga isso à pessoa, resuma o que o kit vai fazer e não instale nada. Ela pode
  acompanhar o repositório (Watch → Releases) e as "Últimas atualizações" da página, e voltar depois.

## Passo 3 — ler e instalar

- Leia o `AGENTS.md` da raiz do kit: é a regra de trabalho (o método, a segurança, os modelos).
- **Leia o código antes de rodar** — inclusive o do kit. O instalador põe as skills `ciclo-*` no Claude Code desta
  máquina; mostre à pessoa o que ele vai fazer e rode com o ok dela.

## Passo 4 — o diagnóstico (a primeira sessão)

Use a skill `ciclo-diagnostico`: levante o sistema, os programas de edição e as versões, o ffmpeg, a GPU; rode a
verificação de plataforma; proponha uma bateria curta do laboratório com mídia sintética para ver o que funciona NESTA
máquina; registre o resultado na camada LOCAL (privada) do banco.

## O que vale sempre

- **Privacidade:** nome de cliente, de produção, de pessoa, caminhos e mídia da pessoa ficam na máquina dela. Para
  contribuir com o kit, você generaliza, anonimiza, mostra o que vai sair e só envia com o "pode enviar".
- **Medir antes de afirmar:** consulte o banco antes; prove com mídia sintética; registre com a confiança
  (`confirmado` / `inferido` / `hipotese`), a versão do programa e o sistema.
- **Modelos:** Opus para investigar, desenvolver e orquestrar; Sonnet para executar e olhar imagens; script para o que
  é mecânico.
- **O piloto** (mouse e teclado) só com o pedido da pessoa ("pode pilotar"), com o freio explicado antes.

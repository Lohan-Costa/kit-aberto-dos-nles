---
name: ciclo-diagnostico
description: A primeira sessão do KIT ABERTO DOS NLEs numa máquina — levantar o sistema, os programas de edição e as versões, rodar a verificação de plataforma e uma bateria curta do laboratório com mídia sintética, e registrar em local/ o que funciona NESTE ambiente.
when_to_use: Na primeira sessão depois de baixar o kit; quando a pessoa trocar de máquina, de sistema ou de versão de um programa de edição; quando ela perguntar "o que dá para fazer aqui?"; quando um fato do banco não bater com o que se vê nesta máquina.
---

# O diagnóstico: o que funciona nesta máquina

O banco foi medido em outras máquinas. Esta skill descobre o que vale NESTA, sem tocar em trabalho da pessoa.

## 1. Combinar (uma linha)

Diga que vai levantar a máquina e rodar testes com mídia sintética, que nada sai do computador e que nenhum projeto
dela será aberto. Pergunte se algum programa de edição está aberto com trabalho não salvo: se estiver, não feche nada.

## 2. Levantar (só leitura)

- Sistema e versão; processador e GPU; memória; espaço livre nos discos.
- Python (3.10 ou mais novo), `ffmpeg` e `ffprobe`, Git, e o Claude Code (versão).
- Os programas de edição instalados e as versões: Media Composer, Premiere Pro, DaVinci Resolve (gratuito ou Studio —
  a API externa é só do Studio), Baselight. No macOS: `/Applications`; no Windows: `Program Files` e o registro.
  As pastas e os nomes de processo de cada um, nos dois sistemas: `bancodedadosnles/transversal/matriz-de-plataforma.md`.
- Para cada programa, a via que o banco conhece para aquela versão (a tabela "Como se fala com cada programa" do
  `AGENTS.md`) e se ela está disponível aqui (ex.: Resolve gratuito = sem API externa; só arquivo e piloto).

## 3. Conferir

- **O ambiente de testes** (uma vez; com o ok da pessoa — instala dois pacotes numa pasta só do kit, nada no sistema):
  - macOS: `python3 -m venv .venv` e `.venv/bin/pip install pytest pillow`
  - Windows: `py -m venv .venv` e `.venv\Scripts\pip install pytest pillow`
  A pasta `.venv/` fica na raiz do kit e o `.gitignore` já a ignora. O Python que já vem no macOS (3.9) basta para o
  kit; o app (Ciclo Assist) pede 3.11 ou mais novo e tem o instalador dele.
- `python3 bancodedadosnles/verificar_plataforma.py laboratorio-de-midia --sem-testes --so-pendentes` (Windows: `py`).
- Os testes que não precisam de programa aberto: `.venv/bin/python -m pytest laboratorio-de-midia/tests piloto/tests -q`
  (Windows: `.venv\Scripts\python`). Nenhum deve FALHAR; vários PULAM e dizem por quê — dado de produção real que
  não vem no kit, ou recurso só do outro sistema. Conte os que pulam e diga à pessoa o motivo de cada grupo.
- Gere uma amostra sintética (skill `ciclo-laboratorio`) e confira com `ffprobe` que o arquivo diz o que é.
- **Sem `ffmpeg`/`ffprobe`** (com o ok da pessoa): macOS com Homebrew → `brew install ffmpeg`; Windows → `winget install
  Gyan.FFmpeg` (ou `choco install ffmpeg`) e abrir um terminal novo; Mac Intel → o Homebrew não serve mais: os binários
  estáticos em `~/Library/Application Support/laboratorio-de-midia/ffmpeg/` (relato da comunidade; não temos Mac Intel).
  Esses caminhos são os que o robô `maquina-limpa` do GitHub refaz do zero a cada envio (Mac e Windows novos).

## 4. Propor a bateria

Com o que achou, proponha à pessoa (e só rode com o "pode"): para cada programa instalado, uma bancada curta do
laboratório que abre o programa, importa a mídia sintética e mede o resultado. O piloto só entra se ela pedir.

## 5. Registrar e dizer

- `local/diagnostico.md`: a data, a máquina, cada programa com a versão e a via, o que passou, o que pulou e por quê,
  o que falhou (com a mensagem exata).
- Fato novo que vale para outras pessoas (ex.: uma versão de programa que o banco não conhece) → registre no banco como
  `inferido`/`pendente`, com a versão e o sistema, e sugira contribuir (skill `ciclo-contribuir`).
- Diga à pessoa, em poucas linhas e em linguagem de quem edita: o que dá para fazer agora, o que falta instalar e o que
  ainda não foi medido nesta combinação de sistema e versões.

# KIT ABERTO DOS NLEs

Um kit aberto para o Claude — ou outra IA com funções agênticas — aprender a trabalhar no Avid Media Composer, no Adobe
Premiere Pro, no DaVinci Resolve e no Baselight, **na versão que você tem, inclusive nas antigas**, e a ligar esses
programas em fluxos que as fabricantes não oferecem. **Scripts e apps que rodam sem IA fazem o mecânico; a IA
orquestra**, no seu computador, aprendendo com o seu fluxo.

**A página do kit:** https://lohan-costa.github.io/kit-aberto-dos-nles/

## Como começar

Abra o Claude no computador onde ficam os seus programas de edição (o app Claude, com o Claude Code dentro, ou o Claude
Code no terminal) e mande esta mensagem:

```
Leia e siga as instruções deste link: https://raw.githubusercontent.com/Lohan-Costa/kit-aberto-dos-nles/main/COMECE-AQUI.md
```

Ele combina com você onde guardar o kit, baixa, lê as instruções, instala as skills (mostrando antes o que faz) e faz um
diagnóstico da sua máquina com mídia sintética — sem tocar no seu material.

## O que tem aqui

| pasta | o que é |
|---|---|
| `AGENTS.md` | a regra de trabalho da IA (o método, a privacidade, a segurança) |
| `bancodedadosnles/` | o banco: o que já se mediu dos formatos (AAF, XML, OTIO, EDL, ALE, AVB, PRPROJ, DRT, DRP, FLE, BLG), das APIs e do ambiente de cada programa, no Windows e no macOS, com a confiança e a versão |
| `piloto/` | o piloto e o vigia: a IA operando a máquina onde a API do programa não alcança, com freio |
| `laboratorio-de-midia/` | receitas de mídia sintética (cada quadro e canal diz o que é) e bancadas que medem cada programa |
| `skills/` | as skills do kit: diagnóstico, laboratório, contribuir, segurança, novidades |
| `contribuicoes/` | a quarentena: o que chega de outras pessoas, antes de ser reproduzido no laboratório |
| `ferramentas/` | a varredura de segurança (a mesma que o GitHub roda nos pull requests) |
| `docs/` | a página do kit |

O app **Ciclo Assist** (sincronizar, conformar, assistir) é aberto e vem em repositório próprio,
https://github.com/Lohan-Costa/ciclo-assist-kit-nle — clone-o DENTRO desta pasta, para ele achar o banco, o piloto e o
laboratório.

## Em que máquinas foi testado

O kit é medido em **Windows 11** e em **Mac com Apple Silicon**. **Mac Intel: não temos máquina para testar** — o que se
sabe dele vem da comunidade, pela pasta `contribuicoes/`. O primeiro relato (novembro de 2026): o Homebrew não instala
mais o ffmpeg num Mac Intel; o ffmpeg estático na pasta do laboratório
(`~/Library/Application Support/laboratorio-de-midia/ffmpeg/`) funciona, e o laboratório procura lá primeiro. Se você usa
um Mac Intel, o diagnóstico da sua máquina é das contribuições mais úteis.

## O método

O diferencial é **como se investiga**: consultar o banco antes; medir antes de afirmar (um render, um número, um
quadro); provar com mídia sintética; registrar depois, com a confiança, a versão do programa e o sistema. Opus investiga
e desenvolve, Sonnet executa e olha a tela, scripts fazem o mecânico.

## Privacidade

O que é seu fica na sua máquina: a pasta `local/` é a sua camada privada e não vai ao Git. Para contribuir, a IA
anonimiza, mostra o que vai sair e só envia com o seu "pode enviar". Tudo o que está neste repositório foi anonimizado:
produções, clientes e pessoas aparecem com apelidos (PRODUCAO-A, casa-pos-1…).

## Como as mudanças são anotadas

A seção "Últimas atualizações" da página lê o histórico deste repositório. Cada envio começa pelo tipo — `adicionado:`,
`corrigido:` ou `mudado:` (aceitos também `feat:` e `fix:`) — seguido de uma frase para quem edita. O resumo por versão
fica em `NOVIDADES.md`.

**Quem colabora é creditado, se quiser.** Quando uma contribuição de fora entra no kit, o envio leva uma linha
`Crédito: @usuario` (ou o nome que a pessoa escolheu) e a página mostra "com a colaboração de…" ao lado da mudança; o
`NOVIDADES.md` cita também. Quem preferir fica anônimo — o Claude de cada pessoa pergunta antes de enviar (skill
`ciclo-contribuir`).

## Licença

Código: Apache-2.0 (`LICENSE`) · Texto do banco: CC BY 4.0 (`LICENSE-banco-CC-BY-4.0`) · Ciclo Assist: GPL-3.0 (no
repositório dele). Idealizado por Lohan Costa, edt. As marcas dos programas citados são de seus donos (`NOTICE`).

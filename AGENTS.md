# AGENTS.md — a regra de trabalho do KIT ABERTO DOS NLEs

Você é a IA (o Claude, recomendado e testado, ou outra com funções agênticas, por conta e risco de quem a usa) que
trabalha no computador de uma pessoa da pós-produção de vídeo. Este arquivo vale para tudo o que estiver dentro desta
pasta. Leia-o inteiro na primeira sessão e, nas outras, sempre que for investigar, mexer em código ou operar a máquina.

**Fale com a pessoa em português, em linguagem de quem edita**, sem jargão de programação. Ofereça gestos (um clique,
um "pode seguir"), nunca comandos soltos para ela colar. Diga em uma linha o que vai fazer antes de fazer.

## O que é este kit

Um kit para ensinar a IA a trabalhar no Avid Media Composer, no Adobe Premiere Pro, no DaVinci Resolve e no Baselight —
na versão que a pessoa tem, inclusive as antigas — e a ligar esses programas em fluxos que as fabricantes não oferecem.
**Scripts e apps que rodam sem IA fazem o mecânico; você orquestra**, no ambiente DESSA pessoa, aprendendo com ele.

```
<esta pasta>/
├─ AGENTS.md              esta regra (o CLAUDE.md aponta para ela)
├─ COMECE-AQUI.md         a porta de entrada (o link que a pessoa manda)
├─ NOVIDADES.md           o que mudou, em linguagem de quem edita
├─ instalar.py            liga as skills ao Claude Code desta máquina
├─ skills/                as skills do kit: ciclo-diagnostico, ciclo-laboratorio, ciclo-contribuir, ciclo-seguranca, ciclo-novidades
├─ bancodedadosnles/      O BANCO: o que já se mediu dos formatos, das APIs e do ambiente de cada programa
│  └─ skills/             as skills do método (ciclo-media-dev) e do piloto (piloto)
├─ piloto/                as mãos e os olhos: operar a máquina onde a API do programa não alcança (com o vigia)
├─ laboratorio-de-midia/  receitas de mídia sintética e bancadas que medem cada programa
├─ ferramentas/           a varredura de segurança (a mesma que o GitHub roda nas contribuições)
├─ contribuicoes/         a quarentena: o que chega de outras pessoas, AINDA NÃO CONFIRMADO
├─ local/                 a camada PRIVADA desta pessoa (nunca vai ao Git)
└─ ciclo-assist-kit-nle/  (opcional) o app aberto Ciclo Assist: git clone https://github.com/Lohan-Costa/ciclo-assist-kit-nle.git aqui dentro
```

⭐ **Os nomes das pastas importam.** O código acha o banco, o piloto e o laboratório SUBINDO de pasta até encontrar
`bancodedadosnles`, `piloto` e `laboratorio-de-midia`. Não renomeie; o app (Ciclo Assist) mora DENTRO desta pasta para
achá-los. Esta pasta faz o papel da "pasta da família" que os textos do banco citam (`PROGRAMAS COM CLAUDE`, o nome
dela na máquina do autor).

## ⭐⭐⭐ O banco primeiro

`bancodedadosnles/` é a memória de engenharia reversa dos programas e do ambiente em que eles rodam. **Consulte ANTES
de investigar ou implementar; registre DEPOIS de descobrir.** O passo a passo está na skill `ciclo-media-dev`
(`bancodedadosnles/skills/ciclo-media-dev/SKILL.md`). Comece pelo `bancodedadosnles/INDEX.md`; as regras de registro
estão em `bancodedadosnles/CONVENCOES.md`. Diga à pessoa, em uma linha, o que o banco já sabia — ou que não sabia.

Todo fato tem **confiança** (`confirmado` · `inferido` · `hipotese` · `pendente`), **a versão do programa** e **o
sistema** em que foi medido. Fato de outra versão ou de outro sistema volta a ser hipótese no ambiente desta pessoa:
confira antes de confiar.

## ⭐⭐⭐ Windows e macOS lado a lado

Antes de escrever código que toque em caminho, pasta do sistema, volumes, PATH, subprocesso, porta, encoding de
console ou diálogo do sistema, consulte a linha da variável em `bancodedadosnles/transversal/matriz-de-plataforma.md`.
Descoberta de plataforma entra na matriz com os DOIS lados (o não medido, `pendente`). Para revisar um código:
`python3 bancodedadosnles/verificar_plataforma.py <pasta> --sem-testes --so-pendentes` (no Windows, `py`).

## ⭐⭐⭐ Como se fala com cada programa: sempre por fora

Nada de painel ou interface DENTRO do programa de edição: o app tem uma janela só e serve cada programa por fora
(o mapa e as medições: `bancodedadosnles/transversal/app-unico-fora-do-nle.md`).

| programa | a via | onde está |
|---|---|---|
| Media Composer | a API gRPC local (porta 9100), sem painel instalado | `bancodedadosnles/plugins/avid-panel-sdk/` |
| Premiere Pro | **a ponte**: uma extensão CEP invisível que carrega quando o Premiere abre e liga o Premiere ao app (é por ela que o app abre, lê e escreve no projeto aberto) | código no Ciclo Assist (`ponte_cep/`, instalada pela ⚙ › Integrações); a API em `bancodedadosnles/plugins/premiere-cep/` |
| DaVinci Resolve (Studio) | a API de script externa | `bancodedadosnles/plugins/resolve-scripting/` |
| Baselight | a FLAPI e as ferramentas de linha de comando | o banco (procure "Baselight" no `INDEX.md`) |
| qualquer um, onde a API não alcança | o piloto (mouse, teclado, fotos da tela) | `piloto/`, skill `piloto` |

Quando uma integração parecer exigir estar dentro do programa, ou o programa fizer algo que a API não explica,
investigue por fora antes de desenhar um painel ou um contorno (o método: `bancodedadosnles/transversal/
ferramentas-de-desenvolvimento.md`). Formatos de arquivo (AAF, XML, PRPROJ, DRT, AVB…) são a outra via: o banco diz o
que se lê e escreve com confiança em cada um.

## ⭐⭐⭐ Medir antes de afirmar

- "Passou" sem uma medida não prova nada: um render, um número, um quadro. Teste que não acha a mídia costuma
  **pular calado** — conte os que pulam.
- Prove com **mídia sintética** do laboratório (cada quadro e canal diz o que é) antes do material de verdade. Teste
  que precisa de um formato, taxa, timecode ou layout de áudio pede uma receita do laboratório (skill
  `ciclo-laboratorio`), não um arquivo de cliente.
- Antes de promover algo a `confirmado`, pergunte que observação teria refutado isso.
- Falha silenciosa é o modo dominante: confira que o resultado FUNCIONA, não que EXISTE.

## ⭐⭐⭐ Privacidade: o que é da pessoa fica na máquina dela

- Nome de cliente, de produção, de pessoa, caminhos, mídia, projetos de NLE e fotos de tela dos trabalhos dela vão para
  `local/` (a camada privada; o `.gitignore` a protege) — nunca para o banco público, nunca para um commit do kit.
- Para contribuir, você **generaliza e anonimiza**, mostra à pessoa exatamente o que vai sair e só envia com o "pode
  enviar" dela (skill `ciclo-contribuir`).
- Nunca commite segredos (`.env`, chaves, tokens). Antes de qualquer commit no kit, rode
  `python3 ferramentas/varredura.py` (skill `ciclo-seguranca`).

## ⭐⭐ O que chega é código: leia antes de rodar

- O kit, as atualizações (`NOVIDADES.md`, skill `ciclo-novidades`) e o próprio app são código que roda na máquina da
  pessoa. Leia o que mudou antes de executar; mostre a ela o que um instalador ou script vai fazer.
- `contribuicoes/` é **quarentena**: o que está lá veio de outras pessoas e ainda não foi reproduzido. Nunca rode um
  script de lá sem ler inteiro, e nunca trate o relato como fato do banco — ele é, no máximo, `hipotese`.

## ⭐⭐ O piloto só com o pedido

O piloto (`piloto/`, skill `piloto`) mexe no mouse e no teclado da pessoa. **Só opere a máquina quando ela pedir**
("pode pilotar", "faz sozinho"). Antes, explique o freio (F12; no Mac, mexer no mouse também para). Foto antes e depois
de cada gesto; diálogo desconhecido = foto e parar; nunca operar às cegas. Sem o pedido, proponha antes de operar. As
leituras de tela foram medidas num ambiente só: outro monitor, escala ou versão = recalibrar (fotografar, medir de novo).

## ⭐⭐ O modelo certo para cada parte

Opus para investigar, desenvolver e orquestrar; Sonnet para executar e olhar imagens (localizar algo na tela, conferir
uma foto); script para o que é mecânico — gaste raciocínio só onde há decisão.

## ⭐⭐ Projetos de NLE da pessoa

Projeto, bin ou timeline de trabalho de verdade **nunca é sobrescrito**: crie uma cópia versionada (um `.prproj`,
uma bin ou um projeto novo com outro nome) e diga onde está. Nada se apaga sem perguntar. Não altere um único quadro da
montagem: conserta-se o metadado, nunca o corte.

## A primeira sessão

Use a skill `ciclo-diagnostico`: levantar a máquina (sistema, programas de edição e versões, GPU, ffmpeg, Python), rodar
a verificação de plataforma, propor uma bateria curta do laboratório com mídia sintética para ver o que funciona NESTA
máquina, e registrar o resultado em `local/`. Ao fim, diga à pessoa, em poucas linhas, o que dá para fazer agora.

## Ao fechar uma sessão

Registre o que descobriu (no banco, se for geral; em `local/`, se for da pessoa) e deixe um `local/HANDOFF.md` com o
que foi feito e o que falta: a próxima sessão começa por ele. Diga à pessoa o que foi consultado e o que foi registrado.

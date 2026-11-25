---
name: ciclo-contribuir
description: Devolver ao KIT ABERTO DOS NLEs o que se aprendeu nesta máquina — generalizar e anonimizar, mostrar à pessoa exatamente o que vai sair, passar a varredura e enviar como relato na quarentena (contribuicoes/) ou como issue, só com o "pode enviar".
when_to_use: Quando se descobriu algo que vale para outras pessoas (uma versão de programa, um formato, um defeito, um contorno) e a pessoa topa contribuir; quando ela pedir "manda isso para o kit"; quando uma investigação travou e vale pedir ajuda a quem souber mais.
---

# Contribuir: generalizar, mostrar, enviar

⛔ Nada sai sem o "pode enviar" da pessoa, depois de ela ver o conteúdo final. Contribuir é opcional.

## 1. Generalizar e anonimizar

- Tire nome de cliente, de produção, de pessoa, de máquina e de usuário; caminhos pessoais (troque por
  `<pasta da mídia>`, `<projeto>`); e-mails; nomes de arquivo que identifiquem o trabalho.
- Mídia, projeto de NLE e foto de tela de trabalho real **não vão**. Se o caso precisa de um arquivo, reproduza-o com
  uma receita do laboratório (skill `ciclo-laboratorio`) e mande a receita.
- Diga o que se mediu, como, com que confiança (`confirmado` / `inferido` / `hipotese`), em que versão do programa e em
  que sistema. O que não se mediu é dito como não medido.

## 2. Escolher o caminho

- **Relato com arquivos** (o texto, o código que gerou, o teste sintético) → um pull request que cria SÓ
  `contribuicoes/<AAAA-MM-DD>-<assunto>/` (um `RELATO.md` com o modelo de `contribuicoes/LEIA-ME.md`, e os arquivos).
  Uma verificação automática recusa o pull request que mexer fora dessa pasta.
- **Relato sem arquivo, ou uma dúvida aberta** → uma issue com o modelo "relato de campo" ou "investigação aberta".

## 3. Perguntar sobre o crédito

Pergunte à pessoa, com estas opções, e anote a resposta na linha `Crédito:` do `RELATO.md` e do pull request:
- **Com o @ do GitHub** (`Crédito: @usuario`) — aparece nas "Últimas atualizações" da página e no `NOVIDADES.md`, com
  link para o perfil, quando a contribuição entrar no kit;
- **Com um nome** que ela escolher (`Crédito: Nome Sobrenome`, ou um apelido);
- **Anônima** (`Crédito: anônimo`) — não é citada nos créditos.

Seja honesto sobre o limite: o pull request (ou a issue) sempre mostra a conta do GitHub que o abriu. Quem não quer nem
isso pode mandar o relato a alguém que já contribui, ou esperar uma forma de envio sem conta.

## 4. Mostrar e conferir

1. Rode `python3 ferramentas/varredura.py contribuicoes/<pasta>` (segredos, caminhos pessoais, e-mails, mídia,
   tamanho) e resolva TODO apontamento.
2. Mostre à pessoa o conteúdo final, arquivo por arquivo (não um resumo), e pergunte se pode enviar.

## 5. Enviar (com o "pode enviar")

- Precisa de uma conta no GitHub (a pessoa cria; você não cria contas). Com o `gh` instalado e logado: fork do kit,
  um ramo, o commit SÓ da pasta da contribuição (mensagem começando por `adicionado:`), o pull request com o modelo.
- Sem o `gh`: prepare a pasta e o texto e guie a pessoa no site do GitHub, passo a passo.
- Diga onde ficou (o endereço do pull request ou da issue) e que um mantenedor vai reproduzir no laboratório antes de
  entrar no banco — e, se ela quis crédito, que o nome aparece quando entrar.

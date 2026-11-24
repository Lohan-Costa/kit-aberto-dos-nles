---
name: ciclo-media-dev
description: Método de desenvolvimento dos apps da Ciclo Media (plugins e painéis de Avid Media Composer, Premiere e DaVinci Resolve; AAF, AVB, PRPROJ, DRT, MXF; pipelines de mídia, ASR, decupagem; apps que rodam em Windows e macOS a partir do mesmo SSD). Guia a sessão a consultar o bancodedadosnles ANTES de investigar ou implementar, a conferir a matriz de plataforma antes de mexer em caminho/processo/disco, e a registrar no banco DEPOIS de descobrir.
when_to_use: No início de qualquer tarefa de desenvolvimento, investigação ou depuração num app da pasta PROGRAMAS COM CLAUDE; quando o assunto for formato de NLE, API/SDK de NLE, bin, timeline, mídia, timecode ou efeito; quando o código tocar caminho, pasta do sistema, PATH, subprocesso, porta, encoding ou diálogo do sistema; antes de levar um app de uma plataforma para a outra; ao fechar uma descoberta que outro app aproveitaria; e quando o usuário pedir para "conferir os bugs do mundo real" num app ou NLE, ou trouxer um bug achado em produção.
---

# Desenvolver na Ciclo Media: o banco primeiro

Os apps da família repetem as mesmas perguntas de baixo nível — e os mesmos erros. O
`bancodedadosnles` é a memória de engenharia reversa e de ambiente, e **só se paga quando é a
primeira parada, não a última** (o banco registra duas vezes a mesma armadilha redescoberta por
não ter sido consultado).

## 0. Achar o banco

Ele mora na raiz da pasta da família (`PROGRAMAS COM CLAUDE/bancodedadosnles`). Desde a arrumação
do SSD (2026-10-06) os apps ficam UM ou DOIS níveis abaixo (`2 ATIVOS/<app>`, `9 ARQUIVADOS/<grupo>/<app>`),
então **suba de pasta a partir da raiz do app até achar uma `bancodedadosnles`** — não use
`../bancodedadosnles` fixo, nem no código (o mesmo vale para `PROGRAMAS COM CLAUDE/CATALOGO.md`, que diz
onde mora cada app):

- a partir da raiz do app: subir até achar (hoje `../../bancodedadosnles` num ativo)
- macOS: `/Volumes/SSD/PROGRAMAS COM CLAUDE/bancodedadosnles`
- Windows: `<letra>:\PROGRAMAS COM CLAUDE\bancodedadosnles` (a letra do SSD varia)

Se não achar, **diga ao usuário** que o banco não está montado — não siga como se ele não existisse.

## 1. Antes de investigar ou implementar

1. Leia o topo do `INDEX.md` (a regra master e os destaques) e localize o tema.
2. Procure no banco os termos da tarefa — formato, chamada de API, nome de classe, a **frase exata
   de erro**: `grep -rn -i "<termo>" <banco> --include=*.md --include=*.json`.
3. Constantes e estruturas: `python3 <banco>/consulta.py listar` / `mostrar <id>` (no Windows, `py`).
4. Leia a nuance, não só o número: `confianca` (`confirmado` · `inferido` · `hipotese` ·
   `pendente`) e a **versão do app** em que foi medido. Fato de outra versão volta a ser hipótese.
5. Diga ao usuário, em uma linha, o que o banco já sabia (com o arquivo) — ou que não sabia.
6. **Bugs do mundo real:** abra `<banco>/transversal/bugs-do-mundo-real.json` e veja as fichas com
   `"estado": "conferir"` para o app × NLE desta sessão (os alvos têm o nome do app e do NLE, ex.
   "De Lá Pra Cá › Premiere"). Diga quantas são. Se a tarefa tocar o assunto de uma delas, ou se o
   usuário pedir para conferir, rode o `como_conferir` da ficha e troque o estado (`corrigido` com
   onde e data, `visto` se o bug estava lá — corrigir —, ou `nao_se_aplica` com o porquê).

## 2. Se o código tocar a plataforma

Caminho, pasta do sistema, volumes, PATH, binário externo, subprocesso, sinal, porta, encoding
de console, diálogo de pasta, arrasto de arquivo, pasta do NLE:

1. Consulte a linha da variável em `<banco>/transversal/matriz-de-plataforma.md` — **os dois
   lados**, Windows e macOS, e as 8 regras do topo.
2. Escreva o ramo das duas plataformas, ou marque explicitamente o que não foi feito.
3. Revise o repositório: `python3 <banco>/verificar_plataforma.py <repo> --sem-testes --so-pendentes`
   (e sem `--sem-testes` para ver os testes isolados só de um lado). Cada ocorrência sem `✓?`
   precisa de uma resposta: tratado, não se aplica, ou pendente.

## 3. Enquanto trabalha

- **Medir, não adivinhar.** Spike pequeno que sai 0 se passou; o número com a data.
- Antes de promover algo a `confirmado`, pergunte **que observação teria refutado isto**.
- Falha silenciosa é o modo dominante: confira que o artefato FUNCIONA, não que EXISTE.

## 4. Depois de descobrir — registrar

Siga `<banco>/CONVENCOES.md`:

- prosa no `.md` do tema (o quê, como foi descoberto, confiança, versão do app);
- constante que um app consumiria → também no `dados/*.json` (`_meta` obrigatório);
- `fontes.md` e `_meta.atualizado` com data absoluta; `INDEX.md` se criou tema;
- **plataforma → uma linha na matriz, com os DOIS lados** (o não medido entra `pendente`) e, se
  houver padrão de código reconhecível, `busca`/`tratado` no `matriz-de-plataforma.json`;
- corrigir fato errado com `CORRIGE:` e a data — nunca apagar a versão antiga em silêncio.
- **bug achado em produção real** (o usuário viu no NLE, não um teste) → depois de corrigir, uma ficha
  nova em `transversal/bugs-do-mundo-real.json` (e a linha da tabela no `.md`): sintoma em linguagem de
  editor, causa, a REGRA geral (o que qualquer outro app/NLE tem de conferir), `como_conferir` e o
  estado de CADA alvo conhecido — `conferir` quando não se sabe. É o que leva o conserto aos outros.

Ao fechar a tarefa, diga ao usuário o que foi consultado e o que foi registrado (arquivos).

## 4b. Contexto aos 85 % — checkpoint

Quando o aviso de contexto chegar (gancho `aviso_contexto.py`, a partir de 85 %): terminar a tarefa em curso, então
handoff do app + registro no banco + commit, e nenhuma tarefa nova; avisar o autor que a sessão está pronta para o
`/clear`. Revezamento autônomo só nos testes do laboratório e só a pedido do autor (regra no `CLAUDE.md` da família).

## 5. Antes de trocar de máquina

1. `verificar_plataforma.py` no repositório (seção 2).
2. Rodar a suíte **na outra plataforma**, com `PYTHONPYCACHEPREFIX` fora do SSD, e conferir que
   nada foi criado na pasta real do usuário.
3. Venv, `node_modules` e caches de modelo não atravessam — ver seção H da matriz.

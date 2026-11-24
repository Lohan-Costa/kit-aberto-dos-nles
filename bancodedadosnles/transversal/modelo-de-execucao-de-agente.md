# Modelo de execução: como a decisão de um agente chega na timeline

Entre "o LLM decidiu onde cortar" e "o corte existe no projeto" há uma escolha de arquitetura que
determina a velocidade percebida, a atomicidade, o undo e a portabilidade entre NLEs. **É a decisão
mais consequente de um assistente de edição, e a menos discutida.** Fatos consumíveis em
[modelo-de-execucao-de-agente.json](modelo-de-execucao-de-agente.json).

Escrito em 2026-08-09 a partir da medição de quatro produtos (ver
[`../plugins/premiere-cep/`](../plugins/premiere-cep/) e
[`../plugins/avid-panel-sdk/paineis-de-terceiros.md`](../plugins/avid-panel-sdk/paineis-de-terceiros.md))
mais a nossa própria implementação em produção.

## Os cinco modelos, e como cada um foi identificado

### 1. Estado-alvo declarativo — *Eddie AI*

O agente não descreve ações; descreve **o resultado**. O painel recebe uma sequência inteira como
dado (ou como XML) e a materializa de uma vez.

**Como isso foi medido:** varredura dos verbos de mutação em
`Eddie AI/jsx/PPRO/Premiere.jsx` (5.267 linhas). Resultado: **`overwriteClip` 11 vezes, e mais
nada** — zero `razor`, zero `split`, zero `trim`, zero `setPlayerPosition`, zero `createSubClip`.
Ele **nunca corta uma timeline existente**. Constrói: `createSequenceFromData`,
`addClipsToSequence`, `updateClipItemTime`, `ensureSequenceHasTracks`, `deleteEmptyTracks`. E a
alternativa é `importXMLToProject` / `importXMLAndResolveToTimeline`.

| | |
|---|---|
| Idas e voltas | **1** por sequência |
| Atomicidade | alta — ou a sequência nasce, ou não |
| Undo | um passo (ou nenhum: é objeto novo) |
| Limitação real | **só cria; não edita cirurgicamente o que já existe** |

### 2. Script gerado — *Premiere Copilot*

O servidor produz **código ExtendScript** e o painel executa. O painel é um interpretador burro.

**Como isso foi medido:** no bundle remoto de 2 MB há **exatamente 2 sítios de `evalScript`**, e os
dois são pontes genéricas:

```js
runExtendScript = (e) => new Promise((res, rej) =>
    new window.CSInterface().evalScript(e, s => s != null ? res(s) : rej(...)))
```

E há muito pouco ExtendScript literal no cliente (`app.project.rootItem`, `activeSequence`,
`videoTracks` 11×, `audioTracks` 27×). **Dois sítios de chamada não significam duas execuções** —
significa **uma ponte genérica chamada N vezes**. É exatamente a sensação que o usuário relatou:
a agulha andando e os cortes saindo ao vivo, devagar, porque cada passo espera resposta.

| | |
|---|---|
| Idas e voltas | 1 por script — mas o servidor manda muitos scripts pequenos |
| Atomicidade | nenhuma entre scripts: quebrar no meio deixa projeto pela metade |
| Undo | um passo por script → o usuário dá Cmd+Z quinze vezes |
| Vantagem | flexibilidade total: alcança qualquer API sem redeploy |
| Risco | executar código gerado por LLM dentro do projeto do cliente |

### 3. RPC fino — *Chat Video Pro*

O painel expõe **funções nomeadas** e o LLM as chama uma por uma, por *tool calling*.

**Como isso foi medido:** em `jsx/main_v2.jsx` (8.093 linhas) existem os verbos que faltam no
Eddie — `setPlayerPosition` (6), `overwriteClip` (6), `split` (4), `trim`, `insertClip`,
`applyPreset`, `remove(false)` — e no `bundle.js` aparecem `tool_calls` e `tool_choice`. Ou seja:
**o laço de ferramentas roda no cliente e cada ferramenta é uma micro-operação de timeline.**

| | |
|---|---|
| Idas e voltas | 1 ida ao LLM **+** 1 ao ExtendScript **por ação** |
| Atomicidade | nenhuma |
| Undo | um passo por ação |
| Vantagem | o agente reage ao estado real a cada passo (corrige rumo) |
| Custo | o pior dos cinco em latência e em tokens |

### 4. Autoração externa de arquivo — *nosso Órbita / RELINKER / DRAMASYNC*

O app escreve o **arquivo de projeto** (`.avb`, `.prproj`, `.drt`) e o NLE abre. Zero chamada de API.

Em produção desde 2026-08-08 no Media Composer (ver
[`../plugins/avid-panel-sdk/`](../plugins/avid-panel-sdk/)). Fidelidade máxima — preserva efeito,
rampa, multicam, metadado de cor, coisas que uma API de painel não expõe e que o OTIO perde.

| | |
|---|---|
| Idas e voltas | **0** |
| Atomicidade | total — o arquivo é válido ou não é |
| Undo | não se aplica (é arquivo novo) |
| Limitação | o NLE tem de **abrir/reler**; não altera o projeto aberto |

### 5. Comando nativo sem parâmetro — *Avid `DoCommand`*

Caso especial e instrutivo: o Media Composer tem 724 comandos (`MarkIN`, `MarkOUT`, `Overwrite`,
`Insert`) mas **nenhum aceita parâmetro**. Editar pela API obriga a sequência
"posiciona → marca → comanda", isto é, **força o modelo 3 mesmo que você não queira**, com o piso
medido de **~500 ms por chamada** e **nenhum canal de evento**.

⭐ **É por isso que no Avid a nossa forma é invertida** (a timeline é autorada, não comandada) —
não por preferência, mas porque a plataforma torna o RPC fino inviável. Um corte de 200 eventos
custaria 100 s só de latência de barramento.

## O quadro comparativo

| | 1. Estado-alvo | 2. Script gerado | 3. RPC fino | 4. Autoração de arquivo | 5. DoCommand |
|---|---|---|---|---|---|
| Quem decide | agente, de uma vez | servidor, passo a passo | LLM, passo a passo | agente, de uma vez | LLM, passo a passo |
| Round trips | 1 | N scripts | 2N | 0 | 3N, ~500 ms cada |
| Atomicidade | alta | nenhuma | nenhuma | total | nenhuma |
| Undo do usuário | 1 | N | N | — | N |
| Edita projeto aberto | cria novo | **sim** | **sim** | não | **sim** |
| Fidelidade de efeito/cor | média | média | média | **máxima** | baixa |
| Testável sem o NLE | parcial | não | não | **sim** | não |
| Exemplo medido | Eddie | Premiere Copilot | Chat Video Pro | Órbita/Avid | Avid API |

## ⭐ O meio que ninguém dos quatro ocupa: plano de ações como dado

A intuição de que **"deveria ser um mapa de ações executado de uma vez, não a agulha andando ao
vivo"** está certa, e o que falta nos quatro produtos é o mesmo: **o plano nunca existe como
objeto**. No modelo 2 ele existe como código; no 3, como histórico de chamadas; no 1, só o
resultado final.

A forma que resolve:

```
LLM  →  PLANO (JSON, NLE-neutro)  →  validador  →  executor do NLE  →  1 script que itera
                 ↑                        ↑                                    ↑
        versionável, diffável,    recusa antes de       um undo group,
        mostrável ao usuário      tocar no projeto      uma ida e volta
```

O que se ganha, item por item:

1. **Uma ida e volta.** O executor recebe o plano inteiro e itera **dentro** do ExtendScript. A
   latência deixa de multiplicar pelo número de eventos.
2. **Um `undoGroup`.** O usuário desfaz a operação, não trinta operações.
3. **Validação antes de tocar no projeto.** O plano é conferido contra as regras que já estão neste
   banco — a regra do áudio vinculado (`V k ↔ A k`), tempo em segundos no `overwriteClip`, tracks
   suficientes — e é **recusado inteiro** se não passar. Hoje esses erros aparecem no meio da
   execução, com o projeto já sujo.
4. **Testável sem NLE.** O plano é um *fixture*: dá para ter suíte de teste do agente sem abrir o
   Premiere. Nenhum dos quatro produtos consegue isso.
5. **Portável.** O plano é neutro; o executor é por NLE. **É o mesmo desenho que já usamos para
   formato** (um modelo neutro, N writers — ver [modelo-neutro-efeitos.md](modelo-neutro-efeitos.md)),
   aplicado a ação em vez de a estrutura.
6. **Auditável.** O plano é o que se mostra ao editor para aprovar antes de aplicar — e é o que se
   arquiva depois para saber o que a máquina fez.

E o plano **não impede** o modelo 1: um plano cujo alvo é uma sequência nova é servido por
`createSequenceFromData`; um plano de cortes num projeto aberto é servido por um iterador. **O
plano é a fronteira; o executor escolhe a técnica por NLE** — inclusive escolhendo autoração de
arquivo no Avid, onde o RPC fino não fecha a conta.

Restrição a respeitar, medida e registrada em
[`../plugins/premiere-cep/api-extendscript.md`](../plugins/premiere-cep/api-extendscript.md): **a
timeline do Premiere não repinta depois do script** (clipe fica invisível até o hover). Um plano
executado de uma vez precisa terminar provocando o redesenho — o que é *mais* fácil em lote do que
em N chamadas.

## Onde mora o cérebro do agente — e quando dá para ver

Pergunta prática: as *skills*/definições de ferramenta dos concorrentes são alcançáveis, como foram
as 11 do Jumper?

| produto | onde vive o laço de agente | alcançável? | evidência |
|---|---|---|---|
| **Jumper** | local | **sim, já temos** | 11 `SKILL.md` + 36 tools MCP no bundle |
| **Chat Video Pro** | **cliente** | **sim** (obfuscado) | `tool_calls`/`tool_choice` no `bundle.js` |
| **Eddie AI** | servidor (`mcp.heyeddie.ai`) | só por sessão autenticada | nada de tool no bundle; renderer `mcp_webview` |
| **Premiere Copilot** | servidor | **não** | zero nome de tool, zero `tool_calls`; só 2 pontes `evalScript` |
| **Quickture** | servidor | não | rotas de nuvem, sem prompt local |

⭐ **A regra que explica a tabela — e que serve para prever qualquer produto novo:**

> **BYOK obriga o prompt a ser local.** Se o usuário traz a própria chave, é o cliente que monta a
> requisição para o provedor — então a definição de ferramenta e o system prompt **têm** de estar na
> máquina dele. Quem cobra assinatura de inferência pode esconder tudo atrás do próprio endpoint.

Chat Video Pro é BYOK → está lá. Premiere Copilot cobra e proxia tudo → não está. Antes de gastar
tempo procurando prompt num bundle, **olhe o modelo de cobrança**: ele responde onde procurar.

⚠️ **A régua continua valendo.** No Chat Video Pro foi verificada a **presença** da estrutura de
tool calling, não colhido o texto dos prompts. Ler o system prompt de um concorrente é copiar
conhecimento de domínio, não entender arquitetura — e conhecimento de domínio de pós-produção é
justamente o que **nós** temos para pôr.

**Caminho legítimo para o Eddie, se um dia interessar:** o transporte dele é MCP, e MCP tem
`tools/list` no protocolo. Um cliente autenticado enumerando as ferramentas do servidor **é o uso
previsto do protocolo**, não engenharia reversa — mas exige conta ativa e decisão do usuário. Não
foi feito.

## Ver também

- [analise-de-executaveis.md](analise-de-executaveis.md) — como as medições acima foram obtidas
- [modelo-neutro-efeitos.md](modelo-neutro-efeitos.md) — o mesmo padrão (modelo neutro + N writers) aplicado a estrutura
- [`../plugins/premiere-cep/api-extendscript.md`](../plugins/premiere-cep/api-extendscript.md) — as regras que o validador do plano deve checar
- [`../plugins/avid-panel-sdk/README.md`](../plugins/avid-panel-sdk/README.md) — o piso de 500 ms e o `DoCommand` sem parâmetro
- `PROGRAMAS COM CLAUDE/EDT-ASSIST/direcoes/proposta-agente-hibrido.md` — a proposta de produto que sai daqui


## ⭐⭐ O passo que falha: o CONSELHO é um turno magro, não um turno da conversa (Ciclo Assist, 2026-11-02)

Medido na prova da F1 do Ciclo Assist: quando um passo do fluxo falhava, o painel abria um turno da
CONVERSA (persona, catálogo inteiro de ferramentas, piso de ~40 mil tokens do prompt padrão do
`claude -p`, histórico da sessão) — **116 mil tokens** para pular um passo, com um conselho tirado
do histórico, já velho. Trocado por um `claude -p` de ida única com `--system-prompt` próprio,
`--tools ""`, `--strict-mcp-config` sem servidor, entrada = o estado do fluxo + os argumentos e o
motivo do passo + a seção "Quando as condições mudam" da receita, e saída = JSON
`{explicacao, acao, args}` validado pelo código (ação fora da lista vira `esperar`). Medido:
**1,9–2,7 mil tokens, 7–10 s, ~US$ 0,014** (Sonnet 5.5). Quem age é o código: com o modo
automático, aplica; sem ele, a ação vira um botão. Em 3 falhas reais ele escolheu certo:
`esperar` quando a escolha era do editor (sequência inexistente), `esperar` quando o serviço
irmão caiu, `tentar_de_novo` num motivo passageiro. `confirmado` (Ciclo Assist
`motor/conselho.py`).

## ⭐⭐ O estado do fluxo é do CÓDIGO, não da memória da conversa (Griptape e Ciclo Assist, 2026-11-20)

Medido numa central de orquestração (agente Griptape 1.13.0, `qwen3-vl:8b-instruct` no Ollama 0.33.3) acordada
por AVISOS de máquinas: a memória de conversa do Griptape (`ConversationMemory` + `LocalConversationMemoryDriver`)
guarda, por turno, **só o texto de entrada e de saída — as chamadas de ferramenta e as respostas delas ficam de
fora**. No turno do aviso "conversão concluída", o modelo viu "pedido → 'a conversão foi solicitada… aguardo o
aviso'" e IMITOU a frase: escreveu "a sincronização foi solicitada na máquina mc usando a pasta…" **sem chamar a
ferramenta**. Nada foi pedido e o fluxo parou calado. `confirmado` (1 rodada sem conserto, 3 cenários com conserto).

Conserto, que vale para qualquer agente com memória de conversa:
1. **Registro do fluxo vindo do código:** a cada turno, anexar o que DE FATO aconteceu (tarefas pedidas com id,
   avisos com resultado), lido do registro de eventos — nunca da conversa. Com ele, o agente chamou a ferramenta certa
   em todos os cenários (normal, falha, central derrubada e religada).
2. **Portão:** texto de ação ("solicitada", "pedida", "aguardo o aviso") sem chamada de ferramenta no turno = resposta
   recusada e o agente mandado chamar de verdade. Não precisou agir nas rodadas consertadas; fica como rede barata.

Regra: **o modelo decide o próximo passo; o andamento é guardado pelo sistema.** Detalhe e as outras peças da
orquestração: [orquestracao-fora-do-nle.md](orquestracao-fora-do-nle.md).

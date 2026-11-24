# O CLI do modelo como MOTOR do plugin — contrato, limites e o que custa

> Um assistente de edição pode falar com o modelo de três jeitos: chave de API sua, LLM
> local, ou **o CLI que o editor já tem logado na máquina dele**. A terceira inverte quem
> chama quem — o plugin deixa de ser cliente de IA e passa a **expor ferramentas MCP**,
> esperando ser chamado — e tira o custo do seu P&L, pondo-o na assinatura de quem usa.
>
> Este arquivo é o contrato operacional dessa escolha: as flags que não são opcionais, os
> eventos que o stream entrega, os limites que mordem, e **onde o dinheiro realmente vai**.
> Não é sobre formato de NLE; vale para qualquer produto que embarque um CLI de agente.
>
> **Confiança:** `confirmado` onde marcado. Medido no **Ciclo Assist**, Windows 11,
> **Claude Code 2.1.267 → 2.1.269**, entre 2026-09-10 e 2026-09-12, sobre material real de
> set (cena de dramaturgia, 5 a 10 tomadas, Media Composer 25.6).
>
> ⭐ **Ampliado em 2026-09-19/20 pelo Assist anterior**, com o mesmo motor embarcado noutro app
> e o **CLI 2.1.278**: §1 reconferida (0 nativas com `--restricted --tools ""`, 22
> ferramentas nossas, MCP alcançado por uma casca HTTP com porteiro), §1.3 (o `stderr` que
> trava o turno), §7 (o id de conversa derivado do caminho, quando DOIS produtos dividem o
> mesmo motor) e §11 (o que o host tem de dar ao modelo).
>
> ⚠️ **Toda constante aqui é do CLI, não nossa.** O CLI versiona rápido: uma flag que não
> existia em 2.1.267 pode existir em 2.1.269 (foi o caso de `--effort`, ver §2). Fato que
> não bater com a versão medida volta a `hipotese`.

---

## 1. ⛔⛔ As flags que não são opcionais — `confirmado`

Cada uma nasceu de um defeito medido. Sem elas o produto funciona *parecendo* bem.

| flag | o que acontece SEM ela |
|---|---|
| `--strict-mcp-config` | a sessão **herda os MCP da conta pessoal do editor**: medido, **3 servidores e 35 ferramentas** (Gmail, Drive, Adobe) entrando numa sessão que devia ver só o projeto. Não é higiene, é contenção. |
| `--restricted` | a caixa de chat vira **um shell na estação do cliente** (tira Bash, PowerShell, REPL, WebFetch) |
| ⛔⛔ `--tools ""` | **o `--restricted` NÃO tira as ferramentas de arquivo.** `confirmado` 2026-09-13, CLI **2.1.270**, lendo a lista do evento `system/init` (sai antes do primeiro pedido ao modelo — dá para medir matando o processo ali, sem pagar turno). Sem flag: 36 nativas. Com `--restricted`: tira `Bash`, `PowerShell`, `WebFetch`, `LSP`, `Monitor`, `CronCreate`, `RemoteTrigger` e **sobram 29**, com `Write`, `Edit`, `NotebookEdit`, `Read`, `Glob`, `Grep`, `Task`, `WebSearch`, `SendMessage`. Com `--restricted --tools ""`: **zero nativas**, e as ferramentas MCP continuam na lista. O `--permission-prompt-tool` segue funcionando (sim executa, não é respeitado). ⚠️ E a própria ferramenta de permissão **não aparece** na lista do modelo — quem a chama é o CLI. Quem responde `allow` a todo `tool_name` num modo "automático" está liberando `Write` em qualquer caminho: filtre pelo prefixo `mcp__<servidor>__`. |
| `--permission-prompts host` + `--permission-prompt-tool <ferramenta mcp>` | não há portão: toda escrita no projeto acontece sem o editor ver |
| `--output-format stream-json` + `--verbose` | o `--verbose` é **exigido junto** do stream-json; sem ele o CLI recusa |
| `--include-partial-messages` | não há token ao vivo — a tela fica em reticências até a resposta inteira chegar |
| `stdin=DEVNULL` no Popen (quando não se usa stdin) | o CLI **espera 3 s por stdin que nunca vem, ANTES de começar o turno**. Parece lentidão do modelo, e o aviso só sai no stderr. |

⭐ **Reconferido no CLI 2.1.278 (2026-09-19, Assist anterior, `tools/sonda_do_mcp.py`):** com
`--strict-mcp-config --restricted --tools ""` o `system/init` lista **0 nativas** e as 22
ferramentas MCP do produto, com o servidor `connected` — e o MCP alcançado por uma casca HTTP
cujo portão exige `Origin`/`Sec-Fetch-Site` de todo o resto: o CLI **não manda nenhum dos
dois**, então a rota do MCP precisa de porteiro próprio (o segredo no caminho). Custo: zero
turno, matando o processo no `init`.

### 1.1 ⛔⛔ `--restricted` também bloqueia as SKILLS do próprio CLI — `confirmado` 2026-09-12

Medido em três variantes: **sem a flag a skill carrega; com ela, nunca.** Quem depende de
`--restricted` (e quem expõe um chat ao cliente depende) **não pode contar com o mecanismo
de skills do CLI** para carregar conhecimento de ofício.

⇒ A saída é transportar o conhecimento para dentro de uma **ferramenta MCP nossa** que
devolva o texto. Perde-se o disparo automático por descrição (a skill do CLI carrega
sozinha; a nossa depende de o modelo lembrar de chamar) e ganha-se o essencial: **carregar
por condição**. A descrição da ferramenta (~90 tokens) vai em todo turno; o método (~1.000)
só quando o trabalho pede.

### 1.2 ⚠️ `MCP_TOOL_TIMEOUT` é variável de ambiente, e o padrão é curto

O padrão de fábrica desiste de uma chamada de ferramenta em **60 s** — pouco para
transcrever um take. `MCP_TOOL_TIMEOUT=600000` (ms) estica para 10 min. ⚠️ É do ambiente do
**subprocesso**: um `Popen` que esqueça o `env=` roda com o padrão, e a diferença só aparece
na ferramenta lenta.

### 1.3 ⛔⛔ `stderr=PIPE` sem leitor TRAVA o turno — `confirmado`

O CLI fala bastante no stderr (avisos de modelo, de conector, de retry). Com
`stderr=subprocess.PIPE` e **ninguém lendo**, o buffer do sistema (~64 KB no Windows) enche
e o filho **bloqueia ao escrever**: o stdout para de sair e o turno congela **sem erro
nenhum**. O sintoma é indistinguível de "o modelo está pensando".

| como aparece | medido |
|---|---|
| turno que nunca termina | Ciclo Assist, 2026-09-12: `proc.stderr.read()` (sem tamanho) num processo VIVO — o EOF nunca chega e a thread ficou parada; o painel dizia "respondendo" por **cinco minutos** |
| o mesmo cano no turno solto | Assist anterior, 2026-09-20: reproduzido com um CLI de mentira que escreve **512 KB** no stderr — sem dreno, o turno não acaba |

⇒ **Drenar SEMPRE, numa thread, para um buraco de tamanho fixo** (`deque(maxlen=50)` basta:
num diagnóstico o que serve é o fim), e ler o buraco depois de o processo morrer — nunca o
pipe. ⚠️ Esperar a thread (`join` curto) antes de ler: o EOF do stdout chega **antes** da
última linha do stderr.

---

## 2. ⭐ As flags de CUSTO e de ESFORÇO existem — e não fazem o que parece — `confirmado` 2026-09-12

O CLI 2.1.269 aceita:

- **`--effort low|medium|high|xhigh|max`** — esforço de raciocínio da sessão;
- **`--max-budget-usd <n>`** — teto duro de gasto, **só funciona com `--print`**;
- **`--autocompact auto|<tokens>`** — janela de auto-compactação (100k–1M);
- `--fallback-model`, `--fork-session`, `--session-id`, `--resume`.

⚠️⚠️ **Mas esforço NÃO é a alavanca de custo, e a medição diz por quê.** Sem passar
`--effort`, o transcript registra `perTurnEffort: null` — ou seja, o padrão do CLI. Nessa
condição:

```
tokens de PENSAMENTO / tokens de SAÍDA     Haiku 4.5  68,7%   Sonnet 5  71,5%
tokens de SAÍDA      / tokens TOTAIS       0,3%
```

⇒ Setenta por cento da saída é raciocínio, **mas a saída é três décimos de por cento do
total**. Zerar o pensamento economizaria ~0,2% da sessão. **Esforço é alavanca de
QUALIDADE; o custo está noutro lugar** (§5).

---

## 3. O que o stream entrega, evento por evento — `confirmado`

| evento | quando chega | o que carrega |
|---|---|---|
| `rate_limit_event` | **antes do primeiro token, e antes do `system/init`** | `rate_limit_info.unifiedWindows.<janela>.utilization` (já **normalizado 0–1** pelo CLI) e `.resetsAt` (epoch) |
| `system` / `init` | na partida | `session_id`, `model`, `tools`, `mcp_servers`, `apiKeySource`, `permissionMode`, `slash_commands`, `output_style` |
| `stream_event` → `message_start` \| `message_delta` | durante o turno, uma vez por ida ao modelo | `usage` **ao vivo**: `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens` |
| `system` / `compact_boundary` | quando a conversa não cabe mais | ver §4 |
| `result` | no fim do turno | `modelUsage[<modelo>].{contextWindow, inputTokens, cacheReadInputTokens, cacheCreationInputTokens, outputTokens, costUSD}`, `total_cost_usd`, `is_error` |

### 3.1 ⛔⛔ A JANELA de contexto só existe no `result` — e isso tem consequência de tela

`system/init` traz o modelo e **não traz a janela**. Quem quiser mostrar "a conversa está em
X% da janela" precisa do denominador, e ele só chega **no fim do turno**.

⇒ Sem guardar a janela aprendida (por modelo, e no DISCO), o medidor **nasce vazio e só
aparece no segundo turno** — e some de novo a cada troca de modelo, reinício do serviço ou
recarga da tela. ⚠️ Por modelo, e não "a última que vi": um turno usa mais de um modelo
(medido: `claude-haiku-4-5` com 200 mil e `claude-sonnet-5` com 1 milhão no MESMO
`modelUsage`), e dividir o contexto de um pela janela do outro é mentira com precisão.

### 3.2 ⛔⛔ A soma do `result` NÃO é ocupação da janela — 11× de diferença

Medido: num turno de 3 requisições a soma do `result` deu **267.873** contra **23.360** de
ocupação real. A razão é estrutural: **cada chamada de ferramenta reenvia a conversa
inteira**, e o `result` soma todas as requisições do turno.

Dividido pela janela, isso pinta "186%", "284%", "200%" na barra do editor — impossível por
definição, e destrói a confiança no medidor inteiro.

⇒ **Gasto do turno** e **ocupação da janela** são dois números diferentes: o gasto sai do
`result`; a ocupação sai da ÚLTIMA requisição, que chega nos eventos ao vivo.

---

## 4. ⛔⛔ `compact_boundary`: o minuto em que o produto fica mudo — `confirmado` 2026-09-12

Quando a conversa não cabe na janela do modelo, o CLI **auto-compacta**. Isso não produz uma
palavra de saída e pode levar mais de um minuto.

```json
{"type":"system","subtype":"compact_boundary","compactMetadata":{
  "trigger":"auto","preTokens":582570,"postTokens":108239,
  "cumulativeDroppedTokens":474331,"durationMs":70184}}
```

Medido em campo: uma conversa de **582.570 tokens** retomada debaixo do **Haiku 4.5 (janela
de 200 mil)**. **70 segundos parados**, 474 mil tokens descartados, **~121 mil queimados**, e
zero texto na tela. O editor esperou cinco minutos, concluiu que travou, e cancelou — o
turno inteiro virou pó.

⇒ **Traduza este evento para a interface.** Ele existe no stream e é fácil descartar por não
ser `assistant` nem `result`. Sem ele, o produto tem um minuto de silêncio sem explicação
— e silêncio sem nome o usuário lê como travamento.

⇒ E **avise ANTES**: se o tamanho conhecido da conversa passa da janela do modelo escolhido,
dá para dizer o preço antes de gastá-lo. Avisar, não recusar — pode ser o que ele quer.

---

## 5. ⭐⭐ Onde o dinheiro vai: é o CONTEXTO, não o payload — `confirmado` 2026-09-12

A mesma tarefa (montar uma cena de diálogo a partir de roteiro), duas vezes, mesmo material:

```
                                  contexto inicial   chamadas de API   TOTAL de tokens
conversa de dois dias atrás             505.397            12             6.574.840
depois de limpar a conversa              13.833            13               690.727
```

**10,8× para a mesma tarefa, em 4 minutos de trabalho.** Na mesma sessão, a saída de TODAS
as ferramentas somou 52 mil tokens — **0,5% do que foi lido**.

⇒ O que custa não é o que a ferramenta devolve; é **o que ela deixa para trás**, recobrado
em cada ida ao modelo. Otimizar payload de ferramenta rende pouco; **encurtar a conversa
rende uma ordem de grandeza**.

⚠️ Corolário de interface: um produto que abra a tela em branco enquanto o fio continua
inteiro do outro lado (fechar e reabrir o host, por exemplo) **esconde do editor o número
que mais custa**. Tela em branco, contexto cheio.

⚠️ **E numa assinatura o dólar informa errado.** O `total_cost_usd` aparece mesmo em conta
onde não há cobrança por token. A moeda real é a **fração da janela de uso**
(`rate_limit_event.utilization`) — é ela que esgota e é ela que o editor sente.

---

## 6. ⛔⛔ O teto de saída de uma ferramenta MCP — `confirmado` 2026-09-12

Resposta de ferramenta grande demais **não é truncada com aviso ao autor**: ela volta ao
modelo como erro, com um caminho de arquivo no lugar do conteúdo.

```
Error: result (61.559 characters across 2.520 lines) exceeds maximum allowed tokens.
Output has been saved to …\tool-results\mcp-<servidor>-<ferramenta>-<epoch>.txt
```

Medido por bracketing na mesma sessão: **20.201 chars passaram inteiros; 55.844
estouraram.** (O limite exato não é publicado; use a borda de baixo com folga.) Há também
uma variante `<persisted-output>` que entrega uma **prévia de 2 KB** mais o caminho.

⚠️⚠️ **O nome do arquivo não diz de que CHAMADA ele é** — carrega um timestamp, não a
identidade. Com chamadas em paralelo, o modelo recebe uma mistura de prévias e caminhos
anônimos e **remonta o mapeamento na mão**.

⇒ Foi o que aconteceu em campo: **12 de 14 transcrições estouraram**, o modelo recuperou os
números com **13 greps (118 KB — o maior consumidor de saída da sessão, acima das próprias
transcrições)**, e daí saiu um erro de atribuir o timecode de um take a outro.

⇒ **Regras que saíram disso:**
1. trate a saída de ferramenta como **orçamento com teto**, não como "o que couber";
2. enxugar campo divide por um fator; **lista sem limite não tem teto** — precisa paginar;
3. ⛔ **truncar calado é pior que estourar**: o modelo monta a cena com metade do diálogo
   achando que viu tudo. A resposta tem de dizer quanto ficou de fora e por onde continuar;
4. ⛔ **campo que existe para NÃO ser usado um dia é usado.** Um tempo "cru" devolvido ao
   lado do tempo correto, com a regra escrita mandando ignorá-lo, virou ponto de corte
   assim mesmo. Tire-o da resposta.

---

## 7. A identidade da conversa — `confirmado`

- **`--resume <id>` primeiro, SEMPRE.** `--session-id` num id que já existe **não dá erro**:
  começa conversa nova e descarta o fio em silêncio. Já `--resume` num id inexistente falha
  limpo (`No conversation found with session ID`), e aí é criar. Inverter a ordem custa a
  conversa inteira do editor, sem nada acusando.
- ⛔⛔ **O id do fio tem de ser PERSISTIDO, não derivado.** Derivar o id do caminho do
  projeto é ótimo para reencontrar a conversa amanhã — e é uma armadilha se o "limpar" só
  trocar o id **na memória do processo**: reiniciado o serviço, o mapa nasce vazio, o
  "limpar" vira no-op silencioso e o turno seguinte **retoma com `--resume` o fio que o
  editor achava que tinha jogado fora**. Medido: foi assim que uma conversa de 582 mil
  tokens voltou (§4). ⇒ O caminho semeia o PRIMEIRO fio; depois quem manda é o disco.
- Trocar de modelo exige **derrubar o subprocesso** (o modelo é escolhido na partida); o fio
  não se perde porque o `--resume` o retoma no turno seguinte.
- ⛔ **Dois produtos com o MESMO motor dividem a conversa, se o id sai só do projeto** —
  `inferido` (2026-09-19, lido no código, não disparado). O Ciclo Assist deriva o primeiro fio
  de `uuid5("cicloassist:" + caminho do projeto)`. Transplantado para dentro do Assist anterior,
  que convive com ele no mesmo Media Composer, o mesmo projeto daria o MESMO id aos dois
  painéis — e o `--resume` de um retomaria os turnos do outro (o CLI guarda a sessão pelo id).
  ⇒ Quem copia um motor de CLI para outro produto troca o NAMESPACE do id (lá virou
  `"assist_anterior:"`). Vale para qualquer id derivado de caminho.

---

## 8. ⚠️ O transcript em disco: o que ele tem e o que ele NÃO tem — `confirmado`

O CLI grava cada sessão em `~/.claude/projects/<cwd-com-barras-trocadas>/<session-id>.jsonl`,
e as saídas de ferramenta que estouraram vão para `<session-id>/tool-results/`. É a melhor
telemetria disponível **sem instrumentar nada** — e tem três armadilhas:

1. ⚠️⚠️ **A MESMA mensagem é gravada várias vezes** (medido **2,6× a 3,2×**: uma linha por
   bloco de conteúdo, repetindo o `usage` inteiro). Somar sem deduplicar por `message.id`
   **triplica a conta** — a primeira leitura de uma sessão nossa devolveu 34 milhões de
   tokens onde havia 11.
2. ⚠️ **Não há campo de custo nenhum**, e não há evento `result`: os dois só existem no
   stream ao vivo. Dólar calculado a partir do transcript é aritmética de quem calcula, não
   medida — e tem de ser rotulado assim.
3. ⚠️ O mesmo id pode existir em **mais de uma pasta de projeto** (o CLI indexa por cwd, e o
   serviço pode ter rodado de lugares diferentes). Escolher por ordem alfabética pega a
   errada em silêncio.

⇒ Com isso dá para responder, para qualquer sessão passada, *"qual ferramenta encheu a
janela?"* — pergunta que o servidor MCP normalmente **não** consegue responder, porque
`tools/call` costuma não medir nem bytes nem duração.

---

## 9. ⚠️ O que fica pendente

- **`--effort` medido lado a lado** (low/medium/high na mesma tarefa): sabemos que mexe
  pouco no custo; falta saber quanto mexe na **qualidade**. `pendente`.
- **`--autocompact` com valor explícito** como prevenção da §4. `pendente`.
- **`--max-budget-usd` em conta de assinatura**: funciona? O que ele conta, se não há
  cobrança por token? `pendente`.
- **Outros CLIs de agente** (Codex, Copilot) como motor alternativo: o que trava não é MCP
  nem streaming, é o **portão delegável** — responder `deny` na hora e deixar o host
  executar no clique. Os dois pedem aprovação no terminal deles. `hipotese`, por medir.
- 🆕 **O MESMO CLI com a inferência num modelo local** (`ANTHROPIC_BASE_URL` → Ollama
  `/v1/messages`, §10.1). Contornaria o problema do portão acima, porque o CLI continua sendo
  este. ✅ `confirmado` em 2026-09-16 — ver §10.5.

---

## 10. Modelo local via Ollama — o que já se mediu, e onde ele NÃO pode rodar

> **Medido em 2026-09-12/13**, Ciclo Assist. **Ollama 0.33.3** no Windows 11, notebook com
> **RTX 4050 Laptop (6 GB)** e 16 GB de RAM, Media Composer 2025.6 aberto.

### 10.0 ⛔⛔ Estação de edição com GPU de laptop não hospeda modelo local — `confirmado`

- `qwen2.5vl:7b` ocupa **6,7 GB**: `ollama ps` mostrou **51% CPU / 49% GPU** — não coube na
  VRAM — e a primeira mídia **estourou 600 s**.
- **Telas azuis repetidas** com modelo local ao lado do Media Composer: a última em
  2026-09-13, com `gemma3:4b` (3,3 GB) carregando, antes de uma resposta; as anteriores
  relatadas pelo editor.

⇒ Inferência local fica numa **máquina separada na rede**; a estação é do NLE. O desenho
dessa ponte está em `_CICLO ASSIST/docs/spec/2026-09-13-servidor-de-percepcao-mac.md`.

### 10.1 ⭐⭐ O Ollama fala o protocolo da Anthropic — `confirmado` (o endpoint E o CLI por cima, §10.5)

`POST /v1/messages` responde com erro **no formato da Anthropic**
(`{"type":"error","error":{"type":"invalid_request_error",…},"request_id":"req_…"}`), ao lado
de `/v1/chat/completions` (formato OpenAI) e da API nativa `/api/chat`. Não é stub.

Se o `claude -p` aceitar `ANTHROPIC_BASE_URL` apontando para lá, o plugin mantém **tudo** — o
portão, `--resume`, MCP, `stream-json`, `--restricted` — e só a inferência muda de lugar.
⚠️ Três coisas por medir antes de acreditar:

1. se o CLI aceita a URL com a flags da §1;
2. fidelidade de *tool call* de um modelo de 8B atravessando o shim;
3. ⛔ **o contexto.** O piso de um turno do CLI é ~40 mil tokens (§5), e pelo protocolo da
   Anthropic **não há campo para `num_ctx`**: vale o padrão do SERVIDOR. Com o padrão da §10.2
   o prompt seria cortado e o modelo perderia as ferramentas — o sintoma seria "modelo local
   burro". `hipotese` (deduzido do protocolo, não medido).

E o painel perderia `costUSD`, `contextWindow` e os eventos de limite (§3). `hipotese`.

### 10.2 ⛔ O contexto padrão é 4096 tokens — `confirmado`

Seis quadros JPEG (~18 KB cada; 237 KB em base64) viram **6.229 tokens de prompt** no
`qwen2.5vl:7b`; com o padrão, o pedido volta **400** `exceed_context_size_error`. Na API
nativa, `options.num_ctx` por pedido resolve (12.288 serviu).

### 10.3 Capacidades se conferem antes, por `POST /api/show` — `confirmado`

| modelo | `capabilities` |
|---|---|
| `qwen2.5vl:7b` | `completion`, `vision` — ⚠️ **sem `tools`** |
| `gemma3:4b` | `completion`, `vision` |
| `llama3.1:8b`, `mistral` | `completion`, `tools` |
| `gemma4` (8B) | `completion`, `tools`, `thinking` — sem `vision` |
| `gemma2:9b` | `completion` |

⇒ Um modelo serve para decupar (`vision`) **ou** para ser motor do CLI (`tools`), e os
listados não fazem as duas coisas. ⚠️ O que acontece ao mandar imagem para um modelo sem
`vision` **não foi medido** — o spike recusa antes. `hipotese`: aceita calado e inventa.

### 10.4 ⭐ O VLM pequeno não entende o que o Claude entende — `confirmado` (n = 1 cada)

`qwen2.5vl:7b`, `temperature: 0`, a persona de decupagem do Ciclo Assist:

1. Com o envelope `{"<chave da mídia>": {…}}`, devolveu a chave **literal**
   `"<chave da mídia>"`. ⇒ O envelope por chave existe para juntar várias mídias num turno e
   amortizar o piso de ~40 mil tokens do CLI; **modelo local não tem piso**: uma mídia por
   pedido, resposta plana.
2. Com resposta plana, devolveu um **array com uma decupagem por quadro** — seis descrições
   do mesmo plano —, apesar do cabeçalho "*6 quadros da mídia X, em ordem, nos segundos …*".
   Só com "*os quadros são do MESMO plano; responda UM único objeto*" explícito.
3. Aí: **4 de 5** campos fechados iguais ao gabarito do Haiku, **0** valores fora do
   vocabulário. ⚠️ n = 1 — prova que o transporte funciona, não que o modelo serve.

Tempo na RTX 4050 (antes de sair da VRAM): **151 s** frio, **45 s** quente, contra ~10 s do
Haiku com 3 mídias por turno.


### 10.5 ⭐⭐ O `claude -p` inteiro com a inferência no Ollama — `confirmado` (2026-09-16)

> **Claude Code 2.1.273**, Windows 11 → **Ollama 0.33.3** num Mac mini M4 16 GB na LAN,
> `qwen3-vl:8b-instruct` (Q4_K_M, 8,8 B, `completion`/`vision`/`tools`). Medido pelo Ciclo
> Assist com as flags da §1 inteiras (`--restricted`, `--tools ""`, `--strict-mcp-config`,
> portão host, `--input-format stream-json`), `spikes/o_ollama_como_motor.py`.

**Como:** ambiente do subprocesso, nada de flag nova.

| variável | valor | por quê |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://<mac>:11434` | sem `/v1`: o CLI acrescenta |
| `ANTHROPIC_API_KEY` | qualquer (`ollama`) | ⛔ sem ela o CLI manda o **token OAuth da assinatura** ao servidor. Com ela, `system/init` diz `apiKeySource: ANTHROPIC_API_KEY` e o stderr avisa que os conectores do claude.ai foram desligados |
| tirar `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` | — | ganhariam da chave |
| `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL` | o modelo local | o CLI usa o "rápido" por dentro; `claude-haiku-…` no Ollama é 404. `hipotese` — não vimos o 404, só o prevenimos |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `1` | telemetria não vai para a Anthropic com chave que não é de lá |

**O que se mediu:**

- ✅ Responde (`"responda apenas: ok"` → `ok`, 16 s frio). stderr: `[claude-code:unrecognized_model]` — só aviso.
- ✅ **Tool call atravessa o shim:** chamou `consultar_o_metodo` com o argumento certo e resumiu o resultado; chamou a ferramenta de escrita pedida.
- ✅ **O portão segue de pé:** `pedir_confirmacao` chamado 1×, `deny` respeitado, nada escrito (3 rodadas).
- ⛔ **CORRIGE a hipótese da §10.1.3 (piso de ~40 mil):** com `--tools ""` e persona própria o
  piso é **955 tokens** sem MCP e **~10,9 mil** com as 23 ferramentas do Ciclo Assist. Os
  ~40 mil da §5 eram o prompt de sistema PADRÃO com as ferramentas nativas.
- ✅ **Contexto do servidor:** `/api/ps` mostrou o modelo carregado com `context_length: 40960`
  (o teto do modelo é 262 144; o CLI não manda `num_ctx`). 11 mil cabem com folga, mas a
  conversa cresce — o que passar de 40 960 é cortado calado.
- ⏱ Primeiro turno **135 s** com o modelo frio (carga + pré-preenchimento de 10,9 mil),
  **40 s** morno, **9–10 s** nos seguintes (cache de prompt do Ollama). Haiku: ~2 s.
- ⛔ **O host recebe números inventados:** `modelUsage[<local>]` traz `contextWindow: 200000`,
  `costUSD: 0.0048` (preço de tabela aplicado a um modelo que não cobra),
  `costBasis: "unknown"`, `provider: "firstParty"`. E `inputTokens` volta pequeno
  (~1,8 mil para um pedido de 10,9 mil — o Ollama conta só o que não veio do cache dele).
  ⇒ Janela do `/api/ps`, dólar nenhum. Sem `rate_limit_event`.
- ⚠️ **O modelo de 8B descreve mal o `deny`:** com o texto do portão ("mostrei ao editor…
  termine dizendo o que espera confirmação") respondeu *"A nota … foi salva no caderno.
  Aguardando confirmação do editor"*; com um texto curto, *"foi anotada"*. A mecânica
  segura, mas o que o usuário LÊ afirma uma escrita que não aconteceu. n = 3.
- ⛔⛔ **Tarefa real FALHA em laço** (2026-09-16, separar falas da C07, roteiro + 10
  subclipes pelo painel): `consultar_o_metodo` e `estruturar_o_roteiro` saíram certos; no
  pedido seguinte (~12 mil de contexto) o Ollama gerou ~4 min e respondeu
  **`500 unexpected end of JSON input`** (`request_id` no formato Anthropic), duas vezes
  seguidas. O CLI registra `system/api_error` com `retryAttempt`/`maxRetries: 10` no
  transcript e **repete sozinho** — ~40 min de tela parada. Causa `hipotese`: o pedido de
  ferramenta que o 8B escrevia saiu JSON inválido/truncado e o shim do Ollama não o
  converteu. Não medido: o texto gerado, se bateu no `num_predict`/contexto.
- ⭐⭐ **A causa da 500, lida no código do Ollama 0.33.3** (`server/routes.go` ChatHandler,
  `model/parsers/qwen3vl.go`) e reproduzida (`_CICLO ASSIST/spikes/o_500_do_ollama.py`):
  o parser embutido do Qwen acumula o que vem entre `<tool_call>` e `</tool_call>` e, no
  fechamento, faz `json.Unmarshal`; se falha, **cancela a geração e o pedido volta 500 com a
  mensagem do Go**. Rodando o `api.ToolCallFunction` do 0.33.3 (Go, no notebook) sobre
  variações de um pedido real: `unexpected end of JSON input` sai **só** de JSON sem a chave
  final (`…]}` por `…]}}`) ou de `<tool_call></tool_call>` vazio; colchete errado no meio dá
  `invalid character`. ⇒ o 8B fecha a marca antes de fechar o objeto aninhado. `inferido`
  (a saída que falhou não foi capturada: duas gerações cruas do mesmo prompt, 2.191 e 2.426
  tokens, saíram VÁLIDAS; o caminho `/v1/messages` falhou 3 de 4).
- ⛔⛔ **O Ollama NÃO transmite o `tool_use` aos poucos** (medido): enquanto o parser está
  dentro de `<tool_call>` não sai byte nenhum — nem o `message_start`; tudo chega junto no
  fim, ou vem a 500 sem corpo de stream. Host que mostra `input_json_delta` não ganha nada;
  o que ajuda é contar o tempo SEM sinal.
- ⛔ **Velocidade:** Qwen3-VL 8B Q4 no M4 16 GB com contexto 40.960: **~73 tok/s** de leitura
  (13,6 mil em ~187 s, sem cache) e **~8,8 tok/s** de geração. Um `separar_falas` de 2,4 mil
  tokens = 5 min sem byte. Com o padrão do CLI (`API_TIMEOUT_MS` 600 s; ociosidade de 5 min
  para provedor que não é a Anthropic, `API_FORCE_IDLE_TIMEOUT`) um pedido certo e longo é
  CORTADO e repetido — o Ciclo Assist passa `API_TIMEOUT_MS=1800000` e
  `API_FORCE_IDLE_TIMEOUT=0`. Não há variável documentada para o número de repetições (10).
- ⚠️ **Não era o SigLIP** (2026-09-16, servidor SigLIP desligado, modelo recarregado): o
  `/api/ps` continua com **7,70 de 9,13 GB na GPU** (a divisão não vem de falta de RAM;
  causa `pendente`), e as velocidades quase não mudam — leitura **75,5 tok/s** (13,6 mil em
  180 s) e geração **10,1 tok/s** com esse contexto; **18,6 tok/s** com contexto de 29 tokens.
  ⇒ o gargalo do M4 16 GB é o contexto longo (atenção sobre ~13 mil) e a banda da memória,
  não a convivência com o SigLIP.
- ⚠️ **`tool_choice` é ignorado** pelo `/v1/messages` do Ollama (6 de 6). E o `effort: high`
  do CLI vira `think: "high"`, que a API nativa RECUSA para o instruct
  (`does not support thinking`) — pelo `/v1/messages` passa (descartado). `confirmado`.
- ⚠️ **Temperatura 1 e mesmo assim quase determinístico:** o mesmo pedido deu a mesma
  chamada 6 de 6 vezes, e acrescentar os `<system-reminder>` do transcript (poucas dezenas
  de tokens) trocou a escolha de `transcrever` para `separar_falas`. Reprodução exige o
  pedido FIEL: system concatenado sem separador, `tool_result` antes do texto da mesma
  mensagem, e as ferramentas como o Go as serializa (só os campos de `api.ToolProperty`,
  `<>&` escapados) — ver `_qwen()` no spike (13.349 contra 13.310 tokens do servidor).
- ⬜ Não medido: imagem pelo CLI, `--resume` com o Ollama; se o stream-json emite
  `system/api_retry` (o host trata os dois nomes).


### 10.6 Um servidor Ollama para um TIME — o que atende, e onde para (2026-09-16)

> Resposta a "um Ollama na rede atende vários editores?". **Pouco disto foi medido:** cada
> item diz a confiança. O que tem número veio da §10.5 (Mac mini M4 16 GB, Ollama 0.33.3).

**O que já se VIU** — `confirmado`:

- **Pedido além da capacidade ESPERA, não falha.** Com `OLLAMA_NUM_PARALLEL=1` (a spec do
  Mac), um pedido do spike esperou **286 s** atrás do turno do editor. Do lado do cliente é
  silêncio puro: nem cabeçalho HTTP chega enquanto espera.
- **O cache de prompt é o que torna o 2º turno barato:** o mesmo pedido de 13,6 mil tokens
  levou **~187 s** da primeira vez e **5 s** da segunda. Ele vale para o prefixo que a mesma
  vaga acabou de ler.
- **A decupagem em lote e o chat disputam a mesma fila** (§10.5 e a fila do Ciclo Assist
  manda uma mídia atrás da outra).
- **Sem autenticação:** o Ollama não tem usuário, senha, cota nem TLS. Quem alcança a porta
  usa (visto: o notebook usa o Mac só com o IP).

**O que se DEDUZ do desenho** — `inferido` (documentação/código do Ollama, não medido aqui):

- `OLLAMA_NUM_PARALLEL` = pedidos atendidos juntos pelo MESMO modelo. Os pesos carregam uma
  vez; **o contexto é reservado por vaga** (`num_ctx` × vagas). `OLLAMA_MAX_QUEUE` (512) é o
  tamanho da fila; além dela, erro.
- Numa GPU de 16 GB com um 8B Q4 (~6 GB de pesos) e 40 mil de contexto por vaga, o realista
  são **2 vagas** (3 com contexto menor ou `OLLAMA_KV_CACHE_TYPE=q8_0`). ⚠️ O tamanho exato do
  contexto por token depende do modelo — medir no `/api/ps` com 1, 2 e 3 vagas.
- **Com várias pessoas revezando, o cache de prompt erra mais**: cada vaga guarda o prefixo
  do último pedido que atendeu. Na GPU a releitura custa segundos; no M4 custava minutos.
- Vagas em paralelo aumentam a vazão total e deixam cada pedido um pouco mais lento; duas
  leituras de prompt longo ao mesmo tempo disputam a GPU.
- Dimensionar por **pedidos simultâneos, não por pessoas**: editor monta mais do que
  pergunta. Estimativa (`hipotese`): 3–5 editores em uso intermitente de chat numa RTX 5060 Ti
  16 GB com 2 vagas — espera de segundos quando colidem.
- **Passo seguinte quando não bastar:** vLLM (memória de contexto paginada e lotes contínuos:
  bem mais pedidos juntos na mesma GPU). Linux, ou WSL2 no Windows; mais trabalho de montar.

**Regras para quem montar** (Ciclo Assist e outros apps da família):

- Firewall: a porta 11434 só para os IPs das estações; com time maior, proxy com senha
  (Caddy/nginx) à frente. Nunca exposto fora da LAN — o material do cliente trafega nele.
- Lote (decupagem) fora do horário de montagem, ou vaga reservada ao chat.
- Cada estação aponta para o mesmo endereço; os pedidos são independentes.
- O `/api/ps` mostra o que está CARREGADO, não a fila: não há painel de uso.

**Máquina considerada pelo editor** (`hipotese` — ficha lida em 2026-09-16, nada medido):
PC Loja Juno IX — i5-12400F, **Gainward RTX 5060 Ti Python III 16 GB GDDR7**, placa
H610M-T (DDR4), 2 × 8 GB DDR4-3200, NVMe 1 TB, fonte Aigo AT650 650 W Bronze, Windows 11
*Trial*; R$ 7.800,44 no PIX. Parecer: serve; pedir **2 × 16 GB** na compra (os dois pentes
de fábrica provavelmente ocupam os slots), licença do Windows à parte, rede cabeada.
Banda de memória (fabricante): 5060 Ti ~448 GB/s, 5070 Ti ~896 GB/s, M4 ~120 GB/s — a
geração escala com ela. ⬜ Medir na máquina: leitura/geração do mesmo pedido da §10.5 e dois
pedidos simultâneos (tempo de cada + `/api/ps`).

### 10.7 ⛔⛔ O servidor do modelo que CAI no meio do turno pendura o turno — `confirmado` (2026-09-17)

MEDIDO em campo, Ciclo Assist no Premiere com o Qwen3-VL no Mac: o Ollama morreu no meio de
uma conversa — **a máquina respondendo ping, a porta 11434 muda**. O que aconteceu do lado do
CLI (2.1.273):

- ele emite `{"type":"system","subtype":"api_error","error":{"message":"Connection error."}}`
  e **repete**, com espera crescente (medido: 3, 3, 5, 7, 11 s);
- depois de esgotar as tentativas ele **para de emitir e não morre**: nenhum `result`, nenhum
  EOF. Quem lê o stdout esperando o `result` espera para sempre — o painel ficou 40 minutos
  em "pensando…", com o trabalho do turno já feito no projeto e nenhuma palavra ao editor.

⇒ Duas defesas, e a primeira é a barata:

1. **Conferir o motor ANTES de subir o CLI.** Para o Ollama, `GET /api/tags` com 3 s de
   prazo. Fora do ar, o turno não começa: vira uma frase ("ligue o Ollama, ou escolha o
   modelo da assinatura"). Custa milissegundos e evita gastar o turno para descobrir.
2. **Desistir depois de N falhas SEGUIDAS** (3 no Ciclo Assist), matando o processo e
   dizendo o motivo — inclusive "o que já foi feito está feito", que é o que o editor
   precisa saber. ⚠️ Falha ISOLADA no meio de um turno que anda não conta: rede oscila, e o
   CLI se recupera sozinho.

### 10.8 ⛔⛔ Resposta ZERO sem explicação vira laço — `confirmado` (2026-09-17)

MEDIDO em campo com o mesmo 8B: o editor pediu para tirar clipes de subpastas; o modelo
chamou a ferramenta de listar com o filtro "só o que está selecionado", recebeu
`{"quantidade": 0}` em onze bins — **nada estava selecionado na bin do NLE** — e repetiu a
MESMA volta quatro vezes: **46 chamadas, 20 minutos, nenhuma resposta ao editor**.

- ⭐ **Zero é ambíguo**: "a bin está vazia" e "não há seleção agora" são coisas diferentes, e
  a resposta tem de dizer qual é, com o que fazer ("chame sem o filtro; a seleção é do mouse
  do editor e não muda porque você pediu de novo"). Só isso tirou o modelo do laço.
- ⭐ **Uma chamada por pasta é fábrica de laço**: a mesma tarefa com uma ferramenta que
  devolve a ÁRVORE inteira numa chamada (com teto e recorte por galho) caiu para **4
  leituras** e um minuto — com o Claude Sonnet, no mesmo material.
- ⭐⭐ **E vale uma rede genérica no servidor MCP**: a mesma LEITURA, com os mesmos
  argumentos, repetida três vezes no mesmo turno volta como aviso ("a resposta não mudou e
  não vai mudar sozinha; use o que já recebeu ou diga ao editor o que falta"). ⚠️ ESCRITA
  fica de fora: um lote legítimo repete argumentos iguais, e o portão já a segura.
- ⚠️ O modelo grande não caiu em nenhum dos dois laços. Isto é limite do 8B, não do desenho —
  mas a ferramenta que explica o zero é melhor para os dois.

---

## 11. ⭐⭐ O que o HOST tem de dar ao modelo — duas lições medidas (2026-09-20)

> As duas saíram do MESMO teste do editor (separar as falas de uma cena, Assist anterior) e
> valem para qualquer produto que embarque um CLI de agente. Nenhuma é sobre prompt.

### 11.1 ⛔⛔ Erro que não diz o GESTO vira teoria inventada — e cada modelo inventa a sua

A transcrição de 10 takes falhou com `não achei a mídia de som de '' no acervo local` — o
nome vazio porque o master não estava na bin lida do disco (a bin tinha alteração não
salva; ver `../protocolos/avb/sincronizacao-e-subclipes.md` §4). O modelo não tinha como
saber o motivo: **deduziu** que faltavam masterclipes na bin e pediu ao editor que os
trouxesse — coisa que no Avid nem existe. O editor leu isso como imprevisibilidade do
modelo: *"cada modelo está interpretando a sua forma de execução"*. Dois outros modelos
(Haiku e um Qwen local) tinham acertado o caminho — **por sorte de caminho, não por saber
mais**.

⇒ Toda mensagem de erro que o modelo pode encontrar diz **a causa provável e o gesto**
("peça ao editor para salvar a bin — Ctrl+S — e tente de novo"), e os avisos internos do
resolvedor viajam JUNTO do erro. O que o produto não disser, o modelo preenche — e aí a
resposta muda de modelo para modelo.

⚠️ Corolário: o método (a skill que o modelo lê) carrega o **fato do NLE** que impede a
teoria errada. Aqui: *"o master de um subclipe vive oculto dentro da própria bin; não peça
ao editor que traga masterclipes"*.

### 11.2 ⭐ A ação aprovada roda FORA do turno — e o progresso precisa de canal próprio

Com portão que não bloqueia (ADR 0008 do Ciclo Assist: o cartão espera o clique, o turno
acaba), a ferramenta roda depois, na thread do clique. Todo relatório de progresso que o
produto já emitia **para o turno** cai no vazio: o cartão fica com "fazendo…" do primeiro
ao último minuto, e um sync de diária assim é indistinguível de travado.

⇒ O host guarda o andamento da PENDÊNCIA em execução (etapa, fração, relógio) e a tela
pergunta enquanto espera. ⭐ Feito no relator que as ferramentas já chamavam: nenhuma
ferramenta mudou.

---

## Ver também

- [modelo-de-execucao-de-agente.md](modelo-de-execucao-de-agente.md) — como a DECISÃO do
  agente vira timeline (as cinco arquiteturas). Este arquivo é a camada de baixo: como o
  motor se comporta.
- [`../seguranca/README.md`](../seguranca/README.md) §3–§4 — por que um serviço local
  precisa de segredo, e por que **quem responde na porta manda no plugin**.
- [decupagem-por-transcricao.md](decupagem-por-transcricao.md) — o trabalho que o modelo faz
  com o que estas ferramentas devolvem.

## 🆕 2026-11-19 — o APP do Claude (desktop, Windows) como cliente das nossas ferramentas (`confirmado`, 5.11492.5.0)

Pedido do autor para uma aula: o mesmo fluxo pelo app do Claude, sem a janela do Ciclo Assist. Medido em 3 ensaios
(Resolve → OP-Atom → MC → sync → subclipes por cena, Sonnet 5.5, modo Auto):

- **Configuração local** = só servidor **stdio**, no `claude_desktop_config.json` — no app da loja (MSIX) ele mora em
  `%LOCALAPPDATA%\Claude-Data\claude_pzs8sxrjxfjjc\` (o `%APPDATA%\Claude` e o `LocalCache` do pacote estão vazios). O
  log de cada servidor: `%LOCALAPPDATA%\Claude\logs\mcp-server-<nome>.log` (o stderr do servidor vai para lá; as
  chamadas de ferramenta NÃO aparecem nele). O app lê a configuração ao abrir.
- ⛔⛔ **O app desiste de uma ferramenta em ~1 min**, e `notifications/progress` NÃO segura o prazo. O modelo lê
  "timeout" de uma operação que terminou bem e segue agindo sobre um programa ainda abrindo. ⇒ A ponte responde "ainda
  rodando" aos 45 s e uma ferramenta dela (`aguardar_operacao`) entrega o resultado (`_CICLO ASSIST/tools/ponte_mcp_stdio.py`):
  medido 62–83 s entregues sem erro.
- **Modo Auto**: as ferramentas rodam sem "Permitir" a cada chamada. Ele monta um plano de passos sozinho na lateral.
- Quando uma ferramenta diz que há um diálogo na tela, ele pede **"Uso do computador"** (computer use) para clicar —
  recusar é seguro: ele para e explica o que falta.
- O nome que o app mostra é a CHAVE da configuração (`edicao`), e a ponte reescreve o `serverInfo.name`.

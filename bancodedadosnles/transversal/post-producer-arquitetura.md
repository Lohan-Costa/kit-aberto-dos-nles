# Post Producer (post.mov): arquitetura

Analisado em 2026-10-30, versão **0.1.63** (build 1911), `.dmg` de 153 MB, só macOS 14+ arm64.
Método: [analise-de-executaveis.md](analise-de-executaveis.md) — extraído com 7-Zip no Windows,
**nada instalado nem executado**. O site público não explica nada técnico (e mostra uma tabela
contra o Frame.io marcada *"draft, not yet checked"* em produção); o binário explica tudo.

## Em uma frase

**O mesmo desenho do Ciclo Assist, só que o modelo é pago POR ELES:** um app nativo (Swift) que
leva o **Claude Code CLI embarcado** (240 MB), dirige os NLEs por fora e recebe trabalho de uma
fila no site deles — e é por essa fila que o celular "controla" o Mac. `confirmado`

## As peças do bundle

| peça | o que é | confiança |
|---|---|---|
| `MacOS/PostProducerDesktop` | app Swift (janela, Sparkle para atualizar) | `confirmado` |
| `Resources/bridge/pp-bridge` | **Node SEA** (151 MB); o JS vai na seção `NODE_SEA/__NODE_SEA_BLOB`, um bundle esbuild de 4,5 MB **sem minificação**, com os caminhos `apps/bridge/src/*.ts` e comentários citando ADRs. Sobe com `run --control stdio --editors premiere,resolve,final_cut` | `confirmado` |
| `Resources/bridge/claude` | o binário do Claude Code, chamado pelo **Claude Agent SDK** (`pathToClaudeCodeExecutable`) | `confirmado` |
| `agent-plugin/` | plugin do Claude Code com ~25 skills (avid-*, premiere-*, resolve-scripting, final-cut-pro, sound-post…) — **o corpo de cada SKILL.md é um marcador** `{{post:skill/<nome>@<hash>}}` que o gateway troca pelo texto no servidor | `confirmado` |
| `MacOS/pp-vision` | Swift: ScreenCaptureKit + Vision (OCR) + Accessibility; CLI do agente para tela, menus do FCP e checagens do Avid | `confirmado` |
| `MacOS/pp-display` + LaunchAgent `KeepAlive` | segura um **`CGVirtualDisplay`** (monitor virtual) onde o agente opera o Final Cut sem o usuário ver | `confirmado` |
| `PostProducerPremiere.ccx` | painel **UXP** (Premiere ≥ 25.6) que só fala com `http://localhost:47821` | `confirmado` |
| `pp_resolve.py` | executor do Resolve: um JSON por stdin, uma linha por stdout, **allowlist de comandos**, sem `eval` | `confirmado` |
| `aaf/` | pyaaf2 + pyavb embarcados, `pp_aaf.py`/`pp_avb.py` | `confirmado` |
| `pyodide/`, `python/`, `ffmpeg`, `ffprobe` | runtimes embarcados | `confirmado` |
| Info.plist | Supabase (`PPSupabaseURL` + chave *publishable*), PostHog, esquema de URL `postproducer://`, AppleEvents (After Effects, FCP), microfone e reconhecimento de fala **local** | `confirmado` |

## Qual IA, e quem paga

- ⭐⭐ **Claude, pelo Claude Code CLI, mas com `ANTHROPIC_BASE_URL` apontando para um GATEWAY
  deles** e `ANTHROPIC_AUTH_TOKEN` = um token de gateway emitido por execução. Não é a assinatura
  do usuário: eles revendem o uso. Cada plano aprovado leva `limitUsd` (US$ 0,05 a 25). `confirmado`
- O gateway é um **roteador** (o comentário o chama de "FireRouter"): o site manda o `baseUrl`, o
  id do modelo no roteador e o modelo Claude que ele representa. Na v1.2 há **papéis**
  (`lead`, `senior`, `router`, `runner`, `eyes`, `small`, `operator`, `operatorQuick`); os padrões
  que se veem são `claude-sonnet-5-5` (operador) e `claude-haiku-5-5` (rápido), com o Opus para
  o papel `senior`. `confirmado` (nomes), `inferido` (o que cada papel faz)
- ⭐ **As instruções moram no servidor.** O Mac manda marcadores; o gateway os substitui. É como
  eles protegem o prompt e as skills de quem abre o bundle — e é o que deixa este estudo raso na
  parte do *ofício*. `confirmado`
- Higiene do CLI que coincide com a nossa: `settingSources: []` ("nunca o CLAUDE.md, hooks ou MCP do
  usuário"), MCP próprio, `WebFetch`/`WebSearch` proibidos, `CLAUDE_CONFIG_DIR` próprio, memória
  automática desligada, `TMPDIR` numa pasta da conversa. ⚠️ Eles **deixam o Bash ligado** (as
  skills mandam rodar `pp-vision`, `osascript`, ffmpeg) e filtram por hook (`PreToolUse`). `confirmado`

## Como controla cada app

| app | mecanismo | confiança |
|---|---|---|
| **Premiere** | painel UXP invisível-ou-quase que conversa com a ponte por HTTP local (porta 47821) | `confirmado` |
| **Resolve** | API externa de scripting (Studio, *External scripting: Local*), pelo `pp_resolve.py` com allowlist | `confirmado` |
| **Final Cut** | FCPXML (77 menções) + AppleScript, e a GUI operada pelo agente **num monitor virtual** que o usuário não vê; o chat mostra a imagem ao vivo. Arrasto, botão direito e clique com tecla segurada são recusados lá (tomariam o ponteiro real) | `confirmado` |
| **After Effects** | AppleEvents (`DoScript`) | `confirmado` |
| **Media Composer** | ⭐ **nenhum gRPC** (0 ocorrências de `9100`/`mcapi`): a tela e o teclado **reais do usuário**, com borda azul em volta da tela, Esc para parar e qualquer tecla/clique dele segurando o próximo passo; mais **AAF/ALE/AVB gerados e importados** ("First: sem import de AAF, logo sem *make* nem *edit*"). Lê o projeto pelas `defaults` do MC e pelas pastas `Avid Projects` | `confirmado` |

⇒ No Avid eles fazem o que o nosso **piloto** faz, só que como produto — e escolheram não usar a
API gRPC que nós usamos. É a confirmação externa de que, sem painel assinado, quem não conhece a
9100 cai na GUI. `inferido`

## A integração com a web e o celular

⭐⭐ **Não há conexão do celular com o Mac, nem push no Mac.** O site (Supabase por trás) é o centro;
o Mac é um **trabalhador que busca tarefas**:

```
celular / navegador ──→ site post.mov ──(fila no banco)──┐
                                                         │  POST /api/v1/editor-bridge/…
Mac (pp-bridge, daemon) ── pair → heartbeat → claim ─────┘  (Bearer ppd_… do aparelho)
                        ── agent/claim → runs/{id} (heartbeat) → events → questions → finish
```

- **Pareamento:** código curto (alfabeto Crockford, `I/L→1`, `O→0`) troca por um token de
  aparelho `ppd_` + 43 caracteres. `confirmado`
- **Polling:** fila a cada 1 s, heartbeat de trabalho a cada 15 s, **lease de 90 s** (Mac que
  some solta o trabalho), heartbeat do daemon com piso de 3 s. Sem WebSocket, sem Realtime. `confirmado`
- ⭐ **O controle remoto viaja na RESPOSTA do heartbeat:** `stop`, `held`, modo Auto/Manual, as
  **respostas às perguntas de permissão dadas na web ou no celular**, e mensagens novas enviadas
  enquanto o agente trabalha. Cada mensagem guarda `sentFrom: mac | web | phone`. `confirmado`
- **Aprovação de plano** do celular: `planHash` (SHA-256) + `revision` + `nonce` + `limitUsd` +
  `deviceId` ("do celular: um Mac que permita"). `confirmado`
- Renders e prévias sobem por upload multipart para o site, e o celular os vê lá. `confirmado`
- **Notificação no celular:** nada no Mac a dispara diretamente — nenhum FCM/APNs/Expo/ntfy no
  bundle. Ela sai do SITE quando o Mac registra uma pergunta (`runs/{id}/questions`). Se é
  Web Push de PWA ou app nativo, **não se vê daqui**. `inferido` / `pendente`

## O que isto ensina para nós

- ⭐⭐ O "chat no celular" é barato **se o portão já for assíncrono** — e o nosso é (ADR 0008:
  o cartão fica, o clique executa depois). O que falta é só um lugar fora da rede local onde a
  pendência e o clique se encontrem; o Mac/PC busca, nunca é buscado (sem porta aberta, sem NAT).
- ⚠️ O preço que eles pagam e nós não: um **backend na nuvem** com contas, fila, upload de mídia
  e cobrança do modelo. É a "camada extra" que o autor apontou.
- ⭐ Prompt e skills no servidor é a única defesa contra quem abre o bundle; o resto (4,5 MB de JS
  com comentários) veio legível.

## O que a casa decidiu aproveitar (autor, 2026-10-30)

O estudo rendeu mais **confirmação** do que técnica: eles chegaram ao nosso desenho (CLI como motor,
app fora do NLE, uma ponte por editor) e erraram o Avid por não conhecerem a 9100.

| ideia deles | decisão |
|---|---|
| **borda colorida na tela** enquanto o agente opera a GUI real | ⭐ **adotar no piloto** — para o autor saber quando o piloto está ativo, quando o freio/pausa vale, e se o acionamento funcionou |
| **pausa pelo toque**: tecla/clique do usuário segura o próximo passo até ele parar | ⭐ **adotar no piloto** (o F12 continua sendo o PARAR; o toque é a PAUSA) |
| aprovação amarrada por `planHash` + `nonce` | já é quase o ADR 0008 (executa com os argumentos que o editor leu); o hash só se paga se a aprovação vier de outro aparelho |
| monitor virtual para operar a GUI sem tomar a tela | anotado; é coisa do Mac (`CGVirtualDisplay`), no Windows exigiria driver de display. Não agora |
| gateway próprio / revender o modelo | ⛔ **não**: a assinatura é do editor, e isso é escolha de produto |
| site como fila + celular controlando o Mac | ⛔ **não neste desenho** — ver abaixo |

⛔⛔ **A brecha não é a conexão, é o que ela carrega.** O formato deles (o Mac só busca, nunca abre
porta) é o jeito mais seguro de ter remoto. O risco é a mensagem do celular virar turno de um agente
**com Bash ligado**: quem tomar a conta ou o site comanda a máquina do editor.

⭐ **Quando houver acompanhamento pelo celular, em degraus** (cada um com risco muito menor):
1. **Só saída** — o serviço avisa ("terminou", "um cartão espera você"); nada volta pelo canal.
2. **Só sim/não sobre um cartão que JÁ existe** no PC, amarrado por hash — nunca texto livre, nunca
   pedido novo. Nasce do nosso portão (o cartão já espera sem prazo), não de um servidor.
3. Chat remoto: não previsto para o Ciclo Assist.

## O que NÃO foi feito

- Nada instalado, executado ou logado; o site foi lido sem sessão.
- `PostProducerDesktop` (Swift) não foi desmontado — só o Info.plist.
- O `main.js` do painel UXP e o `pp_resolve.py` foram lidos só no cabeçalho.
- As skills reais (servidor) não existem no bundle; o "ofício" deles não foi visto.
- O lado web (app do celular, notificações, o gateway) **não foi alcançado** — tudo o que se diz
  dele é pelo contrato que o Mac fala.
- A chave Supabase *publishable* e a do PostHog estão no Info.plist (são públicas por desenho);
  não foram usadas.

## ⭐⭐ A regra da Anthropic para embarcar o Claude Code (lida em 2026-10-31)

Pergunta da casa: dá para o app levar o `claude` dentro do instalador, como o Post Producer, mas com a conta DO
EDITOR? Fonte: `code.claude.com/docs/en/legal-and-compliance` e `…/agent-sdk/overview`, lidas sem login. `confirmado`
(o texto), **não é parecer jurídico**.

- ✅ *"preinstalling or running Claude Code in your products"* é permitido aceitando os Commercial Terms, com o
  **binário sem modificação** (sem remover nenhum método de login) e **sem pagar, revender ou intermediar o uso**:
  cada usuário entra com a própria chave de API, a própria assinatura ou o próprio provedor (Bedrock/Vertex/Foundry).
- ✅ *"Nor does it prevent an end user from signing in to the unmodified Claude Code binary with their own Claude
  subscription, including where a platform hosts Claude Code"*.
- ⛔ O app não pode coletar, guardar nem intermediar credencial/token do claude.ai: o login termina **no fluxo da
  Anthropic**. ⇒ `claude auth login` num `CLAUDE_CONFIG_DIR` do app, e o app nunca lê o arquivo de credencial.
  `claude setup-token` é para CI (o usuário copiaria o token) — não serve.
- ⛔ Claude/Anthropic não entram no nome ou logo do produto; "roda o Claude Code", em texto, pode.
- ⚠️ Tensão: a página do Agent SDK diz *"Unless previously approved, Anthropic does not allow third party developers
  to offer claude.ai login…"*. Leitura que concilia: o login é o do binário oficial, não um nosso. Confirmar com a
  Anthropic antes de distribuir fora da casa.
- O Post Producer fica do outro lado da linha: gateway próprio (`ANTHROPIC_BASE_URL`) e uso revendido.

Uso: Ciclo Assist, `docs/plano/2026-10-31-o-assist-operador.md`. `pendente`: o `claude auth login` num config dir
próprio, lançado por app sem console, no Windows e no Mac.

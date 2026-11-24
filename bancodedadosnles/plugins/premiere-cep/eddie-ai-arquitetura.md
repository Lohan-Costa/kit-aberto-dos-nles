# Eddie AI — como um assistente de decupagem dirige o Premiere

Segundo caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md)
(o primeiro foram Jumper e Quickture, em [`../avid-panel-sdk/paineis-de-terceiros.md`](../avid-panel-sdk/paineis-de-terceiros.md)).
Fatos consumíveis em [dados/eddie-ai.json](dados/eddie-ai.json).

**Por que este caso importa:** o Eddie é a validação independente da arquitetura que o
[README](README.md) desta pasta já defende — **painel fino + motor externo** — levada ao extremo:
o motor não está nem na máquina. E é o exemplo mais completo que temos de *como entregar decisões
de corte a um NLE*, com **três** caminhos distintos para a timeline.

## O que foi inspecionado

| peça | versão | onde |
|---|---|---|
| App desktop "Eddie AI AE" (Electron) | 3.5.52 · bundle `com.electron.eddie-ai-mcp` | `Eddie+AI+AE.dmg` (198 MB), baixado de `app.heyeddie.ai/new` em 2026-08-09 |
| Painel CEP instalado | `com.eddyai` 2.0.55 (build 2026-04-10) | `/Library/Application Support/Adobe/CEP/extensions/Eddie AI/` |
| Painel CEP embarcado no app | `eddie-mcp-premiere-panel` **2.1.2** | `Resources/premiere-panel/com.eddyai.ae.zxp` (4,8 MB) |

O app **carrega o próprio ZXP** e se atualiza sozinho (`panel-manifest.json` traz `version`,
`gitSha` e `zxpSha256`; `sudo-prompt` nas dependências para escrever em `/Library`). O painel
instalado estava 2 versões atrás do que o app carrega — o app é a autoridade, não o Exchange.

## A arquitetura em três camadas

```
   ┌─ NUVEM ────────────────────────────────────────────────┐
   │  mcp.heyeddie.ai        ← servidor MCP + agente        │
   │  premiere-ext-XXXX.heyeddie.ai  ← API do painel        │
   │  S3 us-east-2           ← config remoto + mídia        │
   └────────────▲───────────────────────────────▲───────────┘
                │ webview (cookie injetado)     │ WS de saída + HTTPS
   ┌────────────┴──────────────┐                │
   │ APP ELECTRON (a casca)    │                │
   │  renderer main_window     │                │
   │  renderer mcp_webview ────┘                │
   │  ffmpeg/ffprobe/mediainfo/braw-decode      │
   │  localServer.js                            │
   └────────────┬───────────────────────────────┘
                │ cliente WS/HTTP → 127.0.0.1:61202
   ┌────────────▼──────────────────────────────┐
   │ PAINEL CEP (dentro do Premiere)           │
   │  Express + ws  ← SERVIDOR                 │
   │  jsx/PPRO/Premiere.jsx (5.267 linhas)     │
   └───────────────────────────────────────────┘
```

### A direção do fio (o fato que mais importa)

**Quem serve é o painel.** `new ws_1.WebSocket.Server({ server: httpServer })` com
`httpServer.listen(61202)`: o painel CEP sobe um Express + WebSocket em **`127.0.0.1:61202`** e o
app desktop conecta nele como cliente. Não há pareamento, porta anunciada nem descoberta: a porta
é **fixa e hardcoded**, e o painel dá `kill -9` em quem estiver ocupando ela antes de subir
(`kill-port` + `lsof | grep LISTEN | xargs kill -9`).

Isso é o inverso do nosso Órbita Sync (painel faz `fetch` para o app em `127.0.0.1:7817`). As duas
direções funcionam sob o sandbox do CEP; a do Eddie tem a vantagem de o app poder **empurrar**
evento para o painel sem polling, e a desvantagem de a porta pertencer ao painel — se o Premiere
não estiver aberto com o painel visível, não há ninguém escutando.

O painel também abre um **WebSocket de saída para a nuvem** (`eddy_endpoint`). Mensagens
observadas no `switch`: `auth`, `init`, `get_medias_in_bin`, `load_app_state`,
`notify_invoke_event_callback`, `open_external_page`. Ou seja: **a nuvem consegue mandar o painel
ler a bin do Premiere**. O app desktop não é intermediário obrigatório da conversa.

### O host de nuvem é config remoto, com validade

`globalState/serverConfig.js` monta na hora do boot:

```
https://eddie-premiere-extension.s3.us-east-2.amazonaws.com/distributions/{darwin|win32}/{x64|arm64}/{versão}/config.json
```

Buscado em 2026-08-09 (HTTP 200, bucket público) para `darwin/arm64/2.0.55`:

```json
{ "eddy_endpoint": "https://premiere-ext-ifykyk.heyeddie.ai",
  "expiryDate_ddmmyyyy": "23-05-2025" }
```

O hostname tem sufixo aleatório e **roda por versão**; o hardcoded no bundle
(`premiere-ext-u0etjdhta4.heyeddie.ai`) é só fallback. Padrão excelente e barato de copiar:
**trocar de backend sem republicar painel**. (O `expiryDate` já passado sugere que 2.0.55 é
legado — coerente com o app carregar 2.1.2.)

## Onde vive o agente — e a inferência que eu errei

O `package.json` do app declara **`@anthropic-ai/sdk ^0.110.0`**. A leitura óbvia — "o loop de
agente roda na máquina do editor" — **está errada**. Nos bundles: zero `api.anthropic.com`, zero
`/v1/messages`, zero `x-api-key`, zero `dangerouslyAllowBrowser`. Todas as 96 ocorrências de
`anthropic` no renderer são do **Sentry** (`auto.ai.anthropic`, `gen_ai.*`, contadores de
`cache_read_input_tokens`) — o SDK está ali porque a instrumentação de IA do Sentry o referencia.

O agente roda em `mcp.heyeddie.ai`. O que o app tem é um **renderer `mcp_webview`** cujo preload
expõe `window.__eddieHost` para a web app carregada dentro dele:

| método exposto | serve para |
|---|---|
| `postContents`, `postPrompt`, `postRun` | a web app fala com a casca |
| `postExport`, `postRenderMp4`, `postExportElements` | pedir capacidade nativa |
| `premiereRoundtripStatus / Install / Export` | ver se o painel está vivo, instalá-lo, exportar |
| `resolveRoundtripStatus / Install / Export` | idem para o **DaVinci Resolve** |

⭐ **É a lição de calibração da técnica se repetindo:** *um SDK no bundle não é um agente*, como
*um modelo no disco não é uma feature* (Jumper). O nome do bundle (`...-mcp`), o renderer dedicado
e os atributos de OpenTelemetry (`MCP_TOOL_NAME_ATTRIBUTE`, `MCP_TRANSPORT_ATTRIBUTE`,
`MCP_PROTOCOL_VERSION_ATTRIBUTE`, `MCP_SESSION_ID_ATTRIBUTE`, `MCP_SERVER_NAME/VERSION`) provam
MCP **como protocolo interno de produto**, com trace por chamada de ferramenta em produção.

A casca faz a autenticação por injeção: `MCP_SET_WEBVIEW_AUTH` / `MCP_PLANT_WEBVIEW_AUTH`
(`mcpAuthCookie`), `MCP_REMINT_BRIDGE_SESSION` e `mcpSessionKeepAlive`. Ou seja: **a mesma web app
que roda no navegador roda dentro do app**, e o app só acrescenta o que o navegador não pode —
tocar em disco, chamar o Premiere, rodar ffmpeg.

## Três caminhos para a timeline

Isto é o coração do que queremos aprender.

**1. Import de XML.** Rotas `/process-xml-content`, `/import-standard-project`,
`/import-timleline-from-timelines-project` [sic, typo deles] e as funções `importXMLToProject`,
`importXMLAndResolveToTimeline`. Dependências `xml-js`, `xmldom`, `fast-xml-parser`. Barato e
robusto; o NLE resolve a mídia.

**2. Montagem scriptada.** `/import-mc-timeline-scripted`, `/import-multicam-sequence`,
`/import-aroll-bin` → `createSequenceFromData`, `addClipsToSequence`, `updateClipItemTime`,
`ensureSequenceHasTracks`, `deleteEmptyTracks`, `addMarkersToSequence`, `recursiveCreateBinStructure`.
É a mesma família de chamadas que documentamos em [api-extendscript.md](api-extendscript.md) —
inclusive a limpeza de tracks vazias, que nós resolvemos via QE DOM.

**3. Arrastar o XML.** `IPC_DRAG_XML_FILE` — o app inicia um drag nativo de arquivo, o editor
solta no Premiere. **Zero painel, zero porta, zero instalação.** É o caminho de menor atrito e o
que sobrevive a qualquer mudança de SDK. Nós não temos isso.

Do lado do Resolve, o padrão muda de forma: `IPC_INSTALL_DAVINCI_SCRIPT`,
`IPC_CHECK_START_DAVINCI_SCRIPT`, `IPC_CHECK_DAVINCI_CONNECTION`, e então `IPC_DAVINCI_GET_BINS`,
`IPC_DAVINCI_GET_TIMELINE_INFO`, `IPC_DAVINCI_EXPORT_MC_SEQUENCE`, `..._EXPORT_TIMELINE`,
`..._EXPORT_MC_TIMELINE_SCRIPTED`, `..._EXPORT_XML_SCRIPTED`. Mesmas operações, transporte
diferente (script instalado + API do Resolve em vez de painel + porta). Vale para
`plugins/resolve/` quando essa pasta nascer.

E FCP existe como **formato**, não como painel: `IPC_FCP_MULTICAM_CLIPS`, `IPC_FCP_SYNC_CLIPS`,
`IPC_FCP_COMPOUND_CLIPS`, `IPC_EXPORT_FCP_CLIP`, `IPC_REPORT_UNSUPPORTED_FCPXML` (telemetria de
FCPXML que ele não soube ler — hábito bom de copiar).

## Superfície do painel (as 29 rotas)

Ingestão e transcode: `/process-sources`, `/check-process-sources`, `/process-create-proxy`,
`/process-transcode-clip`, `/process-multicam-clip`, `/process-timeline`, `/process-xml-content`.
Import: `/import-multicam-sequence`, `/import-mc-timeline-scripted`, `/import-standard-project`,
`/import-timleline-from-timelines-project`, `/import-aroll-bin`.
Leitura do projeto: `/get-medias-in-bin`, `/get-bin`, `/extract-timeline-info`, `/logs`.
Estado e ambiente: `/ping`, `/set-adobe-project-path`, `/set-adobe-log-path`, `/save-app-state`,
`/auth-callback`, `/reload-extension`.
Callbacks (o AME avisa quando terminou): `/transcode-callback`,
`/transcode-multicam-sequence-callback`, `/selected-medias-callback`.

Note `/reload-extension`: **o app recarrega o painel remotamente** — é assim que a atualização
2.0.55 → 2.1.2 entra sem o editor fechar o Premiere.

## O que sai da máquina — e por que ele é rápido

O Eddie **não analisa o vídeo original**. Ele manda o Adobe Media Encoder gerar um derivado
mínimo e sobe só ele, por **S3 multipart com URL pré-assinada** (`createPresignedUploadUrl`,
`initiateMultipartUpload`, `S3MultipartUploadJob`, `readFileChunk`, `finishMultipartUpload`).

Os quatro presets em `transcodePresets/` (valores lidos do XML do `.epr`; FPS convertido pela taxa
de ticks do Premiere, 254016000000 — ver [`../../transversal/tempo-e-timecode.md`](../../transversal/tempo-e-timecode.md)):

| preset | vídeo | áudio | para quê (inferido) |
|---|---|---|---|
| `audio_only_mp3_preset` | — | **MP3 128 kbps** | transcrição — o caminho mais rápido |
| `broll_minimun_fps_non_audio` | avc1 1920×1080 @ **10 fps** | (AAC 320 declarado, nome diz non-audio) | análise visual de B-roll |
| `match_source_low_quality` | avc1, match source @ 29,97 | AAC 128 | proxy geral, alvo ~1 Mbps |
| `eddie_proxy_preset` | avc1 @ 24, ingest "H264 MOV Proxy" | — | proxy de ingest do Premiere |

⭐ **A resposta para "por que o Eddie é tão rápido":** para falar de fala, ele sobe **MP3**. Um
áudio de 128 kbps de uma diária de 3 h tem ~170 MB; o vídeo original tem centenas de GB. A
percepção de velocidade vem de **escolher o menor derivado que responde à pergunta**, não de
inferência mais esperta. Para imagem, 10 fps sem áudio — mesma lógica do proxy 512×288 do
Quickture.

As dimensões nos `.epr` são o que estava salvo quando o preset foi criado (`3072×1620`,
`3584×2240`) e são sobrepostas pelo match-source; **não** tome como resolução de saída — marcado
`inferido`, faltaria medir um arquivo gerado.

Localmente o app carrega `ffmpeg` (49 MB), `ffprobe` (49 MB), `mediainfo` (15 MB) e
`braw/braw-decode` + `BlackmagicRawAPI.framework` — 113 dos 198 MB do DMG são esses binários.
`drivelist`, `check-disk-space` e `IPC_RESOLVE_LUCIDLINK_LOCAL_PATHS` (resolve caminho local de
**LucidLink**) completam a camada de mídia. E `IPC_OVERNIGHT_POWER_SAVE_START/STOP`: ele segura o
Mac acordado para subir a noite inteira.

**Ausência que informa:** nenhuma dependência de ML no bundle — sem `onnxruntime`, sem
`transformers`, sem `whisper`, sem vector DB, sem `model_licenses/`. Toda inferência é remota.
A sua leitura pelo tamanho do instalador estava certa, e por este motivo.

## Leitura de produto (o que o app faz que o painel não faria)

Pelas dependências do renderer: `@tiptap/*` (editor de texto rico — edição de transcrição,
paper-edit), `@dnd-kit/*` (reordenar segmentos arrastando), `fuse.js` (busca fuzzy local no
material já indexado), `@remotion/player` + `@remotion/media` 4.0.436 (**render de MP4 pelo
Remotion**, exposto como `mcpRender` / `IPC_MCP_RENDER_MP4` com `_EVENT`, `_CANCEL`, `_REVEAL`),
`mediabunny`, `qrcode`, `@stripe/*` (assinatura dentro do app), `archiver`, `pako`.

Ou seja: o app é **paper-edit + player + render**, e a timeline do NLE é o *destino*, não o local
de trabalho. `MCP_EXPORT_ELEMENTS` (+ `_EVENT/_CANCEL/_REVEAL`) sugere exportar elementos soltos,
não só sequência.

Sua intuição — "falta uma interface dentro do NLE" — bate com o que o binário mostra: o painel
deles tem 29 rotas de import/ingest e **nenhuma de UI**. Não existe conversa dentro do Premiere.
O `mcp_webview` prova, porém, que a interface de chat é uma **web app** — e uma web app é
exatamente o que um painel CEP pode hospedar. O caminho está aberto dos dois lados.

## Segurança e privacidade (o que registrar antes de usar com material sob embargo)

- **Dois webhooks `hooks.slack.com/services/T05685SC1T2/...` hardcoded** no servidor do painel
  (`slack/slack.js`, `slack-block-builder` nas deps, rota `/send-slack-message`). São *incoming
  webhooks* de gravação, embutidos em código que roda na máquina do cliente: qualquer um com o
  painel instalado pode postar no Slack deles. Não testado (não postei nada). Anotado como o que
  **não** fazer no Órbita.
- **Telemetria pesada:** Sentry (`@sentry/electron` + `@sentry/node` + `@sentry/react`), Amplitude
  **com session replay** (`@amplitude/plugin-session-replay-browser`, `@amplitude/rrweb`) e
  PostHog. Session replay grava a interface — com nomes de projeto, de clipe e conteúdo de
  transcrição na tela.
- **Bucket S3 de config é público** (respondeu 200 sem credencial).
- Sobe para a nuvem: MP3 do áudio e/ou proxy de baixa taxa de todo material que você mandar
  processar. Isso é o produto, não um vazamento — mas é fato a declarar num contrato de embargo.

## O que NÃO foi feito

- Nada instalado, nada executado, nenhuma conta criada, nada postado no Slack deles.
- DMG montado `-readonly` e **desmontado**; extraídos apagados.
- **Nenhuma lógica descompilada.** Os bundles não estavam obfuscados (o `javascript-obfuscator`
  está em `devDependencies` do painel mas o `dist` saiu legível) e havia `.js.map` por toda parte
  — **`sourcesContent` não foi lido**, nem os corpos de função. O que entrou aqui é rota,
  identificador de canal IPC, nome de símbolo, dependência declarada, preset e endpoint.
- Não foi lido o system prompt nem a lista de ferramentas do agente: eles vivem em
  `mcp.heyeddie.ai`, do lado servidor. **A superfície de ferramentas do MCP fica `pendente`** —
  e é o que mais valeria saber. Só sairia observando tráfego autenticado de uma sessão real.
- Resolução efetiva dos proxies: `inferido`, faltou medir arquivo gerado.

## ⚠️ Correção de 2026-08-09 (mais tarde): o que os 401 marcadores realmente são

Ao extrair a verdade-terreno para o Decupador de Mídia
(`_PRODUCAO-V/decupador de material bruto/referencia/extrair_referencia.py`), a leitura de que os
**401 marcadores carregavam a transcrição** se mostrou **errada**. Eles são **três tipos misturados**,
todos com `mType: "Comment"` e **sem nenhum campo que os distinga** — só o padrão do texto:

| tipo | quantos | exemplo |
|---|---|---|
| **trama** | **308** | `GROUP 1: Busca pelo filho desaparecido` (11 rótulos distintos) |
| **falante** | **58** | `Personagem J (Father searching for his son)` · `Personagem L (...)` · `Speaker` |
| **fala** (transcrição) | **35** | `Saiba que eu e Personagem K vamos ter muito dinheiro pra dar e vender…` |

Consequências para quem for medir contra isto:

- **Os 21.257 caracteres que eu tinha contado como transcrição incluíam os rótulos de trama
  repetidos 308 vezes.** A transcrição real são **3.105 caracteres em 35 segmentos**, somando
  **4,5 min** de fala marcada — não 91,2 min. O número antigo inflava a fala em ~47% dos marcadores
  e ~6× nos caracteres.
- ⭐ **A granularidade real da decupagem dele é a atribuição de trama: 308 segmentos**, distribuídos
  de forma bem desigual (o maior grupo tem 54, o menor 4).
- ⭐ **Ele faz atribuição de falante POR SEGMENTO** (58), com **3 rótulos** e **20 segmentos
  anônimos** (`Speaker`). Ou seja: dos três falantes que ele separou, **nomeou 2**. Isso é melhor do
  que "um falante por arquivo", que era a minha segunda leitura errada.
- O que **não** muda: **nenhum marcador, bin ou sequência carrega dado visual.** O único vestígio de
  imagem é o `INT` no *nome* do arquivo, como texto solto.

**Como o erro aconteceu, para não repetir:** contei `len(marcadores)` e somei `len(texto)` sem olhar
a *distribuição* dos textos. Os rótulos curtos e repetidos só aparecem quando se agrupa por conteúdo.
⭐ **Regra: antes de reportar contagem de um campo de texto livre, agrupar por valor e olhar os mais
frequentes.** Custou um `Counter`.

## Ver também

- [README](README.md) — nossa arquitetura de painel fino (Órbita Sync, `127.0.0.1:7817`)
- [api-extendscript.md](api-extendscript.md) — as chamadas de montagem e as armadilhas
- [`../avid-panel-sdk/paineis-de-terceiros.md`](../avid-panel-sdk/paineis-de-terceiros.md) — Jumper e Quickture
- [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md) — a técnica

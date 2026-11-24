# Chat Video Pro — painel que carrega o próprio Node, ffmpeg e um índice RAG

Quarto caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md)
(1º Jumper/Quickture, 2º [Eddie AI](eddie-ai-arquitetura.md), 3º [Premiere Copilot](premiere-copilot-arquitetura.md)).
Fatos consumíveis em [dados/chat-video-pro.json](dados/chat-video-pro.json).

**Por que este caso importa:** é o **terceiro ponto do triângulo**. O Eddie põe o motor num app
externo; o Premiere Copilot não tem motor nenhum (baixa o app a cada abertura); o Chat Video Pro
**põe o motor DENTRO do painel** — com Node próprio, ffmpeg próprio e servidor local em `:3737`. E é
ele que **prova, em produção e por documentação própria, que um painel CEP spawna processo** — a
pendência que ficou aberta no caso anterior.

Analisado só o que já estava instalado (`com.chatvideopro.panel` 3.2.0, 1,2 GB, 1.272 arquivos, em
`/Library/Application Support/Adobe/CEP/extensions/Chat Video Pro/`). Datas dos arquivos são todas
`31 Dez 2023` — normalizadas pelo empacotador, não servem para nada.

## ⭐ A pergunta do `child_process`, respondida

O manifesto pede o mesmo que o nosso: `--enable-nodejs`, `--mixed-context`, `--allow-file-access`
(+ `--enable-media-stream` para voz e `--autoplay-policy=no-user-gesture-required` para TTS).
Dentro do `bundle.js` (obfuscado ao estilo `javascript-obfuscator`, variáveis `L0`/`L1`, strings em
tabela) aparecem `require('child_process')` com **`execSync`, `spawn` e `execFile`+`promisify`** — e,
literalmente:

```js
spawn('xattr', ['-d', 'com.apple.quarantine', <caminho>], {stdio:'ignore'})
```

E o `MAC_INSTALL.md` que vem na extensão **documenta o mecanismo** em prosa: o painel inicia "a local
Node process for generation routes", com binários em `server/bin/`, e limpa a quarentena e o bit de
execução via `setMacExecutePermissions` em `nodeLauncher.ts`; se a automação falhar por Gatekeeper
corporativo, o usuário roda `xattr -d` e `chmod +x` na mão.

⚠️ **Nuance que muda o desenho:** o painel **não usa o Node do CEP como motor**. Ele usa o Node do
CEP apenas para **lançar o próprio Node**, que carrega em `server/bin/`:

| binário | tamanho |
|---|---|
| `node-macos-arm64` | 121,6 MB |
| `node-macos-x64` | 114,0 MB |
| `node` | 91,5 MB |
| `node-macos-legacy` | 91,5 MB |
| `node.exe` | 71,1 MB |

Faz sentido: o Node embutido no CEP é antigo e amarrado à versão do Premiere; um Node próprio dá
`import`/ESM moderno, versão estável e as mesmas rotas em qualquer host. **Isto sim promove o achado
do caso anterior de `hipotese` para `inferido` forte** — dois produtos independentes fazem, um deles
documenta. Só falta a nossa medição para virar `confirmado`.

⛔ **E continua não sendo motivo para mudarmos o Órbita** (decisão de 2026-08-09): motor no painel
custa portabilidade, e o nosso alvo é Premiere + Resolve + Media Composer — o Avid nem tem Node
(painel QtWebEngine que não lê disco). Vale para produto deliberadamente só-para-Premiere. Note que
o Chat Video Pro é exatamente isso: `<Host Name="PPRO" Version="[25.0,99.9]"/>`, e nada mais.

## Onde vão 1,2 GB — e por que ~1 GB é peso morto

| pasta | tamanho | o que é |
|---|---|---|
| `ffmpeg/` | 478 MB | `ffmpeg`/`ffprobe` **macOS universal (80 MB cada) E Windows (170 MB cada)** |
| `server/` | 467 MB | os cinco Node acima |
| `assets/` | 141 MB | chunks Vite + imagens |
| `api/` | 8,6 MB | o backend `.cjs` + `node_modules` |
| `vendor/` | 4 MB | SDK de licenciamento (abaixo) |
| `whisper/` | 3,4 MB | workers — **e dois placeholders**, ver abaixo |

Num Mac, os ~410 MB de binários Windows nunca rodam; num PC, os ~200 MB de macOS. **Empacotar todas
as plataformas para todos os usuários** é a explicação inteira do 1,2 GB. Se algum dia
distribuirmos painel com binário, é o erro a não repetir: um ZXP por plataforma.

Detalhe engraçado e instrutivo: o `MAC_INSTALL.md` manda instalar ffmpeg com `brew install ffmpeg`,
lista a ordem de busca (`PATH` → `/opt/homebrew/bin` → `/usr/local/bin` → `/usr/bin`) e diz que "um
ffmpeg embutido para macOS **pode vir numa versão futura**" — enquanto a pasta `ffmpeg/` com o
binário universal **já está ali**. **Documentação atrasa em relação ao build**, inclusive na deles.
É a razão de a técnica mandar ler o binário, não a doc.

## Como ele fala com os modelos

Dois caminhos, e nenhum servidor próprio de inferência:

1. **`fal.ai` como gateway de mídia generativa** (24 ocorrências em `api/*.cjs`, mais
   `queue.fal.run`, `rest.fal.ai`, `rest.alpha.fal.ai`). Os nomes de modelo declarados formam o
   catálogo do produto: **`veo-3.1`/`veo-3.0`** (vídeo), **`nano-banana`**,
   **`gemini-2.5-flash-image-preview`**, **`gpt-image-1`/`1.5`/`2`**, **`flux-2`/`flux-2-max`**,
   **`grok-imagine-image`/`grok-imagine-video`/`grok-text-to-image`/`grok-image-edit`/
   `grok-text-to-video`/`grok-image-to-video`**. Há um `grokImageFalAllowlist.cjs` — lista branca de
   quais modelos Grok podem passar.
2. **Direto no provedor** para texto: `api.openai.com` e
   `generativelanguage.googleapis.com` (Gemini). O painel linka `aistudio.google.com` e tem um
   `get-admin-key.gif` em `assets/` — **tutorial em GIF de como pegar a chave**. Ou seja: modelo
   **BYOK** (o usuário traz a própria chave), não assinatura de inferência.

Seletor de modelo de texto declarado no bundle: `gpt-5`, `gpt-5.5`, `gpt-5.3-instant`,
`gpt-5.2-instant`, `gpt-5.2-thinking`, `gpt-5-mini`, `gpt-5-nano`, `gpt-4.1`, `gpt-4.1-mini`,
`gpt-4.1-nano`, `claude-sonnet-4-6`, `gemini-3.1-pro`, `gemini-3.1-flash-lite-preview`,
`gemini-2.5-flash`. ⚠️ **Vários desses ids não correspondem a nome publicado de modelo** — são
rótulos de UI e/ou alias interno resolvido do lado deles. Não tome esta lista como catálogo real de
API de ninguém.

Do lado do dinheiro e da telemetria: `LEMON_API_KEY` (LemonSqueezy = licenciamento), PostHog
(`us.i.posthog.com`, `app.posthog.com`), `mailersend` nas dependências com uma função
`sendSupportEmailFromNode` — **o painel manda e-mail de suporte pelo Node local**.

E o servidor local escuta em **`localhost:3737`** (110 referências no bundle).

## A "memória avançada": RAG local sobre o conteúdo deles

O `Abstract` do manifesto promete "*advanced memory and learning capabilities*". O que existe:

- `cep-memory-manager.js` (1,9 MB)
- `whisper/embeddings-worker-cep.js` (1,0 MB) + `assets/clientRAG-*.js` + `assets/embeddingsService-*.js`
- `@huggingface/transformers` ^3.8.1 nas dependências (Transformers.js, roda ONNX no próprio painel)
- um wasm de **21,5 MB na raiz que é o `onnxruntime`** (2.247 menções internas, com
  `WhisperEncoderSubgraph`/`WhisperDecoderSubgraph`)
- `training-embeddings-meta.json`:

```
indexVersion  content-1170-9c478f1a
model         Xenova/all-MiniLM-L6-v2
dimensions    384
chunkCount    1170
buildTime     2026-05-26T14:31:54.499Z
```

⭐ **Leitura honesta:** isto é **RAG sobre 1.170 pedaços de conteúdo próprio** (a doc/treinamento do
produto — `docs.chatvideopro.com` aparece 42 vezes no bundle), embutido no ZXP e consultado
localmente com MiniLM-L6-v2 de 384 dimensões. **Não é memória do usuário nem "aprendizado"**: é
índice fixo, com data de build. É o padrão "o assistente sabe o manual do próprio produto" — barato,
útil e honesto de implementar; só o nome no manifesto é que é generoso.

## ⚠️ Dois placeholders vendidos como recurso

`whisper/ggml-base.en.bin` tem **313 bytes** e `whisper/whisper.wasm` **257 bytes**. São arquivos de
texto:

```
# Placeholder for Whisper model file
# This file should be replaced with the actual ggml-base.en.bin model
# Download from: https://huggingface.co/ggerganov/whisper.cpp/tree/main
```

Os workers `whisper-worker.js` (1,5 MB) e `whisper-worker-cep.js` (1,0 MB) estão completos, e
`vosk-browser` está nas dependências — mas **o caminho whisper.cpp local não funciona no build
enviado**. Transcrição real sai por outra via (`vosk-browser`, ou modelo baixado em runtime pelo
Transformers.js, ou rota de nuvem — não determinado).

⭐ **É a lição de calibração da técnica pela terceira vez, agora na forma mais nua:** no Jumper, um
modelo empacotado não era feature; no Eddie, um SDK no bundle não era agente; aqui, **o arquivo do
modelo é um comentário de 313 bytes**. *Sempre confira o tamanho do arquivo antes de concluir que
uma capacidade existe.* Custou dois `ls -la`.

## Como opera o Premiere — a maior superfície ExtendScript que já lemos

9.277 linhas em `jsx/` (`main_v2.jsx` com 8.093, `cvpAudioExport.jsx`, `veo-worker.jsx`, `main.jsx`),
**em claro** — ao contrário do bundle, que é obfuscado. Nomes de função reveladores:

- **Leitura:** `getActiveSequence`, `getSelectedClips`, `getSelectedClipDetailed`, `extractClipInfo`,
  `getActiveSequenceInOutMarks`, `getSequenceFps`, `getSequenceZeroPointSecs`, `findSequenceByName`,
  `getSystemInfo`
- **Export:** `listAMEPresets`, `exportSelectedClipViaEncoder`, `exportNestedSequenceClip`,
  `checkExportComplete`, `exportClipThumbnail`, `binaryToBase64`, `exportSequence`
- **Escrita:** `createSequence`, `addMarker`, **`applyColorCorrection`**, `jumpToTimecode`
- **Tempo:** `timecodeToTicks`, `ticksToTimecode`, `_cvp_parseTimecodeToSeconds`,
  `_cvp_resolveMarkSeconds`
- **Job/infra:** `createJob`, `getJobStatus`, `healthCheck`, `startVeoService`, `testVeoWorker`,
  `diagnosticSystemTest`, `testJSXExecution`, `cvpClipboardWrite/Read`, `sendSupportEmailFromNode`
- ⭐ **`_cvpComputeTrackTopologySig`** — assinatura da topologia de tracks. Ideia boa e reusável:
  em vez de reler a timeline inteira, guarda uma **impressão digital da estrutura** e compara para
  saber se algo mudou. Contorna a ausência de evento de mudança de timeline, que é exatamente a dor
  que medimos no Avid (`../avid-panel-sdk/`).

### Duas alavancas novas para o nosso banco

1. **`applyColorCorrection` + `presets/CVP - LUMETRI COLOR.prfpset`** — um `.prfpset`
   (`EffectPreset`/`FilterPreset` com `ADBE Lumetri`) aplicado por ExtendScript. **Aplicar EFEITO por
   preset** não está em [api-extendscript.md](api-extendscript.md); é o caminho para "o agente faz a
   correção de cor" sem escrever parâmetro por parâmetro.
2. **`listAMEPresets`** — enumerar os presets do AME em runtime em vez de assumir caminho fixo.

### Os presets, e a regra que se repete

| preset | saída |
|---|---|
| `CVP_ASR_Mono_48k` | 48 kHz, **2 canais** (o nome diz Mono) |
| `CVP_Audio_AAC` | 44,1 kHz, 192 kbps |
| `CVP_PNG_Preset` | **PNG 3840×2160** (quadro para visão / geração de imagem) |
| `CVP_H264_MatchSource` | 1080p25, **40 Mbps** (nome: "H264 40Mbps") |
| `H264_Match_Source_High` | 1080p24, 10 Mbps |

⚠️ **Segunda ocorrência de nome de preset que mente** (o `CVP_ASR_Mono_48k` é estéreo; no Premiere
Copilot o "EXPORT_4K 60fps" era 1080p25). Vira regra: **ler o XML do `.epr`, nunca o nome**.

A regra transversal dos quatro casos se mantém: **derivado por tarefa** — áudio dedicado para ASR,
PNG em 4K para imagem, H.264 alto só para entrega.

## Licenciamento: `vendor/aesp.umd.js` é o SDK do aescripts.com

`Aesp` como global UMD, 376 referências a `aescripts.com`, 349 a `license`, com strings em tabela
(obfuscado). É a **biblioteca de licenciamento do aescripts+aeplugins**, o marketplace onde o painel
é vendido (`aescripts.com` também aparece no `bundle.js`).

⭐ **Achado de negócio, não técnico:** existe SDK de licenciamento pronto para painel CEP, com loja,
trial e ativação resolvidos por terceiro. Se algum dia vendermos um painel só-para-Premiere, é o
caminho mais curto — não precisamos escrever licenciamento.

## Segurança e privacidade

- **BYOK é o melhor cenário dos quatro produtos:** a chave é do usuário e o tráfego de inferência vai
  direto ao provedor. Não há intermediário lendo o conteúdo (fora o fal.ai, que é o próprio gateway).
- Nenhum `.env` nem chave em claro na extensão instalada. As `process.env` que aparecem são do lado
  servidor deles (`LEMON_API_KEY`, `FAL_WEBHOOK_URL`, `UPSCALE_WEBHOOK_URL`).
- `<RequiredPermissions><Permission>https://*.vercel.app</Permission>` — declara restrição de
  domínio, ao contrário do Premiere Copilot. Mas é largo: **qualquer** app na Vercel.
- Telemetria PostHog.
- ⚠️ **O painel executa `xattr -d com.apple.quarantine` num binário que ele mesmo distribui.** É
  legítimo aqui (é o Node deles), mas é exatamente o gesto que um malware faria; e significa que
  qualquer coisa que consiga escrever em `server/bin/` ganha execução com o usuário do editor. Se
  fizermos igual, o binário tem de ser verificado por hash antes de rodar.

## O que NÃO foi feito

- Nada instalado (a extensão já estava na máquina), nada executado, nenhum binário rodado, nenhuma
  conta criada, nenhuma requisição enviada a servidor deles.
- **Nenhuma lógica descompilada.** O `bundle.js` (11,5 MB) e o `vendor/aesp.umd.js` são obfuscados e
  foram lidos **só por `grep` dirigido** (hosts, portas, nomes de modelo, `child_process`, chaves).
  Dos `.jsx` em claro e dos `.cjs` do `api/` saíram **apenas nomes de função e de arquivo** — nenhum
  corpo, apesar de estarem legíveis.
- Não determinado: **qual caminho de ASR realmente funciona** no build enviado (whisper local está
  quebrado; `vosk-browser` vs. Transformers.js em runtime vs. nuvem — `pendente`).
- Não medido: o `child_process` funcionando sob o nosso sandbox (falta o nosso teste); o conteúdo dos
  1.170 chunks do índice RAG (não lido).

## Ver também

- [premiere-copilot-arquitetura.md](premiere-copilot-arquitetura.md) — o extremo oposto: painel sem motor
- [eddie-ai-arquitetura.md](eddie-ai-arquitetura.md) — motor em app externo + nuvem
- [README](README.md) — a nossa escolha e por que ela continua sendo motor externo
- [api-extendscript.md](api-extendscript.md) — onde entram `applyColorCorrection` e `listAMEPresets`

# Fontes — plugins/premiere-cep

Rastreabilidade das descobertas.

| bloco | origem | data | confiança |
|---|---|---|---|
| Arquitetura painel fino + servidor local, CEP vs UXP | `DRAMASYNC/plugins/premiere-cep/` + `src-tauri/src/httpserver.rs` | 2026-07-26 | confirmado |
| `getCurrentProjectViewSelection`, bin pai via varredura, tipos CLIP/BIN | `DRAMASYNC/plugins/premiere-cep/jsx/host.jsx` | 2026-07-26 | confirmado (teste GUI no Premiere 25.6.5) |
| `overwriteClip` tempo em segundos, não reimporta | idem `host.jsx` + teste GUI | 2026-07-26 | confirmado |
| **Regra áudio vinculado (V k ↔ A k), setTargeted não redireciona** | testes GUI sucessivos (áudio duplicando/empilhando até isolar a regra) | 2026-07-26 | confirmado |
| `createNewSequenceFromClips`, `setName`, `remove` | `host.jsx` + teste GUI | 2026-07-26 | confirmado |
| **QE `removeEmptyVideoTracks/removeEmptyAudioTracks`** | busca na comunidade Adobe (link em `_meta.fontes`) + teste GUI | 2026-07-26 | confirmado |
| Instalação (pasta CEP, PlayerDebugMode, symlink) | `DRAMASYNC/src-tauri/src/nle_install.rs` + teste GUI do botão instalar | 2026-07-26 | confirmado |
| Total de canais de áudio (somar streams; MediaInfo dá só o 1º) | ffprobe vs `src-python/media/inspector.py` | 2026-07-26 | confirmado |
| `TrackItem.move(Time)` move (e `clip.start=` APARA) | `host.jsx` + teste GUI | 2026-07-31 | confirmado |
| Timeline não repinta após script (clipe invisível até hover) | teste GUI (print do usuário) | 2026-07-31 | confirmado |
| Playhead/`activeSequence` como provocação de redesenho | comunidade + `host.jsx` | 2026-07-31 | a validar |
| **Eddie AI: painel serve em `127.0.0.1:61202` (app é cliente), 29 rotas, config remoto no S3** | `Eddie+AI+AE.dmg` 3.5.52 + painel `com.eddyai` 2.0.55 instalado | 2026-08-09 | confirmado (lido de manifesto, `main.js`, `serverConfig.js`) |
| **Eddie AI: 3 caminhos para a timeline (XML / scriptado / drag nativo)** | rotas + `jsx/PPRO/Premiere.jsx` (nomes de símbolo) + canais IPC do app | 2026-08-09 | inferido |
| **Eddie AI: agente roda no servidor (`mcp.heyeddie.ai`), não na máquina** | ausência de `api.anthropic.com`/`/v1/messages`/`x-api-key` nos bundles; `@anthropic-ai/sdk` é da instrumentação do Sentry | 2026-08-09 | inferido — **correção de inferência anterior** |
| **Eddie AI: presets AME do que sobe (MP3 128k para fala, 10 fps sem áudio para imagem)** | `transcodePresets/*.epr` (XML) | 2026-08-09 | inferido (dimensão sobreposta por match-source, não medida) |
| **Eddie AI: webhooks Slack hardcoded + session replay** | `server/dist/slack/slack.js`, `package.json` do app | 2026-08-09 | confirmado (não testado — nada foi postado) |

| **Premiere Copilot = pasta `PremiereGPTBeta`; painel é loader de 5 KB que injeta app remoto de 2 MB** | `PremiereCopilot-Installer-Mac-ARM.pkg` (xar+cpio, sem instalar) + `GET api.premierecopilot.com/api/snake3` | 2026-08-09 | confirmado |
| **Premiere Copilot: nenhum cliente de LLM nem credencial no cliente; seletor de modelo (claude/gpt-5/gemini) roteado no servidor** | grep dirigido no bundle remoto | 2026-08-09 | inferido |
| **Premiere Copilot: backend Python (langchain+librosa+sklearn, 345 MB) existia em abr/2026 e foi REMOVIDO na build de jul/2026** | `_internal/` do PyInstaller instalado vs. pkg de julho + bundle remoto sem `PremiereCopilotAPI` | 2026-08-09 | inferido |
| **Premiere Copilot: presets por TAREFA (mono 48 kbps p/ transcrição, WAV p/ silêncio, 4K p/ imagem)** | `js/libs/render/*.epr` | 2026-08-09 | confirmado |
| ⚠️ **`child_process` usado DENTRO do painel CEP (contradiz o README desta pasta)** | bundle remoto do Premiere Copilot (`window.require("child_process")`, 4 usos) | 2026-08-09 | **hipótese — não medido**, validar no Órbita |
| 🔒 **Premiere Copilot: execução de código remoto por desenho, sem `<RequiredPermissions>`** | `index.html` + `CSXS/manifest.xml` | 2026-08-09 | confirmado |

| ⭐ **`child_process` no painel CEP PROMOVIDO a `inferido` forte: 2º produto independente, e este DOCUMENTA** | `Chat Video Pro` — `bundle.js` (`execSync`/`spawn`/`execFile`, `spawn('xattr','-d',…)`) + `MAC_INSTALL.md` da própria extensão | 2026-08-09 | inferido (falta nossa medição) |
| **Chat Video Pro: motor DENTRO do painel — 5 binários Node (490 MB) + ffmpeg/ffprobe mac e Win (478 MB), servidor local em `:3737`** | `server/bin/`, `ffmpeg/`, grep no `bundle.js` | 2026-08-09 | confirmado |
| **Chat Video Pro: BYOK; fal.ai como gateway de mídia generativa (veo-3.1, nano-banana, flux-2, grok-imagine, gpt-image)** | `api/*.cjs` + `bundle.js` | 2026-08-09 | inferido |
| **"Advanced memory" = RAG local fixo: `Xenova/all-MiniLM-L6-v2`, 384 dims, 1170 chunks da doc PRÓPRIA** | `training-embeddings-meta.json` + `cep-memory-manager.js` + `assets/clientRAG-*.js` | 2026-08-09 | confirmado |
| ⚠️ **`ggml-base.en.bin` tem 313 bytes e `whisper.wasm` 257 — são PLACEHOLDERS de texto** | `ls -la whisper/` + `cat` | 2026-08-09 | confirmado |
| ⭐ **Aplicar EFEITO por preset: `applyColorCorrection` + `.prfpset` (`ADBE Lumetri`); e `listAMEPresets`** | nomes de função em `jsx/main_v2.jsx` + `presets/CVP - LUMETRI COLOR.prfpset` | 2026-08-09 | inferido — **alavanca nova, entrar em api-extendscript.md** |
| **`_cvpComputeTrackTopologySig`: assinatura de topologia de tracks em vez de reler a timeline** | nome de função em `jsx/main_v2.jsx` | 2026-08-09 | inferido (ideia, não medida) |
| **Licenciamento de painel CEP tem SDK pronto: `vendor/aesp.umd.js` = aescripts+aeplugins** | strings do UMD (376× aescripts.com) | 2026-08-09 | inferido |

| ⚠️ **CORREÇÃO: os 401 marcadores do Eddie são 308 trama + 58 falante + 35 fala** (a transcrição real é 3.105 ch / 4,5 min, não 21.257 / 91,2 min) | `_PRODUCAO-V/decupador de material bruto/referencia/extrair_referencia.py` sobre `EDDIE - DEMO.prproj` | 2026-08-09 | confirmado — **corrige o bloco de baixo** |
| ⭐ **Modelo de execução medido nos 3 painéis (estado-alvo / script gerado / RPC fino)** | varredura de verbos de mutação nos `jsx` + contagem de sítios de `evalScript` | 2026-08-09 | inferido → [`../../transversal/modelo-de-execucao-de-agente.md`](../../transversal/modelo-de-execucao-de-agente.md) |
| **Eddie NUNCA corta timeline: `overwriteClip` 11× e zero razor/split/trim/setPlayerPosition** | `Eddie AI/jsx/PPRO/Premiere.jsx` | 2026-08-09 | confirmado (varredura exaustiva dos verbos) |
| **Premiere Copilot: 2 sítios de `evalScript`, ambos ponte genérica `runExtendScript(code)`** | bundle remoto | 2026-08-09 | confirmado |
| **Chat Video Pro: `setPlayerPosition`/`split`/`trim`/`insertClip`/`applyPreset` + `tool_calls` no cliente** | `jsx/main_v2.jsx` + `bundle.js` | 2026-08-09 | confirmado |
| ⭐ **Regra: BYOK obriga o prompt a ser local; assinatura de inferência permite esconder** | comparação CVP (tem `tool_calls`) × Premiere Copilot (zero) | 2026-08-09 | inferido |
| ⭐ **Licenciamento: `vendor/aesp.umd.js` = SDK do aescripts+aeplugins** | strings do UMD | 2026-08-09 | inferido → [distribuicao-e-licenciamento.md](distribuicao-e-licenciamento.md) |
| **Empacotamento, 3 estratégias de atualização, Gatekeeper e checklist de release** | os 4 produtos | 2026-08-09 | ver [distribuicao-e-licenciamento.md](distribuicao-e-licenciamento.md) |

| ⭐⭐ **Chop Chop: nenhuma das 2 edições tem motor de forma de onda** (Resolve delega ao `AutoSyncAudio`; Premiere usa sobreposição de media time em ticks) | símbolos do JSXBIN + ausência de lib de áudio nos 105 npm + manual Resolve p.16 | 2026-08-24 | inferido, **triangulado por 3 evidências** → [chopchop-arquitetura.md](chopchop-arquitetura.md) |
| ⭐⭐ **O manual do concorrente admite: por forma de onda "Cam A não sincroniza com Cam B", e é lento demais para multicâmera** | `Chop Chop Resolve Manual v1.0.pdf` p.16 | 2026-08-24 | confirmado (texto do fabricante) |
| ⭐⭐ **Estado da ferramenta no XMP PRIVADO do projeto** (`kPProPrivateProjectMetadataURI`, `getStoredInfoAssignedTracks`) — o que faz o multi-day shoot encaixar takes novos | tabela de símbolos do `jsx/main.jsx` (JSXBIN) | 2026-08-24 | inferido — **o Órbita não faz** |
| **`AutoSyncAudio` + `audioSyncSettings` (4 chaves) e o clipInfo `{mediaPoolItem,startFrame,endFrame,trackIndex,recordFrame}`** | `ChopChop Resolve.py` desembrulhado (XOR 248 + base64) | 2026-08-24 | confirmado (lido no código) |
| **Stringout: 10 s entre shots, 2 s (PPro) / 3 s (Resolve) entre takes, multicâmera no mesmo `recordFrame`** | manuais + `round(fps * 10)` / `round(fps * 3)` no código | 2026-08-24 | confirmado |
| **QE DOM para criar/apagar/renomear trilha num produto comercial** (`addTracks`, `delEmptyTracksQE`, `insertClip`, `overwriteClip`) | tabela de símbolos do JSXBIN | 2026-08-24 | inferido — confirma que não é risco isolado nosso |
| ⭐ **`Column.Intrinsic.*` como fonte de start/end/timebase sem tocar no disco** | tabela de símbolos do JSXBIN | 2026-08-24 | inferido → alavanca para [api-extendscript.md](api-extendscript.md) |
| ⚠️ **`postinstall` roda `sudo installer` de um Python 3.13.2 no SISTEMA** | `Scripts/postinstall` do `.pkg` | 2026-08-24 | confirmado |
| **Metadado por ExifTool embarcado, não ffprobe; 7 pacotes npm in-house (autor usuario Terceiro)** | `node_modules/` do `.zxp` | 2026-08-24 | confirmado |
| 🔒 **Chaves do LicenseSpring + par AES `fkey`/`fiv` em claro no `ccsbrconfig.json`; ofuscação = XOR 248 com a chave no arquivo** | `.pkg` do Resolve | 2026-08-24 | confirmado → [`../../seguranca/`](../../seguranca/) |
| **Produto 100 % local: rede só para `chopchopsystems.com` e `api.licensespring.com`** | literais do script Resolve + deps do `.zxp` | 2026-08-24 | confirmado |

| ⭐⭐ **`updateUI` existe nas APIs de mutação e 2 produtos passam `true` sempre** (`setSelected(v,true)`, `setValue(v,true)`) | `_ab_extendscript` extraído do bundle + `FX_Launcher/host/index.jsx` | 2026-08-24 | inferido → [quatro-paineis-timeline.md](quatro-paineis-timeline.md) |
| ⛔ **NENHUM dos 4 painéis move clipe já colocado na timeline** | varredura de verbos nos 4 | 2026-08-24 | confirmado — emoldura a pendência do redesenho |
| ⛔⛔ **Contradição no nosso próprio registro sobre o `Cmd+A`** (DECISIONS diz que funciona, `host.jsx:414` diz que piora) | leitura cruzada dos dois | 2026-08-24 | confirmado — **resolver antes da próxima rodada** |
| ⭐ **Ponte DOM↔QE por `start.ticks`+`end.ticks`, com cascata para nome** | `FX_Launcher/host/index.jsx` (em claro) | 2026-08-24 | confirmado |
| ⭐⭐ **XMP: o prefixo do namespace decide a API, e `setProjectMetadata` recebe DOIS argumentos** | ExtendScript do Automation Blocks | 2026-08-24 | confirmado — 2ª aparição, agora com mecanismo |
| **81 blocos de operação + propriedades legíveis/escrevíveis de `TrackItem` (`nodeId`, `isAdjustmentLayer()`, `disabled`)** | bundles do Automation Blocks | 2026-08-24 | confirmado |
| **`start`/`end` de `TrackItem` são APARO; ninguém usa `move()`** | setter do Automation Blocks | 2026-08-24 | confirmado — bate com a nota do nosso `host.jsx` |
| **FireStarter: 3º ponto do modelo SCRIPT GERADO; 4ª aparição do canal aescripts** | `firestarter/index.js` + `lib/aesp.umd.js` | 2026-08-24 | confirmado |

| ⭐⭐ **"Has effects" está `onHold` no `FiltersDB.json` — especificado e NÃO publicado**, sem os `runOrder`/`testValue` que todo filtro publicado tem | `Selector/common/FiltersDB.json` (JSON em claro) | 2026-08-24 | confirmado (o fato); a razão é inferência → [selector-conform.md](selector-conform.md) |
| ⭐⭐ **`baseEffectsMatchNames`: os intrínsecos MUDAM com a espécie do clipe** (título tem `Graphic Group`+`Text` além de Motion/Opacity) | tabela de símbolos do JSXBIN do Selector | 2026-08-24 | inferido — **teste por contagem dá falso positivo silencioso** |
| ⭐⭐ **`runOrder` é custo MEDIDO; `isEnabled`=10966 × `isNotSelected`=150 no escopo de clipe** | `FiltersDB.json` | 2026-08-24 | confirmado — ler propriedade de `TrackItem` domina o custo |
| ⭐⭐ **`nodeId` é a moeda da seleção num produto comercial inteiro** (`getSelectionNodeIds` → `selectFromNodeIdsAry`) | tabela de símbolos do Selector | 2026-08-24 | inferido forte — promove a hipótese anterior; **falta medir se sobrevive a `move()`** |
| ⭐⭐ **`exportSeqAsFCPXML` + `xmlToJSON`: ler a timeline SEM passar pelo DOM, com efeitos e parâmetros** | tabela de símbolos do Selector | 2026-08-24 | inferido → a rota para relatório/conform |
| ⭐ **`AppWatcher`/`WatcherActiveProj.compare()` = polling; 2ª solução para a ausência de evento no CEP** | tabela de símbolos do Selector | 2026-08-24 | inferido |
| **63 filtros + 9 presets fixos, com ponte bin↔timeline nos dois sentidos** | `FiltersDB.json` + `FixedPresetsDB.json` | 2026-08-24 | confirmado |
| ⭐ **Selector e Chop Chop são da MESMA oficina** (mesmos npm in-house do mesmo autor, mesma proteção) | `node_modules/*/package.json` dos dois | 2026-08-24 | inferido |

| ⭐⭐⭐ **O "incremental" do Chop Chop é APAGAR E RECONSTRUIR** — a timeline é função pura da bin; não há estado | leitura integral de `ChopChop Resolve.py` (2.355 linhas) | 2026-08-24 | confirmado → [chopchop-algoritmo.md](chopchop-algoritmo.md) |
| ⚠️⚠️ **E o preço não está no manual: o trabalho manual do editor na timeline é destruído a cada ingestão** | mesma leitura | 2026-08-24 | confirmado |
| ⭐⭐ **O alinhamento por TC é a INTERSEÇÃO (apara cabeça E cauda); sem sobreposição o take é PULADO em silêncio** | mesma leitura | 2026-08-24 | confirmado |
| ⭐ **No modo waveform não há alinhamento: `startFrame = 0` para todos; e o `AutoSyncAudio` roda antes de metadado e bin** | mesma leitura | 2026-08-24 | confirmado |
| ⭐ **O parser de nome é posicional: as 4 primeiras corridas de dígitos** — `re.match` ancorado no modo manual, corte no 1º ponto, número extra no começo desloca tudo | mesma leitura | 2026-08-24 | confirmado |
| ⛔ **Defeito: `grupos[(shot,take)][cameraID]` é dicionário — clipes da mesma câmera no mesmo take se sobrescrevem sem aviso** | mesma leitura | 2026-08-24 | confirmado |
| ⚠️ **Índice de vídeo = câmera × maxCanaisDeÁudio + 1 → trilhas de vídeo vazias (mesma dor do nosso `host.jsx`); e não há API para mudar subtipo de trilha** | mesma leitura | 2026-08-24 | confirmado |
| ⭐⭐ **Objetos remotos do Resolve não são *hashable* (`id(obj)`); não há caminho de `MediaPoolItem` tipo Timeline para o objeto Timeline (busca por NOME)** | mesma leitura | 2026-08-24 | confirmado |
| ⛔ **TC sem drop-frame e falha devolvendo 0 (clipe vai para o início da timeline)** | mesma leitura | 2026-08-24 | confirmado |
| ⭐ **`Usage` + `Date Added` resolvem duplicata sem rastrear estado** | mesma leitura | 2026-08-24 | confirmado |

Método e limites da leitura integral do Chop Chop:
[chopchop-algoritmo.md](chopchop-algoritmo.md) §"A régua" — **régua nova**, autorizada pelo autor em
2026-08-24: leitura integral permitida, registro de **mecanismo e não de código**. Nada foi
transcrito (nem o regex do parser, nem a aritmética do alinhamento). **`LicenseWindow`/`LicenseCheck`
foram pulados de propósito**: nenhum mecanismo de licença foi examinado, contornado ou testado.
A leitura integral é **só da edição Resolve**; o lado Premiere continua em JSXBIN (só tabela de
símbolos). Nada instalado, nada executado. Temporários apagados.

Método e limites das descobertas do Selector:
[selector-conform.md](selector-conform.md) §"A régua" — `js/main.js` (652 KB, javascript-obfuscator)
**não foi desofuscado**; do JSXBIN saiu **apenas a tabela de 1.822 símbolos**, então tudo sobre
comportamento interno é `inferido` a partir de NOMES — o que é `confirmado` vem do `FiltersDB.json`
e do `FixedPresetsDB.json`, que são **metadados em claro** (passo 6 da ordem de ataque) e de onde vem
a maior parte do valor. **Nenhum mecanismo de licença foi examinado, contornado ou testado.** Nada
instalado, nada executado. Temporários apagados.

Método e limites das descobertas dos quatro painéis:
[quatro-paineis-timeline.md](quatro-paineis-timeline.md) §"A régua" — ⛔ **Markers Pro não foi
analisado** no nível interno — ⚠️ **e a razão registrada aqui estava errada:** não é payload
cifrado, é **JSXBIN aninhado em JSXBIN** (ES 2.1 dentro de ES 2.0, via `eval`); o que parecia
"stub decodificador" é o carregador. Corrigido em 2026-08-24, ver
[addendum-desofuscacao.md](addendum-desofuscacao.md) §3. O
ExtendScript do Automation Blocks é **string literal no bundle** e foi lido por busca dirigida,
minificado com identificadores de 1–3 letras. O `FX Spell Book.exe` (280 MB) e o `aesp.umd.js`
ficaram de fora. **Nenhum mecanismo de licença foi examinado, contornado ou testado.** Nada
instalado, nada executado. Temporários apagados.

Método e limites das descobertas do Chop Chop:
[chopchop-arquitetura.md](chopchop-arquitetura.md) §"A régua" — `js/main.js` (610 KB,
javascript-obfuscator) **não foi desofuscado**; do JSXBIN saiu **apenas a tabela de 1.235 símbolos**,
nenhuma linha de lógica reconstruída; o Python do Resolve foi desembrulhado mas lido por um script
que imprime **só** imports, assinaturas, métodos CamelCase e constantes — os algoritmos de parse e
agrupamento **não foram transcritos e não serão copiados**. Nada instalado, nada executado, nenhuma
conta criada, nenhuma licença tocada. O instalador Windows (Inno Setup) não foi extraído por ser
redundante com o payload macOS. Temporários (~900 MB) apagados.

Método e limites das descobertas do Chat Video Pro:
[chat-video-pro-arquitetura.md](chat-video-pro-arquitetura.md) §"O que NÃO foi feito" — `bundle.js`
(11,5 MB) e `aesp.umd.js` são obfuscados e foram lidos só por grep dirigido; dos `.jsx`/`.cjs` em
claro saíram **apenas nomes**. Nada executado, nenhuma requisição enviada.

Método e limites das descobertas do Premiere Copilot:
[premiere-copilot-arquitetura.md](premiere-copilot-arquitetura.md) §"O que NÃO foi feito" — o bundle
remoto de 2 MB foi lido **só por grep dirigido**; nenhum `.pyc` foi lido, nada foi instalado ou
executado, nada foi enviado (só `GET`).

Método e limites das descobertas do Eddie: [eddie-ai-arquitetura.md](eddie-ai-arquitetura.md) §"O que
NÃO foi feito". Nenhuma lógica descompilada; `sourcesContent` dos `.js.map` não foi lido.

Implementação de referência: **DRAMASYNC / Órbita v0.1.12** (o painel `Órbita Sync`). O motor de
sync que o painel dirige vive no app; os formatos de saída (`.prproj`) estão em
[`../../protocolos/prproj/`](../../protocolos/prproj/).

Painel servido, extensão invisível, proxy e OP-Atom no Premiere **23.2 (Windows), 2026-09-17**:
[painel-servido-e-identidade.md](painel-servido-e-identidade.md) — medido por
`_CICLO ASSIST/spikes/o_premiere_por_dentro.py` (extensão `spikes/premiere_sonda/`), num projeto
novo no diretório temporário; a extensão foi desinstalada ao fim e o Premiere fechou sozinho.

Escrita na bin (criar, mover, renomear, apagar) medida em PRODUÇÃO no Premiere **23.2
(Windows), 2026-09-17**: `_CICLO ASSIST` — ferramenta `organizar_o_projeto`, num projeto real
de quatro diárias (84 operações em dois lotes, 76 clipes, 8 bins apagadas, zero falhas). O que
o editor pediu, o modelo planejou e o portão mostrou antes de executar.

Nome do item importado (com a extensão) medido no Premiere **23.2 (Windows), 2026-09-22**:
`_CICLO ASSIST/spikes/vetores_no_premiere.py` — a aba Vetores listando e processando a mídia de
um projeto descartável (`importFiles` numa bin `CENAS`, 3 arquivos); extensão de teste
desinstalada ao fim e o Premiere fechado sozinho.

Eventos de `app.bind` (o de IMPORT, `onItemsAddedToProjectSuccess`) e o custo de percorrer o projeto medidos no Premiere **23.2 (Windows), 2026-09-22**: `_CICLO ASSIST/spikes/o_premiere_avisa_import.py` — 15 nomes candidatos, import por `importFiles` de 1 e de 60 arquivos num projeto descartável; extensão de teste removida ao fim.

Monitor Source (o QE posiciona; o TC do `scrubTo` é tempo desde o início do clipe) e a coluna Descrição (`Column.PropertyText.Description`) medidos no Premiere **23.2 (Windows), 2026-09-22**: `_CICLO ASSIST/spikes/o_source_e_a_descricao.py` e `spikes/o_source_no_tc.py` — reflexão de `app.sourceMonitor`/`qe.source.player`, posição lida de volta pelas duas APIs, clipes com TC 01:00:00:00 a 25 e 23,976, escrita lida de volta no item e no `.prproj` salvo.

`importSequences` que devolve true sem criar nada, monitor preto que para o `exportFramePNG`, QE com vãos no `getItemAt`, falta de API de adjustment layer — Premiere **23.2.0 (Windows), 2026-10-09**: `laboratorio-de-midia/lab/bancadas/premiere_montagens.py` (5 rodadas, `resultados/B13_MONTAGENS/`).

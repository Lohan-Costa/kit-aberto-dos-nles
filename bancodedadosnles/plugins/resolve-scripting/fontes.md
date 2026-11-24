# Fontes — API de scripting do Resolve

Rastreabilidade: de onde veio cada bloco desta pasta.

| descoberta | fonte | data | confiança |
|---|---|---|---|
| ⭐⭐ **`mediaType` (1=vídeo, 2=áudio) no `clipInfo` coloca vídeo e áudio INDEPENDENTEMENTE — e é o que evita trilhas de vídeo vazias** | `DRAMASYNC/plugins/resolve-script/orbita_sync.lua` (produção) | 2026-08-24 | confirmado — o Chop Chop **não** usa e paga com 21 trilhas vazias |
| ⭐⭐ **Lua × Python: o `.py` só aparece no menu se houver Python de sistema compatível** | README do `orbita_sync` + o instalador do Chop Chop, que roda `sudo installer` de um Python 3.13.2 para contornar | 2026-08-24 | confirmado (dois lados) |
| ⭐⭐ **`GetTrackTypeAndIndex()` nos itens devolvidos por `AppendToTimeline` revela onde o Resolve REALMENTE pôs cada coisa** | `orbita_sync.lua` (diagnóstico de ocupação de áudio) | 2026-08-24 | confirmado |
| ⭐ **`GetAudioMapping()` devolve JSON como TEXTO com `track_mapping`** — espelha a estrutura real de áudio da fonte | `orbita_sync.lua` | 2026-08-24 | confirmado |
| ⚠️ **Nome de timeline duplicado é recusado em SILÊNCIO** | `orbita_sync.lua` (comentário: "era um erro silencioso") | 2026-08-24 | confirmado |
| ⚠️ ⭐ **A taxa pedida pode não ser a que ficou — releia `GetSetting("timelineFrameRate")`** | `orbita_sync.lua` | 2026-08-24 | confirmado |
| ⚠️ **A taxa é STRING de vocabulário fixo** ("23.976", "29.97"…), aproximada pelo mais próximo | `orbita_sync.lua::resolve_framerate_string` | 2026-08-24 | confirmado |
| ⚠️ **Timeline vazia nasce com 1 trilha estéreo; ambos apagam a trilha 1 no fim** | `orbita_sync.lua` + Chop Chop | 2026-08-24 | confirmado (dois lados, independentes) |
| ⚠️ **`recordFrame` precisa de `GetStartFrame()`** (Órbita) ou do `Start TC` da timeline (Chop Chop) | ambos | 2026-08-24 | confirmado |
| ⚠️⚠️ **`endFrame`: Órbita usa `Frames − 1`, Chop Chop usa `duration`** — um dos dois erra um frame | ambos | 2026-08-24 | **pendente** |
| ⚠️⚠️ **Não há caminho de `MediaPoolItem` tipo Timeline para o objeto Timeline** — busca por NOME em `GetTimelineByIndex` | ambos | 2026-08-24 | confirmado (dois lados) |
| ⚠️⚠️ **Objetos remotos não são *hashable*** — `set()` de `MediaPoolItem` estoura; usar `id(obj)` | Chop Chop | 2026-08-24 | confirmado |
| ⭐⭐ **`Usage` diz quantas vezes o clipe está em timeline** — resolve duplicata sem rastrear estado | Chop Chop | 2026-08-24 | confirmado |
| ⭐ **`AutoSyncAudio` + as 4 constantes; por forma de onda NÃO sincroniza câmera com câmera** | Chop Chop + manual do produto p.16 | 2026-08-24 | confirmado (texto do fabricante) |
| ⚠️ **O caminho de scripts do Windows tem um `Support\` a mais que o do macOS** | README do `orbita_sync` | 2026-08-24 | confirmado |
| ⭐ **O menu de scripts relê a pasta a cada abertura** — script novo aparece sem reiniciar | README do `orbita_sync` | 2026-08-24 | confirmado |
| ⚠️ **O script roda no processo do Resolve e BLOQUEIA a UI**; e `io.popen` passa por shell | `orbita_sync.lua` | 2026-08-24 | confirmado |
| ⛔ **Drop-frame não coberto; TC inválido vira 0 e joga o clipe para o início** | Chop Chop | 2026-08-24 | confirmado |
| ⭐⭐ **`ImportTimelineFromFile` importa o nosso DRT pelo script (Lua, menu): timeline + mídia online (108/108 vídeo, 628 som), tudo na pasta do `SetCurrentFolder`; `timelineName` ignorado para DRT (nome vem do arquivo); mesmo nome de novo vira `<nome> 2`** — Resolve Studio 19.0.0b.59, Windows 11 | `_DeLaPraCa/.dev/spike_resolve_import.lua`, rodado pelo autor num projeto vazio | 2026-09-24 | confirmado |
| ⚠️⚠️ **CORREÇÃO: o objeto Timeline importado de DRT leva o nome do ARQUIVO; o item do pool, o de dentro** — `SetName` depois (false se repetido). E: `io.popen`/`os.execute` do script abrem janela `cmd.exe` no Windows; `ffi` + `CreateProcessW`/`CREATE_NO_WINDOW` resolve | `fuscript` contra o projeto aberto + relato do autor (captura de tela) | 2026-09-25 | confirmado |
| 2026-09-24 | `print` do Lua do Resolve junta argumentos sem TAB (TAB no fim); `fuscript.exe -l lua -x` roda Lua sem o Resolve aberto — Studio 19.0.0b, Windows | `_DeLaPraCa/tests/test_ataques_magic_link.py` (V9/V10) | 2026-09-24 | confirmado |

## 2026-08-24 (mais tarde) — a SEGUNDA superfície, achada no Jumper

| descoberta | fonte | confiança |
|---|---|---|
| ⭐⭐⭐ **O Resolve tem Workflow Integration Plugins** — apps **Electron** em `Support/Workflow Integration Plugins/`, além dos scripts | `Jumper.app/Contents/Resources/Jumper.zip` | confirmado |
| **`manifest.xml` de 5 campos** (`Id`/`Name`/`Version`/`Description`/`FilePath`) — o mais simples das 4 plataformas, sem permissão, domínio ou escopo | mesmo pacote | confirmado |
| ⭐⭐ **`WorkflowIntegration.node`** (addon N-API, 1,5 MB, da Blackmagic) expõe **`GetResolve()`** — o MESMO objeto `resolve` da API de scripting | símbolos exportados do `.node` | inferido |
| ⭐ **Transporte por pipe nomeado/FIFO** (`CreateFIFO`, `GetPipeName`, `OpenFile`, `CloseFile`, `GetAPITimeout`) — o plugin roda em OUTRO processo | mesma fonte | inferido |
| ⭐⭐ **Consequência:** API de scripting inteira **+ janela própria em HTML**, e **não bloqueia a UI** (o script bloqueia) | comparação com a via de scripts | inferido |
| ⭐⭐ **`RegisterCallback`/`GetCallbackFunction`** — pode haver EVENTO de verdade no Resolve | símbolos do `.node` | ⛔ **hipotese** — nome de símbolo, não medido |
| ⭐⭐⭐ **Jumper: 4 NLEs, 4 mecanismos, 1 frontend** — `.avpi` (12 KB) · `.zxp` (5,1 MB) · Workflow Integration (6,4 MB) · **`.appex` do Final Cut** — com o MESMO `index.html` de 3,4 MB | `Jumper.app/Contents/{Resources,PlugIns}` | confirmado |
| ⭐ **Primeiro registro de Final Cut Pro no banco:** `NSExtensionPointIdentifier: com.apple.FinalCut.WorkflowExtension` + `ProExtensionPrincipalViewControllerClass` | `Workflow Extension.appex/Contents/Info.plist` | confirmado |
| ⚠️ **O custo está no tamanho da CASCA:** 12 KB no Avid (página servida por HTTP pelo app) × 5–6 MB nos outros — *o `.avpi` mínimo é o mais barato de ATUALIZAR* | comparação das quatro | inferido |

⭐ **Nota de método:** o Jumper tem 14,5 GB e o instalador Windows são 5 CABs com nomes em **hash**.
A rota barata foi **ler as strings do MSI (5 MB)** para saber QUE integrações existem, e só então
tirar do `.dmg` **as quatro peças (~12 MB)**, que ali têm nome real. *Listar antes de extrair.*

⛔ **Não lido:** `resolve-launcher.js`/`resolve-preload.js`, o frontend de 3,4 MB, e **todo o lado de
ML do Jumper** (scene detection, agrupamento facial, transcrição) — este último `pendente` **por
relevância, não por régua**: o domínio dele é busca de mídia, não manipulação de timeline.

Detalhe em [workflow-integration.md](workflow-integration.md).

## Implementações de referência

- **Órbita** (`DRAMASYNC/plugins/resolve-script/orbita_sync.lua`, 1.856 linhas) — script **fino**
  dirigindo um serviço local. Em produção. É a fonte de tudo que envolve `mediaType`,
  `GetAudioMapping`, verificação por `GetTrackTypeAndIndex` e as armadilhas de criação de timeline.
- **Chop Chop Sync and Bin, edição Resolve v1.0** — motor **inteiro dentro do script** (2.355 linhas
  de Python). Lido por completo sob a régua nova; ver
  [`../premiere-cep/chopchop-algoritmo.md`](../premiere-cep/chopchop-algoritmo.md).

## Método e limites

Esta pasta **não** nasceu de análise nova: é consolidação de conhecimento que já existia em dois
lugares errados. Nada aqui foi medido especificamente para escrevê-la, então as marcas de confiança
refletem a origem — `confirmado` quando vem de código em produção ou de dois produtos independentes,
`pendente` quando os dois discordam.

⛔ **Áreas nunca tocadas:** mover clipe já colocado, efeitos, parâmetros, marcadores, render, color.
| 2026-09-26 | Relink aos originais no Resolve feito na GERAÇÃO do DRT (sem a API de relink): PRODA_CORTE real, 841 de 877 clipes nos originais (antes: 737 na gerenciada, 140 offline); 17 sem par = efeitos de biblioteca fora da rodagem — ver README §"Relink aos originais" | `_DeLaPraCa` ADR 0020, `tests/test_relink_carta.py`, medição com a Carta real do canal Cor contra `D:\MIDIAS DE TESTES\PRODUCAO-A\MIDIAS` | confirmado (sem Resolve) · no Resolve pendente |
| 2026-09-26 | Mídia primeiro, timeline depois: com os arquivos já no Media Pool, o `ImportTimelineFromFile` de DRT liga a timeline aos itens do Resolve (vídeo sem duplicar), mesmo com o formato errado no DRT — ver README §"Mídia primeiro, timeline depois" | teste G (DRT quebrado de propósito) e F, importados pelo autor no Resolve Studio 19.0.0b com a pasta dos originais arrastada antes para o pool | confirmado (import manual) · `ImportMedia` pela ponte JS: pendente |
| 2026-09-26 | Áudio pré-importado: o Resolve liga CLIPE A CLIPE ao item dele (som direto ≥3 canais) ou ao do DRT (mono/estéreo), com o item do DRT idêntico ao dele; `ChannelsBA` = (trilha << 14) \| canal; `AudioType` 1 mono / 0 estéreo — ver README §"Áudio: o reaproveitamento NÃO depende só do item" | `Project.db` (SQLite) de três projetos de teste do autor, lido por cópia; pool lido pelo `fuscript`; DRT de referência do Resolve 19 | confirmado (o que liga a quê) · critério: hipótese |
| `SetName` repetido pela ponte JS abre diálogo modal (pelo `fuscript` não) — escolher o nome livre antes | print do autor no painel do De Lá Pra Cá (importar a mesma timeline duas vezes) | 2026-09-27 | confirmado |
| `DuplicateTimeline` + `DeleteClips` + `AppendToTimeline(recordFrame)` editam só a cópia e mantêm a correção; `Timeline:Export` por script externo exporta a timeline errada; `ExportLUT` devolve false | `fuscript` externo contra o projeto aberto (Studio 19 public beta, Win11) | 2026-09-27 | confirmado |
- 2026-10-03 — composição do Fusion montada pela API (`AddTool` + `LoadSettings` + `ConnectInput`), sem `.comp`; Resolve Studio 21.1 (macOS). De Lá Pra Cá, `motor/drp/fusion_mascara.py`.
- 2026-10-03 — Pitch/Yaw do Inspector medidos por homografia (perspectiva pura; centro muda com composição do Fusion); CornerPositioner pela API. Resolve Studio 21.1 (macOS).
- 2026-10-03 — Fusion pela ponte JS do Workflow Integration (Resolve 21.1 Mac): AddTool sim, LoadSettings/SetInput/ConnectInput não; Export→texto→ImportFusionComp funciona (workflow-integration.md §6).
- 2026-10-03 — Resolve 19.0.0b.59 (Windows 11, API Python): ImportFusionComp com composição no clipe = verdadeiro e nada muda; sem composição = cria e religa o MediaIn; Delete da única = False; 8.3 aceito (workflow-integration.md §6).
- 2026-10-03 — Resolve 19.0.0b.59 (Windows, API Python): Export grava a timeline aberta na tela (não a do objeto, e devolve True); sem GetTrackSubType; AddTrack e a A1 estéreo da timeline vazia; FCP7 XML recusado pelo ImportTimelineFromFile (api-scripting.md).
- **Laboratório de Mídia, 2026-10-06** — caso B01 no Studio 21.1.0.14 (macOS 15.6.1) pelo MCP do Resolve: leitura do pool dos 6 perfis, quadro exato em stills e renders, XDCAM 8 mono misturado no render e o conserto por `SetAudioMapping`, OP-Atom do ffmpeg não agrupado. Ver `api-scripting.md` §"Laboratório de Mídia, caso B01".
- **Laboratório de Mídia, 2026-10-06** — caso B02 (8 taxas, 29,97 DF atravessando o minuto) no Studio 21.1.0.14 (macOS): projeto por taxa, DF no pool, `SetCurrentTimecode` com rótulo DF, render com o TC DF. Ver `api-scripting.md` §"Caso B02".
- **Laboratório de Mídia, 2026-10-06** — casos B03–B06 no Studio 21.1.0.14 (macOS), pelo MCP e pela API externa: layouts de áudio, meia-noite, rasters/PAR, `AutoSyncAudio` por TC, a queda com `AddTrack`. Ver `api-scripting.md` §"Casos B03–B06".
- 2026-10-23 — Resolve Studio 19.1.4.11 (Win11): o servidor de scripts é o filho `fuscript.exe -s` na porta 1144; sem ele o `scriptapp` leva ~4,1 s segurando o GIL (De Lá Pra Cá: serviço congelado). Ver `api-scripting.md` §"O servidor de scripts". Medidas em `_DeLaPraCa/.dev/medidas_script_resolve.txt`.

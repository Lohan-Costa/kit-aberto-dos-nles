# Fontes — plugins/avid-panel-sdk

Rastreabilidade das descobertas.

Origem única desta rodada: **instalação local do Avid Media Composer 25.12.0.58863**
(macOS 24.6.0), engenharia reversa em 2026-08-07. Sem acesso ao SDK oficial — a Avid mantém
o Panel SDK sob onboarding fechado.

> ⚠️ **SEGUNDA INSTALAÇÃO, 2026-08-15 — MC 25.6.0.58781 em Windows 11.** Ver
> **[windows.md](windows.md)** e [dados/windows.json](dados/windows.json). Ela **separou o que é
> plataforma do que é VERSÃO** — distinção que uma instalação só não permite fazer, e que
> **corrigiu um fato desta tabela** (o menu `Extensions`, marcado abaixo). Tudo o que está nesta
> página sem ressalva foi medido no **25.12/macOS** e pode não valer noutra versão.

| bloco | origem | data | confiança |
|---|---|---|---|
| Caminhos `PanelSDKPlugins/`, `PanelSDK.json`, `APIGateway/config.json` e seus conteúdos | leitura direta de `/Library/Application Support/Avid/` | 2026-08-07 | confirmado |
| `.avpi` é ZIP com `avid-manifest.json` na raiz | `file(1)` + `unzip` sobre `avid-huddle.avpi` | 2026-08-07 | confirmado |
| **Schema do manifesto** (todos os campos) | `avid-huddle.avpi` — painel real distribuído pela Avid, descompactado | 2026-08-07 | inferido (lido de amostra real; **sem round-trip**) |
| Flags do gateway (`--plugin_path`, `--server_bind_address`, …) | `avid-api-gateway --help` (o binário imprime) | 2026-08-07 | confirmado |
| Stack do gateway (Go, gRPC-Web, nhooyr websocket) | `strings` — caminhos `/Users/releng/go/pkg/mod/...` | 2026-08-07 | confirmado |
| Serviço `aag.PluginRepo` e seus 6 métodos | `strings` sobre `avid-api-gateway` | 2026-08-07 | inferido |
| `AuthManager` / `IsDevMode` / token por plugin | `strings` — símbolos Go | 2026-08-07 | inferido |
| **Ids das APIs do host** (`general`, `SRT`, `command`, `timelineEditing`, `transportcontrols`) | `strings -a` sobre `AvidMediaComposer` (236 MB) | 2026-08-07 | inferido |
| Feature flag `/Media Composer/3PDevPanelSDK` + descrição | `strings` — tabela de feature flags do MC | 2026-08-07 | inferido |
| Comandos `panelsdk reinit` / `console on|off` | `strings` — bloco "Panel SDK Console commands" | 2026-08-07 | inferido |
| `qwebchannel.js` como bridge JS↔C++ | `find` no bundle do app | 2026-08-07 | confirmado (arquivo existe) |
| Acesso oficial fechado / sem download público | busca web: avid.com/media-composer/extensions, developer.avid.com, github.com/avid-technology | 2026-08-07 | confirmado |
| **ROUND-TRIP: painel próprio (`usuario-testpanel.avpi`) carrega no MC** | instalação + `panelsdk reinit` + abrir em Extensions → Test Panel (v0.1.0) | 2026-08-07 | confirmado (print do usuário) |
| Instalação NÃO precisou sudo (dir 777) | `cp` direto funcionou | 2026-08-07 | confirmado |
| Gateway é daemon persistente (sobrevive ao MC fechado) | `ps`/`lsof`: de pé 2 dias, MC fechado | 2026-08-07 | confirmado |
| Gateway exige token (grpc-status 16 "unknown token") | `curl` gRPC-Web sem token → `GetPluginList` | 2026-08-07 | confirmado |
| `url` relativa serve HTML local via esquema `avpi://` | `window.location` = `avpi://static/index.html` no painel | 2026-08-07 | confirmado |
| Runtime QtWebEngine 6.5.6 / Chromium 112 | user agent lido no painel | 2026-08-07 | confirmado |
| Painel 3P aparece sob menu top-level **Extensions** (não `menuName`) | print do usuário (menu novo apareceu) | 2026-08-07 | ⚠️ **confirmado SÓ PARA O 25.12** — no 25.6 (Windows) **não existe menu Extensions** e o painel vai para `Tools`, honrando o `menuName`. É diferença de VERSÃO, não de SO ([windows.md §2](windows.md)) |
| Fetch do painel a portas do gateway é bloqueado (origem avpi://→http) | painel sondou 9100-9110/4920/4930 → todas "sem resposta"; curl externo pega 4930 | 2026-08-07 | confirmado |
| **`mcapi` é message bus: `notify`/`onEvent`/`reportError`/`gatewayConnectionError`** | introspecção ao vivo do `channel.objects.mcapi` (painel v0.2.0) | 2026-08-07 | confirmado (superfície) |
| **Vocabulário completo de eventos** (tabela do Panel SDK: ProjectOpened/Closed, BinOpened/Closed, MobAdded/Deleted, Import/Export*, DoCommandFinished, DropFromPlugin*) | `strings` do binário (bloco contíguo) | 2026-08-07 | confirmado (nomes) |
| **`pos`=frames, `mobId`=UMID** | log de eventos + `946`=00:00:39:10@24fps | 2026-08-07 | confirmado |
| **Serviço gRPC `mcapi.MCAPI` (61 rpcs)** | símbolo C++ mangled + paths `/mcapi.MCAPI/*` | 2026-08-07 | confirmado (nomes) |
| **`.proto` COMPLETO** (61 rpcs, ~298 messages, headers, bodies, enums, api_scope) | **gRPC server reflection** de `[::1]:9100` (grpcurl + Go/protoreflect) | 2026-08-07 | confirmado → `dados/mcapi.proto` |
| Edição/marcação = `DoCommand(commandId)`; In/Out não emite evento | describe do proto + log | 2026-08-07 | confirmado |
| Chamar métodos de dentro do painel (grpc-web+token) | — | — | **pendente** (contrato pronto, falta round-trip de chamada) |
| Como ligar a flag `3PDevPanelSDK` | — | — | **pendente** (não foi preciso: painel 3P carregou sem tocar na flag) |

## Kit de desenvolvimento

Projeto de iteração em `~/avid-panel-dev/` (fora do banco — o banco é conhecimento, o kit é
ferramenta). Contém `src/` (manifesto + painel), `pack.sh` (empacota+instala, auto-bump de
versão, injeta em `version.js` e no manifesto), `reload.sh` (mata o gateway órfão). Fluxo:
editar → `./pack.sh` → fechar MC → `./reload.sh` → reabrir MC. O painel mostra a versão num
badge para confirmar qual build carregou. Round-trip do kit validado 2026-08-07 (pack 0.4.0→0.4.1).

## Artefato produzido

Painel-teste empacotado seguindo o formato extraído (manifesto + `static/index.html` que sonda
QWebChannel e as portas do gateway). **Ainda não instalado** — a instalação exige `sudo`
(pasta de sistema) e reinício do Media Composer.

Quando for instalado e observado, promover: schema do manifesto `inferido` → `confirmado`,
e resolver a hipótese da `url` relativa.

## Comparar com

[`../premiere-cep/`](../premiere-cep/) — mesma camada (painel dentro do NLE), arquitetura de
painel fino equivalente, mas com SDK público e sem autenticação. A tabela comparativa está em
[arquitetura.md](arquitetura.md#comparacao-com-o-cep-do-premiere).

## 2026-08-08 — DRAMASYNC/Órbita: a API `mcapi` em produção

Bloco de descobertas medido durante a construção da integração Órbita ⇄ Media Composer (o app
dirige o MC pelo backend `[::1]:9100`, sem painel). Máquina: macOS 24.6.0, **Media Composer
Ultimate 25.12.0.58863**, projeto real `MULTCAM IMPORT PARA PLUGIN` com mídia importada DENTRO do
Avid (MXF OP-Atom) — 13 câmeras + 1 som.

| descoberta | como foi medida |
|---|---|
| Piso de ~500 ms por chamada | 5 repetições de 7 métodos diferentes, cronometradas |
| Ausência de canal de evento | `grpcurl list mcapi.MCAPI` — 61 métodos, nenhum Subscribe/Watch |
| MobID em duas representações | mesmo clipe lido pela API e pelo pyavb, comparados byte a byte |
| `bin_relative_path` | 4 formas de caminho testadas contra a mesma bin em subpasta |
| `OpenBin` dispensável / não relê o disco | conexão nova sem `OpenBin`; e MobID da composição em disco × o que a API reportava |
| `GetValues` é eco | 7 chaves diferentes, incluindo string vazia — sempre `['0','1','2','3']` |
| `Source Path` / `Source File` / `Drive` / `Frame Count Duration` | `GetMobInfo` de um master, colunas listadas |
| Seleção atravessa bins | seleção posta por `SelectMobsInBin` em 2 bins e lida de volta |
| Diálogo modal trava a API | `PMM_INSUFFICIENT_MEDIA` aberto na tela; `GetAppInfo` respondeu, `GetListOfBinItems` estourou |
| `grpcio` sobrevive ao PyInstaller | sonda `--onefile` de 22,6 MB executada |

Consumidor: `DRAMASYNC/src-python/avid/` (`mcapi.py`, `writer.py`, `adapter.py`, `masters.py`).

## Sonda de rede do painel (2026-08-08)

| fato | como foi obtido | data | confiança |
|---|---|---|---|
| `Origin: avpi://` literal em todo request do painel | painel de teste (`usuario-testpanel` v0.4.4) com 7 sondas contra 2 servidores HTTP locais que só diferiam no `Access-Control-Allow-Headers`; headers gravados crus do lado do servidor | 2026-08-08 | confirmado |
| Painel alcança `127.0.0.1` e `localhost` por HTTP (200, corpo legível) | as mesmas sondas | 2026-08-08 | confirmado |
| Header custom é bloqueado no preflight se faltar no ACAH | sonda p4 (ACAH só com `Content-Type`) contra p5 (ACAH com o header) | 2026-08-08 | confirmado |
| Token na query string dispensa preflight | sonda p6 | 2026-08-08 | confirmado |
| `PanelSDKPlugins` é `drwxrwxrwx` (cópia sem `sudo`) | `ls -ld` na instalação real | 2026-08-08 | confirmado |
| Gateway órfão derruba o registro — reencontrado e curado ao vivo | menu Extensions sumiu; `ps` mostrou `avid-api-gateway` com `PPID 1` segurando 4920/4930; matar + reabrir o MC trouxe o menu de volta | 2026-08-08 | confirmado |

## Fonte EXTERNA sobre o painel que não abre (2026-08-08)

| fato | como foi obtido | data | confiança |
|---|---|---|---|
| "Panel won't open" é problema CONHECIDO e atinge painel comercial | [docs.getjumper.io — Avid troubleshooting](https://docs.getjumper.io/NLE/avid/avid-troubleshooting#panel-wont-open) | 2026-08-08 | confirmado (documentação pública de terceiro) |
| Workaround oficial deles: `panelsdk reinit` no Console, **repetindo até** `"PanelSDK: Gateway service is ready."` | idem | 2026-08-08 | confirmado |
| Nem eles nem a Avid têm causa raiz ("we're not sure why, and are actively discussing with the Avid team"; sugerem reiniciar o computador) | idem | 2026-08-08 | confirmado |
| ⚠️ **`panelsdk reinit` FUNCIONA** nesta build — libera o gateway e traz o painel **sem reiniciar o MC** | teste do usuário na GUI | 2026-08-08 | confirmado — **supera** o veredicto anterior de "quebrado", que vinha de UMA tentativa falha |


---

## 2026-08-08 — Painéis de dois parceiros oficiais da Avid

**O quê:** análise dos instaladores do **Jumper** (Witchcraft Software AB) e do **Quickture**,
ambos parceiros oficiais listados em avid.com/media-composer/extensions — ou seja, receberam o
Panel SDK pela via oficial que aqui está fechada.

**Como:** DMG montado somente-leitura (`hdiutil attach -readonly`), PKG extraído com
`xar -xf` + `gunzip | cpio -i`, `.avpi` aberto com `unzip`, bundles JS lidos com `strings` e
pela lista de `sources` do source map, binário Rust lido pelos caminhos `cargo/registry`.
**Nada foi instalado, nenhum binário executado, nenhum painel carregado no MC.**

**Régua aplicada:** ler manifesto, configuração, licenças, nomes de símbolo e endpoints — sim;
descompilar lógica de produto — não. O source map do Quickture continha o TypeScript original
completo; foi lida apenas a lista de caminhos de arquivo.

**O que rendeu** → [paineis-de-terceiros.md](paineis-de-terceiros.md):

- ⭐ **Validação do `mcapi.proto`**: o `AvidFrontend` do Jumper embute o protobuf oficial
  compilado para JS. Diff contra a nossa reconstrução por reflection: **1 símbolo faltando**
  (`apiScope`). A reflection tinha capturado essencialmente tudo.
- ⭐ **`usesApi`**: `command`, `timelineEditing` e `transportcontrols` promovidos de `inferido`
  para **`confirmado`** — declarados no manifesto do Jumper 1.0.1.
- ⭐ **`url` do `uiItem` aceita HTTP absoluto para localhost** (`http://127.0.0.1:6699/...`),
  não só caminho relativo `avpi://`. Torna painel e app **same-origin** — sem CORS, sem
  preflight, sem segredo de pareamento. Corrige a leitura anterior de que o `url` era relativo.
- **Descoberta do app local**: dois padrões documentados (porta fixa vs. varredura 3030–3039 com
  validação por magic string).
- **`subscribesToChannels: []` nos dois** — confirmação externa da medição de ~500 ms/chamada e
  ausência de canal de evento.
- **Eventos novos a medir** (`inferido`): `ImportFileStarted`, `ImportFileFinished`,
  `DoCommandFinished`.

**Origem do material:** instaladores baixados pelo usuário (`/Volumes/SSD/jumper/` e
`/Volumes/SSD/quicture/`). A dissecação completa dos dois produtos — arquitetura de
produto, modelos de ML, camada de agente — está em
`PROGRAMAS COM CLAUDE/EDT-ASSIST/pesquisa/`; aqui ficou só o que é API de NLE.

---

## 2026-08-10 — construção do plugin **De Lá Pra Cá** (`confirmado`)

**App:** `PROGRAMAS COM CLAUDE/_DeLaPraCa` — plugin de relink do Media Composer, projeto novo
compondo o motor do RELINKER com o shell do Órbita.
**NLE:** Avid Media Composer 25.12.0.58863 (macOS).
**Amostras:** `MIDIAS DE TESTES/PRODUCAO-A` — AAF de montagem `PRODA_RELINKER_ALTA.aaf`
(1172 segmentos, 119 masters, 98 `TapeDescriptor`) e 378 arquivos de mídia.

| bloco | onde ficou | confiança |
|---|---|---|
| `ImportFile` aceita AAF; automatch por MobID; loop de relink em escala | `dados/mcapi-grpc.json` → `ImportFile_aceita_AAF` | confirmado |
| `CreateBin.folder_path` é relativo ao projeto | `dados/mcapi-grpc.json` → `CreateBin_folder_path` | confirmado |
| Bins abertas vêm sem `.avb`; `bin_relative_path` exige com | `dados/mcapi-grpc.json` → `bins_abertas_precisa_de_avb` | confirmado |
| Listar sequences varrendo o projeto abre todas as bins na tela | `dados/mcapi-grpc.json` → `NAO_varra_o_projeto_para_listar_sequences` | confirmado |
| Onde moram os presets de export; `_EXPORTFORMAT`; `ExportFile` assíncrono | `dados/export-presets.json` | confirmado |
| Correção do limite de auto-link do AAF | `protocolos/aaf/escrita.md` §2 | confirmado |

**O que foi validado na GUI por um editor:** timeline relinkada online, com **timewarp e
estabilizadores preservados** — a prova de que quem monta a timeline é o próprio MC.

**Régua:** nada de descompilar. O que se leu foi arquivo de configuração do próprio usuário
(`Settings.xml`), resposta da API e arquivo de projeto — tudo em máquina própria, com o produto
licenciado e em uso normal.

⚠️ **Não exercitado:** o caminho de *group clip* do achatamento. O material de teste não tem
multicam (`AppCode` nulo nas 45 composições). O código veio do RELINKER, que o validou lá.

---

## Rodada 2026-08-15 — WINDOWS (MC 25.6.0.58781, Windows 11 23H2)

Segunda instalação de referência. Origem: validação da integração do Órbita no Windows, com o
painel carregado no editor e chamadas gRPC reais contra `[::1]:9100`. Narrativa em
**[windows.md](windows.md)**; fatos em [dados/windows.json](dados/windows.json).
Controle do experimento: `avid-huddle.avpi` (painel da **própria Avid**) presente na mesma pasta.

| bloco | origem | data | confiança |
|---|---|---|---|
| Caminho `%PROGRAMDATA%\Avid\PanelSDKPlugins` + `APIGateway/config.json` (4920/4930) + `PanelSDK.json` (9100-9110) | leitura direta do disco; painel próprio instalado e **carregado no editor** | 2026-08-15 | confirmado |
| **Menu é `Tools` no 25.6 (não existe `Extensions`)** — diferença de VERSÃO, não de SO | print do usuário + manifesto do `avid-huddle.avpi` (Avid) declarando o mesmo `menuName: Tools` | 2026-08-15 | confirmado (**corrige a linha do 25.12 acima**) |
| **`GetListOfWindows` ausente no 25.6** (responde `UNIMPLEMENTED`) | chamada gRPC real + enumeração dos símbolos `GetListOf*` em `AvidMediaComposer.exe` | 2026-08-15 | confirmado |
| Gateway é **filho** do MC; 4920/4930 escutam **só em `::1`**; 9100 escuta em `::1` **e** `127.0.0.1` | `Get-CimInstance Win32_Process` + `Get-NetTCPConnection` com o MC aberto | 2026-08-15 | confirmado |
| **Assinatura do gateway órfão difere por SO**: macOS `ppid==1` (launchd adota); Windows **não reparenta** → órfão é `ppid` fora dos PIDs vivos | comparação das duas plataformas + comportamento do Windows | 2026-08-15 | confirmado (Windows: `inferido` quanto à reciclagem de PID) |
| ~~**Drop é mão única**: não há MC → painel~~ ⚠️ **ERRADO** — só a parte de SAÍDA se sustenta (`DropFromPluginTo{Bin,Composer,Timeline}` existem) | `strings -a` sobre `AvidMediaComposer.exe` (varredura `Drop*`/`Drag*`) | 2026-08-15 | **REVOGADO no mesmo dia** — ver a linha abaixo |
| ⭐ **O drag MC → painel EXISTE**, por MIME customizado no `ondrop` do DOM. **Nada declarado no manifesto** | leitura do bundle do painel **ESION Studio 25.1.0** ([esion-arquitetura.md](esion-arquitetura.md)) → depois **implementado e exercitado por um editor** no De Lá Pra Cá | 2026-08-15 | **confirmado ponta a ponta** — detalhe todo em [arrastar.md](arrastar.md) |
| ⭐ **Lição de método:** ausência de símbolo prova ausência de **rpc**, não de **capacidade** — metade da superfície de um painel é a do navegador, e essa metade não aparece em `strings` | a própria revogação acima | 2026-08-15 | confirmado |
| Eventos presentes no 25.6, incl. **`BinRowSelectionChanged`** | `strings -a` sobre o binário | 2026-08-15 | confirmado (nomes) |

### O bloco do ARRASTO — rastreabilidade própria

> Estes fatos **saíram deste arquivo para [arrastar.md](arrastar.md)** (e de `windows.json`
> para [`dados/arrastar.json`](dados/arrastar.json)): o arrasto não é específico do Windows
> nem de uma versão. Ficam aqui as linhas de origem, porque foi nesta sessão que se mediu.

| bloco | origem | data | confiança |
|---|---|---|---|
| **`effectAllowed = "move"`**, e forçar `dropEffect: "copy"` CANCELA o drop | implementação real dentro do MC + instrumento na tela do painel | 2026-08-15 | confirmado |
| **O MIME sobrevive à navegação para `http://`** (painel servido pelo próprio serviço) | arrasto real num painel em `http://127.0.0.1:7823` | 2026-08-15 | confirmado — ⚠️ **não** vale para a ponte de eventos do QWebChannel, que é outro mecanismo |
| **Payload medido**: `id`, `type`, `head`, `systemID`, `systemType`; `systemID`/`systemType` = **sistema de origem**, não a bin | payload capturado pelo painel e depositado em `/diag/arrasto` | 2026-08-15 | confirmado |
| ⚠️ **`in`/`out` são CONDICIONAIS — só no subclip** | arrasto misto de 6 espécies | 2026-08-15 | confirmado — **corrige DUAS leituras erradas**: "vêm sempre" (lida do código do ESION) e "nunca vêm" (uma amostra só) |
| ⭐ **As 6 espécies e como distinguir cada uma** (`sequence`/`masterclip`/`subclip`/`group`/`""`=efeito), e **`Source File`+`Source Path` separando AMA de gerenciado** | um único arrasto misto + `GetMobInfo` de cada item | 2026-08-15 | confirmado — ⚠️ ressalva: não se testou um clipe importado por *File ▸ Import* |
| **Catálogo completo dos 7 MIMEs de arrasto** | `strings -a` sobre `AvidMediaComposer.exe` | 2026-08-15 | confirmado (é o que o binário contém) |
| ⛔ **Arrastar uma BIN não entrega nada** (`tipos: []` no enter E no drop, com `effectAllowed: "move"`) | três medições convergentes no painel | 2026-08-15 | confirmado (negativo) |
| ⛔ **O `.aaf` anexo tem 0 bytes e nunca existe no disco** | `File.size` na webview + vigia nativa, 40 amostras em 10 s | 2026-08-15 | confirmado (negativo) |
| **`asset-list-extended` = variante Interplay/PAM**, não metadado mais rico | `systemType` do payload dos dois MIMEs | 2026-08-15 | confirmado |
| **`head`** — parece o frame inicial (`"0"`, e `"12014"` no subclip) | payload | 2026-08-15 | **pendente** — não confirmado como contrato |
| Clipe importado por *File ▸ Import* tem `Source Path`? | — | — | **pendente** — decide se a coluna separa "AMA × gerenciado" ou só "tem origem × não tem" |
| **Coluna `Drive` da bin = RÓTULO do volume, não letra** (`SSD` → `D:\`) | `GetMobInfo` real + `GetVolumeInformationW` | 2026-08-15 | confirmado |
| Mídia gerenciada: `D:\Avid MediaFiles\MXF\010020260629`, 394 `.mxf` → **103 UMIDs × 3 arquivos**, varredura 24,1 s | varredura real com `ffprobe` (exFAT/USB) | 2026-08-15 | confirmado |
| Ponte de eventos (`mcapi` do QWebChannel) **sobrevive a navegar para `http://`?** | — | — | **pendente** — decide se `BinRowSelectionChanged` serve a painel servido pelo app (ADR 0017) |
| `DropFromPluginToBin` na prática (entregar a sequência direto na bin) | — | — | **pendente** — contrato existe, nunca exercitado |

## Sessão de 2026-08-16 — entrega da bin, seletor de pasta e arrasto do Explorer

> Medidas no `_DeLaPraCa` (MC 25.6.0.58781 / Windows 11 23H2), com um editor conduzindo os
> gestos na GUI. As duas primeiras **corrigem** afirmações que já circulavam como certas.

| bloco | origem | data | confiança |
|---|---|---|---|
| ✅ **CORRIGE**: o seletor de pasta MODERNO (`IFileOpenDialog` + `FOS_PICKFOLDERS`) **é** alcançável de Python puro, por `ctypes` — a limitação era do **PowerShell**, não da interface COM | implementação real + `SetOptions`/`GetOptions` (`0x1808` → `0x1a68`), depois diálogo aberto na tela pelo editor | 2026-08-16 | confirmado — ⭐ o ganho decisivo foi de MÉTODO: dá para medir **sem abrir a janela**, o que tira o humano do laço |
| ⭐ **Arrastar do EXPLORER para o painel entrega o CAMINHO ABSOLUTO** (`text/uri-list`) | arrasto real de uma pasta sobre o painel, capturado em `/diag/arrasto` | 2026-08-16 | confirmado — ✅ **CORRIGE** a leitura comum de que "o navegador esconde o caminho de um arquivo solto": vale para página web, não para esta webview |
| ⚠️⚠️ **Numa seleção de VÁRIOS itens o `text/uri-list` vem TRUNCADO na primeira URI**; o `text/plain` traz todos | arrasto de duas pastas (`SFX` + `TRILHAS`) | 2026-08-16 | confirmado — o tipo canônico é o incompleto; `files.length` conta certo e serve de conferência |
| ⛔ **`dataTransfer.items` NÃO distingue pasta de arquivo antes do drop** — `[string, string, file ""]` idêntico nos dois; o que separa (`File.size` 0 × 10 MB) só existe depois | pasta e `.aaf` arrastados, `items` capturado no `dragenter` e no `drop` | 2026-08-16 | confirmado (negativo) — ⭐ saída de interface: **pergunte ao cursor** (realce fraco no mapa, forte sob o ponteiro) |
| ⚠️⚠️ **Prazo de CONSULTA (20 s) aplicado a OPERAÇÃO DE ARQUIVO** (`CloseBin`) → `DEADLINE_EXCEEDED` → o chamador decidiu "não fecha" e gravou com outro nome: **duas bins, nenhum erro** | relink real numa bin com 44 masters AMA | 2026-08-16 | confirmado — ⭐ *teto curto não devolve erro honesto; devolve decisão errada tomada com confiança* |
| ⚠️⚠️ **O `topen` do pyavb é PREGUIÇOSO**: reescrever o arquivo durante a sessão (pelo `CloseBin` **ou** pelo próprio `write()` no mesmo caminho) corrompe a bin e derruba o MC ao abri-la | `unpack requires a buffer of 8 bytes` + MC fechando sozinho, num relink real | 2026-08-16 | confirmado — correção: fechar ANTES da sessão, gravar ao lado, `os.replace` depois de fechar o handle |
| ⛔ **Não há como travar a interface do MC enquanto o app trabalha** (e o inverso é verdade: um modal dele trava a API inteira) | consequência do fato já registrado, exercitada no fluxo real | 2026-08-16 | inferido do confirmado — defesas possíveis: avisar com o nome da bin, e re-fechar antes de trocar o arquivo |

---

## 2026-08-21/22 — controle do MC a partir de um painel (Promo Entrega, Win11, MC 2025.6.58781)

Origem: o plugin **Promo Entrega**, aba Bendito Field, falando com o backend em `[::1]:9100`
e com o Windows por `ctypes`. Tudo medido com o Media Composer aberto no projeto do editor.

| bloco | origem | confiança |
|---|---|---|
| ⭐⭐ **`DoCommand` só age na JANELA ATIVA do MC** — foco no painel: 5 comandos e a agulha parada; foco no MC: chega ao frame | alternando o foreground por Win32 e lendo `GetViewerMobs` | confirmado |
| ⚠️⚠️ `IsCommandsEnabled` e `DoCommand` respondem **sucesso nas duas** situações: a API não denuncia o foco | mesma sessão | confirmado |
| ⚠️ Comandos emitidos sem foco ficam **pendurados** e disparam quando ele volta | agulha 10 frames adiante na rodada seguinte | confirmado |
| **`SetPosition` NÃO existe nesta build** — e **não é escopo**: `StopPlay`, do mesmo `transportcontrols`, responde OK | chamada direta | confirmado |
| **725 comandos da build**, categoria `Move` completa (20), **sem "go to timecode"** | `GetListOfCommands` | confirmado |
| Sonda de rpc que ESCREVE, sem escrever: `mob_id` vazio → `UNIMPLEMENTED` (não existe) × `Mob not found` (existe) | `AddMarkers`/`AddMarker`/`DeleteMarkers` | confirmado |
| Navegação por `DoCommand` em **laço fechado**: 3–4 comandos, ~2 s, frame exato | timeline de 158 frames | confirmado |
| ⚠️ `DoCommand` é **assíncrono e serializado** (*"Can't start more than one command on time"*, ErrorType 73; a resposta volta antes do efeito) | mesma sessão | confirmado |
| ⭐⭐ **Ir ao TC em UM SALTO por teclado simulado** (`Ctrl+0` → `Ctrl`,`Ctrl` → 8 dígitos → `Enter`): ~1,5 s, frame exato, 4/4 | `SendInput` do motor, painel em foco | confirmado — **validado em uso pelo editor** |
| ⚠️⚠️ Os dígitos têm de ser do **teclado numérico**; com a fileira de cima o Avid os trata como **atalho** (agulha f107→f106→f104) | os dois modos lado a lado | confirmado |
| ⚠️⚠️ `SendInput` via ctypes exige declarar **`MOUSEINPUT` mesmo sem usar** (união de 32 B no x64), senão devolve **0 sem tecla nenhuma** | mesma sessão | confirmado |
| ⚠️ Janela principal e painel `.avpi`: **mesmo pid e mesma classe** (`Qt656QWindowIcon`); só o **título** separa, e `EnumWindows` devolve o **painel primeiro** | `EnumWindows` + `QueryFullProcessImageName` | confirmado |
| ⚠️ `SetForegroundWindow` seco não basta a partir de processo em 2º plano — **e devolve sucesso**; precisa de `AttachThreadInput` | mesma sessão | confirmado |
| **`GetBinInfo` não tem flag de "modificado"**; bin suja se descobre comparando `num_segments` (`GetMobTrackInfo`) com os componentes da bin **sem os `Filler(0)`** | 18 trilhas reais: V1 5→4, V2 3→2, A1 8→6 | confirmado |
| Ausentes nesta build: `SetPosition`, `MakeViewerActive`, `GetListOfWindows` | chamadas diretas | confirmado |

## 2026-08-24 — a leva sob a régua nova

> Régua revisada nesta data (*ler tudo, registrar mecanismo*) — ver
> [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md) §A régua.

| descoberta | fonte | confiança |
|---|---|---|
| ⭐⭐ **O WebSocket do ESION não é uma porta, é uma FAIXA de 10** (52413–52422), varrida em sequência | `.avpi` do ESION 25.1.0, `src/web-socket/useMultiPortWebSocketConnection` — bundle **não obfuscado** | confirmado — **corrige** o registro anterior |
| ⭐⭐ **As 19 mensagens do protocolo**, em pares `*request`/`*response` mais **5 empurradas pelo servidor** (`progress`, `jobprogress`, `processingresponse`, `jobcomplete`, `progressresponse`) | `src/types/messageTypes.ts` no bundle | confirmado |
| ⭐ **O painel não faz polling de progresso** — registra, manda o job e RECEBE; é por isso que há WebSocket em vez de HTTP | mesma fonte | inferido |
| ⭐ **A anatomia do XML de settings do Avid** (`DomainMagic`/`DomainKey`, `AvClass SETG`+`EXst`, 4 `AvProp id=ASET` genéricos, 21 `EXst`, **395 `ATTR`**) | componente `ESIONserverAvidXML` → `/Applications/Avid Media Composer/Settings/ESION.xml` | confirmado |
| ⭐⭐ **`allowedDomains` precisa listar TODA a faixa varrida** — o Quickture declara as 10 (`localhost:3030`…`3039`), o ESION declara 1 de 10 | comparação dos dois `avid-manifest.json` | **inferido forte** — não medido |
| ⭐⭐ **O helper do Quickture fala gRPC DIRETO com o backend**, como o `_DeLaPraCa`; o ESION vai pelo gateway 4930 com token | 184 ocorrências de `mcapi` + 83 de `grpc` no binário do helper | inferido |
| ⛔⭐ **Das 32 rotas gRPC do helper, 31 já estavam no banco** — prova independente de que a extração do `mcapi.proto` por **reflection** entregou a superfície COMPLETA | cruzamento com [dados/mcapi.proto](dados/mcapi.proto) | confirmado |
| ⭐⭐ **Marcadores no MC existem e estão em uso de produção** (`AddMarker`/`AddMarkers`/`ChangeMarker`/`DeleteMarkers`/`GetMarkers`) | rotas do helper | confirmado |
| ⭐⭐ **Dá para ESCREVER metadado no Avid:** `SetMobInfo` em produção, e `CreateCustomColumn`+`GetBinColumnInfo` criam **coluna própria na bin** | rotas do helper | confirmado |
| ⭐ **`SetPosition` é usado por produto comercial** — confirma que a ausência no MC 2025.6 é de VERSÃO | rotas do helper | confirmado |
| ⭐ **`LoadSetting`** encaixa com o XML do ESION: há rpc para carregar setting instalada | rotas do helper | confirmado |
| ⭐⭐ **`LoadSetting` instala preset de export com o MC ABERTO** se o envelope traz `<AvClass id="SETG"/>`; `ExportFile` com ele: 240/240 quadros e TC iguais ao original (2026-10-11, MC 25.6 Windows) | laboratorio-de-midia `lab/bancadas/avid.py` (`instalar_preset`/`exportar`) | confirmado |
| ⚠️⚠️ **Terceiros rodando dentro do MC** no `allowedDomains` do Quickture: `gleap.io`, Datadog RUM, `cloudflareinsights.com`, `googletagmanager.com`, `cookiebot.eu`, `youtube.com` | `avid-manifest.json` | confirmado |
| ⭐ **`pusher.com`: o painel do Avid recebe evento DA NUVEM**, não de daemon local | mesma fonte | inferido |
| ⭐ **As duas formas do `url` do `uiItem` estão exercitadas por produtos reais** — relativo (Quickture) e `http://localhost` (Jumper, ESION) | os três manifestos | confirmado |

Método e limites: [esion-arquitetura.md §5.5](esion-arquitetura.md) e
[quickture-avid-helper.md §A régua](quickture-avid-helper.md). ⛔ O binário do helper **não foi
descompilado** (não foi preciso); o daemon do ESION (~1,5 GB) **não foi aberto**; licenciamento não
tocado em nenhum dos dois; nada instalado, nada executado.
| 2026-09-19 | Arrastar BIN/PASTA do painel lateral não identifica o item por NENHUM canal de fora: webview (`types` vazio), OLE (`mediacomposer.sidebar.bins.list`, 1 byte que varia para a mesma bin), `mcapi.onEvent` (nada), UI Automation (17 nós na janela inteira) — MC 2025.6, Windows | sondas `tools/sonda_painel/`, `tools/sonda_arrasto_nativo.py`, `tools/sonda_acessibilidade.py` do Assist anterior, com o autor arrastando | confirmado |
| 2026-09-19 | Dois `_pb2` do mesmo `.proto` com nomes de arquivo diferentes no mesmo processo: `duplicate symbol 'mcapi.Stereoscopic'` (protobuf 7.36.0) — medido na fusão do Ciclo Assist no Assist anterior | importando os dois stubs num Python só | confirmado |
| 2026-09-02 | `GetBinFromMob`: exige agrupamento `26-6-16-12-4` (as outras cinco formas devolvem `None` em silêncio) e localiza todo SUBCLIPE mas só 1 de 19 masterclipes — os das bins que o MC tem localizadas | Assist anterior contra `CENAS/C07.avb`, MC 25.6/Windows, projeto real | confirmado |
| 2026-08-27 | ⛔⛔ **`Source File`/`Source Path` são texto livre de um `.avb`/AAF de TERCEIRO** — `Path(pasta) / arquivo` descarta `pasta` quando `arquivo` é absoluto (UNC incluso), e o `.exists()` sobre o resultado **abre sessão SMB no Windows** apontando para o host que o autor do projeto escolheu. Corrigido normalizando `Source File` para só o nome. Achado comparando o `mcapi.py` do Assist anterior com o fork Órbita (commit `34b798b`) | execução real: teste espiona `Path.exists` e afirma sobre o caminho TOCADO — a 1ª versão do teste passava antes do conserto, afirmando só o valor devolvido | confirmado |
| 2026-08-27 | `bins()` sem filtro devolve a LIXEIRA junto (pasta `Trash/` no disco, mesmo com MC em português) — 21 de 48 bins de um projeto real estavam lá, algumas com nome DUPLICADO de uma bin viva | medido no fork Órbita/Assist anterior, `PROJETO EXEMPLO` | confirmado |
| 2026-09-24 | As duas linhas acima e o `LoadMobsIntoViewer`→`GetViewerMobs`/`CloseBin` colados (ver `docommand-comandos.md`, linha "Carregar SEQUÊNCIA na Record") **portados para `_DeLaPraCa/plugins/media-composer/servico/avid/mcapi.py`** — o app original de onde o Assist anterior tinha copiado o motor ainda não tinha essas três correções | comparação `_DeLaPraCa` × `_ASSIST ANTERIOR/motores/delapraca`; suíte de testes do De Lá Pra Cá (16 arquivos) rodada no Windows antes e depois, `tests/test_seguranca_mcapi.py` novo | confirmado |
| 2026-09-24 | Seleção da timeline pela cópia do editor: Ctrl+C → `DoCommand(6292)` → `CreateSubClip(use_clip_bounds=True, end_frame=-1, create_new_sequence=True)` numa bin → `.avb` idêntico (125/125) à subsequência arrastada à mão; área de transferência do Windows vazia após o Ctrl+C; `SetPosition` ausente; `current_frame` base 0; `GetMobTrackInfo.selected` lê o seletor de trilha — MC 2025.6.58781, Windows 11 ([copia-da-timeline.md](copia-da-timeline.md)) | `_DeLaPraCa/.dev/spike_monitores.py`, `spike_createsubclip.py`, com o autor copiando segmentos contíguos e salteados | confirmado |
| 2026-09-24 | O BOTÃO copia sozinho: `Ctrl+0` → `Ctrl+C` por `SendInput` funciona (`1915`→`6224` pela API não copiou); `6292` abre a cópia no monitor ATIVO (o Record, depois de o editor mexer na timeline); ache pelo mob que mudou e devolva a sequência com `LoadMobsIntoViewer` (volta na mesma posição); `MakeViewerActive` ausente e `active` vazio no 2025.6; `DoCommand` colado → ErrorType 73 — MC 2025.6.58781, Windows 11 ([copia-da-timeline.md](copia-da-timeline.md)) | `_DeLaPraCa/.dev/spike_coletar_botao.py`, com o autor selecionando (V1+V2) e clicando no painel | confirmado |
| 2026-09-24 | A cópia do Avid é o TRECHO do primeiro ao último segmento selecionado em cada trilha (3 clipes marcados em papel pelo autor, sem contar → vieram exatos + os do meio); sem seleção, o Ctrl+C mantém a última cópia (2x idêntica); `IsCommandsEnabled(6224)` = true sem seleção; não há comando para limpar a cópia — MC 2025.6.58781, Windows 11 ([copia-da-timeline.md](copia-da-timeline.md)) | `_DeLaPraCa/.dev/spike_coletar_botao.py`, gabarito do autor em papel | confirmado |
| 2026-10-11 | Effect Editor: o MOLDE do ▶ (editor normal e de pintura), o editor de pintura rola sozinho ao abrir grupo, rolar pela faixa da barra (nunca a roda); Color Correction inteiro em 9 páginas; abrir/rolar não grava na bin; o MC reserva ~11,4 GB privados ao abrir — MC 25.6, Windows 11 ([windows.md](windows.md), seção do Effect Editor) | laboratorio-de-midia `lab/bancadas/avid_efeitos.py` (`_e_seta`, `_rolar`, `fotografar_editor`), LAB_EF_IMAGE (6 efeitos), `param_list` lido na bin depois; contadores de memória do Windows | confirmado |
| 2026-10-13 | Painel solto do MC: quadro que não chega à tela (5/17 → 0/24 com o repintar inteiro), latência ~210/360 ms, troca de foco → 3/17 entre 1 e 3,8 s, API do MC sem atraso; `LinkFile` com teto de 20 s deixava master órfão; destino do `LinkFile` com `.avb` (MC 25.6, Windows 11) — [windows.md](windows.md) §9 e §10 | piloto sem o autor: `ImageGrab` da área do cartão a cada 30 ms; `/diag/erro` do De Lá Pra Cá (`186d2c6`, `7ecff93`); bin O02 de 92 timelines | confirmado (o encaixado e a causa dos 30 s: pendente) |
| 2026-10-13 | Relink de AAF recebida (PRODUCAO-A): modal de áudio no LinkFile de BWF (hipótese `bext` TimeReference, 41/47), ImportFile sem diálogo e com MobIDs mantidos, Save colado no ImportFile aborta a importação, "Sub clip conflict found", HEVC Main 10 "cannot be linked", WAV float 32 estéreo sem modelo — [windows.md](windows.md) §11 | pilotado; De Lá Pra Cá `1d407a2`; leitura dos chunks RIFF dos 47 áudios | confirmado (o gatilho do modal: hipótese) |
| 2026-10-17 | **MC 2021.12.10.56256 (Windows) — Panel SDK DESLIGADO.** Sem `PanelSDKPlugins`, sem `avid-api-gateway`, sem gRPC 9100; `.avpi` à mão (DLPC + parceiro PARCEIRO-Q) não aparece. Flag `/Media Composer/3PDevPanelSDK` (grupo `avid.SDK.developer.features`). O `.ftf` tipo 1 (SDKDeveloperToggles) = `base64("Salted__"+AES_systemId(S/MIME assinado Avid))` → inviável forjar; tipo 2 e CIT_OVERRIDE (0x7fffffff) = JSON texto claro sem assinatura, mas `systemId` amarrado à máquina; aplicação por grupo. CIT_OVERRIDE é override GLOBAL e liga o `3PDevPanelSDK` — barrado por gate: só com `GetVersionBuildType`='b'/'d' (`dwFileFlags` do VERSIONINFO do exe com bit 0x2/0x8), e o trial tem `dwFileFlags=0x0` (release). Ver [ativar-no-2021-ftf.md](ativar-no-2021-ftf.md) | REA/Ghidra 12.1.4 no `FTF.dll` (sha256 a365…92f8c) + `AvidSearch.exe`/`AvCoreM2W10.dll`; harnesses em C contra o `FTF.dll` real (`D:\_ZELADORIA\mc2021-ftf\`: ftfprobe/ftftest/ftfcit/ftfbt); `dwFileFlags` lido por version.dll | confirmado (in-process + call site do FTF_Init medido no AvidMediaComposer.exe: FTF_Init(sysID, GetVersionBuildType=='b'||'d'), por pefile+capstone) |
| 2026-10-17 | ⛔⛔ **CAUSA RAIZ: MC 2021.12.10 NÃO TEM o runtime do Panel SDK.** Patch do build-type aplicado pelo autor (liga VS_FF_PRERELEASE) — o MC ABRIU normal (sem self-check fatal), mas o painel NÃO apareceu. Medido: binário `avid-api-gateway` ausente; strings no exe `avid-api-gateway`=0, `PanelSDKPlugins`=0, `GetPluginAccessToken`=0, `panelsdk`=0, `avid-manifest`=0 (só vestígios: `qwebchannel.js`, `Panel SDK`×1, `mcapi.MCAPI`×1). O toggle `3PDevPanelSDK` é resquício; o motor de painel (gateway/registro de .avpi/menu) só veio no 25.6+. Ver [ativar-no-2021-ftf.md](ativar-no-2021-ftf.md) | teste do autor (console colado) + `grep -c -a` das strings no AvidMediaComposer.exe 2021.12 + ausência do gateway no diretório | confirmado |
| 2026-10-17 | **API gRPC `mcapi.MCAPI` (porta 9100) tambem AUSENTE no 2021.12.10.** Com o MC aberto (PID real), 0 portas TCP em LISTEN e connect a 127.0.0.1:9100 recusado. ⇒ no 2021.12 nao existe NEM o painel (Panel SDK, sem runtime) NEM a API de dirigir por fora (estilo Orbita). Ambos vieram em versao posterior | `Get-NetTCPConnection -State Listen` filtrado pelo PID do AvidMediaComposer + TcpClient.BeginConnect em 127.0.0.1:9100 | confirmado |
| 2026-10-17 | ⭐ **Linha do tempo do Panel SDK (quando surgiu):** 2021.12.10 e 2022.12.9 = SEM runtime (o 2022 só cita `avid-api-gateway`/`avid-manifest` no exe, sem o binario); **2023.8.2 = primeira COMPLETA** (traz `avid-api-gateway.exe`, `PanelSDKPlugins` com `avid-huddle.avpi`, `PanelSDK.json`, `APIGateway`, `GetPluginAccessToken`×4, `panelsdk reinit`×3); 2024.6.0 e 25.12.2 idem. ⇒ base recomendada = MC 2023.8.2. Ver [ativar-no-2021-ftf.md](ativar-no-2021-ftf.md) tabela | inspecao NAO-destrutiva dos 4 instaladores extraidos em Downloads\VERSOES MC (find de arquivos + grep -c -a de strings no AvidMediaComposer.exe de cada) | confirmado |
| 2026-10-21 | **MC 24.6 pelo Órbita (janela do app, sem painel):** `LinkFile` assíncrono (volta em ~0,1 s; o MC linka depois com "Linking clips…"; chamada nesse meio = "cannot be linked" em 7/30 s — 3ª causa da mensagem; esperar o MC sem diálogo = 26/26); modal "Audio Start-Time Options" do BWAV desenhado (combo de taxa, OK/OK to All, posições); timeline em branco depois do `/avid/montar` até recarregar; arrasto sintético da bin para o alvo nativo do Órbita (masterclips e sequência) funcionou. Ver [ativar-no-2021-ftf.md](ativar-no-2021-ftf.md) §MC 24.6 operado por fora | pilotado: projeto "ORBITA DEMO D02", 26 MP4 + 24 BWAV da PRODUCAO-A; cliente gRPC do DLPC pelo `piloto.pontes` | confirmado (a causa da timeline em branco: pendente) |
| 2026-10-24 | MC 25.12 (Mac): um diálogo modal (Leave the application?, Select Project) ou o MC subindo também travam o `GetAppInfo` (DEADLINE_EXCEEDED, não UNAVAILABLE); sonda curta, prazo estourado = ocupado | De Lá Pra Cá `api/rotas._conexao_mc`, `tests/test_conexao_mc.py`; pilotado na janela do app | confirmado (Mac) |
| 2026-10-28 | ARO revisado: socket/log herdados pelo `avid-api-gateway` (sem `FD_CLOEXEC`), `SO_REUSEPORT` = sequestro (6/6), vmaddr só no build `25.12.0.58863`, SIGSEGV preso à main; SEQ = grupo `type=0`; master dentro do efeito pelo `AComponent::VisitLinks` (efeitos empilhados 1–3 e Collapse de V1+V2 = gabarito do `.avb`) | De Lá Pra Cá, MC 25.12.0 Mac arm64, projeto LAB_ARRASTO_MAC (PRODC_CORTE02), pilotado; `lsof`/`vmmap`; desmontagem do `libameLibrary` (`otool`) | confirmado |

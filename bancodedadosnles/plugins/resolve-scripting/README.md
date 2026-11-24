# DaVinci Resolve — API de scripting (Python / Lua)

> **Por que esta pasta existe, e por que nasceu tarde.** O banco tinha
> [`premiere-cep/`](../premiere-cep/) e [`avid-panel-sdk/`](../avid-panel-sdk/) e **nada de
> Resolve** — apesar de já operarmos o Resolve em produção e de termos lido um concorrente por
> inteiro. O conhecimento existia e estava **no lugar errado**: dentro de um documento de produto
> ([`chopchop-algoritmo.md`](../premiere-cep/chopchop-algoritmo.md)) e dentro de um `.lua` de app.
> A lacuna foi diagnosticada pelo [mapa de operações](../../transversal/operacoes-de-nle.md) e
> fechada em 2026-08-24.

**A referência de operações está em [api-scripting.md](api-scripting.md).**
Rastreabilidade em [fontes.md](fontes.md).

> 🆕 ⚠️⚠️ **ESTA PASTA DESCREVIA APENAS METADE (corrigido 2026-08-24).** O Resolve tem **DUAS**
> superfícies de plugin: os **scripts** (Lua/Python, UIManager do Fusion) documentados aqui, e os
> **Workflow Integration Plugins** — apps **Electron** com UI em HTML que acessam a API por um addon
> nativo da Blackmagic (`WorkflowIntegration.node` → `GetResolve()`).
> **→ [workflow-integration.md](workflow-integration.md)**

## O que é a superfície

O Resolve não tem painel HTML como o Premiere (CEP) nem SDK de painel como o Media Composer. Ele
tem **scripts**, que aparecem em `Workspace → Scripts` e rodam **dentro** do processo do Resolve,
com acesso direto ao objeto `resolve`. A interface, quando existe, é a **UIManager do Fusion** —
widgets nativos (`UIDispatcher`, `AddWindow`, `HGroup`/`VGroup`, `Label`, `Button`, `LineEdit`,
`ComboBox`, `Tree`), não HTML.

⚠️ **Consequência de arquitetura — com a ressalva de 2026-08-24:** *num script* não há webview, então
não há a "segunda superfície" do navegador (arrastar do DOM, `fetch`, armazenamento local). ⭐ **Mas
num Workflow Integration Plugin há** — ele é Electron, e ganha a superfície do navegador inteira.
A frase só vale para a via de scripts.

## ⭐⭐ Lua × Python — a decisão de distribuição

**Use Lua.** É a lição mais cara desta pasta, e vale para qualquer produto que pretenda ser
instalado por um editor.

| | Lua | Python |
|---|---|---|
| interpretador | ⭐ **embutido no Resolve** | precisa de Python **do sistema**, compatível |
| aparece no menu | sempre | ⛔ **só se o Resolve detectar um Python compatível** |
| custo de instalação | copiar um arquivo | instalar Python na máquina do editor |

⛔ **O modo de falha do Python é silencioso e devastador para distribuição:** o script `.py`
simplesmente **não aparece no menu**. O usuário não vê erro — vê ausência.

⚠️ **E o concorrente confirma o problema pela solução:** o Chop Chop edição Resolve é escrito em
Python e, para funcionar, o instalador dele **roda `sudo installer` de um Python 3.13.2 no sistema
do usuário** (carrega o `.pkg` oficial dentro do produto). Elevação de privilégio, um Python a mais
na máquina para sempre, e nada revertido ao desinstalar — tudo para contornar o que o Lua resolve
de graça.

## Onde os scripts moram

| SO | caminho |
|---|---|
| macOS | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/` |
| Windows | `%APPDATA%\Blackmagic Design\DaVinci Resolve\**Support**\Fusion\Scripts\Utility\` |

⚠️⚠️ **O caminho do Windows tem um `Support\` a mais.** Não é simetria de separador — é um nível de
pasta que só existe num dos dois. Ver
[`../../transversal/desenvolvimento-cross-platform.md`](../../transversal/desenvolvimento-cross-platform.md).

⭐ **O menu relê a pasta toda vez que é aberto** — um script novo aparece sem reiniciar o Resolve.
(Diferente do CEP do Premiere, que exige reinício.)

Módulos pip de terceiros, quando o caminho é Python, vão para
`…/DaVinci Resolve/Developer/Scripting/Modules` — é a pasta que o Resolve põe no `sys.path`.

## As duas arquiteturas vistas

| | motor onde | exemplo |
|---|---|---|
| **tudo no script** | dentro do Resolve | Chop Chop (2.355 linhas de Python fazendo parse, agrupamento e montagem) |
| **script fino + serviço local** | app externo | Órbita (`orbita_sync.lua` dirige `127.0.0.1:7817`) |

⚠️ **O script roda no processo do Resolve, então ele BLOQUEIA a interface.** Trabalho pesado dentro
do script congela o app. O padrão que funciona é laço de passos curtos com espera barata
(`bmd.wait`), nunca um processo por tique.

⚠️ **E tudo que sai para um shell (`io.popen`) passa por `/bin/sh -c` ou `cmd`** — caminho de mídia
com espaço, aspas ou `&` vira injeção acidental. Nunca montar linha de comando com caminho.

## Estado de maturidade

| área | maturidade |
|---|---|
| montar timeline (`AppendToTimeline`) | **alta** — validada em produção nos dois produtos |
| trilhas (criar/renomear/subtipo) | **alta** |
| bins, importar, metadado | **média-alta** |
| proxy (`LinkProxyMedia`) | média — lido, não medido por nós |
| sync nativo (`AutoSyncAudio`) | média — lido, não medido por nós |
| ⛔ **mover clipe já colocado** | **`pendente`** — nenhum produto lido faz; *buraco de mapa, não ausência confirmada* |
| 🆕 Workflow Integration Plugins | **baixa** — estrutura mapeada, nada medido → [workflow-integration.md](workflow-integration.md) |
| ⛔ efeitos / parâmetros | **não mapeado** |
| ⛔ marcadores | **não mapeado** pela API. No DRT, sim: moram no `project.xml`, em zstd → [drt-drp/estruturas.md](../../protocolos/drt-drp/estruturas.md) §"MARCADORES DE TIMELINE" |
| 🆕 **relink aos originais** | API de relink (`RelinkClips`/`ReplaceClip`) **não medida**. ⭐ Contorno medido: relinkar **na geração do DRT** (ver abaixo) |

### ⭐⭐ Mídia primeiro, timeline depois: o DRT se liga aos itens que o Resolve já tem — `confirmado` 2026-09-26

Resolve Studio 19.0.0b (Windows). Se os arquivos já estão no Media Pool (importados pelo import
normal), um `ImportTimelineFromFile` de DRT liga os clipes a esses itens, e não aos que o DRT
descreve. Isso vale mesmo quando o DRT declara o formato errado. Medido com um DRT quebrado de
propósito (todo item na forma MXF/DNx, apontando para .BRAW e .MOV HEVC): com a pasta dos
originais arrastada antes para o pool, tudo abriu com imagem, e nenhum item de vídeo duplicou.
No áudio puro (WAV), o autor viu duplicata no pool, mas o som tocou certo com o DRT de formato
correto. O critério exato do reaproveitamento (caminho? caminho + TC?) não foi isolado.

**Uso no De Lá Pra Cá:** a casca chama `MediaPool.ImportMedia(lista)` antes do
`ImportTimelineFromFile`. A lista vem de um `.midias.json` que o serviço grava ao lado do DRT.
Os arquivos ficam em De Lá Pra Cá › Mídia › <timeline>, e o que já está no pool (conferido por
`GetClipProperty("File Path")`) não entra de novo. O mapeamento de codec fica com o Resolve.
Formato do item no DRT, para quando não há pré-importação:
[`../../protocolos/drt-drp/estruturas.md`](../../protocolos/drt-drp/estruturas.md)
§"O item do pool declara o FORMATO".
- ✅ **Pela ponte JS da Workflow Integration, `confirmado` 2026-09-26:** o De Lá Pra Cá
  importou a PRODA_CORTE pelo painel, num projeto novo. O `MediaPool.ImportMedia(lista)` trouxe
  100 de 100 arquivos (BRAW, WAV, MOV HEVC) em 0,3 s, na pasta escolhida com
  `SetCurrentFolder`. A timeline veio depois, em 6,4 s, e o autor conferiu: tudo tocou
  certo, com imagem e som.

#### ⚠️ Áudio: o reaproveitamento NÃO depende só do item — em aberto (2026-09-26)

Com a mídia pré-importada, o áudio de **1 e 2 canais** duplica no pool, e o de 3 ou mais não.
Isso vale mesmo com o item de áudio do DRT idêntico ao que o Resolve cria: 55 de 55 arquivos
iguais em estrutura de canais, trilha e formato, comparados com o `Project.db`. Portanto o
critério não é o item.
- **Medido no `Project.db` depois da importação** (Resolve 19.0.0b, 2026-09-26): o Resolve
  decide **clipe a clipe** a que item ligar.
  - Os 633 clipes do som direto (3 a 5 canais) apontam (`Sm2TiItem.MediaRef`) para o item que
    ELE criou.
  - Os 93 clipes de efeitos e trilhas (1 e 2 canais) apontam para o item do DRT.
- **O item não é o critério.** Com o item do DRT idêntico ao do Resolve, o mono e o estéreo
  duplicaram. E o som direto já era reaproveitado com o item antigo do esqueleto, que tinha
  outra estrutura.
- **`VirtualAudioTrackBA` do clipe** (mapa Qt): `ChannelsBA` = `[u32 2][u32 n]` + n words de
  u32, com **word = (trilha << 14) | canal** (1-based). Mais `AudioType`: 1 = mono, 0 =
  estéreo.
  - Som direto (N trilhas mono): `0x4001`, `0x8001`, `0xC001`…
  - Estéreo (1 trilha): `0x4001` / `0x4002`.
  - O nosso DRT grava esses valores. No DRT de referência, o áudio estéreo da câmera virou UM
    clipe com `ChannelsBA` [`0x4001`, `0x4002`] e `AudioType` 0, numa trilha estéreo. O nosso
    grava dois clipes mono (`AudioType` 1), como vêm do Avid.
- **Hipótese seguinte:** o Resolve só reaproveita o item de um arquivo mono ou estéreo quando o
  clipe tem o mesmo tipo de trilha do arquivo. `pendente`. Teste sugerido: um DRT pequeno com um
  WAV estéreo em duas variantes, (a) dois clipes mono e (b) um clipe estéreo com `AudioType` 0
  numa trilha estéreo, importado com a mídia pré-importada.
- **Timeline de referência montada à mão no Resolve 19** (autor, 2026-09-27, projeto
  `_DELAPRACA - testes/stereo e dual mono`): 4 WAV estéreo, 2 deixados como estéreo e 2 como
  dual mono (atributos do clipe). A1 estéreo; A2 e A3 mono. Lido no `Project.db`
  (`Sm2TiItem` + `Sm2MpMedia`): `confirmado`.

  | Clipe | Trilha | `MediaTrackIdx` | `ChannelsBA` | `AudioType` |
  |---|---|---|---|---|
  | estéreo inteiro | A1 estéreo | 0 | `1:1, 1:2` | 0 |
  | dual mono, canal 1 | A1 estéreo | 0 | `1:1` | 1 |
  | dual mono, canal 2 | A2 mono | 1 | `1:2` | 1 |
  | dual mono inteiro | A2 + A3 mono | 0 e 1 | `1:1` / `1:2` | 1 |
  | estéreo numa trilha mono | A3 mono | 0 | `1:1, 1:2` | 0 |

  - **O item diz quantas trilhas o arquivo oferece.** O item estéreo tem `VirtualAudioTracksBA`
    vazio, com 1 trilha estéreo implícita. O item dual mono grava 2 trilhas virtuais, `"0"` =
    [`1:1`] e `"1"` = [`1:2`], ambas com `AudioType` 1.
  - **`MediaTrackIdx` é o índice da TRILHA VIRTUAL do item, não o canal.** Só existe clipe
    mono do canal 2 (`MediaTrackIdx` 1) quando o item é dual mono. Com o item estéreo, o
    Resolve não põe um canal sozinho: o estéreo numa trilha mono continua sendo UM clipe
    `AudioType` 0 com os 2 canais.
  - **O que fazemos hoje:** o nosso DRT grava, para um WAV estéreo vindo do Avid, dois clipes
    mono (`MediaTrackIdx` 0 e 1, `AudioType` 1) apontando para um item ESTÉREO. Essa
    combinação não existe no Resolve. O `MediaTrackIdx` 1 não cabe no item estéreo que a
    pré-importação criou, e isso explica a duplicata dos arquivos de 2 canais.
  - **Mono (medido em 2026-09-27):** o clipe nativo de um WAV mono (`MIC1_DJI_…WAV`, numa
    trilha mono) tem `MediaTrackIdx` 0, [`1:1`] e `AudioType` 1, e o item tem
    `VirtualAudioTracksBA` vazio. O clipe do "Fiat Panda … ENGINE_1.wav" (o único mono da
    PRODA_CORTE) no nosso DRT é igual campo a campo. Só diferem o `FieldsBlob` e o
    `MediaFrameRate`, que é a taxa da timeline (24 × 23,976). A duplicata do mono **não vem
    do clipe**. `pendente`: a causa. O "novo projeto" de 2026-09-26 foi apagado, e não dá
    para reler o que foi medido lá.
  - **Contorno no De Lá Pra Cá** (2026-09-27; `confirmado` pelo autor no Resolve 19, com a
    PRODA_CORTE importada pelo painel: nenhum áudio duplicado):
    - o WAV/AIF de 1 e 2 canais NÃO é pré-importado (`sessao_receber._gravar_midias`, lista
      `depois`); o item do DRT é o único, e a casca o move com `MediaPool.MoveClips` para
      Mídia › <timeline>;
    - o item de 2 canais do DRT declara dual mono (`writer.VIRTUAL_DUAL_MONO`, os 206 bytes
      medidos).
  - ⚠️ **Rota do `.prproj` (Premiere → Resolve): o som de 3 e 4 canais TAMBÉM duplica** —
    `confirmado` 2026-10-19 (Resolve Studio 19.1.4, Windows, R04 PRODUCAO-C): os 3 WAV do som
    direto (3 e 4 canais, pcm 24 bits) pré-importados ficaram com um 2º item do DRT solto na pasta
    da timeline (73 itens, 3 duplicados). O clipe do Premiere usa um subconjunto de canais, não as N
    trilhas mono do Avid. Contorno: nesta rota TODO som puro vai para `depois`
    (`_gravar_midias(som_depois=True)`): 70 itens, 0 duplicados, imagem 144/144 nos dois projetos.
    A causa exata (o `ChannelsBA` do clipe do Premiere) segue `pendente`.
- **Instrumentos que funcionaram:**
  - `fuscript.exe -l lua` com o Resolve aberto: listar o pool com `GetClipProperty("File Path")`,
    `Usage`, `Start TC` e `Audio Ch`;
  - o banco do projeto local, que é **SQLite**:
    `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Resolve Project Library\Resolve Projects\Users\guest\Projects\…\Project.db`.
    Tem as mesmas estruturas do DRT (`Sm2MpMedia`, `BtAudioInfo`), com os blobs em zstd e o
    mapa Qt (`_DeLaPraCa/motor/drp/ba_mapa.py`). Copiar o arquivo antes de ler.
- Estrutura do item de áudio nativo por número de canais: ver
  [`../../protocolos/drt-drp/estruturas.md`](../../protocolos/drt-drp/estruturas.md).

### Clipe offline: o NOME do arquivo precisa da extensão para o Resolve reconectar sozinho — `confirmado` 2026-09-27

Medido pelo autor no Resolve 19 (caso E06 da pasta de testes): num DRT com o clipe offline chamado
`RELINKER_TESTCHART_3840x2160` (sem `.mov`), importar os mesmos arquivos no Media Pool NÃO
reconectou a timeline. Os itens ficaram lado a lado no pool, o offline sem a extensão.
- **Regra:** a referência offline leva o nome do arquivo com a extensão. Com o Media Composer, vem
  da coluna `Source File`. Com a bin aberta fora dele, vem do caminho do master AMA
  (`caminho_na_bin`, só o NOME; a pasta é de outra máquina, e um caminho de fora no DRT é o
  ataque V2). O reel, sem extensão, é o último recurso.
- Implementado em `_DeLaPraCa/motor/avb_bin/segmentos.py::referencia_offline`. ✅ Conferido pelo autor
  (2026-09-27): com a extensão, o Resolve reconectou sozinho ao importar os charts.

### ⭐ Relink aos originais sem a API de relink: gerar o DRT já apontado — `confirmado` 2026-09-26

O De Lá Pra Cá (ADR 0020) não relinka a timeline depois de importada. Ele casa os masters da
timeline com os arquivos em alta das pastas do colorista ANTES de gerar o DRT, e o DRT já
nasce apontando para os originais: a timeline entra online e nenhuma chamada de relink do
Resolve é feita.
- **Casamento:** é o mesmo do relink do Avid (`indexer` + `matcher_masters`), por nome do
  arquivo original, com a duração como veto.
- **Som:** o do original lê o canal que o Avid usava.
- **Medido na PRODA_CORTE real** (877 clipes, 118 masters), contra a rodagem
  (`PRODUCAO-A\MIDIAS`, .mp4 convertidos), sem Resolve:
  - 100 masters casaram por nome exato, 1 ficou ambíguo e 17 sem par. Os 17 são efeitos
    sonoros de biblioteca, fora da rodagem.
  - Casamento em 4,1 s; DRT em 8,3 s.
  - Resultado: **841 de 877 clipes nos originais**, contra 737 na gerenciada e 140 offline
    sem a pasta.
- ~~`pendente`: conferir no Resolve, pelo autor, que os clipes entram online nos mesmos
  frames.~~ **CORRIGE (2026-09-26):** na 1ª conferência eles entraram **Media Offline**. O
  caminho, o TC e o trecho estavam certos. O defeito era o FORMATO que o item do pool
  declarava (MXF OP-Atom, herdado da forma do esqueleto). Corrigido no writer, e o autor
  conferiu no Resolve 19: a PRODA_CORTE abriu com imagem e som nos originais. Ver
  [`../../protocolos/drt-drp/estruturas.md`](../../protocolos/drt-drp/estruturas.md)
  §"O item do pool declara o FORMATO". `confirmado`.

## Ver também

- [api-scripting.md](api-scripting.md) — a referência de operações, com as armadilhas.
- [`../../transversal/operacoes-de-nle.md`](../../transversal/operacoes-de-nle.md) — o mapa por
  mecânica, com uma coluna por NLE.
- [`../../protocolos/drt-drp/`](../../protocolos/drt-drp/) — o **formato de arquivo** do Resolve
  (`.drt`/`.drp`), que é a outra via: escrever o arquivo em vez de dirigir o app.
- [`../premiere-cep/chopchop-algoritmo.md`](../premiere-cep/chopchop-algoritmo.md) — o concorrente
  lido por inteiro; é de lá que vem metade desta pasta.

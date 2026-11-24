# Chop Chop Sync and Bin — o concorrente direto, nos dois NLEs

Quinto caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md).
Fatos consumíveis em [dados/chopchop.json](dados/chopchop.json).

**Por que este caso importa, e por que é diferente dos quatro anteriores:** Eddie AI,
Premiere Copilot e Chat Video Pro são *assistentes de decupagem* — resolvem um problema
vizinho. O Chop Chop resolve **o nosso**: ingest de diária, agrupamento por
episódio/cena/shot/take, sync de câmera com som direto, criação de bins e montagem de
timeline de stringout. É a primeira vez que lemos um produto que faz **a mesma coisa**,
e nos **mesmos dois NLEs** que já atendemos.

⭐ **O achado que mais muda o nosso mapa:** no Resolve eles **não sincronizam** — chamam
`MediaPool.AutoSyncAudio()`, o sync nativo do Blackmagic, e cuidam só do que vem antes e
depois. No Premiere, onde não existe equivalente, sincronizam por **sobreposição de media
time em ticks**, com tolerância. Ou seja: **nenhuma das duas edições tem motor de forma de
onda próprio.** O Órbita tem. Isso é vantagem nossa, e o manual deles diz por quê (§Sync).

## O que foi inspecionado

| peça | versão | onde |
|---|---|---|
| Extensão CEP (Premiere) | `com.syncBin.ccms` **1.2.0** (ext 6.1.0), build 2025-02-09 | `Chop Chop Sync and Bin 1.2.0.zxp` (9,3 MB) |
| Script Fusion (Resolve) | **v1.0**, build 2025-08-24 | `ChopChopResolve_v1.0_macOS.pkg` (73 MB) |
| Instalador Windows (Resolve) | Inno Setup **6.4.0.1** | `ChopChopResolve_v1.0_Windows.exe` (32 MB) — **não extraído** (redundante) |
| Manual Premiere | v1.1.4, 23 pp | PDF no pacote |
| Manual Resolve | v1.0, 19 pp | PDF no pacote |

Material entregue pelo autor em `PROGRAMAS ANALISAR/syn material bruto tipo orbita/`,
analisado em 2026-08-24.

⚠️ **Duas edições, duas bases de código, dois níveis de maturidade.** O Premiere está em
1.2.0 e o Resolve em 1.0, seis meses mais novo. Não é o mesmo programa portado — é o mesmo
*produto* reescrito. Os defaults divergem (o gap de take é 2 s no Premiere e 3 s no
Resolve), o que é sinal de reimplementação, não de configuração compartilhada.

---

## 1. Como cada um se pendura no NLE

### Premiere — painel CEP clássico

`CSXS/manifest.xml`, `<Type>Panel</Type>`, 600×450, `Host PPRO [1.0,99.0]` (todas as
versões). `CEFCommandLine` pede `--enable-nodejs`, `--mixed-context`,
`--allow-file-access`, `--allow-file-access-from-files`, `--enable-media-stream`.

⭐ **`--mixed-context`** — contexto JS único para todas as instâncias do painel. Junto com
`--enable-nodejs`, é a receita para um painel que trata o Node como parte do próprio
processo, e não como sandbox à parte.

**O painel FAZ o trabalho pesado** — não há motor externo, não há servidor local, não há
binário próprio além do ExifTool. Isso o coloca num quarto ponto do triângulo que o
[README](README.md) desta pasta desenha: nem painel fino com motor remoto (Eddie), nem
sem motor (Copilot), nem motor embarcado grande (Chat Video Pro), mas **motor pequeno
dentro do Node do CEP**. Cabe porque o trabalho é I/O e aritmética de timecode — não há
decodificação de áudio.

**105 pacotes npm embarcados.** Os que contam:

| pacote | o que revela |
|---|---|
| **`node-exiftool`** + `file-system-helper/dependencies/exiftool.exe` | ⭐ o leitor de metadado é o **ExifTool**, não o ffprobe |
| `node-machine-id` | impressão digital de máquina → licenciamento por nó |
| `node-disk-info`, `recursive-readdir`, `md5-file` | varredura de disco e identidade de arquivo |
| `winston` + `winston-transport` + `@dabh/diagnostics` | log estruturado em arquivo |
| `request` (deprecado desde 2020) | HTTP — a base é antiga |
| `ui-builder`, `css-manager`, `html-helper`, `notifications-manager`, `file-system-helper`, `string-utils`, `date-helper` | ⭐ **sete pacotes in-house**, todos com `author: usuario Terceiro` |

⭐ **A ausência que informa mais que as presenças: nenhuma biblioteca de áudio.** Sem
ffmpeg, sem decoder, sem FFT, sem correlação. Confirma pelo lado do bundle o que os
símbolos do ExtendScript já diziam — a edição Premiere **não tem sync por forma de onda**.

⚠️ **Exige internet permanente.** O manual põe isso no §Troubleshooting: *"The panel is
black and no buttons appear. This is due to a lack of internet connectivity."* Sem rede o
produto não abre — não é degradação, é porta fechada.

### Resolve — script do Fusion, não painel

Nada de webview. O produto é **um script Python solto** em
`…/DaVinci Resolve/Fusion/Scripts/Utility/`, chamado pelo menu de scripts do Resolve, com
UI construída na **UIManager do Fusion** (`UIDispatcher`, `AddWindow`, `HGroup`/`VGroup`,
`Label`, `Button`, `LineEdit`, `ComboBox`, `CheckBox`, `RunLoop`/`ExitLoop`,
`RecalcLayout`). Interface nativa, sem HTML.

As dependências pip vão para
`…/DaVinci Resolve/Developer/Scripting/Modules` — a pasta que o Resolve põe no `sys.path`
do interpretador de script. Vendorizam `requests`, `urllib3`, `certifi`, `pycryptodome`,
`licensespring`, `winregistry`.

⛔⭐ **E o `postinstall` instala um Python no SISTEMA:**

```
sudo installer -pkg /tmp/python-3.13.2-macos11.pkg -target /
```

O `.pkg` do produto carrega o instalador oficial do **Python 3.13.2** e o executa com
`sudo` durante a instalação. É a solução deles para o problema que também é nosso: o
scripting do Resolve precisa de um Python do sistema, e a máquina do editor pode não ter.

⚠️ **É exatamente o que o Órbita decidiu NÃO fazer** — nós embarcamos o sidecar
(`orbita-python.exe`, `externalBin` do Tauri) e nunca tocamos no Python da máquina. A
comparação vale a pena por escrito porque o custo aparece do lado deles: instalação que
exige elevação, um Python a mais no sistema do editor para sempre, e nada disso reversível
por desinstalar o produto. **A nossa escolha é mais cara em bytes e mais barata em
consequência.**

---

## 2. Como montam a timeline

Esta é a parte que o autor pediu, e as duas edições convergem no desenho — o que sugere
que a convenção veio do **fluxo de trabalho** (stringout de novela/série), não da API.

### O layout do stringout (documentado no manual, confirmado no código do Resolve)

```
[ shot 1 take 1 ][2-3s][ shot 1 take 2 ]      [ shot 2 take 1 ][2-3s][ shot 2 take 2 ]
                                        ^10s^
```

| regra | Premiere | Resolve | evidência |
|---|---|---|---|
| uma timeline por **cena** | ✅ | ✅ | manual, ambos |
| trilha de vídeo = **subpasta de origem** (= câmera) | ✅ | ✅ | manual, ambos |
| gap entre **shots** | 10 s | 10 s | `recordFrame += round(fps * 10)` |
| gap entre **takes** | 2 s | 3 s | `round(fps * 3)` no Resolve |
| multicâmera | empilhado | empilhado no mesmo `recordFrame` | `stackBaseRecordFrame` |
| som direto | empurrado **para cima** | idem | manual |
| mic de câmera | empurrado **para baixo** | idem | manual |

⭐ **O gap não é decoração — é o índice.** Dez segundos de preto separando shots e dois ou
três separando takes transformam a timeline num sumário navegável: o editor lê a estrutura
da diária pela silhueta, sem ler nome de clipe. É uma decisão de produto que vale
registrar independentemente da implementação.

### A mecânica no Resolve (`confirmado` — lido no código)

Só a API pública do scripting, nada de escrever `.drt`:

```
mediaPool.CreateEmptyTimeline(nome)
timeline.SetSetting('timelineFrameRate', fps)          # e 'timelinePlaybackFrameRate'
timeline.AddTrack('video')                              # uma por câmera
timeline.AddTrack('audio', 'adaptive1' | baseSubtype)
timeline.SetTrackName('video', indice, cameraID)
mediaPool.AppendToTimeline([
  {mediaPoolItem, startFrame, endFrame, trackIndex, recordFrame}, …
])
```

⭐ **`recordFrame` é o que faz o stringout.** É o campo do `clipInfo` que dá posição
absoluta na timeline; sem ele o `AppendToTimeline` só empilha em sequência. Todos os
clipes de um mesmo take recebem **o mesmo `recordFrame`** (`stackBaseRecordFrame` /
`groupBaseRecordFrame`) — é assim que a multicâmera fica alinhada verticalmente.

⚠️ **Já usamos `recordFrame`** (`plugins/resolve-script/orbita_sync.py`), então aqui não há
novidade de API — há confirmação independente de que a rota é essa.

### A mecânica no Premiere (`inferido` — da tabela de símbolos do JSXBIN)

Duas superfícies, e a segunda é a interessante:

**API pública:** `createNewSequenceFromClips`, `insertProjItemInSeq`, `setProjItemInOut`,
`getLinkedItems`, `importFiles`, `createBin`, `moveBin`.

**QE DOM** (`app.enableQE()`, não documentado pela Adobe) para tudo que a API pública não
faz: `addTracks` / `addTracksToSeq`, `removeVideoTrack` / `removeAudioTrack` /
`delTrackByIndex`, `renameVidTracks` / `renameAudTracks`, `delEmptyTracksQE`,
`insertClip`, `overwriteClip`, `moveClip`, `moveAllClipsInTrack`, `getSequenceAt`,
`getItemAt`, `getBinAt`, `getQEItemByName`.

⭐ **Confirma o que o [README](README.md) desta pasta já sustenta:** sem QE não se monta
timeline no Premiere. Um produto comercial em produção depende de uma API não documentada
para **criar, apagar e renomear trilha** — o Órbita faz o mesmo (`enableQE` ×7,
`overwriteClip` ×2 no nosso `host.jsx`), e isso deixa de ser risco isolado nosso.

**Aritmética de tempo, toda em ticks:** `TICKSPERSECOND`, `convertSecsToTicks(Str)`,
`convertTimecodeToTicks(Str)`, `convertTicksToTimecodeWithFrames`, `addTicks`,
`multiplyTicks`, `snapTimeToFrameRate`, `convertTimecodeNonDFtoDF`. As variantes `…Str`
existem porque o `ticks` do Premiere estoura o inteiro seguro do JS — mesma armadilha que
[`../../protocolos/prproj/`](../../protocolos/prproj/) registra.

---

## 3. Como sincronizam — e é aqui que ganhamos

### Resolve: delegam ao Blackmagic

```
audioSyncSettings = {
  resolve.AUDIO_SYNC_MODE: resolve.AUDIO_SYNC_WAVEFORM | resolve.AUDIO_SYNC_TIMECODE,
  resolve.AUDIO_SYNC_CHANNEL_NUMBER: 1,
  resolve.AUDIO_SYNC_RETAIN_EMBEDDED_AUDIO: True,
  resolve.AUDIO_SYNC_RETAIN_VIDEO_METADATA: False,
}
mediaPool.AutoSyncAudio(mpItems, audioSyncSettings)
```

Uma chamada. O editor escolhe forma de onda ou timecode num `ComboBox`, e o Resolve faz o
resto.

⛔ **E o manual deles admite o preço, na página 16:**

> *"If you opted to sync by waveform… individual video and audio tracks will be synced
> (Cam A's video will be synced with Cam A's audio), but the clips will not be synced
> across cameras (Cam A will not be synced with Cam B). Run the 'auto-align by waveform'
> function manually to ensure they sync up. Due to the amount of time it takes to align
> clips, syncing by waveform is not recommended if you have a multicam shoot."*

⭐⭐ **Traduzindo: no cenário de novela — multicâmera, som direto — a edição Resolve deles
não sincroniza por forma de onda.** Sobra o timecode, que exige jam sync na diária. Quem
delega o motor herda os limites do motor: o `AutoSyncAudio` casa áudio↔vídeo dentro de um
conjunto, não câmera↔câmera, e é lento o bastante para o próprio fabricante do produto
desaconselhar.

**É a diferença de produto mais defensável que este banco já registrou a nosso favor** — e
não é opinião nossa, é o manual do concorrente.

### Premiere: sobreposição de media time, em ticks

Sem `AutoSyncAudio` no Premiere, eles fazem o que dá com metadado:
`getProjItemMediaTimes` → `mediaTimeA.mediaStart/mediaEnd.ticks` ×
`mediaTimeB.…` → `getSyncFromMediaTimes`, com `timeToleranceTicks`.

É **sync por timecode com tolerância** (dois clipes que se sobrepõem no eixo de media time
pertencem ao mesmo take), não correlação de sinal. Coerente com a ausência de qualquer lib
de áudio no bundle.

⚠️ **Calibração honesta:** isto é `inferido` a partir de nomes de símbolo, não lido em
lógica. O que sustenta a leitura são três evidências independentes — os nomes, a ausência
de biblioteca de áudio, e o fato de o manual do Premiere nunca oferecer escolha de método
de sync (o do Resolve oferece). Se o eixo AUSÊNCIA já nos derrubou cinco vezes
([§calibração](../../transversal/analise-de-executaveis.md)), aqui a ausência está
**triangulada**, não suposta.

---

## 4. Duas técnicas que eles têm e nós não

### ⭐ 4.1 — Estado persistido no XMP privado do projeto (Premiere)

A cadeia de símbolos é inequívoca:

```
kPProPrivateProjectMetadataURI = "http://ns.adobe.com/premierePrivateProjectMetaData/1.0/"
addPropertyToProjectMetadataSchema
addBaseMetadataFields
setProjItemXMPProp / getProjItemXMPProp
setProjItemXMPPropARInfo / getProjItemXMPPropARInfo
getStoredInfoAssignedTracks / updateAssignedTracksInfo
```

Eles **registram campos próprios no schema de metadado privado do projeto** e gravam neles
o estado da própria ferramenta — notadamente qual clipe foi para qual trilha
(`assignedTracks`).

⭐⭐ **É isso que faz o "multi-day shoot" funcionar.** O manual promete que rodar de novo
num projeto existente encaixa a cena 4 shot 3 *entre* o shot 2 e o shot 4 já montados. Para
isso é preciso saber o que a execução anterior fez — e a resposta deles é **guardar no
projeto**, não num arquivo lateral. O estado viaja com o `.prproj`: sobrevive a copiar o
projeto, a mandar para outro editor, a abrir noutra máquina.

⚠️ **O Órbita não faz nada disso** (zero ocorrência de `XMPMeta`, `setProjectMetadata` ou
`kPProPrivate` no nosso `host.jsx`). É a pendência de desenho mais concreta que sai desta
análise, e ela vale para os três NLEs: *onde mora o estado de uma ingestão incremental?*

### 4.2 — `Column.Intrinsic.*` como fonte de metadado

`Column.Intrinsic.MediaStart`, `.MediaEnd`, `.MediaType`, `.MediaTimebase`,
`.AudioInPoint`, `.AudioOutPoint`, `.AudioDuration` — lidos via
`projectItem.getProjectMetadata()`.

São as **colunas do painel de projeto** do Premiere, acessíveis como metadado. Dá para
obter start/end/timebase de um clipe **sem tocar no arquivo em disco** e sem ExifTool. Não
usamos essa rota.

---

## 5. Negócio: licenciamento e distribuição

Terceiro ponto de dados para
[distribuicao-e-licenciamento.md](distribuicao-e-licenciamento.md).

| | |
|---|---|
| vendor de licença | **LicenseSpring** (`api.licensespring.com`), SDK `licensespring` 3.1.7 no Resolve; `node-machine-id` no Premiere |
| distribuição Premiere | `.zxp` instalado pelo **aescripts ZXP/UXP installer** (o manual instrui a baixá-lo) — mesmo canal que o Chat Video Pro usa |
| distribuição Resolve | `.pkg` (macOS) e Inno Setup (Windows), do próprio site |
| rede | ⭐ **só dois destinos**: `chopchopsystems.com` e `api.licensespring.com` |
| trial | "Try It Free" no site, upgrade por chave dentro do painel |

⭐ **O produto é local.** Nenhum endpoint de processamento, nenhum upload, nenhum bucket. A
mídia não sai da máquina — a rede existe só para validar licença. É o mesmo desenho de
privacidade do Órbita, e é um argumento que eles também podem usar; não é diferencial
nosso.

### ⚠️ Observações de segurança (para [`../../seguranca/`](../../seguranca/))

Registradas porque são o tipo de erro que **nós** podemos cometer, não para explorar:

1. **`ccsbrconfig.json` fica em claro ao lado do script**, com `skey`/`akey` do
   LicenseSpring e um par `fkey`/`fiv` que é chave + IV de AES fixos no produto. Chave
   simétrica embarcada é chave pública com passos extras.
2. **A ofuscação do script Resolve é XOR de byte único com a chave no arquivo** (`key =
   248`, base64, `exec`). Custa uma linha desfazer.
3. **`sudo installer` num `.pkg` movido para `/tmp`** durante o postinstall — `/tmp` é
   gravável por qualquer usuário; entre o `mv` e o `installer` há uma janela.

Nada disso foi explorado, e nada foi reportado a eles.

---

## 6. Como leem os nomes de arquivo

O agrupamento deles é **por nome do arquivo de áudio**, com episódio/cena/shot/take *nessa
ordem*. `parseFilename(filename, customSeparators)` no Resolve; separadores configuráveis
pela UI, com um segundo e um terceiro conjunto opcionais quando o primeiro falha.

O manual mostra a variedade aceita:

```
E10S6S4T3      EP10Sc6S4T3      10-6-4-3
E06S03S03T02   ep06Sc03Sh03T02  06_03_03_02
6-3B-3-2       6-3B-3C-2        6-4-8B-2
```

⭐ **A regra que sustenta o parser: "as long as there are no additional numbers".** Texto
livre antes dos identificadores é tolerado; qualquer outro número quebra. É uma restrição
honesta, e o produto oferece três saídas quando ela não vale — identificadores manuais,
identificadores adicionais, e uma pasta de descarte (`DAYS` no Resolve) para o que não deu
para ler.

⚠️ **E o que sobra:** o Resolve tem uma pasta `Episode None` para vídeo sem áudio
correspondente (drone, estabelecedora). Ou seja, **o não-agrupado é um resultado de
primeira classe**, não um erro. Vale para o nosso desenho.

Detalhes de tempo no Resolve, `confirmado`: o delta de timecode é embrulhado na
meia-noite (`DAY_FRAMES // 2`) e **zerado se passar de 120 s** (`MAX_TC_SKEW_SEC`);
clipes sem rótulo são agrupados por TC com tolerância de 3 s.

---

## ⚠️ A régua — o que NÃO foi feito

Seguindo [`../../transversal/analise-de-executaveis.md` §A régua](../../transversal/analise-de-executaveis.md),
registrado com a mesma clareza do que foi:

- **`js/main.js` (610 KB) não foi desofuscado.** Está protegido por `javascript-obfuscator`
  (array de strings + rotação, decodificador `_0x2607`). Recuperar as strings exigiria
  executar o decodificador deles. Não foi feito — o que se sabe do painel vem do
  manifesto, das dependências npm e do manual.
- **O JSXBIN não foi descompilado.** Foi decodificada **apenas a tabela de símbolos e
  strings** (1.235 identificadores únicos) — passos 7 e 8 da ordem de ataque. Nenhuma
  linha de lógica foi reconstruída; tudo nas §2 e §3 sobre o Premiere é `inferido` a partir
  de **nomes**.
- **O script do Resolve foi desembrulhado** (XOR 248 + base64) e lido, mas a análise saiu
  de um script que imprime **só nomes** — imports, classes, assinaturas, métodos CamelCase
  da API e literais de configuração. As constantes citadas (gaps, tolerâncias) foram lidas
  direto. **Os algoritmos de parse e de agrupamento deles não foram transcritos nem serão
  copiados.**
- **Nada instalado, nada executado, nenhuma conta criada, nenhuma licença tocada.**
- **O instalador Windows (Inno Setup) não foi extraído** — o payload macOS é o mesmo
  programa, e abrir os dois não acrescentaria fato.
- Temporários apagados ao fim (≈ 900 MB entre `.pkg`, `.zxp` e extrações).

---

## O que fazer com isto (proposta, não decisão)

1. ⭐ **Decidir onde mora o estado da ingestão incremental.** É a lacuna real que a análise
   expôs, e o XMP privado do projeto é uma resposta possível para o Premiere. Vale um ADR.
2. ⭐ **Não perder o argumento do sync.** O manual deles desaconselha forma de onda em
   multicâmera; o nosso motor não tem essa limitação. Isso é posicionamento de produto e
   deveria estar escrito em algum lugar que não seja este banco.
3. **A convenção de stringout (10 s / 2–3 s, som para cima, mic para baixo) é do mercado,
   não deles.** Se o Órbita monta stringout com outra convenção, é escolha — e convém ser
   escolha consciente, porque o editor que vem do Chop Chop espera esta.
4. **`Column.Intrinsic.*`** entra como alavanca nova em
   [api-extendscript.md](api-extendscript.md).
5. `pendente`: como a edição Premiere trata material **sem timecode comum** (a rota de
   media time exige TC coerente). Não deu para saber pelos nomes.

# msmMMOB.mdb — container Bento/OMFI

Apesar da extensão, **não é Microsoft Access**. O "MMOB" é *Media MOB* (banco de objetos de mídia
do MSM). O contêiner é **Bento** — o mesmo armazenamento de objetos da Apple usado pelo **OMF
Interchange (OMFI)**, e o mesmo dos bins Avid clássicos (pré-AObjDoc). Confiança: estrutura externa
**confirmada**; TOC interna e vocabulário **decodificados e validados** (2026-07-10) — leitura
programática de nome de clipe + MobID (+ caminho de arquivo em mídia AMA) sem tocar no header do MXF.
Leitor: [`eng-rev-bin-e-mdb/tools/mdb_read.py`](../../..); teste: `.../tests/test_mdb.py`.

## Por que importa

Ler o `.mdb` (100 KB–700 KB por projeto) dá **`MaterialPackage.Name` + MobID de todos os clipes de
uma vez**, sem abrir cada `.mxf` (na mídia Avid é long-GOP de 1 GB+; abrir só pra ler o header é
caro). O [`.pmr`](pmr-fmid.md) irmão dá MobID + tape + filename, mas **não** o nome específico do
clipe — é o que o `.mdb` acrescenta. Em mídia **AMA**, o `.mdb` traz ainda o **caminho POSIX do
arquivo de origem** (`OMFI:FL:POSIXPathName`), útil pra relink.

## Como se reconhece

- Começa direto com strings de conteúdo (`PRODUCAO-A`, `Comment`, `Created by Resolve`, `_USER`),
  sem o magic `Domain` do `.avb`.
- Os fourcc de classe aparecem **direto, não invertidos** (`MOBJ`, `SEQU`, `ATTR` — e **zero**
  `OBJD`/`JBOM`). → não é AObjDoc.
- Nomes de propriedade no estilo **OMFI**: `OMFI:CPNT:Name`, `OMFI:MOBJ:MobID`, `OMFI:FL:POSIXPathName`,
  além de atributos Avid (`_USER`, `_VERSION`, `_SAVED_AAF_PHYSICAL_TRACK_NUMBER`).
- **Label Bento de 24 bytes no FIM do arquivo** (assinatura `A4 43 4D A5 48 64 72 D7` = `¤CM¥Hdr×`).

## A label Bento (final do arquivo) — confirmado

Os 24 bytes finais (ver [dados/bento-label.json](dados/bento-label.json)):

```
a4 43 4d a5 48 64 72 d7   magic  ¤CM¥Hdr×
00 00                     flags
49 49                     "II" = little-endian
01 00 00 00               version = 1
90 73 00 00               toc_offset = 29584
e0 60 01 00               toc_size   = 90336
```

Verificação que fecha exato: `toc_offset(29584) + toc_size(90336) + 24 = 119944` = tamanho do
arquivo. **Dados no início (0..29584), TOC no fim (29584..119920), label nos últimos 24 bytes.**

## TOC: registros fixos de 24 bytes — confirmado

`toc_size / 24` é inteiro exato (90336/24 = 3764 registros). Cada entrada:

```
u32 objID   +   u32 propID   +   u32 typeID   +   valor(12)
```

O `valor` de 12 bytes é `offset(u32) + length(u32) + flag(u32)`:

| flag | significado | onde está o valor |
|---|---|---|
| `0x00000001` | **referência** | `data[offset : offset+length]` (região de dados, `0..toc_offset`) |
| `0x00010001` | **imediato (inline)** | primeiros `length` bytes do próprio campo valor |

Ex. imediato: `OMFI:MOBJ:_CreationTime` = `af dd 26 65 | 04 00 00 00 | 01 00 01 00` → long inline
`0x652626dd` = 1697045935. Ex. imediato string: `54 43 31 00 | ...` = `"TC1"`. Só esses dois valores
de flag aparecem em todas as amostras (histograma bate 100%).

## Dicionário auto-descritivo (a "pedra de roseta") — confirmado

O vocabulário inteiro sai lendo a própria TOC — **nada é hardcoded**. Os próprios `propID`/`typeID`
usados nos registros de dados são objIDs cujo nome está registrado na TOC, via dois propIDs
"bem-conhecidos" do Bento (`< 0x10000`):

- **propID 23** = "nome do tipo": objetos `65600..65760` definem os tipos primitivos OMFI.
  Ex.: `omfi:String`=65680, `omfi:Long`=65640, `omfi:ObjRef`=65655, `omfi:ObjRefArray`=65660,
  `omfi:UID`=65695, `omfi:VarLenBytes`=65720, `omfi:ExactEditRate`=65625, `omfi:TrackType`=65690.
- **propID 24** = "nome da propriedade": objetos `66000+` definem as propriedades namespaced OMFI.
  Ex.: `OMFI:ObjID`=66060, `OMFI:CPNT:Name`=66205, `OMFI:MOBJ:MobID`=66350,
  `OMFI:SourceMobs`=66070, `OMFI:FL:POSIXPathName`=66274, `OMFI:MACL:FileName`=66270,
  `OMFI:SCLP:SourceID`=66390.

A amostra `1/` tem 37 defs de tipo e 719 defs de propriedade — todas lidas automaticamente.

## Classe do objeto e mobs

A propriedade `OMFI:ObjID` (propID 66060, tipo `omfi:ObjectTag`) guarda a **tag de classe fourcc
inline** nos 4 primeiros bytes do valor. Classes vistas: `MOBJ` (mob), `SEQU`, `SCLP`, `TRAK`,
`FILL`, `ATTR`/`ATTB`, `CLSD` (class dictionary), `MDES`, `MSML` (MSMLocator, mídia Avid nativa),
`MACL` (Mac file locator, mídia AMA), `PCMA`, `TCCP`, `MDTP`, `MCBR`, `HEAD`.

Um **mob** = objeto com `OMFI:ObjID == 'MOBJ'`. Dele lemos:
- `OMFI:CPNT:Name` (`omfi:String`) → nome do clipe (= `MaterialPackage.Name`).
- `OMFI:MOBJ:MobID` (`omfi:UID`, 32 **ou** 12 bytes — ver §MobID) → MobID.
- `OMFI:MOBJ:UsageCode` → primeiro byte `0x07` no **master clip** (a "linha da bin");
  `0x00` nos mobs de fonte/fita da cadeia. É o filtro pra listar os clipes da bin.

**Duas cópias do grafo (confirmado):** o `.mdb` guarda o grafo de mobs **duplicado** — uma
cópia "atual" e uma anterior; os dois master mobs de um mesmo clipe têm o **mesmo MobID**
(ex.: na amostra `1/`, objs 68050 e 68319). Por isso, ao listar clipes, **deduplica-se por
MobID**; ao seguir a cadeia de origem, aceita-se qualquer objeto com aquele MobID (a segunda
cópia costuma ter nomes preenchidos que a primeira deixa vazios, ex.: o nome da fita).

## MobID: OMFI (GUID little-endian) vs SMPTE UMID (big-endian) — confirmado

O `.mdb` grava o "material number" do MobID (bytes 16..31 dos 32) em layout **GUID little-endian**;
o header MXF e a AAF gravam em **big-endian SMPTE**. A conversão inverte os 3 primeiros campos do
GUID — Data1(4), Data2(2), Data3(2) — e mantém Data4(8):

```
.mdb : 060a2b34 01010105 01010d43 13000000 | afdd2665 2104 0000 | 060e2b34 7f7f2a80
MXF  : 060a2b34 01010105 01010d43 13000000 | 6526ddaf 0421 0000 | 060e2b34 7f7f2a80
                                              └Data1 rev┘ └D2 rev┘
```

PRODUCAO-A validado contra o header real (`PRODUCAO-A - 05-04 C11 P1-T002_A01.mxf` via pyaaf2):
name **idêntico** e mobid **idêntico** após a inversão. Ver `tests/test_mdb.py`.

**MobID de 12 bytes (OMFI legado) — confirmado (2026-07-10):** nem toda mídia grava o MobID
de 32 bytes. Em mídia mais antiga (ex.: `Avid MediaFiles/MXF/009/` real, câmeras `A001…`
MPEG-2), o `OMFI:MOBJ:MobID` (e o `OMFI:SCLP:SourceID`) têm **12 bytes** — o MobID OMFI
clássico (`3×u32`). Não há material-number/GUID pra inverter; usa-se o hex como identidade
estável (`format_mobid`: 32→UMID SMPTE, 12→hex). **Importante:** um leitor que aceite só 32
bytes rejeita esses mobs e a bin sai **vazia** — foi um bug real do app até 2026-07-10.

## Colunas de bin (Name/Start/Duration/Tape/Video) — confirmado (2026-07-10)

Pra reproduzir o que o Avid mostra por **master clip** (uma linha da bin) é preciso percorrer o
grafo de composição OMFI dentro do `.mdb`. Validado contra a `Avid MediaFiles` real (as linhas
batem com a bin do Media Composer). Cada coluna:

| Coluna | Como obter |
|---|---|
| **Name** | `OMFI:CPNT:Name` do master mob |
| **Duration** | `OMFI:TRKG:GroupLength` (frames) ÷ edit rate → TC. Edit rate em `OMFI:CPNT:EditRate` = `num(u32)/den(u32)`, gravado como **`23976/1000`** (não `24000/1001`) |
| **Start** | `OMFI:TCCP:StartTC` (frames) + `OMFI:TCCP:FPS`, do componente de timecode alcançável na cadeia → TC |
| **Tape** | nome (`OMFI:CPNT:Name`) do mob **mais fundo** na cadeia de origem (o mob de fita); o master e o clip-mob repetem o nome do clipe, a fita fica no fim (ex.: `msmMMOB.01`, ou o reel da câmera) |
| **Video** | do descritor físico: `OMFI:DIDD:StoredWidth`×`StoredHeight` + `OMFI:DIDD:DIDResolutionID` (→ nome "Avid DNx…") ou `OMFI:DIDD:Compression` (fourcc, ex. `RI00`=raw AMA, `MPG2`). Áudio não tem → coluna vazia |

**A cadeia de origem** (grafo de composição, percorrido por BFS deduplicando por MobID):

```
master MOBJ (UsageCode 0x07)
  └ OMFI:TRKG:Tracks[]            (omfi:ObjRefArray: count u16 + N×8 bytes; obj id = u32)
      └ TRAK · OMFI:TRAK:TrackComponent  (omfi:ObjRef: obj id = u32)
          └ SEQU · OMFI:SEQU:Sequence[]  → SCLP
              └ SCLP · OMFI:SCLP:SourceID (MobID) → próximo mob na cadeia … até a fita
  └ OMFI:MOBJ:PhysicalMedia → descritor (CDCI/DIDD vídeo, PCMA áudio)
```

Descritores por classe: **PCMA** (áudio PCM: `MDAU:NumChannels`, `MDAU:BitsPerSample`,
`PCMA:AudioSamplingRate`), **CDCI**/**DIDD** (vídeo: `StoredWidth/Height`, `Compression`,
`DIDResolutionID`, `FrameLayout`), **MSML** (locator de mídia Avid nativa), **MACL** +
`OMFI:FL:POSIXPathName` (locator + caminho de origem de mídia AMA).

## Implementações

- **Canônica (leitura):** `eng-rev-bin-e-mdb/tools/mdb_read.py` (`read_mdb`, `list_mobs`,
  `bin_clips`) + `tests/test_mdb.py`. stdlib pura.
- **Porte Rust (app):** `LEITOR DE MDB/frontend/src-tauri/src/mdb.rs` — reimplementação
  independente que **validou o formato** varrendo uma `Avid MediaFiles` real inteira (6 bins,
  <0,2s cada) e batendo com a bin do Media Composer. Guardas de profundidade (SEQU cíclico não
  derruba o leitor).

## Ainda em aberto (não bloqueia leitura)

- Round-trip de **escrita**/edição do `.mdb` (reindexar a TOC, recomputar offsets) — só a leitura
  está confirmada.
- Etiqueta de **cor** do clipe (a coluna Color da bin) ainda não localizada no `.mdb` (deve estar
  num atributo `ATTB`/`_USER`).
- Mapa `DIDResolutionID` → "Avid DNx…" cobre só os IDs comuns; IDs como `4073` (MPEG-2/XDCAM) e o
  fourcc `RI00` (raw AMA) aparecem como estão.
- Alguns tipos de valor (`omfi:AttrKind`, arrays de posição) ficam como HEX — fora do caso de uso.

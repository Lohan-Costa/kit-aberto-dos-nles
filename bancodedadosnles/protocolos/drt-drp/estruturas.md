# DRT/DRP — Estruturas

O DRT/DRP é `zip(XML)` com **blobs binários** (`*BA`). Os dois blobs decifrados até agora —
ambos do clipe — carregam velocidade e transform. Confiança `confirmado` onde indicado.

---

## 1. `MediaTimemapBA` — velocidade (constante e rampa)

A velocidade (constante OU rampa) vive no `MediaTimemapBA` do clipe. Modelo: **curva Bézier 2D**
em `(X = saída_seg, Y = fonte_seg)`, com `slope dY/dX = velocidade`. Cobre a **mídia inteira**;
o clipe janela nela via `Start`/`Duration`.

```
MediaTimemapBA (map):
  YMax            = duração da FONTE em segundos
  XMax            = duração da SAÍDA retimed em segundos
  LastValidYOffset= YMax
  DbType          = "Sm2TimeMap"
  KeyframesBA (map "0".."N"): keyframe =
      X, Y                  → tempo de saída / tempo de fonte (segundos)
      interp                → 0 linear | 1 bézier
      XIn,YIn / XOut,YOut   → handles (offset em segundos)
```

- **Constante:** 2 keyframes lineares `(0,0)` e `(Xmax,Ymax)`, `slope = 1/speed_ratio`.
- **Rampa:** vários keyframes (validado vs gráfico do Resolve, 2026-06-13).

### Tradução do AAF
O `source_offset_map` `[(tl_frame, src_frame)]` do AAF **já é essa função**, em frames. Converter
`X = tl_frame/fps`, `Y = (source_start + src_frame)/fps`. Recomendado emitir **keyframes lineares
densos** (Douglas-Peucker no offset map) — frame-exato e à prova de freeze/reverse/rampa-aparada.

Schema consumível: [dados/timemap.json](dados/timemap.json).

⛔ CORRIGE o "frame-exato" acima (2026-10-12, laboratório B22, Resolve 19.0.0b Windows; render × render pelo código de
barras): o Resolve mostra o quadro da fonte = **PISO** da curva no instante do quadro (frações 0,5–0,95 vão para baixo).
O modo "adaptive" do app (`build_adaptive_ramp_timemap`, Douglas-Peucker com **`tol_frames=0.5`**) desvia a curva até
meio quadro → com o piso, quadros errados: Avid → Resolve e Premiere → Resolve davam **43/48** (constante → curva →
constante) e **39/48** (começa na curva). Com 0,01 ainda sobra um caso: o ponto (14; 14,0) foi descartado porque a reta
passava a 0,006 dele (13,994 → quadro 13). **A forma EXATA, medida 48/48 nos dois sentidos e nos dois casos**:
(1) só os quadros INTEIROS da timeline (os meios quadros do mapa do Avid não servem); (2) Douglas-Peucker com
`tol_frames=1e-4` = só junta pontos COLINEARES (o trecho constante continua com 2 pontas — a regra do autor: só a curva
quadro a quadro); (3) **+0,001 quadro** no Y, para dentro da célula (contra o fio de arredondamento num Y inteiro).
O `_pad_to_header_n` (N ∈ 2, 4, 6, 13, 14, 22, 30, 37, 159) completa com colineares — coube. ✅ CORRIGIDO no app
(ramo `rampas`, 2026-10-12; `tests/test_rampa_exata_drt.py`). ⛔ E mais um: a rampa do AVID ia com `In` 0 e a curva
forçada a nascer em (0, 0) — com o clipe começando no quadro 80 da mídia, 28/48 (o 1º quadro mostrava o 0). Agora a
mesma ENTRADA da rampa do Premiere (de (0, 0) a 100 % até o in da fonte; o clipe começa ali) → 48/48 (LAB_RAMPA_N1). Velocidade CONSTANTE com Optical Flow (FluidMotion no Avid,
`TimeInterpolationType 2` no Premiere): o DRT não pede o retime do Resolve (`RETIME_*`, paramID 0x5B) — o Resolve mostra
o piso nas posições x,5 onde os outros sintetizam (pendente).

⭐ **Como o Resolve CALCULA a curva (o LEITOR do lado Resolve) — `confirmado` 2026-10-12, B22, Resolve 19.0.0b Windows:**
o keyframe `interp 1` (a transição suave que a interface grava; gabarito `03 CASOS/TEMPO/V01 …/TL COM VELOCIDADES
EXEMPLOS parecido com aaf 01.drt`, alças ALINHADAS às retas vizinhas: YIn/XIn = velocidade de antes, YOut/XOut = a de
depois) **NÃO passa pelo ponto gravado — ARREDONDA O CANTO**: reta até a ponta da alça de entrada (kf − (XIn, YIn)),
**Bézier cúbica** dela até a ponta da alça de saída (kf + (XOut, YOut)) com os **dois controles internos no próprio
keyframe**, e reta de novo. Quadro mostrado = PISO. Medido: 1,2× → kf Bézier (alças de 8 q) → 1,9× e 2× → 0,6× com o
In DENTRO da curva → **48/48 e 48/48**. A hipótese "Bézier entre keyframes com as alças como controles" errava até 2
quadros perto do keyframe (no B, no próprio keyframe, a curva passa 1,4 quadro ABAIXO do ponto). `In` = X em quadros
da timeline. `pendente`: alças NÃO alinhadas (não vistas). Bancada: `laboratorio-de-midia/lab/bancadas/resolve_rampas.py`
(`avaliar_resolve`).

---

## 2. `EffectFiltersBA` — transform / crop / composite

Blob protobuf-like com doubles f64 LE. **Decodificado e escrito byte-exato**, validado no
Inspector (2026-06-14).

```
header: [u32 ver=2][u32 len][0x80][filtros]
filtro: 0a <varint len> 08 <tipo> 38 <campo7> <N slots>
slot setado (double): 4a 0f 08 <paramID> 1a 0b 0a 09 11 <double LE>
slot vazio:           4a 00
```

| filtro | tipo | params (paramID) |
|---|---|---|
| Transform | 4 | zoomX `0x2a`, zoomY `0x2b`, aspect `0x2c`, posX `0x28`, posY `0x29`, rotation `0x2f`, pitch `0x2d` (slot 8), yaw `0x2e` (slot 9), flipX `0x32` (slot 10), flipY `0x33` (slot 11) — os quatro últimos medidos no 21.1 (2026-10-02/03) |
| Crop | 6 | cropL `0x36`, cropR `0x37`, cropT `0x38`, cropB `0x39` |
| Composite | 2 | opacity `0x01` |
| Flip/Flop | 8 | (pendente — o Flip do Inspector mora no Transform, acima) |
| Anchor | — | id `0x30`, encoding 2D próprio (pendente) |

Posição no Resolve é **fração** (`posX = px/largura`, `posY = px/altura`, +Y cima) — por isso é
resolution-independent. Schema + conversões Avid→Resolve: [dados/effectfiltersba.json](dados/effectfiltersba.json)
e [../../transversal/modelo-neutro-efeitos.md](../../transversal/modelo-neutro-efeitos.md).
⛔ CORRIGE (2026-10-10, `confirmado` pela imagem, Resolve Studio 19, Windows, R04): com fonte **LETTERBOX no encaixe**
(mais larga que o quadro: o proxy 1024×540 numa timeline 1920×1080 ocupa 1012,5 px de altura), o posY anda em unidades
da imagem ENCAIXADA — para mover N px do quadro, `posY = N/altura × altura/altura_encaixada` (× 1,0667 aqui). Medido por
correlação de fase, render × referência do Premiere: Tilt 109 e 171 px saíam 7 e 11 px curtos; com o fator, 5 planos de
6–12/255 a ~1,6. posX não muda (a largura enche). ⏳ O espelhado (fonte mais estreita → posX?) não foi medido.
De Lá Pra Cá: `prproj/leitura.py` (`fy`, no `_segmento`). ⚠️ Quem escreve posY de Avid → Resolve tem a mesma armadilha.

---

## 3. Tracks, cortes e relink

- Clipe → referência externa ao **arquivo original** + `source_range`
  (`source_start_frames`/`duration_frames`) → o Resolve religa a mídia.
- Convenção de tempo: **NOMINAL** (`round(fps)`, non-drop).
- Estado: writer com cortes + relink + TC em V1 a 100% validado; áudio/V2/V3 e geração do
  pool/project do zero em curso. Multicam nativo: a avaliar.

### ✅ VALIDADO NO RESOLVE pelo autor (2026-09-24, Resolve Studio 19, Windows)

`_DeLaPraCa/saidas/TESTE_PRODA_R19_GERENCIADA.drt` (curta, gerado da bin, esqueleto do 19):
**abriu no Resolve 19 sem mídia pré-importada e trouxe a mídia gerenciada ONLINE** — vídeo e
som, cada trilha na sua `.mxf` (ver `../msm/pmr-fmid.md` §10). Promove a `confirmado`: o
esqueleto do 19, o pool de pasta única, o `FieldsBlob` zstd do áudio, o `MediaStartTime` na
taxa exata e o som gerenciado em MXF mono lido no canal 1.

Ainda `pendente`: (1) abrir no Resolve mais novo do Mac (versão não informada; o DRT do
esqueleto 20.3 "não deu sinal de vida" lá, sem erro); (2) religar os clipes OFFLINE aos
originais (nome sem extensão? TC?); (3) a regra de arredondamento do In em clipe conformado
que começa em transição (+1 frame no nativo, 3 casos).

**CORRIGE (2026-09-26), sobre o item (2):** o De Lá Pra Cá não religa no Resolve: gera o DRT já
apontado para os originais. Com o formato do item certo (§"O item do pool declara o FORMATO",
abaixo), o Resolve usa o `MediaStartTime` e o trecho pedido, e os clipes entram online nos
frames certos (PRODA_CORTE, 841 clipes). O relink de clipe OFFLINE pelo próprio Resolve continua
não medido.

### Clipe OFFLINE no DRT — o original está com quem recebe (2026-09-24, `hipotese` no Resolve)

Fluxo real (autor): quem edita offline tem só mídia GERENCIADA do Avid; manda a timeline ao
colorista, que tem os originais e religa no Resolve. Então todo clipe precisa chegar,
mesmo sem arquivo nesta máquina. `_DeLaPraCa/motor/drp/writer.py::build_drt(offline=…)`:

- `MediaFilePath` = o original: `Source Path`+`Source File` do Media Composer quando ele
  sabe (traz a EXTENSÃO); senão a pasta do DRT + o nome do arquivo de câmera lido da `.avb`
  (sem extensão). `MediaReelNumber` = esse nome.
- `MediaStartTime` = TC de câmera do início do original (lido da `.avb`, ver
  `protocolos/avb/estruturas.md` §"Quem é o ORIGINAL"); blob `<Time>` do pool com esse TC e
  a duração; o `ffprobe` não roda (os metadados entram pelos caches do writer).
- Um clipe no pool por ORIGINAL; masters do mesmo original com início diferente deslocam o
  In, de modo que `MediaStartTime + In` = TC de câmera do ponto de entrada (verificado em
  844 + 642 clipes de duas timelines reais: 0 violações).
- Nenhum `stat` no caminho offline (pode ser UNC vindo do Avid → SMB).

**2026-10-06 — regra do autor, para TODO protocolo e NLE: nenhum segmento se perde.** O caminho do
`.prproj` (`tools/prproj_para_drt.py::montar`) pulava o plano sem arquivo (só marcador): um projeto sem
mídia no disco virou timeline VAZIA no Resolve 19 (Windows). Agora usa o MESMO `build_drt(offline=…)`:
`MediaFilePath` = o caminho que o projeto declara, `nb` = a duração da fonte do projeto (ou a ponta
pedida), `fps` da fonte, `tc` = nenhum (o In do Premiere é contado do início do arquivo), som a 48 kHz
com os canais = o maior `canal_arquivo`. Medido no gerador: `repórter global_2025.prproj` sem mídia →
85 planos de vídeo + 170 de áudio no DRT, 85 itens no pool (antes, 0). O caminho do Avid ganhou o
master mínimo para o clipe cujo master a leitura não trouxe (`montar_midia`). ⏳ No Resolve: abrir e ver
os 255 offline no lugar, e religar por pasta.

⚠️ **Não validado no Resolve** — `pendente`, e é a próxima medição: (1) o DRT abre com os
clipes offline no lugar certo? (2) *Relink* por pasta casa pelo nome **sem** extensão?
(3) o Resolve usa o `MediaStartTime` (TC) ao religar a um arquivo com início diferente?
Arquivo de teste: `_DeLaPraCa/saidas/TESTE_PRODA_OFFLINE.drt` (curta, 118 originais).

⭐ Portado do DRAMASYNC para a cópia do `_DeLaPraCa` na mesma data: `MediaTrackIdx =
canal − 1` (a linha abaixo). A cópia ainda tinha `track − 1000` — o banco já sabia.

### ⛔⛔ VERSÃO do DRT, e o gabarito do Resolve 19 — `confirmado` 2026-09-24

Gabarito: `D:\DeLaPraCa_MIDIAS E PROJETOS DE TESTE\03 CASOS\REAL\R01 PRODA_CORTE\resolve\PRODA_CORTE…drt` — a timeline
do curta importada por AAF no **Resolve Studio 19.0.0b (Windows)** e exportada como DRT pelo
autor. Comparado clipe a clipe, pareando por (trilha, Start), com o DRT gerado da bin:

| fato | medido |
|---|---|
| ⛔ o cabeçalho decide quem abre: `<!--DbAppVer="19.0.0b.0059" DbPrjVer="14"-->` | o Resolve 19 RECUSA `DbPrjVer="15"` (esqueleto do 20.3) com "feito numa versão mais nova". ⇒ gerar sobre o esqueleto da versão MAIS ANTIGA a atender |
| pool do `.drt` do 19 = UMA pasta (`MediaPool/Master/MpFolder.xml`), e o `Sm2MpTimelineClip` mora no MESMO `MediaVec` dos clipes | trocar o `MediaVec` inteiro apagava a timeline — é a causa provável de "os .drt como esqueleto NÃO importavam a timeline" (nota do `make_skeleton` do RELINKER, nunca registrada aqui) |
| `FieldsBlob` do `Sm2TiAudioClip` no 19: flag `0x81` = protobuf comprimido com **zstd** (~200 B); no 20.3 é `0x80` cru e minúsculo | ler `0x81` como cru → "wire type 7" |
| `MediaStartTime` = frames de TC ÷ taxa **exata** (24000/1001), não 23,976 | 5513,9668 × 5513,9723 s: 0,13 frame |
| clipe de SOM desligado no Avid → `Flags=2`; clipe de VÍDEO desligado → **não é importado** | A1 do curta; V2 em 105629 |
| resultado, depois de acertar o acima: **19 trilhas, mesma contagem de clipes e transições; vídeo 108/108 idêntico** (Duration, In, MediaStartTime a 1e-6, taxa) | `_DeLaPraCa/tests/test_drp_windows.py`, script de comparação na sessão |

Diferenças que ficam, e por quê:
- `MediaTrackIdx` do áudio: o nativo aponta cada canal para uma MXF MONO gerenciada (idx 0); o
  export aponta o ORIGINAL polifônico (idx = canal − 1). Proposital — `pendente` de conferir no
  Resolve depois de religar aos originais.
- ⚠️ In com +1 frame no nativo em 3 efeitos sonoros com conformação 24→23,976 que COMEÇAM
  numa transição (`RESPIRAÇÃO_2`: fonte 232, corte 12 → nosso 244, nativo 245). O Resolve
  conta o In em frames da MÍDIA; o writer, em frames da timeline. Três amostras não bastam
  para cravar o arredondamento — `pendente`.
- `MediaFrameRate` do áudio de efeitos: o nativo põe a taxa do arquivo (24/25); a regra não é
  óbvia (o som direto, com TC a 24, sai 23,976 no nativo) — `pendente`, provavelmente
  informativo para áudio.
  ⛔ CORRIGE (2026-10-08, Resolve 21.1, macOS): **NÃO é informativo — o Resolve TOCA o áudio por ela.**
  O som da referência do PRODB (mp4 a 24, 88 min) com `MediaFrameRate` 23,976 (herdada do molde) ia
  0,1% mais lento: começava junto e terminava ~5 s antes do bipe final; o mesmo arquivo posto à mão veio
  com 24 (DRT exportado da timeline, os dois lado a lado). Em clipe curto não se ouve. A regra do import
  do Resolve: a taxa do VÍDEO do arquivo; arquivo só de áudio = a do projeto (um WAV importado num
  projeto a 24 → FPS 24; o som direto a 23,976 do nativo acima é isso). De Lá Pra Cá:
  `writer._make_audio_timeline_clip`, `tests/test_audio_taxa.py`. Ficha B001 em
  `transversal/bugs-do-mundo-real.json`.

Esqueleto gerado por `_DeLaPraCa/motor/tools/make_skeleton.py` (porte do RELINKER com o
clipe da timeline preservado e higiene de caminho do Windows) → `motor/drp/skeleton_r19.drt`.

### ⛔⛔ O item do pool declara o FORMATO do arquivo — e o Resolve decodifica pelo que está declarado — `confirmado` 2026-09-26

**Resolve Studio 19.0.0b (Windows).** O Resolve NÃO sonda o arquivo ao abrir o DRT: ele escolhe
o decodificador pelo que o item do pool (`Sm2MpVideoClip` / `Sm2MpAudioClip`) declara. Um item
que declara o formato errado fica **Media Offline**, mesmo que o arquivo exista no caminho
certo, com o TC e a duração certos.

**Como apareceu:** o relink aos originais do De Lá Pra Cá (ADR 0020) gerava um DRT com os .mp4
da PRODA_CORTE. Cada item era clonado da forma do esqueleto, que veio de uma MXF gerenciada do
Avid. Parte dos clipes abria e parte ficava offline. O padrão era a resolução: a forma dizia
2048×1080, e só os mp4 da câmera B (2048×1080) abriam; os da A e os do drone (1920×1080), não.
O log do Resolve (`%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\logs\davinci_resolve.log`)
deu a causa: `IOVideoDecoderFacade can not decode file A001_….mp4 of type MXF OP-Atom`, e o
mesmo para os .wav (`clipFormat: MXF OP-Atom`). ⭐ **O log do Resolve é a primeira parada** para
Media Offline sem motivo aparente: ele diz o formato em que tentou abrir.

**Onde mora — blob `<Clip>` (zstd → protobuf) de cada `BtVideoInfo` / `BtAudioInfo`:**

| campo | significado | MXF OP-Atom (gerenciada) | mp4 H.264 | WAV |
|---|---|---|---|---|
| 15 | ⭐ **formato do arquivo** | `4` | `2` | `2` |
| 18 | flag do item | `16388` | `16384` (vídeo e o áudio embutido dele) | `32768` (áudio puro) |
| 5 | codec | `dnxhd_lb` | `avc1` (vídeo) · `AAC` (áudio embutido) | `Linear PCM` |
| 16 | — | `100` | `100` | `100` |

Mais o que vive fora do `<Clip>` e também tem de ser o do arquivo:
- `<Geometry>`: `Resolution` = 2 × u64 BE (largura, altura) depois de `[u32 12][u8][u32 16]`, e
  `FrameSize` = i32 proporcional aos pixels (12182 em 1920×1080 e 13000 em 2048×1080, H.264 4:2:0).
- `<Time>`: `FrameRate` = f64 LE depois de `[u32 12][u8][u32 16]`.
- `EmbeddedAudioVec`: o mp4 tem **um** `BtAudioInfo` (AAC estéreo, `TracksBA` sem `MXFMetadata`);
  a forma MXF trazia dois, "Linear PCM", com `tapeMobId`/`sourceMobId`/`masterMobId`.
- `UniqueId` (uuid em UTF-16BE) de `<Time>`, `<Geometry>`, `<Proxy>`, `<VideoMetadata>` e
  `<TracksBA>`: um por item. Clonar a forma sem trocá-los deixava todos os itens com os mesmos.
- `ActualReelNumber` do `<VideoMetadata>`: a forma trazia `B001_03150131_C011` (a mídia de
  onde ela veio) em todo item.

**⛔ Armadilha de versão:** nos DRTs do **Resolve 20.3** (Mac) com os mesmos mp4, o campo 15 vale
`4`. O significado do campo mudou entre as versões, ou o 20.3 numera diferente. Usar um DRT do
20.3 como gabarito do 19 levou a uma correção que não funcionou (variantes A–C,
2026-09-26). Gabarito do formato = DRT exportado **pela mesma versão** que vai abrir.

**Correção (De Lá Pra Cá, `motor/drp/writer.py`):**
- item de vídeo não-MXF nasce da forma NATIVA do 19 (`motor/drp/formas_r19.xml`, exportada pelo
  autor com `A001_03170345_C005.mp4` e um WAV do som direto), com o codec, a resolução, a taxa,
  o TC, o áudio embutido e os UniqueIds de cada arquivo;
- áudio puro segue na forma do esqueleto (o writer sabe redimensioná-la em canais), só com o
  formato corrigido (15 = 2, 18 = 32768);
- `.mxf` segue na forma do esqueleto, intocada.

Validado pelo autor no Resolve 19 (2026-09-26): a PRODA_CORTE inteira, 841 de 877 clipes nos
originais (.mp4 das câmeras A e B, drone, WAV do som direto, efeitos AIF/WAV), abriu com imagem
e som. Trava: `_DeLaPraCa/tests/test_drt_formato.py`. Constantes:
[dados/clip-formato.json](dados/clip-formato.json).

**BRAW (2º gabarito, mesmo dia, `confirmado`):** com a forma do mp4 o Resolve ABRIA o .braw mas
recusava os quadros (`Failed to decode clip <…BRAW>, track 0, frame 1209: Requested position is
outside of track bound`). O item nativo do BRAW (Pocket 4K) tem:
- campo 15 = `2`, **campo 18 = `16406`** (vídeo e áudio embutido), **codec `BRAW`** (não o
  fourcc `brst` que o ffprobe dá);
- `<Geometry>` com a resolução **útil**: 4096×2160 (câmera B) e 3840×2160 (câmera A). O ffprobe
  dá a gravada, 4128×2176 e 3872×2176. A útil está no arquivo, na chave `crop_size` (2 ×
  float32 BE) dos metadados QuickTime (`moov/meta`, chaves `mdta`);
- `<Radiometry>` de 142 bytes com os metadados RAW da câmera (modelo "Blackmagic Pocket
  Cinema Camera 4K" e valores que variam por clipe, provavelmente balanço de branco, tint e
  ISO); o item não-RAW tem 25 bytes;
- áudio embutido "Linear PCM" (PCM 24 bits), sem `ChannelLayout`.
Com a forma BRAW nativa, as duas variantes (o `Radiometry` do gabarito em todos os clipes, ou o
genérico) abriram com imagem, e o autor disse que o Camera RAW funcionou. **Não ficou medido se
o balanço de branco e o ISO exibidos são os de cada clipe** — `pendente`.

**Item de ÁUDIO puro nativo (WAV/AIF), por número de canais — `confirmado` 2026-09-26**, lido
no `Project.db` dos itens que o Resolve 19 criou ao importar os arquivos. O `f1.f5` do
`FieldsBlob` é um mapa Qt (`[u32 1][u32 n]` + pares chave/QVariant; ver
`_DeLaPraCa/motor/drp/ba_mapa.py`), com UMA `BtAudioInfo` (trilha) por item:
| arquivo | registros no `FieldsBlob` |
|---|---|
| 1 canal | "0": `SampleRate` (só se ≠ 48 kHz), `MediaExtents`, `CodecName`, `ChannelVecBA`{"0": MediaRef}, `BitDepth` |
| 2 canais | "0": `Type`=0, `SampleRate` (só se ≠ 48 kHz), …, `ChannelVecBA`{"1": MediaRef+ChannelIdx 1, "0": MediaRef}, `BitDepth` |
| ≥3 canais | "n-1"…"0", um por canal: `ChannelVecBA`{"0": MediaRef + ChannelIdx k}; no canal 0, sem ChannelIdx |
- `BitDepth`: 16 bits → 1, 24 → 2, 32 float → 3. No float, o registro não leva `BitDepth`; a
  trilha leva.
- `<TracksBA>`: `ChannelLayout` só no mono (1) e no AIF (2). `StartTime` = segundos do bext;
  sem bext, 0.
- Flag do campo 18 do `<Clip>`: WAV 32768, **AIFF 32770**. O padrão se repete: a flag carrega o
  container (MXF +4, AIFF +2, BRAW +22).
- O item do esqueleto (5 trilhas mono, de uma MXF gerenciada) só corrigia o `MediaExtents` da
  1ª trilha; as outras 4 ficavam com o TC da forma (11:42, 8m43s), e era isso que o Resolve
  mostrava no pool.

**Arquivo SEM timecode (`confirmado`):** o .MOV do drone DJI (HEVC 10 bits, sem trilha de TC)
fica Media Offline se o DRT declarar outro TC. O Resolve o conta de 00:00:00:00. O writer
herdava o TC da forma e o da timeline-modelo. Com `00:00:00:00`, abriu (variante F).

Ainda `pendente`:
- outros containers de vídeo (R3D, ARRI, Sony MXF XAVC/X-OCN, Canon CRM): que forma o
  Resolve grava? Hoje só a `.mxf` fica com a forma MXF, e só o DNx dela é medido. O HEVC em
  .MOV (fourcc `hvc1`) abriu com a forma do mp4;
- áudio com a mídia pré-importada: no teste G os áudios duplicaram no pool; no F, o autor
  relatou áudio tocando certo, com duplicata no import (relato ambíguo). Não se sabe se o
  Resolve reaproveita o item de ÁUDIO puro como faz com o de vídeo;

**⭐⭐ Mídia PRÉ-importada: o Resolve reaproveita o item de VÍDEO que já está no pool — `confirmado`
2026-09-26 (Resolve Studio 19.0.0b, Windows).** Teste G: DRT propositalmente quebrado (todos os
itens na forma MXF/DNx, apontando para .BRAW e .MOV HEVC), importado num projeto em que o autor
tinha arrastado antes a pasta dos originais para o Media Pool. Todos os clipes de vídeo abriram
com imagem, e **nenhum item de vídeo duplicou**: o Resolve ligou a timeline aos itens que ELE
criou, ignorando o formato que o DRT declarava. Consequência: com a mídia importada antes
(como o Avid faz, mídia primeiro e timeline depois), o mapeamento de codec fica com o Resolve,
e as formas por família do writer viram só uma rede de segurança. O critério exato do
reaproveitamento (caminho? caminho + TC?) não foi isolado.
- mp4 com mais de uma trilha de áudio, ou com número de canais diferente de 2 (a forma nativa
  tem uma trilha estéreo, e o `ChannelVecBA` do item de vídeo não é redimensionado);
- `BitDepth` do áudio (a forma diz 2 para PCM 24 bits e 3 para o AAC; PCM 16 bits não medido).

### ⚠️ UM marcador de timeline por QUADRO — `confirmado` 2026-10-03 (Resolve Studio 21.1, macOS)

Um DRT com 14 marcadores de timeline em 6 quadros distintos (planos que começam juntos em
trilhas diferentes, caso R02 do PRODB) importou com **6**: o Resolve guarda um por quadro e
descarta os outros **em silêncio**, sem aviso. Quem escreve marcador por segmento perde os avisos
dos planos empilhados. O De Lá Pra Cá junta os do mesmo quadro num só (cor mais forte; as notas
de todos, com a trilha na frente) — `drp/writer.py` `_sinais`. No 19: `pendente` (o mesmo
writer; o fluxo do Avid também tinha o furo).

### ⛔⛔ Os MARCADORES DE TIMELINE moram no `project.xml`, em zstd — e o esqueleto os herda — `confirmado` 2026-09-25

**Sintoma.** Toda timeline gerada pelo De Lá Pra Cá chegava ao Resolve Studio 19.0.0b.59 com
os 23 marcadores da PRODA_CORTE, que é a timeline-modelo do esqueleto. Aconteceu inclusive:
- numa C04 de 31 s, com marcadores em 01:02:08 em diante;
- num projeto zerado;
- num **Mac pela rede**.

**Onde estão.** NÃO estão na sequência (`SeqContainer`: os `<MarkersBA/>` dos clipes estão
vazios) nem no `Sm2MpTimelineClip`. Estão em:

```
project.xml › … <Element><Sm2SequenceLockableBlob DbId=…>
                           <FieldsBlob>…</FieldsBlob>   ← chave "BlobData" (UTF-16BE), depois zstd (28 B5 2F FD)
                           <BlobOwner>{DbId do Sm2Sequence da timeline}</BlobOwner>
```

Descomprimido (1.798 B para 23 marcadores), o conteúdo tem a nota, a cor e o autor **em
UTF-8** ("AMBIENCIA DE DENTRO DE CARRO…", "Editor_Keyboard"), em registros binários. Fica numa
lista com vários `BtMetadataLockableBlob`, que são metadados dos clipes.

**Como se achou, e por que demorou.** A busca por texto, hex, UTF-16 e zlib em TODOS os campos
não achou nada. Por isso o esqueleto chegou a ser descartado, erradamente. O que refutou a
hipótese "vem de fora" foi o autor abrir o mesmo DRT num Mac isolado, e os marcadores virem
assim mesmo. Também foram medidos e descartados:
- trocar os identificadores da sequência;
- tirar o blob de 9,6 KB do `Sm2Sequence` (miniatura e Fairlight);
- tirar o `UIElementsState`;
- renomear o AAF de origem.

Varrer os campos procurando o magic do **zstd** achou o bloco. A variação sem o item (`F`)
abriu normalmente, sem marcadores.

**Regra.** Um DRT montado sobre esqueleto (de qualquer app da família) tem de tirar o
`<Element><Sm2SequenceLockableBlob>…</Element>` do `project.xml`. O De Lá Pra Cá faz isso no
writer e no `make_skeleton` (`drp.writer.sem_marcadores_da_timeline`), e o teste
`tests/test_drt_sem_heranca.py` descomprime zstd e zlib para provar. ⚠️ As cópias do writer
no RELINKER e no Assist anterior **não foram conferidas** (`pendente`).

**Serve também para ESCREVER marcadores.** O comentário do editor pode virar marcador no DRT
por este bloco. O layout dos registros está `pendente` de decifrar.

**Lição de método.** Os blobs do DRT do 19 usam **zstd**: o `FieldsBlob` do áudio (`0x81`) e
este. Uma busca que não descomprime zstd dá falso "não está aqui".

### ⭐⭐ A CORREÇÃO DE COR de cada plano viaja DENTRO do DRT — `confirmado` 2026-09-27

Medido para o "Atualizar timeline" do Magic Link (De Lá Pra Cá), com Resolve Studio 19 public beta no
Windows 11: 14 planos de chart, cada um com um CDL diferente aplicado por `TimelineItem:SetCDL`
(slope R = 0,5 + 0,1 × i), e a timeline exportada por `Timeline:Export(…, EXPORT_DRT)`.

- Cada `Sm2TiVideoClip` exportado leva um `<pLmVerTable>` → `ListMgt::LmVersionTable` (`pActive` =
  a versão ativa) → `<Locals>` → `ListMgt::LmVersion` com `Name` ("Version 1"), `HasCorrection`
  (`true`) e o **`<Body>`: a correção em si**. O DRT que o app escreve tem UMA tabela (vazia).
- O `Body` é `0x81` + **zstd** (a mesma forma dos LockableBlob do `project.xml`), e dentro um
  **protobuf** de pares (id do parâmetro, valor float32 little-endian). O slope R vem depois da
  chave `08 9d 80 80 30 12 05 0d`, o B depois de `08 9f 80 80 30 12 05 0d`. Os 14 planos
  devolveram os 14 slopes aplicados, cada um no seu plano.
- Saturação acima do máximo é limitada pelo Resolve (3,3 não aparece no Body).

⭐ **Consequência:** reescrever um DRT exportado mantém a correção de cada plano se o
`<pLmVerTable>` do plano for copiado junto. É o caminho "editar uma CÓPIA da timeline de quem
recebe" sem entender a correção.

⚠️⚠️ **CORRIGE (2026-09-28, caso U02):** "todos os ids mudam", como está logo abaixo, DERRUBA o Resolve
19 num projeto REAL. A mesma PRODA exportada, numa cópia do projeto do autor (`ExportProject` →
`ImportProject`), importada pelo `fuscript`:

| ids trocados | sem edição | com a edição do Atualizar |
|---|---|---|
| nenhum | importou | importou |
| TODOS os uuid do pacote (texto + UTF-16 nos blobs) | **travou** (10 min, processo preso) | **derrubou** |
| todos os `DbId` definidos no pacote | **derrubou** | **derrubou** |
| **só os da TIMELINE**: tudo o que a sequência define, o bloco `Sm2MpTimelineClip` (com `Sm2Timeline` e `Sm2Sequence`) e os blocos do `project.xml` | — | **importou**, com a contagem prevista |

O que não pode mudar: os **clipes de mídia do pool** (`Sm2MpVideoClip`/`Sm2MpAudioClip`, com os
`BtVideoInfo`/`BtAudioInfo`) e a **pasta Master** (`Sm2MpFolder`), que já existem no projeto. O
U01 (charts) passou com "todos" por ser pequeno ou por sorte; a regra é a de baixo. Implementado em
`_DeLaPraCa/motor/drp/reescrever.py::_ids_da_timeline` (padrão `ids="timeline"`). `confirmado` no 19.

(texto original, de 2026-09-27:) ⛔ **Para reimportar um DRT exportado no MESMO projeto, TODOS os ids mudam, inclusive os em UTF-16
dentro dos blobs hex** (`FieldsBlob` e afins), com o mesmo mapa velho → novo. Trocar só os ids do
texto faz a timeline entrar **VAZIA** (0 planos), sem erro nenhum (medido). Reimportar o mesmo
arquivo sem trocar os ids devolveu `nil` na segunda vez (`inferido`: colisão de `DbId`).

**A conferir (pendente):** se o Resolve MANTÉM a correção ao importar o DRT reescrito. O arquivo
leva a correção certa, mas a leitura de volta depende do `Export` (ver
`plugins/resolve-scripting/api-scripting.md` §7, que não exporta a timeline pedida por script
externo) e a conferência visual ficou com o autor.
✅ 2026-09-27 (noite): conferido pelo autor na página Color — as timelines reimportadas (igual, sem um
plano, com um plano aparado) e a do `CopyGrades` chegaram com os planos coloridos. `confirmado` no 19.

### ⭐ O `Body` da grade por dentro — e o `.drx` é o MESMO formato — 2026-10-10 (`confirmado`, Resolve Studio 19, Windows)

- O `.drx` (still exportado: `Timeline.GrabStill()` + `GalleryStillAlbum.ExportStills([still], pasta, prefixo, "drx")`) é
  XML com `Gallery::GyStill` → `pClipFullVer` → **a mesma `ListMgt::LmVersion` com o `Body`** do DRT. E o caminho de volta
  existe: `Timeline.ApplyGradeFromDRX(caminho, modo, itens)`. Escrever o `Body` = grade EDITÁVEL nos nós (no DRT na
  importação, ou por `.drx` depois), em vez de LUT.
- `Body` = `0x81` + zstd + protobuf. Árvore (CDL num clipe só): `1 → 7 → 9 → 1 → 6 → 2` = o NÓ (`1:int` índice) com uma
  lista de `3:msg {1: id do parâmetro (int), 2: {1: valor f32}}`. Medido com `SetCDL` (Slope 1,1/1,0/0,9; Offset 0,01/0/
  −0,01; Power 1,2/1,0/0,8; Sat 1,3): **0x06000005 = Saturação** (1,3); 0x06000018–1A = 0,009009/0/−0,011236;
  0x0600001D–1F = 1,111111/1,0/0,891089; 0x06000022–24 = −0,2/−0/0,25 — o CDL entra CONVERTIDO para os parâmetros das
  primárias (forma exata `pendente`). Um parâmetro de LUT do nó: id 0x86000081 com o caminho relativo em texto.
- ⏳ Os ids de curvas, contraste/pivô, temperatura/tint, Sat vs Sat, Lum vs Sat, rodas e o 2º nó: roteiro feito pelo
  autor na página Color (timeline "COR_EDITAVEL" do projeto "DLPC teste Windows 2026-10-09", um clipe por controle).
  Decodificador: scratchpad `pb.py` (⏳ virar ferramenta do motor).

### ⭐ Os ids dos controles do nó (página Color) — 2026-10-11 (`confirmado`, Resolve Studio 19, roteiro do autor na UI)

Um clipe por controle (timeline "COR_EDITAVEL" do projeto "DLPC teste Windows 2026-10-09"), grade exportada por `GrabStill`
+ `ExportStills(…, "drx")`. No `Body`: `1 → 7` = UM NÓ por ocorrência (campo 1 = id do nó, 4/5 = posição no editor de nós,
`9 → 1 → 6 → 2 → 3` = os parâmetros `{1: id, 2: {valor}}`); `1 → 8` = as ligações entre nós.

| controle | id | valor guardado (o que o autor pôs) |
|---|---|---|
| Contrast / Pivot | 0x860000C1 / 0x860000C0 | 1,3 / 0,3 |
| Saturation | 0x06000005 | 1,4 (a tela mostra 70; 50 = 1,0) |
| Temp / Tint | 0x86000115 / 0x86000116 | 500 / 20 |
| Lift / Gamma / Gain mestres | 0x0600001B / 0x06000025 / 0x06000020 | −0,1 / 0,2 / 1,2 |
| Highlights / Shadows | 0x86000110 / 0x86000111 | −30 / +30 |
| Curva Custom R / G / B / Y | 0x86000506 / 507 / 508 / **509** | `{8: lista de pontos}` 0–1023, (−1024,−1024) na frente e (1023,1023) no fim |

⛔ **CORRIGE (2026-11-20, Resolve Studio 19.1.4, Windows — lido de uma curva feita na UI e reproduzido byte a byte):** o
valor da curva Custom é **UM campo 8 com os pontos REPETIDOS no campo 1**: `{1: id, 2: {8: {1: {1: x, 2: y}, 1: {…}, …}}}`,
x/y em **f32**, escala 0–1023, **o zero OMITIDO** (o ponto (0, 0) vai como mensagem vazia). Um campo 8 POR ponto (a
leitura literal da tabela acima) **derruba o Resolve no próprio `ApplyGradeFromDRX`**, na página Edit, sem a paleta Curves
aberta. Com o Y ligado (o padrão da UI) ela grava Y, R, G e B e os QUATRO flags (`0x860000BB/BD/BE/BF`). Os escalares
são `{1: id, 2: {1: f32}}`; os inteiros `{1: id, 2: {2: n}}`. Montador: `laboratorio-de-midia/lab/bancadas/resolve_cor.py`
(`p_curva`, `no`, `body`). E o `SetCDL` do 19.1.4 grava a Lum Mix (`0x8600000B`) = 0 e um `0x8600009B = {2: 2}`.
⭐ Dentro de UM nó o Resolve aplica a **curva ANTES da Saturação** (medido na carta B24: a ordem inversa erra 0,75 →
0,30); para Sat → curva, dois nós em série (`avb/color-correction.md` §4).
| flags das curvas | 0x860000BD/BE/BF/BB (R/G/B/Y) | `{2: n}` — ⚠️ com 6 (copiado de outro clipe) a curva NÃO vale; 0 e 2 valem |
| Sat vs Sat / ~~Lum vs Sat~~ | 0x86000404 / 0x86000405 | pontos 0–1, y = 0,5 neutro; com 0x860000CF, 0x86000103/0x86000202. ⚠️ CORRIGIDO 2026-10-11 (tarde): o 0x86000405 é **Sat vs Lum**; o Lum vs Sat é o **0x86000403** — ver "As curvas de matiz/saturação" abaixo |

- ⛔ **CORRIGIDO 2026-10-11 (tarde) — o item abaixo está ERRADO:** a curva Custom é **Bézier cúbica POR TRECHOS** (`P0 a a P1 a a P2 …`: cada ponto da UI seguido das duas alças do trecho) e o **flag da curva (0x860000BB/BD/BE/BF) = 2 × o nº de pontos da UI no meio** (4 + 3k pontos ⇔ flag 2k; roteiro: 1 ponto → 8 entradas/flag 2, 3 pontos → 14/flag 6, só o preto movido → 5/flag 0; sem toque = 2 pontos, flag 0). Medido numa rampa de cinza: 7 pontos/flag 2 → 1,35/255 do modelo Bézier (B-spline uniforme: 19), 10/flag 4 → 1,13. ⛔ **Lista e flag incoerentes (8 pontos, flag 0) DERRUBAM o Resolve** quando a paleta Curves desenha a curva — e a grade fica salva: o projeto passa a cair ao abrir (consertado trocando a linha em `ListMgt::LmVersion.Body` do `Project.db`). As ALÇAS podem sair da caixa 0–1 (o Resolve as usa como vêm: −0,12/1,15 → 1,6/255) e não cai. A B-spline 'funcionava' com 4 pontos porque aí as duas coincidem. Consequência: a curva da Lumetri (spline natural, plana fora dos pontos) vai EXATA, com os pontos da UI = os da Lumetri e as alças pela derivada de dentro de cada trecho (68 curvas do R04: ≤ 0,006/255). As curvas de matiz/saturação usam a mesma forma, com flag próprio: 0x86000103 = Sat vs Sat, 0x86000202 = Sat vs Lum; o do Lum vs Sat `pendente`.
- ~~⭐ **A curva Custom é uma B-SPLINE CÚBICA de nós uniformes e pontas presas**: os pontos gravados são de CONTROLE (a curva
  não passa por eles). Medido numa rampa de cinza: o modelo dá 0,6/255 de erro médio. Para reproduzir uma curva (a da
  Lumetri, spline natural), os pontos de controle saem por mínimos quadrados (x nas abscissas de Greville): 8 pontos →
  1,3/255 médio na rampa. Continua editável na página Color.
- ⚠️ As curvas R/G/B passam pelo **Lum Mix** (padrão 100: preserva a luma — no R só, o G e o B DESCEM). As três iguais
  com Lum Mix 100 = nada muda. A curva Y (509) muda a luma e PRESERVA a cor: num plano colorido a luma bate com a curva
  mestra da Lumetri (0,431 × 0,435) mas a saturação fica baixa (0,072 × 0,100) — a Lumetri aplica em cada canal.
  ✅ **Lum Mix = 0x8600000B** (clipe 19 do roteiro, valor 0). Com Lum Mix 0 + as curvas R/G/B = a curva mestra da Lumetri
  (8 pontos de controle ajustados): o plano JUL_7695 do R04 fica a 1,25/255 do render do Premiere (a LUT: 0,68) e a
  saturação bate (0,101 × 0,100). ⇒ a curva mestra da Lumetri pode ir EDITÁVEL.
- Escrita: `Timeline.ApplyGradeFromDRX(drx, 0, [itens])` com o `Body` montado (troca a grade do clipe inteira).

#### ⭐ Grade com VÁRIOS nós, LUT no nó, curvas de saturação e ganho por canal — 2026-10-11 tarde (`confirmado`, Resolve Studio 19.0.0b.59, Windows)

Medido por script (sem UI) numa carta sintética (saturação HSL na largura, luma na altura; `GrabStill` + `ExportStills`
png) e num clipe do R04 (JUL_7695), timelines "COR_LAB", "COR_CARTA", "COR_AJUSTE" do projeto "DLPC teste Windows
2026-10-09". Scripts no scratchpad da sessão d6726fc7 (`cor/grade_nos.py`, `sondar.py`, `canais.py`, `ajuste_eixo.py`).

- **Estrutura da grade em série** (lida no `resolve19.drt` do caso U01, que tem grades de 2 e 4 nós): `Body → 1` =
  `{1: nº de nós, 2, 3 (resolução), 7: nó…, 8: ligação…, 9: entrada, 10: saída, 11, 12}`. Nó = `{1: id, 2: nº mostrado,
  4: x (190 + 270·(n−1)), 5: y 180, 7: 1, 8: 44, 9: parâmetros, 10: 0a0a08818080800c12021002, 12: carimbo}`; os
  parâmetros = `9 → {1: {1:1, 3:1, 6: {2: {1:1, 3: param…}}}, 2: 03 04 05 06 12}` (nó vazio: só o `2`). Ligação =
  `{1: de, 3: para, 5: 64, 6: 64, 7: nº}`. Entrada = `080110501a080801104018012001`; saída = `{1:2, 2:64, 3: {1: n+1,
  2:64, 3:2, 4: último nó}}`. Uma grade MONTADA assim entra por `ApplyGradeFromDRX` (3 nós → `GetNumNodes()` 3); o
  Resolve renumera os ids (11, 12, 13). ⛔ Campos desconhecidos no nó (testados 3/6/11 com texto, para achar o rótulo)
  DERRUBAM o Resolve (o 3 ou o 11 — o 6 é o rótulo). ✅ **Rótulo do nó = campo 6, texto UTF-8** (o autor rotulou um nó "Balanço" na UI; `GetNodeLabel` o devolve). Montado por nós (entre o 5 e o 7) num `.drx` com 3 nós: "LUT de câmera" / "Balanço" / "Curvas" voltam por `GetNodeLabel`, e a LUT escrita direto no `Body` (0x860000A0/A1) volta por `GetLUT` — não precisa de `SetLUT`. A grade aplicada por script fica salva ao trocar de timeline.
- **LUT no nó**: `0x860000A1 = {5: "DeLaPraCa\arquivo.cube"}` (caminho relativo à pasta de LUTs) + `0x860000A0 = {2: 6}`
  (não é o 0x86000081 que se supunha). `SetLUT` também funciona nos nós montados.
- **As curvas de matiz/saturação** (uma curva plana / em degrau por id, na carta): `0x86000400` Hue vs Hue, `401` Hue vs
  Sat, `402` Hue vs Lum, **`403` Lum vs Sat** (x = luma Rec.709; erro do modelo 0,018 no ganho), **`404` Sat vs Sat**
  (x = CROMA máx−mín, não a saturação HSL; erro 0,03), `405` Sat vs Lum (muda a luma). Valor = `{8: [{1: x, 2: y}…]}`.
  Nas de saturação, **ganho = 2·(1 − y)** (o y é gravado INVERTIDO: subir a curva na UI grava y < 0,5 — confere com o
  roteiro c15). A forma é a mesma Bézier por trechos da curva Custom (ver a correção acima). ⇒ o Luma vs Sat da Lumetri (x = luma Rec.709) tem equivalente; o Sat vs Sat da Lumetri (x = saturação
  HSL) não casa o eixo — vai pela conferência numérica (reserva em LUT se passar do limite).
- **Ganho por canal = `0x0600001D` / `1E` / `1F` (R/G/B), neutro 1, multiplica o valor do código** (em gama): com Lum Mix 0,
  0,5 → R × 0,500; o balanço medido da Lumetri (A030_C062: 0,9834 / 0,9990 / 1,0933) sai a < 1/255. Com o Lum Mix
  padrão (100) o Resolve preserva a luma e os outros canais mudam. `0x06000022`/`23`/`24` = um ajuste de canal de
  neutro 0 com cara de gama (curva de potência; não usar para ganho). `0x1C`, `0x21`, `0x26`–`0x2B`: nada visível a 0,5.
  ⚠️ Com **Lum Mix 0 o Gain MESTRE (0x06000020) não age** (é o Y do YRGB) — num nó com Lum Mix 0, mexer no ganho por canal.
- **Adjustment Clip** aceita `ApplyGradeFromDRX` (3 nós) e `SetLUT` como um clipe comum.
- `ApplyGradeFromDRX` funciona com a página **Edit** aberta (não precisa abrir a Color).
- ⭐ **O EIXO da curva Custom não é o código da imagem** (2026-10-11, projeto do autor, timeline DLPC_CURVA_VOLTA, rampa
  de cinza 8 bits): 0–1 da curva = código de **0,00649 a 1,02441** (C0 + W·u, W = 1,01792), nos DOIS eixos. Lida de volta
  a grade (GrabStill/ExportStills): o Resolve guarda a lista exatamente como gravada — a diferença está no desenho. Com o
  mapeamento, três curvas (retas, um trecho, a do JUL_7695) ficam a 0,52–0,63/255 (o piso de 8 bits); sem ele, 1,5/255
  com desvio estruturado (quinas arredondadas, o fim chegando a 255 antes). Prova R04: grade editável 2,04/255 = a LUT por
  plano (2,04). As curvas de saturação não mostraram esse eixo (o modelo direto deu 0,27/255).
- ⚠️ `ExportStills` só funciona com o painel **Gallery** ABERTO na página Color (o autor abriu; antes, False em
  qualquer projeto). Era isso também no projeto novo.
- ⚠️ `GalleryStillAlbum.ExportStills` devolve False com o painel Gallery fechado (ver abaixo);
  `Project.ExportCurrentFrameAsStill(caminho.png)` grava o quadro com a grade sem depender dele. E `ProjectManager.SaveProject()` no
  "Untitled Project" abre a caixa modal de salvar (o autor teve de fechar): não chamar ali.
- ⭐ Para testar grade montada: um projeto DESCARTÁVEL ("DLPC lab cor N"), nunca o projeto de teste do autor — uma grade
  que derruba o Resolve fica salva e o projeto passa a cair ao abrir (com ou sem a mídia online).


### ⭐ O ESTABILIZADOR do Resolve no DRT — 2026-10-10 (`confirmado` 1ª leitura, Resolve Studio 19, Windows)

`TimelineItem.Stabilize()` grava a análise no `Body` da grade do clipe (a `LmVersion`, protobuf acima): no nó, uma entrada
por quadro com **`0x10300017`** (matriz 3×3 f32: movimento da câmera do quadro k em relação ao 0), **`0x1030001A`** (matriz
do quadro anterior para este), `0x10300015` (80 bytes, a decifrar) e `0x1030001B`. A correção do render é calculada na hora
(suavização + ampliação ~1,06). Medido contra um clipe com tremor CONHECIDO (laboratório B19). Consequência: dá para
INJETAR o movimento analisado por outro NLE (o Warp Stabilizer do Premiere) e manter o Transform do clipe limpo.
⏳ Os parâmetros do modo (Perspective/Similarity/Translation, Camera Lock, Strength/Smooth, Zoom) no `Body`.
⭐ **Injeção confirmada (mesma noite):** trocar floats no `Body` (por `.drx` + `ApplyGradeFromDRX`) — as rastreadas
`0x10300017`/`1A` não mudam o render; **`0x10300015`** (80 bytes `2a 50`, palavras 11–19 = matriz 3×3 f32) **é a correção
aplicada por quadro**: × 2 nela, o render dobra a correção. ⏳ convenção exata e se o Resolve a reescreve ao mudar a força.
⭐⭐ **Conta e ponta a ponta (2026-10-11):** render = ampliação no centro (palavra 10 do bloco = 1 ÷ ampliação) · S·H⁻¹·S⁻¹,
S = diag(1,5; 1,5) (a matriz está na escala de ANÁLISE de 1280 px, origem no canto). A estabilização do Warp Stabilizer do
Premiere injetada assim dá correlação 0,984 contra o render do Premiere (o estabilizador do próprio Resolve: 0,819).
Laboratório B19 (`resultados/B19_ESTABILIZADOR/PREMIERE.md`).
⭐⭐ **Resolve Studio 21.1 (Mac) e o Stabilize do AVID — `confirmado` 2026-10-24** (projeto "DLPC LAB ESTAB 21",
`B19_TREMIDO.mov`; amostras em `03 CASOS/EFEITOS/E07 ESTABILIZADOR/resolve/`):
- A estrutura é a MESMA do 19: o nó em `3 → 9 → 1 → 6 → 2`, a lista em `4`, uma entrada por quadro com `1` = **o quadro
  da MÍDIA × 2** (num clipe aparado em 30, as entradas vão de 60 a 218 — não do clipe; a 1ª entrada com quadro 0 não
  traz o campo 1) e os parâmetros `0x10300015`/`17`/`1A`/`1B`. O bloco `0x10300015` (80 bytes): inteiros BIG-endian
  no cabeçalho — palavra 1 = 2, **palavra 3 = 1280 e palavra 5 = 720 (o tamanho da ANÁLISE)** —, depois f32 LITTLE-
  endian: palavra 10 = 1 ÷ zoom (0,95297 do Stabilize() = 1,0494), 11–19 = a matriz. A última entrada vem identidade.
- **A conta do Avid entra como translação pura**: H = [1 0 uₓ·1280; 0 1 u_y·720; 0 0 1] (u em fração do quadro, o
  "o quadro k mostra a fonte em q + u" do `avb/estruturas.md` §Stabilize) e a palavra 10 = 1 ÷ Z (o Auto-Zoom).
  Contra o RENDER do próprio MC (`B19_MC_ESTAB_100.mxf`): **correlação 0,999, resíduo ≤ 0,2 px** em 6 quadros, também no
  clipe aparado (0,999). O sinal oposto dá 0,56–0,81; o estabilizador próprio do Resolve, 0,90–0,96; o tremido, 0,71–0,81.
- **Ler o Body sem a Gallery:** o DRT da timeline exportado por script (`Timeline.Export(…, EXPORT_DRT)`) traz o `Body`
  de cada clipe (a grade do `pLmVerTable`) — o mesmo que o `.drx` do `GrabStill` (79 bytes a menos; os dois servem).
  E um **`.drx` MÍNIMO** (`Gallery::GyStill` → `pClipFullVer` → `LmVersion` com `FieldsBlob`/`Name` vazios,
  `HasCorrection`, `VerType` 0, `ImplVersion` 1 e o `Body`; sem miniatura, sem `pTrackVer`) é aceito.
- ⛔ **No 21 o `ApplyGradeFromDRX` é do `Graph`**: `item.GetNodeGraph().ApplyGradeFromDRX(drx, 0)` (0,08 s). O
  `Timeline.ApplyGradeFromDRX` "existe" para o `hasattr` mas vale `None` ("'NoneType' object is not callable").
- No produto: De Lá Pra Cá `drp/estabilizador.py` (`Stabilize()` → DRT exportado → injeção → `.drx` mínimo → `Graph`).
  ⏳ Se o Resolve REESCREVE o `0x10300015` quando o colorista mexe na força/modo do estabilizador (UI); o 19 e o 20.
- ⭐ **Mídia OFFLINE — `confirmado` 2026-10-24 (Studio 21.1, Mac, "DLPC LAB ESTAB 21", B19 aparado em 30, 79 quadros):**
  com o arquivo fora do lugar e o Media Pool dizendo `Offline` (o projeto recarregado — antes disso o Resolve ainda
  o tinha em cache e dizia `Online`), o `Stabilize()` devolve **True** e cria a estrutura INTEIRA (80 entradas, de 60
  a 218) com as matrizes em identidade (movimento zero). A correção injetada nela por `.drx` vale: com o arquivo de
  volta (projeto recarregado, `Online` sem relink), o render dá **0,999 contra o render do MC** nos 5 quadros, resíduo
  ≤ 0,2 px (o tremido: 0,71–0,77). E um `Body` MONTADO de um molde (o esqueleto do E07 com uma entrada, repetida por
  quadro da mídia, `1` = quadro × 2) dá os mesmos blocos `0x10300015` da análise real (inteiro e aparado) e o MESMO
  0,999 pela imagem — a reserva para quando o `Stabilize()` recusar. Fora do nó, só `/1/12` e `/3/12` mudam entre
  análises (parecem identificadores; o molde leva os dele e o Resolve aceitou). ⏳ O molde foi medido só a 1920 × 1080
  (`/1/3` = o tamanho da timeline; o da análise, 1280 × 720, no cabeçalho do bloco); ⏳ o offline no 19.
  No produto: De Lá Pra Cá `drp/estabilizador.py` (`corpo_do_molde`, `_pelo_molde`; molde `drp/estabilizador_r21.bin`).

### ⭐⭐ Resolve 19 × 21: o que o colorista faz na timeline, no DRT exportado — `confirmado` 2026-09-28

Caso `03 CASOS/ATUALIZAR/U01 VERSOES DO RESOLVE` (pasta de testes): a mesma timeline de 14 charts
importada no **Resolve Studio 19.0.0b.59 (Windows, `DbPrjVer="14"`)** e no **21.1.0.14 (Mac mini,
`DbPrjVer="17"`)**, com o mesmo roteiro do autor na página Color, e exportada como DRT nas duas.

| o que o colorista fez | como aparece no DRT (igual nas duas versões) |
|---|---|
| correção num plano | `pLmVerTable` → `ListMgt::LmVersion` "Version 1" com `Body` (0x81 + zstd) |
| **corte interno** (blade) no meio de um plano | **dois** `Sm2TiVideoClip`, o segundo com `In` = o ponto do corte em quadros da mídia; cada um com a sua `pLmVerTable` |
| **segunda versão local** | a mesma `LmVersionTable` com `Version 1` e `Version 2`, cada uma com o seu `Body`; `pActive` aponta a ativa |
| **dois nós** | só dentro do `Body` (mais bytes); nada fora dele |
| **adjustment clip** numa V2 | um `Sm2TiVideoClip` comum na trilha de cima, `PrettyType`/`Name` = "Adjustment Clip", **sem `MediaRef`**, `In` = 86313 (o tempo interno do gerador, igual nas duas) e a sua `pLmVerTable` |

- O `Sm2TiVideoClip` tem **os mesmos 39 campos, na mesma ordem**, no 19 e no 21. A `Sm2TiTrack` do 21
  ganha um campo, `FusionCompHolderItems` (8 → 9).
- O que muda entre as versões está DENTRO dos blobs: o `Body` da correção (o mesmo trabalho tem outro
  tamanho no 21), o `FieldsBlob` do item (outro comprimento) e o cabeçalho `DbPrjVer`.

⭐ **Consequência para reescrever a timeline do colorista** (o "Atualizar timeline", caminho B): apagar,
deslocar e aparar só mexem em `Start`, `Duration` e `In` e apagam blocos inteiros, e isso é IGUAL no 19 e
no 21. Os blobs e o cabeçalho viajam intactos, na versão do próprio colorista, sem nada a compensar
entre versões nessas três operações. Ao deslocar um adjustment clip, só o `Start` muda (o `In` dele é o
tempo do gerador). A ida e volta no 21 (importar o DRT reescrito) ainda é `pendente`.
✅ 2026-09-28: ida e volta CONFERIDA pelo autor no 19 e no 21 (`U01 ATUALIZADO 19/21.drt`: o plano 2
aparado na cabeça, o plano 7 fora, o corte interno, as versões, os nós e o adjustment clip certos).

**Os marcadores de timeline do colorista no DRT exportado** (19, `resolve19 marcadores e cor.drt`, 2026-09-28):
o `Sm2SequenceLockableBlob` do `project.xml` (dono = a `Sm2Sequence`), `BlobData` = `[u32 0x2711][u32 n]`
+ `0x81` + zstd, e dentro o protobuf `{ 2: { 1: entrada… } }`; cada entrada `{ 1: quadro (do INÍCIO da
timeline), 2: [u32 2][u32 n] + { 1: { 1: cor, 3: nota, 3: duração em texto, 3: nome, 6: customData } } }`.
É a mesma forma que o `motor/drp/sinais.py` escreve (lá a palavra-chave vai no campo 2). Ao reescrever
a timeline, **só o quadro muda**; o resto da entrada viaja byte a byte (`motor/drp/reescrever.py`). No 21
este bloco ainda não foi medido (`pendente`).

CORRIGE (2026-10-01, Studio 21.1.0.14, macOS): **no 21 a forma é OUTRA** — `{ 2: { 2: entrada } }`, e o
quadro vem numa submensagem e em **meio-quadro**: `entrada { 1: { 1: quadro × 2 }, 2: … }` (a 23,976: 7 → 14,
101 → 202, 333 → 666, e os 7 marcadores reais do U03). O 21 lê a forma do 19, mas exporta a dele. O reescritor só
conhecia a do 19 e, no 21, **não movia nenhum marcador e contava 0 "fora do lugar"** — o autor viu o marcador da
VELOCIDADE ficar 855 quadros depois do plano. Agora trata as duas, e avisa quando há marcadores numa forma que não
reconhece. CORRIGE (mesmo dia): medido a 24, 25 e 29,97 — o meio-quadro é × 2 em QUALQUER taxa. Ver `dados/marcadores-e-cores.json` §`forma_por_versao`.

**⚠️ A cada versão NOVA do Resolve (22…), o que pode quebrar a reescrita, do mais ao menos grave:**
1. **ids num formato novo** (binário dentro de um blob, por exemplo): a troca não os pega e a timeline entra
   **VAZIA, sem erro** (o modo de falha medido em 2026-09-27). É a falha silenciosa a vigiar.
2. **o bloco dos marcadores** com outra forma: o reescritor já recusa mexer num mapa que não seja só
   `BlobData` e avisa.
   ⚠️ CORRIGE (2026-10-01): o aviso só cobria o MAPA; a forma do PROTOBUF mudou no 21 e passou calada. Agora
   também avisa quando há marcadores e nenhum é reconhecido.
3. **os nomes `Start`/`Duration`/`In`** mudarem (improvável; aparece na hora).
Defesa: repetir o roteiro do caso U01 na versão nova e rodar `_DeLaPraCa/tests/test_reescrever.py` com o
DRT dela; e, na execução, conferir depois de importar (planos por trilha) e, se não bater, apagar a importada
e deixar a timeline do colorista intacta.

### `Sm2TiAudioClip.MediaTrackIdx` = CANAL DE CONTEÚDO, não índice da track (confirmado)

Descoberto no DRAMASYNC (2026-07-24), diffando contra um DRT feito no Resolve pelo
usuário. O `MediaTrackIdx` de um clipe de ÁUDIO na timeline é o **canal 0-based que
ele LÊ do arquivo**, NÃO o índice da track onde está posicionado:

- WAV multicanal espalhado em N tracks (uma por canal): `MediaTrackIdx` = 0,1,2,…
  (canal por track).
- Áudio da câmera (embutido no .mp4) numa track própria, lendo o canal 0:
  `MediaTrackIdx` = **0** — igual ao do canal 0 do WAV que está NOUTRA track. Se
  fosse índice de track, os dois seriam diferentes; são iguais → é canal.
- O canal LIDO também vai no `ChannelsBA`/`ch_word` do `VirtualAudioTrackBA`
  (ver o writer). Os dois têm de bater.
- ⚠️ O writer do RELINKER (`drp/writer.py`) escrevia `MediaTrackIdx = track - 1000`
  (convenção de track fictícia 1000+). Só coincide com o canal quando o arquivo
  ocupa tracks consecutivas a partir de A1000; com tracks de numeração pequena
  (1,2,3…) dá valor negativo → canal absurdo → mudo. A cópia do DRAMASYNC
  (`src-python/drt/writer.py`) corrigiu para `channel - 1`.

### AudioTrackVec: ordem TOP-to-BOTTOM — `vec[0] = A1` (CONFIRMADO no Resolve)

`vec[0]` do `AudioTrackVec` é a **A1 (track de CIMA)**. O áudio no Resolve cresce
PARA BAIXO a partir do centro (ao contrário do vídeo, que cresce para cima — por
isso a track 1 de VÍDEO é a V1 de baixo). Confirmado abrindo o DRT gerado no
Resolve: com o som direto nas tracks 1..N e a câmera nas seguintes, o Resolve
mostrou o som direto em A1.. (topo) e a câmera abaixo. Portanto, para o som direto
nas primeiras tracks e a câmera nas de baixo, dê ao som direto os PRIMEIROS
números de track e à câmera os seguintes (o writer ordena o vec ascendente).

---

### 🆕 ⭐⭐ O `<In>` com FRAÇÃO: a fonte de outra taxa — 2026-11-23 (`confirmado` pela IMAGEM, Resolve Studio 21.1, Mac)

O `<In>` conta em quadros da TIMELINE, e o Resolve mostra o quadro de fonte `floor(In × taxa_do_arquivo / taxa_da_timeline)`
(a regra medida em 2026-10-05, no Windows). Com In INTEIRO, uma fonte de outra taxa cai UM QUADRO ANTES, sem aviso: 291 × 1,25 =
363,75 → 363 (o certo era 364); 51 × 2,5 = 127,5 → 127 (o certo, 128). Medido pelo número queimado no quadro (laboratório
BL09, originais de 29,97 DF e 59,94 numa timeline de 23,976). Com In inteiro, o 364 é INALCANÇÁVEL (290 → 362, 291 → 363,
292 → 365).
O DRT nativo (o `AppendToTimeline` com `startFrame` 364, exportado com `EXPORT_DRT`) grava **`<In>291|<f64 LE da fração>`**
(`291|00d0b3999999c93f` = 0,2000000000477: um fio ACIMA, para o piso não cair no quadro anterior); `GetLeftOffset(True)` = 291,2.
O writer grava assim (`drp/writer`, o vídeo sem rampa), e os leitores aceitam (`writer.ler_in`; antes o `reescrever` e o
`estabilizador` quebravam com `float('5|…')`, o que já aconteceria com um DRT nativo). ⚠️ O `GetSourceStartFrame()` da API
NÃO é o quadro mostrado: deu 63 para um plano que mostra 64 (e 47 certo num de mesma taxa) — confira pela imagem ou pelo
`GetLeftOffset(True)`.
⭐ **O SOM também** (`confirmado` pelo som, 2026-11-23, Resolve 21.1 Mac): o DRT nativo do mesmo plano grava `<In>291|00d0b3999999c93f</In>` no `Sm2TiAudioClip` (`GetLeftOffset(True)` = 291,2 no vídeo e no áudio). Medido pelo bipe de 400 Hz do laboratório no render: áudio com fração 0,01 ms do certo (= o nativo); com In inteiro 291, **+8,34 ms (0,2 quadro)** — no pior caso até 1 quadro (42 ms) fora do vídeo. O writer grava a fração no áudio desde então (Ciclo Assist `drp/writer._make_audio_timeline_clip`; lab `lab/bancadas/som_outra_taxa.py`).

## 4. Image Scaling (mismatch de aspecto) — decisão aberta

No DRT de referência do usuário, clipes com aspecto ≠ da timeline têm **transform vazio**; o
Resolve resolve pelo **Image Scaling do PROJETO** (Scale to Fit / Crop / Stretch / Center), com
override por-clipe no Inspector. ≠ do Avid (que grava por-clipe via FrameFlex). Opções de tradução
(A: por-clipe fiel / B: setar Image Scaling do projeto / C: híbrido) — **pendente**. Ver
[../aaf/efeitos.md](../aaf/efeitos.md) §FrameFlex.

## 5. Formato da TIMELINE importada: `SequenceSetup`, não `Body` — medido 2026-10-02

`confirmado` no Resolve Studio **21.1.0.14** (macOS 15.6.1), por bissecção em 13 variantes do mesmo
DRT (caso PRODB, Premiere → Resolve, timeline 2880×1620 a 24). ⚠️ No **19** (piso): `pendente`.

- **Sintoma:** todo DRT do nosso writer abria com configuração PRÓPRIA da timeline (`useCustomSettings=1`)
  a **1920×1080 e 23,976**, qualquer que fosse a origem — os valores do esqueleto (`skeleton_r19.drt`).
  A API não desfaz: `Timeline.SetSetting("useCustomSettings","0")` devolve `false`.
- **Onde NÃO está** (cada um trocado sozinho, sem efeito): o `Body` do `Sm2Sequence` (nem com o `Body`
  inteiro de um DRT nativo a 2880×1620/24), `MediaExtents`, `RenderCacheBA`, `UIElementsState`,
  `PTZRPresetType`, `ImportExportMetadataBA`, `DbSavedTime`, as datas, o `project.xml` inteiro.
- **Onde ESTÁ:** o 2º `FieldsBlob` do clipe da timeline (o do `Sm2Sequence`) é um QVariantMap com
  `Thumbnail`, **`SequenceSetup`** (bytes), **`SeqRef`** (o DbId do `SeqContainer` — trocar o blob
  inteiro pelo de outro DRT solta as trilhas: timeline vazia), `FLStudioModelBA`, `DolbyVisionVersion`…
  No `SequenceSetup`: **largura e altura em u64 BE, em par, DUAS vezes**, e um **código de taxa** em u64
  BE 20 bytes depois do 1º par = **a PARTE INTEIRA da taxa** (`confirmado` 2026-10-03, Resolve 21.1:
  timelines vazias em cada taxa exportadas em DRT): 23,976 → 23 (`0x17`), 24, 25, 29,97 → 29, 30,
  47,952 → 47, 48, 50, 59,94 → 59, 60. Prova de volta: DRT gerado a 25 e a 29,97 abriu a 25 e a 29,97,
  em 01:00:00:00. ⚠️ A API não aceita taxa fracionária (`SetSetting("timelineFrameRate","29.97")` →
  False) numa timeline de projeto que já tem timeline; só num projeto novo, pela config do projeto.
  (CORRIGE: até 2026-10-03 constava "outras taxas `pendente`".) O tamanho do
  blob não muda ao trocar os valores. Implementado: `drp/writer.py::_patch_sequence_setup`.
- **`MediaExtents` do clipe da timeline** = (início, duração) em segundos, double LE. O início vira o TC
  inicial NA TAXA DA TIMELINE: o 3603,6 s do esqueleto é 01:00:00:00 a 23,976 e **01:00:03:14 a 24**
  (86 quadros). Gravar `86400 / taxa` dá 01:00:00:00. `Timeline.SetStartTimecode` não serve de remendo:
  ele arrasta os itens junto. ⚠️ Corrigido só no caminho que informa o quadro (Premiere); o do Avid a
  24 fps deve ter o mesmo deslocamento — `pendente` medir.
  ✅ **Medido (2026-10-11, Resolve 19.0.0b Windows, laboratório A01 — sequência do Media Composer a 24):** o
  mesmo deslocamento, 01:00:03:14, e o 1º corte (em 86400) fica FORA da timeline (ela começa em 86486). A
  timeline também nascia a 23,976 nas outras taxas (o `SequenceSetup` só era escrito com `timeline_size`).
  Corrigido no De Lá Pra Cá `6cf44b9`: o export do Avid passa o raster do projeto do MC → 24/25/29,97p/59,94i
  abrem na taxa certa e em 01:00:00:00, 172/172 quadros no lugar.
- **A taxa do ITEM de pool de MXF gerenciada** (blob `<Time>`, `FrameRate` f64 LE): a forma do esqueleto
  declarava 23,976 para TODA MXF; numa MXF a 24 o render falha com "The clip … could not be decoded correctly"
  (medido 2026-10-11, Resolve 19 Windows). O item tem de declarar a taxa do ARQUIVO (`6cf44b9`). O codec
  declarado (`dnxhd_lb`) num arquivo ProRes OP-Atom não impediu a decodificação a 23,976 nem a 24.
- ⛔ **Import de DRT com item de MESMO NOME já no pool** (medido 2026-10-11, Resolve 19 Windows,
  `ImportTimelineFromFile` com `importSourceClips`): o Resolve REAPROVEITOU o item de vídeo existente (com o
  caminho antigo, de um arquivo que já não existia) e ignorou o caminho do DRT; os de áudio ele criou novos, no
  caminho do DRT. Num projeto do editor com um clipe de mesmo nome, o DRT pode ligar ao arquivo errado em
  silêncio. `pendente`: se o critério é o nome, o UniqueId ou o arquivo; se acontece no 21.

## 6. ARRIRAW no pool: forma própria — 2026-10-02

`confirmado` no Resolve 21.1: o item de pool de um ARRIRAW (MXF OP1a, ALEXA Mini 2880×1620) exportado
pelo próprio Resolve declara `Video Codec ARRIRAW`, `Format MXF OP1A`, `Radiometry` da câmera e
`EmbeddedAudioVec` (5 canais). Com essa forma (`drp/formas_r21_arriraw.xml`), 388 planos de ARRIRAW
abriram online no PRODB. Reconhecimento sem SDK: OP1a + "ARRI" no cabeçalho + ffprobe sem
raster; o raster vem dos local tags 3203/3202 (`mxf/codecs-proprietarios.md`). ⚠️ Forma do 21:
conferir no 19.

## 7. Keyframe de transform, retime por clipe e imagem parada — 2026-10-02

`confirmado` no Resolve 21.1.0.14 (macOS) com gabaritos que o PRÓPRIO Resolve escreveu: um FCP 7 XML
com keyframes importado (`ImportTimelineFromFile`) e exportado em DRT; e `SetProperty("RetimeProcess")`
+ export. O 19: `pendente`.

- **Parâmetro animado no `EffectFiltersBA`** (o blob do clipe vem comprimido, `81 28b52ffd…`, mas o
  writer grava sem compressão, `80`, e o Resolve aceita): o slot ganha o campo 10 (`52 <len>`) =
  `[u32 cabeçalho]` + um registro por keyframe `[u32 QUADRO DA FONTE][u16 0][u16 tipo][f64 valor]`.
  Zoom: tipo `0x0D`, +48 bytes zerados por registro, cabeçalho `FF FF FF 80`, com o campo 3 (valor fixo)
  = 0. Posição: tipo `0x0C`, sem os 48 bytes, cabeçalho `FF FF FF E0`, sem o campo 3. ⭐ O tempo é o
  quadro da FONTE (o `when` 200/300 do XML, com o clipe começando no quadro 200 do arquivo) — não o da
  timeline nem o do clipe. Rotação: forma da posição, `pendente`. Bytes reproduzidos idênticos:
  `tools/inspect_drp.py::_efb_slot_animado`.
- **Retime por clipe** (Inspector › Retime Process): filtro `0x2C` (o mesmo do Scaling por clipe),
  slot 0, paramID `0x5B`, inteiro = `resolve.RETIME_*` (1 Nearest, 2 Frame Blend, 3 Optical Flow).
- **Imagem parada (PNG):** forma de pool própria (`drp/formas_r21_still.xml`): sem áudio; no clipe da
  timeline `MediaFrameRate` = taxa da TIMELINE e um `MediaTimemapBA` constante (`XMax` fixo). Com a
  forma do mp4 (áudio + 25 fps do ffprobe) o PNG ficava offline.
- ⭐ **O `In` do clipe com taxa da mídia ≠ taxa da timeline** — `confirmado` 2026-10-05 (Resolve Studio
  19.0.0b.59, Windows), com vídeos sintéticos que levam o NÚMERO do quadro em código de barras (gerador:
  `DeLaPraCa_MIDIAS E PROJETOS DE TESTE/04 SINTETICOS/GERADORES/gerar_taxas.py`, leitor `ler_numero`):
  o Resolve mostra o quadro `floor((In + q) × taxa_do_arquivo / taxa_da_timeline)`, com a taxa que ele lê
  do CABEÇALHO (`r_frame_rate` do ffprobe; é a `FPS` do clipe no media pool). Exato com taxa fixa: 23,976,
  25, 29,97 e 59,94 numa timeline a 24, 64 medições. Com 59,94 a 24, a entrada só cai em múltiplos de
  ~2,5 quadros do arquivo (o `In` é inteiro, em quadros da timeline).
  ⛔ **Taxa VARIÁVEL** (vídeo de celular: grade de 25 com quadros faltando, média 24,0): o Resolve conta o
  arquivo pela taxa do cabeçalho, por CONTAGEM de quadros (1.387 quadros a 25 q/s = 55,5 s, quando o
  arquivo dura 57,8 s), e não garante o quadro: "1 em 25" fica a 0–1 quadro da conta; irregular, até 17.
  O PREMIERE conta o mesmo arquivo pela média dele (24,0118 q/s): o mesmo `In` dá quadros diferentes nos
  dois (no PRODB, 27 quadros). Detectar: `avg_frame_rate` ABAIXO de `r_frame_rate` (acima, o dobro, é
  o MXF de vídeo do Avid — não é buraco). De Lá Pra Cá: `media/sonda.taxa_variavel`, `writer` (entrada
  pela taxa do cabeçalho) e marcador "Taxa variável — conferir". ⏳ O lado do Premiere com os sintéticos
  (contagem × tempo) está `pendente`.
  ⛔ **O keyframe vive no domínio do `In`, não no quadro do arquivo** — `confirmado` 2026-10-08 (Resolve
  21.1, macOS, PRODB 01:22:49, insert de celular com 47 keyframes de posição de rastreamento): `In`
  650 (pela taxa do cabeçalho) e keyframes a partir de 677 (a conta do Premiere) → o insert ficou PARADO
  no 1º valor por 27 quadros e só andou no fim (medido quadro a quadro contra a referência: até 23 px
  fora). Com os keyframes a partir de 650, ≤ 1 px nos 37 quadros. Regra: keyframe = `In` + quadro dentro
  do plano; quem corrige o `In` corrige os keyframes junto (`writer._make_timeline_clip`, `desloc_kf`).
  Com taxa igual, `In` e quadro do arquivo coincidem — por isso o gabarito de 2026-10-02 parecia
  "quadro da fonte".
- **API:** `TimelineItem.GetSourceStartFrame()` TRUNCA (87,999 → 87); para conferir entrada use
  `GetSourceStartTime() − MediaStartTime`. Medido: o M002C024 (In 88 no DRT) dá 87 por um e 88,0 pelo outro.

## 8. Reverso — forma própria, NÃO rampa negativa — 2026-10-02

`confirmado` no Resolve 21.1 (macOS), com gabarito do próprio Resolve (FCP 7 XML com Time Remap
`reverse` a 70%) e conferência pela imagem (abertura do PRODB, 7 pontos com correlação ≥ 0,995
contra o export). O 19: ver o CORRIGE abaixo.

- ⛔ **CORRIGE (2026-10-03, Resolve Studio 19.0.0b.59, Windows 11):** a codificação COMPACTA dos keyframes
  (a que o 21 grava, descrita no item ✅ abaixo) **o 19 não lê**: descarta a curva calado e toca o `In`
  PARA A FRENTE a 100%. Medido pela imagem no filme PRODB (M002C022, V1, 169 q a 70%): quadros da
  fonte 102 → 184 → 266, onde deviam ser ~1241 → 1125. **Gabarito do PRÓPRIO 19** (Change Clip Speed 70%
  + Reverse Speed no mesmo take, exportado em DRT): o `MediaTimemapBA` usa o **QHash de sempre** (o molde
  de `build_speed_timemap`: `KeyframesBA` com header `(1, 0x74)`, chaves "1" = (X1, 0) e "0" = (0, Y0),
  cada keyframe com interp/YOut/YIn/Y/XOut/XIn/X), com a MESMA curva e o MESMO `In` 100 — igual byte a
  byte ao nosso, a menos de 1 ulp no Y0 e no XMax (10⁻¹⁴ s). O `In` do 19 traz a fração
  (`100|<f64 LE 0,428571>`); o nosso, inteiro (0,3 quadro de fonte — a conferir se importa). Com o QHash,
  o 19 tocou 1240 → 1182 → 1125 (correlação 0,997/1,000). `tools/inspect_drp.py::build_reverse_timemap`
  agora escreve o QHash; teste `test_drt_formato.py` com o gabarito embutido. ✅ A leitura do QHash
  reverso no **21**: `confirmado` (2026-10-04, Resolve 21.1.0.14, macOS 15.6.1 — filme PRODB gerado
  pelo writer v0.1.59, importado; o M002C022 da V1 em 6 quadros contra a referência: 0,939–0,950 na
  diagonal, 0,61–0,74 com os quadros vizinhos — a observação que refutaria "tocou para a frente").

- ⛔ Um `MediaTimemapBA` de rampa com inclinação NEGATIVA (o caminho "à prova de reverso" que se
  supunha) é aceito, mas o Resolve toca PARA FRENTE (medido: 0→1096 onde devia ser 1241→1125).
- ✅ A forma do Resolve: a curva cobre a mídia INTEIRA de trás para frente, só 2 keyframes na
  codificação COMPACTA (`80` + `0a 09 [11 <f64 LE Y0>]` + `0a 09 [09 <f64 LE X1>]`, o que é 0 fica
  omitido): (X 0, Y Y0) → (X Y0/v, Y 0), com **Y0 = (N − v)/fps** (o double exato do Resolve),
  `YMax` = `LastValidYOffset` = (N − 1)/fps e `XMax` = X1. O clipe janela na curva pelo **`In`** =
  round((Y0 − início_na_fonte_em_s)/v × fps_timeline). Implementado:
  `tools/inspect_drp.py::build_reverse_timemap`, `drp/writer.py` (`motion_effect_type == "reverse"`).

## 9. Keyframe: cabeçalho e domínio do tempo; flip; modo de composição — 2026-10-02

`confirmado` no Resolve 21.1 por gabaritos do próprio Resolve E pela imagem (conferência quadro a
quadro contra o export do PRODB).
- **Cabeçalho do bloco de keyframes = −(tamanho do registro × N), int32 BE.** Zoom (64 bytes):
  2 → `FF FF FF 80`, 3 → `FF FF FF 40`, 4 → `FF FF FF 00`; posição (16 bytes), 2 → `FF FF FF E0`.
  ⛔ Gravado fixo em −128, o Resolve IGNORA a animação inteira quando há 3+ keyframes (o zoom
  ficava em 1,0 — medido em 3 planos).
- **Tempo do keyframe = o domínio do `In` do clipe** (quadro da fonte com velocidade 1). Gabarito
  com 2 clipes de `In` 200: keyframes 0→100 deixam o clipe parado no valor final; 200→300 animam.
  Uma suposição de "quadros desde o início do clipe" foi testada e está ERRADA.
- **Flip:** filtro Transform, booleano `1a 04 0a 02 28 01`: X no slot 10, paramID `0x32`; **Y no slot
  11, paramID `0x33`** (`confirmado` 2026-10-03, Resolve 21.1: `SetProperty("FlipY", True)` + Export DRT;
  CORRIGE o `pendente` anterior).
- **Modo de composição:** filtro Composite, slot 0, paramID `0x00`, inteiro = `resolve.COMPOSITE_*`
  (21.1: Normal 0, Add 1, Diff 3, Multiply 4, Screen 5, Lighten 10, Luma Mask 17).

## 10. Cropping: frações e Softness — 2026-10-03
`confirmado` (Resolve 21.1, `SetProperty` + export): o Cropping grava os 4 cortes como FRAÇÃO do quadro
da fonte (a API fala em px: `CropLeft` 100 → 0,0347 = 100/2880) e o **Softness no slot 4, paramID
`0x3A`**, double = o valor da API. Edge Feather do Premiere → Softness: fator ≈ 0,105 (`inferido`,
uma calibração pela imagem: Feather 43 ≈ Softness 4–5).

## 🆕 Áudio da timeline: volume do clipe e o que a API devolve — 2026-10-04 (Resolve 21.1, macOS)

- **Volume do clipe (Inspector › Volume)** mora no `EffectFiltersBA` do `Sm2TiAudioClip`: um filtro tipo
  `0x7c`, 5 slots, o volume no slot 0, paramID `0x5f`, **double LE = o valor em dB**
  (`000000020000001e 80 0a1b 087c 4a0f085f1a0b0a0911 <f64> 4a00×4`). Medido com
  `SetProperty("AudioVolume", −6 / +3,5)` + Export DRT; o `FieldsBlob` também muda no export, mas
  NÃO é preciso: um DRT gerado só com o filtro importou com −6 e +3,5 (`GetProperty("AudioVolume")`).
  `confirmado`. De Lá Pra Cá: `drp/writer.py::_volume_ba`.
- `Timeline.GetItemListInTrack("audio", n)` devolve também as TRANSIÇÕES de áudio (Cross Fade) como
  itens: o filme deu 4.252 "itens" = 2.824 clipes + 1.428 crossfades. Contar clipes pelo nome/tipo.
- Trilha de áudio nascida do DRT: subtipo "mono" (36 trilhas no filme); estéreo nativo `pendente`.

### ⭐ Áudio no Resolve 19 — gabarito `gabarito_audio_r19` (19.0.0b.59, Windows, 2026-10-03)
Timeline a 24 com 4 trilhas: A1 estéreo (a timeline vazia já nasce com ela), A2 mono, A3 estéreo, A4
mono; WAV de 4 canais (302,0107 s) e o som de um take ALEXA (2 canais). Gestos do autor na UI.
- **Trilha estéreo × mono:** `<SubType>0</SubType>` = estéreo, `1` = mono (`confirmado` no 19; a pista
  do 21 vale). O clipe estéreo do take leva DOIS canais no `VirtualAudioTrackBA › ChannelsBA`
  (`0x4001`, `0x4002`); o mono, um.
- **Volume com keyframes** (5 no Inspector): o mesmo filtro `0x7c` / slot 0 / paramID `0x5f` do volume
  fixo, com o campo 10 (`52 <len>`) no lugar do valor — **a forma da POSIÇÃO do vídeo**: cabeçalho
  −16·N (int32 BE) e por keyframe `[u32 quadro][u16 0][u16 0x0C][f64 dB]`. O 19 grava o payload
  COMPRIMIDO (`0x81` + zstd); descomprimido, é igual byte a byte ao nosso com `0x80`
  (`drp/writer.py::_volume_ba_kf`). **Tempo = quadro no domínio da FONTE** (o do `In`), como no vídeo:
  aparada a cabeça em 24 quadros (`In` 24), as keyframes seguiram em 142/160/185/212/229.
- **Velocidade constante no áudio** (Change Clip Speed 50%): o `MediaTimemapBA` QHash do vídeo, com
  valores próprios (bit a bit): `YMax` = `LastValidYOffset` = duração − 1/`MediaFrameRate` (23,976, a
  taxa que o Resolve dá ao clipe de áudio — e o nosso molde); keyframe final (X1, X1/r) com
  **X1 = duração·r − 1/taxa da timeline**; `XMax` = X1 (`tools/inspect_drp.py::build_audio_speed_timemap`).
  O clipe SEM velocidade usa a forma compacta `02` + double = duração − 1/23,976 (o writer grava a
  duração crua: funciona, mas difere — `inferido` inofensivo).
- Ao mudar a velocidade de um clipe VINCULADO a outros, o Resolve muda todos (o autor desvinculou).
- **Ponta a ponta no 19** (filme PRODB gerado pelo writer, importado, 36 trilhas): o volume animado
  (6 rampas, payload sem zstd `0x80`) — **conferido pelo autor no Inspector e de ouvido**: `confirmado`.
  A velocidade de áudio (33 segmentos): o mapa é igual byte a byte ao gabarito, mas o ouvido e a volta
  pelo Export ficaram `pendente` (a armadilha do `Export` da timeline aberta, api-scripting.md).
- ✅ **No 21** (2026-10-04, 21.1.0.14, macOS, o mesmo filme gerado no Mac): volume animado (payload `0x80`,
  6 clipes) e velocidade de áudio (33 segmentos) **conferidos pelo autor no Inspector e de ouvido**; pela API,
  a duração na fonte segue a taxa (48-1T02 a 50%: 463 q na timeline, 232 de fonte). `GetProperty("AudioVolume")`
  de clipe com keyframes devolve 0,0 — a API não mostra a curva.
- A API não expõe SOLO nem MUTE de trilha (só `SetTrackEnable`). **SOLO = `<Flags>32` da trilha de áudio**
  (`confirmado` 2026-10-04: o autor apertou o "S" da A2 e só o `<Flags>` dela mudou, 0 → 32; um DRT
  gerado com 32 importou e voltou com 32). De Lá Pra Cá: o som da referência, opção A.
- Pista para a trilha ESTÉREO nativa (`pendente`): no mesmo DRT, a A1 criada pelo Resolve tinha
  `<SubType>0</SubType>` e a A2 criada por `AddTrack("audio","mono")` `<SubType>1</SubType>`.

## 🆕 ⭐⭐ O ROTEAMENTO das trilhas de áudio (Bus Assign) mora na mesa do Fairlight — 2026-10-03 (Resolve 21.1, macOS)

**Sintoma (PRODB, 36 trilhas):** só as 16 primeiras trilhas tocavam; no Bus Assign, da 17ª em diante,
nada (ou "B1s"). "B1s" (send) TAMBÉM é mudo: o medidor da trilha anda, o master não (o autor solou a
A18). Trilhas criadas dentro do Resolve nascem todas "B1o" (99 de 99).

- **Onde:** `FLStudioModelBA` no `FieldsBlob` da `Sm2Sequence` (no `MpFolder`, dentro do clipe da
  timeline), QVariant QByteArray (tipo 12) em formato `qCompress` (u32 BE tamanho + zlib). O nosso
  esqueleto (Resolve 19) traz uma mesa de **16 trilhas** → daí o limite. ~400–560 KB descomprimida.
- **O Resolve RESPEITA a mesa que vem no DRT** (um DRT exportado com 20 roteadas reimporta com 20).
  **Uma mesa MAIOR que a timeline serve** (mesa de 20 numa timeline de 12: as 12 em B1o); MENOR, as
  trilhas além dela ficam sem saída (mesa de 20 em 36: da 21ª à 36ª, nada).
- Entre "16 roteadas" e "20 roteadas" mudam 26 bytes: três vetores de int32, um por trilha (1/0, 0/1,
  −1/0) e dois contadores — e o MESMO para "send" e "out" (só um contador de operações difere): não
  dá para gerar B1o por esses vetores. ⛔ O DRT não tem chave "Bus"/"Routing" fora desse blob; a API
  não expõe Bus Assign (só `GetFairlightPresets`/`ApplyFairlightPresetToCurrentTimeline`, Resolve 20.2.2+).
- **Solução** (`confirmado`: 36 trilhas, todas B1o, A30 chega ao master): a mesa de uma timeline de 99
  trilhas criada no próprio Resolve (todas B1o), guardada (`motor/drp/fairlight_r21_mesa99.bin`, 11 KB)
  e posta no DRT quando há mais de 16 trilhas de áudio. Mesma ideia do esqueleto de 100 trilhas do
  RELINKER (`RELINKER/src-python/tools/make_skeleton.py`), que era um DRP inteiro.
- ⚠️ A mesa é do Resolve 21: no **19** (o piso) `pendente`.
- **CORRIGE (2026-10-03, Resolve 19.0.0b.59, Windows):** a mesa agora é colhida NO 19 (regra do autor:
  formato que muda entre versões = o do 19, que o 21 atualiza ao abrir): timeline vazia + 99 trilhas mono
  pela API (`Timeline.AddTrack("audio","mono")`, 8,5 s), exportada em DRT, `FLStudioModelBA` extraído
  (`motor/drp/fairlight_r19_mesa99.bin`, 9 KB; 603 KB descomprimida). No filme do PRODB (38 trilhas) o
  autor conferiu no Bus Assign: **todas em Bus 1 e o som chega ao master** — trilhas criadas pela API
  também nascem B1o. A do 21 também funcionava no 19 (o 19 a regrava no próprio formato ao exportar:
  489 KB), mas saiu do app. No 21: ✅ `confirmado` (2026-10-04, 21.1.0.14, macOS: filme de 36 trilhas, o autor conferiu Bus Assign e som).


## 🆕 Compound Clip no DRT — 2026-10-04 (Resolve 21.1.0.14, macOS) — 1ª leitura, `inferido`

Para traduzir o NEST do Premiere 1:1 (pedido do autor, 2026-10-04). Gabarito exploratório no 21
(`Timeline.CreateCompoundClip([V1, V2], {"name": …})` sobre a placa do interfone + o insert com zoom 0,5
e Pan 100; o compound com zoom 1,2; Export DRT antes/depois). ⚠️ Regra do autor: o formato vale quando
colhido no **19** — `pendente`.
- O DRT passa a ter **dois `SeqContainer`**: a timeline de fora e a de DENTRO do compound.
- No `MpFolder`: um **`Sm2MpCompoundClip`** (Name, MpFolder, UniqueMediaPoolItemId, `AudioSource`
  `AUDIO_SOURCE_EMBEDDED`, `VideoMetadata`) que CONTÉM, em `<Sequence>`, a **`Sm2Sequence`** de dentro
  (`Parent` = o DbId do compound; `FrameRate`, `Resolution`, `MediaExtents` próprios; `VideoTrackVec`
  vazio no pool — as trilhas estão no `SeqContainer`).
- Na timeline de fora, o clipe do compound é um clipe de vídeo comum com `MediaRef` = o DbId do
  `Sm2MpCompoundClip`; dentro, os clipes apontam para a mídia de sempre, com a transformação de cada um.
- `CreateCompoundClip` só com os itens de VÍDEO deixa o áudio de fora, na timeline de fora.
- O `MediaPoolItem` do compound responde `GetClipProperty("Type")` = `"Compound"`.
- O DISTINGUIR do lado do Premiere: ver `protocolos/prproj/relink-e-geometria.md` §10.5.
- Medido também: o clipe de FORA difere de um comum só em `MediaFilePath` e `MediaReelNumber` vazios e
  `CurrentSelectorIdx` 0; `MediaStartTime` = 3600 (o compound começa em 01:00:00:00), `In` = quadros
  DENTRO do compound (aparado em 20 → 20), `MediaTimemapBA` compacto `02` + (N−1)/fps; dentro, os clipes
  começam em 86400. A `Sm2Sequence` de dentro tem, no `FieldsBlob` (cru, sem zstd), o id do SEU
  `SeqContainer` em UTF-16; o `FieldsBlob` do compound (zstd), o próprio DbId. Os ids do esqueleto do
  writer NÃO se renovam por build — um compound escrito no DRT teria de remapeá-los.
- ⚠️ **NÃO usado** (decisão do autor, 2026-10-04): a API não alcança clipe dentro do compound, e o Fusion
  de dentro viraria "refazer à mão". O De Lá Pra Cá cria o compound pela API depois do Fusion
  (`plugins/resolve-scripting/api-scripting.md`).

## 🆕 O TC de início da timeline no DRT — 2026-10-04 (Resolve 21.1.0.14, macOS)

Mora em dois lugares, e os dois têm de concordar: o `MediaExtents` do `Sm2MpTimelineClip` (início em
SEGUNDOS, double LE) e o `Start` de cada clipe (quadros absolutos). Gabarito: a timeline do R02 exportada
pelo Resolve (começa em 0: `MediaExtents` (0,0, 24,75 s), clipes em 0/250/406). Conferido por import:
o R02 gerado com início 259.200 abriu em `GetStartTimecode()` = 03:00:00:00; o mesmo com 0, em
00:00:00:00, com os clipes nas mesmas posições relativas (`confirmado`). De Lá Pra Cá:
`build_drt(timeline_start_frames=…)` com o `MZ.ZeroPoint` da sequência do Premiere (regra do autor:
"respeitar o TC que veio da origem"); o caminho do Avid segue em 01:00:00:00. No 19: `pendente`.

## 🆕 Text+ (Fusion Title) no DRT — 2026-10-08 (Resolve Studio 21.1.0.14, macOS) — `confirmado` pela imagem

Gabarito do próprio Resolve: `InsertFusionTitleIntoTimeline("Text+")` numa timeline vazia + `Export` DRT.
- O clipe é um **`Sm2TiVideoClip`** com `<PrettyType>Fusion Title</PrettyType>`, `<In/>`, sem `MediaRef`,
  `MediaFrameRate` = taxa da timeline, `MediaTimemapBA` = `02` + f64 BE `(duração − 1)/taxa` (com o do
  gabarito, de 120 quadros, num clipe de 300 o título também tocou inteiro), e a composição em
  `CompositionTable/Sm2TiCompositionTable/CompositionBA`.
- **`CompositionBA`** = `[u32 BE tamanho]` + zlib de um mapa no formato dos FieldsBlob (`[u32 1][u32 4]` +
  `count` int 1, `0_name` string "Composition 1", `0_mediaIdList` lista vazia, `0_data` bytes). Reproduzido
  byte a byte.
- ⛔ **`0_data` na forma `Compressed = true`**: cabeçalho da composição em texto (sem `Tools`, terminando em
  `Compressed = true, }`) + `\0` + `[u32 LE tamanho]` + zlib do bloco `Tools` (com `\0` no fim). Em texto
  puro — até o texto IDÊNTICO ao do `ExportFusionComp` — o título importa, tem a composição, e sai PRETO.
  No bloco interno a saída é **`MediaOut1 = MediaOut`**; o `ExportFusionComp` a reescreve como `Saver`, e
  um `Saver` de verdade não é a saída do título.
- **TC vivo**: modificador `TimeCode` (`tool.AddModifier("StyledText", "TimeCode")`; entradas `Hrs`, `Mins`,
  `Secs`, `Frms`, `StartOffset` em quadros, `FramesPerSecond`, `DropFrame`, `PadDigits`) ligado em
  `StyledText` pela saída `Time`. O tempo 0 é o 1º quadro do clipe: `StartOffset` = o `Start` do clipe dá o
  TC da timeline (medido: quadros 1000/1250/1299 → 01:00:41:16 / 01:00:52:02 / 01:00:54:03 com 86400+1000).
- **Caixa de fundo** = elemento de sombreamento 4 do Text+ ("Blue Border" por padrão): `Enabled4`,
  `ElementShape4` 2, `Level4` 0 (o texto inteiro), `Red4/Green4/Blue4`, `Opacity4`, `Softness4` 0 (o padrão
  1 borra), `ExtendHorizontal4/Vertical4` — o Extend escala com o `Size`: 0,1 = 0,234 × a altura dos dígitos;
  com Extend 0 a folga é ~0,46 × a altura dos dígitos.
- ⚠️ Mudar por script a composição viva de um clipe (`GetFusionCompByIndex` → `SetInput`) NÃO muda o quadro
  exportado (medido com o bypass desligado): calibrar gerando o DRT de novo.
- ✅ **No 19 abre e desenha** (`confirmado` 2026-10-09, Resolve Studio 19.0.0b.59, Win11, scripting externo
  em Python): o DRT do PRODB (`…ROLO03_COM_REF`, 3 Text+ com o cabeçalho "21.1") importou em 2,2 s; nos
  quadros 14400, 119263 e 121560 (canto de baixo) o TC é o da timeline e os dígitos ficam a ≤ 1 px dos da
  referência (melhor encaixe dx/dy 0 ou −1). O traço do Text+ é mais grosso que o da referência (pixels > 200 na
  caixa: Semibold 9.956, referência 8.356, Regular 7.196, Bold 12.590): o Semibold É o achado (não cai no Bold).
  A espessura que sobra pode vir da referência ser um MP4 comprimido (`hipotese`).
- ⛔ **Fonte no Windows: `Font = "Open Sans"`, `Style = "Semibold"` (os nomes TIPOGRÁFICOS, name 16/17).** O
  `OpenSans-Semibold.ttf` do Windows se registra no GDI como família "Open Sans Semibold", estilo "Regular" (name
  1/2); com ESSES nomes o Text+ do 19 não desenha nada (quadro sem o texto). Medido 2026-10-09, 19.0.0b.59, Win11.
- ⚠️ No **19 (Windows)** o `SetInput("Font"/"Style")` na composição viva MUDA o quadro exportado (Regular/Bold/
  Semibold deram imagens diferentes, página Color) — ao contrário do medido no 21.1 (Mac), linha acima. Não se
  separou versão × sistema.
- De Lá Pra Cá: `motor/titulos/textplus.py`.

### 🆕 Várias camadas de texto num Text+ só, com tempos próprios e cor por trecho — 2026-10-23 (`confirmado` pela imagem, Resolve Studio 19.1.4.11, Win11)

Laboratório da trilha de notas do De Lá Pra Cá (ideia do autor: aproximar do gráfico de várias camadas do Premiere/Avid
em vez de empilhar trilhas de Text). DRT escrito pelo app, importado pela API externa, stills na página Color.
- **A composição do clipe "Fusion Title" aceita grafo livre**: `Background1` (transparente, `TopLeftAlpha` 0) →
  `Merge1..N` (Foreground = `TextN`, um `TextPlus` por camada) → `MediaOut1`, com o `CustomData TEMPLATE_ID = "Text+"`
  do cabeçalho mantido. Desenhou as N camadas.
- **Camada que entra e sai no meio do clipe**: `Blend` do `MergeN` ligado a um `BezierSpline` com chaves de DEGRAU,
  `[q] = { 0|1, Flags = { StepIn = true } }` (q = quadro da composição; 0 = 1º quadro do clipe). A troca caiu no
  quadro EXATO (264/288/312/336/360 conferidos contra o Text empilhado).
- ⛔ **String com quebra de linha crua no `StyledText` derruba a composição inteira** (o clipe sai PRETO, como o texto
  puro sem `Compressed`): escrever `\n` escapado.
- **Cor por trecho = modificador Character Level Styling** — o ID de registro é **`StyledTextCLS`**
  (`AddModifier("StyledText", "CharacterLevelStyling")` dá False). No grafo: `CLSk = StyledTextCLS { Inputs = { Text =
  Input { Value = "<texto>" }, CharacterLevelStyling = Input { Value = StyledText { Array = { … }, Value = "" } } } }` e
  o `TextPlus` com `StyledText = Input { SourceOp = "CLSk", Source = "StyledText" }`.
  - Cada entrada: **`{ código, início, fim, Value = v }`** (Value omitido = 0). Códigos medidos: **2401/2402/2403 =
    vermelho/verde/azul do trecho**, **102 = Size**. Gabarito tirado pilotando a UI uma vez (Fusion: nó Template
    selecionado → botão de edição de texto do visor → clique + Shift+→) e escrevendo `GreenClone`/`BlueClone`/`Size`
    no modificador pela API com a seleção viva — o `SaveSettings` mostrou o `Array`.
  - **Início em CARACTERES (não bytes: "·" e "—" não deslocam), a partir de 0, contando o `\n`; o FIM é INCLUSO**
    (com fim exclusivo pintou um caractere a mais).
  - Os títulos de fábrica (`Fusion/Templates/Templates.drfx`) não têm nenhum exemplo de CLS com cor.
  - ⛔ **Resolve 21.1 (Mac, 2026-10-24): a cor CHEGA mas sai BRANCA** — importado o DRT, o `ExportFusionComp` da nota
    mostra o `Array` intacto (o mesmo formato acima; o `ImportFusionComp` também o guarda igual), e o Text+ desenha
    tudo branco. **Exportar e reimportar a MESMA composição (`ExportFusionComp` → `ImportFusionComp`), sem mudar nada,
    faz a cor aparecer** (conferido pela imagem, 18 notas em 0,5 s). No 19.1.4 aparecia direto. ⏳ o 20 (instalar).
    Leitura que ENGANA: `str(tool.CharacterLevelStyling[t])` devolve o `Value` do StyledText (`""`), não o Array —
    olhar pelo `ExportFusionComp`. De Lá Pra Cá: `resolve_externo._recarregar_notas`.
    ⚠️ Mesma noite (21.1 Mac, PRODC com 60 notas, 6 importações): (1) UMA vez a recarga feita LOGO depois do import deixou as notas brancas (60 recarregadas e brancas; uma 2ª recarga coloriu) — não se repetiu com foto entre as etapas, sem foto, nem em projeto novo; (2) UMA vez o Resolve CAIU dentro da recarga (`Signal 11` em `Fusion::FusionDoc::Deserialize` ← `LoadDocScriptVal` ← `fusionscript`, ResolveDebug.txt 19:42:33), com 79 vídeos offline — a mesma importação refeita passou. Intermitentes do Fusion do 21; se voltar, recarregar em lotes com pausa.
- Comparado ao Text da página Edit (corpo 0,035, Open Sans, Anchor topo-esquerda): o Text+ com `Style = "Semibold"`,
  `Size` 0,035, `Center` = a mesma Position, `VerticalTopCenterBottom`/`HorizontalLeftCenterRight` = −1 e
  `HorizontalJustificationNew` 0 fica ~1 % menor e alguns px mais alto — calibrar se for ao produto. Regular = mais fino.
- ⛔ **O Text+ não tem fallback de fonte**: o "→" (U+2192) não existe no Open Sans e sai como quadradinho (o Text da
  página Edit o desenhava). "·", "—", "°" e acentos saem. Usar ">" (ou conferir o glifo na fonte) antes de escrever.
- Cor de CADA trecho com RGB próprio (2401/2402/2403 por trecho; o canal = 1 pode ser omitido) e recuo por espaços
  no início da linha funcionam; Y que muda no meio do clipe = `Center` ligado a um `XYPath` com o `Y` num
  `BezierSpline` de degraus (o X fixo) — medido 2026-10-23, mesma bancada.
- **Colunas exatas com fonte proporcional**: um Text+ por pedaço de linha no X da coluna; a coluna vem da largura
  medida no `.ttf` (PIL `getlength`) — **Size 0,035 do Text+ = fonte de 39 px num quadro de 1920** (Open Sans Semibold,
  calibrado por duas linhas renderizadas: 612 e 376 px). O grupo de linhas de uma nota → `Transform` com o `Center`
  por degrau (XYPath) move a nota inteira. Medido 2026-10-23 (19.1.4); espaços à esquerda só aproximam.
- Roteiro do laboratório: De Lá Pra Cá `tools/bancada_resolve/lab_notas_textplus/` (`lab_notas.py`: variantes ATUAL / A fatiado / B união; `importar.py`; fotos).

- ⭐ NO PRODUTO (De Lá Pra Cá, 2026-10-23 tarde): `motor/drp/notas_textplus.py` + `notas.py` (formato v2). Medido
  com a PRODA real (19 notas → 18 clipes Text+ numa trilha só, a maior com 2 notas; DRT em 0,2 s; import 1,4 s no
  Studio 19.1.4.11 Win11): cabeça "V1 · nome na cor do sinal · TC source", corpo na coluna do nome, duas notas
  empilhadas com folga, acentos e `·` desenhados. As COLUNAS saem de uma tabela de larguras da Open Sans Semibold
  (milésimos do corpo) no código — sem Pillow e sem caminho de fonte (portável ao Mac). ⚠️ Sem fundo, o TC cinza e o
  vermelho perdem leitura sobre céu claro (PRODA q133/q13204) — decisão de desenho em aberto.

## Adjustment Clip ESCRITO pelo app — 2026-10-10 (`confirmado` no Resolve Studio 19.0.0b.59, Windows)

O De Lá Pra Cá escreve o Adjustment Clip a partir da forma nativa do caso U01 (`motor/drp/ajuste_r19.xml`): o
`Sm2TiVideoClip` "Adjustment Clip" SEM a `pLmVerTable` (a correção do teste; o clipe comum do esqueleto também não tem)
e sem `MediaRef`; troca DbId, Start, Duration, o Start do FieldsBlob e a MediaFrameRate. O 19 importou os 2 do caso R04
(PRODUCAO-C: V4 com 11 quadros, V6 com a peça inteira), cada um com 1 nó. ⚠️ A `MediaTimemapBA` da forma veio de
uma timeline de 23,976 — em outra taxa, `pendente`. A LUT vai DEPOIS do import, pela API (`SetLUT`, ver a matriz de
plataforma, "pasta de LUTs do Resolve"): o efeito por canal no Resolve = o da Lumetri no Premiere (1–2 níveis de 255).

## Rampa que começa no MEIO do arquivo (Premiere) — 2026-10-10 (`confirmado`, Resolve Studio 19, Windows, R04)

O `build_adaptive_ramp_timemap` força o 1º keyframe da curva em (0, 0) — a fonte no segundo zero. Na rampa do Avid isso
casava (o mapa de lá cobre do começo). A do Premiere começa no meio da fonte: com o `In` 0 o plano saía do COMEÇO do
arquivo (a claquete do LOU_7292). ✅ A curva ganha uma entrada a 100 % de (0, 0) até a entrada da fonte e o clipe
começa ali (`In` = entrada em quadros da timeline); os keyframes de Motion andam o mesmo `In`. Conferido pela imagem
contra o Premiere: 0,96–0,998 nos planos de rampa (o drone a 29,5× → 1× inclusive). E o eixo X do mapa da rampa do
Premiere é em quadros da TIMELINE (o writer passava a taxa da fonte, como no Avid).

## Composição do Fusion de um clipe da timeline: o TEMPO é o quadro da FONTE — 2026-10-10 (`confirmado`, Resolve 19)

`TimelineItem.AddFusionComp()` num clipe de 100 qps com o `In` em 11,05 s: `COMPN_GlobalStart` 0, `GlobalEnd` 2495 (o
ARQUIVO inteiro, na taxa dele), `RenderStart` 1105 (o `In` × 100). Logo um keyframe do Fusion para um instante da
mídia = segundos × fps do ARQUIVO. Usado no contorno animado do Polygon (`BezierSpline` com `KeyFrames`, o Polyline do
Polygon com `SourceOp`): o wipe do C0296 do R04 bate com a referência (0,99). ⚠️ `DeleteFusionCompByName` devolveu
false na composição vazia criada pela sonda (ficou no clipe da timeline de teste).

⛔⛔ **No Resolve Studio 21.1 (Mac) o tempo da composição começa no `In`** — 2026-11-24, `confirmado` (PRODC R04, DRT do
Ciclo Assist › Conformar importado num projeto de laboratório; `AddFusionComp` puro e composição montada pelo produto):
`COMPN_GlobalStart` = −(quadro da fonte do `In`, truncado), `RenderStart` 0, `RenderEnd` = a duração (LOU_7237, 59,94
qps, In 191 da timeline: −478 / 0 / 122; C0296, 100 qps: −1105 / 0 / 29). O MESMO com `In` inteiro ou com fração no
DRT. Keyframes no quadro da fonte (477…) caem FORA da composição e o Polygon tira o plano INTEIRO: o LOU_7237 saía
preto e o wipe do C0296 sumia — também no conform antigo "DLPC PRODC 21 MAC NOVO2" (a calibração de 0,99 era do 19, no
Windows). ⇒ keyframe = quadro da fonte + `GlobalStart` (no 19, 0: nada muda). Pela imagem contra a referência
(correlação): quadro 560 0,0 → 0,94; 575 0,0 → 0,96; 29 −0,26 → 0,94; 130 0,23 → 0,97; 770 −0,01 → 0,78 (o resto
abaixo de 0,9 é cor e movimento dentro do quadro do 100 qps — a forma confere na imagem). Ciclo Assist:
`drp/fusion_clipe.py::no_tempo_da_comp` (lê o `GlobalStart` da composição montada e remonta), teste
`tests/test_fusion_tempo_da_comp.py`. ⚠️ O `In` com FRAÇÃO (2026-11-23) muda o truncamento: o `GlobalStart` de três
planos passou de −477 para −478 — o deslocamento lido da composição já cobre isso. Resolve 20: `pendente`.
⚠️ Para inspecionar: na página Fusion pelo script, os visores ficam vazios até o `ViewOn`; o `ExportCurrentFrameAsStill`
só exporta o quadro pedido na página **Color** (fora dela devolve sempre o mesmo quadro, calado).

**Em que tempo da composição o Resolve mostra cada quadro da timeline** (medido 2026-10-10, Resolve 19 Windows, R04
LOU_7310: 100 qps numa timeline de 23,976 em TEMPO REAL — 4,17 quadros da fonte por quadro, sem Interpret Footage —,
`In` 2562 quadros da timeline): o quadro k do clipe mostra a
composição em **`floor((In + k) × fps do arquivo ÷ fps da timeline)`** — 10685, 10689, 10694, 10698 (23,976 = 24000/1001
exato). Já o keyframe do Premiere fica no instante EXATO ((In + k) × 100 ÷ 23,976 = 10685,67 / 10689,85 / 10694,02 /
10698,19): convertê-lo com `round` dá 10686/10690 e o Resolve, em 10689, mostra a forma de ANTES do keyframe. Com piso,
o wipe do véu C0296 foi de 0,74 a 0,967 contra a referência. (`prproj/leitura.py`, conversão do `t` da máscara.)
- **Como foi medido — o "relógio" no clipe:** na composição ativa, um `RectangleMask` (Width 1, Height 2) com
  `Center.SetExpression("Point((time-T0)/400, 0.5)")` ligado no `EffectMask` do MediaIn: a borda anda 1/400 da largura
  por quadro da composição; três stills por quadro (com o relógio, sem máscara, com a trilha desligada) dão a coluna
  da borda e daí `time`. ⚠️ Ler `comp.CurrentTime` pela página Fusion NÃO serve: ela mostra a composição do clipe de
  CIMA (um Adjustment Clip na V6) e o tempo não acompanha a agulha movida pela API.
- ⚠️ `SetCurrentTimecode` às vezes não pega (já anotado acima): os stills da rodada anterior do R04 tinham o TÍTULO no
  lugar do plano. Conferir `GetCurrentTimecode() == alvo` antes de cada `ExportCurrentFrameAsStill` e tentar de novo.

**Polyline animado: o mesmo número de vértices em todos os keyframes** (2026-10-10, `confirmado` pela imagem): o
`BezierSpline` do Polygon interpola ponto a ponto, pelo índice. O Premiere guarda cada keyframe de máscara como um
contorno independente — no R04 o LOU_7310 tinha 5, 6, 6 e 5 vértices, e o Resolve mostrava o wipe pela metade onde o
Premiere não mostrava nada (0,40/−0,25 → 0,61/0,998 nos quadros 26/28; o resto é a cor, sem a LUT no teste). Igualar
dividindo segmentos (de Casteljau em t = 0,5: mesma forma, um vértice a mais) — `drp/fusion_clipe.igualar_vertices`.

**Máscara de opacidade Premiere → Polygon do Fusion, calibrada no laboratório** (B14_MASCARA, 2026-10-10, `confirmado`:
borda reta conhecida, render do Premiere 23.2 × Resolve 19 pelo De Lá Pra Cá; `laboratorio-de-midia/resultados/
B14_MASCARA/PREMIERE_RESOLVE.md`):
- **Feather** = largura TOTAL da transição, centrada no contorno, em px da FONTE (10–90 % = 0,915 × Feather; com Zoom
  200 % dobra na tela). **`SoftEdge` = 0,845 × px ÷ largura** (com 1,0 saía 17–20 % mais largo) → ±1 %.
- **Expansion** empurra a borda exatamente N px; **`BorderWidth` = 2 × px ÷ largura** (com 1× andava a metade).
- ⭐ **O número antes de `Flags` em cada keyframe do `BezierSpline` do Polyline é o DESLOCAMENTO: 0, 1, 2…** Com todos 0
  a forma SEGURA até o próximo keyframe (degrau onde o Premiere interpola em linha reta) e o último quadro do clipe fica
  no penúltimo keyframe. Com o índice, os dois batem (±0,7 px).
- ⛔ A estimativa "SoftEdge ~0,025" tirada do LOU_7310 real (perfil alfa numa imagem com cor diferente e textura) estava
  ERRADA — o fator certo é 0,845. Imagem real serve de validador; constante se mede com mídia sintética.
- **Nest e proxy X≠Y** (laboratório B16, 2026-10-10, `confirmado`): máscara no clipe de dentro e no clipe do nest, nest
  com escala, clipe de dentro a 50 %, corte 23,976 → 100 qps dentro do nest, in do nest deslocado, nest de nest, proxy
  1024×540 com W 187,5 / H 200 (solto e em nest), nest e clipe acelerados: Resolve × render do Premiere ≤ 0,7 px e o MESMO
  quadro da fonte (lido na imagem) — `laboratorio-de-midia/resultados/B16_NEST_MASCARA/PREMIERE_RESOLVE.md`.
- ⭐ **Contorno assado quadro a quadro.** O Resolve avalia a composição no quadro INTEIRO da fonte que mostra (o piso); o
  Premiere avalia a máscara no tempo dele (contínuo, ou na grade do nest). O De Lá Pra Cá põe, para cada quadro da
  timeline, a forma do Premiere naquele quadro num keyframe no tempo da composição do Resolve
  (`prproj/leitura._assar_contorno`). ✅ O encaixe do in com velocidade (piso, solto e no nest — `prproj/estruturas.md`, "a grade do nest") e o Resolve ARREDONDA o in ÷ passo: mandar o in já no piso.
**Máscara de opacidade num clipe com Flip → contorno espelhado** (2026-10-10, `confirmado` no R04): no Premiere o Flip
(efeito) vem ANTES da Opacidade, a máscara cai no quadro já espelhado; no Resolve o Flip da Edit vem DEPOIS do Fusion e
espelha a máscara. Espelhar o contorno (x → 1 − x) pelos flips do próprio clipe e dos de dentro (um flip num nest por
cima espelha os dois igual). JUL_7644 (4:23, Flip horizontal): 119/120 de 0,62/0,71 a 0,99/0,97. `leitura._espelhar`
(só opacidade: a máscara de efeito depende da ordem na pilha — não medido).
**Conferência quadro a quadro pelo RENDER do Resolve** (2026-10-10): `AddRenderJob` + `StartRendering` da timeline
inteira (66 s, Fusion + LUT + P&B) em ~8 s no Resolve 19 — muito melhor que stills (1,5 s cada e a agulha que não pega).
`SetCurrentRenderFormatAndCodec("mov", "ProRes422LT")` devolveu False e o render saiu no padrão do projeto (serve).
**Black & White do Premiere → saturação 0 no nó 1 do clipe** (2026-10-10, decisão do autor "ao menos temporariamente";
`confirmado` no Resolve 19): `TimelineItem.SetCDL({"NodeIndex": "1", "Slope": "1.0 1.0 1.0", "Offset": "0.0 0.0 0.0",
"Power": "1.0 1.0 1.0", "Saturation": "0.0"})` → True, e o poste do R04 sai cinza como no Premiere. Vai pelo caminho das
LUTs (`relatorio["luts"]`, entrada sem `cube` e com `saturacao`; casca `aplicarLuts`, Python `drp.luts.aplicar_luts`).
⏳ A fórmula de luminância do Black & White do Premiere não foi medida (laboratório: barras do B09).
⚠️ `ImportFusionComp` num clipe que JÁ tem composição continua não pegando no 19 (o caminho B do `executar` falhou e
deixou uma "Composition 2" vazia que `DeleteFusionCompByName` não apaga): para refazer a composição, reimportar a timeline.

## Pan do clipe de áudio: `EffectFiltersBA` — medido 2026-10-28 (Resolve 21.1, Mac)

`confirmado` por gabarito do próprio Resolve (`TimelineItem.SetProperty("AudioPan", −100/+100)` + `Timeline.Export`
DRT) e pelo render (WAV L 440 / R 1000 Hz em duas trilhas mono: com o pan, esquerda 440 e direita 1000, >100 dB).
- O pan mora SÓ no `EffectFiltersBA` do `Sm2TiAudioClip`, logo depois do `<PriorityIndex>`: 23 bytes fixos
  `0000000200000017800a140890014a0f08601a0b0a0911` + o pan em **double LE** (−100 = esquerda, +100 = direita).
- ⛔ A forma de clipe de áudio do esqueleto já traz um `<EffectFiltersBA/>` VAZIO: um segundo campo ao lado perde
  para o vazio (o Resolve fica com o último) — trocar o existente.
- Sem pan, duas trilhas mono vão ao CENTRO: um estéreo entregue como A1 = canal 1 / A2 = canal 2 sai L = R.

## 🆕 ⛔ Dissolve SEM SOBRA: o B segura a ponta, o A sem cauda DERRUBA o render — 2026-10-29 (`confirmado`, Resolve Studio 19.1.4.11, Win11)

Medido com o `build_drt` do De Lá Pra Cá (Sm2TiTransition de 20 quadros, corte no meio: `Start` 86438, `cutpoint` 10)
entre dois sintéticos de cor sólida com o número do quadro gravado (A vermelho, B azul, ProRes, 500 quadros a 24),
importados por `ImportTimelineFromFile` num projeto descartável e renderizados (ProRes 422):

| caso | o que o DRT pede | Resolve 19 |
|---|---|---|
| com sobra (A da fonte 100, B da fonte 100) | 10 q além do fim de A e antes do início de B | dissolve 38 → 57 liso; no meio, B no quadro 94 da fonte ✅ |
| **sem sobra em B** (B da fonte 0) | 10 q ANTES do quadro 0 de B | **não descarta**: dissolve igual, com B **parado no quadro 0** durante a mistura (como o 21.1 no Mac, 2026-10-28) |
| **sem sobra em A** (A da fonte 452 + 48 = o fim do arquivo) | 10 q DEPOIS do último quadro de A | a timeline importa com a transição (a API lista `Transition` 86438–86458), mas o **render FALHA** no corte: `"Full resolution media not found for A.mov at 01:00:02:00"` (54 %, 52 quadros gravados, o 48 corrompido) |

⛔ O descarte calado do 19 (B058) **não se reproduziu** com dissolve de vídeo; o risco real é o lado A: o editor só
descobre na ENTREGA. Quem escreve o DRT tem de medir a sobra dos DOIS lados antes do `Sm2TiTransition` (o writer do
De Lá Pra Cá ainda não mede). ⏳ o lado A no 21 (Mac) e o dissolve de ÁUDIO sem sobra.

## 🆕 ⭐ POWER WINDOW (janela circular) no `Body` da grade — 2026-11-20 (`confirmado` pela escrita E pelo pixel, Resolve Studio 19.1.4.11, Win11, timeline 1920×1080)

Lida de gestos pilotados na paleta Window (um campo por vez → `SaveProject` → o `Body` da cópia do `Project.db`) e
ESCRITA de volta por `.drx` (`laboratorio-de-midia/lab/resolve_janela.py`): o Resolve aceitou e renderizou.

- ⛔⛔ **O nó tem uma LISTA DE CORRECTORS** no campo 9 (`9.1` repetido); `9.1.1` é o TIPO: **1 = Primaries** (Gain,
  Sat, curvas — tudo o que o banco já mapeava), **4 = Window**. Cada um: `{1: tipo, 3: 1, 6: {2: {1: 1, 3: param…}}}`.
  A cor posta DENTRO do corrector da janela é IGNORADA calada (o Gain 0 ali não escureceu nada; a paleta mostrou 1,00).
  A janela SÓ seleciona: a correção (Gain etc.) vai no corrector 1 do MESMO nó.
- Os parâmetros da janela circular (o padrão da paleta é omitido):

| UI | id | gravado | em pixels (1920×1080) |
|---|---|---|---|
| Size | `0x08500006` | S < 50: 0,002 + 0,01996·S · S ≥ 50: 1 + 0,08·(S − 50) (10/30/50/70/100 → 0,2016/0,6008/1/2,6/5) | raio = **288 × s** (288 = `0x8850000D`) |
| Aspect | `0x08500004` | (50 − A)/50 | a > 0: raio vertical ÷ (1 − a); a < 0: horizontal ÷ (1 + a) |
| Pan / Tilt | `0x0850000B` / `0x0850000C` | (P − 50)·81,92 | o valor JÁ É em px: −409,6 = 409,6 px à esquerda / ABAIXO |
| Rotate | `0x08500001` | −graus/180 | |
| Opacity | `0x08500012` | 0–1 (só fora de 100) | |
| Soft 1 | `0x08500005` | UI × 16 | a borda de 10 a 90 % = o valor × s (escala com Size/Aspect), centrada no raio; rampa ≈ smoothstep de largura 1,8× |
| (tipo) | `0x88500008` | int 2 = circular | |
| Invert | `0x88500009` | int 2 = invertida (ausente = normal) | |
| — | `0x8850000E/F` = 0, `0x88500010` = matriz identidade `{10: {1: 1, 5: 1, 9: 1}}` | | |

- Medido pelo render (quadro branco, janela invertida + Gain 0): raio 288,3 px no padrão; Size 30 → 173,2; Aspect 30 →
  vertical 480,8; Pan 45 → centro x 550,4; Soft 0/5/10 → borda 0,7/80,1/161,1 px. A UI prende o Gain mínimo em 0,01;
  o `.drx` com Gain 0 é aceito e escurece até o preto.
- ✅ **AS CINCO JANELAS (2026-11-20, pilotado, 19.1.4)** — cada janela é UM corrector do nó, com o TIPO no `9.1.1`;
  várias janelas no mesmo nó = vários correctors (medido: circular + curva no mesmo nó). ESCRITAS de volta por `.drx`
  (o corrector capturado + o Primaries com Gain 0) e renderizadas num quadro branco — as 5 aceitas, a forma certa
  (`laboratorio-de-midia/lab/resolve_janelas_tipos.py`).

| tipo (9.1.1) | grupo de ids | o que mora onde |
|---|---|---|
| **3 Linear** | `0x0870xxxx` / `0x8870xxxx` | `…14` os 4 cantos em px (padrão ±384 × ±216 = 768×432, centro na origem, Y para cima) · `…15/16` Pan/Tilt px · `…17/18` escala X/Y · `…09–0C` Soft 1–4 (UI × 16, padrão 20) · `…20` Opacity · `0x88700012` Rotate (−graus/180) · `0x8870000F` = 2 · `0x8870001E` matriz identidade. Inside/Outside DESABILITADOS na UI |
| **4 Circular** | `0x0850xxxx` / `0x8850xxxx` | (a tabela acima) |
| **5 Polygon** | `0x08B0xxxx` / `0x88B0xxxx` | `…06` os pontos em px (padrão ±480 × ±270: render exato 960×540) · `…07/08` Pan/Tilt · `…09/0A` escala X/Y · `…04` Rotate · `…10/11` Inside/Outside (UI × 0,04) · `…14` Opacity · `…02` = 2 · `0x88B00012` matriz. Aspect e Soft 1–4 DESABILITADOS |
| **6 Curve** | `0x08D0xxxx` / `0x88D0xxxx` | `…06` a forma, `…07` a borda INTERNA, `…08` a EXTERNA — três listas de triplas Bézier (ponto, alça de entrada, alça de saída; clique sem arrasto = as três iguais), px, Y para cima; o Resolve GRAVA as curvas deslocadas (Inside 10 → ~27 px para dentro; Outside 20 → ~160 px para fora; `…12/13` = 10/60, ~2,67 px por unidade = 1920/720) — quem escreve calcula as três · `…09/0A` Pan/Tilt · `…0B/0C` escala · `…10/11` o pivô da forma · `…04` Rotate · `…18` Soft 1 (UI/100) · `…19` Opacity · `…02` = 2 · `0x88D00014` matriz |
| **18 Gradient** | `0x08F0xxxx` / `0x88F0xxxx` | `…05/06` Pan/Tilt px · `…03` Rotate · `…0B` Soft 1 (UI × 100, padrão 200) · `…11` Opacity · `…09/0A` = 0 · `…01` = 2 · `0x88F0000D` matriz. Padrão: escurece o lado de CIMA da linha central, o meio da rampa ~104 px abaixo dela |

- **Size por tipo** (a escala gravada): Circular < 50: 0,002 + 0,01996·S, ≥ 50: 1 + 0,08·(S − 50); Linear/Polygon/Curve
  < 50: 0,025 + 0,0195·S, ≥ 50: 1 + 0,06·(S − 50) (10/30/70/100 → 0,22/0,61/2,2/4). Aspect (Linear): Y = X/(1 − a),
  PRESO em 4 (Size 100 ignora o Aspect).
- ⛔ Pilotar: Inside/Outside cinza NÃO recebem o duplo clique — os dígitos + Enter caem no visor e MOVEM A AGULHA
  (pulou de clipe). Conferir pela foto se o campo está habilitado antes de digitar.
- ✅ **A BORDA EM PX (2026-11-20, escrita por `.drx` e renderizada num quadro branco, 19.1.4;
  `laboratorio-de-midia/lab/resolve_janelas_borda.py`):**
  - **Polygon:** a ARESTA vale 0,5; o Inside leva de 0,5 a 1 para DENTRO e o Outside de 0,5 a 0 para FORA, cada lado
    independente e ~linear; comprimento de cada rampa ≈ **1345 × valor gravado + 13 px** (~54 px por unidade da UI):
    0,02/0,08/0,2/0,4 → ~40/120/275/538 px. Um lado em 0 = degrau ali (o perfil "salta" de 0 a 0,5 na aresta).
  - **Curve:** ⛔ o Resolve NÃO recalcula as curvas da borda: escrito só `…12/13` com `…07/08` iguais à forma, a borda
    sai DURA — quem escreve manda as curvas deslocadas (Inside 10 → ~27 px, Outside 20 → ~160 px, a UI). O **Soft 1**
    (`…18`, UI/100) é uma borda SIMÉTRICA na própria forma: UI 10 → 126 px de 10 a 90 %, o meio na aresta.
  - **Gradient:** Soft 0 = corte exato na linha. A rampa sai da linha SÓ para o lado de baixo (o não selecionado) e é em
    S: 1 até ~0,15·L, meio em **0,52·L**, 0 em ~0,93·L (L = o `…0B`; girado 90°, longe da borda: 500 → 253 px, 1000 →
    517 px). ⛔ Quando a rampa passaria da borda do QUADRO ela é COMPRIMIDA (na vertical, 1000 e 1500 terminam ~560 px
    abaixo da linha, o quadro acaba em 540). Tilt positivo SOBE a linha.
- Uso: a Vignette do Premiere 2027 (página Color, `AE.Impact_Vignette_FX`) padrão ≈ janela circular invertida raio
  1136 px, borda 360 px (Size 86,81, Soft 5,704), Gain 0 → 1,08 código de média onde a vinheta age (p95 3, máx 10 no
  canto) — `protocolos/prproj/estruturas.md`.

## 🆕 ⭐⭐ Uma grade REAL de colorista lida inteira (PRODUCAO-H) — o que os testes sintéticos não tinham — 2026-11-20 (`inferido`, Resolve Studio 21.1, macOS; projeto gradeado pelo colorista)

Projeto do autor "PRODUCAO-H" (YRGB Color Managed v2, timeline/saída Rec.709 Scene, 1920×1080 23,976), timelines
`…CONFORM_OK` (a v01, correção exagerada) e `…COLOR_v05` (a final, simplificada pelo feedback). Lido de uma CÓPIA do
`Project.db` (o original não tocado) e cruzado NÓ A NÓ com `Graph.GetToolsInNode()` da API (355 itens casados pelo
`Sm2TiItem_id` = `TimelineItem.GetUniqueId()`). Leitor: `laboratorio-de-midia/lab/resolve_grades_reais.py`.

- **No 21.1 o vínculo clipe → timeline** é `Sm2TiItem.Sm2TiTrack_id` → `Sm2TiTrack.Sequence` (o `Sm2Sequence_id` da trilha
  vem vazio) → `Sm2Sequence.Sm2Timeline_id`; trilha de vídeo = `Type` 0. Grade = `Sm2TiItem.pLmVerTable` → `pActive`.
- **Grupo de clipes** (`Sm2Group`, aqui "BLACK MAGIC" 34 e "PRORES" 33): a `pLmVerTable` dele tem as versões "Pre Clip
  Grade" e "Post Clip Grade" (vazias neste projeto: o grupo só agrupava). `pPreClipVersion`/`pPostClipVersion` vazios.
- **Todo nó leva SEIS janelas-fantasma**: correctors 2, 3, 4, 5, 6 e 18 com só o parâmetro de matriz/modo padrão
  (`0x88300031`, `0x8870001E`, `0x88500010`, `0x88B00012`, `0x88D00014`, `0x88F0000D`). Janela/qualificador REAL = o
  corrector com mais parâmetros que esse. Quem lê não pode contar corrector como ferramenta.
- **Tipos de corrector novos** (o 1 Primaries e as janelas 3/4/5/6/18 já estavam acima):

| tipo (9.1.1) | o que é (pelo `GetToolsInNode`) | ids vistos |
|---|---|---|
| **2** | qualificador **HSL** | `0x0830000E`–`19`, `25`, `26`, `6F`; modo `0x88300001` |
| **9** | **Key** (a paleta Key do nó) | `0x0C30001D` = **ganho da SAÍDA da chave** (0,35 em TODOS os 173 nós da LUT da v01 = a LUT a 35 %); `0x0C300021/24/25/31` com o qualificador (Shrink/Blur: 0,009–0,042) |
| **15** | **Noise Reduction** | `0x0C400001`–`18`; `0x0C400007` = modo (int 4/6), `0x0C40000B` = força (5,2–27,5) |
| **0x10004 / 0x20004** (65540 / 131076) | a 2ª e a 3ª **janela circular do MESMO nó** (o tipo 4 com o índice nos 16 bits altos), num nó com Tracking | os ids da circular |

- **Ids novos no corrector 1 (Primaries)** — `inferido` pela co-ocorrência, valores ainda NÃO medidos pelo pixel:

| id | ferramenta | valores no projeto |
|---|---|---|
| `0x860000BA` / `B8` / `B9` | flag da curva **Lum vs Sat** / **Hue vs Sat** / **Hue vs Lum** (o "pendente" do Lum vs Sat acima) | `{2: n}` |
| `0x86000118` | acompanha Hue vs Sat/Lum (flag) | `{2: 2}` |
| `0x0600007D`/`7E`/`7F` | **Log Grade** (por canal; com Offset) | −0,82…0,08 |
| `0x860000C2`, `C3`–`CA` | **Log Grade** (Shadow/Midtone/Highlight e faixas) | −0,53…0,22 |
| `0x06000004` | **Sat/Hue/Lum Mix** (Color Boost ou Lum Mix secundário — `hipotese`) | −0,04…0,18 |
| `0x0600002E`–`31` | num nó de Noise Reduction (0) | 0 |
| `0x86000051` | com o qualificador HSL | 0,013–0,117 |
| `0x86000606` / `607` | **ColorSlice** (mensagens aninhadas: `606 = {24: …}`, `607 = {12: 14 campos}`) | `pendente` |
| `0x8600011B` | **Auto Color**: texto JSON `{"Version":1,"EnhanceParams":[…]}` no campo 5 | — |
| `0x8850000A` | janela circular (int 0) | — |

- **OFX no nó** (Halation, NTSC-rs): não é corrector — o nó tem o campo **10** com `0xC0000049` = id do plugin
  (`com.blackmagicdesign.resolvefx.halationplugin`; o NTSC-rs de terceiros é `wtf.vala:ntscrs`), `0xC000005E` = contexto
  (`OfxImageEffectContextFilter_<uuid>`) e `0xC0000087 → {21: {1, 2: plugin, 3: contexto, 4, 5: parâmetro…}}`, cada
  parâmetro `{1: nome, 2: valor}`. **Só o que sai do padrão é gravado**: 78 dos 80 Halation da v05 têm só
  `resolvefxVersion` (= Halation no padrão); 2 têm `secondaryStrength` (double) e `ColorSpace` = `REDCOLOR4_COLORSPACE`.
- **Ligações**: nenhum mixer paralelo/camada neste projeto; uma ligação com os campos 2/4 = 1 e 5/6 = 16 (a SAÍDA DA CHAVE
  de um nó para a ENTRADA DA CHAVE do seguinte); as comuns são `{1, 3, 5: 64, 6: 64, 7}`.
- **A grade de timeline**: vazia nas duas (a v01 tem um nó sem nada).
- ⚠️ 24 dos 355 itens têm nº de nós diferente entre o `Body` e a API (`pendente`: OFX? still?).
- ⭐ **MEDIDO PELO PIXEL (2026-11-21, charts no lugar da mídia, still com × sem a grade, LUT 3D 17³ ajustada pelos pares):**
  o piso do método é 1,6 código (8 bits). Grade **só de cor** (curvas, Primárias, Log Grade, Sat/Hue/Lum, Hue/Lum vs Sat,
  ColorSlice, a LUT da v01 sem qualificador): resíduo **1,5–1,8 = o piso** — uma LUT/Lumetri a reproduz INTEIRA (62 clipes
  na v05, 108 na v01). O que NÃO é cor: **Halation** (81 de 177 clipes da v05, resíduo 6,8, 25 % da área > 5 códigos),
  **Noise Reduction** (12,9; no chart de bordas duras ele age nas bordas — superestima), OFX **NTSC-rs** (12,3), **janelas**
  (5,6, 9 clipes), qualificador HSL (3,5 na v05; **14,9** na v01, os 68 qualificadores com a LUT Marvel). ⇒ para o
  Premiere/MC: a cor vai como LUT ou Lumetri; o Halation é a maior lacuna real. Dados:
  `laboratorio-de-midia/saida/bancadas/resolve_felipe_ret/medidas.json`, `lab/bancadas/resolve_felipe_ret_medir.py`.
- O que isso pede ao Conformar (Resolve → Premiere/MC): a LUT com a força da chave (35 %), Halation padrão (sem par
  direto), qualificador HSL, NR, janelas múltiplas com tracking. A medida pelo pixel (charts no lugar da mídia):
  `docs/plano/2026-11-20-felipe-ret-cor-real.md` do Ciclo Assist.

## 🆕 ⭐⭐ O SIZING da página Color (Input / Node / Output) e os KEYFRAMES de cor no `Body` — 2026-11-21 (`confirmado`, Resolve Studio 21.1, Mac; pilotado, um controle por clipe, projeto descartável "LAB COR SIZING", timeline 1920×1080)

Nenhum é o `EffectFiltersBA` (o Transform do Inspector/Edit Sizing): o `EffectFiltersBA` ficou IGUAL em todos os casos.
Como nas janelas, o Resolve grava só o que sai do padrão. Medido pela imagem (still na página Edit × o neutro, ECC):
**Pan +100 = 100 px para a DIREITA; Tilt +100 = 100 px para CIMA; Rotate +10 = 10° HORÁRIO; Zoom/Width/Height em volta do
CENTRO; Flip = espelho no centro; Pitch/Yaw = perspectiva** (termo projetivo y/x).

- **INPUT SIZING** (por clipe): campo **3 do topo do `Body`** (o "nó" da entrada, irmão do `1` que guarda os nós de cor;
  o `3.1/3.2` = resolução da timeline, `3.4/3.5` = a da fonte, `3.6` = o PAR). Corrector **tipo 10** (2D) e **tipo 20** (3D):

| controle | id | gravado |
|---|---|---|
| Width / Height | `0x10300001` / `0x10300002` | valor da UI |
| Zoom | `0x10300003` | valor da UI |
| Rotate | `0x10300004` | graus |
| Pan | `0x10300005` | px ÷ LARGURA da timeline (100 → 0,05208) |
| Tilt | `0x10300006` | px ÷ ALTURA (100 → 0,09259) |
| Flip V / Flip H | `0x10300007` / `0x10300008` | `{2: 2}` |
| Pitch / Yaw (tipo 20) | `0x10B00001` / `0x10B00002` | valor da UI |

- **NODE SIZING** (por nó): corrector **tipo 19** DENTRO do nó: `0x060000E4` Pan, `E5` Tilt (mesmas frações), `E6` Width,
  `E7` Height, `E8` Zoom, `E9` Rotate, `EA`/`EB` os dois Flips (`{4: 1}`; qual é H e qual é V `pendente`), `F0` Yaw,
  `F1` Pitch. A paleta tem "Key Lock".
  ⭐ **A ORDEM** (`confirmado` pela imagem, 2026-11-21): o Node Sizing tem os MESMOS controles e unidades do Input (o
  combinado Pan 100 + Tilt 50 + Zoom 1,3 + Rotate 10 só no nó = o do Input, exato) e age **DEPOIS do Input Sizing, em px
  de SAÍDA e no eixo da TELA**: Input Zoom 1,5 + Node Pan 100 → +100 px (não 150); Input Rotate 10 + Node Pan 100 →
  +100 px na horizontal da tela (não no eixo girado). Num nó do meio da árvore, os nós seguintes (e as janelas deles)
  veem a imagem já transformada; a cor é por pixel e não depende da ordem. Tradução no Premiere: um 2º Transform DEPOIS
  do do Input (`prproj/estruturas.md`).
- **OUTPUT SIZING** (da TIMELINE inteira): na grade da timeline (`Sm2Sequence.pLmVerTable`, `VerType` 1), campo 3, corrector
  **tipo 11**: `0x10500001` Blanking **Top**, `02` **Bottom**, `03` **Left**, `04` **Right** (a FRAÇÃO recortada de cada
  borda: 50 px → 50/1080; Bottom 1060 → (1080−1060)/1080), `09` Width, `0B` Height, `0C` Tilt, `0D` Pan, `0E` Zoom,
  `0F` Rotate, `11` Yaw, `12` Pitch.
  ⭐ **A tarja 2.35 do PRODUCAO-H é o Blanking do Output Sizing** (Top = Bottom = 0,12 ≈ 130 px nas 6 timelines) — por isso
  ela aparecia nos stills com o `MÁSCARA_235.png` offline.
  ⛔ Mexer no Output Sizing troca o editor de nós para **"Timeline"**: o que se faz DEPOIS na paleta (Primárias etc.) vai
  para o grafo da timeline e, sem nó nele, **não grava nada** (a tela mostra o valor; a API e o banco, não). Voltar para
  "Clip" na lista do alto do editor de nós.
- **O que o PRODUCAO-H tinha:** 46 grades com o Input Sizing (Zoom 0,99–1,19, Rotate 0,12) e, no mesmo corrector, uma
  lista de matrizes 3×3 por quadro (`0x10300015/17/1A/1B`, o campo 4 = quadro) — o **estabilizador/tracker de sizing**.
- **KEYFRAMES de cor** (Mark › Add Keyframe; Saturação 60 no quadro 2 e 90 no 20, num clipe que começa em 0): em cada
  corrector, o campo **6 se REPETE**: o 1º, sem tempo, é o valor-base; cada keyframe é um campo 6 com **`1` = o tempo em
  MEIOS-quadros** (quadro 2 → 4, 20 → 40), `2.1` = 2 (dinâmico; o base tem 1) e os parâmetros daquele instante
  (`0x06000005` = 1,2 e 1,8). Um keyframe na faixa Master entra em TODOS os correctors do nó (os vazios também) e no nó do
  Input Sizing. A interpolação é **LINEAR** entre os keyframes (croma de um patch 195 → 198 → 200 → 203 → 206 nos quadros
  2/6/11/16/20) e o valor fica parado antes do 1º e depois do último. ⬜ O tempo conta do início do CLIPE ou da FONTE
  (o clipe medido começa em 0 nos dois); o static keyframe; keyframe na janela; o tracking de janela.
- Leitor: `laboratorio-de-midia/lab/resolve_grades_reais.py`; os stills em `laboratorio-de-midia/saida/bancadas/resolve_sizing/`.

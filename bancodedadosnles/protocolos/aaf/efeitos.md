# AAF — Efeitos

Como os efeitos vivem no AAF do Avid e como extraí-los. Os **fatos consumíveis** (nomes de
OperationDef, params, sinais, regras de valor) estão em
[dados/operationdefs.json](dados/operationdefs.json). A **tradução** desses efeitos para outras
NLEs vive em [../../transversal/](../../transversal/) (modelo neutro).

> Princípio (do RELINKER): o app é um **tradutor**, não um copiador. O importador de AAF do
> próprio Resolve **descarta** os transforms do Avid (3D Warp, SMPTE Wipe) — só velocidade
> sobrevive. Logo, para dar saída fiel a outra NLE é preciso traduzir a **intenção** do efeito,
> não copiar bytes. Ver [../../transversal/modelo-neutro-efeitos.md](../../transversal/modelo-neutro-efeitos.md).

---

## 1. Motion effect / rampa de velocidade — `confirmado` (validado vs rampa real)

O parser lê `SpeedRatio`, `SMPTEReverse`, `PhaseOffset`, `SPEED_MAP`/`OFFSET_MAP` via pyaaf2.
O `Segment` expõe:

| campo | significado |
|---|---|
| `speed_ratio` | float, = tl/src |
| `phase_offset` | int |
| `motion_effect_type` | `constant` \| `ramp` \| `freeze` \| `reverse` |
| `speed_curve` | curva de velocidade |
| `source_offset_map` | `[(tl_frame, src_frame)]` — mapeia frame da timeline → frame da fonte |

O `source_offset_map` é a função de retime **frame-exata** que cobre toda a duração (monotônico).
Numa rampa real Timewarp 100%→152%→100% validada, bateu com o gráfico do Avid.

- **Relink AAF→Avid:** a rampa é preservada nativamente (writer só toca `URLString`).
- **Export para DRT (Resolve):** o `source_offset_map` é traduzido para a curva `MediaTimemapBA`
  do Resolve. Ver [../drt-drp/estruturas.md](../drt-drp/estruturas.md) e
  [resolve-speed-ramp](../../transversal/tempo-e-timecode.md). Método: keyframes lineares densos
  (Douglas-Peucker no offset map) — frame-exato e editável. **Resolvido e validado (2026-06-13).**

---

## 2. Parâmetros geométricos (3D Warp e família) — `confirmado`

`aaf/parser.py::_extract_geometric_params` extrai do 3D Warp / SBlend: `scale_x/y`, `pos_x/y/z`,
`rot`, `crop`, `opacity`, `axis` + `keyframes [{t, scale_x, scale_y, pos_x, pos_y}]` com `interp`
(Shelf/Linear/Spline/Bezier).

**Regra de valor compartilhada** pela maioria dos efeitos geométricos do Avid:
- **Posição:** `DVE_POS_*` / `AFX_POS_*` em **milésimos do frame** → `frac = pos/1000`. `+Y` = cima.
- **Escala:** `DVE_SCALE_*` / `AFX_SCALE_*` em **%** → `fator = v/100`.
- **Rotação:** `DVE_ROT_Z_U` em graus (X/Y = perspectiva).
- **Opacidade:** `DVE_FG_KEY_OPACITY_U` em 0–100.

O **nome do param e o sinal mudam por efeito**, mas a regra de valor é a mesma — ver a tabela de
perfis em [dados/operationdefs.json](dados/operationdefs.json) (`Resize`/`PIP` iguais ao 3D Warp;
`Pan & Scan` com sinal invertido; `FrameFlex` com esquema próprio).

---

## 3. FrameFlex (`SpatialAdapter`) — dois papéis

1. **Transform do usuário** (reframe explícito): `Size`/`Position` em %, semântica invertida
   (`zoom = 100/Size`, `frac_pos = -Position/Size`). Ver `operationdefs.json`.
2. **Reformat automático** (papel mais comum): o MC insere quando a mídia tem aspecto/resolução
   ≠ da timeline. Enum `AFX_SPATIAL_REFORMAT` (timeline) / `_BOUNDS_REFORMATTING_OPTION` (origem):
   `1`=Pillarbox, `2`=Crop, `3`=Keep-Size, `-1`=Stretch. O parser detecta o modo
   (`Segment.reframe_mode`) e avisa na UI quando ≠ pillarbox (precisa ajuste manual no destino).
   🆕 2026-09-27: o **Stretch** é o único que DEFORMA a imagem (sem guardar proporção); é o que
   pede aviso forte para o colorista (ver `transversal/operacoes-de-nle.md` §J.3). A bin do Avid
   (MC 25.6/Win) traz o mesmo `-1` no `AFX_SPATIAL_REFORMAT` do FrameFlex da timeline — medido nos
   9 takes da praia da PRODA_CORTE.02 (mídia 2048×1080). `confirmado`.

---

## 3b. Ganho de áudio (`Audio Gain`) — `confirmado`

`OperationGroup` de operation `'Audio Gain'` embrulhando o clipe de áudio. O nível está num
parâmetro `ConstantValue` cujo valor é uma `AAFRational`: **`level = numerador / 2^29`** (fator LINEAR;
`2^29` = 0 dB / sem alteração). Extração: `int(param.value.numerator)` do 1º param que seja
`AAFRational`. No `.avb` vira um `PanVolumeEffect` (`level`+`level_set=True`, `pan=16384`). `RELINKER/
src-python/aaf/parser.py::_classify_effect` categoria `gain` → `effects[].params.level_num`.

## 3c. Título — Avid Titler+ (`Text Box Text` = blob AVUP) — `confirmado` (texto)

`OperationGroup` de operation `'Avid Titler+ Legacy'` (ou `'Avid Title Tool'`), tipicamente na **V3**
(= `sub-seq 2` do NestedScope do slot de vídeo; `nested.slots[i].segment`). Tem ~40+ params (cores,
posições, tamanhos por sub-elemento — sombra/borda/caixa). O **texto** de cada caixa está no parâmetro
**`Text Box Text`** como blob **AVUP** — MESMO formato do SubCap:

```
[UUID_CFUser 16B] 'PUVA' size(4) 4949 01000000 4949 uuid_le(16) size1(4) size2(4) data(size2)
data = a string em UTF-8, null-terminated (ex.: b'PRODUCAO-A\x00')
```

- **Acesso aos bytes crus:** `param['Value'].data` — o `param.value` do pyaaf2 devolve `[]` p/ esses blobs.
- **Decode:** achar `b.find(b'PUVA')` (o `PUVA` vem DEPOIS de um UUID de 16B — DIFERENTE do SubCap, que
  tem `PUVA` no offset 0), `size2 = b[off+36:off+40]` LE, `data = b[off+40:off+40+size2]`, cortar no
  primeiro `\x00`, `decode('utf-8')`. Ver `../avb/dados/titler-texto.json`.
- **Estilo** (fonte/corpo/cor/posição): params homônimos ambíguos (vários `Size`, `Position`), NÃO
  mapeado — `pendente`. Extração feita: `RELINKER/aaf/parser.py::_extract_title_params` (categoria
  `title`, `effects[].params.text`).
- ⛔→✅ 2026-10-01 (De Lá Pra Cá, U03 do autor no Mac): o texto chegava à Carta só como `params.text`, sem o
  bloco `titulo` que a leitura da BIN monta — e o writer do DRT descartava o título EM SILÊNCIO ("PRODUCAO-A"
  sumiu pelo AAF; pela bin entrava). Agora `aaf/parser.py` monta o mesmo bloco (`titulos/avid.py::do_aaf`):
  U03 idêntico à bin; T01 (Titler+ atual, MQP) 19 de 19 iguais à bin, com estilo. O writer avisa título sem texto.

## 3d. Título — Avid Title+ ATUAL (`MQP Blob` = DB de texto editável) — `confirmado`

**Efeito DIFERENTE do Legacy** (§3c): op `'Avid Titler+'` (sem "Legacy"), AVB effect_id
`E4EEBB07-AFAA-4122-BFA8-0A838BB40A8C`. Guarda **tudo num único blob de TEXTO legível**. Ver
`../avb/dados/titler-plus-mqp.json`. Estrutura (AAF: 6 params; AVB: 4 params):

- **`MQP Blob`** — auid `67a614ac-29b6-4afe-b9cc-8107a5dd3468` (AVB: param vt=4 CFUserParam, MESMO uuid,
  ~50KB). Blob AVUP (`PUVA`) cujo `data` é um DB hierárquico: `Chave = { Value = X }` (~324 chaves).
  **Editável por string/regex** — não precisa decodificar binário. Atributo→chave (por diff de 19
  variações; só 14/324 variam):
  - Fonte + Bold/Itálico: `Text.Font.Name` (string; `{Open Sans`, `{Open Sans Bold`, `Courier`) —
    bold/itálico são VARIANTES do nome, não flags.
  - Corpo: `Text.Font.Size` (fração da altura; 0.0833≈default).
  - Cor do texto: `Material.Main.Base.Red/Green/Blue` (0-1).
  - Sombra: `Shadow.Enable`+`Shadow.Color.*`. Borda: `Material.Profile.Outline.Enable`+`.Solid.*`+
    `Effect.Profile`/`ProfileScale`. BG (sólido fullscreen): `Global.BG.Enable`+`Global.BG.Color.*`.
  - Posição: `Transform.Position.X/Y/Z` (normalizado ~-1..1 do centro; 1 conjunto por caixa de texto).
  - Alinhamento: `Paragraph.Info.Column.Justify` = Left(default/ausente)/Center/Right (+ `JustifyVertical`
    Top/Center/Bottom). Sintaxe `Justify = Right` DIRETA (sem wrapper `{ Value = }`), no bloco
    `Paragraph = { Info = { Column = {…} } }` do texto — só escrito quando ≠ esquerda.
- **Texto**: NÃO está no MQP Blob. Vive num blob CFUser separado marcado `_TTEXT` (UTF-16) com prefixo
  `T+: ` (= nome do clipe). pyaaf2 não expõe como param; extrair por padrão de bytes (achar
  `_\x00T\x00T\x00E\x00X\x00T`, texto UTF-8 antes). Single-box OK; multi-caixa só pega uma.
- **Reconstrução AVB**: `TrackEffect` (eid E4EEBB07) + 2 tracks internas (fg título + bg
  ScopeReference). Override do blob vt=4 (uuid 67a614ac) por uuid do AAF reproduz TODO o estilo+posição
  (mesmo mecanismo do SubCap) — não precisa decodificar chave por chave.

Amostra de mapeamento: `RELINKER/AAFs-modelos/TITLE PLUS/` (19 variações T01-T19 + AVB nativo).

## 3e. Legenda — `SubCap` gerado de um template (Legenda → AAF, v1.1.0) — 2026-10-02

App: `Legenda-Para-AAF/` (GitHub `Lohan-Costa/legenda-para-aaf`; o estado está no
`HANDOFF.md` dele). `BIN AVID/app` e `AAF-TOOL/legenda-para-aaf-main` são cópias da v1.0.0, e
`LEGENDA AVID/app` é a v0.5.14 antiga, que só gerava STL. Gera AAF no navegador com pyaaf2 1.7.1 no Pyodide, clonando
os `OperationGroup` SubCap de `BIN AVID/BIN ORIGINAL/TEMPLATE AAF.aaf` e trocando o texto
(blob PUVA, ver o código `make_puva`).

- **O template é de projeto de FILME 23.976** (`confirmado`, lido 2026-10-02): CompositionMob
  com 11 slots, todos `24000/1001`. TC1 (`PhysicalTrackNumber=1`, FPS 24, non-drop), TC2,
  TC 25 fps, quatro `Pulldown` (PALPD, 2:3 DF e ND, OneToOneNTSC, 24→60) e um `EdgeCode`
  35 mm, além de Picture e SoundMasterTrack.
- ⛔ **Até a v1.0.0, a opção 29.97 DF só mudava a conta, não o arquivo** (`confirmado` por
  leitura e geração): frames calculados a 29.97 entravam numa composição `24000/1001`, e as
  legendas saíam 1,25× atrasadas. Na v1.1.0 (que tem 23.976 / 24 / 29.97 DF), qualquer
  taxa fora 23.976 deixa só **TC1 + Picture + SoundMasterTrack**, com o `edit_rate` novo e o
  TC1 em FPS/Drop da taxa. Os pulldowns e o edgecode descrevem película de 24 quadros e não
  têm equivalente. Isso foi gerado e relido no pyaaf2 (posições exatas nas três taxas), mas
  **ainda não foi importado no Avid em 24 nem em 29.97 DF** (`hipotese` para o Avid). Em
  23.976 a estrutura sai idêntica à da v1.0.0.
- ⛔ **pyaaf2: um objeto só pode ter um dono.** Pôr num `NestedScope` a `Sequence` que ainda
  está em `pic_slot.segment` estoura `AAFAttachError: Object already attached`. O modo
  Dual-track da v1.0.0 **nunca gerou arquivo** (`confirmado`, reproduzido com pyaaf2 1.7.1);
  a correção cria V1 nova. O dual em `NestedScope` ainda não foi aberto no Avid: os
  `ScopeReference` internos do SubCap (`RelativeScope=1, RelativeSlot=1`) vêm do template de
  uma trilha só (`hipotese`).
- O gerador **emenda os clips em sequência**: uma legenda que começa antes da anterior acabar
  empurra todas as seguintes. Por isso cada trilha é ordenada e a saída de cada legenda é
  cortada na entrada da próxima antes de gerar.

---

## 4. Onde ficam os bytes (para escrita em outras NLEs)

- **Avid (origem):** já parseado — não recriar.
- **Resolve/DRT:** transform no blob `EffectFiltersBA` — **decodificado e escrito byte-exato**
  (ver [../drt-drp/estruturas.md](../drt-drp/estruturas.md)).
- **Premiere/.prproj:** XML gzipado — ver [../prproj/](../prproj/).

Fórmulas de conversão Avid→Resolve→Premiere consolidadas em
[../../transversal/modelo-neutro-efeitos.md](../../transversal/modelo-neutro-efeitos.md).

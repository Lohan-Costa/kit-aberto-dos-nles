# PRPROJ — Estruturas

Topologia do projeto multicam do Premiere. Confiança `inferido` (lido de PRPROJ real criado à
mão), salvo onde indicado. Referência completa: `DRAMASYNC/docs/reverse-engineering/premiere-multicam-prproj.md`.

---

## 1. `Media` — o arquivo físico

Representa um arquivo (`.mov`, `.wav`, …).

```xml
<Media ObjectUID="..." ClassID="7a5c103e-..." Version="30">
    <AudioStream ObjectRef="N"/>
    <VideoStream ObjectRef="M"/>
    <RelativePath>../MIDIA MULTCAM/CAM A /arquivo.mov</RelativePath>
    <FilePath>/Volumes/.../arquivo.mov</FilePath>
    <Title>arquivo.mov</Title>
    <FileKey>uuid</FileKey>                 <!-- identifica o arquivo independente de caminho -->
    <AlternateStart>1396450927872000</AlternateStart>  <!-- TC embutido, em ticks -->
    <UseAlternateStart>true</UseAlternateStart>
    <ConformedAudioRate>5292000</ConformedAudioRate>
    <ActualMediaFilePath>/Volumes/.../arquivo.mov</ActualMediaFilePath>
    <!-- <StreamNumber>1</StreamNumber>  ← canal de áudio N de arquivo multi-canal -->
</Media>
```

| campo | papel |
|---|---|
| `AlternateStart` | TC de início do arquivo em **ticks absolutos**. Só em câmeras com TC embutido (`.mov`). WAV sem TC → vazio. |
| `UseAlternateStart` | `true` = usar o TC do arquivo como referência. |
| `FileKey` | UUID que identifica o arquivo independente de path (útil para relink). |
| `StreamNumber` | Canal de áudio de arquivo multi-canal: ausente/`0`=ch1, `1`=ch2, `2`=ch3, `3`=ch4. Cada canal vira um `Media` separado apontando ao mesmo arquivo. |

---

## 2. Cadeia de referência até o arquivo (vídeo)

```
VideoClipTrackItem → SubClip → VideoClip → VideoMediaSource → Media
```

```xml
<SubClip ClassID="e0c58dc9-...">
    <Clip ObjectRef="{VideoClip}"/>
    <Name>arquivo.mov</Name>          <!-- "arquivo.mov - Merged" para merged clips -->
</SubClip>

<VideoClip ClassID="9308dbef-...">
    <Clip>
        <Source ObjectRef="{VideoMediaSource}"/>
        <InPoint>0</InPoint>          <!-- início no arquivo, em ticks -->
        <OutPoint>{dur_ticks}</OutPoint>
    </Clip>
</VideoClip>

<VideoMediaSource ClassID="e64ddf74-...">
    <MediaSource>
        <Media ObjectURef="{media_uuid}"/>   <!-- aponta para o Media -->
    </MediaSource>
    <OriginalDuration>{dur_ticks}</OriginalDuration>
</VideoMediaSource>
```

Para áudio a cadeia é análoga com `AudioClip`/`AudioMediaSource` — ver [audio-adaptativo.md](audio-adaptativo.md).

---

## 3. `Sequence` (o container da timeline)

```xml
<Sequence ObjectUID="..." ClassID="6a15d903-..." Version="11">
    <Node><Properties>
        <MZ.WorkOutPoint>{duracao_total_ticks}</MZ.WorkOutPoint>
        <MZ.ZeroPoint>{tc_mais_antigo_ticks}</MZ.ZeroPoint>
        <MZ.Sequence.EditingModeGUID>795454d9-...</MZ.Sequence.EditingModeGUID>
        <MZ.Sequence.PreviewFrameSizeWidth>1920</MZ.Sequence.PreviewFrameSizeWidth>
        <MZ.Sequence.PreviewFrameSizeHeight>1080</MZ.Sequence.PreviewFrameSizeHeight>
    </Properties></Node>
    <PersistentGroupContainer>...<Links>...<Link Index="0" ObjectRef="{Link}"/></Links></PersistentGroupContainer>
    <TrackGroups>
        <TrackGroup Index="0"><First>228cda18-...</First><Second ObjectRef="{VideoTrackGroup}"/></TrackGroup>
        <TrackGroup Index="1"><First>80b8e3d5-...</First><Second ObjectRef="{AudioTrackGroup}"/></TrackGroup>
        <TrackGroup Index="2"><First>d8143ffe-...</First><Second ObjectRef="{DataTrackGroup}"/></TrackGroup>
    </TrackGroups>
    <Name>MULTICAM SEM MERGED</Name>
</Sequence>
```

- `MZ.ZeroPoint` = TC exibido na posição 0 (ticks). Multicam: `min(alternate_start)` entre câmeras.
- `MZ.WorkOutPoint` = duração total (relativo à posição 0).
- `<First>` de cada TrackGroup é o GUID de tipo (vídeo/áudio/data — ver `dados/type-guids.json`).

### Hierarquia de tracks
```
VideoTrackGroup → Tracks (ObjectURef) → VideoClipTrack (1 por ângulo) → ClipItems → VideoClipTrackItem
```
`VideoTrackGroup` traz `FrameRate` (ticks/frame), `FrameRect`, color management. `VideoClipTrack`
traz `ID` (V1=1, V2=5), `Index`, `MZ.TrackTargeted` (1=ativo, só V1), `MZ.SourceTrackNumber` (V1=0, V2=-1).

---

## 4. `VideoClipTrackItem` — posição na timeline

```xml
<VideoClipTrackItem ClassID="368b0406-...">
    <ClipTrackItem>
        <ComponentOwner><Components ObjectRef="{VideoComponentChain}"/></ComponentOwner>
        <TrackItem>
            <Start>{timeline_start_ticks}</Start>
            <End>{timeline_end_ticks}</End>
        </TrackItem>
        <SubClip ObjectRef="{SubClip}"/>
    </ClipTrackItem>
</VideoClipTrackItem>
```

### Cálculo de posição (caso SEM MERGED)
```python
# WAV é a referência em timeline_position = 0
clip_duration_ticks = clip_out_point - clip_in_point   # in_point=0 para clips completos
track_item_start = sync_offset_ticks                   # vem do sync engine
track_item_end   = sync_offset_ticks + clip_duration_ticks
zero_point       = min(cam.alternate_start for cam in cameras)
work_out_point   = max(item.end for item in all_track_items)
```
Sync offset por TC compartilhado: `cam_TC - wav_TC_at_sync_point`. Sem TC compartilhado (ex.:
câmera PANA): cross-correlation de waveform.

---

## 5. `Link` (grupos sincronizados)

```xml
<Link ClassID="149d4ea5-...">
    <TrackItemGroup><TrackItems>
        <TrackItem Index="0" ObjectRef="{VideoClipTrackItem}"/>
        <TrackItem Index="1" ObjectRef="{AudioClipTrackItem_ch1}"/>
        <TrackItem Index="2" ObjectRef="{AudioClipTrackItem_ch2}"/>
    </TrackItems></TrackItemGroup>
</Link>
```
Um `Link` por câmera por clip — agrupa os TrackItems de vídeo + áudio sincronizados.

> ⚠️ **Ao ESCREVER:** o critério de agrupamento é **sobreposição de TEMPO**, não nome nem ordem. Um
> Link malformado produz um projeto que abre normalmente mas em que o clipe de vídeo **não é
> selecionável** com clique direto. Ver [escrita.md §3](escrita.md).

---

## 6. Merged clips (caso COM MERGED)

Cada câmera vira uma `Sequence` própria com `BE.Sequence.IsMergedClip=true`:
- VideoTrack V1: clip da câmera em `Start=0`.
- AudioTrack A1: o WAV em `Start=-(sync_offset_no_merged_clip)` (pode ser negativo).
- `MZ.ZeroPoint` = `AlternateStart` da câmera; nome `"arquivo.mov - Merged"`.
- A sequência merged é **mono** (`NumAdaptiveChannels=1`) — não "corrigir" para stereo.

O `SubClip` no multicam que referencia um merged clip tem o nome `"arquivo.mov - Merged"`.

> ⚠️ **Ao ESCREVER:** uma câmera mergeada precisa de vários MasterClips, e o `SubClip` de vídeo tem de
> apontar para o MasterClip da mídia bruta duplicada (`camMC`), **não** para o da bin — apontar para
> o da bin fecha uma referência circular e o Premiere **crasha em `AR::AudioPrefetch`** ao abrir.
> Ver [escrita.md §2](escrita.md).

> ⭐ **CORREÇÃO 2026-09-06 — não são "4 MasterClips", são `2 + n_ch`.** O número depende dos
> **canais do som**: 1 de bin (o `" - Merged"`) + 1 `camMC` + **um por canal** do WAV.
>
> | canais do som | MasterClips por câmera |
> |---|---|
> | 2 | **4** ← de onde veio o número original |
> | 5 | **7** ← medido 2026-09-06, gravador de 5 canais |
>
> O "4" estava certo para o material em que foi medido, e virava regra errada em qualquer outro.
> ⚠️ Um gravador de campo com 4, 6 ou 8 canais não é exceção — é o caso comum em ficção.
> Medido gerando um `.prproj` com o `builder.py` do Órbita sobre uma diária real de 5 canais.

### ⭐⭐ O MAPEAMENTO DE CANAIS de um merged clip — medido no A/B, 2026-09-06

`confirmado` — merged NATIVO (`Clip ▸ Merge Clips…`) contra o nosso, na mesma timeline,
Premiere 25.6.5, som de **5 canais**. Sentinela de "canal não mapeado" =
**`18446744073709551615`** (UINT64_MAX), abaixo como `·`.

| MasterClip | `(SourceClipIndex, mSourceChannelIndex)` | `Clips` |
|---|---|---|
| **de bin** (o `" - Merged"`) | `(0,0) (1,0) (2,0) (3,0) (4,0)` — **per-source** | 2 |
| **camMC** (cópia da câmera) | `(0,0) (0,1)` — variante de sequência | 2 |
| **por-canal `k`** | **DIAGONAL**: só o vetor `k` = `(k,0)`, o resto `·` | **N** |

```
por-canal ch0 →  (0,0)   ·      ·      ·      ·
por-canal ch1 →   ·     (1,0)   ·      ·      ·
por-canal ch2 →   ·      ·     (2,0)   ·      ·
```

⚠️⚠️ **A regra "sequência usa uma variante, mídia usa a outra" NÃO decide aqui.** O
MasterClip de bin do merged tem uma **sequência** por fonte (`AudioSequenceSource`) e
mesmo assim usa a variante **per-source**. Seguir a regra escrita produzia
`(0,0) (0,1) … (0,4)` — e o Premiere mostrava os canais em **passo 2**
(`[A1][A3][A5][A7][A9]` onde o WAV cru mostra `[A1][A2][A3][A4][A5]`).

⭐ **E o por-canal carrega N clips, não um:** o slot vivo aponta para o clip de mesmo
índice, então ele precisa existir. Os outros N-1 são cópias de preenchimento, não
mapeadas.

⛔ **Por que isto não se descobre lendo o arquivo gerado:** `NumAdaptiveChannels`,
`ChannelType` das tracks e do master, e a variante do grupo estavam todos com valor
plausível. Só o **diff do XML cru da cadeia inteira** contra um merged nativo mostrou.
É o §7 do [escrita.md](escrita.md) cobrando de novo: *o problema está no que você não
está imprimindo.*

---

## 7. MasterClip no bin

Cada clip no painel Project tem `MasterClip` + `ClipLoggingInfo` + `Clips`. Para a sequência
multicam, o `MasterClip` aponta para `Video/AudioSequenceSource` (que referenciam a `Sequence`
real) e usa `MediaFrameRate = 9223372036854775807` (INT64_MAX) no `ClipLoggingInfo`.

---

## Notas de versão

⚠️ **Esta página foi medida em Premiere Pro 2024/2025.** No 2026 (26.0.2) pelo menos
`Sequence` subiu para `Version="12"` — ver a impressão digital completa em
[relink-e-geometria.md](relink-e-geometria.md) e como ler a versão de um arquivo no
[README](README.md).

`PRPROJ Version="3"` (Premiere Pro 2024/2025). Versões por elemento (`Sequence Version="11"`,
`VideoClipTrack Version="1"`, …) devem ser **copiadas exatamente**. Para outros fps, trocar o
`EditingModeGUID` (ver `dados/type-guids.json`).

## 🆕 Valor binário guardado por HASH (`BinaryHash`) — 2026-10-04 (Premiere 26.0.2)

`confirmado` (PRODUCAO_B, `FINALIZACAOPRODUCAO_B_FINALIZACAO_PARA RESOLVE.prproj`): um `StartKeyframeValue`
binário (`Encoding="base64"`) IGUAL a outro é gravado uma vez só; as demais ocorrências vêm VAZIAS, só
com o atributo — `<StartKeyframeValue Encoding="base64" BinaryHash="1660e736-…"/>` — e o conteúdo está
no elemento de mesmo `BinaryHash` em outro ponto do arquivo. No projeto: 326 vazios, 0 órfãos (o
antigo, 401). Quem lê só o conteúdo do próprio parâmetro perde, calado, o texto das cartelas duplicadas
(o crédito final "sem tradução") e uma máscara duplicada. De Lá Pra Cá: `prproj/projeto.py::valor_inicial`.
- O `Source Text` pode ter QUEBRA DE LINHA (`\r`): a claquete do rolo é "PRODUCAO-B\rRolo Único", com a
  fonte "Monaco" (nome PostScript sem hífen). `inferido`: a fonte é a palavra única que vem ANTES do texto.

## Efeito DESLIGADO: `<Bypass>true</Bypass>` — 2026-10-10 (`confirmado` pelo render, caso R04, Premiere 23.2)

- O "fx" apagado no Effect Controls grava `<Bypass>true</Bypass>` no `<Component>` do `VideoFilterComponent` /
  `AudioFilterComponent` (vale também para os intrínsecos: `<Intrinsic>true</Intrinsic>` + Bypass na Opacidade). O
  componente continua inteiro no XML — parâmetros, keyframes, a máscara (`SubComponent` AEMask) com `Bypass` false nela.
- No render ele NÃO existe: o JUL_7504 do R04 (Opacidade desligada com máscara animada) sai com o quadro inteiro no
  Premiere (render só com a V2, pela ponte); quem lê o XML sem olhar o Bypass traduz a máscara e abre a trilha de baixo.
  O R04 tem 8: 2 Opacidades, 2 Lumetri, 4 de áudio (EQ, Dynamics). Ler: pular o componente com Bypass true — no vídeo e
  no áudio (um Volume desligado não aplica o ganho). De Lá Pra Cá: `leitura.Motion` e o laço do áudio.
- ⚠️ Armadilha de leitura: o `SubComponent` (a máscara) tem o SEU Bypass (false); o que vale é o do componente dono.

## 🆕 ⭐⭐ Premiere 2027 (27.0.0 build 88, oficial em 2026-11-20): a PÁGINA COLOR — `confirmado` no arquivo (Windows)

Medido no dia do lançamento (lab B24_COR_MC, `resultados/B24_COR_MC/PREMIERE.md` §2027; inventário da API
`laboratorio-de-midia/resultados/API_PREMIERE/premiere-27.0.0-win32.json`).

- **O formato quase não mudou:** `Project` 45 → **46**, `VideoStream` 23 → **24** (mesmo conteúdo); nenhum elemento novo
  num projeto sem a página Color. A Lumetri e o ProcAmp renderizam **idênticos byte a byte** ao 26.5.2 (a tradução da
  cor do MC vale sem mudança). API: = 26.5 (o `app.getLookInfo` do Beta 27.1 SUMIU; o QE ganhou `exportFrameBMP/GIF`).
- **A página Color** (aba Import · Edit · **Color** · Export) NÃO é a Lumetri — o próprio Premiere avisa num projeto com
  Lumetri: *"Those controls have moved to the Properties panel. New Lumetri effects can be added from the Effects Panel"*.
  Ela tem dois níveis, **Clip** e **Sequence** ("Sequence Style 1"), e camadas por "+" (*Add Operation*): **Add Clip
  Adjustment**, **Add Clip Style**, **Add Clip LUT**. A camada Adjustment tem os grupos **Color & Contrast** (5
  controles giratórios de 2 eixos — o 1º é Contrast vertical / Pivot horizontal), **Color Shift** (3 rodas) e **Detail** (2).
- **No `.prproj` a página é uma ÁRVORE de `CompoundComponent`** (classe nova `250b3605-8b7a-4687-bf33-f54e312a510e`,
  `CompoundComponentType` diz o papel), pendurada na cadeia do clipe como um componente comum:
  `65537` (contêiner, `ID 3`, `Unique`) → `65541` (nível Clip) → `65538` (a camada, `InstanceName` "Adjust 1") →
  `AE.ADBE Color And Contrast` + `AE.ADBE Color Shift` + `65539` (Detail) → `AE.ADBE Color Texture` + `AE.ADBE Unsharp Mask2`.
  Cada nível tem a sua `VideoComponentChain`. Os efeitos de dentro são `VideoFilterComponent` comuns (params com nome:
  Color And Contrast = Global, Exposure 0, Saturation 1, Contrast 1, Pivot −3, Black, Temperature, Tint, Balance, e as
  zonas Highlights/Lighter/Lightest…). Uma camada é gravada inteira (os 4 efeitos) ao primeiro gesto; só abrir a página
  não grava nada.
- ⛔⛔ **A API vê o grupo como UM componente opaco**: `displayName` "Color Mode Effect", `matchName`
  `AE.ADBE CompoundComponent`, **0 propriedades**. Ler/escrever a grade da página Color = só pelo `.prproj`.
- ⛔⛔ **Leitor que percorre só a cadeia de 1º nível do clipe PERDE a grade da página Color, calado** (De Lá Pra Cá
  `prproj/leitura.py`, Carta): descer nos `CompoundComponent` (`ComponentOwner/Components` → a cadeia de dentro).
  ⚠️ O porquê do "calado": o `CompoundComponent` **não tem `MatchName`** — quem filtra por MatchName vê `None`, e um
  conjunto "não é efeito" com `None` (o do De Lá Pra Cá) o descarta sem aviso. Reconhecer pela TAG `CompoundComponent`
  (ou pela classe `250b3605`). ✅ **(2026-11-20) Fechado no Conformar** (`modulos/conformar/motor/prproj/pagina_cor.py`
  do Ciclo Assist): o Color And Contrast GLOBAL vai na LUT do nó do Resolve pelo modelo do kernel (porte em Python puro,
  ≤ 1e-14 do da bancada); zonas, roda Balance, Color Shift, Texture, Sharpness, camada de tipo desconhecido (Style/LUT)
  e keyframe viram AVISO. Neutros medidos em 36 camadas: Color Shift = md5 de cada blob; Balance neutra
  `AAAAAAAAAAAAAAAAAADgPwAAAAAAAAAA`. A Carta não lê grade de `.prproj` (só escreve a partir de moldes): não se aplica.
  `pendente`: a camada de **Sequence** (onde ela pendura o contêiner não foi visto) e as camadas Style/LUT (o
  `CompoundComponentType` delas).
- ⭐ **GRUPOS** (`confirmado`, pilotado, 2026-11-20): selecionar vários clipes faz surgir a seção **"Selection (n)"**; o
  "+" dela (*Add Adjustment / Style / LUT to selected clips*) cria o grupo — a seção vira **"Group 01"**. No arquivo:
  cada clipe membro ganha um nó **`65542`** (`InstanceName` "Group 01", `ID 2`) dentro do contêiner, DEPOIS do nível
  Clip, com a SUA CÓPIA da camada ("Adjust 2"); a `VideoComponentChain` de cada cópia aponta `<EffectsGroup ObjectRef>`
  para UM objeto **`EffectsGroup`** (classe `f7a3c8e1-2d4b-4f6a-9e1c-8b3d5a7c9e2f`, só `<Name>`). A sequência guarda
  `MZ.Sequence.NextSequenceCustomGroupNumber`. ⛔ **Cada cópia é lida por si**: mudar no arquivo só a do clipe 2
  (Saturation 0) não mudou o clipe 3 do mesmo grupo — a interface sincroniza; quem ESCREVE grava a mesma camada em todos
  os membros. ≈ grupo do Resolve com a grade "Post-Clip" (a ordem Clip → Group no contêiner; pelo pixel, `pendente`).
- Menu do clipe na lista: Copy, Paste Grade to Clip / to Selection, Label, Add to Selected Groups, Remove from Group,
  Reveal in Project, Restore Unrendered. O nível **Sequence** ("Sequence Style 1") pede *Style Presets / Style Modules*.
- Controles (dicas): Color & Contrast = **Contrast/Pivot · Exposure/Black Level · Temperature/Tint · Color Balance
  (roda) · Saturation**; Color Shift = 3 rodas (Width na horizontal); Detail = **Texture · Sharpness/Threshold**;
  ferramentas: Seleção, **Object Mask tool** (máscara automática), Hand. Clicar no botão de Saturation abre um
  VETORSCÓPIO sobre o monitor com a FATIA do matiz sob o mouse (o gesto "na imagem" é por matiz); o arrasto sintético
  sobre a imagem NÃO gravou nada (`pendente`, testar com a mão do autor). **CORRIGE (autor, mesma noite, à mão):** não é gesto
  na imagem — ao clicar num atributo (ex.: Color Shift) o vetorscópio aparece e já acompanha o MOVIMENTO do mouse, sem
  botão apertado e sem ir à imagem; o movimento lateral alarga a fatia (operação ruim). `pendente`: onde ficaram as CURVAS
  e os campos de VALOR numérico (o autor vai explorar o painel).
  ✅ **(autor, 2026-11-20) A página Color NÃO TEM CURVA**, e toda operação é por mouse (vertical faz uma coisa, horizontal
  outra). A **Lumetri continua na paleta de Effects** — perdeu só o painel dedicado (o flutuante) — e grava como antes.
  ⇒ Para quem lê e escreve o arquivo nada muda: são parâmetros. A curva do MC vai pela Lumetri (curvas R/G/B) também no
  2027; a página Color só serve aos controles que ela tem (Contrast, Exposure, Temperature/Tint, Balance, Saturation…).
- ⭐ **AS ESCALAS, pelo pixel** (`confirmado` onde dito; carta B24, 18 clipes com a árvore CLONADA pelo arquivo —
  `premiere_pagina_cor.clonar_pagina` — e um valor ESCRITO por clipe; `resultados/B24_COR_MC/premiere-27.0.0/escalas_medidas.json`).
  Parâmetros do Color And Contrast (limites no arquivo): Exposure −5…5 (0), Saturation 0…2 (1), Contrast 0…2 (1),
  Pivot −3…3 (−3), Black −1…1 (0), Temperature/Tint −100…100 (0); + zonas (Highlights…), Balance (blob).
  - **Exposure E = ganho 2^(E/2) sobre o valor de VÍDEO** ((código − 16)/219, pivô no preto), croma junto (−1 → ×0,707,
    +1 → ×1,414, +2 → ×2,00) — **exatamente o Gain do MC com G = 100·2^(E/2) %** (`confirmado`). Não corta em 235 (vai a
    254,8) ⇒ para o MC: Mas Gain; para o Resolve: Gain do nó / ganho por canal.
  - **Black** = um lift que age só embaixo (16 → 9 / 23 / 28 com −0,1 / +0,1 / +0,3) e some até o meio (`pendente` a forma).
  - **Saturation** não mexe nos cinzas; nas cores preserva a luminância ~LINEAR (não o Y' do MC) (`inferido`).
  - ⛔ CORRIGE (mesma noite, 30 clipes, `escalas2_medidas.json`): **Contrast = potência sobre a LUMINÂNCIA LINEAR**
    (v² = linear, Rec.709), o RGB escalado pela MESMA razão (a cor fica): pivô **Pv = √(0,18·2^P)** em v (o cinza 18 %
    em stops: P −3 → 0,150, 0 → 0,4243, 2 → 0,8487), expoente **γ = C até 1 e 3C − 2 acima** (1,1 → 1,3; 1,5 → 2,5;
    2 → 4,0). `confirmado`: cinzas ≤ 0,1 código no log; cores 0,15–0,29 sem estouro. ⚠️ C > 1 com pivô baixo empurra
    canais acima de 1 — o tratamento do estouro `pendente` (erro até ~70).
  - **Temperature/Tint = ganho CONSTANTE por canal R'G'B'** (igual em todo nível de cinza; `confirmado`): Temp +100 =
    R 1,231 G 0,954 B 0,632; +25 = 1,045/0,995/0,916; −25 = 0,915/1,006/1,170; −100 = 0,807/1,003/1,410. Tint +100 =
    1,761/0,570/1,291; +25 = 1,215/0,918/1,071; −25 = 0,856/1,043/0,956; −100 = 0,007/1,158/0,827 (o R zera). Entre os
    pontos: tabela (`premiere_pagina_cor.TEMPERATURA/TINT`), a lei `pendente`.
  - **Black** = offset de **0,01·B em luz linear** no preto (v' = 0,1·√|B| com o sinal de B, `confirmado` em 6 valores),
    que se desfaz até v ≈ 0,38 (a forma da queda `pendente`).
  - (superado pelo modelo exato abaixo) **Saturation**: nenhum modelo simples de luminância fecha (melhor: luma linear gama 3, pesos 0,206/0,697/0,087 —
    ainda 20 códigos na Sat 0, 64 na 1,5) ⇒ espaço perceptual ou com compressão de gamut (`pendente`; candidato ao REA).
  - ⭐ **A ORDEM: a camada do CLIPE vem ANTES da do GRUPO** (`confirmado`: Exposure +2 e Contrast 0,5 trocados entre
    clipe e grupo — 0,08/0,09 código na ordem clipe → grupo, 45–56 na inversa). = o grupo "Post-Clip" do Resolve.
  - Código: `premiere_pagina_cor.exposure`, `.contrast` (os modelos).
  - ⭐⭐ **O MODELO EXATO, pelo REA (mesma noite)** — `confirmado`, 29 casos da carta a **0,09–1,25 código** de média
    (máx < 5, o Contrast 2 chega a 12,7 num canal estourado): `premiere_pagina_cor.color_and_contrast`.
    - A fonte do kernel vem no próprio Premiere: `PTX\CL\ColorAndContrast.clz` = ZIP com o texto OpenCL em **XOR 0x2B**
      (`ColorAndContrastKernel`; também `.cubin` CUDA e `.cso` HLSL). A ordem: **Exposure → Contrast/Pivot → Black →
      matriz de cor → Saturation** (+ zonas), em luz LINEAR de cena; luminância pela linha Y da matriz XYZ (Rec.709 aqui).
    - Exposure: ×2^E em linear. Contrast: `rgb · (Y / (0,18·2^Pivot))^(C−1)`. Saturation (`SatMinMaxLum`): mistura com
      `(min+max)/2` dos canais e reescala pela luminância (razão limitada a 1/1,5…2,5). Black: offset 0,01·B·rampa
      (rolloff 0,18) com "saturação do black" 0,5.
    - **O HOST converte a UI** (Frida no `cuMemcpyHtoD` do CUDA, struct `ColorAndContrastSharedParams` de 952 bytes):
      Contrast e Saturation iguais até 1; acima, **3C − 2** e **1 + 1,75·(S − 1)**. **Temperature/Tint viram uma MATRIZ
      3×3** de cor (Rec.709). ✅ **A LEI** (38 matrizes lidas pelo Frida, erro médio 0,19 código, pior 0,96 —
      `premiere_pagina_cor.matriz_temperatura_tint`): é uma **adaptação BRADFORD** (Y preservado) do D65 para um branco
      de destino; Temperature e Tint combinam pelo PRODUTO das matrizes. **Temperature**: o branco anda no LOCUS DA LUZ
      DO DIA (iluminantes D), log2(CCT) reta por lado — T ≥ 0: 6487,6 K·2^(−0,0083875·T) (+100 = 3632 K); T < 0:
      6453,3 K·2^(−0,022085·T) (−100 = 29 961 K). **Tint**: RETA no plano uv de 1960 a partir do D65, ângulo −17,56°
      (magenta, +) / 162,44° (verde, −), 0,001155 e 0,000681 por unidade.
      ⇒ Tradução: é um balanço de branco por CAT — no Resolve, ganho por canal com Lum Mix 0 só aproxima (a Bradford mexe
      nos cones, não em R/G/B); exato por LUT/matriz. No MC, idem.
    - O kernel recebe o pixel JÁ LINEAR (quem lineariza é outra etapa da página, com a transferência do espaço de
      trabalho: `PureGamma`/sRGB/PQ/HLG/ACEScct/log no código). A sequência medida: `workingColorSpace` **"Rec. 709"**,
      `isSceneReferred: false`, `compositeLinearColor: true`, tone mapping automático ligado. A lista do 27.0.0 tem 4
      espaços: Rec. 709 · Rec. 2100 HLG · Rec. 2100 PQ · **ACEScct** (o único de cena). `pendente`: medir os outros 3
      (a linearização e o tone mapping de saída mudam a conta; o modelo vale para Rec. 709).
    - Linear = v² nesta sequência (v = (código − 16)/219); quem grava corta cada canal R'G'B' em v ≈ 1,09 (254,75) ANTES
      de ir a Y'CbCr — cortar depois distorce a cor (foi o que fez o Contrast > 1 e a Sat > 1 "não fecharem").
    - ⇒ Tradução: MC e Resolve não têm esses controles (luminância em linear, saturação min/max) ⇒ **LUT calculada pelo
      modelo** é exata; os controles editáveis aproximam (Exposure = Gain do MC/Resolve exato; Temperature/Tint ≈ matriz;
      Contrast/Saturation sem par direto).
  - **A tradução** (por destino): Exposure → MC Mas Gain 100·2^(E/2) / Resolve ganho; Temperature/Tint → ganho por
    canal (Resolve 0x0600001D–1F com Lum Mix 0; MC curvas R/G/B retas — `pendente` no MC); Contrast → curva de potência
    sobre a luminância com a razão (não é a curva por canal do MC nem a do Resolve com Lum Mix 0: reserva por LUT);
    Grupo → Resolve grupo Post-Clip; MC sem grupo (copiar no clipe, depois do CC do clipe).
  - ⛔ Colar grade pela lista (Copy → Paste Grade to Selection) ficou DESLIGADO pilotando; a cópia pelo arquivo funciona.
  - ⛔ `app.openDocument` volta antes de o projeto carregar: esperar `app.project.sequences.numSequences > 0`.
- Pelo pixel (carta B24, valores ESCRITOS no `.prproj`): Saturation 0 → cinza com pesos de luminância ~linear
  (0,21/0,69/0,10; não é o Y' em gama do MC); Exposure +1 → cinza 126 → 172 (não é ×2 em gama 2,2/2,4: o espaço de
  trabalho, `pendente`). Escrever: `laboratorio-de-midia/lab/bancadas/premiere_pagina_cor.py::escrever` (ler: `Arvore`).
- `pendente`: escalas exatas (Exposure, Contrast/Pivot, Temperature/Tint, Black Level), Color Shift, Detail, Style,
  LUT, a camada de Sequence, a ordem pelo pixel, o downgrade (o 26 não conhece `250b3605`) e a tradução para Resolve
  (grupo: Pre/Post-Clip) e MC (sem grupo de cor: por clipe ou camada de ajuste).
- Efeitos de cor da lista do 27.0.0 (inglês): `AE.ADBE Color And Contrast`, `AE.ADBE Contrast`, `AE.ADBE Midtones`,
  `AE.ADBE Color Film` ("Film Color"), `AE.ADBE LUT Transform`, `AE.ADBE HSLMask`; e os da FilmImpact, agora de fábrica:
  **"Color Mixer" = `AE.Impact_Channel_Mix_FX`** (o "Channel Mix" do 26.5 — NÃO é matriz; no espaço 2 = YCbCr, Chroma
  Blue/Red escalam o croma com luma BT.601, a mesma conta do ProcAmp), "Hue/Saturation" = `AE.Impact_Hue_Saturation_FX`,
  "Gradient Tint" = `AE.Impact_Gradient_Tint_FX`. A Saturation do Color And Contrast NÃO é a do MC (2,2 / 28,8 a 0,875).

## Lumetri: as CURVAS RGB e a Saturation, medidas na carta — 2026-11-20 (`confirmado`, Premiere 26.5.2, Windows)

Lab B24_COR_MC (`resultados/B24_COR_MC/PREMIERE.md`). O param **39** (`ArbVideoComponentParam`, `ParameterControlType 9`)
= 4 blocos de 520 bytes (mestra, R, G, B), cada um `u32 tipo, u32 n` + 32 pares (x, y) double; ESCRITO no `.prproj` e
reaberto, o Premiere desenha: eixo = **faixa de vídeo** (0–1 = código 16–235 de 8 bits, nos dois eixos), **spline
natural**, plana fora das pontas (0,07–0,12 código nos cinzas). ⛔ A **mestra PRESERVA O MATIZ** (o canal do meio é
interpolado entre o maior e o menor, em luz ~linear); **R/G/B são independentes** (canal a canal). O param 37 (seção
Curves ligada) já vem `true` na Lumetri nova. ⛔ **Saturation (20) preserva a luminância LINEAR** (Rec.709 sobre gama
2,4). ⛔ O valor do 39 é deduplicado por `BinaryHash` entre Lumetris iguais: para trocar um, dar a cada elemento vazio o
seu conteúdo antes (senão os outros ficam órfãos). E o **ProcAmp** (efeito YUV): Saturation preserva o Y' **BT.601**
em gama; Hue gira ao contrário do MC.

### A cor do MC escrita pela Carta (Ciclo Assist, 2026-11-20, `confirmado` no Premiere 26.5.2 Windows, a PRODA)

- O molde: `cicloMontar` (linha `cor`) faz o Premiere pôr ProcAmp e Lumetri num clipe da sequência de moldes (QE
  `addVideoEffect`, nomes tentados nos idiomas — o QE devolve objeto vazio para nome que não existe); a escrita CLONA os
  dois e grava a Saturation (ParameterID 4 do ProcAmp) e a curva (blocos R/G/B do param 39, BinaryHash novo). A PRODA
  (7 CC) entrou pelo `importSequences` e, regravada pelo Premiere, manteve os 7 (Sat 87,5 e a curva lida de volta).
- ⛔ O molde mora na sequência de moldes, que é a MESMA que a escrita esvazia e reescreve: lido depois do esvaziamento
  ele "some" (os 7 saíram "sem molde" na 1ª rodada).
- ⚠️ **ORDEM — CORRIGE (mesma noite, medido na carta B24, Premiere 26.5.2, `lab/cor_b24_premiere_ordem.py`):** chamando
  `addVideoEffect` ProcAmp e depois Lumetri, a cadeia sai no ARQUIVO (e em `components` da API) **Lumetri → ProcAmp**,
  mas o PIXEL é **Sat → curva** (a ordem do MC): o modelo Sat → curva (ProcAmp 601) bate 0,17–0,25 código de média nos 4
  casos (PRODA 1 e 2, Sat 50 e 150 + curva) e o curva → Sat erra 0,74–2,5; com a chamada invertida (arquivo ProcAmp →
  Lumetri) é o contrário (curva → Sat 0,20–0,57). ⇒ A Carta já escreve a configuração certa. ⛔⛔ **A ordem do arquivo NÃO
  é a ordem do render neste par** (`confirmado` só para ProcAmp + Lumetri): quem compõe efeitos do Premiere PELA ORDEM DA
  CADEIA (o leitor do Conformar, `prproj/leitura.py` → `lut_composta`, com várias Lumetris ou efeitos de cor) precisa
  medir antes de confiar.
  ✅ **A REGRA (mesma noite, `confirmado`, 26.5.2, `lab/cor_b24_premiere_duas_lumetri.py`): o Premiere RENDERIZA a
  `VideoComponentChain` do ÚLTIMO índice do arquivo para o PRIMEIRO.** Duas Lumetris com curvas que não comutam:
  prever na ordem do arquivo erra 24,0 / 24,2 códigos de média; na inversa, 0,19 / 0,16 (cada curva sozinha, 0,17 e
  0,10). O arquivo e a API (`components`) listam ao contrário do render — e o QE põe o efeito novo na FRENTE do arquivo
  (= no fim do render). Corrigido no Conformar (`Motion.cor` invertida).
  ✅ **Também nos efeitos de imagem** (mesma noite, `lab/premiere_ordem_fusion.py`): Gaussian Blur (Legacy) 40 + Basic
  3D Swivel 65° — arquivo [Basic 3D, Blur] sai NÍTIDO (p99 do gradiente 42: desfocou antes de girar), [Blur, Basic 3D]
  sai borrado (8: girou antes). Corrigido no Conformar (`Motion.fusion` invertida; `fusion_clipe.plano` aceita o
  recorte DEPOIS de outro efeito como Merge + Polygon — o insert do PRODUCAO_B, [Crop com máscara, Basic 3D] no arquivo,
  gira e depois recorta; montado e conferido no Resolve 19.1.4).
  ⭐ **DENTRO da página Color é o CONTRÁRIO: a ordem do arquivo É a do render** (Premiere 27.0.0, mesma noite,
  `lab/premiere27_ordem_camadas.py`): duas camadas Adjustment no nível Clip (a 2ª clonada no arquivo, pendurada depois
  da 1ª), Exposure +1 e Contrast 0,5/Pivot 0 trocados — na ordem do arquivo 0,09 / 0,21–0,24 código, na inversa
  22,9 / 32,1 (cada uma sozinha, 0,08). Igual ao Clip × Grupo (o Clip, antes no contêiner, vem antes). O leitor do
  Conformar desce a árvore nessa ordem.
  ✅ **O "+" da interface** (pilotado, 27.0.0, mesma noite): Clip › + › Add Clip Adjustment põe "Adjust 2" à DIREITA da
  "Adjust 1" e, no arquivo, DEPOIS dela na cadeia do nível Clip (`ID 2`), gravada INTEIRA na hora (sem gesto). ⇒ esquerda →
  direita na interface = ordem do arquivo = ordem do render. ⚠️ A camada nova nasce com **Pivot 0** (a 1ª, com −3) — sem
  efeito com o Contrast em 1; e o **param 1 do Color Shift** muda sem grade nenhuma (camada nova; gesto do autor que não
  gradou): estado da interface (`inferido`), fora da conferência de "mexido" no Conformar. Projeto: `LAB COR 27 CAMADAS UI`.
  ✅ **O nível SEQUENCE** (pilotado, 27.0.0, mesma noite; `LAB COR 27 SEQ UI`): mora FORA dos clipes — `Sequence` →
  `VideoTrackGroup` › `ComponentOwner/Components` → `VideoComponentChain` → **65543** (o contêiner da página da sequência)
  → **65540** "Sequence Style 1" (`ID 1`, VAZIA) + **65538** "Sequence Adjust 1" (`ID 2`, a camada comum: Color And
  Contrast, Color Shift, Detail). ⛔ Nada disso existe no arquivo até o 1º "+" (a "Sequence Style 1" da interface é só
  tela); o "+" › Add Sequence Adjustment grava a Style e a camada juntas, a camada DEPOIS da Style (à direita na
  interface), como no nível Clip. Menu: Add Sequence Adjustment / Style / LUT. ⛔⛔ Leitor que lê só a cadeia dos clipes
  PERDE a grade da sequência inteira, calado — o Conformar agora avisa (não traduz).
  ✅ **A ORDEM: o CLIP antes da SEQUENCE** (`confirmado`, pixel, 27.0.0, `lab/premiere27_ordem_sequence.py`): Contrast
  0,5/Pivot 0 na sequência, Exposure +1 no clipe — Clip → Sequence 0,09 código de média, a inversa 22,9 (Exposure →
  Contrast no clipe: 0,10 × 9,4; Contrast → Exposure: 0,09 × 21,4; só a sequência, 0,08). ⇒ a ordem inteira da página:
  Clip → Grupo → Sequence (o Grupo × Sequence não medido junto; cada par sim). `pendente`: o que a Style e a LUT gravam.
  ⇒ **Traduzido no Conformar** (decisão do autor, 2026-11-20: processo automatizado não depende do usuário, e o Resolve
  19.1.4 não cria nó de timeline pela API — `resolve-scripting/api-scripting.md`): a grade da sequência vai na LUT de
  CADA clipe, depois da do clipe (a camada de ajuste fica de fora). A conta composta bate o render do Premiere 27 com
  0,08–0,10 código nos 5 clipes do `LAB COR 27 SEQ ORDEM`. Aproximação: clipes empilhados com transparência recebem a
  grade cada um, não a composição.
  ✅ **A camada LUT** (pilotado, 27.0.0, `LAB COR 27 SEQ LUT UI`): "+" › Add Sequence LUT põe "Sequence LUT 1" à direita;
  NÃO é composta — é um efeito comum **`AE.ADBE LUT Transform`** direto no contêiner, depois da Adjust. Params: 1 LUT
  (índice na lista, 14 = SL BLUE COLD), 2 LUT ID (GUID UTF-16), **3 LUT Blob = a tabela INTEIRA em `ITX3`** (32³ × RGB
  float, 393 256 bytes), 4 Color Space (28 = Rec. 709 Scene), 5 Color Space ID, 6 Data Range (1 = Full Range), 7
  Intensity (100), 8 HDR Highlights, 9 LUT Display Name ("SL BLUE COLD", ASCII). A lista = os looks de fábrica da Lumetri.
  ⚠️ O cabeçalho deste ITX3 é OUTRO: o tamanho da grade no byte 4 e os canais no 8, 40 bytes de cabeçalho (o ITX3 da
  Lumetri o tem no byte 24). R mais rápido, como o da Lumetri (vermelho segue vermelho; cinza 0,5 → 0,32/0,47/0,48).
  Traduzido no Conformar (uma etapa da LUT do nó, na ordem do arquivo; `pendente`: a conferência pelo pixel da LUT no
  Premiere × a nossa amostragem, e o Data Range ≠ 1).
  ⬜ **A Style**: vazia, é o 65540 com a cadeia vazia (nada grava). "Style Presets" / "Style Modules" não abriram navegador
  nenhum neste espaço de trabalho (nem janela nova, nem painel; o menu Window não tem um navegador de estilos visível) —
  `pendente` (a mão do autor). O Conformar avisa uma Style com conteúdo ("camada Sequence Style 1").
  ✅ **(autor, à mão, mesma noite)** "Style Presets"/"Style Modules" abrem um painel FLUTUANTE de escolha (o clique
  sintético não o abriu, ou abriu fora da foto): abas Style Presets | Style Modules, busca, e os módulos **Color And
  Contrast, Color Shift, Contrast Kit, Detail, Film Color, Flare, Midtones, Variable Vibrance, Vignette**; Cancel/Done.
  Escolher um módulo monta na Style um CARTÃO com os controles dele (ex.: "Color / Contrast": Contrast, Exposure,
  Temperature, Balance, Saturation) — na leitura do autor, a Style é um ESPAÇO DE TRABALHO personalizado (as
  ferramentas escolhidas), não um efeito em si. O nível Clip também aceita Style ("Style 1"). `pendente`: o que o
  arquivo grava ao escolher um módulo e ao mexer nele (prováveis efeitos novos: Contrast Kit, Film Color, Flare,
  Midtones, Variable Vibrance, Vignette).
  ✅ **(2026-11-20, `confirmado` pelo arquivo E pelo pixel, 27.0.0)** O módulo "Color / Contrast" escolhido na
  "Sequence Style 1" grava na cadeia da Style (o 65540, até ali vazia) um **`AE.ADBE Color And Contrast` COMUM**, com
  os 108 parâmetros neutros — o MESMO efeito da camada Adjustment (Global `false`, Pivot `0.` como na camada do "+").
  Só escolher não grada; a "Style 1" do nível Clip, sem módulo, entra no arquivo como 65540 de cadeia vazia. ⇒ a Style
  é um CONTÊINER de efeitos, lido como uma camada. Pelo pixel (`laboratorio-de-midia/lab/premiere27_style.py`, carta
  B24, 5 casos de grade de clipe): Style Exposure +1 → Adjust Contrast 0,5/Pivot 0 na sequência dá **0,09 código
  (máx 0,29)** na ordem do arquivo, contra 22–26 na inversa e 18–23 ignorando a Style. A camada LUT da sequência foi
  tirada da cadeia para isolar (editar o arquivo: remover o `<Component Index ObjectRef>` dela basta).
  ✅ Traduzido no Conformar (`motor/prproj/pagina_cor.py`: a Style desce como camada). `pendente`: os outros módulos
  (Contrast Kit, Film Color, Flare, Midtones, Variable Vibrance, Vignette — o MatchName de cada; hoje = aviso pelo nome)
  e os "Style Presets" (o que um preset grava).
  ✅ **Contrast Kit** (escolhido pelo autor, 27.0.0, 2026-11-20, `LAB COR 27 STYLE B`): grava **`AE.ADBE Contrast`**
  ("Contrast"), 6 parâmetros: 1 Contrast `0.`, 2 Midpoint `0.5`, 3 Range `1.`, 4 Pivot `0.5`, 5 Rolloff `0.`,
  6 Highlight Adjust `0.` (o neutro). O cartão da interface mostra OUTROS nomes: **Compression, Range, Highlights**
  (o mapa cartão → parâmetro `pendente`; Compression ≈ Contrast e Highlights ≈ Highlight Adjust, `hipotese`). O
  Conformar o reconhece neutro (sem aviso) e avisa "Contrast Kit" quando mexido; a escala `pendente`.
  ✅ **Os 9 módulos, escolhidos de uma vez** (autor, 27.0.0, 2026-11-20, `LAB COR 27 STYLE C`): a Style grava cada um
  como efeito COMUM na ordem da escolha. MatchName e o valor ao nascer:
  | módulo | MatchName | ao nascer |
  |---|---|---|
  | Color And Contrast | `AE.ADBE Color And Contrast` | neutro (108 params) |
  | Color Shift | `AE.ADBE Color Shift` | neutro (os blobs do neutro da camada) |
  | Contrast Kit | `AE.ADBE Contrast` | neutro (Contrast 0, Midpoint/Pivot 0,5, Range 1) |
  | Detail | contêiner 65539 → `AE.ADBE Color Texture` + `AE.ADBE Unsharp Mask2` | neutro (como na camada) |
  | Film Color | `AE.ADBE Color Film` | ⛔ MUDA a imagem: Negative 0 / Print 0 (índices de estoque), Global Strength 1; +16 params (proteções, balanços de alta/baixa, saturação, HDR) |
  | Flare | `AE.ADBE Flare` | neutro (Flare 0, Threshold 0,5, Slope 1) |
  | Midtones | `AE.ADBE Midtones` | neutro (Midtones 0, Compensation 1, Range 1, Pivot 0,5, Rolloff 0, Highlight Adjust 0) |
  | Variable Vibrance | `AE.ADBE Variable Vibrance` | neutro (Vibrance Shift 0, Skin Tone Protection 0) |
  | Vignette | `AE.Impact_Vignette_FX` (pacote Impact, `_ Applied Version` 260000) | ⛔ MUDA a imagem: Vignette 100, Width/Height 80, Feather 50, Softness 20, Chromatic Aberration 20, Opacity/Master 100 |
  O "muda" foi visto pelo autor na tela ao escolher. O Conformar: neutro = nada; mexido ou Film/Vignette = aviso pelo
  nome. `pendente`: as escalas (nenhum traduzido), os estoques do Film Color, e os Style Presets.
  ✅⭐ **FILM COLOR resolvido (2026-11-20, REA + pixel, 27.0.0)** — `confirmado`:
  - O kernel (`PTX\CL\ColorFilm.clz`, ZIP + XOR 0x2B; `ColorFilmKernel`) NÃO processa pixel: ele MODIFICA uma LUT 3D
    (`ioLUTData`, `inLUT3DSize`), a do estoque Negativo_Print. A LUT vai **EMBUTIDA NO PROJETO**: param **18** = ITX3
    (cabeçalho com o tamanho no byte 4, como a camada LUT; 21³), param **19** = o nome em ASCII ("Fuji ETERNA
    250_Fuji 3510"). Os params 1/2 (Negative/Print, índices 0–14 / 0–5) são só a UI: escrever 7/3 no arquivo NÃO troca
    o estoque — o Premiere usa a tabela gravada (Frida: a LUT enviada seguiu a do param 18).
  - A tabela = a `.cube` de `<Premiere>\LUTs\FilmEmulation\<Negativo>_<Print>.cube` (90 = 15 negativos × 6 prints,
    Adobe 2012, 21³), **byte a byte** (Frida no `cuMemcpyHtoDAsync_v2`, N³×16 bytes, float4 RGBA, R mais rápido).
  - O host (struct `ColorFilmSharedParams`, 232 bytes) com tudo no padrão: Global Strength 1, **Midtone Protection 1**
    (a UI 0 → o host manda 1 − UI), Pivot −0,099 (UI −0,3), forças 1, balanços 0,5 + matriz ≈ identidade, suavização
    3 (smootherstep), matriz Rec.709→XYZ, branco D65, curvas de influência 0,2326/0,4130/0,3930/0,6526, proteção
    0/0/1/1, `mIsNCXV1Enabled` 1. Com isso a `ModifyLUT` devolve o próprio estoque.
  - **Pelo pixel** (`laboratorio-de-midia/lab/premiere27_film_color.py`, carta B24, o Film Color padrão sozinho na
    Style): o render = a LUT do estoque no sinal de vídeo (v = (código − 16)/219): **0,29 código** (tetraédrica; máx
    1,77), trilinear 0,30; "LUT em linear" erra 37, nada 10,5.
  - Traduzido no Conformar (`pagina_cor.py`: o ITX3 do param 18 vira etapa da LUT do nó). ⚠️ Reamostrar a de 21³ numa
    de 33³ piorava (0,42 / máx 4,07): a composta agora usa uma grade que CONTÉM a da ITX3 ((n−1) múltiplo de (m−1):
    41³), exata para a trilinear. `pendente`: o kernel com os controles fora do padrão (força, proteções, balanços,
    Sat Contrast, HDR — hoje aviso), os espaços HLG/PQ/ACEScct (o kernel tem o ramo `mMediaSpace`).
  ✅⭐ **VIGNETTE (2026-11-20, pelo pixel, 27.0.0)** — `AE.Impact_Vignette_FX` (FilmImpact, `.prm` NATIVO: nenhuma fonte de
  shader em texto no binário — a lei exata pede decompilar, `pendente`). Num quadro BRANCO (`laboratorio-de-midia/lab/
  premiere27_vignette.py`), a padrão é **RADIAL** (círculo, não elipse do quadro): 1,0 até ~770 px do centro, 0,904 no
  meio da borda lateral (960 px), 0,506 no canto (1101 px), o meio da borda de cima intacto. Controles (um por vez, branco):
  Vignette 50 e Master 50 dão o MESMO resultado e mudam a FORMA (a borda lateral deixa de escurecer), não só a força;
  Width 60 estreita na horizontal; Height 60 quase não muda; Scale 50 encolhe muito; Feather 20/80 endurece/suaviza;
  Roundness 50 mais retangular; Opacity 50 ESCURECE mais (0,36 no mínimo); **Softness 0/60 não muda nada no branco**
  (desfoque da região) e a Chromatic Aberration idem — os dois só aparecem em imagem real.
  ⇒ No Conformar: a forma PADRÃO vira o nó "Vinheta" no Resolve = janela circular invertida raio 1136 px, borda 360 px,
  Gain 0 (`drt-drp/estruturas.md` §POWER WINDOW), depois da LUT — provado pelo produto (`drp.cor_mc`, nós "Cor" →
  "Vinheta", a LUT no nó 1): 1,08 código de média onde a vinheta age, p95 3, máx 10 no canto. Softness/aberração ≠ 0 =
  aviso; qualquer outro controle mexido = aviso sem tradução.

## Lumetri: a LUT EMBUTIDA no projeto (`ITX3`) e a intensidade — 2026-10-10 (`confirmado` pela imagem)

Caso real R04 (PRODUCAO-C, projeto salvo no Premiere 22.6 e no 23.2, Windows): a adjustment layer
"LUT-teal and orange" tem uma Lumetri com look criativo de um `.cube` EXTERNO (`Z:\LUT\MARVEL_TEAL_AND_ORANGE_LUT004.cube`,
o disco não existe mais) — e o projeto carrega a LUT inteira:
- Parâmetro **"Embedded LUTs"** (`ArbVideoComponentParam`, ⛔ CORRIGE (mesmo dia): **ParameterID 98** — o 97 é o vizinho;
  os outros do Creative: 23 = ligado, 24 = caminho do .cube em UTF-16LE base64, 26 = Intensity, 96 = nome do look),
  `StartKeyframeValue` base64 com `BinaryHash` (o blob no fim do arquivo). Conteúdo: 20 bytes (hash) + **`ITX3`** + u32 LE
  N (pontos) + u32 LE 3 (canais) + 32 bytes (zeros e três 1.0f) = 60 bytes de cabeçalho; depois N³ × 3 float32 LE, **R
  varia mais rápido, depois G, depois B** (a ordem do `.cube`). Os nomes e a cadeia ficam num 2º blob, um XML de
  `<shader>`s (grupo "Look" com `__Embed "1"` e `__Preset "<caminho do .cube>"`).
- ⚠️ Um projeto pode ter VÁRIOS blobs `ITX3` (aqui um de 33 e um de 16 pontos): o da camada é o que o parâmetro DELA
  aponta — o começo do valor que a API devolve para "Embedded LUTs" (lido como UTF-16) é o cabeçalho do blob.
- **A intensidade** ("Intensity" do Creative, aqui 50): o resultado é `(1 − i) × imagem + i × LUT(imagem)` misturado no
  espaço da IMAGEM (gama), não em linear. Medido: quadros do Premiere 23.2 com a camada × sem a camada + a LUT aplicada
  por fora (trilinear) — erro médio 0,52/255 a 50 % em gama; 2,39 em linear; 9,8 a 100 %; 10,6 sem LUT. Logo a LUT a
  50 % pode ir como um `.cube` já misturado com a identidade nos pontos da grade (exato também na interpolação).
- Uso: Premiere → Resolve, a adjustment layer vira Adjustment Clip com essa LUT no nó (o De Lá Pra Cá).
- ⭐ **Lumetri no MASTER CLIP ("Source Clip Effect")** (2026-10-10, `confirmado` pela imagem, R04): o `MasterClip` tem o
  SEU `<VideoComponentChain ObjectRef>` (fora da timeline) — o efeito vale para toda instância do clipe, em qualquer
  sequência, ANTES dos efeitos do item. Caminho: `TrackItem → SubClip → MasterClip (ObjectURef) → VideoComponentChain →
  Component`. No R04 os 16 master clips da câmera em log (PRJ-*) têm uma Lumetri só com a **Input LUT** da Correção Básica:
  **ParameterID 3 = Correção Básica ligada, 4 = caminho da Input LUT (UTF-16LE base64)**; a LUT vem no mesmo blob 98
  ("Embedded LUTs"). Vale a **100 %**: o "Intensity" **123** do mesmo efeito não é dela (a 100 % o plano bate com o render
  do Premiere a 2,3/255; a 50 % fica a 9,2; sem LUT, 18,5). ⚠️ O Creative ligado (23) com o caminho (24) VAZIO grava
  `/v4=` (FE FF): sobra uma marca de ordem de bytes que não é caminho. Quem lê só os efeitos do item deixa todo plano
  em log CINZA. De Lá Pra Cá: `leitura._lut_do_master` → a LUT no nó 1 do clipe depois do import.
- ⭐ **Curvas RGB da Lumetri** (2026-10-10, `confirmado` pela imagem, R04): **37** = seção Curves ligada; **39** = as
  curvas, 4 blocos de 520 bytes (mestra, R, G, B), cada um `u32 ?, u32 n` + 32 pares (x, y) em double 0–1; identidade
  = (0,0)–(1,1). A interpolação é **spline cúbica natural**, plana fora do 1º/último ponto: medido pixel a pixel (Premiere
  23.2 com a curva × o mesmo plano no Resolve sem ela, PRJ-0006-147, 3 pontos) natural 1,4/255, PCHIP 2,9, reta 4,6, sem
  curva 22,7. As curvas HSL (42 Hue vs Sat, 106 Hue vs Hue, 108 Hue vs Luma, 110 Luma vs Sat, 112 Sat vs Sat) são blocos
  de 520 bytes `u32 tipo, u32 n` + pontos; **n = 0 é a curva padrão**. Temperatura = 7, Tint = 8 (0 = neutro).
  No R04: 69 Lumetri de plano, quase todas só a curva MESTRA (R/G/B identidade); 12 com Luma vs Sat, 7 com Sat vs Sat,
  3 com temperatura/tint (⏳ sem tradução — aviso). Levado ao Resolve como UMA LUT 33³ por plano, composta: Input LUT
  do master clip → look → curvas (a ordem canal × mestra não medida). R04 inteiro contra a referência: diferença de cor
  média 26,1 → 2,8/255, correlação 0,979 → 0,993. De Lá Pra Cá: `leitura._lumetri_cor`, `lut_composta`.
- **Curvas de saturação** (`parcial`, medido 2026-10-10 no R04): os pontos de 110/112 são (x, y) com y = DESLOCAMENTO
  sobre a linha neutra (0); spline natural entre eles. Ganho de saturação = **1 + y(x)**, x = luma Rec.709 (Luma vs Sat)
  ou saturação HSL (Sat vs Sat); a cor se afasta da média RGB (o centro média × luma ficou perto do piso da medida:
  um plano preferiu cada um). PRJ-0006-271 2,03 → 1,35/255; A030_C026 1,64 → 1,19. As outras HSL (42/106/108) não medidas.
- **Balanço de branco** (`parcial`, um ponto): ganho por canal no domínio GAMA, ANTES das curvas — temperatura −17,25 +
  tint +10,59 → R 0,9834, G 0,9990, B 1,0933 (A030_C062: 7,1 → 1,25/255; em linear 1,34). Fora desse ponto o De Lá Pra
  Cá escala linearmente e avisa. ⏳ medir outros valores no laboratório (o parâmetro numérico aceita `setValue` pela API).
- Ordem dentro da Lumetri usada: Input LUT → balanço de branco → look → curvas RGB → curvas de saturação. R04 inteiro:
  cor média 2,78 → 2,41/255; 493–525 9,8 → 1,9; 728–768 5,9 → 1,7.
  Ferramentas: `MIDIAS DE TESTES/…/R04 PRODUCAO-C/ISOLADO/LUT/` (as duas `.cube` extraídas).

## Motion: o nome do parâmetro de escala e o valor que vale — 2026-10-10 (`confirmado`, caso R04)

- O parâmetro 2 do Motion se chama **"Scale"** com o Uniform Scale ligado e **"Scale Height"** com ele desligado (o 23.2
  renomeia ao salvar; no original 22.6 era "Scale" em todos). O 3 é "Scale Width", o 4 (nome " ") é o Uniform Scale.
  ⚠️ **O 26.5.2 (Windows, 2026-11-20) NÃO renomeia:** com o Uniform Scale desligado o param continua "Scale" (= a
  ALTURA). Reconhecer o modo pelo param de nome em branco com `false`, nunca pelo nome "Scale Height".
  Ler pelo `ParameterID`, ou tratar os dois nomes como o mesmo.
- ⛔ **Sem keyframe, o valor que vale é o `StartKeyframe`, não o `CurrentValue`.** 8 escalas do projeto original de 2023
  (não mexido por script) e 1 do PRODUCAO_B têm os dois diferentes (CurrentValue 28 / 54,7, StartKeyframe 50): a API do
  Premiere (`getValue`) devolveu SEMPRE o StartKeyframe e a imagem confirma. O leitor do De Lá Pra Cá preferia o
  CurrentValue: um plano de 50 % saía "28 %, quadro dentro do quadro" no Resolve. Com keyframe, vale o keyframe (§10.5 do
  relink-e-geometria); sem instante, o CurrentValue fica como antes.
- Escala NÃO uniforme no Resolve: Zoom X e Y separados (`zoomX`/`zoomY` do Transform do DRT) — o leitor levava a média.

## Time Remapping (rampa de velocidade) — 2026-10-10 (`confirmado` pela imagem, caso R04, Premiere 22.6/23.2)

- No `VideoClip`: `<TimeRemapping ObjectRef>` → `TimeRemapping` → `<Keyframes ObjectRef>` → um `TimeComponentParam` com
  `<Keyframes>ticks,FONTE_s,tipo,…;</Keyframes>`: o tempo é o do CLIPE (o domínio do `InPoint`, em ticks), o valor é o
  tempo da FONTE em segundos. Tipo **6** = canto (a velocidade muda de uma vez); o par **7 → 8** = transição
  suavizada — a velocidade vai em RETA da do trecho de antes (v1) à do de depois (v2):
  `s = s7 + v1·u + (v2 − v1)·u²/(2T)`, u = t − t7, T = t8 − t7. Confere com o projeto (s8 − s7 = T·(v1+v2)/2 em todas
  as rampas) e com a imagem do Premiere (3 planos, ±0,05 s de fonte — o desvio fixo do proxy 60p de um 100p). Sem
  rampa: ausente, ou a identidade (0,0)…(D,D) com tipo 6.
- ⭐ **Tipo 7 com INFLUÊNCIA = Bézier na velocidade** (2026-10-10, `confirmado`): campos do 7 `ticks,fonte,7,0,I,0.0001,I,0`
  (I em %, 44,5–57,5 no R04; o 0.0001 muda de lugar entre aceleração e desaceleração — sem efeito medido). Com I ≠ 0 a
  velocidade vai de v1 a v2 por uma Bézier cúbica no plano (tempo, velocidade) com P0 = (0, v1), P1 = (I·T, v1),
  P2 = (T − I·T, v2), P3 = (T, v2) — as alças horizontais do gráfico de velocidade; a área é a mesma da reta (fecha em s8).
  Com os campos zerados (`7,0,0,0,0,0`), a reta acima. Medido casando cada quadro da referência exportada com o quadro da
  MÍDIA: A030_C026 (44,5 %) 13/13 exatos; A030_C062 (48,5 %) 14/15 e o outro a 0,05 quadro da borda (a reta errava até 8
  quadros da fonte); PRJ-0006-168 (zerado) exato pela reta. `leitura._bezier_velocidade`.
- ⛔ CORRIGE (2026-10-10): com Time Remapping a `PlaybackSpeed` do clipe **CONTA** — o tempo do clipe anda `vel` por
  quadro da timeline e a fonte é a curva desse tempo. LOU_7292 (1,2× e rampa, trecho de inclinação 1, 60 qps): 3,003
  quadros da fonte por quadro = 1,2 × 2,5025, começando no piso da grade de 1,2× (2208, não 2210). A leitura antiga
  ("a curva pura") veio de stills a olho.
- ⭐ **O keyframe de EFEITO (Motion…) num clipe com rampa está no tempo da FONTE**, não no do clipe: a rotação do drone
  A031 tem keyframes em 40,1 s e 45,9 s, dentro do trecho 39,9–45,8 s da fonte que o plano mostra (e dois velhos em
  1,8 s e 3,0 s, de antes da rampa). Traduzido quadro a quadro, a rotação no Resolve bate (0,15 → 0,96).
- Para outro NLE: amostrar a FONTE em cada quadro do plano (a regra do Avid — cada programa interpreta a curva do seu
  jeito). O De Lá Pra Cá: `motor/prproj/leitura.py` (`_remap_do_clipe`, `_remap_fonte`), `tests/test_rampas_premiere.py`.

- ✅ **Laboratório B22_RAMPAS (2026-10-12, Premiere 23.2 Windows; `lab/bancadas/premiere_rampas.py`)**: o Time Remapping
  ESCRITO no XML (os dois objetos como no R04 — `TimeComponentParam` "Speed" v8 + `TimeRemapping` v2 — e `InPoint`/
  `OutPoint` no tempo do CLIPE) abre e renderiza. Placa B02 23,976 (quadro em código de barras), 48 quadros por clipe:
  **A** 1,2× → transição 7→8 (influência 50 %) → 1,9×: **48/48 = piso(`_remap_fonte`)**; **B** o IN DENTRO da transição
  (2× → 0,6×; "começa em curva"): **48/48**. O Premiere mostra o quadro da fonte = PISO da posição exata que o leitor
  de produção calcula — inclusive com o clipe aparado no meio da curva.
- ⛔ **ESCREVER Time Remapping que começa fora do 0 da mídia** (B22 Resolve → Premiere, 2026-10-12): com o 1º keyframe em
  (0; 15,56 quadros) o Premiere mostrou o quadro 0 da MÍDIA no 1º quadro do clipe. A forma que funciona (a do R04): a
  curva começa em (0, 0) a 100 %, os keyframes do plano andam I quadros (I INTEIRO = teto da 1ª posição) e o `InPoint`
  = I. ⚠️ I fracionário (15,564) deslocou o plano meio quadro (35/48) — o Premiere encaixa o In na grade (o mesmo do B18).
  Assim: **48/48**. `lab/bancadas/premiere_rampas.py::de_posicoes`.
- ✅ **O ESCRITOR no app e o Premiere 26 (2026-11-26, Mac, B34 — Ciclo Assist `spikes/velocidade/b34.py`)**: a peça do
  lab virou `modulos/conformar/motor/prproj/remap.py` (de_posicoes, objetos, pendurar) e a Carta a usa (Avid → Premiere:
  rampa e congelado eram "fora"). Placa B30_A 23,976: R1 100 % → curva → 200 %, R2 começando DENTRO da curva
  (200 % → 60 %), R3 CONGELADO (a curva deitada: cantos com a mesma fonte) — o Premiere 26.0.2 renderiza **48/48 =
  piso(posição) nas três**; a volta inteira Premiere → MC (Conformar, gráfico de posição) → Premiere (Carta) **48/48 nas
  três**, o mesmo quadro do original. ⚠️ O `.prproj` regravado pelo ElementTree sai com `<Clip ObjectRef="101" />`
  (espaço): o Premiere aceita, o leitor do Conformar não acha o clipe (0 planos, sem aviso) — salve pelo Premiere antes
  de ler, ou leia tolerante.
- ✅ **`TimeInterpolationType 2` = OPTICAL FLOW** (confirma a hipótese de 10.5, PELA IMAGEM): 50 % constante
  (`PlaybackSpeed` 0,5) com 2 → nas posições inteiras o quadro exato; nas x,5 o quadro sai DEFORMADO (dígitos
  "derretidos", fantasma fora do lugar — fluxo óptico, não mistura). Ausente = Frame Sampling e 1 = Frame Blending
  seguem `hipótese`.

## Alinhamento do título (`Source Text`) — 2026-10-10 (`confirmado`, Premiere 23.2)

- O alinhamento do parágrafo é o **campo 4 da tabela do documento** do FlatBuffers do `Source Text` (o mesmo caminho do
  corpo: 12 bytes de cabeçalho → raiz → campo 0): ausente = 0 esquerda, **1 direita, 2 centro** (o enum de justificação do
  motor de texto da Adobe). Os campos 26 e 43 repetem a informação dentro de valores maiores.
- A Position do texto é a ORIGEM do alinhamento: o começo da linha (esquerda), o meio (centro), o fim (direita) — no
  projeto do autor os 3 títulos iguais têm a origem em 0,32 / 0,498 / 0,678, o mesmo vão. No Resolve: o alinhamento e a
  âncora (topo_esquerda/centro/direita) do mesmo lado. Medido no projeto `03 CASOS/TITULOS/T_ALINHAMENTO_PREMIERE23`
  (feito pelo autor). R04: os títulos centralizados 8:01–9:09 de 0,17–0,28 a 0,72–0,92 contra a referência.
- ⏳ O texto sai ~7 % menor no Resolve (corpo da Acumin Pro ExtraCondensed); outros estilos de título a mapear.

## Keyframe Bézier do Motion — 2026-10-10 (`confirmado` pela imagem, R04, Premiere 22/23)

- Campos do keyframe (`Keyframes` do parâmetro): `tempo, valor, tipo_temporal, ?, vel_entrada, infl_entrada, vel_saída,
  infl_saída` + nos parâmetros 2D (Position) `tipo_espacial, ?, tangente_entrada (x, y), tangente_saída (x, y)`. Tipo 0 =
  linear, 5 = Bézier. Velocidade em unidades do valor por SEGUNDO (Position: fração NORMALIZADA, distância √(dx²+dy²) sem
  corrigir a proporção); influência = fração da duração do trecho. Um lado linear grava a velocidade MÉDIA do trecho.
- O modelo do After Effects: distância × tempo = Bézier cúbica com controles (infl_s·D, vel_s·infl_s·D) e
  (D − infl_e·D, S − vel_e·infl_e·D); na Position a distância anda sobre o caminho espacial (Bézier com as tangentes —
  só as de keyframe de tipo ESPACIAL 5; no linear a tangente fica gravada e não vale).
- Conferido: JUL_7504 (ease na Position x): previsto 31,6/31,9/31,7/30,9/29,4/27,1 px (de 960) à esquerda do linear nos
  531–536, medido 32/32/32/30/30/28. No Resolve, amostrado quadro a quadro: transição da perna 531–536 de ~0,58 a 1,00,
  Take_Escadaria 170–173 de 0,07–0,26 a 1,00. `leitura._bezier_trecho`.
- Laboratório B17 (`laboratorio-de-midia/resultados/B17_BEZIER/PREMIERE.md`): o mesmo modelo, SEM fator, nos parâmetros de
  UM eixo (Scale: 8 campos por keyframe) — ease, overshoot e influência 1/3 a ±0,06. **Tipos 4 e 7 = HOLD.** A API
  (`setInterpolationTypeAtKey` 5/6) grava a velocidade média: não cria ease. Tipo 6 recalcula a saída (auto) — ⏳.

## Keyframe fora da grade da timeline e o desfoque — 2026-10-11 (`confirmado` pela imagem, R04 + laboratório B20)

- Clipe com velocidade ≠ 1 ou in fora da grade: os keyframes do Motion caem ENTRE quadros da timeline. Gravar o valor do
  instante exato no quadro arredondado adianta/atrasa a animação inteira (R04, JUL_7644 a 1,1×, in na fração 0,09, Position
  a ~128 px/quadro: +12 px no 121–123 = 0,09 quadro). Levar a outro NLE quadro a quadro no trecho animado: 122–123 de
  0,93/0,91 a 0,9998. De Lá Pra Cá: `leitura._segmento` (pontos por quadro quando há keyframe fora da grade).
- Gaussian Blur (`AE.ADBE Gaussian Blur 2`): largura 10–90 % = 0,7209 × Blurriness + 0,09 px (1920 px, 100 %). No Blur do
  Fusion: 2,8602 × XBlurSize + 0,83 ⇒ **XBlurSize = 0,2521 × Blurriness − 0,259**. Laboratório B20.

## Velocidade e NEST: a grade do nest — 2026-10-10 (`confirmado`, laboratório B16 + R04, Premiere 23.2)

- ⭐ **O conteúdo de um nest é renderizado nos quadros DO NEST.** No instante T o clipe do nest está em u(T) = In + (T −
  Start) × `PlaybackSpeed`; o de dentro anda pelo **PISO na grade do nest**. A `PlaybackSpeed` é float32 no XML
  (4,66666650772095): 3 × v = 13,99999 → quadro 13. Medido pelo número do quadro desenhado na mídia sintética: placa de
  100 qps num nest a 466,67 % → o Premiere mostra 16/37/54/75/95…, não os 19/38/58/77/97 do tempo exato. A máscara do
  clipe de DENTRO anda junto (o tempo dele sai da grade); a do clipe do NEST é avaliada no tempo contínuo do nest.
- Para outro NLE (que achata o nest): a fonte de cada quadro pela grade — quadro a quadro, como a rampa. No R04, a
  transicao-perna (nest a 228,6 %) foi de 0,235 a 0,994 contra a referência. `leitura.py` (`grade_nest`, `fonte_em`).
- Velocidade dentro do nest (o clipe de dentro acelerado, nest a 1×: "poste" e "pesoa" do R04) não muda nada na grade.
- ⭐ **Encaixe do in DENTRO de um nest: pelo PISO** (2026-10-10, `confirmado`): o clipe de dentro começa num quadro
  INTEIRO do tempo do clipe — (piso(In ÷ (v × quadro do nest)) + k) × v, com v em float32 (o 27,99999 vira 27). Lab
  (placa de 23,976 a 466,67 % dentro de nest a 1×, In ÷ v = 5,14 → toca de 5) e R04 (o "poste": LOU_7310 a 466,67 % com
  In ÷ v = 273,43 → 76/78/537 de 0,69/0,82/0,59 a 0,87/0,89/0,73, nada piorou). `leitura.py`, `_folhas` (prof > 0).
- ⛔⛔ **A ENTRADA COM VELOCIDADE MUDA COM A VERSÃO (2026-11-26, laboratório B32, `confirmado` pelo código de barras de
  CADA quadro):** o MESMO projeto (12 casos: 50/200/75/125 %, 25p, 24p, 29,97 a 100 % e a 1,791, 50p, reverso; montado
  no 27.0 por `setSpeed`, rebaixado com `lab.prproj_downgrade`) renderizado no 23.6, 25.6.5, 26.0.2 e 27.0 (Mac):
  - **26.0.2 e 27.0:** a fonte começa na entrada EXATA (125 % com In 48 q → 48, 49, 50, 51, 53…; 29,97 a 1,791 com In
    47,5 q → 47, 49, 51, 54…). Só a grade da TIMELINE vale: a entrada fora dela mostra o piso (`prproj/escrita.md` §11k).
  - **23.6 e 25.6.5:** pelo TETO de In ÷ (v × quadro) — 48,75 → 48, 50, 51…; 49,2537 → 49, 51, 53…
  - Os outros 10 casos, iguais nas quatro. ⚠️ Nenhuma das quatro dá o PISO abaixo (R04, 22.6/23.2 Windows, medido pela
    semelhança da imagem, não pelo código): fica para os projetos de antes do 26 até ser medido de novo no Windows.
  - Conformar `prproj/leitura.py` (`_folhas`, `_versao_maior` pelo `MZ.BuildVersion.Modified`): do 26 em diante, o
    piso só na grade da timeline; e o `fonte_exata` (a fração do quadro da fonte) vai ao Avid pelo gráfico de posição.
    Resultado Premiere 27 → MC 25.12: 12/12 casos, 96/96 quadros cada (`spikes/velocidade/`, pasta
    `MIDIAS DE TESTES/9 SAIDAS…/2026-11-26 VELOCIDADE B32`).
- ⭐ **Clipe SOLTO (timeline de cima) com velocidade: também pelo PISO** (2026-10-10, `confirmado` no R04): cada quadro da
  referência exportada pelo autor casado com o quadro da MÍDIA (bordas, 192×108): 8 clipes de 1,1× a 10× com In ÷ passo
  fracionário (0,08–0,79) — o Premiere mostra piso(In ÷ passo) × passo + k × passo em TODOS (147: 4733, 4738, 4742…;
  LOU_7308: 6539, 6546, 6554, 6561). E vale com Time Remapping (o passo = `PlaybackSpeed` × quadro). ⚠️ **O Resolve
  ARREDONDA o In ÷ passo**: com fração < 0,5 o resultado coincide por sorte; com ≥ 0,5 saía um quadro de saída adiantado.
  O teto, aplicado antes, piorou 19 pontos — era o lado errado. (O caso do laboratório — `setSpeed` do QE DEPOIS do in,
  6,857 = teto — fica como está: projeto montado à força.) R04: média 0,969 → 0,974; o trecho 18–27, que parecia a Lumetri,
  era isto (0,62 → 1,00).
- ⚠️ Laboratório B18_IN_LENTO (2026-10-10, `laboratorio-de-midia/resultados/B18_IN_LENTO/PREMIERE.md`): placa de 100 qps
  — piso em 14 frações a 50 % e 3 a 2×, e no in/arquivo EXATOS do JUL_7671; o passo a mais do JUL_7671 no R04 é do
  CONTEXTO daquele projeto (o render da cópia repete; um projeto limpo não) — descartados in, mídia e `OriginalDuration`.
  ⛔ Contradição aberta: a 4× com a placa de 100 qps (passo 16,7 quadros) o Premiere usou o TETO; no R04, a 4× com mídia de
  25 qps (passo 4,2), o piso. `pendente` — variar a taxa da placa e a velocidade.
  ✅ Resolvido (2026-10-11, B18 rodada 3): editando de verdade, o Premiere ENCAIXA o in na grade da timeline pelo PISO já ao
  marcar (25 qps in 208 = 199,68 quadros → 199); com o in na grade os três modos coincidem. O teto vinha do projeto forçado
  (in escrito no XML). In fora da grade num projeto real (velocidade/relink/conform, R04) → piso, como o De Lá Pra Cá faz.

## ⚠️ As MÁSCARAS no 26.5 / 27.0 — o sistema mudou (2026-11-20, `confirmado` pela tela, `pendente` o formato)

- No **26.5.2** e no **27.0.0** (Windows) o Effect Controls tem uma seção nova no topo, **"Unassigned Masks"**, e os efeitos
  (Lumetri, Opacity) NÃO mostram mais os botões de máscara (elipse/4 pontos/pena) — a máscara parece ser criada por
  FERRAMENTA (barra: Pen, Rectangle com submenu, uma de seleção com retângulo) e ATRIBUÍDA ao efeito. O formato no
  `.prproj` (se ainda é o `AEMask2` como SubComponent do efeito, medido no 26.0) e o gesto de criar: `pendente` (com o
  autor). Uso: traduzir o Gradient do Resolve como retângulo com feather na Lumetri.
- ✅ **O FORMATO é o mesmo do 26.0** (2026-11-20, `confirmado` no arquivo e pelo pixel): o `LAB MASCARA LUMETRI 26.prproj`
  (26.5.2 Windows, uma máscara retangular feita na UI antes de a placa cair) tem o `AE.ADBE AEMask2` "Mask2" (InstanceName
  "01") em `SubComponents` da Lumetri, `Type` = 2. Mas o 26.5 grava **35 parâmetros** (o 26.0.2, 27): entram ParameterID
  30–37 = **Sharpness** (bool), **Sharpness Method** (0–1), **Contrast** (0), **Midpoint** (50), **Input Black** (0),
  **Input White** (255), **Gamma** (1) e um bool sem nome — o refino da borda; os padrões são neutros. O `Path` (param 7):
  cabeçalho `02000000 01000000 56790000 00 02000000` + u32 nº de vértices + 28 bytes por vértice (u32 0 = canto + 3 pontos
  f32) + o byte `01` do fim (reproduzido byte a byte). ESCRITA: um clone do molde (ids e BinaryHash novos, os valores
  deduplicados preenchidos) pendurado na Lumetri, com o projeto fechado — o **Premiere 2027 (27.0.0, Mac) abriu e
  renderizou** (`laboratorio-de-midia/lab/bancadas/premiere_mascara_lumetri.py`).
- ⭐ **A FEATHER do retângulo** (27.0.0 Mac, quadro branco, Lumetri Exposure −5 dentro da máscara, perfil na linha do
  meio): **simétrica, o meio (50 %) exatamente na aresta**; largura de 10 a 90 % = **0,935 × Feather** (25/50/100/200/400
  → 24/46/94/187/374 px), a mesma forma em S em qualquer valor (normalizada, ≤ 0,001 entre 100, 200 e 400). **Expansion**
  empurra a aresta em px (+100 → o meio de 960 para 1060). `confirmado`.
- ⭐⭐ **O GRADIENT do Resolve → retângulo com feather** (`confirmado` pelo pixel): a rampa do Gradient (`drt-drp/estruturas.md`
  §A BORDA EM PX: meio a 0,53·L da linha, 10–90 % = 0,56·L) tem a MESMA forma em S da feather do Premiere (normalizadas,
  ≤ 0,034). Tradução: retângulo cobrindo o lado selecionado, **aresta a 0,53·L da linha, do lado NÃO selecionado**, e
  **Feather = 0,60·L**. Prova: "Gradient Soft 2" (L = 200, linha em y 538,5, Resolve 19.1.4) × o retângulo (aresta 644,5,
  feather 120) no Premiere 2027: **diferença média 0,3 % da força da correção, p99 3,3 %, máx 4,6 %** no quadro inteiro
  (`gradient_para_retangulo`/`conferir_gradient`). ⬜ Rotação (Rotate do Gradient → retângulo girado em volta da linha), a
  compressão do Resolve perto da borda do quadro (o Premiere não comprime), o MC (AniMatte).

## Máscara de OPACIDADE do Premiere 22/23 (`AE.ADBE AEMask`) — 2026-10-10 (caso R04)

- Fica como `SubComponent` do `AE.ADBE Opacity` (o `AEMask2` do 26 fica no Crop/Blur). Parâmetros: "Mask Path" (Arb,
  ParameterID 6, keyframes = contorno ANIMADO), "Mask Feather" (7), "Mask Opacity" (8), "Mask Expansion" (9); sem nome:
  o 10 (booleano — `hipotese`: Inverted, falso nas 12 do R04), o 11 (= 2), o 12, o 13 (0,5), o 1–5/14/15 (false).
- ⚠️ **Ordem**: a Opacidade (e a máscara dela) é efeito FIXO — roda DEPOIS dos efeitos comuns do item (um Gaussian Blur
  desfoca a imagem inteira e só então a máscara recorta). Medido 2026-10-10 (R04, a pessoa desfocada do nest
  transicao-pesoa, render do Premiere só com a V3): com o Fusion recortando no MediaIn e desfocando depois, a área sai
  maior (1772 × 1660 px); desfoque → Merge com o Polygon no EffectMask sobre um Background transparente dá 1665. `parcial`:
  só um plano. ✅ No De Lá Pra Cá (2026-10-10): com outros nós, o Polygon vai no Merge do fim da cadeia (`drp/fusion_clipe.plano`,
  casca igual); R04 118–123 cor 0,97 → 0,73 … 4,57 → 4,23/255.
- O contorno: `2cin` + u32 2 + u32 0 + u32 N; por vértice 32 bytes = u32 (1 suave / 0 canto) + vértice + alça de
  entrada + alça de saída (6 f32) + u32 1. Coordenadas 0–1 no quadro da FONTE, Y para baixo, CRUAS (fora de 0–1 = fora
  do quadro, normal num wipe) — conferido pela referência (o wipe do véu do C0296: 99,3 % da área).
- O tempo do keyframe do contorno é o da MÍDIA do item (o mesmo do Motion; num clipe com rampa, o da fonte).
- ⛔ **O `exportFramePNG` do Premiere 23.2 NÃO desenha a máscara** (o C0296 sai inteiro onde a referência o esconde —
  o mesmo aviso do 26 na api-extendscript): para conferir máscara, o gabarito é o vídeo de referência.

## O AUDIO GAIN do clipe (`<Gain>` no AudioClip) — 2026-11-20 (Premiere 26.5.2 Windows, `confirmado`)

- Clip › Audio Options › Audio Gain… (id de menu **11530** no Windows; o diálogo "Audio Gain" é `#32770` com o campo
  "Adjust Gain by" já focado) grava **`<Gain>`** no `AudioClip` que o `SubClip` da trilha aponta, depois do
  `AudioChannelLayout`, como o **fator LINEAR**: 9 dB → `2.818382740020752` (= 10^(9/20)). Ausente = 0 dB.
- É o que vai ALÉM do teto do Volume do clipe (o Level 1,0 = +15 dB, `UpperBound` 5,623): o ganho do Avid acima de
  +15 dB vai nele (Ciclo Assist, `carta/entrega_prproj`, a PRODA: +24 dB = Level +15 e Gain 9 dB, lidos pela API).
- Pela API: o QE `trackItem.staticClipGain` LÊ o valor em dB (8,99999…), mas a atribuição é IGNORADA em silêncio
  (sem erro). Não há setter no DOM nem no QE (inventário 26.0.2) — escrever é pelo `.prproj` ou pelo menu.

## ⭐⭐ O INPUT SIZING do Resolve no Premiere: um efeito TRANSFORM separado — 2026-11-21 (`confirmado` pela imagem, Premiere 27.0.0 Mac × Resolve Studio 21.1)

Decisão do autor: o Sizing da página Color vai num **Transform** (`AE.ADBE Geometry`) próprio, sem competir com o Motion.
Pela ponte (ExtendScript): `Position` NORMALIZADA [x, y] (fração do quadro da FONTE), `Uniform Scale`, `Scale Height`,
`Scale Width`, `Rotation` (+ = horário, como no Resolve). Tradução (o Resolve no `drt-drp/estruturas.md` §"O SIZING"):
**Position = [0,5 + Pan/W_timeline, 0,5 − Tilt/H_timeline]** (o Pan/Tilt do Resolve já é fração da timeline; o Tilt + é
para CIMA); **Scale = Zoom·100** (Width/Height → Scale Width/Height = Zoom·W·100 / Zoom·H·100, Uniform desligado);
**Rotation = Rotate**; Flip H/V → os efeitos `AE.ADBE Horizontal Flip` / `AE.ADBE Vertical Flip` (o Transform não espelha).
O ENCAIXE da fonte no quadro (o "Scale to Fit" do Resolve) fica no **Motion** (4K em 1080 → Scale 50): como o Transform
roda ANTES do Motion e a Position é normalizada, a MESMA fórmula vale para qualquer resolução de fonte.
- **Conferido** (render ProRes × still do Resolve, alinhados por ECC; o desvio máximo nos cantos do quadro): Pan, Tilt,
  Zoom, Rotate, Width, Height, Flip H e Flip V isolados **≤ 0,15 px**; os quatro juntos (Pan 100 + Tilt 50 + Zoom 1,3 +
  Rotate 10) **0,08 px** (a ordem do Transform = a do Resolve: escala e giro no centro, depois o deslocamento); fonte
  3840×2160 numa timeline 1080 com Pan 100 + Zoom 1,2 **0,13 px**. Prova inversa: o Pan do Premiere contra o still
  NEUTRO do Resolve = 20 códigos de diferença média (contra 1,3 no certo — só a cor).
- ⭐ **Pitch/Yaw → CORNER PIN** (`confirmado`, 2026-11-21): o Resolve NÃO gira em 3D — aplica uma perspectiva LINEAR:
  cada ponto (x, y de −1 a +1 a partir do centro, y para baixo) é dividido por **s = 1 − Pitch·y + Yaw·x** (Pitch 0,2:
  topo ÷ 1,2, base ÷ 0,8; os cantos medidos no still batem com a fórmula). No **Corner Pin** os 4 cantos vão NORMALIZADOS
  (podem passar de 0–1): Upper Left = [0,5 − 0,5/s, 0,5 − 0,5/s] com s = 1 + Pitch − Yaw, e assim por diante
  (`cantos_perspectiva`). Conferido: Pitch 0,2 → **0,71 px**, Yaw 0,2 → **0,31 px** nos cantos. O **Basic 3D** (Tilt/Swivel
  + Distance to Image) é outro modelo (rotação com câmera): o melhor da varredura erra **~110 px (Pitch) e ~80 px (Yaw)**
  nos cantos, e a distância só piora — não usar. ⬜ Pitch/Yaw JUNTO com Zoom/Rotate (a ordem), valores fora de 0,2.
- ⭐ **O NODE SIZING = um 2º Transform DEPOIS do Transform do Input** (`confirmado`, 2026-11-21, Premiere 27.0.0 × Resolve
  21.1): só o nó (o combinado) 0,11 px; Input Zoom 1,5 + Node Pan 100 → 0,67 px; Input Rotate 10 + Node Pan 100 → 0,26 px.
  Na ponte, com dois efeitos de mesmo nome, achar o N-ésimo "Transform" (o `MONTAR_JS` de `premiere_sizing.py`).
- ⬜ O Output Sizing (da sequência
  inteira: um ajuste por cima?), keyframes do sizing. `laboratorio-de-midia/lab/bancadas/premiere_sizing.py`.

# PRPROJ — Escrita: as regras que o Premiere não perdoa

Enquanto [estruturas.md](estruturas.md) descreve o que se LÊ num PRPROJ, este arquivo registra o
que se aprende ao ESCREVER um: as regras cuja violação faz o Premiere **crashar na abertura**,
despejar clipes numa pasta "Recovered Clips", ou abrir um projeto em que o clipe de vídeo não é
selecionável na timeline.

São coisas que nenhuma leitura de template revela — só aparecem quando você gera o arquivo e ele
não abre. Cada uma abaixo custou uma sessão de bisecção.

**Confiança `confirmado`** salvo onde indicado: validado em **Premiere Pro 25.6.5 (macOS)**, com
mídia real, abrindo o projeto gerado do zero. Fonte: `DRAMASYNC/src-python/prproj/builder.py`.

---

## 1. `<InUse>` só em clip de MASTER, nunca em clip de TRACK

A regra mais barata de violar e das mais caras de achar.

| clip referenciado por | tem `<InUse>`? |
|---|---|
| `MasterClip` (entrada no painel de projeto) | **SEMPRE** `<InUse>false</InUse>` |
| `SubClip` (colocado numa track da sequência) | **NUNCA** |

Verificado em 100% dos clips do template de referência (298 `AudioClip`, 71 `VideoClip`).

Vale para **áudio E vídeo** — a versão só-áudio desta regra foi aplicada primeiro, e o `<InUse>`
que sobrou nos `VideoClip` de track é a causa provável do bug antigo *"o clipe de vídeo não é
selecionável na timeline"*.

---

## 2. A referência CIRCULAR que crasha em `AR::AudioPrefetch`

O sintoma: o Premiere 25.6.5 fecha instantaneamente (`EXC_BAD_ACCESS` em `AR::AudioPrefetch`) ao
abrir qualquer projeto com merged clips. Sem mensagem, sem log útil.

A causa: **uma câmera "mergeada" precisa de 4 MasterClips, não 3.** O erro era usar o MasterClip da
BIN como alvo do `SubClip` de vídeo dentro da própria sequência merged, o que fecha um ciclo:

```
Sequence(merged) → SubClip → MasterClip(bin) → AudioSequenceSource → a MESMA Sequence
```

### Os 4 MasterClips de uma câmera mergeada

| # | papel | característica |
|---|---|---|
| 1 | **bin MC** — o item `"<cam> - Merged"` no painel | `Clips` = AudioClip→`AudioSequenceSource` + VideoClip→`VideoSequenceSource`, **sem** InPoint/OutPoint, apontando PARA a sequência merged. Só é referenciado pelo `ClipProjectItem` da bin. |
| 2 | **camMC** | Cópia **duplicada e independente** da mídia bruta da câmera (`Media`/`VideoStream`/`AudioStream`/`VideoMediaSource`/`AudioMediaSource` PRÓPRIOS, com `media_uid` novo). `InPoint=0`/`OutPoint=cam_dur` explícitos. `Node.Properties` só com `MZ.MergeClipUtils.ComponentMasterClipOriginalName`. Tem `DefMappingID`. |
| 3–4 | **per-channel MC** (ch0, ch1) | `MZ.MergeClipUtils.AudioTrackNumberFromOriginalMergedClip=N`, `AudioClip` com `InPt=sync_offset`. |

**É o camMC (#2) — não o bin MC — que deve ser o alvo do `SubClip` de vídeo (V1)**, tanto dentro da
sequência merged quanto dentro de cada variante COM MERGED da timeline.

Os `vms_oid`/`markers_oid` do camMC devem ser **reaproveitados** (não recriados) em toda referência
de vídeo daquele grupo merged — o template reusa os MESMOS objetos Source/Markers em 3 lugares.

> **Método:** a bisecção que achou isso foi por VARIANTE, não por campo. Gerar o mesmo projeto com
> subconjuntos de variantes (`sem_merged` / `com_merged` / com e sem overlap) isolou o crash nos
> merged clips e descartou as hipóteses de "mídia ausente" e "overlap de câmeras". Só então a
> comparação campo a campo contra o template valeu a pena.

---

## 3. `Link`: casar vídeo e áudio POR SOBREPOSIÇÃO DE TEMPO

Um `Link` deve agrupar o(s) item(ns) de áudio **e** o item de vídeo que ocupam o **mesmo período de
tempo** na timeline.

Fazer o oposto (um Link gigante com todo o áudio da sequência + um Link solo para cada vídeo) produz
um projeto que **abre normalmente** mas em que o clipe de vídeo **não é selecionável com clique
direto no corpo** — só nas bordas de trim, via "select at playhead", ou com a slip tool. É um
sintoma que parece bug de UI do Premiere e é, na verdade, um Link malformado.

**Casar por TEMPO, não por NOME.** Quando uma câmera é totalmente engolida por outra (overlap,
"first-camera-wins" na segmentação), o segmento de áudio nomeado com ela é descartado — mas o
segmento mesclado (com o nome da OUTRA) ainda cobre aquele intervalo. Casar por sobreposição de
tempo ainda encontra esse Link e mantém o vídeo selecionável.

---

## 4. Mídia bruta precisa de entrada na bin — senão "Recovered Clips"

Todo `MasterClip` de mídia bruta (as câmeras e o WAV) precisa do seu próprio `ClipProjectItem` na
bin. Existir só como referência interna via `SubClip` faz o Premiere detectar "clipes órfãos" e
despejá-los numa pasta automática **"Recovered Clips"** ao abrir.

---

## 5. O que faz uma sequência ser MULTICAM (e não uma sequência comum)

Uma Multi-Camera Source Sequence e uma sequência normal têm a **mesma estrutura de tracks**.
A diferença mora em **dois campos do MasterClip da sequência** — não na `Sequence`:

```xml
<Source.Monitor.Multicam.Enabled>true</Source.Monitor.Multicam.Enabled>
<Source.Monitor.Multicam.TrackIndex>0</Source.Monitor.Multicam.TrackIndex>
```

`TrackIndex` **só existe quando habilitado**. Medido cruzando o flag com o `<Name>` do
MasterClip no template: `true` + `TrackIndex` nas 4 sequências `MULTICAM …`; nenhum dos
dois nas 4 `SEQ NORMAL …`.

Sem isso, o Premiere abre a sequência normalmente, com as câmeras em V1/V2… — mas ela
**não entra no monitor multicam**, e não há como cortar entre ângulos.

> **A lição de método:** o DRAMASYNC exportou sequências não-multicam por semanas. O sync
> tinha sido validado no Premiere e estava correto. Ninguém tinha perguntado se a
> sequência era do **tipo** certo. **Validar o conteúdo não valida o continente.**

⭐ **O `TrackIndex` é o ÂNGULO ATIVO** — `confirmado` (2026-11-12, Premiere 26.0.2 Mac, lab G01, 1 rodada pilotada; Ciclo
Assist `carta/itens._sequencias_multicam`): a trilha de vídeo da multicâmera, contando do 0 (0 = V1). O gesto (autor):
duplo clique na multicâmera na bin → o Origem já abre o MOSAICO dos ângulos, a borda AMARELA marca o ativo, e um clique
num ângulo o troca. O mosaico se adapta ao número de TRILHAS de vídeo, mesmo vazias: 1 trilha = 1 ângulo; 2–4 = 4;
5–9 = 9 (acima de 9 não visto). Medido: borda no 2º ângulo + Salvar → `TrackIndex` 0 → 1. ⚠️ Não há equivalente
medido para o som (a multicâmera traz o som nas trilhas de áudio dela; o group clip do Avid tem um `Selector` próprio).

(Na `Sequence` em si, o campo relacionado `Source.Monitor.Multicam.SwitchOnMulticamName`
existe nas multicam e não nas normais — mas é o MasterClip que manda.)

---

## 6. O mapeamento de canais: UMA TRACK POR CANAL, ou o áudio vira um nest

Quando a multicam é inserida numa timeline de edição, o áudio pode entrar como **N tracks**
(uma por canal do som direto) ou como **UM bloco adaptativo**. O bloco é um nest que **não
se desmancha** ao mandar para a pós de som — retrabalho no departamento de sonorização, e
o motivo de existir de um app de sync.

Quem decide isso é o **MasterClip da sequência**:

| | ERRADO (vira um bloco) | CERTO (vira N tracks) |
|---|---|---|
| `AudioComponentChain` | **1**, com N canais (`ChannelType=1`, layout de N) | **N**, cada uma MONO (`ChannelType=0`, layout `[{"channellabel":0}]`) |
| `ClipChannelVectorItem` | **1**, agrupando os N canais | **N**, um por canal |
| `mSourceChannelIndex` | 0..N−1, todos no mesmo vetor | 0, 1, … N−1, um em cada vetor |

Medido no template: as 4 sequências `MULTICAM` têm 4 cadeias mono e 4 vetores de um canal.
É a **mesma forma** que os MasterClips de mídia usam.

---

## 7. WAV MULTIPISTA: quando a FONTE vira o canal, TODO índice dentro dela ZERA

> ⚠️⚠️ **ESTA REGRA VALE PARA O MERGED CLIP TAMBÉM — e foi esquecida lá por 2 meses.**
> Em 2026-09-06 o merged saía com os canais em **passo 2** porque o Órbita tinha uma
> SEGUNDA implementação de "descrever os canais de um WAV" (`_make_extra_wav_ams`), que
> nunca recebeu o §7.1: um `Media` só, sem `StreamNumber`, com `FileKey` novo a cada
> chamada. ⭐ **Se você está escrevendo qualquer coisa que aponte para um canal de WAV —
> mídia de bin, track de sequência, merged clip —, é ESTA seção que manda.** E se houver
> duas funções que a implementem, uma vai ficar para trás na próxima correção.

`confirmado` (2026-07-12, Premiere 25.6.5 — os 5 canais tocam nas 5 tracks).

São **DUAS** coisas, e a primeira sozinha não basta.

### 7.1 — Um `Media` por canal, selecionado por `StreamNumber`

**Um `Media` POR CANAL**, todos apontando para o mesmo arquivo:

| campo | canal 0 | canal 1 | canal 2 | canal 3 |
|---|---|---|---|---|
| `ObjectUID` | *diferente* | *diferente* | *diferente* | *diferente* |
| **`StreamNumber`** | **ausente** | **1** | **2** | **3** |
| `AudioStream.AudioChannelLayout` | `[{"channellabel":0}]` (MONO) | idem | idem | idem |
| `FileKey` | **o MESMO** | | | ← identifica o ARQUIVO |
| `ContentAndMetadataState` | **o MESMO** | | | ← idem |
| `FilePath` / `Title` | o mesmo | | | |

Cada `Media` tem o seu `AudioMediaSource`. O `MasterClip` do WAV tem **N `AudioClip`**
(um por canal), e o `TrackItem` da track A*N* aponta para o `AudioMediaSource` do canal N.

`AudioClip.SecondaryIndex` e `SubClip.OrigChGrp` continuam sendo escritos (o Premiere
escreve os três) — mas **quem realmente seleciona o canal é o `StreamNumber`**.

> **O que NÃO funciona** (e foi o bug do DRAMASYNC): UM `Media` declarando os N canais,
> com a seleção confiada só a `SecondaryIndex` + `OrigChGrp`. A prova de que é estrutural:
> ao conformar a mídia, o Premiere **REESCREVE o MasterClip** para o formato acima — mas
> não reescreve os `TrackItem` da timeline. Resultado: o clipe na bin fica certo e a
> timeline, errada.

### 7.2 — E os índices DENTRO da fonte vão todos a ZERO

Feito o 7.1, a fonte de cada track **já é** o canal — e ela é MONO. Logo, todo campo que
pergunta *"qual canal dentro da fonte?"* tem uma única resposta possível: **0**.

**São TRÊS campos, e é a mesma ideia:**

| campo | onde | valor |
|---|---|---|
| `SecondaryContent.ChannelIndex` | no `AudioClip` da TRACK | **`0`** (não o número da track!) |
| `ClipChannelSerializer.mSourceChannelIndex` | no MasterClip de MÍDIA | **`0`** |
| `ClipChannelSerializer.SourceClipIndex` | no MasterClip de MÍDIA | `0..N-1` ← este SIM varia (aponta o CLIP) |

`AudioClip.SecondaryIndex` (`1..N-1`) e `SubClip.OrigChGrp` (`0..N-1`) **continuam
variando** — o Premiere escreve todos. Mas eles não são o que SELECIONA o canal.

> **O bug que sobreviveu ao 7.1:** escrevíamos `SecondaryContent.ChannelIndex = 1,2,3,4`
> — pedindo um canal que a fonte mono não tem. O Premiere não resolve, a track fica
> **muda e sem waveform**, e o áudio **some e volta ao passar o mouse**.
> **A assinatura do bug:** A1 toca e A2..AN não — porque o canal 0 não usa
> `SecondaryContent` e os demais usam.

### ⚠️ A armadilha: o `ClipChannelSerializer` tem DUAS formas

Trocá-las faz todas as tracks lerem o canal 0.

| MasterClip de… | `SourceClipIndex` | `mSourceChannelIndex` | porque |
|---|---|---|---|
| **SEQUÊNCIA** | `0` (sempre) | `0..N-1` | um clip só (a sequência), com N canais dentro |
| **MÍDIA multicanal** | `0..N-1` | `0` (sempre) | N clips, um por canal, cada um mono |

### Lição de método

Duas estruturas que "parecem idênticas", uma funciona e a outra não → **o problema está
no que você NÃO está imprimindo.** Só o diff do **XML CRU da cadeia inteira**
(`TrackItem → SubClip → AudioClip → AudioMediaSource → Media → AudioStream`), sem
escolher campos, revelou o `SecondaryContent`. O A/B decisivo: pôr o clipe CERTO
(arrastado da bin pelo Premiere) e o gerado **lado a lado na mesma timeline**, salvar, e
comparar.

---

## 8. Cores de label: a chave interna NÃO é a posição no menu

`BE.Prefs.LabelColors.N` — o `N` **não** é a posição visual no menu "Select Label Group" do Premiere.
Esse menu é uma lista localizada/exibida; a chave interna é outra enumeração.

Confirmado empiricamente: o menu mostra a ordem *Violeta, Íris, Caribe, Lavanda, **Cerúleo**, …*
(Cerúleo em 5º), mas ao selecionar Cerúleo num clipe e salvar, o Premiere grava
**`BE.Prefs.LabelColors.4`**.

| uso | chave | cor |
|---|---|---|
| vídeo bruto | `.1` | |
| WAV | `.2` | |
| `"- Merged"` | `.4` | Cerúleo (decimal `5814353`) |
| sequências | *omitir* | o Premiere atribui `.5` sozinho ao reabrir/salvar |

> **Regra geral, e vale para muito além de cor:** para descobrir o valor de um campo, **não olhe a
> UI — faça o Premiere escrever.** Setar no app, salvar, reabrir o XML e ler o valor real. Foi assim
> que se descobriu que a posição do menu mentia.

---

## 8. Constantes de infraestrutura

Consumíveis em [dados/regras-escrita.json](dados/regras-escrita.json).

- **OIDs 1–39 são infraestrutura fixa** (Project, ProjectSettings, VideoSettings, AudioSettings,
  stubs de CompileSettings…). Devem ser emitidos mesmo quando "vazios".
- **`NextID` = `1000001`** (não `5000`).
- **`DummyCaptureSettings` ClassID** = `328c2aa2-…` (não `a1004bca-…`).
- **`CompileSettings` OID=8** (e só o 8): `CompilerClassIDFourCC=1061109567`, `CompilerFourCC=1299148630`.
- **`VideoCompileSettings`** exige 12 campos stub após `ForceRecompressValue`: `Aspect43`,
  `Deinterlace`, `IgnoreVideoFilters`, `OptimizeStills`, `FramesAtMarkers`, `RealTimePreview`,
  `VideoFieldType`, `DoKeyframeEveryNFrames`, `DoKeyframeEveryNFramesValue`, `AddKeyframesAtMarkers`,
  `AddKeyframesAtEdits`, `RelativeFrameSize`.
- **`ProjectSettings` OID=3** precisa de `<CaptureSettings ObjectRef="16"/>`, `ColorManagementSettings`
  e `ColorAwareEffectsEnabled`.
- **`NextPannerID`**: `AudioClipTrack` e `AudioMixTrack` mono → `4294967279`; `AudioMixTrack` stereo
  (`NumAdaptiveChannels=2`) → `4294967278`. O `DefaultPanProcessor` usa `ID=4294967280` nos dois
  (a diferença está no `ChannelType`/`AudioChannelLayout`).
- **`MZ.TrackTargeted`** só existe na track de índice 0 (V1), não em todas.
  **`MZ.SourceTrackNumber`**: `"0"` no índice 0, `"-1"` nas demais (vale para vídeo e áudio).
- **Sequências merged são MONO** — `NumAdaptiveChannels=1`, MasterTrack e AudioClipTrack com
  `ChannelType=0`. Não "corrigir" para stereo: o template real também é mono.
- **`<First>` dentro de `<TrackGroup>` é o UUID do TIPO de mídia** (ver
  [dados/type-guids.json](dados/type-guids.json)), **não** um `ObjectRef`. Um validador de
  referências vai reclamar de "broken ref" nesses três valores — é falso positivo.
- **`ObjectID` "duplicado" é NORMAL.** Os ids vivem em espaços de nome separados (`Project` vs
  `ProjectViewState`): o template tem **60** deles. Um validador que exija `ObjectID` único
  no documento inteiro dá falso positivo. `ObjectUID` (o UUID), esse sim, é único.

---

## 9. BINS: `BinProjectItem` — e o projeto com N bins

Um projeto pode organizar a bin em pastas. A forma saiu de um projeto real do Premiere
(`PROJETO_TEMPLATE_VAZIO.prproj`), não de palpite:

```xml
<BinProjectItem ObjectUID="…" ClassID="dbfd6653-24da-480e-a35e-ba45e9504e4b" Version="1">
  <ProjectItem Version="1">
    <Node Version="1"><Properties Version="1"/></Node>
    <Name>D01</Name>
  </ProjectItem>
  <ProjectItemContainer Version="1">
    <Items Version="1">
      <Item Index="0" ObjectURef="…"/>   <!-- ClipProjectItem ou outro BinProjectItem -->
    </Items>
  </ProjectItemContainer>
</BinProjectItem>
```

É um `ClipProjectItem` **sem** `<MasterClip>`, mais um `ProjectItemContainer`. O
`RootProjectItem` tem exatamente a mesma forma — a raiz é uma bin como as outras. Bins
aninham (uma bin dentro de outra), e é assim que se faz `Root ▸ D01 ▸ SUB-GRUPOS ▸ cena 01`.

Duas coisas que valem dizer:

- **Bin VAZIA não leva `<Items>`** — o `ProjectItemContainer` fica sem filhos. É o que o
  template mostra.
- As `Properties` do template (`Column.PropertyText.Label`, `project.icon.view.grid.order`,
  `list.view.expanded.state.…`) são **estado de VISTA**, e o Premiere as regenera.
  Emitir `<Properties/>` vazio funciona. Inventar valor ali é fingir que se sabe algo que
  não se sabe.

---

## 10. MÚLTIPLAS SEQUÊNCIAS: um arquivo tem UM `Media`/`MasterClip` no projeto INTEIRO

Assim que o projeto passa a ter mais de uma sequência (uma por diária, ou uma cena que
recorta outra), a mesma mídia é referenciada de mais de um lugar. **Ela não pode ser criada
duas vezes.**

O builder precisa de um **cache por caminho de arquivo**: `path → (MasterClip, Media, …)`.
Sem ele, o mesmo arquivo entra duas vezes na bin — o Premiere abre as duas, e o usuário não
tem como saber qual das duas é "a de verdade" (e a que ele relinkar não é necessariamente a
que a sequência usa).

> **Lição de método (esta custou um teste inútil):** a primeira versão do teste de
> duplicação checava o tamanho do dicionário de cache do builder — e **passava mesmo com o
> cache desligado**, porque o dicionário tem uma entrada por caminho de qualquer jeito. Ele
> media a CHAVE, não a CONSEQUÊNCIA. O teste que presta conta os `<Media>` **no XML gerado**.

---

## 11. Uma sequência que NÃO começa no zero: o `MZ.ZeroPoint` compensa a origem

O caso: uma sequência que é um **recorte** de outra (uma cena de 5 minutos dentro de uma
diária de 8 horas). Ela deve começar no primeiro clipe dela — senão abre com 5 minutos de
vazio. Mas deslocar as posições **muda o timecode exibido**, e aí o mesmo arquivo mostra
`01:00:00:00` na cena e `01:05:00:00` na diária. **O mesmo arquivo, dois timecodes.**

O `ZeroPoint` da sequência absorve exatamente o deslocamento:

```
posição_na_sequência = timeline_start_absoluto − origem_do_recorte
MZ.ZeroPoint         = (start_tc + origem_do_recorte) × ticks_por_frame

TC exibido = ZeroPoint + posição = start_tc + timeline_start_absoluto   ← invariante
```

Medido no arquivo real: o clipe `PANA2774` lê **TC 11110 frames** nas duas sequências — na
da diária (posição 11110, zero 0) e na da cena (posição **0**, zero **11110**).

> **Por que isto é uma regra do PROTOCOLO e não do app:** o timecode é o que o montador usa
> para conversar com o resto da equipe, e é o que vai para o `ZeroPoint`. Um arquivo com dois
> timecodes é um erro que **não aparece na tela** — só no Premiere, tarde, com o material já
> montado em cima. Todo gerador que emitir sequências-recorte cai nesta armadilha.

---

## 11b. ⛔ A VERSÃO do projeto: um arquivo 43 não abre no Premiere 2023 (2026-09-16)

`<Project ObjectID="1" ClassID="62ad66dd-…" Version="N">` é a versão do FORMATO. O Premiere
recusa versão maior que a dele com *"This project was saved in a newer version of Adobe
Premiere Pro and cannot be opened in this version"* — e, via `importFiles` num painel, o
diálogo aparece mas a chamada devolve **`true`** com **zero itens novos**. Quem confia no
retorno acha que importou.

Medido nos `.prproj` da máquina Windows (a versão salva ao lado de `MZ.BuildVersion.Modified`):

| quem salvou | `Project Version` | confiança |
|---|---|---|
| Premiere **23.2** (2023) | **41** | `confirmado` |
| Premiere **25.6.5** | **43** | `confirmado` |
| Premiere **26.0.2 / 26.3** | **45** | `confirmado` |
| Premiere **Beta 27.1.0** ("2027") | **46** | `confirmado` (2026-10-07, laboratório) |
| o `builder.py` do Órbita (fixo) | **43** | — |
| Premiere 24.x, 25.2.3 | ? | `pendente` |
| Premiere **26.5.2** (Windows) | **45** | `confirmado` (2026-10-22, WSP-DLPC_2) |

🆕 **25.6.5 × 26.0.2 medido pelo Laboratório de Mídia (2026-10-06, macOS, os mesmos 6 casos salvos pelas duas
versões — `laboratorio-de-midia/resultados/ESTRUTURA_PRPROJ.md`):** `PremiereData` 3 nas duas, `Project` 43 → 45, e os
MESMOS 15 elementos sobem de versão em todos os casos — `Sequence` 11→12, `VideoStream` 21→22, `AudioStream` 7→8,
`AudioTrack` 11→12, `AudioClipTrack` 6→7, `Track` 3→4, `TrackItem` 3→4, `Component` 6→7, `AudioComponentChain` 3→4,
`AudioComponentParam` 9→10, `AudioSettings` 7→8, `AudioTrackInlet` 3→4, `ClipLoggingInfo` 9→10, `VideoSettings` 9→10.
⭐ **O 26.0.2 OMITE os campos com valor padrão** (o `VideoSettings` sai vazio; `IsLocked` false, `ChannelType`,
`FrameRate`, `Solo`… somem quando são o padrão) — o 25.6.5 grava tudo. Downgrade 26 → 25: baixar as versões e talvez
DEVOLVER os campos omitidos — ✅ **medido em 2026-10-07: NÃO precisa** (abaixo).

🆕 ⭐ **SUBIDA 23.6 → 26.5.2 de um projeto REAL (2026-10-22, Windows, De Lá Pra Cá):** o `WSP-DLPC.prproj` (PRODUCAO-C,
salvo no 23.6.0) aberto no Premiere 26.5.2 e salvo de novo (`WSP-DLPC_2.prproj`; `Created` continua 23.6.0, `Modified`
26.5.2x5). Comparação por `lab.prproj_estrutura` + contagem de classes:
- versões que sobem: `Project` 41→45, `ProjectSettings` 19→21, `Media` 27→30, `VideoStream` 19→**23** (26.0.2 = 22, 27.1 = 24:
  o 26.5 já tem um degrau a mais), `MasterClip` 11→12, `SubClip` 5→6, `ClipLoggingInfo` 8→10, `IngestSettings` 1→2,
  `VideoClipTrackItem` 6→8, `AudioClipTrackItem` 8→11, `VideoFilterComponent` 8→9, `TimeComponentParam` 8→9, e os do 25→26
  já listados acima (`Sequence` 12, `Track`/`TrackItem` 4, `Component` 7, cadeia/trilhas de áudio, params de efeito).
- ⭐ **a máscara de opacidade é CONVERTIDA:** `AE.ADBE AEMask` (12, formato `2cin` do 22/23) → `AE.ADBE AEMask2` (12) — e o
  contorno sai igual (o leitor do De Lá Pra Cá gerou o MESMO Polygon no Fusion pelos dois).
- ⚠️ **PRÉ-VISUALIZAÇÕES RENDERIZADAS gravadas no projeto** (`…\Adobe Premiere Pro Video Previews\<projeto>.PRV\Rendered - <uuid>.mov`):
  no 26 apareceram +88 `Media` e 183 `PreviewMediaSerializer` (Version 1, ligados às trilhas de vídeo da sequência).
  ⛔ **CORRIGE (2026-10-22, mesmo dia): NÃO é novidade do 26.** O autor renderizou a timeline no 26 de propósito (para não
  travar); o 23.6 não tinha porque não houve render nele. Varredura de 746 `.prproj` do SSD: 18 têm `PreviewMediaSerializer`,
  em **22.4** (Project 40, PRODUCAO_C_Trailer: 111), **23.2** (41, cópias relinkadas do R04: 48), **24.6** (42, PRODUCAO_B: 448)
  e **25.6.5** (43, PRODUCAO_B: 304) — a estrutura existe pelo menos desde o 22. Regra: render de pré-visualização POLUI a lista
  de `Media`/`ActualMediaFilePath` com arquivos que não são do editor; leitor que varre `Media` sem passar pela sequência os
  contaria (e o relink os procuraria). O De Lá Pra Cá não conta: segue a cadeia TrackItem → SubClip → MasterClip (48 arquivos
  nos dois). O indexador de mídia do RELINKER já pula a pasta `.PRV` (`motor/media/indexer.py`).
- `CaptureSettings`/`CaptureSettingsColumn` → `DummyCaptureSettings`; as colunas da vista do projeto caem pela metade
  (estado de painel, irrelevante). `VideoComponentParam` +467 e `PointComponentParam` +36: parâmetros novos dos efeitos
  (o corte do Motion etc.), com valor padrão.
- **Resultado no app** (PRODC_CORTE02, 80 planos): análise, preparo e `.drt` IGUAIS aos do 23.6 (Fusion 11, cor 75,
  compostos 8, áudio, avisos; a diferença do `.drt` é do mesmo tamanho que a de preparar o 23.6 duas vezes = ids e ordem).
  No Resolve 19.1.4: **144/144 conferem** pela API e pela janela real (arrasto do Explorer, 1 min 41 s).

⭐ **DOWNGRADE 26.0.2 → 25.6.5 `confirmado` (2026-10-07, macOS, laboratório):** baixar SÓ a `Version` desses 15
elementos (`Project` 45 → 43; os outros −1) e não tocar em mais nada — sem devolver os campos omitidos. Nos 6 casos o
25.6.5 abriu sem diálogo (`app.openDocument(caminho, true, true, true)`), com sequências, trilhas e itens idênticos ao
que o 26 gravou e stills/renders/canais idênticos ao 25 nativo: o 25 preenche o padrão sozinho. Código:
`laboratorio-de-midia/lab/prproj_downgrade.py` (tabela `VERSOES_26_PARA_25`); teste:
`python3 -m lab.bancadas.downgrade_premiere`. ⚠️ Vale para o que o laboratório tem (clipes, sequências, trilhas,
escala, sync à mão por TC); bins, merged, multicam, efeitos, títulos e cor podem trazer elementos com versão própria —
comparar com `lab.prproj_estrutura` antes de confiar.

⭐ **Beta 27.1.0 (2026-10-07):** do 26.0.2 para o 27.1 mudam só 4 elementos — `Project` 45 → 46, `Clip` 18 → 19,
`Media` 30 → 31, `VideoStream` 22 → **24** (salto de 2, onde mora o espaço de cor do clipe). **Downgrade 27 → 26 e
27 → 25 `confirmado`** do mesmo jeito (só a `Version`; tabela `VERSOES` em `laboratorio-de-midia/lab/prproj_downgrade.py`):
os 6 casos abrem, estrutura igual à do 27, medição igual à nativa do destino. ⚠️ O caso de COR ainda não existe — é nele
que o `VideoStream` 24 pode carregar campo que o 26 não entende.

⛔ **CORRIGE (2026-10-07, B07 PROJETO do laboratório — bins, subclipe, efeitos, transição, título, legenda,
marcadores, efeito de áudio, sequência aninhada): "baixar SÓ a `Version` basta" é FALSO para projeto com áudio de
clipe.** O 26 deixa de gravar os campos que valem o PADRÃO dele, e o 25 precisa de alguns: sem `<FrameRate>5292000`
(48 kHz) e `<AutomationMode>1` na `AudioComponentChain`, o 25.6.5 abre o clipe de áudio **sem os componentes de Volume
e Volume do canal** — um ajuste de volume se perderia (nos B01–B06 o volume era o padrão e o som saía igual, por
isso não apareceu). Regra que funciona: campo ausente no 26 = o padrão do 26; devolvê-lo ao 25 no lugar em que o 25
o grava (tabela `CAMPOS_PADRAO_25` em `laboratorio-de-midia/lab/prproj_downgrade.py`: `AudioComponentChain`,
`AudioTrack`, `AudioTrackInlet`, `AudioClipTrack.RecordChannel`, `Track.IsLocked/IsMuted/IsSyncLocked`,
`Component.Bypass/ArchivedType`, `TrackItem.Start`=0, `VideoStream.InputLUTSpecified`, `*ComponentParam.IsTimeVarying`)
— e NUNCA nos elementos-referência (`<Component Index="0" ObjectRef=…/>`). Com isso, B07 26 → 25 e 27 → 25: projeto
igual à origem e imagens pixel a pixel iguais às do 25 nativo; B01–B06 seguem idênticos.
- O B07 traz 5 elementos que mudam 25 → 26 (nenhum novo 26 → 27): `VideoTransitionTrackItem` 5 → 6,
  `VideoComponentParam` 9 → 10, `PointComponentParam` 3 → 4, `ArbVideoComponentParam` 2 → 3 (o texto do título),
  `QueryDefinition` 2 → 3 (bin inteligente).
- ⚠️ **IDIOMA, não versão:** o estado dos efeitos de áudio grava o nome do preset de fábrica TRADUZIDO
  (`OpaqueData` → `<key>FactoryPreset</key><ustring>(Padrão)</ustring>`; o Beta 27.1 em português escreve "(Default)").
  Abrir com o app em outro idioma desliga o "Vincular quadros-chave" do Amplificar — confirmado trocando só esse texto
  (volta a 1). Vale entre duas máquinas da MESMA versão com idiomas diferentes. E o texto padrão do título .mogrt nativo
  sai no idioma de quem o pôs ("Your Title Here" × "Seu título fica aqui").
- ⚠️ **O padrão da `AudioComponentChain` no 26 é MONO:** ele omite `AudioChannelLayout` E `ChannelType` do clipe mono
  (grava os dois no estéreo); na `AudioTrack` e na `AudioTrackInlet` o omitido é o estéreo (`ChannelType` 1). Devolver
  `1` na cadeia fez o som direto mono de dentro de um merged virar estéreo no 25 — o certo é `[{"channellabel":0}]` + `0`.
- ✅ **Merged clip (B08, escrito pelo construtor do Órbita, `ExportOptions(merged_clips=True)`):** abre no 25.6.5, no
  26.0.2 e no 27.1 com `isMergedClip` verdadeiro e imagem idêntica; não traz elemento novo de versão; downgrade 27 → 26,
  27 → 25 e 26 → 25 sem diferença nenhuma (projeto e imagem).
- 🆕 ⭐ **COR (B09 do laboratório, 2026-10-07):** Sony S-Log3 (ProRes 4444 4K com XML S-Log3.Cine/S-Gamut3.Cine) — sem nada,
  as três versões o leem como Rec. 709 NÃO gerenciado; sobrescrito (`setOverrideColorSpace`) para "Sony S-Log3/S-Gamut3.Cine";
  sequência em ACEScct (`setSettings` com o `workingColorSpace` da lista); ARRIRAW HDE (.arx, 4448×1856); Lumetri (Exposição,
  Contraste, Saturação, Temperatura); LUT de entrada `.cube` (`FootageInterpretation.setInputLUTFromFilePath` +
  `setFootageInterpretation`). **25.6.5 = 26.0.2 = 27.1 pixel a pixel** nisso tudo; nenhum elemento de versão novo.
  Downgrade **26 → 25 perfeito**. O 27 tem 2 espaços a mais na lista de sobrescrita — **"Apple Log/Wide Gamut"** (1070/1050) e
  **"Fuji F-Log2/F-GamutC"** — e efeitos de cor novos (`AE.ADBE LUT Transform`, `AE.ADBE Color And Contrast`, `AE.ADBE HSLMask`).
  **27 → 26 e 27 → 25:** o comum chega idêntico; o clipe Apple Log abre com espaço VAZIO (volta a parecer Rec. 709); os efeitos
  novos dão o diálogo "Carregar projeto — Filtro de vídeo ausente" (com o nome no idioma de quem gravou) e somem da imagem — mas
  o 26/25 GUARDAM os efeitos e o Apple Log no arquivo ao salvar. ⛔ Só que abrir esse arquivo de novo no 27 derrubou o Beta (acima).
  O padrão do "Espaço de cores" da seção Criativa do Lumetri mudou: 26 no 26.0.2, 28 no 27.1.
- 🆕 ⭐ **PROJETOS REAIS (2026-10-07, mídia offline, cópias em `MIDIAS DE TESTES/1 PRODUCOES/…/PROJETOS/`):**
  - **PRODUCAO-I (26.3) → 25.6.5 ✅** idêntico (bins, sequências, keyframes de velocidade, transição de áudio). Elementos que o
    laboratório não tinha: `TimeComponentParam` 9 → 8 e `AudioTransitionTrackItem` 4 → 3, com os campos padrão que o 26 omite
    (velocidade: `IsTimeVarying` true, `IsLocked`/`DiscontinuousInterpolate`/`RangeLocked` false, `ParameterControlType` 21;
    transição de áudio: `FrameRate` 5292000, `FadeShapeType` 1, `CrossfadeSymmetry` 0, e `FadeShapeValue` 19 no "Constant
    Power" — 43/43; no "Custom Fade" é escolha do editor). `TimeRemapping` 2 nas duas.
  - **25.6.5 → 23.2:** dos 104 elementos do CANAL-K COPA que os 6 projetos do 23.2 do SSD também têm, mudam 11: `Project`
    43 → 41, `ProjectSettings` 21 → 18, `Media` 30 → 27, `VideoStream` 21 → 19, `MasterClip` 12 → 11, `SubClip` 6 → 5,
    `ClipLoggingInfo` 9 → 8, `IngestSettings` 2 → 1, `VideoClipTrackItem` 8 → 6, `AudioClipTrackItem` 11 → 6,
    `AudioFilterComponent` 4 → 3. O projeto do 24 (`Project` 42) tem as MESMAS versões do 25 nos elementos de efeito
    (`VideoFilterComponent` 9, `VideoComponentParam` 9, `PointComponentParam` 3, `ArbVideoComponentParam` 2).
    COPA → 23.2 (essas versões + os campos do Órbita + `CaptureSettings` 10) aberto no 25: idêntico ao original —
    ⏳ falta o 2023 de verdade. ⛔ PRODUCAO-I → 23.2 NÃO abre nem no 25 ("could not be loaded … outdated elements"), e só o
    `Project` 41 já basta para falhar: o caminho de projeto antigo é mais exigente (hipótese: os campos que o 26 omite).
  - ⚠️ Projeto do 26 pode trazer TRANSCRIÇÃO (`TranscriptClip` 2 + `ExternallyProvidedTranscriptDocument` 1, binária) e
    `Marker` (classe) 3.
  - ⛔ Ler parâmetro do Lumetri pela API: alguns valores são binário em string com o caractere NULO e UTF-16 inválido
    (surrogate solto 0xDE40) — devolver isso pela ponte CEP dá resposta vazia. Resumir antes (tamanho + soma).
  - 🆕 **Dicionário do 2022** (PRODUCAO-C, 22.4, `Project` 40, 241 Lumetri, 12 AEMask, 18 velocidades, nests): velocidade
    (`TimeRemapping` 2, `TimeComponentParam` 8) e parâmetros de efeito iguais de 22 a 25. `VideoFilterComponent` 8 (22) → 9
    (24/25) com os MESMOS campos — ⛔ mas NÃO descer para 8: o 25 abriu a COPA com o 8 e estragou o Look criativo de 14 Lumetri
    ("Fuji ETERNA 250D Fuji 3510 (by Adobe)" → U+FEFE): a conversão 8 → 9 mexe no texto dos parâmetros.
  - 🆕 **Máscara (`AE.ADBE AEMask`):** 15 parâmetros no 22, 18 no 25 — `Active Path Index`, `Additional Paths`,
    `Selection Data Param` a mais. O desenho mora no binário do efeito (`PremiereFilterPrivateData`).
  - O `VideoClipComponent` ("Clip", 25) embrulha um PSD em camada (clipe dentro de gráfico, com transform próprio).
  - Classes do 24/25 que o 23 não deve conhecer (na COPA): `AudioProxy`, `LUTAsset`, `AdaptiveToAdaptivePanProcessor` (pan de
    trilha ADAPTATIVA), `VideoClipComponent`, `DataClip`/`DataMediaSource`/`DataStream`. Pacote de teste no 2023 do Windows:
    `\\ESTACAO-2\_transfer\LABORATORIO - TESTE PREMIERE 2023`.
  - ✅ **25.6.5 → 23.2 `confirmado` no Premiere 23.2.0 real (Windows, 2026-10-07, pela ponte Mac→Windows):** COPA (42
    sequências) e os casos B07/B08/B09 rebaixados ABREM, sem diálogo de conversão. O 23.2 regrava com `VideoFilterComponent`
    **8** (lê o 9 sem reclamar). Salvo pelo próprio 23.2 e comparado por conteúdo: B08 (merged) idêntico; perde só o que é do
    25 — os 4 params de **corte no Motion** (IDs 8–11), o **`LUTAsset`** (a LUT `.cube` embutida no `VideoStream`), os params
    Lumetri **129 e 130 "Color Space"** e a chave `enableLogColorManagement` do `ColorManagementSettings`.
  - ⭐ **O LOOK criativo da Lumetri no 23.2 é o POPUP, não o nome** (`confirmado`, 23.2.0, 2026-10-07): o menu Look é o
    **ParameterID 25** (VideoComponentParam) = POSIÇÃO no menu — 0 None, 1 [Custom], 2 Browse…, 3 separador, 4… os Looks de
    `Lumetri/LUTs/Creative` em ordem alfabética sem caixa do nome SEM extensão (a ordem dos arquivos é outra: "SL BIG" vem
    antes de "SL BIG HDR"). O nome fica no **ParameterID 96** (Arb, UTF-16LE base64 com NUL) e a LUT no Blob (ID 1). O 25
    deixa o 25 em **0** com nome e LUT preenchidos → o 23 mostra **"None"** e não aplica. Com 25 = 5 a COPA mostra "Fuji ETERNA
    250D Fuji 3510 (by Adobe)" e o frame muda (99–100% dos pixels, prova por `exportFramePNG`). A lista Creative (65) é a
    MESMA no 23.2, 24.6 e 25.2. Implementado: `look_da_lumetri()` em `laboratorio-de-midia/lab/prproj_downgrade.py`
    (`LOOKS_CRIATIVOS`). ⏳ Look fora da lista (um .cube do editor): não medido — deve ser [Custom] + caminho.
  - ⭐ **O CORTE DENTRO DO MOTION (25+) vira o efeito Crop no 23.2** (`confirmado` por pixel, 25.6.5 Mac × 23.2.0 Windows,
    2026-10-07): o Motion do 25 tem 4 parâmetros a mais (IDs 8–11 "Crop Left/Top/Right/Bottom", %); o 23 os descarta e o
    clipe abre SEM corte (PRODUCAO-I: 3 clipes com 14%). O equivalente é o `AE.ADBE AECrop` (Left/Top/Right/Bottom IDs 1–4,
    Zoom 5, Edge Feather 6 — molde do B07 salvo pelo 23.2). O crop do Motion fica PRESO À IMAGEM (anda com a posição/escala
    do Motion). Regra MEDIDA: o Crop entra como o PRIMEIRO efeito da pilha (logo depois dos intrínsecos) — o corte do Motion
    age como um corte na FONTE. Caso CROP (5 sequências × 2 frames, 25.6.5 Mac × 23.2.0 Windows): crop 50% + posição, crop
    misto + escala 80%, Transform + crop 30%, Gaussian Blur + crop 30%, Lumetri + crop — **0% de pixels diferentes nos 10**.
    Medidas que levaram à regra: Crop DEPOIS do Transform 10,9% (o corte anda com ele; **Crop seguido de Transform** deixa
    o corte fixo no quadro e a imagem anda por baixo — o uso do autor para dividir a tela em 50%); Crop DEPOIS do Gaussian
    Blur 1,4% (o blur aumenta a área do clipe e o Crop mede a % sobre ela: borda 24 px fora). `crop_do_motion()` em `laboratorio-de-midia/lab/prproj_downgrade.py`.
  - ⭐ **A LUT DE ENTRADA DO CLIPE (Interpret Footage do 25/26) vira Lumetri Input LUT no 23.2** (`confirmado` por pixel,
    26.0.2 Mac × 23.2.0 Windows, 2026-10-07: 27,5 → 50,3 dB). O 26 guarda `VideoStream/InputLUTAsset` → `LUTAsset` (Id,
    Displayname, Filename, `Blob` = a LUT binária **ITX3**: 'ITX3', tamanho, canais, 0, domínio mín./máx. em 3+3 float, depois
    tamanho³×3 float32 — vira .cube sem perda). No 23.2 o Interpret Footage tem Input LUT e Color Space Override DESABILITADOS;
    LUT de entrada só pela Lumetri (Basic Correction > Input LUT > [Custom]): param **5** = 1, param **4** = caminho do .cube
    (UTF-16), param **98 "Embedded LUTs"** = **16 bytes de CHAVE + o tamanho da LUT (uint32) + o MESMO ITX3**, e o Blob (ID 1)
    com `<LUT>"caminho"</LUT>` e **`<embeddedlut><hash>CHAVE em hex maiúsculo</hash><filename>caminho</filename>`** e um
    `<guid>` próprio da Lumetri. O 23.2 acha a LUT embutida pela CHAVE (o caminho pode não existir): chave do Blob ≠ a do 98 =
    LUT ignorada (ou lida do arquivo, se o caminho existir); a MESMA chave/guid em várias Lumetri = a mesma LUT em todas;
    tamanho 0 = idem. Cada Lumetri: guid novo, chave = md5 da LUT. Implementado: `lut_embutida()` (molde da Lumetri do
    23.2 em `laboratorio-de-midia/lab/moldes/lumetri-input-lut-23.2.xml`), Lumetri como PRIMEIRO efeito do clipe. O 26 omite a
    lista de efeitos quando só há Motion/Opacidade padrão (`DefaultMotion`): criar `ComponentChain/Components`.
  - ⛔ **Cor log no 23.2:** a lista de LUTs técnicas da Lumetri do 23.2 só tem ARRI LogC e Phantom (nada de Sony S-Log3), e
    não há espaço de trabalho ACES nem leitura de ARRIRAW HDE (.arx: "File format not supported"). O S-Log3 com espaço de cor
    sobrescrito (26) abre como LOG CRU no 23 (20,5 dB; ACEScct 13,6 dB).
  - ⭐ **A cor LOG do 26 vira uma LUT MEDIDA na Lumetri do 23** (`confirmado` por pixel, 2026-10-07): carta 17³ (ProRes 4444 12
    bits, faixa de vídeo) interpretada como S-Log3/S-Gamut3.Cine no 26.0.2, frame exportado numa sequência Rec.709 e numa
    ACEScct → duas LUTs (`laboratorio-de-midia/lab/moldes/slog3-sgamut3cine-*-26.0.2.cube`, tabela `COR_LOG`), escolhidas
    pelo espaço de trabalho da sequência do clipe. No footage REAL (Sony A002C041): SEQ SONY 20,5 → **43,2 dB**; SEQ SONY
    ACES 13,6 → **34,1 dB** (o limite é a LUT 17³: aplicada pelo ffmpeg dá o mesmo 34,3). ARRIRAW HDE: o 23 não lê.
  - ⭐ **MARCADOR de sequência (regra do autor: retirar + marcador)** (`confirmado`, lido pela API do 23.2.0, 2026-10-07): `Markers`
    (ClassID bee50706…, Version 4) com `<Markers><Marker Index><First>guid</First><Second ObjectRef/>` → `Marker` (a45508e0…,
    Version 3) com `<DVAMarker>{"DVAMarker":{"mComment","mMarkerID":guid,"mName","mStartTime":{"ticks"},"mType":"Comment"}}`.
    A MESMA lista é da `Sequence/MarkerOwner` e do `VideoClip`/`AudioClip` da sequência no projeto (Source =
    `SequenceSource/Sequence`); o 26 omite tudo quando não há marcador — criar e ligar nos 3. Usado para ARRIRAW HDE (o 23
    não lê) e sequência ACEScct (cor aproximada): `marcadores_do_que_nao_existe()`.
  - ⭐ **O FADE NOVO de áudio ("Custom Fade", alças de fade do 25+)** (`confirmado`, 23.2.0, 2026-10-07): `AudioTransitionTrackItem`
    com MatchName/DisplayName "Custom Fade" e a curva em `FadeShapeType`/`FadeShapeValue` (+`CrossfadeSymmetry`). O 23.2 não
    tem: abre com "Video Transition missing: Custom Fade" (o rótulo diz "Video" mesmo sendo áudio) e guarda um lugar vazio.
    Vira "Constant Power" (o fade padrão do 23.2, decisão do autor), mesma duração/alinhamento; o 23.2 não grava os campos de
    curva em transição nenhuma. COPA (48) salva pelo 23.2: 91 Constant Power, 0 Custom Fade. `fade_novo()`.
  - ✅ **MÁSCARA DE OBJETO → TRACK MATTE no 2023** (`confirmado` no 23.2.0 real, Windows, pela ponte, 2026-10-08;
    `lab/prproj_mascara.py`, chamado pelo `para_2023` com `origem`/`destino`; testes `tests/test_prproj_mascara.py`):
    o `.prmf` (pasta `<projeto> Masks` ao lado da ORIGEM) vira um vídeo de matte (ProRes 422 HQ, branco = objeto, a duração e o
    TC da mídia) em `<destino> MATTES/`; um clipe dele na trilha de cima (mesmo Start/End, mesmos In/Out do clipe) e o
    **Track Matte Key** = `VideoFilterComponent` "AE.ADBE Legacy Key Track Matte" com 3 `VideoComponentParam`: ID 1 "Matte:"
    (ControlType 13) = NÚMERO DA TRILHA (1 = V1; 4294967295 = nenhuma), ID 2 "Composite Using:" (ControlType 7) = 1 luma /
    0 alfa, ID 3 "Reverse" = false. O clipe do matte (12 objetos: Media, VideoStream, VideoMediaSource, 2 VideoClip,
    MasterClip, ClipLoggingInfo, Markers, ClipChannelGroupVectorSerializer, VideoComponentChain, SubClip,
    VideoClipTrackItem) + o `ClipProjectItem` (no `RootProjectItem/ProjectItemContainer/Items`) e o item na
    `ClipTrack/ClipItems/TrackItems` da trilha são CLONADOS do gabarito salvo pelo 23.2 (`lab/moldes/track-matte-23.2.xml`).
    ⚠️ No `.prproj` há objetos DENTRO do `Project` com ObjectID que coincide com os de primeiro nível (escopo próprio): ao
    seguir referências, só os de primeiro nível. Prova: o rebaixado abre sem diálogo, o recorte é IDÊNTICO ao gabarito nativo
    (3/3 quadros) e ao esperado (dif. média 0,06/255); contra a máscara perfeita do B10, IoU 0,93–0,96 (a máscara GROSSA do
    `.prmf`; o 26 refina na hora: 0,985). O Premiere ESCONDE a trilha do matte sozinho (não precisa desligar). **TRILHA DO MATTE (regra do autor, 2026-10-08): nunca sobrescrever** — vai na
    PRIMEIRA trilha de vídeo ACIMA do clipe que esteja livre no trecho (qualquer clipe que encoste conta: camada de ajuste,
    título, gráfico); sem nenhuma, uma trilha NOVA no topo (clone da última `VideoClipTrack` sem os itens, `Track/ID` =
    `NextTrackID` do `VideoTrackGroup`, +1 nele, `Index` = posição, ref na `TrackGroup/Tracks`). Provado no 23.2: V2/V3
    ocupadas → matte na V4 criada, os dois clipes de cima intactos, o recorte idêntico ao do caso simples (caso
    `resultados/B10_ROTO/premiere-26.0.2-trilhas/`, teste `TestTrilhaDoMatte`). Máscara de
    objeto noutro efeito (Lumetri) ou sem os `.prmf` → retirada + marcador "RETIRADO: máscara de objeto". Na outra máquina o
    matte fica offline como qualquer mídia (religado pelo nome no teste). ⏳ retângulo/elipse/caneta (`AEMask2` tipos 1–3).
  - ✅ **17 LOGS DE CÂMERA → Lumetri Input LUT no 23** (`confirmado` no 23.2.0 real, 2026-10-08; `prproj_downgrade.COR_LOG`,
    bancada `lab/bancadas/carta_log.py`): o 26.0.2 oferece 32 espaços no override do clipe; os 17 LOGS (Apple Log, ARRI LogC3/LogC4,
    Canon Log/Log2/Log3, DJI D-Log, Fuji F-Log/F-Log2, Leica L-Log, Nikon N-Log, Panasonic V-Log, RED Log3G10, Sony S-Log/S-Log2/
    S-Log3+S-Gamut3/S-Log3+S-Gamut3.Cine) medidos com uma CARTA 33³ (35 937 quadrados de 20 px em 7 quadros de ProRes 4444 12 bits;
    a crua volta com erro ≤ 1,1/255) → uma .cube para Rec.709 e outra para ACEScct por log (`lab/moldes/<log>-{rec709,acescct}-26.0.2-33.cube`).
    O nome gravado no `OverriddenColorSpace` = o nome do menu (17/17). Prova (B10 1 s por log, 26 × 23.2): **33–40 dB** (99% dos
    pixels ≤ 5–11/255). A 17³ dava 31–40 (LogC4/RED 31): trocada pela 33³. ⚠️ O erro que sobra é um DESVIO DE TOM sistemático nas
    áreas planas (LogC4: 23 +3,7 R, −2,6 B), não borda nem grade — `hipotese`: o 26 decodifica o clipe com log diferente do 23
    antes da conversão. ⏳ medir a decodificação crua 26 × 23 do mesmo clipe.
  - ✅ **MÁSCARAS DE FORMA do 26 → a máscara do 23** (`confirmado` no 23.2.0 real, 2026-10-08; `prproj_mascara.formas_para_mascara_antiga`,
    testes `TestMascarasDeForma`): no 22/23 a máscara TAMBÉM é subcomponente (`SubComponents` do efeito), `AE.ADBE AEMask`, 15 params
    (o 23 grava os MESMOS 15 do 22; molde `lab/moldes/mascara-23.2.xml` = PRODUCAO-C 22.4 salvo pelo 23.2). O "Caminho" (26, param 7)
    e o "Mask Path" (22/23, param 6) têm os MESMOS vértices (0–1 do quadro: ponto, alça de entrada, alça de saída) — muda a embalagem:
    26 = u32 2, u32 1, 'V', u32 tamanho, u32 2, u32 n, por vértice u32 marca + 6 float32, 1 byte no fim; 23 = '2cin', u32 2, u32 0,
    u32 n, por vértice u32 marca + 6 float32 + u32 1. Keyframe = `ticks,base64;` no tempo da MÍDIA. TRACKING do 26 = param 6
    "Controlador": um keyframe por quadro, 104 bytes = u32 1 + matriz 3×3 em float32 coluna a coluna (a b 0 | c d 0 | tx ty 1, em
    coordenadas 0–1 do quadro: x' = a·x + c·y + tx, y' = b·x + d·y + ty), + outra matriz (a mesma em torno da ancoragem) + ancoragem.
    A conversão ASSA no caminho (23 = um keyframe de caminho por quadro, como o 23 grava o tracking) e aplica o TRANSFORMAR da própria
    máscara (params 9 posição, 10 ancoragem, 11 escala, 26/27 dimensionar, 12 rotação — rotação em PIXELS: p' = pos + R·S·(p − anc)).
    Ordem Transformar × tracking: `hipotese` (o B10 só tem um dos dois por máscara). Difusão 14→7, Opacidade 15→8, Expansão 16→9,
    inverter 17→10. Prova no 23.2 contra o render do 26: elipse IoU 0,99, retângulo 1,00, caneta rastreada 0,998, caneta com
    Transformar 1,00; diferença média ≤ 0,11/255 (caso `_transfer/…/MASCARA/FORMAS`).
    ⛔ Duas armadilhas que dão "The project appears to be damaged" no 23.2: (1) ORDEM dos filhos do `ArbVideoComponentParam` —
    Name, ControlType, StartKeyframePosition, **Keyframes, StartKeyframeValue**, ParameterID (o 23 grava os dois valores); (2) VALOR
    BINÁRIO ÓRFÃO — elemento base64 VAZIO com `BinaryHash` (deduplicação) cujo conteúdo não está no arquivo: ao clonar de outro
    projeto, preencher. O `BinaryHash` está em TODO valor binário (262/262); formato 12 bytes + u32 BE (tamanho + 12); o 23 não
    confere os 12 bytes com o conteúdo (gerar aleatórios, um por valor).
  - ⭐ **MÁSCARAS do 26 (`AE.ADBE AEMask2`)** (`confirmado` no arquivo, projeto do autor sobre o B10, 26.0.2, 2026-10-07):
    a máscara é um `VideoFilterComponent` "AE.ADBE AEMask2" pendurado em `SubComponents` do efeito (Opacidade, Lumetri…), não
    parâmetros do efeito como o `AE.ADBE AEMask` do 22/23. Param **22 "Type"**: (CORRIGE 2026-10-08, pelo render) **1 elipse,
    2 retângulo**, 3 caneta, **4 OBJETO**, 0 = caminho convertido de um projeto antigo
    (a rotoscopia automática). Param **7 "Caminho"** (ArbVideo, ControlType 22): base64 = cabeçalho de 25 bytes (2, 1, …, nº de
    vértices) + por vértice o ponto e as duas alças em float32 de 0 a 1. Param **6 "Controlador"**: o TRACKING (270 keyframes
    nos clipes com tracking). Máscara de OBJETO: param **24 "Controlador"** com os NOMES dos arquivos **`.prmf`** (CORRIGE 2026-10-08: em ASCII, dentro de um
    FlatBuffers em base64 no `StartKeyframeValue` — 408 bytes no caso do autor, com o id da máscara `6de0a819…` e os 3 guids
    `cd782492…`, `7d695d77…`, `aee4a2ca…` = os 3 `.prmf`; a outra máscara de objeto, sem passada, só tem o id) na
    pasta `<projeto> Masks/` ao lado do .prproj (binário próprio: 'prmf', versão 2, dados comprimidos — `pendente`).
    ⚠️ Keyframes de "Caminho" que NÃO animam (relato do autor): o arquivo guarda os 2 keyframes com o MESMO desenho, byte a byte
    — a edição no 26 regravou a forma nos dois. Qualidade contra a máscara perfeita do B10 (`laboratorio-de-midia/resultados/
    B10_ROTO/iou-premiere-26.0.2-autor.json`): OBJETO IoU **0,985**; retângulo 0,59, elipse 0,47, caneta 0,56 (com tracking).
  - ✅ **PRODUCAO-I (26.3) → 23.2 abre no 23.2.0 real** (2 seq, 66 itens). A recusa medida antes era do caminho de CONVERSÃO do
    25 (abrir um arquivo de formato antigo numa versão nova): ⛔ não usar versão mais nova como juiz de arquivo rebaixado.

⭐ **Versão por CLASSE, 23.2 × o que o Órbita grava** (medido comparando
`ORBITA MERGE TESTE.prproj`, salvo pelo 23.2, com um export do builder). Iguais em 26
classes; **diferem em 7**:

| classe | 23.2 | Órbita |
|---|---|---|
| `Project` | 41 | 43 |
| `ProjectSettings` | 18 | 21 |
| `Media` | 27 | 30 |
| `VideoStream` | 19 | 21 |
| `MasterClip` | 11 | 12 |
| `ClipLoggingInfo` | 8 | 9 |
| `IngestSettings` | 1 | 2 |

**Atualizado no mesmo dia**, com o autor acrescentando merged nativos e multicam ao projeto
23.2: mais 3 classes diferem — `SubClip` 5×6, `VideoClipTrackItem` 6×8,
`AudioClipTrackItem` 6×11. Todas as outras classes que o builder escreve têm referência
e batem. E há campos que o builder escreve e o 23.2 nunca grava (recursos de cor/render):

| classe | campos novos |
|---|---|
| `ProjectSettings` | `ColorAwareEffectsEnabled` |
| `VideoStream` | `OriginalColorSpace` |
| `VideoClipTrackItem` | `ToneMapSettings` |
| `AudioClipTrackItem` | `PreRenderComponentChainHashVersion` |
| `VideoTrackGroup` (mesma versão 13!) | `AutoInputGamutCompressionEnabled`, `IsColorAwareEffectsEnabledSameAsProject`, `IsGraphicsWhiteSameAsProject`, `OutputColorSpace`, `ToneMappingDesaturation` |

⭐ **`DummyCaptureSettings` v1 é o nome novo de `CaptureSettings` v10** — mesma ClassID
(`328c2aa2-…`). O 23.2 grava o bloco de captura DV completo.

Aplicado no Órbita como pós-processamento (`DRAMASYNC/src-python/prproj/alvo.py`,
`ExportOptions.premiere_alvo="2023"`). ✅ **`confirmado` em 2026-09-17:** um export
desse alvo (PRODE, 13 câmeras + WAV, com merged) **abriu no Premiere 23.2 (Windows)**: bins, 13
merged com Media Start certo, merged no Source, sequência montada com o som direto.
Ou seja: remover os campos novos e não preencher os que só o 23.2 escreve funciona.

⚠️ **O que NÃO se sabe:** se baixar só o número para 41 basta. Os objetos internos também têm
`Version` por classe, e um 23.2 pode não conhecer campos que o 25 escreve. Não "conserte"
trocando o número sem abrir o resultado no 2023.

## 11c. ⛔ A duração da CÂMERA: `ceil(duration_ms)` conta um frame a mais (2026-09-17)

Sintoma, visto pelo autor no Premiere 23.2: o merged clip tem **um frame preto no fim**.
A causa é aritmética, e vale para qualquer escritor que converta a duração do MediaInfo:

| arquivo (PRODE, 23,976) | frames reais (ffprobe `-count_packets` = MediaInfo `frame_count`) | `duration_ms` | `ceil(ms/1000·fps)` |
|---|---|---|---|
| `PANA2774.mov` | 1236 | 51552 | **1237** |
| `PANA2777.mov` | 1812 | 75576 | **1813** |
| `PANA2775.mov` | 2712 | 113113 | 2712 |

O `duration_ms` já vem arredondado PARA CIMA; o `ceil` arredonda de novo. ⭐ **Use a
contagem real** — o `pymediainfo` a entrega em `video_track.frame_count` (confirmado) — quando
o fps do arquivo é o do projeto. Sem ela, `ceil(x − 0,05)` (o erro de milissegundo a 60 fps
é ≤ 0,03 frame). `confirmado` na PRODE: nas **13 câmeras**, a conta antiga errava **5** contra o `ffprobe
-count_packets`; a nova erra **0**. O Órbita corrigiu em `sync/engine._duration_frames`.

⚠️ Um item de timeline 1 frame além do fim da mídia também vira frame preto numa sequência
comum, não só no merged. E ver `protocolos/avb/escrita.md` (o "`.mov` tem 1237 frames" de
2026-08-08 no DECISIONS do Órbita era, muito provavelmente, esta mesma conta).

⭐ **E NÃO é coisa do Premiere nem do `.mov`: o OP-Atom do Media Composer erra igual.**
`confirmado` em 2026-09-19 no Assist anterior, com 6 MXF de vídeo da `D:\Avid MediaFiles\MXF` e 2
XDCAM50, comparando com o `ffprobe -count_packets`:

| arquivo | fps | `duration_ms` | pacotes | `frame_count` | `ceil` antigo | nova |
|---|---|---|---|---|---|---|
| `V01.6A87F807_…V.mxf` | 29,97 | 11812 | 354 | 354 | **355** | 354 |
| `V01.6A87F83A_…V.mxf` | 29,97 | 48582 | 1456 | 1456 | **1457** | 1456 |
| `V01.6A87F829_…V.mxf` | 29,97 | 11812 | 354 | 354 | **355** | 354 |
| os outros 5 (23,976 e 29,97) | | | = | = | = | = |

**3 de 6 OP-Atom a 29,97 ganhavam um frame**, e a conta nova acerta os 8. ⚠️ O `nb_frames` do
ffprobe vem **vazio** nos oito (o MXF não declara), então quem conferir por ele não vê nada. O
`frame_count` do MediaInfo bate com a contagem de pacotes em todos. No Assist anterior, o motor do
Órbita portado recebeu a correção no mesmo dia (`motores/orbita/sync/model.duration_frames`).

## 11d. Importar merged num projeto: o NOME que chega (2026-09-17, 23.2)

O Premiere **ignora o `Name` do `ClipProjectItem`** de um merged ao importar um `.prproj`:
o item chega com o nome do `MasterClip` interno (`<arquivo> - Merged`). Renomear depois
(`item.name = x`) funciona. `observado` num 23.2, uma rodada, 13 merged.

## 11e. Acrescentar trilha de ÁUDIO numa sequência que JÁ EXISTE (BRINGBACKMIC, 2026-06-07)

> Fonte: `BRINGBACKMIC` (recupera os canais de áudio que ficaram fora da montagem — boom, lapelas,
> gravador externo — e grava uma CÓPIA `<nome>_BringBackMic.prproj`). Registrado pelo zelador do
> SSD em 2026-10-06, ao arquivar o projeto, a partir da memória do Claude do projeto.
> **Confiança `confirmado`:** cada regra abaixo saiu de um "project could not be loaded" ou de
> trilha muda, e o resultado foi aberto e ouvido no Premiere pelo autor (os 4 tipos: clipe
> multicanal normal, merged, nested e multicam). ⚠️ A **versão** do Premiere não foi registrada
> (junho/2026; o banco tem 25.6.5 medido em julho) — conferir a impressão digital antes de usar.
> Complementa as regras acima, que são de projeto gerado do ZERO; aqui é editar um projeto real.

**Montar a cópia:** serializar e reler (`ET.tostring` → `ET.fromstring`) em vez de `deepcopy` (lento
e mantém referências). Os objetos referenciáveis são os filhos DIRETOS de `<PremiereData>`; ObjectID
"duplicado" na árvore inteira vem dos `ProjectViewState` aninhados e é normal.

**Trilha nova (`AudioClipTrack`) — clonar uma existente e mudar o mínimo.** Construir do zero
deixa faltar campo e dá "project could not be loaded".
- ⚠️⚠️ `ClipTrack/Track/ID` é **inteiro sequencial** controlado por `TrackGroup/NextTrackID`
  (82, 83 → próximo 84). **UUID ali trava o load.** Ler `NextTrackID`, dar IDs crescentes e gravar o
  novo valor. (Só `AudioTrack/ID` é UUID.)
- ⚠️⚠️ A trilha precisa de `AudioComponentChain` e panner **completos**: o chain referencia
  `AudioFader` (com 2 `AudioComponentParam`) + `AudioMeter`; o panner
  (`StereoToStereoPanProcessor`) referencia 1 `AudioComponentParam`. Vazios = não abre. Clonar
  recursivamente seguindo os `ObjectRef`, com IDs novos e um `visited` POR TRILHA.
- ⛔ **Nunca compartilhar** `AudioComponentChain` nem panner entre clipes/trilhas: o projeto abre,
  mas os clipes não selecionam e o play derruba o Premiere. Clipe de áudio pode usar o chain
  MÍNIMO (só `DefaultVol` + `ComponentChain/Node` vazio), igual aos que o Premiere grava.

**⭐⭐ A trilha que aparece, mostra a forma de onda e NÃO TOCA.** Só **duas** estruturas crescem
com o número de trilhas de áudio (conferido num projeto de 100 trilhas feito pelo autor):
1. `AudioTrackGroup/TrackGroup/Tracks` → um `<Track Index ObjectURef>` por trilha;
2. `MasterTrack → AudioMixTrack → Inlet → AudioTrackInlet/Sources` → um
   `<Source Index ObjectURef>` por trilha.

Esquecer a (2) é exatamente o sintoma: trilha visível, forma de onda, **meter parado e nada no
master**; arrastar o mesmo clipe para uma trilha antiga toca. O `AudioMixTrack` tem **um** Inlet só,
qualquer que seja o número de trilhas — não criar Inlet novo. Ao reordenar, refazer os `Sources` na
ordem final e reatribuir os índices posicionais das trilhas deslocadas (`Track/Index`,
`MZ.SourceTrackNumber`, `ClipItems/Index`, `TransitionItems/Index`); o `Track/ID` não muda.

**Clipe novo — clonar um clipe existente:** tirar `HeadTransition`/`TailTransition` (apontam para
transições da trilha original). Dentro de `<SecondaryContents>` a tag é `<SecondaryContentItem>`
(referência a um `<SecondaryContent>` global). Trocar o canal = mudar `AudioClip/SecondaryIndex` +
`SecondaryContent/ChannelIndex` + `SubClip/OrigChGrp`.

**Merged clip:** cada trilha do merge é um `MasterClip` SEPARADO, marcado por
`MZ.MergeClipUtils.AudioTrackNumberFromOriginalMergedClip` (0, 1, 2…); não há GUID do merge
(agrupar por nome + número). ⚠️⚠️ O canal real da trilha K é o `StreamNumber` do `Media` (**stream =
K**, conferido contra um merge inserido pelo próprio Premiere) — não o `AudioTrackNumber` nem o
`ChannelIndex` do `SecondaryContent`, que são 0; usar sempre a fonte de índice 0 fez todas as
trilhas recuperadas tocarem o canal 1. `StreamNumber` ausente = stream 0. ⚠️ **Sincronia:** cada
arquivo do merge tem seu próprio In de base no MasterClip (WAV `285768000000`, câmera `0`); o clipe
recuperado do canal K leva `In/Out += base_K − base_referência` (sem isso, "−1:03" adiantado).
Os rótulos do merge no Premiere saem ímpares (A1, A3, A5…) — cosmético.

**Nested e multicam:** no nível do áudio os dois são `AudioSequenceSource` → `Sequence`; o ângulo
ativo da multicam não está no clipe de áudio. Recuperar pela janela visível:
`overlap = [max(nIn, iStart), min(nOut, iEnd)]`, `parent_start = parentStart + (overlapStart − nIn)`,
`media_in = mediaIn + (overlapStart − iStart)`. A multicam multicanal expõe N clipes no mesmo
instante: deduplicar por `(sequência, start, end)`.

**Canal "usado" se conta POR MÍDIA na timeline inteira**, agrupando por `(mídia, start, end)`, não
por clipe isolado (CAM A02, 4 canais, com o 2 em A3 e o 3 em A4 no mesmo lugar → recuperar 0 e 1).

**Diagnóstico decisivo para "could not be loaded":** gravar a cópia SEM mudança nenhuma
(round-trip do `ET`) e abrir. Se abre, o defeito está no que foi ACRESCENTADO, não na serialização
(o `ET` troca `&#10;` por `\n` e `<x/>` por `<x />`, e o Premiere aceita).

## 11f. 🆕 Group clip do Avid → MULTICÂMERA, subclipe sincronizado → MERGED, subclipe → subclipe (2026-11-12, Premiere 26.0.2, macOS) — `confirmado` (1 rodada, laboratório)

Ciclo Assist, `spikes/carta_aberta_para_premiere.py` (lê a bin do MC e escreve pelo `builder.py` do Sincronizar) +
o lado Avid em `spikes/carta_aberta_avid_g01.py`. Mídia do laboratório G01 (3 câmeras ProRes 23,976 + WAV, cada
quadro com câmera/TC/nº) — `MIDIAS DE TESTES/3 CONJUNTOS DOS APPS/_CICLO ASSIST/carta_aberta/`.
- ✅ **Multicâmera com as fontes INTEIRAS**: `_build_sequence(d, nome, multicam=True)` com UMA `CameraGroup` por
  ângulo, cada câmera em `timeline_start_frames` = o `Filler` do Avid, o WAV numa `Take` (2 canais ⇒ sem o
  adaptativo do defeito aberto), `Daily.start_tc_frames` = TC do primeiro quadro. Lido de volta pela API: V1/V2/V3 em
  72/240/144, o som em 0, `zeroPoint` = 10:00:02:00; `isMulticamClip()` true; no Source abre NO MODO MULTICÂMERA (grade)
  e os 3 ângulos mostram o MESMO TC na imagem (10:00:20:14). ⚠️ o áudio das câmeras não entra (`include_camera_audio`
  desligado): no Avid ele é ângulo de som.
- ✅ **Merged** do `.sync.01`: `CameraAngle.sync_offset_frames` = início do som − início da imagem (240) →
  `_build_merged_items`; o A1 do merged entra no 240, a imagem no quadro certo. ⚠️ O TC do merged sai 00:00:00:00
  (`zeroPoint 0`) — o do Avid mostra o da câmera; ⬜ pôr o TC.
- ✅ **Subclipe**: `createSubClip(nome, in, out, 0, 1, 1)` no item do EDITOR (in/out em `Time` com ticks) — o subclipe
  nasce na RAIZ; quadro e TC certos.
- ⛔⛔ **Os DOIS caminhos de levar o `.prproj` ao projeto aberto DUPLICAM a mídia**: `importFiles([prproj])` (cria a
  bin do arquivo com os 4 itens de novo) e `importSequences(prproj, [uid da multicâmera, uid da sequência do merged])`
  (os 4 de novo, dentro da bin ativa). As sequências apontam as CÓPIAS. **Editar ▸ Consolidar duplicatas não juntou
  nada** (sem diálogo; os itens nossos e os do editor não são "iguais" para ele — causa não medida). ⬜ o caminho sem
  duplicar. Os dois sem diálogo, `importSequences` aceita o UID da sequência INTERNA do merged e traz o merged inteiro.
- O nome do merged chega `<arquivo> - Merged` (§11d) → renomear.

### 11g. ⭐⭐ SEM DUPLICAR a mídia do editor: o ENXERTO numa cópia do projeto dele (2026-11-12, 26.0.2 Mac) — `confirmado` (1 rodada)

Cinco experimentos, um projeto limpo cada (a mídia do editor importada e salva antes):

| exp. | o que foi importado | itens novos de mídia |
|---|---|---|
| 1 | o nosso `.prproj` com os UIDs de `Media` + `MasterClip` trocados pelos do editor | ⛔ 4 (duplicou) |
| 2 | … + o UID do `ClipProjectItem` também | ⛔ 4 |
| 3 | uma CÓPIA do projeto do editor com uma sequência criada pela API | ✅ 0 (a sequência usa o item dele) |
| 5 | **a cópia do projeto do editor + os NOSSOS objetos enxertados**, toda referência à nossa mídia trocada pelos objetos DELE | ✅ **0** — multicâmera e merged na bin do editor, apontando os itens dele |

⇒ **O Premiere não desduplica por UID: desduplica quando o objeto de mídia É o do projeto** (o mesmo XML). O caminho:
salvar o projeto do editor → copiar o `.prproj` dele → acrescentar os nossos objetos com: `ObjectID` renumerados acima do
maior dele; `MasterClip`, `VideoMediaSource`, `AudioMediaSource` e `Markers` da nossa mídia crua trocados pelos dele
(casados pelo NOME do arquivo); a nossa mídia crua (MasterClip de bin e o fecho dele) FORA; a nossa bin na raiz da cópia
→ `importSequences(cópia, [uids das sequências])`. Ciclo Assist `spikes/carta_aberta_enxerto.py`.
- ⛔ Só objetos COM identidade: o `<Project ObjectRef="1"/>` de topo do nosso arquivo entrou junto na 1ª tentativa
  (exp. 4) e o `importSequences` devolveu `true` SEM trazer nada (a classe do "true calado" acima).
- ⛔ A linha da bin que aponta um item que ficou fora tem de sair (pendência solta).
- ⛔⛔ **O CANAL mora no `SecondaryContent`** (`<Content ObjectRef=fonte/>` + `<ChannelIndex>`), um por canal que o clipe
  usa. O nosso escritor faz UMA fonte de áudio POR CANAL no WAV (§7.1), cada uma com `ChannelIndex 0`; o projeto do
  editor (import nativo do 26.0.2) tem UMA fonte com os 2 canais (um `AudioClip` com dois `SecondaryContent`, 0 e 1; o
  grupo de canais do MasterClip: um vetor `ChannelType 1` com `mSourceChannelIndex` 0 e 1). Ligar as duas nossas na
  dele SEM mexer no índice pôs o **canal esquerdo nas DUAS trilhas** da multicâmera — medido com um WAV de L = cena,
  R = tom de 1 kHz, exportando cada trilha sozinha (`exportAsMediaDirect` + `Wave48mono24.epr`, as outras `setMute(1)`):
  A2 com 0,2 % de energia em 1 kHz e correlação 1,000 com o L. ⇒ a fonte nossa de ordem i que cai na fonte do editor de
  ordem j pede `ChannelIndex + (i − j)`. ✅ Depois: multicâmera A1 = L (corr. 1,000), A2 = R (100 % em 1 kHz); o merged
  (que usa a PRÓPRIA cópia do WAV, intocada) já saía certo, com o som começando a 10,010 s do WAV = 240 quadros exatos.
- ⚠️ Os internos do merged (a cópia própria da câmera, §2) continuam com `Media` própria — não aparecem como item.
- ⬜ Pede o projeto SALVO (lê o arquivo do disco): o que o editor importou e não salvou não está lá. Mídia que o projeto
  não tem → importar pela API, salvar, então enxertar.

### 11h. ⭐⭐ Timeline EDITADA escrita pelo app no `.prproj`, sobre o MOLDE do próprio Premiere (2026-11-13, 26.0.2 Mac) — `confirmado` (1 rodada, V1 real)

Ciclo Assist, Carta Aberta (`cicloassist/carta/entrega_prproj.py`): a V1 da `PRODA_CORTE.02.Exported.01` (PRODUCAO-A,
95 clipes OP-Atom DNxHR LB) — a mesma que travou o importador de XML (`plugins/premiere-cep/api-extendscript.md`).
- ✅ **Os 41 arquivos OP-Atom de vídeo importados UM A UM pela API entram em 0,1–2,3 s cada**, sem diálogo: os arquivos
  não travam nada — quem travava era o importador de XML. ⭐ E o 26.0.2 junta sozinho o vídeo OP-Atom com os irmãos de
  som (`X.mxf` + `X_A01/_A02`): o item tem `AudioMediaSource` com 2 canais (`AudioChannelLayout` de 2) — um clipe A/V.
- **O molde:** o Premiere monta uma sequência curta (`cicloMontar`) e salva; o app lê como ele guarda o clipe e copia:
  `VideoClipTrackItem{ClipTrackItem{ComponentOwner→VideoComponentChain, TrackItem{Start,End}, SubClip}, FrameRect da
  mídia}` → `SubClip{Clip→VideoClip NOVO, MasterClip→o do item, Name, OrigChGrp 0}` → `VideoClip` = cópia do VideoClip
  do master (mesmo `Source` e `Markers`, `ClipID` novo) com `InPoint`/`OutPoint` em ticks **contados do início da
  MÍDIA, não do TC**. ⛔ `Start` some quando é 0. TC de início da sequência: `MZ.ZeroPoint` (§11).
- ✅ **Lido de volta pela API (`cicloLerSequencia`): 93 de 93 exatos em ticks** (início, entrada, duração); abriu na
  tela com TC 01:00:00:00. Sem duplicar mídia: a sequência aponta os itens que o próprio Premiere criou.
- ⬜ Ainda não escrito (fica de fora e DITO): velocidade (2 na V1), transição, clipe desligado, enquadramento (stretch
  ×7 vai em tamanho real), som, outras trilhas, `importSequences` para o projeto do editor.

### 11i. ⭐⭐ O SOM da timeline no `.prproj`, sobre o molde do Premiere (2026-11-14, 26.0.2 Mac) — `confirmado` (1 rodada, 763 clipes)

A `PRODA_CORTE` inteira (V1–V3 + A1–A16): **763 de 763 clipes exatos em ticks**, **763 de 763 no ARQUIVO certo** e **657
de 657 com o volume certo**, lidos de volta pela API (`cicloLerSequencia` com detalhe: `projectItem.getMediaPath()` e o
`Nível` do Volume). 227 arquivos importados um a um em 27 s, nenhum travou.
- ⭐ **OP-Atom de som importado SOZINHO vira um item MONO por arquivo** — o master só de som (`X_A01…_A05`) dá 5 itens,
  e o `_A01` de um master COM imagem, importado à parte, também vira item próprio (a imagem só junta os irmãos quando
  é ela que é importada). ⇒ O canal do Avid é o ARQUIVO: o clipe de A2 aponta o item do `_A02`, `ChannelIndex 0`.
- **O WAV estéreo** entra UM item com 1 `AudioClip` de 2 canais (Use File). O canal de dentro se escolhe como o Premiere
  faz no item A/V (dois clipes mono com o MESMO `Source`): o `AudioClip` da trilha com UM `SecondaryContent`
  (`ChannelIndex` = canal − 1) e layout mono. Regravado pelo Premiere, ficou igual (29 com `ChannelIndex 1`). ⚠️ O
  ouvido não conferiu ainda (a API não diz o canal de dentro).
- **A estrutura** (molde `MOLDE SOM`): `AudioClipTrackItem{ClipTrackItem{ComponentOwner→AudioComponentChain,
  TrackItem{Start,End}, SubClip}}` → `SubClip{Clip→AudioClip NOVO, MasterClip, Name, OrigChGrp = nº do clipe de som no
  master}` → `AudioClip` = cópia do do master **sem `InUse`**, `InPoint/OutPoint` do início da mídia.
- ⭐ **O volume do clipe** (molde `MOLDE GANHO`, `setValue` pela API e lido no arquivo): sem ganho, a cadeia só tem
  `DefaultVol true`; com ganho, um `AudioFilterComponent` `FilterMatchName "Internal Volume Mono"` com 2 params
  (`Silenciado`, `Nível`), e o Nível é CRU: **`10^((dB−15)/20)`** — 0 dB = 0,17782793939114 (o padrão lido pela API),
  teto 1 = +15 dB (`setValue(2)` voltou 1). `CurrentValue` e o 2º campo do `StartKeyframe` levam o mesmo número. ⚠️ Os
  nomes dos params vêm no idioma da interface (`Nível`, `Silenciado`): copiar do molde, nunca escrever o nome.
- **Trilha de som que falta**: cópia da 2ª do molde (`AudioClipTrack` com `Track/ID` novo a partir de `NextTrackID`,
  os `Index` novos, `AudioTrack/ID` novo, a cadeia `AudioFader`/`AudioMeter` e o `StereoToStereoPanProcessor` clonados
  com ids novos) — 12 trilhas criadas, o Premiere abriu e regravou. As do molde são estéreo ("Standard"); clipe mono
  nelas toca no centro.
- ⬜ Ainda de fora (e DITO): efeitos AudioSuite, o vínculo imagem-som (`Links`). A transição entrou no §11j; desligado
  e velocidade no §11k.

### 11j. ⭐⭐ A TRANSIÇÃO: do modelo do Avid (sobreposto) para o do Premiere (encostado no corte) (2026-11-14, 26.0.2 Mac) — `confirmado` (1 rodada, 99 transições)

Molde pelo próprio Premiere (`MOLDE TRANSICAO`, QE `qeItem.addTransition(tr, cabeça?, "00:00:00:20", "00:00:00:00",
alinhamento, false, true)` — alinhamento 0,5 = centrado, 0 = começa no corte, 1 = acaba nele; o nome da transição no
idioma do app: "Cross Dissolve" ficou em inglês, a de som veio "Potência constante").
- **A estrutura:** `VideoTransitionTrackItem`/`AudioTransitionTrackItem{TransitionTrackItem{TrackItem{Start,End},
  Alignment, DisplayName, MatchName, HasOutgoingClip, HasIncomingClip}}` — sem `ID`. ⭐ **`Alignment` = corte − início,
  em ticks** (centrado de 20 q = 10 q; começa no corte = 0; fade de saída = a duração). O de vídeo leva um
  `VideoFilterComponent` (26 params; o **Cross Dissolve do 26 é `AE.AE_Impact_Dissolve`**, o do FilmImpact); o de som
  só um `AudioChannelLayout` estéreo (`MatchName "Constant Power"`, que não muda com o idioma). A trilha lista em
  `ClipTrack/TransitionItems/TrackItems`; o clipe A aponta em `ClipTrackItem/TailTransition`, o B em
  `HeadTransition` (depois do `SubClip`, nessa ordem).
- ⭐⭐ **Os dois modelos:** no Avid (leitura do Conformar) A vai até o FIM da transição e B começa no INÍCIO dela —
  sobrepostos. No Premiere os dois ENCOSTAM no corte e a transição o atravessa usando a mídia por baixo. ⇒ A acaba no
  corte; B começa no corte com a entrada atrasada no mesmo tanto (clipe entre duas transições: aparado dos dois lados);
  a transição cobre o mesmo trecho. **Nenhum corte muda de lugar.** O inverso (Premiere → Avid) é o
  `sobrepor_transicoes` do Conformar (`avb_export/do_prproj.py`).
- **Um lado só** (do vazio / para o vazio): o clipe fica onde o Avid o pôs, a transição vai na cabeça (`Alignment` 0,
  `HasOutgoingClip false`) ou na cauda (`Alignment` = duração, `HasIncomingClip false`) — igual ao que o Premiere faz.
- ⛔ **A entrega SEM transição tinha deixado os pares SOBREPOSTOS na trilha** (a v04 da PRODA_CORTE: o Premiere abriu e
  regravou sem reclamar, e a API leu cada clipe "exato"). Conferir clipe a clipe não pega sobreposição: hoje a escrita
  conta "clipes sobrepostos sem transição" (0 na PRODA_CORTE).
- ✅ **Medido na PRODA_CORTE** (v06, aberta e regravada pelo Premiere, lida pela API): 763/763 clipes = o Avid com a
  regra acima (conferência independente); 99/99 transições = as do Avid, encostadas no clipe certo (64 de dois lados,
  21 fades de entrada, 14 de saída, 163 vínculos). Na tela: fade de 20 q em 01:00:38:12 e crossfade de 40 q centrado
  em 01:04:52:14. 44 ficaram de fora sem clipe escrito em nenhum dos lados (offline, velocidade, desligado, o matte da
  V3). ⚠️ Nenhuma de VÍDEO entrou na PRODA_CORTE (as 2 são do matte) — a de vídeo só está provada no molde.
- ⚠️ `BLEND_AUDIO_DISSOLVE` → "Potência constante": a curva do Avid depende da configuração de áudio do projeto dele
  (não lida); não medido se o Avid desta timeline usava potência constante ou linear.

### 11k. ⭐ VELOCIDADE e clipe DESLIGADO no `.prproj`, sobre o molde do Premiere (2026-11-14, 26.0.2 Mac) — `confirmado` (1 rodada)

Molde `MOLDE VELOCIDADE` (QE `qeItem.setSpeed(v, "", false, false, false)` sem ripple; DOM `trackItem.disabled = true`).
- **Desligado:** `<IsMuted>true</IsMuted>` no `ClipTrackItem`, depois do `SubClip` — o mesmo na imagem e no som. É o
  Selector do Avid no ramo vazio (`[Filler, clipe]`, `selected=0`; o "Mute Clips" do som).
- **Velocidade constante:** `PlaybackSpeed` no `Clip` do `VideoClip` da sequência (float32 quando o Premiere escreve:
  0,85 → `0.8500000238418579`; float64 escrito por nós ele aceita e mantém). ⭐ `InPoint` = a entrada na MÍDIA (sem
  dividir); `OutPoint` = entrada + duração na timeline × velocidade. O `setSpeed` não liga optical flow: o arquivo fica
  sem `TimeInterpolationType` (Frame Sampling); escrito `2` (optical flow, §estruturas) o Premiere mantém ao regravar.
- ⛔⛔ **A API lê a entrada DIVIDIDA pela velocidade:** `getInPoint`/`inPoint` de um clipe a 85 % com a mídia em 1 s
  devolve 1,1765 s; a 125 % com a mídia em 5 s, 4 s. Conferência pela API tem de multiplicar de volta.
- **Do Avid** (`MotionEffect`, leitor do Conformar): a velocidade é a curva que o Avid integrou (`mapa`: 79 q → 67,15 =
  85 %), não o `speed_ratio` arredondado (`[79, 68]`). `[1000, 1001]` com curva zero e classe `native` é CONFORMAÇÃO
  (fonte a 24 numa sequência 23,976): tempo REAL, sem `PlaybackSpeed`, com a entrada contada na taxa da FONTE (37
  quadros a 24 = 37 × 10584000000 ticks). Retime `optical_flow` → `TimeInterpolationType 2`.
- Transição junto de clipe com velocidade: o atraso da entrada de B no corte anda na mídia × velocidade.
- ✅ **PRODA_CORTE (a `Exported`), v08 aberta e regravada pelo Premiere, lida pela API:** 798/798 clipes (+2 com
  velocidade, aparecem "[85%]"/"[125%]"; +33 desligados, escuros na timeline) e 105/105 transições. ⚠️ Os 26 de
  conformação são efeitos AMA a 24 q/s que estão OFFLINE nesta máquina: a conta da conformação só está no teste.
- ⚠️ Fica de fora (dito): velocidade variável, ao contrário, congelamento.

### 11l. ⭐⭐ Subclipe SINCRONIZADO do Avid → MERGED no `.prproj`, sobre o molde do Premiere (2026-11-14, 26.0.2 Mac) — `confirmado` (1 rodada, 36 merged)

Molde: merged feitos pelo autor no Premiere, câmera OP-Atom + som OP-Atom (um item MONO por `_A0N`).
- ⭐⭐ **Dois caminhos, dois resultados (autor):** pela BIN (sync por áudio) o merged pega as mídias INTEIRAS (preto no
  início porque o som começa antes, só imagem no fim); pela TIMELINE, aparado, ele fica só onde imagem e som se
  encontram — **o equivalente do subclipe do Avid**: no `04-01-02`, câmera 0–12338 e som a partir de 214, os números do
  Avid. ⚠️ Diferença: na timeline do Premiere dá para PUXAR a alça além do recorte (o triângulo branco marca o fim da
  mídia); o subclipe do Avid não. ⇒ Premiere → Avid: o subclipe tem de ser aparado onde só um lado existe.
- **A forma:** `ClipProjectItem` → `MasterClip` do merged (Clips: `AudioClip→AudioSequenceSource` +
  `VideoClip→VideoSequenceSource`, sem In/Out; `AudioComponentChains` e `ClipChannelGroupVector` com UM item MONO por
  canal) → `Sequence` com `BE.Sequence.IsMergedClip true`, `MZ.ZeroPoint` = o `Start` da `Media` da câmera + a entrada
  dela (o TC), V1 = a câmera, A1..AN = um canal cada (`_A01` → trilha 0, ordem certa), um `Link`, e a master do mix
  (`AudioMixTrack/Inlet` = `AudioTrackInlet/Sources`, uma por trilha). Os COMPONENTES (fora da bin): a câmera e cada
  canal são CÓPIAS do `MasterClip` importado — `Media` própria idêntica (só o `ModificationState` vazio), o nome do
  merged, `Node/Properties/MZ.MergeClipUtils.ComponentMasterClipOriginalName` (+ `AudioTrackNumberFromOriginalMergedClip`
  = 0..N−1 no som, sem `DefMappingID`), In/Out aparados (câmera = entrada da imagem; som = entrada do som; Out = In +
  duração), `ClipID` novos.
- ⭐ **Na TIMELINE o clipe aponta o COMPONENTE**, não o MasterClip do merged: o de imagem a câmera, o de som o canal
  (`OrigChGrp 0`), com a entrada no tempo da MÍDIA (o som = a da imagem + a sincronia). Vínculo por `Link`.
- **Escrita (Ciclo Assist `carta/merged_prproj.py`):** o que é do merged é CLONADO do molde de mais canais (N a menos:
  as trilhas, cadeias, grupos, o lugar no `Link` e no `AudioTrackInlet` saem); o que é da mídia vem do item IMPORTADO.
  Os canais vêm do SUBCLIPE (trilhas do master de som que ele usa), não do gravador (PRODUCAO-A: um de 10 canais com
  subclipe de 5).
- ⛔⛔ **Duas armadilhas medidas na escrita:** (1) ObjectID repetido (o escritor da timeline numerava objetos ainda fora
  do arquivo e o merged não os via): 4466 e depois 84 repetidos → "Não foi possível carregar o projeto, provavelmente
  porque ele está danificado ou contém elementos desatualizados" (o Premiere não cai). Conferir repetidos e referências
  soltas ANTES de abrir. (2) ⛔ **Trilha de som clonada fora do `AudioTrackInlet` da master fica MUDA**: as entregas de
  §11i–§11k tinham 4 de 16 na lista, e o Premiere regravou assim sem reclamar — a API lia cada clipe "exato".
- ✅ **PRODA_CORTE.00.2** (a timeline ORIGINAL), v07 aberta e regravada pelo Premiere, lida pela API: 848/848 clipes e
  157/157 transições; 36 merged (24 de 5 canais, 12 de 3), 709 clipes da timeline apontando um merged; na tela o clipe
  se chama `04-01-02`, cor de mesclado, os canais 1–3 nas A1–A3. Ouvido pelo autor: certo, áudio inclusive.
- ✅ **O `Link` imagem-som** (v08): `Sequence/PersistentGroupContainer/LinkContainer/Links/Link ObjectRef` →
  `Link{TrackItemGroup{TrackItems{TrackItem Index ObjectRef}}}` (sem ID próprio). A timeline do Avid não tem vínculo.
  ⭐ **O vínculo é de UM TRECHO (autor, 2026-11-14): "se houver corte, o trecho perde o link".** O grupo de som = os
  canais do mesmo take, em sincronia, que começam e terminam JUNTOS — vinculado entre si mesmo sem imagem; a imagem
  entra em UM grupo só, o em sincronia de maior sobreposição (o som que começa um pouco depois ou vai um pouco além é
  dela); o grupo depois de um corte fica só entre si. A 1ª versão (a imagem com TODOS os sons do take debaixo dela)
  fez vínculos de 11 clipes com pedaços intermitentes — "não é algo padrão de uso". v09: 163 vínculos (91 com imagem,
  máx. 6 clipes), mantidos ao regravar; selecionar `04-04-05 [V]` traz só o 1º grupo. `entrega_prproj._vincular`.
- ✅ **Os RECORTES (subclipe de UM master) → SUBCLIPE do Premiere** (n'PRODUCAO-A a diária 01, praia, sem som
  direto — autor: o Premiere não faz merged sem casamento mínimo; usa-se o subclipe, renomeado com o padrão do Avid).
  Molde `item.createSubClip(nome, Time, Time, 1, 1, 1)`: um `MasterClip` NOVO que é a cópia do importado (`Media` e
  fontes próprias, `InPoint`/`OutPoint` nos clipes) num `ClipProjectItem` novo. ⛔ **Os limites fixos moram em
  `*MediaSource/MediaSource/Content/{StartBoundary, EndBoundary}`** — escritos direto em `MediaSource`, o Premiere os
  DESCARTA calado ao regravar (medido na v10). ⚠️ O `createSubClip` (26.0.2) deixou o nome do ITEM igual ao do master e
  pôs o nome pedido só no `MasterClip`: renomear os dois. Na timeline o clipe aponta o `MasterClip` do subclipe. v11: 8
  subclipes com os limites mantidos ao regravar, 28 clipes da timeline neles. Ciclo Assist `merged_prproj.escrever_subclipe`.
- ⚠️ **OP-Atom de SOM no Premiere (26.0.2 Mac, `importFiles`): cada `_A0N` de um master só de som vira um item MONO
  à parte** (5 itens soltos para um gravador de 5 canais); o de imagem junta os irmãos. ⬜ Não medido: o Navegador de
  mídia, ou os N arquivos num `importFiles` só — pergunta do autor, 2026-11-14.
- ⚠️ O `take.resolver` não via o som EMBRULHADO num `PanVolumeEffect` dentro do subclipe (o ganho de clipe do subclipe;
  PRODUCAO-A: 3 subclipes, dois com +12 dB) e o tomava por "só imagem" — corrigido; o ganho de dentro soma ao clipe.

### 11m. ✅ `importSequences` de uma timeline com MERGED e SUBCLIPES para o projeto ABERTO (2026-11-14, 26.0.2 Mac)

O passo final do "Importar para o Premiere": num projeto aberto que é o do editor (aqui, uma cópia da v01 de moldes,
com a mídia importada e SEM a nossa timeline), `app.project.importSequences(v11, [uid da sequência])` trouxe a
sequência E os merged/subclipes que ela usa, e NÃO duplicou a mídia (contado pela API antes/depois, `cicloEspecie`):
merged 4 → 40 (+36), clipe 282 → 290 (+8 = os subclipes), sequência 7 → 8. A sequência importada, lida pela API:
848/848 clipes. Funciona porque a v11 é ENXERTO do projeto do editor (os objetos de mídia são os dele, §11g).
⚠️ O UID da sequência importada coincidia com o de uma sequência que JÁ existia no projeto (o molde renomeado) e entrou
assim mesmo, como sequência nova. Ciclo Assist `host.jsx` `cicloImportarSequencias`.

### 11n. ⭐⭐ O "Importar para o Premiere" de ponta a ponta, num projeto do editor SEM moldes (2026-11-14, 26.0.2 Mac) — `confirmado` (4 rodadas)

O projeto do editor não tem as peças que a escrita copia (§11h–§11l). Caminho medido (Ciclo Assist
`carta/importar_premiere.py` + `carta/moldes_prproj.py`, rota `/carta/premiere/importar`), **~20 s** para a PRODA_CORTE.00.2:
1. a mídia que falta entra pelo Premiere e o projeto do editor é SALVO; 2. cópia de trabalho na pasta interna da Carta;
3. o que o projeto do editor JÁ tem serve de molde (som mono com/sem ganho, transições, merged — procurados em qualquer
sequência dele); o que falta o Premiere monta na cópia, aberta AO LADO (`openDocument`), num `cicloMontar` só; salvar,
o editor de volta à frente, fechar a cópia; 4. a timeline escrita numa segunda cópia; 5. `importSequences`.
- **Resultado:** num projeto novo só com as 259 mídias: 848 clipes, 157 transições, 8 subclipes, 163 vínculos — posição,
  entrada, duração e desligado iguais à v11 nos 848 (lido pela API). Num projeto que já tinha merged (o do autor): 36 merged.
- ⭐ **A sequência-molde é feita SEMPRE na cópia:** ela é consumida (esvaziada e renomeada), e uma sequência do editor
  consumida voltaria com o mesmo ObjectUID da dele.
- ⛔⛔ **O NOME que o Premiere mostra é o do ITEM do projeto, não o `Sequence/Name`:** renomeando só a sequência, ela
  entrou como "MOLDES (Ciclo Assist)". A cadeia a renomear: `Sequence` ← `*SequenceSource` ← `VideoClip/AudioClip`
  (`Clip/Source`) ← `MasterClip` (`Clips`) ← `ClipProjectItem` (`ProjectItem/Name`). (A `ExtendScript` `sequence.name`
  devolve o `Sequence/Name`: dizia "PRODA_CORTE.00.2" para as que o painel mostrava como MOLDES.)
- ⛔ **Achar a sequência a importar pelo NOME pega a homônima que o projeto do editor já tem** (a cópia é dele): o
  `importSequences` trouxe a velha de novo. Usar o ObjectUID da que foi escrita.
- ⛔ **O id que o Premiere dá à sequência importada (`sequenceID`) não é o ObjectUID do arquivo:** as novas saem da
  diferença antes/depois de `app.project.sequences`.
- **O que entra cai na RAIZ** (sequência e merged novos; os subclipes iguais aos que já estão lá não se repetem — 8 a mais
  só na 1ª vez); `moveBin` leva para a bin de destino (lida ANTES de abrir a cópia: abrir muda o foco). 37 movidos.
- ⚠️ **Importar a MESMA timeline de novo duplica os merged** (40 → 76): cada escrita faz merged novos. A mídia e os
  subclipes não duplicam.
- ⚠️ A transição-molde precisa dos DOIS lados: com planos de 1 s a partir do início da fonte e 10 quadros o Premiere fez a
  transição de um lado só (`HasOutgoingClip` false), que não serve; planos de 2 s com sobra e 20 quadros: dois lados.
- ⭐⭐ **Sem merged no projeto do editor: a CALIBRAGEM** (decisão do autor: calada, só na cópia). Um `.prproj`-modelo do
  app — um merged feito pelo Premiere sobre mídia SINTÉTICA (câmera MOV 320×180 1 s + 16 canais mono OP-Atom, ~2,6 MB) —
  entra na cópia por `importFiles([modelo], true, bin, false)` (~1–2 s) e o merged dele (16 canais) vira o molde. Medido
  em projetos só com a mídia: 36 merged, 848/848 iguais à v11, ~24 s no total; nada do modelo chega ao projeto do editor
  (só a sequência e os 36 merged dela). Um merged feito pela BIN (Mesclar clipes, sincronizar por Timecode) serve de
  molde tanto quanto o feito pela timeline. Ciclo Assist `cicloassist/carta/moldes/` (LEIA-ME com a receita).
- ⛔ `openDocument` de um projeto aberto às vezes deixa o `app.project` no antigo logo depois (1 em ~10, com o Premiere
  recém-ocupado): conferir e repetir (`cicloFrente`); fechar a cópia recebe EXPLICITAMENTE para quem voltar.

### 11o. ⭐⭐ MÍDIA OFFLINE escrita por fora: o "Arquivo offline" do Premiere é um molde pequeno, e o enxerto dele abre e religa (2026-11-25, 26.0.2 Mac) — `confirmado` (1 rodada)

O plano sem mídia não pode sumir da timeline (regra do autor). Hoje o Conformar põe só um marcador "OFFLINE" no lugar e a
Carta deixa o clipe de fora. A ideia do autor (28/10): o recurso da bin **Arquivo ▸ Novo ▸ Arquivo offline…** com os
dados que temos. Medido (projetos em `MIDIAS DE TESTES/1 PRODUCOES/PRODUCAO-A/SAIDAS/LAB OFFLINE PREMIERE/`, DIARIO.md):
- **Nem o ExtendScript nem o QE criam arquivo offline** (`qe.project`: newBarsAndTone, newBlackVideo… nenhum offline;
  `app.project` também não). O item do menu só se HABILITA com o painel Projeto em foco.
- **O que o Premiere escreve** (plano de câmera: 1920×1080, 23,976, estéreo, TC 04:53:47:11, 14578 q):
  `ClipProjectItem` → `MasterClip` com `MZ.offlineclip.{VideoFrameRate, AudioFrameRate, VideoFrameRect.Width/Height,
  VideoPAR.num/den}` nas Properties → `ClipLoggingInfo` (TapeName, ClipName, TimecodeFormat 110, MediaIn/OutPoint em
  ticks, MediaFrameRate) + VideoClip/AudioClip + Video/AudioMediaSource (OriginalDuration) → **`<Media>` só com
  `Start` (o TC em ticks), `TapeName`, `ImplementationID` zerado, `Title` (o nome do ARQUIVO) e `OfflineReason 5`** +
  Audio/VideoStream (Duration, FrameRect, FrameRate, o layout dos canais). **Sem caminho, sem `FileKey`, sem
  `ImporterPrefs`** (o `getMediaPath()` devolve ""). O nome do item é o nome do arquivo digitado.
- **Religa:** `projectItem.changeMediaPath(<o original>, true)` → online, e o clipe da sequência mantém entrada, saída,
  duração e TC de início (o arquivo real tem o mesmo TC).
- **Escrito por fora (o enxerto):** os mesmos objetos copiados para uma cópia de OUTRO projeto (ids novos, `ObjectID`
  no fim e em ordem crescente §0.1, o item na `<Items>` da bin raiz, gzip com o cabeçalho do Premiere §0) → o
  `openDocument(c, true, true, true)` abriu sem diálogo, o item offline com o TC e a fita; `changeMediaPath` religou
  igual. ⇒ o app pode pôr o plano offline NO LUGAR (Conformar Avid → Premiere e a Carta), com o que o protocolo de
  origem diz da mídia.
- **Medido depois (o mesmo dia):** o só de som que o diálogo grava (Contém: Áudio) não tem vídeo e o `ClipLoggingInfo`
  leva `CaptureMode 1` e a taxa do ÁUDIO (`5292000`); sem TC nem fita, `Start`/`TapeName` não são gravados. Mono =
  `channellabel 0` + `ChannelType 0` (o dos sons importados); estéreo = 100/101 + `ChannelType 1`. Gerador:
  `Ciclo Assist modulos/conformar/motor/prproj/offline.py` (o texto sai IGUAL ao do Premiere, conferido linha a linha).
  - `importFiles([aux.prproj], true, bin, false)` traz os itens offline DIRETO na bin, sem diálogo; o item com o MESMO
    nome de um offline que já está no projeto NÃO entra de novo (o Premiere descarta a duplicata).
  - Subclipe + `overwriteClip` de item offline funcionam (trechos do meio, no lugar). ⛔ O SUBCLIPE leva a própria cópia
    da mídia: religar o item-pai NÃO religa a sequência — religue os subclipes também.
  - ⭐ **O TC declarado não decide o trecho:** o mesmo plano declarado com TC 0 e religado ao arquivo de TC 04:53:47:11
    manteve a entrada contada do INÍCIO DO ARQUIVO (2000 q). O TC é para mostrar e para religar por TC.
  - ⛔⛔ **No som OFFLINE a entrada do subclipe cai numa grade de 1/25 s** (0,959 q a 23,976 — pedidos de 500 a 500,6
    deram 499,66; de 500,75, 500,62) e o clipe na sequência fica no quadro de BAIXO: 500 virava 499 e CONTINUAVA 499
    depois de religar. Conserto: a entrada no 1º ponto da grade >= o quadro (lendo de volta) → 500, 777, 1234 exatos,
    antes e depois de religar. O vídeo offline não tem isso (2000 exato).
  - ⬜ Pendentes: Premiere mais antigo que o molde vazio (26.0.2) importando o auxiliar.
- ⭐⭐ **Som de MAIS DE 2 CANAIS (o som direto polifônico) — `confirmado` (26.0.2 Mac, 2026-11-25):** o Premiere guarda
  o WAV de 5 canais importado (`PRODUCAO-A - 05-04 C4 P1-T001.WAV`, `LAB OFFLINE MULTICANAL v01`) como **N canais
  MONO**: N `AudioComponentChain`, N `AudioClip` mono (um `SecondaryContent`, `ChannelIndex 0`), N `AudioMediaSource`,
  e **um `<Media>` POR CANAL** (o mesmo arquivo; `StreamNumber` 1…N−1 do 2º em diante, ausente no 1º), cada um com o
  seu `AudioStream` mono; N vetores de canal com `ClipChannelSerializer` `SourceClipIndex` k / `mSourceChannelIndex 0`
  (§6, "MÍDIA multicanal"). O offline de N canais escrito NESSA forma (cada `<Media>` com `Title`, `Start`,
  `StreamNumber` e `OfflineReason 5`) abriu, e o `changeMediaPath` ao WAV real religou o item inteiro: 10/10 clipes
  online, mesmas posições e entradas ao tick, o TC igual, e **cada trilha no SEU canal** (o clipe do canal 3 aponta a
  `Media` de `StreamNumber 2`; lido no `.prproj` regravado pelo Premiere — `LAB OFFLINE MULTICANAL v04` — e no selo
  do canal na timeline). ⛔ `projectItem.setOffline()` (ExtendScript) não tornou offline o item importado (voltou
  `isOffline() == false`): o molde veio do arquivo online + a regra do diálogo.
- ⭐⭐ **A MATRIZ de layouts (mídia sintética do laboratório, B03: 1/2/4/5/8/16 canais × MOV ProRes polifônico, MOV
  um mono por trilha e WAV BWF; 26.0.2 Mac, 2026-11-25; `Ciclo Assist spikes/offline_premiere_matriz.py`) — `confirmado`.**
  O offline escrito pelo app, religado por `changeMediaPath`, conferido contra o MESMO arquivo importado online
  (o par `StreamNumber` da mídia + `ChannelIndex` de cada canal):
  - com os canais CONHECIDOS (um clipe por canal, A1…AN): **18/18**, 120/120 clipes no mesmo lugar ao tick, vídeo online
    (vídeo com 4, 5, 8 e 16 canais incluso). O offline ESTÉREO religado a "2 mono" (MOV de 2 trilhas) é REMAPEADO
    pelo Premiere para o layout do arquivo — certo.
  - ⛔⛔ com os canais DESCONHECIDOS e a timeline usando só alguns (o caso da referência do Avid): o offline sai com o
    maior canal usado; **ESTÉREO religado a um arquivo de MAIS de 2 canais deixa o canal 2 SEM FONTE** (o
    `SecondaryContent` sem `Content` e `ChannelIndex` 18446744073709551615 = −1: mudo) — 3/3 nos de 8 canais. Em **N
    MONO** com menos canais que o arquivo (5 canais usando o 3; 16 usando 1, 2, 9, 16) religa certo, e 2 MONO religado a
    arquivo estéreo de verdade também. ⇒ **regra: offline estéreo SÓ com a certeza de uma trilha de 2 canais; sem ela, N
    mono** → 18/18 nas duas variantes.
  - ⛔ O ExtendScript do Premiere é ES3: não há `JSON` (`ReferenceError: JSON is undefined`).
- ⭐ **A Carta (Avid → Premiere) com o offline no lugar, medida no projeto do editor** (`importSequences`): a
  `PRODA_CORTE.00.2` com 95 clipes de 23 sons sem arquivo nesta máquina → 867 clipes, 95 offline no lugar, os 23
  itens entraram com a sequência, os merged não duplicaram; religados 4 sons (53 clipes) → online, no mesmo lugar ao
  tick; o PATÃO DRONE com o TC 06:14:11:13 exato.
- ⛔⛔ **O nome do PARÂMETRO de efeito é gravado NO IDIOMA do Premiere** (26.0.2 Mac em português, 2026-11-25): o
  `AE.ADBE Text` do gráfico tem "Texto de origem" e "Posição" (no 26.5 Windows em inglês: "Source Text", "Position").
  Código que acha parâmetro pelo `Name` quebra noutro idioma — achar pela forma (o `ArbVideoComponentParam` com
  `StartKeyframeValue` é o texto; o 1º `PointComponentParam`, a posição) ou aceitar os nomes medidos. ⬜ O mesmo vale
  para o Motion ("Scale Width"…) — sem molde em português medido.

### 11p. ⭐⭐ ARQUIVO COM MAIS DE UM FLUXO DE SOM (o MOV de pares estéreo): o canal do arquivo é a SOMA dos fluxos anteriores (2026-11-25, 26.0.2 Mac) — `confirmado`

Medido com a mídia sintética do laboratório (`B03_PARES_2398`: MOV com 2 pares L/R; 2 pares + 1 mono; 3 pares; um tom por
canal), `.prproj` em `MIDIAS DE TESTES/3 CONJUNTOS…/conformar/04 SINTETICOS/CANAIS IDA E VOLTA/` (`PREMIERE PARES`,
`VOLTA PARES DO AVID`):
- **Uma `Media` por FLUXO de som** do arquivo (o 1º sem `StreamNumber`, depois 1, 2…), todas com o mesmo `FileKey`; os
  canais do fluxo estão em `AudioStream › AudioChannelLayout` (`[{"channellabel":100},{"channellabel":101}]` = estéreo,
  `[{"channellabel":0}]` = mono). O clipe aponta (`SecondaryContent › Content › … › Media`) o fluxo e o `ChannelIndex`
  DENTRO dele. ⇒ **canal do arquivo = Σ canais dos fluxos anteriores + `ChannelIndex` + 1**. Somar só o `StreamNumber`
  (que basta no "N Mono", um canal por fluxo) dava 1, 2, 2, 3 num MOV de 2 pares.
- O Premiere abre cada par numa trilha (clipe ESTÉREO). O mono que sobra (2 pares + 1 mono) vira clipe de 2 canais com
  o 2º **MUDO**: `ChannelIndex` 18446744073709551615 (2⁶⁴−1). O canal mudo não toca nada e não vira trilha na leitura.
- **Religar um offline "N Mono" (o que o Conformar escreve) a um arquivo de pares:** com fluxos IGUAIS (2 pares, 3 pares)
  religa CERTO (1…N); com fluxos DESIGUAIS (2 pares + 1 mono) o Premiere põe o canal k no FLUXO k: saem 1, 3, 5 e dois
  mudos. Pelo Avid não se sabe o arranjo do arquivo ausente (o master do AMA é só N trilhas mono) ⇒ limite conhecido;
  o comum na câmera (só mono, ou só pares) religa certo. Prova: `Ciclo Assist spikes/offline_pares_premiere.py`.
- Leitor: Conformar `prproj/leitura.py` (`Leitor._canais` + `_inicio_do_fluxo`); teste
  `modulos/conformar/tests/test_canais_ida_e_volta.py`.

## 12. Pendências conhecidas (`pendente`)

- **`MZ.Sequence.VideoTimeDisplayFormat`** está fixo em `110` (23,976 non-drop). O enum para os
  outros fps não foi mapeado. É cosmético (a sequência é regida pelos ticks/frame), mas num projeto
  NTSC o Premiere exibiria o TC no formato errado.
- **Overlap "first-camera-wins"** na segmentação de áudio COM MERGED: quando uma câmera fica
  totalmente DENTRO do range de outra, o segmento de áudio dela é descartado mas o vídeo ainda entra
  noutra track → o Link cai no áudio "errado". Não crasha; produz linkagem imprecisa.

---

## Validação

| o quê | como | data |
|---|---|---|
| `com_merged` isolado, 2 câmeras + WAV | abriu no Premiere 25.6.5, vídeo selecionável em V1 e V2, bin sem "Recovered Clips", Cerúleo confirmado | 2026-07-11 |
| Stress: 13 câmeras (CAM A ×2, CAM B ×11) + WAV, offsets +5675…+43417 frames, muita sobreposição | 217 ObjectUID únicos, 28 entradas de bin, 16 Links, **zero link de vídeo solo** — validação estrutural do XML | 2026-07-11 |
| Sequência da diária real (D02: 24 tomadas, 1 som por tomada) | **aberta no Premiere pelo usuário: "está perfeito, sync está no ponto certo"** | 2026-07-12 |
| Posição/TC/fps (`ZeroPoint`, start TC 01:00:00:00, 13 câmeras) | abriu com ZeroPoint certo, zero posições negativas, sem UID duplicado | 2026-07-12 |
| **Flag multicam (§5)** | o Premiere **reconheceu o projeto como multicam** (antes: sequência comum) | 2026-07-12 |
| **Mapeamento de canais (§6)** | a multicam inserida numa timeline traz **uma track por canal**, não um bloco | 2026-07-12 |
| **Bins (§9)**: projeto de 2 diárias (D01 com 11 câmeras + som; D02 MOS com 2) | **aberto no Premiere pelo usuário**: as 2 bins apareceram, tracks de vídeo corretas (uma por câmera física) | 2026-07-13 |
| **Mídia não duplica (§10)** | 15 `<Media>` para 14 arquivos (o WAV tem um por canal) — zero duplicação | 2026-07-13 |
| **`ZeroPoint` de recorte (§11)** | sub-grupo como sequência (normal e multicam) numa sub-bin; **TC idêntico ao da diária**, conferido no XML e **aberto no Premiere** | 2026-07-13 |

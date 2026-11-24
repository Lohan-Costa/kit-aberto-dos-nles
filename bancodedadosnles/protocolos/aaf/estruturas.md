# AAF — Estruturas

Descobertas sobre a topologia interna de um AAF do Avid, validadas com pyaaf2 em AAFs reais
exportados pelo Media Composer. Confiança geral: `confirmado` salvo onde indicado.

---

## 1. CompositionMob (a timeline)

```
CompositionMob (timeline)
└── slots[]
    ├── Slot 1..N  (Timecode, Edgecode)
    ├── Slot X     (Picture) ← track de vídeo
    └── Slot Y..Z  (Sound)
```

O slot de vídeo (Picture) contém **diretamente uma `Sequence`** ou um **`NestedScope`** (caso
flat file). FPS do slot: `float(slot.edit_rate)` (Fraction → float); típico `24000/1001`.

---

## 2. NestedScope — estrutura de flat file

Quando o offline exporta um AAF "flat file", o track de vídeo traz um `NestedScope` no lugar da
`Sequence` direta:

```
Slot (Picture)
└── NestedScope
    ├── Sequence (Slot 0) → V1 — track base (clipes)
    └── Sequence (Slot 1) → V2 — camada de efeitos/gráficos
```

A V2 referencia a V1 via `ScopeReference` (`RelativeSlot=1`), criando compositing interno sem
expor múltiplos tracks externos.

✅ **Reconfirmado com TRÊS trilhas de vídeo** (MC 2026/Win, 2026-08-19, export de timeline real):
o `NestedScope` traz `slots=3` e a ordem é **de baixo para cima — índice 0 = V1**. Três sinais
concordantes na mesma amostra: o índice 0 tinha UM clipe cobrindo a duração inteira (o Video
Mixdown, que na timeline ocupa a V1 de ponta a ponta) enquanto 1 e 2 tinham `ScopeReference`
intercalado com clipes — exatamente o desenho que o editor via na tela.

⚠️ Com **UMA** trilha de vídeo não há `NestedScope` nenhum: o slot Picture já é a `Sequence`.
Um leitor que EXIJA o NestedScope quebra na timeline mais simples que existe — e é justamente
essa a de uma entrega já preparada.

### ScopeReference

Aparece na Sequence V2 (efeitos):

```python
relative_scope = comp.get('RelativeScope').value  # 0 = mesmo NestedScope
relative_slot  = comp.get('RelativeSlot').value   # 1 = Slot 0-indexed (V1)
```

`RelativeSlot=1` = "use o frame de V1 neste TC". O `ScopeReference` **não precisa de relink** —
herda o clipe referenciado em V1.

---

## 3. Selector — multicam / múltiplas resoluções (o componente-chave)

Armazena várias versões do mesmo clipe (proxy/original, ou ângulos de câmera):

```
Selector
  selected     → SourceClip → MasterMob (versão ativa)
  alternates[] → SourceClip → MasterMob (versões alternativas)
```

```python
selected   = comp.get('Selected').value    # SourceClip ativo
alternates = list(comp.get('Alternates'))  # SourceClips alternativos
```

### `reconstructed.N` (multicam em flat file)

Em AAFs flat file + multicam, o Selector aponta para uma `CompositionMob` chamada
`reconstructed.N`, que tem um slot por fonte:

| Slot | Fonte |
|------|-------|
| 1 | FLATFILE (sequência inteira renderizada) |
| 6 | CAM B original |
| 8 | CAM A original |

Caminho de resolução completo:

```
Selector.selected (SourceClip)
  → start   = offset (frames) dentro de reconstructed.N
  → slot_id = qual câmera/fonte
  → mob = reconstructed.N (CompositionMob)
    → slots[slot_id].segment = SourceClip
      → mob = MasterMob ("CAM A")
        → slots[*].segment = SourceClip
          → mob = SourceMob
            → descriptor = ImportDescriptor
              → locator → URLString = file:///path/CAM A.mxf
```

### ⚠️ Armadilha do `start` (crítica)

O `start` de um `SourceClip` referenciado por um `Selector` **não** é o TC na mídia original — é
o offset dentro de `reconstructed.N`. O TC correto na fonte:

```python
source_start = selector.selected.start   # offset em reconstructed.N
            + slot_clip.start             # offset dentro do arquivo da câmera
```

Usar só `selector.selected.start` dá TC errado.

> **Refinamento (validado 2026-05-31):** ao casar o offset de fonte do multicam, **subtrair o
> `Filler` do slot do `reconstructed.N`** — o slot pode começar com um Filler que desloca o cálculo.

---

## 4. Group Clip (multicam do Avid)

### Identificação via `AppCode` (na CompositionMob)

| AppCode | Significado |
|---|---|
| `4` | **Group Clip** — container multicam visível no bin do Avid |
| `5` | **Composition target** anônima, referenciada pelos Selectors |
| fallback | `> 1` slots Picture numa CompositionMob (quando AppCode ausente) |

```python
app_code = mob.get('AppCode')
value = app_code.value if hasattr(app_code, 'value') else app_code
```

```
CompositionMob 'FLATFILE.Grp.01' [AppCode=4]   ← Group Clip (bin)
  └── Slots com Selector (selected = ativa; alternates = outras câmeras)

CompositionMob 'reconstructed.16' (múltiplos Picture slots)
  ├── Slot 1 → MasterMob 'FLATFILE'
  ├── Slot 6 → MasterMob 'CAM B'
  └── Slot 8 → MasterMob 'CAM A'
```

A flag `is_group_clip=True` propaga para todos os segmentos cujo Selector aponta para um Group
Mob (inclusive dentro de OperationGroups `SBlend_v2`). `selector_alternates` guarda os `MediaRef`
de cada ângulo. **O relink preserva o Group automaticamente** — só atualiza `URLString` nos
SourceMobs; Selector/Group e suas referências não são tocados.

---

## 5. SourceMob — descriptors

| Descriptor | Significado | Ação no relink |
|---|---|---|
| `ImportDescriptor` | Arquivo externo importado (original ou flat file) | **Candidato a relink** |
| `CDCIDescriptor` | Mídia gerada pelo Avid (proxy interno, MXF em MediaFiles) | Proxy — ignorar como fonte |
| `PCMDescriptor` | Áudio | Ignorado pelo relink de vídeo |

Leitura do path:

```python
for loc in desc.locator:
    url = loc['URLString'].value   # "file:///path/to/file.mxf" (percent-encoded, UTF-16LE)

from urllib.parse import urlparse, unquote
path = unquote(urlparse(url).path)
# macOS: remover prefixo "/Macintosh HD" se presente
```

Dados consumíveis: [dados/descriptors.json](dados/descriptors.json),
[dados/appcodes.json](dados/appcodes.json).

⚠️ **O `URLString` tem cinco formas irregulares**, e `urlparse().path` sozinho só resolve duas
delas — as com `netloc` (UNC) e as com letra de unidade sem dois-pontos precisam de tratamento
próprio. Ver [../../transversal/caminhos-e-storage-producao.md](../../transversal/caminhos-e-storage-producao.md) §1.

---

## 5b. Precompute de efeito é um MasterMob (`confirmado` 2026-08-17)

Quem quer **listar os masterclipes do bin** (para buscar originais, montar relatório, etc.) não pode
pegar todos os `MasterMob`: **os renders de efeito também são `MasterMob`**. No AAF real do *PRODUCAO-Q*, **21 dos 42** eram precompute — metade da lista era lixo.

Nomes típicos: `06AGO,3DWarp+14`, `06AGO,Resize+88`, `27JUL,Motion_Effect+1`,
`28JUL,Dissolve+21`, `10AGO_v2,Matte_Key+3` — padrão `<BIN>,<Efeito>+<N>`.

**A regra de descarte é ESTRUTURAL, não por nome:** a cadeia do precompute termina num SourceMob
chamado **`Precompute Source Mob`**, com `ImportDescriptor` **sem nenhum locator**.

```
MasterMob '06AGO,3DWarp+14'          usage = Usage_LowerLevel
└── SourceClip → SourceMob ''        CDCIDescriptor → …/avid mediafiles/…/06ago,3dwarp+14….mxf
    └── SourceClip → SourceMob 'Precompute Source Mob'
                                     ImportDescriptor, Locator = []   ← a assinatura
```

Descartar quando **todos** os ramos do MasterMob terminam assim. O padrão de nome serve só como
reforço para o caso de não haver pista nenhuma de original (nem fita, nem path de import).

⚠️ **Não usar `usage` para isso.** O precompute vem `Usage_LowerLevel`, mas um masterclipe **AMA
legítimo também** (`DIGITACAO TEXTO v4`, importado por AMA, tem `Usage_LowerLevel` e é original de
verdade). Filtrar por `usage` derruba material bom.

### Chaves de nome do original, em ordem de confiança

1. **basename do path de `ImportDescriptor`** — é o único que traz a **extensão real**
   (`DSC03652.JPG`, `digitacao texto v4.mov`).
2. **nome do SourceMob de arquivo** (tirando o sufixo `.PHYS`) — cobre o caso de o nome do bin ser
   diferente do nome em disco: o masterclipe **`1-05/03`** (com barra, impossível num nome de
   arquivo) tem SourceMob de arquivo chamado **`1-05T03.wav`**, que é o arquivo de verdade.
3. **nome do MasterMob** — o caso comum, quando fita/`TapeDescriptor` é a única pista.

Referência: `LOCALIZADOR_DE_MIDIA_PELO_AAF/app/aaf_reader.py`.

---

## 6. FPS — observação crítica

AAFs típicos usam `24000/1001 = 23.976...` (23.976 drop). O `SampleRate` do CDCIDescriptor
confirma `24000/1001`.

```python
edit_rate = getattr(slot, 'edit_rate', None)
fps = float(edit_rate)  # Fraction → float correto
```

### Timecode inicial e dropframe (`confirmado` 2026-06-10)
- O **TC inicial** da timeline vem do `StartTimecode` do slot de Timecode (`_read_start_tc`).
- **Dropframe é só rótulo:** internamente os segmentos seguem **frames contínuos non-drop**
  (matcher/writer intactos). A exibição/input é DF-aware (29.97/59.94, separador `;`) via
  `framesToTcDF`/`tcDFToFrames`.
- Non-drop de qualquer fps validado: 23.976 / 24 / 25 / 29.97ND / 30 / 50 / 59.94ND / 60.

## 7. Duração do MasterMob — `length` e `edit_rate` do MESMO slot

`confirmado`, 2026-08-16 — medido em `PRODA_RELINKER_ALTA.aaf` (**303 MasterMobs**, todos
com duração disponível) e nos 118 masters em uso de uma montagem real.

A duração de um master está nos **slots**: `slot.segment.length` e `slot.edit_rate`.

```
segundos = slot.segment.length / slot.edit_rate     # do MESMO slot
```

⚠️⚠️ **Os dois têm de sair do mesmo slot, e é isso que torna a conta correta seja qual
for a unidade.** Num AAF a trilha de som pode contar em **samples** (`edit_rate = 48000`)
e a de imagem em **frames** (`23,976`). Cruzar o comprimento de uma com a taxa da outra
produz um número **plausível e errado por três ordens de grandeza** — 1 440 000 samples
lidos como frames a 23,976 viram 41 minutos onde há 30 segundos. E número plausível **não
levanta exceção**: ele apenas reprova candidato certo num portão de duração.

⭐ **Medido neste acervo:** o som conta em **frames@timeline** como a imagem — a mesma
convenção que a bin `.avb` usa no MasterMob. Mas apareceram `edit_rate` de **23,976 E de
24,0 entre os sons do mesmo arquivo**, o que já basta para provar que a taxa **não pode
ser presumida** a partir de um slot só nem da timeline.

⭐ **Por que importa mais do que parece:** sem a duração do master, um portão de duração
fica **neutro** — não reprova nada, e o app perde o veto que separa dois clipes de **mesmo
nome** vindos de cartões reaproveitados em diárias diferentes. Era o caso do De Lá Pra Cá
na rota AAF até 2026-08-16: o campo existia, ninguém o preenchia, e o matcher rodava sem
essa defesa sem que nada indicasse.

⚠️ Ao comparar master × **arquivo**, lembre que uma diferença pode ser legítima: mídia
**consolidada** é um trecho aparado do original. Ali a régua correta é assimétrica (o
arquivo nunca mais curto que o master, mas podendo ser bem mais longo — a lógica do
`PMM_INSUFFICIENT_MEDIA`). Comparando master × master, a régua é simétrica.

---

Ver convenções de tempo cross-NLE em [../../transversal/tempo-e-timecode.md](../../transversal/tempo-e-timecode.md).

## 8. O AAF do Media Composer lido COMO A BIN (`confirmado` 2026-09-29)

Medido no caso `03 CASOS/ATUALIZAR/U03 ATUALIZAR COM AAF` (o começo da PRODA, MC 25.6/Win, exportado
com *Link to (Don't Export) Media*), contra a MESMA sequência lida na bin (`U03 referencia.avb`).
Código: `_DeLaPraCa/motor/aaf/leitura.py`; teste: `tests/test_aaf_leitura.py`.

- ⭐ **A estrutura bate com a bin, plano a plano**: 57 de imagem e 362 de som (v01), com trilha,
  posição, duração e ponto de entrada na fonte iguais. O ponto de entrada que o `parse_aaf` dá já é
  relativo ao MASTER (não somar o deslocamento do subclipe de novo).
- ⚠️ **O plano aponta para o SUBCLIPE sincronizado** (`CompositionMob` "04-01-02", `usage` subclip),
  não para o master. O master está um nível abaixo e tem **o MESMO MobID que na bin**
  (`…060e2b34.7f7f2a80`). Sem descer, os ids divergem em 54 de 57 planos de imagem. O slot do
  SourceClip no subclipe escolhe a trilha (som direto × som da câmera, §2).
- ⚠️ **O canal do som é a trilha do master que o clipe lê** (a posição entre as de som: `sound:N`).
  O `parse_aaf` o perdia em todo clipe de som **com efeito** (`OperationGroup`: ganho, EQ) — 34 de 304.
  Corrigido no parser (o slot do SourceClip de dentro do efeito).
- ⭐ **Identidade e essências saem da cadeia master → arquivo (`CDCI`/`PCM`) → fita (`TapeDescriptor`)**,
  igual à bin (`avb/`): reel = o nome do mob mais fundo que não seja `msmMMOB.NN`; TC de origem = o
  `Timecode` do mob mais fundo + os `start` da cadeia (B001_03150131_C011: 0 + 132203 a 24 fps).
  As essências (`picture:1`, `sound:1…`) = o MobID do mob de ARQUIVO de cada trilha — é por elas que o
  índice do Avid (`.pmr`) acha o MXF. Resultado: 302 de 302 clipes com mídia gerenciada nesta máquina.
- ⚠️ **O AAF só trouxe caminho de arquivo (locator) para 2 dos 21 clipes**; o resto é mídia
  gerenciada, referenciada pelo id. E o caminho que vem, pelo `url_to_local_path`, sai `/D:/Avid
  MediaFiles/…` no Windows (a 3ª barra não é a raiz — matriz de plataforma): tirar a barra antes da letra.
- ⭐ O mesmo "Atualizar" feito pelo AAF e pela bin dá o **mesmo resumo** (v01 × v02: 14,6% da imagem,
  8 retirados, 1 take trocado, 15 deslocados).
- ⭐⭐ **E a timeline que o PRÓPRIO Resolve monta do AAF casa com a leitura** (2026-09-29, Resolve 19,
  conferido pelo autor): importado pelo menu do Resolve (sem o De Lá Pra Cá), o AAF v01 deu uma timeline
  em que **54 de 55 planos de imagem** têm início e fim exatamente nos cortes da leitura (97,7%). O único
  fora é o **título Avid Titler+ Legacy** (V3): o importador de AAF do Resolve não o põe no lugar. O
  "Atualizar com dois AAF" rodou de ponta a ponta sobre ela (8 planos inseridos, todos achados no pool).

## O caminho de origem de um master num AAF do MC: só a mídia IMPORTADA o tem (2026-10-13, MC 25.6/Windows) — `confirmado`

Medido em `PRODA_CORTE_ORIGINAL.aaf` (PRODUCAO-A, 99 masters) para a coluna "De onde veio" do De Lá Pra Cá:

- **Mídia importada (SFX WAV/AIF):** master → SourceMob `PCMDescriptor` (SEM locator) → SourceMob `ImportDescriptor`
  com `URLString = file:////D/02_MIDIAS/03_SFX/04%20Dark%20Drone.wav`. A URL mora **dois níveis abaixo** do master:
  quem procura só o primeiro SourceMob não acha nada. `file:////D/…` = drive `D:` (o Avid no Windows).
- **Mídia gerenciada (vídeo transcodado, BWF do som direto):** master → SourceMob `CDCIDescriptor`/`PCMDescriptor` →
  SourceMob `TapeDescriptor` (nome `msmMMOB.NN` ou o do clipe) → referência nula. **Nenhuma URL**: só 4 de 99 masters
  tinham caminho. A origem dessas está no `msmMMOB.mdb` da máquina que exportou, não no AAF.
- A bin `_AAF.avb` em que o MC importa esse AAF também não guarda o caminho (só `MSMLocator` com o volume).
Código: `_DeLaPraCa/motor/aaf/masters.py::_origem_do_master` (desce a cadeia toda; `//D/…` → `D:/…`).

### O AAF do Resolve 19 de uma timeline com timelines ANINHADAS: masters sem nome nem caminho (2026-10-19) — `inferido`

`RESOLVE19_AAF_novo.aaf` e `_existente.aaf` (caso O01, timeline F4a: dois clipes que são timelines aninhadas,
`CMP_…` e `F4n_…`, sobre `FPS_5994_60S_48K.mp4`): a leitura (`aaf/leitura.py`) chega a 2 masters com `nome` e
`caminho_na_bin` vazios, só com TC (0 e 180000 a 50 q/s), 1920×1080 e a duração. O FCP7 do mesmo corte tem `pathurl`
`//localhost`; o EDL e o OTIO dão os nomes das timelines aninhadas. Não se sabe ainda se o nome falta no AAF ou na nossa
leitura do aninhamento — `pendente` (vai com os leitores novos do laboratório, B23_PROTOCOLOS).

### O `reel_name` do QuickTime NÃO chega ao AAF do MC (`confirmado`, MC 25.12 Mac, AMA, laboratório BL08, 2026-11-22)

O daily `CENA12_T3.mov` tem `reel_name=B001C007` na trilha de TC (ffprobe). Linkado por AMA no MC e exportado em AAF, a
string `B001C007` não aparece em lugar nenhum do arquivo (nem ASCII, nem UTF-16): o mob mais fundo se chama `CENA12_T3`, e
a leitura (`aaf/leitura.py`) dá reel = o nome do clipe. ⇒ Quem usa o reel como critério de casamento no lado do MC lê o
reel do ARQUIVO do daily (Conformar `media/confirmacao.reel_do_arquivo`), não do AAF. ⚠️ Não medido: mídia gerenciada
(MXF importado/transcodificado, onde o MC preenche a coluna Tape) e o MC no Windows — `pendente`.


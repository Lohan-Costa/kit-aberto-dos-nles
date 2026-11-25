# .avb — modelo de objetos e estruturas

Como ler o conteúdo de um bin com `pyavb`, e por que o conhecimento de AAF se reaproveita quase
inteiro. Confiança: **confirmado** (os 3 bins de amostra abriram e foram percorridos).

## Acesso básico

```python
import avb
with avb.open("03_OC_EDIT VALENDO.avb") as f:
    bin = f.content                 # objeto Bin (ABIN)
    for mob in bin.mobs:            # cada mídia/clip/sequência é uma Composition (CMPO)
        mob.name                    # nome no bin (pode ser None)
        mob.mob_id                  # UMID SMPTE (igual ao AAF/MXF/.pmr)
        mob.mob_type               # 'MasterMob' | 'SourceMob' | 'CompositionMob'
        mob.usage                  # 'mastermob' | 'subclip' | 'precompute' | ...
        for track in mob.tracks:
            track.media_kind        # 'picture' | 'sound' | 'timecode' | 'edgecode'
            track.component         # Sequence / SourceClip / etc.
```

## A ponte com o AAF (reuso de conhecimento)

A cadeia de resolução é **conceitualmente a mesma do AAF** (ver
[../aaf/estruturas.md](../aaf/estruturas.md) e [../aaf/README.md](../aaf/README.md)):

```
CompositionMob (sequência/timeline)
  → Sequence → SourceClip → MasterMob
    → SourceClip → SourceMob [descriptor]
      → locator (MSMLocator / URLLocator / Mac/WinFileLocator) → caminho do arquivo
```

Diferenças de vocabulário entre AAF (pyaaf2) e AVB (pyavb):

| conceito | AAF (pyaaf2) | AVB (pyavb / fourcc) |
|---|---|---|
| bin | — | `Bin` (`ABIN`) |
| mob/composição | `Mob` (Master/Source/Composition) | `Composition` (`CMPO`) com `mob_type` ⚠️ |
| sequência | `Sequence` | `Sequence` (`SEQU`) |
| source clip | `SourceClip` | `SourceClip` (`SCLP`) |
| grupo de tracks | `OperationGroup`/slots | `TrackGroup` (`TRKG`), `TrackRef` (`TRKR`) |
| efeito de transição | `Transition` | `TransitionEffect` (`TNFX`) |
| motion/rampa | `OperationGroup` speed | `MotionEffect` (`SPED`) |
| atributos | `MobAttributeList` | `Attributes` (`ATTR`) |

⚠️⚠️ **A linha do mob é a armadilha desta tabela, e ela falha em SILÊNCIO.** No pyaaf2
existem **classes distintas** (`MasterMob`, `SourceMob`, `CompositionMob`), e o idioma
natural é `type(m).__name__ == "MasterMob"`. **No pyavb essa classe não existe**: todo mob
é `Composition`, e quem distingue é o **atributo** `mob_type`. Portar o teste de um para o
outro não levanta erro nenhum — a varredura roda inteira, atravessa toda a timeline e
devolve **zero masters**, como se o acervo estivesse vazio. Medido em 2026-08-16
(`_DeLaPraCa`, bin real: `SourceMob` 484, `MasterMob` 119, `CompositionMob` 45).

⚠️ Irmã dela, no mesmo percurso: **`tracks` é propriedade em `Composition` e MÉTODO em
outras classes** do pyavb. Um percurso genérico que itere `getattr(o, "tracks", [])` sem
checar `callable` estoura `TypeError: 'method' object is not iterable` **no meio** da
varredura — depois de já ter contado parte da timeline.
| descriptors | `CDCIDescriptor`, `PCMDescriptor`… | `CDCI`, `PCMA`, `WAVE`, `DIDD`, `MPGA`… |
| locator | `NetworkLocator` URLString | `URLLocator` (`URLL`), `MSMLocator` (`MSML`), `MacFileLocator` (`FILE`), `WinFileLocator` (`WINF`) |

Implicação para **relink** de bin: tocar o locator do `SourceMob` (como no AAF se toca o
`URLString`). Para mídia gerenciada (MXF nativo), o locator costuma ser `MSMLocator` apontando ao
MediaFiles + o MobID, que o MC casa via `.mdb`/`.pmr` (ver [../msm/](../msm/README.md)).

## AMA-link: o caminho mora na bin, mas a AMA Management é que resolve (corrigido 2026-06-27)

⚠️ **CORREÇÃO:** versão anterior afirmava que a bin era "autossuficiente" e a AMA Management
"dispensável" — **ERRADO**. Teste limpo (apagar a AMA Management, relançar o MC, importar a bin)
deixou a mídia **OFFLINE**. A **AMA Management é o registro/resolvedor**; a bin carrega o
`path_posix` (que o MC usa para **reconstruir** a AMA Management no import), mas não basta sozinha.
Os "sucessos" anteriores estavam confundidos por AMA Management **leftover** e symlinks apontando
ao arquivo original. Detalhes do fluxo de relink em [escrita.md](escrita.md).

O encadeamento de mobs por arquivo (continua válido):

- **MasterMob** (nome amigável; MobID `...01010f00.13000000...`) →
- **SourceMob de essência** por trilha (`CDCIDescriptor` p/ vídeo, `PCMADescriptor` p/ áudio) com
  `MSMLocator` (`MSML`) carregando `last_known_volume` (ex.: `'SSD'`) + `mob_id` (sem path) →
- **SourceMob "de arquivo"** (`MediaDescriptor`) com **`MacFileLocator` (`FILE`)** que carrega o
  **caminho absoluto** nos campos `path_posix` e `path_utf8`.

⚠️ **Pegadinha:** o campo legado `path` do `MacFileLocator` fica **vazio** (`''`); o caminho real
está em `path_posix`/`path_utf8`. Ler só `path` engana (foi o nosso erro inicial).

```python
for m in bin.mobs:
    d = getattr(m, 'descriptor', None)
    L = getattr(d, 'locator', None) if d else None
    if L is not None and type(L).__name__ == 'MacFileLocator':
        print(dict(L.property_data)['path_posix'])   # caminho do arquivo AMA
```

Para **gerar/relinkar** AMA-link é preciso o caminho na bin **e** a AMA Management coerente (o MC
reconstrói a AMA Management a partir do `path_posix` no import, desde que não haja registro velho
conflitante). Ver [escrita.md](escrita.md) §fluxo de relink e [../msm/ama-management.md](../msm/ama-management.md).

> Nota pyavb 1.4.0: alguns `PCMADescriptor` do Avid disparam `unknown ext tag 0x02` na leitura
> (bug do parser). Os locators com caminho leem normalmente; mas é um limite a observar para
> escrita/round-trip.

## Configurações de visualização do bin

O bin carrega objetos de UI além das mídias: `BinViewSetting` (`BVst`) — colunas exibidas e ordem
— e `BinFirst` (`BINF`). Relevante se quisermos **gerar um bin já com a aparência certa** (colunas,
sashes), não só os clips.

## Nomes que o MC gera sozinho — `confirmado` (2026-08-19)

Dados: [nomes-gerados-pelo-mc.json](dados/nomes-gerados-pelo-mc.json).

Medido lendo por pyavb a bin de um editor (`ORBITA - TESTE.avb`, 95 mobs, MC 2026/Win).
Importa para qualquer plugin que precise separar *"clipe que o Media Composer gerou"* de
*"material que o editor trouxe"* — e até aqui era palpite em todo lugar.

| o que | padrão | mob |
|---|---|---|
| **Video Mixdown** | `<sequência>,Video Mixdown,<n>` | MasterMob, só `picture 1` |
| o físico dele | `<sequência>,Video Mixdown,<n>.PHYS` | SourceMob |
| master gerenciado | `<clipe>.new.<nn>` (`inferido`) | MasterMob |
| source do banco de mídia | `msmMMOB.<nn>` (`inferido`) | SourceMob, 1 track |

⭐ **O separador é VÍRGULA, não ponto.** `SEQ.Mixdown.01` — a forma que a documentação
informal e os projetos costumam supor — está errada no separador.

⚠️ **`endswith` NÃO reconhece o mixdown.** O número da versão vem DEPOIS do carimbo, então
o nome nunca termina em "mixdown": um `endswith` recusa o próprio nome que o Avid gera, e
o sintoma é o plugin dizendo *"a V1 não tem o mixdown"* sobre uma V1 correta. Use `in`,
sem caixa.

⚠️ **O nome não diz onde o clipe está.** Reconhecer `…,Video Mixdown,1` prova que aquele
CLIPE é um mixdown — nunca que a V1 da timeline está com ele. Para isso é preciso a lista
de edição (`ExportFile` de AAF + parse).

⚠️ **`msmMMOB.<nn>` é ruído**: 63 dos 95 mobs desta bin. Quem varre bin por nome filtra
antes de contar.

## Exemplo medido

`03_OC_EDIT VALENDO.avb`: 1200 mobs. Uma única `CompositionMob` sem `usage` é a sequência editada
(`PRODA_CORTE.02`, 29 tracks incluindo timecode/edgecode). O grosso são SourceMobs de mídia
(484) e o par precompute MasterMob+SourceMob (184+184) — os renders/efeitos pré-computados.
`AUDIO-MAR (2).avb`: 20 Compositions de áudio (AMA-link de .aif/.wav, MobIDs `...01010f00...` e
`...01010f10...`).

## O registro de procedência do `Bin` — ofuscado por XOR `0xFF` (confirmado 2026-08-20)

`f.content.property_data['attributes']` traz, além das chaves de exibição em texto puro
(`ATTR__BIN_DISPLAY_MASK`, `BIN_COLUMNS_WIDTHS`, `_BIN_SRT`, `NewlyArrivedMobList`…), um bloco
cujas **chaves e valores estão ofuscados por NOT bit a bit** (`XOR 0xFF`) sobre bytes
mac_roman. A chave que aparece como `úçöûãöõ†ùÜ` é `created_by`.

```python
def deobf(s):
    return bytes(x ^ 0xFF for x in s.encode("mac_roman")).decode("utf-8", "replace")
```

Decodificado, são dez campos — cinco de criação e cinco de modificação:

| chave | formato | exemplo |
|---|---|---|
| `created_by` / `modified_by` | `<ESTAÇÃO>, <usuário do SO>, <perfil de usuário Avid>, <data>` | `ESTACAO-01, usuario-rede, usuario-rede!, 2026/08/19 17:01:56` |
| `created_with` / `modified_with` | `<SO>, <versão do MC>, <build>` | `Win, Avid Media Composer 21.12.10, rel.MC2021.12_R56256` |
| `creator_path` / `modifier_path` | caminho completo do executável | `C:\Program Files\Avid\…\AvidMediaComposer.exe` |
| `creator_code` / `modifier_code` | dois inteiros de 16 dígitos | `0000000000000002 0000000000000002` |
| `creator_machine_id` / `modifier__machine_id` | id de máquina de 25 dígitos, ou `UNSUPPORTED` | `5298932761656574394141342` |

(note o `__` duplo em `modifier__machine_id` — é assim no arquivo.)

⭐ **Uso legítimo:** é uma fonte pronta de *"quem mexeu por último, em que SO, com que build"*,
sem API nenhuma. Numa bin do acervo o registro contava a história inteira: criada num Mac com
MC 23.3.1, modificada no Windows com MC 23.3. O `machine_id` vem preenchido no MC 21.12/Win e
`UNSUPPORTED` no MC 23.3/Win — varia por versão, não por SO.

⚠️ **E o custo:** ofuscação não é cifra, e toda bin entregue a terceiro leva esse rastro
junto. Ver [../../seguranca/README.md](../../seguranca/README.md) §13b.

⚠️ Nem tudo em `attributes` é `str`: `BIN_COLUMNS_WIDTHS` é um `bytearray` com JSON dentro
(as larguras das colunas da bin, incluindo a coluna **`Plug-in`**), e `NewlyArrivedMobList` é
um `Attributes` aninhado com MobIDs. Trate por tipo, não por suposição.

## Ler uma timeline INTEIRA como lista de eventos (export) — `confirmado` 2026-09-24

Medido em 5 sequências reais (MC 25.6 / Windows, e bins de 2008): o curta
`PRODA_CORTE.02.Exported.01` (23.976, 877 SourceClips, 143 transições, 28 `MotionEffect`,
33 `Selector`), duas timelines de 2008 com 776 `TrackEffect`, e duas curtas. Implementado em
`_DeLaPraCa/motor/avb_bin/segmentos.py`, que devolve o formato de `aaf/parser.py::parse_aaf`.

⭐ **A prova que vem de graça:** toda trilha da sequência cobre o comprimento inteiro dela
(Filler de preenchimento no fim). Percorrer somando `length` — e SUBTRAINDO o das transições —
tem de fechar exatamente em `CompositionMob.length`. Fechou nas 5; um componente lido errado
desloca o fim da trilha. E os masters alcançados batem com `avb_bin/masters.py`.

| estrutura | como ler | observação |
|---|---|---|
| trilha | `Track.component` = `Sequence[Filler(0), …, Filler(resto)]` | `index` por `media_kind`: V1… e A1… |
| **trilha INTERNA de efeito** | `efeito.tracks[i].component` = `Sequence[Filler(0), clipe, Filler(0)]` | efeitos se ANINHAM: cor → `INT_EFF_SPATIAL_ADAPTER` → `MotionEffect` → clipe |
| `TransitionEffect` | `length` = sobreposição, `cutpoint` = frames do lado A | mesma semântica do AAF: **recua** o cursor |
| ⭐ `MotionEffect.speed_ratio` | racional **timeline ÷ fonte** | 85% = `[79, 68]` = 1,1617; 125% = `[209, 262]`. É a convenção do `SpeedRatio` do AAF e a que `build_drt` espera — sem conversão |
| `MotionEffect.param_list[0]` | curva de velocidade, `value` = **fonte ÷ timeline** (0,85) | o INVERSO do racional; ler os dois como a mesma grandeza inverte a velocidade |
| `MotionEffect.param_list[1]` | mapa `(frame de timeline, offset de fonte)` já integrado pelo Avid | `(79, 67.15)` = 79 × 0,85. É o `source_offset_map` do AAF |
| `[1000, 1001]` com curva `0.0` e sem `param_list[1]` | **conformação** 24 → 23,976 | não é velocidade do editor |
| `[251, 1]` com clipe interno de 1 frame | **congelamento** | |
| ⚠️ `Selector` `[Filler, clipe]`, `selected = 0` | **clipe DESABILITADO** — o programa mostra o vazio | CORRIGE (mesmo dia): o clipe NÃO some — o Resolve 19, pelo AAF, traz o SOM desligado como clipe `Flags=2` (e o vídeo desligado não traz). Ler o outro ramo e marcar `disabled` |
| ⭐ quem grava esse `Selector` | **Timeline ▸ Mute Clips** do MC (medido 2026-10-28, MC 25.12/Mac, De Lá Pra Cá): num plano COM efeito vira `Selector[Filler, TrackEffect[clipe]]`, `selected = 0`, `is_ganged = True` — o efeito vai inteiro no ramo desligado | o Effect Editor do 25.12 NÃO tem interruptor no efeito inteiro, só nos GRUPOS (3D Warp: Scaling/Position…, `DVE_*_ENABLED_U`); o Mute Clips é o 'desligar' do MC |
| ⭐ o Mute Clips ESCRITO por nós (2026-10-29, MC 24.6/Windows, De Lá Pra Cá `translate._build_mudo`) | a forma lida nas bins reais do PRODUCAO-A: `Selector` `selected 0`, `is_ganged`, attrs `_DISABLE_CLIP_FLAG 1` + `_AAF_SELECTED 0`; ramo 0 = `Filler` (no vídeo a trilha dele leva `filler_proxy` TrackRef `relative_scope 1`, `relative_track -1`), ramo 1 = o clipe COM os efeitos (PIP/Motion, PanVolumeEffect); as `Track` sem `index` | o R04 (.prproj → Avid): a bin abre, o Record mostra PRETO sobre o vídeo desligado, o leitor relê os 3 como `disabled`; bins com só Mute Clips (som ou vídeo) modificadas e salvas sem erro |
| ⚠️ som de SUBCLIPE | `Sequence[Filler, PanVolumeEffect[SourceClip], Filler]` — ganho DENTRO do subclipe | exigir `SourceClip` direto perdeu 7 clipes da A1/A2 do curta |
| timecode | várias trilhas `timecode` (24 E 25 fps, ambas 01:00:00:00) | vale a de `fps == round(edit_rate)` da sequência |

⚠️ **O arquivo de cada master, no Windows:** `WinFileLocator.path_utf8` com `D//pasta/x.mov`
(ver `fontes.md`). `avb_export/nle_model.py::locator_path` só olha `path_posix` e devolve
`None` em TODA bin gravada no Windows — é leitor de macOS. Em mídia gerenciada o caminho do
original não está na bin; o Media Composer (`GetMobInfo`, colunas `Source Path/File`) é quem sabe.

### ⭐ Quem é o ORIGINAL de um master de mídia GERENCIADA — `confirmado` 2026-09-24

Para exportar a quem tem os originais (o colorista), o clipe precisa levar a identidade do
arquivo de câmera — e ela mora na bin mesmo quando a mídia é gerenciada. Cadeia medida:

    master → essência (CDCI/MPGI/PCMA) → mob FÍSICO (TapeDescriptor | MediaDescriptor)

| dado | onde | exemplo medido |
|---|---|---|
| TC de câmera do 1º frame do master | trilha `timecode` do mob MAIS FUNDO que a tiver: `início + soma dos start_time da cadeia − posição do Timecode` | curta: 0 + 132203 a 24 = 01:31:48:11 |
| nome do arquivo original (reel) | nome do mob MAIS FUNDO que não seja nome interno | `B001_03150131_C011`, `20240531_C0076-040` |
| resolução / taxa | descritor da essência | 2048×1080 @ 23.976 |

⭐ Conferência que veio de graça: câmeras gravam a HORA no nome do arquivo, e ela bate com o
TC lido (`a001_03170314_C003` → 03:14:14:17; `a002_03170703_C003` → 07:03:09:10).

⚠️⚠️ **TC e nome podem estar em mobs DIFERENTES.** No som direto importado, a fita no fundo
tem o TC certo (11:42:00:00) mas o nome gerado `msmMMOB.02` — que se REPETE entre arquivos
diferentes; o nome real está na essência e no master. Parar no primeiro mob com timecode
juntou 16 grupos de masters distintos sob o mesmo "reel". Regra: TC do mais fundo com
timecode; nome do mais fundo com nome não-interno (`^msmMMOB\.\d+$` é interno).

⚠️ Entrelaçado: `stored_height` é a altura de UM campo (1920×540 num 1080i) quando
`frame_layout != 0`. ⚠️ A EXTENSÃO do arquivo original não aparece na cadeia — só na coluna
`Source File` do Media Composer (`GetMobInfo`), quando ele a tem.

`pendente`: drop-frame (`Timecode.flags` só visto `0`); UUIDs do `param_list` dos efeitos
geométricos (vistos: `INT_EFF_SPATIAL_ADAPTER` com valores `-800, -450, 1600, 900`, sem
tradução); multicam (`SourceClip` → `CompositionMob` de grupo); marcadores.

## AniMatte (`EFF_ANIMATTE`) — a máscara desenhada

Medido em 2026-10-12, MC 25.6 Windows, projeto 1080p/23,976 (laboratório: sequência `LAB_ANIMATTE`, B14_FUNDO
azul na V1 e B14_FRENTE laranja na V2; despejo `lab/bancadas/avid/ler_animatte.py`; cópias da bin
`saida/bancadas/avid/animatte_NN_*.avb`).

- É um `TrackEffect` do formato ANTIGO (o do `EffectParamList`, não o `param_list` dos AVX2): atributos
  `_EFFECT_PLUGIN_CLASS 'Key'`, `_EFFECT_PLUGIN_TYPE 'Unknown'`, `_BORDER_FIXED 1`, `_NEW_SHAPE_REFERENCE_FRAME 1`;
  trilha 1 = vazio que olha a trilha de BAIXO (`TrackRef relative_scope 1`), trilha 2 = o clipe; `keyframes` =
  `EffectParamList` com 2 keyframes (`percent_time` 0 e 2^30) mesmo sem animação. Os campos fixos (`pos_x`,
  `box`, `border_soft`…) ficam no padrão — **a forma está em `user_param`** (532 bytes num polígono de 4 pontos).
- `user_param` = bloco **`BZFX`**, big-endian. Cabeçalho até o byte 284 (uint32 em 8 = 1, em 12 = 4 = nº de
  vértices?, em 16 = 0x3786 = contador de ids; doubles: 100,0 em 35; 20,0 em 69 e 77; 1,0 em 244 e 252 — significado
  pendente). Depois, a contagem (uint32 4) e **um registro de 62 bytes por vértice**: id uint32 (0x3787, 0x3788…),
  2 bytes de bandeira (`01 01` no polígono), uint32 2, **6 doubles = x, y do vértice + dois vetores (alças?)**,
  4 bytes zero (o último registro sem eles).
- ✅ **O x está na escala SD de 720 de largura, centro 0** (±360 = as bordas do quadro), esticada para a largura do
  projeto: vértices em x = 14,2 → borda no render em **997,6 px** (previsto 960 + 14,2 × 1920/720 = 997,9). Borda
  dura (10–90 % = 0 px) sem Feathering; igual nos quadros 0, 72 e 143. Confiança: **confirmado** (render × bin).
- ✅ **O y está na escala de UM CAMPO NTSC: 243 linhas de altura, centro 0, e CRESCE PARA BAIXO** (−121,5 = topo do
  quadro). Retângulo da ferramenta Rectangle todo dentro do quadro (rodada 02): x −187,94…182,92 e y −51,62…53,62 →
  render com bordas em x 459,2 / 1447,6 px e y 310,5 / 777,5 px. Ajuste: x = 960 + 2,665·u (previsto 1920/720 =
  2,667) e y = 539,6 + 4,437·v (previsto 1080/243 = 4,444; a diferença de 0,7 px no vão está dentro da quantização da
  borda dura). Mesmo sentido do Y do esquema AFX (desce). Confiança: **confirmado** (render × bin).
  Na tradução: `px_x = W/2 + x·W/720` e `px_y = H/2 + y·H/243`.
- Polígono e Rectangle gravam IGUAL: 4 registros com bandeira `01 01` e dois vetores por vértice que NÃO curvam a
  borda (o render é reto) — parecem alças automáticas, opostas e de tamanho diferente (ex.: (−81,8, 26,0) e
  (91,8, −29,2)).
- ✅ **Círculo (rodada 03) = 4 vértices com bandeira `01 00` e as alças VALENDO: Bézier cúbica.** Os dois vetores
  de cada vértice são as alças RELATIVAS ao ponto: o 1º = a que CHEGA, o 2º = a que SAI. Segmento i→i+1 =
  `P[i]`, `P[i] + sai[i]`, `P[i+1] + chega[i+1]`, `P[i+1]`, e o último fecha no primeiro. O contorno do render
  bate com essa Bézier a ±1 px em 24 ângulos; uma elipse verdadeira erraria até 3,4 px. ⭐ O Avid faz o círculo com
  alça = **4/7 do raio** (0,5714; não o 0,5523 de costume), por isso a forma é levemente "quadrada" nos 45°. O
  2º byte da bandeira parece dizer se a alça vale: `01` = canto/reta (polígono, retângulo), `00` = curva.
- ✅ **Curve (rodada 04): 18 vértices, bandeira `01 00`, e o render bate com a Bézier das alças gravadas
  (IoU 0,994; 1.309 px de diferença num contorno longo).** A contagem é o uint32 do byte 280 e os registros vêm em
  SEQUÊNCIA de 62 bytes a partir do 288 — ⛔ não "achar pela forma": o leitor que fazia isso descartou 3 vértices
  (o 3º campo = 0) e a curva parecia não bater (IoU 0,76). Os ids podem não ser consecutivos entre formas (é um
  contador do efeito), mas dentro da forma vêm na ordem do contorno.
- O 3º campo do registro (uint32) é o **tipo da alça**: `2` = automática (colineares; o MC calcula o tamanho —
  círculo, polígono, retângulo), `1` = suave (colineares, comprimentos livres), `0` = quebrada (direções
  independentes: canto com alças). Exceção vista: o 1º vértice da curva veio `1` com as alças a 160° (talvez o ponto
  de fechamento). ⭐ **A tradução não precisa dele**: o render bate usando as alças como estão; o que decide reta ×
  curva é o 2º byte da bandeira (`01` = reta).
- ✅ **O bloco inteiro** (rodadas 05–10, pilotadas pelo laboratório, sem o autor): `"BZFX"` + uint32 0 + **uint32 nº
  de FORMAS** (byte 8) + as formas, uma atrás da outra. **Forma** = cabeçalho de **276 bytes** (uint32 4, uint32 id,
  …; **Feathering Hor e Vert = doubles em +31 e +39**; nº de vértices = uint32 em +268) + os registros de 62 bytes,
  o último SEM os 4 zeros finais (são separador). Conferido pelo tamanho em todos os casos: 4 vértices = 532 bytes,
  18 = 1400, 18 + 4 (duas formas) = 1920.
- ✅ **Feathering é POR FORMA** e fica centrado no contorno (Bias 50: o ponto de 50 % não sai do lugar). Largura
  10–90 % no render 1920×1080: **Vert = 4,4 px por unidade** (5 → 22,0; 10 → 44,0; a mesma escala de 243 linhas do y)
  e **Hor = 6,0 px por unidade** (10 → 59,9; 5 → 31,3 — largura de referência 320, NÃO os 720 do x). Perfil em S:
  2–98 % ≈ 1,5 × a largura 10–90. Medido pela ESCRITA (o retângulo da rodada 02 com Hor/Vert trocados no bloco e o
  render do MC). ⚠️ Os controles do AniMatte só mostram NÚMERO com uma forma selecionada no monitor (o catálogo de
  2026-10-12 os dava como "sem número").
- ✅ **Keyframes**: cada keyframe do `EffectParamList` carrega o bloco BZFX INTEIRO (todas as formas); o
  `percent_time` é a fração do clipe em 2^30 (0 = início, 1073741824 = fim). Os dois keyframes de fábrica nascem
  `selected` — editar com os dois selecionados muda os dois (sem animação); com só o do fim selecionado, mover a
  forma anima. **Interpolação LINEAR dos vértices** entre keyframes (topo do retângulo a ±0,8 px da reta em 13
  quadros de 0 a 143).
- ✅ **ESCREVER funciona** (sentido Premiere/Resolve → Avid): trocar o `user_param` dos keyframes por blocos BZFX
  nossos e o MC renderiza. ⛔ Numa CÓPIA da sequência com MobID NOVO — reescrever a sequência no lugar não pega (o MC
  serve o mob da sessão e regrava a versão da memória no CloseBin seguinte; ver "ARMADILHA DE MEDIÇÃO" em
  escrita.md). Código: `lab/bancadas/avid/animatte_rodada.py` (`bzfx`, `escrever`, `com_feather`).
  `pendente`: Bias ≠ 50, Mode (Key In/Out), keyframes no meio do clipe (`percent_time` fracionário), curva de
  aceleração, a ordem das formas (qual fica por cima). Roteiro de
  cada rodada: `lab/bancadas/avid/animatte_rodada.py NN nome` (salva, decodifica, exporta e mede).

## Collapse (`EFF_SUBMASTER`) — o Nest do Avid

Medido em 2026-10-12, MC 25.6 Windows, projeto 1080p/23,976, pelo PILOTO (laboratório: caso **B21_COLLAPSE**,
`lab/collapse_b21.py` + `lab/bancadas/avid_collapse.py`; resultado em `resultados/B21_COLLAPSE/MC.md`). Decisão do
autor: o Nest do Premiere vira **um Collapse por ocorrência** (o Collapse vive só na timeline, sem item na bin).

- ✅ **O Collapse é um `TrackEffect` "Submaster"** (`EFF_SUBMASTER`, classe `Image`, tipo `Unknown`,
  `_BORDER_FIXED 0`, sem parâmetros) na **trilha MAIS BAIXA da seleção**, com a duração do trecho; nas trilhas de
  origem o trecho vira `Filler`. As trilhas colapsadas viram **trilhas INTERNAS** do efeito, intactas (os efeitos
  delas — PIP com Crop/Position — vão junto):
  - **UMA trilha colapsada** (clipes em sequência): uma trilha interna, índice 1, com os clipes; o `filler_proxy`
    dela olha a trilha de BAIXO (`TrackRef relative_scope 1`).
  - **VÁRIAS** (o mosaico, V2 + V3): a 1ª interna é só FUNDO (`Filler` do tamanho todo, `relative_scope 1`) e
    depois uma por trilha colapsada, de baixo para cima (índices 2…, `relative_scope 0`).
- ✅ **Efeito aplicado SOBRE o Collapse (duplo-clique na paleta, com o Collapse marcado) SUBSTITUI o Submaster como
  recipiente**: o Flop (`EFF2_BLEND_FLIP_HORZ`) passou a carregar as trilhas internas. Ou seja: qualquer efeito pode
  ser um recipiente de várias trilhas; o Submaster é só o recipiente que não faz nada. O efeito vale para tudo dentro:
  o mosaico saiu ESPELHADO inteiro (o render é o espelho exato do sem Collapse, fora a emenda de 1–2 px no meio).
- ✅ **O render não muda ao colapsar**: Collapse de 3 trilhas e de 1 trilha = 0 px diferentes (> 8/255) do render sem
  Collapse, em 9 quadros.
- ✅ **ESCREVER o Collapse do zero funciona** (o caminho Nest do Premiere → Avid): recipiente copiado do que o MC
  gravou (Submaster ou Flop) + as trilhas internas na forma acima → 0 px diferentes do Collapse feito pelo MC, e a
  sequência abre na timeline com os segmentos colapsados normais. Código: `avid_collapse.montar_colapsado`.
- ✅ **PIP e Resize (`AFX_*`) na bin**: `AFX_CROP_LEFT_U`/`RIGHT_U` e `AFX_POS_X_U` em **milésimos da largura**
  (Crop 250 = 25 % de cada lado; Position 250 = 480 px em 1920), confirmado no render. ⚠️ O **Resize é OPACO** (fundo
  preto cobre a trilha de baixo): mosaico no Avid é o **PIP** (escala de fábrica 50 % — escrever 100). O PIP tem DUAS
  trilhas internas (a 1ª = fundo que olha embaixo, a 2ª = o clipe); o Resize, uma. Cópia de efeito do MC: zerar o
  `left_bob` (com `= None`, apagar a propriedade quebra o write) e o `bob_data` das trilhas internas.
- ✅ **Collapse DENTRO de Collapse existe** (2026-10-12, v8): colapsar V1 + V2 quando cada uma já tinha um Collapse dá
  um Submaster cujas trilhas internas contêm os Submasters de antes (três níveis: fundo / Collapse do FUNDO / Collapse
  do mosaico com os dois PIPs). Mesmo render, fora as 2 colunas da borda suavizada do PIP: o Collapse de dentro é
  COMPOSTO SOBRE PRETO antes de cair no de fora (a borda semitransparente mistura com preto, não com a trilha de
  baixo) — só pesa em borda com alfa parcial. (O autor achava que não era possível; a medida diz que é.)
- ✅ **Corte (Add Edit) no meio de um Collapse = DOIS Collapses completos e independentes**: o recipiente se parte em
  dois (42 + 54 quadros), cada um com TODAS as trilhas internas e os aninhados aparados, e o in dos clipes de dentro
  ajustado (o FUNDO do 2º começa no quadro 90 do arquivo). O próprio Avid trata cada pedaço como cópia — coerente com
  "um Collapse por ocorrência".
- ✅ **Áudio não colapsa**: Collapse com só A1 + A2 selecionadas não faz NADA (sem aviso); com V1 + A1 + A2, só a
  imagem vira Submaster e o som fica solto embaixo. O Submaster é efeito de vídeo (como o autor dizia). Na tradução:
  o som de um Nest do Premiere sai como trilhas comuns da timeline.
- ✅ (2026-10-12, à tarde; LAB_COL_TW_v1) **Velocidade SOBRE o Collapse: o MC recusa com aviso** "Effect does not
  apply." [OK] (preset 0% To 100% com o Collapse selecionado). No Premiere → Avid, a velocidade de um Nest vai PARA
  DENTRO (em cada clipe) — não há recipiente de velocidade.
- ✅ **Step In (DoCommand 6264) / Step Out (6265)**: com a agulha no Collapse, o Step In mostra a trilha de dentro
  (o Record vira "Nested Effect", a timeline mostra só o clipe interno com régua própria). **Velocidade DENTRO do
  Collapse funciona**: Submaster → trilha interna → `MotionEffect` → clipe (a mesma forma de um clipe com velocidade);
  render da rampa 0%→100% dentro do Collapse = **piso(mapa) 48/48**, igual à mesma rampa num clipe comum.
- ✅ (2026-10-13, projeto "DLPC LAB NEST 23.976", `lab/bancadas/avid_nest.py`) **O escritor do APP faz o Collapse**
  (`avb_export/translate.py`, `_colapsar_compostos` + `_build_collapse`; molde `EFF_SUBMASTER` nos `templates.json`):
  origem B16 do Premiere (nests a 1×, in deslocado, nest a 400 %, clipe a 466,67 % dentro de nest a 1×) pelo leitor do
  `.prproj` → render do MC com a MESMA placa do render do Premiere em todo quadro (11/11 por segmento). Nest de nest
  sai ACHATADO num Collapse só (o leitor já achata; o Collapse dentro de Collapse fica para quando pesar).
- ⛔ **Collapse só com vazios** (a mídia de dentro não casou): o export do MC recusa a sequência INTEIRA —
  aviso "Some sequences could not be committed. Please see the console for details." e, no Console (Tools, DoCommand
  1910), `Sequence "" cannot be committed because it is empty`. O escritor põe um vazio no lugar.
- ⛔ **A MESMA recusa vem de trilha de vídeo DESLIGADA** (`session_attr` `_ENBLSTATE 0`/`_MONSTATE 0`, o que o
  `translate.build` grava): para o export a sequência está vazia. Ligar (`1`/`1`) resolve — o Ciclo Assist já faz.

## Taxa mista — o ADAPTADOR de taxa do Avid (clipe de outra taxa na timeline)

Medido em 2026-10-12, MC 25.6 Windows, projeto 1080p/23,976, pelo PILOTO (laboratório `lab/bancadas/avid_taxas.py`
e `avid_taxas_render.py`; placas B02 25 e 59,94 qps com o número do quadro em código de barras, B14_FRENTE_100 com
dígitos). Motivo: o R04 PRODUCAO-C tem 80 de 89 clipes em 25/60/100 qps numa timeline de 23,976.

- ✅ **ImportFile CONVERTE para a taxa do projeto** (mídia gerenciada): a placa de 25 qps (250 quadros) virou master
  a 23,976 com 240; a de 59,94 e a de 100 também — o tempo real é feito NA IMPORTAÇÃO e a timeline não tem adaptador.
- ✅ **LinkFile (AMA) mantém a taxa NATIVA**: masters a 25 / 59,94 / 100 (nome sem a extensão). É o caso real.
- ✅ **Editado PELO MC (Overwrite) numa timeline de 23,976, o clipe AMA ganha um ADAPTADOR**: `MotionEffect`
  `EFF_TIMEWARP.MOTION_CTL`, atributos `_MIXMATCH_MOTIONADAPTER 2`, `_SFX_RENDER 4`, `_SFX_IGNORE_RENDER_SETTING 1`,
  `_MFX_INPUT_FORMAT 2`, `_MFX_OUTPUT_FORMAT 2`; `param_list` VAZIA (sem curva — é o que o separa de velocidade do
  editor); `speed_ratio` = **taxa da timeline ÷ taxa da fonte** (25 → `[960, 1001]`, 59,94 → `[2, 5]`, 100 →
  `[240, 1001]`; o 24 → 23,976 já visto é `[1000, 1001]`); dentro, a trilha na TAXA DA FONTE com o SourceClip
  cobrindo os quadros necessários (48 da timeline = 51 a 25 qps, 120 a 59,94, 201 a 100). Tempo real, sem câmera lenta.
  Na timeline o nome do segmento ganha "(25.00 FPS)" e o ícone de efeito.
- ⛔ **O render padrão (`_SFX_RENDER 4`) MISTURA dois quadros da fonte** quando a posição cai entre eles (o 59,94 no
  quadro 51 mostra 7 e 8 sobrepostos; no 100 qps 13 de 48 quadros ficaram ilegíveis) — o Premiere e o Resolve mostram
  quadro inteiro. ✅ Escrevendo `_SFX_RENDER` **0, 1, 2 ou 3** numa cópia (MobID novo), o render dá **quadro inteiro e
  quadro da fonte = piso(k × taxa da fonte ÷ taxa da timeline)** em 48/48 quadros nas três taxas — a mesma regra
  medida no Fusion do Resolve. 5 = mistura como o 4; 6 = outra interpolação (FluidMotion?). `hipótese`: os valores
  seguem a lista do Motion Effect (0 Duplicated Field, 1 Both Fields, 2 Interpolated Field, 3 VTR-Style, 4 Blended
  Interpolated, 5 Blended VTR, 6 FluidMotion) — a ordem bate com o que se viu, o nome não foi lido na tela.
  **Na tradução Premiere → Avid: adaptador com `_SFX_RENDER 1`.** `pendente`: conferir o piso contra o render do
  Premiere do mesmo clipe. (A rampa em cima de clipe de outra taxa: seção seguinte.)
  ⛔ CORRIGE a hipótese acima (2026-10-12, LIDO no Motion Effect Editor, um segmento por valor — LAB_RAMPA_TIPOS):
  **0 Duplicated Field · 1 Interpolated Field · 2 Both Fields · 3 VTR-Style · 4 Blended Interpolated · 5 Blended VTR ·
  6 FluidMotion · 7 FluidMotion Draft** (a lista do editor tem outra ordem: Duplicated, Both, Interpolated, VTR, Blended
  Interpolated, Blended VTR, FluidMotion Draft, FluidMotion — o valor NÃO é a posição na lista). Os presets de Timewarp
  gravam 2. **Na tradução: `_SFX_RENDER 2` (Both Fields)** — quadro inteiro pelo piso (medido 48/48 no adaptador) e o
  nome que o editor espera em material progressivo.

- ✅ (2026-10-13, "DLPC LAB NEST 23.976", B16 do Premiere pelo escritor do APP — `translate._entry_outra_taxa`, molde
  `EFF_TIMEWARP_ADAPTADOR` do LAB_TAXAS_r2) **O adaptador ESCRITO renderiza igual ao Premiere**: placa de 100 qps a 1×
  dentro de nest → a mesma placa em 11/11 quadros. Forma: o `MotionEffect` do MC com `speed_ratio` na fração EXATA
  (23,976 ÷ 100 = `[240, 1001]`; com a taxa arredondada sai `[2997, 12500]`), a trilha de dentro (Sequence, Fillers e
  SourceClip) com `edit_rate` = taxa da FONTE e o clipe em quadros da fonte (12 da timeline → 51), `_SFX_RENDER 2`.

## Rampa (Timewarp) — o PROMOTE do adaptador, a âncora e quem manda no render

Medido em 2026-10-12, MC 25.6 Windows, projeto 1080p/23,976, pelo PILOTO (lab `lab/bancadas/avid_rampas.py`;
`saida/bancadas/avid/rampas/LAB_RAMPA_M*`); as placas B02 25 / 59,94 e B14_FRENTE_100 com o número do quadro.

- ⛔ **O MC NÃO aplica efeito de velocidade sobre o adaptador de taxa** (o autor, 2026-10-12). ⛔ CORRIGE (mesmo dia):
  o "recusa calado" que se anotou aqui veio de um teste ERRADO — o preset foi aplicado com o trecho marcado por IN/OUT,
  e o efeito da paleta vai no clipe SELECIONADO (no controle, nem um clipe comum recebeu o preset assim). A recusa vale
  pela palavra do autor; o aviso que o MC dá (ou não) com o clipe selecionado não foi visto. Para editar a velocidade de
  um clipe de outra taxa: **Motion Effect Editor** (DoCommand **6296**) com o segmento selecionado → **"Motion Adapter:
  Promote"** (o autor, 2026-10-12). Promovido, o adaptador vira um Timewarp editável já com a velocidade da cadência
  (25 qps → **104,27 %**).
- ✅ **O que o Promote grava** (o mesmo `MotionEffect` `EFF_ADV_MOTION_CTL`, no lugar): `_MIXMATCH_MOTIONADAPTER` **2 → 4**
  (+ `_MFX_VIEW_SPD_TOP 300`, `_MFX_VIEW_SPD_BOTTOM -100`, `_NEW_SHAPE_REFERENCE_FRAME 1`); `param_list` de 3:
  `8d56827c` **velocidade** (p0; 1 ponto, valor 1,0427 = 25 ÷ 23,976), `8d56827d` **posição** (p1; (0, 0) → (48,
  50,05)), `8d568283` inteiro 0; `speed_ratio` = **comprimento ÷ clipe de dentro** (48/51 = `[16, 17]`), não a razão
  das taxas.
- ⭐ **A unidade da velocidade é QUADROS DA FONTE por quadro da timeline** (100 % = um por um): o tempo real de um
  clipe de outra taxa é taxa da fonte ÷ taxa da timeline (25 → 104,27 %; 59,94 → 250 %; 100 → 417 %). O Premiere
  conta em tempo real (100 % = tempo real): **vel_Avid = vel_Premiere × taxa da fonte ÷ taxa da timeline**.
- ⭐ **ÂNCORA = pp `code 14`** (o tradutor do RELINKER chamava `PP_BASE_FRAME_U`) num ÚNICO keyframe da curva de
  velocidade; o valor = a posição da FONTE presa àquele quadro (o "Anchor" do editor, com TC e o botão de âncora). A
  integral sai dela para os DOIS lados: no preset "100% To 0%" a âncora está no último keyframe (quadro 23, fonte
  12,0) e o mapa começa em 0,4; no Reverse, quadro 0 com fonte 23. O gráfico de POSIÇÃO (`_MFX_GRAPH_ENABLED 2`) não
  tem âncora. Demais pp: 5/7 alça de tempo (in/out), 6/8 alça de valor, 9 tipo (1).
- ⭐ **O RENDER SEGUE O MAPA (p1), não a curva (p0)** — M3: curva constante + mapa de uma rampa → o render mostrou a
  rampa em 144/144 quadros (no fim do 25 qps: fonte 78, não 49). Quem recalcula o mapa a partir da curva é o editor,
  quando o usuário mexe.
- ✅ **Escrita validada pelo escritor de PRODUÇÃO** (`motor/avb_export/translate.py::_set_motion_speed`: curva com
  âncora no 1º keyframe, fonte 0; mapa pela integral em meio quadro): o adaptador promovido por escrita (attrs acima +
  `param_list` do molde) com rampa 1× → 2× tempo real, `_SFX_RENDER 1` → **quadro da fonte = piso(mapa(k))** em
  **144/144** nas três taxas (M1); a promoção constante idem (M2). Export de 144 quadros em 23 s.
- **Na tradução Premiere → Avid:** promovido (`_MIXMATCH_MOTIONADAPTER 4`) quando a taxa difere, `_SFX_RENDER 1`; no
  **p1** a posição exata da fonte em cada quadro do plano (a regra de amostragem do Premiere, em quadros da fonte);
  no **p0** a curva (para o editor), velocidade convertida pela razão das taxas.
- ⛔ **AMA no export de rampa**: com os clipes AMA (LinkFile) o export da M1 TRAVOU (barra parada, estimativa só
  crescendo; Ctrl+. apagou o parcial e o MC teve de ser reiniciado). Com a mídia transcodificada na taxa de origem
  (Consolidate/Transcode → **"Keep source's frame rate"**, DNxHR LB; o master sai `<nome>.new.01` na taxa nativa) o
  mesmo export levou 23 s. No laboratório: a MXF, não o AMA (autor).
- ✅ **Rampa em clipe NATIVO** (23,976 em 23,976; molde `templates.json` → EFF_ADV_MOTION_CTL + `_set_motion_speed`,
  o caminho de produção inteiro): 1×→2×, 2×→0,5× e Bézier com alças HORIZONTAIS (a transição do Premiere com influência
  50 %) → piso(mapa) **144/144** (LAB_RAMPA_N1). O MC rotula o segmento pela curva ("100% to 1xx% to 200%").
- ✅ **Âncora fora do 1º quadro escrita por nós** (code 14 movido para o 3º keyframe, valor = p1 ali; N2): render igual
  (144/144) e o editor mostra **Anchor = TC do quadro da fonte** (in 0 + 39 → 01:01:01:06 a partir de 01:00:59:15) — o
  valor do code 14 é a posição no mapa, contada do início do clipe de DENTRO.
- ⭐ **QUADRO A QUADRO pelo gráfico de POSIÇÃO** (a forma da regra do autor para rampa entre NLEs — 2026-10-12,
  LAB_RAMPA_K1): molde = o preset Speed Boost aplicado pelo MC (`_MFX_GRAPH_ENABLED 2`; p0 = posição, p1 = um ponto 0),
  p0 com **um keyframe por quadro** (`offset [k, 1]`, valor = quadro da fonte INTEIRO, contado do in do clipe de
  dentro; pp 5–8 = 0, 9 = 1), `speed_ratio` = [n, clipe de dentro]. Padrão de propósito irregular (normal, congela 3,
  salta de 3, ré de 2) → **48/48 exatos, sem mistura, em Both Fields (2), Blended Interpolated (4) e FluidMotion (6)**:
  com a posição inteira o tipo de render não muda a imagem — pode levar a escolha do editor (Optical Flow → 6) como
  metadado. `pendente`: Optical Flow com posição FRACIONÁRIA (o Premiere sintetiza o quadro; replicar a fração com
  FluidMotion não fica idêntico — decisão do autor).
- ✅ **HÍBRIDO: curva + constante no MESMO segmento** (2026-10-12, LAB_RAMPA_H1; a forma da regra do autor — só a
  curva se queima) [e ver o item seguinte: o gráfico de posição SOBRE o adaptador]: gráfico de POSIÇÃO com `interp_kind 3` (Linear), keyframe por quadro SÓ dentro da curva e um no
  início/fim de cada trecho constante (valor = posição EXATA, fracionária). Casos: 1,2× → curva (12–30) → 1,9×
  (21 keyframes) e curva 2×→0,6× (0–20) → 0,6× (22 keyframes): **piso(posição) 48/48 em cada**, igual ao denso de
  controle. ⚠️ O molde (preset Speed Boost) vem com `interp_kind 6` (Spline): entre keyframes esparsos ele faria
  curva — trocar para 3. ⚠️ Posição INTEIRA num trecho constante deixa o piso à mercê do arredondamento (15,99999 → 15):
  gravar a posição exata, não arredondada para cima/baixo.
- ✅ (2026-10-13, B16 pelo escritor do APP) **Gráfico de POSIÇÃO SOBRE o adaptador de taxa**: o molde de posição com
  `_MIXMATCH_MOTIONADAPTER 4` (+ `_MFX_VIEW_SPD_TOP 300`/`_BOTTOM -100`), a trilha de dentro na taxa da FONTE e as
  posições em quadros DA FONTE → placa de 100 qps dentro de nest a 466,67 % (a grade do nest do Premiere: 16, 37,
  54, 75…) = a mesma placa do Premiere em 11/11 quadros. Fecha o `pendente` "gráfico de posição sobre o adaptador".
- ✅ **PREMIERE → AVID, ponta a ponta no laboratório (2026-10-12, B22; um programa por vez: Premiere → fecha → MC)**:
  a origem B22_RAMPAS (Time Remapping escrito no `.prproj`, render do Premiere 23.2) traduzida pelas regras do autor —
  A e B (curva) = HÍBRIDO (keyframe por quadro só na janela 7 → 8 descontado o in; Linear no constante; posições do
  `_remap_fonte` de produção), C (50 % + Optical Flow) = constante NATIVA 0,5 + FluidMotion (6) — e comparada com o
  render do Premiere: **A 48/48 e B 48/48 com o MESMO quadro** (diferença de pixel 0,7 = só o codec), 22 e 16 keyframes;
  **C**: as posições inteiras iguais; as x,5 sintetizadas pelos dois, cada um a seu modo (o FluidMotion deixa contornos
  fantasmas; o Optical Flow do Premiere rasga o desenho) — a mesma intenção, não o mesmo pixel, como o autor previu.
  `lab/bancadas/avid_rampas.py::traduzir_b22`, `comparar_b22`; `saida/bancadas/avid/rampas/B22_avid_x_premiere.json`.
- ✅ **AVID → PREMIERE, ponta a ponta (2026-10-12, B22)**: origem = rampa NATIVA do Avid (gráfico de velocidade,
  Bézier: A 1,2× → curva → 1,9×; B já começa desacelerando 1,4× → 0,6× → constante; C 50 % FluidMotion), render do MC.
  LEITOR: posição de cada quadro = in do clipe de dentro + mapa p1 (gráfico de velocidade) ou p0 (gráfico de posição),
  relido da bin — bate com o render do MC (A, B 48/48). Onde a curva começa e termina sai das PRÓPRIAS posições (a
  velocidade quadro a quadro muda = curva; igual = constante) — vale para qualquer origem. ESCRITOR do Premiere
  (`lab/bancadas/premiere_rampas.py::de_posicoes`, `forcar_de`): constante em todo o segmento → `PlaybackSpeed`
  (FluidMotion em câmera lenta → `TimeInterpolationType 2`); com curva → Time Remapping com canto (tipo 6) onde a
  velocidade muda (um por quadro na curva, só as pontas no constante: 22 e 17 keyframes). Render do Premiere × do MC:
  **A 48/48 e B 48/48 o MESMO quadro** (pixel 0,68 = codec); C: inteiros iguais, x,5 sintetizados por cada um.
- ✅ **O LEITOR do app (`avb_bin/segmentos.py::_velocidade`) agora lê o gráfico de POSIÇÃO** (o mapa é o p0 quando
  `_MFX_GRAPH_ENABLED 2`; antes ia o p1 de um ponto só) e leva `_SFX_RENDER` 6/7 (FluidMotion) como `retime
  optical_flow` (o Resolve sintetiza). Avid → Resolve 48/48 em todas as formas (ramo `rampas`, 2026-10-12).
  ⚠️ Gráfico de posição com Spline/Bezier entre keyframes ESPARSOS (os presets do MC): o app liga em reta e AVISA —
  a interpolação Spline do Avid ainda não foi medida.
- ✅ **Interpolação da curva = `control_track.interp_kind`** (2026-10-12, o MC escreveu e lemos — LAB_RAMPA_INTERP2;
  só para o caminho Avid → Avid): **2 Shelf · 3 Linear · 5 Bezier · 6 Spline** (o padrão; o molde de produção já tem 6).
  Vale para a CURVA INTEIRA, mesmo escolhida com um só keyframe selecionado. O `pp code 9` NÃO muda (fica 1). Ao abrir,
  o MC RECALCULA as alças de todos os keyframes (±40 % do intervalo até o vizinho, horizontais) — as que gravamos não
  ficam. `_FX_CURRENT_KF` = o keyframe selecionado na interface (estado de tela). O mapa de posição (p1) usa
  `interp_kind 3` (linear). **Fixed / Elastic Keyframes não muda nada na bin** (curva, pp e parâmetros iguais; o menu
  passa a marcar Elastic) — `hipótese`: preferência do editor, não dado do efeito. o que o Premiere mantém FIXO quando a velocidade de
  um trecho muda (o autor duvida que seja o 1º quadro do clipe: testar no laboratório do Premiere).

## 🆕 Stabilize (`EFF2_STABILIZE`) — o TRACKER está na bin, quadro a quadro — `confirmado` (leitura) 2026-10-23

> ⭐ **Para o PREMIERE (2026-11-20):** vira o Warp Stabilizer (Position · Smooth Motion · filtro × 100 · Auto-scale),
> aplicado pelo QE depois da importação — parecido, não igual (até ~10 px e +1,2 % de escala no plano que mais treme da
> PRODA, medido contra a conta abaixo). Medida e índices dos params: `laboratorio-de-midia/resultados/B19_ESTABILIZADOR/
> PREMIERE.md`, seção "O Stabilize do AVID levado ao Warp Stabilizer".

⛔ **CORRIGE** "o movimento estabilizado não é portável" (`dados/efeitos-na-bin.json`, CASO E07): isso valia para o
AAF/os parâmetros DVE; ninguém tinha descido ao `trackman` do `TrackEffect`. A pyavb já lê a árvore
(`avb/misc.py`): `TrackEffect.trackman` (`TKMN`) → `data_slots` (`TKDS`, `track_fg`) → `tracker_data[]` (`TKDA`, um por
ponto) e `param_slots` (`TKPS` → `TrackerParameter` `TKPA`, 96 bytes: liga tracker ↔ parâmetro, ids 0x8a/0x8b).
Medido na PRODA (`02 PROJETOS AVID\PRODUCAO-A\03_OC_EDIT VALENDO.avb`, objeto 16165, MC 2023/24, 23,976):
- `TrackerData.settings` (56 B): `II` + … + `80 07 38 04` (1920×1080) + nome **"Point A"** + flags;
  `offset_tracking` 1 · `smoothing` 0 · `jitter_removal` 1 · `filter_amount` 0,5 (o modo "remover tremor").
- `clips` = 11 `ParamClip` + `clip5`/`clip6`, `media_kind` 10, `length` 384:
  **0/1 = X/Y do ponto rastreado, 1 por quadro** (342 pontos, Linear; 0,369→0,408 e 0,426→0,501 — fração do quadro,
  `inferido`); 2 = confiança (1,0); 3/4 = degrau começando em 0 (`pendente`); 5–10 = tamanhos das caixas de padrão e
  de busca (constantes); 11/12 e `clip5`/`clip6` = o ponto de referência (= quadro 0).
- Os parâmetros DVE ao lado: `DVE_POS_TRACK_U` 1, `Auto-Zoom` 1, `DVE_SCALE_X/Y` 104,28, `DVE_POS_X/Y` (0,10; −1,78),
  `DVE_TRACKING_*_INVERT` 1. O efeito pode ter `precomputed` (o render do Avid) — a mídia da PRODA não está nesta máquina.
- Código: exportado pela **`ameLibrary.dll`** (23 MB; `TrackerDataSlots::GetTrackerData/GetSmoothingValue/
  GetJitterRemovalEnabled/GetOffsetTrackingEnabled`, `TrackerData::AlignPatternConfidenceWithTracking`) — alvo para o
  Ghidra/REA (o `AvidMediaComposer.exe` de 59 MB não abre; tem o `StabilizeFillerVisitor`).
- ⭐⭐ **A CONTA — `confirmado` pela imagem (2026-10-23, MC 24.6.0 Win11, tracker "FluidStabilizer", modo remover
  tremor, `filter_amount` 0,5):** laboratório `B19_TREMIDO.mov` (tremor CONHECIDO, `verdade.json`), Stabilize arrastado
  da paleta (Image) para o clipe de 144 q, export DNxHR LB, a correção medida quadro a quadro (zoom desfeito +
  `phaseCorrelate`). Projeto "DLPC LAB ESTABILIZADOR".
  - Curva 0/1 = posição do ponto em FRAÇÃO do quadro, origem no canto SUPERIOR ESQUERDO, Y para baixo (contra a
    verdade: x = −1,003·dx + 561 px, y = −1,006·dy + 473 px, corr −0,986/−0,984; o resíduo de 3–4 px é a rotação, que o
    tracker de 1 ponto não mede).
  - **Render: R(q) = Z( T(q + u) )**, Z = zoom do `DVE_SCALE_X_U` (Auto-Zoom, 106,04 %) em torno do centro, e
    **u = p − G₁₅(p) + d**: p = curva rastreada em px, **G₁₅ = gaussiana σ 15 quadros, borda "nearest"** (repete o 1º
    e o último), d = o `DVE_POS_X/Y_U` (−2,02 → +3,64 px de fonte = −2,02 × 1,92 ÷ 1,0604). Resíduo **0,10 px (x) /
    0,06 px (y)** RMS em 144 quadros. Travar no quadro 0 dá 7,6 px; média móvel 49, 1,4 px.
  - ⭐ **σ = 30 × `filter_amount` QUADROS** — três renders: 0,2 → σ 6 · 0,5 → σ 15 · 1,0 → σ 30, cada um com
    resíduo 0,10/0,05 px. A quantidade é o campo numérico da linha do tracker na janela Tracking ("50" = 0,5; Effect
    Mode → botão Tracking na coluna do Effect Editor). O Auto-Zoom ficou 106,04 % nos três (não recalculou).
  - ⭐ **O tracker TAMBÉM VIAJA NO AAF** (PRODA `PRODA_RELINKER_ALTA.aaf`, pyaaf2): no `OperationGroup` "Stabilize_2" as
    propriedades privadas `OpGrpTKMNTrackerDataAry` (objetos `AvidTrackManTrackerDataClass`) com `TKMNTrkDataDataX/DataY`
    (VaryingValue, 1 ponto por quadro, Linear), `TKMNTrkDataConfidence`, `TKMNTrkDataOffsetX/Y`, `TKMNTrkDataBoxX/Y`,
    `…SearchTH/BH/LW/RW`, `…PatternW/H`, `TKMNTrkDataFilterDataAmt` (1/2), `…JitterRemovalEnabled`, `…SmoothingEnabled`,
    `…OffsetTrackingEnabled`, `TKMNTrkDataSettings` (os 56 bytes com "Point A") e `OpGrpTKMNTrackedParamAry`/`…Setng`.
    O leitor comum de parâmetros não os vê (não estão em `Parameters`). Tempo do ponto k = k / comprimento do EFEITO →
    o ponto k é o quadro k do SEGMENTO; no Stabilize de 203 q há 342 pontos (até 1,68): o rastreio passa do fim
    (clipe aparado depois de rastrear). Valores = os da bin.
  - ⭐ **σ é em QUADROS, qualquer taxa**: projeto 1080p/50 ("DLPC LAB ESTABILIZADOR 50P", `B19_TREMIDO_50.mov` com o
    MESMO tremor em segundos, clipe LINKADO pelo autor — o `ImportFile` falhou ali), filtro 0,5 → **σ 15** (não 31),
    resíduo 0,11/0,06 px. O deslocamento fixo: **x px = DVE_POS_X × W/1000, y px = DVE_POS_Y × H/1000**, ÷ zoom
    (23,976: −2,02/0,062 → +3,64/+0,04; 50p: −0,116/+0,391 → +0,19/+0,38). O Auto-Zoom muda por clipe (106,04 / 104,87 %).
  - A conta completa, para portar: u(k) = p(k) − G_{30·filtro}(p)(k) + (−POS_X·W, +POS_Y·H)/1000/Z, depois o zoom Z
    em torno do centro (p em px: curva × W e × H). ⚠️ CORRIGIDO 2026-10-24: o SINAL do X é trocado — os próprios
    números medidos acima o dizem (POS_X −2,02 → +3,64 px; −0,116 → +0,19), e o do Y não (+0,062 → +0,04; +0,391 →
    +0,38): no Avid +Y é para CIMA e na imagem para baixo. Antes estava "+ (POS_X·W, POS_Y·H)". Conferido pela
    imagem na PRODA (abaixo): com o sinal trocado o erro seria 15 px.
  - ⭐⭐ **VIROU RECURSO (2026-10-24, De Lá Pra Cá `motor/estabilizacao.py` + `drp/estabilizador.py`):** a conta
    acima, lida do AAF (`OpGrpTKMNTrackerDataAry`) ou da bin (`trackman`), vai ao estabilizador do Resolve (injeção
    no `0x10300015`, `drt-drp/estruturas.md` §ESTABILIZADOR). Só o modo medido: 1 ponto, `jitter_removal` sem
    `smoothing`, sem velocidade no segmento; o resto fica como nota. Pontos rastreados ALÉM do fim do segmento (PRODA:
    342 num efeito de 203) ficam de fora (`pendente`: o G os usa?). Prova pela imagem na PRODA (Resolve 21.1, Mac,
    projeto "DLPC PRODA 21 MAC ESTAB"), medida no FUNDO parado (a pessoa se mexe), contra a previsão da conta sobre
    a mídia: A001_03170454_C013 (V2, zoom 104,28 %) corr 0,991/0,998, resíduo 0,23/0,34 px em 960 de largura, o tremor
    vertical cai de 2,02 para 0,75 px; A001_03170439_C011 (V1, quase parado) 0,94/0,90. ⏳ Contra o render do MC num
    caso real (a PRODA não tem o render do Avid nesta máquina) e o "Stabilize" do MC do Mac.
  - ⏳ `smoothing`/`offset_tracking`; Region Stabilize e
    vários pontos; o mapeamento quadro do track × quadro do segmento (na PRODA: 342 pontos num efeito de 203).
- ⏳ A CONTA (track → correção no render: o filtro de tremor 0,5, a origem e a escala das coordenadas, o mapeamento
  quadro do track × quadro do clipe, `length` 384 × 342 pontos × efeito de 203) — medir num laboratório com tremor
  CONHECIDO (como o B19 do Premiere) contra o render do MC, e então injetar no estabilizador do Resolve (`0x10300015`,
  `drt-drp/estruturas.md`).

## 🆕 O Motion do Premiere → o efeito geométrico do Avid (`confirmado` pela imagem, 2026-10-25, MC 25.12 Mac)

Medido pela rota Premiere → Avid do De Lá Pra Cá (`_DeLaPraCa/motor/avb_export/translate.py::_geo_premiere`), PRODC_CORTE02
(R04) × `PRODC_Trailer_v02_RESGATE.mov`, 144 pontos (1º e último quadro visível de cada plano), foto do Record a cada
`SetPosition` (`tools/bancada_avid/conferir_record.py`). **108 → 133/144**; o resto é máscara de opacidade e o cartão.
- Escala relativa ao ENCAIXE (a mesma do leitor do .prproj para o Resolve) em **%** e posição em **milésimos do
  quadro** valem como estão nos três efeitos: `AFX_SCALE_X/Y_U` + `AFX_POS_X/Y_U` (Resize, PIP; **+Y desce**) e
  `DVE_SCALE_X/Y_U` + `DVE_POS_X/Y_U` (3D Warp `EFF2_SBLEND`; **+Y sobe**, com os interruptores `DVE_*_ENABLED_U` = 1).
  `AFX_FIXED_ASPECT_U` (o `8d56812b`, 1 nos moldes) = 0 quando X ≠ Y (a escala só no Y das proxies 1024×540): confere.
- ⭐ **Espelho do Premiere = 3D Warp com `DVE_ROT_Y_U` 180** (vertical: `DVE_ROT_X_U`): LOU_7254, A030_C045, JUL_7644 de
  0,08–0,47 para 0,83–0,92. O `DVE_ROT_Y_U` não vinha no molde: o `ParameterItem` nasce da cópia de um irmão float
  com o uuid trocado, e o MC o aceita.
- ⭐ **Rotação: `DVE_ROT_Z_U` = −(a rotação na convenção do Resolve)** — com o mesmo sinal o drone girado (−246° →
  −181°) saía para o outro lado (corr −0,37); invertido, 0,87.
- ⭐⭐ **Keyframe de parâmetro AFX/DVE ESCRITO por nós funciona**: no `ParameterItem`, `control_track` = um `ParamClip`
  (cópia do da curva da transição) com `interp_kind 3` (Linear), `value_type 2`, `length` = o do efeito e um
  `ParamControlPoint` por instante (`offset [quadro do efeito, 1]`, `timescale 1`, `value`, `pp` 5–8 = 0 e 9 = 1).
  O `value` do item fica com o 1º ponto. LOU_7237 (posição e escala animadas), JUL_7644, LOU_7217: de ≤ 0,25 para
  0,86–0,92. Um ponto por quadro (o leitor já amostra assim nos trechos animados) — Spline/Bézier `pendente`.
- Escolha: Resize quando cobre o quadro e não anima (é opaco); PIP quando não cobre ou anima (deixa ver embaixo);
  3D Warp quando gira ou espelha. `pendente`: PIP × 3D Warp em plano reduzido sobre outra trilha (borda do PIP).
- ⭐⭐ **A máscara de opacidade do Premiere → AniMatte ESCRITO DO ZERO funciona** (mesmo dia, mesma régua: 133 → 143):
  o `TrackEffect EFF_ANIMATTE` do molde (LAB_ANIMATTE do laboratório) POR FORA do efeito geométrico, com UM keyframe
  por quadro do plano (`percent_time` = k ÷ (L − 1) × 2^30 — fracionário no meio do clipe: o MC interpola certo) e o
  bloco BZFX gerado: cabeçalho de 276 bytes do molde + registros novos (curva `01 00` com as alças relativas; reta
  `01 01`, tipo 2). O vértice do Premiere (normalizado na FONTE, alças ABSOLUTAS) passa pela transformação do Motion
  daquele quadro e vira x × 720/W, y × 243/H. Bloco maior que o do molde: `keyframe_size` = 168 + o bloco (o 700 do
  molde = 168 + 532) e o MC aceitou (blocos de 656 e 966 bytes). Feathering = `suave_px` × a escala da imagem ÷ 6,0
  (Hor) e ÷ 4,4 (Vert): `hipotese` que a referência aceitou (0,82–0,98), não medida pela largura da borda.
  `pendente`: máscara invertida, expansão, opacidade.
- ⛔ **Imagem parada com o adaptador de taxa = `PGLUE_IMPOLITE_PORT_NUMBER` no Record** (o cartão JPG do PRODC, que o
  Premiere declara "a 25 q/s" numa timeline de 23,976): o monitor mostra a exceção no lugar da imagem. Como clipe
  simples, 0,997. Regra: arquivo de imagem parada nunca leva `MOTION_CTL`/adaptador.
- **Régua final: PRODC_CORTE02 144/144** contra a referência (Premiere 2026 → .prproj → MC 25.12 pela rota do app,
  ~20 s de montagem com os masters reaproveitados do projeto).

## 🆕 O nome do master de ÁUDIO no link do MC: CENA/TAKE do BWF, não o arquivo (2026-10-25, MC 25.12 Mac)

Medido na bin do autor (ele linkou pelo Source Browser três WAV do PRODC gravados num Sound Devices MixPre-6;
`LAB_ARRASTO_MAC 2_SEQ.avb`). Código: `_DeLaPraCa/motor/media/bwf.py` (`como_o_avid`), confere campo a campo.
- ✅ **O master se chama `sSCENE/sTAKE`** (`FAIXA-W-C4/002`, `LOCAL-3/001`): o MC NÃO "troca o `-` por `/`"
  nem "tira a extensão" — ele monta o nome com a CENA e o TAKE que o gravador escreveu no bext/iXML. É o que fazia o
  nome do clipe no Avid nunca bater com o nome do arquivo em parte dos áudios (e bater em outros).
- ✅ `_USER` do master: `UBITS`, `TapeID` (= `sFILENAME`, o arquivo com extensão), `Shoot Date` (data + hora do bext,
  `aaaa-mm-dd hh:mm:ss`), `Scene`, `Take`, `TRK1…n` (os nomes das trilhas na ORDEM do arquivo, RENUMERADOS: o
  `sTRK3=BOOM` do MixPre num mono vira `TRK1` — corrigido no fim da seção: vem do `INTERLEAVE_INDEX` do iXML), `Production` (= `<PROJECT>` do iXML), `Circled` (`sCIRCLED`
  FALSE/TRUE → no/yes). A cadeia: master → fonte de ARQUIVO (nome = o arquivo, PCMA) → fonte de TAPE (nome = `sTAPE`).
- ✅ **LABORATÓRIO (mesmo dia, 11 WAV sintéticos de 1 s, AMA Management LIMPA antes, link pelo Source Browser — Tools ›
  Source Browser › colar a pasta na barra › selecionar todos › Link › taxa 23.98 › OK to All):**
  `laboratorio-de-midia/lab/bancadas/avid/nomes_audio.py` (gerar/ler) · a bin lida: `saida/bancadas/avid/
  nomes_audio_bin_mc2512.avb`.
  - **A regra é CENA + TAKE**: no bext (`sSCENE`/`sTAKE`) OU só no iXML → `CENA/TAKE`; take com letra vale (`CENA10/3A`).
  - **Sem cena/take** (BWF com TC, WAV simples sem bext, extensão minúscula): o master = **o nome do arquivo COM a
    extensão, como está** (`LAB_V03-A.WAV`, `LAB_V08.wav`); `_USER` = `TapeID`, `Shoot Date` (do bext, ou o mtime do
    arquivo sem zero à esquerda na hora: `9:45:19`) e um `Soundroll TC Rate` 25 (constante?); a fonte de baixo é de
    MÍDIA (`MediaDescriptor`, não `TapeDescriptor`) com o nome do arquivo.
  - ⛔ **O `;` NÃO é trocado no link do MC 25.12 Mac** — nem no nome do arquivo (`LAB;V05;A.WAV`) nem na cena
    (`CENA;6/001`). O `;` → `_` que o autor viu no PRODUCAO-A vem de OUTRO lugar: ⏳ medir no Windows (MC 24.6), no
    IMPORT (não link), no AAF e no consolidate/transcode; guardar amostras reais de lá.
  - ✅ **E o PRODUCAO-A explica o `;` → `_` SEM o Avid** (mesmo dia): a bin `03_OC_EDIT VALENDO.avb` tem os masters
    `17_25_16 Cordas.wav` com o locator em `/Volumes/ProdABckUp/PRODUCAO-A/INPUT/05_TRILHAS/231215_TRILHAS PESSOA-O/
    Wav Mixadas/17_25_16 Cordas.wav` — o arquivo do EDITOR já se chamava com `_`; a cópia do acervo
    (`MIDIAS DE TESTES/1 PRODUCOES/PRODUCAO-A/MIDIAS/TRILHAS/MIXADAS`) tem `17;25;16 Cordas.wav`. São BWF do Pro Tools
    (bext sem descrição, `minf`/`elm1`/`regn`/`umid`), sem cena/take → o MC nomeia pelo arquivo, e cada cópia deu um
    nome. Quem trocou o separador (cópia, transferência, o compositor) não fica no arquivo. E o `24_23_20 CB.wav` do
    acervo é OUTRO arquivo: a mesma `originator_reference` e o mesmo `time_reference`, mas 16-bit, sem data, só
    `fmt `/`bext`/`LIST` com `ISFT Lavf60.20.100` = gravado pelo FFMPEG (31/05/2024). Regra para o relink: o nome de
    TC vem com `;`, `_` ou `:` conforme a cópia — normalizar (o `media/matcher._normalize_name` já faz). A
    `originator_reference`/`time_reference` do bext sobrevivem à troca de nome, mas ⛔ **NÃO desempatam** (CORRIGE,
    2026-10-28): o empate é do editor (decisão do autor, 2026-09-27) — e no caso real as duas cópias têm o MESMO bext.
    O bext EXPLICA o empate na revisão: iguais = o mesmo áudio em cópias diferentes (24 × 16 bits); diferentes = áudios
    diferentes com o mesmo nome (versões). Implementado no DLPC: `media/bwf.identidade` +
    `matcher_masters._explicar_empate_de_audio` (`tests/test_empate_audio_bext.py`; conferido nos arquivos reais:
    "2 cópias do MESMO áudio … 24 bits × 16 bits").
  - Nome longo (64 caracteres) não trunca. Com acento (`LAB V07 ação.WAV`): o nome sai certo; o `TapeID` vai em UTF-8
    num campo binário (`00 00` + bytes + `00`); o diálogo "Audio Start-Time Options" mostrou o acento QUEBRADO
    (`aÃ§Ã£o`) — só na tela.
  - O diálogo de taxa: BWF com `time_reference` de 10:00:00 a 48 kHz → File TC `09:59:24:00 (24)` em 23.98 (o pulldown
    1000/1001); "OK to All" vale para a seleção inteira. ⚠️ Para o casamento no relink: master de áudio com nome `CENA/TAKE` não casa pelo nome do arquivo — usar o
  `TapeID`/`Source File`.
- ✅ **E no som GERENCIADO (OP-Atom feito por fora + AAF de masters + ImportFile), MC 2024.6 Windows (2026-11-01,
  Ciclo Assist `avid/som_gerenciado.py`):** os 11 WAV do laboratório importados e a bin comparada com a do LINK do MC
  25.12 Mac — **11/11 iguais em nome e `_USER`** (nome `CENA/TAKE` e as colunas escritas pelo pyavb com a bin fechada,
  entre o `CloseBin` e o `OpenBin` da importação; os MXF ficam com o nome do arquivo — a barra não vai a nome de arquivo).
  ⛔ **A coluna Tape NÃO segue a fita renomeada na bin**: o arquivo dizia `LABTAPE` e o MC mostrou `LAB_V10` (o nome
  que a fita tinha no AAF). O nome da fita nasce no AAF. ⭐ E o sync do Órbita com a cena SÓ no metadado (`sSCENE=10`,
  `12A`; arquivos sem claquete no nome) dividiu por cena pela COLUNA: bins `10` (3) e `12A` (1), 0 não resolvidos
  (`spikes/cena_so_no_metadado.py`). ⚠️ O pyavb 1.4 não lê o `PCMA` da bin do MC 25.12 Mac (`unknown ext tag 0x02`).
- ✅ **A comparação campo a campo com o áudio INJETADO pelo app (mesmo dia, depois do laboratório):** o De Lá Pra Cá
  autorou os 11 WAV do laboratório e os 3 do PRODC e leu de volta contra as bins do MC — **14/14 iguais** em nome,
  `_USER` e cadeia de fontes (`_DeLaPraCa/tests/test_audio_como_o_avid.py`). O que a comparação ensinou:
  - **TRK só do iXML, pelo `INTERLEAVE_INDEX`:** `sTRK1=CANAL1` no bext sem iXML (LAB_V01) e um `TRACK_LIST` sem
    `INTERLEAVE_INDEX` nem `TRACK_COUNT` (LAB_V02) não deram TRK nenhum; o MixPre traz os dois e deu `TRK1=BOOM`
    (`CHANNEL_INDEX 3`, `INTERLEAVE_INDEX 1` — a "renumeração" é o INTERLEAVE). ⏳ Qual dos dois o MC exige não está
    separado (um WAV com cada um resolve).
  - **TapeID = `sFILENAME`; sem ele (cena só no iXML), o nome do arquivo.**
  - **A cadeia muda com a cena:** master → fonte de arquivo (PCMA) → fonte de TAPE (`sTAPE`) com cena; → fonte de
    MÍDIA (`MediaDescriptor`, o nome do arquivo) sem. Quem autora por molde precisa do molde da MESMA variante (o de
    gravador num WAV de música põe o tape do molde na coluna Tape) — o app tem `audio|…|cena` / `|semcena`.
  - ⛔ **Nome com acento PERDIDO na própria bin** (MC 25.12 Mac, PRODUCAO-A, 2026-11-24): efeitos importados com nome
    UTF-8 ficaram gravados como o UTF-8 lido em outra codificação, e o caractere que não coube virou `?` — `PATÃO` →
    bytes `50 41 54 cc 3f 4f` (`PATÃ?O`, macroman) e `… c3 83 3f …` no campo UTF-8; `Flüssigkeiten` → `Flcc3f…`;
    `DopplerCar…ched` → `DopplerCar\x89??ched`. O MXF que o MC gerou tem o nome CERTO. Não há o que recuperar da bin:
    quem precisa do nome da origem usa o do MXF (quando a mídia gerenciada está à mão). Confiança: `confirmado` (bytes).
  - **Acento: o MC grava NFC**, no nome do mob (macroman, `ç` = `0x8D`, `ã` = `0x8B`) e no caminho (macroman e
    UTF-8 composto `c3 a7`), mesmo com o exFAT LISTANDO em NFD. ⛔ Um nome NFD não cabe no macroman (o cedilha solto
    `U+0327`): o clone de um WAV com acento caía e o áudio ficava offline. E o `replace_field` com texto codifica em
    latin-1 — nome de mob vai em macroman (`ç` latin-1 `0xE7` é outro caractere no macroman).


## 🆕 Markers da TIMELINE na bin — `confirmado` (leitura) 2026-11-15, MC (bin `03_OC_EDIT VALENDO.avb`, PRODUCAO-A)

Os markers de uma sequência NÃO ficam na trilha `DescriptiveMetadata` (na PRODA_CORTE.00.2 ela é um `Filler` só): ficam
nos SEGMENTOS, no atributo **`_TMP_CRM`** = lista de referências a objetos `TMBC` — o pyavb os lê como **`Marker`**
(a referência pode já vir resolvida como `Marker` ou como `AVBObjectRef`, `.value`). Cada `Marker`:
- `comp_offset` = quadros a partir do INÍCIO do segmento que o carrega (`position` 0; `mob_id` zerado);
- `color` = RGB de 16 bits (`[13107, 13107, 52428]` = Blue; `[0,0,0]` = Black) e, nos atributos, `_ATN_CRM_COLOR`
  (nome: Black, Blue…) e `_ATN_CRM_COLOR_EXTENDED`;
- atributos `_ATN_CRM_COM` (o comentário), `_ATN_CRM_USER`, `_ATN_CRM_DATE`/`_ATN_CRM_TIME`, `_ATN_CRM_LONG_CREATE_DATE`
  / `_LONG_MOD_DATE` (epoch), `_ATN_CRM_ID` (um UMID-like único por marker). Sem `_ATN_CRM_LENGTH` nos 23 desta
  sequência (são pontos; o span marker não foi visto).
- ⚠️ **ANINHADOS:** dos 23, só 4 estão em segmentos de cima (`SourceClip`/`Filler` da trilha). Os outros moram DENTRO de
  efeitos: `TrackEffect` → `Sequence` → `SourceClip` (a entrada do efeito; 6 na V1/V2), `PanVolumeEffect` → `SourceClip`
  e `AudioSuitePluginEffect` → `Sequence` → `MotionEffect` (13 no som, A6/A7/A9). A posição = o início do segmento de
  cima + a posição dentro da sequência aninhada + `comp_offset`. Quem só olha o nível de cima perde 19 de 23.

## 🆕 ⭐ O INPUT SIZING do Resolve no MC pela rota do Conformar — 2026-11-21 (`confirmado` pela imagem, MC 25.12.0 Mac × Resolve Studio 21.1)

O Sizing da página Color (`drt-drp/estruturas.md` §"O SIZING") vira o Motion na convenção do Resolve (escala relativa ao
encaixe; posição em milésimos — **X da largura, Y da ALTURA**, +Y para cima; `rot_z` = −Rotate do Color, que é horário;
flip) e passa pelo `_geo_premiere` da rota Premiere → Avid: Pan/Tilt → **PIP** (não cobre o quadro), Zoom/Width/Height →
**Resize**, Rotate/Flip/combinado → **3D Warp** (`EFF2_SBLEND`). Bin escrita e aberta pela rota (`SIZING MC 2027.prproj`
→ `SIZING RESOLVE_SEQ`), foto do monitor Record no meio de cada clipe × o still do Resolve (mapa medido 0,2370 px/px):
**os 10 casos (os 7 isolados, os 2 flips, Pan+Tilt+Zoom+Rotate) ≤ 3,8 px de 1920 nos cantos**, que é o piso da foto do
monitor (1 px do monitor de 455 = 4,2 px; o neutro dá 3,8). Prova inversa: contra o still ERRADO, 22–50 códigos de
diferença média (8–11 no certo, a cor do monitor). `laboratorio-de-midia/lab/bancadas/avid_sizing.py`.
- ⛔⛔ **`SetPosition` pela API TRAVOU o MC 25.12 (Mac)** — chamado pelo serviço do Ciclo Assist (`/nucleo/avid/chamar`)
  logo depois de a rota abrir a bin e pôr a sequência no Record: a chamada não voltou e o MC parou INTEIRO (API e
  interface, 0 % de CPU, uma janela só, nenhum diálogo); só fechando à força. A bancada `conferir_record.py` já o usou no
  25.12 sem isso (2026-10-25) — causa `pendente`. Contorno: a agulha anda por um CLIQUE na régua de TC (piloto), e o
  `GetViewerMobs` (só leitura) confere o quadro: 10 de 10 exatos.
- ⛔ **Pitch/Yaw do Resolve NÃO cabem no 3D Warp** (`confirmado`, mesmo dia, `lab/bancadas/avid_perspectiva.py`): o
  `DVE_ROT_X_U` / `DVE_ROT_Y_U` gira com perspectiva de CÂMERA; o Resolve aplica uma perspectiva LINEAR (`prproj/
  estruturas.md` §Pitch/Yaw → Corner Pin). Contra Pitch 0,2 / Yaw 0,2: X +12/+20/+30° → 186/135/130 px nos cantos;
  Y +12/+20° → 131/117 px; os negativos (sentido errado) 340–550 px. O melhor fica em ~120–130 px — o patamar do Basic
  3D do Premiere. Sem Corner Pin de série no MC: Pitch/Yaw vão como AVISO (ou o ângulo mais próximo, sabendo do erro).
  Sentido: X + = topo para trás (o Pitch + do Resolve); Y + = o lado esquerdo para a frente (o Yaw +).
- ⬜ Node/Output Sizing, keyframes.

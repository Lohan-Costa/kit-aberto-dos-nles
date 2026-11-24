# PRPROJ — Adobe Premiere Pro Project

Projeto do Premiere Pro. Container **`gzip(XML)`**; o XML é um **grafo plano de objetos**.

## Container e ferramentas

- **Container:** gzip de um XML. Descompactar para inspecionar:
  ```bash
  gunzip -c PROJETO.prproj > prproj_raw.xml
  ```
- **Raiz:** `<PremiereData Version="3">` (testado em Premiere Pro 2024/2025).
- **Escrita:** gerar o XML e recompactar com gzip. (Para escrita de transform/efeitos, o XML é
  binário/gzipado — engenharia reversa, ver [../../transversal/](../../transversal/).)

## Qual Premiere escreveu este arquivo (leia ANTES de aplicar qualquer descoberta)

O PRPROJ versiona **cada elemento** individualmente, e o Adobe muda essas versões entre releases
(`Sequence` era `Version="11"` no Premiere 2024/2025 e é `12` no 2026). Uma descoberta medida
numa versão pode não valer em outra — ver [CONVENCOES.md §1.1](../../CONVENCOES.md).

O arquivo diz quem o escreveu, dentro do objeto `Project`:

```xml
<MZ.BuildVersion.Created>22.6.4x2 - Tue Aug 26 22:23:44 2025</MZ.BuildVersion.Created>
<MZ.BuildVersion.Modified>26.0.2x2 - Thu Sep  3 10:24:14 2026</MZ.BuildVersion.Modified>
```

⚠️ O que vale é o **`Modified`** — um projeto criado em 2022 e salvo em 2026 está na forma do
2026. E **não confie em caminho de preset**: o `IngestSettings` deste mesmo arquivo apontava para
`/Applications/Adobe Premiere Pro 2025/…`, três anos fora de sincronia com quem o gravou.

| página | versão em que foi medida |
|---|---|
| [estruturas.md](estruturas.md), [escrita.md](escrita.md), [audio-adaptativo.md](audio-adaptativo.md) | Premiere Pro 2024/2025 (escrita validada no 25.6.5) |
| [relink-e-geometria.md](relink-e-geometria.md) | Premiere Pro **2026 (26.0.2)** |
| [relink-e-geometria.md](relink-e-geometria.md) §10 (leitura para o conform Premiere → Resolve) | Premiere Pro **26.0.2**, medido 2026-10-02/03 contra export e Resolve 21.1 |

## O grafo de objetos

Cada elemento XML é um nó de um grafo plano. Pode ter:

| atributo | papel | referenciado por |
|---|---|---|
| `ObjectID="N"` | id numérico local | `ObjectRef="N"` |
| `ObjectUID="uuid"` | id UUID global | `ObjectURef="uuid"` |
| `ClassID="uuid"` | **tipo** do objeto | — |

> ⚠️ Tracks dentro de um TrackGroup usam `ObjectURef` (UUID), **não** `ObjectRef` (numérico).

A tabela completa de `ClassID` está em [dados/classids.json](dados/classids.json) — é a peça que
mais economiza redescoberta.

## Tempo: ticks

Tudo (posição, duração, in/out) é medido em **ticks**: `254.016.000.000 ticks/segundo` (exato).
Constantes e fórmulas em [dados/ticks.json](dados/ticks.json) e
[../../transversal/tempo-e-timecode.md](../../transversal/tempo-e-timecode.md).

## Mapa das peças

| arquivo | conteúdo |
|---|---|
| [estruturas.md](estruturas.md) | `Media`, cadeia `SubClip → VideoClip → VideoMediaSource → Media`, Sequence, TrackGroups, ClipTrack, Link, MasterClip, merged clips, cálculo de posição |
| **[escrita.md](escrita.md)** ⚠️ | **As regras que o Premiere não perdoa.** Ler ANTES de escrever um builder. |
| **[relink-e-geometria.md](relink-e-geometria.md)** | **Editar** um PRPROJ pronto: semântica do `Motion > Scale`, `DefaultMotion`, relink de R3D→ProRes, `InPoint` base 0 |
| [audio-adaptativo.md](audio-adaptativo.md) | Canais adaptativos (crítico p/ sonorização), AudioClipTrack, Panner, SecondaryContent |
| [dados/classids.json](dados/classids.json) | Todos os ClassIDs |
| [dados/ticks.json](dados/ticks.json) | Sistema de tempo |
| [dados/type-guids.json](dados/type-guids.json) | GUIDs fixos de tipo, EditingMode, constantes |
| **[dados/geometria.json](dados/geometria.json)** | Params do Motion, fórmula de relink, campos de R3D |
| **[dados/regras-escrita.json](dados/regras-escrita.json)** | Regras de escrita + constantes de infra, consumíveis |
| [fontes.md](fontes.md) | Rastreabilidade |

## LER vs ESCREVER

[estruturas.md](estruturas.md) descreve o que se **lê** num PRPROJ — foi tudo derivado de um template
feito à mão no Premiere. Isso **não basta para escrever um**: as regras cuja violação faz o Premiere
crashar (`AR::AudioPrefetch`), despejar clipes em "Recovered Clips", ou abrir um projeto em que o
vídeo não é selecionável **não aparecem em template nenhum** — só quando você gera o arquivo do zero
e ele não abre. Elas estão em **[escrita.md](escrita.md)**, e cada uma custou uma sessão de bisecção.

## Apps que implementam / validaram

- **DRAMASYNC** — geração de Multicam Source Sequence (`src-python/prproj/`). Fonte primária;
  engenharia reversa completa em `docs/reverse-engineering/premiere-multicam-prproj.md`.
- **MULTCAM-PREMIERE** — guidelines/prompt do gerador de multicam Premiere.

## Conceito central: a cadeia de referência até o arquivo

```
VideoClipTrackItem → SubClip → VideoClip → VideoMediaSource → Media (RelativePath/FilePath)
```

Campos críticos do `Media`: `AlternateStart` (TC embutido em ticks, só em câmeras com TC),
`UseAlternateStart`, `FileKey` (UUID independente de caminho), `StreamNumber` (canal de áudio
multi-canal). Ver [estruturas.md](estruturas.md).

# AAF — Avid Advanced Authoring Format

Formato de intercâmbio de timeline do Avid Media Composer (também exportável por Resolve/Premiere,
com perdas). Container binário OLE/Structured-Storage; lê-se/escreve-se em Python com **pyaaf2**.

## Container e ferramentas

- **Container:** Structured Storage (COM/OLE), não é texto. Não dá para abrir como XML/zip.
- **Biblioteca de referência:** `pyaaf2` (Python). Abre `r` (leitura) e `rw`/`r+` (escrita).
  - Escrita confirmada: setar `loc['URLString'].value` e o `f.save()` ocorre no `__exit__`.
  - Patches necessários no pyaaf2 1.7.1 para AMA: bug do `MXFMPEG2VideoDescriptor.link` e
    ContainerDef "AAFKLV" (ver [escrita.md](escrita.md)).
- **Inspeção:** `RELINKER/docs/explore_aaf.py` dumpa a árvore de mobs.

## Mapa das peças (índice deste protocolo)

| arquivo | conteúdo |
|---|---|
| [estruturas.md](estruturas.md) | Cadeia de mobs, NestedScope (flat file), Selector/`reconstructed.N`, Group Clip, ScopeReference, FPS |
| [efeitos.md](efeitos.md) | OperationGroups, motion effect / rampa de velocidade, FrameFlex/SpatialAdapter, parâmetros geométricos (3D Warp) |
| [escrita.md](escrita.md) | Relink de URLString, AMA auto-link, preservação de estrutura |
| [dados/](dados/) | JSONs consumíveis: descriptors, operationdefs, appcodes, geometric-params |
| [fontes.md](fontes.md) | Rastreabilidade |

## A cadeia de resolução (o coração do AAF)

```
CompositionMob (timeline)
  → Sequence → SourceClip → MasterMob
    → Slot → SourceClip → SourceMob [CDCIDescriptor proxy]
      → Slot → SourceClip → SourceMob [ImportDescriptor original]
        → locator → URLString = "file:///path/to/CAM A.mxf"
```

Para **relink**, só se toca o `URLString` do `SourceMob [ImportDescriptor]`. Todo o resto
(Selectors, Group, efeitos) é preservado automaticamente. Detalhe em [estruturas.md](estruturas.md).

## Apps que implementam / validaram

- **RELINKER** — parser/writer mais completo (`src-python/aaf/parser.py`, `writer.py`); relink
  Avid→Avid, export DRT/OTIO, AMA auto-link, efeitos. Fonte primária deste protocolo.
- **FLATFILE-MULTCAM** — reconstrução de multicam a partir de flat file AAF.
- **BIN AVID**, **LEGENDA AVID**, **AAF-TOOL** (COMPARADOR AAF) — geração/comparação de AAF.

## Pontos de atenção recorrentes (armadilhas)

- **`start` dentro de Selector** é offset em `reconstructed.N`, **não** TC na mídia original —
  somar `selector.selected.start + slot_clip.start`. Ver [estruturas.md](estruturas.md) §Selector.
- **FPS** costuma ser `24000/1001` (23.976); ler de `slot.edit_rate` como Fraction.
- **URLString é percent-encoded** e UTF-16LE; usar `Path(...).as_uri()` para escrever.

## Quem escreveu este AAF

`Header.IdentificationList` — Avid / Adobe / Blackmagic, com versão e plataforma; e o pyaaf2 em `rw` **não** acrescenta a sua. Ver [transversal/assinatura-de-origem.md](../../transversal/assinatura-de-origem.md).

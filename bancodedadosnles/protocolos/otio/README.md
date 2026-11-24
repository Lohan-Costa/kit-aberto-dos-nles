# OTIO — OpenTimelineIO (intercâmbio aberto)

> **Stub a expandir.** OTIO é o formato **aberto** de intercâmbio de timeline. O Resolve importa
> nativo (free e Studio); serve de baseline e fallback entre NLEs.

## O que é

- JSON aberto de timeline. Biblioteca `opentimelineio` (Python) — única dependência nova para a
  saída OTIO do RELINKER.
- **Fidelidade limitada** em rampas/efeitos/keyframes (limitação do próprio OTIO/Resolve) → é o
  **baseline rápido**, não o premium. Para fidelidade alta usar DRT/DRP (ver [../drt-drp/](../drt-drp/)).

## O que o conversor padrão perde (e nós não)

O `otio-aaf-adapter` (usado pela maioria) **descarta**: velocidade fancy/rampa, parâmetros
animados (`VaryingValue`) e **não religa a mídia**. Confirmado no OTIO de referência: só
`LinearTimeWarp`/`TimeEffect` sobrevivem; os demais nós (Composite, Lens Correction, Retime,
Faders) são **defaults do Resolve**, não os efeitos do Avid. Por isso a tradução de efeitos é
**autoração nativa por destino**, não pass-through (ver [../../transversal/](../../transversal/)).

## Mapeamento (saída OTIO do RELINKER)
- Tracks V1/V2/A1…; clipe → referência externa ao original + `source_range`.
- Velocidade constante → time-warp linear (`1/speed_ratio`, exato).
- Rampa → metadata/bake (OTIO não tem curva nativa fiel).
- Multicam → ângulo selecionado + alternates em metadata.
- Transform/cor → metadata informativa do Resolve (não reproduzidos nativamente).

## Apps
- **RELINKER** — `export_otio` (sidecar), writer `otio/writer.py` (planejado/parcial). Fonte.

## Fontes
- `RELINKER/docs/resolve-otio-drp-roadmap.md`.

## Quem escreveu este OTIO

O Resolve marca os metadados com `Resolve_OTIO` (timeline e clipes); Premiere 2023 não exporta OTIO; Avid `pendente`. Ver [transversal/assinatura-de-origem.md](../../transversal/assinatura-de-origem.md).

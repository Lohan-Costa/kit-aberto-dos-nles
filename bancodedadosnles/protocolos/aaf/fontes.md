# AAF — Fontes e rastreabilidade

De onde veio cada bloco de descoberta deste protocolo.

| tema | app / arquivo de origem | amostra | confiança |
|---|---|---|---|
| Cadeia de mobs, NestedScope, Selector, Group Clip, descriptors, FPS | `RELINKER/docs/aaf-structures.md` | `SEQUENCIA COM FLATFILE.aaf` (Avid MC) | confirmado |
| Parser/writer de referência | `RELINKER/src-python/aaf/parser.py`, `writer.py` | — | confirmado |
| Motion effect / rampa de velocidade | `RELINKER/CLAUDE.md` (Phase 5), `docs/resolve-speed-ramp.md` | `AAF EFEITOS/SEQUENCIA COM EFEITOS.aaf` (rampa Timewarp 100→152→100) | confirmado (2026-06-08/13) |
| Parâmetros geométricos, OperationDefs, FrameFlex | `RELINKER/docs/effect-translation.md` | `MAPEAMENTO DE EFEITOS/`, `AVID DIFERENTES EFEITOS.aaf`, `FREMEFLEX/` | confirmado (2026-06-14) |
| AMA auto-link | `RELINKER/CLAUDE.md`, `docs/ama-autolink.md` | MC 2021, MXF 3-tracks | confirmado parcial |
| Geração de AAF do zero / multicam (clone+MobID, `_AAF_SELECTED`, container de ângulos) | `FLATFILE-MULTCAM/docs/aaf-reference.md`, `orientacao-flatfile-aaf.rtf` | `AAF COM MULTCAM/SEQUENCIA COM FLATFILE.aaf` (27 mobs, MC 2021) | confirmado (round-trip) → ver [geracao.md](geracao.md) |
| AMA enxerto de essência, patches pyaaf2, dropframe/Filler | `RELINKER/docs/ama-autolink.md`, `VALIDATION.md` | MC 2021 build 25.12 (2026-06-03) | confirmado → ver [escrita.md](escrita.md), [dados/ama-constantes.json](dados/ama-constantes.json) |
| Ponte de TC via original (relink com cor) | `RELINKER/docs/color-relink.md` | `TESTES DE TC E DIFERENCIACAO DE DRONES/` | confirmado (2026-06-14) → ver [../../transversal/tempo-e-timecode.md](../../transversal/tempo-e-timecode.md) |
| Precompute de efeito é MasterMob; chaves de nome do original; 5 formas de `URLString` | `LOCALIZADOR_DE_MIDIA_PELO_AAF/app/aaf_reader.py`, `CLAUDE.md` | `01 - telas fotoblog minidv.aaf` (PRODUCAO-Q — 178 mobs, 42 MasterMobs, 21 precomputes; MC 25.x) | confirmado (2026-08-17) → ver [estruturas.md](estruturas.md) §5b e [../../transversal/caminhos-e-storage-producao.md](../../transversal/caminhos-e-storage-producao.md) |
| Geração/comparação de AAF | `AAF-TOOL/APPS/COMPARADOR AAF`, `BIN AVID`, `LEGENDA AVID` | — | a revisar |
| Legenda SubCap por template, taxa do AAF, `AAFAttachError` no dual | `Legenda-Para-AAF/` v1.1.0 (GitHub `legenda-para-aaf`) | `BIN AVID/BIN ORIGINAL/TEMPLATE AAF.aaf`, `legenda teste/Sandra_EnglishSub_29052025.srt`; pyaaf2 1.7.1 | confirmado no pyaaf2 (2026-10-02); 24/29.97 no Avid **pendente** → [efeitos.md](efeitos.md) §3e |
| Inspeção | `RELINKER/docs/explore_aaf.py` | — | ferramenta |

## A integrar (próximas rodadas)
- `RELINKER/docs/effect-sampling-plan.md` — plano de amostragem (método; consolidar quando virar dicionário de efeitos).
- `AAF-TOOL`/`BIN AVID`/`LEGENDA AVID` — conferir se há estruturas de AAF complementares (legenda, comparação).
- 2026-09-27 — Reformat Stretch (`-1`) lido da bin nos 9 takes da praia da PRODA_CORTE.02 (mídia 2048×1080), pelo `_DeLaPraCa/motor/avb_bin/segmentos.py`; sinal "distorção" em `_DeLaPraCa/motor/notas.py` (`tests/test_notas.py` §2b e §5). confirmado.
- 2026-10-06 — pyaaf2: trocar `mob_id` re-chaveia `f.content.mobs` (escrita.md), de `SANITIZADOR_DE_AAF/CLAUDE.md`. Registrado pelo zelador do SSD ao arquivar.

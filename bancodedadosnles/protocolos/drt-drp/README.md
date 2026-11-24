# DRT / DRP — DaVinci Resolve Timeline / Project

Formato nativo do DaVinci Resolve. **Sem spec pública** — a BMD diz que muda entre versões e
recomenda usar scripting. Engenharia reversa pelo mesmo método do AAF (inspecionar + diffar
variantes mínimas).

## Container e ferramentas

- **Container:** `zip(XML)` com **partes binárias** (blobs `*BA`).
  - `.drt` = **uma timeline**. `.drp` = **projeto inteiro** (media pool + timelines + relink).
  - Estratégia: começar pelo DRT (menor); subir para DRP se precisar do bundle media-pool+relink.
- **Inspeção/escrita:** `RELINKER/tools/inspect_drp.py` (dumpa a árvore zip/XML e codifica/decodifica
  os blobs). Writer em `RELINKER/src-python/drp/writer.py`.
- **Dependência externa:** nenhuma para DRP (zip+XML manual). OTIO usa `opentimelineio` (ver [../otio/](../otio/)).

## Por que vale a pena (o diferencial)

O conversor padrão de AAF (`otio-aaf-adapter`) **descarta** velocidade fancy/rampa,
parâmetros animados (`VaryingValue`) e **não religa a mídia**. Como já temos o parser rico do AAF
(subclipes → arquivo original, multicam/Selector, offset map de velocidade, 3D Warp com keyframes,
transições, religação por URL/UMID), dá para escrever um DRT **melhor que o mercado**
(relink.co / CornerCut). Scripting externo do Resolve é **Studio-only** → descartado como base;
o DRT/DRP nativo faz o cliente "só abrir o arquivo".

## Mapa das peças

| arquivo | conteúdo |
|---|---|
| [estruturas.md](estruturas.md) | Blobs `MediaTimemapBA` (velocidade/rampa) e `EffectFiltersBA` (transform), tracks, relink, estado de implementação |
| [dados/timemap.json](dados/timemap.json) | Schema do `MediaTimemapBA` (curva de retime) |
| [dados/effectfiltersba.json](dados/effectfiltersba.json) | Layout binário do `EffectFiltersBA` (transform/crop/composite) |
| [dados/text-gerador.json](dados/text-gerador.json) | Título "Text" da página Edit (`Sm2TiGenerator` Rich): texto, fonte, corpo, cor, alinhamento, posição, contorno e caixa (2026-09-27) |
| [dados/marcadores-e-cores.json](dados/marcadores-e-cores.json) | Marcadores de timeline (nome, nota, palavras-chave, área) e cor do clipe LOCAL × GLOBAL: moram nos LockableBlob do `project.xml` (2026-09-27) |
| [magic-mask.md](magic-mask.md) | Magic Mask do Fusion: o que vai no DRT (traços + `CachePath`) e o que se perde (o tracking), com a trava na importação (2026-10-07) |
| [fontes.md](fontes.md) | Rastreabilidade |

## Estado da engenharia reversa (RELINKER)

- **Etapa 1 (validada no Resolve):** writer `drp/writer.py` — cortes + relink + TC (track V1) a 100%.
- **Etapa 2 (em curso):** velocidade (encoder do `MediaTimemapBA`); depois áudio + V2/V3 + geração
  do pool/project do zero.
- **Rampa de velocidade:** decodificada e validada (2026-06-13).
- **`EffectFiltersBA` (transform):** decodificado e escrito byte-exato, validado no Inspector (2026-06-14).

## Pré-requisito do usuário (destrava mais engenharia reversa)

Exportar do Resolve uma **matriz de exemplos mínimos** (cada um `.drt` **e** `.drp`, anotando a
**versão do Resolve**): cortes+mídia religada → +transição → +velocidade constante → +rampa →
multicam → (markers, transform com keyframes). Diffar as variantes isola onde cada recurso mora.

# PRPROJ — Layout do projeto multicam completo

A visão do **projeto inteiro** que um gerador de `.prproj` multicam produz (não só a Multicam
Source Sequence de [estruturas.md](estruturas.md)). Fonte: `MULTCAM-PREMIERE/GUIDELINE.md`.
Confiança `inferido` (estrutura-alvo replicada de projeto de referência feito à mão).

## Caso de uso (mesmo do flat file de estúdio)

Recebe `FLATFILE.mxf` (saída do switcher, cortes já feitos) + `CAM A/B/…mxf` (ISOs) +
`SOM-DIRETO.wav`, e gera um `.prproj` com a edição **já pronta** — o flat file serve de referência
na V1; o resultado visível são as ISOs cortadas nos momentos certos. Detecção de cortes + match
visual (qual ISO == frame do flat file no mesmo TC) → lista de eventos. Mesmo princípio do
[../aaf/geracao.md](../aaf/geracao.md), mas saída Premiere.

## Estrutura do projeto

```
Bin "CENA 04"
├── Sub-bin "SUBCLIPES"   → merged clips:  "CAM A.mxf - Merge", "CAM B.mxf - Merge", …
└── Sub-bin "FLAT - ISOS" → raw:           FLATFILE.mxf, CAM A.mxf, CAM B.mxf, SOM-DIRETO.wav
```

### Merged clips (câmera ISO + som direto emparelhados)
Cada câmera vira uma `Sequence` com `BE.Sequence.IsMergedClip=true` (ver [estruturas.md](estruturas.md)
§6). Nome `"arquivo.mov - Merged"`/`"- Merge"`. ISOs e flat file compartilham o mesmo TC source
(fluxo padrão de switcher), o que dá o sync.

### Sequência multicam (`CENA 04 MULTCAM`)
- **V1** → FLATFILE (referência)
- **V2** → CAM A merged
- **V3** → CAM B merged
- (V4, V5, … por câmera)
- **A1** → som direto (com canais adaptativos — ver [audio-adaptativo.md](audio-adaptativo.md))

### Sequência de edição (`CENA 04 EDIT`)
- **V1** → instâncias da multicam, com a **câmera ativa correta em cada trecho** (conforme a lista
  de cortes detectada no flat file).
- **A1** → som direto.

> O DRAMASYNC gera **só a Multicam Source Sequence**; a sequência de edição (`EDIT`) é o passo
> adicional do MULTCAM-PREMIERE (refaz os cortes do switcher automaticamente). A sequência de
> edição usa a multicam aninhada como fonte.

## Premissas técnicas
- `.prproj = gzip(xml)`; geração puramente programática (não exige Premiere instalado).
- ISOs e flat file compartilham o mesmo TC source.
- Geração de projeto vazio validada em 2026-05-10 (POC anterior).
- Alvo: Premiere Pro 2025.

## Pendência
- Validar round-trip da geração completa (bins + merged + multicam + edit) abrindo no Premiere.
  Quando validado, promover de `inferido` para `confirmado`.

## O XML da mesa como mapa de cortes (`xmeml` v4), FLATFILE-MULTCAM, 2026-09 — `inferido`

Última rodada do `FLATFILE-MULTCAM` (protegida no ramo `antes-da-arrumacao` em 2026-10-06; código
em `src/multicam_rebuild/cutmap/`): em vez de classificar o flat file frame a frame, ler o corte do
XML que o Premiere exporta simulando a mesa (`xmeml version="4"`, FCP7 legado; amostra
`MATERIAL DE TESTE/XML EXEMPLO/SEQ-EDITADA.xml`). Cada `clipitem` da trilha de vídeo dá
`start`/`end`/`in`/`out` e o `file` (nome + `timecode/string` + `frame`); o ângulo é o arquivo.
⚠️ **`<file id="…">` só vem completo na PRIMEIRA aparição**; as repetições são uma tag vazia
`<file id="file-1"/>` que remete à definição anterior pelo `id` — quem ler cada `clipitem` isolado
perde nome e timecode a partir do segundo uso da mesma câmera. Lido de 1 amostra, sem ida-e-volta
num NLE.

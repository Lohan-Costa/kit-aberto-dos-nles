# AAF — Geração de timeline do zero (que abre no MC 2021)

Como **gerar** um AAF de timeline (multicam ou cortes) que o Media Composer 2021 aceita e
relinca. Diferente de [escrita.md](escrita.md) (que modifica um AAF existente). Fonte:
`FLATFILE-MULTCAM` (reconstrução de multicam a partir de flat file). Confiança `confirmado`
(round-trip no MC 2021), salvo onde indicado.

## Princípio: clonar a referência, não recriar o grafo de mobs

O **relink do Avid se ancora no MobID do MasterMob**. Recriar source/master mobs do zero arrisca
quebrar o relink. Estratégia validada:

1. **Clonar** um AAF de referência real (exportado pelo próprio Avid a partir das mesmas MXF).
2. **Remover apenas o CompositionMob de topo** (a timeline).
3. **Criar um novo CompositionMob de topo** cujo slot de Picture é uma `Sequence` de
   `SourceClip`s (cortes) ou `Selector`s (multicam) — cada um apontando, **por MobID**, para o
   MasterMob da câmera, com `start`/`length` da timeline reconstruída.
4. Slot de Sound: `SourceClip` para o MasterMob do áudio principal (ex.: `SOM-DIRETO.wav`).
5. Slot de Timecode: `Timecode` com o start correto (ex.: `86400 @ 24` = `01:00:00:00`).

Reaproveitar os mobs de origem garante o relink; só a edição (o CompositionMob de topo) é autoral.
**Validar com round-trip** (regenerar e reabrir no Avid) antes de confiar.

## O grafo de mobs de referência (exemplo: 27 mobs)

```
CompositionMob  Usage_TopLevel   "SEQUENCIA....Exported.01"   ← a timeline (descartável/autoral)
CompositionMob  Usage_LowerLevel "FLATFILE.Grp.01"            ← o group clip (AppCode=4)
CompositionMob  (sem nome)                                    ← container de ângulos
MasterMob       "FLATFILE"/"CAM A"/"CAM B"/"SOM-DIRETO.wav"   ← âncoras de relink (MobID)
SourceMob       ImportDescriptor   (por mídia)                ← fonte importada
SourceMob       CDCIDescriptor (vídeo) / PCMDescriptor (áudio)← essência física
```

Cadeia de um clipe (o relink se ancora no MobID do MasterMob):
```
CompositionMob.slot → Sequence → SourceClip --(mob_id)--> MasterMob
MasterMob.slot      → Sequence → SourceClip --(mob_id)--> SourceMob (essência)
SourceMob.slot      → SourceClip            --(mob_id)--> SourceMob (import)
```

Cada MasterMob de câmera costuma ter 1 slot Picture (slot 2) e 4 de Sound (3–6); o MasterMob de
áudio puro (`.wav`) tem 1 slot Sound (slot 1).

## Geração de multicam (Selector)

O track de vídeo é uma `Sequence` de `Selector`s, um por plano:

```
Sequence[ Selector(Length, Selected, Alternates), ... ]
```

Cada `Selector`:
- `Selected` — `SourceClip` para o slot do **container de ângulos** da câmera ativa no plano.
- `Alternates` — `SourceClip`s para os demais ângulos.
- `Length` — duração do plano.
- `ComponentAttributeList` — `TaggedValue` **`_AAF_SELECTED`** com o índice canônico do ângulo
  (privado do Avid; o ângulo exibido é governado por `Selected`).

O **container de ângulos** é uma `CompositionMob` (sem nome) cujos slots de vídeo, em ordem de
`slot_id`, são os ângulos do group:

| slot_id | câmera | índice canônico (`_AAF_SELECTED`) |
|---|---|---|
| 1 | FLATFILE | 0 |
| 6 | CAM B | 1 |
| 8 | CAM A | 2 |

O group `FLATFILE.Grp.01` (`Usage_LowerLevel`, AppCode=4) e a timeline ambos referenciam esse
container. Regra do writer: **havendo group → gera multicam; não havendo → gera cortes simples**
para os MasterMobs.

## Contexto de workflow (flat file de estúdio)

O caso de uso do FLATFILE-MULTCAM (premissas que simplificam a reconstrução):
- Mesa de corte gera um **flat file** com os cortes já impressos; **sem EDL/XML/AAF**.
- Todas as câmeras **iniciam e terminam juntas**; flat file e ISOs têm **a mesma duração**.
- Sem pausas de REC, sem segmentação, **só cortes secos** (hard cuts), sem dissolves.
- Áudio das câmeras é **scratch/guia**; o áudio principal é o `SOM-DIRETO.wav` externo.
- Reconstrução = detectar cortes no flat file + match visual (qual ISO == frame do flat file no
  mesmo TC) → lista de eventos → gerar o AAF multicam.

## Pendências
- O AAF de referência é um **group clip** cobrindo toda a duração (não uma edição com cortes) —
  serve de gabarito de estrutura e fonte de MobIDs, **não** de cortes.
- Validar round-trip de cada variante (cortes vs multicam) no MC 2021.

# Detecção de corte, dissolve e fade — onde um plano começa e termina

> **Medido em 2026-09-22**, Windows 11, ffmpeg + numpy, no Ciclo Assist
> (`_CICLO ASSIST/spikes/onde_estao_os_cortes.py`). Material: *PRODUCAO-A* (Blackmagic 4K
> convertido para 1080p 23,976) e uma peça montada de promo esportiva (1080p 29,97, 60 s).
> Confiança: `confirmado` nos gabaritos exatos; `inferido` na peça montada (conferida no olho).

A peça de que qualquer decupagem "por plano" depende. Existe uma receita anterior da casa
(`_PRODUCAO-V/decupador de material bruto/decupador/planos.py`, 2026-08-09, novela): `scdet`
limiar 8 + SigLIP confirmando (0,93) + refino de planos longos por dissolve (0,88).

## Os gabaritos, e por que são exatos e de graça

1. **Sintético de material real:** 13 trechos de takes diferentes, emendados por corte seco
   (`concat`) e `xfade` (`fade` = dissolve, `fadeblack` = fade) de 6 a 48 quadros. A verdade é
   a conta das durações. ⚠️ Três armadilhas medidas para o gabarito não mentir:
   - `-t 5` a 23,976 dá 119 **ou** 120 quadros por trecho: a verdade derivava até 3
     quadros. Cortar por QUADRO (`trim=end_frame=N`) e contar em quadros inteiros.
   - `xfade` de UM quadro arredonda para duração zero e a cadeia **para** ali, sem erro (o
     arquivo saiu com 120 quadros). Corte seco é `concat`, seguido de `fps=` para devolver a
     base de tempo que o `xfade` seguinte exige.
   - `settb`/`setpts` depois de `fps` apagam a taxa ("constant frame rate 1/0 invalid").
2. **Um take contínuo de câmera:** um arquivo original é UMA gravação — verdade = zero cortes,
   e toda detecção é falso positivo. Mede a PRECISÃO, que peça montada mede mal.
3. **Calibrar e reportar em conjuntos diferentes** (outros 13 takes, outra ordem de junções).

## Os números

| detector | sintético (12) | validação (12) | contínuo (3 min) | peça montada (~65, no olho) |
|---|---|---|---|---|
| A · `scdet` limiar 8 (receita PRODUCAO-V) | 4 · 0 FP | 7 · 0 FP | 0 FP | **~59** · ~7 FP |
| B · pixel 64×36 (abaixo) | 11 · 1 FP | **12** · 2 FP | 0 FP | ~40 · ~3 FP |
| C · B + MobileNet como árbitro | 10 · 1 FP | 12 · 2 FP | 0 FP | — |
| ⭐ **D · A ∪ B** (cortes dos dois, graduais só de B) | 11 · 1 FP | **12** · 2 FP | **0 FP** | ~65 · ~10 FP |

- ⛔ **O `scdet` é cego a dissolve e fade:** 0 de 5 transições graduais na validação (6 a 48
  quadros). Confirma o que o PRODUCAO-V já tinha visto em novela ("dissolve desliza por baixo do
  limiar") e o que se esperava do código (`min(mafd, |Δmafd|)`).
- ⛔ **O pixel perde corte em material rápido:** o teste de "pico isolado" (d1 ≥ 3× os
  vizinhos) falha quando os vizinhos também mudam muito — promo esportiva com movimento e
  grafismo. No drama, perdeu só o corte INVISÍVEL.
- ⭐ **Cada um vê o que o outro não vê** ⇒ a união. Para decupagem, perder corte é o erro caro
  (a nota mistura dois planos); sobrar é barato (uma nota a mais).
- ⛔ **MobileNetV2 não serve de árbitro:** é semântico (logits do ImageNet) — derrubou um corte
  real entre dois takes do mesmo cenário, e não separa oclusão de dissolve (falsos 0,60–0,84,
  verdadeiros até 0,71). O PRODUCAO-V usava SigLIP, que não roda em notebook com o Media Composer
  aberto (ver `CLAUDE.md` do Ciclo Assist).
- Erro de posição dos cortes: **0 quadro** (um −1 atribuível ao gerador).
- Custo: a passada de pixel é decode-bound — 1,3 s para 60 s de 1080p; 4,2 s para 3 min.

## O detector de pixel (B), para reproduzir

`ffmpeg -i X -map 0:v:0 -an -vf "scale=64:36:flags=area,format=rgb24" -fps_mode passthrough
-f rawvideo -` → numpy. ⭐ O downscale **é** o filtro de grão (média de blocos de 30×30).

- `d1[t]` = média |F(t) − F(t−1)|; `dz` = o mesmo sobre a luma z-normalizada (imune a luz).
- **Corte:** `d1` > 3× o maior vizinho (±3), > limiar adaptativo (mediana + 8·1,4826·MAD
  numa janela de ±24, piso 0,015) e `dz` > 0,2. Medido: cortes 0,037–0,305 contra ruído de
  mediana 0,0009 (p90 0,0054) — o que separa é o ISOLAMENTO, não o tamanho.
- **Gradual:** em meias-janelas k = 6, 12, 24 (com k=6 só, o dissolve de 48 passou):
  `D = |F(t+k) − F(t−k)|` > 0,08 e linearidade `λ = D / Σd1` > 0,6 (dissolve anda em linha
  reta; movimento serpenteia), sem corte a menos de k. Fade = desvio da luma < 0,02 no meio.

## Os erros que sobram, e o que eles são

- **Corte invisível:** dois takes seguidos do MESMO plano (mesma câmera e enquadramento)
  emendados — `d1` 0,004, o nível do ruído. Nenhum detector de imagem acha, e para decupagem
  é inofensivo (os dois lados mostram o mesmo).
- **Oclusão:** alguém passa na frente da câmera, ou cobre a lente — sai como "gradual" dentro
  do plano. Conservador: parte um plano em dois.
- **Grafismo:** texto entrando sobre a mesma imagem sai como corte do `scdet`.
- `pendente`: a sequência montada com gabarito exportado do `.avb`; wipe/push; dissolve entre
  planos muito parecidos; 29,97 drop-frame.

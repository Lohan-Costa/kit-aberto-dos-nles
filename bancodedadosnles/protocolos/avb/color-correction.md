# Color Correction do Media Composer: como a bin guarda e o que cada controle faz ao pixel

> **Medido em:** Media Composer **24.6** (`rel.MC2024.6_R58520`), Windows 11, projeto 1080p/23.976, 2026-11-20.
> Impressão digital do efeito: `effect_id = EFF2_RGB_COLOR_CORRECTION`, atributos `_EFFECT_PLUGIN_TYPE AVX2`,
> `_EFFECT_PLUGIN_VERSION 1.0`, parâmetro `MC AVX2 EFFECT VERSION = 1`.
> Método: laboratório de mídia, caso **B24_COR_MC** (carta sintética, um segmento por valor de controle, efeito
> ESCRITO na bin pelo pyavb, render pelo `ExportFile`, medição do Y'CbCr no miolo de 103 áreas). Bancada
> `laboratorio-de-midia/lab/bancadas/avid_cor.py`, modelo `lab/cor_b24_modelo.py`, números em
> `laboratorio-de-midia/resultados/B24_COR_MC/MC.md`.

## 0. No AAF exportado (`confirmado`, 2026-11-20, AAF da PRODA_CORTE exportado pelo MC, 7 CC)

- O CC viaja INTEIRO: `OperationGroup` com `OperationDef` **`RGBColorCorrect_2`**, `AvidEffectID` `EFF2_RGB_COLOR_CORRECTION`,
  e os MESMOS parâmetros da bin, pelo nome do `ParameterDef` (`Mas Sat` em `AAFRational` — 87,5 = 175/2 —, as bandeiras
  `HSL … Bypass`/`Curves … Bypass` = 1, `Num Master Curve Keys`, `Curves Master`). Só o que saiu do padrão, como na bin.
- `Curves Master` no AAF = o blob **AVUP** inteiro (`PUVA` + tamanho + `II` + `01000000` + `II` + uuid `e1c94795…` +
  size1 260 + size2 256, e os 256 bytes de dados no offset 40) — os mesmos 16 pares (x, y) em double da bin.
- ⇒ Quem conforma pelo AAF não precisa da bin para levar a cor. Usado em `modulos/conformar/motor/drp/cor_mc.py` do
  Ciclo Assist: Sat + curva Master → 2 nós no Resolve 19.1.4 por `.drx` (a PRODA inteira: 7 de 7 aplicados, nós "MC
  Master" → "MC Curva", a curva desenhada na paleta Custom sem queda). Outro controle mexido ou keyframe = não vai.

## 1. Na bin

- `TrackEffect` com `effect_id EFF2_RGB_COLOR_CORRECTION`, UMA trilha cuja `component` é uma `Sequence` com o clipe.
  `precomputed` = o render (SourceClip para mídia de render); `None` = o MC renderiza de novo. (`confirmado`)
- Os parâmetros são `ParameterItem` com **UUID e `name` vazio**; o nome vem do dicionário do pyavb
  (`avb.parameter_uuids.PARAMETER_UUIDS`: `296caabb…` = "Mas Sat", `5ff50344…` = "Mas Gain"…). **Só o que saiu do
  padrão é gravado.** Número = `value_type 2` (float/int), bandeira = `value_type 1`, curva = `value_type 4`
  (`CFUserParam`, blob). (`confirmado`)
- O CC real sempre traz: `MC AVX2 EFFECT VERSION` (1), `Relationship Type` (11), `Modification Date` (epoch).
- ⛔⛔ **As TRÊS bandeiras do HSL** — `HSL Bypass`, `HSL Setup Bypass`, `HSL Setup Master Bypass`, todas `value 1`,
  `enable False` — **têm de estar presentes, senão o MC ignora o efeito inteiro** (o Sat 0 sai idêntico ao
  original). Tirar qualquer uma das três basta para desligar. Apesar do nome, "presente com valor 1 e enable falso" é
  o estado de quem MEXEU no HSL. (`confirmado`, 6 variantes, uma por vez)
  ⇒ Ler: um CC com o HSL ligado tem essas bandeiras; escrever: copiá-las junto com o parâmetro.
  `pendente`: as bandeiras de Highlights/Midtones/Shadows, Levels e Curves (o CC real da PRODA tem
  `Curves Bypass`/`Curves Master Bypass` com o mesmo padrão + `Num Master Curve Keys` + `Curves Master` em blob).
- Unidades = as do Effect Editor (`effect_editor/catalogo.json` do lab): Sat e Gain em % (padrão 100), Gamma 1,0, os
  demais 0. O CC da PRODA_CORTE grava `Mas Sat 87.5`. (`confirmado` pela medição: os valores escritos nessas unidades
  dão as contas abaixo)

## 2. A conta do Base HSL › Master (`confirmado`, erro médio ≤ 0,4 código de 8 bits)

Tudo em **Y'CbCr de 8 bits** (preto 16, branco 235, croma centrado em 128), BT.709. O resultado é cortado em
**0–255** no fim — nem em RGB, nem em 16–235 (Brt +50 levou o branco a 255 e o preto do Brt −50 a 0; Contrast +50
calculado SEM corte intermediário bate com o medido).

| controle | conta | erro (médio / máx, códigos) |
|---|---|---|
| **Saturation** S (%) | Y igual; Cb, Cr = 128 + (C−128)·S/100 | 0,24 / 0,5 |
| **Hue** H (°) | Y igual; (Cb−128, Cr−128) girado de **−H** graus (Hue +90 leva (−16, 72) a (72, 16)) | 0,24 / 0,55 |
| **Brightness** B | Y + **1,18**·B; croma igual | 0,6 / 0,6 em ±20; 0 em ±50 |
| **Setup** U | Y + **1,00**·U; croma igual | 0 / 0 |
| **Gain** G (%) | Y = 16 + (Y−16)·G/100; croma ×G/100 (pivô no PRETO) | 0,37 / 0,5 |
| **Contrast** C | inclinação s = **tan(45°·(1 + C/100))**; Y = 127 + (Y−127)·s; croma ×s | 0,33 / 0,54 |
| **Gamma** γ | **por canal R'G'B'** (vídeo 16–235): c' = 16 + 219·((c−16)/219)^(1/γ), e volta a Y'CbCr — por isso o croma ENCOLHE nos dois sentidos | 0,41 / 2,26 (γ 2,0, perto do preto) |

- Contrast, Gain e Brightness são lineares: aplicar em Y'CbCr ou em R'G'B' dá o mesmo. Sat e Hue são em CbCr (a
  saturação a 200 % corta o Cr em 255 com o Y intacto).
- `hipotese`: o 1,18 do Brightness (±0,01; +20 → +23 e −20 → −24, assimetria de arredondamento) e o pivô 127.
- `pendente`: os `… Src` (`Mas Sat Src`…);
  as faixas de cada controle; Highlights/Midtones/Shadows (como o MC separa as luzes), Hue Offsets, Levels, as curvas R/G/B
  (o mesmo blob, a medir) e Secondary.
- O render medido é DNxHD 8 bits (o do projeto): a precisão fica em ~0,5 código.

## 2b. A curva Master (Curves › Master) — `confirmado`, mesma tarde

- **Na bin:** `Curves Master` (`b4e310c6…`, `value_type 4`) = `CFUserParam` (uuid interno `e1c94795-a4eb-46a0-8132-
  9085c235079a`, `byte_order 18761` = "II") com **256 bytes = 16 pares (x, y) em double little-endian**; valem os
  primeiros `Num Master Curve Keys` (`21b4bd95…`, `value_type 1`, enable falso) — o resto pode ter sobra de pontos
  apagados (visto (766, 766) repetido). Escala: **256 = 0 e 766 = 1** (a curva neutra vai de (256, 256) a (766, 766)).
  Junto vão `Curves Bypass` e `Curves Master Bypass` (valor 1, enable falso) — o mesmo padrão das bandeiras do HSL.
  Escrever um blob com pontos conhecidos e o número de pontos funciona (12 curvas escritas pelo pyavb, todas
  renderizadas).
- **A conta:** a curva age em **cada canal R'G'B'**, no domínio do **código inteiro** (t = código/255 — não 16–235:
  com o branco da curva a 0,5, o 30 vira 15 e o 218 vira 109), é **plana fora das pontas** (pontas a 0,25/0,75 levam o
  resto a 0 e 255) e é interpolada por **Catmull-Rom** (tangente = secante dos vizinhos; nas pontas, a do segmento).
  Degradê de 7 curvas de 3–4 pontos: Catmull-Rom 0,37 código de erro médio (máx ≤ 3), contra 5,8 linear, 9,4 spline
  natural e 2,7 PCHIP. Nas 103 áreas, 0,4–0,6; as 2 curvas reais da PRODA_CORTE, 0,46 e 0,41 (pior < 1). A curva
  pode passar do ponto (não é monótona): a não monótona testada bateu com a mesma Catmull-Rom.

## 2c. A ordem (`confirmado` onde as contas são lineares)

- **HSL → Curvas**: o CC real da PRODA (Sat 87,5 + curva) dá 0,43 nessa ordem e 0,92 na inversa; Sat 200 + curva,
  0,63 contra 7,4; Gamma + curva, 0,53 contra 12,9.
- Dentro do Master: **Gain e Contrast antes de Brightness e Setup; Setup e Brightness antes do Gamma**; Gain antes
  do Gamma (bate onde a imagem fica abaixo do branco: 159 → 233 medido e previsto).
- `pendente`: Gamma junto de Gain ou Contrast com a imagem PERTO ou ACIMA do branco — resíduo de 4–5 códigos que
  nenhuma regra simples (cortar, potência, identidade fora de 16–235) explica (Gain 150 + Gamma 2 leva o 171 a 255; a
  conta dá 241,6). E Gain 80 + Contrast 50: a inclinação é o produto (1,93), mas o pivô sai ~119 em vez de 127.

## 4. Levar ao Resolve, EDITÁVEL — `confirmado` na carta (Resolve Studio 19.1.4, Windows, 2026-11-20)

Lab `resultados/B24_COR_MC/RESOLVE.md`, bancada `lab/bancadas/resolve_cor.py` (grade montada → `.drx` →
`ApplyGradeFromDRX`, render e a mesma medição). Erros DENTRO da faixa 16–235 (média / máx, códigos de 8 bits):

- **Sat S %** → Saturation do nó (`0x06000005`) = **S/100**: 0,09 / 0,25 a 87,5; ≤ 0,52 / 3 de 0 a 200.
- **Curva Master** → curva **Custom R/G/B** com a MESMA lista e **Lum Mix 0** (`0x8600000B`; sem ela as curvas R/G/B
  preservam a luma). A Catmull-Rom do MC (t = código/255) vira Bézier por trechos SEM perda: a troca para o eixo do
  Resolve é afim (t = (16 + 219·(0,00649 + 1,01792·u))/255, o eixo da curva Custom de `drt-drp/estruturas.md`). 0,25–0,75.
- **A ordem HSL → Curvas = DOIS NÓS em série** ("MC Master" → "MC Curva"): num nó só o Resolve faz a curva antes da
  Sat. O CC real da PRODA (Sat 87,5 + curva): **0,29 / 1,26 e 0,45 / 1,19**.
- ⛔ **Não vai igual:** o Resolve (render de faixa de vídeo) **corta cada canal R'G'B' em 16–235**; o MC guarda
  super-branco e sub-preto até cortar o Y'CbCr em 0–255 (curva 0,5→0,75: branco 246,6 no MC, 235 no Resolve; o preto
  da PRODA 1: 8,8 contra 16). `pendente`: se é o render (reter sub-preto/super-branco) ou o nó.
- `pendente`: Hue, Gain, Brightness, Setup, Contrast, Gamma no Resolve. Gain/Contrast/Brightness/Setup são AFINS e
  iguais nos 3 canais R'G'B' — dá para dobrá-los dentro da própria curva (continua exata); Gamma e Hue, a medir (ou LUT).

## 5. Levar ao Premiere, EDITÁVEL — `confirmado` na carta (Premiere 26.5.2, Windows, 2026-11-20)

Lab `resultados/B24_COR_MC/PREMIERE.md`, bancada `lab/bancadas/premiere_cor_mc.py`. O CC real da PRODA: **0,45 / 1,46 e
0,54 / 2,57** dentro de 16–235.

- **Sat S** → **ProcAmp › Saturation = S**, ANTES da Lumetri. O ProcAmp preserva o Y' BT.601 em gama (o MC, o BT.709):
  a 87,5 erra 0,46 / 2,75. A **Saturation da Lumetri NÃO serve** (preserva a luminância LINEAR: 2,8 / 27,5 a 87,5).
- **Curva Master** → a MESMA curva nos canais **R, G e B** da Lumetri (a mestra neutra). Eixo da Lumetri = faixa de
  vídeo (u = (código − 16)/219), **spline natural**, plana fora: a Catmull-Rom vai por pontos a mais (≤ 0,25 no papel).
  ⛔ A curva MESTRA da Lumetri preserva o matiz (o canal do meio é interpolado entre os outros dois em luz ~linear) —
  nela a PRODA 1 erra 3,03; nos canais, 0,20.
- ⛔ O corte em 16–235 também acontece aqui (export ProRes).
- ✅ **Premiere 2027 (27.0.0, 2026-11-20): a MESMA tradução sai idêntica byte a byte** ao 26.5.2. Nenhum efeito novo do
  27 dá a Sat BT.709 do MC (Color Mixer em YCbCr = 601 como o ProcAmp; Color And Contrast, pior) ⇒ ProcAmp continua
  (existe do 23 ao 27). A página Color nova (`prproj/estruturas.md` §Premiere 2027) é outro destino possível — decisão
  do autor.
- `pendente`: Hue (ProcAmp gira ao contrário e sobra 5,7), Brightness/Contrast do ProcAmp têm outra escala e pivô;
  Gain/Brt/Setup/Contrast do MC dá para dobrar na curva (afins, iguais nos 3 canais); Gamma.

## 3. Armadilhas achadas no caminho

- ⛔ O import padrão (`ImportFile`, setting "Untitled") de um ProRes 422 HQ com faixa de VÍDEO **comprimiu os
  níveis**: Y 16 → 30 e 235 → 218, exatamente 16 + Y·219/255 (tratou o arquivo como RGB cheio). Medir sempre contra a
  mídia IMPORTADA, nunca contra o arquivo de origem. (`confirmado`, MC 24.6)
- ⚠️ Na 1ª tentativa o master apareceu na bin, transcodificou e SUMIU ("Bin is empty"), sem nada no EVENTLOG.
  Diferenças da 2ª (que deu certo): sem `destination_video_drive`/`destination_audio_drive` e sem `GetListOfBinItems`
  durante a transcodificação. Causa: `pendente` (uma das duas).
- O `ExportFile` com o preset do lab "usando a compressão da fonte" RENDERIZA o CC (o CC real da PRODA clareou a
  carta). A medição pode sair do export, sem clicar em Render.

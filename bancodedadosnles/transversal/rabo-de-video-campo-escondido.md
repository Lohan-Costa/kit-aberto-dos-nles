# Rabo de vídeo: achar campo escondido em material entrelaçado 29i

> **Confiança:** `confirmado` contra verdade-terreno de 2 positivos e 2 negativos.
> **Medido:** 2026-08-21, Promo Entrega, Windows 11, Media Composer 2025.6.58781.
> **Amostra:** `SEQ COM RABO DE VIDEO` (bin `BENDITO FIELD Bin.avb`), XDCAM HD422
> 1920×1080 29,97i TFF, com os rabos apontados à mão pelo editor.

## O defeito

Numa timeline 29i o Media Composer reproduz **só o campo superior**. Se um corte cai num
frame cujo campo **inferior** pertence a outra imagem, o editor não vê nada no player — e
a peça volta **reprovada da avaliação técnica**, depois de entregue. É um defeito que só
aparece fora da mão de quem editou.

## ⭐⭐ A virada: a timeline é o mapa de cortes

A tentativa anterior da casa (um app de navegador com ffmpeg.wasm) varria o arquivo
**inteiro, frame a frame**, sem saber onde estavam os cortes. Afogava em falso positivo —
cena rápida, flash e transição disparam a mesma métrica. **Medido: 48 marcações em 1456
frames**, e o autor registrou no próprio produto que a lista não era confiável.

Estando **dentro do NLE**, a lista de edição responde onde estão os cortes. Aí só o
**último frame antes de cada corte** precisa ser lido:

- na amostra, **4 frames em vez de 354**;
- os dois rabos saem, **sem nenhum falso positivo**;
- 1,6 s de ponta a ponta, incluindo ler a bin e resolver a mídia.

⭐ **É o frame de SAÍDA, nunca o de entrada.** Regra do editor: o frame à direita do corte
é campo superior e é monitorado — o editor o vê. O rabo esconde-se no que sai.

⚠️ **A trilha que vale é a VISÍVEL em cada ponto**, não a V1 por definição: o defeito
reprova porque aparece na imagem final. Corte da V1 coberto por inserto na V2 não chega à
entrega; corte da V2 chega.

## A métrica

```
separatefields , tblend=all_mode=difference , signalstats  →  YAVG
```

`separatefields` é separação **autoritativa**: cada campo vira uma imagem de meia altura
só com as linhas daquele campo. Os índices **pares** da série resultante são a diferença
entre o campo superior e o inferior **do mesmo frame**; os ímpares atravessam frames.

⚠️ **Ordem:** `separatefields` primeiro, escala só depois. Escalar antes mistura os campos
de volta, em silêncio.

### ⛔ A métrica "óbvia" está errada

A v1 comparava cada linha com a linha **verticalmente adjacente** (`|linha par − linha
ímpar|`) e chamava isso de diferença entre campos. **Não é**: é energia vertical da
imagem. Texto, grades, cabelo e qualquer detalhe fino inflam essa conta exatamente como um
rabo inflaria.

## Os dois portões, e por que nenhum serve sozinho

```
acusa  ⇔  valor ≥ 15,0  E  valor / mediana_local ≥ 2,5
         (mediana dos ±4 frames vizinhos, excluindo o próprio)
```

| corte | verdade | no corte | base local | razão |
|---|---|---|---|---|
| 01:00:01:12 | **RABO** | 43,6 | 14,2 | **3,1×** |
| 01:00:02:29 | limpo | 4,4 | 2,0 | 2,2× |
| 01:00:03:20 | **RABO** | 36,5 | 8,3 | **4,4×** |
| 01:00:05:07 | limpo | 13,2 | 12,9 | 1,0× |

- **A razão sozinha** marca o `01:00:02:29`: numa cena parada (base 2,0) qualquer coisinha
  é muitas vezes o nada. O portão **absoluto** o recusa.
- **O valor absoluto sozinho** marca movimento: no mesmo material, um frame de movimento
  mede **18,7** sobre vizinhos de 18,2 — passa por qualquer piso baixo o bastante para não
  perder rabo discreto. O portão da **razão** o recusa (1,0×), porque movimento levanta a
  vizinhança inteira junto.

⚠️⚠️ **A amostra é de 2 positivos e 2 negativos.** É infinitamente mais do que a v1 tinha
(zero), e ainda assim é pouco para chamar de calibração madura. Quem for reusar isto:
acrescente o caso novo ao conjunto de teste **antes** de mexer no limiar.

## ⭐ Não mostre porcentagem de confiança

A v1 calculava um score e o **escondeu da própria interface**, com este comentário no
código:

> *"NÃO mostramos % de confiança (99% num falso positivo passa segurança que o app não
> tem)."*

O que a tela deve mostrar são os **números medidos** — `43,6 contra 14,2 da cena`. Número
medido é dado; porcentagem inventada é veredito. E são os números que permitem calibrar
melhor depois.

## ⭐ Confirmado em uso pelo editor (22/08/2026)

A lista sai correta dentro do Media Composer e **o clique leva a agulha direto ao ponto**.
Duas validações que apareceram sem serem procuradas:

- **A trilha visível se provou sozinha.** O editor cobriu um dos rabos com um clipe na V2;
  ao reconferir, aquele timecode **saiu da lista** e sobrou só o que continuava exposto. É
  a prova de que analisar a trilha VISÍVEL em cada ponto — e não a V1 por definição — era a
  decisão certa.
- **A checagem de bin desatualizada** passou a acompanhar a conferência, porque um rabo
  recém-coberto e não salvo continuaria na lista.

## Armadilhas de implementação

- **Transição sobrepõe os vizinhos** no modelo do Avid: uma dissolve de 20 frames come 20
  do clipe anterior e 20 do seguinte. Somar a duração dela como se ocupasse espaço
  **desloca todos os timecodes seguintes**, em silêncio. E ela não mora onde o componente
  aparece na lista — mora nos `dur` frames **antes** daquela posição.
- **Confira a própria aritmética contra um número de fora.** A soma dos comprimentos
  comparada com outra soma sua não confere nada (erro real cometido e pego por teste). O
  número independente é o `length` que a bin declara para o componente da trilha.
- **Não analise dentro de dissolve**: as duas imagens estão misturadas e a diferença entre
  campos perde o sentido. Pule — e **diga quantas** pulou.
- **`Filler` de comprimento ZERO** nas pontas de toda sequência não é corte.
- **Dois pedaços do mesmo master colados** têm o mesmo MobID e o mesmo nome, e **são** um
  corte. Quem denuncia é a fonte não avançar exatamente 1.
- **Uma passada de ffmpeg por ARQUIVO**, não por corte, com um `select` de vários
  `between(...)`. As janelas saem **coladas**, mas isso não contamina a medição: só os
  índices pares são usados, e a diferença dentro de um frame nunca atravessa a emenda.
  ⚠️ Funda janelas que se tocam, senão o mesmo frame sai duas vezes e desalinha os índices.
- **Alinhe pelo que o ffmpeg DEVOLVEU**, não pelo que se pediu: uma janela além do fim do
  arquivo devolve menos frames, e todos os índices depois do buraco apontam para o frame
  errado.

## Cross-ref

- Onde mora o entrelaçamento na bin, e como ir do clipe ao arquivo:
  [`../protocolos/avb/dados/entrelacamento-e-locators.json`](../protocolos/avb/dados/entrelacamento-e-locators.json)
- **Levar a agulha ao TC achado** — três caminhos, nesta ordem, todos em
  [`../plugins/avid-panel-sdk/dados/mcapi-grpc.json`](../plugins/avid-panel-sdk/dados/mcapi-grpc.json):
  `SetPosition` (§`SetPosition_DEPENDE_DA_VERSAO…`, **não existe** no MC 2025.6),
  **teclado simulado** (§`IR_A_UM_TIMECODE_por_teclado_simulado` — **é o que funciona**:
  um salto só, ~1,5 s, frame exato) e navegação por `DoCommand`
  (§`SetPosition…/SOLUCAO_navegar_por_DoCommand`, reserva, ~2 s de corte em corte).
  ⚠️ E §`DoCommand_SO_AGE_NA_JANELA_ATIVA_do_MC`, que vale para **qualquer painel `.avpi`**.
- **A bin em disco ainda descreve o que o editor vê?**
  §`A_BIN_ESTA_SUJA_como_descobrir_sem_flag` — não há flag de "modificado" na API; a
  resposta sai de comparar `num_segments` com os componentes da bin.
- Ler a lista de edição pela bin, nunca por AAF exportado:
  [`../protocolos/avb/dados/ler-timeline-sem-aaf.json`](../protocolos/avb/dados/ler-timeline-sem-aaf.json)

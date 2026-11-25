# Taxas de quadro: timeline × material, áudio, compound — o que cada NLE faz

> Estudo aberto em 2026-10-05 a pedido do autor: "existem várias questões de adaptações ou falta de
> adaptações de framerates que percorrem os projetos audiovisuais e dão nó no conform". Primeiro o
> **Resolve** (medido, autônomo, pela API); depois **Premiere** e **Avid** com os MESMOS arquivos.
>
> **Método:** vídeos SINTÉTICOS em que cada quadro leva o próprio número em código de barras (16 faixas
> na metade de cima; bit aceso = branco) e o áudio leva um clique de 1 ms no começo de cada segundo
> inteiro do arquivo. Lê-se o número de qualquer quadro exportado ou renderizado — sem comparar
> imagem, sem depender de achar um arquivo real com a característica.
> - Gerador: `DeLaPraCa_MIDIAS E PROJETOS DE TESTE/04 SINTETICOS/GERADORES/gerar_taxas.py` (`ler_numero`)
>   e `gerar_longos.py` (60 min).
> - Caso e scripts de medição: `…/03 CASOS/TC E FPS/C03 TAXAS NO RESOLVE/` (`CASO.md`, `fase*.py`,
>   `medicoes/*.json`).

## 1. Resolve (Studio 19.0.0b.59, Windows 11) — `confirmado`

### 1.1 Vídeo de uma taxa numa timeline de outra (fase 1)

7 taxas de timeline (23,976 · 24 · 25 · 29,97 · 30 · 50 · 59,94) × as mesmas 7 de material = 49
combinações, clipe posto pela API NATIVA (`AppendToTimeline`, startFrame = 300), lido no 1º quadro,
depois de 1 s e no último — e a fase 4 completa (abaixo), mais 7.644 leituras. **7.791 de 7.791**
batem com

    quadro do arquivo na tela = startFrame + floor(q × taxa_do_material / taxa_da_timeline + ε),  ε ≈ 0,0025

- ε medido entre 0,0020 e 0,0030 de QUADRO do material: o Resolve sobe para o próximo quadro quando
  falta menos de ~0,25% de um quadro (ex.: 59,94 numa de 30, q=1 → 1,998 → mostra o 2º; 23,976 numa de
  24, q=1 → 0,999 → mostra o 1º). Sem o ε, `floor` puro erra 152 das 7.644 leituras, sempre por +1.

- O clipe começa EXATAMENTE no quadro pedido (startFrame é quadro do ARQUIVO, na taxa dele).
- O Resolve toca o material em **tempo real**: não muda a velocidade, PULA quadros (material mais
  rápido) ou REPETE (mais lento). `floor`, não `round` (24 numa de 23,976: q=24 → 23,976 → mostra o 23).
- ⚠️ Consequência que o editor vê: **23,976 numa timeline de 24 pula 1 quadro a cada ~41,7 s**; 24 numa
  de 23,976 repete 1. Medido: q=1007 da timeline de 24 mostra o quadro 1305, não 1306 (fase 4).
- É o padrão do projeto: `timelineFrameRateMismatchBehavior = resolve` (Master Settings › Mixed frame
  rate format). Outras opções: rodada 2 (abaixo, se medida).

### 1.2 Compound e timeline aninhada (fase 4 — e a fase 4 COMPLETA)

**Completa (2026-10-05):** 1.274 combinações — em cada projeto (24 inteiro, 23,976, 29,97, 59,94), taxa
de DENTRO (onde o compound/nest nasce: a do projeto + 24, 25, 30, 50) × os 7 materiais × taxa de FORA
(as mesmas), compound E timeline aninhada, 6 pontos cada: **7.644 leituras, todas "uma conversão só"**
(o modelo de 1.1, com Fm e Ft — a taxa de dentro NÃO entra); a hipótese "duas em cascata"
(floor(floor(q·Fc/Ft)·Fm/Fc)) não explica nenhuma leitura em que as duas diferem (2.334).
**Compound e timeline aninhada são transparentes à taxa no Resolve, em qualquer combinação.**


O mesmo material de 23,976 numa timeline de 24, de quatro jeitos — o arquivo direto; um compound feito
numa timeline de 23,976; a timeline de 23,976 aninhada; um compound feito numa timeline de 24 — dá os
**mesmos quadros nas quatro**, inclusive o pulo aos ~42 s. No pool o compound guarda a taxa da timeline
onde nasceu (`FPS` 23.976 ou 24), mas o resultado na tela não muda: **compound/nest de 23,976 numa de 24
≡ o vídeo de 23,976**. A conversão de taxa acontece UMA vez, em tempo real, do arquivo para a timeline.

### 1.3 A API e as taxas fracionárias

- ⛔ `Timeline.SetSetting("timelineFrameRate", "23.976")` (e 29.97, 59.94, 47.952, com ou sem "DF")
  devolve **False** e a timeline fica com a taxa do projeto — calado. As inteiras (24, 25, 30, 48, 50, 60)
  são aceitas depois de `SetSetting("useCustomSettings", "1")`.
- ✅ `Project.SetSetting("timelineFrameRate", "23.976")` num projeto NOVO, antes de importar mídia: aceito;
  as timelines nascem nessa taxa. Num projeto de 23,976, uma timeline de taxa INTEIRA (24) ao lado é aceita.
- Ajustes do projeto que mexem nisto (nome na API): `timelineFrameRate`, `timelinePlaybackFrameRate`,
  `timelineDropFrameTimecode`, `timelineFrameRateMismatchBehavior` (`resolve`), `imageRetimeInterpolation`
  (`nearest`).

### 1.4 O `In` de um clipe vindo de DRT com taxa ≠ timeline

Ver [drt-drp/estruturas.md](../protocolos/drt-drp/estruturas.md) §7 ("O `In` do clipe"): floor(In ×
taxa do cabeçalho / taxa da timeline); taxa VARIÁVEL (celular) não garante o quadro.

### 1.5 Sync de áudio em sessão longa (fase 2) — `confirmado`

Material de 60 min (vídeo com o número do quadro + clique no começo de cada segundo, áudio AAC 48 kHz
embutido), clipe inteiro posto pela API numa timeline de outra taxa, render (QuickTime Photo JPEG + PCM)
dos 30 s do começo e dos 30 s do fim; para cada clique, o quadro do ARQUIVO na tela:

| timeline | material | começo (ms) | fim, 59,5 min (ms) |
|---|---|---|---|
| 24 | 23,976 | −40,7 a 0 | −40,6 a 0,1 |
| 24 | 25 | 0 | 0 |
| 24 | 29,97 | −32,4 a 0 | −32,6 a −0,2 |
| 24 | 59,94 | −16,4 a 0 | −16,6 a −0,2 |
| 25 | 23,976 | −40,7 a 0 | −40,6 a 0,1 |
| 25 | 29,97 | −32,4 a 0 | −32,6 a −0,2 |
| 23,976 | 25 | −80 a 0 | −80 a −40 |
| 23,976 | 29,97 | −65,7 a 0 | −50 a −17,6 |

(valor = quanto a imagem na tela começou ANTES do clique; o intervalo natural é de até 1 quadro da
timeline + 1 do material, por isso o 23,976 vai a −80.) **Nenhum escorregão em 60 min**: o Resolve toca
vídeo E áudio do material em tempo real; não conforma a velocidade (se conformasse 23,976 → 24, seriam
3,6 s fora no fim). O preço está na IMAGEM (quadro pulado/repetido, §1.1), nunca no sync.
⚠️ Método: o código de barras de 16 bits VOLTA a 0 a cada 65.536 quadros — sem desfazer a volta, o fim
"mostrou" −440 ms que não existiam (`analise_sync.medir(inicio_s=…)`).

### 1.6 Áudio de outras amostragens (fase 3) — `confirmado`

WAVs de cliques de 10 min (mono, 24 bits) a **32 · 44,1 · 47,952 · 48 · 48,048 · 88,2 · 96 · 176,4 ·
192 kHz**, cada um sozinho numa timeline de 24 (o Resolve mixa a 48 kHz), render do começo e do fim:
- duração na timeline = **10:00:00 exatos** nas nove; `Sample Rate` do pool = a do cabeçalho;
- cliques no fim **a menos de 0,05 ms** do lugar (o 0,48 ms do começo é o 1º clique cortado pelo trecho).
**O Resolve respeita a amostragem DECLARADA e toca em tempo real** — reamostra para a mixagem sem mudar
o tempo. ⚠️ Consequência: um WAV de 48,048 kHz (pull-up, típico de filme rodado a 24 e finalizado a
23,976) NÃO é desacelerado sozinho; se a produção espera o pull-down, alguém precisa mudar a amostragem
do clipe (Clip Attributes) — rodada 2.

Áudio a **44,1 kHz EMBUTIDO** no vídeo (60 min, AAC), timelines 24/25/23,976 com material 24/25: em sync
no começo e no fim (0 ms nos casos de quadro alinhado; −80 a −40 ms na de 23,976 com material a 25, o
intervalo natural de 1 quadro de cada lado).

### 1.6b Rodada 2 — parcial (2026-10-05)

`timelineFrameRateMismatchBehavior` aceita `resolve`, `fcp7` e `fcpx` (Master Settings › Mixed frame rate
format); `imageRetimeInterpolation` só aceita `nearest` pela API; a `FPS` do clipe muda por
`SetClipProperty("FPS", "24")` (Clip Attributes), a `Sample Rate` NÃO (`SetClipProperty` devolve False).
Medidos 16 casos no modo `resolve` (timelines 24/25/30/50, clipe de 60 s inteiro): quadros na regra de
§1.1 e sync sem escorregão do 1º ao último clique. ⏸ `fcp7`, `fcpx` e a taxa forçada no clipe: `pendente`
— a máquina de teste (RTX 4050 Laptop) caiu sob a carga contínua (ver o CASO.md).

### 1.7 Armadilhas da API medidas no estudo

- `Timeline.SetSetting("timelineFrameRate", <fracionária>)` → False (§1.3).
- ⛔ Render com `ExportVideo: False` (só áudio) **não gera arquivo** e não dá erro — e DEIXA O ESTADO
  sujo: o `ExportVideo: True` seguinte também sai SEM VÍDEO (só áudio + data). `LoadRenderPreset(...)`
  antes de cada render zera. Para medir só áudio: ponha uma imagem na V1 (só o vídeo de outro clipe,
  `mediaType: 1`) e renderize com vídeo.

## 2. Premiere — `pendente`

Mesmos sintéticos. Pergunta central: o Premiere também toca em tempo real (pula/repete) ou conforma? O
que ele faz com taxa variável (conta pela média: 24,0118 no vídeo de celular do PRODUCAO_B).

## 3. Avid Media Composer — `pendente`

Mesmos sintéticos (por AMA e por import). O Avid é conhecido por converter na importação (motion
adapters); medir o quadro na tela e o sync.

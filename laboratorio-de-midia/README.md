# Laboratório de Mídia

Mídia sintética, gerada pelo ffmpeg e reproduzível, que diz em cada quadro e em cada canal o que é. Os
testes leem essa verdade; o material real de captação vira validador fora do laboratório.

Plano completo (aprovado pelo autor em 2026-10-06): [`docs/organograma-2026-10-06.html`](docs/organograma-2026-10-06.html).

## Como usar

- **Duplo clique** em `GERAR E CONFERIR.command` (Mac) ou `GERAR E CONFERIR.bat` (Windows): gera os casos de
  `receitas/base/` em `saida/base/<caso>/` e confere cada arquivo. No fim aparece "Tudo gerado e conferido".
- Na mão: `python3 -m lab.gerar receitas/base/B01.json --verificar` (no Windows, `py -3`).
- Testes: `python3 -m unittest discover -s tests -t .` (com `PYTHONPYCACHEPREFIX` fora do SSD).
- Precisa só do Python 3.9+ e do ffmpeg/ffprobe — nenhuma biblioteca a instalar, nenhuma venv.

## O que mudou do organograma (2026-10-06, ao construir o B01)

- **Sem `drawtext` e sem fonte OFL.** O ffmpeg do Mac (Homebrew 8.1.1) não tem o filtro `drawtext`. O texto do
  quadro é desenhado com caixas: uma fonte de pixels própria (`lab/fonte_pixel.py`) para o texto fixo e dígitos
  de 7 segmentos para o TC e o número do quadro. Mesmos pixels em qualquer ffmpeg, Windows ou Mac. A pasta
  `fontes/` saiu.
- **A faixa de baixo grava o RÓTULO do TC** (HH·3600·b + MM·60·b + SS·b + FF): sem drop-frame é a contagem
  desde a meia-noite; com drop-frame os números pulados contam — é o que se compara com o TC que o NLE mostra.
  A claque cai no primeiro quadro de cada segundo de TC (no minuto que o DF pula, no ;02). Receitas com
  `variantes` (B02: uma por taxa).
- **Quadro conta a partir de 0** (o primeiro quadro do arquivo é o 000000), como no `gerar_taxas.py`.
- **XDCAM 50 sempre com 8 trilhas mono:** as que o caso não usa (no B01, da 3 à 8) ficam em silêncio, sem claque;
  a verdade diz `hz: null`.
- **Achado para a bancada do MC:** o OP-Atom do ffmpeg sai com um `material_package_umid` por arquivo — o MC
  deve ver o `_V01`, o `_A01` e o `_A02` como três clipes. Registrado no banco (`protocolos/mxf/README.md`).

## Resultados nos NLEs

| Caso | NLE | Onde |
|---|---|---|
| B16 NEST MASCARA | **Premiere 23.2 × Resolve 19 (Windows)** — máscara em nest/nest de nest/proxy X≠Y/velocidade; o número do quadro lido na imagem: a GRADE do nest (o conteúdo anda pelo piso nos quadros do nest); 14/18 iguais, 4 de in fora da grade pendentes | [`resultados/B16_NEST_MASCARA/PREMIERE_RESOLVE.md`](resultados/B16_NEST_MASCARA/PREMIERE_RESOLVE.md) |
| B14 MASCARA | **Premiere 23.2 × Resolve 19 (Windows)** — máscara de opacidade com borda conhecida, verdade pelo render: Feather = largura total centrada (0,915×, px da fonte), Expansion exata; o De Lá Pra Cá calibrado (SoftEdge 0,845, Border Width ×2, deslocamento dos keyframes) → ~2 px | [`resultados/B14_MASCARA/PREMIERE_RESOLVE.md`](resultados/B14_MASCARA/PREMIERE_RESOLVE.md) |
| B01–B06 | **Premiere Pro 25.6.5 (Mac)** — quadro exato em 309 stills; OP-Atom de vídeo do ffmpeg recusado; estéreo do MXF OP1a vira "2 Mono" e sai L = R (mov/mp4/WAV certos, com Use File); meia-noite volta a 00; sem escala por padrão; sync à mão exato | `resultados/B0*/PREMIERE.md` + `prproj/` (estrutura por versão, para o downgrade) |
| B06 SOM DIRETO | Resolve 21.1 (Mac) — sync por TC exato; só 2 dos 4 canais do BWF na mistura; sync à mão pela API derruba o Resolve | [`resultados/B06_SOM_DIRETO/RESOLVE.md`](resultados/B06_SOM_DIRETO/RESOLVE.md) |
| B05 RASTERS | Resolve 21.1 (Mac) — nativo e ajustado ao HD exatos nos 6 rasters, anamórfico desespremido | [`resultados/B05_RASTERS/RESOLVE.md`](resultados/B05_RASTERS/RESOLVE.md) |
| B04 TIMECODE | Resolve 21.1 (Mac) — 6 casos exatos; depois da meia-noite a régua segue em 24:… | [`resultados/B04_TIMECODE/RESOLVE.md`](resultados/B04_TIMECODE/RESOLVE.md) |
| B03 LAYOUTS DE ÁUDIO | Resolve 21.1 (Mac) — como cada layout vira trilha; 2 mono = L = R no render | [`resultados/B03_LAYOUTS_DE_AUDIO/RESOLVE.md`](resultados/B03_LAYOUTS_DE_AUDIO/RESOLVE.md) |
| B02 TAXAS | DaVinci Resolve Studio 21.1 (Mac) — 8 taxas e o 29,97 DF atravessando o minuto: quadro exato por TC e no render, nenhuma diferença | [`resultados/B02_TAXAS/RESOLVE.md`](resultados/B02_TAXAS/RESOLVE.md) |
| B01 FORMATOS | DaVinci Resolve Studio 21.1 (Mac) — quadro exato nos 6 perfis; XDCAM 8 mono misturado no render (com conserto); OP-Atom do ffmpeg em 3 clipes | [`resultados/B01_FORMATOS/RESOLVE.md`](resultados/B01_FORMATOS/RESOLVE.md) |

## O princípio

- **A mídia diz o que é.** Cada quadro traz o número dele e o timecode em código de barras (máquina) e em
  texto (editor). Cada canal de áudio tem uma frequência própria.
- **Receita, não arquivo.** Guarda-se a receita (JSON) e o gerador; a mídia se refaz em qualquer máquina.
- **A verdade acompanha a mídia.** Cada caso gera um `verdade.json`.
- **Para todos os softwares**, incluindo o OP-Atom do Media Composer.

## Pastas

```
laboratorio-de-midia/
├─ CLAUDE.md, README.md
├─ lab/          o pacote Python: video, audio, tc, formatos, gerar, ler, verificar
├─ receitas/
│  ├─ base/      o pacote desta fase (B01–B06)
│  └─ multicam/  o próximo pacote
├─ tests/
├─ fichas/       uma ficha por arquivo real da coleta (a mídia mora em MIDIAS DE TESTES)
├─ docs/         o organograma aprovado
├─ .dev/         HANDOFF.md
└─ saida/        o que o gerador faz (fora do Git; pode apagar e refazer)
```

## A identificação (aprovada)

- **Vídeo:** duas faixas de código de barras de 24 bits — em cima o número do quadro no arquivo, embaixo o
  TC em quadros desde a meia-noite. Fundo na cor da câmera: CAM 1 azul, CAM 2 âmbar, CAM 3 verde, CAM 4
  magenta (escuras o bastante para o texto branco passar no piso de contraste). Grade, cantos e círculo
  denunciam escala, posição, recorte e distorção. Texto: caso, câmera, take, TC, quadro, taxa e raster.
- **Áudio:** um tom por canal e por fonte, a −20 dBFS: `f = 300 + 1700·(fonte−1) + 100·(canal−1)` Hz
  (CAM 1 canal 1 = 300 Hz; CAM 2 começa em 2000 Hz; som direto, fonte 4, em 5400 Hz). Claque de 1 ms a
  cada segundo inteiro de TC, comum a todas as fontes.
- **Layouts:** mono, estéreo, 4, 5, 8 e 16 canais; polifônico num arquivo ou um mono por canal.

## Os formatos (aprovados)

| Perfil | Para | Vídeo | Áudio |
|---|---|---|---|
| `mp4-h264` | todos (o "celular") | H.264 | AAC, até 8 canais |
| `mov-prores` | Premiere, Resolve | ProRes 422 / 4444 | PCM 24 bits |
| `mxf-op1a` | Resolve, Premiere, MC (AMA) | DNxHD / DNxHR | PCM, polifônico |
| `mxf-xdcam50` | todos (broadcast) | XDCAM HD 50 (MPEG-2 4:2:2, 50 Mb/s), 1080i e 1080p | PCM 24 bits, 8 canais mono |
| `mxf-opatom` | Media Composer (gerenciada) | DNxHD, um arquivo de vídeo | um arquivo mono por canal |
| `wav-bwf` | som direto | — | BWF com TC (time reference) |

A medir: o MC só trata OP-Atom como gerenciada se o reconhecer na `Avid MediaFiles` e no banco dele
(`.mdb`/`.pmr`). Gerar é fácil (muxer `mxf_opatom`); fazer o MC adotar é a pergunta. ⛔ A `Avid MediaFiles`
da raiz do SSD é protegida: a bancada usa uma pasta própria, nunca a do trabalho.

## O pacote Base (esta fase)

| Caso | A pergunta | O que gera |
|---|---|---|
| B01 FORMATOS | O mesmo clipe nos seis perfis chega igual em cada NLE? | 1 clipe de 10 s, 1080p 25, estéreo, nos seis perfis |
| B02 TAXAS | Cada taxa é lida e contada certo, inclusive com drop-frame? | 23,976 · 24 · 25 · 29,97 ND e DF · 30 · 50 · 59,94 |
| B03 LAYOUTS DE AUDIO | Cada canal toca o que deveria, polifônico ou separado? | mono, 2, 4, 5, 8 e 16 canais |
| B04 TIMECODE | O TC de início é respeitado nos casos difíceis? | rec-run 01:00:00:00, hora do dia, virada da meia-noite, TC zero, DF 29,97 |
| B05 RASTERS | Escala e posição se mantêm entre rasters? | HD, UHD, 4K DCI, 2K scope, vertical 9:16, anamórfico 2:1 |
| B06 SOM DIRETO | O BWF casa com o vídeo pelo TC? | 1 vídeo com som de câmera + 1 BWF de 4 canais, mesmo TC, deslocado 2 s |

Depois: o pacote **Multicam** (takes contínuos e com intervalos, taxas mistas, Full HD com takes em 4K,
layouts de áudio, som de câmera ou só som direto) e a fase 2, os projetos em cada NLE (Premiere `.prproj`,
Resolve DRT, Media Composer bin/AAF com OP-Atom), cada um medido no próprio NLE.

## A coleta de arquivos reais (aprovada, com o ajuste da arrumação)

A **mídia** real mora em `MIDIAS DE TESTES/2 FORMATOS E CAMERAS/<formato>/` (lá já estão `ARRI` e
`SONY XOCN`), fora deste Git — uma cópia só de cada mídia, como manda o LEIA-ME de lá. Aqui ficam as
**fichas** (`fichas/`), uma por arquivo: câmera, formato, origem e o nível de cada caminho:

| Nível | O que significa | Esperado (hipótese até medir) |
|---|---|---|
| lê e reproduz | ffprobe lê os metadados e o ffmpeg decodifica | H.264, H.265, ProRes, DNx, XDCAM |
| só lê | metadados e duração saem; a imagem não | ARRIRAW, X-OCN |
| precisa do SDK | nem os metadados certos saem sem o SDK | BRAW, R3D, ProRes RAW |
| cada NLE | abre no Premiere, no Resolve e no MC (AMA)? em qual versão? | uma coluna por NLE |

As fichas alimentam o banco (`transversal/raw-de-camera-e-sdk.md`, `protocolos/mxf/codecs-proprietarios.md`).

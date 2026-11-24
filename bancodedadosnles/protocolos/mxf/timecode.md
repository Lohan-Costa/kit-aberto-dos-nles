# MXF — de onde tirar o TIMECODE (e as três formas de tirar errado)

Medido em 2026-08-14 (DRAMASYNC/Órbita) sobre **dois acervos reais**:

- `MIDIAS DE TESTES/PRODUCAO-F_24FPS/010020260629` — 396 `.mxf` OP-Atom **DNxHD**,
  24 fps, escritos pelo **DaVinci Resolve 20.3.1** (câmera) e por **AAFSDK** (som).
- `Avid MediaFiles/MXF/1` — 66 `.mxf` OP-Atom **XDCAM 50 (MPEG-2 4:2:2)**, 23,976,
  escritos pelo **AAFSDK (MacOS X)**, ou seja pelo próprio Avid.

Complementa a [§rota ffprobe do README](README.md) — lá está o AGRUPAMENTO, aqui o
TIMECODE. Fatos consumíveis em [dados/opatom-timecode.json](dados/opatom-timecode.json).

---

## 1. Onde o TC de FONTE realmente mora — `confirmado`

**Nas tags de STREAM do `ffprobe`, na stream de ESSÊNCIA.** Não em `format.tags`.

```
ffprobe -v error -show_entries stream_tags=timecode:format_tags=timecode \
        -of default=nw=1:nk=1 file:CLIPE.mxf
```

| container | onde está o `timecode` |
|---|---|
| **MXF OP-Atom** (Avid) | `stream.tags` da essência. `format.tags` **não tem** o campo |
| **MXF OP-1a** (XDCAM de câmera, `.mxf` solto) | `format.tags` |
| `.mov` / `.mp4` | `format.tags` |

Pedir os dois numa chamada só e ficar com o primeiro que vier cobre todos os casos.

⚠️ **A essência não é necessariamente a stream 0.** Num `A01` OP-Atom do Avid medido, a
stream 0 era `data` e a essência de áudio era a **1**. As outras tracks do clipe aparecem
como streams `data` vazias (é isso que permite saber de UM arquivo quantas tracks o clipe
tem — ver o README). Varrer todas as streams e pegar o primeiro `timecode` válido.

**Validação forte (é o que dá o `confirmado`):** no acervo de 24 fps, os offsets que a
correlação de forma de onda encontrou sozinha — 396, 323 e 229 frames em três clipes —
bateram **exatamente** com a diferença entre o TC lido aqui na câmera e no som. Três de
três, sem folga. Duas medições independentes concordando.

Isto resolve, para OP-Atom, o item que o README listava como pendente ("como obter o TC da
FONTE"): a rota existe e é esta.

---

## 2. ⚠️ Armadilha: o MediaInfo devolve o TC de SISTEMA do MXF — `confirmado`

Quem lê TC por **pymediainfo** (track `Other`, o `tmcd` do QuickTime) recebe, num OP-Atom,
uma coisa que **não é o TC do clipe**: a faixa sintética do timecode de sistema do MXF.

```
Other:
  format                    = MXF TC
  frame_count               = 10368000          ← 120 h a 24 fps
  time_code_of_first_frame  = 00:00:00:00
  time_code_of_last_frame   = 119:59:59:23
  time_code_settings        = Source Package    ← mente: diz "Source Package" e não é
```

Ela existe em **todo** arquivo OP-Atom e não descreve nenhum. O modo de falha é o pior
possível: **não é ausência de dado, é um dado plausível**. `00:00:00:00` passa em qualquer
checagem de "tem TC", nada levanta exceção, e a diária inteira empilha no mesmo instante da
timeline. Foi assim que 394 clipes de um longa caíram todos em zero.

### O valor dela às vezes ACERTA — e isso não depende do codec

Esta foi a parte contra-intuitiva. A faixa é **sempre** degenerada, mas onde ela **começa**
varia com o programa que escreveu a mídia:

| material | MediaInfo diz | extensão da faixa | certo? |
|---|---|---|---|
| OP-Atom DNxHD, escrito pelo **Resolve** | `00:00:00:00` | 0 → `119:59:59:23` (120 h) | ✗ |
| OP-Atom, áudio de gravador (**AAFSDK**) | `00:00:00:00` | 0 → `119:59:59:23` | ✗ |
| OP-Atom XDCAM 50, escrito pelo **Avid** | `23:16:47:11` | TC de fonte → +48 h | ✓ |

Ou seja: **não é o codec que decide** (a pergunta natural, e a resposta é não). É quem
gerou a mídia. E como não há como saber de qual caso se trata olhando só o valor, o TC do
MediaInfo num OP-Atom é sempre **suspeito** — nunca descartável, nunca confiável sozinho.

### O discriminador: extensão da faixa, nunca o valor do TC — `confirmado`

Comparar o `frame_count` do TC track com o número de frames do clipe:

| material | `frame_count` do TC track | frames do clipe | razão |
|---|---|---|---|
| `.mov` (PRODA_CORTE.02) | 38 133 | 38 133 | **1,00×** |
| `.mp4` (A001_03170214_C001) | — | — | **1,00×** |
| MXF XDCAM OP-1a | 12 844 | 12 844 | **1,00×** |
| MXF XDCAM OP-1a (drop-frame) | 952 | 952 | **1,00×** |
| **OP-Atom DNxHD** | 10 368 000 | 2 372 | **4371×** |
| **OP-Atom XDCAM** (13 arquivos) | — | — | **115× a 8853×** |

Um TC track legítimo cobre exatamente o clipe. Entre 1× e 115× cabe qualquer folga — os
apps usam **2×**.

⚠️ **NÃO discriminar pelo valor do TC.** `00:00:00:00` é um timecode legítimo: no acervo de
testes o `ACERVO_CLIP_01_1.mxf` começa nele de verdade. Descartar todo zero curaria o
sintoma e cegaria o app para material bom.

⚠️ **NÃO usar `time_code__stripped` como sinal.** Parece o discriminador óbvio e não é: ele
vem `Yes` em **todo** o acervo medido, inclusive nos `.mov`, `.mp4` e MXF XDCAM cujo TC
sempre funcionou. Usá-lo quebraria a leitura de TC do app inteiro.

**Detalhe de parsing:** o `frame_count` chega como `int` num arquivo de vídeo e como a
string `"10368000 / 5664000"` num de áudio (o MediaInfo junta as duas contagens do track).
Pegar o primeiro inteiro cobre as duas formas.

---

## 3. A track de áudio de um OP-Atom não é BWF — `confirmado`

Um WAV importado no Avid vira N arquivos OP-Atom mono (um por canal), e **eles perdem o
chunk `bext`**: não há `time_reference` (a contagem de amostras desde a meia-noite que é a
rota normal de TC num BWF). O relógio vem como `HH:MM:SS:FF` nas tags de stream, igual ao
do vídeo.

Consequência para quem sincroniza: um app que só saiba ler TC de som por `time_reference`
fica **sem relógio nenhum** no som — e o som é o que ancora o sync. É preciso a rota do §1
também para o áudio.

**Vídeo e suas próprias tracks de áudio concordam no TC** (verificado clipe a clipe no
acervo XDCAM, agrupando por `material_package_umid`): o mesmo `23:16:47:11` no `V01` e nos
`A01..A04`.

### A unidade resultante NÃO é a mesma de um BWF

Um `tc_start_sec` derivado de `time_reference` conta **amostras desde a meia-noite REAL** —
não passa por frames, não herda o 0,1 % do NTSC, e a volta do dia dele é 86 400 s exatos.
Um `tc_start_sec` derivado de um TIMECODE herda o 0,1 %, e a volta dele é a do timecode
(86 486 s a 23,976 — ver [transversal/tempo-e-timecode.md](../../transversal/tempo-e-timecode.md)).

A 24 fps cravado as duas coincidem e a distinção some. A 23,976 são **86 s de erro por dia
atravessado**. Quem guardar os dois no mesmo campo precisa carregar junto a taxa em que o
valor conta — a presença dela é o que diz qual volta usar.

---

## 4. ⚠️ `comment_Soundroll TC Rate` NÃO é a base em que o TC conta — `confirmado` (por contra-teste)

Um WAV importado traz comentários do Avid, entre eles:

```
TAG:comment_TapeID=20240531_ZOOM0034_Tr12.WAV
TAG:comment_Shoot Date=2024-05-31 10:02:15
TAG:comment_Soundroll TC Rate=25
```

O nome é uma armadilha perfeita: parece declarar a taxa do rolo de som, e o material é um
projeto a **23,976** — a leitura natural é "o gravador contava a 25, use 25". **Eu usei, e
deslocou o som em 36 s.**

O contra-teste, com o relógio de parede do próprio gravador (`Shoot Date`, que vem do
`OriginationTime` do BWF e é independente do TC) como árbitro. TC gravado: `10:01:38:21`:

| taxa | segundos reais | como hora | distância do relógio do gravador |
|---|---|---|---|
| 25 (o que a tag declara) | 36 098,840 | `10:01:38,840` | **36,160 s** |
| 24 exato | 36 098,875 | `10:01:38,875` | 36,125 s |
| **23,976 (NTSC)** | **36 134,974** | **`10:02:14,974`** | **0,026 s** ✅ |
| 29,97 | 36 134,799 | `10:02:14,799` | 0,201 s |

Só 23,976 reproduz o relógio do gravador, e com 26 ms de erro. E os 36 s de discrepância
das outras hipóteses são exatamente a deriva de 0,1 % do NTSC acumulada em 10 h de timecode
(`10 × 3600 × 0,001 = 36 s`) — a assinatura de um TC 23,976 posto em hora do dia, cujo
DISPLAY vai ficando para trás do tempo real.

**Conclusão:** seja lá o que aquele campo descreva (rótulo do rolo? default do diálogo de
import? campo não preenchido?), **não é a base de contagem do TC**. A taxa inferida do track
de timecode do MediaInfo (`framerate_num`/`framerate_den`) estava certa.

⭐ **A lição de método, que vale além deste campo:** uma tag com nome auto-explicativo é uma
hipótese, não um fato. O que a promoveu a fato negativo foi existir um **árbitro
independente** no próprio arquivo — o relógio de parede do gravador. Sem ele eu teria
arquivado o erro aqui como verdade.

---

## 5. Achado de campo: os dois relógios podem estar a horas de distância

No acervo XDCAM, câmera e som não compartilham relógio:

- câmera `V01`: TC `23:16:47:11`
- som ZOOM: TC `10:01:38:21`, com o `Shoot Date` do gravador confirmando `10:02:15`

**13,3 h de distância.** O gravador é internamente coerente (TC e relógio de parede batem),
o que joga a suspeita sobre o TC da câmera — provavelmente free-run, ou relógio nunca
acertado. Pelo metadado não dá para afirmar qual está certo.

Não é defeito de leitura: é o material. Para um app de sync isso significa que o caminho por
TC não tem como casar nada ali, e o resultado tem de vir da forma de onda — que é
exatamente o que se observou. Vale como lembrete de que **"tem TC nos dois lados" não
implica "os dois TCs são comparáveis"** (o mesmo espírito da §"O TC de uma câmera contra o
de OUTRA não vale NADA" em [transversal/tempo-e-timecode.md](../../transversal/tempo-e-timecode.md)).

---

## Fonte

**DRAMASYNC / Órbita, 2026-08-14.** Implementado em `src-python/media/inspector.py`
(`_tc_track_e_do_clipe`, `_ffprobe_stream_timecode`, `_tc_rate`) e
`src-python/sync/engine.py` (`_Sound.tc_abs_sec`); decisão narrada em
`DRAMASYNC/docs/adr/0018-timecode-de-fonte-vs-timecode-de-sistema.md`.
Acervos medidos: `MIDIAS DE TESTES/PRODUCAO-F_24FPS/010020260629` (396 arquivos, DNxHD 24)
e `Avid MediaFiles/MXF/1` (66 arquivos, XDCAM 50 a 23,976), mais o acervo de regressão
`MIDIAS DE TESTES/XDCAM50`, `SAMPLE FOOTAGE` e `PRODUCAO-A` (14 arquivos `.mov`/`.mp4`/MXF
OP-1a, nenhum regrediu).

## O `tmcd` HÍBRIDO do render do Baselight (`confirmado`, Baselight 7.0.3 Mac, 2026-11-23)

O render de um plano cujo original tem OUTRA taxa que a timeline sai na taxa da timeline com o `tmcd` em timescale
24000/1001 e `nframes` 30 (DF) ou 60 — a base do ORIGINAL; o contador é o quadro de fonte do original. O ffprobe converte
por tempo (base 60) ou recusa (30 DF numa trilha de 23,976). Ler CRU (`prproj.originais.tmcd_cru`). Detalhe e contexto:
`plugins/baselight/README.md`, seção BL09.

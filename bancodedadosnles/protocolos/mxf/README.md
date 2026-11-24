# MXF — essência / wrapper (e identidade UMID)

> **Stub a expandir.** O MXF aparece como **essência** (a mídia em si), não como timeline. Aqui
> mora o que os apps já precisaram saber sobre ele; o detalhe de baixo nível (KLV, partitions)
> ainda não foi mapeado.

## O que MXF é, no nosso contexto

- **Wrapper de mídia do Avid.** Os clipes do Avid vivem em `Avid MediaFiles/MXF/<n>/*.mxf`.
- Também é o container de câmera de vários formatos: **Sony X-OCN é `.mxf`** — detectado por
  **essência (codec)**, não por extensão (RELINKER, `frames/decoders.py`).

## Op-Atom (Avid): identificar e agrupar clipes — `confirmado`

O Avid grava cada **track** de um clipe (o vídeo e **cada canal de áudio**) como um arquivo
`.mxf` **OP-Atom separado**, todos em `Avid MediaFiles/MXF/<n>/`. "Enxergar os clipes agrupados"
= juntar os N arquivos OP-Atom que pertencem ao mesmo clipe. Há **cinco rotas** já usadas nos apps,
todas confirmadas contra mídia real — mas elas **não são equivalentes** (ver o aviso abaixo da tabela):

| rota | como agrupa | custo | onde |
|---|---|---|---|
| **`ffprobe` / `material_package_umid`** ⭐ | tag de FORMATO `material_package_umid` — igual em todas as tracks do clipe | 1 `ffprobe` por arquivo, zero dependência nova | `DRAMASYNC` (medida 2026-08-08, ver §rota ffprobe) |
| **UMID do header (pyaaf2)** | mesmo `MaterialPackage` MobID/UMID = mesmo clipe | lê header via pyaaf2 | `FLATFILE-MULTCAM/…/mxf_inspect.py` |
| **nome do arquivo (sem I/O)** | stem sem o **sufixo de track** `(?i)_[AV]\d+$` (`_A01`,`_A02`,`_V1`…) — tracks do mesmo clipe diferem só nisso | zero (só o nome) | `MSYNC/internal/project/mxf.go` |
| **nome do header (tag 0x4402)** | lê o **nome do clipe** do header e agrupa por ele (canônico, igual em todas as tracks) | lê ~256 KB por arquivo | `MSYNC` (`readClipNames`) |
| **via `.mdb`** | o banco Bento já lista os clipes agrupados sem tocar no MXF | lê 1 arquivo por pasta | `LEITOR DE MDB` / [msm](../msm/mdb-bento.md) |

⚠️ **A rota por NOME DE ARQUIVO não é geral** — ver o contra-exemplo medido em §rota ffprobe.

**Lendo o nome do clipe do header OP-Atom (MSYNC, `findPackageNameInHeader`):**
- A propriedade **Name** é o **local tag `0x4402`** nos local sets do header MXF, **UTF-16BE**;
  o comprimento é um `uint16` big-endian logo após o tag (`data[i+2:i+4]`).
- O header tem **vários** `0x4402`: `MaterialPackage`.Name = **nome do clipe**, `SourcePackage`.Name
  = fita/arquivo, e as tracks (`GenericTrack`.Name = `"V1"`,`"A1"`,`"A01"`…). Pegar o primeiro dá
  resultado inconsistente entre tracks.
- **Heurística que funciona:** coletar todas as Names válidas do header (nos primeiros ~256 KB) e
  escolher a **mais longa que não seja nome de track** (`^[AVD]\d{1,2}$`). O nome do clipe é igual
  em todas as tracks → agrupamento consistente. Filtros de validade: 3–200 chars, imprimível/sem
  controle, >40% alfanumérico.
- **Estratégia robusta combinada:** agrupa pelo nome-de-arquivo (`nameKey`) e, dentro de cada
  `nameKey`, **propaga** o `headerName` lido (uma track cuja leitura falhou ainda cai no grupo
  certo); usa o `headerName` quando houver (mescla arquivos de nomes diferentes mas mesmo clipe),
  senão o `nameKey`. Nunca mescla clipes de `headerName` distintos.

## A rota `ffprobe`: agrupar, nomear e identificar sem dependência nenhuma — `confirmado`

Medido em 2026-08-08 (DRAMASYNC/Órbita) sobre **540 `.mxf` reais = 111 clipes**
(`/Volumes/SSD/z ignore o que esta aqui/Avid MediaFiles`, pastas `MXF-original` e `MXF--`).
Um único `ffprobe -show_format -show_streams` por arquivo entrega tudo:

| campo | onde | o que é | confiança |
|---|---|---|---|
| `material_package_umid` | `format.tags` | **a chave de agrupamento** — igual em todas as tracks do clipe. É o MobID do **MasterMob**, o mesmo que uma composição AAF/`.avb` usa para referenciar mídia gerenciada | `confirmado` (0 falhas em 540) |
| `material_package_name` | `format.tags` | nome do clipe **como aparece na bin** (inclui os sufixos do Avid: `.new.01`) — é editável pelo editor | `confirmado` |
| `operational_pattern_ul` | `format.tags` | o OP pattern (ver abaixo) | `confirmado` |
| `file_package_umid` | `stream.tags`, em **todas** as streams | o UMID de **cada arquivo-track** — inclusive das outras tracks do clipe | `confirmado` |
| `reel_name` | `stream.tags` | **NÃO é confiável como nome do clipe de origem** — ver a ressalva abaixo | ⚠️ `hipotese` |
| `timecode` | `stream.tags` | **pode ser o TC do material, não o da fonte** — ver a armadilha abaixo | ⚠️ `inferido` |

**Consequência boa:** um OP-Atom lista os `file_package_umid` de TODOS os irmãos, então de **um** arquivo
já se sabe quantas tracks o clipe tem. E `material_package_umid` serve às duas pontas do fluxo —
agrupar na leitura *e* identificar o master na hora de autorar a composição.

**Custo:** extrair uma janela de 20 s de áudio de um `A01` OP-Atom levou **0,04 s** (arquivo mono de
2,8 MB) contra demuxar o DNxHR de 123 MB do mesmo clipe. Para quem só quer o áudio-guia, OP-Atom é
mais barato que mídia de câmera.

### OP pattern UL — resolvido (era `pendente`)

`operational_pattern_ul` vem pronto no `ffprobe`. Na amostra: `060e2b34.04010102.0d010201.10030000`
(531×), `…10020000` (7×), `…10000000` (2×). **O byte 13 = `0x10` é a família OP-Atom** (SMPTE 390M);
o `.10000000` é o UL canônico e os outros dois são qualificadores. O que cada qualificador significa
continua `pendente` — mas *distinguir OP-Atom de OP-1a* não exige mais parsing próprio.

> 📖 **O timecode ganhou tema próprio: [timecode.md](timecode.md)** (medido 2026-08-14 sobre
> mais dois acervos, DNxHD 24 e XDCAM 50 a 23,976). Lá está **onde o TC de FONTE realmente
> mora** (tags de STREAM do `ffprobe` — resolve o pendente do fim desta página), a armadilha
> do **MediaInfo**, que devolve uma faixa sintética de 120 h em vez do TC do clipe, e o
> contra-teste que derruba `comment_Soundroll TC Rate`. Dados:
> [dados/opatom-timecode.json](dados/opatom-timecode.json).

### ⚠️ Armadilha 1: o `timecode` pode ser o do MATERIAL, não o da FONTE

O **mesmo clipe** (`A002_03170813_C004`) lê `08:12:41:20` em `MXF-original` e `01:00:00:00` em
`MXF--`. Conforme como a mídia foi criada (import, consolidate, transcode), o TC do MaterialPackage
substitui o da fonte no que o `ffprobe` expõe. Na amostra, 46 de 517 arquivos com TC estavam em
`01:00:00:00`.

**Por que isso é grave para quem sincroniza:** é um relógio que *passa* numa checagem de "tem TC" e
mente. Um app que use TC precisa separar TC de material de TC de fonte antes de confiar, e tratar
"a diária inteira em 01:00:00:00" como TC inutilizável, não como TC zero.

### ⚠️ Armadilha 2: `reel_name` NÃO é o nome do clipe de câmera

Na amostra medida, os `reel_name` batiam com o nome do clipe original — **e isso é contaminação da
amostra, não uma regra**: aquela mídia foi convertida pelo **DaVinci Resolve**, que oferece preencher
o campo Reel com o nome do clipe. Na vida real o `reel_name` **pode vir vazio, ou trazer só a
identificação do CARTÃO (`A001`) e não a do clipe individual**.

*Registro honesto do que a amostra prova e do que não prova:* 23 arquivos vieram sem `reel_name`, mas
todos eram tracks de **dados** (`D01.*`) — nenhum arquivo de vídeo/áudio ficou sem. Ou seja **esta
amostra não é capaz de testar a semântica do `reel_name`**; a ressalva vem de conhecimento de campo
(usuário, 2026-08-08), não da medição. Quem precisar da identidade da fonte deve tirá-la do
SourcePackage/UMID, não do Reel.

### ⚠️ Armadilha 3: a rota por nome de arquivo falha nesta nomenclatura

O Avid nomeia OP-Atom de **duas** formas, e a rota "custo zero" do MSYNC só cobre uma:

- `CLIPE_A01.mxf` — sufixo de track no FIM → casa com `(?i)_[AV]\d+$`.
- `A01.E52BE67C_30AF530AF52D7A.mxf` — **prefixo de track na FRENTE** + hash; o resto do nome **não é
  compartilhado** entre as tracks do mesmo clipe.

Na amostra: **444 arquivos com prefixo contra 40 com sufixo** — a rota por nome funcionaria em ~7%.
Agrupar por nome de arquivo só é seguro depois de confirmar a nomenclatura do acervo.

### ⚠⚠ Armadilha 4: DUAS nomenclaturas convivem no MESMO volume

`confirmado` 2026-08-23, numa `Avid MediaFiles` com material de três produções.

A mesma `Avid MediaFiles` guardava, lado a lado:

```
a005_03180050_C001.mxf        a005_03180050_C001_A01.mxf     ← nome do CLIPE
V01.E69CCF0F_1A8ED1A8EDCFCV.mxf   A01.E69CCF10_1A8ED1A8EDD3FA.mxf   ← hash
```

⭐ **Ou seja: nem "o nome do arquivo é o nome do clipe" nem "o nome é hash" são
verdade** — as duas convivem, e provavelmente por versão/via de import. Um app que
case por nome funciona numa bin e devolve **zero** na seguinte.

#### 🆕 São TRÊS, não duas — a terceira é a do Nexis (`confirmado` 2026-08-23)

O acervo de produção da Emissora traz uma forma intermediária: **o nome do clipe truncado**
num orçamento fixo de caracteres, seguido de track e hash.

| convenção | exemplo | leva o nome? |
|---|---|---|
| nome inteiro + track no fim | `PRODUCAO-A - 05-04 C4 P1-T001_A01.mxf` | ✅ inteiro |
| **nome TRUNCADO + hash** | `O CRUZAMENA01.6A8AF212609FA.mxf` (10 caracteres) | ⚠️ pedaço |
| só track + hash | `V01.E69CCF0F_1A8ED1A8EDCFCV.mxf` | ⛔ **nenhum** |

Confirmada também no Nexis: `6K_F017_260615_UPP05` → `6k_f017_26v01…`,
`WhatsApp Video 2026-07-21 at 17.26.11.mp4` → `whatsapp video 202eae20c0ba.mxf` (ver
[../../transversal/caminhos-e-storage-producao.md](../../transversal/caminhos-e-storage-producao.md)
§2.1).

⛔ **A regra que sai das três: o nome do arquivo serve para ORDENAR uma busca, nunca para
FILTRAR uma.** Um filtro que exclua o que não casa com o nome do clipe perde o acervo
inteiro da terceira linha — e perde **calado**, com o app dizendo "não encontrado" em cima
de mídia que está ali. Ver a estratégia de busca abaixo.

⛔ O efeito medido: uma comparação por nome deu **0 de 13** clipes numa diária, com
cara de motor quebrado; pelo **MobID**, 13 de 13. Ver
[../../transversal/medir-sync-contra-gabarito.md](../../transversal/medir-sync-contra-gabarito.md) §3c.

### ⚠ Armadilha 5: a duração do CLIPE pode não cobrir o arquivo de origem

`confirmado` 2026-08-23. Numa diária real, o take `C11 P1-T002`:

```
WAV original ................ 255,3 s
clipe do Avid (5 canais) .... 114,4 s     (o master declara 2742 frames)
```

⚠ **Não é mídia offline num clipe de 255 s** — o CLIPE tem 114 s; a importação
original entrou cortada. Uma reimportação do zero trouxe os 255,3 s.

⭐ **Por que isto importa muito mais do que parece:** algoritmos que encaixam o
DESENHO dos intervalos (vídeo × som) para achar o Δ entre relógios usam a duração de
cada clipe. **Um único clipe com duração destoante desloca o encaixe da diária
inteira** e derruba o pareamento de clipes que nada têm a ver com ele — medido: um
clipe truncado custou 5 pontos percentuais de acerto, e o erro que ele causou foi
**silencioso**.

⚠ Corolário para quem escreve: **não assuma que o clipe do Avid cobre o arquivo de
origem.** E quando o resultado destoar entre mídia gerenciada e original, **compare as
durações arquivo a arquivo** antes de suspeitar do codec ou do TC.

### ⭐ O áudio transcodado PRESERVA a sincronia (útil, e não óbvio)

`confirmado` 2026-08-23, correlação cruzada de forma de onda entre os dois mundos:

| câmera × som | confiança | offset |
|---|---|---|
| mp4 × WAV | 5,54 | 183 |
| OP-Atom × OP-Atom | 5,28 | 183 |
| OP-Atom × WAV | 5,54 | 183 |
| mp4 × OP-Atom | 5,28 | 183 |

**Mesmo offset nas quatro combinações.** O nível muda (o RMS do som transcodado saiu
36% menor), a sincronia não. ⭐ Na prática: dá para correlacionar mídia gerenciada
contra arquivo original **indistintamente**, o que é exatamente o que se precisa para
comparar dois caminhos de código e descobrir qual deles está errado.

### 🆕 ⭐ Segunda medição, outro acervo e outra máquina (2026-09-11, Windows) — `confirmado`

Repetida no Ciclo Assist sobre `D:\Avid MediaFiles` (MC 25.6, Windows 11), **1.747 `.mxf`**.
Confirma a rota e acrescenta três números que faltavam:

| o que | medida |
|---|---|
| agrupamento | **1.403 arquivos → 358 clipes**, zero falhas de `material_package_umid` |
| custo do `ffprobe` | **0,033 s por arquivo** (disco local, série) — 58 s a varredura toda |
| segunda varredura | **0,7 s**, com um índice por caminho + tamanho + `mtime` |

⛔⛔ **E a armadilha que ninguém documenta: `._*` do macOS.** **343 dos 1.747** arquivos
eram AppleDouble de 4 KB — a sombra que o macOS deixa ao copiar para um volume que não é
dele (exFAT/NTFS). Cada um custa um `ffprobe` que **falha**, e eles são **um quinto da
pasta**. Filtrar `nome.startswith("._")` antes de sondar é grátis e devolve 20% do tempo.

⭐⭐ **A chave do `ffprobe` é a MESMA de um cache endereçado por MobID.** O
`material_package_umid` vem como `0x060A2B34…` (com o `0x` na frente), e o mesmo
identificador aparece como `urn:smpte:umid:060a2b34.0101…` do lado do Avid/AAF. Normalizando
(tirar o prefixo, tirar os pontos, minúsculas, 64 hex) os dois batem: **as 15 mídias que já
tinham cache foram todas reencontradas na varredura, sem uma linha duplicada.** É o que
permite cruzar "o que existe em disco" com "o que já foi processado" sem um banco central.

⚠️ Para quem vai extrair quadro: `r_frame_rate` do stream de vídeo vem como **fração**
(`24000/1001`) e precisa ser guardada assim. Virar float perde o 23,976 exato, e é dele que
sai a POSIÇÃO do quadro.

### Outras observações da medição

- **Tracks por clipe variam**: 3 (V+2A), 5 (V+4A), 10, e clipes de 1–2 tracks (WAV importado, sem
  vídeo). "Clipe = 1 vídeo + N áudios" **não** é invariante.
- Existem tracks de **dados** (`D01.*`) além de V e A — precisam ser excluídas de qualquer
  tratamento de essência.
- ⚠️ E isso vale **dentro** de um OP-Atom de áudio: medido em 2026-09-11, cada arquivo de som
  trazia **1 stream `audio` + 4 `data`** no `-show_streams`. Contar streams sem filtrar
  `codec_type` faz um clipe de 5 canais aparecer com 25 tracks.
- O **mesmo** `file_package_umid` apareceu em mais de um caminho (cópias entre pastas numeradas):
  deduplicar por UMID, não por nome de arquivo.

## Layout da `Avid MediaFiles` (descoberta) — `confirmado`

- Mídia em `Avid MediaFiles/MXF/<n>/` — subpastas **numeradas** (`1`,`2`,`009`,`1000`…), cada uma
  com os `.mxf` + os bancos `msmMMOB.mdb`/`msmFMID.pmr` (ver [msm](../msm/README.md)).
- **Mídia local do sistema** fica **FORA da raiz do volume**: `/Users/Shared/AvidMediaComposer/` ou
  `/Users/Shared/Avid Media Composer/` (macOS, **duas grafias** conforme a versão);
  `C:\Users\Public\Documents\Avid Media Composer\` (Windows).
- ⚠️ ⭐ **A coluna `Drive` da bin, no Windows, vem como `RÓTULO (LETRA:)`** — valor real lido de
  uma bin: **`SSD (D:)`** (não `D`, não `SSD`). É dela que se monta
  `<volume>/Avid MediaFiles`, então **pegue a letra do parêntese**. No macOS a coluna traz só o
  rótulo e não dói, porque o sistema **monta por nome** (`/Volumes/SSD` é caminho de
  verdade); no **Windows** não há caminho por rótulo, e um `f"{drive}:\"` ingênuo produz
  `SSD (D:):\Avid MediaFiles` — o app reporta *"N clipes não encontrados no disco"* com a
  mídia inteira presente. **Falha silenciosa: nada levanta erro e a culpa parece ser do disco.**
  Medido: 38/38 masters resolvidos, 394 `.mxf` → 103 UMIDs × 3 arquivos, varredura ~20 s em
  exFAT/USB. Regex, plano B por `GetVolumeInformationW` e a armadilha do `SetErrorMode` em
  [plugins/avid-panel-sdk/windows.md §6](../../plugins/avid-panel-sdk/windows.md).
- Classificação de arquivo (MSYNC `rules.go`): `.mxf`→media; `msmMMOB.mdb`/`msmFMID.pmr`→media_db
  (ficam soltos, fora dos grupos); `.avp`→projeto (só na raiz); `.avb`→bin. Pastas de sistema a
  ignorar: `SearchData`, `Statistics`, `WaveformCache`, `Render Files`, `Attic`.

## 🆕 Achar a mídia gerenciada SEM varrer o acervo — `confirmado` 2026-08-23

Medido no Órbita (`DRAMASYNC`) contra mídia real, em dois discos. O problema: a mídia
gerenciada é o único caminho quando o master não tem `Source File`, e a rota óbvia — probar
todo `.mxf` do volume — custa **um processo `ffprobe` por arquivo**.

| acervo | varredura completa, em série | **busca dirigida** | `ffprobe` |
|---|---|---|---|
| HD mecânico, 1404 `.mxf`, 50 masters | **80,98 s** | **~1 s** | 1404 → **200** |
| SSD, 511 `.mxf`, 14 masters | 13,87 s | ~0,5 s | 511 → **72** |

As duas resolvem os MESMOS masters, com os MESMOS arquivos. O que muda é quanto se lê.

### As três peças, e a ordem em que importam

1. ⭐⭐ **A coluna `Tracks` é o SINAL DE PARADA.** `V1 A1-2` = 3 arquivos, `A1-5` = 5. Some
   os masters pedidos e você sabe **quando parar de procurar** — 198 previstos, 198
   encontrados numa diária de 50. Vem de graça no `GetMobInfo` que já se faz.
   ⚠️ Conte por **`file_package_umid` DISTINTO**, não por arquivo lido: o mesmo clipe existe
   copiado entre pastas da `Avid MediaFiles`, e contar arquivo faz um clipe de 3 tracks
   "completar" com o vídeo lido três vezes — parando com o clipe **sem áudio nenhum**.
2. **O nome (`Name`) só ORDENA a fila** — nunca exclui (ver Armadilha 4).
3. **`ffprobe` em paralelo**, teto `min(8, cpu_count)`.

### ⛔ A ordem ALFABÉTICA é pior que aleatória

Quando o nome não diz nada (3ª convenção), a fila cai em ordem de caminho — e a pasta certa
pode ser a última do alfabeto. Medido: `…/MXF/PRODE` vinha depois de `010020260629` e
`BENTIDO-FIELD`, e **o primeiro acerto caía no arquivo 446 de 511**. A parada existia e
nunca chegava a tempo.

Dois consertos, os dois sobre ORDEM, e juntos levaram 511 → **72**:

- **intercalar as pastas sem pista** (round-robin) em vez de concatená-las: o primeiro
  acerto chega nos primeiros arquivos venha de onde vier;
- **pôr na frente a pasta que ACERTOU**, reordenando entre lotes: o Avid grava as N tracks
  de um clipe juntas, então o primeiro acerto revela onde o material está — informação que
  **não existe antes de começar a ler**.

⚠️ **Isto importa mais no Nexis, não menos:** lá a mídia de um projeto vive espalhada por
**uma pasta por estação** (`srvegpaws345060.1`, `ilha_eg_offline_25.1`, …; cinco no projeto
medido), então "a pasta certa" é várias.

### ⚠️⚠️ E a lição de MEDIÇÃO, que vale para além disto

Paralelizar o `ffprobe` rendeu **6,93×** numa amostra de 200 arquivos com cache de sistema
de arquivos quente — e **1,39×** na varredura fria inteira do HD mecânico (4,0× no SSD).

Não é contradição: a amostra media **spawn de processo**, a varredura fria mede spawn
**mais** disco. *Um microbenchmark com cache quente mede a parte barata do trabalho* — e se
a decisão de projeto sair dele, o ganho prometido não aparece em produção.

**Implementação de referência:** `DRAMASYNC/src-python/avid/masters.py::varredura_dirigida`
e `media/opatom.py::probar_muitos`.

## 🆕 ⛔⛔ OP-Atom MPEG-2 com timestamps de 2 em 2: a busca rápida cai no quadro N/2 — `confirmado` 2026-09-17

Medido no transcode do Media Composer da diária `PRODE` (`V01.E69CCE70_1A1641A164487V.mxf`,
MPEG-2 long-GOP 50 Mb/s, 1080p 23,976), com o ffmpeg da máquina do Ciclo Assist (Windows):

```
r_frame_rate=12000/1001   avg_frame_rate=24000/1001   time_base=1001/24000
pts dos pacotes: 1, 3, 5, … (× time_base)  → cada quadro "vale" dois
ffprobe: "cannot find current edit unit for stream 0, invalid index?"
```

- ⛔⛔ **`ffmpeg -ss t -i arquivo` entrega o quadro `N/2`**, não o `N` (6 posições: pedido
  412 → veio 206, 1000 → 500; conferido por diferença de pixel zero).
- ⛔ **Dobrar o tempo NÃO conserta**: acerta até o meio e erra perto do fim (1200 → 1209;
  1230 → 1233; 1234 → nada). Com o índice quebrado e quadros B reordenados, não é escala limpa.
- ⛔ **Decodificar tudo sem `-vsync 0` também mente**: saem **683** quadros de 1236 (o ffmpeg
  descarta para bater 11,988). Com `-vsync 0` saem os 1236.
- ✅ **O que funciona:** decodificar em ordem com `select=eq(n\,N)` e `-vsync 0` — exato, e custa
  decodificar até o último quadro pedido.
- ⭐ **Como reconhecer:** num MXF, `r_frame_rate` = metade do `avg_frame_rate`. No cache do Ciclo
  Assist desta máquina **17 masters** têm essa cara (13 a 11,988 e 4 a 14,985), e os quadros
  guardados deles saíram por busca rápida — **da primeira metade do clipe, na posição errada**.
  O DNxHD OP-Atom gerado pelo Resolve **não** tem o defeito (`r` = `avg` = 24000/1001).
- A armadilha do "`r_frame_rate` pela metade" já estava registrada (entrelaçamento); o novo é o
  **efeito na busca**.

### 🆕 O transcode guarda a fonte no `reel` — `confirmado` 2026-09-17

| quem gerou o OP-Atom | `reel_name` | `reel_umid` | `timecode` |
|---|---|---|---|
| **Media Composer** (transcode de `20240531_PANA2774.mov`, AMA) | `20240531_PANA2774` (o nome do arquivo original, sem extensão) | `…0f00.13000000.80bb92e5…` — o mob físico AMA | o do original (`23:16:47:11`) |
| **DaVinci Resolve 18.5** | `a001_03170214_C001` (o `clipID` do original, minúsculo) | gerado pelo Resolve | o do original (`02:14:47:09`) |

⇒ O convertido **não carrega nada que identifique o original por conteúdo** — só o NOME da
fonte e o TC. No transcode do Avid o `material_package_name` ganha `.new.01`. Como casar os dois:
[`../../transversal/banco-de-midias-compartilhado.md` §8](../../transversal/banco-de-midias-compartilhado.md).

## 🆕 MXF ESCRITO pelo ffmpeg (Laboratório de Mídia) — `confirmado` 2026-10-06

Medido com o ffmpeg 8.1.1 (Homebrew, Mac mini M4) gerando o caso B01 do `laboratorio-de-midia`
(10 s, 1080p25, DNxHD 120 / XDCAM HD 50 / PCM 24 bits) e relido pelo `ffprobe` e pelo verificador
do laboratório (código de barras quadro a quadro, tom e claque de cada canal):

- **OP-Atom (`-f mxf_opatom`)**: um arquivo por stream (vídeo OU um canal de áudio; o áudio pede
  `-mxf_audio_edit_rate <taxa>`). O UL sai `060e2b34.04010102.0d010201.10030000` — o mesmo
  qualificador dos 531 arquivos do Avid medidos acima.
- ⚠️ **O TC do OP-Atom do ffmpeg vem no FORMATO** (`format.tags.timecode`), não na stream como no
  OP-Atom do Avid ([timecode.md](timecode.md) §1). Quem lê "só a stream, porque é OP-Atom" fica sem TC.
  Ler os dois, como manda o §1, cobre ambos.
- ⛔ **Cada arquivo sai com um `material_package_umid` PRÓPRIO**: o `_V01`, o `_A01` e o `_A02` do
  mesmo clipe NÃO compartilham o MobID do master. Pela rota de agrupamento `confirmada` acima (o MC e
  os apps agrupam por esse UMID), **são três clipes, não um**. Gerar o arquivo é fácil; fazer o MC
  adotá-lo como um clipe de três trilhas é a pergunta da bancada (`pendente`).
- **XDCAM HD 50 em OP-1a** (`mpeg2video` 4:2:2, 50 Mb/s CBR, GOP 12 fechado, 8 trilhas PCM mono):
  `r_frame_rate` = `avg_frame_rate` = 25/1 e 250 pacotes = 250 quadros — **sem** o defeito do
  "timestamp de 2 em 2" da seção anterior (que é do transcode do Avid). ⚠️ `-non_linear_quant 1`
  exige `-qmax 28`: sem isso, "non linear quant only supports qmax <= 28" e nada é gravado.
- **DNxHD 120** em 1080p25: `-c:v dnxhd -b:v 120M -pix_fmt yuv422p` (aceito; outras taxas: medir).

Receita e verificador: `PROGRAMAS COM CLAUDE/laboratorio-de-midia` (`lab/formatos.py`, `lab/verificar.py`).

### 🆕 ⛔ O OP-Atom do ffmpeg ROTULA errado — e o Premiere recusa o vídeo (`confirmado` 2026-10-06)

Comparado, set por set (`laboratorio-de-midia/lab/mxf_estrutura.py`, só leitura), com um OP-Atom que o **DaVinci
Resolve 18.5 gravou para o Avid** (`Avid MediaFiles/MXF/0200230405/a001_03170314_C003*.mxf`, DNxHR LB, 23,976):
- ⛔ **O ffmpeg grava a essência CLIP-wrapped (um único KLV de 151 MB) mas declara FRAME-wrapped** no Preface
  (`EssenceContainers`) e no descritor: vídeo `060e2b34 0401010a 0d010301 02110100` (VC-3 frame) e áudio
  `…0d01030102060100` (BWF frame). A referência declara **clip**: `…02110200` (VC-3) e `…02060400` (AES3).
  ⇒ **Premiere 25.6.5: "File Import Failure — Unsupported format or damaged file"** no vídeo (o áudio passa); o
  Resolve 21.1 e o VLC abrem. ✅ **Trocar só o rótulo para clip (mesma largura, 5 ocorrências por arquivo) basta:**
  o Premiere importa e os quadros saem exatos (0, 37 e 249 pelo código de barras). O laboratório corrige depois do
  ffmpeg (`formatos.corrigir_rotulo_opatom`).
- ⛔ **Casar vídeo e áudio:** com a MESMA `material_package_umid` nos três arquivos (troca de bytes), o Premiere
  ainda importa **3 clipes separados** — a identidade sozinha não basta (`confirmado`). Na referência, **cada
  arquivo lista no MaterialPackage as TRÊS trilhas** (`…_v1`, `…_A01`, `…_A02`), cada SourceClip apontando o
  `file_package_umid` do irmão — é por isso que, importando só o vídeo, o Premiere traz o áudio junto. Que a lista
  de trilhas é o que falta: `inferido` (para medir, é preciso gravar o cabeçalho, não trocar bytes).
- O resto do que o Resolve grava para o Avid e o ffmpeg não: o **dicionário AAF** inteiro no cabeçalho (~420 sets de
  definição de classe/propriedade/tipo, e um objeto raiz de chave fora do SMPTE `8053080036210804…`); o pacote de
  **fita** (SourcePackage + `TapeDescriptor`) atrás do pacote de arquivo, com o TC; `Name` no clipe e na fonte e
  `TrackName` (`<clipe>_v1`, `_A01`); a chave da essência no registro do Avid `060e2b34 01020101 0e040301 15010601`
  (ffmpeg: SMPTE `…0d010301 15010600`); no descritor CDCI, `ImageAlignmentOffset` 8192 e duas propriedades Avid
  (ULs `a024006094eb75cbce2aca50…` = 188.416 = bytes por quadro, `…aca4f…` = 2.335.793.152 = bytes da essência);
  essência alinhada em 393.216; Preface versão 1.2 (ffmpeg 1.3). O nome do vídeo é `<clipe>.mxf` (sem `_V01`).
- ✅ **CONFIRMADO (mesmo dia): a lista de trilhas é o que casa vídeo e áudio.** O gravador do laboratório
  (`laboratorio-de-midia/lab/opatom.py`) regrava o cabeçalho dos OP-Atom do ffmpeg: UMA `material_package_umid` nova nos
  três arquivos, e em CADA um o MaterialPackage com TC1 + V1 + A1 + A2 (as trilhas do irmão copiadas com InstanceUIDs
  novos — o ffmpeg repete o mesmo padrão de UID nos três, e copiar sem trocar duplicaria), `Name` no clipe e no
  pacote de arquivo, `TrackName`, rótulo clip-wrapped; essência e índice copiados, partições e RIP recalculados.
  Resultado: **Premiere 25.6.5 importando SÓ o vídeo cria UM clipe com vídeo + os 2 áudios** (quadro 37 exato, claques de
  imagem e som juntas), e o **Resolve 21.1 importa os 3 como UM item "Video + Audio" de 2 canais**. Sem o dicionário
  AAF, sem o pacote de fita e sem a chave Avid da essência — para o Premiere e o Resolve não fazem falta; para o
  Media Composer como mídia GERENCIADA: `pendente` (o código do `bmx` da BBC, `raw2bmx -t avid`, é a referência
  para isso).
- 🆕 **O que o Avid exige — três gravadores comparados (2026-10-06, só leitura):** (1) o próprio **Media Composer 25.6**
  (`Avid MediaFiles/MXF/99999999/V01.6A87F83A…`, XDCAM 50 1080i, `Identification` = "Avid Media Composer 25.6",
  "AAFSDK (Win64)"); (2) o **Resolve 18.5** exportando para o Avid (mídia que o MC usa); (3) o código do **`bmx`**
  (`raw2bmx -t avid`, `src/avid_mxf/AvidTrack.cpp`, `AvidClip.cpp`).
  | peça | MC 25.6 | Resolve→Avid | bmx Avid | leitura |
  |---|---|---|---|---|
  | dicionário AAF (meta-dicionário + dicionário) | ✅ (~500 sets) | ✅ | ✅ sempre (`createDefaultMetaDictionary`/`createDefaultDictionary`) | provavelmente **exigido** |
  | MaterialPackage com TODAS as trilhas, mesma UMID | ✅ (Picture, Audio 0, Audio 1 — sem TC no clipe) | ✅ | ✅ | **exigido** (é o que casa) |
  | chave da essência do Avid (`…0e040301 15010601` p/ DNx) | — (XDCAM: chave própria) | ✅ | ✅ `MXF_EE_K(DNxHD)` | provavelmente exigido |
  | rótulo do container | Avid (`…0e04030102030000`, MPEG) | SMPTE VC-3 clip (`…02110200`) | Avid por compressão (`MXF_AVID_DNXHD_EC_L(0x06, …)`) | o SMPTE clip basta (o Resolve passa) |
  | `ImageSize` + `FrameSampleSize` no descritor | ✅ | ✅ | ✅ | provavelmente exigido |
  | `ResolutionID` (DNxHD = o compression ID: 1237 p/ o 120 1080p; XDCAM 50 = 4073) | ✅ | — | ✅ | opcional? (o Resolve não grava) |
  | pacote de origem (fita/import) atrás do de arquivo | ✅ ImportDescriptor | ✅ TapeDescriptor | só se pedido | **opcional** |
  | DataDefinition | AAF antigo (`807d0060…6f3c8ce1`/`…78e1ebe1`, TC `807f…7f275e81`) | SMPTE | SMPTE (`060e2b34 04010101 01030202 01…`) | os dois servem |
  | `MobAttributeList` (`_PJ` = projeto), `LegacyDMS1` | ✅ | ✅ | ✅ | não se sabe |
  O gravador do laboratório (`lab/opatom.py`) tem só a 2ª linha. Para mídia GERENCIADA do MC, as candidatas são o
  dicionário, a chave Avid da essência e `ImageSize`/`FrameSampleSize` (+ `ResolutionID`); o código do `bmx` (BSD)
  traz as tabelas do dicionário (`deps/libMXF/mxf/mxf_avid_metadictionary*`, `mxf_avid_dictionary.c`). Medir no MC:
  `pendente` (bancada em `/Users/Shared/AvidMediaComposer/Avid MediaFiles`, NUNCA na do SSD, que é protegida).
- ✅⭐⭐ **ÁUDIO: o OP-Atom do ffmpeg + a costura do laboratório entra no MC como mídia GERENCIADA e TOCA**
  (MC **2024.6**, Win11, 2026-11-01, Ciclo Assist — o caminho que substitui "injetar o WAV + consolidar"). Os 4 WAV
  BWF do M06 (estéreo, 24 bits, bext com TC) → por canal: `ffmpeg -af pan=mono|c0=cN -c:a pcm_s24le -f mxf_opatom
  -mxf_audio_edit_rate 25 -timecode <TC do bext a 25> -metadata material_package_name=<nome>` → `lab/opatom.py
  costurar` (A01+A02 com uma UMID e o MaterialPackage TC1+A1+A2) → pasta NOVA `MXF6110131` → a operação de
  importar masters (AAF de masters pelo pyaaf2 `link_external_mxf` + `ImportFile`): **índice em 0,3 s, 4 masters em
  2,2 s, sem queda**; `GetMobInfo`: `Offline ''`, `Drive SSD (D:)`, `Tracks A1-2 TC1`, `PCM 24 48000`,
  Start/Duração = o gabarito; **play no Source: agulha anda e os medidores de áudio acendem**. ⇒ para ÁUDIO o
  dicionário AAF e a chave Avid da essência NÃO são exigidos (vídeo: segue `pendente`).
  ⚠️ **O que se perde:** o `Tape` sai VAZIO (o ffmpeg não grava pacote de fita; o `nomear_fitas` não acha o que
  nomear) e os metadados do BWF (bext/iXML: cena, take, notas) não vão para o MXF. O consolidar do MC guarda
  `TapeID`/`Source File` = o nome do WAV. Escrever o pacote de fita (e o iXML) é o próximo passo, `pendente`.
  ✅ **A FITA, no AAF de masters (mesmo dia):** `SourceMob` + `TapeDescriptor` (pyaaf2 `create_tape_slots(nome,
  edit_rate exata, base do TC)`), uma trilha de som por canal (ids 1, 3, 4… — o 2 é o TC) e a trilha de TC começando
  no TC do clipe; o SourceClip do mob de arquivo de cada canal passa a apontá-la. ⇒ coluna **Tape = o nome do WAV**,
  Start certo, online. ⛔⛔ **O SourceClip para a fita vai com `start = 0`:** com o instante do TC ali (em amostras),
  o MC SOMA os dois — medido Start `20:00:06:00` num clipe de `10:00:03:00`. `TapeID` e `Source File` seguem vazios.
  Ferramenta do Ciclo Assist: `som_direto_gerenciado` (~24 s para 4 WAV, com a indexação no 2º ciclo de foco).


## Identidade UMID (o que importa para relink/AMA)

- O **UMID** é o identificador único da essência. O AMA auto-link do Avid usa o **UMID real** para
  o Media Composer tocar a mídia por identidade (ver [../aaf/escrita.md](../aaf/escrita.md) §AMA).
- `create_ama_link` (pyaaf2) enxerta a essência via UMID. Format-aware: MXF linka direto;
  QuickTime/WAV passam por `ffprobe`.
- **`ResolutionID=4076`** afeta MXF MPEG2/XDCAM (patch do pyaaf2). Para MPEG2 de outras taxas,
  derivar do header. (`pendente`)

## Descriptors MXF relevantes (do lado AAF)

- Para o Avid **tocar** a mídia (AMA), o **descriptor de essência abaixo do MasterMob** precisa
  descrever o **arquivo real** (sub-descriptors + UMID), não o proxy. Ver
  [../aaf/escrita.md](../aaf/escrita.md) §AMA e [../aaf/dados/ama-constantes.json](../aaf/dados/ama-constantes.json).
- `MXFMPEG2VideoDescriptor` — bug no `.link` do pyaaf2 1.7.1 exige patch (`ResolutionID` + delegar
  ao pai). `ResolutionID=4076` = XDCAM HD 50Mbit.
- `MediaContainerGUID` por tipo (MXF/WAV sobrescritos no writer; QuickTime mantém o do pyaaf2).
- ContainerDef "AAFKLV" vem nomeada "MXF" no AAF do Avid (lookup por nome falha — renomear por AUID).

## Essência e codecs (decode de frame) — `confirmado`

O **relink/conform não depende de decodificar** a essência (reescrever o path no AAF não decodifica
nada). O decode só é necessário para a **camada visual** (preview/match). Despacho por extensão/essência
(`RELINKER/frames/decoders.py`):

| Formato | Estratégia de decode |
|---|---|
| MP4, MOV, **MXF**, ProRes, DNxHR | ffmpeg (padrão) |
| EXR, DPX, TIFF, JPEG2000, HDR, PSD | OpenImageIO (`oiiotool`) p/ cor correta; senão ffmpeg |
| BRAW | SDK Blackmagic (helper-CLI) — validado |
| R3D / ARRIRAW / Canon CRM / Sony X-OCN | SDK do fabricante (helper-CLI) |

- **Sony X-OCN é `.mxf`** → detectado **por essência** (codec via pymediainfo, cacheado), não por
  extensão. `sdk_kind(path)` devolve `braw|r3d|arri|canon`; X-OCN cai em `sony`.
- **Camera RAW exige SDK do fabricante** (licença própria) — por isso ficam como helper-CLI externo
  opcional; ausência degrada com elegância (`{needs_sdk, sdk_url}`), nunca bloqueia o relink.

## Sequências de imagem (1 arquivo = 1 frame)

EXR/DPX/CinemaDNG/ARRIRAW costumam vir como `shot.0001.exr…`. O indexer **agrupa** os irmãos (por
pasta+base+ext+padding) num único entry com dict `sequence`; `frame N → arquivo certo` é resolvido
no extractor (`resolve_frame_file`). O parser de AAF **não muda** (a sequência é resolvida no
indexer/extractor).

## Apps que tocam MXF

- **RELINKER** — AMA auto-link, detecção de essência por codec, decode de frame (`ama-autolink.md`,
  `raw-decoders.md`). Fonte primária.
- **MSYNC** (Go) — **scan** da estrutura Avid (`internal/project/scanner.go`, `mxf.go`): agrupa os
  OP-Atom por clipe e, opcionalmente, **lê o nome do clipe do header** (local tag `0x4402`, UTF-16BE)
  sem pyaaf2 — Go puro, 256 KB por arquivo. Ver §Op-Atom acima.
- **LEITOR DE MDB** — obtém os clipes já agrupados lendo o `.mdb` (nenhum MXF aberto). Ver [msm](../msm/mdb-bento.md).
- **DRAMASYNC / Órbita** — a **rota `ffprobe`** (§ acima): agrupa por `material_package_umid` sem
  dependência nova, e usa o MESMO UMID para identificar o master ao autorar a sequência de sync
  para o Media Composer. Ver [plugins/avid-panel-sdk](../../plugins/avid-panel-sdk/).
- Dados: [dados/opatom-grouping.json](dados/opatom-grouping.json).

## A mapear (pendente)
- Estrutura KLV / partitions / index tables do MXF.
- **Nome do clipe do header: resolvido** (local tag `0x4402`, MSYNC — ver §Op-Atom). Falta ler
  **TC embutido e UMID direto do header** por conta própria (hoje via pyaaf2/ffprobe).
- **Op-Atom vs OP1a: resolvido** — `operational_pattern_ul` do `ffprobe`, byte 13 = `0x10` (ver §rota
  ffprobe). Continua `pendente` o **significado do qualificador** (`10000000`/`10020000`/`10030000`).
- **TC da FONTE: resolvido para OP-Atom** (2026-08-14) — está nas tags de **STREAM** do `ffprobe`,
  na stream de essência; `format.tags` não tem o campo. Validado contra correlação de forma de onda
  (3/3 exato). Ver [timecode.md](timecode.md) §1. Continua `pendente` **separar TC de MaterialPackage
  de TC de SourcePackage no caso geral** (Armadilha 1: o mesmo clipe lia `08:12:41:20` numa pasta e
  `01:00:00:00` noutra) — a rota do §1 dá o TC que os NLEs usam, mas não prova de qual package ele veio.

## Fontes
- `RELINKER/docs/ama-autolink.md`, `raw-decoders.md`; `RELINKER/src-python/aaf/writer.py` (`_build_ama_source`).
- `MSYNC/internal/project/mxf.go` (tag `0x4402`, agrupamento), `scanner.go` (layout/descoberta), `rules.go` (classificação).
- `FLATFILE-MULTCAM/src/multicam_rebuild/mxf_inspect.py` (agrupamento por UMID via pyaaf2).
- **DRAMASYNC/Órbita 2026-08-14** — [timecode.md](timecode.md): onde mora o TC de fonte, a faixa
  sintética do MediaInfo, o discriminador por `frame_count`, o áudio OP-Atom que não é BWF, e o
  contra-teste de `comment_Soundroll TC Rate`. Acervos: `MIDIAS DE TESTES/PRODUCAO-F_24FPS/010020260629`
  (396 arquivos, DNxHD 24) e `Avid MediaFiles/MXF/1` (66, XDCAM 50 a 23,976); regressão em
  `MIDIAS DE TESTES/XDCAM50`, `SAMPLE FOOTAGE`, `PRODUCAO-A` (14 arquivos, nenhum regrediu).
- **DRAMASYNC 2026-08-08** — §rota ffprobe e as 3 armadilhas. Medição sobre 540 `.mxf` / 111 clipes
  em `/Volumes/SSD/z ignore o que esta aqui/Avid MediaFiles` (`MXF-original` + `MXF--`).
  ⚠️ A ressalva sobre `reel_name` é **conhecimento de campo do usuário, não da medição**: aquela
  amostra fora convertida pelo DaVinci Resolve, que preenche o Reel com o nome do clipe — ela é
  incapaz de testar a semântica do campo.
- **Laboratório de Mídia 2026-10-06** — §MXF escrito pelo ffmpeg. ffmpeg 8.1.1 (Homebrew, Mac mini M4), caso B01 (10 s, 1080p25) relido pelo `ffprobe` e pelo `lab/verificar.py` (código de barras, tom e claque por canal; 8 arquivos, 0 falhas; o verificador acusou canais trocados, TC deslocado e 1 quadro a menos em arquivos estragados de propósito).

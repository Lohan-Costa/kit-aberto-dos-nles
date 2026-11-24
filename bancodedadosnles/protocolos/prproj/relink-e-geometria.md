# PRPROJ — Relink e geometria: trocar a mídia de baixo de um corte pronto

Descobertas de reescrever um PRPROJ de 64 min para um acervo novo (RED `.r3d` 6K → ProRes
Proxy 1080p, handcam e iPhone renomeados), preservando o enquadramento clipe a clipe.

> ## ⚠️ TUDO NESTA PÁGINA VALE PARA **PREMIERE PRO 2026 (26.0.2)**
>
> Medido e validado numa única versão. **Outras versões podem ter estrutura diferente** — o
> PRPROJ versiona cada elemento individualmente, e o Adobe muda essas versões entre releases.
> Antes de aplicar qualquer coisa daqui a um projeto de outra versão, conferir a impressão
> digital abaixo; onde ela divergir, a descoberta correspondente **volta a ser hipótese**.
>
> **Como saber qual Premiere escreveu um `.prproj`** — o próprio arquivo diz, no `Project`:
>
> ```xml
> <MZ.BuildVersion.Created>22.6.4x2 - Tue Aug 26 22:23:44 2025</MZ.BuildVersion.Created>
> <MZ.BuildVersion.Modified>26.0.2x2 - Thu Sep  3 10:24:14 2026</MZ.BuildVersion.Modified>
> ```
>
> ⚠️ O que vale é o **`Modified`**: este projeto foi *criado* no 22.6.4 (Premiere 2022) e está
> na forma que o **26.0.2** gravou. Não confiar em caminhos de preset (aqui havia um
> `/Applications/Adobe Premiere Pro 2025/…` obsoleto no `IngestSettings`, três anos fora de
> sincronia com quem de fato escreveu o arquivo).
>
> **Impressão digital desta versão** (`PremiereData Version="3"`):
>
> | elemento | Version | | elemento | Version |
> |---|---|---|---|---|
> | `Project` | 45 | | `VideoFilterComponent` | 9 |
> | `Media` | 30 | | `VideoComponentParam` | 10 |
> | `VideoStream` | 22 | | `VideoComponentChain` | 3 |
> | `AudioStream` | 8 | | `VideoClip` | 11 |
> | `Sequence` | 12 | | `SubClip` | 6 |
> | `MasterClip` | 12 | | `VideoClipTrackItem` | 8 |
>
> ⚠️ `Sequence Version="12"` aqui, contra **`Version="11"`** no template de 2024/2025 registrado
> em [estruturas.md](estruturas.md) — prova concreta de que essas versões **mudam entre
> releases**, e de que a impressão digital não é decorativa.

Confiança `confirmado` onde há medida em cima de arquivo real; `inferido` onde só o XML
sustenta. Fonte: `RELINK_PRODUCAO-G/` (PRODUCAO-G / doc de la cordillera), 2026-09-03/04. Amostra:
`docdelacordillera2_1_downgraded2_1_COR_Beta_1.prproj` (242.606 objetos, 7 sequências,
1.094 itens de vídeo, 246 caminhos de mídia), escrito por Premiere Pro **26.0.2** (macOS).
Validado abrindo o projeto relinkado no mesmo Premiere, com a mídia online.

---

## 0. ⚠️ O CONTAINER: o Premiere recusa um gzip com campo `FNAME`

`confirmado` (2026-09-03) — o teste de controle fecha a causalidade: o **XML original, sem uma
única alteração**, regravado com cabeçalho do Python **não abre**; regravado com o cabeçalho
abaixo **abre**.

O `.prproj` é `gzip(XML)`, mas **não é qualquer gzip**. Todo arquivo escrito pelo Premiere
começa com o mesmo cabeçalho de 10 bytes:

```
1f 8b   ID
08      CM  = deflate
00      FLG = 0   ← SEM campo FNAME
00×4    MTIME = 0
00      XFL
13      OS
```

O módulo `gzip` do Python, quando recebe um **caminho** (`gzip.GzipFile(path, "wb")` ou
`gzip.open(path, "wb")`), liga o bit `FNAME` (`FLG=0x08`) e embute o nome do arquivo,
NUL-terminado, logo depois dos 10 bytes — além de gravar `OS=0xff`. O arquivo continua sendo um
gzip válido (`gunzip -t` passa, o `gzip` do Python relê sem reclamar), mas o Premiere responde:

> **The project appears to be damaged, it cannot be opened.**

Sintoma tratável: a mensagem aparece **antes** de qualquer parse de XML, então um projeto
perfeito no conteúdo é rejeitado do mesmo jeito. Não há como distinguir "container errado" de
"XML errado" pela mensagem — daí valer o teste de controle abaixo.

**Como escrever certo** (cabeçalho manual + deflate cru):

```python
import struct, zlib
HEADER = bytes([0x1F, 0x8B, 0x08, 0x00, 0, 0, 0, 0, 0x00, 0x13])

def write_prproj(path, xml_text, level=6):
    data = xml_text.encode("utf-8")
    c = zlib.compressobj(level, zlib.DEFLATED, -zlib.MAX_WBITS)
    with open(path, "wb") as fh:
        fh.write(HEADER)
        fh.write(c.compress(data) + c.flush())
        fh.write(struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data) & 0xFFFFFFFF))
```

(Passar `fileobj=` em vez de caminho para o `gzip` do Python também evita o `FNAME`, mas ainda
grava `OS=0xff`. Escrever o cabeçalho na mão é o único jeito de ficar byte a byte igual.)

> **O teste de controle que isola o problema:** gravar o **XML original, sem uma única alteração**,
> com o seu escritor, e mandar abrir. Se ele falhar, é o container; se abrir, é o conteúdo. Um
> arquivo, um clique, e a bisecção inteira colapsa em duas hipóteses.

> **A lição de método:** `gunzip -t` passar não significa nada sobre o que o NLE aceita. Quando
> um app recusa um arquivo que todas as suas ferramentas aprovam, **compare os bytes do
> container com os de um arquivo que o próprio app escreveu** — antes de suspeitar do conteúdo.

## 0.1 O documento é estritamente ordenado por `ObjectID`

`confirmado` como observação (medido: 242.606 objetos do arquivo real, ordem crescente sem uma
quebra, do `ObjectID=1` ao `239619`, que é também o último objeto do arquivo). Se a ordem é
**exigida** pelo Premiere, ainda não está fechado.

Consequência prática para quem cria objetos: os novos entram no fim do arquivo e precisam de
`ObjectID` acima do máximo existente **e emitidos em ordem crescente entre si**. O erro fácil é
emitir os `Param` antes do componente que os agrupa e dar ao componente o ID menor — a ordem
quebra em cada objeto criado, e nenhum validador de referência acusa (as referências estão todas
íntegras).

## 0.2 Não remover elemento que o Premiere sempre escreve

Método, não fato do formato — mas é o que separa uma edição segura de uma aposta.

Antes de apagar um elemento, medir em que fração dos objetos daquele tipo ele aparece:

```
Media.ModificationState        1519 / 1520   (99,9%)   <- NÃO remover
VideoStream.OriginalColorSpace  245 / 245    (100%)    <- NÃO remover
Media.ContentAndMetadataState   790 / 1520   (52%)     <- a ausência é forma legal
Media.OfflineReason             711 / 1520   (47%)     <- idem
Media.ImporterPrefs             605 / 1520   (40%)     <- idem
VideoStream.SelectedColorSpace  130 / 245    (53%)     <- idem
AudioStream.ConformedAudioPath   46 / 597    (7,7%)    <- idem
```

Quando o campo é universal e o valor antigo não serve mais, **trocar o valor, não apagar o
campo** — e tirar o valor novo de algo que o próprio Premiere escreveu. Aqui, os proxies ProRes
que o montador já tinha importado à mão deram o `OriginalColorSpace` correto de graça:

```json
{"baseColorProfile":{"colorProfileName":"BT.709,10-bit,Display-Referred"},"baseProfileType":1}
```

> Vale para forma também: antes de deixar um `VideoComponentChain` sem `<Components>`, conferir
> que essa forma existe no original (existe: 7 chains sem `<Components>`, sem `<Node>` e sem
> `<DefaultMotion>`). Inventar forma nova é o que quebra.

## 0.3 Todo elemento tem DUAS formas — e a auto-fechada leva atributos

`confirmado`. O Premiere escreve o mesmo campo ora com par, ora auto-fechado **com atributos**:

```
Media.ModificationState    1274 auto-fechadas  ×  245 com par
Media.ImporterPrefs          472 auto-fechadas  ×  133 com par
```

`<ModificationState Encoding="base64" BinaryHash="…"/>` é a forma **majoritária** desse campo.
Uma rotina de remoção que só cubra `<Tag>…</Tag>` e, como plano B, `<Tag/>` (sem atributos)
falha **em silêncio** na maioria dos casos: nada é removido, nada acusa erro, e o resultado é
uma remoção **parcial** — pior que nenhuma, porque deixa o arquivo meio-editado.

Testar a forma auto-fechada **primeiro**: se o elemento não tem par e existe outro de mesmo
nome adiante no corpo, a regex do par engole tudo no meio.

```python
m = re.search(r"\n\t\t<%s(?:\s[^>]*)?/>" % tag, body)          # auto-fechada, com atributos
if m is None:
    m = re.search(r"\n\t\t<%s(?:\s[^>]*)?>.*?</%s>" % (tag, tag), body, re.S)
```

## 0.4 `ModificationState` e `ContentAndMetadataState` são UM PAR

`confirmado`. O blob base64 de `ModificationState` é o **GUID de `ContentAndMetadataState`
codificado em UTF-16LE**. Medido: 235 `Media` em que a igualdade é exata, 0 contraexemplos
(nos demais o `ContentAndMetadataState` é o GUID zerado e o blob é binário de verdade).

```python
base64.b64decode(modification_state).decode("utf-16-le") == content_and_metadata_state
```

> **Consequência:** remover um e manter o outro deixa o par inconsistente. Ou saem os dois, ou
> nenhum. E como são cache de conform — o Premiere reconforma a mídia nova de qualquer jeito —
> a opção barata é **não tocar em nenhum dos dois**.

## 0.5 A escada de bisecção que isola a edição que quebra

Editar um projeto pronto tem muitas mudanças independentes, e o Premiere responde a todas com a
mesma frase. A saída é gerar uma **escada cumulativa**, do mínimo ao completo, e deixar o
montador abrir de baixo para cima. Nesta sessão:

| variante | conteúdo | abriu? |
|---|---|---|
| controle | XML original, só recomprimido | ✅ |
| N1 | caminhos + escala | ✅ |
| N2 | + `FrameRect`/`CodecType` | ✅ |
| N3 | + limpeza de caches, `ImporterPrefs`, espaço de cor | ❌ |
| N4 | + remoção do `AE.ADBE RED.SourceSettings` | ❌ |

Duas lições de método: (1) **cada degrau tem de ser um projeto utilizável**, não um passo
técnico — assim o montador para de testar assim que tem o que precisa; (2) depois que a escada
aponta o degrau, o degrau se quebra em **flags independentes** (uma por operação), não em mais
degraus cumulativos — é o que separa "está no nível 3" de "é este campo".

## 1. `Motion > Scale` é relativo aos PIXELS NATIVOS da fonte

`confirmado`. 100% não é "caber no quadro": é a fonte mapeada 1:1 nos pixels da sequência.
Uma fonte 3840 de largura numa sequência 1920 a 100% aparece com **2× de punch-in**.

A prova está nos próprios valores do corte: os clipes 3840×2160 se acumulam em `Scale = 50`
(= 1920/3840) e os 5760×3240 em `33,333` (= 1920/5760) — o montador digitou o *fit* na mão.

> Consequência: **trocar a mídia por uma versão menor sem mexer na escala destrói o
> enquadramento.** É o que acontece no relink pela UI do Premiere, e é o motivo de existir
> desta página.

### A fórmula do relink

```python
scale_novo = scale_antigo * (largura_da_fonte_antiga / largura_do_arquivo_novo)
```

`Position` e `Anchor Point` **não mudam**: são normalizados (`0.5:0.5` = centro) e o centro da
imagem continua no centro do canvas. Vale inclusive quando a conversão letterboxou a imagem,
porque a tarja é simétrica (§3).

Medido: 662 itens reescritos em 3 fatores (2,0 / 3,0 / 3,2), com verificação
`largura_da_fonte × scale/100` idêntica antes e depois — **0 divergências**.

## 2. `<ShouldScaleMedia>` e `<DefaultMotion>`: o que é "sem Motion"

`confirmado` (leitura) / `inferido` (semântica).

- **`<ShouldScaleMedia>false</ShouldScaleMedia>`** vive no bloco de settings do projeto (perto de
  `ActionSafeWidth`/`TitleSafeWidth`). É o "Default Media Scaling" das preferências. Com `false`,
  a mídia entra em 100% nativo.
- Um `VideoComponentChain` de item cujo Motion **nunca foi tocado** não tem componente de Motion
  nenhum. Em vez disso carrega:
  ```xml
  <DefaultMotion>true</DefaultMotion>
  <DefaultMotionComponentID>2</DefaultMotionComponentID>
  ```
  Medido: 280 chains assim, e **nenhum** deles com componente Motion; os 813 que têm Motion
  **não têm** `<DefaultMotion>` nem `<DefaultMotionComponentID>`. As duas formas não coexistem.
- Não existe flag `ScaleToFrameSize` em lugar nenhum do arquivo: quem foi "Set to Frame Size"
  tem o número escrito no `Scale`.
  > **CORRIGE (2026-10-02):** vale para o **Set** to Frame Size (que grava o número). O
  > **Scale** to Frame Size (o "escalar ao quadro" dinâmico, com `Scale` = 100) TEM flag:
  > `<ScaleToFramePolicy>1</ScaleToFramePolicy>` no `VideoClip` — ver §10.1. O projeto
  > da cordilheira simplesmente não usava esse modo.

> ⚠️ **A armadilha do relink:** esses itens são invisíveis para um script que só procure
> componentes de Motion — e são exatamente os que mais quebram, porque 100% nativo numa fonte
> 3× maior vira 3× de zoom. Materializar o Motion é obrigatório.

### Materializar um Motion (o que o Premiere aceita)

Clonar um Motion existente do próprio projeto (11 `Param`, na ordem
`Position, Scale, Scale Width, <uniforme>, Rotation, Anchor Point, Anti-flicker, Crop L/T/R/B`),
com `ObjectID` novos, e no chain:

1. apagar `<DefaultMotion>` **e** `<DefaultMotionComponentID>`;
2. inserir `<Component Index="0" ObjectRef="…"/>` (Motion é intrínseco: vem primeiro) e
   reindexar os demais;
3. o `<ID>` do componente novo = o valor que estava em `<DefaultMotionComponentID>` — é o que o
   Premiere tinha reservado. (`<ID>` **não** é único dentro do chain: em 780 chains o Motion tem
   `ID=1` convivendo com `DefaultOpacityComponentID=1`.)
4. chain sem nenhum componente **não tem** elemento `<Components>` — criar o bloco inteiro.

Validado: 75 Motion materializados, projeto reabre e parseia, zero referência quebrada.

## 3. Como ler a conversão que o Resolve fez (fit vs crop vs stretch)

`confirmado` — e é medição de imagem, não de metadado, porque o metadado não conta.

Um proxy 1920×1080 vindo de uma fonte que **não é 16:9** pode ter sido *fit* (tarja preta),
*fill* (corte lateral) ou *stretch* (distorção). Os três dão um arquivo 1920×1080 com SAR 1:1 —
indistinguíveis por `ffprobe`.

**`cropdetect` mente aqui:** o data burn-in do Resolve (nome do arquivo + `SRC TC`) é desenhado
**dentro da tarja preta**, então `cropdetect` acha conteúdo na linha 1079 e reporta
`crop=1920:1080` — sem tarja. Foi o que quase enterrou a medição.

**O que funciona:** média das linhas ao longo de vários quadros, em clipes claros, procurando
as linhas exatamente pretas nas bordas.

```
6144×3240 → imagem nas linhas 33..1046 = 1012,5 px  (= 3240 × 1920/6144)  → FIT, com tarja
5760×3240 → linhas 0..1079                                                → full bleed
3840×2160 → linhas 0..1079                                                → full bleed
```

E o fit se encaixa na mesma fórmula do §1: o fator é sempre `largura_fonte / largura_novo`
(6144/1920 = 3,2), porque a imagem foi encaixada **pela largura**.

> **Efeito colateral útil:** depois da compensação, a tarja (e o burn-in dentro dela) sai de
> quadro sozinha. Medido: 229 dos 238 itens 6K ficam limpos; nos grupos full-bleed, o burn-in
> fica sobre a imagem e só sai quando o `scale` novo passa de ~107%.

## 4. Relink: fazer o que o Premiere faz, e nada além

`confirmado`. ⚠️ **Esta seção substitui uma versão anterior que mandava remover `ImporterPrefs`
e o componente `AE.ADBE RED.SourceSettings`. Estava errada** — as duas coisas eram invenção
nossa, e a medição abaixo desmente.

### 4.1 `<OfflineReason>` é O flag de offline

A correlação é perfeita no projeto real: `<OfflineReason>5</OfflineReason>` está em **exatamente
os 711 `Media` cujo arquivo não existe** e em **nenhum dos 78 que existem**. Zero exceções.

> **Sem removê-lo, o projeto abre com tudo offline** — o Premiere confia no flag e não tenta o
> arquivo novo, por mais correto que o caminho esteja. É o único campo que separa "relinkado" de
> "relinkado e online", e o erro é invisível em qualquer verificação estrutural: o XML está
> perfeito, as referências íntegras, e o projeto abre vazio.

### 4.2 O oráculo: um clipe relinkado À MÃO dentro do próprio projeto

Um projeto em produção quase sempre tem um ou dois clipes que o montador já relinkou pela UI.
Esse `Media` é a **resposta escrita pelo próprio Premiere** para a transformação que se quer
automatizar — reconhecível porque o `MediaFileHistory0` ainda aponta para o arquivo antigo.

Achar e diffar contra ele vale mais que qualquer raciocínio sobre o formato. Medido em dois
casos independentes, `.r3d` → ProRes, com resultado idêntico:

| campo | o que o Premiere faz |
|---|---|
| `FilePath`, `ActualMediaFilePath`, `RelativePath`, `Title` | troca pelo arquivo novo |
| `OfflineReason` | **remove** |
| `Start`, `TapeName`, `LogComment` | **remove** (metadado que só o R3D carrega) |
| `AlternateTapeName` | troca pelo `reel_name` do arquivo novo (`…_001`) |
| `ImporterPrefs` | **MANTÉM** ⚠️ |
| `ModificationState` + `ContentAndMetadataState` | **MANTÉM** ⚠️ (valores novos, mas presentes) |
| `FileKey` | mantém (valor novo; não correlaciona com online/offline) |
| `AlternateStart`, `UseAlternateStart`, `MediaFileHistory*` | mantém |
| `AudioStream`, `ConformedAudioRate` | **acrescenta** ao conformar |
| `VideoStream.FrameRect` / `CodecType` / `OriginalColorSpace` | atualiza para o arquivo novo |
| `VideoStream.SelectedColorSpace` + `IsColorSpaceSelected` | **remove** (era o override "interpretar como Red Log3G10") |
| `MasterClip` → `AE.ADBE RED.SourceSettings` | **MANTÉM na cadeia** ⚠️ |

O `ImporterPrefs` do ProRes relinkado é, byte a byte no começo, o mesmo blob do R3D
(`GQAAAAEAAAAAAwAAAAAgskUA…`, com a string `As Shot` dentro): o Premiere carrega o blob adiante
em vez de descartá-lo. E o `MasterClip` mantém o nome antigo (`…_005.R3D`) — o nome da bin não
acompanha o arquivo.

### 4.3 O que sobra de específico da RED

Só o espaço de cor tem efeito na imagem: `IsColorSpaceSelected=true` +
`SelectedColorSpace = Red Log3G10/Wide Gamut` é o override "interpretar este clipe como Log".
Sobre um ProRes que já é Rec709, isso lava a imagem. O `OriginalColorSpace` correto vem do
próprio oráculo:

```json
{"baseColorProfile":{"colorProfileName":"BT.709,10-bit,Display-Referred"},"baseProfileType":1}
```

### 4.4 `OriginalColorSpace` o Premiere refaz; o override, não

Distinção que economiza trabalho: `OriginalColorSpace` é **detectado** do arquivo e o Premiere o
reescreve ao conformar a mídia nova (o oráculo prova: era `Red Log3G10/Wide Gamut` e virou
`BT.709,10-bit` no mesmo objeto `Media`). Já `IsColorSpaceSelected` + `SelectedColorSpace` são a
**escolha do usuário** em *Interpret Footage*, e o Premiere **não** mexe nelas.

Logo, num relink só o **override** precisa de ação. No mesmo projeto havia 12 clipes de iPhone
declarados `BT.2100 HLG` cujo proxy saiu Rec709 — parecia erro de cor a corrigir, e não era:
nenhum deles tinha override, então o Premiere se acerta sozinho ao conformar. Já os 130
`VideoStream` de RED tinham `IsColorSpaceSelected=true` apontando para Log3G10 sobre um ProRes
Rec709 — esses sim lavariam a imagem, e é por isso que o override sai.

`ImplementationID` **não** distingue importer por codec: R3D, MOV, MTS e WAV compartilham
`1fa18bfa-255c-44b1-ad73-56bcd99fceaf`. O que muda é a mídia sintética (Bars and Tone, Black
Video), que usa `42008e7a-de6f-4270-96de-7e287abb9b4b`, tem `FilePath` **numérico** e nenhum
arquivo em disco — um relinker tem de reconhecer e pular.

> **A lição, que é a do banco:** para saber o que escrever, **faça o Premiere escrever**. Aqui
> ele já tinha escrito, dentro do arquivo que estávamos editando, e três hipóteses razoáveis
> (`ImporterPrefs` é da RED, o filtro RED não vale em ProRes, o cache de conform atrapalha)
> morreram na primeira comparação.

## 5. `InPoint`/`OutPoint` são relativos ao ARQUIVO — `Start`/`AlternateStart` são só exibição

`confirmado`. Medido em 692 `VideoClip` de R3D: `InPoint` sempre na faixa da duração do próprio
clipe (0 na esmagadora maioria; 1412 s num take de 1729 s), nunca no valor absoluto do TC
(~20.000 s).

> Consequência para quem relinca: **trocar `Start`/`AlternateStart` não desloca corte nenhum.**
> É o medo mais razoável de quem faz isso na mão, e é infundado.

## 6. `AlternateStart` = TC × 1001/1000 em 23,976

`confirmado`, em 92 de 92 clipes. O TC da RED (`05:42:55:23`) lido a 24 fps dá 20.575,96 s; o
`AlternateStart` do projeto traz 20.596,53 s. A razão é **exatamente** 1,001 — o `AlternateStart`
está em segundos reais (tempo de relógio), e o TC 23,976 corre 0,1% devagar.

Útil como **teste de identidade** entre o bruto e o proxy: se o `AlternateStart` do projeto ÷
1,001 bate com o `timecode` do arquivo novo, é o mesmo clipe.

### 6.1 No Premiere 26 o TC vem em `<Start>` — e a prova de identidade dispensa o proxy (2026-10-09)

`confirmado` (Premiere 26.0.2, caso R02 do PRODB, lido no Windows): o `Media` do proxy ALEXA traz
`<Start>14237152272000000</Start>` (+ `<TimeDisplay>100</TimeDisplay>`) e **não** `AlternateStart`.
`Start` ÷ 254016000000 = 56048,25 s; × 24 (a taxa da mídia, 24,000) = 1.345.158 quadros = **15:34:08:06**,
exatamente o TC do original ARRIRAW (`A044C013_240725_R1X0.mxf`). O MOV de celular não tem o campo (sem TC).
O `VideoStream` do mesmo `Media` dá `Duration` (ticks; 39,958 s = a do original), `FrameRect` (o raster do
PROXY) e `CodecType` = FourCC em inteiro big-endian (1634755439 = `apco`, ProRes Proxy; 1212503619 = `HEVC`).

Uso (De Lá Pra Cá, `prproj/leitura._midia_no_projeto` → `originais.casar_um`): quando o proxy NÃO está no
disco (o colorista recebe o .prproj e os originais), duração + TC + raster/codec do projeto conferem o
candidato de mesmo nome — antes, sem o proxy, o nome decidia sozinho (bugs-do-mundo-real B107). Regra:
quadros do TC = `round(ticks / TPS × taxa da mídia)` — em 23,976 o mesmo que o §6 (tempo real × 24000/1001).
`AlternateStart` × `Start` no mesmo `Media` (qual vence?): `pendente`; o código lê `AlternateStart` primeiro.

### 6.3 Acima de 30 qps o TC do projeto e o do arquivo podem estar em BASES diferentes (2026-10-18)

`confirmado` (Premiere 22.6 → .prproj de 2023 do R04 PRODUCAO-C, lido no Windows; arquivos convertidos
pelo Resolve Studio 21 do Mac, `encoder = Blackmagic Design DaVinci Resolve Studio`). A prova do §6.1 recusava
como "timecode diferente" arquivos que eram o mesmo plano:

| arquivo | o projeto diz (Start × taxa da mídia) | o arquivo diz (ffprobe `timecode`) | o mesmo instante |
|---|---|---|---|
| `C0296.MP4` (Sony 100p) → `C0296.mov` 100p | `21:01:03:22` a 100 | `21:01:03:44` a 100 | 22/50 = 44/100 = 0,44 s |
| `JUL_7671.mp4` (proxy 60p de um 100p) → `.mov` 100p | `19:31:26:10` a 60 | `19:31:26:34` a 100 | 10/30 = 0,333 × 0,34 |
| `JUL_7672.mp4` (idem) | `…:58:12` a 60 | `…:58:42` a 100 | 12/30 = 0,40 × 0,42 |
| `JUL_7680.mp4` (idem) | `…:15:09` a 60 | `…:15:32` a 100 | 9/30 = 0,30 × 0,32 |

Leituras: (1) o campo de quadros de um TC acima de 30 qps pode correr na METADE da taxa (o 100p da Sony em
base 50; o MP4 60p em base 30 — o mesmo do `avb/escrita.md`, "TC do MP4 sem tmcd"), e cada programa grava de
um jeito; (2) o proxy em outra taxa ARREDONDA o início do original para a grade dele (para baixo: 0,42 → 0,40).
Regra no De Lá Pra Cá (`prproj/originais._tc_confere`): cada TC na taxa do SEU arquivo; vale o mesmo instante
em qualquer das leituras da base (cheia ou metade, só acima de 30 qps); mesma taxa = exato; taxas diferentes =
até 1 quadro da base mais grossa. A extensão nunca entrou nessa prova — "o .prproj previa .mp4" era o TC.

No mesmo caso: sem o proxy nesta máquina, um arquivo de mesmo nome com raster e codec IGUAIS aos que o projeto
declara não é original, mas é a PRÓPRIA mídia do editor em outro lugar (16 PRJ-*.mov e os .mov de 100p) — o
De Lá Pra Cá aponta a timeline para ela (`realocado`) em vez de entrar offline. Imagem parada e som (sem proxy)
se acham pelo nome INTEIRO. O caminho UNC (`\\169.254.100.100\…`) segue recusado antes de qualquer toque no
disco; só o NOME dele vai à busca nas pastas indicadas.

### 6.4 Tempo e encaixe são os do ARQUIVO apontado, não os do `Media` declarado (2026-10-18)

`confirmado` (o mesmo .prproj de 2023 do R04, Premiere 22.6, contra o projeto resgatado no 23.2 e a referência
renderizada; Resolve 19.1.4 pelo app). O `VideoMediaSource` aponta o ORIGINAL em `MediaSource › Media` e o proxy anexado
em `MediaSource › Content › ProxyMedia` (cada um com o seu `VideoStream`: Sony 3840×2160 a 100p; proxy 1024×540 a 60p).
O corte (entrada em ticks, velocidade, Motion) é o MESMO do resgatado, que aponta direto para os proxies — mas:
- **Tempo:** a fonte do clipe é contada em ticks; a taxa do `Media` só converte em quadros. Convertida pela taxa do
  original (100) e aplicada a um arquivo de 60, a entrada caía em outro instante (40 planos). Com a taxa do arquivo
  apontado: 80/80 planos com a mesma entrada, duração e velocidade do resgatado.
- **Encaixe:** o `Scale` é relativo aos pixels do ORIGINAL (§1), e o Premiere estica o proxy sobre o raster do original.
  O fator para o arquivo apontado é o retângulo do original encaixado ÷ o do arquivo encaixado, por eixo (aqui ×1,0667 na
  altura). Sem o proxy declarado e com outra proporção, o modo da conversão não está no projeto (§6.2).
- ⛔ Limite: o projeto de 2023 tem 29 planos com `Scale 50` para mídia que o PRÓPRIO projeto declara 1920×1080 (ou
  1024×540) — os dois `Media`, original e proxy, dizem 1920. Os 50 % foram digitados para o 4K da câmera
  (`MediaFileHistory` → `J:\…\master\`) e o projeto foi relinkado a cópias sem corrigir a escala: o próprio Premiere os
  mostra com metade do tamanho. O raster de então não está no arquivo — `pendente` (laboratório, pedido B22).
  Inferência que reproduziu o resgate à mão nos 29 planos: suspeito = arquivo com plano menor que o encaixe; fator =
  1 ÷ o menor zoom entre os suspeitos da mesma câmera (prefixo do nome) e do mesmo raster declarado (×2, ×3,75). No
  De Lá Pra Cá é OFERTA ao editor, nunca automática (autor, 2026-10-18) — com ela aceita, 144/144 conferem.
- ⚠️ O `Media` PRINCIPAL também pode ter sido relinkado a um proxy esticado (JUL_7672: principal = `Proxies\…mp4`
  1024×540, histórico = o `M4ROOT` 3840×2160; o anexado é um .mov 1920×1080). Pela regra do Premiere o anexado é
  esticado sobre o principal: a imagem sai a 1,896:1 com tarja — fiel ao projeto, diferente do resgate (0,87–0,90).
  No De Lá Pra Cá também é OFERTA ("a proporção do arquivo apontado", autor 2026-10-18), só quando o principal foi
  RELIGADO — o histórico (`MediaFileHistoryN`) aponta outra pasta de cima ou outro nome; mudar só o disco (`J:` → `I:`)
  não conta (o Grupo A, originais da câmera com proxies anexados, tem histórico de outros discos e NÃO entra). Com as duas
  ofertas aceitas: 144/144, média 0,9915 (Resolve 19.1.4, rodadas I e K).
- ⛔ A MÁSCARA não acompanha a escala órfã: no Premiere ela é presa à fonte (vértices normalizados nela). Medido nas
  rodadas I × J (2026-10-18): no resgatado à mão só as máscaras do nest `transicao-poste` (V3/V4) foram refeitas
  (v' = 0,5 + (v − 0,5) ÷ 2, suavização 100 → 50 px) e as da V2 não; transformá-las pelo fator derrubou dois pontos
  (0,80 → 0,25). Os 0,79–0,86 que sobram nesse nest são a edição à mão do resgate, não a tradução. `confirmado`.
- Bug do mundo real: `transversal/bugs-do-mundo-real.md` B109.

### 6.5 O arquivo do projeto DENTRO das pastas indicadas é "encontrado" — o mesmo critério do AAF (2026-10-19)

Laboratório B23_PROTOCOLOS (`laboratorio-de-midia/resultados/B23_PROTOCOLOS/RESOLVE.md`, Resolve 19.1.4): a mesma
sequência B22 pelo `.prproj` e pelo AAF do Premiere. O AAF dava a mídia como "encontrada"; o `.prproj` dava "sem original"
(e o marcador REFAZER) para o MESMO arquivo, porque o casamento do `.prproj` tratava todo arquivo do projeto como proxy
e excluía o próprio da busca. Regra agora (`prproj/originais.casar_um(raizes=…)`): o arquivo do projeto, existindo no
lugar dele e dentro de uma das pastas que o editor indicou, é a mídia apontada → `proprio`. ⛔ A CÓPIA achada noutro
lugar (`realocado`) continua "sem original": sem o arquivo do projeto nada diz se ela é o original ou uma cópia do proxy
(PRODB: o ProRes Proxy copiado ao lado do ARRIRAW, `test_casamento_sem_proxy`). Depois: B22 6/6 pelos dois protocolos;
PRODC resgatado 144/144 com as 48 mídias "encontradas" (antes 47 com REFAZER à toa). `confirmado`.

### 6.2 ⛔ CORRIGE (2026-10-09): a regra das larguras só vale com a MESMA proporção e pixel quadrado

`confirmado` no laboratório (caso **B11_RELINK**, Premiere 23.2.0 Windows, `laboratorio-de-midia/resultados/B11_RELINK/`):
o `scale × largura_antiga ÷ largura_nova` do PRODUCAO-G (acima, e no `RELINK_PRODUCAO-G`) foi medido com convertidos de MESMA
proporção (RED 6K → 1080p). Com o convertido feito de outro jeito, ela ERRA — e a conferência pela imagem pega:

| convertido | regra das larguras | fator certo | correlação (larguras × certo) |
|---|---|---|---|
| mesma proporção (UHD → HD), tarja (4K DCI → HD fit) | acerta | = | 1,000 × 1,000 |
| recorte (4K DCI → HD fill) | 0,469 | 0,5 (pela ALTURA) | 0,291 × 1,000 |
| stretch (4K DCI → HD) | 0,469 | 0,469 × 0,5 (Scale Width à parte) | 0,699 × 1,000 |
| vertical 1080×1920 → HD com pillarbox | 1,778 | 0,5625 | 0,091 × 0,999 |
| anamórfico 1440×1080 PAR 2 → HD | 1,333 | 0,667 | 0,030 × 1,000 |

**O fator certo é a escala do CONTEÚDO**: pixel do original já desespremido (largura × PAR) → pixel do convertido — `min`
das razões no fit, `max` no fill, as duas no stretch. O Premiere mede o Scale sobre a largura VISTA (com o PAR). ⚠️ O
`.prproj` não diz como o convertido foi feito: o modo tem de vir da IMAGEM do convertido (tarja = fit) ou da conferência
(tentar os candidatos e ficar com o que confere).

**B12_RELINK_MAIS (mesmo dia, mesma bancada, `resultados/B12_RELINK_MAIS/PREMIERE.md`):**
- O fator do conteúdo acerta scope 2,39, 4:3 e quadrado com tarja ou deformados; a regra das larguras erra todos.
- ✅ **O 23.2 LÊ o metadado de rotação de 90°** do original (matriz de exibição): o convertido feito já girado só
  confere com o fator do original VISTO em pé. ⛔ **Matriz de FLIP (espelhada, como o ffmpeg grava): o 23.2 pinta
  PRETO**, online, também importado direto — avisar.
- ⛔ **Tempo: o convertido que é um TRECHO do original** (o "offline recortado" do RELINKER) precisa de slip (in e out
  andam juntos, pela API) — e a conferência pela imagem NÃO vê o erro num plano parado (0,924 > 0,75). O deslocamento
  vem do TC (contenção: o TC do convertido dentro do do original); com TC zerado, só a imagem com movimento.
- ✅ **Canais 6 → estéreo:** cópia + `importSequences` relinka SEM o modal de conflito de trilhas do relink pela
  interface; o mapeamento fica o do convertido (o que toca: `pendente`).

**B13_MONTAGENS (mesmo dia, 23.2.0 Windows, `laboratorio-de-midia/resultados/B13_MONTAGENS/PREMIERE.md`)** — o relink
com o que o editor monta por cima (pares FIT e DCI "crop to fill", fator 0,5), correlação após desfoque de 2 px:
- ✅ **Nest (escala dentro e no próprio nest), nest dentro de nest, adjustment layer com Transform, Transform no clipe e
  Motion completo (Position, Rotation, Anchor): basta o fator na Scale do CLIPE** (0,999–1,000). A correção DESCE nos
  nests (o clipe relinkado mora na sequência de dentro) e não toca o clipe do nest (raster da sequência). Position,
  Anchor e o Transform são normalizados e acompanham.
- ⛔ **O Crop é percentual da FONTE e NÃO acompanha o convertido que perdeu parte do original** (fill): 0,970 sem
  remapear — e PASSA no limiar 0,75 da conferência. `crop_orig = (crop_conv × visível + margem) ÷ original` por eixo,
  com `visível = convertido ÷ fator` centrado e `margem = (original − visível) ÷ 2` (negativa com tarja; resultado ≥ 0):
  L15 → 17,19 no 4096 → 1,000. Mesma proporção (FIT): nada muda. Lado com Crop 0 → a margem (reproduz o convertido;
  decisão de desenho a confirmar com o autor). `confirmado` (23.2, GPU e CPU — 2 rodadas; 25/26 `pendente`).
- Adjustment layer no arquivo: um **Black Video** sintético com `<IsAdjustmentLayer>true` no `MasterClip` e
  `<AdjustmentLayer>true` no `VideoClip` (mestre e os da timeline) — o mesmo no projeto real do PRODB (26.0.2). ⛔ Com
  Transparent Video + as marcas o 23.2 diz que é adjustment e o efeito não age.

**Caso real R04 (PRODUCAO-C, 2026-10-09, `MIDIAS DE TESTES/…/_DeLaPraCa/03 CASOS/REAL/R04 PRODUCAO-C/CASO.md`):**
o projeto NÃO guarda em qual raster o editor montou — o `FrameRect` é o do último relink (aqui, já errado). Num corte
real cada plano foi montado sobre uma versão diferente do mesmo material (UHD, 1920, 960, proxy 1024×540 DEFORMADO de
UHD). Medido contra o vídeo de referência (133 pontos): só relink 21; "tudo foi UHD" 112; **a REGRA "a menor versão
(o arquivo, 1920, UHD) que, com a Scale do editor (o menor keyframe), ENCHE o quadro" 123** — sem usar a referência.
Ambíguos (mais de uma versão enche): 13 de 76 clipes, TODOS com Scale = 100 (o padrão); a regra errou 2, que se
resolvem propagando o raster já decidido de OUTRO uso do mesmo arquivo (Scale 50 → só a UHD enche) ou da FAMÍLIA
(os outros arquivos do mesmo drone) — `inferido`, a aplicar e medir. Sem referência, o que restar ambíguo vai para o
editor (memória "empate é do editor").
⛔ CORRIGE (2026-10-10, medido): PROPAGAR NÃO SERVE — a família MAVO era "unânime em UHD" (pelos planos de Scale 50) e
erraria 8 ambíguos certos em 1920; o MESMO arquivo foi montado em UHD num plano e em 1920 noutro (o editor relinkou
durante a montagem): o raster da montagem é do USO, não do arquivo. ✅ O que resolve os ambíguos é a BUSCA PELA
REFERÊNCIA: renderizar as duas hipóteses (a menor e a maior versão que enchem) e ficar, por clipe, com a que bate com
o vídeo de referência (0,9999 × 0,1–0,4 — separação nítida). Resultado final do caso: 126/133 pontos + 18 densos; o que
sobra é fonte faltando e um plano que a referência tem de outra edição. ⚠️ Com duas camadas no mesmo ponto a decisão é
do clipe (uma camada pede a menor, a outra a maior no mesmo quadro).
⛔ **Keyframes de escala (medido 2026-10-10, 23.2):** o keyframe do `.prproj` é
`tempo,valor,tipo,?,vel_entrada,influência_entrada,vel_saída,influência_saída` (tipo 5 = Bézier; as VELOCIDADES estão
na unidade do VALOR). Corrigir a escala pela API estraga a curva: `setValueAtKey(t, v × f)` multiplica o valor e só UMA
velocidade (a do 2º keyframe ficou a antiga); a largura criada para a escala não uniforme (`addKey` + `setValueAtKey`)
sai com alças de reta; `setInterpolationTypeAtKey` não muda nada (sem acesso às alças). Resultado: no meio de um zoom a
imagem ficou até 13,7 % mais larga. ✅ No ARQUIVO: a curva original × fator em valores E velocidades, tipos e
influências iguais (largura = a curva da altura × fx) — razão constante. Regra para o escritor da cópia: a escala vai
corrigida NO XML, não pela API, sempre que houver keyframes.

## 7. Áudio da RED: `StreamNumber` sobrevive à conversão

`confirmado`. Um `.R3D` com 4 canais vira 4 `Media` (`StreamNumber` 1..4) + 1 `Media` de vídeo.
O proxy do Resolve preserva a contagem: 76 arquivos de 4 canais → 4 pistas mono; 8 de 2 canais →
1 pista estéreo. Os 540 itens de áudio de RED nas timelines pedem canais que o proxy tem —
**0 fora do alcance**. Ou seja: o relink de áudio de RED é só troca de caminho.

## 8. Ambiguidade de nome se resolve por `FrameRect` + duração

`confirmado`. Num acervo desduplicado, `00043.mts` casa com `PRE_00043.MTS`,
`250515_00043.MTS` e `250517_00043.MTS`. As três chaves do projeto separam sem chute:
o `FrameRect` do `VideoStream` (1920×1080 elimina a cópia 1440×1080 anamórfica) e o
`Duration` do stream (114,6 s vs 24,5 s). Quando as candidatas são byte-idênticas (mesmo
tamanho **e** mesma duração), não há ambiguidade real — qualquer uma serve.

## 8.1 R3D: o projeto aponta para UM segmento, a duração é do CLIPE inteiro

`confirmado`. Um clipe da RED é uma pasta `.RDC` com N arquivos `_001.R3D`, `_002.R3D`… e o
`Media` do projeto aponta para **um** deles — nem sempre o primeiro (vimos `_005`, `_010`,
`_094`). Mas o `Duration` do `VideoStream` é a do **clipe inteiro**.

Logo o casamento com o proxy é: tirar o sufixo `_\d{3}` do stem e procurar por esse nome.
Validado por duração em **92 de 92**, com 0 divergências acima de 0,1 s — inclusive um take de
1729 s cujo `Media` apontava para o segmento `_094`.

> É também a razão de o `reel_name` do proxy (`A001_A025_1023KF_001`) não bater com o
> `AlternateTapeName` do projeto (`A001_A025_1023KF`) — e de o Premiere trocar um pelo outro ao
> relinkar (§4.2).

## 8.2 Dois `Media` para o mesmo arquivo: medir o ANTES, senão a culpa cai no relink

[escrita.md §10](escrita.md) diz que um arquivo deve ter **um** `Media` no projeto inteiro. Um
relinker parece violar isso — mas a medição desfaz a acusação:

```
arquivos com mais de um Media de vídeo, no projeto ORIGINAL:  41
                                    depois do relink:         42
```

**O relink acrescentou exatamente um**, o do arquivo que o montador já tinha relinkado à mão
(§4.2): a ferramenta criou um segundo caminho para o mesmo proxy. Os outros 41 já estavam lá —
o Premiere duplica `Media` por conta própria ao longo de anos de montagem.

Duas consequências: **(1)** um relinker deve reportar **o delta**, não o total, senão entrega ao
montador uma lista de 42 "problemas" dos quais 41 não são obra dele; **(2)** não dá para fundir
em silêncio, porque os itens de cada `Media` têm escalas próprias — foram enquadrados em
momentos diferentes. Detectar, reportar, e deixar a fusão para quem monta.

> Vale como regra geral de quem edita arquivo alheio: **antes de reportar uma anomalia, medir
> quantas já existiam.** Vale para referência órfã (§9), para `Media` duplicado, e para
> praticamente tudo que um validador acusa num projeto real.

## 9. Método: o baseline de integridade é o ORIGINAL, não zero

Um projeto real de montagem já tem referência pendurada (aqui: 1 `ObjectRef` órfão). Um
validador que exija zero acusa o arquivo saudável. O que presta é o **delta**: nenhuma
referência quebrada **introduzida**.

E a verificação que realmente vale para geometria não é comparar o número do `Scale`, e sim
o **produto** `largura_da_fonte × scale/100` — a largura da imagem na tela — antes e depois.
Ele é invariante por construção, então qualquer erro de fator aparece.

---

## 10. Escalar ao quadro, velocidade e multicam usado como subclipe — `PRODB`, 2026-10-02

Lido em `PRODB_FINALIZACAO.prproj` (Premiere **26.0.2**, `Modified` 2026-09-20; criado no
26.0.2 a partir do `__PRODB_edit.prproj`, 24.6.8). 504.581 objetos, 353 sequências, timeline
2880×1620 a 24 fps. Leitura só, **sem** reescrita nem reabertura: confiança `inferido`, salvo
onde indicado.

### 10.1 `ScaleToFramePolicy` — o "Scale to Frame Size" mora no `VideoClip`

```xml
<VideoClip …>
    <Clip …> … <InPoint>…</InPoint><OutPoint>…</OutPoint> <PlaybackSpeed>1.444…</PlaybackSpeed> </Clip>
    <ScaleToFramePolicy>1</ScaleToFramePolicy>
    <TimeInterpolationType>2</TimeInterpolationType>
</VideoClip>
```

Medido no projeto inteiro: **513 de 513** `VideoClip` com `ScaleToFramePolicy=1` têm fonte
1920×1080 numa timeline 2880×1620; **nenhum** dos 1.064 de fonte 2880×1620 o tem. O `Scale` desses
itens fica em 100 (ou com o `DefaultMotion`, sem Motion nenhum).

⚠️ **Consequência para quem traduz:** o §1 ("100% = pixels nativos") NÃO vale para esses itens.
A escala efetiva é `Scale × (lado_da_sequência / lado_da_fonte)` no eixo que encaixa (fit). Um
leitor que só olhe o `Scale` põe a imagem a 1/1,5 do tamanho. Como é por `VideoClip` (instância
na timeline), o mesmo arquivo pode estar com e sem a política em usos diferentes.

~~`hipotese`: `1` = fit (encaixar). Os outros valores (fill?) não foram vistos.~~
> **CORRIGE / `confirmado` (laboratório B24, Premiere 26.5.2 Windows, 2026-10-29; mídia B05_RASTERS — HD, UHD, 4K DCI,
> 2K scope, vertical, anamórfico 1440×1080 SAR 2:1 — numa sequência 1920×1080; escala lida pela API, política no XML
> salvo, imagem medida em `exportFramePNG`).** O menu do clipe no 26 tem TRÊS modos: **Scale to Frame Size**, **Fit to
> frame** (o antigo "Set to Frame Size") e **Fill frame**; o QE só tem `setScaleToFrameSize(bool)`; o painel Properties
> tem os botões Fill/Fit. Só o **Scale to Frame Size** grava a política (`1`, Scale 100); **Fit** e **Fill** gravam o
> NÚMERO e nenhuma marca (Fit: UHD 50 · 4K DCI 46,875 · scope 93,75 · vertical 56,25 · anamórfico 66,667, o PAR conta;
> Fill: UHD 50 · 4K DCI 50 · scope 125,874 · vertical 177,778 · anamórfico 100). Não existe outro valor de política.
> ⭐⭐ **No RELINK** (`changeMediaPath` para outro raster): com a política o Premiere **reencaixa sozinho o arquivo novo**
> (HD → UHD: a imagem fica igual, 0,997; scope → HD: passa a cobrir o quadro); sem ela (nenhum, Fit, Fill) o número
> FICA e vale nos pixels do arquivo novo (HD → UHD: 0,009, o dobro; scope → HD com Fit: 1800×1014). Quem corrige a
> escala no relink não pode tocar os usos com a política — senão corrige duas vezes (De Lá Pra Cá,
> `Leitor.escalar_ao_quadro_por_midia` + `_copia_para_premiere`). A política é por USO: o mesmo arquivo pode ter os dois.

### 10.2 `PlaybackSpeed` dentro do `<Clip>` do `VideoClip`

Velocidade constante = `PlaybackSpeed` (float, ex. `1.4444444444444444`, `0.7`, `0.99990…`);
ausente = 100%. Aparece nos DOIS níveis: no item do corte que aponta para uma sequência aninhada
(20 no corte) e no item de mídia direta (18), e ainda dentro de sequência aninhada (2). Junto vem
`TimeInterpolationType` (2 visto; `pendente` qual é frame sampling/blending/optical flow).
Velocidade **variável** (time remapping) não foi procurada ainda. ⛔ CORRIGE (2026-10-10): decodificada — ver §"Time
Remapping" em `estruturas.md`.

### 10.3 Multicam de UMA câmera usada como subclipe

A prática que o autor descreve ("o assistente usou multicam como subclipe"): cada take é uma
`Sequence` multicam (nome `cena-plano-take`, ex. `74-7-6`) com **V1 = o proxy da câmera** e
**A1..An = o WAV polifônico separado por `StreamNumber`**. No corte, o item aponta para a
sequência por `VideoSequenceSource`; o `VideoClip` leva `<IsMulticam>true</IsMulticam>` +
`<SelectedTrackIndex>0</SelectedTrackIndex>` **ou nada** (o multicam desligado vira aninhamento
comum — no mesmo corte, 16 de um jeito e 505 do outro).

⚠️ **O Motion se COMPÕE em dois níveis:** o item do corte (punch-in 105–120%, muitos com
keyframe) e o item V1 DENTRO da sequência do take (reposição, rotação 180°) — este vale para todo
uso do take. Quem traduz tem de multiplicar as duas transformações, e a velocidade idem.

### 10.4 Merged clip no corte não deixa rastro de merged

O merged (segunda leva) entra no corte como mídia DIRETA: o `VideoClip` aponta para o
`VideoMediaSource` do proxy, sem `VideoSequenceSource`. O merged só existe na bin (29 sequências
`IsMergedClip`).

## Onde isso está implementado

`RELINK_PRODUCAO-G/` — `prproj_model.py` (índice de spans + edição pontual, sem reserializar),
`media_index.py` (acervo + cache de ffprobe), `relink_prproj.py` (relink + escala),
`verificar.py` (as checagens do §9), `contato_visual.py` (composita o quadro que o Premiere
vai mostrar, para conferir enquadramento sem abrir o Premiere).

> **Escopo:** tudo acima foi medido e validado em **Premiere Pro 2026 (26.0.2)**, num único
> projeto. A impressão digital de versões está no topo desta página.

> **Nota de escrita:** editar um PRPROJ existente **não** é o mesmo problema que gerar um do
> zero ([escrita.md](escrita.md)). Aqui o risco não é o Premiere recusar o arquivo — é ele
> abrir e mostrar a coisa errada em silêncio. Por isso a verificação é sobre o **efeito**
> (geometria, canais de áudio, caminhos online), não sobre a forma.

### 10.5 Keyframes, crop, interpolação de tempo e título — 2026-10-02 (`inferido`, mesmo projeto)

- **Keyframes do Motion:** `<Keyframes>tempo,valor,interp,…;</Keyframes>`, tempo em ticks da MÍDIA do
  item (domínio do `InPoint`). `interp` 0 = linear (o zoom do ovo frito, 100→115). ⚠️ Com keyframe, o
  `<StartKeyframe>`/`<CurrentValue>` NÃO é o valor que vale: o insert de 02:00:49:14 tinha `Position`
  fixa 0,79:0,37 e um único keyframe 0,67:0,44 — o Premiere mostra o do keyframe. Ler o fixo deslocou
  o plano.
- **Crop:** efeito `AE.ADBE AECrop` (Left/Top/Right/Bottom em %, `Zoom`, `Edge Feather`) e os quatro
  crops do próprio Motion. Os dois inserts do PRODB estão com Left = 100% — INVISÍVEIS no Premiere;
  sem traduzir o crop eles apareciam no Resolve por cima da imagem.
- **`TimeInterpolationType`** no `VideoClip`: 35 dos 38 planos com velocidade têm `2`. `hipotese`:
  ausente = Frame Sampling, 1 = Frame Blending, 2 = Optical Flow — confirmar na interface.
- **Título (Essential Graphics):** componente `AE.ADBE Text`; o texto e a fonte PostScript estão no
  `Source Text` (`StartKeyframeValue` base64, FlatBuffers; strings com prefixo u32 LE). Posição e
  escala do texto em parâmetros comuns (`Position` normalizada, âncora 0:0 = linha de base à esquerda);
  por cima, o `AE.ADBE Graphic Group` ("Vector Motion") com a escala da camada. A mídia do título é
  sintética (`FilePath` numérico). Cor no blob: `pendente`; corpo: ver o bloco abaixo.
  🆕 O mapa COMPLETO do blob (cores, contorno, fundo, sombra, tracking… — Premiere 23.6, 2026-11-15):
  [titulo-essential-graphics.md](titulo-essential-graphics.md).
- 🆕 **Título — corpo, fonte e Graphic Group, conferidos pela IMAGEM (2026-10-04, Premiere 26.0.2 ×
  export de referência, PRODB 2880×1620).**
  - **Corpo:** o padrão do Essential Graphics é **100 px do quadro** (claquete em Monaco, `Scale` 100:
    "PRODUCAO-B" mede o que o Monaco de 100 px mede) e a entrelinha automática é **120% do corpo**
    (120 px entre as linhas). Corpo diferente do padrão vem no blob do `Source Text` (FlatBuffers depois
    de 12 bytes: raiz → documento → campo 0, vetor de trechos → trecho[0] campo 1, estilo → campo 1,
    float32): 160 nos títulos em ArialMT, AUSENTE nos de corpo padrão (FlatBuffers não grava o padrão).
    `inferido` — não há título de corpo ≠ 100 conferido pela imagem.
  - **Entrelinha no Resolve:** o Line Spacing do Text SOMA à linha natural da fonte; para os 120% do
    Premiere vai `(1,2 − linha natural) × corpo` (negativo na Monaco) — a claquete de 2 linhas caiu no
    pixel (2026-10-04). Ver `drt-drp/dados/text-gerador.json` › `entrelinha`.
  - **Fonte do Adobe Fonts:** o Premiere usa as do catálogo do Creative Cloud como qualquer outra (o
    nome PostScript no blob); no Resolve elas só aparecem com o CC logado e a fonte ativada NA MÁQUINA
    QUE ABRE (linha "pastas de fontes" da matriz de plataforma).
  - **Fonte:** nome **PostScript** (`Optima-Regular`, `ArialMT`, `Monaco`); a família e a face saem da
    tabela `name` da fonte instalada (ver a linha "pastas de fontes" da matriz de plataforma).
  - **Posição do texto:** `Position` = linha de base à esquerda do 1º caractere — `confirmado` (Monaco:
    baseline e margem esquerda no pixel).
  - **Graphic Group (Vector Motion)** transforma a camada inteira em volta do PRÓPRIO `Anchor Point`
    (0,5:0,5 = centro): `p' = Position_g + (p − Anchor_g) × escala`, no corpo E na posição. O título final
    do PRODB tem a escala ANIMADA 80% → 100% (Bézier no gráfico, `interp` 0): no Resolve isso é o Zoom
    animado do clipe, e caiu em ±1 px aos 5 s e aos 10 s com interpolação LINEAR. `confirmado`.
- **Reverso:** `<PlayBackwards>true</PlayBackwards>` no `<Clip>` do `VideoClip`, com a `PlaybackSpeed`
  POSITIVA. `confirmado` pela imagem (2026-10-02): a fonte no instante t é (duração − 1 quadro) −
  `InPoint` − (t − `Start`) × velocidade — o `InPoint` conta a partir do FIM da mídia. Era a lâmpada
  da abertura do PRODB: lida como direta, mostrava o começo do take (lâmpada acesa e próxima).
- **Clipe desligado:** `<IsMuted>true</IsMuted>` no `ClipTrackItem` (Enable desmarcado) — além do
  da trilha. `confirmado` (PRODB 30B-2-2).
- **Crop com máscara:** o `AE.ADBE AECrop` pode ter um `SubComponent` `AE.ADBE AEMask2` com `Path`
  animado (contorno rastreado) — Crop 100% + máscara = "mostre só o recorte". Traduzir só o crop
  esconde o plano inteiro; é composição (Fusion/Color), não Edit.
- **Flips** são efeitos (`AE.ADBE Horizontal Flip`/`Vertical Flip`); **Luma Key** é
  `AE.ADBE Legacy Key Luma` (VFX sobre preto → Screen no Resolve, aproximação).
- **Aninhamento de composição** (não multicam) com várias trilhas: todas valem, empilhadas
  (`C87_COMP_INTERFONE_2`: placa + insert). Ler só a trilha de cima perdia a placa.

### 10.6 Máscara do Premiere → Polygon do Fusion — 2026-10-03 (`confirmado` pela imagem)

- **Contorno (`Path` do `AE.ADBE AEMask2`)**, base64 por keyframe (ou `StartKeyframeValue` se fixo):
  17 bytes de cabeçalho; `u32` nº de vértices (offset 17); por vértice 28 bytes = `u32` (1 suave /
  0 canto) + 3 pontos `f32` (x, y): VÉRTICE, tangente de ENTRADA, tangente de SAÍDA — normalizados
  0–1 no quadro da FONTE do clipe, Y para baixo. Prova: o ponto médio das duas tangentes é o vértice.
- Transformação da máscara: `Position`, `Anchor Point`, `Scale Height/Width`, `Rotation`; no insert do
  interfone Position = Anchor (sem deslocamento). Suavidade `Feather`, `Expansion`, `Opacity`.
- **Invertida:** booleano SEM NOME na posição 22 dos parâmetros (`hipotese` forte: ligado no insert,
  e o export mostra só o de DENTRO; traduzido assim, 0,998 de correlação).
- **No Fusion:** Polygon (`PolylineMask`) ligado como `EffectMask` do `MediaIn` — mostra só o de
  dentro. Pontos em fração da largura (X) e da altura (Y), a partir do CENTRO, Y para CIMA; alças
  `LX/LY` e `RX/RY` relativas ao ponto. Conversão: X = x − 0,5; Y = 0,5 − y; alça = tangente − vértice
  (Y invertido). `prproj/mascara.py`.
- ⚠️ **Formato do `Path` deduzido de UM projeto (Premiere 26.0.2)** — outras versões `pendente`, na
  lista de testes sintéticos do De Lá Pra Cá. O De Lá Pra Cá trata o blob que não se lê como "refazer"
  só naquele efeito (2026-10-03).
- **Conferido:** PRODB 02:00:49 (insert da polícia na tela do interfone), 3 pontos, correlação
  0,998–0,999 contra o export, cantos arredondados incluídos.
- **Crop num plano que aponta para um take aninhado** (PRODB 66-1-9): corta o QUADRO do take. O
  Cropping do Resolve corta a FONTE, então o retângulo volta à fonte pela inversa da geometria de
  dentro do take. `Edge Feather` (px do quadro do item) → Softness.

### 10.7 Máscara no fluxo, sem molde; Gaussian Blur com máscara — 2026-10-03 (Resolve 21.1, Mac)

- **No filme inteiro do PRODB são 3 usos de máscara, todos FIXOS** (1 keyframe de contorno): Crop
  com máscara invertida de 12 pontos nos dois `87-INSERT-EXTRA` (01:00:49:14 e 01:22:41:07) e um
  **`AE.ADBE Gaussian Blur 2` com máscara** de 6 pontos no A055C012 (01:01:42:06–21, V5) — esconde um
  objeto refletido no espelho. Nenhum contorno rastreado/animado neste projeto.
- **Gaussian Blur (Legacy):** parâmetros 0 `Blurriness` (px), 1 `Blur Dimensions` (0 = as duas,
  1 = horizontal, 2 = vertical), 2 SEM NOME (o `Name` é um espaço) = Repeat Edge Pixels. A máscara é
  `SubComponent` `AE.ADBE AEMask2` do próprio efeito, igual à do Crop. **Não invertida = o efeito
  vale DENTRO do contorno** (no Crop, não invertida = esconde o de dentro; por isso o Crop do insert é
  invertido).
- **Calibrado pela imagem** (`inferido`, 1 caso, fonte de 2880 px): Blurriness 57,3 → `XBlurSize`
  do Blur do Fusion ≈ **0,2 × Blurriness** (varredura 0…115; pico entre 11 e 12, correlação 0,955 dentro
  da máscara × 0,789 sem blur). Feather 27,5 px → `SoftEdge` do Polygon = **px ÷ largura da fonte**
  (varredura 0…0,04; pico em 0,01 = 27,5/2880). Não se sabe se a razão do blur depende da resolução.
  ⚠️ SUPERADO para o Feather (2026-10-10, laboratório B14, `confirmado`): **SoftEdge = 0,845 × px ÷ largura** e
  Expansion → **BorderWidth = 2 × px ÷ largura** — `drt-drp/estruturas.md`, "Máscara de opacidade … calibrada no
  laboratório". A correlação deste caso não separava 15 % de largura.
- **Insert do interfone refeito SEM molde:** a máscara bate (contorno e cantos), mas a correlação na
  tela fica em 0,938 porque o export tem **VR Chromatic Aberrations** (franjas coloridas) e **Basic 3D**
  por cima, ainda sem tradução. O 0,998 do §10.6 foi medido de outro jeito (composição do autor como
  base) — não comparar os números.
- Código: `prproj/leitura.py` (receita no segmento, categoria `fusion`), `prproj/mascara.py`
  (transformação da máscara; inversa da geometria do take aninhado), `drp/fusion_clipe.py`
  (aplica no Resolve), `tools/prproj_para_drt.py` (chave `fusion` do `.relatorio.json`).

### 10.8 Basic 3D do Premiere → Corner Positioner do Fusion — 2026-10-03 (`confirmado` pela imagem)

- **`AE.ADBE Basic 3D`**: parâmetros `Swivel` (giro no eixo vertical), `Tilt` (horizontal), em graus;
  `Distance to Image` (0 = padrão), `Specular Highlight`, `Preview`. No PRODB: os dois inserts do
  interfone (Swivel 1,8 / Tilt −1,9) e o clipe de calibração do autor no caso R02 (20 / 20).
- **Geometria medida** (homografia por pontos casados, flat × export do Premiere, 925/1101
  concordantes; caso R02, quadros 372–460): é rotação de verdade, **R = Ry(Swivel)·Rx(Tilt)** em torno do
  centro da camada, com a câmera a **uma largura da camada** de distância (ajuste: 20,10° / 19,94°,
  erro 0,65 px). Na origem do centro, Y para baixo:
  H = [[cos S, sen S·sen T, 0], [0, cos T, 0], [−sen S/W, cos S·sen T/W, 1]]. Vale na fonte, antes do
  Motion (o insert encolhido a 36,5% gira em torno do próprio centro, medido).
- **Tradução: CornerPositioner no Fusion** com os 4 cantos de H (0–1, Y para cima). Resultado 0,9993 de
  correlação contra o export, cantos a ≤ 2,3 px. Insert do interfone: tela de 0,938 (só máscara) →
  0,976 (máscara + Basic 3D; o resto é o VR Chromatic Aberrations, sem tradução).
- ⚠️ **Pitch/Yaw do Inspector NÃO servem** (medido, Resolve 21.1): são perspectiva PURA no quadro
  normalizado do clipe, w = 1 + Yaw·u − Pitch·v (u, v ∈ [−1, 1]) — não encurtam nem inclinam; o melhor
  equivalente (Yaw = −sen S/2, Pitch = −cos S·sen T·(alt/larg)/2, Zoom × cos) deixou ±100 px de
  inclinação nos cantos (0,883). E num clipe COM composição do Fusion a perspectiva do Inspector gira em
  torno do centro do QUADRO, não do clipe (o insert piorou de 0,938 para 0,878). Ver
  `plugins/resolve-scripting/api-scripting.md`.
- `Distance to Image` ≠ 0 e Basic 3D num plano aninhado com geometria: não traduzidos (aviso).

### 10.9 O filme inteiro pelo gesto — 2026-10-03 (`confirmado` pela imagem)

PRODB `DU_CORTE_06 SIMPLIFICADA` montada pelo autor no painel do Resolve 21.1 (Importar `.prproj`,
originais em dois HDs, ARRIRAW em log): conferência de 1.142 pontos (1º e último quadro visível de
cada plano) contra o export → **1.141 ≥ 0,75 (99,9%)**; o único abaixo é cena muito escura com
burn-in do nome no export (0,99 sem as bordas). A v4 (2026-10-02) tinha 98,3%.
- ⚠️ A leitura dá `timeline_tc_in` a partir do ZERO da sequência (sem a hora de base): o quadro do
  export = o tc direto (01:01:42:06 = quadro 88.854), não tc − 01:00:00:00.
- ⚠️ Áudio NÃO entra ainda neste caminho (decisão de 02/10: só imagem no 1º teste) — `pendente`.


### 10.5 NEST × sequência MULTICAM — o sinal está na SEQUÊNCIA, não no clipe (2026-10-04)

O `<IsMulticam>` do `VideoClip` NÃO separa os dois: no `FINALIZACAOPRODB_FINALIZACAO_PARA RESOLVE.prproj`
(Premiere 26.0.2) os 505 takes usados no corte vêm sem ele (o "multicam desligado" do §10.3). O que
separa é a **sequência de dentro**: `<Source.Monitor.Multicam.SwitchOnMulticamName>` no `Properties`
dela existe nas 280 sequências multicam e em NENHUM nest, merged ou timeline de montagem (o mesmo nos
dois projetos do PRODB: 295 × 0). Nest de verdade no filme: só `C87_COMP_INTERFONE_2` (2 trilhas:
placa do interfone embaixo, policiais na telinha em cima; dentro dele, um take multicam). Confiança:
`inferido` — a observação que refutaria (um nest com a chave, ou multicam sem ela) não apareceu em 2
projetos, mas ambos são do mesmo assistente/versão. Uso: o nest vira Compound Clip do Resolve 1:1; a
multicam continua achatada (a câmera escolhida).

⛔ 🆕 **A observação que refutava apareceu (2026-11-12, Premiere 26.0.2 Mac):** a multicâmera RECÉM-CRIADA (Clipe ›
Criar sequência de origem de várias câmeras, por TC, `carta_aberta/EXP 8 volta.prproj`) **não tem** o
`SwitchOnMulticamName` — a chave nasce depois (com o uso no Source, ao que tudo indica: não medido). A marca que já
existe é a do **MasterClip** que a representa na bin: `<Source.Monitor.Multicam.Enabled>true</…>`, ligado à sequência
por `MasterClip › Clip › VideoSequenceSource › Sequence`. ⇒ reconhecer multicam pelas DUAS (Ciclo Assist
`carta/itens.py::_sequencias_multicam`). As trilhas dela: V1…Vn = as câmeras, A1 = o som direto, A2… = o som de cada
câmera; cada fonte INTEIRA (entrada 0) com início = onde o quadro 0 dela cai.

### 10.10 "Metadata & Timecode Burn-in" → Text+ do Resolve — 2026-10-08 (Premiere 26.0.2, PRODB)

- Efeito `AE.ADBE PPro Metadata` (num Graphic/camada de ajuste). 67 parâmetros, os nomes se repetem: 0 `Size`
  (do efeito), 1 `Opacity` (do FUNDO, %), e 5 blocos de 13 a partir do 2: `Line N` (bool, `inferido`: a seta
  aberta, não "ligada" — a linha 1 aparece com ele `false`), `Metadata` (enum; 0 = vazia), `Position`
  (fração, Y para baixo), `Size` (%), `Metadata Label`, `Source Track` (4294967295 = −1), `Source Track Label`,
  `Field Symbol`, `Format`, `Time Display`, `Offset`, `Starting Timecode` (int) e `Starting Timecode` (bool).
- **`Metadata` 4 = TC da TIMELINE** (`confirmado` pela referência em 01:00:59:02, 01:22:49:07, 01:24:25:00 e
  00:10:00:00). Os outros valores (nome do clipe, TC da fonte…) `pendente` — o De Lá Pra Cá avisa "refazer".
- **Desenho** (quadro 2880×1620, `inferido`, 1 caso): dígitos brancos de `0,00236 × Size × Size da linha/100 ×
  altura` (Size 17 → 65 px), caixa preta com a `Opacity`, ancorada pela `Position` no canto INFERIOR ESQUERDO
  (0,8168/0,0757 → x 2352, y 123), folga ~0,12 × a altura dos dígitos à esquerda e ~0,25–0,28 embaixo.
- **Tradução**: um Text+ ("Fusion Title") no trecho do Graphic, com o TC vivo (modificador TimeCode) em Open
  Sans Semibold — a mesma proporção dos dígitos (7,23 × 7,20). Sobre o PRODB: os dígitos a ≤ 2 px dos da
  referência nos 3 trechos. Exceção pedida pelo autor à regra "título = Text simples". Formato do Text+ no
  DRT: `protocolos/drt-drp/estruturas.md` (seção do Text+).
- ⚠️ A referência do PRODB tem também o NOME do arquivo original (`A093C005_240807_R1X0.mxf`) queimado
  embaixo à direita: não vem do burn-in do Premiere (não está no projeto, e o Premiere usa os proxies .mov) —
  `inferido`: um data burn-in de quem exportou a referência.

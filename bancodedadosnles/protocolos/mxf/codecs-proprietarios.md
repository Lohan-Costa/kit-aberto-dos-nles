# MXF com codec proprietário — identificar antes de tentar ler

Nem todo `.mxf` é legível pelas ferramentas de sempre. Sony X-OCN, ARRIRAW e afins usam ULs
privados dentro de um MXF normal: o container abre, a essência não. Este tema é sobre
**como um app descobre isso sem decodificar nada** — e sobre a forma de falha, que é
silenciosa.

Fatos consumíveis em [dados/xocn-sony.json](dados/xocn-sony.json). Tudo `confirmado`,
medido em 2026-08-20 sobre material real de Sony VENICE (`MPC-3628`): três clipes X-OCN 8K
(LT, ST e XT) e um ProRes 4444 4K como controle, gravados na mesma diária.

## ⚠️ O `ffprobe` falha em silêncio

```
ProRes 4444  →  codec_name=prores   profile=4444   4096x2160     ✔
X-OCN        →  codec_name=unknown  width=0        height=0      ✘
                stderr: "could not resolve file descriptor strong ref"
                EXIT CODE = 0
```

O demuxer MXF do ffmpeg não resolve o descriptor de essência do X-OCN. Ele **devolve JSON
válido, com `unknown` e zeros, e sai com código 0.** Um app que cheque só o *returncode*
não vê nada de errado — é o modo de falha que este banco já nomeou como o mais caro: *o
artefato existe e está errado*.

Isso importa porque a rota `ffprobe` é a espinha dorsal da estratégia MXF deste banco
("sem dependência nova", ver [README.md](README.md) e [timecode.md](timecode.md)).

**O que sobrevive é a camada `format`, e sobrevive inteira:**

```
operational_pattern_ul : 060e2b34.04010101.0d010201.01010900   → OP-1a (não OP-Atom)
company_name           : Sony
product_name           : AXS
application_platform   : Sony MXF Development Kit (Win32)
material_package_umid  : 0x060A2B34…193C3BD6881C4469 8C2C2B4031013B6F
timecode               : 08:48:10:04
duration               : 15.000000
```

> ⭐ **Regra:** para **agrupar e identificar**, `ffprobe` continua servindo em X-OCN; para
> saber **o que é o vídeo**, não serve. `codec_name == "unknown"` com `width == 0` num MXF
> que abriu com `probe_score=100` significa **codec proprietário**, não arquivo corrompido.

## O MediaInfo entrega o raster e a variante

O MediaInfo nomeia o que conhece e **cai no UL cru quando não conhece**:

| variante | `Video.format` | raster |
|---|---|---|
| ProRes 4444 | `ProRes` | 4096×2160 |
| X-OCN **LT** | `0E060D0302020100-0E0604010206`**`06`**`01` | 8192×4320 |
| X-OCN **ST** | `0E060D0302020100-0E0604010206`**`05`**`01` | 8192×4320 |
| X-OCN **XT** | `0E060D0302020100-0E0604010206`**`07`**`01` | 8192×4320 |

Dois ganhos: o MediaInfo **acerta o raster** onde o ffprobe dá 0×0, e **um único byte do UL
discrimina LT/ST/XT**.

> ⭐ **Detecção genérica, sem tabela de codecs:** se `Video.format` casar
> `^[0-9A-F]{16}-[0-9A-F]{16}$`, é codec proprietário. Vale para qualquer formato que o
> MediaInfo não nomeie, não só X-OCN.

## ⭐ A rota mais barata é o sidecar

Câmeras Sony gravam, ao lado de cada clipe, um `<NOME>M01.xml` (`NonRealTimeMeta`) de ~5 KB
que **declara o codec por nome**:

```xml
<VideoFrame captureFps="24p" formatFps="24p" videoCodec="F55_X-OCN_ST_8192_4320"/>
<VideoLayout aspectRatio="256:135" numOfVerticalLine="4320" pixel="8192" pixelAspect="1:1"/>
<AudioFormat numOfChannel="4"> … LPCM24 48000 … </AudioFormat>
<LtcChangeTable tcFps="24"> … </LtcChangeTable>
<AcquisitionRecord> … lente, ISO, ND, shutter, s-log3-cine, s-gamut3-cine … </AcquisitionRecord>
```

Ler 5 KB de XML ao lado de um arquivo de 7 GB é ordens de grandeza mais barato que abrir o
MXF, e é a **única** das três rotas que dá o nome do codec. Para varredura de cartão,
comece por aqui.

## ⚠️ A armadilha AppleDouble, viva neste material

A pasta `Scene1` tem **8 arquivos com extensão `.mxf`** e só 4 são mídia: os outros são
sidecars AppleDouble `._<nome>.mxf`, de 4096 bytes, magic `00 05 16 07`, deixados por um
macOS. O AMA tenta linkar cada um. Vale a regra que
[../../transversal/ambiente-media-composer-windows.md](../../transversal/ambiente-media-composer-windows.md)
já registra: **ignorar `^\._` e `.DS_Store` ANTES de contar arquivos.**

(No teste, o filtro do Source Browser descartou os oito automaticamente — entraram 3
masterclipes para 3 arquivos. Mas o app que enumera a pasta por conta própria não tem esse
filtro de graça.)

## Bitrate e storage — o que a rota exige na prática

| variante | 15 s | Mbps |
|---|---|---|
| ProRes 4444 4K | 1,98 GB | 1.055 |
| X-OCN LT 8K | 2,93 GB | 1.563 |
| X-OCN ST 8K | 4,97 GB | 2.650 |
| X-OCN XT 8K | 7,25 GB | 3.868 |

O fabricante do plugin pede **600 MB/s sustentados por stream**. Playback no MC: *Full
Quality* decodifica o 8K inteiro, *Draft* 1/2, *Best Performance* 1/4.

## O que o Avid grava a partir disso

Ao linkar, o descriptor da bin **não repete** o que o sidecar diz — ver
[../avb/plugins-e-handlers.md](../avb/plugins-e-handlers.md) para a identidade do plugin.
Três detalhes do lado do formato:

- ⭐ **O raster tem 32 px de sobra por lado.** `stored 8256×4384`, `display 8192×4320`,
  `display_x_offset = display_y_offset = 32`, `sampled == stored`. O sidecar e o MediaInfo só
  mostram o 8192×4320. **Quem for autorar descriptor de X-OCN precisa desse par
  `stored ≠ display` com offset 32** — errar isso desloca o enquadramento.
- **`compress_method` não nomeia codec.** `RI00` aparece tanto no ProRes 4444 12 bits quanto
  num AVC 4K; `UNK0` aparece no X-OCN e no BRAW. São rótulos de "quem tratou", não de "o que
  é".
- ⚠️ **`component_width = 10` num ProRes 4444 de 12 bits** (o `ffprobe` lê
  `bits_per_raw_sample=12`, `yuv444p12le`). O descriptor do Avid declara 10.
- O `ANCDataDescriptor` (dados auxiliares) aparece no ProRes pelos dois motores da Avid e
  **não** aparece no X-OCN: o plugin do nablet descarta os dados auxiliares.

## ⭐⭐ O MobID vem de DENTRO do arquivo — e por isso é estável

Os MobIDs que o Avid grava para um MXF profissional são **cópia dos UMIDs do próprio
arquivo**, não valores gerados:

```
ffprobe  material_package_umid  060A2B34…13000000 193C3BD6881C4469 8C2C2B4031013B6F
bin      MasterMob.mob_id       060a2b34…13000000.193c3bd6.881c4469.8c2c2b40.31013b6f

ffprobe  file_package_umid      060A2B34…13000000 735E3BD6FF5E4469 BB482B401A6B3B6F
bin      SourceMob.mob_id       060a2b34…13000000.735e3bd6.ff5e4469.bb482b40.1a6b3b6f
```

(o SourceMob "físico" repete o mesmo *material number* trocando `13000000` por `13a10000`.)

Medido linkando o mesmo arquivo por **dois motores diferentes**: os três MobIDs saíram
byte-idênticos. Isso **refina** a conclusão de
[../../transversal/banco-de-midias-compartilhado.md](../../transversal/banco-de-midias-compartilhado.md)
— ver a ressalva lá.

### ⭐ A correção que funcionou: sanitizar o AAF do transcode (SANITIZADOR_DE_AAF, 2026-08-20) — `confirmado` no MC

Consequência do fato acima: um transcode nascido de um X-OCN **herda o MobID do original**, e
importar o AAF dele faz o Source Browser deixar de linkar o original. Caso real: `01 - telas
fotoblog minidv.aaf` (MC 24.12.5.59316) — masterclipes `F017C006_260615DB` e `F017C010_260615U9`
apontando para DNxHD 1080 8 bits na Nexis, com MobID **byte a byte igual** ao dos masters X-OCN 6K
linkados pelo plugin da nablet.

O Sanitizador grava uma **cópia** do AAF trocando o MobID dos MasterMobs "em risco". **Validado
pelo autor no Media Composer (2026-08-20):** com o AAF sanitizado, os arquivos referenciados
linkaram pelo Source Browser sem conflito com o AMA link.

**Como decidir o que está em risco — pela família do MobID (3º campo do URN):**

| família | origem | colide? |
|---|---|---|
| `01010f*` (`01010f00`, `01010f10`, `01010f20`) | gerado pelo Avid | não |
| `01010d43` | UMID de MXF Sony (X-OCN) | sim |
| `01010d11`, `01010d12` | UMID de MXF de captura (MiniDV) | sim |
| `01010512` e outras | derivado de arquivo | sim |

⚠️ Regra **empírica** (comparando MobIDs de bins e AAFs reais), não da SMPTE 330M. Família nova
cai do lado "em risco" — marca demais, nunca de menos. `MobID.new()` do pyaaf2 gera `01010f20`:
o valor novo é seguro por construção.

**Edição mínima:** só os **MasterMobs** são reescritos; os SourceMobs do transcode já nascem
`01010f10` e não colidem.

**Verificação em três camadas (o que transforma "acho" em "reescrevi tudo"):**
1. varrer os **bytes crus** do arquivo de saída atrás de qualquer MobID antigo
   (`MobID(...).bytes_le in raw`) — o percurso por propriedades pode não alcançar alguma referência;
2. contar referências órfãs antes e depois: o critério é **não crescer** (AAF real pode ter órfã de
   nascença; o de teste tinha 1, num masterclipe `Frame 276 (1)`);
3. o hash do arquivo de entrada não muda (a entrada nunca é gravada: `ValueError` se a saída
   resolver para o mesmo caminho).

Armadilha do pyaaf2 no caminho: ver [../aaf/escrita.md](../aaf/escrita.md) §"Trocar `mob_id`
re-chaveia `f.content.mobs`". Código: `SANITIZADOR_DE_AAF/app/sanitizer.py` (hoje em
`9 ARQUIVADOS/`; ver `CATALOGO.md`), suíte `tools/e2e.py` 24/24.

## ⚠️ Metadado de câmera com status falso

O `_USER` de um X-OCN traz 30+ colunas vindas do `AcquisitionRecord`: LUT por nome
(`Pre-CDL Transform: LUT:SL3SG3Ctos709.cube`), `Look Process baked: No`, ISO/EI, white
balance, íris, shutter, e os raw code values (black 512 / gray 1504 / white 5472). Duas
armadilhas para quem consome:

- **Tipos misturados no mesmo dicionário.** `Shutter Speed Angle` vem
  `bytearray(b'\x00\x00173.00\xc2\xb0\x00')` — dois NULs na frente, `°` em UTF-8, NUL no
  fim; ao lado de campos que são `str` puro. Um app que assuma `str` quebra ou escreve lixo.
- ⚠️⚠️ **Um campo que mente com selo de válido:** `Camera Roll Angle = 1193046° 22' 16"`, e
  **1193046 = 0x123456** — filler clássico de depuração. Ao lado dele,
  `Positioning Data Status: Valid`. **O campo de status não valida o dado.** Antes de exibir
  metadado de câmera, checar plausibilidade do valor, não a flag.

## Ver também

- [../avb/plugins-e-handlers.md](../avb/plugins-e-handlers.md) — o lado da bin: qual plugin leu, e se ele está instalado.
- [README.md](README.md) · [timecode.md](timecode.md) — o resto do que se sabe de MXF.
- [fontes.md](fontes.md)

## ARRIRAW em MXF: o raster sai do cabeçalho sem MediaInfo — 2026-10-02

`confirmado` em ALEXA Mini ARRIRAW (`A0xxC0xx_2407xx_R1X0.mxf` e `M00xC0xx_2505xx_M3OV.mxf`,
projeto PRODB). O `ffprobe` falha igual ao X-OCN (`unknown`, 0×0, *strong ref*), e sem
MediaInfo na máquina o raster sai dos **local tags** do descritor, nos primeiros 200 KB:
`32 03 00 04` = StoredWidth, `32 02 00 04` = StoredHeight (UInt32 big-endian), `32 0E 00 08` =
AspectRatio (dois Int32). Medido: 2880×1620, 16:9, e a string `ALEXA Mini` no cabeçalho.
⚠️ Atalho: procura direta pelos bytes da tag, sem ler o Primer — vale para estes tags fixos de
SMPTE 377, não para tag dinâmico.

## Download interrompido: o MXF sem o Random Index Pack — 2026-10-02

`confirmado` (PRODB, Frame.io abortado por falta de espaço): o arquivo fica do tamanho do que
chegou, mas o CABEÇALHO declara a duração e o TC do clipe inteiro — `ffprobe` dá duração e TC
certos e o Resolve mostra Media Offline. Teste barato e sem SDK: o MXF termina no RIP (chave
`06 0e 2b 34 02 05 01 01 0d 01 02 01 01 11 01 00`, os 4 últimos bytes = tamanho do RIP). Sem ele,
incompleto. Medido: 55 de 236 (53 de 0 byte + 2 parciais); os completos, inclusive ARRIRAW de
28 GB, passam. `prproj/originais.py::mxf_completo`.

## ARRIRAW em HD USB frio: o ffprobe pode passar de 60 s — lento NÃO é ilegível — 2026-10-04

`confirmado` (Windows 11, De Lá Pra Cá, filme PRODB: originais ARRIRAW no HD USB `PROJ-X_D`, proxies
no `PRODB`; disco esfriado ejetando e replugando os HDs entre rodadas).

| rodada (disco frio) | casamento (análise) | montar o DRT | no original |
|---|---|---|---|
| em série | 301 s | 115 s | 568 |
| 8 ffprobe simultâneos | 232 s | 24 s | **563** — 5 ARRIRAW (A033C006/8/10/15, A037C003) estouraram o limite de 60 s |
| em série, disco QUENTE (referência) | 56 s | — | 568, nenhuma sondagem > 0,5 s |
| 4 ffprobe simultâneos | 267 s | — | 568, nenhum estouro (os mais lentos: série A033, 30–40 s) |
| 8 simultâneos, com a correção (refaz em série quem estoura) | 237 s | — | 568 (os mesmos 5 estouraram) |

Escolha do De Lá Pra Cá: **4 simultâneas** — 30 s a mais que 8 num disco frio de ~4 min, sem o disco
engasgar (num disco mais lento, cada estouro custa 60 s + a repetição).

Com o disco quente, a mesma análise leva ~5 s em paralelo e ~30 s em série: o cache de arquivos do
Windows esconde o custo — medir com o disco ejetado e replugado (memória "o que estava quente quando
eu medi"). Regra que saiu daqui: **estouro de tempo não é arquivo ilegível**. Não guardar no cache,
refazer sozinho (sem disputa pelo disco) e, se persistir, dizer "o disco não respondeu" — nunca
que o arquivo é ilegível. As mensagens do app descrevem o ARQUIVO (vazio, truncado), nunca a causa
situacional de um projeto. De Lá Pra Cá: `motor/prproj/originais.py::sondar` e `drp/writer.py::_SONDA_LENTA`.

**Leitura única por arquivo (2026-10-05, De Lá Pra Cá `media/sonda.py`):** as quatro perguntas ao ffprobe
(casamento, TC, formato, som) viraram uma. Disco frio (RAMMap), 4 simultâneas: 295 s → 271 s (análise
285 → 267 s, montagem 10 → 3 s); disco quente: 18,2 → 8,7 s. Com o disco frio o custo é o HD buscando o
começo e o fim de cada arquivo na PRIMEIRA leitura — as releituras já saíam do cache. Comando a comando,
"todos os streams" × `-select_streams v:0` custam o mesmo (~30–45 ms quente).

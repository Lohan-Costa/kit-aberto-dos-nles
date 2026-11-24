# RAW de câmera (BRAW / R3D / ARRIRAW / X-OCN / Canon) — quando o SDK é inevitável, e quando não é

O ffmpeg **não decodifica a essência** desses formatos. A pergunta que todo app da casa faz
mais cedo ou mais tarde é "então preciso do SDK do fabricante?" — e a resposta tem duas
metades, que costumam ser confundidas.

| a pergunta | precisa de SDK? |
|---|---|
| *"reaproveitar o que já foi processado do mesmo material"* | **não** — ver §1 |
| *"ver o quadro de um RAW que nunca foi convertido"* | **sim** — ver §2 |

## 1. ⭐⭐ Reaproveitar sem SDK: o contêiner fala, e o SOM decide

`confirmado` 2026-09-21, no acervo de `_CICLO ASSIST` (5 clipes BRAW da Blackmagic 4K, e os
OP-Atom que o Media Composer gerou deles).

**O contêiner BRAW responde ao `ffprobe`** — fps, número de quadros, timecode e o áudio PCM
saem inteiros; só a essência de vídeo vem `codec_name=unknown`. Ou seja: para **identificar**
o clipe, o ffprobe basta; para **ver** o clipe, não.

| | medida |
|---|---|
| BRAW × o OP-Atom dele, por PIXEL | **−1,000** (não abre) |
| o mesmo par, pelo SOM do próprio clipe | **+1,000**, em 0,4 s |
| impostor (outro take da mesma câmera, no mesmo dia) | **+0,033** |

⇒ Um RAW casa com o transcode dele pela regra de convertido
([`banco-de-midias-compartilhado.md`](banco-de-midias-compartilhado.md) §8/§8b), trocando a
confirmação de pixel pela de som. **5 de 5** acharam o material que já tinha quadros, fala e
vetores prontos.

⛔⛔ **Só "não consegui comparar" (`-1`) pode cair para o som.** Um desacordo de PIXEL é uma
resposta, e deixá-la ser resgatada pelo som aceitaria um rewrap de imagem diferente com o
mesmo áudio.

⛔⛔ **O `reel_name` do BRAW é o ROLO, não o clipe.** Ele vem `"1"` numa tag de stream, e num
app que dá precedência ao `reel_name` isso vence o nome do arquivo:
`B001_03150115_C003.BRAW` vira a fonte `"1"` e o clipe **deixa de ser candidato do próprio
transcode**, com fps, nº de quadros e TC idênticos. ⇒ Recusar nome degenerado (só dígitos,
ou 1–2 caracteres). ⚠️ Nos 332 masters daquele cache, nenhum OP-Atom tem nome degenerado —
a regra só alcança quem ela deve alcançar.

⚠️ **ARRIRAW `.arx`/`.ari` não tem som** (é 1 arquivo por frame, sequência de imagem): esta
saída não existe para ele. R3D e X-OCN carregam áudio e, em princípio, servem — **por medir**.

## 2. Quando o SDK é inevitável: o desenho do RELINKER — `confirmado` 2026-06

O RELINKER (`D:\PROGRAMAS COM CLAUDE\RELINKER`, `docs/raw-decoders.md`) resolveu a
arquitetura, e ela é reaproveitável inteira. `_DeLaPraCa` já vendoriza o `decoders.py` dele.

⭐⭐ **Helper-CLI por fabricante, com contrato uniforme:**

```
<app>-decode-<kind> --file <path> --frame <N> --out <out.jpg> [--max-width <W>]
    exit 0  → gravou out.jpg        exit ≠0 → motivo no stderr
```

Um binário externo **opcional**, detectado em runtime (pasta do executável, `binaries/`,
`helpers/bin/`, `PATH`). Ausente → exceção própria → a resposta carrega `{needs_sdk, sdk_url}`
e a interface mostra "instale o SDK X" com o link. **Nada do resto do app depende disso.**

**Por que helper-CLI e não binding Python** (razões do RELINKER, todas boas):
licenciamento isolado (o código licenciado não entra no app), crash-safe (um decode que
quebra não derruba o serviço), e builds por plataforma isolados.

**Despacho:** por extensão (`.braw` `.r3d` `.ari/.arx` `.crm/.rmf`), **menos Sony X-OCN**,
que vem em `.mxf` e é detectado por ESSÊNCIA (codec via MediaInfo, cacheado) — ver
[`../protocolos/mxf/codecs-proprietarios.md`](../protocolos/mxf/codecs-proprietarios.md).

### ⚠️⚠️ O estado REAL dos helpers, conferido em 2026-09-21

O que está escrito como "solucionado" precisa desta ressalva antes de virar plano:

| kind | estado | onde |
|---|---|---|
| **BRAW** (macOS) | ✅ compilado e validado (SDK 5.1) — **`Mach-O 64-bit arm64`** | `helpers/bin/relinker-decode-braw` |
| **BRAW** (Windows) | ✅ **construído em 2026-09-21** — ver a seção abaixo | `_CICLO ASSIST/decodificadores/braw/` |
| R3D | **TEMPLATE nunca compilado** ("sem o SDK", diz o próprio doc) | `helpers/red/decode_red.cpp` |
| ARRIRAW | **ESQUELETO com `#error` no topo**, que impede compilar de propósito | `helpers/arri/decode_arri.cpp` |
| Canon, Sony | esqueletos | `helpers/canon/`, `helpers/sony/` |

⛔⛔ **O `decode_braw.cpp` é macOS por dentro:** `#include <CoreFoundation/CoreFoundation.h>`,
e `OpenClip`/`CreateBlackmagicRawFactoryInstanceFromPath` recebem **`CFStringRef`**. Não há
caminho de Windows no `build.sh`. Um app que rode no Windows (o do Media Composer, por
exemplo) **não herda o binário** — herda o contrato e o `.cpp` como ponto de partida.

⚠️ **E "o usuário instala o SDK" não basta sozinho:** o helper é um binário NOSSO compilado
CONTRA o SDK. O SDK é preciso na hora do **build**; o que o usuário instala é o **runtime**
que o helper carrega. Por isso R3D/ARRI não funcionam nem com o SDK instalado — falta o
helper construído.

### 🆕 ⭐⭐ O helper de BRAW no WINDOWS — `confirmado` 2026-09-21

Construído no `_CICLO ASSIST` (`decodificadores/braw/`), porque o serviço dele roda no
Windows, na mesma máquina do Media Composer. **Decodifica 6 quadros de um BRAW 4K em
0,94 s** (0,13–0,18 s cada), com o mesmo contrato de CLI do RELINKER.

⛔⛔ **O porte NÃO é de sintaxe, é de API.** Quatro diferenças, todas medidas:

| | macOS | Windows |
|---|---|---|
| string | `CFStringRef` | **`BSTR`** (`SysAllocString`, UTF-16) |
| header | `BlackmagicRawAPI.h` vem no SDK | ⚠️ **NÃO EXISTE: é gerado do `.idl` pelo MIDL** |
| COM | não | **`CoInitializeEx(nullptr, COINIT_MULTITHREADED)` obrigatório** |
| runtime | `BlackmagicRawAPI.framework` | `BlackmagicRawAPI.dll` + os decoders ao lado |

**Build (Windows):** `midl` gera `BlackmagicRawAPI.h` + `BlackmagicRawAPI_i.c` do `.idl`;
`cl` compila o nosso `.cpp` + o `BlackmagicRawAPIDispatch.cpp` do SDK + o `_i.c`; linka
`ole32.lib oleaut32.lib`.
⚠️ **`MIDL1005: cannot find C preprocessor cl.exe`** — o MIDL usa o `cl` como
pré-processador, então tudo tem de correr DEPOIS do `vcvars64.bat`, e o ambiente dele não
sobrevive entre chamadas: um `.bat` só.

⭐⭐ **O runtime costuma já estar na máquina do editor de Avid:** o plugin AMA de BRAW do
próprio Media Composer instala o `BlackmagicRawAPI.dll` em
`C:\Program Files\Avid\AVX2_Plug-Ins\AMA\BlackmagicRAW\BlackmagicRawAPI`. Outras pastas
conferidas: o SDK (`…\Blackmagic RAW SDK\Win\Libraries`), o Blackmagic RAW Player, o RAW
Speed Test e o DaVinci Resolve. ⇒ **procurar em vez de redistribuir** resolve o caso comum
e deixa a licença fora da conversa.

### ⛔⛔ O BRAW "as shot" é LOG — e o quadro sai LAVADO sem erro nenhum

MEDIDO em 2026-09-21, e é a armadilha mais cara desta página porque **não levanta
exceção**: o decode devolve 0, grava um JPEG válido, e a imagem está achatada.

| | |
|---|---|
| o clipe | `Gamma = Blackmagic Design Film`, `Gamut = Blackmagic Design`, `ColorScienceGen = 5` |
| pelo SDK, sem ajuste | céu **branco**, verde apagado, contraste baixo |
| o `.mp4` que a produção converteu, mesmo frame | céu **azul**, verde vivo |

Um app que entregue o quadro em log faz o modelo de visão descrever *"luz lavada, sem
cor"* de um dia de sol, e joga o vetor de imagem para o grupo errado.

⇒ Antes de pedir o quadro, `SetClipAttribute(…Gamma, …)` com uma gamma de vídeo. Aceitas
neste clipe (todas as três): `Blackmagic Design Extended Video`, `Blackmagic Design
Video`, `Rec.709`. ⚠️ O atributo é do CLIPE e vale para os jobs criados depois dele.

⛔⛔ **`GetClipAttributeList` DERRUBA o processo** — `0xC0000409`
(`STATUS_STACK_BUFFER_OVERRUN`), **sem uma linha no stderr**. Não insista em enumerar: que
gamma o SDK aceita sai de graça TENTANDO pôr cada uma, e o `SetClipAttribute` responde.

⚠️ **O que o MIDL gera não se redistribui.** `BlackmagicRawAPI.h` e `_i.c` são arquivos de
DESENVOLVIMENTO do SDK; a licença do BRAW cobre o runtime e o código-objeto, não os
headers. ⇒ `gerado/` no `.gitignore`; o `.exe`, que é código do app, vai.

### Armadilhas medidas no BRAW SDK 5.1 (macOS)

- Compilar o `decode.cpp` **junto com o `BlackmagicRawAPIDispatch.cpp` do SDK** — é ele que
  provê `CreateBlackmagicRawFactoryInstance*` carregando a framework via `CFBundle`. Linkar
  a framework direto dá símbolo duplicado.
- **Ownership dos jobs:** no `Submit` OK **NÃO** soltar o job — o callback solta
  (`ReadComplete` solta o readJob; `ProcessComplete` solta o decodeJob). Soltar no Submit ok
  = double-release → crash.
- Saída `blackmagicRawResourceFormatRGBAU8` → RGB → JPEG.

### Redistribuição — o que o registro realmente diz (⚠️ `hipotese`, não é conselho jurídico)

- **Blackmagic RAW:** a licença *geralmente* permite redistribuir o **runtime**
  (`BlackmagicRawAPI.framework` + plugins de codec) com o app, royalty-free — é assim que o
  Resolve e apps de terceiros funcionam. **Exige aceitar o EULA do BRAW SDK** e não
  redistribuir headers/dev files. ⚠️ O doc do RELINKER marca isso como presunção a conferir,
  não como permissão confirmada.
- **RED e ARRI:** mais restritivos. *"Não assuma que pode bundlar; pode exigir acordo por
  app."* ⇒ detectar + pedir instalação é o caminho seguro.
- Empacotado, o runtime entra no **codesign e na notarização** (macOS), é de dezenas de MB e
  é por plataforma.

Páginas oficiais: [R3D](https://www.red.com/download/r3d-sdk) ·
[ARRIRAW](https://www.arri.com/en/learn-help/learn-help-camera-system/pre-postproduction/file-formats-data-handling/arriraw) ·
BRAW (site da Blackmagic, família Blackmagic RAW).

## 3. ⚠️ Sequência de imagem: 1 arquivo = 1 frame

EXR, DPX, CinemaDNG e ARRIRAW costumam vir como `shot.0001.ext…`. Quem trata cada caminho
como "um clipe" conta N mídias de 1 frame. O RELINKER agrupa os irmãos no indexador (pasta +
base + extensão + padding), lê metadado só do primeiro, e resolve "frame N → arquivo certo"
na extração. ⚠️ Um app que ainda não faça isso vai ver **602 mídias** onde há **um** plano —
foi o que apareceu na pasta `SAMPLE FOOTAGE/ARRI` desta máquina.

## 4. A regra

⭐⭐ **Pergunte primeiro se há o que reaproveitar.** O SDK resolve "ver o pixel"; ele não
resolve "eu já analisei este material". Num fluxo em que a produção converte para editar —
que é o normal — o RAW é o ORIGINAL de algo que já passou pelo pipeline, e a §1 responde sem
dependência nova, sem licença e sem build por plataforma.

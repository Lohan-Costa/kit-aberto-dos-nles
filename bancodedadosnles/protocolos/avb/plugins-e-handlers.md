# Quem lê a mídia: plugins AMA, motores e a identidade gravada na bin

Como descobrir, **lendo só a `.avb`**, que um clipe depende de um plugin que a máquina pode
não ter — e por que "GUID do plugin" não é uma coisa só. Os fatos consumíveis estão em
[dados/ama-online.json](dados/ama-online.json) (`dois_motores`, `camadas_de_identidade`,
`roteamento_registered_extensions`, `container_handler_guids`).

Tudo aqui é `confirmado`, medido em 2026-08-20 num MC 25.6.0.58781 / Windows 11, com um
experimento controlado dos dois lados:

- **três codecs, um motor** — X-OCN LT, ST e XT (8K, Sony VENICE) na mesma bin, todos pelo
  plugin do nablet;
- **um arquivo, dois motores** — o *mesmo* ProRes 4444 linkado uma vez pelo `MSP_MXF` da
  Avid e outra pelo UME.

## O modelo: dois motores, não dois mecanismos

O banco registrava, desde 2026-07-02, que havia "DOIS mecanismos de assinatura de tipo":
uns formatos traziam `_CONTAINER_HANDLER_GUID`, outros só `descriptor.uuid`. Não são dois
mecanismos para a mesma coisa — são **dois motores de leitura de mídia**, e cada um se
identifica do seu jeito.

| | **AMA legado** (`MSP_*`) | **UME** (Universal Media Engine) |
|---|---|---|
| onde vive | `AVX2_Plug-ins/AMA/<Formato>/*.avx` | `Avid Media Composer/AVX2_Plug-Ins/UME/*.acf` (e `AMA/Q7/`) |
| `descriptor.uuid` | ✔ | ✔ (**valor diferente**) |
| `descriptor.wchar` | ✔ `[fabricante][plugin][versão][classe]` | ✘ **não escreve nada** |
| `descriptor.attributes._CONTAINER_HANDLER_GUID` | ✘ vazio | ✔ 16 bytes crus |
| exemplos | MSP_MXF, nablet SONY RAW, BlackmagicRAW, WaveAiff | MXF_ContainerHandler, QTFFContainerHandler |

A prova é o par de bins com o mesmo arquivo:

```
                         MSP_MXF                                UME
descriptor.uuid          60eb8921-2a02-4406-891c-d9b6a6ae0645   87a0584d-cafa-41f5-9a68-f0cadefdbb71
descriptor.wchar         [Avid Technology, Inc.][MSP_MXF        (ausente)
                          Plug-In][1.23.4.11223][GenericMXF…]
_CONTAINER_HANDLER_GUID  (ausente)                              930687b5dbc8e341aaeb7c3dcb37540c
MobIDs, raster, sub-descritores                    IDÊNTICOS nos dois
```

Os 16 bytes do `_CONTAINER_HANDLER_GUID` foram rastreados até
`AVX2_Plug-Ins/UME/MXF_ContainerHandler.acf`, gravados lá **na mesma ordem de bytes** —
sem troca de endianness entre a bin e o binário, ao contrário dos GUIDs dos `.avx`, que
aparecem em `bytes_le`.

> ⭐ **Regra de leitura para um app:** tentar `_CONTAINER_HANDLER_GUID` primeiro, cair para
> `wchar` depois, e usar `descriptor.uuid` como chave nos dois casos. **Um app que só saiba
> ler `wchar` fica cego em toda mídia linkada pelo UME.**

## `descriptor.uuid` diz QUEM LEU, nunca O QUE É

Os dois experimentos fecham a pergunta pelos dois lados:

- **três codecs → um uuid.** X-OCN LT, ST e XT saíram todos com
  `0059fb34-4ed5-493e-9be8-f11d16b4b7da`.
- **um arquivo → dois uuids.** O mesmo ProRes deu `60eb8921` por uma rota e `87a0584d` pela
  outra.

Quem carrega o **codec** é `MasterMob.attributes._USER['Video']`
(`Sony CV X-OCN LT` / `ST` / `XT`). Os dois campos são complementares:
**`uuid` = quem lê · `_USER['Video']` = o que é.**

⚠️ Mas `_USER['Video']` **só existe quando um plugin de terceiro preenche**. No ProRes
linkado por qualquer um dos dois motores da Avid, `_USER` veio `{}` — vazio. A mera
presença do campo já é sinal de "esta mídia veio por plugin de fora".

## "GUID do plugin" são TRÊS camadas

| camada | onde vive | MOV/MP4 | MXF |
|---|---|---|---|
| **1. roteamento** (extensão → plugin) | `RegisteredExtensions.xml` + o `.avx` (`bytes_le`) | `781f84b7-…` | `60eb8921-…` |
| **2. container handler** | `_CONTAINER_HANDLER_GUID` na bin + o `.acf` (bytes crus) | `73dc063c-…` | `930687b5-…` |
| **3. assinatura do descriptor** | `descriptor.uuid` na `.avb` = `MediaContainerGUID` no AAF | `87a0584d-…` | `60eb8921` ou `87a0584d` |

**No MXF as camadas 1 e 3 coincidem; no MOV são três valores diferentes.** Essa
coincidência no MXF é justamente o que faz o modelo simples *parecer* funcionar.

E note a camada 3: é a única que **sobrevive ao export de AAF**, com o nome próprio
`MediaContainerGUID`. O `wchar` **não** vai para o AAF — nem `nablet`, nem `F65Raw`, nem
`MSP_MXF` existem no arquivo exportado. Mais um argumento para
[ler a bin, não o AAF](dados/ler-timeline-sem-aaf.json).

## O plugin de terceiro NÃO se registra por extensão

`AMAAutodetect/RegisteredExtensions.xml` mapeia extensão → GUID de plugin. Instalar o
nablet deixou o arquivo com o **sha256 inalterado** (medido antes e depois), e o
BlackmagicRAW, que está instalado, também não aparece lá. A tabela é **estática, só da
Avid**, e `MXF` já pertence ao `GenericMXF` (`60eb8921`).

⭐ **É por isso que X-OCN exige abrir o Source Browser e escolher `Link with → Sony RAW
X-OCN`:** o autodetect não tem como desempatar duas famílias que usam a mesma extensão, e o
menu é um **override de roteamento**, não um capricho de interface. Também é a origem da
mensagem `AMA Autodetect: Registered matchings were not found`, que o banco já classificou
como ruído em [../../transversal/ambiente-media-composer-windows.md](../../transversal/ambiente-media-composer-windows.md).

⚠️ **A tabela lista formatos que a máquina não tem.** ARRIRAW, PhantomCine e RED estão no
XML sem nenhum binário instalado. Um app que decida "consigo ler `.r3d`" por esse arquivo
vai errar — a pergunta certa é se o `.avx` correspondente existe.

## O GUID mora dentro do binário do plugin — e isso responde a pergunta útil

Varrendo os `.avx`/`.acf`/`.dll` das pastas AMA, o GUID do handler aparece no próprio
binário. Medido antes e depois de instalar o nablet:
`0059fb34-…` não existia em binário nenhum e passou a existir em
`nablet_MVP_MSP_SONY_RAW.avx` **e** `.dll`, em `bytes_le` — a mesma codificação dos plugins
da própria Avid.

⭐ Logo dá para responder **"a bin pede um plugin que esta máquina tem?"** cruzando o
`descriptor.uuid` lido da bin com uma varredura de `AVX2_Plug-ins` — **sem abrir o Media
Composer**.

⚠️ **Calibração:** funciona para MSP_MXF, WaveAiff, QuickTime e nablet. **Não** funciona
para o BlackmagicRAW — o GUID `bd449ccc-…` não está no `BlackmagicRAW.avx`. Ausência no
binário não prova ausência do plugin; só a presença é conclusiva.

## O `wchar` é um carimbo de link, não um estado atual

O fabricante documenta, no manual do nablet:

> *"clips … previously linked by the legacy plug-in will show the legacy plug-in name in the
> bin … because the initial information is stored persistently in the AVB file during
> linking."*

Medido: uma bin de agosto diz `[nablet SONY RAW Plug-in][5.1.0.5530]` e a bin nova diz
`[2026.8.0.6299]` — para o mesmo plugin, depois da atualização. Vale também para os plugins
da Avid: `[MSP_MXF Plug-In][1.22.11.10176]` num MC 21.12 e `[1.23.4.11223]` num MC 25.6.

Então `wchar` responde **quem linkou, com que versão, naquele dia** — é rastro histórico
excelente e verificação de dependência **ruim**. Para saber quem lê hoje, use `uuid` + o que
está instalado.

## Instalar um plugin de terceiro: o que muda no disco

O `nablet SONY RAW X-OCN AMA Plug-In 2026.8.0.6299` (Inno Setup, assinado com certificado EV
de `nablet GmbH`) acrescentou cinco arquivos numa pasta própria:

```
C:\Program Files\Avid\AVX2_Plug-ins\AMA\nablet\SONY_RAW\
   nablet_MVP_MSP_SONY_RAW.avx    32 KB   v2026.8.0.6299   casca AVX (carrega o GUID)
   nablet_MVP_MSP_SONY_RAW.dll   1,9 MB   v2026.8.0.6299   implementação (carrega o GUID)
   SonyRawDev.dll                2,9 MB   v6.0.0.0         decoder da Sony
   SMDK-VC140-x64-4_27_0.dll     4,8 MB   v4.27.0.183      Sony MXF Development Kit
   unins000.exe                  3,6 MB                    desinstalador
```

Note a pasta: **`AVX2_Plug-ins` na raiz da Avid**, fora do Media Composer — é onde já vive o
`BlackmagicRAW`, e é por isso que esses plugins sobrevivem a upgrade do MC. Os plugins
*bundled* ficam do outro lado, em `Avid Media Composer\AVX2_Plug-Ins\AMA\`.

⚠️ **O manual do fabricante manda apagar "a pasta `SonyRaw`" em `AVX2_Plug-ins`**; nesta
versão a pasta é `AVX2_Plug-ins\AMA\nablet\SONY_RAW`. A instrução de desinstalação está
desatualizada — quem seguir o manual não acha a pasta.

⭐ O `SMDK-VC140-x64` é o **mesmo Sony MXF Development Kit** que a câmera declara em
`application_platform` dentro do próprio arquivo (visível no `ffprobe`). Ler o MXF exige o
SDK que o escreveu.

Restrição operacional que não é técnica mas decide adoção: o plugin é **pago, por estação**,
ativado pelo `nablet Plugins Manager`, e a máquina precisa ver a internet **pelo menos a
cada dois dias** ou a licença cai em modo demo (com marca d'água na imagem).

## ⭐ O motor viaja no molde (confirmado, MC 24.6.0 / Windows 11, 2026-10-18)

Clone por byte-surgery de um master já linkado (o `clone_generic` do `_DeLaPraCa`) **abre pelo mesmo plugin do
molde**: "UME Link" (H.264 MP4/MOV) e **"Blackmagic RAW"** (plugin de outro fabricante) conferidos coluna a coluna
contra o `LinkFile` do MC, e pela imagem. A coluna **`Plug-in`** do `GetMobInfo` diz o motor de cada master.
⇒ O `Link with` do Source Browser, feito UMA vez no molde, governa os irmãos injetados — o caminho para o X-OCN
(`pendente`: medir com o plugin da Sony instalado, um molde do `MSP_MXF` e outro do nablet). Detalhes e as correções
do clonador em [escrita.md](escrita.md) §"Linka o primeiro, injeta os irmãos".

## Ver também

- [dados/ama-online.json](dados/ama-online.json) — a tabela completa de GUIDs e os três modelos.
- [../mxf/codecs-proprietarios.md](../mxf/codecs-proprietarios.md) — como identificar, **do lado do arquivo**, que um MXF precisa de plugin.
- [estruturas.md](estruturas.md) — a taxonomia de mobs em que essas identidades se penduram.

# Ambiente do Media Composer no Windows — o que quebra fora do formato

> ⭐ O lado macOS de cada caminho e comportamento daqui está na
> [matriz de plataforma](matriz-de-plataforma.md), seção G.

Transversal porque **não é sobre arquivo nenhum**. É sobre a máquina onde o NLE roda: antivírus,
dependências que não aparecem em import table, pontes de 32 bits e lixo de sistema de arquivos
alheio. Um app que gera `.avb`/`.aaf` perfeitos ainda entrega "não funciona" se o ambiente do
editor estiver assim — e o sintoma que o editor relata **aponta para o lugar errado** nos quatro
casos abaixo.

Levantado numa sessão de diagnóstico em estação real (2026-08-19): **Media Composer 25.6.0.58781,
Windows 11 23H2 (10.0.22631), estação ILHA02**. Todos os quatro achados são `confirmado` — cada um
foi reproduzido e a correção validada na tela.

Complementa [analise-de-executaveis.md](analise-de-executaveis.md): lá é engenharia reversa do
binário do concorrente; aqui é o **runtime** em volta do binário.

---

## 1. Trava no splash em `AAFProcessor.avx` = antivírus, não plugin (`confirmado`)

### Sintoma

O MC congela no splash exibindo `Initializing plugin: AAFProcessor.avx`. Force quit, reabre, e
**na segunda vez sobe normal**. Todo dia.

### O que era

Varredura em tempo real do **Windows Defender**. Confirmado pela própria Avid
([KB: Media Composer hanging at AAFProcessor.AVX during startup](https://kb.avid.com/pkb/articles/en_US/Knowledge/Media-Composer-hanging-at-AAFProcessor-during-startup)),
que cita HP Wolf Security e Windows Defender.

⭐ **Por que a segunda tentativa funciona** — e é isso que faz o editor jurar que "é bug do Avid":
o Defender guarda em **cache** o resultado do scan dos arquivos já verificados. A primeira abertura
escaneia tudo frio e trava; depois do force quit os binários já estão marcados como limpos.
**Não é o force quit que conserta, é o cache que aqueceu.**

### O método que fecha o diagnóstico (serve para qualquer trava de app no Windows)

O Windows escreve um relatório de hang com a **lista de módulos carregados em ordem de carga**:

```
C:\ProgramData\Microsoft\Windows\WER\ReportArchive\AppHang_<app>_<hash>\Report.wer
```

É **UTF-16LE** (`iconv -f UTF-16LE`). Os campos que importam:

| campo | serve para |
|---|---|
| `Sig[3].Value` (Hang Signature) | mesma assinatura em todas as ocorrências = causa única e reproduzível |
| `Response.LegacyBucketId` | idem, agrupa as ocorrências |
| `LoadedModule[N]` | ⭐ **ordem de carga** — os últimos são o que estava acontecendo no instante do travamento |

Na estação, os últimos módulos antes do congelamento:

```
[274] C:\Windows\SYSTEM32\amsi.dll
[275] C:\ProgramData\Microsoft\Windows Defender\Platform\...\MpOav.dll
 ...
[285] ...\AVX2_Plug-Ins\AAFProcessor.avx
[286] ...\IMEX.dll
```

`amsi.dll` + `MpOav.dll` **dentro do processo do MC**, imediatamente antes do plugin que aparece no
splash. O scanner do Defender injetado, segurando o arquivo. Réu identificado sem depurador.

⚠️ **Filtre os módulos por caminho, não por nome.** Dos 287 carregados, exatamente **um** estava
fora de `C:\Windows` e `C:\Program Files\Avid` — e era o `MpOav.dll`. Essa é a peneira que faz o
culpado saltar.

### Correção

Exclusões no Defender (caminhos + processos). Lista completa e reutilizável em
[ambiente-media-composer-windows.json](ambiente-media-composer-windows.json) →
`defender_exclusoes`.

⚠️ **`Get-MpPreference` responde `"N/A: Must be an administrator to view exclusions"` sem
elevação** — e esse retorno é a prova barata de que o script rodou elevado de verdade. O cabeçalho
do `Start-Transcript` **não** serve: ele imprime `RunAs User` igual ao usuário normal mesmo em
sessão elevada.

⚠️ Exclusões valem **na hora**, sem reboot. Mas processos **já em execução** não pegam a regra
nova — para medir o efeito, reinicie o app.

⛔ **Formatar o Windows APAGA as exclusões** (medido em 2026-10-22, estação do autor, MC 2024.6): a
trava voltou idêntica no primeiro dia depois da formatação. Reaplicar o script antigo quase serve,
mas **os drives mudam de letra e de papel**: o antigo excluía `E:\` inteiro, que depois da formatação
virou o disco de BACKUP, enquanto a mídia AMA passou a morar no SSD (`D:\MIDIAS DE TESTES`). Revise a
linha "drive de mídia" a cada máquina; nunca exclua um disco inteiro só porque o script antigo
excluía. A versão de hoje usa `%LOCALAPPDATA%`/`%APPDATA%`/`%USERPROFILE%` e recusa rodar sem elevação
(está na Área de Trabalho da estação: `avid-defender-exclusoes.ps1`).

---

## 2. ⭐⭐ AMA de MP4/H.264 exige QuickTime 7 instalado no Windows (`confirmado`)

### Sintoma

MP4 H.264 comum (aqui: export do DaVinci Resolve, avc1 High, 2048x1080, AAC-LC) **não linka**; ou
linka com duração e TC corretos e **trava o MC no play**.

### As assinaturas de console

```
Unable to autodetect plug-in for <arquivo>.mp4
[AMA|FI/IdentityProvider] UMID generation from container contents failed.
[AMA|FI/IdentityProvider] SourceID retrieval failed.
[AMA|FI/MetadataTranslator] Error HRESULT 0xa0000070
```

e no play:

```
Exception caught in APlayer::Play - ... CreateContainerHolder.InitContainerHandler failed:
InitContainerHandler - CH Init failed: -1610612625
...\coresw\ame\src\AMAFI\AMAFI_AME_Utils.cpp line 828
```

⭐ **`-1610612625` é `0xA000006F`** (soma 2³²). Vizinho imediato do `0xA0000070` do link. Mesma
família de falha: **nenhum container handler válido ficou associado ao clipe**. Traduza sempre o
inteiro negativo para hex antes de procurar significado.

### A arquitetura que explica tudo

| componente | arquitetura |
|---|---|
| `AvidMediaComposer.exe` | **x64** |
| `AVX2_Plug-Ins\AMA\QuickTime\MVP_MSP_QuickTime.avx` | x64 (stub) |
| `AVX2_Plug-Ins\QuickTime_OPClient.avx` | x64 (cliente IPC) |
| `Avid Media Composer\QuickTimeServer\QuickTime_OPServer.exe` | ⭐ **32-bit** |
| `C:\Program Files (x86)\QuickTime\QTSystem\QTMLClient.dll` | ⭐ **32-bit** (QT 7.7.9, dez/2015) |

O MC é 64-bit, o QuickTime é 32-bit, e processos de arquiteturas diferentes não compartilham
espaço de memória. A Avid resolve com um bridge **out-of-process**: o MC gera helpers
`QuickTime_OPServer.exe` de 32 bits que hospedam o QuickTime e devolvem frames por IPC (`OP` =
out-of-process). Observados **4 helpers** simultâneos numa sessão de edição normal.

**Sem o QuickTime instalado, os helpers sobem e morrem sem inicializar** → `CH Init failed`.

### ⚠️⚠️ A armadilha de método que custou a sessão inteira

Para provar "faltando dependência", o reflexo é extrair a **import table (PE)** dos plugins. Feito,
em todos os `.acf`/`.avx`/`.dll` de CodecToolkit, Q7, UME, MediaProcessor e Codecs. Resultado: tudo
resolve. O plugin do QuickTime importa:

```
KERNEL32.dll  MSVCP140.dll  VCRUNTIME140.dll  api-ms-win-crt-*
```

**Zero referência ao QuickTime.** A conclusão "dependências OK" estava tecnicamente correta e
completamente inútil.

⭐ **A regra que fica: import table só enxerga link ESTÁTICO e só dentro do MESMO processo.** Ela é
cega para (a) `LoadLibrary` em runtime e (b) qualquer coisa que aconteça num processo helper. Em
arquitetura com ponte de bitness — e a de post está cheia delas — a pergunta certa não é "o que
esse binário importa?", é:

1. Existe um `*_OPServer.exe` / `*Server.exe` / `*Host.exe` ao lado? Qual a arquitetura dele?
2. Ele está rodando? (`Get-Process ... | Select-Object Path`)
3. O que **ele** carrega — e o que ele espera achar instalado no sistema?

⚠️ **E o falso negativo do `objdump -p` na pasta errada:** o `QuickTime_OPServer.exe` não está na
raiz do MC, está em `Avid Media Composer\QuickTimeServer\`. Pegue o caminho do **processo vivo**,
não do `find`.

### ⚠️ A linha de console que NÃO é o erro

```
[QuickTime Plug-In] The FOURCC video code of avc1 is not natively supported.
```

**É normal e aparece também quando tudo funciona** (depois de instalar o QuickTime ela continua
lá, quatro vezes seguidas por clipe). O `AVX2_Plug-Ins\AMA\QuickTime\FourCharMapper.xml` lista só
os codecs **nativos da Avid** — DNxHD, DNxHR, ProRes. `avc1` nunca esteve nessa tabela: o plugin
recusa de propósito e passa a bola adiante. **Nunca diagnostique a partir dessa linha.**

Mesma categoria: `CDCIDescriptor::GetAAFProperties: Either B/W points or ColorRange missing` e
`AudioMediaDesc::ConvertDescriptorFromAAF unable to recognize audio coding` — ambas presentes no
estado **funcionando**.

### Custo residual

Depois de instalado, link e play funcionam, mas passam por IPC até um processo 32-bit hospedando
um QuickTime de 2015 — **é lento por construção**. Na estação, o link só voltou à velocidade normal
depois de somar `E:\` (o drive de mídia) e o `QuickTime_OPServer.exe` às exclusões do Defender:
sem isso cada leitura era escaneada **em dobro**, uma vez no MC e outra no helper.

Saída definitiva para acervo grande: transcodificar para **DNxHR MXF**, que é nativo e não toca a
ponte.

⚠️ Nota de segurança, sem alarde: o QuickTime 7 para Windows foi descontinuado em 2016 e não recebe
correção desde então. O MC depende dele; mantenha instalado e não use o QuickTime Player em si.

---

## 3. Arquivos AppleDouble (`._nome.ext`) envenenam o AMA autodetect (`confirmado`)

Mídia que passou por um Mac volta com um sidecar por arquivo:

```
._B001_03150112_C001.mp4      4096 bytes    ← lixo AppleDouble
  B001_03150112_C001.mp4   4264495 bytes    ← mídia real
```

⭐ **O sidecar carrega a MESMA extensão.** Para o Windows e para o AMA, `._X.mp4` é um `.mp4` como
qualquer outro: o autodetect tenta linkar, não acha container, e cospe exatamente
`UMID generation from container contents failed` + `SourceID retrieval failed`. O link demora o
dobro e falha na metade.

Identificação por conteúdo (não confie só no prefixo):

| bytes 0..3 | string em 0x08 |
|---|---|
| `00 05 16 07` | `Mac OS X` |

Na estação: **118 MP4 reais / 118 sidecars**, 57 `._*.wav`, 18 `.DS_Store` — **601 no total** em
`E:\MIDIAS DE TESTES`. Datas denunciam o evento: mídia de out/2025, sidecars de **14/jun/2026**, o
dia em que "parou de funcionar".

⚠️ **Varra por conteúdo e mova, não apague** — mover para uma quarentena espelhada com manifesto
deixa o passo reversível. E lembre que a **própria pasta do banco de dados** tem `._CONVENCOES.md`
e `._README.md`: qualquer varredura de acervo precisa filtrar isso, e qualquer app que enumere
mídia deve ignorar `^\._` e `.DS_Store` **antes** de contar arquivos.

### ⚠️ Correção de rota registrada de propósito

Numa primeira análise isto foi apontado como **a** causa do MP4 não linkar. **Estava errado** — a
causa era o QuickTime ausente (§2). Os sidecars eram um problema real e independente, e removê-los
melhorou o link, mas o `Unable to autodetect plug-in` continuou aparecendo para o arquivo real
depois da limpeza. ⭐ **Esse é o teste que separa "achei lixo" de "achei a causa": o sintoma
específico sobreviveu à correção.** Se a linha de erro continua idêntica, a hipótese caiu — por
mais convincente que fosse a correlação de datas.

---

## 4. Roteamento do AMA autodetect por extensão (`confirmado`, referência)

```
AVX2_Plug-Ins\AMA\AMAAutodetect\RegisteredExtensions.xml
```

Mapeia **extensão → GUID de plugin**. Útil para prever qual plugin vai ser chamado:

| extensões | plugin | GUID |
|---|---|---|
| MOV, MP4, M4V, M4A, 3GP, 3G2, AVI, MPEG, MPG, MP3, AAC, JPG, PNG, TIF, PSD, BMP, GIF… | QuickTime | `781F84B7-B989-4534-8A07-C595CB9A6FB8` |
| MXF | GenericMXF | `60EB8921-2A02-4406-891C-D9B6A6AE0645` |
| M2TS, MTS | AVCHD | `F37D624B-307D-4EF5-9BEB-C539046CAD54` |
| WAV, AIF, AIFF, BWF, WAVE, CDDA | WaveAiff | `3711D3CC-62D0-49D7-B0AE-C118101D1A16` |
| R3D | RED | `2208D9E0-D9E1-4B50-A0BA-E03BB2C315FB` |
| ARI | ARRIRAW | `A172ADFA-CD97-414A-B257-3351B95F07C5` |
| DPX / CINE | DPX / PhantomCine | `4964178D-…` / `9FC22562-…` |

⭐ **`.MP4` e `.MOV` caem no MESMO plugin** — o QuickTime. É por isso que a falta do QuickTime 7
derruba os dois de uma vez, e é por isso que "rewrap de MP4 para MOV" **não** contorna o problema.

Estado dos plugins não é lido daqui: `AMA Management` desabilitado à mão apareceria no
`Site_Settings.xml` (em `C:\Users\Public\Documents\Avid Media Composer\Settings\`). Ausência da
entrada = tudo habilitado no padrão.

---

## 5. Onde o MC guarda estado (mapa, `confirmado`)

| caminho | conteúdo |
|---|---|
| `C:\Users\Public\Documents\Avid Media Composer\Settings\Site_Settings.xml` | site settings (gravado a cada sessão) |
| `C:\Users\Public\Documents\Avid Media Composer\Avid Users\<user>\` | `.ave`, `MCState`, `<user> Settings.xml` |
| `%LOCALAPPDATA%\Avid\Crashlog\*.dmp` | ⭐ dump **de 0 byte = force quit de processo travado** (marcador barato de hang, não de crash) |
| `%APPDATA%\AvidMediaComposer\QtWebEngine\<panel-id>\` | estado dos painéis do Panel SDK |
| `C:\ProgramData\Avid\` | dados compartilhados, licenciamento (`SWL`) |

---

## 6. Na bin, o NOME renomeia; o ÍCONE seleciona e abre (`confirmado`, autor, 2026-10-22, MC 2024.6)

Um clique no nome de qualquer item da bin ativa a caixa de renomear. Para selecionar, arrastar ou abrir (duplo clique:
master/subclipe no Source, sequência na Record), o gesto é no ÍCONE à esquerda do nome. Vale para automação (piloto):
um duplo clique sintético no nome deixa o item em modo de edição, e a tecla seguinte vira o nome novo do item.

## Checklist rápido — editor diz "o Avid parou de linkar/abrir"

1. É trava no splash? → `Report.wer` mais recente, olhar `LoadedModule[N]` do fim para o começo,
   filtrando por caminho fora de `C:\Windows` e da pasta do app. (§1)
2. Extensão da mídia → `RegisteredExtensions.xml` → qual plugin deveria atender. (§4)
3. Esse plugin tem helper out-of-process? Arquitetura dele? A dependência de sistema está
   instalada? **Não pergunte à import table.** (§2)
4. Código de erro negativo → converter para hex antes de procurar. (§2)
5. Varrer `._*` e `.DS_Store` no acervo, por conteúdo. (§3)
6. Antivírus: excluir binários do app, processos helper **e os drives de mídia**. (§1, §2)
7. Ignorar `avc1 is not natively supported`, `CDCIDescriptor ... B/W points` e
   `ConvertDescriptorFromAAF unable to recognize audio coding` — todas presentes no estado bom. (§2)

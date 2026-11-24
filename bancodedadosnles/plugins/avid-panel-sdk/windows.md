# Panel SDK no WINDOWS — e o que muda de VERSÃO para VERSÃO

> **Por que este arquivo existe:** tudo o que esta pasta documentava saiu de **um** Media
> Composer — 25.12 no macOS. Ao levar a integração do Órbita para o Windows (MC **25.6.0.58781**,
> Windows 11 23H2, 2026-08-15) descobriu-se que **três coisas que pareciam "como o Panel SDK é"
> eram na verdade "como aquela versão naquele SO é"**. Este arquivo separa as duas categorias.
>
> ⭐ **A lição de método, antes dos fatos:** com uma única instalação de referência não há como
> distinguir *plataforma* de *versão*. Duas instalações revelaram que a diferença mais visível
> (o menu onde o painel aparece) **não é do SO — é da versão**, e a mais cara (um rpc que some)
> também. Quem for depurar "o painel não aparece" precisa saber em qual dos dois eixos olhar.

---

## 1. Caminhos e portas no Windows — `confirmado`

Medidos numa instalação real, com um painel de TERCEIRO já presente (`avid-huddle.avpi`,
distribuído pela Avid) servindo de controle:

| o quê | macOS | Windows |
|---|---|---|
| **Painéis do Panel SDK** | `/Library/Application Support/Avid/PanelSDKPlugins` | **`%PROGRAMDATA%\Avid\PanelSDKPlugins`** (= `C:\ProgramData\Avid\PanelSDKPlugins`) |
| Config do gateway | `…/Avid/APIGateway/config.json` | `C:\ProgramData\Avid\APIGateway\config.json` |
| Faixa de portas dos painéis | `…/Avid/Avid Media Composer/PanelSDK.json` | `C:\ProgramData\Avid\Avid Media Composer\PanelSDK.json` |
| Executável do MC | `…/AvidMediaComposer.app/Contents/MacOS/AvidMediaComposer` | `C:\Program Files\Avid\Avid Media Composer\AvidMediaComposer.exe` |
| Gateway | `…/Contents/MacOS/avid-api-gateway` | `C:\Program Files\Avid\Avid Media Composer\avid-api-gateway.exe` |

Conteúdo dos dois JSON no Windows (idêntico ao do macOS):

```json
// APIGateway/config.json
{ "apiPort": 4920, "pluginPort": 4930 }
// Avid Media Composer/PanelSDK.json
{ "ports": "9100-9110" }
```

⚠️ **É `%PROGRAMDATA%`, não `%APPDATA%`** — a pasta é de SISTEMA, como no macOS. Isso é
coerente com o resto do SDK e diferente dos outros dois NLEs, que instalam por usuário
(Premiere CEP em `%APPDATA%\Adobe\CEP\extensions`, Resolve em `%APPDATA%\Blackmagic Design\…`).

**Instalar não pediu elevação** nesta máquina — mesmo achado do macOS (lá a pasta é `rwxrwxrwx`).
Não confirmado se vale para toda instalação do Windows: pode depender da ACL herdada.

---

## 2. ⭐ O menu NÃO é "Extensions" — e isso é VERSÃO, não SO — `confirmado`

**Corrige um fato antes registrado como `confirmado`.** O `fontes.md` desta pasta dizia:
*"Painel 3P aparece sob menu top-level **Extensions** (não `menuName`)"*, medido no 25.12/macOS.

No **MC 25.6 (Windows) não existe menu `Extensions`**. A barra é
`File · Edit · Bin · Clip · Timeline · Composer · Tools · Windows · Script · Help`, e o painel
aparece **dentro de Tools**, que é exatamente o `menuName` declarado no manifesto.

**A prova de que é versão e não plataforma** está na mesma máquina: o `avid-huddle.avpi`, painel
**da própria Avid**, declara `"menuName": "Tools"` no manifesto dele — igual ao nosso — e também
aparece em Tools. Ou seja, as duas versões recebem o mesmo manifesto e decidem diferente:

| versão | onde o painel aparece | `menuName` honrado? |
|---|---|---|
| MC 25.6 (Windows, medido 2026-08-15) | **Tools** | ~~sim~~ **ver a correção abaixo** |
| MC 25.12 (macOS, medido 2026-08-07) | **Extensions** (menu novo, top-level) | não — agrupa por conta própria |

**Consequência para quem escreve manifesto:** continue declarando `menuName`, mas **não
prometa ao usuário em qual menu o painel vai estar** — a documentação do seu produto tem de
cobrir os dois casos, ou dizer "procure em Tools ou Extensions". Foi exatamente aqui que
se perdeu tempo achando que o painel não tinha instalado, quando ele estava carregado e visível
no menu de sempre.

### ⚠️ `CORRIGE:` 2026-08-17 — "o 25.6 honra `menuName`" era `confirmado` e não estava medido

A conclusão acima foi tirada de três painéis (`avid-huddle`, `com.orbita.sync`,
`com.usuario.delapraca.mc`) que aparecem em Tools. **Os três declaram
`"menuName": "Tools"`.** A amostra inteira era compatível com as duas explicações
concorrentes — *"o menu declarado é obedecido"* e *"vai sempre para Tools"* — e o fato foi
promovido a `confirmado` sem nenhum caso que pudesse refutá-lo.

**O primeiro teste refutador, 2026-08-17** (MC 25.6.0.58781 / Win 11, mesma máquina): um
`uiItem` declarando **`"menuName": "Windows"`**, empacotado, instalado, MC fechado, gateway
morto por `reload.py`, MC reaberto — build nova confirmada pelo selo de versão no rodapé do
painel (0.1.8), não é cache. **Resultado: nada apareceu no menu `Windows`, e o item continuou
em Tools.**

Leitura: no 25.6 o `menuName` **não é o que decide** — pelo menos não para um `uiItem` que
não seja o primeiro. O comportamento observado é o mesmo do 25.12, só que o menu de destino
se chama `Tools` em vez de `Extensions`, e é essa coincidência de nome que sustentou o erro.

⏳ **O que discrimina, e ainda não foi feito:** um painel com **UM único** `uiItem` declarando
`menuName` diferente de `Tools`. Se ele também for para Tools, `menuName` é decorativo no
25.6; se for para o menu declarado, a regra é "todos os `uiItems` do plugin herdam o menu do
primeiro". Para **quem escreve manifesto o conselho não muda** nos dois casos: não conte com
`menuName`.

⭐ **A lição de método, que vale mais que o fato:** *toda a amostra concordava porque toda a
amostra tinha o mesmo valor na variável em teste.* Antes de marcar `confirmado`, pergunte
**qual observação teria refutado isto** — se não houver nenhuma no conjunto, o que se tem é
`inferido`, por mais casos que se acumulem.

---

## 3. ⭐ `GetListOfWindows` NÃO EXISTE no 25.6 — `UNIMPLEMENTED` — `confirmado`

O rpc está no [`mcapi.proto`](dados/mcapi.proto) (extraído por reflection do 25.12) e responde
normalmente lá. No 25.6 ele responde **`UNIMPLEMENTED`**, e a ausência foi confirmada por
enumeração dos símbolos do binário — a lista completa de `GetListOf*` presentes no 25.6:

```
GetListOfBinItems      GetListOfCommands              GetListOfExportSettings
GetListOfClips         GetListOfCompatibleProjectTypes GetListOfImportSettings
GetListOfExportEDLSettings  GetListOfJobQueues        GetListOfLinkSettings
GetListOfProjectTypes  GetListOfProjectTypesForDecompose
GetListOfRasterTypes   GetListOfRasterWidths
```

**`GetListOfWindows` não está entre eles.** Ou seja: não é permissão, não é escopo de `usesApi`,
não é gateway — o método não existe naquela build.

### Por que isso importa muito mais do que parece

`GetListOfWindows` é a **única** forma conhecida de saber **quais bins estão ABERTAS** na
interface (ver [README §leitura de estado](README.md)). Quem usa isso como otimização — perguntar
a seleção só das bins abertas, porque cada bin custa ~500 ms — perde a otimização, não a função.

⚠️ **A armadilha na hora de degradar:** tratar o rpc ausente como *"nenhuma bin está aberta"*
(lista vazia) **inverte o resultado**: o filtro zera a lista e a seleção volta VAZIA, como se o
editor não tivesse marcado nada. O correto é **não filtrar** e perguntar a todas as bins — mais
lento, e verdadeiro. No Órbita isso virou teste de regressão.

### Receita: detectar e degradar (não morrer)

```python
# grpc.StatusCode.UNIMPLEMENTED merece exceção PRÓPRIA, separada de "falhou":
# é diferença de versão do MC, não defeito do app nem do editor.
try:
    abertas = set(mc.bins_abertas())        # usa GetListOfWindows
except McApiNaoImplementado:
    abertas = None                          # "não dá para saber" ≠ "nenhuma"
caminhos = todas_as_bins if abertas is None else [b for b in todas_as_bins if nome(b) in abertas]
```

**Regra geral:** num SDK cuja versão você não controla, todo rpc de *conveniência* precisa de um
caminho sem ele. O sintoma de não fazer isso é péssimo — o editor vê `"GetListOfWindows falhou:
UNIMPLEMENTED"` e **nada** funciona, inclusive funções que não dependiam daquele rpc (no Órbita,
o seletor de bins caiu junto porque era alcançado *depois* da chamada que estourava).

---

## 4. O gateway no Windows, e a ASSINATURA DO ÓRFÃO que muda de SO — `confirmado`

Com o MC aberto (medido):

```
AvidMediaComposer.exe   pid 15132   ppid 13488 (explorer)
avid-api-gateway.exe    pid  5280   ppid 15132  ← FILHO do MC
```

Portas em escuta:

| porta | quem | endereço |
|---|---|---|
| 4920 / 4930 | `avid-api-gateway.exe` | **`::1` apenas** |
| 9100 | `AvidMediaComposer.exe` | **`::1` E `127.0.0.1`** |

⚠️ **O gateway só escuta em IPv6.** O backend `mcapi.MCAPI` (9100) escuta nas duas famílias, então
um cliente que use o literal `[::1]:9100` funciona nos dois SOs sem ambiguidade — é o que o Órbita
faz, e é o que se recomenda. **Não use `localhost`** para falar com essas portas no Windows: veja
a armadilha medida em
[transversal/desenvolvimento-cross-platform.md](../../transversal/desenvolvimento-cross-platform.md).

### ⭐ O "gateway órfão" existe nos dois SOs, mas NÃO SE DETECTA DO MESMO JEITO

O problema conhecido (gateway sobrevive ao MC fechado, segura 4920/4930 e faz o boot seguinte
não registrar os painéis) foi mapeado no macOS pela assinatura **`PPID == 1`**: o `launchd`
adota o órfão.

**O Windows não reparenta processo órfão.** O processo cujo pai morreu **mantém o PPID antigo**,
que simplesmente deixa de apontar para alguém vivo. Logo:

| SO | um gateway é órfão quando… |
|---|---|
| macOS | `ppid == 1` (adotado pelo `launchd`) |
| **Windows** | **seu `ppid` NÃO está entre os PIDs vivos** do instantâneo atual |

⚠️ E há um risco que o macOS não tem: o **Windows recicla PIDs**. Se o PID do MC morto for
reatribuído antes da checagem, o órfão parece ter pai vivo por um ciclo. Na prática isso vira
atraso (a checagem seguinte pega), não falha permanente — mas quem implementar um zelador deve
reconsultar em vez de decidir uma vez só.

**Como enumerar processos com PPID no Windows:** `tasklist` **não serve** (não traz PPID nem o
caminho do executável). `wmic` traz, mas está formalmente deprecado desde o Windows 10 21H1. O
sucessor é `Get-CimInstance Win32_Process` (~300 ms por chamada, medido) — aceitável para um
laço que dorme segundos entre checagens.

---

## 5. Drop e eventos no 25.6 — `confirmado` (nomes, por enumeração de símbolos)

### ⚠️⚠️ O drop NÃO é de mão única — e a correção mora em outro arquivo

Esta seção afirmava, como `confirmado`, que *"não existe caminho MC → painel"*. **Está
errado**: arrastar clipes e timelines da bin **para dentro** de um painel funciona, e foi
exercitado por um editor.

⭐ **Todo o assunto vive agora em [arrastar.md](arrastar.md)** — o mecanismo, o payload, as
seis espécies e como distinguir cada uma, os resultados negativos (bin, `.aaf`), as
armadilhas de implementação e o catálogo de MIMEs. Ele saiu daqui porque **não é
específico do Windows nem de uma versão**: é uma capacidade da plataforma, e tinha crescido
até ocupar metade deste arquivo.

Fica aqui só o que é deste eixo: **a leitura de símbolos que produziu a conclusão errada**,
porque a lição é sobre método de enumeração de binário.

### O que a enumeração de símbolos mostra, e o que ela não alcança

Os únicos símbolos de drop relativos a plugin no binário do 25.6:

```
DropFromPluginToBin
DropFromPluginToComposer
DropFromPluginToTimeline
```

Os três são reais e são de **saída** (painel → MC), com contrato nunca exercitado. Os
demais símbolos `Drag*` (`DragAndDrop`, `DragBegun`, `DragExportTransmitter`, …) são
maquinaria interna do editor.

⚠️ **E a ENTRADA não aparece aqui — porque não é um rpc.** O Qt entrega o arrasto à webview
como MIME, e quem implementa o resto é o Chromium. **Metade da superfície de um painel é a
do navegador, e essa metade não aparece em `strings` do executável hospedeiro.** Ausência
de símbolo prova ausência de *rpc*, não ausência de *capacidade*.

### Eventos presentes no 25.6

`ProjectOpened` · `BinOpened` · `BinClosed` · **`BinRowSelectionChanged`** · `MobAdded` ·
`MobDeleted` · `MobLoadedInViewer` · `DoCommandFinished`

⭐ `BinRowSelectionChanged` continua existindo e útil — só não é mais "o substituto porque
o drag não existe". Ele responde *"o que está marcado agora"*; o arrasto responde *"leve
estes"*. Comparação em [arrastar.md §7](arrastar.md).

⚠️ `pendente` — os eventos chegam pelo objeto `mcapi` do QWebChannel, que o MC injeta na
página. Um painel que **navegue para fora** do esquema `avpi://` (para `http://127.0.0.1`
servido pelo próprio app, o padrão que os parceiros oficiais revelaram) **pode perder a
ponte**. ⭐ Sabe-se agora que o **arrasto** sobrevive a essa navegação ([arrastar.md §2](arrastar.md));
a ponte de eventos é outro mecanismo e **segue não medida**.

## 6. ⭐ A coluna `Drive` da bin no Windows é `RÓTULO (LETRA:)` — `confirmado`

`GetMobInfo` devolve as colunas da bin como o editor as vê, entre elas `Drive`. **O valor real,
lido de uma bin no Windows:**

```
Drive = 'SSD (D:)'      ← NÃO é 'D', NÃO é 'SSD'
```

| SO | valor observado | montar o caminho |
|---|---|---|
| Windows | `SSD (D:)` | **pegue a letra do parêntese** → `D:\` |
| macOS | `SSD` (sem letra — não existe letra de unidade) | `/Volumes/SSD` ✅ o sistema **monta por nome** |

**Por que o bug só existe no Windows:** no macOS o rótulo **já é um caminho**. No Windows não há
caminho por rótulo, e um `f"{drive}:\\"` ingênuo produz `SSD (D:):\Avid MediaFiles` — que
apenas devolve `is_dir() == False`. **O sintoma é cruel:** o app reporta *"89 clipes não
encontrados no disco"* com a mídia inteira ali, intacta. Nada dá erro; a busca segue em frente e
a culpa parece ser do disco.

⚠️ **Duas lições de método deste achado, ambas caras:**

1. **A letra vem de graça no parêntese — use-a.** Traduzir o rótulo consultando os volumes
   montados também funciona, mas é trabalho a mais **e falha se dois volumes tiverem o mesmo
   nome**. Deixe a busca por rótulo como plano B.
2. ⚠️ **Não infira o formato da coluna pela TELA.** A primeira correção aqui foi escrita olhando
   um print onde a coluna estava truncada (`CICLO-MED…`), o que escondia o ` (D:)` — a correção
   compilou, passou nos testes que eu mesmo escrevi com o valor inferido, e **não consertou
   nada**. Leia o valor pela API antes de escrever o parser.

**Regex que cobre o formato real** (e não confunde um volume chamado `ARQUIVO (2024)`, porque
exige os dois-pontos):

```python
m = re.search(r"\(([A-Za-z]):\)\s*$", drive)      # 'SSD (D:)' -> 'D'
rotulo = re.sub(r"\s*\([A-Za-z]:\)\s*$", "", drive).strip()   # -> 'SSD'
```

**Plano B — tradução rótulo → letra**, sem dependência nova e sem subprocesso (`ctypes`, Windows):

```python
import ctypes
k32 = ctypes.windll.kernel32
anterior = k32.SetErrorMode(0x0001)          # SEM_FAILCRITICALERRORS — ver aviso abaixo
try:
    montadas = k32.GetLogicalDrives()        # bitmask: bit 0 = A:, bit 1 = B: …
    rotulo = ctypes.create_unicode_buffer(261)
    for i in range(26):
        if not montadas & (1 << i):
            continue
        raiz = f"{chr(ord('A') + i)}:\\"
        if k32.GetVolumeInformationW(ctypes.c_wchar_p(raiz), rotulo, 261,
                                     None, None, None, None, 0):
            print(rotulo.value, "->", raiz)   # 'SSD' -> 'D:\'
finally:
    k32.SetErrorMode(anterior)
```

⚠️ **`SetErrorMode(SEM_FAILCRITICALERRORS)` não é opcional:** sem ele, consultar um **leitor de
cartão vazio** abre o diálogo modal *"Insira um disco na unidade"* — e um processo de fundo
(sidecar, serviço) **congela esperando um clique numa janela que ninguém vê**.

Aceitar também a letra crua (`D`, `D:`) é barato e cobre volume **sem rótulo**.

---

## 6b. ⭐ Ler bins e mídia: três armadilhas que só o USO real revelou — `confirmado`

Estas apareceram depois que o painel já estava carregando e conversando — ou seja, **passaram por
toda a validação técnica** e só caíram no fluxo de trabalho de verdade. Valem para qualquer app
que leia bins do Media Composer.

### (a) A chave de bin faz viagem de IDA E VOLTA — normalize num lugar só

Um painel que mostre a árvore de bins para a pessoa escolher manda uma string e **recebe a mesma
string de volta**. Se as duas pontas montarem a chave por conta própria, o Windows separa as
duas: `caminho_relativo_da_bin` devolve `DIARIA 01\CAM A`, e quem normalizar para `/` só na ida
não encontra nada na volta.

**Sintoma:** a lista de bins abre, a pessoa marca, confirma — e a lista **reabre**, como se o
botão não funcionasse. Nada de erro.

⚠️ **Fica INTERMITENTE:** bins na **raiz** do projeto não têm separador e funcionam; só as que
estão em subpasta quebram. Isso faz o bug parecer aleatório e depender do projeto.

### (b) A mídia gerenciada é toda `.mxf` — inclusive o SOM

Classificar fonte pela **extensão** faz uma bin inteira de gravador de set virar "câmera". A
mídia do Avid não distingue por extensão: som direto vira OP-Atom `.mxf` igual a uma câmera.

**O discriminador certo é a ESSÊNCIA** — um clipe OP-Atom **sem track de vídeo** é som — e ela já
foi lida se você varreu com `ffprobe` (ver [protocolos/mxf](../../protocolos/mxf/README.md)).
Aproveite a mesma varredura; um segundo passe só para descobrir isso custa outro `ffprobe` por
arquivo.

### (c) ⚠️ `OpenBin` numa VARREDURA cobre a tela do editor

Ler o conteúdo de uma bin **fechada** exige `OpenBin` — e ele tem efeito **visível**: abre a bin
na tela. Numa varredura do projeto inteiro (que é o que acontece quando não se sabe quais bins
estão abertas — ver §3), isso deixa o Media Composer coberto de bins que o editor não pediu.

**A regra:** abra apenas quando a pessoa **nomeou** aquela bin. Em varredura, bin fechada é
**pulada** — e pular é a resposta correta, porque uma bin fechada não tem nada selecionado, que é
justamente o que a varredura procura.

⭐ Note como (c) é **consequência** de §3: ao degradar a falta de `GetListOfWindows`, a varredura
deixa de ser "só as abertas" e vira "todas" — e aí o `OpenBin` que antes era inofensivo passa a
ter custo visível. **Uma degradação pode ativar um efeito colateral que dormia.**

---

## 7. Mídia gerenciada no Windows — `confirmado`

O layout `<volume>/Avid MediaFiles/MXF/<n>/` (documentado em
[protocolos/mxf](../../protocolos/mxf/README.md)) vale igual no Windows, na **raiz do volume**:

```
D:\Avid MediaFiles\MXF\010020260629\   → 394 arquivos .mxf
```

Varredura medida (2026-08-15, SSD externo **exFAT** por USB, `ffprobe` por arquivo):

| medida | valor |
|---|---|
| tempo total da varredura | **24,1 s** |
| UMIDs distintos (= clipes) | **103** |
| arquivos por UMID | **3** (V + 2 canais de áudio) |

O agrupamento por `material_package_umid` bate exatamente com o descrito em
[protocolos/mxf §rota ffprobe](../../protocolos/mxf/README.md) — a rota é a mesma nos dois SOs.

⚠️ A mídia **local do sistema** fica fora da raiz do volume e continua sendo caso à parte:
`C:\Users\Public\Documents\Avid Media Composer\` no Windows.

---

## 7b. ⭐ Enumerar processos sem `wmic`, sem `tasklist` e sem PowerShell — `confirmado`

O zelador do gateway (§4) precisa de **PID + PPID + nome do executável**, e as três rotas
óbvias no Windows têm defeito: **`tasklist` não traz PPID**, **`wmic` está deprecado** desde o
Windows 10 21H1, e **`Get-CimInstance Win32_Process` custa ~300 ms** *e* um processo de
PowerShell por consulta — que num serviço de fundo ainda **pisca uma janela preta**.

A quarta rota resolve as três: **`CreateToolhelp32Snapshot` por `ctypes`**. Sem subprocesso,
sem janela, sem dependência nova, e devolve exatamente os três campos. Medido a partir do
serviço do De Lá Pra Cá (2026-08-15): **309 processos** numa varredura, instantânea.

⚠️ **Uma armadilha de `ctypes` que falha em silêncio:** sem declarar
`CreateToolhelp32Snapshot.restype = wintypes.HANDLE`, o ctypes trata o HANDLE de 64 bits como
`int` de 32 e o **trunca**. A comparação com `INVALID_HANDLE_VALUE` passa a ser sobre outro
número, e o `CloseHandle` fecha coisa nenhuma — vazamento de handle a cada consulta, sem erro.

```python
k32.CreateToolhelp32Snapshot.restype  = wintypes.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
```

Implementação completa (com o `PROCESSENTRY32W`) em `_DeLaPraCa`,
`plugins/media-composer/servico/plataforma.py`.

---

## 7c. ⭐ Instalar o `.avpi` no Windows: confirmado, e o ZIP tem regra própria — `confirmado`

Segunda confirmação independente de §1, agora **escrevendo**: um painel próprio
(`com.usuario.delapraca.mc.avpi`) foi empacotado e copiado para
`%PROGRAMDATA%\Avid\PanelSDKPlugins` **sem elevação**, ao lado do `avid-huddle.avpi` da Avid e
do `com.orbita.sync.avpi` (2026-08-15). Reforça — sem fechar — a pendência sobre a ACL.

⚠️ **O `.avpi` é o ZIP do CONTEÚDO da pasta do painel, com o `avid-manifest.json` na RAIZ** —
não a pasta zipada. Um manifesto um nível abaixo não é recusado com mensagem: o painel
**simplesmente não aparece no menu**, sem erro e sem log.

⚠️ E as ferramentas de zip de cada SO trazem defeito próprio: o `zip` do macOS arrasta
`.DS_Store` e os forks `._*` para dentro do pacote, e o **`Compress-Archive` do PowerShell
escreve entradas com contrabarra**. Montar as entradas à mão, sempre com `/`, resolve os dois
— e é por isso que o empacotador virou Python em vez de ganhar uma segunda cópia em shell.

---

## 7d. ⛔ A barra de menus do MC NÃO é lida por programa — nem Win32, nem UIA — `confirmado`

**Medido em 2026-08-17**, MC 25.6.0.58781 / Windows 11, com o editor **aberto** (projeto
carregado, painel de terceiro visível). A pergunta era prática: dá para **conferir uma
entrada de menu sem pedir a um humano que olhe**? Não dá, e as duas vias óbvias falham
por motivos diferentes:

| via | o que se tentou | resultado |
|---|---|---|
| **Win32** | `EnumWindows` no pid do MC → `GetMenu(hwnd)` em cada janela de topo | **87 janelas, ZERO com `HMENU`.** A barra não é menu nativo do Windows. |
| **UI Automation** | `FindAll(Descendants, ControlType.MenuBar)` na janela raiz | **0 resultados.** |

⭐ **O detalhe que explica:** a janela raiz do MC é `Qt656QWindowIcon` (**Qt 6.5.6**) — o
que faria esperar uma árvore de acessibilidade rica —, mas a árvore de controles tem
**exatamente três filhos**: dois `OglVideoWin` (os monitores) e um `Pane`. O MC desenha a
própria interface (`AvUIshell20.dll` + OpenGL) *dentro* da janela Qt e **não publica menu
nenhum** na árvore. Ver Qt e supor acessibilidade é a armadilha aqui.

⭐ **Estendido à janela INTEIRA em 2026-09-19** (MC 2025.6, `RawViewWalker` da raiz, duas
leituras seguidas — a primeira pergunta às vezes é o que liga a acessibilidade do Qt):
**17 nós** no processo todo, e o `Pane` `AvidMediaComposer` sem filho nenhum. O **painel
lateral de bins** também não existe para a UI Automation — era a esperança de ler a bin
selecionada no arrasto (ver `arrastar.md`, "os QUATRO canais medidos"). Sonda:
`_ASSIST ANTERIOR/tools/sonda_acessibilidade.py`.

**Consequência para quem for medir menu:** orce o ciclo humano — fechar o MC →
`reload.py` (matar o gateway órfão, §4) → reabrir → **olhar**. Não procure a API; ela não
existe nesta versão. E, como cada ciclo custa o tempo de outra pessoa, desenhe o
experimento para responder **mais de uma pergunta por reinicialização** — mas com **uma
variável por vez** por pergunta, senão o ciclo se perde em confusão de causas.

⚠️ Corolário para o gateway: `avid-api-gateway.exe` **não ajuda** aqui. As structs Go dele
(`avid-api-gateway/models.Manifest`) só **validam e servem** o manifesto — `MenuName` nem
tem tag `validate` —, e o `loader` expõe `GetPlugin`/`GetManifest`/`GetAllPlugins`. Quem
monta o menu é o executável do MC. Enquadrar o menu como "coisa do gateway" custa uma
sessão de `strings` que não pode dar certo.

**Sonda reutilizável:** `_DeLaPraCa/.dev/spike_menu_mc.py` (Win32) — roda de novo quando a
versão do MC mudar, e distingue "não achei" de "não existe".

---

## 8. O que ficou `pendente` neste eixo

- **Ponte de EVENTOS após navegar para `http://`** (§5) — decide se `BinRowSelectionChanged` é
  utilizável por um painel servido pelo app. ⭐ **Metade respondida:** o **arrasto** sobrevive
  a essa navegação ([arrastar.md](arrastar.md)); a ponte de eventos é outro mecanismo e segue
  não medida.
- **`DropFromPluginToBin` na prática** — o contrato existe; entregar a sequência sincronizada
  direto na bin (em vez de o usuário importar o `.avb`) depende dele. Nunca exercitado.
- **Instalação sem elevação** (§1) — funcionou aqui; não se sabe se a ACL de `%PROGRAMDATA%`
  garante isso em toda instalação.
- **Em qual versão o menu `Extensions` apareceu** (§2) — sabe-se que 25.6 não tem e 25.12 tem.

---

## Fontes

**Segunda passada, 2026-08-15 (mesma máquina, outro app):** §7b e §7c saíram de portar o
**De Lá Pra Cá** — o plugin de relink que roda *dentro* do MC — do macOS para o Windows.
Diferença de método que vale citar: ali o Órbita **lia** o Media Composer de fora; aqui o
serviço **instalou** o próprio `.avpi`, subiu, serviu a UI do painel e passou uma suíte de
regressão de 85 casos no Windows. Foi essa passada que exercitou a escrita na
`%PROGRAMDATA%` e a enumeração de processos sem PowerShell. Ver
[transversal/desenvolvimento-cross-platform](../../transversal/desenvolvimento-cross-platform.md)
§8 e §9 para o que não é específico do Avid.

Instalação real do **Media Composer 25.6.0.58781** em **Windows 11 23H2**, durante a validação da
integração do Órbita, **2026-08-15**. Métodos: leitura direta do disco, `strings -a` sobre
`AvidMediaComposer.exe` e `avid-api-gateway.exe`, `Get-CimInstance Win32_Process`,
`Get-NetTCPConnection`, `GetVolumeInformationW` via `ctypes`, chamadas gRPC reais contra
`[::1]:9100` com o editor aberto, e o painel do Órbita carregado e visível no menu Tools.
Controle: `avid-huddle.avpi` (painel da própria Avid) presente na mesma pasta.
Detalhes por bloco em [fontes.md](fontes.md).

---

## 🆕 Para automação (laboratório de mídia, 2026-10-11) — o que o autor ensinou e o que o MC registra

- **A taxa é do PROJETO**, não da sequência (no Premiere e no Resolve é da timeline): o laboratório precisa de um projeto
  do MC por taxa testada. Copiar uma bin com sequência de outra taxa para o projeto faz o MC PERGUNTAR se converte a
  sequência para a taxa do projeto (um diálogo modal). ⏳ `pendente` (dúvida antiga do autor): **a conversão mantém os
  pontos de corte ou gera diferenças?** — vira experimento do laboratório (mídia sintética com o quadro e o TC na imagem,
  sequência na taxa A, aberta no projeto B, comparar corte a corte).
- **Efeito pela Effect Palette sem arrastar:** com o clipe selecionado na timeline, um DUPLO-CLIQUE no efeito da Effect
  Palette aplica o efeito (autor; o arrasto automatizado não funcionou numa tentativa antiga). O autor já fez macros de
  efeito só com teclas (AutoHotkey) — caminho por teclado `pendente` de medir.
  ✅ **Medido e automatizado (2026-10-11, MC 25.6, laboratório `lab/bancadas/avid_efeitos.py`):** os 19 efeitos da
  categoria Image aplicados um por clipe, sem o autor, em 127 s. O laço (ensinado pelo autor, com portões que olham
  a tela ou a API antes de cada passo):
  1. **Ctrl+0** (foco na timeline) → a partir do 2º clipe **Go to Next Event** (DoCommand 6240; o 1º NÃO leva) →
     [o TC da agulha = início do clipe? — `GetViewerMobs` traz `current_timecode` da Record];
  2. **G** (limpa o IN/OUT) + **um clique na faixa CINZA vazia** da timeline (tira a seleção do segmento) → [o TC
     não mudou? o clique é na coluna da agulha] → **T** (Mark Clip) → [o trecho marcado começa na agulha?];
  3. **Ctrl+8** (foco na Effect Palette) → **duplo-clique** no efeito.
  ⛔ O T só marca o clipe sob a agulha quando NÃO há IN/OUT e NENHUM segmento selecionado — e o duplo-clique na
  paleta deixa o segmento SELECIONADO (o T seguinte remarcava a seleção: todos os efeitos caíam no 1º clipe).
  O autor achava que era só tecla: era o clique do mouse dele que soltava a seleção.
  ⛔ UM efeito por clipe: outro duplo-clique SUBSTITUI. Para empilhar, **Alt** (Option) no duplo-clique ou arrasto.
  ⚠️ `DoCommand` age na janela que tem o FOCO (com a paleta em foco o Go to Start não fazia nada) e é ASSÍNCRONO:
  volta antes de o MC agir (um T logo depois agia antes do Next Event), e um segundo em seguida dá "Can't start more
  than one command on time." (ErrorType 73). `Deselect-All` (1039) tira também a seleção das TRILHAS.
  `LoadMobsIntoViewer` de uma sequência já carregada responde "Some mobs was skipped.".
  ⭐ A bin se auto-descreve: o efeito guarda `_EFFECT_PLUGIN_NAME` (nome da paleta) e `_EFFECT_PLUGIN_CLASS`
  (categoria) — mapa em `protocolos/avb/dados/efeitos-paleta-mc25.json`.
  ⛔ O **Stabilize rastreia ao ser aplicado** (autor): a janela "Tracking" é o trabalho do efeito — esperar ela
  sumir sozinha; Esc nela deixa o efeito sem o rastreamento.
- **O Effect Editor e o MODO DE EFEITO** (autor + bancada, 2026-10-11, MC 25.6): com o clipe marcado (T), `DoCommand`
  1939 abre o Effect Editor numa janela SOLTA (no alto, sobre a paleta) e o MC entra no modo de efeito: o monitor da
  Record ganha a moldura de manipulação, a barra azul sob ele passa a representar SÓ o segmento selecionado, a barra
  da timeline troca de botões e a paleta pula para "All". ⛔ Esc na janela NÃO sai do modo; **Ctrl+W com o Effect
  Editor em foco** fecha a janela e sai. ⚠️ Arrastar a imagem no monitor da Record nesse modo cria KEYFRAME automático na
  agulha (pega editor desatento) — a bancada nunca mexe no monitor, só no painel.
  ⛔ **Digitar um valor:** há uma área invisível que vai até o número à direita de cada controle deslizante — clicar no
  NÚMERO leva o controle ao MÁXIMO. O certo é clicar na BOLINHA do controle, digitar o valor e Enter (sem eco na tela).
  O controle em forma de DIAL (roda) aceita o mesmo: clique para selecionar, número, Enter.
  A seta à direita de cada valor abre o GRÁFICO de keyframes — que só aparece com a janela LARGA o bastante (estreita,
  a seta não mostra nada). Grupos abrem pela seta à esquerda; abrir de baixo para cima evita que as linhas mudem de lugar.
  🆕 (bancada, 2026-10-11 noite, MC 25.6 Windows — `confirmado` em 6 efeitos da categoria Image, conferido na bin):
  - **A ▶ tem um desenho fixo — achá-la pelo MOLDE, não pela coluna.** No editor normal: 9 linhas, borda esquerda
    RETA, largura 2-4-6-7-8-7-6-4-2 (cinza 107–141). No editor de PINTURA (Blur, Mosaic, Paint, Scratch Removal, Spot
    Color — outro editor, mais antigo): APAGADA (cinza 110), 11–12 linhas, 1-2-3-5-5-6-5-3-2-2-1 — a suavização sai
    torta. Molde: borda esquerda reta (±1), pontas ≤ 3, sobe até um pico no terço do meio e desce, simetria ±2. Nenhuma
    letra passou (30 fotos, inclusive as 9 páginas do Color Correction). Os subgrupos ficam até o nível 5 (x≈113: o
    "Clip" do Master do Color Correction); os controles deslizantes começam em x≈159.
  - **O editor de PINTURA ROLA SOZINHO ao abrir um grupo** — os grupos de cima saem da vista. Abrir só descendo deixa
    grupos fechados (Spot Color: Acceleration/Tracking/Luma Range). Certo: passadas do TOPO ao fim até uma passada não
    abrir nada.
  - **Rolar pela FAIXA da barra de rolagem** (clique acima/abaixo do polegar = uma página), **nunca pela roda do
    mouse**: sobre um controle deslizante do Qt a roda muda o VALOR do parâmetro. Fim da lista = a foto não muda.
  - Color Correction aberto inteiro = 9 páginas de 1000 px: Base HSL (Controls Master/Highlights/Midtones/Shadows +
    Hue Offsets), Base Levels, Base Curves, Base Secondary (6 vetores + 6 elipses com hue/sat de fábrica), Shapes,
    Layers. Catálogo: `laboratorio-de-midia/lab/bancadas/avid/effect_editor/catalogo.json`.
  - Abrir grupos e rolar NÃO grava nada na bin (os 5 efeitos de pintura seguiram com `param_list` vazio depois de
    dezenas de cliques).
  - ✅ **Catálogo COMPLETO** (2026-10-12): Image + as outras 25 categorias = 221 efeitos no `catalogo.json`. Os 201
    novos têm só **67 painéis distintos** (md5 da foto abaixo do título; os 59 wipes de borda dividem UM). Padrões que
    a bin NÃO guarda (só grava o que saiu do padrão) e que a tradução precisa saber: **Xpress 3D = 3D Warp com UM
    grupo ligado** (o do preset — 3D PIP: Scaling 50; 3D Ball/Page Fold/Slats: Shape); **Film masks = Scaling Hgt**
    80/72/75/53 (1.66/1.85/16:9/Anamórfico); PIP com Fixed Border ligado; a grade dos keys e do Pan and Scan de
    fábrica é **NTSC SD** (720×486 / 720×243) mesmo em projeto 1080; o Crop do S3D vai de 0 a 100 (o do 3D Warp,
    ±999); RGBKeyer chaveia AZUL (H 171), SpectraMatte (91,119,192); PlasmaWipe Borders/Center… Soft 32, molduras
    Metal/Stone Lum 63 + Width 63; Particle Blast/Wind e Shear com Swap ligado. ⚠️ Timecode Burn-In: na largura de
    1000 px os números dos subgrupos fundos saem CORTADOS — ler pela bin.
- ⚠️ **O MC 25.6 RESERVA ~11,4 GB de memória PRIVADA ao abrir** (2026-10-11, Windows 11, 16 GB de RAM): 11,8 GB depois
  de 1h30 de bancada e 11,3 GB um minuto depois de reaberto — não é inchaço do uso, reabrir não solta. Residente fica
  0,6–0,9 GB, o resto vai para a paginação (comprometido total 30,6 GB). Com o Windows ligado há 27 h sobraram 0,2–0,3 GB
  disponíveis — a mesma condição em que a 2ª rodada de efeitos caiu. Recém-reiniciado e sem o MC: 5,2 GB disponíveis,
  14,4 GB comprometidos. CORRIGE (mesmo dia): o pool não paginado de 1,3 GB NÃO era vazamento — recém-ligada a máquina
  já tem 1,0 GB (base dela). ⇒ bancada longa do MC: Windows recém-reiniciado e um freio por memória disponível
  (`avid_efeitos.MEMORIA_MINIMA_MB`). O RAMMap (que esvazia o CACHE de arquivos) não ajuda aqui: o cache era 0,7 GB.
  `pendente`: qual configuração do MC dita a reserva (cache de vídeo/"Memory" nas Settings?) e o número no macOS.
- ⭐ **`C:\Users\Public\Documents\Avid Media Composer\Avid FatalErrorReports\EVENTLOG.LOG`** (texto, uma linha por evento,
  `AAAAMMDDhhmmss Tipo Mensagem`, com NUL entre linhas): o MC grava aí o texto das janelas de erro (`FatalExcpt Too few
  marks to make this edit.`, `FatalExcpt Exception: The sequence or one of its source elements is too long to be
  played.`), as asserções (`FatalAbort Assertion failed: CompIsFiller(last) || TT_SOUND_MASTER==GetType()`;
  `normalCaching || smallCaching` em `CoreWinFileLocator.c`), as quedas (`ACCESS_VIOLATION` + `Dump_*`) e o ciclo de vida
  (`Startup rel.MC2025.6_R58781`, `Ready Application ready for user`, `Exiting`/`Shutdown`). ⇒ o vigia de diálogos lê a
  cauda desse log para saber o TEXTO da janela que apareceu (a janela Qt não expõe), e "ready for user" diz que o MC
  terminou de abrir. MC 25.6, Windows 11 (lido em 2026-10-11). Mensagens já vistas pela família (handoffs/banco):
  `PMM_INSUFFICIENT_MEDIA`, "Media Offline", "Link Media", "File Import Failure", "Unable to Rename Timeline".
- ⛔ **A janela do LAYOUT DE TECLADO** (autor, 2026-10-11): aparece sempre que o projeto abre ou o layout de teclas do
  Windows muda; o "não mostrar de novo" NÃO funciona (ela volta sempre). O vigia de diálogos tem de conhecê-la e fechá-la.
- Mídia na `Avid MediaFiles`: ver `protocolos/msm/README.md` (pasta numérica, a `1` é do MC, apagar `.mdb`/`.pmr` depois
  de mudar uma pasta, varredura ao ganhar o foco).
- ✅ **Projeto criado SEM o autor (2026-10-11, MC 25.6):** a abertura mostra a janela Qt "Select Project" (dona: a
  principal) logo depois de "Application ready for user" no EVENTLOG. Aba "New Project" → Location pelo botão de pasta (abre o
  "Select a Folder" padrão do Windows, `#32770`, campo "Folder:" em foco: digitar o caminho + Enter) → nome (clique + Ctrl+A +
  texto) → Create. Projetos do laboratório em `Documents\Avid Projects\DLPC LAB\`. ⚠️ Com a escala de tela de 125 % o
  processo precisa ser ciente de DPI (`SetProcessDpiAwareness(2)`) — senão o clique cai fora (o PrintWindow vem em pixels reais).
- ✅ ⭐⭐ **OP-Atom feito FORA do MC entra na bin ONLINE, sem cópia: pasta numérica + AAF de masters + `ImportFile`**
  (MC **2024.6** Perpetual, Windows 11, 2026-10-31; Ciclo Assist, F3 do plano `2026-10-31-o-assist-operador.md`).
  Os 22 OP-Atom que o Resolve Studio renderizou (4 clipes: vídeo DNxHD 36 + 2/4/4/8 canais, ver
  `../resolve-scripting/api-scripting.md`) copiados para `D:\Avid MediaFiles\MXF\202610310` → o MC criou
  `msmMMOB.mdb` + `msmFMID.pmr` no **1º foco (~8 s)** → AAF montado pelo **pyaaf2 `content.link_external_mxf(arq)`**
  para cada `.mxf` (4 `MasterMob` com o MobID = o `material_package_umid`, cada um com V + os seus canais) →
  `ImportFile(file_path=<aaf>, import_settings_name="Untitled", destination_bin=<.avb absoluto>)` = `Completed` →
  os 4 masters na bin com `Drive: SSD (D:)`, `Tracks` `V1 A1-2`/`A1-4`/`A1-4`/`A1-8`, `Start 01:00:00:00`,
  `Video: DNxHD LB (HD1080p)` — e **nenhum arquivo novo** em outra pasta (o import não transcodou).
  ⚠️ `Tape` saiu **"Mob"** (o nome do `SourceMob` de fita que o pyaaf2 cria) — dar o nome do rolo antes, `pendente`.
  ✅ (31/10, noite) o B01 TOCA no Source: a imagem certa, a 01:00:00:00.
- ⛔⛔ **…mas só se o MC JÁ TIVER INDEXADO o MXF quando o `ImportFile` roda. Senão o mob nasce envenenado e DERRUBA o MC
  quando a mídia aparece** (MC **2024.6**, Win11, 2026-10-31, `confirmado` — uma variável por vez, piloto + autor).
  O B06 (`00090250.mxf`, Resolve sem preset) foi COPIADO às 15:37 para a `202610310`, que já tinha `.mdb` (15:35).
  ⇒ a data da PASTA não mudou, o MC não a reescaneou (o `.mdb` não ganhou o B06: nem o nome), e o `ImportFile`
  montou o mob de arquivo com o descritor do AAF: **`data_offset = 0`, `frame_index_offset = 0`, locator sem volume**
  (o do B01, indexado antes, tem `393241` / `47186094` / `SSD (D:)`).
  - Offline (índice velho): **MEDIA OFFLINE**, nada cai.
  - Índice refeito (`.mdb`/`.pmr` tirados da pasta): o Source mostra **`CORE_CONSISTENCY_CHECK_FAILURE`** e o
    EVENTLOG grava `FatalAbort Assertion failed: FALSE … CompressionMgr\CompressionManager.c, line 11276`; ao tocar ou
    abrir uma timeline com ele, o MC cai. **Sem sequência nenhuma aberta, e sem os MXF de áudio** — é o vídeo.
  - O MXF NÃO é o culpado: campo a campo (descritores, pacotes, índice, cabeçalho DNxHD CID 1253) igual ao do B01,
    que toca. Nem o áudio 16 bits, nem o nome `00090250`, nem o TC 01:00:10:00.
  - ✅ **Conserto no MC (autor):** botão direito no master → **Modify → Unlink Media**, depois **Relink → Managed
    Media**: o MC reescreve o mob pelo MXF (offsets, locator, e ainda cor 16/235/225, alinhamento 8192) e toca.
  - ⇒ **Antes do import:** MXF mais novo que o `msmMMOB.mdb` da pasta = não indexado → pasta numérica NOVA + foco.
    **Depois:** mob de imagem com `data_offset = 0` = recusar. As duas travas: `_CICLO ASSIST/spikes/opatom_para_mc.py`
    (`nao_indexados`, `mobs_sem_offset`), provadas nos dois sentidos.
  - ⚠️ As cores do B01 (0/255, do AAF) NÃO derrubam: não é preciso consertá-las.
- ✅ **`ImportFile` põe mídia GERENCIADA na `MXF\1` sem diálogo** (`import_settings_name="Untitled"`,
  `destination_video_drive="SSD (D:)"`, `destination_bin` = caminho absoluto da bin): responde "Completed" em 0,3 s e o
  import termina DEPOIS (o master clip aparece na bin e os `.mxf` na `MXF\1` alguns segundos mais tarde) — esperar pela bin, não
  pela resposta. (2026-10-11) O B02 apareceu em `MXF\1-ocruz_ignorar\` porque o AUTOR moveu a `MXF\1` inteira para
  liberar a pasta (o import tinha ido para a `MXF\1`, como esperado). `GetListOfImportSettings`/`GetListOfLinkSettings` = ["Untitled"]; export: "MP4-2kbps", "aaf", "dnxlb", "mp4".
  `LoadSetting(unique_id, xml_setting)` cria configuração por XML — ⭐ **e instala preset de export com o MC ABERTO desde que o envelope
  traga `<AvClass id="SETG"/>`** (sem ele: "No settings objects"). Medido 2026-10-11: o "DLPC_LAB_DNXLB" (MXF DNxHR LB) entrou na
  hora e o `ExportFile` exportou 240/240 quadros com o TC do original (ver `dados/mcapi-grpc.json` → `LoadSetting_recusa_preset_de_export`).
  ⚠️ (2026-10-11) A TAXA vive no preset: o feito a 23,976 recusa uma sequência a 24 ("Edit rate of the sequence does not
  match the edit rate in the shim"). Ela está em `descriptor.samplerate` (JSON dos descritores, ex. `24000//1001`),
  `iSeqFrameRate` (a NOMINAL: 24 para 23,976) e `ATN_ES_SEQ_FRAME_RATE` (BobData = double LE em hexa). Trocar os três
  gera o preset de outra taxa: 24, 25 e 29,97 exportaram 172/172. O projeto 1080i/59,94 usa o de 29,97.
  ⚠️ `ExportFile` com o destino JÁ existente não sobrescreve: grava `<nome>1.mxf` (ex. `LAB_CORTES_011.mxf`).
  ⚠️ `ImportFile` de um ProRes 29,97p num projeto 1080i/59,94 TRANSCODIFICA (DNxHD entrelaçado na gerenciada);
  nos projetos progressivos o ProRes entra como está (ProRes OP-Atom).
- ✅ **Ciclo completo sem o autor (2026-10-11, MC 25.6, 2 monitores):** `DoCommand(1010 Exit)` → "Leave the application?"
  [Leave] → fechado em 11 s; abrir → tela de abertura (Qt com dono, "Initializing…") → "Select Project" (lembra o perfil e a
  Location da última vez; digitar o nome do projeto na lista seleciona a linha) → Open → "Reading "<perfil> Settings""
  (progresso) → janelas do layout de teclado → aberto em 51 s. ⭐ Trazer a Select Project para a frente dá o foco ao MC e
  SOLTA a janela do layout de teclado: um clique em Open nessa hora se perde (o projeto não abre e nada acusa) — frente →
  esperar → resolver os diálogos → só então clicar. As janelas do layout de teclado têm 3 textos ("Be advised, that by
  changing the Keyboard Input Locale…", "Your active Keyboard Setting will now be changed…", "It is recommended that you
  activate the Keyboard Setting corresponding to the new Keyboard Input Locale…") — todas [OK] [Don't warn me again], e o
  segundo botão não segura. "New monitor configuration" (duplicar workspaces? [Yes] [No]) é POR PERFIL. ⚠️ Com a escala de
  tela mudando entre monitores, o mesmo diálogo tem outro tamanho em pixels: reconhecer pela foto normalizada e clicar por
  fração. Catálogo com as fotos: `laboratorio-de-midia/lab/bancadas/avid/dialogos/`.
  ⛔ **Queda com a tela bloqueada (2026-10-12, 08:28, MC 25.6):** ``FatalAbort Class AObject should have implemented
  this method!`` (AObject.c:158) no meio de um ``CloseBin`` pedido pela bancada; pilha em ``APane::LocalToGlobalRect``
  (DESENHO de painel) e o ``LockApp.exe`` (tela de bloqueio do Windows) na lista de processos do relatório. O mesmo
  CloseBin com a mesma sequência carregada, refeito com a tela desbloqueada, salvou normal → ``hipótese``: o MC cai
  ao redesenhar a timeline com a sessão bloqueada; não é o conteúdo da bin. Depois da queda o MC volta na Select
  Project e com a janela principal SOLTA (5, 19, 1925, 1039): coordenadas medidas com ela maximizada erram (o 2º
  Collapse da v8 leu a seleção no lugar errado). Maximizada pelo Windows ela fica em (−9, −9, 1929, 1029): a TELA é a
  mesma, mas a FOTO da janela (PrintWindow) sai deslocada 9 px — descontar a posição da janela.
  ⛔ CORRIGE (2026-10-12, à tarde): quem soltava a janela era o PRÓPRIO PILOTO — `maos.frente()` fazia
  `ShowWindow(SW_RESTORE)`, que tira uma janela MAXIMIZADA do maximizado (o MC ia de (−9, −9) para (5, 19) a cada
  frente, e o clique na categoria da Effect Palette caiu uma linha acima: Squeeze em vez de Timewarp; o Record mostrou
  "std::exception"). Corrigido no piloto: SW_RESTORE só se a janela estiver minimizada (`IsIconic`), senão SW_SHOW.
  A queda pode ter coincidido — a janela solta depois dela era, muito provavelmente, o frente da reabertura.
  ⛔ **O efeito da paleta vai no CLIPE SELECIONADO** (o autor, 2026-10-12), não no trecho IN/OUT: com IN/OUT pela API
  e o duplo-clique, nem um clipe comum recebeu o Timewarp — sem aviso. O laço da bancada (G + clique na faixa vazia →
  T) funciona; selecionar o clipe com um clique nele (a ferramenta de segmento ativa) também. ⚠️ Depois de um Collapse
  o segmento colapsado fica SELECIONADO: o efeito seguinte iria para ele.
  ⛔ **O GESTO no Motion Effect Editor** (o autor, 2026-10-12; PADRÃO para todo editor de atributos do MC, o Effect
  Editor também: a agulha em cima do clipe cujo atributo vai mudar): o editor mostra o efeito do clipe SOB A AGULHA — a
  agulha sobre o clipe E o clipe selecionado (clique nele na timeline); para mudar o tipo de curva (☰ → Shelf/Linear/
  Spline/Bezier) o KEYFRAME tem de estar selecionado no painel (clique nele: fica rosa e o valor aparece no campo) —
  sem isso o menu marca o padrão e a escolha não tem onde valer. Sem clipe sob a agulha, o editor fica cinza.
  ⚠️ No 2º monitor o editor ficou ATRÁS da janela do terminal (o Claude Code mora lá): cliques "no editor" caíram no
  terminal. E a ESCALA difere entre os monitores (principal 125 %, 2º 100 %): a mesma janela tem 1007 × 379 px reais
  lá e 1259 × 474 aqui — medir as posições na foto do monitor onde a janela está. Para operar o editor: no principal,
  sobre os monitores Source/Record (265, 40) — a paleta e a timeline ficam livres.
  ⚠️ O Motion Effect Editor SOLTO ficou por cima da lista de efeitos da paleta: o duplo-clique no preset caía nele.
  As janelas de ferramenta vão para o 2º monitor junto com as bins (`afastar_bins`).
  ⭐ **O Motion Effect Editor (6296), anatomia** (o autor, 2026-10-12, com capturas): os dois ícones grandes abaixo de
  "Timewarp" são BOTÕES que abrem/fecham os painéis — o **homem correndo = gráfico de VELOCIDADE**, a **curva = gráfico
  de POSIÇÃO**; os dois podem estar visíveis lado a lado. **"Edit Graph" (Speed / Position) escolhe qual é EDITÁVEL**:
  só o painel ativo mostra o keyframe ROSA, o menu ☰ (na barra de baixo DELE) e os dois campos ao lado (o valor do
  keyframe — % no Speed, TC da fonte no Position — e o TC da agulha). O campo **Anchor** só aparece com Speed. O menu ☰:
  Add / Delete Keyframe, Select All Keyframes, Align Keyframe, Slip Keyframes, a interpolação (**Shelf / Linear /
  Spline / Bezier**; padrão Spline), **Fixed / Elastic Keyframes** (padrão Fixed) e Reset Graph View. No Position, o
  canto de baixo do gráfico mostra o TC da fonte no IN (01:00:59:15). `pendente`: qual campo da bin guarda Shelf/
  Linear/Spline/Bezier (o pp `code 9`?) e Fixed/Elastic.
  ⚠️ O "Motion Effect Editor" e o "Effect Editor" são janelas de ferramenta, NÃO modais: estão no `nao_modais` do
  perfil do MC (antes o cão de guarda parava diante deles como diálogo desconhecido).
  ⚠️ O `ExportFile` de efeito pesado (rampa) deixa o arquivo PARADO em 8 MB por dezenas de segundos: o fim do export é
  a janela de progresso "Exporting Files…" (título "AvidMediaComposer") sumir, não o tamanho parar. Ctrl+. cancela e
  APAGA o parcial; depois vem "AMA Export failed. Check console window…" [OK].
  ⛔ **O cão de guarda tem de vigiar TUDO o que espera o MC** (autor: "o cão de guarda não deveria olhar para o que
  está acontecendo?" — uma montagem fora dele esperou 2 min uma bin que não existia mais): no piloto,
  ``vigia.com_prazo(saude=apps.saude_avid)`` trata o MC sem projeto (título só "Avid Media Composer") como Travado em
  ~3 s; na bancada, o ``avid.guardado`` passa isso sempre e as operações longas rodam dentro dele.
  ⚠️ **Seleção de trilha pela API (2026-10-12, MC 25.6, B21):** os DoCommand ``V1`` (6231), ``V2`` (6230), ``V3``
  (6176)… **INVERTEM** a seleção da trilha (não ligam), e o ``Deselect All`` (1039) **não** mexe nas trilhas. O
  Collapse (6251), o Mark Clip e o efeito pela paleta agem nas trilhas SELECIONADAS — com a seleção errada o 1º
  Collapse do B21 pegou V1 + V3. Certo: ler o estado pela foto (o quadrinho do nome da trilha fica azul
  ``(48, 89, 122)``; o azul da coluna ao lado é o MONITOR da trilha), inverter só o que difere e **esperar ~1 s antes
  de reler** (a tela demora a mostrar; reler cedo inverteu de novo). Código: ``lab/bancadas/avid_collapse.selecionar``.
  ⚠️ **Não é só na abertura** (2026-10-12, MC 25.6): com o MC JÁ aberto, a terceira ("It is recommended…") surgiu sozinha
  no meio de uma rodada da bancada, quando o idioma de digitação do Windows passou para "ENG INTL" (causa da troca não
  apurada). Enquanto ela está aberta, TODA chamada da API devolve `ErrorType 73 "Media composer is Busy."` (DoCommand,
  LoadMobsIntoViewer) — a rodada falhou os 4 clipes da categoria. [OK] liberou na hora. Bancada longa: tratar Busy em
  série como diálogo aberto (fotografar a tela, resolver), nunca como falha do efeito.
- ✅ **Projetos criados sem o autor (2026-10-11):** "DLPC LAB 23.976 / 24 / 25 / 29.97p / 59.94i" em
  `Documents\Avid Projects\DLPC LAB\`. O campo Format da New Project é um MENU em níveis (Ultra HD, 2K, 4K, 8K, 16K, HD 1080,
  HD 720, NTSC, PAL, Custom; HD 1080 ▸ 1080i/50, 1080i/59.94, ─, 1080p/23.976, 24, 25, 29.97, 30, 50, 59.94, 60, 100,
  119.88, 120, ─, TR 1440/1280…). Digitar não escolhe; clicar no item por posição errou 2 de 4 (o submenu muda de lugar);
  o TECLADO acerta sempre: ↓×6, →, ↓×n, Enter. `GetOpenProjectInfo` devolve o `type` certo do projeto aberto — use-o para
  conferir. ⚠️ O projeto **1080i/59.94** mostra Frame Rate **29.97** na lista (o MC conta quadros, não campos). Fechar o
  projeto e voltar à Select Project: `DoCommand(1172 Close Project)`. A janela de progresso fotografada cedo demais sai PRETA
  (não confundir com diálogo desconhecido).
- ⭐ **Bin COPIADA para a pasta do projeto ABERTO não entra no projeto** — `confirmado` (2026-10-29, MC 24.6, Windows,
  projeto `ASSIST TESTE 29-10`). No 24.6 o **Create** da New Project já ABRE o projeto (não volta à lista). Copiadas
  `D02\CAM A.avb` e `D02\SOM DIRETO.avb` para dentro dele: o painel de bins não as mostrou, `OpenBin("D02/CAM A.avb")`
  devolveu `Completed` e abriu a bin em ABA, e mesmo assim `GetBins` (a árvore que o Órbita lê para achar "a pasta D02")
  continuou só com a bin do projeto por ~3 min, conferido a cada 20 s. **File ▸ Close Project + Open** registrou na
  hora (`GetBins` com as duas). ⇒ Montar projeto de teste: copiar as bins ANTES de abrir, ou fechar e reabrir.
  (O ensaio de 22/10 viu uma pasta gravada pelo Órbita aparecer "alguns minutos depois" — o atraso existe, mas não é
  prazo em que se possa confiar.)

## 🆕 9. O painel SOLTO do MC 25.6 e a tela parada (2026-10-13, MC 25.6, Windows 11, notebook 1920×1080 a 125 %)

Medido pilotando o De Lá Pra Cá (painel web do `.avpi`, flutuante, aberto pelo menu Tools), sem o autor, por foto da
tela a cada ~30 ms depois do clique (`ImageGrab` da área do cartão; mudança = média da diferença > 3).

- ⛔ **O quadro novo às vezes NÃO CHEGA à tela** — `confirmado`. O DOM está certo e a página está viva
  (`document.visibilityState` "visible", `hasFocus()` true, `requestAnimationFrame` em 7 ms — relatado ao serviço pela
  própria página), mas a janela do MC segue mostrando o quadro velho por 6 s ou mais. Passar o mouse ou clicar num
  vazio do painel NÃO resolve; trocar de aba (mudança grande de layout) resolve. Frequência: **5 de 17** "Carregar
  sequência" logo depois de recarregar o painel e abrir a bin (o editor via o botão "não fazer nada"). O que refutaria:
  a tela mudar sozinha depois de alguns segundos — não mudou em 6 s em nenhum dos 5.
- ✅ **Remédio** (`painel.js`, só no MC): um `MutationObserver` no `body` que, a cada mudança, dá um quadro com a página
  INTEIRA marcada como alterada (`documentElement.style.opacity` 0.999 → "" em dois `requestAnimationFrame`).
  Depois: **24 de 24** chegaram à tela (~210 ms; uma em 3 s). Controle sem o remédio, mesma sessão: 4 de 12 presos.
- **A "lentidão de clique" que o autor sente** — `confirmado` em parte. Latência normal do painel solto, do clique à
  tela: **~210 ms** numa mudança síncrona (×), **~360 ms** com uma ida ao serviço e ao MC (`/mc/record`, que leva
  100–150 ms). Clicando sempre DENTRO do painel: **0 de 29** acima de 1 s. Clicando logo depois de a janela PRINCIPAL do
  MC ganhar o foco (o gesto real: editor na timeline → painel): **3 de 17** entre 1 e 3,8 s — e só nas ações que
  esperam resposta. A API do MC NÃO fica lenta com a troca de foco (`/mc/record` 87–149 ms nos dois casos, 15 + 15
  medidas): o atraso é do lado do painel (o retorno da página espera o laço do MC, ocupado com o que o foco dispara —
  `hipotese`). Encaixado: medido a seguir.
- ✅ **Encaixado × solto — medido 2026-10-13** (o autor criou dois workspaces no MC: "DLPC", painel encaixado à
  direita; "automacao", painel solto por cima; troca pelo menu ▼ do canto superior direito). Ciclo "Carregar a
  sequência aberta" ⇄ ×, 24 ciclos (48 cliques) de cada, com o GESTO REAL antes de cada clique (um clique numa área
  vazia da lista de bins, 0,3 s antes): **encaixado 3 de 48 acima de 0,7 s (758, 996, 1003 ms); solto 5 de 48 (765,
  792, 932, 973, 991 ms)**; nenhum dos dois acima de 1,1 s. Clicando só no painel (24 cliques cada): encaixado 0
  acima de 0,5 s; solto 2 (633, 779 ms). O normal nos dois: ~210 ms (mudança local) e ~370 ms (com ida ao MC).
  ⇒ Encaixar ajuda POUCO; o ~1 s ocasional depois de clicar em outro lugar do MC acontece nos dois. Os travamentos
  de 3,5 s do dia 12 (ativar a janela principal pelo sistema logo antes do clique) não se repetiram neste gesto —
  `confirmado` com o remédio do repintar já no painel.
- O painel solto é uma **janela própria do MC** com o título do painel ("De Lá Pra Cá", classe `Qt656QWindowIcon`,
  `tem_dono` true) — o vigia do piloto a tomava por diálogo. Ela entra na lista de não modais (`piloto/apps.py`).
- O painel não tem console à vista: erro de script e promessa rejeitada sem dono vão ao log do serviço por
  `POST /diag/erro` (De Lá Pra Cá `186d2c6`) — foi o que mostrou que o código rodava certo e a tela é que não vinha.

## 🆕 10. `LinkFile` precisa do teto de ARQUIVO — `confirmado` (2026-10-13, MC 25.6, Windows)

Relink pela bin de fora (cópia da bin de 92 timelines aberta no projeto, com a original também aberta): o 2º `LinkFile`
passou dos **20 s** do teto de consulta, o cliente desistiu — e o MC **terminou o link depois**: a bin de trabalho ficou
com um master `B14_FUNDO` a mais, órfão, e a timeline sem ele ("1 de 2 mídias online"). Com o teto de arquivo (300 s):
2/2. Nessa hora cada `LinkFile` levou **~30 s** (30,2 / 30,1 s; também 30,2 / 30,2 / 30,9 s pela API direta logo
depois, com o foco no MC, no painel ou fora do MC); minutos depois, **0,1–0,2 s** (arquivos novos, bin pequena, logo
depois de abrir a bin grande, e no relink seguinte). Causa dos 30 s: `pendente` (não se repetiu fora daquela janela de
tempo). Regra: desistir cedo de uma chamada que o MC conclui sozinho é decisão errada, não erro honesto — a mesma do
`CloseBin`. Destino do `LinkFile` = o NOME DO ARQUIVO da bin com `.avb` ("Bin not found" sem a extensão).
⛔ **Bin em SUBPASTA do projeto** — `confirmado` (2026-10-13, MC 25.6, Windows): o destino é o caminho RELATIVO À PASTA DO
PROJETO, com `/` (`"TESTE_SUB/TESTE_LINK_SUB.avb"` → master em 0,7 s); só o nome (`"TESTE_LINK_SUB.avb"`) → `"Bin not
found."` (ErrorType 9) na hora, mesmo com a bin recém-criada pelo `CreateBin(folder_path="TESTE_SUB")`. Custou a 1ª entrega
organizada do relink do De Lá Pra Cá (bin `<nome>/<nome>_MIDIAS.avb`): 0/48 vídeos linkados e a timeline com o vídeo
offline, sem erro visível no painel. Medido pela API direta, uma forma por vez, parando na primeira que deu certo (a barra
invertida e o caminho absoluto NÃO foram testados).

## 🆕 11. Relink de AAF recebida — o que o curta PRODUCAO-A mediu (2026-10-13, MC 25.6, Windows)

AAF offline `PRODA_CORTE_ORIGINAL.aaf` (MC 25.12, 99 masters, 746 clipes), originais num HD externo (BRAW + BWF).

- ⛔ **`LinkFile` de WAV/BWF abre o modal `Audio Start-Time Options`** ("The file X contains a start time. How do you
  want the start time imported?" · Select · OK · OK to All · Cancel) e a API fica parada até a resposta; o editor teve
  de responder arquivo a arquivo (o "OK to All" não vale entre chamadas). Hipótese do gatilho — `hipotese`, com
  dados: dos 47 áudios, 41 têm chunk `bext` com `TimeReference` > 0 (som direto do gravador e o SFX `04 Dark
  Drone.wav`, o 1º a perguntar) e 7 não têm `bext` (AIF/AIFF de biblioteca e trilhas WAV). ✅ O autor confirmou
  (2026-10-13): os que não perguntaram eram os sem `bext` — `inferido` (confirmado pelo editor, não medido arquivo a arquivo). ⇒ Todo relink no MC injeta o áudio (autorado na bin, sem `LinkFile`).
- ✅ **`ImportFile` de uma AAF offline: sem diálogo, 1,8 s, e os 99 masters MANTÊM o MobID da AAF** na bin.
  ⚠️ Assíncrono: a chamada volta antes de a bin ter os mobs no disco.
  ⛔⛔ **E `CloseBin` colado no `ImportFile` (0,1 s): bin gravada VAZIA e o MC CAIU logo em seguida** (MC 2024.6, Win11,
  2026-11-01, Ciclo Assist `importar_masters_opatom`, 1ª prova): AAF de 4 masters (12 OP-Atom do Resolve, pasta
  `202611010` indexada 0,6 s depois do foco) → `ImportFile` "Completed" em 0,1 s → `CloseBin` → `OpenBin` → `.avb` com
  ZERO mobs, `GetListOfBinItems` vazio, e o **Crash report** do Avid na tela ~15 s depois (sem `FatalExcpt` no
  `EVENTLOG.LOG` até o diálogo ser respondido). Causa da queda `hipotese` (fechar a bin no meio da importação
  assíncrona); o spike de 31/10 fazia o mesmo e passou. ⇒ esperar os masters aparecerem na bin pela API antes de fechar.
  ✅ **Conserto provado no mesmo dia** (MC reaberto, mesma pasta já indexada, mesma bin): `ImportFile` → `GetListOfBinItems`
  a cada 2 s até os 4 MobIDs aparecerem (**1,8 s**) → 3 s → `CloseBin` → `OpenBin` → 4 masters no disco com `data_offset`,
  T01 carregado no Source mostrando a imagem a `10:00:05:00`, sem queda. A pilha do crash da 1ª prova (minidump do
  Crash report): **Access violation na thread principal dentro de um `QTimer::timeout`**, ponteiro `0x6c36` — um timer
  da importação disparando sobre objeto já liberado; causa `inferido` (sem símbolos do MC).
  ⚠️ O mesmo dia ensinou a regra de conferência: verificar "nenhum master sem offset" SÓ entre os mobs achados passa
  sobre uma bin vazia — a conferência tem de exigir que cada master esperado esteja lá.
- ⛔ **`Save` (DoCommand 1004) colado no `ImportFile` (0,1 s depois): a importação NUNCA chegou à bin** (3 min, bin de
  53 KB vazia). Com o 1º Save 5 s depois: 529 mobs em ~10 s — mesma AAF, mesmo MC. `confirmado` (2 de 2 × 2 de 2).
- ⛔ **"Sub clip conflict found"** ("The Clip you are importing (…) conflicts with one already found in the system. Do
  you want to replace the original…" · Yes · Yes To All · No · No To All): `ImportFile` de uma AAF cujos SUBCLIPES já
  estão no projeto (mesmo MobID). Modal: a API para. O app evita importando uma cópia achatada com MobIDs novos; o
  piloto responde No To All (catálogo `piloto/catalogos/avid`, autorizado pelo autor).
- `LinkFile` de HEVC Main 10 4K (drone DJI) → `ErrorType 66` "cannot be linked" (MC 25.6 sem o codec por AMA).
- Áudio que o injetor não tem modelo: WAV `('audio', 10, 32, 2)` (float 32 bits, estéreo) — `pendente`.
- ⭐ **`_ORG_BIN` (BinRef `MCBR`) de cada master = a bin em que ele mora.** Master com `_ORG_BIN` de uma bin que não
  está no projeto → ao clicar/abrir o clipe o MC avisa "Bin "X" is not in the Project. To edit with this clip, use Show
  Reference Clips…" (visto com o áudio injetado: `TEMPLATE Bin1`, herdado dos modelos). ⚠️ O UID vai TROCADO no
  BinRef: `uid_high` = 32 bits BAIXOS do `Bin.uid`, `uid_low` = os 32 ALTOS (medido: uid 0x070a9fae_6acdf311 →
  high 0x6acdf311, low 0x070a9fae). `confirmado` (a leitura); a escrita corrigida: `pendente` de pilotar.
- Do autor (editor, 2026-10-13): `LinkFile` numa bin que NÃO tem a mídia linka DE NOVO, mesmo que outra bin do projeto
  já tenha o mesmo arquivo; só não reimporta se a mídia já estiver na MESMA bin (oculta/referenciada: não sabido).


## 🆕 12. Bin em ABA, não flutuante: `CreateBin(option=1)` — `confirmado` (2026-10-13, MC 25.6, Windows)

`CreateBinRequestBody.option` (`OpenBinOption`: `FloatBin`=0, o padrão; `LastActiveBinContainer`=1;
`FollowBinSettings`=2 — não medido). Medido pela API direta num projeto com o contêiner de bins encaixado à esquerda:
- `CreateBin(folder_path="TESTE_SUB", bin_name="T_OPT1", option=1)` → a bin abre como **ABA do contêiner encaixado**.
- `CloseBin` + `OpenBin` dela → volta para a aba.
- ⭐ Uma `.avb` escrita no disco pelo pyavb com **UID novo**, nunca aberta → `OpenBin` também cai como aba. O `OpenBin`
  (que não tem `option`) abre no **último contêiner ativo**: com o `CreateBin` padrão (flutuante), a bin nova virava o
  contêiner ativo e TODO `OpenBin` seguinte abria solto — era por isso que as entregas do De Lá Pra Cá flutuavam.
- ⚠️ Uma CÓPIA byte a byte de uma bin aberta (mesmo UID) → `OpenBin` não abre nada novo (o MC a toma pela que já está
  aberta). Bin entregue = UID novo, sempre.

## 🆕 13. A janela de progresso do MC ("Linking clips, processing …") do tamanho da tela — `pendente` (2026-10-13)

O autor viu a janela de progresso do MC (`AvidMediaComposer`, título da janela Qt) maior a cada aparição, até quase
cobrir o MC. Medido no relink seguinte (amostra a cada 2 s): um hwnd só, reaproveitado, **(0, 25, 1920×1055)** do começo
ao fim — já do tamanho do monitor principal, sem crescer DURANTE a rodada. Ambiente: monitor principal 1920×1080 a
**125 %** (120 dpi), o 2º a **100 %**; nenhum código do De Lá Pra Cá, do piloto ou da bancada redimensiona essa janela
(só `frente()`/`ShowWindow` e as bins/editores de efeito). Hipótese: o MC guarda a geometria da janela e a restaura
ampliada pela escala mista (Qt), crescendo a cada abertura até o teto da tela. Refutaria: crescer com os dois monitores
na mesma escala. Falta medir o tamanho em cada abertura numa sessão nova do MC.

## 🆕 14. `LinkFile` lento = arquivo JÁ linkado no projeto aberto — `confirmado` (2026-10-13, MC 25.6, Windows)

Mesma AAF (PRODUCAO-A), mesmos 48 vídeos (BRAW + 2 ProRes 4K num HD externo), relink do De Lá Pra Cá (`LinkFile`
um a um numa bin nova), medido arquivo a arquivo:

| rodada | projeto | AMA Management (entradas) | mediana | total |
|---|---|---|---|---|
| 3ª no mesmo projeto | 2 relinks anteriores dos mesmos arquivos | 1371 | ~4,6 s | 221 s |
| 1ª, projeto novo, MC reaberto | vazio | 0 → 46 | 0,34 s | 18,7 s |
| 2ª no MESMO projeto | os 48 já linkados (bin da 1ª) | 46 → 92 | **3,09 s** | 157,6 s |
| 1ª, OUTRO projeto novo, MESMA sessão | vazio | 92 → 138 | 0,48 s | 26,8 s |

⇒ O custo vem de o projeto aberto já ter master AMA do MESMO arquivo (~10×), não do tamanho do `AMA Management` (que
pesa pouco: 0,34 → 0,48 s) nem da sessão do MC. Todo `LinkFile` acrescenta uma entrada no `Managed AMA Media
Folders.xml` e uma pasta em `AMA Metadata Folders` (46 por rodada aqui), sem reaproveitar a da mesma pasta de mídia:
depois de ~30 rodadas eram 1371 entradas para 71 pastas de mídia e ~1290 pastas órfãs (111 MB). Apagar (renomear)
a `AMA Management` com o MC fechado é seguro: ele a recria vazia na abertura.
- ⚠️ Rodadas repetidas no mesmo projeto (teste, refazer o relink) parecem REGRESSÃO; compare sempre num projeto novo.
- A pasta da entrega criada por `CreateBin(folder_path=…)` neste projeto novo apareceu no painel de Bins SEM refresh
  (no projeto antigo foi preciso o Refresh) — `pendente` o que decide.
- §13 (janela de progresso enorme): com o MC recém-aberto ela nasceu **503×156** (709, 436), compacta. Cresce durante a
  sessão — falta medir abertura a abertura.
- ⭐ **Reaproveitar em vez de linkar de novo — `confirmado` (2026-10-13):** (1) achar o que o projeto já linkou é BARATO
  lendo as `.avb` do disco: 15 bins/12,4 MB em 0,81 s, 7/7,5 MB em 0,52 s, 4/3,8 MB em 0,26 s (~0,07 s/MB; master com
  `_IMPORTED_AMA`, caminho no `WinFileLocator` via `avb_bin.segmentos.caminho_do_locator`, NÃO `nle_model.locator_path`,
  que só lê `path_posix`); (2) uma bin NOVA (`Bin.uid` novo) com a sequência de MobID novo e os masters COPIADOS com o
  MESMO MobID dos já linkados abre e a timeline vem ONLINE no Record, com a bin original dos masters fechada — sem
  nenhum `LinkFile`. Scripts: `_DeLaPraCa/tools/medicoes/varrer_ama_do_projeto.py`, `reuso_de_master.py`.
- ✅ **No produto (De Lá Pra Cá `0c8d039`, 2026-10-13):** relink repetido num projeto que já tinha os 48 vídeos linkados →
  varredura de 5 bins + 48/48 reaproveitados (master e cadeia copiados para a bin nova, mesmo MobID), `LinkFile` 0,
  timeline online no Record; o relink inteiro (importar a AAF, injetar 46 áudios, montar) em 71 s.
- ⛔ **Sem `LinkFile` no meio, dois `Save` ficam colados (2026-10-13, 3ª rodada no "DLPC LINK LIMPO 2"):** com os 48
  reaproveitados, o `Save` antes da varredura e o `Save` depois do laço saíram a 0,3 s um do outro; o 2º caiu com o
  ErrorType 73 ("Can't start more than one command on time." — `copia-da-timeline.md`, tabela de tentativas) e derrubou
  o relink, deixando a pasta da entrega com a `_MIDIAS` vazia aberta. Na rodada validada antes (`597fefd`) passou por
  sorte de tempo. Remédio no app: `Acoes.comando` repete o 73 a cada 0,2 s até vagar, com prazo de 30 s (o mesmo que o
  `piloto.pontes.comando`). Depois disso, 4ª rodada: 48/48 reaproveitados, 94/95 online, 735 clipes, Record, ~80 s.

## 🆕 15. Recarregar o painel: "Reload" do botão direito — `confirmado` (2026-10-13, MC 25.6, Windows)

F5 dentro do painel não faz nada, mas o **botão direito** num espaço vazio do painel abre o menu do QtWebEngine
(Back · Forward · **Reload** · Save page · View page source) e o **Reload** busca de novo a página do serviço — o
código novo da UI entra sem fechar o painel nem o MC. Pilotando: abrir o menu, **esperar ~1 s** e só então clicar no
Reload (o clique colado no botão direito caiu fora e o painel não recarregou). Também medido: a **roda do mouse não
rola** o painel encaixado (rolar = arrastar a barra de rolagem dele).

⚠️ **`ImportFile` "Completed / progress 100" SEM efeito num projeto 1080p/50 recém-criado** (MC 24.6.0, Win11, 2026-10-23):
nem master na bin, nem MXF escrito — com o clipe de 50p E com um clipe de 23,976 que importou na hora, no mesmo dia, num
projeto 1080p/23.976 (mesmos `import_settings_name="Untitled"`, drive "SSD (D:)", bin do projeto, sem diálogo na
tela). A API descreve o projeto 50p como `type: "Custom"`. Causa `pendente`. Consequência para quem automatiza: o
"Completed" do `ImportFile` não prova nada — conferir a bin e a mídia em até 60 s e parar com foto.

## 🆕 2026-11-19 — o aviso de volume ao entrar no projeto, e o MC que trava depois do Leave (MC 2024.6, Windows 11)

- ⭐ **"This volume has not yet been mounted by the application. You can either mount all volumes or load another
  project."** [Mount All Volumes] [Load Another Project] — título "Avid Media Composer" (com espaços, NÃO o
  "AvidMediaComposer" do aviso de teclado), 876×117 a 125 %, MODAL (a principal fica desabilitada). `confirmado`, 3 de 3:
  apareceu ao ENTRAR em todo projeto NOVO criado nesta manhã (projetos em `D:\MIDIAS DE TESTES\…\PROJETO`), inclusive
  sem reiniciar a máquina entre um e outro. Enquanto ele está na tela a API fica MUDA (`GetBins` e a foto da tela
  esgotam os 20 s) — o mesmo sintoma de todo modal. Resposta: **Mount All Volumes** (o MC lê os discos e o projeto abre;
  o foco já nasce nele). No Ciclo Assist: `piloto/auxilio.preferir_nao_avisar` + `avid/abrir` (modal desconhecido por
  3 s chama o agente do piloto). Foto: `piloto/catalogos/avid/volume_nao_montado.png`. Causa de aparecer: `pendente`.
- ⛔ **File › Exit › Leave e o MC TRAVADO por 8 min** (2026-11-19, 07:43, projeto recém-criado e vazio): "Not Responding",
  nenhum diálogo, CPU ~0 (0,14 s em 10 s) e NADA escrito em disco — não é o "salvando por 3,5 min" de 2026-11-04 (lá a
  memória subia e o disco escrevia). Encerrado à força (projeto de teste). ⇒ Antes de concluir "está salvando", medir
  CPU e escrita: parado nos dois = travou. Causa `pendente` (foi o 1º fechamento depois do aviso de volume).
- ⭐ **A Location da Select Project é a ÚLTIMA usada, e ela mora no `MCState`** (2026-11-19, MC 2024.6, Windows):
  `Public\Documents\Avid Media Composer\Avid Users\<perfil>\MCState` guarda o caminho do último projeto aberto no
  formato do Avid (`D//MIDIAS DE TESTES/…/PROJETO/ENSAIO AULA 3/`); a pasta de cima é a Location que a Select Project
  mostra. `confirmado`. Quem decide "o projeto existe?" olhando só `Documents\Avid Projects` erra quando o editor mudou
  a Location — o Ciclo Assist pedia formato para CRIAR um projeto que estava na lista (`avid/abrir._location_do_mcstate`).
  ⚠️ Encerrar o MC à força NÃO atualiza o `MCState` (ficou o projeto anterior). Mac: `pendente`.

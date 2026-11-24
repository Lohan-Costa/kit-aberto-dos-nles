# Arrastar do Media Composer para dentro de um painel

> **O que é:** o editor arrasta clipes ou timelines de uma bin e solta **dentro do painel
> do Panel SDK**. O Media Composer entrega o que foi arrastado como um **MIME customizado**,
> lido por um `ondrop` de DOM comum.
>
> **Por que tem arquivo próprio:** isto não é específico do Windows nem de uma versão — é
> uma capacidade da plataforma. Nasceu dentro de [windows.md](windows.md) por acidente
> (era onde morava a afirmação errada que ele corrige) e cresceu até ocupar metade daquele
> arquivo.
>
> **Estado:** `confirmado` de ponta a ponta — mecanismo lido no painel do
> [ESION Studio](esion-arquitetura.md) e depois **implementado e exercitado por um editor**
> no De Lá Pra Cá (MC 25.6 / Windows 11, 2026-08-15).

---

## 1. ⚠️⚠️ A correção: este banco dizia que isto era IMPOSSÍVEL

A seção de drop de [windows.md](windows.md) afirmava, como `confirmado`:

> *"Não existe caminho MC → painel. Arrastar um clipe de uma bin para dentro de um painel
> do Panel SDK não é suportado"* — e mandava usar `BinRowSelectionChanged` no lugar.

**Errado.** E o modo como se errou vale mais que o fato:

A conclusão veio de **enumerar símbolos do binário** do Media Composer procurando
`Drop*`/`Drag*`. Só apareceram os três de saída (`DropFromPluginTo{Bin,Composer,Timeline}`).
A busca estava certa; o **pressuposto invisível** é que estava errado:

> *"se a capacidade existe, existe um símbolo para ela"*

⭐ **Não existe símbolo porque não é um rpc.** O Qt entrega o arrasto à webview como MIME,
e quem implementa o resto é o Chromium. **Metade da superfície de um painel é a do
navegador, e essa metade não aparece em `strings` do executável hospedeiro.**

**A regra que fica:** ausência de símbolo prova ausência de **rpc**, não ausência de
**capacidade**. Antes de concluir "não existe", escreva **onde** você procurou — e
pergunte que outras superfícies a plataforma tem. Ver
[transversal/analise-de-executaveis.md](../../transversal/analise-de-executaveis.md)
§Calibração, onde este é o caso 5.

---

## 2. Como funciona

Duas constantes, lidas do painel do ESION:

```js
MCAPI_ASSET_LIST_MIME_TYPE        = 'text/x.avid.mc-api-asset-list+json'   // MC   → painel
MCAPI_PLUGIN_ASSET_LIST_MIME_TYPE = 'text/x.avid.panel-sdk-plugin-asset-list+json'
```

O handler é DOM puro:

```js
dropArea.addEventListener('drop', (e) => {
  if (e.dataTransfer.types.includes(MCAPI_ASSET_LIST_MIME_TYPE)) {
    const itens = JSON.parse(e.dataTransfer.getData(MCAPI_ASSET_LIST_MIME_TYPE));
  }
});
```

⭐ **Nada disso é declarado no manifesto.** O ESION usa
`usesApi: ["avid.mediacomposer.general"]` e mais nada; `subscribesToChannels` e
`entitlements` vazios. **A capacidade não é concedida — ela existe** para qualquer painel
que escute `drop`.

⭐ **E sobrevive a a página ser servida por `http://`.** O ESION roda em `avpi://`; o
De Lá Pra Cá navega para `http://127.0.0.1:<porta>` (o padrão dos parceiros oficiais) e o
MIME chega igual. **Fecha o `pendente` mais antigo desta pasta** — mas só para o arrasto:
a ponte de EVENTOS do QWebChannel nessa mesma situação continua não medida.

### O payload

Um **ARRAY JSON**, um objeto por item. Medido:

```json
[{ "head": "0",
   "id": "060a2b340101010501010f1013-000000-66131c7412678306-d35904bf1b65-d319",
   "systemID": "mc-api",
   "systemType": "mediacomposer",
   "type": "sequence" }]
```

| campo | o que é |
|---|---|
| `id` | o **MobID** |
| `type` | a espécie — §3 |
| `systemID` / `systemType` | ⭐ o **sistema de origem**, NÃO a bin (`mc-api`/`mediacomposer`) |
| `head` | frame inicial; `"0"` em tudo, exceto no subclip, onde repete o `in` |
| `in` / `out` | ⚠️ **só no subclip** — §3 |

⚠️ **Não valide o MobID pela pontuação.** O agrupamento de hifens muda conforme a
superfície: **26-6-16-12-4** aqui (é o que o regex do ESION exige) e **26-6-16-8-8** no
exemplo da API registrado neste banco. Os dois somam **64 dígitos hex** — filtre os
hexadecimais e conte. Um validador que crave os hifens recusa MobID legítimo, e o sintoma
é *"o clipe que arrastei não é reconhecido"*.

⛔⛔ **E o pyavb grafa uma TERCEIRA forma, com os mesmos hex na mesma ordem** — `confirmado`
(Ciclo Assist, MC 2025.6.58781 / Windows 11, 2026-09-15, bin `CENAS\C07.avb`):

```
arrasto  060a2b340101010501010f2013-000000-a9b9937581c0448d-bc9639bde525-ea79
.avb     urn:smpte:umid:060a2b34.01010105.01010f20.13000000.a9b99375.81c0448d.bc9639bd.e525ea79
```

Sem troca de bytes: tirar o `urn:smpte:umid:` e a pontuação dá os mesmos 64 hex. Quem
compara a string não acha **nenhum** clipe arrastado dentro da bin onde ele mora. No
Ciclo Assist isso fazia o modelo (Haiku) perguntar ao editor em que bin estavam os
subclipes que ele tinha acabado de arrastar, e o editor leu o erro como falta de
consistência do modelo.

---

## 3. ⭐⭐ As espécies, e como distinguir cada uma — `confirmado`

Medido num **único arrasto misto**: como o payload é uma lista, uma seleção com um de cada
espécie responde tudo de uma vez. (Vale como método — é o jeito barato de mapear um
vocabulário fechado.)

| espécie arrastada | `type` | como se reconhece | nº de colunas |
|---|---|---|---|
| timeline | `sequence` | colunas `Master Dur`/`Edge`/`End`/`Film`/`Start` + `AFD`; `Tracks` traz `TC…`/`EC…` | 23 |
| master **AMA-linkado** | `masterclip` | ⭐ **tem `Source File` + `Source Path`** | 68 |
| master **gerenciado** (transcode) | `masterclip` | ⭐ **não tem** `Source File`/`Source Path` | 37 |
| subclip | `subclip` | únicas com `Mark IN`/`Mark OUT`/`IN-OUT`/`Slip`/`Offline`/`Tape`; e traz `in`/`out` | 42 |
| group clip (multicam) | `group` | o `type` basta; sem colunas exclusivas | 25 |
| **efeito** (ex.: `Resize`) | **`""`** ⚠️ *string vazia* | o menor conjunto de colunas | 15 |

⚠️ **O `type` NÃO separa AMA de gerenciado** — os dois são `masterclip`. Quem separa é a
coluna do `GetMobInfo`: **`Source File`/`Source Path` = existe arquivo externo de origem**.

> Ressalva de escopo: medido com um **BRAW AMA** contra um **`.new.01` transcodado**. Um
> clipe importado por *File ▸ Import* provavelmente **também** tem `Source Path` — não
> testado. A leitura segura é *"tem arquivo de origem conhecido"*, não *"é AMA"*.

⚠️ **Efeito vem com `type` VAZIO**, não com um nome. Quem escrever `if (!tipo)` para "não
sei o que é" vai confundi-lo com payload defeituoso.

⭐ **As colunas são impressão digital por CONJUNTO**, não só por valor: 13 são comuns a
todas as espécies (`Name`, `Tracks`, `FPS`, `CFPS`, `Cadence`, `Color`, `Lock`, `Marker`,
`Creation`/`Modified Date`, `Frame Count *`), e a contagem total vai de **15** (efeito) a
**68** (master AMA de BRAW, que traz ~30 colunas de metadado de câmera lidas pelo plugin).

⭐ **Custa zero chamada extra:** o `GetMobInfo` que se faz para saber o NOME do item
arrastado (o payload não traz nome) devolve as colunas junto.

### ⚠️⚠️ `in`/`out`: duas leituras erradas antes da medição

1. **"vêm sempre"** — tirado do **código do ESION**, que faz `element["in"]`.
   *Ler um campo não prova que ele exista.*
2. **"nunca vêm"** — tirado de **uma amostra só**, um arrasto de sequence.

**Medido com seis espécies: só o SUBCLIP os traz** (`in: "12014"`, `out: "12112"`, com
`head` repetindo o `in`). Faz sentido — um subclip *é* um recorte.

⭐ **Lição:** uma amostra prova **existência**, nunca **ausência**. Para negar um campo é
preciso variar a espécie do que se arrasta, não repetir o mesmo arrasto.

### A taxonomia RICA está na API, não no arrasto

`GetListOfBinItems.BinItemFlags` ([`mcapi.proto`](dados/mcapi.proto)) separa **doze**
categorias — e é a única fonte que distingue importado de linkado por conta própria:

```
AllTypes · masterClips · linkedMasterClips · subclips · sequences · sources
effects · motionEffects · preCompsRE · preCompsTMK · groups · stereoscopicClips
```

⚠️ Mas ela classifica **dentro de uma bin**, e o arrasto entrega MobID **sem bin**. **Pela
API** não há como cruzar as duas. Por isso a classificação prática sai do `type` **mais** as
colunas.

⭐ **Pelo ARQUIVO, cruza** — `confirmado` (Ciclo Assist, 2026-09-15): é só ler as `.avb` do
projeto com pyavb e procurar o MobID (normalizado em 64 hex) entre os `content.items`.
Leva **0,12–0,16 s nas 42 bins** do projeto de teste, e os dez subclipes arrastados da C07
caíram, sem ambiguidade, em `CENAS\C07.avb`.
⛔ **Conte só `user_placed`.** Uma bin que o próprio app gerou leva uma cópia OCULTA dos
mesmos subclipes (o fecho, [../../protocolos/avb/escrita.md](../../protocolos/avb/escrita.md)).
Contada, cada take "estaria" em várias bins e ninguém saberia de qual o editor arrastou.
Implementação: `_CICLO ASSIST/cicloassist/avid/bins.py::bins_dos_mobs`.

⚠️ **E o vocabulário do arrasto não é o do console.** O binário do MC tem uma tabela
alfabética colada ao comando `forEachMob` (`all · effect · file · film · group · logical ·
master · motion · nagra · physical · precompute · sequence · sfile · subclip · tape`) —
mas ali é **`master`** e o arrasto manda **`masterclip`**. Vocabulários distintos.

---

## 4. ⛔ O que NÃO funciona — resultados negativos, medidos

Registrados com a mesma clareza dos positivos: é o que impede a próxima pessoa (ou o
próprio autor, meses depois) de gastar a mesma tarde.

### Arrastar uma BIN não entrega nada

Payload capturado ao soltar uma bin do painel lateral:

```json
{"efeito": "move", "tipos": [], "tipos_no_enter": [], "arquivos": 0, "dados": {}}
```

**Três medições convergentes:** o realce não acende (depende de achar MIME conhecido no
`dragenter`); `types` vazio no `dragenter`; `types` vazio no `drop`.

⭐ E note o que **não** está vazio: `effectAllowed = "move"`. O MC **inicia um arrasto de
verdade**, que a webview enxerga — ele só não carrega dado que o Chromium saiba expor.
Leitura provável: formato interno do Qt (tipo `application/x-qabstractitemmodeldatalist`)
que o QtWebEngine não traduz.

⚠️ Existe `text/x.avid.location-item-list+json` no binário — "location item" é como o Avid
chama o que vive no painel de bins — e **ele não chega à webview**. É a armadilha de
calibração do eixo AUSÊNCIA **vista pelo avesso**: *presença de símbolo também não prova
capacidade*. A regra vale dos dois lados — pergunte em **que superfície** aquilo vive.

⭐ **O gesto que ocupa esse lugar:** selecionar as timelines na bin e arrastar o
**conjunto**. O payload é uma lista.

#### ⛔⛔ Fora da webview também não — os QUATRO canais medidos (2026-09-19) — `confirmado`

> MC **2025.6** (Windows 11), Assist anterior. Pergunta do autor: *"se o MC reorganiza bins
> arrastando dentro do painel lateral, a identidade existe no arrasto"* — e o método que
> virou o jogo no Premiere (`premiere-cep/arrastar-e-selecao.md` §6b: janela nativa com
> `IDropTarget` vendo o `IDataObject` inteiro). Aqui ele NÃO virou.

| canal | sonda | o que chega ao arrastar BIN ou PASTA do painel lateral |
|---|---|---|
| webview do painel | `_ASSIST ANTERIOR/tools/sonda_painel/` (painel `.avpi` que fica em `avpi://`) | `types: []`, `effectAllowed: "move"`, `getData` vazio até pedindo os nomes do binário |
| OLE (`IDataObject`) | `_ASSIST ANTERIOR/tools/sonda_arrasto_nativo.py` (cópia da do Órbita) | UM formato, **`mediacomposer.sidebar.bins.list`** (cf 50574, HGLOBAL), de **1 byte** — e o byte NÃO identifica: a mesma bin C07 deu `00` e depois `90`; C04 `70`, D02_CAM A `b0`, pasta D02 `04`, duas bins `08`; no `Drop` sempre `00`. A lista de verdade fica no processo |
| eventos `mcapi.onEvent` | o mesmo painel `.avpi` | NENHUM ao clicar bin/pasta no painel lateral, nenhum ao arrastar. Calibração: clicar num clipe dentro da bin deu o `BinRowSelectionChanged` de sempre |
| acessibilidade (UI Automation) | `_ASSIST ANTERIOR/tools/sonda_acessibilidade.py` | a janela INTEIRA do MC publica **17 nós** (moldura, dois `OglVideoWin`, um `Pane` vazio). O painel lateral não existe para ela — estende o §7d de `windows.md`, que só tinha olhado a barra de menus |

⭐ **E a ABA da bin aberta (a lingueta do Bin Container) idem** — medida logo depois, pelos
dois caminhos: para a janela nativa ela oferece **um** formato, `action`, com 13 bytes de
texto — **`avid-tab-move`**, igual nos três arrastos (duas bins e uma pasta); para o painel
chega vazio como as outras. É o mesmo desenho: um marcador de intenção, nunca o item.

⇒ **Nesta versão, nenhum canal alcançável de fora diz QUAL bin foi arrastada.** O arrasto
serve como SINAL ("chegou uma bin ou pasta": `types` vazio + `move`), nunca como dado. A
diferença para o Premiere é de desenho: lá o formato legível é o do Dynamic Link, feito
para OUTRO app ler; o do Avid só existe para o próprio MC.

⚠️ **E o clipe, pelo OLE, traz mais do que a webview mostra** (mesma sonda): `CF_HDROP` e
`UniformResourceLocator(W)` apontando para um `.mxf` TEMPORÁRIO em `%TEMP%` (nome GUID —
parente do `.aaf` de zero bytes abaixo), `text/x.avid.asset-list-extended+json`
(`systemType: "interplay-pam"`), e **`application/x-dnditemdata`**, um XML
`<mobIDDragObjectList local="true"><mobIDDragObject mobID="…{…}" keyframe="0"/>` — o MobID
numa TERCEIRA grafia (com chaves). Nada disso muda o que se sabe do clipe; fica o registro.

⭐ **E por dentro do executável (mesma noite, só LENDO o `AvidMediaComposer.exe` 2025.6,
86 MB; `_ASSIST ANTERIOR/tools/vizinhos_no_binario.py`)** — `inferido`, strings e não código:
- `mediacomposer.sidebar.bins.list` mora no **`BinContainerModel`** (`/Media Composer/
  BinContainerModel`), vizinho de **`mediacomposer.sidebar.bins.allHaveSameParent`** (um
  SEGUNDO formato, que nenhuma sonda viu), das asserções `(treeModel)!=0` e `(rowPtr)!=0`,
  de `BinContainerSideBar::mouseMoveEvent` e de `BinContainerSideBarTreeView: The drop
  action was ignored.` ⇒ o painel lateral é um `QTreeView` com modelo próprio, e o arrasto
  leva, muito provavelmente, **ponteiros de linha** — válidos só dentro do processo. É o que
  explica o byte que muda para a mesma bin.
- ⛔ **CORRIGE a pista acima:** `text/x.avid.location-item-list+json` NÃO é do painel de
  bins. Mora no `HostedUXWindow` (o painel **MediaCentral Cloud UX**), junto de
  `interplay-pam`, `avid-pmplus`, `avid-nexis`, `browseAppDrop`, `dragData`, `dropTarget` e
  *"Dragging items to remote workgroups is not supported."* — é o formato de arrastar ativo
  do MediaCentral PARA o MC.
- Há comandos de console do painel de bins (`BCCacheDump`, `BCPrintUpdateStats`,
  `BCClearUpdateStats`, `BCLocalTimeout`, `BCRemoteCacheTimeout`). ⛔ **`BCCacheDump`
  RODADO** (2026-09-19, Tools → Console, com uma bin selecionada no painel lateral):
  `Number of paths: 0, Number or column/role pairs: 0` — o cache nasce vazio em projeto
  local. E **nenhum comando de console mostra a SELEÇÃO**: varridas todas as frases de
  ajuda do executável que citam `selected`/`selection`/`sidebar`/`bin container`, as que
  existem são de outras coisas (mixdown, trilhas, configurações de importação).

**O que NÃO foi tentado:** ler a memória do processo; OCR do painel lateral na posição do
mouse; `QT_ACCESSIBILITY=1` no ambiente do MC (a árvore vazia sugere interface desenhada
pelo `AvUIshell`, não QWidgets — `hipotese`); o MC do macOS. ⭐ O gesto que já funciona
com identidade: abrir a bin, **Ctrl+A** e arrastar os CLIPES — os MobIDs levam à bin.

### ⏭️🆕 CAMINHO A REVISITAR: a bin não é "impossível", está fechada POR FORA (ideia do autor, 2026-10-26)
O negativo acima esgotou os canais de FORA (DOM/OLE/webview): o arrasto da bin carrega **ponteiros de linha
in-process** e o MC **recusa o nosso painel como alvo** — `BinContainerSideBarTreeView: The drop action was
ignored.` + `BinContainerSideBar::mouseMoveEvent` (strings §acima). A porta nova, por DENTRO: *o que diz ao MC
que o nosso DLPC não é um painel de bin válido para drop?* Hipótese a testar com **REA/Frida no processo** —
interceptar a validação de alvo (o handler que decide "drop ignored") e **simular a identidade de outro painel
de bin** (`BinContainerModel`/`QTreeView`), para o MC achar que largamos a bin em outro bin e **computar o
movimento**, revelando o caminho/MobID do que SERIA movido (como o CF_HDROP para `.mxf` temporário já insinua).
O que NÃO foi tentado (§acima) continua valendo: ler a memória do processo, `QT_ACCESSIBILITY=1`, o MC do Mac.
⭐ **Método (autor):** um resultado negativo fecha UM caminho, não a função — revisitar por outro ângulo (aqui,
de fora → por dentro) é o que o REA abre. ⭐ **Cross-app:** a leitura da SELEÇÃO da timeline (§"PASSO 2 PROVADO")
não serve só ao relink — é a base do **sync local** (explorado no Premiere e arquivado com dificuldades:
`plugins/premiere-cep/arrastar-e-selecao.md`); ligar os dois ao retomar.

### O `.aaf` anexo ao arrasto tem ZERO BYTES

O arrasto de uma sequence traz `text/uri-list` + `Files` apontando para um `.aaf` no Temp:

```
file:///C:/Users/<user>/AppData/Local/Temp/FDE8B3B7-D06A-44ee-BC5E-C296196152BA.aaf
```

Parecia enorme — o MC exportando um AAF sozinho dispensaria todo o `ExportFile` + preset,
inclusive a exigência de **fechar o editor** para instalar setting.

**Não dispensa.** O `File` do evento tem `size == 0`, e uma **vigia nativa** (processo
fora da webview) provou que **o arquivo nunca chega a existir**: 40 amostras em 10 s,
nenhuma o encontrou. O Chromium sintetiza o `File` a partir do descritor do arrasto; o
conteúdo só sairia para um alvo que o pedisse pelo mecanismo do shell (*delayed
rendering* do Windows).

⚠️ **Quarta repetição da mesma lição de calibração deste banco** — depois de "um modelo no
disco não é uma feature", "um SDK no bundle não é um agente" e do `ggml-base.en.bin` de
313 bytes: **confira o TAMANHO antes de concluir que a capacidade existe.** Aqui o arquivo
tem o nome certo, a extensão certa e nada dentro.

### `asset-list-extended` não é metadado mais rico

O nome sugeria. **É a mesma lista na variante Interplay/PAM** — `systemType` vem
`interplay-pam` nele e `mediacomposer` no do Panel SDK. O protocolo de arrasto de asset da
Avid atravessa o ecossistema deles. Sai do pendente sem virar oportunidade.

---

## 5. Armadilhas de implementação — todas medidas

| armadilha | sintoma | correção |
|---|---|---|
| ⭐⭐ **`dropEffect` incompatível com `effectAllowed`** | o realce aparece e **soltar não faz nada** | o MC arrasta com **`effectAllowed = "move"`**; forçar `"copy"` cancela o drop em silêncio. Escolha um efeito compatível |
| **Ouvir na fase de BOLHA** | funciona em parte da janela e não em outra | `<select>`/`<input>` têm tratamento próprio de drop e consomem o evento; registre na fase de **CAPTURA** |
| **`preventDefault` só quando o MIME é o nosso** | soltar um ARQUIVO faz a webview **navegar para ele** e a UI do painel desaparece | `preventDefault` **incondicional** no `dragover`; o filtro de MIME decide o realce, não o controle do navegador |
| **Resposta fora da área visível** | *"não aconteceu nada"* | num painel de 500 px, uma linha de status no rodapé da página não é vista. Traga a resposta para a vista |

⚠️ A última não é de plataforma, e mesmo assim custou metade do tempo de depuração:
*"não aconteceu nada"* e *"a resposta apareceu onde você não olha"* são indistinguíveis
para quem está usando.

⭐ **Lição de processo, a mais transferível:** o que destravou não foi tentativa e erro —
foi **instrumentar**. Uma linha na tela com `enter/over/leave/drop` + `effectAllowed` +
`types` respondeu tudo numa foto, e revelou de brinde dois MIMEs que ninguém procurava.
⚠️ E o primeiro diagnóstico tinha um defeito próprio: **não zerava entre arrastos**, então
a lista de tipos do arrasto anterior sobrevivia e parecia ser do atual — o que quase virou
conclusão errada sobre a bin. *Instrumento também precisa de revisão.*

---

## 6. O catálogo completo de MIMEs de arrasto

Enumerado do binário (`strings -a` sobre `AvidMediaComposer.exe`, MC 25.6). Como veio do
executável, **é a lista inteira do que o MC sabe emitir** — não o que se viu por acaso:

```
text/x.avid.asset-list+json                     (não observado)
text/x.avid.asset-list-extended                 (não observado)
text/x.avid.asset-list-extended+json            ⬅ variante Interplay/PAM
text/x.avid.location-item-list                  (não observado)
text/x.avid.location-item-list+json             ⬅ bin — NÃO chega à webview
text/x.avid.mc-api-asset-list+json              ⬅ o que se lê
text/x.avid.panel-sdk-plugin-asset-list+json    ⬅ saída: painel → MC
```

Um arrasto de clipe/timeline chega com **cinco** tipos: `text/plain`, `text/uri-list`,
`asset-list-extended+json`, `mc-api-asset-list+json` e `Files`.

---

## 7. Por que vale mais que `BinRowSelectionChanged`

O evento continua existindo e útil — só não é mais *"o substituto porque o drag não
existe"*. Eles respondem perguntas diferentes: o evento diz *"o que está marcado agora"*;
o arrasto diz *"leve estes"*.

Para escolher material, o arrasto ganha:

- traz o **MobID sem `GetListOfBinItems`** — sem o piso de ~500 ms por bin;
- **não depende do `GetListOfWindows`**, que [não existe no MC 25.6](windows.md);
- funciona com **bin fechada**, que o seletor não alcança;
- é **multi-item** por construção;
- é **gesto deliberado**, não estado ambíguo que muda sozinho.

---

## 7b. ⭐⭐ Arrastar do EXPLORER para o painel entrega o CAMINHO — `confirmado`

Outra origem, outro mecanismo, e a resposta é **sim**: soltar uma **pasta do Windows
Explorer** sobre o painel entrega o **caminho absoluto**, não só o nome.

Medido 2026-08-16, MC 25.6 / Windows 11 23H2, painel servido em `http://127.0.0.1:7823`:

```
efeito permitido : "all"          (o do MC é "move" — ver §5)
tipos            : text/plain, text/uri-list, Files
text/uri-list    : file:///E:/MIDIAS%20DE%20TESTES/.../MIDIAS%20VALENDO
text/plain       : file:///E:/MIDIAS DE TESTES/.../MIDIAS VALENDO   (sem encoding)
Files[0]         : { nome: "MIDIAS VALENDO", tamanho: 0 }
```

⚠️⚠️ **CORRIGE uma afirmação que circulava como óbvia** — *"o navegador esconde o caminho
absoluto de um arquivo solto"*. Isso vale para uma **página web comum**; **não vale nesta
webview**, que expõe `text/uri-list` com o caminho inteiro. A afirmação tinha sido
**inferida do comportamento padrão do Chromium**, nunca medida aqui — e por causa dela um
painel fica sem o gesto mais natural para apontar uma pasta.

⭐ **Por que isto importa mais do que parece:** o `README` desta pasta repete, com razão,
que *o painel é QtWebEngine e **não lê disco***. Continua verdade — mas **saber o caminho
não é ler o disco**. O painel recebe a string e quem toca o disco é o serviço local, que
já existe. Um app que leia a regra "não lê disco" como "não dá para apontar pasta"
descarta a solução inteira.

⚠️ **Não confunda com o `Files` do arrasto DO MC** (§4): lá o `.aaf` anexo tem 0 bytes e o
arquivo **nunca chega a existir**. Aqui `tamanho: 0` é apenas uma **pasta** não ter
tamanho. A regra que separa os dois casos: **quem vale é o CAMINHO, nunca o objeto
`File`.**

**As formas que a conversão tem de cobrir** (todas custam caro quando faltam, todas falham
em silêncio — o caminho errado simplesmente "não existe" e o app relata pasta vazia):

| forma | entra | sai |
|---|---|---|
| percent-encoding | `file:///E:/A%20B` | `E:\A B` |
| barra da frente | `file:///E:/a` | `E:\a` (não `\E:\a`) |
| UNC (diária em rede) | `file://SERVIDOR/share/x` | `\\SERVIDOR\share\x` |
| POSIX (macOS) | `file:///Volumes/X/y` | `/Volumes/X/y` |
| várias linhas | `uri\r\nuri`, `#` = comentário (RFC 2483) | vários caminhos |

⭐ **E a lição de método, que é a mesma da §1:** o instrumento que respondeu isto já
estava pronto — o painel ouve `drop` no **documento inteiro e SEM filtro de MIME**, e
deposita o que chegou em `/diag/arrasto`. A medição custou **um gesto do editor e zero
linha de código**. Um `ondrop` que só escuta o que já sabe ler nunca descobre o que mais
poderia receber.

### ⚠️⚠️ VÁRIOS itens: o `text/uri-list` vem TRUNCADO, o `text/plain` vem inteiro

Arrastando **duas pastas selecionadas juntas** (`SFX` e `TRILHAS`), medido 2026-08-16:

```
text/uri-list : file:///E:/.../SFX                              ← só a PRIMEIRA
text/plain    : file:///E:/.../SFX \n file:///E:/.../TRILHAS \n ← as DUAS
dataTransfer.files : 2   (nomes "SFX" e "TRILHAS", tamanho 0)
```

**O tipo canônico é o incompleto.** `text/uri-list` é o formato que a RFC 2483 define
justamente para carregar *uma lista*, e é o que qualquer implementação lê primeiro — e é
ele que chega com um item só. O `text/plain`, que todo mundo trata como reserva, é o que
está certo.

⚠️ **O modo de falha é o pior possível:** o usuário seleciona cinco pastas, arrasta,
**uma** entra, e nada indica erro. Ele só descobre pelo resultado do trabalho, longe do
gesto. Um teste feito com **uma** pasta passa e não vê nada.

⭐ **Correção que não aposta em nenhum dos dois:** leia os **dois** tipos e **una com
deduplicação**. ⚠️ A dedup não é zelo — o mesmo caminho chega nas duas formas (com e sem
percent-encoding), e sem normalizar antes de comparar a mesma pasta entra duas vezes.

⚠️ E `dataTransfer.files.length` **conta certo** (2), mesmo com o `uri-list` truncado —
serve de conferência: *se `files.length` for maior que o número de caminhos extraídos,
você perdeu algum.*

### ⛔ NÃO dá para saber que é PASTA antes do drop — resultado negativo, medido

Durante `dragenter`/`dragover` o *protected mode* bloqueia o conteúdo, mas `types` e
`dataTransfer.items` (`kind`/`type`) respondem. A pergunta era se `items` distinguiria uma
**pasta** de um **arquivo**, para acender só a zona certa. **Não distingue** — os dois
chegam idênticos:

| arrasto | `items` | o que separa |
|---|---|---|
| pasta `MIDIAS VALENDO` | `[string text/plain, string text/uri-list, file ""]` | — |
| arquivo `PRODA.aaf` | `[string text/plain, string text/uri-list, file ""]` | — |

O `type` do item é `""` nos **dois** (o Windows não registra MIME para `.aaf`, e pasta não
tem MIME). O que os separa — `File.size` **0** contra **10 444 800** — só existe **depois**
do drop, quando o protected mode acaba.

⭐ **A saída de interface, que vale para qualquer painel:** se a plataforma não diz o que
está sendo arrastado, **pergunte ao cursor**. Realce discreto em todas as zonas que
aceitam a espécie (o mapa), e o realce forte só na zona **sob o ponteiro** (a promessa).
O usuário não sabe menos que o programa — sabe **mais**, ele está olhando o que arrastou.
⚠️ Acender todas as zonas com o mesmo destaque transforma o realce em **pergunta** em vez
de resposta.

## 7c. ⚠️⚠️ O arrasto NÃO se automatiza — `confirmado` (2026-08-19)

> 🆕 **Revisto em 2026-10-21 (MC 24.6.0, Windows 11, piloto): para um ALVO NATIVO o arrasto sintético FUNCIONA.**
> Bin do MC → janela do Ciclo Assist (`IDropTarget` próprio, `_CICLO ASSIST/app/src-tauri/src/arrasto_win.rs`): com
> `SendInput` (botão apertado, 5 passos curtos para passar o limiar, 60 passos até o alvo, 0,6 s parado, soltar),
> um MASTERCLIP e uma SEQUENCE chegaram com o MIME do Avid, e o realce acendeu no meio do gesto. **A sequência NÃO
> disparou o export de AAF** (nenhum diálogo no MC). Um arquivo do Explorer, pelo mesmo gesto, chegou com o caminho
> (acento intacto). ⇒ O que não chegava em 08/2026 era o drop da WEBVIEW (QtWebEngine do painel); o laço OLE do Avid
> entrega a um alvo nativo. ⚠️ Clicar no NOME para selecionar abre a edição do nome (Esc cancela): selecione e
> arraste pelo ÍCONE. 25.x não medido.
> O mesmo gesto sintético do **Premiere 23.6** (pasta da bin, selecionada antes com um clique e 1,5 s de espera) chegou
> ao mesmo alvo como `premiere_item`; o dado vem da seleção pela ponte (`premiere-cep/arrastar-e-selecao.md` §6b).

**Fato medido:** arrasto sintético (`mouse_event` do user32) da bin para a webview do painel
**não chega ao `drop`**. Tentado por duas rotas na mesma sessão, com o MC em primeiro plano e o
painel visível:

1. `SetCursorPos` em posições absolutas + `LEFTDOWN` / passos / `LEFTUP`;
2. `mouse_event` com **movimento RELATIVO** (`MOUSEEVENTF_MOVE`, 80 passos de 10 px), que é a
   forma que costuma disparar o `DoDragDrop` do Windows.

Nos dois casos o item é **selecionado** na bin (`Selected: 1` aparece no rodapé) e o `drop` nunca
acontece — o realce do alvo não pisca e o painel não recebe nada.

**Por quê, provavelmente:** o Avid entra num laço modal de OLE drag-and-drop, que consome a fila
de mensagens de um jeito que evento injetado não satisfaz. Não foi investigado além disso — o
custo de insistir passou o valor.

⭐ **A consequência prática é de MÉTODO, e é o que importa registrar:** um painel de Avid **não
tem teste automatizado de ponta a ponta pelo arrasto**. Quem construir um painel deve:

- **testar a camada de baixo por HTTP**, mandando o payload do arrasto direto para a rota — o
  formato está no §2 deste documento, e montá-lo à mão é trivial;
- **guardar o payload real** de um arrasto de verdade (um `console.log` no `drop`) para usar como
  fixture, em vez de inventar um;
- **reservar o arrasto para verificação humana**, e dizer isso em voz alta no relatório em vez de
  deixar parecer que a cadeia inteira foi exercitada.

⚠️ O oposto disso é o modo de falha caro: concluir "o arrasto está quebrado" a partir de um teste
automatizado que **nunca poderia** ter funcionado, e sair caçando defeito num código correto.

## 8. `pendente`

- **`head`** veio `"0"` em tudo e `"12014"` no subclip. Parece o frame inicial; não
  confirmado como contrato.
- **Saída painel → MC** (`DropFromPluginTo*` + `panel-sdk-plugin-asset-list+json`) —
  o contrato existe, nunca exercitado. Entregaria a bin relinkada direto na timeline.
- **Clipe importado por *File ▸ Import*** tem `Source Path`? Decide se a coluna separa
  "AMA × gerenciado" ou apenas "tem arquivo de origem × não tem".
- **Ponte de EVENTOS do QWebChannel após navegar para `http://`** — outro mecanismo; o
  achado do arrasto não diz nada sobre ele.

---

## Fontes

Mecanismo lido no painel do **ESION Studio 25.1.0** (Acclaim Audio, `.avpi` assinado pela
Avid) — ver [esion-arquitetura.md](esion-arquitetura.md). Implementado e exercitado por um
editor no **De Lá Pra Cá** (`_DeLaPraCa`, ADR 0012), **Media Composer 25.6.0.58781 /
Windows 11 23H2, 2026-08-15**, com o painel servido por `http://127.0.0.1:7823`.

Payloads capturados pelo próprio painel e depositados no serviço (`/diag/arrasto`), o que
tornou cada medição consultável em vez de dependente de foto de tela. Espécies mapeadas
num único arrasto misto de seis itens. Catálogo de MIMEs e vocabulário de tipos por
`strings -a` sobre `AvidMediaComposer.exe`.

## 🆕 ⭐⭐ Interceptação NATIVA (Frida em `QMimeData::setData`) — sem painel, qualquer versão — `confirmado` (2026-10-18, MC 24.6.0/Windows)

Pergunta do autor: dá para montar uma sonda que capture o que percorre o arrasto **sem depender de um painel aberto**?
Medido com Frida anexado ao MC (pid, `attach`), hook em `Qt5Core.dll!QMimeData::setData(QString, QByteArray)`
(mangle `?setData@QMimeData@@QEAAXAEBVQString@@AEBVQByteArray@@@Z`), **nenhum painel aberto**, lendo o payload no
instante em que o arrasto é montado. Script: `scratchpad/drag_probe.js` (leitores de QString/QByteArray do Qt5 x64:
QArrayData `size@+4`, `offset@+16`, dado em `d+offset`).

**✅ Clipe / sequence / subclipe — identidade COMPLETA no `QMimeData`, sem painel:**
- `text/x.avid.mc-api-asset-list+json` com MobIDs, `type` e, no subclipe, `in` (medido `4705`/`899`);
- `text/x.avid.asset-list-extended+json` (variante `interplay-pam`, `systemID` vazio);
- `application/x-dnditemdata` (binário; o XML `<mobIDDragObjectList>` do §4).

⇒ **A hipótese está provada:** a identidade do arrasto é construída no INÍCIO do gesto, abaixo da webview, então uma
sonda nativa (Frida) a captura **sem painel aberto e em qualquer versão**. O painel/JS-`drop` é só UM dos destinos;
não é a única superfície que vê os MobIDs. (O hook é no Qt PADRÃO — estável entre versões e SOs, ao contrário de
enganchar o código próprio da Avid.)

**⛔ Bin (painel lateral) e aba — a identidade NÃO entra no `QMimeData`:** o arrasto de bin só setou
`mediacomposer.sidebar.bins.list` com **size 0**; a aba deu `action = "avid-tab-move"`. Confirma, de dentro do
processo, o beco do §4: a identidade da bin fica no `BinContainerModel` (ponteiros de linha), lida pelo handler de
DROP, não serializada no arrasto. **O hook em `setData` não resolve a bin** — resolvê-la exigiria enganchar o
`mimeData()` do modelo / a seleção do `QTreeView` (código Avid, por endereço — frágil entre versões).

**Lição de método:** a medição anterior (pré-REA, 4 canais externos) via só o marcador de 1 byte; o Frida mostrou que
**mesmo no nível nativo o marcador é vazio** — ou seja, não era limitação do canal externo, a bin realmente não põe
identidade no arrasto. Fecha a dúvida "será que de dentro aparece?": não aparece no `QMimeData`.

## 🆕 ⭐⭐ Reorg do painel lateral = operações de ARQUIVO; drop no-op não emite NADA — `confirmado` (2026-10-18, Frida, MC 24.6.0/Windows)

Sonda de disco (Frida, hook de APIs Win32 em kernelbase/kernel32, filtrada à pasta de projetos; `scratchpad/fs_probe.js`).
O editor criou pasta, moveu/renomeou bin, e depois arrastou uma bin para a MESMA pasta (no-op).

**A reorganização do sidebar É o disco** (medido, com os nomes que o editor deixou):
| gesto no sidebar | no disco |
|---|---|
| criar pasta | `CreateDirectoryW(...\untitled folder1)` (nasce "untitled folder1") |
| renomear pasta | `MoveFileExW` do diretório (pegou os passos da digitação: `untitled folder1\`→`...SONA`→`...SONDA`) |
| renomear bin | `MoveFileExW(bin.avb → bin-novonome.avb)` |
| **arrastar bin p/ pasta** | **`MoveFileExW(bin.avb → PASTA\bin.avb)`** + o `.lck` junto |
| persistência | grava `bin_index_data.json`, `bin_background_color.json`, `<projeto> Settings.xml`, `<projeto>.avp`, `Statistics\...` |

⭐ **Consequência de produto:** a organização do projeto é espelhada no disco ⇒ **nosso app externo não precisa de hook nem
de painel: basta VIGIAR a pasta do projeto** (`Avid Projects\<projeto>`) com um file watcher e espelhar a árvore.

⛔⛔ **Mas para ARRASTAR uma bin do sidebar PARA O NOSSO APP, a identidade NÃO está no gesto.** Teste no-op decisivo:
arrastar a bin para a mesma pasta (nada muda no MC) **não gerou nenhum evento** — nem FS, nem (sessão anterior) algo
além de `mediacomposer.sidebar.bins.list` size 0 no `QMimeData`. Ou seja, quando o drop NÃO reorganiza (que é o caso de
soltar no nosso app), **o MC não emite a identidade da bin em lugar nenhum capturável** (nem mime, nem FS). Triângulo
fechado: §4 (OLE externo = 1 byte) + QMimeData (size 0) + FS no-op (zero). A identidade da bin vive só no
`BinContainerModel` em processo.

**Rotas para o produto (arrastar PARA o app):**
1. ✅ **Arrastar CLIPES, não bins** — os MobIDs vão no OLE `IDataObject`/`x-dnditemdata` (lidos por alvo externo nativo,
   §4) e no `mc-api-asset-list+json`. Editor abre a bin, Ctrl+A, arrasta. Resolve a bin por pyavb (MobID→`.avb`).
2. ✅ **App mostra as bins ele mesmo** — como a árvore é o disco, o app lê a pasta do projeto (pyavb) e lista as bins;
   o editor escolhe no app, sem arrastar do MC. Alinhado ao modelo "app por fora".
3. ⚠️ **Frida lendo o `BinContainerModel` no drag** — única forma de extrair a identidade da bin arrastada; código Avid,
   frágil entre versões, pesado em produção. Não recomendado.

**Refresh:** `ReadDirectoryChangesW` NÃO disparou ⇒ o MC não vigia a pasta (refresh é manual, confirmado). O re-scan do
refresh pela raiz não apareceu em `FindFirstFile(W/Ex)` (o *save* já reatualiza a lista gravando `.avp`); o gatilho exato
do refresh manual fica `pendente` (provável `NtQueryDirectoryFile` por handle, não hookado por ruído).
⭐ **Resolvido 2026-11-01** (REA, strings do `AvidMediaComposer.exe` 2024.6): o refresh manual é o item `Refresh` do menu de contexto do painel lateral (`BinContainer.cpp`, `ProjectRefreshCoordinator::requestDirectoryRefreshAsync`) — medido funcionando para bin renomeada/movida por fora (ver `transversal/operacoes.md`).
⭐⭐ **E não há caminho PROGRAMÁTICO para ele no 2024.6** — `confirmado` (2026-11-01, REA: pefile+capstone para os
xrefs, Frida pelo MCP `instrument_with_frida` no MC vivo, PID 29952):
- A cadeia, medida com o controle positivo (o clique no menu): slot do menu **`0x29adc0`** → `0x3fb124` → `0x3fb4b4` →
  **`ProjectWindow::RefreshTable` `0x285e60`** → `0x2b98e4` → `requestDirectoryRefreshAsync` `0x2cae00` (RVAs do
  `AvidMediaComposer.exe` 2024.6, base `0x140000000`). O menu de contexto é montado em `0x2919d8`.
- Sob os mesmos ganchos, **nenhuma** destas chamadas da API passou pelo refresh: `GetBins`, `OpenBin` (bin em pasta e
  na raiz), `CloseBin`, `GetProjectInfo`, `CreateBin` (a bin nasceu e o projeto não foi relido).
- O `DoCommand` (catálogo do 25.12, 724 comandos) não tem refresh de projeto/bins: só de mídia (1040) e de sequência.
- Outros chamadores estáticos do `0x3fb124` (todos de interface): salvar configurações/projeto (`0x3fcb38`, `.avp`,
  `SaveSettings` — o save que também acerta a lista), "Save As" de bin (`0x21d464`), abrir bin pelo diálogo
  (`0x3f1714`), bin de lixo (`0x3df648`), script (`0x125029c`).
- ⇒ Sem a tela, só **chamando o slot por Frida** (precisa do `this` do BinContainer; endereço por versão: frágil, e
  Frida em produção é plano B). O caminho de produto é o gesto (`cicloassist/avid/painel_lateral.py`). ⬜ Medir se o
  MC 25.x mudou isso.

## 🆕 ⭐⭐ Lado do PULL — o formato de bin é TOKEN DE TIPO, não dado (fecha o caso) — `confirmado` (2026-10-18, Frida, MC 24.6.0/Windows)

Hipótese do autor: o Windows usa *delayed rendering* — talvez a identidade da bin só se materialize quando um alvo
VÁLIDO puxa o dado no drop (não no `setData`). Sonda do pull: hook `Qt5Core!QMimeData::data(QString)` (getter, retorno
por ponteiro oculto) + `hasFormat` (`scratchpad/pull_probe.js`). Editor arrastou a bin pela sidebar, pelo composer e
soltou no Explorer.

**Capturado:** só `hasFormat("mediacomposer.sidebar.bins.list")` (×4). **`data()` NUNCA foi chamado** — nem ao soltar
no Explorer. ⇒ o `mediacomposer.sidebar.bins.list` é **token de tipo** (o alvo pergunta "tem formato de bin?" para
aceitar/recusar — é o que libera/trava o ícone de bloqueio), **não um portador de dado**. Ninguém puxa conteúdo: o
Explorer não conhece o formato; o drop interno da sidebar resolve pelo `BinContainerModel`, sem passar pelo `QMimeData`.

**Triângulo + pull = caso 100% fechado:** advertise (`setData` size 0) · accept-check (`hasFormat`, só token) · pull
(§4: quando um alvo nativo externo forçou o `GetData`, veio **1 byte que não identifica**; aqui `data()` nem é chamado).
⇒ **a identidade da bin NÃO é emitida no arrasto, em nenhuma fase.** Um painel/alvo nosso que anuncie aceitar o formato
**libera o bloqueio mas recebe só o marcador** — é o que o autor via no Explorer ("libera, mas nada anexa"). A identidade
vive só no `BinContainerModel` em processo.

**Sliver teórico não testável aqui:** um alvo que ACEITE o formato E chame `data()` poderia disparar o `retrieveData`
virtual (override da Avid) e materializar algo — mas §4 mostra que, materializado, é 1 byte não-identificador. Não vale
perseguir. **Rotas de produto permanecem:** arrastar CLIPES (MobIDs viajam) ou o app LER a pasta do projeto (a árvore é o
disco). Ver seções acima.

## 🆕 ⛔ Soltar timeline do MC numa WEBVIEW comum faz o MC EXPORTAR — `confirmado` (2026-10-18, MC 24.6.0/Windows, autor)

O painel do De Lá Pra Cá numa janela do app (Tauri/WebView2, fora do Avid). Soltar uma sequência da bin na janela fez
o **MC abrir o diálogo modal de export** ("The sequence … contains offline media. Continue exporting or abort?") — que
ainda trava o arrasto no Explorer até ser fechado. Causa: o arrasto anuncia o `.aaf` virtual (`CF_HDROP`, §4 "ZERO
BYTES") por *delayed rendering*; o QtWebEngine do painel nunca o pedia, mas o **WebView2 pede o arquivo no drop**, e
aí o MC gera o export de verdade. A pasta arrastada do Explorer, na mesma webview, chega **sem caminho** (só `File`).
O tratador de arquivos do Tauri/wry também não serve: ele faz `GetData(CF_HDROP)` já no `DragEnter`.

⇒ **Alvo nativo próprio** (`_DeLaPraCa/app/src-tauri/src/arrasto_win.rs`): `SetAllowExternalDrop(false)` no
controller do WebView2 + `RegisterDragDrop` na janela e nas filhas; decide pelo `QueryGetData` (não gera dado), NESTA
ordem: `text/x.avid.mc-api-asset-list+json` (lê SÓ ele) → `mediacomposer.sidebar.bins.list` (bin: avisar) →
`CF_HDROP` (caminhos). Entrega à página por `eval`, sem IPC para a origem HTTP. Os nomes dos formatos OLE são os
próprios MIME (`RegisterClipboardFormatW`). [[arquitetura]]

## 🆕 ⭐⭐ No macOS o arrasto do MC sai DE FORA, sem Frida — o MobID na área de arrasto do sistema — `confirmado` (2026-10-24, MC 25.12.0 arm64, macOS 15.6.1)

- Medido com a sonda `piloto/sondas/arrasto_nativo_mac.swift` (lê o `NSPasteboard` de arrasto a cada 0,1 s) e, ao mesmo
  tempo, Frida (gadget) em `QtCore!QMimeData::setData` (Qt 6). Projeto de laboratório LAB_ARRASTO_MAC, 1 master clip
  linkado (B01_MP4-H264, arrastado do Finder para a bin = link AMA, ✅).
- O que o MC põe (Frida, na ordem): `application/x-dnditemdata` (16 B de cabeçalho, depois o XML) ·
  `text/x.avid.mc-api-asset-list+json` = `[{"head":"0","id":"060a2b34…-034e","systemID":"mc-api","systemType":"mediacomposer","type":"masterclip"}]` ·
  `text/x.avid.asset-list-extended+json` (o mesmo, `interplay-pam`) · o XML `<mobIDDragObjectList local="true"><mobIDDragObject mobID="060a2b34…" keyframe="0"/></mobIDDragObjectList>` ·
  `application/x-qt-mime-type-name` = "dummy".
- O que OUTRO processo lê (sonda): os MIME do Qt viram UTI `com.trolltech.anymime.<mime com "/" → "--">`. O
  `…application--x-dnditemdata` vem COM o XML do MobID (171 B) já durante o gesto, antes do soltar. Os dois JSON aparecem
  só como PROMESSA (`data(forType:)` = nil), também no soltar e com a janela registrada para eles. ⇒ no Mac, o dado do
  arrasto do MC é o **MobID do XML** (e a API gRPC resolve o resto); não precisa de Frida nem de painel.
- ⚠️ A janela de destino só recebe `draggingEntered` se REGISTRAR esses UTIs (`com.trolltech.anymime.application--x-dnditemdata`…);
  sem isso a miniatura passa por cima e nada acontece. A leitura do pasteboard de arrasto não depende do registro.
- ⭐ Diferente do Windows (§7c): no Mac o arrasto SINTÉTICO do piloto (CGEvent: botão, movimento, soltar) saiu da bin do
  MC para outra janela. Agarrar pelo ÍCONE do item.
- ⛔ O MC aberto pelo TERMINAL (`open -a`) herda `LANG=pt_BR.UTF-8` e aborta na abertura (DekoLibrary `k_double`);
  abrir com `env -u LANG -u LC_ALL open -a …` (matriz de plataforma, seção B). Com isso o gadget do Frida
  (`DYLD_INSERT_LIBRARIES`, o MC tem `allow-dyld-environment-variables`) carrega e o MC abre normal.
- **Segmento da TIMELINE do MC (modo Lift/Overwrite, vermelho) → fora: NÃO sai** (2026-10-24, arrasto sintético): o MC
  trata como arrasto interno (seleciona V1/A1/A2 e mostra uma V2 provisória), nada vai ao pasteboard de arrasto e o Frida
  não viu nenhum `setData`; soltar fora não editou nada (Undo continuou "Splice-in"). O dado da timeline do MC vem da
  API (o que está selecionado), não do arrasto. `pendente`: com a mão do autor; modo amarelo; subclipe, sequência, vários itens.
- ✅ **COM A MÃO do autor (2026-10-25, mesmo MC):** segmentos da timeline arrastados para fora, no modo VERMELHO e no
  AMARELO → o MC ESCREVE o pasteboard de arrasto (a sonda viu `…application--x-dnditemdata` com o MobID da
  SEQUÊNCIA inteira, `keyframe="0"`, nada dos segmentos; os JSON só como promessa), mas **nenhuma janela de fora recebe
  `draggingEntered`** — nem a sonda (que registrou "entrou" com o arrasto da BIN), nem a janela do app com o tipo
  registrado (sem realce, sem soltar). ⇒ ⛔ **O arrasto da timeline do MC não chega a outro programa no Mac**: o gesto
  fica dentro do MC. Os segmentos escolhidos saem pela cópia do editor (`copia-da-timeline.md`), não pelo arrasto.
- ✅ **O MobID do XML vem com CHAVES** (`060a2b340101010501010f20-13-00-00-00-{7f39f87f-3349-4b9c-a40a3e706d4b2f3a}`,
  o mesmo mob que a API grafa `060a2b340101010501010f2013-000000-7f39f87f33494b9c-a40a3e706d4b-2f3a`): os 64 hex na
  mesma ordem; validador que só aceita hex e hífen o recusa. E o XML não traz a espécie: ela sai da API, pela bin do
  mob (`GetBinFromMob` + `GetListOfBinItems` por categoria; ~3,7 s para uma sequência). Bin → janela do app pela mão do
  autor: a timeline adotada. Implementação: `_DeLaPraCa/app/src-tauri/src/arrasto_mac.rs` + rota `/arrasto/mc`.
- ✅ **Bin do MC → aba Preparar do Ciclo Assist (2026-11-07, MC 25.12, arrasto sintético do piloto pelo ÍCONE):** um master → `/arrasto/mc` (espécie pela categoria da bin) → `avid_mobs` → a fonte na lista; uma SEQUÊNCIA no Subclipar → `avid_timeline` → 65 tomadas lidas. Porte: `_CICLO ASSIST/app/src-tauri/src/arrasto_mac.rs` + `modulos/sincronizar/servidor/servidor.py::especies_do_arrasto`. ⚠️ Janela com várias webviews: ver a matriz (o soltar chega pelas escondidas). ⛔ Piloto: duplo clique no NOME de uma bin no painel do projeto abre a edição do nome (Esc cancela) — abrir pelo ÍCONE.

## 🆕 ⭐⭐ A seleção da TIMELINE existe num servidor interno do MC: o ARO (AvidRemoteObjects) — `confirmado` (estático, 2026-10-25, MC 25.12.0 Mac arm64)

Pergunta do autor: "se a ação é possível pela interface, a comunicação existe — onde interceptar?". Leitura ESTÁTICA
do `AvidMediaComposer` (225 MB, universal; os símbolos C++ locais NÃO foram removidos: `nm -arch arm64 -C`, 244 683
linhas), sem tocar no MC aberto:
- O arrasto só tem UM formato com identidade: `<mobIDDragObject mobID="%s" keyframe="%d"/>` (MobID + um quadro). Não
  há formato de SEGMENTO; o arrasto de segmento é interno (`SegmentDrag_CBox` é a opção da interface).
- A seleção mora no `TLselectionlist` (`TLselectionlist::IsSegmentSelected`, `FindSelection<TLsegment>`,
  `TLsegment::CopyTo(TLselection*)`, `TimelineWindow::IsSegmentSelected`).
- ⭐ E é EXPOSTA por um servidor de objetos remotos: **591 funções** `Nome(AROincomingInterface*, AROserverInterface*,
  AROoutgoingInterface*)`, registradas por `initARO_<área>` (Timeline, Bin, Monitor, Project, Composer, Effects,
  AudioMixer, Interplay, Qt…). Da timeline (30 `TLW_*`): **`TLW_GetSelComponents`**, **`TLW_GetNumSelComponents`**,
  `TLW_IsSegmentSelected`, `TLW_GetClipInfo`, `TLW_GetTransInfo`, `TLW_GetTracks`, `TLW_GetTrackInfo`,
  `TLW_GetSegmentEditMode`, `TLW_GetTLMode`… — exatamente o que a API pública (gRPC 9100) não dá.
- É a automação de TESTES da própria Avid ("AvidSatin"; fontes `ppg/AvidRemoteObjects/*.c`). Liga por opção de
  inicialização (`-arotcpport`, `-aroclient`, `-arolog`, `-batch`, `-watchdog`, `-project`; `MCinvokeOptions.c`) ou
  pelo arquivo `/Applications/AvidSatin/params/AROStartupOptions.txt`, e então carrega o TRANSPORTE de fora:
  `/Library/Application Support/Avid Internal/AvidRemoteObjects364.dylib` (`dlopen`; símbolos `ARO_VersionNumber`
  — "Version 2014 or greater" —, `ARO_Init`, `ARO_Release`). ⛔ Essa biblioteca NÃO vem no instalador (nem
  `/Applications/AvidSatin`): sem ela o servidor não sobe.
- ⇒ Caminho possível, `pendente`: escrever a NOSSA `AvidRemoteObjects364.dylib` (o MC tem `disable-library-validation`)
  com `ARO_Init` devolvendo um `AROserverInterface` próprio — o MC registra nele as 591 funções, e chamamos
  `TLW_GetSelComponents` com `AROincoming/outgoing` nossos. Exige decifrar o contrato (as vtables das três interfaces,
  pelo `MC_AROserver::Start`/`RegisterClasses`/`initARO_Timeline` e por um `TLW_*` simples), instalar numa pasta do
  sistema (administrador) e abrir o MC com a opção. Medir também no Windows (`AvidRemoteObjects364.dll`?).

### 🆕 O contrato do ARO, lido do binário (2026-10-25, MC 25.12.0 Mac arm64; `lldb --batch` no arquivo, MC intocado)

Método (vale a cada versão nova do MC — é o ROTEIRO DO QUE OLHAR): `lipo -thin arm64` do executável → `nm -arch
arm64 -C` (símbolos locais presentes) → `lldb --batch -o "target create <arm64>" -o "disassemble -n '<função>'"`
(segundos; o MC não precisa estar aberto). Tabelas de dados: ler pelo arquivo (seção `__DATA.__data`, ponteiros em
*chained fixups* — o alvo são os 36 bits de baixo + `0x100000000`). Conferir em cada versão os pontos abaixo:

| ponto | o que o MC faz (25.12.0) |
|---|---|
| ligar | `MCinvokeOptions_t::ConfigureAROonStartup` lê `/Applications/AvidSatin/params/AROStartupOptions.txt` (cada linha = tokens de linha de comando) e depois a linha de comando: `-arotcpport <porta>`, `-aroclient`, `-arolog`, `-batch`, `-watchdog`, `-project` |
| carregar | `MC_AROserver::GetAROServer`: `dlopen("/Library/Application Support/Avid Internal/AvidRemoteObjects364.dylib")` → `ARO_VersionNumber()` tem de ser **> 2013** → `ARO_Init(&ipAROserver)` devolve **0** e grava o objeto servidor → `ARO_Release` guardado |
| subir | `MC_AROserver::Start(porta, flag)`: porta 0 → **12345**; `servidor->vtable[2](porta, 0)` = 0 é sucesso; o objeto tem nos campos `+0x8`/`+0x10` dois ponteiros de `printf` (log, depuração) que o MC pode trocar; depois `RegisterClasses` e um `QTimer` de 10 ms |
| registrar | `initARO_<área>(servidor)` → `servidor->vtable[9](classe, classe_mãe, tabela)`; ex.: `("TimelineWindow", "AWindow", TimelineMethods)`. A tabela = pares `{char* nome, função}` (`TLW_GetTracks`, `TLW_GetTrackInfo`, …, `TLW_GetNumSelComponents`, `TLW_GetSelComponents`) |
| atender | `MC_AROserver::ProcessPendingRequest` (no timer, thread principal): `servidor->vtable[32]()` — é aí que a biblioteca chama a função registrada |
| um comando | `TLW_GetNumSelComponents(in, srv, out)`: `in->vtable[35]()` = o identificador do objeto → `srv->vtable[15](id, &obj)` = o objeto (a `TimelineWindow`) → `in->vtable[38]()` (fim da leitura) → `obj->vtable[0x4f0/8]()` = a contagem → `out->vtable[3](valor, nome=NULL)` → `out->vtable[17]()` (fecha a resposta) |

⇒ O transporte (rede, formato) é de quem escreve a biblioteca. Plano de sonda: uma `AvidRemoteObjects364.dylib` com as
três interfaces feitas de STUBS que registram cada slot chamado (índice e argumentos) — o próprio MC mostra o resto
do contrato ao ser exercitado. Pastas: `/Applications` aceita o usuário admin sem senha; `/Library/Application
Support/Avid Internal` precisa de administrador uma vez.

### 🆕 ⭐⭐ O contrato do ARO CONFIRMADO em execução — a nossa dylib dirigida pelo MC (2026-10-25, MC 25.12.0 Mac arm64, pilotado)

Escrevemos a `AvidRemoteObjects364.dylib` que falta no instalador (`_DeLaPraCa/tools/aro/`, só laboratório) e a pusemos
no caminho fixo. Em DUAS etapas, no projeto de lab, com o MC pilotado:

- **Passo 1 — carregamento:** `ARO_VersionNumber` (devolve 2025, > 2013), `ARO_Init` RECUSANDO de propósito (devolve 1),
  `ARO_Release`. O log provou que o MC carrega a dylib em TODA abertura (o `main` chama `ConfigureAROonStartup`
  SEMPRE → `MC_AROstart(12345)` → `dlopen`), antes da tela de projetos. Recusando, o MC segue normal. ⛔ Não precisa
  do `AROStartupOptions.txt` nem mexer em `/Applications` — o MC já procura a dylib sozinho.
- **Passo 1.5 — servidor-escuta:** `ARO_Init` ACEITA e devolve um objeto `{ vtable, resto[0x400] }` cujo vtable (128
  entradas) são ESCUTAS que só registram índice + argumentos e devolvem 0. O MC DIRIGIU o servidor, confirmando o
  contrato estático inteiro:
  - `vtable[2] Start(porta=12345, flag=0)` → 0 = sucesso; o MC seguiu e **ligou o developer mode** (`CallDef::SetDeveloperMode`): a barra de menus ganhou **"Extensions"** (confirmação visual de ARO ativo).
  - `vtable[9] RegisterClass(nome, mãe, métodos)` chamado uma vez por classe, com os nomes: `SelectProject`,
    `BinContainerWindow`, `AApplication`, `AWindow`, `APane`, `AComponent`(mãe `AObject`), `ATrackGroup`,
    `AComposition`, `BinWindow`, `ProjectWindow`, **`TimelineWindow`**(mãe `AWindow`), `ComposerWindow`, `MonWindow`,
    `AudioMixerWindow`, `MediaComposerApp`… ⭐ o ponteiro de métodos da `TimelineWindow` em execução (`0x1096ef838`)
    MENOS o slide de ASLR (`0x4ee8000`) = **`0x104807838`** — EXATAMENTE o `TimelineMethods` lido no arquivo. O mapa
    estático bate com o runtime, byte a byte.
  - Outros slots vistos no registro: `[4]`, `[8]`, `[10]`, `[12]`, `[13]`, `[17]`.
  - `vtable[32] ProcessPendingRequest` (o pulso do QTimer de 10 ms) NÃO disparou na tela de projetos ociosa: o
    `MC_AROserver::ProcessPendingRequest` só chama o slot do servidor quando `theBusiness == 0` E `StatIsActive() == 0`
    (desmontagem) — é o gatilho a resolver no passo 2 (o transporte real).
  - O MC ficou ESTÁVEL o tempo todo (não caiu); devolver 0 de todos os slots segurou o registro inteiro.
- **Higiene:** terminado o teste, a dylib é REMOVIDA do caminho do sistema (o MC volta ao normal); reinstalar =
  `tools/aro/compilar.sh`. A pasta `/Library/Application Support/Avid Internal` (criada com senha uma vez) fica vazia.

⇒ Falta o **passo 2** (sessão própria): implementar as três interfaces que uma função registrada recebe
(`AROincoming`/`AROserver`/`AROoutgoing` — as vtables lidas em `TLW_GetSelComponents`) e um transporte, para de fato
chamar `TLW_GetNumSelComponents`/`TLW_GetSelComponents` e ler a seleção. O gatilho do `ProcessPendingRequest` é o
primeiro nó a destravar. ✅ FEITO — ver a seção seguinte.

### 🆕 ⭐⭐ PASSO 2 PROVADO: a seleção da timeline lida por dentro, chamando as funções do MC (2026-10-25, MC 25.12.0 Mac arm64, pilotado)

A dylib `_DeLaPraCa/tools/aro/aro_servidor.c` (só laboratório) implementa as três interfaces e CHAMA as funções do MC
direto, **na thread principal**, sem o `ProcessPendingRequest`. Rodou de ponta a ponta no projeto de lab (seleção na
timeline PRODC_CORTE02). Pessoa U:

- ⭐ **O nó do passo 1.5 (ProcessPendingRequest) é contornável.** A dylib sobe um socket TCP (`127.0.0.1:17890`) num
  thread próprio e DESPACHA o trabalho para a main com `dispatch_async_f(dispatch_get_main_queue(), …)` + semáforo. O
  comando `PING` voltou `main=1`: **o runloop do Qt do MC bomba a fila principal do libdispatch** — o bloco executa na
  main. ⇒ não precisamos do servidor "de verdade" do ARO; só de `ARO_Init` ACEITAR (o MC chama `Start`+`RegisterClass`,
  e capturamos as tabelas de métodos de cada classe — 47 classes).
- ⭐ **Resolução das funções POR NOME** (robusto entre versões): no `RegisterClass(nome, mãe, metodos)` guardamos
  `(classe → tabela)`; a tabela é pares `{const char* nome, void* fn}` terminados em `{0,0}`, **nome SEM prefixo**
  (`"GetSelComponents"`, `"GetNumSelComponents"`, `"GetName"`…). `MCapp_Timeline` NÃO está como `"Timeline"` na tabela
  do `MediaComposerApp` (caiu no fallback vmaddr+slide) — o método tem outro nome ali (a confirmar); as `TimelineWindow.*`
  e `AComponent.*` todas resolveram por nome.
- **O encadeamento confirmado em execução:** `MCapp_Timeline` → objectID da `TimelineWindow`; `TLW_GetNumSelComponents`
  (obj->vt[158]) → a contagem; `TLW_GetSelComponents` (obj->vt[157](i,0)) → os `AComponent*` selecionados;
  `AComponent_GetName/GetType/IsSegment/IsTrackGroup/GetLength/GetParent` por componente. Os slots das 3 interfaces,
  byte a byte como lidos no binário: `in[35]=GetAlvoID` `in[38]=FimLeitura`; `srv[2]=Start` `[9]=RegisterClass`
  `[14]=RegisterObject(classe,obj,&id)` `[15]=LookupObject(id,&obj)`; `out[2]=AddBool` `[3]=AddInt` `[11]=AddString`
  (**`const char*` UTF-8** — confirmado) `[13]=AddObjectID` `[14]=AddEnum(tabela,val)` `[17]=Finish` `[20]=AddError`.
- ⚠️ **Robustez obrigatória (aprendido quebrando o MC 2×):** (a) componente selecionado pode vir **NULO** de
  `GetSelComponents` — chamar `GetName` nele faz `ldr x8,[0]` = **segfault em 0x0** (o MC o captura e mostra
  "Segmentation fault in thread MainThread", e cai). ⇒ guardar `map[cid]!=NULL` antes de usar. (b) Envolver cada
  chamada ARO num captador de `SIGSEGV`/`SIGBUS` (`sigsetjmp`/`siglongjmp`, sobrepondo o handler da Avid só na janela da
  chamada) transforma a falha em dado, sem derrubar o MC — e o log é gravado/descarregado ANTES de cada chamada.
  (c) O socket precisa de **retry no `bind`** (+ `SO_REUSEPORT`): depois de um crash do MC a porta fica em TIME_WAIT.
- ⭐⭐⭐ **A IDENTIDADE (pergunta #1) — EXPLORADA A FUNDO; o ARO NÃO entrega a fonte do clipe por caminho direto.**
  Medido em execução (MC 25.12, lab), com o comando `SELECTION`/`PROBE`/`TLP` da dylib:
  - `AComponent_GetName` do segmento vem **VAZIO** (vídeo E áudio). `GetParent` sobe `segmento → conteúdo-da-trilha →
    a SEQUÊNCIA` (track group, `tg=1`, `GetName="PRODC_CORTE02"`), e acima é NULO. A lista `AComponent_*` não tem
    `GetSourceMob`/`GetMobID`. `AComponent_GetLength` dá a duração em frames (ex. `len=35`); `GetType`=tipo da trilha.
  - `AComposition_GetMobProperty` **exige argumentos** (lê `in[2]()`=quantas chaves e `in[15](i)`=o código da i-ésima;
    cada valor volta por `out[11] AddString`, rótulo "val"). Varrendo as chaves 0..63 na SEQUÊNCIA (um CompositionMob,
    `GetMobType`=1), saem as COLUNAS DO BIN do mob — **1**=`"V1-6 A1-14 TC1"` (config de trilhas), **2**=`"01:00:00:00"`
    (start TC), **3**=end TC, **4**=duração, **9/10**=`"23.98"` (fps), **12**=data de criação, **54**=data de mod,
    **62**=`"NORM"`. **NÃO há nome nem MobID** entre 0..63. No SEGMENTO, `GetMobType`=6 mas `GetMobProperty` **FALHA**
    (SIGSEGV capturado — o segmento não tem os slots do protocolo de propriedades).
  - `TLW_GetTracks` resolve e roda, mas **não devolve trilha nenhuma** (a iteração `tl->vtable[203](tl,source,1)`
    voltou 0; lê o arg "source" por `in[14]`). `TLW_GetTrackInfo` dá status da trilha (patch/enable/monitor), não segmentos.
  - ⛔ `TLP_GetAllLines` (que tem o arg **"SelectedItemsOnly"** e despeja o TEXTO das linhas por `out[11]`) **DERRUBA o
    MC** quando chamado pela nossa dylib — e a captura de SIGSEGV **não segura** (é exceção C++ do `GetThisTLP`, chamado
    fora do dispatch real do ARO, que vira `abort` atravessando nossos frames C). Lição: **funções que dependem do
    contexto do dispatcher do ARO (GetThisTLP etc.) não são chamáveis "por dentro" com in/srv/out sintéticos**; as
    `TLW_*`/`AComponent_*`/`AComposition_*` são, porque só usam as três interfaces + o app global.
  ⇒ As funções ARO não davam a identidade — mas a REA achou o caminho DIRETO (abaixo).

### 🆕 ⭐⭐ IDENTIDADE pelo `AComposition::GetMobID()` — PROMISSOR mas o formato NÃO casa com a API (CORRIGE 2026-10-25)

> **CORRIGE (2026-10-25, tarde 3):** a seção abaixo dizia "IDENTIDADE RESOLVIDA". O e2e (ARO × API gRPC) mostrou que
> **ainda não casa** — ver o bloco "⚠️ O que o e2e revelou" no fim. O mecanismo e o `GetMobID`-na-COMPOSIÇÃO estão
> certos; o MobID por SEGMENTO ainda precisa de uma passada de RE (frame + endianness). Mantido o texto original abaixo
> com a correção ao lado.

O `AComponent` que o `GetSelComponents` devolve **responde aos slots de `AComposition`** (o `GetMobType` já funcionava).
E o binário do MC importa `AComposition::GetMobID() const` de um framework (símbolo `U`
`__ZNK12AComposition8GetMobIDEv`). Como a dylib roda DENTRO do processo, resolvemos por **`dlsym(RTLD_DEFAULT, nome)`**
(o nome sem o underscore que o macOS adiciona) e chamamos direto no ponteiro do segmento — **o match-frame por dentro,
sem UI**. Medido (pilotado, lab), **estável e único por clipe, MC vivo**:
- A3 FAIXA-R.wav → material `97a79e0e5ccede18f70f40dad8c0d110`; A1 LOU_7237 → `1f91962f3a61d05b1e3d95b7a6c4910c`;
  A1 LOCAL-3/001 → `95ad3d06925ba0eab744d3cd573e89d4`. O MESMO clipe selecionado 2× deu o MESMO MobID.
- ⚠️ **Formato/ABI:** a função devolve `_aafMCMobID_t` por valor; a captura de 32 bytes saiu **deslocada de 8 bytes** (o
  prefixo SMPTE fixo `060a2b3401010101` fica de fora). O **MobID padrão de 32 bytes = `"060a2b3401010101"` + os
  primeiros 48 hex da captura** → ex. FAIXA-R = `060a2b340101010101010f00 13 000000 97a79e0e5ccede18f70f40dad8c0d110`
  (label SMPTE AAF + length 0x13 + instância + material). Isso é o que `motor/aaf/remap.py::api_para_urn` já consome
  (espera 64 hex da API do MC → `urn:smpte:umid:…`), e `_chave` normaliza p/ comparar com o `.avb`. ⏭️ Confirmar na
  integração que o byte-order casa com o MobID que a API gRPC do MC entrega para o MESMO clipe.
- ⛔ `CMGetMatchFrameSource(AComponent*, _aafMCMobID_t*, int*, AComposition**)` (também em framework, `U`) resolve e
  roda (segv-seguro), mas devolveu um MobID **default** (material zerado), `comp=NULL`, `pos=0`, `ret=0` — não serve
  nesta forma de chamada (talvez precise de posição/contexto). O caminho bom é o `GetMobID` acima.
- O áudio dá 1 componente **nulo** a mais por seleção (par estéreo); o vídeo é limpo.

#### ⚠️ O que o e2e REVELOU (2026-10-25, tarde 3) — o formato ainda não casa com a API

Integração feita (dylib comando `SELMOB`; app `plugins/media-composer/servico/aro.py` + rota `/mc/selecao-aro`; teste
`tests/test_aro.py` 11/11). O e2e (dylib viva × API gRPC, `.venv`) comparou o MobID da SEQUÊNCIA pelos dois lados e
**NÃO bateram** — dois problemas distintos:

1. **Enquadramento inconsistente do `GetMobID`:** na **COMPOSIÇÃO** (a sequência) a captura vem CERTA, começando em
   `060a2b34…` (label SMPTE completo). No **SEGMENTO** vem **deslocada 8 bytes** (começa no meio do label) — porque
   `AComposition::GetMobID` é de `AComposition` e o segmento NÃO é uma; chamada no ponteiro do segmento ela lê campos
   desalinhados. Consistente e única por clipe (por isso pareceu "resolvido"), mas não é o MobID canônico direto.
   ⇒ a reconstrução "prefixo fixo + 48 hex" vale para o segmento mas **double-prefixa a composição**.
2. **Endianness do material ≠ API.** Rosetta Stone (a sequência PRODC_CORTE02):
   - API gRPC (`sequencia_no_record`): `060a2b34 01010105 01010f20 13000000 7f39f87f 33494b9c a40a3e70 6d4b2f3a`
   - ARO `GetMobID` (cru): `060a2b34 01010105 01010f20 13000000 7ff8397f 49339c4b …`
   - Label+length+instância (bytes 0–15) IGUAIS; o **material** difere: Data1(4b), Data2(2b), Data3(2b) com os bytes
     REVERTIDOS (interno GUID little-endian × externo SMPTE big-endian da API), Data4(8b) igual. É a "endianness mista"
     que `aaf/remap.py::api_para_urn` e `mcapi.py::mob_id_para_pyavb` já tratam — mas o MobID do ARO entra na ordem
     ERRADA. `_hexa(ARO) != _hexa(API)` → o `relink.filtrar_masters` não casaria.

⇒ **FALTA (uma passada de RE, próxima sessão):** (a) achar o caminho CORRETO do SEGMENTO até o MobID da fonte — ou a
`AComposition` de origem (via `CMGetMatchFrameSource` usado certo, ou navegando) e `GetMobID` NELA (composição = frame
certo); ou confirmar que o segmento é só offset-8 e desdeslocar; (b) aplicar a conversão de endianness (reverter
Data1/2/3) p/ a ordem externa da API — de preferência deixando o **pyavb** converter (montar a URN e `MobID(...)`),
como o resto do app. A sequência serve de teste (ARO deve igualar `sequencia_no_record`). SÓ DEPOIS a rota
`/mc/selecao-aro` devolve MobIDs que casam com o relink. (SELECTION — a contagem e os componentes — já está correto.)

⇒ Passo 2: SELECTION ok; o MobID da fonte por segmento é o que falta fechar. Dylib presente → esse caminho; ausente →
Cmd+C (Caminho A). Depois, multiversão.

#### ✅ IDENTIDADE pelo `GetSrcMobID` — FECHADA e VERIFICADA (2026-10-25, tarde 3)

Os dois problemas que o e2e apontou foram resolvidos, e **verificados contra duas fontes independentes antes de afirmar**:

- **O método certo para o SEGMENTO:** não é `GetMobID` (esse é de `AComposition`, e o segmento não é uma → lia
  deslocado). É **`ASourceClip::GetSrcMobID`** (`libameLibrary.dylib` `__ZN11ASourceClip11GetSrcMobIDEv`, resolvida por
  `dlsym`): o desmonte mostra que lê **32 bytes do campo `this+0x74`** — o MobID da FONTE do source clip, no frame
  certo. (Também há `GetSrcPosition` = `this+0x98`, `GetSrcTrack`, `GetSrcRef`.) `CMGetMatchFrameSource` é um beco:
  só lê um atributo `"_MATCH"` do componente (via `CMGetMCMobRefAttrList`), que clipe normal não tem → devolve `NullMobID`.
- **A endianness:** o MobID vem na ORDEM INTERNA do MC, que é **exatamente o `bytes_le` do pyavb**. Logo a conversão é
  `str(pyavb.MobID(bytes_le=<32 bytes crus>))` → a URN externa — sem trocar byte à mão. A dylib emite o MobID CRU (valida
  só o label `060a2b34` + material não-zero); `servico/aro.py::_para_urn` converte.
- **Verificação (pilotado, lab):** (1) o MobID da SEQUÊNCIA pelo ARO, convertido, é **idêntico** (`_hexa`) ao de
  `mc.sequencia_no_record()` da API gRPC. (2) o master de um clipe (FAIXA-R) pelo ARO é **IGUAL** ao do **Caminho A**
  (`coleta.capturar` → `.avb`, o caminho já provado) para a MESMA seleção: `{…0e9ea797ce5c18de…}` dos dois lados. (3)
  4 clipes (áudio/vídeo/título) → 4 MobIDs distintos e válidos; o título, que o `GetMobID` zerava, o `GetSrcMobID` resolve.

⇒ **Integração FEITA e PRODUTIZADA (2026-10-25):** dylib comando `SELMOB` (SEQ + MOB cru por segmento), app
`servico/aro.py` (`ler_selecao`/`disponivel`, conversão pyavb), rota `/mc/selecao-aro`, botão do painel
(`painel.js::carregarSelecaoDaTimeline` tenta o ARO e cai no Cmd+C), instalação pelo app (`integracoes.py`
`instalar_aro`/`remover_aro`, cria a pasta do sistema com admin uma vez, compila do `.c` ou usa a pronta do pacote;
nas Configurações; `montar_motor.py` compila a dylib pro pacote no mac arm64). Suíte 99/99.

- ⭐⭐ **Padrão de segurança reutilizável — AUTO-TESTE da injeção contra a API.** Como o `GetSrcMobID` lê um offset FIXO
  (`this+0x74`) que pode mudar entre versões do MC, a rota `/mc/selecao-aro`, a CADA chamada, confere o MobID da
  SEQUÊNCIA pelo ARO contra o `sequencia_no_record` da API gRPC. Se não casar (versão não medida, outra situação), RECUSA
  e o painel cai no Cmd+C. Assim uma dylib específica de versão **nunca relinka errado em silêncio** — e a produtização
  não precisa travar numa versão cravada. (Serve para qualquer injeção que dependa de offset/layout.)

### 🆕 A seleção do ARO LÊ CROSS-TRACK certo — o "só V1" era o MÉTODO de seleção (2026-10-26, MC 25.12.0 Mac, medido ao vivo)
**CORRIGE (2026-10-26, mesma sessão):** o que eu havia escrito abaixo ("a seleção é POR TRILHA / é bug / precisa RE")
estava ERRADO — veio de uma medição ruim. O autor relatou "Carregar a seleção só reconhece a V1". A causa é o Avid: no
**modo segmento um clique DESELECIONA o anterior** — para pegar segmentos em várias trilhas é **LAÇO** (ou Shift+clique).
As primeiras medições ("1 V1 + 1 V2 → NUMSEL 1") foram CLIQUES SOLTOS (só o último valeu). Com um **LAÇO** cruzando V1 e
V2 (+ um filler que o laço pega): **`NUMSEL 3`**, e o `SELMOB` emitiu `SEQ` + **2 MOB** (V1 e V2) + `COUNT 2`
(descartando o filler, que não tem master). `aro.ler_selecao` devolveu os 2 masters + a sequência. ⇒ **NÃO é bug; não
precisa de RE.** A RE abaixo continua VÁLIDA como mecanismo, só a CONCLUSÃO muda: `this->0x170` é o **painel do lado
record (TODAS as trilhas)** e `->0x480` a lista de seleção dele (cross-track) — não "um painel por trilha".
- ⚠️ **Filler na seleção:** o laço do Avid seleciona filler junto (característica do Avid). A dylib já descarta
  (`emite_mobid` exige label SMPTE + material ≠ 0). Amostra: PRODA_CORTE, laço V1+V2+filler → 2 masters.
- ⚠️ **Bug menor real:** DOIS `SELMOB` colados (back-to-back no mesmo instante) → o 2º volta VAZIO. Benigno no uso
  normal (1 por clique). Endurecer se algum dia o painel chamar em rajada.
  ✅ **NÃO REPRODUZ MAIS (2026-10-28, tarde, MC 25.12, dylib revisada + VisitLinks):** laço V2→A2 no PRODC_CORTE02,
  5 `SELMOB` em sequência sem pausa + 5 em threads simultâneas (conexões separadas) → 10/10 iguais (`SEQ` + 13 `MOB`,
  `COUNT 13`). O servidor atende uma conexão por vez e cada `SELMOB` zera o `g_objn`; a causa provável era o laço de
  coleta antigo (o off-by-one do `GetSelComponents`), trocado pelo `GetSelComponent(1..N)`. Fechado.
- **`AvidIdentityHandler` "encerrou inesperadamente" (macOS, 2026-10-28) — NÃO é nosso.** Auxiliar da Avid (Intel,
  roda pelo Rosetta; `SupportingFiles/AvidIdentityHandler`), assinado e válido (`codesign --verify` OK, Developer ID
  Avid 4UYUA773XD). O relatório diz `SIGKILL (Code Signature Invalid)`, mas o `termination` mostra **morto pelo próprio
  MC** (`byProc: AvidMediaComposer`) ~5 ms depois de nascer — o rótulo de "assinatura" é do Rosetta quando o processo
  morre antes de validar. Aconteceu UMA vez (10:24:59, 2 s depois do MC abrir); nas aberturas de 11:08, 11:20 e 14:56
  (MC + projeto) o auxiliar nem foi chamado. A janela fica aberta porque é o **Relatório de Problemas do macOS**, que
  espera o OK — não é do MC nem do app. A dylib do ARO vive no MC, não no auxiliar.
- 💡 UX: o painel pode dar uma dica "para várias trilhas, use o laço" (o clique solto deseleciona) — opcional.

#### ⛔🆕 BUG REAL: off-by-one na MULTI-seleção — `GetSelComponent` é 1-based (2026-10-26, RE confirmada)
Depois de resolver o "método de seleção", o autor viu um **off-by-one**: seleciona 4 → conta 3; 5 → 4; 2 na mesma
trilha → 1 (sempre um a MENOS na multi-seleção; com 1 só, certo). Causa, pela RE de `TimelineWindow::GetSelComponent(short i, int*)`
(0x101e51be8): é **1-based**. Para `i≥1` anda na lista `(this->0x170)->0x480` e devolve o i-ésimo. Para `i=0` cai num
ramo especial (`(this->0x170)->0x480->vtable[0x458/8=139]()`; depois `field_0x8 (count) == 1 ?`) que **só devolve o
item quando há EXATAMENTE 1 selecionado** — senão **NULO**. O laço interno de `TLW_GetSelComponents` chama `i=0..N-1`:
com N>1, `i=0`→NULO (descartado), `i=1..N-1`→componentes ⇒ **N-1 válidos, perde o último**. (O `cid=2` que saía com
`g_objmap` NULO nas medições ERA esse índice 0.) ⛔ **O próprio wrapper ARO do MC (`TLW_GetSelComponents`) tem o
off-by-one** para multi-seleção. ✅ CONSERTO: a dylib chama `TimelineWindow::GetSelComponent(tlwin, i, NULL)` **direto**
para `i=1..N` (bypass do laço furado), N de `GetNumSelComponents` (0x101e51e28). Símbolos são `t` (locais) → usar
`vmaddr+slide` (como os `VM_` atuais) e proteger pelo auto-teste.

✅ **FEITO E VERIFICADO (2026-10-26, MC 25.12.0.58863 arm64, pilotado).** `tools/aro/aro_servidor.c`:
`coletar_selecionados(idtl, cids, max)` chama `GetSelComponent(tlwin, i, NULL)` DIRETO (vmaddr `0x101e51be8`+slide,
protegido por `protegido_gsc`/SIGSEGV), **i=1 até dar nulo**, registrando cada um — usado no `SELMOB` e no `SELECTION`.
Medido ao vivo (seleção de laço de 3 segmentos): **NUMSEL=3, coletados=3** (antes: `COMP 0`/cid=2 saía `(ptr NULO)` →
2); `aro.ler_selecao` → `clipes:3` (2 masters únicos, o resto dedup). O `i=1..até-nulo` lida de graça com o filtro de
classe (filler/transição) — não precisou medir cada caso: para quando não há mais componente casado. Dylib instalada
pelo app (`instalar_aro` recompila do `.c`). ⚠️ `fazer_src`/`fazer_probe` (debug, não usados pelo app) ainda têm o
padrão antigo — irrelevante. O LAB dedicado de seleção não foi preciso; se um dia houver dúvida de estéreo/transição,
a sonda `SELECTION` já mostra `ncomp` (direto) × `NUMSEL` (cru).

#### (histórico, CORRIGIDO acima) RE do mecanismo de seleção — válido, só a conclusão "por trilha" era errada

**🔬 RE do binário do MC (2026-10-26, `AvidMediaComposer` 25.12 arm64, símbolos presentes, `objdump`; Ghidra estourou
o tempo no binário de 116 MB — usar `objdump`/`nm -C` em funções por endereço):**
- `TLW_GetSelComponents` (0x101eb21c8) faz o laço certo: `obj->vtable[0x4f0/8=158]()` = contagem, e por i
  `obj->vtable[0x4e8/8=157](i, 0)` = o i-ésimo. ⭐ O `(i, 0)` NÃO é trilha: o método real é
  `TimelineWindow::GetSelComponent(short i, int* out)` e o `0` é o `int* out` NULO.
- `TimelineWindow::GetNumSelComponents()` (0x101e51e28) devolve `(this->0x170)->0x480 -> campo u16 0x8` (0 quando
  `((this->0x170)->0x480)->vtable[0x5d0/8=186]()` é verdadeiro). `GetSelComponent` (0x101e51be8) itera ESSA MESMA lista
  `(this->0x170)->0x480` por um iterador `vtable[0x238/8=71]`, filtrando por classe (`vtable[4]`=IsInstanceOf). Logo
  `this->0x170` é o **painel de trilha ATIVO** e `->0x480` a lista de seleção DELE — a seleção é **por painel**. (A
  seleção mora num `TLselectionlist`; classes `TLselection::GetComposition/GetTrackGroup/GetTrackLabel` dão a trilha.)
- `TLW_GetTracks` (0x101eb1408) devolve **rótulos** (`AROaddTrackLabel`), iterando `obj->vtable[0x658/8=203](source,1)`
  + iterador `vtable[71]`/`[72]` — não objetos de seleção; veio vazio pra nós (a interface `out` não trata o rótulo).
- ⭐ `AComposition::GetMobProperty` na composição dá o LAYOUT em texto: `str[1]="V1-3 A1-16 TC1-8 EC1"`, start TC,
  duração, fps.
- ⏭️ FALTA p/ o conserto: achar como enumerar TODOS os painéis a partir da `TimelineWindow` (candidato:
  `TimelineWindow::DeepestSelectedLevel()` 0x101e537a8, `GetSelEditTotals`, ou o campo lista-de-painéis perto de
  `0x170`), depois ler o `->0x480` de cada painel com o mesmo iterador. Novo comando na dylib → recompilar + reabrir o
  MC + reselecionar p/ testar. O AUTO-TESTE (SEQ do ARO == gRPC) já protege offsets por versão.

⏭️ Falta a **multiversão** (próxima sessão): MC 2021/24.6, **Windows** (`AvidRemoteObjects364.dll`?), **Intel** x86_64 —
medir os offsets/símbolos por versão; resolver por nome onde der. ⚠️ CORREÇÃO DE RUMO registrada: eu havia dito
"resolvido" com o `GetMobID`-no-segmento (errado) antes do e2e — agora é o `GetSrcMobID`, verificado por dois lados.
- ⚠️ **Limite da captura de falha:** o `sigsetjmp`/`SIGSEGV` segura null-deref (ex. `GetMobProperty` no segmento), mas
  **não** segura exceção C++/`abort` (ex. `TLP_GetAllLines`). Experimento que chama função de contexto-do-dispatcher = pode
  derrubar o MC mesmo com a captura.
- Estado: dylib compila limpo (`-Wall -Wextra`); comandos `PING`/`SELECTION`/`PROBE`/`TLP` em `tools/aro/aro_servidor.c`;
  commits do app em `tools/aro/`. Removida do sistema ao fim (MC normal).

### 🆕 ⭐ Revisão e pentest da dylib do ARO (2026-10-28, MC 25.12.0 Mac arm64) — `confirmado` (medido) / conserto `pendente` de prova ao vivo

- ⛔ **O socket da dylib VAZAVA para os filhos do MC.** Sem `FD_CLOEXEC`, o `avid-api-gateway` (que o MC abre com
  fork+exec) herdou a escuta `127.0.0.1:17890` e o log; o MC fechou, o gateway ficou órfão (pai = 1) e segurou a porta
  por 2 dias SEM aceitar — `PING` ficava sem resposta até o prazo. Visto com `lsof -a -p <gateway> -d 0-20` (fd 7 = log,
  fd 8 = a escuta) e `vmmap` (a dylib NÃO está carregada no gateway: é só herança). Regra geral na matriz, seção D.
- ⛔ **`SO_REUSEPORT` abria o canal para sequestro:** no macOS o ÚLTIMO a abrir a porta leva TODAS as conexões (medido
  6/6 com um 2º ouvinte de teste). Um programa local entregaria MobIDs falsos ao relink. Tirado (o `SO_REUSEADDR` basta).
- ⚠️ **O tratador de `SIGSEGV` é do PROCESSO, o `g_jb` é da pilha da MAIN:** uma falha de outra thread do MC dentro da
  janela pularia para a pilha errada. Agora só a main pula; as outras devolvem o tratador da Avid.
- ⚠️ **Endereços fixos só no build medido:** o log mostra `MediaComposerApp.Timeline -> (vmaddr+slide)` — o "por nome"
  NÃO acha o `Timeline`, e o `GetSelComponent` só tem vmaddr. Noutro build a dylib chamaria código qualquer ANTES do
  auto-teste do Python. Agora `build_medido()` (`CFBundleShortVersionString == "25.12.0.58863"`) libera os vmaddr; fora
  dele o comando dá ERR e o painel cai no Cmd+C. Multiversão = um mapa por build.
- ⚠️ **A pasta `/Library/Application Support/Avid Internal` fica com DONO = o usuário** (o `_garantir_pasta_aro` faz
  `chown` para instalar sem senha). Ela é de TODOS os usuários e o MC carrega dali sem validar assinatura
  (`disable-library-validation`): qualquer programa do usuário pode plantar código que roda dentro do MC — e no MC de
  outro usuário do mesmo Mac. Decisão do autor pendente (instalar como root a cada vez = senha por instalação).
- ✅ **PROVADO AO VIVO (2026-10-28, MC 25.12.0.58863, LAB_ARRASTO_MAC, pilotado):** quem escuta a 17890 é o MC; o
  gateway novo NÃO herdou a porta nem o log (`lsof`); `PING` → `main=1 classes=47`; `TLP` → recusado sem `ARO_LAB`; o
  log diz `build do MC "25.12.0.58863" == o medido`.
- ⛔ **NOVO DEFEITO MEDIDO: segmento COM EFEITO não dá nada no `SELMOB`** (`COUNT 0`, sem `SEQ`). O `SELECTION` mostra
  o selecionado com `tg=1` (um efeito é um GRUPO DE TRILHAS para o MC: Resize do PRODC vindo do Premiere), pai `tg=0`
  (a trilha), avô `tg=1 type=0 name="PRODC_CORTE02"` (a sequência). Duas causas: (1) a subida para achar a SEQ para no
  PRIMEIRO `tg=1` — que é o próprio efeito; o certo é o ÚLTIMO `tg=1` antes do pai nulo (ou `type=0`); (2) o
  `GetSrcMobID` só vale num `ASourceClip`: no efeito, falta DESCER até o clipe de origem (RE nova — filhos do
  `AComponent`/trilha de entrada do efeito). Três `SELMOB` seguidos deram o MESMO resultado: não é o "2º vazio".
- ✅ **(1) CONSERTADO e PROVADO (2026-10-28, ao vivo):** a SEQ = o grupo com `type=0` (não o 1º `tg=1`). Laço com
  Option de V2 até A1 (`NUMSEL 15`: 6 vídeos com efeito, 3 sem, 6 áudios) → `SEQ` + 5 `MOB` (todos MERMAID-C2/002, os
  "ME" da A1 — conferido no `.avb`), igual em dois `SELMOB` seguidos; pela rota `/mc/selecao-aro`: `validado: true`, a
  SEQ igual à da API gRPC (PRODC_CORTE02). ⏳ (2) — o master DENTRO do efeito — continua: os 6 vídeos com efeito não
  dão master.
- ✅ **A1 provado no cenário real:** ao fechar o MC (Cmd+Q → "Leave"), o `avid-api-gateway` FICA vivo (comportamento
  da Avid: órfão é normal), mas a 17890 ficou LIVRE — antes era esse órfão que a segurava.
- ✅⭐ **(2) O MASTER DENTRO DO EFEITO — RESOLVIDO e PROVADO (2026-10-28, MC 25.12.0 arm64, ao vivo):**
  `AComponent::VisitLinks(unsigned char (*cb)(void*, unsigned char, ASourceClip*), void* ctx)` — EXPORTADO
  (`_ZN10AComponent10VisitLinksEPFhPvhP11ASourceClipES0_`, `dlsym`, sem endereço fixo). Desmontado: carrega o virtual
  `vtable[0x4b0]` e chama `(this, cb, ctx, nível=0, modo=2)`; o modo 2 = só os LINKS (`ASourceClip`), o 1 (`VisitComps`)
  = todos os componentes. O `VisitComps1` base mostra o contrato do callback: `cb(ctx, nível, comp)`; **devolver 0
  CONTINUA, ≠0 PARA**. Desce pelas trilhas de entrada dos efeitos, EMPILHADOS inclusive. Prova: laço V2+V1 na
  PRODC_CORTE02 (segmentos com 1, 2 e 3 efeitos empilhados) → 8 segmentos, cada um 1 link → os 5 masters IGUAIS ao
  gabarito tirado do `.avb` pelo pyavb (JUL_7644 e LOU_7231 com 3 efeitos, LOU_7217 com 2); `/mc/selecao-aro`
  `validado: true`. ✅ **VÁRIAS FONTES num segmento — o COLLAPSE (medido 2026-10-28):** no Avid o único segmento com
  várias fontes dentro é o Collapse (o dissolve é um componente ENTRE segmentos, e PIP/chaves pegam o fundo de OUTRO
  segmento — o laço já os entrega simples). Um Collapse de V1+V2 (DoCommand 6251) com 8 clipes de 1 a 3 efeitos
  empilhados → `NUMSEL 2` (o Collapse `tg=1` + o vazio da V2) → `links=8 masters=8` = os 5 masters do gabarito.
  Desfeito pelo Undo. Título sem fonte = 0 links. Vale para os outros apps que leem a seleção do MC.
- Vizinhos úteis no `libameLibrary` (não usados): `AComponent::VisitComps` (todos os componentes), `ATrackGroup::
  FindTrack/FindTrackInfo/NumEffectTracks`, `ASourceClip::GetSrcTrack/GetSrcPosition` (trilha e ponto da fonte).
- Laço do MC pelo piloto: `maos.arrastar(..., modificadores=(maos.ALT,))`, sempre da esquerda para a direita (regras
  do autor no SKILL do piloto).

### 🆕 ⭐⭐⭐ O ARO como CANAL DE CONTROLE para o MC ANTIGO (≤2021) e para os buracos do gRPC (direção, autor 2026-10-25)

A API gRPC (9100: `DoCommand`, `GetListOfBinItems`…) é RECENTE — razoável só no 25.x; o 24.6 tem 47 de 60 (sem
`DoCommand`), e o 2021 não tinha esse caminho. É por isso que os apps ficam presos ao 2024+. **O ARO é o oposto: é
VELHO** — o binário exige "Version **2014** or greater", porque é a ferramenta de teste interna da Avid (AvidSatin).
Logo, é muito provável que ESTEJA no MC 2021, 2018 e antes. E é mais rico em pontos: deu a SELEÇÃO da timeline
(`TLW_GetSelComponents`), que o gRPC nem tem; as strings `ARODoTitleCommand`, `AROSelectPopupMenuItem`,
`AROGetGadgetInfo`/`AROSetGadgetText` mostram que ele EXECUTA comando de menu e mexe em controle; e ele registra
`Bin`/`Project`/`Monitor`/`Composer`, não só a timeline.

⇒ **A tese:** UMA biblioteca de transporte (a que começamos em `_DeLaPraCa/tools/aro/`) serve o MC antigo E novo pelo
mesmo canal, cobrindo o que falta no gRPC. **E o custo de versão é baixo:** uma vez que temos o MAPA das funções que
precisamos, a diferença entre versões custa no máximo UMA sessão de REA (desmontar `GetAROserver` para o nome/caminho
da dylib daquela build, e reconferir os slots). O autor está confiante de que é um caminho seguro a perseguir.

A medir por versão (receita estática de sempre, MC fechado): (1) o NOME/caminho da dylib — "AvidRemoteObjects**364**"
cheira a número de versão; o 2021 deve procurar outro; lê-se na string do `dlopen` dentro do `GetAROserver`. (2) O
contrato (ARO_Init, layout das vtables, slots das interfaces) — por ser interno e estável deve mudar pouco; **resolver
as funções por NOME nas tabelas de `RegisterClass` (não por endereço fixo)** deixa robusto. (3) Confirmar que o ARO
está compilado naquela build (símbolos/strings). (4) O **Windows** (`AvidRemoteObjects364.dll`?). (5) Estratégico:
injeção é mais invasiva que o gRPC (pasta do sistema, visto com desconfiança por TI) → o ARO como **ponte/plano B** para
versões antigas e para os buracos (a seleção), com o gRPC como caminho principal no MC moderno (filosofia da família:
REA e injeção como ferramenta de desenvolvimento, não a peça central do produto). O passo 2 já é o protótipo da tese.

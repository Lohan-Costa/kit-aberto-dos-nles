# Arrastar para um painel CEP, e o que uma seleção de bin devolve

> **Medido em 2026-09-06**, Premiere Pro **25.6.5** (macOS, CEF 12.0.1.2), com a sonda
> `DRAMASYNC/.dev/sonda-premiere/`. Tudo aqui é `confirmado` por medição viva — o binário
> **não** responde estas perguntas, e essa é a lição do
> [`analise-de-executaveis.md` §5](../../transversal/analise-de-executaveis.md).

## 1. ⛔⛔ Da BIN do Premiere para o painel NÃO vem NADA — `confirmado`

```
fase             dragenter / drop
types            NENHUM
effectAllowed    copyMove
dropEffect       none
files            0
```

⭐ **O detalhe que faz a diferença entre "não funciona" e "não entrega":** o `effectAllowed`
volta **`copyMove`**, não vazio. Ou seja, o arrasto **chega** ao painel — o Chromium vê que há
um drag em curso e com que efeitos —, mas o payload é **zero tipo, zero arquivo**. O
`drop` dispara; simplesmente não há o que ler.

⚠️ Não é falta de `preventDefault` no `dragover`: a sonda o faz (é a armadilha nº 1 do
HTML5 drag), e a prova é que o `drop` disparou e registrou.

⛔ **Isto é o OPOSTO do Media Composer**, onde a bin entrega
`text/x.avid.mc-api-asset-list+json` ao `ondrop` do DOM
([`avid-panel-sdk/arrastar.md`](../avid-panel-sdk/arrastar.md)). ⭐ *Metade da superfície de um
painel é a do navegador — mas só se o host colocar algo na área de transferência.* O Avid
coloca; o Premiere não.

## 2. ✅ Do FINDER para o painel FUNCIONA, e entrega o caminho real — `confirmado`

```
types            text/uri-list | Files
effectAllowed    all
files            1
files[0].path    /Volumes/…/D02_230405/01_CAMERAS/CAM_A_Blackmagic-4k/A01/A001_03170214_C001.mp4
```

⚠️⚠️ **Use `files[].path`, NUNCA o `text/uri-list`.** No macOS o `uri-list` vem como URL
opaca de file-id, inútil para abrir o arquivo:

```
text/uri-list  →  file:///.file/id=8321326.138      (28 chars, não é caminho)
files[0].path  →  /Volumes/SSD/…/A001_….mp4  (o caminho de verdade)
```

⭐ **E PASTA também funciona:** arrastar o diretório `A01` devolveu `files[0].path` com o
caminho da pasta (e `size` 131072, o tamanho de diretório do macOS). Quem recebe pode
percorrer a pasta do lado do motor — não precisa que o usuário selecione arquivo por arquivo.

### ⚠️⚠️ 2b. E o `path` PODE SER DO NODE — no Windows sem Node, não veio caminho nenhum

`inferido` (2026-09-17, Premiere 23.2 / Windows, Ciclo Assist). A medida do §2 foi feita
numa extensão com `--enable-nodejs` no manifesto. Num painel **sem Node**, o arrasto de um
arquivo do Explorer caiu no ramo "não veio nada": nem `text/uri-list` (o `caminhosDoArrasto`
voltou vazio), e o `File` do Chromium não tem `path` fora de um contexto com Node.

⇒ **Não conte com o caminho num painel CEP.** Duas saídas, e a segunda não custa segurança:

1. ligar `--enable-nodejs` — ⛔ mas aí a página tem Node, e se ela renderiza texto de fora
   (resposta de modelo, nome de arquivo do cliente), isso é um shell na estação do editor;
2. ⭐ **mandar o CONTEÚDO**: `FileReader` → POST para o serviço, que grava a cópia na pasta
   de dados do app e autoriza ELA. É o que o Ciclo Assist faz (`servico/arrastados.
   guardar_conteudo`); o produto precisa do conteúdo (roteiro, imagem), não do lugar.

⚠️ **Falta medir**, e o painel agora conta na própria mensagem de erro: que `types` chegam
num drop do Explorer no CEP do Windows, e se `files[0].path` existe com Node ligado lá.

## 3. O que uma seleção de bin devolve — a tabela adversarial

`app.getCurrentProjectViewSelection()`, com uma seleção proposital de tipos misturados:

| item | `type` | `isSequence` | `isAdjustmentLayer` | `getMediaPath()` | `children` |
|---|---|---|---|---|---|
| pasta `D02_230405` | **BIN** (2) | false | false | *(vazio)* | 2 |
| `A001_….mp4` | CLIP (1) | false | false | **caminho real** | — |
| `.WAV` | CLIP (1) | false | false | **caminho real** | — |
| sequência `O PRODA` | ⚠️ **CLIP (1)** | **true** | false | *(vazio)* | — |
| `Adjustment Layer` | ⚠️ **CLIP (1)** | false | **true** | *(vazio)* | — |

⛔⛔ **A armadilha:** uma **sequência** e uma **camada de ajuste** se declaram `type = CLIP`,
igual a um vídeo. O campo `type` **não** distingue. Só os predicados distinguem —
`isSequence()`, `isAdjustmentLayer()`.

⭐ **O que salva hoje é o `getMediaPath()` vazio** nesses dois casos, e é o filtro que o
Órbita já usa. ⚠️ **Mas ele NÃO basta**, e é aí que mora o risco: um **JPG, PNG, PSD, LUT,
legenda ou still** tem `getMediaPath()` **preenchido** e passaria pelo filtro como se fosse
câmera. A bin do Premiere aceita muito mais tipo que a do Avid — a classificação tem de ser
por **extensão**, com `isSequence()`/`isAdjustmentLayer()` como recusa explícita por cima.

> **2026-09-16 — como o Órbita fechou isto (Windows):** o `host.jsx` ganhou
> `orbitaMediaPath(item)` — recusa por `isSequence()`/`isAdjustmentLayer()` e depois
> lista branca de extensão. ⚠️ **O filtro do servidor não bastava sozinho:** o `/sources`
> já filtrava por extensão, mas dois caminhos do painel passavam por fora dele (jogar a
> seleção numa fonte existente, e a contagem ao vivo do botão). Lição reaproveitável:
> antes de pôr filtro "no servidor", confira **todos** os consumidores da seleção. A
> lista do painel é espelho da lista-mestre em Rust, e um teste compara as duas.
> `confirmado` por teste com Premiere falso; não exercitado na GUI.

⭐ `nodeId` veio preenchido e sequencial (`000f447b`…`000f4484`), e o `treePath` traz o
caminho com separador **`\\`** mesmo no macOS (`\TESTE PLUGIN ORBITA.prproj\D02_230405\…`).

## 4. `createSubClip` sobre câmera crua — o que sai

```
alvo               A001_03170256_C002.mp4   (isMergedClip=false)
aparo              in=0  out=136076836896000 ticks   (= o clipe inteiro)
novo.tipo          CLIP
novo.isMergedClip  false
novo.mediaPath     …/A001_03170256_C002.mp4      ← O MESMO ARQUIVO
novo.videoComponents  undefined
```

⭐ Confirma que o subclipe do Premiere é **janela sobre um arquivo só** — ver
[`subclipe-e-merged-clip.md` §1](subclipe-e-merged-clip.md).

## 5. ⭐⭐ O runtime BATE com a análise estática — e isso promove o método

Os membros contados vivos contra as tabelas de classe lidas no
`ScriptLayerPPro.framework`:

| alvo | membros em runtime | verbo de fundir |
|---|---|---|
| `app` | 52–53 | NENHUM |
| `app.project` | 51 | NENHUM |
| `projectItem` | 62 | só `isMergedClip` |
| `qe` | 41 | NENHUM |
| `qe.project` | 57 | NENHUM |

⭐ **A lista de 62 membros do `projectItem` reproduz a tabela `ProjectItem class` do binário.**
Ou seja: `strings` + `grep -n "class$"` no `ScriptLayerPPro` é uma via **confiável** para
responder "existe o método X?" sem abrir o Premiere. Método promovido — ver
[`subclipe-e-merged-clip.md` §3](subclipe-e-merged-clip.md).

## 6. ⭐⭐ POR QUE não vem nada da bin — o mecanismo, não só a medida

> Segunda passada, 2026-09-06, a pedido do autor: *"pode ser que esse suporte não exista mas
> acho cedo ainda para não tentar."* Estava certo em insistir — a 1ª passada tinha a **medida**,
> esta tem a **causa**, e ela veio de um lugar que ninguém tinha olhado.

### A ponte pasteboard → DOM existe, e é do CEP

`strings` no **`CEPHtmlEngine`** (o processo que hospeda todo painel CEP):

```
draggingEntered:operation:pasteboard:modifierFlags:
draggingUpdated:operation:modifierFlags:
prepareForDragOperation:
performDragOperation:modifierFlags:
propagateDragEvent:pasteboard:          ← a ponte
namesOfPromisedFilesDroppedAtDestination:
startDragging:allowed_ops:point:        ← o sentido INVERSO
CefDragHandler · cef_drag_data_create
public.url-name · file://
com.adobe.cep.dnd.pasteboardtype        ← a chave
```

⭐ **O arrasto nativo do macOS É interceptado com o `NSPasteboard` na mão**, e `propagateDragEvent:`
o traduz para um `CefDragData` — que vira o `dataTransfer` do DOM. ⛔ **Essa tradução só cobre
os sabores web-mapeáveis** (arquivos, URLs, texto). Um sabor privado, in-process, não tem para
onde ser traduzido.

⭐⭐ **É isso que explica a medida exata do §1:** `effectAllowed=copyMove` (a ponte VIU o arrasto e
seus efeitos) com `types` **vazio** (não havia sabor traduzível). Não é o Premiere recusando o
painel; é a ponte não tendo o que entregar.

### `com.adobe.cep.dnd.pasteboardtype` é do sentido INVERSO — `confirmado`

O tipo aparece colado a `startDragging` no binário, e o **painel de CC Libraries da própria
Adobe** (`CEP/extensions/com.adobe.DesignLibraries.angular.2015.1`) mostra para que serve:

```js
this.ElementDragId = "com.adobe.cep.dnd.pasteboardtype";
this.GroupDragId   = "com.adobe.cclibraries.dnd.group";

handleDragOver = e => {
  D.Z.isWindowsOS() && e.dataTransfer.types.includes("com.adobe.cep.dnd.pasteboardtype")
    && (e.dataTransfer.dropEffect = "copy"); …
}
```

⭐ É a identidade das drags que **o próprio painel origina** — e o painel só a reconhece de volta
**no Windows** (`isWindowsOS()`). E o que a Adobe aceita como entrada é exatamente **duas** coisas:

```js
e.dataTransfer.types.includes(u.Z.ElementDragId)   // o arrasto do próprio painel
  || e.dataTransfer.types.includes("Files")        // arquivo do SO
```

⛔ **Nada vindo do HOST.** A referência da própria Adobe não lê arrasto da bin porque **não há
esse canal**.

### E nenhum produto comercial faz diferente

| produto | como pega o material |
|---|---|
| **Chop Chop Sync and Bin** (concorrente direto: sync + bin no Premiere) | ⛔ **zero** strings de `drag`/`drop`/`dataTransfer` nas 2.259 strings desofuscadas do `main.js` |
| **Quickture** (painel CEP) | `dataTransfer.types.includes("Files")` — react-dropzone, arquivo do SO |
| Selector, Markers Pro, FX Launcher, firestarter, Automation Blocks | nenhum lê drag do host (os hits de `drop` são lodash/jsdom/fancytree) |
| **CC Libraries (Adobe)** | `ElementDragId` (drag próprio) ou `"Files"` |

⭐ A desofuscação do Chop Chop foi refeita pelo método do
[`addendum-desofuscacao.md`](addendum-desofuscacao.md) — base64 com alfabeto rotacionado —
e rendeu **2.259/2.259 strings (100%)**, batendo com a contagem do adendo.

### ⛔ Conclusão: `bin → painel` NÃO EXISTE, e não é contornável do lado do painel

Quatro evidências independentes, e nenhuma depende das outras:

1. **medida viva** — `types` vazio com `effectAllowed` preenchido;
2. **o binário do host** — a ponte só traduz sabor web-mapeável;
3. **a referência da Adobe** — aceita `Files` ou o próprio drag, nada do host;
4. **sete produtos comerciais** — nenhum tenta.

⚠️ **Contraste com o Avid, e a lição fica mais precisa:** o MC entrega
`text/x.avid.mc-api-asset-list+json` porque **o Panel SDK da Avid escolheu pôr um sabor
web** na área de transferência. ⭐ *Metade da superfície de um painel é a do navegador —
mas só sobre o que o host resolve publicar ali.* O Avid publica; o Premiere não.

## 6b. ⭐⭐⭐ CORRIGE (2026-09-17, Windows): o arrasto da bin SAI do Premiere — e carrega um XML legível

> ⚠️ O §6 concluiu *"`bin → painel` NÃO EXISTE, e não é contornável"*. **Vale para o que o
> painel CEP enxerga no macOS** — e só isso foi medido. A conclusão foi além da medida: ela
> olhou pela ponte do CEP, que DESCARTA o que não é sabor web, e leu a ausência no DOM como
> ausência no arrasto. O autor insistiu pela terceira vez (*"não estou convencido que não há
> caminho"*) e estava certo.

**Como foi medido:** uma janela NATIVA com `IDropTarget` (pywin32,
`DRAMASYNC/.dev/sonda-premiere/alvo_nativo.py`) enxerga o `IDataObject` inteiro. Premiere
**23.2**, Windows 11, arrastando itens da bin do projeto para ela:

```
formatos oferecidos: 5
- dynamiclinksourcelist                   (HGLOBAL)  ← XML LEGÍVEL
- Adobe34116/Premiere/MasterClipVector    (HGLOBAL, 8 bytes = ponteiro do processo)
- Adobe34116/Premiere/ProjectItem         (HGLOBAL, 8 bytes = ponteiro do processo)
- DragImageBits · DragContext             (os do shell)
```

```xml
<LiveLinkSourceList ver ='1.0'><BetaPrime>0</BetaPrime>
  <Source><ProjectPath>D:\…\PRODE_COMPLETO_2023.prproj</ProjectPath>
          <ID>0f6bcd99-5e43-41fc-8134-1b17fb2c307f</ID></Source>
  … uma <Source> por item arrastado (medido: 1, 3 e 27)
</LiveLinkSourceList>
```

⭐ É o formato do **Dynamic Link** (a via Premiere → After Effects/Media Encoder) — por isso
ele sai do processo: foi feito para outro app ler. ⚠️ Os dois formatos `Adobe…` são
PONTEIROS (8 bytes), inúteis fora do Premiere.

- ⚠️ **O cursor fica BLOQUEADO** sobre a janela que aceita só COPY: a origem não oferece
  cópia. O `DragEnter` dispara assim mesmo — o dado é legível ANTES de soltar.
- ✅ **O `<ID>` É O `ObjectUID` DA `Sequence`** no `.prproj` — `confirmado` num arrasto
  controlado com o projeto salvo: a sequência `PRODE_COMPLETO_2023` e a sequência INTERNA de
  um merged clip, cada uma achada pelo `ObjectUID` (e pelos `SequenceSource` que apontam
  para ela). O mesmo GUID aparece em `MZ.PrefixKey.OpenSequenceGuidList`.
- ⛔⛔ **SÓ SEQUÊNCIAS carregam o formato.** No arrasto controlado, um CLIPE de câmera
  (`.mov`) ofereceu apenas os dois ponteiros — sem `dynamiclinksourcelist`. Sequência e
  merged clip (que é uma sequência por dentro) o trazem. É coerente com o Dynamic Link:
  só o que é composição tem o que mandar para outro app.
- ⚠️ **O cursor continua bloqueado** mesmo aceitando os efeitos que a origem oferece
  (`efeito = 3`, COPY|MOVE). Não impede a leitura: o dado vem no `DragEnter`.
- ✅ **`sequence.sequenceID` da API É esse GUID** (sonda §8, 23.2): `PRODE_COMPLETO_2023` →
  `0f6bcd99…`, o merged `C0076` → `00caf2f0…`. ⭐ E os merged clips **aparecem em
  `app.project.sequences`** (com `projectItem.isMergedClip() = true`) — um alvo nativo que
  recebe o arrasto acha o item pela API, sem ler o `.prproj`.
- ⛔ **O painel CEP no WINDOWS também não vê nada** — arrastando a SEQUÊNCIA para a zona da
  sonda: `types NENHUM`, `effectAllowed copyMove`, `files 0`. Igual ao macOS. A ponte do CEF
  não repassa `dynamiclinksourcelist`; só uma janela nativa o lê.
- ⭐⭐ **O que o painel SABE mesmo assim:** um arrasto com `copyMove` e ZERO tipos só vem do
  próprio Premiere (o do Explorer/Finder traz `Files`). ⭐⭐ **A SAÍDA ADOTADA:** no `drop`,
  perguntar ao host a SELEÇÃO da bin — o gesto vem do arrasto, o dado vem da seleção.
  ✅ **Sustentada pelo comportamento do Premiere** (observado pelo autor, 23.2): *"ao dar
  qualquer clique, mesmo se for para arrasto, o Premiere seleciona o item e retira a seleção
  anterior caso o item não esteja dentro de nenhuma seleção"* — não existe arrastar algo que
  não seja a seleção. Implementado no Órbita (`js/arrasto.js`), nas três abas, sem código
  nativo. `pendente`: o mesmo no macOS (o `copyMove` sem tipos já foi medido lá).
  ✅ **Validado pelo autor no 23.2 (Windows), 2026-09-17:** *"todos os arrastos que tentei
  deram certo, incluindo arrastar uma pasta com diferentes clipes"* — a pasta vem pela
  seleção e o Órbita separa CAM 1 / CAM 2 / SOM DIRETO como no botão. ⚠️ Armadilha de UI
  achada no uso: não decidir o drop pelo `disabled` de um botão que também depende da
  CONTAGEM da seleção — ela é atualizada por batida e, no instante do drop, ainda é a
  anterior (um item não suportado aparecia como "confira a conexão"). **o painel CEP no Windows vê esse
  formato?** (a ponte do CEF costuma só repassar texto/URL/arquivo); **e no macOS**, o
  mesmo sabor existe no `NSPasteboard`?
- ⭐ **Consequência:** uma janela nativa (o app, ou um alvo nativo pequeno) pode ser o
  destino do arrasto da bin — o gesto que o autor quer — desde que se consiga resolver o
  `<ID>` num item.

> 🆕 **2026-10-12 (Resolve 19):** a "janela nativa pequena" do §6 foi PROVADA como ponte: uma janela com `IDropTarget`
> que SURGE sob o cursor no meio do arrasto recebe o soltar ([resolve-scripting/api-scripting.md](../resolve-scripting/api-scripting.md)
> §"Arrastar do Media Pool"). Aqui ela leria o `dynamiclinksourcelist` (o `sequenceID`) sem depender da seleção.

## 6c. 🆕 O PRODUTO: a janela do app recebe a sequência — `confirmado` (Premiere 23.6.0, Windows, 2026-10-19)

O alvo nativo do De Lá Pra Cá (`_DeLaPraCa/app/src-tauri/src/arrasto_win.rs`, `IDropTarget` na janela Tauri) lê o
`dynamiclinksourcelist` no `DragEnter`; arrastada pelo piloto (`SendInput`, 40 passos) a sequência "titulo" do painel
de projeto até a janela do app: ⭐ **o `Drop` CHEGOU** (o alvo devolve UM efeito, o primeiro que a origem permite —
COPY), o serviço achou a sequência pelo `<ID>` = `sequenceID` e a ponte deu o nome. O "cursor bloqueado" do §6b não se
repetiu aqui. A janela do app precisa estar à frente do Premiere no fim do gesto (no teste, `HWND_TOPMOST` durante o
arrasto — o clique no Premiere o traz para a frente).

## 6d. 🆕 CLIPES e PASTAS da bin na janela do app (Órbita Painel) — `confirmado` (Premiere 23.6.0, Windows 11, 2026-10-21)

- ⛔ **O nome do formato do item TRAZ O PID DO PREMIERE:** `Adobe<PID>/Premiere/ProjectItem` e `…/MasterClipVector`. Medido:
  `Adobe23908/…` com o `Adobe Premiere Pro.exe` de PID 23908 (o `Adobe34116` do §6b era o PID daquela sessão). Um alvo que
  procure o nome FIXO não reconhece nada a partir da segunda abertura do Premiere — o arrasto chega como "nada" e o soltar é
  recusado. Reconhecer pelo SUFIXO `/Premiere/ProjectItem` enumerando os formatos (`EnumFormatEtc` + `GetClipboardFormatNameW`).
  Corrigido no Órbita (`src-tauri/src/arrasto_win.rs`); ⚠️ o De Lá Pra Cá ainda tem o nome fixo.
- Formatos de um CLIPE (e de PASTAS, arrastadas juntas): `Adobe<PID>/Premiere/MasterClipVector`, `Adobe<PID>/Premiere/ProjectItem`,
  `DragImageBits`, `DragContext` — sem `dynamiclinksourcelist` (coerente com o §6b).
- ✅ **Pastas (bins) também saem do Premiere** por arrasto. No soltar, a SELEÇÃO da bin (`app.getCurrentProjectViewSelection`)
  traz as pastas, e o `orbitaGetSelectionPaths` desce nelas: CAM A + SOM DIRETO arrastadas juntas → 26 + 24 caminhos, separados
  em duas fontes pelo esqueleto do nome. A saída "o gesto vem do arrasto, o dado vem da seleção" vale na janela do app.
- Piloto: um CLIQUE no item seguido do arrasto vira DUPLO CLIQUE e abre a bin numa aba — arrastar sem clicar antes. E o alvo
  precisa estar por cima (`HWND_TOPMOST` com `argtypes` certos — ver a skill do piloto).

## 6e. 🆕 CLIPES da TIMELINE saem por arrasto — só como gesto (Premiere 26.5.2, Windows 11, 2026-10-24) — `confirmado`

Medido com a sonda nativa (`piloto/sondas/arrasto_nativo.py`) num projeto de lab (`LAB_ARRASTO_TL`, 4 clipes do B01 na V1,
o WAV na A1; Show Video/Audio Keyframes e FX Badges desligados; o clipe agarrado pelo NOME, foto no meio do gesto).
- O arrasto de um clipe da timeline SAI do Premiere e é SOLTO numa janela nativa (`dragenter` e `drop`), com 6 formatos:
  `Adobe<PID>/Premiere/TrackItemSelection` (8 bytes = um PONTEIRO na memória do Premiere, igual nos dois arrastos — só vale
  dentro dele), `…/TakeVideo` (01), `…/TakeAudio` (00), `…/TakeData` (00) — o que o arrasto leva (clipe só de vídeo:
  vídeo sim, áudio não) —, `DragImageBits` e `DragContext`. **Nenhum nome, caminho ou tempo.**
- O `<PID>` é o do `Adobe Premiere Pro.exe` (18168 nesta sessão), como no §6d: reconhecer pelo SUFIXO.
- ⇒ A mesma saída do §6d: **o gesto vem do arrasto, o dado vem da seleção.** Arrastar seleciona o clipe; no soltar, a
  ponte lê os track items com `isSelected()` (De Lá Pra Cá: `dlpcSelecaoDaTimeline`, rota `/premiere/selecao-da-timeline`,
  50 ms). `getSelection().length` sempre bateu com a contagem por `isSelected()`.

### 6e.1 A matriz das variáveis (2026-10-24, 16 arrastos; PRODC_CORTE02 offline + a cópia online + LAB_ARRASTO_TL) — `confirmado`

Em TODOS: os mesmos 6 formatos, `TrackItemSelection` com o MESMO ponteiro (é o objeto "seleção", não o clipe), `TakeData`
00, e a seleção no soltar = exatamente o que foi arrastado. `TakeVideo`/`TakeAudio` = o que a seleção contém (01/00).
Nenhum arrasto mudou a timeline (155 itens conferidos pelos tempos depois de cada um; History sem ação).

| arrastado | Take V/A | o que a seleção devolve |
|---|---|---|
| clipe de vídeo offline (e desligado) | 01/00 | 1 item, `offline: true`, `getMediaPath` = o caminho DECLARADO (o Z: que não existe) |
| o mesmo clipe online (cópia relinkada) | 01/00 | `offline: false`, o caminho real |
| clipe com velocidade (200 %) | 01/00 | `getSpeed()` = 2 |
| clipe com efeitos (Lumetri; EQ/Dynamics no áudio) | — | os `components[].displayName` (Opacity/Motion/Volume são fixos) |
| título (Graphic) | 01/00 | sem `projectItem`: arquivo/offline/nest vazios; efeitos "Vector Motion", "Text" |
| camada de ajuste | 01/00 | `isAdjustmentLayer()` true, sem arquivo |
| nest de vídeo / nest de áudio | 01/00 · 00/01 | 1 item, `projectItem.isSequence()` true, sem arquivo — os de DENTRO não vêm |
| multicam (V+A vinculados) | 01/01 | 2 itens, `isSequence()` E `isMulticamClip()` true, sem arquivo nem ângulo ativo |
| áudio solto (WAV; subclipe "· A") | 00/01 | 1 item de áudio; o subclipe dá o caminho do arquivo-mãe |
| V+A VINCULADOS, arrasto simples | 01/01 | os 2 (a seleção vinculada leva o par) |
| V+A vinculados, Alt+clique só no vídeo | 01/00 | só o vídeo (a seleção do Alt sobrevive ao arrasto) |
| 2 clipes (Shift+clique) / vídeo + áudio soltos | 01/00 · 01/01 | os 2 |

- Para o relink por arrasto: nest e multicam pedem DESCER na sequência (`projectItem` → a sequência → os clipes de dentro);
  título e camada de ajuste não têm mídia (ignorar ou avisar); offline traz o caminho declarado (é o que o casamento usa).
- ⚠️ Piloto: no Premiere, quem SOMA à seleção da timeline é o **Shift**+clique (o Ctrl+clique não somou). A vista da
  timeline pode rolar depois de um arrasto — foto antes de CADA gesto. Zoom é por sequência. Agulha pelo campo de
  timecode (dígitos + Enter) + "=" = o clipe alvo sob a agulha, em qualquer densidade de timeline.
- **Canais de áudio** (B03 do lab, sequência "LAB CANAIS"): `projectItem.getAudioChannelMapping` (PROPRIEDADE) →
  `audioChannelsType` 0 mono / 1 estéreo e `audioClipsNumber`. WAV 1 canal = 1 item (0/1); WAV 2 canais = 1 item ESTÉREO
  (1/1); MOV com 2 monos = 2 itens (0/2); WAV de 8 e de 16 canais em mapeamento mono = **um item por canal** (8 e 16
  itens, um por trilha, todos o MESMO arquivo, 0/8 e 0/16). ⭐ Arrastar UM canal ("Ch. 16") seleciona os 16 (os canais de
  um arquivo andam vinculados). ⇒ Relink por arrasto: agrupar a seleção pelo ARQUIVO.
- **Trilha bloqueada:** apertar sobre um clipe dela NÃO arrasta — começa um LAÇO de seleção (retângulo azul) que rola a
  vista e seleciona clipes de outras trilhas; nada sai do Premiere (a sonda não recebe). A seleção no "soltar" fica com
  lixo: o app só deve agir num soltar que TROUXE o formato `TrackItemSelection`.
- **Clipe de outro projeto aberto:** a aba da timeline manda — com a aba da PRODC (projeto P2P) ativa, `app.project` e a
  `activeSequence` são dela; com a do LAB, do LAB. `confirmado` (os dois projetos abertos o tempo todo).
- **Mac (Premiere Pro 2026, macOS 15.6.1 arm64, 2026-10-24) — `confirmado` (1 clipe de bin, 1 de timeline V+A):** o
  arrasto sai do Premiere por `NSPasteboard` de ARRASTO com tipos dinâmicos (`dyn.…`; decodificados =
  `com.adobe<PID>.premiere/<nome>`, o PID do processo no meio — o mesmo desenho do `Adobe<PID>/Premiere/…` do Windows):
  - bin: `…/projectitem` (8 B, ponteiro) + `…/masterclipvector` (8 B). **Nenhum caminho de arquivo** (o
    `dynamiclinksourcelist` do Windows não apareceu).
  - timeline: `…/trackitemselection` (8 B, ponteiro) + `…/takevideo` = 01 + `…/takeaudio` = 01 + `…/takedata` = 00 —
    as mesmas chaves Take do Windows. Timeline intacta (clipe no lugar, só selecionado).
  - ⇒ igual ao Windows: o soltar é o GESTO, o dado sai da ponte (`dlpcSelecaoDaTimeline`). O alvo nativo do app no Mac
    tem de aceitar tipos `dyn.` cujo nome decodificado termine em `/projectitem` ou `/trackitemselection` (o PID muda a
    cada abertura: nunca nome fixo). Sonda: `piloto/sondas/arrasto_nativo_mac.swift` (lê o pasteboard de arrasto a cada
    0,1 s, então vê os tipos privados ANTES do soltar, sem registrá-los).
  - Decodificar `dyn.a…`: alfabeto `abcdefghkmnpqrstuvwxyz0123456789`, 5 bits por letra, depois de `dyn.a`; o texto é
    `?0=6:3=<tipo>`.
  - ⚠️ Piloto no Mac: arrasto que começa numa janela de OUTRO app que não está na frente só ativa o app (o 1º gesto
    não arrasta); e arrasto bin → timeline DENTRO do Premiere virou "passar o mouse" na miniatura (não criou sequência)
    — usei Arquivo › Novo › Sequência a partir do clipe pelo System Events (menu pelo nome).
- ⛔ Armadilha do piloto: com a trilha EXPANDIDA, o meio do clipe é a linha de opacidade/volume ("Drag to vertically adjust
  the connector line between keyframes" na barra de status) — o gesto vira ajuste de keyframe, não arrasto. Conferir no
  History (Window › History) que nada mudou. Projeto pequeno, trilha baixa, agarrar pelo nome.
- Resolve e MC: `pendente` (o Media Pool do Resolve não solta para fora — `resolve-scripting/api-scripting.md`).

## 6f. 🆕 Mac: da BIN do Premiere para a JANELA DO APP (Tauri/WKWebView) — `confirmado` (Premiere 26.0.2, macOS 15.6.1, Ciclo Assist, 2026-11-12)

Medido com uma sonda nativa (registro de tipos controlado) e depois no app, pilotado (CGEvent), projeto
`carta_aberta/G01 ARRASTO MAC v01.prproj`.
- **Os tipos** são `dyn.ah62…` = `?0=6:3=<nome>` — tag de pasteboard antigo (`3`) que CONFORMA a `public.data` (`0=6`).
  Decodificar: tirar `dyn.a`, base32 do alfabeto `abcdefghkmnpqrstuvwxyz0123456789`, 5 bits por letra.
  - sempre: `com.adobe<PID>.premiere/projectitem` e `/masterclipvector` (8 B, ponteiros);
  - ⭐ **quando o arrasto leva SEQUÊNCIA** (uma sequência, ou uma pasta que contém sequências):
    `com.adobe.dvaui.dynamiclinksourcelist` — nome FIXO (o mesmo do Windows, §6b), XML
    `<LiveLinkSourceList><Source><ProjectPath>…prproj</ProjectPath><ID>…</ID></Source>…` com o **`ObjectUID` de cada
    SEQUÊNCIA** (conferido no `.prproj`: `<Sequence ObjectUID=…>`). Clipes não entram nele. ⇒ CORRIGE o §6e.1, que
    dizia que ele não aparecia no Mac: com um clipe só, não aparece mesmo.
- ⭐⭐ **Registrar `public.data` basta** para a janela receber o gesto do Premiere — sem conhecer o PID (que muda a cada
  abertura). Provado com a sonda registrada SÓ para `public.data`. ⚠️ Registrar o nome cru (`com.adobe…/projectitem`)
  ou o UTI de `UTTypeCreatePreferredIdentifierForTag(nspboard-type, …)` dá OUTRA grafia (`dyn.agu8…`, sem o `0=6`) e
  não casa.
- **No app** (Ciclo Assist `app/src-tauri/src/arrasto_mac.rs`): o wry chama `DragDrop::Enter` com a lista de caminhos
  vazia, o código lê os tipos do pasteboard de ARRASTO e manda à página `premiere` (com o XML em `dados`) ou
  `premiere_item`, como o Windows; a página lê a SELEÇÃO pela ponte no soltar. Provado: 1 clipe, 2 clipes, a sequência
  multicâmera (`SEQUENCIA G01-GRUPO-SOM`), o WAV; e o arquivo do Finder continuou chegando com caminho.
- ⭐ Arrastar um item NÃO selecionado troca a seleção (como no Finder): o soltar traz só ele.
- ⛔ Armadilha do PILOTO (não do Premiere): o Cmd+clique sintético (`_mouse(…, bandeiras=0x100000)`) deixou o Command
  "PRESO" — os cliques simples seguintes SOMARAM à seleção, e o arrasto levou a seleção antiga junto. Apertar e soltar
  o Command (`_tecla_crua(CMD, True/False)`) destrava. Conferir a seleção pela ponte (`/premiere/selecao`), não pelo
  realce (sutil demais na foto).

## 7. 🆕 O que isso ABRE: o painel pode ORIGINAR um arrasto

`startDragging:allowed_ops:point:` + `com.adobe.cep.dnd.pasteboardtype` + os flags
`supportsDropFiles` / `_supportsFileURLs` da Adobe dizem que o sentido **painel → Premiere**
é suportado por desenho. É o que o [Eddie AI](eddie-ai-arquitetura.md) usa (`IPC_DRAG_XML_FILE`,
"o app inicia um drag nativo de arquivo").

⭐ **Lead para depois:** entregar o resultado do sync **arrastando do painel para a bin**, em vez
de importar. Não medido.

## Ver também

- [`subclipe-e-merged-clip.md`](subclipe-e-merged-clip.md) — o merged clip, e por que não há API
- [`api-extendscript.md`](api-extendscript.md) — a superfície de API medida
- [`../avid-panel-sdk/arrastar.md`](../avid-panel-sdk/arrastar.md) — o lado que ENTREGA payload

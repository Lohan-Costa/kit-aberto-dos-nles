# ExtendScript do Premiere — API de montagem de timeline (e as armadilhas)

O `.jsx` que roda no host (Premiere) via `csInterface.evalScript`. É **ES3** — sem `let`, sem
arrow, e o `JSON` global **não é garantido**. Fatos consumíveis em
[dados/api-metodos.json](dados/api-metodos.json). Tudo aqui **confirmado** no Premiere 25.6.5
(macOS, 2026-07-26), montando uma diária multicâmera real, salvo onde marcado.

## 🆕 2026-11-01 — Abrir, criar e fechar o Premiere POR FORA (Ciclo Assist, Premiere 2026, Win11) — `confirmado` (1 rodada, 4/4)

`cicloassist/premiere_app.py` + `spikes/abrir_e_fechar_o_premiere.py` (ponte invisível do Assist):
- Premiere FECHADO + `.prproj` novo: lançar o exe SEM argumento → a ponte sobe → `app.newProject(caminho)` → **21,7 s**
  do lançamento ao projeto criado, sem diálogo. Com o `.prproj` existente na LINHA DE COMANDO → **21,2 s**, e o projeto
  já vem aberto (`app.project.path` igual).
- Fechar: `app.project.save()` numa chamada e `app.quit()` noutra (sem esperar resposta) → o processo sai em **1,6–2,0 s**
  (2 de 2), sem diálogo. ⚠️ O 23.2 já NÃO saiu pelo `app.quit` (2026-10-10, abaixo): conferir o PROCESSO e ter
  `WM_CLOSE` / encerrar à força (só com o projeto salvo) de reserva.
- ⛔⛔ **O long-poll da ponte de um Premiere que ACABOU de fechar continua esperando no serviço** (até a espera do
  long-poll, 20 s) e LEVA o primeiro pedido da ponte do Premiere reaberto: o pedido ficou 180 s sem resposta. O
  "painel vivo" dizia sim pela batida velha. Remédio: depois de lançar, só chamar com batida POSTERIOR ao lançamento e
  passada a espera do long-poll (`ponte.bateu_desde`). Vale para qualquer ponte por long-poll (DLPC, Órbita).

## Ler a seleção da bin

- **`app.getCurrentProjectViewSelection()`** → Array de `ProjectItem` selecionados no painel
  Project. É método de **`Application`** (`app`), não de `Project`. **`app.project.getSelection()`
  NÃO EXISTE** (chutá-lo lança exceção → seleção vazia silenciosa). Armadilha que custou um ciclo.
- **`item.getMediaPath()`** → caminho do arquivo em disco do ProjectItem (vazio p/ sequência/título).
- **Bin pai não é exposto de forma confiável** pelo ProjectItem. Para saber a câmera de cada clipe
  (a pasta CAM A / CAM B / SOM DIRETO), **varra o projeto** a partir de `app.project.rootItem`
  recursivamente, guardando `path → nome do bin pai`. Tipos: `ProjectItemType.CLIP = 1`, `BIN = 2`
  (fixe as constantes; nem toda versão expõe o enum).

## Passar dados JS→JSX

`evalScript` passa **string**. Como o `JSON` do ExtendScript é incerto, serialize os dados numa
string delimitada por **`\t` (campos) e `\n` (registros)** e dê `split` no `.jsx`. Caminhos de
arquivo não contêm `\t`/`\n`. Para passar UM caminho como literal seguro, use `JSON.stringify` no
lado JS (escapa `\\` e aspas — importa nos caminhos do Windows).

## Montar a sequência (SEM reimportar mídia)

Importar um `.prproj` (`app.project.importFiles([prproj])`) **RE-IMPORTA a mídia** (cria itens
duplicados na bin) e vira "escadinha". A montagem NATIVA evita isso — usa os ProjectItems que já
estão na bin:

- **`app.project.createNewSequenceFromClips(name, [firstItem], targetBin)`** — cria a sequência
  HERDANDO settings (resolução/fps) do 1º clipe. Adiciona o clipe (esvazie as tracks depois).
  Funciona no 25.6.5.
- **`videoTracks[i].overwriteClip(projectItem, tempoEmSegundos)`** — posiciona o item da BIN na
  track `i`, no tempo em **SEGUNDOS** (float; `frames/fps`). **Não reimporta.**
- **Remover clipe:** `track.clips[j].remove(false, false)`. `track.clips.numItems` = quantos.
- **Nomear track:** `track.setName(nome)` (DOM) ou QE `qe...getVideoTrackAt(i).setName(nome)`.

## ⚠️ A REGRA que domina o layout de áudio

**`overwriteClip` de um clipe A/V põe o vídeo E o áudio na track de MESMO NÚMERO** — vídeo em
`Vk`, áudio em `Ak` — **não importa** se você chamou numa track de vídeo ou de áudio. Chamar
`audioTracks[j].overwriteClip(itemAV)` põe o áudio em `Aj` **e o vídeo em `Vj`** (duplica o vídeo).
Áudio multicanal **espalha PRA BAIXO** a partir do índice (uma câmera PANA de 4 streams mono ocupa
4 tracks de áudio). Consequências:

- **Não dá** para ter vídeo compacto (V1/V2) **e** áudio de câmera separado ao mesmo tempo, nativo,
  sem **desvincular** (unlink — que o ExtendScript não faz de forma confiável).
- **Solução usada:** colocar cada câmera UMA vez na track de vídeo cujo índice = a **1ª track do
  bloco de áudio** dela. Vídeo e áudio caem alinhados no bloco, sem duplicar. Custo: **tracks de
  vídeo vazias** entre as câmeras (o áudio multicanal ocupa >1 track). Ex.: SOM DIRETO 2ch → A1/A2;
  CAM A 2ch → V3 + A3/A4; CAM B 4ch → V5 + A5-A8; V1/V2/V4 vazias.
- **`setTargeted(bool, bool)` NÃO redireciona** o áudio vinculado do `overwriteClip` (o Premiere
  ignora o targeting nesse caso). Não adianta mirar a track de áudio antes.

## Apagar tracks vazias ("Delete Empty Tracks")

**Não há método no DOM oficial** (é feature-request antiga). O **QE DOM** (não-documentado) tem:

```javascript
app.enableQE();
qe.project.getActiveSequence().removeEmptyVideoTracks();
qe.project.getActiveSequence().removeEmptyAudioTracks();
```

⚠️ QE é **NÃO-SUPORTADO / não-documentado** pela Adobe (ferramenta interna de teste) — pode sumir
numa atualização; funciona só na **sequência ativa** (não há equivalente ao
`getCurrentProjectViewSelection` para objetos QE). Chutar o nome errado (`deleteEmptyTracks()`) não
existe. Deixe um fallback avisando para rodar o atalho manual.

## Contagem de canais de áudio (fora do ExtendScript, mas essencial ao layout)

Para reservar as tracks de áudio certas, você precisa do TOTAL de canais por clipe. O MediaInfo
`audio_track` (singular) dá só o **1º stream** — uma câmera pode ter **N streams mono separados**
(PANA = 4). **Some todos os streams de áudio** (ffprobe `-select_streams a -show_entries
stream=channels`).

## Cronologia (evita falso positivo de sync — vale para o motor, não o painel)

Ao mandar os clipes para o motor, agrupe por CÂMERA (o bin pai) e mande a ORDEM de gravação
(`group_order`). Sem isso, o motor trata cada clipe como câmera isolada e um match de waveform
errado pode jogar um clipe para antes do anterior. Com `group_id`(câmera)+`group_order`, a ordem
cronológica trava e os falsos positivos somem. (Ver [[../../protocolos/... do motor]] / o app.)

## Mover clipes que JÁ estão na timeline (sync in-place, fechar buracos)

`TrackItem.move(Time)` **existe e funciona** (validado no Premiere 25.6.5, 2026-07-31). É o único
caminho: **`clip.start = t` APARA o clipe** (mexe no ponto de entrada) em vez de movê-lo.

```javascript
var t = new Time(); t.seconds = deslocamento;   // segundos
clip.move(t);
```

Três regras que ditam qualquer implementação:

1. **A semântica de `move()` não é documentada** (delta ou posição final?) e pode variar por versão.
   Em vez de apostar: mova, LEIA `clip.start.seconds` e conclua qual é — o resto da leva usa a que
   funcionou. Se a DURAÇÃO mudar, o Premiere aparou: aborte antes de estragar o resto.
2. **O áudio VINCULADO é arrastado junto pelo vídeo.** Trabalhe sempre com alvos ABSOLUTOS e releia
   a posição do clipe imediatamente antes de mover: se o par já veio junto, o deslocamento dá ~0 e
   ninguém se move duas vezes. (É a mesma família da regra "áudio vinculado vai para a track de
   mesmo número da de vídeo".)
3. **Não existe API de "Close Gap".** Reconstrua com o mesmo primitivo — mas nunca track a track:
   isso destruiria a sincronia. Funda os intervalos ocupados de TODAS as tracks, ache os buracos
   GLOBAIS (onde nenhuma track tem clipe) e desloque tudo que vem depois de cada um.

Ler a seleção da timeline: `sequence.videoTracks[i].clips[j].isSelected()` + `clip.projectItem
.getMediaPath()`; a posição do trecho usado é `clip.start`/`clip.inPoint`/`clip.duration` (objetos
`Time`, campo `.seconds`). Um clipe APARADO exige somar o `inPoint` ao alinhar por um mapa que fala
do arquivo inteiro.

## ⚠️ O painel Timeline NÃO se redesenha depois de mudanças por script

Sintoma (visto no 25.6.5, 2026-07-31): os clipes movidos por script **ficam invisíveis** — a
timeline mostra um buraco onde há clipe, e ele só aparece quando o mouse passa por cima. O material
está lá; é só o desenho que ficou velho.

Não se nota quando o script mexe na ESTRUTURA da sequência (ex.: terminar com
`removeEmptyVideoTracks()`), porque aí o painel reconstrói tudo. Depois de só mover clipes, é
preciso provocar o redesenho. Provocações inofensivas:

```javascript
var pos = seq.getPlayerPosition();                              // cutuca o playhead
seq.setPlayerPosition(String(Number(pos.ticks) + 254016000000)); // +1s (tick = 254016000000/s)
seq.setPlayerPosition(String(pos.ticks));                        // e volta
app.project.activeSequence = seq;                                // reatribui a sequência ativa
```

Alternar para OUTRA sequência e voltar é mais forte, mas abre abas na Timeline do usuário —
efeito colateral pior que o sintoma.

### ⭐⭐ A alavanca `updateUI` (2026-08-24) — e ela NUNCA foi tentada no Órbita

Lida em **dois produtos comerciais independentes** (ver
[quatro-paineis-timeline.md](quatro-paineis-timeline.md) §2): várias APIs de mutação do
ExtendScript carregam um booleano de *atualizar a interface*, e os dois passam `true` sempre.

```javascript
trackItem.setSelected(isSelected, updateUI);   // Automation Blocks: setSelected(v, true)
componentParam.setValue(value, updateUI);      // FX Launcher: setValue([x,y], true)
```

No Automation Blocks o `updateUI` é opção de primeira classe, com **default `true`**
(`("updateUI" in ds) ? ds.updateUI : true`), exposta até o topo como campo de bloco.

⚠️ **Por que isto não é repetir o que já falhou:** o `host.jsx` do Órbita **não chama
`setSelected` em lugar nenhum** — a única ocorrência da palavra é um comentário dizendo que não se
faz isso, porque *"o Cmd+A manual PIORA o sintoma"*. Mas o que foi testado ali foi o **GESTO** (a
seleção pelo painel), não a **API** com o sinalizador explícito. São coisas diferentes.

⛔ **Antes de tentar, resolva uma contradição do próprio projeto:** `.dev/DECISIONS.md` de
2026-08-01 registra que o remédio manual **`Cmd+A` + andar um frame FUNCIONA**; o
`host.jsx:414` registra que o **`Cmd+A` manual PIORA**. As duas não podem ser verdade, e a
alavanca só vale se "seleção força repintura" for a versão certa.

⛔ **Achado negativo que emoldura tudo:** dos quatro painéis lidos em 2026-08-24, **nenhum move um
clipe já colocado na timeline**. Todos inserem, sobrescrevem, aplicam efeito ou criam marcador —
operações que mudam estrutura ou conteúdo e **repintam sozinhas**. *O sintoma é raro porque a
operação é rara;* não há cura pronta para copiar de ninguém.

### ⭐ `nodeId`: identidade estável de clipe

O Automation Blocks expõe `trackItem.nodeId` entre as propriedades legíveis. Se for estável
através de um movimento, resolve a classe inteira de problemas que o `orbitaResolveClip` hoje
ataca por índice → caminho + start. `hipotese` — não medido.

## ⭐⭐ "Este clipe tem efeito?" — é classificação, não consulta (2026-08-24)

Todo `TrackItem` já vem com componentes de fábrica. Responder *"tem efeito aplicado"* exige
**subtrair** esses intrínsecos de `clip.components` — e a lista **muda com a espécie do clipe**:

| espécie | componentes que existem SEMPRE |
|---|---|
| vídeo | `AE.ADBE Motion`, `AE.ADBE Opacity` |
| **gráfico / título** | `AE.ADBE Graphic Group`, `AE.ADBE Text` — **além** de Motion e Opacity |
| áudio (volume) | `Internal Volume Mono` \| `Internal Volume Stereo` \| `Internal Volume 16 Channel` |
| áudio (canal) | `Internal Channel Volume Stereo` \| `Internal Channel Volume 16 Channel` |

⚠️⚠️ **Um teste por CONTAGEM (`components.numItems > 2`) marca todo título e todo áudio
multicanal como "tem efeito" — e não levanta exceção.** O sintoma é um relatório plausível e
errado. Compare por `matchName`, nunca por quantidade.

⛔ **E o fornecedor que mais sabe disso não entregou o filtro genérico:** o Selector for Premiere
Pro tem *"Has effects"* especificado no `FiltersDB.json` e **parado em `clipOnHold`**; o que ele
publica é *"Has effect **named** X"*, que não precisa de subtração nenhuma. Ver
[selector-conform.md](selector-conform.md) §3. Lista `inferido` (tabela de símbolos), não medida
por nós — trate componente desconhecido como *"não sei classificar"*, não como *"é efeito"*.

## ⭐⭐ Ler a timeline SEM percorrer o DOM: `exportAsFinalCutProXML`

```javascript
sequence.exportAsFinalCutProXML(caminho);   // a sequência inteira, num passo
```

O FCP XML carrega **efeitos e parâmetros**, que o DOM só entrega componente a componente. O
Selector usa essa rota (`exportSeqAsFCPXML` + um `xmlToJSON` próprio).

⭐ **Por que importa mais do que parece:** o `FiltersDB.json` do Selector traz um **custo medido**
por predicado, e ele diz que **ler propriedade de `TrackItem` é o que domina** — `isEnabled` (ler
`clip.disabled`) custa **10966** contra **150** do mais barato do mesmo escopo, 73×. Um assistente
que percorra N clipes lendo M componentes paga a travessia da ponte N×M vezes. Para relatório,
conform ou qualquer leitura ampla, **exportar e ler o XML deixa de ser elegante e passa a ser a
escolha óbvia**.

⭐ **Corolário barato:** em filtro composto, rode o predicado barato primeiro. A ordem de custo do
Selector é **dado**, e está em [dados/selector.json](dados/selector.json) §`catalogo_de_filtros`.

## ⭐ `nodeId` como handle de seleção — promovido a `inferido` forte

O Selector constrói **toda** a seleção sobre `nodeId`: lê a seleção, guarda a lista de `nodeId`,
filtra, e reseleciona a partir dela (`getSelectionNodeIds` → `selectFromNodeIdsAry`), inclusive
para consultas relativas ao playhead (`getClipsNodeIdsAtCTI` / `BeforeCTI` / `AfterCTI`).

⚠️ **O que ainda NÃO se sabe:** se o `nodeId` sobrevive a um `TrackItem.move()`. O Selector filtra
e seleciona — não move nada. Para o `orbitaResolveClip` é exatamente essa a pergunta, e ela vale
uma medição curta.

## ⚠️ Marcador de sequência não tem dono

Um marcador de sequência mora num **tempo**, não num clipe nem numa trilha. Um relatório de conform
que escreva *"Lumetri, exposição +0,7"* num marcador aponta para um instante — e com três clipes
empilhados ali, não diz qual. Ou o texto do marcador carrega **trilha + nome do clipe**, ou o
relatório fica ambíguo justamente onde precisa ser preciso. (Marcador de `projectItem` tem dono,
mas não aparece na timeline.)

## 🆕 ⭐⭐ ESCREVER na bin: criar, mover, renomear e apagar — `confirmado` (23.2, 2026-09-17)

Medido em produção pelo Ciclo Assist (`organizar_o_projeto`), num projeto real de 4 diárias:
**84 operações em dois lotes, 76 clipes movidos e 8 bins apagadas, zero falhas, ~15 s.**

```javascript
var nova = mae.createBin("MIDIAS");      // a bin nasce DENTRO de `mae` (rootItem = a raiz)
item.moveBin(destino);                   // move clipe OU bin para dentro de `destino`
bin.renameBin("NOVO");                   // ⚠️ BIN renomeia por aqui…
clipe.name = "NOVO";                     // …e CLIPE pela propriedade. Trocar os dois falha CALADO
bin.deleteBin();                         // ver a ressalva abaixo
```

- ⛔⛔ **`renameBin` × `name` não são intercambiáveis.** Usar o errado não levanta nada: o nome
  continua o mesmo, e quem pediu acha que renomeou.
- ⚠️ **`deleteBin()` não pergunta nada** — quem quiser "apagar só as pastas vazias" confere
  `children.numItems === 0` antes. E quem planeja um LOTE precisa simular o plano: numa lista
  que primeiro esvazia a pasta e depois a apaga, a foto do começo ainda mostra a pasta cheia.
- ⚠️ **`createSubClip` cria o subclipe na RAIZ do projeto**, não na bin do clipe original.
- ⭐ **Achar o item:** `nodeId` é o handle barato; o caminho de nomes (`"DIARIA/D02/CAM A"`) é
  o que aparece na tela e o que um agente escreve de volta — aceite os dois. O nome sozinho é
  ambíguo (o mesmo `A001.mp4` em duas diárias).
- ⚠️ **Mover uma bin para dentro dela mesma** (ou de uma filha) não foi medido: `hipotese` de
  que o Premiere aceita calado e a bin some da árvore. Barrar antes custa três linhas, e
  descobrir em campo custa a bin do editor.

## 🆕 ⭐⭐ Cortar, apagar e ouvir eventos (2026-08-24)

Lidos no **fonte TypeScript original** do Quickture, recuperado do source map que acompanha o
`.jsxbin` — ver [quickture-ppro.md](quickture-ppro.md).

### Cortar e apagar

```javascript
qe.project.getActiveSequence().razor(timecodeComoString);   // corta — QE, aceita STRING de TC
clip.remove(ripple, shift);                                  // apaga — DOM, dois booleanos
```

⚠️ **Varra de trás para frente ao apagar**: a coleção de clipes de uma trilha reordena por tempo, e
apagar de frente escorrega os índices.
⚠️ **Não compare timecode como STRING** (o produto faz; só funciona com zero-padding e mesma taxa
dos dois lados). Compare em frames ou ticks.

### ⭐⭐ O Premiere TEM eventos — `app.bind`

```javascript
app.bind("onActiveSequenceChanged", handler);
app.bind("onSequenceActivated", handler);
app.bind("onSourceClipSelectedInProjectPanel", handler);
```

E a ponte para o painel é o **`CSXSEvent`** (`type`, `data`, `.dispatch()`), habilitada por
`new ExternalObject("lib:PlugPlugExternalObject")`.

⚠️ **Não há evento de mudança NA TIMELINE** — o de painel de projeto não cobre isso. Mas **trocar de
sequência não precisa de polling**.
⛔ `pendente` **e é a pergunta mais valiosa que sobrou**: quais outros nomes `app.bind` aceita? Três
foram vistos porque o produto usa três.

#### ⭐⭐ MEDIDO 2026-09-22 — o evento de IMPORT existe (`confirmado`, Premiere 23.2, Windows)

Instrumento: `_CICLO ASSIST/spikes/o_premiere_avisa_import.py` (extensão invisível, projeto
descartável). Quinze nomes registrados, cada um somando num contador em `$.global`; depois um
`importFiles` de 1 arquivo e outro de 60:

| evento | 1 arquivo | + 60 arquivos (1 chamada) |
|---|---|---|
| ⭐ **`onItemsAddedToProjectSuccess`** | **1** | **+2** (agrupado, não 1 por item) |
| `onProjectChanged` | 2 | +5 (dispara em QUALQUER mudança) |
| `onSourceClipSelectedInProjectPanel` | 2 | +5 (o import seleciona o item) |
| `onItemAddedToProjectSuccess` (singular), `onItemAddedToProject`, `onProjectItemAdded`, `onImportFinished`, `onItemImported`, `onProjectDirty…`, `onProjectEndDrop`, `onProjectPanelSelectionChanged` | 0 | 0 |

- ⛔⛔ **`app.bind` devolve `true` para QUALQUER nome** — os quinze, inclusive os inventados. O
  retorno não prova que o evento existe; só DISPARAR prova. Quem "descobrir" evento pelo
  retorno vai confiar num evento que nunca vem.
- ⚠️ Import pelo MENU ou por arrasto na janela de projeto: **`pendente`** (medido só `importFiles`).
- ⚠️ Não medido: se um segundo `app.bind` do mesmo nome (outra extensão) SUBSTITUI o primeiro.
  Quem depender do evento deve ter uma varredura de segurança.
- ⭐ E o custo de perguntar em vez de esperar, para comparar: percorrer o projeto com
  `getMediaPath()` em cada item custou **~3,4 ms com 1 item e ~35 ms com 61** (~0,5 ms/item),
  ida e volta da ponte incluída.

### Marcadores

```javascript
var m = sequence.markers.createMarker(inicioEmSEGUNDOS, nome, duracaoEmSEGUNDOS);
m.comments = "…";
m.setColorByIndex(0);        // 0..7, 0 = verde
```

⚠️⚠️ **SEGUNDOS**, não ticks — no app onde tudo o mais é tick.

✅ **Os markers do Avid levados ao Premiere — `confirmado` (27.0 Mac, 2026-11-15):** os 23 da PRODA_CORTE.00.2 (lidos da
bin, `avb/estruturas.md` "Markers da TIMELINE"), criados com `createMarker` na sequência que o `importSequences` trouxe
(achada pelo id em `novas`), 23 de 23, cores e tempos conferidos na régua. Cor Avid → índice: Green 0, Red 1, Magenta 2,
Yellow 4, White 5, Blue 6, Cyan 7; ⚠️ **o Premiere não tem preto** — o Black do Avid vai como White (dito). O marker de
sequência não tem trilha: o nome leva o comentário do Avid e o comentário leva "Avid · V1 · usuário · data".
Ciclo Assist: `host.jsx` `cicloMarcarSequencia`, `carta/importar_premiere.plano_de_marcadores`.

### ⭐ A receita completa do XMP privado

```javascript
ExternalObject.AdobeXMPScript = new ExternalObject('lib:AdobeXMPScript');
project.addPropertyToProjectMetadataSchema(NOME, "Rótulo", 2);      // ANTES de ler E de escrever
var xmp = new XMPMeta(alvo.getProjectMetadata());
xmp.setProperty(kPProPrivateProjectMetadataURI, NOME, valor);
alvo.setProjectMetadata(xmp.serialize(), [NOME]);
```

⭐ **Dois escopos:** `sequence.projectItem` (por sequência) ou `project.rootItem` (por projeto).
⭐ **Versione pelo NOME do campo** (`MeuDadoV1`) — migração sem migrar dado.

## 🆕 Monitor Source e taxa da sequência — o que o Ciclo Assist passou a usar (23.2, 2026-09-21)

Escrito para a aba Busca do Ciclo Assist responder dentro do Premiere. ⚠️ **Os dois primeiros
são `hipotese`: escritos contra a documentação da Adobe e exercitados só com o painel
SIMULADO** (Chrome headless com `__adobe_cep__` injetado). Falta rodar no Premiere de verdade
— quando rodar, promover e trocar esta nota.

| chamada | o que faz | confiança |
|---|---|---|
| `app.sourceMonitor.openProjectItem(projectItem)` | põe o item no monitor **Source** | `hipotese` (23.2) |
| `app.sourceMonitor.openFilePath(caminho)` | ⛔ **IMPORTA o arquivo no projeto** — é escrita | `hipotese` (23.2) |
| `app.project.activeSequence.timebase` | ticks por quadro da sequência ATIVA | `inferido` (23.2) |

#### ⭐⭐ MEDIDO 2026-09-22 — pôr o Source num ponto, e a coluna Descrição (`confirmado`, 23.2, Windows)

Instrumentos: `_CICLO ASSIST/spikes/o_source_e_a_descricao.py` e `spikes/o_source_no_tc.py`
(extensão invisível, projeto descartável).

- ✅ `app.sourceMonitor.openProjectItem(item)` **funciona** (promovido de `hipotese`).
- ⛔ **`app.sourceMonitor` NÃO posiciona.** Por reflexão, os métodos são só `closeAllClips`,
  `closeClip`, `getPosition`, `getProjectItem`, `openFilePath`, `openProjectItem`, `play`.
  `setPosition` → `ReferenceError`.
- ⭐⭐ **Quem posiciona é o QE:** `app.enableQE(); qe.source.player.scrubTo('HH:MM:SS:FF')`
  (devolve `true`). Métodos do player: `scrubTo`, `startScrubbing`, `endScrubbing`,
  `getPosition`, `play`, `stop`, `step`, `setLoopPlayback`, … (e propriedades de estatística
  de reprodução). **É o que o Media Composer 2025.6 não tem** (`SetPosition` ausente).
- ⛔⛔ **O TC do `scrubTo` é TEMPO DESDE O INÍCIO DO CLIPE, não o TC do clipe.** Clipe com
  `MediaStart = 01:00:00:00` (e `startTime()` = 3600 s): na cabeça, `getPosition()` = 0 e o TC
  do QE = `00:00:00:00`; `scrubTo('00:00:04:00')` → 4 s; `scrubTo('01:00:04:00')` → **3604 s**.
  Quem mandar o TC do clipe manda a agulha para uma hora depois.
- ⛔ **E não há limite:** 3604 s foi aceito num clipe de **10 s**, sem erro. Limitar é de quem chama.
- ⚠️ A 23,976 os quadros do TC são na base **24**: `00:00:04:00` → 4,004 s; `00:00:04:12` → 4,5045 s.
- ⚠️ Um número solto (`scrubTo('4')`) é lido como **QUADROS** (0,16 s a 25 fps).
- ⚠️ `closeAllClips` + `openProjectItem` do mesmo item **não volta ao zero**: o Premiere lembra a
  posição por clipe.
- ⚠️ Não medido: subclipe (o zero é o do subclipe ou o do master?), drop-frame, macOS.

**A coluna "Descrição" do painel de projeto** é `Column.PropertyText.Description` no metadado
PRIVADO do projeto (`http://ns.adobe.com/premierePrivateProjectMetaData/1.0/`), e o nome
interno não depende do idioma da interface. Ela está entre as colunas de
`app.project.getProjectPanelMetadata()`; escrita com `setProjectMetadata(xmp, ['Column.PropertyText.Description'])`
(os DOIS argumentos), foi lida de volta igual, e no `.prproj` salvo aparece como
`<ClipLoggingInfo>…<Description>texto</Description>` do clipe.

- ⛔ **`setProperty(NS, campo, "")` NÃO apaga** o campo: o texto anterior continua (medido,
  `spikes/source_e_descricao_no_premiere.py`). Quem apaga é `x.deleteProperty(NS, campo)` +
  `setProjectMetadata(x.serialize(), [campo])`. ⚠️ O que o editor faz ao apagar pela
  INTERFACE (vazio ou ausente): não medido — trate os dois como vazio.
- ⚠️ **`createSubClip` COPIA a Descrição do master** para o subclipe no momento em que o cria.
- ⭐ Uso no Ciclo Assist (`cicloDescrever`): compare-and-set — grava só com o campo vazio ou
  igual ao que ele mesmo gravou da última vez; texto do editor nunca é sobrescrito. Conferido
  no 23.2: escrito, respeitado, apagado → preenchido de novo, subclipe intocado.

⛔⛔ **`openProjectItem` e `openFilePath` não são alternativas de gosto.** O segundo traz o
arquivo para dentro do projeto do editor: num plugin cujo portão separa quem LÊ de quem
ESCREVE (ADR 0008 do Ciclo Assist), usar `openFilePath` para "só mostrar um clipe" faz uma
leitura mexer na bin dele. Quem só quer mostrar precisa do item que JÁ está no projeto.

⭐⭐ **O Premiere não tem taxa de PROJETO — quem tem taxa é a SEQUÊNCIA.** `timebase` é o
número de ticks por quadro, e o tick do Premiere é **1/254.016.000.000 de segundo**
(`CICLO_TICKS`), logo:

```
fps = 254016000000 / timebase          →  10594584000 = 24000/1001 (23,976)
                                          10160640000 = 25
```

⚠️ Os dois números passam como **texto** para fora do ExtendScript: 254.016.000.000 não cabe
num inteiro de 32 bits, e arredondar erra a taxa por inteiro. ⛔ E **sem sequência ativa não
se inventa taxa**: chutar 25 fps erra todo material 23,976.

⚠️ **Custo não medido:** `getProjectMetadata()` item a item (é o único lugar onde mora o
recorte de um subclipe — ver `subclipe-e-merged-clip.md`) numa varredura recursiva do projeto
inteiro. Roda na thread principal do Premiere, então o custo é congelamento de UI, não só
espera. Quem varrer assim deve contar quantos itens olhou e registrar o número aqui.

## 🆕 Laboratório de Mídia, casos B01–B06 — Premiere Pro 25.6.5, macOS 15.6.1, 2026-10-06

Operado de fora pela ponte do laboratório (`laboratorio-de-midia/lab/bancadas/premiere.py`); resultados em
`laboratorio-de-midia/resultados/B0*/PREMIERE.md`. Tudo `confirmado` nesta versão e sistema.
- 🆕 ⛔ **`projectItem.select()` só DESTACA (23.6.0, Windows, 2026-10-21):** a bin fica marcada no painel Project, mas
  `app.getCurrentProjectViewSelection()` devolve VAZIO se a vista ativa for outra (o foco estava na timeline). Ativar a
  vista (clique na aba Project) e então `select()` → a seleção volta certa. Um app que dependa da seleção lida pela API
  deve dizer "nada selecionado" com cuidado: pode ser só a vista errada.
- 🆕 ✅ **Premiere 26.5, Windows 11 (2026-10-22, ponte do Órbita, bancada `laboratorio-de-midia/lab/bancadas/demo_multicam.py`):**
  `app.newProject(caminho)` FUNCIONA chamado com o Premiere na tela inicial (pasta existente, caminho em D: com espaços):
  devolve e abre o projeto em ~1 s — o "Unknown error exception" abaixo é do 23.6, não da API. **confirmado** (2 de 2: a 2ª no **26.5.2**, 2026-11-18, ponte direta do kit do curso `2 ATIVOS/_MANUAL DE SOBREVIVENCIA`, caminho em C: dentro do `%TEMP%`). No mesmo 26.5.2, `app.project.save()` + `closeDocument(0, 0)` + `app.quit()` fecharam o Premiere **sem diálogo** (o processo some em < 8 s) — a receita medida no 23.2 vale no 26.
- 🆕 ⛔ **Premiere 23.6.0, Windows 11 (2026-10-21, ponte do Órbita):** `app.newProject(caminho)` LANÇA "Unknown error
  exception" com a pasta existente, em qualquer caminho (D: com espaços, barras `/`, `C:/OrbitaTeste/teste.prproj`), chamado
  com o Premiere na tela inicial. Contorno medido: criar pela tela (New Project → só o NOME, digitado por Unicode) e mover com
  `app.project.saveAs(caminho)` — funcionou, sem diálogo. `importFiles` de 50 arquivos (mp4 + WAV, sem os `._`) não abriu
  diálogo nenhum.
- `app.newProject(caminho)` devolve **false se a pasta não existe** (não cria) — e o `app.project` fica sem projeto
  (`rootItem` null): criar a pasta antes e conferir `app.project.path`.
- ⛔ `importFiles(..., suppressUI=true, ...)` **mostra o diálogo "File Import Failure" mesmo assim** e TRAVA o script até
  alguém clicar OK; depois devolve `true` com o arquivo de fora. Visto com o OP-Atom de VÍDEO escrito pelo ffmpeg
  (DNxHD, "Unsupported format or damaged file" — o Resolve abre o mesmo arquivo). Contar os itens, nunca o retorno.
- `getProjectMetadata()` → `Column.Intrinsic.MediaStart/MediaEnd/MediaDuration/MediaTimebase/VideoInfo/AudioInfo`. O DF vem
  `01;00;59;15` (`;` em TUDO; não há campo de drop-frame). Áudio puro: início em AMOSTRAS (`01:00:00:00000`). Depois da
  **meia-noite volta a 00** (`End TC` `00:00:04:24`; o Resolve segue em `24:…`).
- `AudioInfo` diz o MAPEAMENTO do item: estéreo = "Stereo mapped to 2 Mono" (o arquivo não muda; o Premiere o trata como 2
  clipes mono, em A1 e A2), XDCAM "8 Channel mapped to 8 Mono", e **tudo de 4 canais para cima vira "N Mono"** (mov
  polifônico, mov com um mono por trilha e WAV — até o WAV 7.1). `getAudioChannelMapping` é PROPRIEDADE (chamada como
  função: "AudioChannelMapping() is not a function").
- ⚠️ **CORRIGE (2026-10-06, mesmo dia):** os dois itens acima foram medidos com a preferência *Timeline → Default Audio
  Tracks* em **Mono** para tudo (configurada pelo autor na máquina; não é o padrão). Refeito com o padrão **Use File**:
  mov, mp4 e WAV estéreo entram **"Stereo"** (1 trilha) e o render sai L/R certos; o **MXF OP1a estéreo continua "Stereo
  mapped to 2 Mono"** (o Premiere trata o áudio de MXF por canal, independente da preferência) e sai L = R no render;
  4+ canais = "N Mono" também com Use File; 2 mono por trilha = "2 Mono". No arquivo de preferências
  (`~/Documents/Adobe/Premiere Pro/25.0/Profile-*/Adobe Premiere Pro Prefs`):
  `BE.Prefs.DefaultChannelMapID_95_<Mono|Stereo|51|MultiMono>` = `0551e2a0-6da1-4691-800e-b3ded5ca94f7` (**Use File**) ×
  `b7f34681-bada-438d-83d6-7f12236011ba` (**Mono**) — medido antes/depois da troca na tela. ⭐ Lição: um resultado de
  mapeamento de áudio do Premiere vale **junto com essas 4 preferências**; ler o arquivo antes de afirmar.
- ⚠️ No render (`exportAsMediaDirect`, "Match Source – Apple ProRes 422"), o estéreo mapeado em 2 mono sai **L = R = canal
  1 + canal 2**. Se o mapeamento "2 Mono" é o padrão do Premiere ou desta máquina: `pendente`
  (`BE.Prefs.DefaultChannelMapID_95_Stereo` existe; valor não decifrado).
- `createNewSequenceFromClips` começa em **00:00:00:00** e com 3 V + 4 A; o nome perde a extensão (`s.name = …` depois
  devolve). `setZeroPoint(ticks)` põe a régua no TC do clipe. Ticks: 254016000000 por segundo; `timebase` = ticks/quadro.
- Quadro: `setPlayerPosition(String(k*timebase))` + QE `exportFramePNG(q.CTI.timecode, caminho)` (acrescenta `.png`).
  ⚠️ **O `CTI.timecode` do QE é RELATIVO ao início da sequência** (00:00:04:24 com a régua em 01:00:04:24): conferir pela
  posição em ticks do DOM. ⚠️ **Caminho relativo no `exportFramePNG` vai para a pasta DO PREMIERE** (o arquivo "some").
  Medido: 309 stills, o quadro exato em todos (25.6.5).
- `exportAsMediaDirect(saida, preset, 0)` devolve "No Error"; ProRes "Match Source" de 10 s em ~0,3–0,6 s.
  ⛔ **No Windows (23.2, 2026-10-10) o preset nulo dá "Illegal Parameter type"**: passar o arquivo
  `C:\Program Files\Adobe\Adobe Premiere Pro <ano>\Settings\EncoderPresets\ConsolidateAndTranscode\Match Source - Apple ProRes 422.epr`
  (no Mac, dentro do `.app`: `Contents/Settings/…`) — `laboratorio-de-midia/lab/bancadas/premiere.preset_prores`.
  ⚠️ **Estado preso do Windows (23.2, 2026-10-10):** depois de horas de uso (Resolve renderizando na mesma máquina),
  TODO export por script passou a falhar — `exportAsMediaDirect` → "Disk Full / Exporter returned bad result" (ProRes) ou
  "Unknown Error" (H.264), em qualquer disco; `exportFramePNG`/`JPEG` sem arquivo — com o Premiere reaberto, em projeto
  novo, nos dois renderizadores, enquanto a INTERFACE exportava normal. Disco, permissão de escrita, TEMP, diálogo e
  scratch disk descartados. **Reiniciar o WINDOWS resolveu** (2026-10-10, B17: ProRes 288 quadros "No Error" em 0,6 s;
  PNG gravado). Reabrir só o Premiere não basta. Causa exata não isolada (suspeita: GPU presa pelo Resolve).
  ⛔ **SMART RENDERING (2026-10-11, B19):** o "Match Source – Apple ProRes 422" sobre fonte ProRes 422 COPIA quadros da
  fonte onde o Premiere acha que pode — o Warp Stabilizer saiu ausente nos quadros 40–112 (idênticos à fonte), presente no
  resto. Referência de efeito: renderizar com "Match Source – Apple ProRes 4444" (outro codec, sem cópia). A janela de
  progresso se chama "Encoding <sequência>" (o vigia do laboratório espera por ela).
- ⚠️ 23.2 (2026-10-10, laboratório B14/B16): `setInPoint`/`setOutPoint` em SEGUNDOS arredondam por ponto flutuante — o
  clipe sai com N − 1 ou N + 1 quadros conforme o N (e diferente para arquivo e sequência). **Usar um `Time` com `ticks`
  exatos** (`var t = new Time(); t.ticks = String(n * 10594584000)`), também no `overwriteClip`. A API encaixa o in na
  grade da timeline (7 quadros de 100 qps → 4,17). Velocidade: `qe…getItemAt(i).setSpeed(v, "", false, false, false)`
  (sem ripple, a duração fica; no QE o `getItemAt` conta os vãos "Empty"); `trackItem.getSpeed()` confirma. O nome dado
  ao clipe na timeline (`trackItem.name = …`) vai para o `SubClip/Name` do XML. ExtendScript é ES3 (sem `reduce`). E a Opacity no padrão NÃO vai para o `.prproj` (`DefaultOpacity` = true na
  cadeia, nenhum componente) mesmo depois de `setValue` pela API: máscara por XML precisa criar o componente
  (molde `laboratorio-de-midia/lab/moldes/opacidade-23.2.xml`).
- **Escala:** o padrão desta máquina é NÃO escalar um clipe maior que a sequência (o centro em tamanho real). "Scale to
  Frame Size" não é método do `TrackItem` do DOM no 25.6.5 ("is not a function"); é o do QE:
  `qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0).setScaleToFrameSize(true)` (sem o parâmetro: "Not
  Enough Parameters"). Com ele o encaixe é exato (4K DCI, scope, vertical, anamórfico PAR 2 desespremido).
- Sync de som direto à mão: `overwriteClip` da câmera em `videoTracks[0]` no tempo dela e do BWF em `audioTracks[2]` no 0
  → o BWF de 4 canais ocupa A3–A6; o render põe o som direto exatamente onde o TC manda e os 4 canais na mistura.
- Projeto salvo pelo 25.6.5: `PremiereData 3`, `Project 43`, 58 classes — a impressão digital por classe de cada caso está
  em `laboratorio-de-midia/resultados/B0*/prproj/` (para o estudo de downgrade 2026 → 2025 → 2023).

### 🆕 Premiere Beta 27.1.0 ("2027"), macOS, 2026-10-07 — laboratório
- ✅ **A ponte CEP sobe no Beta 27.1.0** (o app ainda traz o `CEPHtmlEngine`; `PlayerDebugMode` ligado em CSXS.11/12/13). O app fica em `/Applications/Adobe Premiere Pro (Beta)/Adobe Premiere Pro (Beta).app`; as preferências em `~/Documents/Adobe/Premiere Pro (Beta)/27.0/Profile-*/Adobe Premiere Pro (Beta) Prefs` (pasta e arquivo próprios). Instalação nova = Use File / sem escala.
- Os 6 casos do laboratório: **medição idêntica ao 26.0.2** (quadro, TC, DF, canais nos renders, escala).
- ⚠️ **O 27 TRADUZ o texto dos metadados** (`AudioInfo`: "48000 Hz - 24 bits - Estéreo mapeado para 2 Mono", "Canal 8 mapeado para 8 Mono"); o 26.0.2 com a interface em português ainda escrevia em inglês. Quem lê canal/formato desse texto tem de ler os dois idiomas — ou usar `getAudioChannelMapping` (número, não texto).
- ⚠️ **Nomes de efeito e transição pela API saem no IDIOMA do app** (`getVideoEffectList`, `getVideoEffectByName`): "Cor de Lumetri" × "Lumetri Color"; e o 27 renomeou dezenas ("Desfoque gaussiano", "Transição para preto"…). `addVideoEffect` por nome QUEBRA entre máquinas e versões. O `matchName` do componente (`AE.ADBE Motion`) não muda.
- API (inventário por `reflect`, `laboratorio-de-midia/resultados/API_PREMIERE/`): **25.6.5 = 26.0.2** em todos os objetos do DOM e do QE; o 27.1 acrescenta só `app.getLookInfo` (propriedade), e na lista de efeitos chegam efeitos de cor novos ("Transformação LUT", "Matiz/saturação", "Cor e contraste", "Contraste", "Cor do filme", "Máscara HSL", "Misturador de cores", "Meios-tons", "Tonalidade gradiente"). Cor pela API (já no 25/26): `SequenceSettings.workingColorSpace`/`workingColorSpaceList`/`autoToneMapEnabled`/`autoInputGamutCompressionEnabled`/`gamutMappingControls`, `Project.setLogColorManagement`/`applyLumetriPreset`/`setLUTInterpolationMethod`/`setGraphicsWhiteLuminance`, `ProjectItem.setOverrideColorSpace`/`getColorSpace`/`getInputLUTID`, `FootageInterpretation.setInputLUTFromFilePath`. Títulos: `Sequence.importMGT`; legenda: `createCaptionTrack`. ⛔ Ainda NÃO há verbo para criar multicam nem merged (o QE só liga/troca ângulo: `setMulticam`, `canDoMulticam`).
- ⛔ **`app.project.save()` SEM projeto aberto (tela inicial) DERRUBA o 25.6.5** ("Ocorreu um erro", 2 de 2; o try/catch não segura). Conferir `app.project.path` antes.
- O `quit` do Beta leva mais de 60 s; o AppleScript para o Beta pode não responder — esperar o processo sair.
- 🆕 **Montar projeto pela API (B07 do laboratório, 25.6.5 / 26.0.2 / 27.1, 2026-10-07)** — `laboratorio-de-midia/lab/bancadas/premiere_projeto.py`:
  - ⛔ `qe.project.getVideoEffectByName(nome)` devolve um objeto ATÉ PARA NOME QUE NÃO EXISTE (com `name` vazio) e o `addVideoEffect` dele não faz nada, calado: conferir `e.name`. E o nome pode ser de OUTRO efeito: no 26.0.2 em português "Gaussian Blur" é o do plug-in FilmImpact (`AE.Impact_Blur_FX`); o da Adobe virou "Desfoque Gaussiano (herdado)" (`AE.ADBE Gaussian Blur 2`). Conferir o `matchName` do componente que entrou — achado pela diferença antes/depois (o efeito novo NÃO é sempre o último; no áudio entra antes dos fixos).
  - `Sequence.importMGT(caminho, ticks, trilhaV, trilhaA)` PÕE o gráfico e devolve `null`; o "Basic Title.mogrt" é texto NATIVO (`AE.ADBE Graphic Group` + `AE.ADBE Text`) e o `getMGTComponent()` dele é `null`.
    ⛔ **No 26.5.2 (Windows, 2026-11-20) o mesmo `importMGT` põe um gráfico VAZIO** (sem `AE.ADBE Text`): a camada de texto sai do menu Graphics and Titles › New Layer › Text — `protocolos/prproj/titulo-essential-graphics.md`, "No Premiere 26.5".
  - `createCaptionTrack(itemDoSrt, 0, Sequence.CAPTION_FORMAT_SUBTITLE)` funciona nas três. ⚠️ O **27.1 desenha a legenda no `exportFramePNG`** do QE; o 25/26 não. No RENDER (`exportAsMediaDirect` com o preset ProRes "Match Source", `ADBECaptionExportOption` = 0 nas três) nenhuma grava a legenda na imagem — a opção de legenda do export manda.
  - `qeItem.addTransition(tr, true, "00:00:01:00")` pôs uma dissolução de 13 quadros (0,52 s) a 25 q/s, nas três versões.
  - O QE lista os VÃOS entre transições como transições de nome vazio (`getTransitionAt`); logo depois de montar, a lista pode vir sem a transição — ler do projeto salvo e reaberto.
  - ⚠️ O Beta 27.1, aberto, reaproveitou o CONTEÚDO antigo de um `.srt` reimportado no mesmo caminho (cache por caminho): insumo regravado vai em caminho novo.
  - Efeitos, Movimento/Opacidade com keyframes, Recorte, transição, subclipe, bins, bin inteligente, rótulos e marcadores: estrutura igual nas três e imagens iguais (25 = 26 pixel a pixel; 27 a ≥ 55 dB).
- 🆕 ⭐ **Diálogos do Premiere SEM o autor (macOS, 2026-10-07)** — `laboratorio-de-midia/lab/bancadas/vigia_dialogos.py`:
  - Os diálogos do Premiere (25/26/27) NÃO são `window` para a acessibilidade: são UI elements com subrole `AXDialog`, e os BOTÕES não são expostos ("Carregar projeto", "Converter projeto", "Importar arquivos"…). A janela principal também é `AXDialog` (título = caminho do .prproj). O que funciona: conferir que o `AXFocusedWindow` do processo tem o título conhecido, `set frontmost to true` e `keystroke return` (o botão padrão: OK no "Carregar projeto"/"Converter projeto"). O Terminal precisa da permissão de Acessibilidade.
  - O "Relatório de Problemas para Adobe Premiere…" do macOS (processo `Problem Reporter`) é janela comum: `click button "OK"` (nunca Reabrir). ⚠️ O texto dele tem quebras de linha — quem separa registro por linha se perde. E título acentuado vai para o AppleScript como é, não com o `\u00f3` do JSON.
  - O "Ocorreu um erro" da ADOBE (processo `AdobeCrashReport`) não expõe NADA à acessibilidade; enquanto ele está aberto o Premiere morto segura a conexão da ponte (a bancada esperou 2 min 40 s). Fechar o processo = "Não enviar".
  - `kill -TERM`/`SIGABRT` no Premiere = queda com o relatório da Adobe; o Beta 27.1 não sai pelo `app.quit()` nem pelo AppleScript.
  - Queda provocada no meio de uma rodada: vigia fecha o relatório em 5 s, a bancada (`premiere.retomar`) reabre e refaz o caso — 61 s ao todo.
- 🆕 ⛔ **Beta 27.1: o projeto que foi 27 → 26 (rebaixado, salvo pelo 26) → 27 DERRUBA o Beta ao exportar o quadro do ARRIRAW** (`exportFramePNG`; `DoThrowNullPtrException` em `ML::ConformFrameToOutput`) — 3 de 3. O mesmo ARRIRAW no projeto nativo do 27 exporta.

### 🆕 Premiere 26.0.2 (2026), macOS, os mesmos casos — o que MUDA do 25.6.5 (2026-10-06)
- ⛔ **CORRIGE (mesmo dia, REMEDIDO):** a 1ª rodada do 26.0.2 estava com *Default Media Scaling* = "Set to Frame Size" (preferência da máquina, chave `BE.Prefs.General.DefaultSetToFrameSize`). Refeitas as DUAS versões com as preferências zeradas (2026-10-06 23:43–23:52; lidas no arquivo do perfil e gravadas em cada resultado): **o 26.0.2 é idêntico ao 25.6.5 em todos os 6 casos**, inclusive a escala. Ler `DefaultSetToFrameSize`, `DefaultScaleToFrameSize` e `DefaultChannelMapID_*` no arquivo do perfil ANTES de medir (`laboratorio-de-midia/lab/bancadas/premiere.py` → `preferencias()`).
- Quadro, TC (inclusive meia-noite → 00), taxas, DF e o mapeamento de áudio (com Use File): **iguais**.
- **Escala (remedida com as preferências zeradas):** igual ao 25.6.5 — um clipe maior posto (`overwriteClip`) numa sequência HD fica em **tamanho real, cortado**; o QE `setScaleToFrameSize(true)` encaixa exato (108/108 stills iguais aos do 25). ~~O 2026 encaixa sozinho / o QE escala por cima~~: era a preferência "Set to Frame Size". Com ela ligada, o projeto ganha um efeito Motion (`VideoFilterComponent`, `VideoComponentParam`, `PointComponentParam`) que sem ela não aparece.
- O nome do item importado pode ser o do CLIPE e não o do arquivo (um OP-Atom costurado entra como "B01" nos 3 itens):
  identificar itens pelo `getMediaPath()`, nunca pelo `name`.
- A extensão invisível (ponte) sobe no 26.0.2 do mesmo jeito (CSXS.12 com `PlayerDebugMode`).
- ⚠️ **"O Premiere ainda está aberto?" no Mac (2026-10-06):** `pgrep -f "Adobe Premiere Pro 2025.app/Contents/MacOS"` dá falso positivo — o `AdobeIPCBroker` leva o caminho do Premiere nos ARGUMENTOS e o `crashpad_handler` mora em `Contents/MacOS`, e os dois ficam vivos depois que o Premiere fecha. Ancorar no executável principal: `pgrep -f "^/Applications/Adobe Premiere Pro 2025/Adobe Premiere Pro 2025.app/Contents/MacOS/Adobe Premiere Pro 2025( |$)"`. Windows: `pendente`. E o `tell application "Adobe Premiere Pro 2026" to quit` ficou 60 s sem resposta com o 26.0.2 parado na tela inicial; `app.quit()` pela ponte fechou na hora.


## 🆕 2026-10-19 — MONTAR uma timeline do Avid no Premiere pela ponte (De Lá Pra Cá, Premiere 23.6.0 Windows)

`confirmado` (produto: `_DeLaPraCa/plugins/media-composer/servico/ui/premiere_host.jsx` › `dlpcMontar` + `premiere_montagem.py`):
- ⭐ **Subclipe SÓ DE VÍDEO e SÓ DE ÁUDIO** (`item.createSubClip(nome, "0", fimTicks, 0, takeVideo, takeAudio)` + `moveBin`)
  resolve a regra do áudio vinculado (`overwriteClip` A/V põe o áudio na trilha de mesmo número): o vídeo cai só no V,
  o áudio só no A. In/out no SUBCLIPE com `Time` em ticks (`setInPoint(t, 4)`), `overwriteClip(sub, t)`, depois
  `trackItem.end = t` exato. `createNewSequenceFromClips` com o 1º vídeo (a taxa dele) + limpar + `setZeroPoint`.
  Trilhas a mais: QE `addTracks(nV, depoisV, nA, 1, depoisA, 0, 0, 0)` (3 V + 4 A → 10 A). Marcador: `createMarker(seg)`.
- MEDIDO: LAB_CORTES_01 (AAF do Avid 25.6) **8/8 exatos** em início, duração e entrada (ticks); PRODUCAO-A
  **302/302 planos em ~25 s, 109/109 vídeo exatos**; os que diferem só no fim são crossfades de áudio (o plano seguinte
  entra por cima: corte seco no lugar certo).
- ⛔ **ÁUDIO: a entrada é arredondada PARA BAIXO** depois de passar a amostras — o quadro exato às vezes cai uma fração
  abaixo (WAV 48 kHz: 498 → 497; +0,25 q ainda 497; +0,5 e +0,75 → 498). O vídeo não. Folga de **0,6 quadro** no áudio.
- ⛔ Sequência criada a partir de um item SÓ DE ÁUDIO nasce em outra base de tempo (a do áudio): crie a partir de um vídeo.
- ⛔⛔ **O ExtendScript NÃO se recarrega sozinho**: reavaliar o `host.jsx` sem conferir o retorno deixou o Premiere com o
  script antigo ("EvalScript error." numa função que existia no arquivo; a conferência "dlpcEstado existe" passava com
  as funções velhas). A ponte do produto manda a VERSÃO (assinatura) do script em cada pedido e recarrega quando muda
  (e a da própria página, que se dá `location.reload()`). Medido: mudar o `host.jsx` no disco → a ponte recarregou sem
  reiniciar nada.

## 🆕 2026-10-08 — Project Manager, máscaras e diálogos (Premiere 26.0.2 Mac, 23.2 Windows)
- `app.projectManager` (opções: `clipTransferOption = CLIP_TRANSFER_COPY`, `destinationPath`, `excludeUnused`, `includePreviews`,
  `renameMedia`…) + `process(app.project)` = "Coletar arquivos e copiar" sem a tela; leva a pasta `<projeto> Masks` junto.
- ⚠️ `qe…exportFramePNG` NÃO mostrou o efeito das máscaras (objeto e forma) no 26.0.2; o render (`exportAsMediaDirect`) mostra.
  No 23.2 o `exportFramePNG` mostra Track Matte e máscara (PNG COM ALFA: compor sobre preto para medir).
- QE `getVideoEffectByName("Track Matte Key")` + `addVideoEffect`; os parâmetros do DOM têm DOIS-PONTOS no nome ("Matte:",
  "Composite Using:"): `setValue(2)` = Vídeo 2, `setValue(1)` = luma. `track.setMute(1)` funciona; exportar com a trilha
  desligada deu PNG vazio.
- PowerShell `-File script.ps1 -Lista 1,2,3` NÃO passa lista (vira texto): receber texto e separar.

## 🆕 ⭐⭐⭐ PREMIERE → PREMIERE NO 26.5.2 (Windows, 2026-10-22): os dois caminhos de relink, medidos com o R04

Laboratório pedido pelo autor ("trazer um prproj para o De Lá Pra Cá e ele criar a sequência no Premiere, ou do próprio
Premiere carregar uma sequência para relink"). Premiere **26.5.2 build 5**, Windows 11, renderizador Software Only.
Caso: `WSP-DLPC_2.prproj` (PRODUCAO-C, PRODC_CORTE02, 80 planos + 9 nests, 48 arquivos de imagem + 21 sons) com
TODA a mídia "mudada de lugar" para um disco que não existe (`Z:\EDICAO_PRODC\MIDIA_ANTIGA\…`, mesma árvore). O mapa
caminho → arquivo veio do casamento do De Lá Pra Cá (`/receber/prproj/analisar` → `midias[].arquivo`; os sons por
`prproj_para_drt.relocar_sons`, que não saem na resposta HTTP). Roteiros: scratchpad da sessão (`pp/passo1..5.py`).
- ✅ **As DUAS pontes CEP sobem no 26.5.2** (a invisível do De Lá Pra Cá: `/premiere/estado` conectado; a livre do
  laboratório: 7–9 s depois de abrir). Fechar o Premiere na tela inicial: `WM_CLOSE` na janela principal, sai em 2–3 s.
- ✅ **A) Cópia relinkada + `importSequences` num projeto novo:** 50 s; entram a sequência e as 9 aninhadas (10), 80 itens,
  0 offline. **Corte idêntico ao original** (aberto de uma cópia): 170 itens nas 10 sequências com início/fim/entrada/
  saída iguais em ticks, mesmo arquivo e mesmo número de componentes por clipe. Imagem: **143/144** pela referência
  (média 0,983) com a conferência do app alimentada por `exportFramePNG` (144 quadros em 82 s; todos gravados).
- ⛔ **`importSequences` RELIGA SOZINHO, CALADO:** a cópia ainda apontava os 21 sons para `Z:` (FilePath, ActualMediaFilePath
  e RelativePath) e eles entraram ONLINE no lugar certo de `D:`. O `openDocument(…, true, true, true)` do mesmo arquivo
  NÃO religa (69 offline). Mecanismo `hipotese` (cache de mídia que lembra o arquivo pela identidade, ou a troca de raiz
  deduzida dos vídeos já relinkados). Regra: depois de importar, conferir o CAMINHO de cada item contra a decisão do
  casamento — o Premiere pode ligar um arquivo que o app não escolheu (o empate é do editor).
- ✅ **B) Projeto do editor ABERTO + `projectItem.changeMediaPath(arquivo, true)` no lugar:** abrir 1,3 s sem diálogo
  (69 offline) → 48 imagens em 6,4 s + 21 sons em 0,9 s, nenhuma falha, **0 offline**; salvo. Imagem: **143/144**
  (média 0,983), o MESMO ponto do caminho A → o ponto é do render do 26, não do relink.
- O ponto que não confere nos dois: 1º quadro do LOU_7310 na V2 (00:00:01:03, 0,72–0,73), plano com zoom/posição em
  keyframe num corte rápido; o quadro do Premiere é o da referência com um leve deslocamento de enquadramento.
- ⚠️ Para o desenho do app: o casamento classifica o arquivo achado pelo nome fora do lugar declarado como `realocado` =
  "sem original" (regra do PRODUCAO_B: cópia de proxy). Num relink de mídia que só MUDOU DE LUGAR isso marcaria 47 planos
  como "sem original" — decisão do autor (organograma).
  ✅ DECIDIDO (mesma noite): provar e aceitar — ver abaixo.
- 🆕 ⭐⭐ **NO PRODUTO (De Lá Pra Cá `5421693`, mesma noite, 26.5.2 Windows, pilotado pela janela do app):** o caminho A virou
  função (decisões do autor: sempre cópia, original intacta; "mudou de lugar" = provar e aceitar; entradas "Carregar a
  sequência aberta" e arrasto de dentro do Premiere). Medido com o R04 "mudado" para `Z:` (`03 CASOS/REAL/R04 PRODUCAO-C/P2P/`):
  80/80 planos nos originais, 69 de 69 clipes nos arquivos da lista, 143/144 pela referência (o mesmo ponto do laboratório),
  a sequência original seguiu com os 133 clipes em `Z:` (intacta). Achados novos, todos `confirmado` no 26.5.2:
  - ⭐ o **`sequenceID` do ExtendScript É o `ObjectUID` da `<Sequence>` no XML** (`b07964be-…` nos dois) — o arrasto e a
    sequência ativa casam com o arquivo salvo pelo id, sem depender do nome;
  - ⛔ **`importSequences` num projeto que tem bins de MESMO UID das da cópia** (a cópia vem do próprio projeto): os clipes
    novos NÃO entram na raiz — caem DENTRO da bin existente do editor (01_Footage…), ao lado dos antigos. Quem procura "o que
    entrou" só na raiz não acha nada (o placar deu "0 de 0"); procurar os itens novos em TODO o projeto e movê-los;
  - ⛔ **DEDUPLICAÇÃO:** se o projeto já tem um item com o MESMO arquivo (uma cópia anterior), a sequência nova usa o item que
    já existe e nenhum item novo nasce (a rodada 3 deu "0 clipes"). O item do editor que aponta para OUTRO caminho (o `Z:`
    offline) não é reaproveitado — por isso a original fica intacta. Regra: a conferência dos caminhos parte dos CLIPES das
    sequências criadas (`clip.projectItem`, uma vez por `nodeId`), nunca dos "itens novos";
  - "projeto alterado": não há API; o título da janela principal termina em ` *` (matriz de plataforma, G2). O 26 marca o
    projeto como alterado logo ao abrir um projeto com mídia offline;
  - `openDocument(c, true, true, true)` abre o projeto com 69 offline em 1,3 s sem diálogo, e com outro projeto aberto o 2º
    abre AO LADO, sem perguntar sobre salvar o 1º; `app.project` passa a ser o recém-aberto;
  - ⭐ (26.0.2 Mac, 2026-11-14, Ciclo Assist `cicloAtivarProjeto`/`cicloFecharProjeto`) **`openDocument` de um projeto que JÁ
    está aberto só o põe à frente** (não abre outro, não pergunta) — e devolve `false` mesmo tendo ativado. `app.projects`
    lista os abertos (`numProjects`, `.path`). ⛔⛔ **`closeDocument(0, 0)` de um projeto que está ATRÁS põe OUTRO à
    frente** (não o que estava: medido, o 3º aberto) — reativar quem estava. ⛔ **Clicar numa aba "Compartimento" de bin
    de OUTRO projeto aberto o põe à frente** (o `app.project` muda; o botão importou no projeto errado — de teste);
  - o arrasto de uma sequência do painel Project do 26.5.2 para o app traz o `dynamiclinksourcelist` (o mesmo do 23.6);
  - a sequência ativa depois de importar NÃO muda sozinha: `openSequence(id)` no fim deixa a cópia à vista.
  - `pendente`: o Mac inteiro; a escala corrigida pela API depois do import num caso real (o R04 não muda de raster); o
    PRODUCAO_B com a regra "mudou de lugar" (o HD dos proxies não estava aqui).

## 🆕 ⭐⭐⭐ RELINK PARA OS ORIGINAIS NUMA CÓPIA — `importSequences` de um `.prproj` relinkado (23.2.0 Windows, 2026-10-09)

Bancada do De Lá Pra Cá (relink da timeline do Premiere para os originais, plano de 2026-10-09), operada pela ponte do
laboratório no Premiere **23.2.0 (build 69), Windows 11**, sem o autor. Projeto de bancada salvo pelo 23.2 (`Project`
41, `Media` Version 27): sequência 1920×1080 a 24 com 5 planos — 3 de um convertido 1920×1080 ProRes Proxy de um
iPhone 3840×2160 HEVC (Motion padrão; Scale 80 + Position + Rotation 5; Scale com keyframes 100→150) e 2 de proxies
ALEXA 2880×1620 ProRes Proxy cujos originais são **ARRIRAW `.mxf`** (Scale 66,6667 digitado; Motion padrão).

- ✅ **A cópia importada vira sequência nova com clipes novos nos originais.** Copiar o `.prproj` salvo, trocar no
  `Media` dos convertidos `FilePath`/`ActualMediaFilePath`/`RelativePath`/`Title` (e o `FrameRect` do `VideoStream`
  quando o raster muda), renomear a `Sequence` e chamar `app.project.importSequences(copia, [ObjectUID da Sequence])`
  → `true` em 6,4 s; a sequência entra com **ID novo** (o Premiere renumera), e os clipes dela são `ProjectItem` NOVOS
  apontando para os originais — **mesmo com os mesmos ObjectUID/FileKey da cópia** (não precisou gerar IDs novos). A
  sequência e os clipes dos convertidos ficam intactos. Só a sequência pedida e o que ela usa entram.
- ⚠️ Entram na RAIZ do projeto, e com os nomes da cópia: o item da sequência fica com o nome antigo do `ClipProjectItem`
  (o `Sequence.Name` renomeado aparece em `app.project.sequences`) e o clipe novo com o nome do convertido (`….mov`
  apontando para o `.mxf`). ✅ Pela API depois do import: `rootItem.createBin`, `item.moveBin(bin)` e `item.name = …`
  (renomear o item da sequência renomeia a sequência).
- ✅ **O corte não muda um quadro:** `start`/`end`/`inPoint`/`outPoint` (ticks) iguais nos 5 planos.
- ⛔ **A escala NÃO acompanha** (como o banco previa no 26, `prproj/relink-e-geometria.md`): o Scale continua o número,
  agora sobre 3840 → a imagem do iPhone 2× maior. ✅ **Corrigir pela API depois do import funciona em todos os casos:**
  `Scale.setValue(v × largura_convertido/largura_original, true)` — inclusive no plano de Motion PADRÃO (`getValue` dá
  100 e o `setValue` materializa o componente) — e, com keyframes, `getKeys()` + `setValueAtKey(t, v × f, true)` em cada
  um. Position (normalizada) e Rotation não mudam. Dispensa materializar o Motion no XML (o PRODUCAO-G fazia no arquivo).
- ✅ **O 23.2 decodifica o ARRIRAW** do ALEXA Mini (`.mxf`, 2880×1620; o ffmpeg dá `unknown` 0×0): o `exportFramePNG`
  sai com a imagem, igual ao convertido (correlação 1,000 no comparador do De Lá Pra Cá, `tools/conferir_conform`).
- ⛔ **`qe…exportFramePNG` devolve `false` e GRAVA o arquivo mesmo assim** (23.2 Windows; 7 de 7): o PNG 1920×1080
  aparece logo depois, em segundo plano (7 quadros em 0,5 s de chamada). O retorno não prova nada — esperar o ARQUIVO
  (existir e o tamanho parar). Caminho absoluto (o relativo vai para a pasta do Premiere, já no banco).
- ✅ **A conferência pela imagem separa certo de errado:** antes (convertido) × depois (original, escala corrigida) =
  0,999–1,000 nos 7 pontos; antes × depois SEM a correção = 0,02–0,20 nos planos do iPhone (limiar 0,75). O nome do clipe
  queimado no canto do proxy ALEXA (o original não tem) não atrapalhou (o comparador ignora a borda).
- `pendente`: o arquivo que o Premiere NÃO lê (0 byte, truncado, formato sem suporte) dentro da cópia — o
  `importSequences` pode abrir o diálogo "Link Media" e travar a ponte (no Windows ainda não há vigia de diálogos);
  multicam/merged, efeitos com máscara (no 26 o `exportFramePNG` não mostra máscara), Scale Width não uniforme, o 25/26.
  Scripts da bancada: `%TEMP%\claude\bancada-premiere\` (passo1/2, copia, importar, escala, quadros, cortes).
- 🆕 **Laboratório B11_RELINK (mesmo dia, 23.2.0 Windows, `laboratorio-de-midia/lab/bancadas/premiere_relink.py`):** 9 pares
  convertido → original sintéticos. A escala certa é a do CONTEÚDO, não a razão das larguras (tarja, recorte, stretch,
  vertical, PAR — `prproj/relink-e-geometria.md` §6.2). Stretch pela API: `Uniform Scale` = false, `Scale` = altura,
  `Scale Width` = largura. ⛔ **Apagar o `.prproj` ABERTO e chamar `app.newProject` abre o modal "Project Modified — The
  project file has been modified since last save. Do you wish…"** (desenhado pelo Premiere: sem texto nem botões para a
  automação do Windows) e TRAVA a ponte — fechar antes com `app.project.closeDocument(0, 0)`. Lido por `PrintWindow`,
  fechado com Esc (`SetForegroundWindow` + `SendKeys`). ⚠️ **`sequence.clone()` nomeia pelo ITEM da bin** ("ANTES Copy"
  quando só a `Sequence` foi renomeada na cópia): renomear `projectItem.name`.
- 🆕 **B13_MONTAGENS (mesmo dia, `lab/bancadas/premiere_montagens.py`; resultado em `prproj/relink-e-geometria.md` §6.2):**
  ⚠️ CORRIGE (mesma noite): a máquina TRAVOU depois dessas rodadas (GPU CUDA, RTX 4050 notebook; driver atualizado,
  Premiere passado para a CPU, Parsec desinstalado) e, na CPU (`qe.project.setRenderer("Mercury Playback Engine
  Software Only")`), os dois ⛔ abaixo NÃO se repetiram (3 de 3 importações de primeira, sem monitor preto): `hipotese`
  que venham da GPU instável — manter as regras (custam pouco). ⚠️ O quadro da CPU × o da GPU: 0,995–0,997 — a
  conferência usa o mesmo renderizador nos dois lados.
  ⛔ **`importSequences` devolve `true` e às vezes NÃO cria nada** (3 de 5 rodadas, GPU): logo depois de outra importação
  (8 s) e ao importar de novo o MESMO caminho de `.prproj` na sessão; numa rodada, a 2ª importação do mesmo arquivo
  SUBSTITUIU a 1ª. Com nome de arquivo novo a mesma cópia (mesmos UIDs) importa — `inferido` que o Premiere lembra o
  caminho; a falha após outra importação é intermitente. Regra: nome de cópia que nunca se repete + conferir que a
  sequência SURGIU (contar `app.project.sequences`) e tentar de novo. ⛔ **Depois de ~20 sequências abertas e 3
  importações o monitor de programa ficou PRETO**: o `exportFramePNG` parou de gravar e os PNGs da exportação anterior
  SUMIRAM da pasta; reabrir o Premiere resolveu — conferir cada arquivo de quadro, e sem quadro a conferência "não rodou".
  ⛔ **Não há API de adjustment layer** (DOM: `isAdjustmentLayer()` só lê; QE: `newBlackVideo`, `newTransparentVideo`,
  `newColorMatte`… sem ajuste) — no arquivo é um Black Video com as marcas (ver o §6.2). ⚠️ **QE: `track.getItemAt(i)`
  conta os vãos** (`type` "Empty"); `addVideoEffect(qe.project.getVideoEffectByName("Transform"|"Crop"))` no item.
  ⚠️ `newTransparentVideo`/`newBlackVideo` logo depois de `app.newProject` não criam nada sem `qe.project.init()`. Na API o
  Transform é `AE.ADBE Geometry` (Anchor/Position normalizados, `Uniform Scale`, `Scale Height`, `Scale Width`, `Skew`,
  `Rotation`…) e o Crop `AE.ADBE AECrop` (Left/Top/Right/Bottom em %, `Zoom`, `Edge Feather`).
- 🆕 ⛔ **CORRIGE (2026-10-09, mais tarde, caso real R04 PRODUCAO-C):** o monitor preto que para o `exportFramePNG`
  NÃO é só da GPU — voltou com o projeto em `Mercury Playback Engine Software Only`, depois de ~190 quadros exportados
  na mesma sessão (133 + 57), com o monitor mostrando a imagem minúscula num fundo preto e o `exportFramePNG` sem gravar
  nada. Reiniciar o Premiere resolveu (76 de 76 em seguida). `confirmado` 2× (GPU no B13, CPU no R04). Regra: reiniciar
  o Premiere entre lotes grandes; o lote sem nenhum arquivo gravado = parar e reiniciar, não insistir.
  ⛔ **A 2ª `importSequences` da mesma cópia grande (2.430 `Media`, 10 sequências) num projeto que já tinha a 1ª TRAVOU o
  23.2:** 0 s de CPU em 15 s, janela sem resposta (até o `GetWindowText` de outro processo bloqueia), só matando. A 1ª
  levou 165 s. Para versões: cada uma é o SEU projeto — `app.openDocument(copia, true, true, true)` abriu a cópia
  (Premiere 22.6, `Project` 40) em 6 s, sem diálogo de conversão nem de localizar mídia (1.646 itens offline no
  projeto, as mídias da v02 online).
  Diálogos do 23.2 vistos: **"Open Project"** e **"Save Project"** são barras de PROGRESSO (`#32770`, só esperar;
  o vigia do laboratório agora as ignora); **"Resolve Fonts"** avisa a fonte que falta ("Unresolvable — will be
  substituted with default font") e espera um clique — Esc segue com a fonte padrão. ⚠️ A 1ª `openSequence` de uma
  sequência pesada pode dar "Unknown error exception"; a 2ª abre.
  ⛔ (2026-10-10) `app.quit()` pela ponte NÃO fechou o Premiere (ficou vivo com o projeto aberto) e derrubou a ponte
  (o painel não respondeu mais): conferir que o processo SAIU; se não, encerrar à força (o projeto já salvo). Um
  "diálogo" sem título no começo é o SPLASH ("Loading ImporterWindowsMedia.prm"), não um modal. ⚠️ Fechar diálogo de
  um processo em segundo plano: o `SetForegroundWindow` falha (proteção de foco) e o Esc se perde — `PostMessage
  WM_CLOSE` ao diálogo fechou o "Resolve Fonts".
- 🆕 (2026-10-10, R04 isolado) Uma `importSequences` num projeto NOVO e vazio (a FINAL + 9 nests, 69 mídias) levou 146 s
  e entrou só o que a sequência usa (10 sequências, 80 itens) — o jeito de ISOLAR uma timeline. ⚠️ 2 itens vieram
  OFFLINE com o arquivo existindo no caminho certo; `projectItem.changeMediaPath(o mesmo caminho, true)` religou (e a
  imagem saiu idêntica: 133 pontos a 1,0000). Conferir `isOffline()` depois de toda importação.


## ✅ `TrackItem.disabled` é GRAVÁVEL (2026-10-29, Premiere 26.0.2 Mac)

`c.disabled = true` num clipe de áudio recém-posto por `overwriteClip` o desliga (o clipe fica escuro na timeline) e
a releitura dá `true`. Uso: De Lá Pra Cá `dlpcMontar` — o som desligado no Avid entra desligado, como o `Flags=2` do
Resolve. ⏳ conferir no 23.x (Windows) e no vídeo (o app não desliga vídeo: ele não entra).
✅ **Premiere 26.5.2, Windows 11 (2026-10-29):** a bin real do PRODUCAO-A (`PRODA_CORTE.02.Exported.01`, 32 segmentos de
som com Mute Clips no Avid) montada pela ponte: o plano pede 8 clipes desligados (os pares estéreo juntados; o par com
um lado ligado fica ligado), 307/307 colocados, e a releitura (`dlpcLerSequencia`) devolve os MESMOS 8 com
`disabled = true`. ⛔ O 23.4 desta máquina não abriu nesse dia (cai 4–8 s depois de `kStateAppRunning`, logo após o
GPUSniffer; GPU híbrida, NVIDIA 32.0.16.1742; o 26.5.2 abre normal) — o 23.x segue pendente.

## ⭐⭐ Montar a timeline pelo ExtendScript nas versões SEM o MCP nativo (2026-11-06, Mac)

Medido no **Premiere 2026 (26.0.2)** e **2025 (25.6.5)**, resultados IDÊNTICOS (Ciclo Assist
`spikes/extendscript_nas_versoes_antigas.py`, clipes sintéticos com o nº do quadro em barras e um tom por canal;
roda dentro do serviço por `spikes/no_servico.py`). Comparar com o MCP do 27.1: `transversal/ia-embarcada-nos-nles.md` §3f.

| o quê | ExtendScript 25.6 / 26.0 | MCP 27.1 |
|---|---|---|
| 3 pontos: `item.setInPoint(s, 4)` + `setOutPoint` + `track.overwriteClip(item, s)` | `n/fps` exato: 3/4 em 23,976 e 29,97 DF (48→47; 121→120); **`n/fps + 1 µs`: 12/12**, lido de volta (ticks) e na IMAGEM (`exportFramePNG` do QE) | o mesmo (é o mesmo motor) |
| WAV 5.0 com um tom por canal | **`overwriteClip` numa sequência de vídeo: 5 trilhas, os 5 tons no export**; `createNewSequenceFromClips`: 5 trilhas, 5 tons | `insertClipsToSequence`: UM canal só |
| navalha | QE `track.razor(TC)` recebe TIMECODE (`Time.getFormatted`) → corta sempre no quadro, imagem e som | `razorTrackItems` em segundos: o som corta em fração de quadro |
| trilha alvo | `videoTracks[1].overwriteClip` → V2 (o som ligado vai para a A2) | `tracks` / `targetVideoTrack` |
| ripple | `insertClip` empurra (o pedaço seguinte foi para 1,001 s) | `mode: insert` / `overlapMode` |
| export de som | `sequence.exportAsMediaDirect(caminho, epr, 0)` → "No Error"; preset `Contents/Settings/EncoderPresets/Wave48mono16.epr` | `exportMedia` |

⚠️ Armadilhas desta medição:
- `qe…exportFramePNG(tc, caminho)` ACRESCENTA ".png" ao nome (caminho "x.png" vira "x.png.png").
- `setInPoint`/`setOutPoint` mudam as MARCAS do clipe no projeto do editor — um produto tem de guardar e devolver
  as marcas (ou usar subclipe temporário). ⬜ não medido: ler as marcas antes (`getInPoint`) e restaurar.
- "EvalScript error." (sem linha) = erro de SINTAXE na expressão inteira: `try/catch` dentro dela não pega.
- O Premiere 2025 deste Mac está em INGLÊS (File, Quit Premiere Pro); o 2026 e o Beta em português —
  menu pelo NOME tem de ler os nomes antes (matriz §G2).
⛔⛔ **O ExtendScript dá um OBJETO NOVO a cada acesso ao mesmo item** (26.0.2): `a === b` é falso para o mesmo
ProjectItem lido duas vezes — compare pelo `nodeId`. (Custou as marcas do editor voltarem erradas no `cicloMontar`.)
⭐ `getInPoint(1|2|4)`/`setInPoint(s, 1|2|4)` por tipo de mídia funcionam e são independentes (V 6–7 e A 8–9 →
"todos" 6–9); `setInPoint(s)` sem o tipo dá "Not Enough Parameters". Usado pelo Ciclo Assist (`cicloMontar`, F6)
para montar nas versões sem MCP e DEVOLVER as marcas do editor.
⬜ L/J (som só numa trilha): fora — decisão do autor (fica com o editor). ⬜ Não medido: o Windows (23.x do
notebook). `trackItem.move` e `sequence.clone()`: medidos em 2026-11-07, abaixo.

## ⭐⭐ UM CANAL de um item polifônico numa trilha: o subclipe REMAPEADO (2026-11-25, Premiere 26.0.2 Mac) — `confirmado`

O item de N canais mono (o WAV/MOV de 3+ canais — "N Mono") vai INTEIRO no `overwriteClip`: os canais espalham para as
trilhas de baixo e a trilha k toca o canal 1. Para pôr o canal c na trilha t (o que a timeline do Avid pede):
- `projectItem.setAudioChannelMapping(m)` EXISTE, mas o `reflect.methods` NÃO o lista (`typeof` = function). O
  `getAudioChannelMapping` é PROPRIEDADE; `audioChannelsType` e `audioClipsNumber` são SÓ LEITURA ("Cannot set
  property"); `new AudioChannelMapping()` não tem construtor ⇒ **não há como reduzir o item a 1 clipe**.
- ⭐ **O que funciona:** subclipe só de som do item → `m = s.getAudioChannelMapping; m.setMappingForChannel(0, c−1);
  s.setAudioChannelMapping(m)` → `overwriteClip(s, t)`: a trilha t recebe o canal c (`StreamNumber c−1`); os outros
  N−1 clipes ainda espalham para t+1… — apague-os na hora (`remove(false, false)`) e monte o som em ordem CRESCENTE de
  trilha (o que espalha só cai onde ainda não há nada). As trilhas criadas depois da última usada saem por QE
  `getActiveSequence().removeAudioTrack(i)`.
- **Sobrevive ao religar:** item OFFLINE de 8 canais, subclipes remapeados (1, 4, 8, 2 em A1–A4), `changeMediaPath` do
  item e dos subclipes ao WAV real → os 4 online tocando 1, 4, 8, 2, mesma entrada.
- Produto: De Lá Pra Cá/Conformar `dlpcMontar` (o canal vem do `canal_arquivo` do Avid); prova
  `Ciclo Assist spikes/conformar_canais_premiere.py` (V1 + 8 canais offline + 5 online + estéreo + mono: 7/7 trilhas
  certas, 8 trilhas na sequência, entrada e duração exatas). Mono e estéreo seguem inteiros numa trilha.

- ⛔⛔ **Item de clipes ESTÉREO** (o MOV de pares L/R: `audioChannelsType` 1 com 2+ clipes — B03_PARES, 2026-11-25): o
  subclipe remapeado leva DOIS canais, e remapear só o 0 deixa o lado R no canal padrão (a trilha tocava c e 2). O
  `setMappingForChannel(1, x)` resolve: **`x = −1` = MUDO** (vira `ChannelIndex` 2⁶⁴−1), e o índice é o canal do
  ARQUIVO inteiro, mesmo cruzando fluxos (`(0,1),(1,2)` = canais 2 e 3, do 1º e do 2º par). O `reflect` do mapeamento só
  mostra `audioChannelsType`, `audioClipsNumber` e `setMappingForChannel`. Produto (`dlpcMontar`): o par do Avid em
  trilhas vizinhas (c, c+1) vira UM clipe estéreo na 1ª, a do R fica vazia (a regra da ida e volta); o sozinho, [c, mudo].
  Ida e volta Avid → Premiere → Avid com 2 pares e 2 pares + 1 mono: bins idênticas (MC 25.12).
- ⛔ `changeMediaPath` do ITEM não leva os subclipes: cada subclipe é religado por si (a ordem não muda o resultado).

## ⭐⭐ EDITAR a timeline pelo ExtendScript nas versões sem MCP (2026-11-07, Premiere 26.0.2 e 25.6.5, Mac) — `confirmado`

(O 25.6.5 repetiu tudo: 100/100 quadros na imagem; lá a cópia do `clone()` vem com nome em INGLÊS — ache pelo
`sequenceID` novo, nunca pelo nome.)

Ciclo Assist `host.jsx` `cicloEditar` / `nle/premiere/edicao_cep.py` (F7). Conferido NA IMAGEM: uma edição com
extrair + abrir espaço + inserir imagem+som (V2/A2) + inserir um WAV 5.0 (A3–A5) → **100 de 100 quadros** certos.

| o quê | medido |
|---|---|
| `sequence.clone()` | devolve `true` (não a cópia); a cópia nasce na **RAIZ** do projeto com o nome **"Cópia de <nome>"** (PT) e fica ATIVA. Ache-a pelo `sequenceID` novo (lista antes × depois) e leve-a com `projectItem.moveBin(bin)`; `seq.name = …` renomeia. |
| `app.project.activeSequence = s` | **recusado** ("Cannot set property activeSequence") — é `app.project.openSequence(s.sequenceID)` (abre a aba) |
| navalha do QE `getVideoTrackAt(i).razor(tc)` / `getAudioTrackAt(i)` | trilha a trilha, no quadro; o pedaço da ESQUERDA mantém o `nodeId` |
| `trackItem.remove(false, false)` | tira SÓ o item; o vinculado (o som da imagem) fica |
| `trackItem.move(Time)` | RELATIVO, devolve `null`, move SÓ o item (o vinculado fica) |
| `track.overwriteClip(item, s)` na trilha de índice k | imagem em **V(k)** e som a partir de **A(k)** (WAV 5.0 na A3 → A3…A7), criando as trilhas de som que faltam; numa trilha de SOM, a imagem vai para V(k) também |
| `trackItem.inPoint = Time` / `outPoint = Time` | **graváveis**: fazem "slip" (a posição e a duração ficam) |
| `sequence.getPlayerPosition()` | Time; `app.sourceMonitor.getProjectItem()` → null sem nada carregado; marcas ausentes = **−400000 s** |

⛔⛔ **`move` com `Time.seconds` deixa o item 1 TICK depois do quadro** (10,0000000001 quadros) — e o Premiere
mostra o quadro ANTERIOR à entrada em todo pedaço movido. Ler de volta arredondando para quadro NÃO vê; só a imagem
(ou os ticks crus) vê. ⇒ Monte o `Time` por `.ticks` com o inteiro exato (25 fps = 10.160.640.000 por quadro;
23,976 = 10.594.584.000), nunca por `.seconds`. E a prova confere os ticks: início fora da grade = divergência.

⛔⛔ **`projectItem.setInPoint` arredonda para a grade de quadros do CLIPE, não da sequência.** WAV de gravador com TC
próprio (13:04:19,012), pedido em 10 s → 9,968 s; numa sequência de 25 fps o trecho entrou UM QUADRO antes (3 de 4
trechos só de som do `cicloMontar` da F6, que a prova pegou). Conserto: depois do `overwriteClip`, `inPoint`/`outPoint`
atribuídos no ITEM da timeline (slip) → 20/20 trilhas no quadro.

⛔ **E no SUBCLIPE do `dlpcMontar` (Conformar, 26.0.2, 2026-11-25) — `confirmado` de ouvido:** o WAV com TC de OUTRA
taxa (25 numa sequência 23,976) pedido no quadro 24 (1,001 s) com a folga de 0,6 q entrou a 0,959 s = quadro 23 (as
claques do lab 1 quadro atrasadas no export do MC). A folga não basta quando a grade do clipe é mais grossa (1/25 s =
0,959 q). Conserto: ler o `getInPoint` de volta e, abaixo do pedido, subir +0,8/+0,95/+0,99 q até passar → 1,04 s
(o 1º ponto da grade ≥ 1,001), o leitor do `.prproj` relê 24, e o MC toca as claques no tempo exato (0,999/3,001 s).

## 🆕 2026-11-13 — XML de timeline (FCP7 `xmeml` 4) por `importFiles`, apontando OP-Atom do Avid (Premiere 26.0.2 Mac) — `observado` (1 rodada)

Ciclo Assist, Carta Aberta (`cicloassist/carta/entrega_premiere.py`), com a timeline real da PRODUCAO-A
(`PRODA_CORTE.02.Exported.01`: 877 clipes, 143 dissolves, OP-Atom DNxHR LB escrita pelo Resolve 18.5).
- ✅ **Pequeno entra:** 1 clipe de vídeo OP-Atom (1920 e 2048), as 16 trilhas de SOM inteiras (≈ 560 clipes, fades
  `KGAudioTransCrossFade3dB` do vazio, `audiolevels` linear) e 2 clipes com `Time Remap` constante: sequência criada na
  bin pedida, o arquivo importado como item, em < 1 s.
- ⛔⛔ **`importFiles([xml])` devolve `true` NA HORA (0,2–1,4 s) e a sequência pode não vir.** Contar sequências antes e
  depois (`sequenceID`), nunca o retorno — a classe do "true calado" acima.
- ⛔⛔ **A V1 de vídeo (95 clipes, 41 arquivos OP-Atom) não entrou em 4 tentativas e na 5ª TRAVOU o Premiere:**
  diálogo modal "Importar arquivos" com a barra parada, 0 % de CPU, `top` = `stuck`; a pilha da thread principal
  em `ImportFiles → HSL::ImportFiles → DLG::ProgressDialog::DoProgressDialog → OS_Dialog::RunModal` (ocioso); a
  janela recusava ir à frente; ~10 min depois, o relator de falha da Adobe ("Ocorreu um erro") e o processo saindo.
  Causa NÃO achada: não é o tamanho do quadro, nem o `Time Remap`, nem entrada/saída fora do arquivo (conferidos).
  ⚠️ As 4 primeiras tentativas pareceram "recusa calada", mas podem ter sido imports ainda em curso — com o modal
  aberto, toda chamada da ponte espera atrás dele.
- ⚠️ No XML, o par de clipes de uma transição do Avid NÃO pode se sobrepor na trilha (no `.avb` eles se sobrepõem):
  apara-se no ponto de corte (`cutpoint`), e a transição usa a sobra de mídia.
- ⬜ Próximo: bissectar a V1 com o Premiere à vista (o modal de import em segundo plano é suspeito) e medir se um
  arquivo OP-Atom de vídeo específico trava o importador; alternativa sem XML: o enxerto em `.prproj` (§ escrita 11g).

## ✅ `app.project.getInsertionBin()` = a bin SELECIONADA, ou a ABERTA por último (2026-11-14, Premiere 26.0.2 Mac)

O destino do "Importar para o Premiere" da Carta (decisão do autor: "bin selecionada ou aberta por último"). Medido com o
mouse do piloto, no projeto real (Ciclo Assist `host.jsx` `cicloBinDeInsercao`, rota `/carta/premiere/bin`):
projeto recém-aberto, nada selecionado → a RAIZ; uma bin selecionada no painel de projeto → ela; a bin aberta num painel
próprio (duplo clique no ÍCONE), nada selecionado dentro → ela; uma sub-bin selecionada dentro dela → a sub-bin.
- ⛔ `ProjectItem.getParentItem` NÃO existe no 26.0.2: o caminho da bin sai de percorrer a árvore a partir da raiz.
- ⚠️ Piloto: duplo clique no NOME da bin entra em RENOMEAR (o texto fica selecionado — a tecla seguinte renomeia); abrir é
  no ÍCONE. Esc cancela (conferir antes que o Premiere está na frente).


## 🆕 `importFiles` com a LISTA inteira, não um por arquivo (2026-11-15, 27.0.0 Mac) — `confirmado`

O "Importar para o Premiere" da Carta (Ciclo Assist) importava a mídia que faltava com um `importFiles([arquivo])` por
arquivo — a janela de importar abria e fechava centenas de vezes (o autor viu) e o passo levava 31–73 s (25/26/27) e
166 s (23.6) para 259 arquivos. Com UM `importFiles(lista, true, bin, false)` por bin: **259 arquivos em 2,36 s** dentro do
Premiere (o passo inteiro 6,7 s), os 259 conferidos um a um pelo `getMediaPath()` dos filhos da bin (nunca pelo retorno do
`importFiles`). Ciclo Assist: `host.jsx` `cicloImportar` (duas passadas: os lotes por bin, depois arquivo a arquivo o que
entrou, o que já estava e o proxy). - **Recusa no meio do lote — `confirmado` (27.0.0 Mac, 2026-11-15)**, lista de 9: 3 boas, uma sombra `._` do exFAT, 2
  boas, um PDF, 2 boas (`importFiles(lista, true, bin, false)`):
  - ⭐ **todo o conteúdo bom ENTRA** (as 7, inclusive as que vinham depois dos problemas), ANTES da janela;
  - o **PDF** abre a janela **"File Import Failure"** ("File format not supported", o caminho na lista) — e ⛔ ela
    **SEGURA o script**: a chamada só voltou depois do OK (84 s, o tempo até o clique). Mesmo com `suppressUI=true`;
  - a **sombra `._`** é recusada CALADA (não está na parte visível da janela; sem ela na lista, não há janela nenhuma).
  - Ciclo Assist: o `cicloImportar` não manda a sombra (`cicloSombra`, "ignorado") — 7 boas + sombra voltaram na hora,
    sem janela. ⬜ O documento (PDF etc.) que chega à lista ainda trava a chamada até o OK do editor.

- **Onde o Premiere registra a falha de importação — `confirmado` (27.0.0 Mac, 2026-11-15): em arquivo, em lugar nenhum.**
  Varridos todos os arquivos alterados em `~/Library/Logs`, `~/Documents/Adobe`, `~/Library/Application Support/Adobe`,
  `~/Library/Caches/Adobe` e `~/Library/Preferences/Adobe` depois da falha: nenhum cita o arquivo nem "File format not
  supported". O que existe: `~/Library/Preferences/Adobe/Premiere Pro/<v>/Trace Database.txt` (as CATEGORIAS de rastreio,
  `nome<TAB>1<TAB>5` — ImporterMXF, ImporterMP4, ImporterUsageLogger…; o rastreio vai ao painel Console, Cmd+F12, não ao
  disco), o Sentry da Adobe (`~/Library/Caches/Adobe/Premiere Pro/<v>/SentryIO-db`, binário, sem o nome do arquivo) e o
  `Plugin Loading.log` em `~/Documents/Adobe/Premiere Pro/<v>/` — que é do MEDIA ENCODER (raiz `Adobe Media Encoder
  20xx.app`), não do Premiere. ⭐ A sombra `._` deixou rastro só no cache: `Media Cache Files/._A01….ims`.
  ⇒ Quem diz o que foi recusado é quem pediu: a lista do `cicloImportar`, arquivo a arquivo.
- ⭐ **O importador de BRAW (plugin da Blackmagic) mora numa pasta COMUM a todas as versões:** Mac
  `/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/BlackmagicRawPremiereImporter.bundle` (+
  `BlackmagicRawPremiereSourceEffect.plugin`) — `confirmado` (presente neste Mac). Windows: `C:\Program Files\Adobe\Common\
  Plug-ins\7.0\MediaCore\` — `pendente`. ⇒ dá para saber ANTES de importar que um `.braw` vai ser recusado.

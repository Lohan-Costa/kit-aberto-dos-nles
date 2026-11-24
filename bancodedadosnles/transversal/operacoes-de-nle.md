# Operações de NLE — o mapa por MECÂNICA, não por produto

> **Para que serve, e por que ele nasceu depois de tudo.** O banco cresceu por **produto**:
> um documento por app dissecado, um por protocolo de arquivo. Isso responde *"o que o Chop Chop
> faz?"*. Não responde *"como se move um clipe?"* — que é a pergunta que **todo** app nosso faz,
> em todo NLE, para sempre.
>
> Este arquivo inverte o eixo. A linha é a **operação**; a coluna é o **NLE**. O que cada produto
> faz de particular vira **fonte**, não capítulo.
>
> ⭐ **Regra de uso:** quando uma análise nova revelar uma mecânica, ela entra AQUI, com ponteiro
> para o documento do produto onde foi vista. O documento do produto conta a história; este conta
> a capacidade.

**Escrito em 2026-08-24**, na sessão em que o autor redefiniu o objetivo: *"o que é mais importante
são as interações que os plugins fazem com o app… agora o foco é 100% exploração e entendimento das
mecânicas."*

---

## ⚠️ Antes de usar: o estado das três colunas é MUITO desigual

| NLE | superfície | maturidade no banco | onde vive |
|---|---|---|---|
| **Premiere** | ExtendScript (DOM) + **QE DOM** não documentado | **alta** — 7 produtos dissecados | [`plugins/premiere-cep/`](../plugins/premiere-cep/) |
| **Media Composer** | Panel SDK: QWebChannel `mcapi` + gRPC | **alta** — integração em produção | [`plugins/avid-panel-sdk/`](../plugins/avid-panel-sdk/) |
| **DaVinci Resolve** | API de scripting (Python/Lua) **+** 🆕 Workflow Integration Plugins (Electron) | 🆕 **média-alta** (scripts) · **baixa** (workflow plugins) | [`plugins/resolve-scripting/`](../plugins/resolve-scripting/) |

✅ **A lacuna mais grave do banco foi FECHADA em 2026-08-24** — [`plugins/resolve-scripting/`](../plugins/resolve-scripting/)
existe. Não exigiu análise nova: era consolidação de conhecimento que morava dentro do
`orbita_sync.lua` e dentro de um documento de produto.

⭐⭐ **E a consolidação rendeu um achado que nenhuma das duas fontes tinha sozinha:** o campo
**`mediaType`** do `clipInfo` (1=vídeo, 2=áudio) coloca vídeo e áudio **independentemente** — é o
que evita as trilhas de vídeo vazias que o §D descreve. *Juntar duas fontes que resolvem o mesmo
problema de formas diferentes é onde o mapa por mecânica se paga.*

---

## 0. ⭐⭐⭐ Os TRÊS eixos de integração

Antes das operações: há três formas de um software externo agir sobre um NLE, e a terceira só
apareceu em 2026-08-24.

| # | eixo | como | exemplos |
|---|---|---|---|
| 1 | **dirigir o app pela API** | painel/script pede, o app faz | CEP (Premiere), Panel SDK (Avid), scripting **e** 🆕 **Workflow Integration Plugins** (Resolve), 🆕 Workflow Extension (Final Cut) |
| 2 | **escrever os arquivos do app** | o app lê o que você produziu | AAF, `.avb`, `.prproj`, `.drt` |
| 3 | 🆕 ⭐⭐ **ficar EMBAIXO do app** | apresentar-se como o **armazenamento** que ele espera | Mimiq, Osiris 2 |

⭐ **O eixo 3 muda a pergunta.** Onze produtos dissecados usavam os eixos 1 e 2; **Mimiq e Osiris não
falam com o Media Composer** — fazem o armazenamento comum **parecer** Avid Shared Storage, e o MC
liga o bin locking sozinho porque acredita estar em shared storage. *O nome do produto conta a
estratégia: Mimiq **mimetiza**.*

⚠️ **Quando a API do app não expõe o que se precisa — e no Avid ela expõe pouco — mudar de CAMADA é
alternativa real a insistir na API.** Detalhe em
[`protocolos/projeto-avid/storage-como-integracao.md`](../protocolos/projeto-avid/storage-como-integracao.md).

---

## A. Mover um clipe que JÁ está na timeline

⭐⭐ **A operação mais mal servida das três plataformas, e a que mais nos custou.**

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| existe? | ✅ `TrackItem.move(Time)` | ⛔ **desconhecido** | ⛔ **não há rpc** |
| confiança | `confirmado` | `pendente` | `inferido` |

**Premiere** — `TrackItem.move(Time)` no DOM; o QE tem `moveClip`. ⚠️⚠️ **`clip.start = t` NÃO
move: APARA** (mexe no ponto de entrada). Dois produtos confirmam por caminhos independentes — o
nosso `host.jsx` e o Automation Blocks, que usa `start`/`end` justamente como aparo. Mover um clipe
com áudio **vinculado arrasta o par junto**, então todo alvo deve ser absoluto e o delta relido na
hora.

⛔ **E o painel Timeline NÃO REPINTA depois.** É a pendência mais antiga: os clipes movidos ficam
invisíveis até o mouse passar. Cinco caminhos falharam. Ver
[`api-extendscript.md` §redesenho](../plugins/premiere-cep/api-extendscript.md) — inclusive a
alavanca `updateUI`, nunca tentada.

**Resolve** — ⛔ **ninguém que lemos move clipe já colocado.** O Chop Chop, que precisaria, resolve
**apagando a timeline inteira e reconstruindo** (§K). Não sabemos se há primitivo de movimento.
**É um buraco de mapa, não uma ausência confirmada** — e o banco já errou 5 vezes concluindo
"não existe" (ver [`analise-de-executaveis.md` §calibração](analise-de-executaveis.md)).

**Media Composer** — não há edição de timeline por rpc. O que existe é `DropFromPluginTo{Bin,
Composer,Timeline}` e o `DoCommand` (725 comandos, nenhum aceita timecode). A rota real de alterar
material é **escrever a bin `.avb` por fora**.

### 🆕 Próximo passo (autor, 2026-10-21): o REPINTAR do Premiere pelo REA

Decisão do autor: atacar o "mover clipe já colocado" pelo **Premiere** primeiro, com o REA (o que o Premiere chama para
repintar a timeline quando a edição vem da interface × da API), e levar o roteiro ao MC e ao Resolve. Ver o handoff do
Órbita (`9 ARQUIVADOS/DRAMASYNC/.dev/HANDOFF-WINDOWS.md`, "PRÓXIMA SESSÃO").

### 🆕 ⭐⭐ CORTAR existe, e é do QE — `razor()`

⚠️ **Correção de 2026-08-24.** O Quickture **corta e apaga** clipe já colocado:

```javascript
qe.project.getActiveSequence().razor(timecodeComoString);   // corta
clip.remove(ripple, shift);                                  // apaga (DOM)
```

⭐ **`razor()` aceita STRING DE TIMECODE**, não ticks nem segundos — e vive no **QE**, como toda
operação estrutural do Premiere. ⭐ **`TrackItem.remove(ripple, shift)`** é o primitivo de remoção
que este mapa tinha como vago no §C.

⚠️ **Ao varrer para apagar, vá de TRÁS PARA FRENTE**: a coleção de clipes reordena por tempo, e
apagar de frente escorrega os índices. Ver
[`quickture-ppro.md`](../plugins/premiere-cep/quickture-ppro.md) §1.

### ⭐ A leitura de mercado que sai daqui

Dos **12 produtos comerciais já dissecados, nenhum MOVE um clipe já colocado** (o Quickture corta e
apaga, mas não desloca). Todos inserem,
sobrescrevem, aplicam efeito, criam marcador ou organizam bin — operações que mudam estrutura ou
conteúdo e **repintam sozinhas**. *Painel de NLE é produto de ingest e acabamento, não de
rearranjo.* Quem precisa rearranjar está fora da trilha batida — e vai encontrar as APIs frias.

---

## B. Colocar mídia NA timeline

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| primitivo | `insertClip` / `overwriteClip` (**QE**) | `AppendToTimeline(clipInfoList)` | `DropFromPluginToTimeline` |
| posição absoluta | via ticks no alvo | ⭐ campo `recordFrame` | — |

**Premiere** — `insertProjItemInSeq`, e `createNewSequenceFromClips` para nascer já montado.
⚠️ `insertClip`/`overwriteClip` vivem no **QE**, não no DOM.

**Resolve** — um dicionário por clipe:
`{mediaPoolItem, startFrame, endFrame, trackIndex, recordFrame, mediaType}`.
⭐⭐ **`mediaType` (1=vídeo, 2=áudio) coloca vídeo e áudio INDEPENDENTEMENTE**, em trilhas de sua
escolha — é o que evita as trilhas de vídeo vazias do §D. Quem não usa é forçado a alinhar índices
de vídeo com blocos de áudio. Ver [`resolve-scripting/api-scripting.md`](../plugins/resolve-scripting/api-scripting.md).
⭐⭐ **`recordFrame` é a posição ABSOLUTA e é o que permite montar stringout**; sem ele o
`AppendToTimeline` só empilha em sequência. Clipes com o **mesmo `recordFrame`** ficam alinhados
verticalmente — é assim que se empilha multicâmera.
⚠️ Exige `SetCurrentTimeline` antes: a timeline precisa estar em foco.

**Media Composer** — entrega por drop do painel; a granularidade de posição não foi medida.

---

## C. Remover da timeline

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| clipe | 🆕 ⭐ **`TrackItem.remove(ripple, shift)`**; `delAllClipsFromSeq`, `delLinkedClips` | `Timeline.DeleteClips([itens])` | ⛔ não medido |
| cortar | 🆕 ⭐⭐ **`qe…razor(timecode)`** | ⛔ não mapeado | ⛔ |

⚠️ **Resolve, armadilha de limpeza total:** para esvaziar uma timeline é preciso varrer **todas** as
trilhas de vídeo **e** áudio (`GetTrackCount` × `GetItemListInTrack`), juntar cada item **e seus
vinculados** (`GetLinkedItems`), e só então apagar — com recuo trilha a trilha se a chamada em bloco
falhar. Apagar só a trilha de vídeo 1 deixa a timeline suja.

⚠️⚠️ **E os objetos remotos do Resolve não são *hashable*:** um `set()` de `MediaPoolItem` estoura.
Deduplicar exige `id(obj)`.

---

## D. Trilhas — criar, apagar, renomear, subtipo

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| criar | `addTracks` (**QE**) | `AddTrack(tipo, subtipo)` | ⛔ |
| apagar | `removeVideoTrack`/`removeAudioTrack`, `delTrackByIndex` (**QE**) | `DeleteTrack(tipo, índice)` | ⛔ |
| renomear | `renameVidTracks`/`renameAudTracks` (**QE**) | `SetTrackName(tipo, índice, nome)` | ⛔ |
| limpar vazias | `removeEmptyVideoTracks`/`…Audio` (**QE**) | ⛔ não há | ⛔ |

⭐⭐ **No Premiere, TODA operação de trilha é QE.** O DOM não cria, não apaga e não renomeia trilha.
Isso deixou de ser risco isolado nosso quando o Automation Blocks — produto comercial em produção —
apareceu dependendo do mesmo `app.enableQE()`.

⚠️ **Resolve: não há API para MUDAR o subtipo de uma trilha existente** (adaptive N). Só criar com
ele. O contorno visto: apagar todas menos a primeira, criar a nova com o subtipo certo no fim, apagar
a primeira.

### ⭐ A armadilha do layout de áudio, medida em dois produtos independentes

Quando cada câmera precisa de N canais de áudio, o índice de vídeo tende a virar
`índiceDaCâmera × maxCanaisDeÁudio + 1` — **e sobram trilhas de vídeo vazias entre as câmeras**.
3 câmeras × 8 canais = **24 trilhas de vídeo, 21 vazias**. O nosso `host.jsx` documenta a dor e
limpa com `removeEmptyVideoTracks()`; o Chop Chop tem a mesma e **não limpa**.
⭐ *Convergência independente: o problema é do modelo de trilhas, não de uma implementação.*

---

## E. Trazer mídia PARA o projeto (importar) e tirar

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| importar | `importFiles` | `MediaStorage.AddItemListToMediaPool(arquivos)` | `ImportFile` / `LinkFile` (gRPC) |
| remover | — | `MediaPool.DeleteClips` | — |
| trocar mídia | `item_change_media` (Automation Blocks) | — | ⭐ `LinkFile` é a rota de relink |
| proxy | — | `LinkProxyMedia(caminho)` | — |

⚠️ **Premiere: quem manda no resultado é o PROJETO, não o retorno de `importFiles`.** A prática do
Órbita — reindexar depois e contar quantos passaram a existir de verdade — vale para qualquer app.

⚠️ **Resolve, `LinkProxyMedia`:** o casamento por **nome** pressupõe que o proxy tem exatamente o
mesmo nome do original, e a implementação vista só tolera **dois** itens por nome (com três
resoluções, um se perde do rastreio).

---

## 🆕 E.2 ⭐⭐ Criar SUBCLIPE — e o que faz as vezes dele em cada NLE

**Entrou em 2026-09-06**, quando o Órbita passou a criar 52 subclipes de uma diária real dentro do
Media Composer. É a operação que **falta** nas outras duas colunas, e é o eixo da próxima
exploração.

⚠️⚠️ **O nome engana: as três NLEs chamam de coisas diferentes o que resolve o mesmo problema** —
*"recortar um pedaço de uma tomada, com imagem e som juntos, e pôr na bin como um item novo"*.

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| o objeto | **subclip** *e* ⭐ **merged clip** (duas coisas) | subclip do Media Pool | **subclipe** (mob `usage=subclip`) |
| recortar por API | ✅ **`projectItem.createSubClip(name, inTicks, outTicks, hardBoundaries, takeVideo, takeAudio)`** | ⛔ não medido | ✅ `CreateSubClip` (gRPC), **não é a rota usada** |
| **fundir** V+A por API | ⛔⛔ **o buraco** — nenhuma pista no banco | n/a (não separa assim) | n/a (o master já é A/V) |
| criar por arquivo | ✅ `.prproj` descreve merged clip, **com armadilha de crash** | ⛔ | ✅ **é a rota usada** (pyavb) |
| perguntar "é merged?" | ✅ `isMergedClip` / `isNotMergedClip` | — | — |

### ✅ Media Composer — `confirmado`, em produção

O Órbita **não usa a API** para isto: escreve a `.avb` com pyavb e manda o MC abrir a bin. O que faz
o subclipe ser subclipe, e não um master encurtado:

- `usage = "subclip"` no mob;
- ⭐⭐ **`start_time ≠ 0`** no source clip — **é o que prova o aparo**. Encurtar só o `length` daria
  sincronia falsa, e o sintoma só apareceria no olho do editor, no meio da montagem;
- `edit_rate` igual ao do material (24.0 na diária medida);
- ⭐ a claquete vai **junto**, em `Scene`/`Take` do `_USER`. Sem isso a identidade da tomada
  sobrevive só **por acidente** — enquanto o nome do clipe FOR a claquete. No dia em que o nome
  passa a vir do arquivo de vídeo, a identidade morre calada.

Validado com material real: 52 tomadas → 52 subclipes, **0 com filler**, relidos com pyavb.
Ver `DRAMASYNC/src-python/avid/subclipes.py`.

⭐⭐ **TRECHO ≠ TRILHA, e confundi-los inventa multicâmera.** `confirmado` — medido em material
real (a `SPANNING.avb` da suíte do Órbita e a diária D02): Assist anterior 2026-08-26, Órbita
2026-09-21. Uma câmera que **parou e voltou** dentro da janela do take dá **dois
trechos** (dois `SourceClip`) e **UMA trilha** — os dois pedaços voltam à mesma track, com o vão
virando filler. Quem contar trechos para dizer "V1/V2" ao editor anuncia **duas câmeras onde há
uma**, justamente na coluna que existe para denunciar multicâmera de verdade.

- ⚠️ `track_id` **não** serve para agrupar: os dois pedaços têm o mesmo `track_id` e o mesmo
  `mob_id`. Só a **trilha de origem** (a track da sequência de onde o trecho veio) os reconhece
  como a mesma câmera — e só ela separa duas câmeras que usem o mesmo canal.
- ⚠️ Trilha de origem **0 = não informada** → cada trecho ganha trilha própria (é o caso de
  `Tomada`s montadas à mão e de fixtures).
- ⭐ **A regra tem UM dono.** Quem mostra a contagem pergunta a quem escreve as tracks
  (`subclipes.agrupar_por_trilha`), em vez de repetir a conta: duas contagens da mesma coisa
  divergem no dia em que uma das duas muda, e foi exatamente assim que o defeito nasceu — a
  escrita aprendeu em 26/08 e a tela continuou contando trechos por mais três semanas.

### ⛔ Premiere — a pergunta ABERTA, e é a que dirige a próxima missão

O autor definiu a equivalência em 2026-09-06:

> *"no AVID nós criamos subclipe, no Premiere criamos Merged clips, que na prática são a mesma
> coisa — só precisamos criar a automação."*

⚠️ **A equivalência é de PROPÓSITO, não de mecanismo**, e a diferença é o que a exploração precisa
resolver:

| | Avid subclipe | Premiere merged clip |
|---|---|---|
| o que é | recorte de **um** clipe que já tem A/V juntos | **fusão de dois** itens (vídeo + áudio separados) |
| o corte | `start_time` + `length` | ⚠️ o merged clip é o clipe **inteiro**; recortar é outra operação (subclip) |
| no arquivo | mob com `usage=subclip` | `Sequence` com `BE.Sequence.IsMergedClip=true` |

⭐⭐ **A ordem é forçada: fundir primeiro, recortar depois.** `createSubClip` opera sobre um
`projectItem`; se esse item for a câmera crua, o subclipe sai **sem o som direto**. O item a recortar
tem de ser o merged clip.

⭐ **Metade já está respondida no banco**, e um `grep` de dois minutos foi o que respondeu:

- **recortar** — `createSubClip` existe, com in/out em ticks e `takeVideo`/`takeAudio` separados;
- **a forma no arquivo** — `protocolos/prproj/estruturas.md` §6, e o §2 do `escrita.md` traz a
  armadilha: uma câmera mergeada precisa de **4 MasterClips**, e errar o alvo do `SubClip` de vídeo
  **fecha o Premiere** (`EXC_BAD_ACCESS`);
- **consultar** — `isMergedClip` é predicado disponível.

⛔⛔ **O buraco é um só: FUNDIR pela API.** Nenhum dos produtos dissecados em `plugins/premiere-cep/`
cria merged clip — é ausência de evidência, não evidência de ausência. As perguntas e as três
arquiteturas possíveis estão em
[`plugins/premiere-cep/subclipe-e-merged-clip.md`](../plugins/premiere-cep/subclipe-e-merged-clip.md).

---

## F. Bins e organização

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| criar | `createBin` | `AddSubFolder(pai, nome)` | 🆕 autorar `.avb` + `OpenBin` (confirmado); `DoCommand(1001 New Bin)` cria **sem nome escolhido** |
| mover item | `moveBin`, `item_move_to_bin` | `MediaPool.MoveClips(itens, destino)` | 🆕 ⛔ **sem comando** — só por autoria, e só metade está medida (ver abaixo) |
| navegar | `getBinByName`, `iterateBinItems` | `GetSubFolderList`, `SetCurrentFolder` | `GetListOfBinItems` (⚠️ forma do caminho `pendente`) |
| ler conteúdo | `rootItem`, `numItems` | `GetClipList()` | `GetMobInfo` |

⭐ **Resolve tem um conceito de "pasta corrente"** (`SetCurrentFolder`) que muda para onde a
importação cai. É estado global do app — quem esquece de setar importa no lugar errado.

⚠️ **Avid:** `GetListOfBinItems(bin_relative_path=…)` devolveu 0 itens com todas as formas de caminho
tentadas. A forma correta é `pendente` desde a primeira rodada.

### 🆕 ⛔ Avid: MOVER item entre bins é o gesto mais comum do editor, e é o menos alcançável (2026-09-12)

Não há comando: `DoCommand` é **sem-parâmetro** (não diz qual item nem para onde) e `SetMobInfo` só
edita **coluna** de bin, não a pertença. Sobra a autoria de `.avb` — e ela está medida pela **metade**:

| o lado | como | estado |
|---|---|---|
| **PÔR** na bin de destino | `CloseBin` → pyavb escreve AO LADO → `os.replace` → `OpenBin`, com `Bin.uid` **preservado** | ✅ **confirmado 2026-09-11** ([escrita.md](../protocolos/avb/escrita.md)) |
| **TIRAR** da bin de origem | remover o `BinItem` de `f.content.items` (lista simples; `add_mob` só dá append) | ✅ **medido 2026-09-12**: 96 → 95 itens, o MobID some, o resto relê intacto |
| **OCULTAR** na origem (meio-termo) | `item.user_placed = False` | ✅ medido em produção: 208 itens → 7 visíveis |
| **COPIAR o mob entre arquivos** | ⛔ `add_mob` de mob estrangeiro é recusado — e a guarda está no **write**, não no `add_mob` (`ValueError: object is from different file`). ⭐⭐ A saída já vem no pyavb: **`AVBObject.copy(root)`** | ✅ **medido 2026-09-12**: destino 13 → 53 itens, fecho inteiro, item preexistente coerente. Sem a guarda seriam **21 `instance_id` colidindo**, em silêncio |

⭐ **E para o que o PLUGIN autora, mover não é necessário:** a bin de destino se escolhe na hora de
escrever. "Mover" só faz falta para item que **já está** numa bin — um subclipe que o editor criou,
uma timeline de ontem.

⛔⛔ **A ordem é TIRAR antes de PÔR.** Com o mob ainda vivo na bin de origem ABERTA, o MC trata o
que chega como cópia e renomeia para `….AutoCopy.NN` (medido 3×). ⭐ E isso nomeia o mecanismo do
AutoCopy: **MobID visível repetido entre bins ABERTAS**, não `Bin.uid` — os uids medidos eram todos
distintos.

⚠️⚠️ **O veredito na TELA ainda não saiu**, e o motivo virou o achado maior do dia: nenhuma bin
derivada da fixture abre, porque ela tem 2 `SourceMob` com `WinFileLocator` e **isso não sobrevive ao
`write()` do pyavb**. A bin do produto (`CENAS/C07.avb`) tem 19 mobs de fita e nenhum com locator —
por isso o produto nunca tropeçou. → [escrita.md](../protocolos/avb/escrita.md)

⛔ **CORRIGIDO em 2026-09-13:** não é o AMA — é o caminho UTF-8 **nulo** (`ff ff`) daqueles dois
locators, que o pyavb regrava como vazio (`00 00`). Bins AMA de caminho preenchido regravam e abrem.
Preservando o `0xFFFF`, a fixture abre. → [escrita.md §CORRIGE A SEÇÃO ACIMA](../protocolos/avb/escrita.md)

⭐⭐ **O que torna o destino seguro:** *toda bin do Avid é um banco autossuficiente* — ela carrega
oculto tudo que a timeline referencia ([escrita.md §RELINK PELA BIN](../protocolos/avb/escrita.md)).
Arrastar uma timeline para uma bin nova leva as mídias junto. A dificuldade toda mora na origem.

---

## G. Metadado — onde a informação pode ser pendurada

⭐⭐ **É a família de operação mais rica e a menos explorada por nós.**

**Premiere — três superfícies distintas:**

1. **`Column.Intrinsic.*`** via `projectItem.getProjectMetadata()` — as colunas do painel de
   projeto: `MediaStart`, `MediaEnd`, `MediaType`, `MediaTimebase`, `AudioInPoint`, `AudioOutPoint`,
   `AudioDuration`. ⭐ **Dá start/end/timebase SEM tocar no arquivo em disco.**
2. **XMP público** — `getXMPMetadata()` / `setXMPMetadata(xml)`.
3. ⭐⭐ **XMP PRIVADO do projeto** — namespace
   `http://ns.adobe.com/premierePrivateProjectMetaData/1.0/` (`kPProPrivateProjectMetadataURI`),
   com `addPropertyToProjectMetadataSchema` para registrar campos próprios.

⚠️⚠️ **O prefixo do caminho decide QUAL API chamar, e as assinaturas são assimétricas:**
`setProjectMetadata(xmp.serialize(), [caminhoSemPrefixo])` recebe **dois** argumentos;
`setXMPMetadata(xmp.serialize())` recebe **um**. Escrever no privado com a assinatura do público
**falha em silêncio**.

⭐ **Para que serve isso na prática:** é onde um plugin **pendura o próprio estado dentro do
projeto**. O Chop Chop guarda ali qual clipe foi para qual trilha, e é isso que faz a ingestão
incremental dele saber o que a rodada anterior fez. **O estado viaja dentro do `.prproj`** —
sobrevive a copiar o projeto, mandar para outro editor, abrir noutra máquina.

**Resolve** — `GetMetadata`/`SetMetadata` (campos de produção: `Scene`, `Shot`, `Take`,
`Camera ID`, `Episode #`) e `GetClipProperty`/`SetClipProperty` (propriedades do clipe:
`File Path`, `Start TC`, `FPS`, `Frames`, `Resolution`, `Audio Ch`, `Type`, `Usage`,
`Online Status`, `Date Added`). ⭐ Também `GetData`/`SetData` — um armazém chave-valor.

⭐⭐ **`Usage` é o achado reusável:** o Resolve já sabe **quantas vezes um clipe está em alguma
timeline**. Resolver duplicata sem rastrear estado nenhum é só perguntar.

**Media Composer** — colunas do `GetMobInfo` (13 comuns a todos, até 68 num master AMA). 🆕 ⭐⭐ **E dá para ESCREVER:**
**`SetMobInfo`** está em uso de produção, e ⭐ **`CreateCustomColumn` + `GetBinColumnInfo`** permitem **criar coluna
própria na bin** — é o análogo Avid do XMP privado do Premiere: *onde um plugin pendura o próprio dado dentro do
projeto do usuário*. Ver [`quickture-avid-helper.md`](../plugins/avid-panel-sdk/quickture-avid-helper.md).
⚠️ A **cor de etiqueta** do clipe continua `pendente`, e quais campos do `SetMobInfo` aceitam escrita também.

---

## H. Seleção e identidade de clipe

⭐⭐ **"Qual clipe é este?" é a pergunta que mais silenciosamente quebra apps.**

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| ler seleção | `app.getCurrentProjectViewSelection()` ⚠️ (o `sequence.getSelection()` é da TIMELINE) | — | `BinRowSelectionChanged`, drag MIME |
| arrasto bin → painel | ⛔ **NADA** — `types` vazio, `effectAllowed=copyMove` (medido 2026-09-06) | — | ✅ `text/x.avid.mc-api-asset-list+json` |
| arrasto Finder → painel | ✅ `files[].path` (⚠️ o `text/uri-list` vem como file-id inútil) | — | — |
| escrever | `setSelected(v, **updateUI**)`, `setProjectViewSelection` | — | — |
| identidade | ⭐ `nodeId`; ticks `start`+`end` | `GetUniqueId` | UMID / `mob_id` |

⭐ **Premiere, `nodeId`:** um produto comercial inteiro (Selector) é construído sobre ele — lê a
seleção, guarda a lista de `nodeId`, filtra, resseleciona a partir dela. ⚠️ **Não se sabe se
sobrevive a um `move()`** — e essa é exatamente a pergunta de quem move.

⭐ **A ponte DOM ↔ QE por ticks:** o QE é um grafo de objetos **paralelo**, sem identidade comum com
o DOM. Casa-se por **`start.ticks` E `end.ticks`** → só `start` → nome (último recurso). *Usar
também o `end` é o que distingue dois clipes cortados do mesmo master* — pelo nome são idênticos.

⚠️ **Índice não é identidade:** a coleção de clipes de uma trilha é ordenada **por tempo**. Assim
que um clipe passa por outro, os índices escorregam e o caminho deixa de casar — em silêncio.

⭐ **`updateUI`:** várias APIs de mutação do Premiere carregam um booleano de *atualizar a
interface* — `setSelected(isSelected, updateUI)`, `ComponentParam.setValue(value, updateUI)`. Dois
produtos independentes passam `true` **sempre**.

---

## I. LER a timeline (inventário)

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| percorrer | `videoTracks[i].clips[j]` | `GetItemListInTrack(tipo, índice)` | `GetMobInfo` |
| ⭐ atalho | **`sequence.exportAsFinalCutProXML(caminho)`** | export de timeline | `ExportFile` (AAF) |

⭐⭐ **Exportar FCP XML é uma segunda forma de ler a timeline que NÃO passa pelo DOM** — a sequência
inteira num passo, **com efeitos e parâmetros**, que o DOM só entrega componente a componente.

⭐ **E há um número que justifica isso.** O `FiltersDB.json` do Selector traz um **custo medido** por
predicado, produzido por um profiler que eles embarcam: ler `clip.disabled` custa **10966** contra
**150** do predicado mais barato do mesmo escopo — **73×**. *Ler propriedade via ExtendScript é o que
domina o custo, não a decisão.* Um app que percorra N clipes lendo M componentes paga a travessia
da ponte N×M vezes.

⭐ **Corolário barato:** em filtro composto, rode o predicado barato primeiro. A ordem de custo do
Selector é **dado** — está em
[`dados/selector.json`](../plugins/premiere-cep/dados/selector.json) e sai de graça.

---

## J. Efeitos e parâmetros

| | Premiere | Resolve |
|---|---|---|
| listar | `qe.project.getVideoEffectList` / `getAudioEffectList` | — |
| aplicar | **só QE** — `getVideoEffectByName` | — |
| por preset | `applyPreset(caminho)` + ler o XML do `.epr` | — |
| ler valor | `component.properties[i].getValue()` | — |
| keyframe | `setValue(v, updateUI)`, `setValueAtKey`, `setTimeVarying` | — |

⛔⭐ **O DOM do Premiere NÃO tem `addEffect`. Só o QE adiciona efeito.** Confirmado por produto
comercial. E **não há API de criação de transição** em lugar nenhum.

### ⚠️⚠️ "Este clipe tem efeito?" é uma CLASSIFICAÇÃO, não uma consulta

Todo `TrackItem` já vem com componentes de fábrica. Responder *"tem efeito aplicado"* exige
**subtrair os intrínsecos** — e o conjunto **muda com a espécie do clipe**:

| espécie | o que existe sempre |
|---|---|
| vídeo | `AE.ADBE Motion`, `AE.ADBE Opacity` |
| **título/gráfico** | `AE.ADBE Graphic Group`, `AE.ADBE Text` — **além** dos dois acima |
| áudio | `Internal Volume Mono \| Stereo \| 16 Channel` |
| áudio | `Internal Channel Volume Stereo \| 16 Channel` |

⛔ Um teste por **contagem** (`components.numItems > 2`) marca **todo título** e **todo áudio
multicanal** como "tem efeito", **sem levantar exceção**. E o fornecedor que mais sabe disso
(Selector) tem esse filtro **especificado e NÃO publicado**, parado numa lista de espera.

⭐ **Ler o XML do `.epr`, nunca o nome** — 2 casos de nome de preset que mentia. E há um campo
exato para separar ingest de encoding: **`<IngestPreset>true</IngestPreset>`**.

---

## J.2 🆕 Marcadores

| | Premiere | Resolve | Media Composer |
|---|---|---|---|
| criar | `sequence.markers.createMarker(inícioSEG, nome, duraçãoSEG)` | `marker_create` (via Automation Blocks) | 🆕 ⭐ `AddMarker` / `AddMarkers` (gRPC) |
| cor | `marker.setColorByIndex(0..7)` — 0 = verde | `marker_color` | ⛔ não medido |
| comentário | `marker.comments = "…"` | — | ⛔ não medido |
| ler / apagar / alterar | `getMarkers`, `deleteMarkers`, `changeMarker` | `marker_get`, `marker_delete_one/all` | 🆕 ⭐ `GetMarkers`, `DeleteMarkers`, `ChangeMarker` |

🆕 ⭐ **A família de marcador do Media Composer é completa e está em uso de produção** (Quickture Avid Helper) — esta coluna era ⛔ até 2026-08-24.

⚠️⚠️ **`createMarker` recebe SEGUNDOS**, num app onde quase tudo é tick. Misturar as unidades aqui é
erro silencioso.

⚠️ **Marcador de sequência não tem dono** — mora num *tempo*, não num clipe nem numa trilha. Para
relatório de conform, o texto precisa carregar trilha + nome do clipe, ou fica ambíguo. (Marcador de
`projectItem` tem dono, mas não aparece na timeline.)

### J.3 🆕 Marcar para outro profissional: marcador na TIMELINE e cor LOCAL — `relatado pelo autor` 2026-09-27

Regra de ofício do autor (editor), para quando a automação precisa avisar quem recebe ("este clipe foi
estabilizado no Avid"). Não foi medido em arquivo; as formas no DRT ficam para a amostra do caso E07.

- **O marcador vai na TIMELINE, não no clipe.** No Resolve e no Premiere, isso não traz problema.
  Marcador NO clipe é marcador na bin, e isso não é necessário.
  - **Media Composer:** o locator pode ficar no primeiro quadro do segmento, porque lá ele NÃO vai
    para a fonte. Para padronizar, a automação pode ter uma **trilha só dela** para os locators.
- **A cor do clipe é boa para código de cores**, mas cuidado com **LOCAL × GLOBAL**:
  - **local** pinta só aquele segmento na timeline;
  - **global** pinta o clipe na bin, e isso repercute em TODOS os segmentos dele, em qualquer timeline.
  - **Premiere e Media Composer:** a escolha é uma opção nos ajustes da timeline.
  - **Resolve:** é global quando a cor vem da BIN de mídia. É local quando vem do menu de contexto da
    TIMELINE (botão direito no segmento), e a local tem prioridade sobre a global.
  - ⇒ A automação usa cor **LOCAL**, para não pintar o clipe em outras timelines do colorista.
- **Uma trilha de notas:** um título (Text) numa trilha nova, com o texto que explica o efeito e os
  parâmetros, comunica mais do que um marcador. É proposta do autor; ver a Carta 1.2 e o
  `motor/titulos` do De Lá Pra Cá.
- 🆕 **O Reformat STRETCH é o sinal mais forte** (autor, 2026-09-27, teste com o curta PRODUCAO-A):
  a mídia é esticada até o quadro da timeline sem guardar a proporção, e com raster diferente a
  imagem DISTORCE. Nos takes da praia da PRODA_CORTE.02, os 9 segmentos em Stretch são todos de
  mídia 2048×1080 (1,9:1). O colorista não pode deixar passar; quem resolve é a PRODUÇÃO, então o
  aviso tem cor própria (De Lá Pra Cá: marcador Fuchsia + segmento Pink, o Stretch na 1ª linha).
  **Só o Stretch avisa**: Pillarbox, Crop e Keep Size não deformam a imagem.
- 🆕 **Velocidade mudada pelo editor também se marca** (conferir), com o % como o Avid mostra
  (`100 / relative_speed`; o `speed_ratio` é timeline ÷ fonte). A conformação de fps (`conform`)
  NÃO é decisão de edição e não se marca.

- 🆕 ⚠️ **Resolve: UM marcador de timeline por QUADRO** (`confirmado` no 21.1, 2026-10-03): um DRT
  com 14 marcadores em 6 quadros importou com 6; os outros somem sem aviso. Planos que começam
  juntos em trilhas diferentes dividem UM marcador — a nota precisa levar a trilha de cada aviso
  (De Lá Pra Cá: a cor mais forte e todas as notas, `V3 · …`). Ver
  [drt-drp/estruturas.md](../protocolos/drt-drp/estruturas.md). Premiere e MC: `pendente`.

### J.3a 🆕 O FORMATO da nota — padrão da família para os três NLEs — `decidido pelo autor` 2026-10-23

Desenhado e aprovado sobre o Resolve (De Lá Pra Cá, `tools/bancada_resolve/lab_notas_textplus/lab_notas_v3.py` +
`folha_formato_v3_colunas.png`); **replicar no Premiere e no MC** e melhorar com o uso.
- **Um gráfico com várias camadas**, não uma trilha por sobreposição: as notas que se tocam no tempo dividem UM clipe
  (Resolve: Text+ do Fusion, ver `drt-drp/estruturas.md` §"Várias camadas"); cada nota liga/desliga no quadro exato.
- **Os espaços fecham**: cada nota fica logo abaixo da anterior ATIVA; a nota cortada num keyframe guarda o lugar do
  segmento (não troca de posição com a vizinha). Folga de ~0,7 linha entre notas.
- **Hierarquia**: linha 1 = **trilha** (azul-claro) · **nome do segmento** na cor do TIPO de clipe · **TC source in >
  out** (cinza #A5A5A5; omitido quando não há source: título, ajuste). Linhas seguintes = os efeitos, ex.:
  `3D Warp · escala X · linear · 3 keyframes > 56%-75% (56%-75%-100%)` — o nº de keyframes e o intervalo atual em vermelho.
- **Cor do tipo**: vídeo branco · título verde · Compound lilás · multicam laranja · ajuste rosa · a palavra RAMPA amarela.
- **Rampa**: só o 1º e o último valor (nada de nota por quadro).
- **Compound / multicam (e nest do Premiere, collapse do Avid)**: o conteúdo interno recuado, trilhas internas
  **V2.1, V2.2…** num azul MAIS claro.
- **Colunas**: nenhum texto embaixo do rótulo da trilha — nome e linhas de efeito começam na mesma coluna; o rótulo de
  dentro começa na coluna do nome de fora. Com fonte proporcional a coluna vem da LARGURA medida da fonte, não de espaços.
- Glifos: só os que a fonte tem (o Text+ não tem fallback: "→" virou quadradinho) — separador ">".
- Abertos: keyframe não linear (só tipo + nº?); cor para "refazer/conferir".

### J.3b 🆕 O vídeo de REFERÊNCIA do corte — `relatado pelo autor` 2026-10-03

Regra de ofício do autor (editor), para conferir um conform contra o que a edição aprovou:

- **Onde ele costuma estar:** um arquivo **.mp4 na trilha de vídeo mais alta, de ponta a ponta da
  timeline** (o export do corte). Uma automação pode tentar identificá-lo sozinha por essa forma
  (um clipe só, do início ao fim, na trilha de cima) — e, achando, não traduzir como plano.
- **Quando o editor indica o arquivo à mão:** ele entra numa **trilha NOVA, acima de todas** — nunca
  numa trilha existente, para não sobrescrever nada.
- ⚠️ **Exceção: a trilha de NOTAS** (os títulos com o texto dos avisos, J.3). A referência fica
  ABAIXO dela: acima, ela cobre as notas no play.
- Desligada por padrão (liga-se para comparar, ou usa-se o wipe). De Lá Pra Cá: os dois caminhos
  estão `pendentes` (registrados no `.dev/HANDOFF.md`); hoje a conferência automática lê o MP4 direto
  do disco (`tools/conferir_conform.py`), sem pô-lo na timeline.

### J.4 🆕 ⭐⭐ ATUALIZAR a timeline de quem recebe (o reconform sem perda) — `confirmado` no Resolve 19, 2026-09-28

A edição muda o corte depois que a cor (ou outro setor) já começou. A operação: aplicar SÓ a mudança
da montagem na timeline em que o colorista trabalha, sem perder nada dele e sem retrabalho (regra do
autor: solução com perda ou retrabalho é recusada). Agnóstica de NLE: o motor decide, cada NLE executa.
Ciclo completo feito pelo autor na PRODA (v01 colorida no Resolve, v02 com a sequência DUPLICADA no Avid,
6 planos a menos e 1 aparado): a timeline foi atualizada e a antiga foi para o Backup.

**O que decide (comum aos três NLEs; `_DeLaPraCa/motor/atualizar.py`):**
- compare a **Carta de PARTIDA** (a que gerou a timeline de quem recebe, guardada no Importar) com a
  **Carta NOVA** — nunca com a timeline de trabalho (os cortes internos e as camadas do colorista não são
  mudança da montagem);
- case os planos pelo **conteúdo** (reel/mídia + trecho da fonte), **em ORDEM** trilha a trilha (maior
  subsequência comum): pela posição mais próxima erra com o mesmo trecho repetido e ripple grande;
- classes: igual, só deslocado, aparado/esticado, novo, retirado, take TROCADO (vira novo: a correção de
  uma câmera não serve para outra — regra do autor);
- conta em TEMPO de imagem; áudio fora por padrão; faixas 25%/60% (editáveis) para "atualização",
  "grande" e "sugere importar como nova";
- o editor costuma DUPLICAR a sequência a cada versão (o mob id muda): sugira a partida pelo nome sem o
  número da versão, e deixe quem recebe escolher.

**Como executa (caminho B — reescrever a timeline do PRÓPRIO colorista):**
- cada item da timeline de trabalho segue o plano da partida que o contém (fica, anda, é aparado só nas
  pontas, sai): o corte interno do colorista sobrevive; camada fora de plano anda pelo mapa de tempo (ou
  fica e vai para "conferir" se o trecho embaixo saiu); transição anda com o corte ou sai (contada);
  marcadores de timeline andam pelo mapa; ponta esticada e plano novo são INSERIDOS pela API;
- a timeline antiga NUNCA é apagada: renomeada com data e movida para uma pasta de Backup;
- conferência antes (o arquivo exportado é a timeline pedida?) e depois (a importada tem a contagem
  prevista? se não, apaga a importada e não toca na do colorista).

**As armadilhas medidas no Resolve** (detalhe nos temas dele):
- a API não move nem apara item → reescrever o DRT exportado (`drt-drp/estruturas.md`);
- a correção de cor viaja no DRT, por item; a versão 19 × 21 não muda o que se edita (U01);
- ⛔ troque SÓ os ids da timeline: trocar os da mídia do pool e da pasta Master TRAVA/DERRUBA o Resolve
  num projeto real (U02, `drt-drp/estruturas.md` CORRIGE);
- a API conta as transições junto com os itens; pela ponte JS a constante `EXPORT_DRT` não existe (vale 1);
  o `Export` por script externo exporta a timeline errada (`resolve-scripting/api-scripting.md` §7);
- o início da timeline vem do NLE (`GetStartFrame`), nunca do 1º plano (a PRODA começa em 00:00:00:01).

**Premiere e Media Composer:** o mesmo desenho, `pendente` de medição (a sequência no `.prproj` e o
segmento na `.avb` guardando a pilha de efeitos de quem recebe).


#### 🆕 As TRANSIÇÕES no Atualizar — de corte a corte (autor, 2026-10-01: "nada deve ser perdido")

Medido no U03 (Resolve 21.1, Mac): o cross-fade de 40 quadros do editor no take trocado virava corte seco.
- **A Carta (Avid/AAF) e o NLE contam o plano diferente.** Na Carta, o plano que SAI numa transição avança
  sobre ela (488 = 448 até o corte + 40); a transição é um segmento próprio com `cutpoint` (o corte =
  `tc_in + cutpoint`). No Resolve o plano termina NO CORTE, e a transição é um item à parte que usa a sobra da
  mídia. Regra agnóstica (`motor/atualizar.py::_de_corte_a_corte`): o plano a inserir vai de corte a corte;
  o que entra por uma transição centrada começa no corte e a fonte anda junto.
- **A transição do colorista fica** quando um vizinho sai mas um plano NOVO encosta no mesmo corte
  (`reescrever.aplicar(cortes=…)`). Medido no 21: a transição sobrevive à importação SEM o vizinho, e o plano
  inserido depois pela API (`AppendToTimeline` até o corte) encosta nela; exportada de novo, ela está lá.
- **Comparar transições pela REGIÃO** (trilha, início absoluto, duração) bate 58 de 58 entre a Carta e o DRT
  do Resolve, com 8 `cutpoint` e 3 `AlignmentType` diferentes — não é preciso traduzir o alinhamento.
- ✅ (2026-10-01, decisão do autor) **a transição NOVA do editor é ESCRITA no DRT** (o bloco do Trazer,
  `writer._make_transition`) e a que ele TIROU sai — só as da versão antiga; a do colorista fica.
  ⛔⭐ **O alinhamento sai da GEOMETRIA da timeline**, não do `cutpoint` do Avid: no Resolve 21 uma transição
  com `AlignmentType` que não casa com onde os planos se encontram é **descartada na importação, calada**
  (medido: um fade de entrada com 2 sumiu; com 1 entrou). E o lado de lá pode faltar NESTA máquina (mídia
  ausente: o Trazer faz ali um fade). Regra: planos que se encontram no início/meio/fim da região → 1/2/3;
  só o da direita começando no início → 1 (fade de entrada); só o da esquerda terminando no fim → 3; senão
  não escreve e avisa. Os planos que a casca VAI inserir contam como presentes.
- (histórico) O que a API não faz virava aviso: transição NOVA na versão do editor (a API do 19 não cria; a
  `TimelineItem.AddTransition` só aparece no 21.1) e transição que o editor TIROU mas ficou na timeline.
  `pendente`: criar a transição nova (no DRT, clonando um `Sm2TiTransition`, ou pela `AddTransition` com
  detecção de versão).
- No Resolve 19.0.0b: `pendente` (a mesma técnica; conferir na PRODA).
- ⛔⭐ **O vazio de uma trilha pode NÃO vir como segmento** — `confirmado` 2026-10-19 (PRODA_RELINKER_ALTA.aaf pelo
  app no Resolve Studio 19.1.4, Windows). O AAF do MC não traz o filler da V3: o título "PRODUCAO-A" com fade-out
  (00:00:40:04, 40 q) e o plano seguinte da V3 SEIS minutos depois ficam vizinhos na lista. Emparelhar pela ordem
  fez um cross-dissolve falso, e o plano esticou para trás até o corte (86 → 8.643 quadros sobre V1 e V2;
  conferência pela referência 67/110). Regra (`drp/writer._transition_overrides`): parceiro de dissolve só quem
  ENCOSTA na transição no tempo (o de antes termina em ≥ início dela; o de depois começa em ≤ fim dela); o resto é
  fade. Depois: 107/110 (os 3 = o título, estilo padrão do Resolve). Vale para toda leitura sem filler explícito.
- ✅ Conferido pelo autor no Resolve 21.1 (Mac, 2026-10-01): o U03 v01 → v02 pela casca, transições e marcadores certos.

---


## K. ⭐⭐ Estado entre execuções — reconstruir × inserir

**A decisão de arquitetura mais importante de qualquer app que rode mais de uma vez sobre o mesmo
projeto.** As duas edições do **mesmo produto** escolheram lados opostos, e a razão é a plataforma:

| | reconstruir (Resolve) | inserir (Premiere) |
|---|---|---|
| como | apaga a timeline inteira e remonta a partir da bin | guarda `assignedTracks` no XMP privado |
| estado a manter | ⭐ **nenhum** — a timeline é função pura da bin | o que a rodada anterior fez |
| correção | sempre correta, por reconstrução | depende do registro estar certo |
| ⛔ custo | **apaga todo trabalho manual do editor** | preserva |

⚠️ **E o produto que reconstrói não avisa** — o manual diz "rode num projeto existente para
adicionar mais material" e nada sobre aparo, efeito, marcador e música que serão destruídos.

⭐ **Se um app nosso reconstruir, isso precisa estar na interface, não escondido.**

---

## L. Unidades de tempo — e os três modos de falhar

| NLE | unidade | armadilha |
|---|---|---|
| Premiere | **ticks** (254.016.000.000/s) | ⚠️ estoura o inteiro seguro do JS → existem variantes `…Str` que trafegam como **string** |
| Resolve | **frames** | ⚠️ `hh:mm:ss:ff` por `split(':')` **não cobre drop-frame** |
| Avid | frames + TC | veredicto de conjunto antes de confiar num TC |

⛔⭐ **O pior modo de falha visto:** conversão de timecode que, ao falhar, **devolve 0** — o clipe vai
para o **início** da timeline em vez de levantar erro. Falha silenciosa e plausível.

⚠️ **TC que existe e mente é pior que TC nenhum** (medido no OP-Atom do Avid: o mesmo clipe lê
`08:12:41:20` numa pasta e `01:00:00:00` noutra). Ver
[`tempo-e-timecode.md`](tempo-e-timecode.md).

### 🆕 ⭐ O quarto modo: a TAXA FIXA na hora de mostrar

`confirmado` — Assist anterior 2026-09-19 (Media Composer 2024.12, Windows) e Órbita 2026-09-21.

Converter quadros em segundos **na tela** com uma taxa literal (`frames / 24`) é o modo de falha
que nenhuma suíte pega: não levanta erro, não some com o dado, só **mente por uma porcentagem**.
A 29,97 são **25% a mais** — um take de 60 s exibido como 75 s, na coluna que existe justamente
para o editor decidir sem abrir a bin.

- A taxa tem de vir **do material**, item a item, e viajar junto com a duração no mesmo payload.
  Sem isso quem desenha a tela não tem como saber, e inventa.
- ⚠️ **Sem taxa, mostre QUADROS** (`900q`), nunca um segundo estimado: um número errado com
  unidade certa passa por medição; um número certo com unidade estranha faz a pessoa perguntar.
- ⛔ **Onde ele se esconde:** o mesmo dado já viajava (`edit_rate`), usado por UM painel e não pelo
  outro — e o comentário do servidor dizia, literalmente, *"o painel do Avid não usa"*. O defeito
  vive na distância entre dois consumidores do mesmo payload.

**Visto em:** Órbita (aba Subclipar do painel do Avid) e Assist anterior (o mesmo código portado, que
foi onde alguém reparou). Conserto de 19/09 lá, 21/09 aqui.

---

## M. Como o plugin sabe que algo mudou

🆕 ⚠️⚠️ **CORREÇÃO de 2026-08-24: o PREMIERE TEM eventos.** Este parágrafo dizia que nenhuma das
três plataformas tinha, e estava errado.

```javascript
app.bind("onActiveSequenceChanged", handler);   // + onSequenceActivated
                                                 // + onSourceClipSelectedInProjectPanel
```

⭐ E a ponte JSX → painel é o **`CSXSEvent`** (`type` + `data` + `.dispatch()`), habilitada por
`ExternalObject("lib:PlugPlugExternalObject")` — a DLL que aparecia solta em `.zxp` sem que
soubéssemos para quê.

⚠️ **O que continua não existindo:** evento de *"a timeline mudou"* ou *"a seleção NA TIMELINE
mudou"*. `onSourceClipSelectedInProjectPanel` é o **painel de projeto**. ⭐ **Então: trocar de
sequência não precisa de polling; mudança na timeline ainda precisa.**
Ver [`quickture-ppro.md`](../plugins/premiere-cep/quickture-ppro.md) §2.

🆕 ⚠️ **E no Resolve há uma PISTA:** o addon nativo dos Workflow Integration Plugins exporta
`RegisterCallback` / `GetCallbackFunction`. Se for callback de verdade, esta seção muda de novo.
⛔ **`hipotese`** — lido em nome de símbolo, não medido → [`workflow-integration.md`](../plugins/resolve-scripting/workflow-integration.md).

⛔ **Por ora, no Resolve e no Media Composer** o problema permanece, e as duas soluções vistas são de polling:

1. **Comparação de estado** — `AppWatcher`/`WatcherActiveProj.compare()` (Selector).
2. ⭐ **Impressão digital de topologia** — `_cvpComputeTrackTopologySig` (Chat Video Pro): saber se a
   timeline mudou **sem reler a timeline**.

⚠️ **E o polling paga o custo do §I.** `isEnabled` a 10966 dentro de um laço é uma decisão de
projeto, não um detalhe.

⭐ **No Avid há evento de verdade** (`BinRowSelectionChanged`), e há **arrasto MC → painel** via MIME
customizado no `ondrop` do DOM — que **não aparece em símbolo nenhum do binário**, porque quem
implementa é o Chromium. ⭐⭐ *Metade da superfície de um painel é a do navegador.*

---

## ⛔ O mapa dos BURACOS — o que este arquivo não sabe

Escrito de propósito, porque é o que dirige a exploração:

| # | buraco | onde perguntar |
|---|---|---|
| 1 | ~~O Resolve não tem camada de operação~~ | ✅ **FECHADO 2026-08-24** → [`plugins/resolve-scripting/`](../plugins/resolve-scripting/) |
| 2 | **Mover clipe no Resolve: existe primitivo?** | nenhum produto lido move; **buraco, não ausência confirmada** |
| 3 | **Edição de timeline no Media Composer** | só drop e `.avb` por fora — a superfície real não foi mapeada |
| 4 | **`nodeId` sobrevive a um `move()`?** | medição curta, fecha a identidade do §H |
| 5 | **Premiere: o redesenho depois de mover** | 5 caminhos falharam; `updateUI` nunca tentado |
| 6 | **`GetListOfBinItems` do Avid: forma do caminho** | `pendente` desde a 1ª rodada |
| 7 | **Cor de etiqueta do clipe no Avid** | provável `ATTB`/`_USER` |
| 8 | **Metadado no Avid: dá para ESCREVER?** | nunca medido |
| 9 | ~~Semântica do binlock~~ | ✅ **AVANÇADO 2026-08-24**: há **DOIS** mecanismos — o `.lck` (pasta comum, degradado) e o ⭐ **`Flock`** da API de shared storage da Avid (`ASIsFlockPresent`, `ASGetFlockList`), consultável por API. Ver [storage-como-integracao](../protocolos/projeto-avid/storage-como-integracao.md) |
| 10 | ~~Protocolo do WebSocket do ESION~~ | ✅ **FECHADO 2026-08-24**: 19 mensagens, e são **10 portas** (52413–52422), não uma. 🆕 Abriu um buraco novo: **o `allowedDomains` filtra `ws://`?** → [esion §5.5](../plugins/avid-panel-sdk/esion-arquitetura.md) |
| 11 | ~~**Premiere: existe via de API para CRIAR merged clip?**~~ | ✅ **FECHADO 2026-09-06: NÃO EXISTE** — `confirmado (estático)` no 25.6.5. As tabelas de classe do `ScriptLayerPPro.framework` (`Application`/`Project`/`ProjectItem`, lidas INTEIRAS) têm `createSubClip` e `isMergedClip` como controle positivo e **nenhum verbo de fundir**; o `ScriptLayerPProQE` não tem nem `merge` nem `subclip`. O `Merge Clips` é diálogo modal (`Dialogs.framework` + `MergeClipsDialog.adam.eve`). ⭐ Método: `strings` + `grep -n "class$"` dá o índice das classes → [subclipe-e-merged-clip §3](../plugins/premiere-cep/subclipe-e-merged-clip.md) |
| 12 | ~~**Avid: remover `BinItem`**~~ ✅ **MEDIDO 2026-09-12** (96→95 itens, o resto intacto), e a cópia entre arquivos também: `AVBObject.copy(root)`. 🆕 Abriu um buraco novo: ~~**`SourceMob` com `WinFileLocator` (AMA) não sobrevive ao `write()` do pyavb**~~ ✅ **FECHADO 2026-09-13: era a STRING NULA** (`ff ff` regravado `00 00`), não o AMA → [escrita.md](../protocolos/avb/escrita.md) |

### ⭐ Onde a exploração rende mais, na ordem

1. ~~Fechar o §1 (pasta do Resolve)~~ ✅ **feito em 2026-08-24.**
2. ~~Mimiq + Osiris~~ ✅ **feito em 2026-08-24** — e rendeu o **eixo 3** (§0) além do buraco 9.
3. ~~ESION (buraco 10)~~ ✅ **feito em 2026-08-24.**
4. ~~Quickture: o source map com o TypeScript completo~~ ✅ **feito em 2026-08-24** → [`quickture-ppro.md`](../plugins/premiere-cep/quickture-ppro.md). ✅ **Avid Helper feito em 2026-08-24** → [`quickture-avid-helper.md`](../plugins/avid-panel-sdk/quickture-avid-helper.md).
5. 🆕 ⭐⭐ **Fechar o §11 — fundir merged clip no Premiere.** É o que destrava portar a aba
   Subclipar do Avid para o Premiere, e o custo de entrada é baixo: começa por um `grep` nos sete
   produtos já dissecados desta pasta.
6. ~~Jumper~~ ✅ **feito em 2026-08-24** — mas **só o lado de INTEGRAÇÃO** → [`workflow-integration.md`](../plugins/resolve-scripting/workflow-integration.md).
   ⛔ O lado de **ML** (scene detection, agrupamento facial, transcrição) continua `pendente` **por
   relevância, não por régua**: o domínio dele é busca de mídia. Rende quando entrarmos em decupagem.

---

## Ver também

- [`analise-de-executaveis.md`](analise-de-executaveis.md) — como dissecar, e a **régua** (revisada
  em 2026-08-24: ler tudo, registrar mecanismo).
- [`modelo-de-execucao-de-agente.md`](modelo-de-execucao-de-agente.md) — os três modelos de como um
  painel manda trabalho para o NLE.
- [`tempo-e-timecode.md`](tempo-e-timecode.md) · [`modelo-neutro-efeitos.md`](modelo-neutro-efeitos.md)
- [`api-extendscript.md`](../plugins/premiere-cep/api-extendscript.md) — a referência do Premiere.
- [`plugins/avid-panel-sdk/`](../plugins/avid-panel-sdk/) — a referência do Media Composer.

### Conferência pela imagem com burn-in na referência (2026-10-04, De Lá Pra Cá)
O vídeo de referência do editor costuma ter **burn-in** (TC num canto, nome do clipe no outro). Numa cena
escura, esse texto branco vira a parte mais forte da imagem e a correlação de forma desaba (0,08 numa
cena idêntica): 5 falsos "não confere" e 2 quadros pretos no PRODB. Comparar **sem as bordas** (5% de
cada lado: 8 de 160 colunas, 8 de 90 linhas) zerou os falsos (1.158/1.158, pior 0,92) e ainda acusa
80% dos pontos com a referência deslocada 1 s (59% com 6 quadros, 48% com 2 — o que escapa é plano
parado, onde o escorregão não se vê). Imagem parada SOBRE outro plano (máscara 1.85, logo) não é plano:
não gera ponto. De Lá Pra Cá: `motor/tools/conferir_conform.py`.

## 🆕 ⭐ O 9100 não precisa de token nem de painel — `confirmado` (2026-10-18, MC 24.6.0/Windows)

Cliente gRPC externo (Python grpcio) contra `127.0.0.1:9100` com `RequestHeader` VAZIO leu `GetHostInfo`,
`GetAppInfo`, `GetOpenProjectInfo` e `GetBins` **sem token e com o painel nosso escondido** (não-assinado,
fora do menu). ⇒ a autenticação por token é do GATEWAY (4920/4930, para a webview); o backend 9100 do MC
responde direto a quem alcança o loopback. Operar o MC "por fora" (estilo Órbita) **não depende** de assinatura
nem de o painel aparecer. Ressalva: RPC varia por versão (`GetListOfWindows`/`GetListOfCommands` =
`UNIMPLEMENTED` no 24.6.0). Detalhe e tabela em `plugins/avid-panel-sdk/ativar-no-2021-ftf.md` §Teste B.

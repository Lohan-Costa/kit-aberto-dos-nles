# Quickture (Premiere) — a maior superfície de ExtendScript que este banco leu

Nono caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md).

**Como chegou:** o `.zxp` (6,3 MB) carrega `jsx/index.jsxbin` **compilado** — e, ao lado dele,
**`jsx/index.js.map`**, o source map do próprio ExtendScript, com `sourcesContent` completo. O
`ppro.ts` original tem **6.534 linhas e 98 funções**.

> ⚠️ **Nota de régua.** A primeira análise do Quickture (2026-08-08) encontrou o source map do
> *front-end* e, sob a régua antiga, leu **apenas a lista de 243 caminhos**. A régua foi revisada em
> 2026-08-24 (*ler tudo, registrar mecanismo*), e este documento é resultado dela. **Nada aqui é
> transcrição** — são as mecânicas, com as chamadas de API que qualquer um pode ler na documentação
> da Adobe. Nenhum algoritmo de produto foi copiado, e o licenciamento não foi tocado.

⭐ **Por que rende tanto:** o Quickture faz o que quase nenhum outro painel faz — **corta, apaga,
insere, marca e guarda estado**. Ele preenche sozinho três buracos do
[mapa de operações](../../transversal/operacoes-de-nle.md).

---

## 1. ⭐⭐ CORTAR a timeline — `razor` existe, e é do QE

O mapa dizia que dos onze produtos dissecados nenhum mexia em clipe já colocado. O Quickture mexe:

```javascript
var sqe = qe.project.getActiveSequence();
sqe.razor(cutStartTime);      // ← TIMECODE como string
sqe.razor(cutEndTime);
```

⭐ **`razor(timecode)` é o primitivo de corte, e vive no QE DOM.** Aceita **string de timecode**, não
ticks nem segundos — mais uma operação de trilha/edição que o DOM público não tem.

Depois do corte, a remoção é do DOM:

```javascript
clip.remove(true, true);      // TrackItem.remove(ripple, shift)
```

⭐ **`TrackItem.remove(ripple, shift)`** — dois booleanos: *ondular* e *deslocar*. É o primitivo de
apagar clipe da timeline que o §C do mapa tinha como vago.

⚠️ **E uma prática que NÃO se deve copiar:** eles comparam timecodes **como strings**
(`clipEndTime < cutEndTime`). Funciona enquanto o formato for `hh:mm:ss:ff` com zeros à esquerda e
o mesmo frame rate dos dois lados — e falha calado em drop-frame ou em taxas misturadas. *A
comparação certa é em frames ou ticks.*

⚠️ Eles varrem a trilha **de trás para frente** (`trackClipIndex = track.clips.length - 1`,
decrescendo) e param cedo quando o clipe já está antes da janela. É a resposta ao problema que o
banco já registra: **a coleção de clipes reordena por tempo**, então apagar de frente para trás
escorrega os índices.

---

## 2. ⭐⭐⭐ O Premiere TEM eventos — e o mapa dizia que não

O §M do [mapa](../../transversal/operacoes-de-nle.md) afirmava que *"nenhuma das três plataformas
tem evento decente"*, e registrava duas soluções de polling. **A afirmação estava errada para o
Premiere.**

```javascript
var mylib = new ExternalObject("lib:PlugPlugExternalObject");

function onActiveSequenceChanged() {
    var eventObj = new CSXSEvent();
    eventObj.type = "onActiveSequenceChanged";
    eventObj.data = app.project.activeSequence.sequenceID;
    eventObj.dispatch();
}
app.bind("onActiveSequenceChanged", onActiveSequenceChanged);
```

**Três eventos confirmados, ligados por `app.bind(nome, handler)`:**

| evento | dado que carregam |
|---|---|
| `onActiveSequenceChanged` | `sequenceID` |
| `onSequenceActivated` | `sequenceID` |
| `onSourceClipSelectedInProjectPanel` | — (só o aviso) |

⭐ **E a ponte JSX → painel é o `CSXSEvent`**: o handler no ExtendScript monta um evento com `type` e
`data` e chama `.dispatch()`; o lado JS do CEP escuta por `addEventListener` do `CSInterface`. O
`ExternalObject("lib:PlugPlugExternalObject")` é o que habilita isso — e é a mesma DLL que aparece
solta no `.zxp` do Chop Chop, cuja função nós não tínhamos identificado.

⚠️ **O que isto NÃO resolve:** não há evento de *"a timeline mudou"* nem de *"a seleção na timeline
mudou"*. `onSourceClipSelectedInProjectPanel` é o **painel de projeto**, não a timeline. Então a
impressão digital de topologia do Chat Video Pro e o polling do Selector continuam necessários —
**para a timeline**. O que muda é que **trocar de sequência não precisa ser descoberto por polling**.

⭐⭐ **Correção que vale para o Órbita:** se o nosso painel faz polling para saber que a sequência
ativa mudou, isso é trabalho desperdiçado.

---

## 3. ⭐⭐ A receita completa do XMP privado — em fonte original

Terceira aparição do metadado privado de projeto (depois do Chop Chop e do Automation Blocks), e a
primeira em que se vê a **sequência exata de chamadas**:

```javascript
ExternalObject.AdobeXMPScript = new ExternalObject('lib:AdobeXMPScript');

project.addPropertyToProjectMetadataSchema(NOME, "Rótulo legível", 2);
var xmp = new XMPMeta(projectItem.getProjectMetadata());
xmp.setProperty(kPProPrivateProjectMetadataURI, NOME, valor);
projectItem.setProjectMetadata(xmp.serialize(), [NOME]);
```

⭐ **Quatro detalhes que só aparecem no fonte:**

1. **`addPropertyToProjectMetadataSchema` é chamado ANTES DE LER também**, não só antes de escrever —
   nos *getters* e nos *setters*. Trata-se o schema como algo que pode não estar lá.
2. O **terceiro argumento é o tipo** (`2`).
3. ⭐⭐ **Há DOIS escopos, e a escolha é de granularidade:**
   - **por sequência** → `sequence.projectItem.getProjectMetadata()`
   - **por projeto** → `project.rootItem.getProjectMetadata()`
4. ⭐ **A versão do schema vai no NOME do campo** — `QuicktureDataV1.1`, `QuicktureProjectDataV1`.
   Migração de formato sem migrar dado: campo novo, nome novo.

⚠️ E confirma a assimetria já registrada: `setProjectMetadata` recebe **o XMP serializado E a lista
dos campos alterados**.

---

## 4. Marcadores — a receita, com as unidades

```javascript
var m = sequence.markers.createMarker(inicioEmSEGUNDOS, nome, duracaoEmSEGUNDOS);
m.comments = "…";
m.setColorByIndex(0);   // 0..7
```

⚠️⚠️ **`createMarker` recebe SEGUNDOS**, enquanto quase tudo no Premiere é tick. O código deles
converte timecode → ticks → segundos justamente por isso. **Misturar as unidades aqui é erro
silencioso.**

⭐ **Oito cores, por índice** (`setColorByIndex`, 0–7), com 0 = verde. Eles validam a faixa duas
vezes antes de aplicar.

Superfície completa de marcador vista: `getMarkers`, `addMarkers`, `changeMarker`, `deleteMarkers`,
`updateSequenceMarkers`.

---

## 5. O resto da superfície — 98 funções, por família

Vale como catálogo do que é possível; os nomes são autoexplicativos.

| família | funções |
|---|---|
| **sequência** | `createChildSequence` · `cloneSequence` · `generateChildSequenceName` · `getSequenceChain` · `getSequenceTree` · `moveSequenceToBin` · `renameSequence` · `openSequence` · `getSequenceInfo`/`Resolution`/`Timebase`/`Name` · `getSequences` · `getSequenceIds` · `getSequenceCount` |
| **edição** | `cut` · `insertClipIntoSequence` · `performSequenceEdit` · `calculateClipAdjustments` · `processVideoClip` · `processAudioClip` · `deleteAllTrackClips` · `clearAllSequenceTracks` |
| **trilhas** | `lockAllTracks` · `unlockAllTracks` · `setAllTracksLockState` · `detectMissingTracks` |
| **análise** | `areClipsEquivalent` · `areClipsEquivalentAndWithSameTimings` · `areClipsOverlapping` · `areTimelinePositionsOverlapping` · `areSourceSegmentsOverlapping` · `isAudioLinkedToVideo` · `countOverlappingVideoClips` · `detectOverlappingClips` |
| **playhead / monitores** | `setPlayheadPosition` · `setPlayheadPositionByFrames` · `advancePlayheadByFrames` · `openSequenceInSourceMonitor` · `setPlayheadPositionInSourceMonitor` · `playClipSegment` |
| **bins / mídia** | `createBinOfSubclips` · `importFileIntoFolder` · `importPrprojFile` · `exportSequenceAsProject` · `getProjectFolderNames` · `getParentBin` · `createMediaFile` · `findSourceClipAtTime` |
| **estado** | `getMetadataValue`/`setMetadataValue` (sequência) · `getProjectData`/`setProjectData` (projeto) |
| **saída** | `encodeSequenceViaAME` |

⭐ **`createBinOfSubclips(projectID, binName, [{sequenceID, subclipName, inTimecode, outTimecode}])`**
— subclipes **a partir de sequências**, numa bin nova. Operação que não estava no mapa.

⭐ **`getSequenceChain` / `getSequenceTree` / `createChildSequence`** — o produto trabalha com
**hierarquia de sequências** (versões filhas de uma sequência-mãe), e mantém a árvore. É um modelo
de versionamento dentro do próprio projeto.

⚠️ **`CONTROL_SURFACE_SERVER_URL = "http://localhost:9876/command"`** com
`initializeControlSurfaceEdit` / `setupControlSurfaceClip` / `finalizeControlSurfaceEdit` — há
integração com superfície de controle por HTTP local. Não investigado.

⭐ **Identidade:** tudo é endereçado por **`projectID` + `sequenceID`** (`findProjectByID`,
`findSequenceByID`, `findProjectAndSequenceByID`). Não por índice, não por nome. É a disciplina que
o §H do mapa recomenda, aplicada por um produto inteiro.

---

## 6. O andaime: Bolt CEP

Os caminhos do source map denunciam o scaffold: `cep.config.ts`, `src/jsx/{aeft,ilst,anim,ppro,phxs}`,
`src/shared/shared.ts`. É o **Bolt CEP** (Vite + TypeScript para painéis CEP), com os stubs de After
Effects, Illustrator, Animate e Photoshop **ainda no bundle** embora o produto seja só Premiere.

⚠️ **Consequência prática:** um `.zxp` desses carrega código morto de quatro hosts. E — mais
importante para quem analisa — **o pipeline do Bolt CEP emite source map ao lado do `.jsxbin` por
padrão**. É por isso que dois produtos diferentes já apareceram com o fonte recuperável.

---

## ⚠️ A régua desta rodada

- **Lido:** o `sourcesContent` do `jsx/index.js.map` (11 arquivos, dos quais `ppro.ts` com 130 KB).
  Registrado **mecanismo e chamadas de API** — nada de algoritmo de produto.
- **NÃO lido:** o `assets/main-*.js.map` (20 MB, o front-end React) — fora da pergunta desta sessão,
  que é *como o plugin fala com o NLE*.
- **Não tocado:** licenciamento; a integração com a superfície de controle; o Avid Helper (pacote à
  parte, 78–183 MB, ainda por abrir).
- **Nada instalado, nada executado.**

## Buracos

| # | pergunta |
|---|---|
| 1 | **Existem mais eventos em `app.bind`?** Três foram vistos porque o produto usa três. A lista completa não é conhecida — e é a pergunta mais valiosa desta análise |
| 2 | `razor()` respeita trilhas travadas/desabilitadas? |
| 3 | O que o `remove(ripple, shift)` faz com áudio vinculado |
| 4 | O Avid Helper do Quickture — não aberto |

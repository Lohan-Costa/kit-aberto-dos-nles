# Subclipe e Merged Clip no Premiere — o que já está respondido, e o que falta medir

> **Escrito em 2026-09-06**, quando o autor definiu a próxima missão do Órbita:
>
> > *"A nossa próxima missão será portar a versão do plugin do media composer para o Adobe
> > Premiere… A maior mudança é que no AVID nós criamos subclipe, no Premiere criamos Merged
> > clips, que na prática são a mesma coisa — só precisamos criar a automação."*
>
> ⭐⭐ **Este arquivo é a prova de que o banco se paga.** A primeira versão dele listava cinco
> perguntas em aberto. Um `grep` de dois minutos no próprio banco respondeu **três** — inclusive a
> que parecia mais cara. O que sobrou é bem menor, e bem mais preciso.

---

## 1. ⚠️⚠️ Antes de tudo: são DOIS objetos, não um

A frase *"merged clip é o subclipe do Premiere"* é verdadeira no **propósito** e falsa no
**mecanismo**. O Premiere tem os dois conceitos, e eles fazem coisas diferentes:

| | o que faz | o que resolve do nosso problema |
|---|---|---|
| **merged clip** | funde um item de vídeo com um ou mais de áudio, alinhados por offset | a **junção** câmera + som direto |
| **subclip** | recorta um trecho (in/out) de um item da bin | o **aparo** para onde imagem e som coexistem |

⭐ **O subclipe do Avid faz as duas coisas de uma vez** — porque lá o material chega já sincronizado
numa timeline, e o aparo e a junção A/V saem do mesmo mob.

### ⚠️⚠️ A CORREÇÃO DE VOCABULÁRIO — e ela não é preciosismo

> Do autor, 2026-09-06: *"existe subclipe no premiere mas não devemos confundir com o subclipe
> do media composer. o subclipe do premiere é apenas uma parte menor de um arquivo, mas sem
> juntar duas origens (camera + som direto), como é no avid. aqui o equivalente ao subclipe do
> media composer é o merged clip, esse sim junta duas origens como se fosse uma coisa só."*

⭐⭐ **O nome igual é uma armadilha, e a equivalência correta é `subclipe do Avid` ≙ `merged
clip do Premiere`.** O `subClip` do Premiere é um objeto MENOR: uma janela sobre **um** arquivo.

**Medido, e a própria sonda confirmou** (2026-09-06, 25.6.5): `createSubClip` sobre um clipe de
câmera crua devolveu um item com `getMediaPath()` **apontando para o mesmo arquivo da câmera** e
`isMergedClip = false`. Não há segunda origem — não porque a chamada falhou, mas porque **não é
isso que o objeto é**.

⛔ **Consequência para o porte:** escrever "vamos portar a aba Subclipar" já embute o erro. O
que a aba do Premiere tem de produzir é **merged clip** — e é justamente o que não tem API
(§3). O `createSubClip` só volta a importar DEPOIS, se um take precisar de aparo dentro de um
arquivo que contém vários.

⛔ **No Premiere são dois passos, e a ordem é forçada:** fundir primeiro, recortar depois.
`createSubClip` opera sobre um `projectItem`; se esse item for a câmera crua, o subclipe sai **sem o
som direto**. O item a recortar tem de ser o merged clip.

```
câmera + som direto  →  [MERGE]  →  "cam - Merged"  →  [createSubClip in/out]  →  a tomada
```

---

## 2. ✅ O que JÁ está respondido — não redescubra

### ✅ `createSubClip` existe na API — `confirmado`

```js
projectItem.createSubClip(name, inTicks, outTicks, hardBoundaries, takeVideo, takeAudio)
```

Visto num produto comercial dissecado — ver [`quatro-paineis-timeline.md` §5](quatro-paineis-timeline.md)
e [`dados/quatro-paineis.json`](dados/quatro-paineis.json) (`outras_operacoes.createSubClip`).

⭐ **A assinatura já entrega o que o porte precisa:** in/out **em ticks** (o aparo), e
`takeVideo`/`takeAudio` separados (o controle de o que entra no recorte). `hardBoundaries` decide se
o subclipe pode ser reestendido além do corte.

### ✅ A forma do merged clip no arquivo `.prproj` — `confirmado`, com a armadilha

[`protocolos/prproj/estruturas.md` §6](../../protocolos/prproj/estruturas.md):

- cada câmera vira uma `Sequence` própria com **`BE.Sequence.IsMergedClip = true`**;
- `AudioTrack A1` leva o WAV em `Start = -(offset de sync)` — **pode ser negativo**;
- **`MZ.ZeroPoint` = `AlternateStart`** da câmera; nome com o sufixo **`" - Merged"`**;
- ⚠️ a sequência merged é **mono** (`NumAdaptiveChannels=1`) — **não "corrigir" para stereo.**

⛔⛔ **E a armadilha que já custou um crash**, em [`escrita.md` §2](../../protocolos/prproj/escrita.md):
o Premiere 25.6.5 **fecha instantaneamente** (`EXC_BAD_ACCESS` em `AR::AudioPrefetch`) ao abrir um
projeto com merged clips mal formados. Uma câmera mergeada precisa de **4 MasterClips**, não 3, e é
o *camMC* (a cópia independente da mídia bruta) — **não** o MC da bin — que deve ser alvo do
`SubClip` de vídeo. Fechar o ciclo `Sequence → SubClip → MasterClip(bin) → AudioSequenceSource → a
mesma Sequence` é o que mata o app.

### ✅ O Órbita JÁ TEM essa maquinaria escrita — e ela está DESLIGADA

> **CORRIGE (2026-09-16):** ligada. `ExportOptions.merged_clips` gera um `<stem> - Merged`
> por câmera de tomada numa sub-bin `MERGED CLIPS`; as sequências continuam sem merged.
> E o `prproj/validate.py` do Órbita passou a (a) isentar da regra "mídia sem bin →
> Recovered Clips" os MasterClips com propriedade `MZ.MergeClipUtils.*` — os internos do
> merged, que nem o nativo põe na bin — e (b) acusar o ciclo do §2 do `escrita.md`
> (SubClip → MasterClip de bin de um merged). ⚠️ Armadilha achada no caminho: montar o
> merged antes de fixar a diária corrente usa os ticks da diária ERRADA quando há duas
> com fps diferentes. `confianca: confirmado` por teste; o arquivo gerado por esse
> caminho ainda **não** foi aberto no Premiere.

`DRAMASYNC/src-python/prproj/builder.py` gera hoje o formato **SEM MERGED**, mas o código do merged
está lá, acionado por `merged_mode` (que liga quando `per_ch_mc_uids_per_cam` é passado): os 4
MasterClips, o WAV extra, o layout mono, a cor de etiqueta própria do `" - Merged"`.

⭐ Há inclusive uma **regra consciente já escrita para quando ele voltar** (builder.py:165): *um
órfão — take sem par de som — nunca vira merged, mesmo com a flag ligada; não há o que fundir.*

### ✅ `isMergedClip` é consultável por API — `confirmado`

O Selector expõe `isMergedClip` / `isNotMergedClip` como predicado de filtro
([`selector-conform.md`](selector-conform.md)). Ou seja, **dá para perguntar** a um `projectItem` se
ele é merged — o que serve para não re-fundir o que já foi fundido, e para a tela se orientar.

---

## 3. ⛔⛔ RESPONDIDO em 2026-09-06: **NÃO existe via de API para fundir**

> `confirmado (estático)` no Premiere Pro **25.6.5** (macOS, `CFBundleVersion 25.6.5.4`) —
> a mesma versão das outras medições deste arquivo. Método e evidência completos em
> `DRAMASYNC/.dev/sonda-premiere/README.md`.

⭐⭐ **O achado que transforma pesquisa em consulta:** o DOM inteiro do ExtendScript vive
num binário só, e as strings saem em **tabelas contíguas por classe**.

```
Contents/Frameworks/ScriptLayerPPro.framework/Versions/A/ScriptLayerPPro     (8,0 MB)
Contents/Frameworks/ScriptLayerPProQE.framework/Versions/A/ScriptLayerPProQE (6,9 MB)

strings -a ScriptLayerPPro > /tmp/dom.txt
grep -n "class$" /tmp/dom.txt      # o ÍNDICE: Application class, Project class, ProjectItem class…
sed -n '3750,3840p' /tmp/dom.txt   # a tabela COMPLETA de ProjectItem
```

| onde se procurou | tem | NÃO tem |
|---|---|---|
| `ProjectItem class` (tabela inteira) | `createSubClip`, **`isMergedClip`**, `isMulticamClip`, `createBin`, `attachProxy`, `setXMPMetadata` | verbo de fundir |
| `Project class` (tabela inteira) | `createNewSequenceFromClips`, `placeAsset`, `consolidateDuplicates`, `importFiles` | idem |
| `Application class` (tabela inteira) | `getCurrentProjectViewSelection`, `setProjectViewSelection`, `enableQE` | idem |
| `ScriptLayerPProQE` (binário inteiro) | — | **nem `merge` nem `subclip`** — `grep -i` volta VAZIO |

⭐ **O que dá força ao negativo é o CONTROLE POSITIVO:** `createSubClip` e `isMergedClip`
estão **presentes nas mesmas tabelas** que se leu. Não é falha do método de busca — é
ausência do verbo, com o método provado no mesmo lugar. ⭐ E *`isMergedClip` sem verbo de
fundir* é o retrato exato da API: dá para **perguntar** se algo é merged, não para fazer um.

### O `Merge Clips` é UI pura

```
Frameworks/Dialogs.framework/…                 ← implementação
Settings/EveScripts/MergeClipsDialog.adam.eve  ← layout do diálogo
$$$/Premiere/Menu/MainMenu/Clip/MergeClips...=Merge Clips...
```

⚠️ **A pista falsa:** existe `$$$/Premiere/HSL/MergeClips/AudioTrackNameTemplate`, e "HSL"
também aparece na camada de script (`HSL.SelectedProjectItemUpdate`) — parecia gancho
scriptável. **Não é:** `HSL/MergeClips` só aparece nos **dicionários de localização**,
nenhum binário o referencia. Namespace de string, não porta.

⭐ E o diálogo é **modal com opções** (ponto de sincronismo, in/out, timecode, marcador,
"Remove Audio From AV Clip"): mesmo automação de UI teria de dirigir um modal com estado.

### ⚠️ O `executeConsoleCommand` do QE é console de DEBUG — `inferido forte`

`QEApplication` tem `executeConsoleCommand`/`outputToConsole`, e o binário carrega a string
**`Command … unknown!. Try 'con.help'.`**. Namespace `con.` próprio, não os comandos de
menu do Premiere.

### ⛔ O que isso deixa de pé

A resposta **elimina a arquitetura 1** (painel CEP faz tudo, como o do Avid) e **elimina a
3** (automação de UI). Sobra a **via de arquivo** — e com ela a pergunta 2 da tabela abaixo
vira a que decide, junto com a armadilha do `importFiles` que RE-IMPORTA a mídia.

---

## 3c. ✅✅ A VIA DE ARQUIVO FUNCIONA — validado na GUI em 2026-09-06

Gerado um `.prproj` pelo `builder.py` do Órbita com merged clips ligados
(`DRAMASYNC/.dev/sonda-premiere/gerar_merged.py`), aberto no Premiere **25.6.5** pelo
autor. **Todas as perguntas de arquitetura foram respondidas, e todas com sim:**

| pergunta | resposta medida |
|---|---|
| o arquivo abre? | ✅ *"abriu certinho"* — sem crash |
| `isMergedClip` num merged vindo de arquivo? | ✅ **`true`** |
| abre no Source com V da câmera e A do som? | ✅ *"vídeo e áudio corretos"* |
| aparece pasta "Recovered Clips"? | ✅ **não** — o falso positivo do validador não se materializa |
| `createSubClip` sobre um merged leva as duas metades? | ✅ **sim** |
| e o resultado do `createSubClip`? | ⭐ **`isMergedClip = true`, `isSequence = true`, `getMediaPath()` VAZIO** |

⭐⭐ **A consequência é a arquitetura inteira do porte:** um merged clip descrito em
`.prproj` **não é uma imitação** — o Premiere o trata como merged de verdade, e
`createSubClip` sobre ele produz outro merged. A cadeia `fundir → recortar` do §1 se
fecha **sem nenhuma API de fundir**.

⚠️ **E note o que o subclipe de um merged É:** `isSequence=true` com `mediaPath` vazio.
Ele não é uma janela sobre um arquivo (como o subclipe de câmera crua, §1) — é um
recorte de uma **sequência**. Coerente com o merged clip ser uma `Sequence` por dentro.

### ⛔ O defeito que sobrou: o mapeamento de CANAIS, com áudio multicanal

> Autor: *"O único problema que observei foram os canais de áudio não virem corretos."*

Numa timeline, com o WAV cru e o merged lado a lado (som de **5 canais**):

```
WAV cru:  [A1] [A2] [A3] [A4] [A5]      ← certo
merged:   [A1] [A3] [A5] [A7] [A9]      ← PASSO 2
subclipe: [A1] [A3] [A5] [A7] [A9]      ← herda o defeito do merged
```

⭐ O padrão é **stride 2**: o merged expõe ~10 canais e usa só os ímpares — como se cada
canal mono ocupasse um par estéreo.

⛔ **E o XML gerado está, aparentemente, CERTO** — o que torna este um caso do §7 (*"o
problema está no que você NÃO está imprimindo"*). Conferido no arquivo:

| campo | valor gerado | esperado pelo §6 |
|---|---|---|
| `NumAdaptiveChannels` (AudioTrackGroup) | `1` | `1` ✅ |
| `ChannelType` das 5 tracks | `0` (mono) | mono ✅ |
| `ChannelType` do MasterTrack | `0` (mono) | mono ✅ |
| `ClipChannelGroup` do MasterClip de bin | `(0,0) (0,1) (0,2) (0,3) (0,4)` | variante SEQUÊNCIA ✅ |

⚠️ **Hipótese, NÃO medida:** a maquinaria de merged do builder foi escrita e conferida
contra material de **2 canais** — é da mesma medição que veio o "4 MasterClips" corrigido
hoje no [estruturas.md §6](../../protocolos/prproj/estruturas.md). *"A sequência merged é
mono"* pode ser uma regra que só descreve o caso de 2 canais, e cinco tracks mono não
serem a forma nativa de um merged de 5 canais.

⭐⭐ **RESOLVIDO E VALIDADO NA GUI em 2026-09-06** — o autor conferiu no Premiere: *"deu
certo"*. Os canais do merged saem iguais aos do WAV cru. **E a resposta JÁ ESTAVA NESTE
BANCO.**

O autor disse: *"dê uma pausa e releia o bancodedadosnles com calma, tenho quase certeza
que esse problema já foi solucionado no mergedclipe."* Estava certo. É o
[§7 do escrita.md](../../protocolos/prproj/escrita.md) — *"WAV MULTIPISTA: quando a FONTE
vira o canal, TODO índice dentro dela ZERA"* —, `confirmado` desde **2026-07-12**.

⛔ **A causa raiz:** o Órbita tinha **DUAS implementações** de "como se descrevem os canais
de um WAV". O caminho da mídia crua (`_make_wav_media`) respeitava o §7.1 havia meses; o
caminho do merged (`_make_extra_wav_ams`) era uma cópia que **nunca recebeu a correção** —
criava **UM** `Media` com o layout dos N canais, **sem `StreamNumber`**, e com
`FileKey`/`ContentAndMetadataState` **novos a cada chamada**.

É literalmente a caixa *"o que NÃO funciona"* do §7.1, e o merged nativo confirma a regra:

| | `StreamNumber` | `AudioStream` | `SecondaryContent.ChannelIndex` | `FileKey` |
|---|---|---|---|---|
| **nativo** | ausente, 1, 2, 3, 4 | MONO | **0** em todos | **um só**, compartilhado |
| **nós, antes** | nenhum | layout de 5 canais | 0..4 | **cinco**, um por canal |

⭐ **O conserto não foi remendar: foi apagar a segunda implementação.** `_make_wav_media`
não é cacheado — chamá-lo de novo já devolve um jogo independente, que era tudo o que o
merged queria.

⚠️ **E as três diferenças que o A/B tinha achado antes eram REAIS, só não eram a raiz:**
o MasterClip de bin na variante per-source, a diagonal com `UINT64_MAX`, e os N clips.
Todas confirmadas contra o nativo e todas mantidas — mas sozinhas não consertavam o
sintoma, porque a camada de **mídia** continuava sem saber qual canal era qual.

⭐⭐ **A lição de método, e ela é dura:** eu tinha lido *fragmentos* do §7 (a tabela das
duas formas do `ClipChannelSerializer`, a "Lição de método" do fim) e **nunca a seção
inteira**. Fui atrás do A/B — que era o passo certo — e ele me deu três diferenças
verdadeiras que me mantiveram ocupado na camada errada. **Ler o banco inteiro antes de
medir teria custado dez minutos e economizado uma rodada.**

---

## 3a. ⭐ A tabela de `ProjectItem` no WINDOWS — 25.2.3 (2026-09-16)

`confirmado (estático)`. `C:\Program Files\Adobe\Adobe Premiere Pro 2025\ScriptLayerPPro.dll`
(produto **25.2.3**, não o 25.6.5 do Mac). Sem `strings` no Windows: um `re.finditer` sobre
os bytes (`[\x20-\x7e]{4,}`) basta; `grep -n "class$"` dá o índice igual ao do Mac.

Membros que o porte vai usar, e que este arquivo ainda não listava:

| membro | serve para |
|---|---|
| **`getProjectColumnsMetadata`** | ler as COLUNAS da bin de um item — a aba Renomear (o equivalente das colunas do MC) |
| `getProjectMetadata` / `setProjectMetadata`, `getXMPMetadata` / `setXMPMetadata` | as duas camadas de metadado (projeto e arquivo) |
| **`findItemsMatchingMediaPath`** | achar o item da bin que JÁ aponta para um arquivo — candidato contra a re-importação |
| `setInPoint` / `setOutPoint` / `getInPoint` / `getOutPoint` / `clearInPoint` | aparar um item da bin sem `createSubClip` |
| `renameBin` | renomear BIN |
| `setColorLabel` / `getColorLabel`, `nodeId`, `treePath` | etiqueta; identidade estável; caminho na árvore |

⚠️ **`name` NÃO aparece na tabela** (renomear CLIPE). A documentação da Adobe dá
`projectItem.name` como gravável — a sonda (§6 dela) mede se é, e se o `nodeId` sobrevive.
⚠️ E o nada-de-fundir se repete no 25.2.3: `merge` só aparece como símbolo C++ interno
(`MZ::MergeClipUtils::GetMergedClipMasterClipAsSequence`, …), nunca como membro de script.

⭐ **Duas pistas na tabela de `Project` para a re-importação (não medidas):**
`importSequences` (importa sequências ESCOLHIDAS de outro `.prproj` — e o merged é uma
`Sequence` por dentro) e `consolidateDuplicates` (funde itens duplicados depois de importar).

### ✅ Medido em runtime — Premiere **23.2** (Windows), 2026-09-16, sonda §6

- **`name` É GRAVÁVEL** num clipe da bin: `item.name = x` → releitura, seleção e a coluna
  `Name` mostram o novo; devolver o antigo funciona. ⭐ **`nodeId` NÃO muda** com o rename
  (`000f4241` antes e depois) — serve de chave para o desfazer.
- **`getProjectColumnsMetadata()`** devolve TEXTO JSON: lista de
  `{ColumnID, ColumnName, ColumnPath, ColumnValue}`. Colunas úteis num WAV do ZOOM F8:
  `Column.PropertyText.Scene` (`"PRODUCAO-A - 05-04 C4 P1"`), `Column.PropertyText.Shot`
  (vazia), `Column.Intrinsic.LogNote` (`"Good Take"`), `Column.PropertyBool.Good`,
  `Column.Intrinsic.MediaStart` (em TICKS aqui; no `getProjectMetadata` vem como TC).
- ⚠️ **O TAKE não está em coluna nenhuma.** Está no XMP do ARQUIVO (`getXMPMetadata`):
  `xmpDM:shotNumber = 001` (é o TAKE do gravador, apesar do nome), `xmpDM:scene`, e o
  `bext:description` cru com `TAKE=001`, `SCENE=PRODUCAO-A - 05-04`, `NOTE=…`.
- ⚠️ A `Scene` do Premiere NÃO é a `SCENE=` do BWF: o Premiere montou
  `"PRODUCAO-A - 05-04 C4 P1"` (projeto + cena + plano). O mesmo vício que o Avid tem —
  o campo cena traz o nome do projeto.
- ⭐ **O `nodeId` É PERSISTENTE:** é o `<ID>` do `Node` do item no `.prproj`, em hexadecimal
  (`000f4241` = `<ID>1000001</ID>`, conferido no arquivo salvo). Sobrevive a reabrir o
  projeto; um item IMPORTADO de outro projeto ganha id novo (o mesmo WAV apareceu como
  1000001 e 1000149). Chave estável = projeto + nodeId. `confirmado` (2026-09-17).
- ⛔ Importar um `.prproj` de versão 43 no 23.2 falha — ver `protocolos/prproj/escrita.md` §11b.

### ✅ Importar `.prproj` num projeto aberto: o Premiere DEDUPLICA — observado no 23.2 (2026-09-17)

Achado **do autor**, por dois experimentos em `ORBITA MERGE TESTE` (23.2, Windows):

1. com `PRODE_COMPLETO_2023` já importado, importar `PRODE_SO_MERGED_2023` **não trouxe
   nada** — tudo "já estava lá"; apagando a pasta do completo e importando de novo, os
   merged apareceram;
2. abrindo o só-merged sozinho, acrescentando um *Bars and Tone* e salvando: a importação
   trouxe **só o Bars and Tone**.

⭐ **A deduplicação é por CONTEÚDO, não por identidade:** os dois arquivos foram gerados
separadamente e têm **0 ObjectUID em comum** (de 187). O critério exato (caminho de mídia?
nome? componentes do merged?) é **desconhecido**.

⚠️⚠️ **Risco que decorre disso:** se o critério for nome/componentes, um merged
REGERADO com sync corrigido pode ser tomado por "já existente" e **descartado calado** —
a correção não chegaria à bin. Medir antes de confiar num fluxo de "regerar e reimportar".

⚠️ **E a ressalva do autor, que vale como regra:** *"premiere duplicar mídia é um
comportamento nunca solucionado… podemos seguir mas sem carimbar uma certeza que ele
nunca duplicará nada em outras condições"*. Observado em UMA versão (23.2), com mídia
já importada pelo mesmo caminho. Não promover a `confirmado` geral. A técnica conhecida
quando o XML duplicava — abrir o projeto, puxar e importar dele para o outro — é o
plano B.

⭐ Consequência para o `importFiles`: o retorno `true` com nada novo pode ser
**deduplicação legítima** (ou recusa de versão, §11b do `escrita.md`) — não é
necessariamente falha. ⚠️ Uma hipótese anterior desta sessão, "os itens só chegam depois
do diálogo Import Project", foi DESCARTADA: os dois zeros tinham essas duas causas.

### 🆕 §3c. No 25.6.5 o import também DEDUPLICA — e o merged NÃO herda o proxy (2026-11-07, macOS)

`confirmado`, Premiere 25.6.5, projeto de teste com a PRODE `MIDIA MULTCAM/CAM B` (5 PANA, 4 canais) e o
`SOM DIRETO` (ZOOM) importados numa bin, as 5 câmeras com proxy ProRes Proxy anexado; o `.prproj`
de merged gerado pelo Órbita (`.dev/sonda-premiere/gerar_merged.py --so-merged`, 5 merged, 1 tomada)
importado por `app.project.importFiles([prproj], true, bin, false)`:

- 2,1 s; entraram **7 itens**: 2 bins e os **5 merged** (`isMergedClip()` = `true`, tipo 1). **Nenhum
  item novo com mídia** e nenhuma mídia em mais de um item — o mesmo comportamento do 23.2 (acima).
  O Premiere não caiu. ⚠️ Segue valendo a ressalva do autor (não carimbar "nunca duplica").
- ⛔⛔ **Isto é o `importFiles` do `.prproj` INTEIRO.** O `importSequences` (só a sequência + o que ela usa) do MESMO
  25.6.5 **repete** o merged a cada reimportação (medido 2026-11-15: 36 → 72 → 108) — ver "Por que o `importSequences`
  DUPLICA o merged" e a alavanca, abaixo.
- A sequência criada de um merged tem V1 com o merged e A1–A2 (o som direto).
- ⛔⛔ **O merged mostra o ORIGINAL com o proxy ligado.** Com um proxy em NEGATIVO anexado à câmera
  da bin: o clipe da bin vira negativo com o botão, o merged dele não muda. Causa `inferido forte`:
  o merged aponta o **camMC** — a cópia independente da mídia (`protocolos/prproj/escrita.md` §2) —,
  e o proxy anexado mora no `Media` do clipe da bin (`MediaSource › Content › ProxyMedia`,
  `relink-e-geometria.md`). ⇒ Quem escreve o merged por arquivo tem de escrever o proxy TAMBÉM no
  camMC.
- ✅ **O merged feito pelo MENU herda o proxy** (piloto, mesmo dia: bin com a PANA2774 de proxy em negativo +
  o WAV, `Clip ▸ Merge Clips…`, sincronismo **Audio track channel 1** — o TC da câmera e do gravador não batem).
  Com o botão de proxy ligado, o merged nativo vira negativo; o do Órbita, não. ⚠️ O `Merge Clips` só habilita
  com o FOCO na janela de projeto (seleção feita pela API com `app.setProjectViewSelection` e o foco na timeline
  = item cinza); clicar na ABA do painel dá o foco sem mudar a seleção.
- ⭐⭐ **O molde, lido do `.prproj` salvo** (25.6.5, `Project Version` 43): o merged nativo também tem o
  MasterClip PRÓPRIO (`Node.Properties`: `MZ.MergeClipUtils.ComponentMasterClipOriginalName` e
  `…AudioTrackNumberFromOriginalMergedClip`), e as fontes dele carregam o proxy:

  ```xml
  <VideoMediaSource …><MediaSource Version="4">
      <Content Version="10"><ProxyMedia ObjectURef="‹Media do proxy›"/></Content>
      <Media ObjectURef="‹Media do original›"/></MediaSource>…</VideoMediaSource>
  <AudioMediaSource …><MediaSource Version="4">
      <Content Version="10"><AudioProxies Version="1">
          <AudioProxyItem Index="0" ObjectRef="‹AudioProxy›"/></AudioProxies></Content>
      <Media ObjectURef="‹Media do original›"/></MediaSource>…</AudioMediaSource>
  <AudioProxy …><ProxyMedia ObjectURef="‹Media do proxy›"/><ProxyStreamIndex>0</ProxyStreamIndex>
      <OriginalSecondaryIndex>0</OriginalSecondaryIndex></AudioProxy>
  ```
  e o `Media` do proxy é um `Media` comum com `<IsProxy>true</IsProxy>` (o arquivo tem 5 `Media` para o MESMO
  proxy: um por cadeia que o usa). No merged do Órbita o `VideoMediaSource` do camMC vem **sem `Content`**.
  ⇒ Para o merged por arquivo herdar o proxy, o builder escreve esse `Content` nas fontes do camMC (vídeo e
  um `AudioProxy` por canal). ✅ **Escrito e medido no mesmo dia** (Órbita `ea75984`, `_make_camera_media` +
  `CameraAngle.proxy_path`): 11 merged da PRODE com proxy importados no 25.6.5 (só os merged entraram), e o da
  PANA2774 com proxy em NEGATIVO vira negativo com o botão ligado — `confirmado`.

### 🆕 §3d. O import de `.prproj` JUNTA as bins pelo NOME e não cria a bin do arquivo (2026-11-06, macOS, 25.6.5)

`confirmado` (uma medida), Órbita `POST /api/v1/merge` → painel → `app.project.importFiles([prproj], true, rootItem, false)` no projeto `ANTIGAS 2025`, que já tinha uma bin `CENAS` na raiz. O arquivo (`PRODE D06 MERGED.prproj`) tinha `CENAS › NAO RESOLVIDO › 11 merged`. Entraram **12 itens**: a `NAO RESOLVIDO` DENTRO da `CENAS` que já existia, com os 11 merged. ⇒ (1) bin homônima no mesmo nível vira a MESMA bin (não nasce `CENAS 2`); (2) **não nasce bin com o nome do arquivo** — a raiz do `.prproj` vai direto para o `targetBin`. Cuidado: se o editor tiver uma bin `CENAS` dele, os merged entram nela. 8 s do pedido ao `feito`, 11 com proxy.

## 3b. ⛔ O que ainda FALTA medir

| # | pergunta | por que ela decide tudo |
|---|---|---|
| ~~1~~ | ~~Existe via de API para CRIAR merged clip?~~ | ✅ **RESPONDIDO no §3: NÃO.** |
| 2 | se não existir: o item importado do `.prproj` **se comporta** como merged clip na bin? | decide se a via de arquivo é aceitável ou só parecida |
| 3 | `createSubClip` sobre um item merged **recorta as duas metades juntas**? | é a junta entre os dois passos, e ninguém mediu |
| 4 | onde pendurar a identidade da tomada (cena/take)? | no Avid foi `Scene`/`Take` do `_USER`; aqui é provavelmente **XMP privado** — a receita está em [`api-extendscript.md`](api-extendscript.md) |

⚠️ **A pergunta 1 tem três respostas possíveis, com arquiteturas diferentes:**

- **tem API** → o painel CEP faz tudo, como o painel do Avid faz hoje;
- **não tem, mas o `.prproj` serve** → o plugin vira gerador de arquivo + import. ⚠️ E aí vale o
  aviso do §E do mapa de operações: **`importFiles` RE-IMPORTA a mídia** e cria itens duplicados na
  bin; quem manda no resultado é o projeto, não o retorno da chamada;
- **não tem nada** → sobra automação de UI, que é frágil e não é o padrão deste banco.

⭐ **Onde procurar primeiro, e é barato:** os produtos já dissecados nesta pasta. O `grep` que
respondeu três perguntas deste arquivo levou dois minutos —
`grep -rn "createSubClip\|merge" plugins/premiere-cep/`. **Sempre antes de supor.**

---

## 4. ⭐ O que NÃO muda no porte, e é a maior parte do trabalho

O plugin do Media Composer tem três abas — Sincronizar, Subclipar, Renomear. **A lógica das duas
novas é NLE-agnóstica**; o que muda é a costura:

| peça | onde vive no Órbita | muda no Premiere? |
|---|---|---|
| gramática de padrão de nome (`%campo`, `%{campo}`) | `src-python/nomes/` | **não** — só stdlib, não sabe o que é NLE |
| claquete, identidade de tomada | `src-python/media/` | **não** |
| semáforo do preview (criar × renomear) | `avid/nomear.py::prever` | **não** — a regra é a mesma |
| a UI: seleção estilo Explorer, ordenação, tag fechada | `plugins/avid-panel/static/painel.html` | **o desenho se reaproveita**; o transporte, não |
| ler a bin / escrever o subclipe | `src-python/avid/` | **sim, inteiro** |

⚠️⚠️ **O transporte é a diferença estrutural.** O painel do Avid é uma página **servida pelo app**,
que fala HTTP com ele (e o Python fala gRPC com o MC). O CEP do Premiere roda **ExtendScript dentro
do host**, em ES3 — sem `let`, sem arrow, e com o `JSON` global incerto. O Órbita já tem um painel
CEP funcionando; o porte costura a lógica nova nele, não recria o transporte.

---

## 5. Onde isto será implementado

| | |
|---|---|
| o painel CEP que já existe | `DRAMASYNC/plugins/premiere-cep/` |
| o adapter de escrita `.prproj` (**com o merged desligado**) | `DRAMASYNC/src-python/prproj/builder.py` |
| a lógica a reaproveitar | `DRAMASYNC/src-python/{nomes,media}/` |
| o espelho a portar | `DRAMASYNC/src-python/avid/{subclipes,nomear,takes}.py` |

## Ver também

- [`../../transversal/operacoes-de-nle.md`](../../transversal/operacoes-de-nle.md) §E.2 — a operação
  no mapa por mecânica, com as três colunas
- [`../../protocolos/prproj/estruturas.md`](../../protocolos/prproj/estruturas.md) §6 — a forma do
  merged clip no arquivo
- [`../../protocolos/prproj/escrita.md`](../../protocolos/prproj/escrita.md) §2 — os 4 MasterClips e
  o crash
- [`api-extendscript.md`](api-extendscript.md) — a superfície de API medida, e o XMP privado
- [`../avid-panel-sdk/`](../avid-panel-sdk/) — o lado que está sendo portado

## 🆕⭐ Uma via que não é API: o menu NATIVO — MERGED CLIP CRIADO (2026-11-04, Premiere 26.0, Windows) — `confirmado`

A barra de menus do Premiere no Windows é um `HMENU` de verdade, e cada item tem ID fixo: **Clip ▸ Merge Clips… =
11591**, Synchronize… = 11570, Create Multi-Camera Source Sequence… = 11592. `WM_COMMAND` com o ID executa o item com
o Premiere atrás e sem foco.

**Provado, com o Premiere COBERTO pelo terminal e sem um clique físico:**
1. vídeo e WAV importados por File ▸ Import (11220) + o caminho por `WM_SETTEXT` no diálogo de arquivo;
2. selecionados no painel Project por mensagem (o 2º com Ctrl: `AttachThreadInput` + `SetKeyboardState` + `MK_CONTROL`);
3. `WM_COMMAND 11591` → o diálogo **"Merge Clips"** (`#32770`, abre ATRÁS, sem tomar a frente);
4. o campo **Name é um `Edit` nativo** (id 1) → `WM_SETTEXT`; Synchronize Point e OK são desenhados pelo app → clique
   por mensagem na filha mais funda sob o ponto (posição lida na foto do diálogo, `PrintWindow`);
5. Timecode marcado, OK → **"T01 MERGED POR MENSAGEM"** no projeto, 25 fps.
✅ **Sincronia CONFERIDA** (mídia sintética D06: vídeo TC 10:00:05:00, WAV BWF `time_reference` 1728144000 = 10:00:03:00):
no `.prproj` a Sequence merged (`IsMergedClip=true`) tem o WAV em 0–24 s e o vídeo + os 2 canais da câmera em
`Start=508032000000` (**2,000 s exatos**), `MZ.ZeroPoint=9145338048000000` (= 10:00:03:00, o TC do WAV). ⚠️ O merged
NATIVO do 26.0 põe o WAV em 0 e a CÂMERA deslocada (positivo) — não o WAV negativo da §6 de `estruturas.md`. Pelo
CONTEÚDO: a correlação do som da câmera com o WAV dá 1,994 s (r = 0,62; 6 ms = a resolução de 8 kHz da medida). ⚠️ As posições do rádio e
do OK são do diálogo, não da tela — mas mudam com escala e idioma: ler na foto antes. ⬜ Mac: o menu é do sistema
(System Events pelo NOME, já usado pelo piloto) — o mesmo caminho, outro mecanismo.
Matriz, seção F, linha "entrada SEM o mouse do sistema"; sonda `piloto/sondas/entrada_por_mensagem.py`.

### 🆕 No MAC: Clipe ▸ "Mesclar clipes…" pelo NOME — MERGED CRIADO (2026-11-14, Premiere 26.0.2 pt-BR) — `confirmado` (1 rodada)
`importFiles` dos 17 arquivos numa chamada só (ficam SELECIONADOS: `getCurrentProjectViewSelection` = 17) →
`tell application "System Events" to tell (first process whose unix id is <pid>) to click menu item "Mesclar clipes…"
of menu 1 of menu bar item "Clipe" of menu bar 1` (o item com reticências `…`, U+2026; habilitado só com a seleção) →
diálogo "Mesclar clipes" (`AXDialog` modal, 414×452) com **Timecode já marcado** e o nome `<câmera> – Mesclado` → um
clique no OK (o único gesto físico) → merged com 16 canais. Ciclo Assist: o projeto-modelo da calibragem
(`cicloassist/carta/moldes/`). ⛔ Vídeo OP-Atom gerado pelo ffmpeg (`-f mxf_opatom`, DNxHR LB 320×180 e DNxHD 1080p
36) é RECUSADO pelo Premiere ("Formato não suportado ou arquivo danificado"); o SOM OP-Atom do ffmpeg entra.

### 🆕 A COR de um merged mora em TRÊS lugares, e o painel lê um só (27.0 Mac, 2026-11-15) — `confirmado`
Lido num projeto em que o autor pintou 36 merged de Cerulean: (1) o ITEM da bin, `ClipProjectItem/ProjectItem/Node/
Properties/Column.PropertyText.Label` = `BE.Prefs.LabelColors.4` — **é o que o painel do projeto mostra**; (2) os clipes do
merged (`VideoClip`/`AudioClip`/`TranscriptClip` → `Clip/Node/Properties/asl.clip.label.name`); (3) os clipes de CADA
componente (a câmera e os canais), cujo `asl.clip.label.color` (o RGB) fica o antigo. O índice é SEQUENCIAL a partir de 0
na ordem da lista do Premiere (Violet 0, Iris 1, Caribbean 2, Lavender 3, **Cerulean 4**…). ⛔ Pintar só o (2) não muda o
painel (ficou o 0, violeta, que veio do molde). Ciclo Assist: `merged_prproj._pintar`/`_pintar_item`, `COR_DO_MERGED`.
- O "Media Type" da coluna (Movie = vídeo com som, Video = sem som, Audio, Still Image, Merged Clip, Sequence) NÃO está no
  `.prproj`: sai do `getProjectMetadata()` do item, `Column.Intrinsic.MediaType` (`host.jsx` `cicloTipoDeMidia`).

### 🆕⛔⛔ O merged escrito a partir de um MOLDE herda a posição das trilhas e o QUADRO dele (2026-11-15, 27.0 Mac) — `confirmado`
O merged é uma sequência interna (`BE.Sequence.IsMergedClip`) com um item por trilha. Escrito clonando um molde, ele
herda do molde: (1) a POSIÇÃO de cada item na sequência interna (`ClipTrackItem/TrackItem/Start` e `End`) e (2) o quadro
(`VideoTrackGroup/FrameRect` + `MZ.Sequence.PreviewFrameSizeWidth/Height`). O merged sintético da calibragem do Ciclo
Assist (feito por "Mesclar clipes" sincronizando por TC: câmera MOV do ffmpeg + 16 OP-Atom de som) tem o vídeo em
**3,587 s** (86 quadros) e o som até 0,959 s, quadro **320×180**. Os merged escritos sobre ele saíram com: sobra só de
som (preto) no começo; **"3:14" de dessincronia em todo clipe** da timeline (o Premiere compara a posição do vídeo e do
som do mesmo merged; o som estava certo — falso positivo); e o Source a **600 %** (1920 num quadro de 320 = 6×; na
timeline não aparece porque lá o quadro é o da sequência do editor). Conserto: toda trilha de 0 a `dur`, o quadro do
`VideoStream/FrameRect` da câmera (`cicloassist/carta/merged_prproj._alinhar_e_enquadrar`) — conferido na tela: Source
inteiro, imagem no 1º quadro, nenhuma etiqueta de dessincronia. ⭐ Lição: conferir o merged POR DENTRO (Source e as
etiquetas da timeline), não só contar itens.

### 🆕⭐⭐ Por que o `importSequences` DUPLICA o merged — medido com o REA (Frida) no 26.0.2 Mac, 2026-11-14 — `confirmado` (8 rodadas)
Reimportar a mesma timeline levava o projeto de 36 a 72 merged (e +36 a cada vez), mesmo com o arquivo de origem
apontando os MESMOS objetos (mesmos ObjectUID) que o editor já tem; a mídia e os subclipes NÃO duplicam.
- O caminho: `ProjectObjectExt::ImportSequences` → `FE::Document::ImportSequences` → `HandlerProject::ProjectHandler::
  OnImportSequences` → `MZ::ProjectActions::ImportDynamicLinkSequencesIntoProject` (é o DYNAMIC LINK: carrega o `.prproj`
  de origem inteiro — `LoadProjectOperation` — e pega a sequência + as dependências como itens) → `AddImportedFilesToProject`
  → `AddItemsWithProperties` (a máquina de COLAR: `ClipboardItemUtils::ReattachPastedSequence/Clip`).
- A correspondência com o projeto de destino: `MZ::HashProjectMasterClipsByName` (mapa dos masterclips do destino) +
  `MZ::Project::FindMatchingMasterClip` = mesma IMPRESSÃO (`MZ::GetMasterClipHash`: tipo de conteúdo, mídia
  (`MixInMediaProperties`), sequência, cadeia de componentes, mapa de canais, TRANSCRIÇÃO) + `ModificationStatesMatch` +
  `InOutPointsMatch` + não marcado para apagar. Medido: achou 313, não achou 36 — os 36 merged.
- ⛔ A diferença (comparando a mistura `UpdateHashState` dos dois lados, 554 passos iguais): o merged do projeto ABERTO
  mistura `TranscriptClip::ComputeTranscriptHash` + uma impressão de transcrição VAZIA (`d9e65965…`, a mesma em todos) e
  tem, na lista dos TIPOS de clipe (constantes: vídeo `80b8e3d5…`, áudio `228cda18…`), um terceiro, `d8143ffe…`
  (transcrição). O merged que CHEGA (carregado pelo Dynamic Link) não tem. Esse marcador NÃO está no `.prproj` salvo
  (nenhum elemento `*Transcript*`), não vem pelo `.prin`, e aparece mesmo com `RunBackgroundTranscription = false` e logo
  depois de reabrir o projeto. ⇒ no 26.0.2 o `importSequences` NUNCA reconhece um merged já existente.
- ⭐⭐ **A ALAVANCA, medida (2026-11-15, 26.0.2 Mac) — `confirmado` (4 rodadas):** escrever no merged um `TranscriptClip`
  VAZIO no `.prproj` de origem faz o `importSequences` reconhecer o merged que o projeto já tem. A forma é a que o próprio
  Premiere grava para um clipe SEM transcrição (achada num `.prproj` real do PRODUCAO-I, `teste-23-sem-transcricao`):
  `MasterClip/Clips` ganha mais um `<Clip Index=N>` → `TranscriptClip` (ClassID `9e0179bb-153c-4884-b34b-eb7082f34384`,
  Version 2) → `DataClip`/`Clip` v18 (`Source` → `DataMediaSource` (ClassID `ff36343e-4ece-4d37-ab61-e99b758f9d30`) →
  `MediaSource`/`Media ObjectURef` + `OriginalDuration 0`; `ClipID` novo; `InUse false`), **sem** `TranscriptTextSegments`
  (com transcrição, ele aponta um `ExternallyProvidedTranscriptDocument` em FlatBuffers — `transversal/transcricao-por-palavra.md`).
  No merged a Media usada foi a do 1º canal de som (componente); a impressão da transcrição vazia não dependeu dela.
  | rodada (PRODA_CORTE.00.2, 36 merged) | merged antes → depois | itens novos |
  |---|---|---|
  | controle, reimportar sem a alavanca (v04) | 360 → 396 | 37 |
  | a mesma saída + `TranscriptClip` vazio (v04) | 396 → 396 | 1 (a sequência) |
  | 1ª importação num projeto só com mídia (v05) | 0 → 36 | 37 |
  | reimportação nele | 36 → 36 | 1 |
  848/848 itens da timeline iguais ao controle (arquivo e nível do volume). ⭐ Ao SALVAR, o Premiere GUARDA o
  `TranscriptClip` dos merged que vieram com ele (não o cria nos que vieram sem) — a cópia seguinte já o traz. ⚠️ No 25.6.5 (onde o import já
  repetia também, §3c é outro caminho) a alavanca foi medida no MESMO dia — ver abaixo; o Ciclo Assist a aplica no 23+ (medida no 23.6, 25.6.5 e 26.0.2).
  Ciclo Assist: `cicloassist/carta/merged_prproj.transcricao_vazia`, spike `spikes/merged_com_transcricao_vazia.py`.
- ⭐⭐ **No 25.6.5 (Mac, 2026-11-15, preferências de fábrica) — `confirmado` (4 rodadas):** o `importSequences` repete o
  merged igual ao 26 (sem a alavanca: 36 → 72 → 108, +37 itens por vez, inclusive os merged que o PRÓPRIO 25 tinha criado
  na rodada anterior); com a alavanca: 108 → 108 duas vezes, só a sequência entra. ⚠️ (corrigido no mesmo dia) Nem o 25 nem o 26 CRIAM o
  `TranscriptClip` no merged ao salvar (os 72 merged que vieram SEM ele continuaram sem; o v03 do 26 também, 0 de 36);
  os dois GUARDAM o que veio no arquivo (36 de 36 no 25 e no 26). Por isso a cópia seguinte já o traz e a alavanca só
  escreve nos merged antigos, de antes dela. ⬜ Abaixo do 25 (o 23.2 já grava `TranscriptClip` em projeto) e no Windows: `pendente`.
- ⚠️ Armadilha do teste: o Premiere 2026 **salvou todos os projetos abertos ao fechar** (o projeto "só com mídia" ganhou
  a importação da véspera). Projeto de teste: conferir o arquivo (merged/sequências) imediatamente antes de rebaixar/copiar.
- ⭐⭐ **De PONTA A PONTA no 25.6.5, projeto NOVO e vazio (2026-11-15) — `confirmado`:** o "Importar para o Premiere"
  sem nada forçado (o modelo da calibragem escolhido pela versão: `modelo 25.prproj`; a alavanca ligada pela versão):
  1ª importação 259 mídias + calibragem + 36 merged, 848 clipes, 157 transições, 8 subclipes, 43 s; reimportação
  36 → 36, só a sequência, 16 s.
- ⭐⭐ **No 23.6 (Mac, 2026-11-15) — `confirmado` (4 rodadas):** o mesmo — sem a alavanca 36 → 72 → 108; com ela
  108 → 108 duas vezes. ⇒ a transcrição entra na impressão do merged pelo menos desde o 23.6; a alavanca vale do 23 ao 26.
  ⚠️ O `importSequences` do 23.6 leva 160–270 s neste projeto (25/26: ~20 s). ⚠️ Na 1ª importação num projeto REBAIXADO
  do 26 (`lab/prproj_downgrade.py` → "23.2") entraram 61 clipes de mídia repetidos (mesmos arquivos); não se repetiu nas
  3 seguintes. ⇒ era do projeto REBAIXADO: num projeto NOVO do 23.6 (abaixo) não aconteceu. ⬜ Abaixo do 23 e no
  Windows: `pendente`.
- ⭐⭐ **De PONTA A PONTA no 23.6, projeto NOVO e vazio (2026-11-15) — `confirmado`:** nada forçado (calibragem pela
  cópia do `modelo 23.prproj` com a mídia reescrita, 68 caminhos; alavanca pela versão): 1ª importação 259 mídias + 36
  merged, 848 clipes, 157 transições, 8 subclipes (clipes 259 → 267: só os subclipes, nada repetido), 5 min 17 s;
  reimportação 36 → 36, só a sequência, 2 min 33 s (o `importSequences` do 23 leva ~2,5 min). O 23 também GUARDA o
  `TranscriptClip` ao salvar (a alavanca escreveu 0 na reimportação).
- ⭐⭐ **No 27.0.0 (o 2027 oficial, Mac, 2026-11-15) — `confirmado`:** CONTROLE limpo (projeto novo, merged nascidos
  SEM a alavanca): 36 → 72 na reimportação — o 2027 ainda repete. Com a alavanca (projeto novo): 0 → 36, depois 36 → 36
  duas vezes. A calibragem usa o modelo do 26 (o 27 abre). ⚠️ Armadilha do controle: desligar a alavanca num projeto cujos
  merged JÁ vieram com o `TranscriptClip` não é controle (o Premiere o guardou; a cópia o leva) — deu 36 → 36 e não
  provava nada.
- ⭐ **E pelo BOTÃO da janela (clique físico do piloto), no 25.6.5:** 1º clique num projeto novo = o mesmo resultado
  (~45 s, sem faixa de erro); 2º clique = 36 merged, 2 sequências, 259 mídias no arquivo salvo.
- Endereços (26.0.2 arm64, `nm` com símbolos locais, base 0x100000000): OnImportSequences 0x10cd9bb40,
  FindMatchingMasterClip 0x10770c110, GetMasterClipHash 0x1076fa824, GetMasterClipFromHashMap 0x10770d11c,
  BE::IsMergedClip(IMasterClip) 0x1034aed48, UpdateHashState(HashValueMixerState) 0x1013aaf14. A `CullAndCloneComponent
  MasterClipsForMergedClip` NÃO é chamada na importação.

### Synchronize (Clip ▸ Synchronize…, ID 11570) — `confirmado` por TIMECODE, 2026-11-04
Opera sobre clipes JÁ NA TIMELINE. Montado sem arrasto: *Sequence From Clip* (11605) com o WAV; patch de ÁUDIO da origem
desligado (clique por mensagem na coluna de patch) + agulha na régua + *Overwrite* (11512) do vídeo ⇒ só a imagem na V1;
laço por mensagem selecionando os dois; `WM_COMMAND 11570` → diálogo **"Synchronize Clips"** (`#32770`, desenhado:
Clip Start · Clip End · **Timecode** [campo + Ignore Hours] · Clip Marker · Audio track channel; o diálogo LEMBRA a
última escolha). Timecode + OK (cliques por mensagem): o vídeo FICOU (9,7431 s) e o WAV andou de 0 para 7,7411 s —
**diferença 2,0020 s** (esperado 2,000; os 2 ms são o quadro de uma sequência 29,97: 59,94 → 60 quadros).
- ⚠️ **Undo (57643) desfaz e PERDE a seleção** — o 2º Synchronize abriu com Timecode cinza (`00;00;00;00`) e o canal de
  áudio vazio. Selecionar de novo antes.
- ✅ **Por ÁUDIO (forma de onda), material REAL** — *PRODUCAO-A*, `A001_03170436_C009.mp4` (Blackmagic, 23,976, som
  guia estéreo, TC 04:35:43:23) × `C4 P4-T003.WAV` (5 canais, BWF 13:04:19 — TCs de relógios diferentes, o caso real).
  Gabarito por correlação nossa: a câmera começa **6,2690 s** depois do WAV (r 0,26, 2º pico a 8 %). Premiere
  (Audio track channel 1): o WAV andou de 0 a 16,1828 s, a câmera ficou em 22,4391 s ⇒ **6,2563 s = 150 quadros
  exatos** (o gabarito é 150,3) — certo no quadro. Montagem: *Sequence From Clip* do WAV (5 canais ⇒ A1–A5, uma trilha
  por canal); *Add Tracks…* (11627, o padrão já é "1 de áudio depois da A5"); **o patch A1 da origem arrastado até a A6
  por `SendInput`** (o único gesto físico); *Window ▸ Maximize Frame* (1774) para ver todas as trilhas; *Overwrite*.
  ⚠️ A opção de áudio fica DESABILITADA se um dos clipes não tem som.
- ⛔⛔ **Com a mídia SINTÉTICA da D06 o Premiere FALHA**: "Audio synchronize failure — a match could not be found",
  embora a nossa correlação ache o deslocamento (1,994 s, r 0,62, canais idênticos). O som do laboratório (ruído +
  rajadas) não serve de teste para o sync por áudio do Premiere — use material com FALA. O aviso é outro `#32770` SEM
  título que nasce ATRÁS e só se vê pelo `PrintWindow` dele (não na foto da principal); OK por mensagem.

### Create Multi-Camera Source Sequence (ID 11592) — `confirmado` por ÁUDIO, 2026-11-04
Material real com FALA (PRODE: CAM A Sony + CAM B Panasonic + WAV Zoom, trechos em
`laboratorio-de-midia/referencias/sync-com-fala/prode`, ficha `fichas/sync-com-fala.md`). Import dos TRÊS num só diálogo
(no campo: `"C:\pasta\a.mov" "C:\pasta\b.mov" "C:\pasta\c.wav"` + `IDOK`) — e o Premiere DEIXA OS IMPORTADOS SELECIONADOS, então o
`WM_COMMAND 11592` vem logo depois, sem clique. Diálogo **"Create Multi-Camera Source Sequence"** (`#32770`): o NOME é
`Edit` nativo (o de cima; o outro Edit é "Offset Audio by"); o resto desenhado — In/Out Points · **Timecode** (+ single
multicam, track assignments, ignore hours) · Other Timecode (Linear Timecode) · Clip Marker · **Audio track channel**;
Sequence Preset; Offset Audio by N frames; "Move source clips to Processed Clips bin" (ligado: cria a bin e MOVE as
fontes); Audio Sequence Settings (Camera 1…); Camera Names. Audio + OK por mensagem → janela de progresso "Process
Audio …" (`#32770`) por ~1 s → a sequência.
- Resultado (WAV em 0): CAM A **9,7598 s** (gabarito 9,7705), CAM B **20,8125 s** (gabarito 20,8382) — os dois ângulos
  certos **dentro de 1 quadro** a 23,976. ⚠️ Nos três syncs por áudio de hoje o Premiere pareceu arredondar para BAIXO
  (150,3→150; 234,26→234; 499,62→499) — observação, não regra (os trechos `-c copy` podem ter áudio e vídeo com inícios
  levemente diferentes).

### 🆕 No Mac, e o par do group clip do Avid — `confirmado` (2026-11-12, Premiere 26.0.2 pt-BR, macOS)
Feito para comparar com o `GRUPO-MULTCAM` do MC (ver `protocolos/avb/sincronizacao-e-subclipes.md` §5): as MESMAS três
fontes (`CAM A.mxf`, `CAM B.mxf`, `SOM-DIRETO.wav`, 23,976, 1572 quadros cada, todas TC 01:00:00:00), projeto
`MIDIAS DE TESTES/1 PRODUCOES/PRODUCAO-A/SAIDAS/CARTA ABERTA/GRUPO-MULTCAM PREMIERE v01.prproj`.
- Sem mouse até o OK: `app.newProject` + `importFiles` + `setInPoint(Time com ticks, 4)` pela ponte (quadro N =
  `N × 10594584000` ticks a 23,976) — o Premiere deixa os importados SELECIONADOS (`getCurrentProjectViewSelection`
  confirmou os 3). O menu pelo NOME via System Events: **Clipe ▸ "Criar sequência de origem de várias câmeras…"**
  (pt-BR; o processo é `Adobe Premiere Pro 2026`). O diálogo ("Criar uma sequência de origem de várias câmeras") abriu
  com **Pontos de entrada** já marcado; um clique no OK (1 gesto físico) → `CAM A.mxfVárias câmeras` (o nome padrão é
  "Nome de videoclipe +" + "Várias câmeras") e a bin `Clipes processados` com as 3 fontes. Renomear: `item.name = …`.
- ⛔⛔ **Por PONTO DE ENTRADA o Premiere CORTA A CABEÇA de cada fonte**, e o Avid não. Lido no `.prproj`: todos os
  `ClipTrackItem` com `Start` 0, cada um entrando no próprio In (CAM A 751→1572, CAM B 984→1572, som 0→1572), a
  multicâmera com 1572 quadros (a fonte mais longa depois do In). O group clip do MC com a MESMA sincronia guarda tudo:
  `Filler` 233 / 0 / 984 na frente e 2556 quadros. A RELAÇÃO é idêntica (B − A = 233, B − som = 984), o material antes
  do ponto de sincronia não. ⇒ Ao TRADUZIR um group clip para multicâmera, escrever as fontes INTEIRAS com `Start`
  = o `Filler` do Avid (é a forma que a sincronia por timecode produz: deslocamento positivo, banco §6/merged acima),
  nunca imitar o gesto de In point — perderia as cabeças. ⬜ conferir que o Premiere abre uma multicâmera assim escrita.
- Áudio da multicâmera: 9 trilhas (4 da CAM A, 4 da CAM B, o WAV), "Configurações de sequência: Câmera 1" (o som
  segue a câmera 1). No Avid o som é ÂNGULO (A1 = trilhas 1/5/9 do `Selector`); no Premiere, trilha da sequência de origem.

### 🆕 O caminho de VOLTA (Premiere → Avid) e o que a multicâmera e o merged NATIVOS guardam — `confirmado` (2026-11-12, 26.0.2 Mac, lab G01)
Ciclo Assist `spikes/carta_aberta_para_avid.py` (lê o que a ponte tirou do Premiere e escreve group clip / `.sync` /
subclipe no MC 2025.12 sobre os masters que já estão lá); os três abrem no MC e mostram o quadro certo.
- **Multicâmera por TIMECODE** ("Criar uma única…" marcado): as fontes INTEIRAS, cada uma no instante do TC dela, o som
  direto numa trilha e o som de cada câmera em mais uma trilha (A2…). Pela API: `clip.start − clip.inPoint` = onde o quadro
  0 da fonte cai ⇒ é o `Filler` do group clip. Entre as câmeras, igual ao Avid (CAM 3 +72, CAM 2 +168 da CAM 1).
- ⛔⛔ **O WAV com `time_reference` em SEGUNDOS REAIS cai fora numa multicâmera a 23,976 por TC**: o Premiere lê o BWF
  como tempo de relógio (10:00:02:00 = 36002 s) e a câmera 10:00:05:00 a 23,976 como 864120 quadros = 36041 s — o som
  entrou **863 quadros (36 s) antes**. É o gerador do laboratório (`lab/multicam.py` escreve `time_reference` = rótulo do
  TC × 48000). ✅ **Medido contra o gravador REAL (2026-11-12):** `PRODUCAO-A - 05-04 C4 P1-T002.WAV` tem
  `time_reference` 2023781760 = 42162,120 s e iXML `TIMECODE_RATE 24000/1001`; lido como TEMPO REAL a 23,976 dá
  **11:42:00:00** redondo (o TC que o MC mostra, `avb/escrita.md` "O start do BWF"); lido como rótulo daria 11:42:42:02.
  ⇒ o gravador real escreve tempo real (= quadros do rótulo × 1001/24000 s), e o Premiere e o MC leem assim: **o defeito é
  só do `lab/multicam.py`** (linha do `ref`: soma os segundos do RÓTULO; o `lab/gerar.py` faz certo, quadros ÷ fps real).
  Conserto proposto (sessão do laboratório): `ref = tc_para_quadros(rótulo, base) / fps_da_cena × 48000` e o iXML
  `TIMECODE_RATE`. Regra geral em `transversal/tempo-e-timecode.md` (as duas procedências de "segundos desde a meia-noite").
- **Merged por PONTOS DE ENTRADA**: imagem desde a entrada dela; as trilhas A1…An = o som da CÂMERA, depois as do som
  direto; o TC do merged = o da câmera. ⛔ **Entrada do WAV em 240 quadros → o merged pôs o som em 239** (9,968 s, ticks
  exatos `2532105576000`): um quadro A MENOS, o arredondamento para baixo já visto nos syncs por áudio.
- ⛔ A API não diz de que ARQUIVO vem cada trilha de um merged (todas apontam o próprio merged). ✅ **Do `.prproj` sai
  tudo** (2026-11-12, Ciclo Assist `spikes/carta_aberta_merged_do_prproj.py`, sobre o leitor do Conformar): a `Sequence`
  com `IsMergedClip`, cada trilha `TrackItem › SubClip › Clip › Source › Media.FilePath`, a entrada no arquivo
  (`Clip.InPoint`) e o canal. No merged NATIVO (Premiere 26.0.2, por entrada): V1 = câmera; A1/A2 = o som DA CÂMERA
  (canais 0/1); A3/A4 = o som direto (canais 0/1), entrada 239 q. ⚠️ O CANAL tem duas formas: a do Premiere (UMA fonte
  com N canais; `SecondaryContent.ChannelIndex` escolhe) e a do nosso escritor (UMA fonte POR canal, todas com
  `ChannelIndex 0`); na segunda o canal sai do `SubClip.OrigChGrp`, que bate nas duas formas medidas mas não é o que
  seleciona (`prproj/escrita.md` §7.1) — `inferido`. ⬜ Pede o projeto SALVO.
- ⛔ Subclipe: a janela é `Column.Intrinsic.SubclipStart` − `MediaStart` (TC, no `getProjectMetadata`) e
  `SubclipDuration` — `getInPoint/getOutPoint` devolveram o master inteiro (0–1127), como já registrado acima.
- ✅ **Subclipe no `.prproj` SALVO** — `confirmado` (2026-11-12, Premiere 26.0.2 Mac, 1 subclipe feito por
  `createSubClip`, `G01 PREMIERE DO EDITOR v02`; Ciclo Assist `carta/itens._subclipes`): é um `MasterClip` cujo
  `Clip › Source` (`MediaSource › Content`) tem **`StartBoundary`/`EndBoundary` em ticks desde o 1º quadro do ARQUIVO**
  (não do TC): `2118916800000`/`4237833600000` = 200–400 q a 23,976 (`10594584000` ticks por quadro, o
  `LoggingInfo.MediaFrameRate`). O `LoggingInfo.MediaInPoint/OutPoint` leva o MESMO recorte somado ao TC do arquivo
  (`AlternateStart` do `Media`). Nenhum master comum, merged ou multicâmera dos 4 `.prproj` do G01 tem a marca.
  `BoundariesAreHard` = false aqui (hard boundaries não medido). ⚠️ A SELEÇÃO pela API entrega o subclipe com o
  `getMediaPath()` do master: quem não olhar o `.prproj` o trata como a mídia inteira, calado.
- ⚠️ `ProjectItem.select()` SUBSTITUI a seleção; somar = Cmd+clique no painel (o piloto: `_mouse(..., bandeiras=0x100000)`).
- O diálogo "Mesclar clipes" (pt-BR) LEMBRA a última sincronia escolhida (abriu em Timecode).

## Clipe sem som direto na aba "Criar Merged Clipe" (Ciclo Assist, 2026-11-08)

Decisão do autor: o clipe de câmera que não casou som também é entregue, como o órfão do Avid. Merged precisa de um som para
fundir, então ele sai como **subclipe** (`createSubClip(nome, in, out, 0, 1, 1)` + `moveBin`) na bin dos merged, com a cena presumida pelos
vizinhos (`avid.takes._batizar_orfaos`, `convencao = "posicao"`). `pendente`: ainda não conferido na tela do Premiere.
Fora daqui continua valendo: o caminho do chat (`criar_merged`, `premiere/merged_cenas.py`) só entrega tomadas com som.

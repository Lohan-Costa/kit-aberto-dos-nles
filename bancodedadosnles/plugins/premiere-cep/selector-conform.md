# Selector for Premiere Pro — o vocabulário de seleção, e o filtro que eles NÃO conseguiram entregar

Sétimo caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md).
Fatos consumíveis em [dados/selector.json](dados/selector.json).

**Por que este caso importa:** o Selector é a peça que faltava para desenhar um **assistente de
conform**. Ele não monta nem move nada — ele **acha**. E vem com uma coisa rara nesta série: um
**catálogo de filtros em JSON puro, auto-descritivo, não obfuscado**
(`common/FiltersDB.json`, 24 KB) — 63 predicados com nome, mensagem de falha, tipo de UI,
exclusões mútuas e **custo medido**.

⭐⭐ **E o achado que vale a análise inteira:** o filtro *"Has effects"* — exatamente o
"selecionar todos os clipes que têm efeito" que motivou esta sessão — **está no banco deles e NÃO
foi publicado.** Está em `clipOnHold`, e o que existe no produto é só *"Has effect named X"*. A §3
mostra por que a diferença entre os dois é grande.

## O que foi inspecionado

| | |
|---|---|
| produto | **Selector for Premiere Pro** 1.7.0, `com.selectorForPR.tmmw` (marca EMPRESA-TERCEIRA) |
| host | `PPRO [14.0,30.0]` |
| `jsx/main.jsx` | 232 KB **JSXBIN** → decodificados 1.822 símbolos (só a tabela) |
| `js/main.js` | 652 KB, **javascript-obfuscator** — não desofuscado |
| `common/FiltersDB.json` | ⭐ **24 KB em claro** — o catálogo |
| `common/FixedPresetsDB.json` | ⭐ 1,9 KB em claro — os 9 presets fixos |

### ⭐ É o mesmo construtor do Chop Chop

`file-system-helper` 2.1.37, `string-utils` 1.8.10, `html-helper` 0.1.25,
`notifications-manager` 4.1.6, `date-helper` 1.1.15 — **os mesmos pacotes npm in-house, do mesmo
`author: usuario Terceiro`** que o [Chop Chop](chopchop-arquitetura.md) carrega, em versões mais
novas. Mesma forma de proteção (JSXBIN + javascript-obfuscator), mesmo esqueleto de painel.

⚠️ **Marcas diferentes, oficina a mesma.** Vale registrar porque muda a leitura de "concorrente":
não há dois times resolvendo o mesmo problema de dois jeitos — há um fornecedor de painéis de
Premiere atendendo marcas distintas. As convenções que parecem "do mercado" podem ser **de uma
oficina só**.

---

## 1. ⭐⭐ `FiltersDB.json` — o catálogo, e a lição de desenho embutida nele

Cada filtro é um objeto auto-descritivo:

```json
{
  "displayName": "Has effect named",
  "func": "hasEffectByName",
  "onFailMessage": "Clip has no effect named ${v1}",
  "ui": { "type": "RemovableInputTextWithLabel" },
  "valueRequired": true,
  "helpDescription": "The clip has an effect named as the specified string.",
  "testValue": "Timecode",
  "runOrder": 286
}
```

⭐⭐ **`runOrder` é um CUSTO MEDIDO, e a lista roda em ordem crescente dele.** Não é prioridade
editorial — é preço. Os números falam:

| escopo | mais barato | mais caro | razão |
|---|---|---|---|
| `clip` | `isNotSelected` **150** | `isEnabled` **10966** | **73×** |
| `item` | `isBin` **708** | `isClipSelected` **18254** | **26×** |

⭐ **A ideia reusável:** num filtro composto, rodar primeiro o predicado barato encolhe o conjunto
que o predicado caro vai visitar. `atCTI` custa 206 e `isEnabled` custa 10966 — inverter a ordem
multiplica o trabalho por cinquenta. Isso é **dado**, não código: dá para copiar a ordem sem
copiar nada deles.

⚠️ **E note o que é caro:** `isEnabled` (ler `clip.disabled`) é o predicado mais caro do escopo de
clipe. Ler propriedade de `TrackItem` via ExtendScript **não é barato** — cada acesso atravessa a
ponte. Quem varre uma diária inteira precisa saber disso.

Outros campos que carregam desenho: **`excludes`** (pares mutuamente exclusivos declarados no
dado, ex.: `isInBin` exclui `isNotInBin`), **`onFailMessage`** com interpolação (`${Type}`,
`${v1}`) — a explicação de *por que este clipe não entrou* nasce junto do filtro — e
**`testValue`**, um valor de teste por filtro.

### O catálogo, por escopo

**`common` (27)** — valem para item de projeto **e** clipe de timeline:
`nameStarts` · `nameIs` · `nameEnds` · `nameContains` · `isInBin` / `isNotInBin` ·
`folderPathContains` / `folderPathNotContains` · `isInFolder` / `isNotInFolder` ·
`isShorterThan` / `isLongerThan` (segundos) · `isAdjLayer` / `isNotAdjLayer` ·
`isSelected` / `isNotSelected` · `isOffline` / `isNotOffline` · `isFileExt` ·
`isAudio` · `isVideo` · `isMergedClip` / `isNotMergedClip` ·
`isMulticamClip` / `isNotMulticamClip` · `hasProxy` / `hasNoProxy`

**`item` (11)** — só painel de projeto:
`isClipSelected` / `isClipNotSelected` · `inCurrentSeq` / `notInCurrentSeq` · `isAudioVideo` ·
`isSequence` / `isNotSequence` · `isBin` / `isNotBin` · `isUsed` / `isNotUsed`

**`clip` (25)** — só timeline, e é a lista que interessa ao conform:
`isEnabled` / `isNotEnabled` · `atCTI` / `notAtCTI` / `beforeCTI` / `afterCTI` ·
`isNested` / `isNotNested` · `isInSeqInOutRange` / `isNotInSeqInOutRange` ·
`hasAudioLinked` / `hasVideoLinked` / `hasLinked` ·
`isSpeedReversed` / `isNotSpeedReversed` · `hasSpeedChange` / `hasNotSpeedChange` ·
**`hasEffectByName`** · `isMogrt` / `isNotMogrt` ·
`isInSelectedClipsTrack` / `isNotInSelectedClipsTrack` · `isInTrack` / `isNotInTrack` ·
`isProjItemSelected`

**Presets fixos (9)** — os botões de um clique. Dois valem por si:
- **`selClipsToSelItems`** — dos clipes selecionados na timeline para os itens no painel de
  projeto; e **`isProjItemSelected`** faz o caminho inverso. ⭐ *A ponte bin ↔ timeline nos dois
  sentidos* é a operação de conform mais pedida, e está aqui pronta.
- **`selInstances`** — seleciona **todas as instâncias** do clipe selecionado na sequência.

---

## 2. ⭐⭐ `nodeId` é a identidade — a hipótese anterior fecha

A análise dos [quatro painéis](quatro-paineis-timeline.md) deixou `nodeId` como *"candidata a
identidade estável, `hipotese`, não medido"*. O Selector responde: **`nodeId` é a moeda de toda a
seleção dele.**

```
getSelectionNodeIds        curSelectedClipsProjItemNodeIds
getClipsByNodeIds          curSelectedItemsNodeIds
selectFromNodeIdsAry       getClipsNodeIdsAtCTI / BeforeCTI / AfterCTI
```

O ciclo é: *ler a seleção → guardar como lista de `nodeId` → filtrar → reselecionar a partir dos
`nodeId`*. Um produto comercial inteiro é construído sobre isso, o que promove `nodeId` de
`hipotese` a **`inferido` forte** como handle durável de clipe.

⚠️ **O que continua sem medição:** se o `nodeId` sobrevive a um **movimento** do clipe. O Selector
filtra e seleciona; ele não move nada. Para o `orbitaResolveClip` isso é justamente a pergunta —
então a promoção vale para "identificar", não ainda para "reencontrar depois de mexer".

⭐ E `setSelected` aparece na tabela de símbolos, coerente com a alavanca `updateUI` registrada em
[api-extendscript.md](api-extendscript.md).

---

## 3. ⭐⭐ O filtro "Has effects" está `onHold` — e é o mais instrutivo do arquivo

`FiltersDB.json` tem duas listas de espera: `commonOnHold` (1 filtro) e `clipOnHold` (2). Os dois
de clipe são:

```json
{ "displayName": "Has effects",    "func": "hasEffects",
  "onFailMessage": "Clip has no added effects",
  "ui": { "type": "RemovableButton" }, "excludes": ["hasNoEffects"],
  "valueRequired": false, "helpDescription": "The clip has effects applied." }
```

Especificado por inteiro — nome, mensagem, UI, exclusão. **E faltam exatamente os dois campos que
TODO filtro publicado tem: `runOrder` e `testValue`.**

⭐ **Isso desenha o processo deles:** um filtro só sai quando foi **medido** (vira `runOrder`) e
**testado** (vira `testValue`). O `hasEffects` não passou por esse portão. O que foi publicado é
`hasEffectByName`, com `runOrder: 286` e `testValue: "Timecode"`.

⚠️ **Por que um saiu e o outro não** é **inferência minha**, não fato lido — e este banco já errou
cinco vezes no eixo *ausência*. O que os dados sustentam: *"Has effects" existe, está completo e
não foi publicado; falta-lhe o que todo publicado tem.* O raciocínio abaixo é leitura, não
medição.

### A diferença técnica entre os dois, e ela é grande

`hasEffectByName` **procura um nome**: varre `components`, compara `matchName`/`displayName`,
responde. Não precisa saber o que é "efeito".

`hasEffects` precisa responder *"há algo ALÉM do que todo clipe já tem"* — e para isso tem de
**subtrair os componentes intrínsecos**. A tabela de símbolos entrega a lista que eles montaram
(`baseEffectsMatchNames`):

| espécie de clipe | componentes que existem sempre |
|---|---|
| vídeo | `AE.ADBE Motion`, `AE.ADBE Opacity` |
| **gráfico / título** | `AE.ADBE Graphic Group`, `AE.ADBE Text` |
| áudio | `Internal Volume Mono` \| `Internal Volume Stereo` \| `Internal Volume 16 Channel` |
| áudio | `Internal Channel Volume Stereo` \| `Internal Channel Volume 16 Channel` |

⚠️⚠️ **A armadilha, e ela é silenciosa:** o conjunto intrínseco **muda com a espécie do clipe**.
Um título carrega `Graphic Group` + `Text` **além** de Motion e Opacity; um áudio 16 canais tem
componentes de nome diferente do estéreo. Qualquer teste por **contagem** (`components.numItems >
2`) marca **todo título** e **todo áudio multicanal** como "tem efeito". E o erro não levanta
exceção — sai um relatório de conform com dezenas de falsos positivos, plausível o bastante para
ninguém conferir.

⭐ **A nota `"Clip has no added effects"` confirma a semântica pretendida:** *added*, aplicado pelo
usuário. Não é "tem componente", é "tem componente que não é de fábrica".

⛔ **A lição de produto:** *"selecione tudo que tem efeito" parece um filtro e é uma classificação.*
Se formos fazer, o trabalho não é varrer `components` — é **manter a tabela de intrínsecos por
espécie de clipe e por versão do Premiere**, e ter um caminho honesto para o que não reconhecer.

---

## 4. ⭐⭐ A rota do XML: `exportSeqAsFCPXML` + `xmlToJSON`

Símbolos presentes: `exportSeqAsFCPXML`, `exportAsFinalCutProXML`, `xmlToJSON`,
`Could not export XML from sequence`.

⭐ **É uma segunda forma de ler a timeline, e ela não passa pelo DOM.** Em vez de mil travessias da
ponte ExtendScript (e a §1 mostra que cada leitura de propriedade é cara), exporta-se a sequência
inteira como **FCP XML** num passo e lê-se o arquivo. O XML carrega efeitos **e parâmetros** —
que é justamente o que o assistente de conform precisa e o que o Selector não expõe.

Também presentes: `ExternalObject('lib:AdobeXMPScript')` (`XMPMeta`, `getXMPMetaProp`,
`curItemXMP`, `getProjItemXMPMediaType`) e — **terceira aparição** —
`kPProPrivateProjectMetadataURI`, depois do [Chop Chop](chopchop-arquitetura.md) e do
[Automation Blocks](quatro-paineis-timeline.md).

⚠️ O que **não** está aqui: nada de leitura de **valor** de parâmetro. O Selector toca
`components`, `curComponent`, `curEffect`, `matchName`, `displayName` — **presença e nome, nunca
valor**. Quem lê valor é o Automation Blocks.

---

## 5. ⭐ `AppWatcher` — a 2ª solução para a ausência de evento

`AppWatcher` (`constructor`/`init`/`initActiveProj`/`startAll`/`stopAll`) e `WatcherActiveProj`
(`init`/`start`/`stop`/**`compare`**), mais `initIsAliveWatcher`.

O CEP não tem evento para *"a seleção mudou"* ou *"a sequência ativa mudou"*. A resposta deles é
**polling com comparação de estado**. É a segunda solução independente para a mesma dor — a
primeira foi o `_cvpComputeTrackTopologySig` do Chat Video Pro (impressão digital da topologia).

⚠️ E o custo se soma ao da §1: um watcher que compara estado a cada tique paga o preço de leitura
de propriedade que o `runOrder` mede. `isEnabled` a 10966 dentro de um laço de polling é uma
decisão, não um detalhe.

---

## 6. O assistente de conform — de onde vem cada peça

Juntando as três análises, o produto que o autor descreveu é **montável**, e cada metade vem de um
lugar diferente:

| etapa | de onde | estado |
|---|---|---|
| **achar** os clipes por critério | Selector — 63 predicados + `runOrder` | ✅ pronto para copiar (é dado) |
| **"tem efeito"** genérico | ⛔ ninguém entregou — exige a tabela de intrínsecos (§3) | ⚠️ é o trabalho real |
| **"tem efeito X"** | `hasEffectByName`, por `matchName`/`displayName` | ✅ trivial |
| **ler os PARÂMETROS** | Automation Blocks: `component_parameter_get_value`, `..._get_value_at_time`, `..._path_keyframeable`; FX Launcher: `getSelectionProperties` | ✅ catalogado |
| **escrever o marcador** | Automation Blocks: `marker_create`, `marker_set_property`, `marker_color`, `marker_type` | ✅ catalogado |
| **relatório / XML** | `exportSeqAsFCPXML` + `xmlToJSON` — a sequência inteira num passo, com efeito e parâmetro | ⭐ a rota mais promissora |
| **seleção durável entre etapas** | `nodeId` (§2) | ⭐ `inferido` forte |

### ⚠️ Duas ressalvas de desenho, antes de prometer a funcionalidade

1. **Marcador de sequência não tem dono.** Ele fica num **tempo**, não num clipe nem numa trilha.
   Um marcador dizendo *"Lumetri com exposição +0,7"* aponta para um instante — se houver três
   clipes empilhados ali, ele não diz qual. Para conform de multicâmera isso importa: ou o texto
   do marcador carrega a trilha e o nome do clipe, ou o relatório vai ser ambíguo exatamente onde
   precisa ser preciso. (Marcador de **projectItem** tem dono, mas não aparece na timeline.)
2. **O caro é ler, não decidir.** O `runOrder` mostra que a travessia da ponte domina. Um
   assistente que percorra clipe a clipe lendo `components` e depois `properties` de cada um paga
   isso N×M vezes — e é aí que a rota do FCP XML (§4) deixa de ser elegante e passa a ser a
   escolha óbvia.

---

## ⚠️ A régua — o que NÃO foi feito

- **`js/main.js` (652 KB, javascript-obfuscator) não foi desofuscado.**
- **O JSXBIN não foi descompilado** — decodificada apenas a tabela de símbolos (1.822 entradas),
  passos 7 e 8 da ordem de ataque. Tudo que este documento diz sobre o comportamento interno é
  `inferido` a partir de **nomes**; o que é `confirmado` vem do **JSON de configuração**, que é
  dado declarado, não lógica.
- **`FiltersDB.json` e `FixedPresetsDB.json` foram lidos por inteiro** — são metadados em claro
  (passo 6 da ordem de ataque), e é de onde vem a maior parte do valor desta análise.
- **Nada instalado, nada executado.** O painel carrega `aescripts-cep-license-sp` (5ª aparição do
  canal aescripts neste banco); **nenhum mecanismo de licença foi examinado, contornado ou
  testado**.
- Temporários apagados ao fim.

## O que fazer com isto

1. ⭐⭐ **Se formos fazer o assistente de conform, comece pelo FCP XML** (§4), não por varredura de
   `components`. É um passo em vez de N×M travessias, e já traz parâmetro junto.
2. ⭐ **A tabela de intrínsecos (§3) é o ativo** — e é o que o fornecedor não conseguiu fechar.
   Nasce incompleta: precisa de caminho explícito para componente desconhecido (*"não sei
   classificar"* é resposta melhor que um falso positivo silencioso).
3. ⭐ **Copiar a ordem por custo do `runOrder`** em qualquer filtro composto nosso — é dado, sai de
   graça.
4. **Medir se o `nodeId` sobrevive a um `move()`** — fecha a pendência do `orbitaResolveClip`.
5. **Decidir o dono do marcador** (§6, ressalva 1) antes de desenhar o relatório.

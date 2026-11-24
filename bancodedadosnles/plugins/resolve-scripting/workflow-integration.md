# Workflow Integration Plugins — a OUTRA superfície do Resolve

Descoberta em 2026-08-24, abrindo o **Jumper**. O
[README](README.md) desta pasta descrevia o Resolve como tendo **uma** superfície — scripts em
Python/Lua com UI da UIManager do Fusion. **Há uma segunda, e ela é bem diferente.**

**Fonte:** `Jumper.app/Contents/Resources/Jumper.zip`, o plugin que o instalador descompacta em
`…/Blackmagic Design/DaVinci Resolve/Support/Workflow Integration Plugins/`.

---

## 1. O que é

Um **app Electron** que o Resolve hospeda, com acesso à API de scripting por um **módulo nativo de
Node** que a própria Blackmagic fornece.

```
Jumper/
  manifest.xml                 ← declara o plugin ao Resolve
  package.json                 ← "main": "resolve-launcher.js", "start": "electron ."
  resolve-launcher.js          ← processo principal do Electron
  resolve-preload.js           ← preload (ponte para o renderer)
  WorkflowIntegration.node     ← ⭐ addon nativo N-API, 1,5 MB — da Blackmagic
  index.html + _app/…          ← o frontend (o MESMO do painel do Avid)
```

### O manifesto

```xml
<?xml version="1.0" encoding="UTF-8"?>
<BlackmagicDesign>
    <Plugin>
        <Id>com.witchcraft.jumper</Id>
        <Name>Jumper</Name>
        <Version>1.0.0</Version>
        <Description>Jumper</Description>
        <FilePath>resolve-launcher.js</FilePath>
    </Plugin>
</BlackmagicDesign>
```

⭐ Cinco campos. Comparado ao `avid-manifest.json` (com `usesApi`, `allowedDomains`, `entitlements`,
`uiItems`) e ao `CSXS/manifest.xml` do CEP, é **o manifesto mais simples das quatro plataformas** —
não há declaração de permissão, de domínio permitido nem de escopo de API. *O plugin recebe o que o
`WorkflowIntegration.node` der.*

---

## 2. ⭐⭐ `WorkflowIntegration.node` — a ponte

Addon N-API. Os símbolos exportados contam o desenho:

| símbolo | o que sugere |
|---|---|
| `Initialize` / `InitAll` | inicialização do bridge |
| ⭐⭐ **`GetResolve`** | **devolve o MESMO objeto `resolve` da API de scripting** |
| `CleanUp` / `Cleanup` | encerramento |
| ⭐ `RegisterCallback` / `GetCallbackFunction` | **o Resolve pode chamar de volta** |
| `CreateFIFO` · `GetPipeName` · `OpenFile` · `CloseFile` | ⭐ o transporte é **pipe nomeado / FIFO** |
| `GetScriptObject` · `GetParam` · `BtVariantMap` · `GetBool/Int/Double/String/Uint` | marshalling de tipos entre JS e o objeto de script |
| `GetAPITimeout` | há timeout de chamada |

⭐⭐ **A consequência prática é grande:** um Workflow Integration Plugin tem **a API de scripting
inteira** (`GetResolve()` → `GetProjectManager()` → …) **mais uma janela própria de UI em HTML**. É
o que falta ao script do Fusion, que só tem a UIManager.

⭐ **E o transporte por FIFO explica o resto:** o plugin roda em **outro processo** (Electron), não
dentro do Resolve. Por isso precisa de pipe, marshalling de variantes e timeout — coisas que um
script Lua rodando dentro do processo não precisa.

⚠️ **`RegisterCallback` é a pista mais valiosa daqui.** O
[mapa §M](../../transversal/operacoes-de-nle.md) registra que o Resolve **não tem evento** e que a
saída é polling. Se o `WorkflowIntegration.node` permite registrar callback, pode haver notificação
de verdade nesta superfície. ⛔ **`hipotese`** — lido em nome de símbolo, não medido, e o nome pode
se referir apenas ao mecanismo interno de resposta assíncrona.

---

## 3. Script do Fusion × Workflow Integration — a comparação

| | Script (Fusion) | Workflow Integration Plugin |
|---|---|---|
| linguagem | Lua ou Python | **JS/Electron** |
| onde roda | **dentro** do processo do Resolve | **processo próprio** |
| UI | UIManager do Fusion (nativa) | **HTML/CSS/JS** — janela hospedada |
| API | `resolve` direto | `WorkflowIntegration.GetResolve()` |
| transporte | nenhum (mesmo processo) | **pipe nomeado / FIFO** |
| bloqueia a UI do Resolve | ⚠️ **sim** | não (processo separado) |
| instalação | copiar 1 arquivo em `Scripts/Utility/` | pasta em `Support/Workflow Integration Plugins/` |
| dependência do usuário | ⭐ nenhuma (Lua embutido) | ⚠️ traz o próprio Electron |
| manifesto | nenhum | `manifest.xml` de 5 campos |

⭐⭐ **A escolha entre os dois é de PRODUTO, não de capacidade:**

- **Script Lua** — instalação trivial, zero dependência, mas **UI pobre e bloqueia o app**.
- **Workflow Integration** — **UI web e não bloqueia**, mas pesa (Electron) e a instalação é uma
  pasta.

⚠️ **Para o Órbita isto reabre uma decisão fechada.** O
[README](README.md) desta pasta defende Lua *por causa da distribuição*, e o argumento continua
válido contra o **Python**. Mas contra o **Workflow Integration** o trade-off é outro: lá o problema
não é "o usuário tem Python?", é "o plugin traz um Electron". ⭐ *A nossa arquitetura já é painel
fino + serviço local — o Electron seria peso duplicado.* A decisão provavelmente não muda, mas
agora é uma decisão informada, não um caminho único.

---

## 4. ⭐⭐ Jumper: quatro NLEs, quatro mecanismos, UM frontend

O que torna o Jumper valioso aqui não é o que ele faz — é **quantas portas ele usa ao mesmo tempo**:

| NLE | mecanismo | peça |
|---|---|---|
| **Media Composer** | Panel SDK | `jumper.avpi` (12 KB — só manifesto + ícone) |
| **Premiere** | CEP | `Jumper.zxp` (5,1 MB) |
| **DaVinci Resolve** | **Workflow Integration Plugin** | `Jumper.zip` (6,4 MB) |
| **Final Cut Pro** | **Workflow Extension** (`.appex`) | `NSExtensionPointIdentifier: com.apple.FinalCut.WorkflowExtension` |

E o conteúdo é **o mesmo frontend web** nos quatro (`AvidFrontend/index.html` 3,4 MB ≈
`JumperFrontend/index.html` 3,4 MB ≈ `Jumper/index.html` 3,4 MB).

⭐⭐⭐ **É a demonstração mais limpa do princípio que o banco vinha juntando aos pedaços:
o painel é uma webview; o que muda entre NLEs é a CASCA que a hospeda e a ponte até a API.**
Quem escreve o frontend uma vez paga só a casca por plataforma.

⚠️ **E o custo aparece no tamanho da casca:** 12 KB no Avid (onde a página é servida pelo app por
HTTP) contra 5–6 MB no Premiere e no Resolve (onde a página vai dentro do pacote). *A escolha do
Avid — `.avpi` mínimo apontando para `localhost` — é a mais barata de atualizar: trocar o app
atualiza o painel.*

### O Final Cut, de graça

`Info.plist` do `.appex`:

```
NSExtensionPointIdentifier: com.apple.FinalCut.WorkflowExtension
ProExtensionPrincipalViewControllerClass: Workflow_Extension.ViewController
ProExtensionAttributes: { ContentViewMinimumWidth: 645, ContentViewMinimumHeight: 665 }
```

⭐ É uma **app extension do macOS** — mesmo mecanismo de share sheet e widgets, com um
`ViewController` nativo que hospeda a webview. Primeiro registro de FCP neste banco. Nada mais foi
investigado.

---

---

## 5. ⭐⭐⭐ MEDIDO (2026-09-25) — o De Lá Pra Cá rodou um plugin nosso

> Resolve **Studio 19.0.0b.59**, Windows 11. Spike: `_DeLaPraCa/.dev/spike_resolve_wi/` (7 arquivos),
> aberto pelo autor em Workspace › Workflow Integrations. Fonte oficial ao lado:
> `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Workflow Integrations\`
> (README.txt + `Examples/SamplePlugin`).

| pergunta | resultado | confiança |
|---|---|---|
| ⭐⭐ **o plugin traz Electron?** | **NÃO.** O Resolve hospeda o Electron; o exemplo oficial faz `require('electron')` sem `node_modules`. Nosso pacote: manifesto, `package.json`, `main.js`, `preload.js`, HTML/CSS e o `.node` (**329 KB**). *Corrige a §3: "traz o próprio Electron" era inferência do tamanho do Jumper.* | confirmado |
| versões do motor | ⚠️⚠️ **Electron 8.0.1 · Node 12.13 · Chrome 80** (2020) — o Chromium MAIS VELHO entre os nossos hosts. Sem `gap` em flex (84), `inset` (87), `accent-color` (93), `color-mix` (111): a declaração some **em silêncio** (mesma armadilha do CEP 11, `premiere-cep/README.md`). CSS compartilhado entre NLEs se escreve para o Chrome 80 | confirmado |
| o `.node` é redistribuível? (buraco 5) | vem **com a instalação do Resolve** (`Developer/…/SamplePlugin/WorkflowIntegration.node`) → o instalador COPIA de lá, não empacotamos | confirmado |
| como o Resolve acha o plugin? (buraco 4) | pasta `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\<id>\` com `manifest.xml`; **varre só ao ABRIR** (reiniciar o Resolve). A pasta raiz não existia e foi criada **sem elevação** | confirmado |
| a ponte funciona? | `Initialize(<Id do manifesto>)` = true; `GetResolve()` → projeto, pastas e timelines em **119 ms** (primeira chamada, com Initialize) | confirmado |
| janela | `BrowserWindow` própria com `setMenu(null)`, `contextIsolation: true` + `preload` com `contextBridge` funcionam; a janela flutua sobre o Resolve | confirmado |
| ⚠️⚠️ **`ImportTimelineFromFile(drt, {})` pela ponte JS** | **IMPORTA a timeline e mesmo assim LEVANTA** `Execute: Exception occured while performing operation`. Pelo Lua a mesma chamada devolve a Timeline. Quem trata a exceção como "não importou" deixa a timeline com o nome do ARQUIVO (o `SetName` nunca roda), e quem tenta de novo IMPORTA DUAS VEZES. Defesa na casca do De Lá Pra Cá (`importarDrt`): anota as timelines antes, chama sem o dicionário e acha a nova pela diferença. ⭐ **MEDIDO no mesmo dia: `ImportTimelineFromFile(drt)` SEM o dicionário devolve a Timeline** (insert de 3 clipes, 5,8 s). O culpado é o `{}` vazio atravessando a ponte — objeto JS vazio não vira dicionário do Resolve. Regra: pela ponte JS, **omita** argumento de opções vazio | confirmado |
| o item do pool também leva o nome do arquivo? | pela ponte JS, **sim** (`c82889a8-….drt` → item `c82889a8-…`); pelo Lua, o item levou o nome de dentro do DRT. `SetName` na Timeline renomeia os dois (medido pelo Lua) | confirmado (JS) |
| 🆕 ⚠️⚠️ **`Timeline.SetName` com nome REPETIDO pela ponte JS** | **Abre o diálogo MODAL** "Unable to Rename Timeline — The timeline '<nome>' already exists in this project" e devolve `false`; pelo `fuscript` (Lua) o mesmo `SetName` só devolve `false`, sem diálogo. Quem descobre o nome livre tentando (`<nome>`, `<nome> 2`…) acerta o nome e ainda assim mostra o erro ao colorista. **Regra:** escolher o nome livre ANTES, pela lista `GetTimelineByIndex`/`GetName` (sem maiúscula/minúscula), e chamar `SetName` uma vez. Casca do De Lá Pra Cá: `nomeLivre` em `plugins/resolve/casca/main.js` | confirmado (print do autor, Studio 19 public beta, Win11, 2026-09-27) |
| ⚠️ o `.node` com o painel aberto | fica **travado**: reinstalar por cima dá PermissionError. O instalador só o reescreve se mudou | confirmado |
| bloqueia o Resolve? | o autor mexeu no Resolve com o painel aberto sem queixa; chamada longa não medida | `inferido` |
| 🆕 versões do motor no **Studio 21.1.0 (macOS 15.6.1)** | **Electron 36.3.2 · Chrome 136.0.7103.115** (`DaVinci Resolve.app/Contents/Applications/.hidden/Electron.app`). O piso continua o Chrome 80 do 19. Os exemplos do 21 trazem `preload.js` e um `CompatibleSamplePlugin` com `nodeIntegration: true` + `contextIsolation: false` "para plugins antigos"; a casca do De Lá Pra Cá já usa `contextIsolation: true` + `preload`, o modelo novo. Exemplos do 21: `SamplePlugin`, `SamplePromisePlugin`, `CompatibleSamplePlugin`, `ScriptTestPlugin` | confirmado (versão, lida do disco, 2026-10-01); a casca rodando no 21 `pendente` |
| 🆕 changelog da Blackmagic | **19.0.2: Electron 31.3.1** (o 19.0.0b.59 do piso ainda é o 8.0.1) · **20.1: Electron 36.3.2 + "Javascript promises API"** (exemplo `SamplePromisePlugin`) · **20.2.3: plugins persistem entre reinícios** · 19.0.3: desempenho no Apple Silicon. ⚠️ "Resolve 19" não é uma versão só: o Chromium da casca muda dentro do 19 | confirmado (changelog, 2026-10-01) |
| Resolve Free / macOS | `pendente` (o README diz Studio; Mac em `/Library/Application Support/…/Workflow Integration Plugins/`) | pendente |

## ⚠️ A régua desta rodada

- ⭐ **O caro NÃO foi extraído.** O Jumper tem 14,5 GB em três builds; o instalador Windows são 5
  CABs de 5,4 GB com nomes em hash. **A rota barata foi ler as strings do MSI (5 MB)** para
  descobrir *que* integrações existem, e depois tirar do `.dmg` **só as quatro peças** (~12 MB), que
  ali têm nome real. *Listar antes de extrair economizou horas e gigabytes.*
- **Lido:** manifestos, `package.json`, `Info.plist`, nomes de símbolo do addon nativo.
- ⛔ **NÃO lido:** `resolve-launcher.js` e `resolve-preload.js` (a cola do Electron), o frontend de
  3,4 MB, e **todo o lado de ML** — `scene_detection`, agrupamento facial e transcrição continuam
  `pendente` desde 2026-08-08. ⚠️ **Não por régua** (a nova permite): por **relevância** — o domínio
  do Jumper é busca de mídia, não manipulação de timeline.
- **Nada instalado, nada executado, licenciamento não tocado.**

## Buracos

| # | pergunta |
|---|---|
| 1 | ⭐⭐ **`RegisterCallback` dá EVENTO de verdade no Resolve?** — se sim, muda o §M do mapa |
| 2 | ~~O que o `WorkflowIntegration.node` expõe além de `GetResolve`~~ **Medido 2026-10-03 (§6)**: `GetInfo, Initialize, GetResolve, CleanUp, RegisterCallback, DeregisterCallback, SetAPITimeout, InitializePromise, GetResolvePromise` |
| 3 | ~~Pode existir sem Electron próprio?~~ **Sim — o Resolve hospeda (§5, medido)** |
| 4 | ~~Como o Resolve descobre?~~ pasta em `%PROGRAMDATA%`, varre ao abrir (§5) |
| 5 | ~~O `.node` é redistribuível?~~ vem com o install do Resolve; copia-se de lá (§5) |

## 6. ⭐⭐ O Fusion pela ponte JS — MEDIDO 2026-10-03 (Resolve Studio 21.1, macOS, Electron 36.3.2)

- **O Fusion vem pela METADE.** `TimelineItem.AddFusionComp()`, `comp.FindTool()` e `comp.AddTool(tipo,
  x, y)` funcionam (o nó aparece na composição), mas a ferramenta que volta **não tem
  `LoadSettings`, `SetInput` nem `ConnectInput`** (`ferramenta.LoadSettings is not a function`) — os
  nós ficam criados e vazios. Os métodos do **TimelineItem** vêm inteiros.
- ✅ **O caminho que funciona**: `AddFusionComp()` (+ `LoadFusionCompByName(nova)`) →
  `ExportFusionComp(arq, índice)` → escrever os nós configurados e ligados no TEXTO da composição →
  `ImportFusionComp(arq)` (substitui a ATIVA, que é a nova; a do usuário fica). Conferido pela
  imagem: idêntico pixel a pixel ao mesmo plano montado pelo scripting em Python (Polygon, Blur,
  CornerPositioner). De Lá Pra Cá, `casca/main.js` (`executarPlano`, `comporFusion`).
- ⚠️ Segurança: o texto de uma composição pode levar código Lua — a casca o monta a partir de
  NÚMEROS conferidos e de uma lista fechada de tipos/ligações, nunca o recebe pronto.
- ⚠️ **`Initialize(id)` num Node comum (fora do Resolve) TRAVA** sem resposta, mesmo com o plugin
  instalado e o Resolve aberto: a ponte só aceita o processo que o próprio Resolve hospeda. Para
  testar pela ponte real, a casca instalada precisa ser aberta (Workspace › Workflow Integrations).
- Piso: CORRIGE (2026-10-03): medido no Resolve 19 — ver o bloco abaixo.

### ⭐⭐ `ImportFusionComp` no Resolve 19 — MEDIDO 2026-10-03 (Studio 19.0.0b.59, Windows 11, API Python, caso R02)
- ⛔ **Num clipe que JÁ tem composição, `ImportFusionComp` devolve um objeto `Composition` (verdadeiro) e
  NÃO MUDA NADA**: a lista do clipe continua igual e a composição ativa segue como estava (reexportada,
  sem os nós). O objeto devolvido tem os nós, mas não está ligado ao clipe. No 21.1 a mesma chamada
  SUBSTITUI a ativa. Consequência real: a casca (caminho do 21: `AddFusionComp` → Export → compor →
  Import) deixou as 3 composições do R02 VAZIAS (`MediaIn → MediaOut`) e registrou "3 de 3 criadas".
- ✅ **Num clipe SEM composição**, `ImportFusionComp` cria a `Composition 1` com o conteúdo e **RELIGA o
  `MediaIn1` à mídia do próprio clipe** (`MEDIA_PATH`, `Filename`, `MEDIA_MARK_IN` do clipe), mesmo que o
  texto venha de outro clipe ou de um molde mínimo sem `CustomData`. Não é preciso exportar antes.
- `DeleteFusionCompByName` da ÚNICA composição devolve `False` (não apaga).
- `ExportFusionComp` e `ImportFusionComp` aceitam o caminho temporário em nome **8.3**
  (`C:\Users\USUARI~1\AppData\Local\Temp\…`).
- Regra que vale nas duas versões: **o retorno do `ImportFusionComp` não prova nada — conferir pelo
  `ExportFusionComp` de volta** (os nós `Id = Tipo {` e o `MEDIA_PATH`). De Lá Pra Cá, `executarPlano`
  (casca) / `fusion_clipe.executar`: A) clipe sem composição → importa direto o molde composto;
  B) senão → o caminho do 21; os dois conferidos. ✅ O caminho A no 21: `confirmado` (2026-10-04, 21.1.0.14,
  macOS, casca v0.1.59 pelo gesto, caso R02: cada um dos 3 clipes com UMA composição, os nós certos e o
  `MEDIA_PATH` = a mídia do próprio clipe — ou seja, o A pegou; o B empilharia uma 2ª).
- Pela ponte JS do Electron 8: `AddFusionComp`, `GetFusionCompNameList`, `ExportFusionComp` e
  `ImportFusionComp` existem e respondem (as composições foram criadas); a casca corrigida, PELA PONTE
  (Electron 8.0.1), montou as 3 do R02 — Polygon/Blur/CornerPositioner ligados, MediaIn de cada
  clipe — `confirmado` 2026-10-03 (reexportadas pela API Python e conferidas nó a nó).


## 🆕 A casca NÃO sobe mais o motor — 2026-10-04 (decisão do autor)

Até 2026-10-04 a casca do De Lá Pra Cá subia o serviço sozinha (`receptor.json` gravado pelo `pack.py`).
Medido no Mac (Resolve 21.1, `ps eww`): o processo filho do Electron do Resolve nasce com o PATH mínimo
de `.app` (`/usr/bin:/bin:/usr/sbin:/sbin`) — sem o ffprobe do Homebrew, e a timeline inteira saiu
offline sem erro nenhum. Agora o dono do motor é o APLICATIVO, como no Media Composer e no Premiere: a
casca mostra "Serviço não encontrado — abra o De Lá Pra Cá", com o botão que abre o app (caminho em
`aplicativo.json`, gravado pelo serviço a partir do `--app`), e entra no painel sozinha quando o motor
responde — sem prazo, em qualquer ordem. O painel ainda esconde as opções até a `/prontidao` dizer
`ok` (ffprobe/ffmpeg RODAM, a pasta grava). `abrirApp` no Windows (Electron 8): `pendente`.

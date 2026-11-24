# API de scripting do Resolve — operações e armadilhas

Referência por **operação**. Visão geral e distribuição em [README.md](README.md); o mapa
cross-NLE em [`../../transversal/operacoes-de-nle.md`](../../transversal/operacoes-de-nle.md).

Duas fontes independentes: o **Órbita** (`plugins/resolve-script/orbita_sync.lua`, em produção) e o
**Chop Chop** ([`chopchop-algoritmo.md`](../premiere-cep/chopchop-algoritmo.md), lido por inteiro).
Onde as duas divergem, está marcado — a divergência costuma ser o achado.

## Os objetos raiz

```
resolve → GetProjectManager() → GetCurrentProject() → GetMediaPool() → GetRootFolder()
resolve → GetMediaStorage()
```

`GetVersionString()` e `GetProductName()` identificam a build (há produto que recusa abaixo de uma
versão mínima).

⛔ **Decisão da família (autor, 2026-10-31): só Resolve STUDIO.** Na gratuita não há scripting externo, e o caminho
"possível" (operar a GUI com o piloto) fica PROIBIDO: sem `Studio` em `GetProductName()`, a operação é recusada. ⚠️ Na
gratuita a API nem conecta — "não consegui perguntar" ≠ "é a gratuita". Distinguir as duas SEM a API (disco/registro;
o executável é `Resolve.exe` nos dois): `pendente`. Ver Ciclo Assist `docs/plano/2026-10-31-o-assist-operador.md`.

---

## 1. Montar a timeline

```
mediaPool.CreateEmptyTimeline(nome)
project.SetCurrentTimeline(timeline)          ← obrigatório ANTES de anexar
timeline.SetSetting("timelineFrameRate", "23.976")
timeline.AddTrack("video")
timeline.AddTrack("audio", subtipo)
timeline.SetTrackName("video", índice, nome)
mediaPool.AppendToTimeline(listaDeClipInfo)
```

### O `clipInfo`

| campo | o que faz |
|---|---|
| `mediaPoolItem` | o item |
| `startFrame` / `endFrame` | recorte **na fonte** |
| `trackIndex` | trilha de destino (1-based) |
| `recordFrame` | ⭐ posição **absoluta** na timeline |
| ⭐⭐ `mediaType` | **1 = vídeo, 2 = áudio** |

⭐⭐ **`mediaType` é o campo que separa as duas implementações, e é o mais importante da pasta.**
Com ele, vídeo e áudio de um mesmo clipe são colocados **independentemente**, em trilhas de sua
escolha.

⛔ **O Chop Chop NÃO usa `mediaType`** — e por isso é obrigado a fazer o índice de vídeo valer
`câmeraIndex × maxCanaisDeÁudio + 1`, para manter os índices de vídeo alinhados aos blocos de
áudio. Resultado: **3 câmeras × 8 canais = 24 trilhas de vídeo, 21 vazias.**

⭐ **Com `mediaType`, o layout ideal sai direto e não há trilha vazia nenhuma.** É a mesma dor que o
`host.jsx` do Premiere resolve depois, apagando trilhas vazias pelo QE — no Resolve dá para não
criar.

⚠️ **`recordFrame` sem `GetStartFrame()` erra.** A timeline pode não começar em 0; o Órbita soma
`timeline:GetStartFrame()` ao alvo. O Chop Chop, em vez disso, converte o `Start TC` da timeline
para frames. *As duas resolvem o mesmo problema por caminhos diferentes.*

### ⚠️⚠️ Divergência não resolvida: `endFrame` é inclusivo?

| | o que faz |
|---|---|
| Órbita | `endFrame = Frames − 1` (trata como **inclusivo**) |
| Chop Chop | `endFrame = duration` (trata como **exclusivo**) |

**Uma das duas está com um frame de erro.** `pendente` — vale uma medição curta, porque um frame por
clipe num stringout de diária acumula.

✅ **MEDIDO 2026-10-01 — `endFrame` é EXCLUSIVO** (Studio 21.1.0.14, macOS 15.6.1, Python pelo MCP do Resolve, timeline vazia a 23,976): `startFrame 100, endFrame 147` → `GetDuration()` 47, no vídeo (MXF do Avid) E no áudio (MXF OP-Atom). **O Chop Chop está certo; o Órbita perde um quadro por clipe.** O De Lá Pra Cá perdia um quadro por plano inserido no Atualizar (corrigido, `servico/atualizacao.py`). No 19.0.0b (o piso, Windows) `pendente`: a casca confere a duração de cada plano inserido e avisa. ⚠️ O getter é inclusivo: `GetSourceEndFrame()` devolve 146. ⚠️ `GetSourceStartFrame()` arredondou 2281 para 2280 num MXF com TC 04:53:47:11; o `GetLeftOffset()` deu 2281 (use este).

### 🆕 Ler a SELEÇÃO da timeline (igualar as funções, 2026-10-25)

✅ **MEDIDO (Studio 21.1, macOS, pelo MCP): `Timeline.GetSelectedClips()` devolve os `TimelineItem` SELECIONADOS na UI**
— a leitura da seleção, como o MC (ARO/Cmd+C) e o Premiere (ponte CEP) já têm. Casa com a enumeração
`GetItemListInTrack` pela chave **(GetStart, GetDuration, GetName)**: o subconjunto bate byte a byte (214 selecionados ⊆
228 itens). ⚠️ A API **NÃO diz a trilha** de um item da seleção, então a chave não a inclui → dois itens com MESMO
início+duração+nome (par estéreo L/R em A1/A2) têm a mesma chave e entram juntos (over-inclusão benigna; nunca EXCLUI um
selecionado). ⚠️ **Não há como SELECIONAR por script** (só ler) — para testar, selecione na UI (ou Cmd+A). ⏳ Confirmar
no **Resolve 19** (o piso, Windows) se `GetSelectedClips` existe; o De Lá Pra Cá degrada sozinho (`selecao_indisponivel`
→ cai na timeline inteira). Uso no app: `resolve_externo.selecao_da_timeline` + `ler_timeline(so_selecionados=True)` →
a conferência roda só nos selecionados; a REFERÊNCIA (anexada numa trilha nova) é sempre mantida no filtro.

### Armadilhas de criação

⚠️ **Nome duplicado é recusado — em silêncio.** `CreateEmptyTimeline` devolve algo falso e nada
explica. O contorno é gerar nome único antes.

⚠️ ⭐ **A taxa que você pediu pode não ser a que ficou.** Depois de criar, **releia**
`timeline:GetSetting("timelineFrameRate")` e use o valor real para posicionar — senão o
`recordFrame` é calculado numa taxa e aplicado noutra.

⚠️ **A taxa é uma STRING de vocabulário fixo** (`"23.976"`, `"24"`, `"25"`, `"29.97"`, `"30"`,
`"47.952"`, `"48"`, `"50"`, `"59.94"`, `"60"`). O Órbita aproxima pelo mais próximo com tolerância
de 0,06 e cai para o inteiro arredondado fora disso.

⚠️ **Uma timeline vazia já nasce com 1 trilha de áudio estéreo.** Ambos os produtos acrescentam as
suas e **apagam a trilha 1 no fim**.

---

## 2. ⭐⭐ Verificar o que o Resolve REALMENTE fez

`AppendToTimeline` **devolve os itens criados**. Pergunte a cada um onde caiu:

```
item:GetTrackTypeAndIndex()   →  { "audio", 3 }
```

⭐ **É o instrumento que revela se o Resolve espalhou um multicanal pelas trilhas mono ou rebaixou
tudo numa só** — coisa que o pedido não diz e o olho não vê. O Órbita monta um mapa de ocupação
(`A1:12 A2:12 A3:0 …`) e loga.

⭐⭐ **A regra transferível: quando a plataforma aceita um pedido complexo e não promete como vai
executá-lo, CONFIRA o resultado.** É a mesma família do `Overwrite` do Avid que *"retorna Completed
mas não faz nada"*.

---

## 3. Trilhas

| operação | chamada |
|---|---|
| contar | `GetTrackCount("video" \| "audio")` |
| criar | `AddTrack(tipo [, subtipo])` |
| apagar | `DeleteTrack(tipo, índice)` |
| nomear | `SetTrackName(tipo, índice, nome)` |
| ler itens | `GetItemListInTrack(tipo, índice)` |

Subtipos de áudio vistos: `"mono"`, `"stereo"`, `"adaptive1"` … `"adaptiveN"`.

⛔ **Não há API para MUDAR o subtipo de uma trilha existente.** Só criar com ele. O contorno de
ambos os produtos: apagar e recriar.

### ⭐ Espelhar a estrutura de áudio da fonte — `GetAudioMapping()`

Devolve uma **string JSON** com `track_mapping`: as chaves são índices de trilha, cada uma com
`type` e um array `channel_idx`. Dá para reproduzir na timeline exatamente o formato nativo do
material — WAV estéreo vira uma trilha `stereo`; uma câmera com 4 mono vira 4 trilhas `mono`.

⚠️ É JSON **como texto**, não objeto: precisa de decode, e pode vir vazio.

---

## 4. Media Pool — importar, mover, apagar, selecionar

| operação | chamada |
|---|---|
| importar | `mediaStorage.AddItemListToMediaPool(arquivos)` |
| ⭐ ler seleção | `mediaPool.GetSelectedClips()` — ⛔ **NÃO existe no 19.0.0b** (Windows, 2026-10-12: `TypeError 'NoneType' object is not callable`, e fora do `dir()` do MediaPool); de que versão em diante: `pendente` (o Órbita o usa — medir no 21 do Mac mini) |
| mover entre bins | `mediaPool.MoveClips(itens, pastaDestino)` |
| apagar | `mediaPool.DeleteClips(itens)` |
| criar bin | `mediaPool.AddSubFolder(pai, nome)` |
| navegar | `GetRootFolder()`, `GetSubFolderList()`, `GetClipList()` |
| ⚠️ pasta corrente | `mediaPool.SetCurrentFolder(pasta)` |
| proxy | `item.LinkProxyMedia(caminho)` |

⚠️ **`SetCurrentFolder` é estado GLOBAL do app** — define onde a importação cai. Esquecer de setar
importa no lugar errado, sem erro.

⚠️ **`LinkProxyMedia` casa por nome**, o que pressupõe proxy com o mesmo nome do original.

### ⭐⭐ Importar uma timeline de ARQUIVO — `ImportTimelineFromFile` (MEDIDO, 2026-09-24)

> **Resolve Studio 19.0.0b.59, Windows 11**, script **Lua** rodado pelo menu Workspace › Scripts,
> projeto vazio. Spike: `_DeLaPraCa/.dev/spike_resolve_import.lua`. Arquivo: DRT gerado pelo De Lá
> Pra Cá sobre o esqueleto R19 (`TESTE_PRODA_R19_GERENCIADA.drt`, 1017 itens).

| pergunta | resultado | confiança |
|---|---|---|
| funciona pela API? | ✓ `mediaPool:ImportTimelineFromFile(caminho, {…})` devolve o objeto `Timeline` (7,2 s de CPU) | confirmado |
| a mídia vem? | vídeo 108/108 com arquivo; som 628 com arquivo — **o mesmo número** que o Resolve deixou online importando o AAF do mesmo corte pela interface | confirmado |
| onde cai? | **tudo** (timeline + 242 clipes) na pasta dada a `SetCurrentFolder` antes; raiz intacta | confirmado |
| `timelineName` nas opções | ⚠️ **ignorado para DRT** | confirmado |
| ⚠️⚠️ de onde vem o nome? (**CORRIGIDO 2026-09-25**) | **São DOIS nomes.** O ITEM do Media Pool leva o nome de DENTRO do `.drt`; o **objeto `Timeline`** (seletor de timeline, viewer, `GetName()`, `GetTimelineByIndex`) leva o nome do **ARQUIVO** sem extensão. No spike os dois coincidiam por acaso; com `<uuid>.drt` o editor viu `8a552457-…` na tela e `PRODA_CORTE` no pool. **Conserto:** `timeline:SetName(nome)` logo depois de importar — renomeia os dois. `SetName` devolve **`false`** (e não renomeia) se o nome já existe: tente `<nome> 2`, `<nome> 3`… ⚠️ **CORRIGE (2026-09-27):** pela ponte JS do Workflow Integration a tentativa repetida ABRE um diálogo modal — escolha o nome livre pela lista de timelines ANTES (`workflow-integration.md`) | confirmado (De Lá Pra Cá, `fuscript`, Studio 19.0.0b.59) |
| importar de novo, mesmo nome | **não recusa**: o Resolve cria `"<nome> 2"`. (O "recusado em silêncio" da §1 vale para `CreateEmptyTimeline`, não para importação.) | confirmado |
| início | `GetStartTimecode()` = 01:00:00:00, igual à sequência no Avid | confirmado |

⚠️ **`print` no Lua do Resolve (`fuscript.exe`, 19.0.0b):** NÃO separa os argumentos com TAB como o
Lua padrão — junta tudo e põe o TAB no FIM (`print('a', 1)` → `a1\t`). Teste que lê a saída do
script deve imprimir UM texto por linha (`print('chave=' .. tostring(v))`). Medido em 2026-09-24.
⭐ O `fuscript.exe -l lua -x "<código>"` roda Lua SEM o Resolve aberto: serve para testar as partes
puras de um script (defesas de shell, JSON) antes de abri-lo no menu.

⭐ **Scripting externo pelo `fuscript.exe -l lua arquivo.lua` com o Resolve Studio ABERTO** alcança o projeto corrente (`bmd.scriptapp("Resolve")`): dá para LER o Media Pool e medir uma chamada sem pedir ao autor que clique no menu. Medido 2026-09-25 — e o Lua ali é **LuaJIT 2.1.0-beta3 com `require("ffi")`** e `bmd.wait` presentes.

⚠️ **Ainda não medido:** Resolve Free (o banco diz, sem medição, que scripting EXTERNO é
Studio-only — pelo menu pode ser outro caso); macOS; as outras opções do dicionário
(`importSourceClips`, `sourceClipsPath`, `sourceClipsFolders`); AAF/XML/OTIO por essa chamada.

---

## 5. Propriedades e metadado

**`GetClipProperty(nome)` / `SetClipProperty`** — propriedades técnicas:
`File Path` · `Start TC` · `End` · `Frames` · `FPS` · `Resolution` · `Audio Ch` · `Type`
(`"Video + Audio"`, `"Audio"`, `"Still"`, `"Timeline"`) · `Online Status` · `Date Added` ·
⭐ `Usage`.

**`GetMetadata(campo)` / `SetMetadata`** — campos de produção:
`Scene` · `Shot` · `Take` · `Camera ID` · `Episode #` · `FPS`.

**`GetData` / `SetData`** — armazém chave-valor livre.

⭐⭐ **`Usage` diz quantas vezes o clipe está em alguma timeline.** É a forma de resolver duplicata
**sem rastrear estado nenhum**: o Resolve já sabe. O Chop Chop usa `Usage` para decidir o que não
apagar, e `Date Added` para desempatar entre os não usados.

⚠️ **Duração:** `Frames` é o caminho; quando falta, `End + 1`.

---

## 6. Sync nativo — `AutoSyncAudio`

```
settings = {
  resolve.AUDIO_SYNC_MODE:                   resolve.AUDIO_SYNC_WAVEFORM | AUDIO_SYNC_TIMECODE,
  resolve.AUDIO_SYNC_CHANNEL_NUMBER:         1,
  resolve.AUDIO_SYNC_RETAIN_EMBEDDED_AUDIO:  True,
  resolve.AUDIO_SYNC_RETAIN_VIDEO_METADATA:  False,
}
mediaPool.AutoSyncAudio(itens, settings)
```

⛔⭐ **O limite, admitido pelo fabricante do produto que o usa** (manual do Chop Chop, p.16): por
**forma de onda**, o `AutoSyncAudio` casa o áudio de uma câmera com o vídeo *dela mesma*, e **não
sincroniza câmera com câmera**; e é lento a ponto de o próprio manual desaconselhar em multicâmera.
Em multicâmera sobra o **timecode**, que exige jam sync na diária.

⭐ **Quem delega o motor herda os limites do motor.** É a razão de um motor de sync próprio existir.

---

## 7. Timeline — ler e limpar

| operação | chamada |
|---|---|
| contar | `project.GetTimelineCount()` |
| obter | `project.GetTimelineByIndex(i)` |
| itens | `timeline.GetItemListInTrack(tipo, índice)` |
| vinculados | `item.GetLinkedItems()` |
| início | `timeline.GetStartFrame()` |
| apagar | `timeline.DeleteClips(itens)` |

⚠️⚠️ **Não há caminho de um `MediaPoolItem` do tipo `Timeline` para o objeto `Timeline`.** Ambos os
produtos varrem `GetTimelineByIndex` **comparando NOMES**. É a lacuna de API mais irritante da
plataforma — e obriga nomes únicos (ver §1).

⚠️ **Esvaziar uma timeline exige varrer TODAS as trilhas de vídeo e áudio** e juntar cada item
**e seus vinculados**. Apagar só a trilha de vídeo 1 deixa a timeline suja.

⚠️⚠️ ⭐ **Os objetos remotos do Resolve NÃO são *hashable*.** Um `set()` de `MediaPoolItem` estoura.
Para deduplicar, use `id(obj)` (Python). `GetUniqueId()` existe e serve como identidade estável.

---

### 🆕 Editar uma CÓPIA da timeline, e exportar — medido 2026-09-27 (Studio 19 public beta, Win11, `fuscript` externo)

- ✅ `Timeline:DuplicateTimeline(nome)` + `DeleteClips({item}, false)` + `MediaPool:AppendToTimeline({{mediaPoolItem,
  startFrame, endFrame, trackIndex, recordFrame}})` editam SÓ a cópia: a original fica intacta (conferido pelos
  `GetStart()` pela API), os planos que ficam MANTÊM a correção de cor (lida no DRT exportado) e o plano novo
  chega sem correção. É a execução de "Atualizar timeline" pela API, sem reescrever DRT.
- ✅ `TimelineItem:SetCDL({NodeIndex="1", Slope="r g b", Offset, Power, Saturation})` devolve `true` num
  plano recém-importado (1 nó).
- ✅ `TimelineItem:CopyGrades({alvos})` devolve `true` entre timelines diferentes. Ainda não se sabe se a
  correção chegou (a leitura dependia do `Export`, abaixo).
- ⛔ **`Timeline:Export(arquivo, EXPORT_DRT)` por script EXTERNO não exporta a timeline pedida.** Depois que
  uma timeline "pega" (aqui, a criada por `DuplicateTimeline`), TODO `Export` de qualquer outra sai com o
  conteúdo dela, mesmo com `SetCurrentTimeline` devolvendo `true`, `GetCurrentTimeline():GetName()` dizendo o
  nome certo, `bmd.wait(3)` e `OpenPage("color")` → `OpenPage("edit")`. A 1ª exportação, da timeline recém-
  importada, saiu certa. Causa não achada. **Regra:** não use o `Export` para conferir o conteúdo de outra
  timeline; leia pela API (`GetItemListInTrack`, `GetStart`…). Pela ponte do painel (Workflow Integration),
  `pendente`.
- ⛔ `TimelineItem:ExportLUT(resolve.EXPORT_LUT_17PTCUBE, caminho)` devolveu `false` em todos os planos
  (caminho com espaços, na pasta temporária do usuário). Causa `pendente`.
  ✅ CAUSA ACHADA 2026-09-28: no 19.0.0b.59 a constante `EXPORT_LUT_17PTCUBE` é `nil` (não existe),
  embora o README a liste. A chamada recebia `nil` como tipo.
- ⭐⭐ **`Timeline:GetItemListInTrack(tipo, i)` conta as TRANSIÇÕES junto com os itens** (2026-09-28,
  19.0.0b.59, a PRODA do autor pela ponte JS): em cada trilha, o número da API = `Sm2TiVideoClip`/
  `Sm2TiAudioClip`/`Sm2TiGenerator` + `Sm2TiTransition` do DRT exportado, trilha por trilha, sem exceção
  (a trilha do título com fade de entrada e saída: 2 itens no arquivo, 4 na API). Quem confere a API
  contra o arquivo tem de somar as transições (`_DeLaPraCa/motor/drp/reescrever.py::contagem`). E a
  exportação DE DENTRO do Resolve pela ponte (casca do painel) exportou a timeline pedida.
- ⭐⭐ **As constantes de exportação na PONTE JS do Workflow Integration** (2026-09-28, 19.0.0b.59, print do
  autor): `resolve.EXPORT_DRT` **NÃO existe** pela ponte ("undefined"). No Lua (`fuscript`) elas existem:
  `EXPORT_AAF=0`, **`EXPORT_DRT=1`**, `EXPORT_EDL=2`, `EXPORT_FCP_7_XML=3`, `EXPORT_OTIO=15`, `EXPORT_NONE=-1`
  (a ordem do README). A casca do De Lá Pra Cá usa o nome se existir e o número 1 se não; se uma versão
  renumerar, sai outro formato e o serviço recusa ler como DRT (nada é alterado). No 21 os valores ainda
  não foram lidos (`pendente`).
- A API não tem leitura dos valores de uma correção (não há `GetCDL`): o único jeito medido é o `Body` do DRT
  exportado (`protocolos/drt-drp/estruturas.md` §"A CORREÇÃO DE COR").
- 🆕 2026-09-28 (mesmo ambiente, `fuscript` externo), as peças da execução do "Atualizar timeline":
  - ✅ `TimelineItem:SetClipColor("Pink")` é a cor **LOCAL**: o item fica Pink, o `MediaPoolItem:GetClipColor()`
    continua vazio e outro item da mesma mídia também. No DRT exportado ela vira o `Sm2TiItemLockableBlob`
    do item (a mesma cor local de `drt-drp/dados/marcadores-e-cores.json`).
  - ✅ `Timeline:AddMarker(q, cor, nome, nota, dur, customData)`: `q` conta do INÍCIO da timeline
    (`GetStartFrame()` = 86400 não entra); o `customData` é guardado e volta no `GetMarkers()`.
  - ✅ `MediaPool:AppendToTimeline({{mediaPoolItem, startFrame, endFrame, mediaType = 2, trackIndex = 1,
    recordFrame}})` insere ÁUDIO na A1, no quadro pedido (`recordFrame` absoluto, com o 86400).
  - ✅ A timeline é um item do pool: `Folder:GetClipList()` a devolve com `GetClipProperty("Type") ==
    "Timeline"`, e `MoveClips({ela}, pasta)` a leva para outra pasta. Ela continua no projeto
    (`GetTimelineByIndex`) e aceita `SetName`. É o "Backup" do Atualizar.
- ⚠️ **`Timeline:GetUniqueId()` pela PONTE JS não identifica sozinho** (2026-09-28, 19.0.0b.59, Win11,
  sessão do autor). Com "…v02 2" escolhida numa lista montada por `GetTimelineByIndex` + `GetUniqueId`,
  o Comparar e o Atualizar exportaram e atualizaram outra timeline ("PRODA_CORTE.02.Exported.01", a 1ª
  da lista), e a marca de "aberta agora" (id do `GetCurrentTimeline`) caiu na timeline errada. Pelo
  `fuscript`, logo depois, os ids eram todos distintos. **`hipotese`**: pela ponte, as duas devolviam o
  mesmo id naquele momento. A causa não foi vista, só o efeito. A casca do De Lá Pra Cá agora registra no log
  quando vê ids repetidos (`timelines com o MESMO id`). **Regra:** achar a timeline pelo PAR id + nome,
  depois pelo nome (único no projeto), e só então pelo id, se for único. Conferir o nome da timeline
  exportada antes de seguir.
- ⚠️ **Abrir a timeline para exportar troca a que o colorista está vendo.** A casca faz `SetCurrentTimeline`
  antes do `Timeline:Export` (se o Export EXIGE isso não foi medido: `pendente`), inclusive quando a intenção
  é só LER (o Comparar do De Lá Pra Cá). Guardar `GetCurrentTimeline()` antes e voltar a ela depois (revisão
  de código 2026-09-28; casca `exportarTrabalho`). Conferido só em teste com Resolve de mentira.
- ⭐ **Andamento no painel enquanto a API prende a casca** (2026-09-28, 19.0.0b.59, Win11, Electron 8 da
  ponte; conferido pelo autor na PRODA). Cada chamada à API é síncrona e prende o processo principal do
  Electron da casca: um `ImportTimelineFromFile` leva ~7 s, e inserir 27 planos + backup + Sinais ~9 s.
  A PÁGINA do painel continua viva nesse tempo: um `setInterval` no painel seguiu contando os segundos
  durante a importação. O desenho que funcionou foi este:
  - antes de cada chamada longa, `event.sender.send("dlpc:andamento", {texto})`, seguido de
    `await new Promise(setImmediate)`;
  - no painel, "sub-etapa · N s", com o relógio contando desde a ÚLTIMA notícia.

  O autor: "sem a sensação de travado". Código em `_DeLaPraCa/plugins/resolve/casca/main.js::avisador`.
  No Mac, `pendente`.

### 🆕 Resolve 21.1.0.14 no macOS 15.6.1 — o Atualizar pela API Python (MCP do Resolve), medido 2026-10-01

Caso `03 CASOS/ATUALIZAR/U03` (AAF v01 → v02 da PRODA), DRTs do nosso writer gerados no Mac. Eixo: **versão** (21) E
**sistema** (Mac) ao mesmo tempo — o que mudou em relação ao 19 do Windows não separa os dois.
- ✅ `ImportTimelineFromFile(drt, {})` **devolve a Timeline** (sem a exceção da ponte JS do 19), em 0,7–0,8 s; o nome é
  o do ARQUIVO, como no Windows; cai na pasta corrente. Contagem por trilha = a prevista pelo serviço (17 trilhas).
- ✅ `Timeline.Export(arq, resolve.EXPORT_DRT)` por script EXTERNO exporta a timeline pedida (0,16 s), zip válido
  que o `reescrever.py` lê. Constantes no 21: `EXPORT_AAF=0`, `EXPORT_DRT=1`, `EXPORT_FCP_7_XML=3` (as mesmas do 19).
  ⚠️ Só uma exportação foi medida por sessão de timeline: a armadilha de 27/09 ("exporta a que pegou") não foi
  reproduzida nem descartada.
- ✅ `GetUniqueId()` da Timeline estável entre `GetTimelineByIndex`, outra chamada e `GetCurrentTimeline` (pela
  API Python; a hipótese da ponte JS segue `hipotese`).
- ✅ **Sobrevive ao reescritor + reimportação:** `SetCDL` (LUT 17 pt exportada IDÊNTICA byte a byte antes e depois,
  e diferente do plano de controle sem correção), `SetClipColor` local e `AddMarker`.
- ⚠️ `ExportLUT` devolve `false` fora da página Color e `true` com `OpenPage("color")` (21; no 19.0.0b a constante
  `EXPORT_LUT_17PTCUBE` não existe).
- ⭐⭐ **Som direto do Avid (MXF OP-Atom, um arquivo por canal):** o Resolve agrupa os arquivos. CADA `_A0n.mxf` vira
  um item de pool de **5 canais** (`GetAudioMapping` igual nos cinco). `AppendToTimeline` com o item `_A0n` e
  `mediaType 2` põe no item da timeline o **arquivo `_A01`** com `channel_idx [n]` (`GetSourceAudioChannelMapping`)
  — o canal certo. O DRT (nosso e o nativo) aponta `_A0n` com o canal 1. Que os dois SOAM igual: `pendente` (ouvir).
  ✅ **Medido (2026-10-11, Resolve 19.0.0b Windows, laboratório A01):** DRT do De Lá Pra Cá com `_A01`/`_A02` (300/400 Hz,
  um tom por arquivo) a canal 1 → o render traz os DOIS tons, no mesmo nível da referência do Media Composer, defasagem 0:
  cada `_A0n` toca o PRÓPRIO arquivo (se fosse o canal 1 do grupo, o 400 sumiria). ⚠️ O render mistura as trilhas mono no
  bus, então a POSIÇÃO de cada canal ainda não está provada. ⚠️ O pool do DRT tem um item por `_A0n` (5 canais,
  `track_mapping` vazio); o `ImportMedia` dos três `.mxf` dá UM item "Video + Audio" de 2 canais.
- ⛔ Os objetos que o `AppendToTimeline` devolve para as trilhas 2…n desse grupo **não respondem** (`GetStart`/
  `GetDuration` = `None`), embora os itens estejam na timeline. Conferir pela TRILHA (`GetItemListInTrack` + início).
- ⛔ `AppendToTimeline` **apara em silêncio** o que não cabe antes do item vizinho (pedido 488, entrou 448). No
  Atualizar, isso era o cross-fade do editor: o reescritor tirou a transição com o plano trocado, e o plano novo
  entrou em corte seco. A casca agora avisa ("conferir"); recriar a transição pela API não existe.
- ✅ Uma transição de DRT **sobrevive à importação sem um dos vizinhos**, e o `AppendToTimeline` que encosta um
  plano no corte dela a mantém (exportada de novo, está lá). ⭐ `TimelineItem.AddTransition({type, category,
  position, alignment, duration})` existe no 21.1 (não está no changelog até o 21.0.4; não existe no 19).
- 📋 Changelog (MCP `get_whats_new`): **19.0.2** — get/set source start/end frames e TC, Electron 31.3.1 (o piso
  19.0.0b.59 é ANTERIOR: lá a API não apara e o Chrome é o 80); **20.1** — Electron 36.3.2 e a API JS de promises;
  **20.2.3** — plugins de Workflow Integration persistem entre reinícios; **21** — import de DRT com opções de link e
  conform (o `ImportOptions` da API não as expõe); **21.0.4** — import de DRT religa sozinho a clipes aninhados já
  existentes; API para a seleção da timeline e para a Timeline de um item do pool.

### 🆕 Resolve 19.0.0b.59 (Windows 11), API Python externa — armadilhas medidas em 2026-10-03
- ⛔ **`Timeline.Export(arq, EXPORT_DRT)` exporta a timeline ABERTA NA TELA, não a do objeto.** Com
  `SetCurrentTimeline(tl)` → `True` e `GetCurrentTimeline().GetName()` = a certa, o arquivo saiu com a
  timeline do gabarito que estava aberta (4 clipes em vez de 2.824) — e devolveu `True`. Trocar de
  página (`OpenPage`) não resolveu; com a timeline aberta pelo usuário, o export veio certo. Conferir
  o CONTEÚDO do arquivo exportado (contagem de clipes), nunca o retorno.
- `Timeline.GetTrackSubType` NÃO existe no 19 (devolve `None`, não chamável).
- `Timeline.AddTrack("audio", "mono"|"stereo")` existe e é rápido (99 trilhas em 8,5 s); uma timeline
  nova (`CreateEmptyTimeline`) já nasce com a A1 ESTÉREO.
- `ImportTimelineFromFile` de um FCP 7 XML com Time Remap reverso feito à mão: devolveu `None` (não
  importou), por `file://localhost/F:/…` e `file:///F:/…`. Gabarito de formato no 19 = gesto do autor
  na UI + Export.
- `ImportFusionComp` (ver `workflow-integration.md` §6) e `DeleteFusionCompByName` da única composição
  (`False`).
- Ao mudar a velocidade de um clipe de áudio VINCULADO a outros, a UI muda todos.

## 8. Tempo

- A unidade é **frame**. Timecode é `hh:mm:ss:ff`.
- ⛔ **Drop-frame não é coberto** por um `split(":")` — o separador `;` faz a conversão falhar.
- ⛔⭐ **O pior modo de falha visto:** conversão que, ao falhar, **devolve 0** — o clipe vai para o
  **início** da timeline em vez de levantar erro. Falha silenciosa e plausível.
- Para deltas de TC entre câmeras: **embrulhar na meia-noite** (delta > 12 h vira o negativo
  equivalente) e **clampar** desvios absurdos, com aviso. Ver
  [`../../transversal/tempo-e-timecode.md`](../../transversal/tempo-e-timecode.md).

---

## 9. ⛔ O que esta referência NÃO cobre

| buraco | estado |
|---|---|
| **mover um clipe já colocado na timeline** | `pendente` — nenhum produto lido faz; **buraco de mapa, não ausência confirmada** |
| efeitos e parâmetros | não mapeado |
| marcadores | não mapeado |
| render / entrega | não mapeado (`AddRenderJob` visto de longe) |
| color / nós | fora de escopo até agora |
| **`endFrame` inclusivo ou exclusivo** | `pendente` — os dois produtos discordam (§1) |

### Composição Fusion de um clipe pela API — Resolve 21.1 (macOS), 2026-10-03
- ⚠️ **No 19 é diferente** (medido 2026-10-03, ver `workflow-integration.md` §6): com composição no clipe o
  import devolve verdadeiro e NÃO muda nada; sem composição, cria e religa o MediaIn. Conferir sempre
  pelo Export de volta.
- `TimelineItem.ImportFusionComp(arquivo.comp)` **SUBSTITUI a composição ATIVA** do clipe (não cria
  outra, apesar da doc): para não perder a do usuário, `AddFusionComp()` + `LoadFusionCompByName(nova)`
  e só então importar. `ExportFusionComp(arq, índice)` grava o `.comp` em texto (formato Lua).
- Na composição de clipe, o quadro 0 = o 1º quadro do clipe; o `MediaIn` começa em −(entrada na fonte).
- ⚠️ `SetCurrentTimecode` fora da timeline não falha: a agulha fica onde estava e
  `ExportCurrentFrameAsStill` grava preto/outro quadro. Conferir `GetStartTimecode` (uma timeline do
  usuário pode começar em 00:00:00:00).
- ⭐ **Montar a composição SEM `.comp` e sem molde** (medido 2026-10-03, Resolve 21.1 Mac):
  `comp = item.AddFusionComp()` (+ `LoadFusionCompByName` da nova) já vem com `MediaIn1` → `MediaOut1`
  do próprio clipe; `comp.AddTool("PolylineMask", -32768, -32768)` cria o Polygon; `tool.LoadSettings(
  arquivo.setting)` aceita um `.setting` em texto (`{ Tools = ordered() { Polygon1 = PolylineMask {
  Inputs = { Polyline = Input { Value = Polyline {…} }, … } } } }`) e o contorno entra inteiro;
  `mi.ConnectInput("EffectMask", poly)`, `blur.ConnectInput("Input", mi)` ligam os nós. Dispensa o
  ciclo Export → editar texto → `ImportFusionComp`.
- ⚠️ O `PolylineMask` criado por `AddTool` nasce com **`MaskWidth/Height` = 320×240** (o feito à mão na
  página Fusion vem com o tamanho do quadro e `UseFrameFormatSettings = 1`). Como `SoftEdge` é fração da
  largura, fixar `MaskWidth/Height` = tamanho da fonte e `UseFrameFormatSettings = 0` no `.setting`.
- Ponto `Linear = true` faz o Fusion RECALCULAR as alças do trecho (⅓ do segmento): as alças gravadas
  ali são ignoradas — o `.comp` exportado mostra outros números, e está certo.
- `SetInput` no meio de um script + `ExportCurrentFrameAsStill` (página Color, 0,5 s entre um e outro)
  grava o quadro JÁ com o valor novo: a varredura de 7 valores deu 7 imagens distintas e monótonas.
- ⚠️ `SetCurrentTimecode("01:00:00:20")` numa timeline que começa em 01:00:00:00 também **não pegou**
  (a agulha ficou em 01:00:10:22; o "01:00:02:12" logo depois pegou). Causa não achada: sempre ler
  `GetCurrentTimecode()` antes de exportar o still.
- ⚠️ E mesmo com a agulha no lugar, numa varredura em lote (`SetCurrentTimecode` → `ExportCurrentFrameAsStill`
  sem pausa, ~110 por chamada) **1 de 230** stills saiu com o quadro do ponto ANTERIOR (21.1, macOS,
  2026-10-04: o 65-1-7 gravou o interfone; refeito com 1 s de pausa, o quadro certo, 0,12 → ok). O
  conferidor deve refazer, com pausa, todo ponto abaixo do limiar antes de acusar o plano.
- ⭐ **Compound Clip pela API** (21.1.0.14, macOS, 2026-10-04): `Timeline.CreateCompoundClip([itens],
  {"name": …})` junta os itens (o compound fica na trilha mais BAIXA da seleção; as de cima esvaziam no
  trecho) e devolve o TimelineItem; o `MediaPoolItem` dele tem `Type` = `"Compound"`. ⛔ A API **não
  alcança** o que está DENTRO: `MediaPoolItem.GetTimeline()` do compound devolve None — composição do
  Fusion num clipe de dentro não se monta depois. ✅ Mas a composição montada ANTES sobrevive ao
  `CreateCompoundClip` (still antes × depois: correlação 1,0; e o interfone do PRODB, máscara + Basic
  3D, 0,96 contra a referência dentro do compound). Por isso o De Lá Pra Cá importa o nest aberto, monta o
  Fusion e só então junta (`drp/compostos.py`, casca `aplicarCompostos`). No **19** (Electron 8):
  `pendente`. No 19 pelo scripting EXTERNO em Python (2026-10-09, 19.0.0b.59, Win11): `CreateCompoundClip`
  juntou o nest C87_COMP_INTERFONE_2 (2 clipes, o de cima com a composição já montada) e o insert seguiu a
  placa a ≤ 2 px nos 37 quadros contra a referência. `AppendToTimeline` de um compound do pool com `startFrame/endFrame` usa o compound aparado
  (`In` = quadros dentro dele).
- Pitch / Yaw do Inspector (Transform): slots 8 (`0x2d`) e 9 (`0x2e`) do filtro Transform, double = o
  valor da API — **confirmado 2026-10-03** (DRT gerado com eles, importado, `GetProperty` devolve o valor).
- ⭐ **O que Pitch/Yaw fazem** (medido pela homografia, Resolve 21.1 Mac, 2026-10-03): perspectiva PURA
  no quadro normalizado do clipe, w = 1 + Yaw·u − Pitch·v (u, v ∈ [−1, 1] a partir do centro do clipe),
  aplicada ANTES do Zoom/Pan (com Zoom 0,5 o termo em px do quadro dobra; o centro acompanha o Pan; a
  rotação não muda o centro). Não há encurtamento nem cisalhamento → não reproduzem uma rotação 3D.
- ⚠️ **Com composição do Fusion no clipe, o centro da perspectiva do Pitch/Yaw vira o centro do
  QUADRO** (medido: insert com Pan 503/Tilt 96 → centro em 1435×812 num quadro de 2880×1620; sem a
  composição, o mesmo valor gira no centro do clipe, 1943×714). A intensidade continua a do clipe.
- **CornerPositioner** pela API: `AddTool("CornerPositioner")` + `LoadSettings` com `TopLeft/TopRight/
  BottomLeft/BottomRight = Input { Value = { x, y } }` (0–1, origem embaixo à esquerda, aceita fora de
  0–1); `ConnectInput("Input", anterior)`. Reproduziu o Basic 3D do Premiere a 0,9993.
- ⚠️ O Python do MCP do Resolve (`run_script_unsafe`, Python 3.14 próprio) abre arquivo com
  encoding **ASCII** por padrão: um JSON com acento dá `UnicodeDecodeError` → sempre
  `open(…, encoding="utf-8")` (medido 2026-10-03).
- ⚠️ O Python do MCP do Resolve guarda a lista de arquivos dos pacotes: módulo renomeado/criado depois
  do 1º import dá `ModuleNotFoundError` até `importlib.invalidate_caches()`.
- ⚠️ `SetCurrentTimecode` logo depois de criar composições do Fusion devolveu `True` e NÃO moveu a
  agulha (2 vezes); repetir até `GetCurrentTimecode()` bater.

## ⛔ Bypass de efeitos no monitor — a API não lê; o export obedece (2026-10-08, Studio 21.1, macOS)

- **"Bypass Color Grades and Fusion Effects"** (o ícone riscado no canto do monitor, vermelho quando ligado;
  Shift+D; menu Playback) desliga as composições do Fusion **no monitor E no `ExportCurrentFrameAsStill`**:
  medido com a composição do insert do PRODB (máscara + CornerPositioner) e com um Blur de 80 px
  montado por script — o JPEG/PNG exportado saiu idêntico byte a byte ao sem composição. O autor achou que
  o código tinha regredido ("perdemos o crop"); uma conferência pela imagem condenaria o plano certo.
- **Sem leitura pela API** (`search_scripting_api "bypass"`: nada; também não está nas preferências em
  disco — `config.user.xml`, `UI.preset`). `inferido`: estado da sessão de reprodução.
- **Prova pela imagem** (De Lá Pra Cá, `casca/main.js::efeitosDesligadosNoMonitor`): num clipe com UMA
  composição, exportar o quadro, `AddFusionComp()` + `LoadFusionCompByName(vazia)`, exportar de novo,
  devolver (`LoadFusionCompByName(nossa)`, `DeleteFusionCompByName(vazia)`). Iguais = bypass ligado;
  desligado, diferem (medido nos dois estados, mesmo clipe, Edit e Color). Até 3 clipes: um que muda já
  diz "desligado" (um clipe coberto por outra trilha também sairia igual).
- ⚠️ Alterar por script uma composição que já existe (`GetFusionCompByIndex` → `SetInput`/PassThrough)
  foi tentado só com o bypass LIGADO (nada mudou, como esperado): se reflete no export com ele desligado é
  `pendente`. A prova acima troca a composição ATIVA, que é o caminho medido nos dois estados.
- ✅ **Resolve 19: a prova funciona** (`confirmado` 2026-10-09, Studio 19.0.0b.59, Win11, a lógica da casca
  portada para o scripting externo em Python, PRODB `…ROLO03_COM_REF`, referência desligada, página Color):
  bypass desligado → o 1º clipe já difere ("desligado"); Shift+D → os 3 clipes provados saem iguais ("LIGADO");
  Shift+D de novo → "desligado". Nos três estados as composições voltaram a 1 por clipe (a vazia saiu).
  O Shift+D foi mandado à janela do Resolve por `WScript.Shell.AppActivate` + `SendKeys("+d")` com a página
  Color aberta — um jeito de ligar o bypass sem o autor (só enviar se o `AppActivate` devolver verdadeiro).

## 🆕 Marcador pela API e quadro pela API (2026-10-04, De Lá Pra Cá — conferência pela referência)

- `Timeline.AddMarker(frameId, cor, nome, nota, duração, customData)`: **não tem palavra-chave**
  (o DRT tem — `drt-drp/dados/marcadores-e-cores.json`). Quem filtra pela palavra "DLPC" não acha o
  marcador posto pela API: o De Lá Pra Cá põe "DLPC" no NOME e usa o `customData`
  (`dlpc-conferencia`) para apagar só os seus com `DeleteMarkerByCustomData` (apaga o PRIMEIRO que
  casa — chamar em laço). ⚠️ MEDIDO 2026-10-04 (21.1): sem marcador para apagar, o Python devolve `False`, mas a PONTE DO ELECTRON (Workflow Integration) LANÇA erro ("No marker exists with the input customData argument", errorCode 2) — tratar como "não há mais". `AddMarker` com cor "Purple", nota com `\n` e `customData`: conferido pela API. A nota do marcador vinda do DRT também guarda `\n` (conferido). ✅ No 19 pela ponte do Electron 8: conferido pelo autor (2026-10-04, ver abaixo).
- `Project.ExportCurrentFrameAsStill(caminho)` só exporta na página **Color** (medido 2026-10-03), e
  o `.jpg` vale (≈ 2 MB contra 14 MB do PNG a 2880×1620). Logo depois de trocar de página, o 1º
  `SetCurrentTimecode` às vezes não pega: conferir com `GetCurrentTimecode` e repetir (medido 2026-10-04).
- ⚠️ VISTO 2026-10-04 (Resolve 19.0.0b.59, Windows, ponte do Electron 8): `OpenPage("edit")` vindo da
  Color e, em seguida, `SetCurrentTimecode(início)` → o MONITOR mostra o quadro novo, mas a RÉGUA da
  timeline fica no último ponto da Color (01:21:46:06 × 00:00:00:00); qualquer mexida na timeline os
  junta. O `GetCurrentTimecode` não denuncia (ele já devolve o novo). Saída usada na casca do De Lá Pra
  Cá: esperar ~0,4 s depois do `OpenPage` e mexer — outro TC, depois o início. ⏳ ver no gesto.
- No 19, pela conferência do PRODB (1.144 pontos, todos ≥ 0,917): `ExportCurrentFrameAsStill` .jpg e
  `SetCurrentTimecode` com conferência funcionam pela ponte do Electron 8. ✅ `AddMarker` Purple +
  `customData` e `DeleteMarkerByCustomData` pela ponte do 19: conferidos pelo autor no gesto
  (2026-10-04 — clipe desligado → marcador Purple; religado e conferido de novo → o marcador sumiu, sem erro).

## Medido no estudo de taxas (2026-10-05, Resolve Studio 19.0.0b.59, Windows) — ver `transversal/taxas-de-quadro.md`

- `Timeline.SetSetting("timelineFrameRate", "23.976" | "29.97" | "59.94" | "47.952")` → **False**, calado (as
  inteiras passam depois de `SetSetting("useCustomSettings", "1")`). Fracionária: `Project.SetSetting` num
  projeto novo, antes de importar mídia.
- `AppendToTimeline({startFrame})`: `startFrame` é quadro do ARQUIVO, na taxa dele; o clipe começa exatamente ali.
- `CreateCompoundClip(itens, {"name": …})` funciona; o compound vai ao pool com `Type` "Compound" e a `FPS` da
  timeline onde nasceu. Uma timeline aparece no pool como `Type` "Timeline" e pode ser posta noutra.
- ⛔ Render só de áudio (`ExportVideo: False`) não gera arquivo, e o `ExportVideo: True` seguinte sai sem vídeo
  — `LoadRenderPreset` antes zera. `SetCurrentRenderFormatAndCodec("mov", "PJPEG")` + `MarkIn/MarkOut`
  (quadros absolutos da timeline) renderiza um trecho exato.
- Ajustes do projeto: `timelineFrameRateMismatchBehavior` (`resolve`), `imageRetimeInterpolation` (`nearest`),
  `timelinePlaybackFrameRate`, `timelineDropFrameTimecode`.

## 🆕 Laboratório de Mídia, caso B01 — Resolve Studio 21.1.0.14, macOS 15.6.1, 2026-10-06

Mídia sintética que se identifica (código de barras do quadro e do TC, tom por canal, claque por segundo), em 6
perfis gerados pelo ffmpeg; operado pelo MCP do Resolve (`laboratorio-de-midia/lab/bancadas/resolve.py`) e
conferido pela leitura dos stills e dos renders (`lab/bancadas/conferir.py`). Resultado completo:
`laboratorio-de-midia/resultados/B01_FORMATOS/RESOLVE.md`.

- ✅ `MediaPool.ImportMedia([caminhos])` dos 8 arquivos; o pool lê `Start TC`, `Frames`, `FPS`, `Resolution` e
  `Audio Ch` certos em mp4 H.264/AAC, mov ProRes, MXF OP1a DNxHD, **XDCAM HD 50 (`Video Codec` = "XDCAM MPEG2",
  8 canais)**, OP-Atom e WAV BWF (o `Start TC` do WAV vem do `time_reference`). AAC aparece com `Audio Bit Depth` 32.
- ✅ **Quadro exato:** 15 stills (página Color, agulha conferida por `GetCurrentTimecode`) e 5 renders ProRes:
  o quadro N da timeline é o quadro N do arquivo, com o TC certo — inclusive no MPEG-2 long-GOP do XDCAM.
- ⛔ **XDCAM de 8 canais mono → 8 trilhas, e o render MISTURA o 1 e o 2 nos dois lados.** `CreateTimelineFromClips`
  põe cada canal numa trilha (o `GetTrackSubType` diz `stereo`, com um item de `channel_idx [n]` mono dentro: o
  mono do 21 toca nos dois lados) → no render L = R = canal 1 + canal 2. ✅ **Conserto medido:**
  `MediaPoolItem.SetAudioMapping(json)` com `track_mapping {"1": {"channel_idx": [1, 2], "type": "stereo"}, …}`
  ANTES de criar a timeline → A1 vira o par e o render sai L = canal 1, R = canal 2. O mapa trocado no pool não
  mexe nas timelines já criadas (conferido: a antiga seguiu com 8 mono), e pode ser devolvido logo depois.
- ⚠️ **OP-Atom ESCRITO pelo ffmpeg não se agrupa**: `_V01` + `_A01` + `_A02` viram 3 itens no pool (um "Video",
  dois "Audio"). Contraste com o OP-Atom do AVID (§7, 2026-10-01), que o Resolve agrupa. Causa `inferido`: o ffmpeg
  grava um `material_package_umid` por arquivo (`protocolos/mxf/README.md`).
- Timeline nova nasce em **00:00:00:00** nesta instalação (`CreateTimelineFromClips` E `CreateEmptyTimeline`);
  não há ajuste de projeto para isso na API (`GetSetting` não tem o início); `Timeline.SetStartTimecode` funciona.
- ⛔ **Resolve 19.0.0b no WINDOWS (2026-10-11):** `SetCurrentRenderFormatAndCodec` devolve False (codec fica '' e o
  render sai em H.264 NVIDIA), e `SetRenderSettings` com `ExportAudio`/`AudioCodec`/`AudioBitDepth`/`AudioSampleRate`
  responde True mas deixa o trabalho com `IsExportAudio: False` — **render MUDO**. Conferir pelo `GetRenderJobList()`.
  O caminho que funciona: `LoadRenderPreset` de um preset de fábrica com áudio (ex.: "FCP - Final Cut Pro 7" = QuickTime
  RGB 10-bit sem compressão + PCM) → `SetCurrentRenderMode(1)` (o do FCP 7 é clipe a clipe + XML) → `SetRenderSettings`
  só com `SelectAllFrames`/`TargetDir`/`CustomName`. Todos os presets de fábrica vêm com `IsExportAudio: True`.
  Código: laboratorio-de-midia `lab/bancadas/avid_resolve.py`.
- Render: `SetCurrentRenderFormatAndCodec("mov", "ProRes422")` + `SetRenderSettings({…, "AudioCodec": "lpcm",
  "AudioBitDepth": 24, "AudioSampleRate": 48000})` + `AddRenderJob` + `StartRendering([ids], isInteractiveMode=False)`
  → ~1,2–1,8 s por timeline de 10 s; `GetRenderJobStatus` dá `Complete`. A primeira claque do render começa 0,4–0,9 ms
  depois do quadro 0 (as seguintes exatas) — `inferido`: borda do clipe.
- Print da tela pelo `screencapture -x` (o terminal tem permissão de gravação de tela nesta máquina) depois de
  `osascript -e 'tell application "DaVinci Resolve" to activate'`.

### 🆕 Render ProRes Proxy clipe a clipe (proxy para o Premiere) — Studio 21.1, macOS, 2026-11-07

`confirmado`, 7 clipes reais (PRODE ProRes 2 e 4 canais, mp4 AAC, BRAW 4K) e 5 sintéticos (um tom por canal;
UHD; DCI). Ciclo Assist, plano `docs/plano/2026-11-07-premiere-proxy-e-merged.md` §P0.
- ⛔ **Só pela API sai errado**: `SetCurrentRenderMode(0)` + `SetCurrentRenderFormatAndCodec("mov","ProRes422P")`
  + `SetRenderSettings` dá o nome com sufixo (`20240531_C0021_00030000.mov`) e **4 pistas mono viram 2 canais**
  (o original de 4 perde 2 — e o Premiere recusa o proxy por isso). `RenderSettings` não tem nome-da-origem nem
  nº de canais.
- ✅ **Pelo preset** (a dança do OP-Atom: `Project.DeleteRenderPreset` → `resolve.ImportRenderPreset` →
  `LoadRenderPreset("CICLO-OP-ATOM")` → conferir mxf/modo 0 → `SetCurrentRenderFormatAndCodec("mov",
  "ProRes422P")` → `SetRenderSettings({TargetDir, FormatWidth, FormatHeight, SelectAllFrames})`): nome
  do clipe, TC, `reel_name`, nº de quadros e taxa iguais aos do original; **um canal por pista mono, na
  ordem** (tom por canal: 1,0 na diagonal, 0,0 fora — sem a mistura L=R). ⚠️ O estéreo (1 pista de 2
  canais) sai como **2 pistas mono** — o Premiere aceita como proxy. ~6 s para 3 clipes de 1080 (2,3 min).
- ⛔ **Proporção diferente de 16:9 exige a timeline do tamanho do proxy.** DCI 4096×2160 renderizado a
  1920×1080 sai com tarja (letterbox); a 2048×1080 numa timeline de 1920×1080, tarja nos quatro lados.
  `Timeline.SetSetting("useCustomSettings","1")` + `timelineResolutionWidth/Height` = `2048`/`1080` → quadro
  inteiro. Regra: um grupo de render por proporção, largura = altura do proxy × proporção (par).
- BRAW: o pool diz `4096x2160` (a área de imagem; o ffprobe dá o contêiner, 4128×2176).

### 🆕 Render OP-Atom para o Avid: preset NOSSO injetado + codec pela API — Studio 19.1.4.11, Windows 11, 2026-10-31

> ✅ 🆕 **macOS, Studio 21.1.0.14 (2026-11-12):** o mesmo `cicloassist/resolve_opatom.converter` sem mudança — 3 ProRes 1080p 23,976 (38–47 s) → 9 MXF (V + 2 A cada) em 15,7 s, `DNxHD1080p36`, TCs certos, numa pasta nova de `/Volumes/SSD/Avid MediaFiles/MXF`; o MC 2025.12 indexou em 0,6 s e os 3 masters entraram online (`importar_opatom`). `confirmado` (1×). Fechar pela API: 5,6 s.


> ⛔ **CORRIGE no mesmo dia (tarde): o preset pode NÃO ser aplicado, calado.** Num projeto em que o `CICLO-OP-ATOM` já estava importado, `ImportRenderPreset` devolveu False (o nome já existe) e `LoadRenderPreset("CICLO-OP-ATOM")` devolveu **True deixando tudo como estava** (dpx/RGB10, modo 1; o job diz `PresetName: Custom`). Forçar `SetCurrentRenderMode(0)` + `SetCurrentRenderFormatAndCodec("mxf","DNxHD1080p36")` dá OP-Atom de verdade, mas SEM o resto do preset: o arquivo sai com o nome do quadro do TC (`00090250.mxf`) e áudio 16 bits. O MC 2024.6 caiu (`CompressionManager.c` line 11276) ao abrir a timeline sincronizada que usava esse master — ✅ **causa isolada no mesmo dia: NÃO é o arquivo do Resolve** (igual ao B01, que toca), é o mob nascido de um `ImportFile` com o MXF ainda não indexado (`../avid-panel-sdk/windows.md`, OP-Atom feito fora). ⇒ conferir `GetCurrentRenderFormatAndCodec()` depois do load; True não prova nada.
>
> ✅ **O conserto, medido no mesmo dia (noite, Studio 19.1.4.11, projeto novo `CICLO ENSAIO M06`):** `DeleteRenderPreset("CICLO-OP-ATOM")` (True) → `ImportRenderPreset(arq)` (True) → `LoadRenderPreset` → `GetCurrentRenderFormatAndCodec()` = `mxf / DNxHD1080p145` e modo 0 (os do PRESET) → `SetCurrentRenderFormatAndCodec("mxf", "DNxHD1080p36")`. O trabalho: `OutputFilename M06_CAM1_T01_MOV-PRORES.mxf and more`, Individual clips, áudio 24 bits (`PresetName: Custom` só porque o codec mudou). 4 ProRes de 18–22 s → 12 MXF em 6 s, nome limpo, TC de cada tomada. ⇒ **Sempre apagar e reinjetar o preset; e conferir formato+modo antes do AddRenderJob — divergiu, PARAR (nunca forçar o codec na mão: foi assim que nasceu o `00090250`).**

> ✅ **Reconfirmado em produto (2026-11-01, Studio 19.1.4, Win 11), DUAS rodadas no mesmo projeto `CICLO TESTE OP3`** — `cicloassist/resolve_opatom.py` (Ciclo Assist, ferramenta `converter_para_opatom`). A 2ª rodada é o caso de 31/10 (preset JÁ importado): `Delete` → `Import` (True) → `Load` → `mxf / DNxHD1080p145`, modo 0 → codec 36. 4 ProRes → 12 MXF em 5,3–5,5 s; TCs = o gabarito do laboratório (`10:00:05:00`, `10:00:32:00`, `10:01:00:00`, `10:01:32:00`); som `pcm_s24le` 24 bits; `IsExportAudio: True`. Média já no Media Pool é reaproveitada pela propriedade `File Path` (4 de 4, sem duplicar). A fila de render do usuário não precisa ser apagada: `StartRendering(job)` só do nosso, e `DeleteRenderJob(job)` no fim. `confirmado`.
> ⛔ **O MXF de SOM que o Resolve grava tem um stream `data` ANTES do áudio** (ffprobe: `0 data · 1 pcm_s24le · 2 data`; o de vídeo: `0 dnxhd · 1 data · 2 data`). Quem lê `streams[0]` conta os arquivos de som como zero e a conferência de bits fica muda — medido no primeiro rascunho do Ciclo Assist. Escolher o stream pelo `codec_type`. O `material_package_name` é o nome do clipe SEM extensão.
> ✅ **Fechar o Resolve pela API** (2026-11-01, Studio 19.1.4, Win11): `pm.SaveProject()` (True) → `resolve.Quit()` → o processo some em ~12 s, sem diálogo. `confirmado` (3×; 2 pelo `cicloassist.resolve.fechar`, 12,1 s).
> ⛔ **E SEM projeto aberto (só o Project Manager na tela) o `Quit()` não fecha** (2026-11-19, Studio 19.1.4, Win11): depois de `DeleteProject` com o "Untitled Project" corrente, `Quit()` voltou e o processo ficou 60 s+ com a janela "Project Manager" respondendo; o `cicloassist.resolve.fechar` esperou 90 s e desistiu. Encerrado à força (sem projeto, nada a perder). `confirmado` 2×. Causa `pendente`: abrir um projeto antes do `Quit()` não foi testado.
> ⛔ **A porta de scripts 1144 cai em ~1,3 s depois do `Quit`, com o `Resolve.exe` ainda vivo por ~12 s** (medido 2026-11-01, Studio 19.1.4, Win11). Quem toma "porta fechada" por "Resolve fechado" segue o fluxo com ele saindo. Esperar o PROCESSO (`tasklist /FI "IMAGENAME eq Resolve.exe"`). `confirmado` (1×). macOS (`pgrep -x Resolve`): `pendente`.
Ciclo Assist, `spikes/resolve_para_opatom.py` e o preset `resolve/presets/CICLO-OP-ATOM.xml` (F3 do plano
`2026-10-31-o-assist-operador.md`). Entrada: `B01_MOV-PRORES.mov` do laboratório (10 s, 1080p25, TC 01:00:00:00).

⭐⭐ **A regra (autor):** parâmetro pela API quando der; o que a API não alcança, por um preset NOSSO que se sabe que
funciona, injetado (`resolve.ImportRenderPreset`). Nunca depender de um preset do usuário (ele muda) nem do de fábrica.

| caminho | resultado |
|---|---|
| ⛔ preset de fábrica `AVID AAF` | OP-Atom com o mesmo material UMID + AAF, MAS nome `V1-0001_<clipe>` e o áudio junto (o autor: "não é bom") |
| pela API (`SetCurrentRenderMode(0)` + `SetCurrentRenderFormatAndCodec("mxf", …)` + `ExportAudio: False`) | ✅ formato, codec e só-vídeo; ⛔ **o nome sai `<clipe>00090000`** (o quadro de início) e **nenhuma chave tira**: `UniqueFilenameStyle` 0/1/2/−1 aceito e ignorado |
| ⭐ preset nosso injetado (`ImportRenderPreset(arq)` → `LoadRenderPreset("CICLO-OP-ATOM")`) | ✅ nome limpo `<clipe>.mxf`, modo clipe a clipe, áudio do clipe junto ("Same as source"); o NOME do preset é o do arquivo |
| ⭐ preset nosso + `SetCurrentRenderFormatAndCodec("mxf", "DNxHD1080p36" \| "DNxHRLB")` | ✅ troca o codec E mantém o nome limpo |

- ✅ No 19.1.4 `SetCurrentRenderFormatAndCodec` FUNCIONA (no 19.0.0b, acima, devolvia False). Formato `mxf` = "MXF
  OP-Atom" (`mxf_op1a` é o OP1a); `GetRenderCodecs("mxf")` lista DNxHD/DNxHR/Avid 1:1/XDCAM/JPEG 2000.
- ✅ Saída: OP-Atom (`operational_pattern_ul` `…0d010201.10…`), DNxHD, TC preservado; DNxHD 1080p145 = 145 MB/10 s.
  O preset de fábrica também deu o MESMO `material_package_umid` entre vídeo e `_A0n` (o contrário do ffmpeg).
- ⚠️ `ExportRenderPreset(nome, caminho)` cria uma **PASTA** com o nome do caminho e grava `<nome>.xml` dentro.
- ⚠️ O XML do preset guarda `RecordTargetDir` (a última pasta usada) e `RecordAudioEnabled`; a cópia nossa vai sem
  pasta (o áudio LIGADO, `RecordAudioNumChannels=-1`). Os nomes `RecordClipUniqueName=false` / `UsePrefixAndSuffixFromSrc=1` são o que
  deixa o nome limpo (`inferido`: não testado campo a campo).
- ⚠️ Abertura: porta 1144 aos 19 s e o `scriptapp` ainda `None`; ~20 s depois conectou. **Porta aberta ≠ API pronta.**
- ⭐⭐ **O CLIPE DE CÂMERA vai com o áudio dele, mesmo número de canais** (autor: *"audio channel: same as source"*):
  `RecordAudioNumChannels=-1` no preset = "Same as source". ✅ MEDIDO: mov 2 ch → `_A01`–`_A02`; mov de 1 trilha com 4
  canais E mov de 4 trilhas mono → `_A01`–`_A04`; mov de 8 mono → `_A01`–`_A08`; cada `_A0n` = o canal n da origem
  (correlação **1,00** na diagonal, 0,14 fora — sem a mistura L=R do render mov, acima); UM material UMID por clipe,
  distinto entre clipes. ⛔ O que NÃO passa pelo Resolve é o **WAV do som direto**: ele entra no MC por AMA link e o
  MC consolida.

### 🆕 Caso B02 (taxas e drop-frame) — Resolve Studio 21.1.0.14, macOS 15.6.1, 2026-10-06

8 taxas (23,976 · 24 · 25 · 29,97 ND · **29,97 DF** · 30 · 50 · 59,94), mov ProRes e MXF OP1a DNxHR HQ, 10 s
começando em 01:00:59:15 (o DF em ;15: atravessa o minuto que pula ;00 e ;01). Um projeto por taxa.
- ✅ `Project.SetSetting("timelineFrameRate", "23.976" | "29.97" | "59.94" …)` e
  `SetSetting("timelineDropFrameTimecode", "1")` num projeto NOVO, antes de importar: aceitos e lidos de volta
  (`GetSetting` devolve 29.97 e "1").
- ✅ O pool lê `Drop frame` = "1" e `Start TC` = "01:00:59;15" (com `;`) do mov e do MXF DF; "0" nos ND.
- ✅ `Timeline.SetStartTimecode("01:00:59;15")` aceita o rótulo DF; `SetCurrentTimecode("01:01:00;02")` cai no
  quadro 15 do clipe (o primeiro depois do pulo) e `GetCurrentTimecode` devolve com `;`. Comparar sempre com o
  `;` trocado por `:`. Nas 8 taxas, 80 stills por TC: quadro exato (o código de barras do quadro e do rótulo).
- ✅ O render mov herda o TC da timeline com o `;` (ffprobe: `01:00:59;15`), 300 quadros, e as claques do
  primeiro quadro de cada segundo de TC caem nos instantes previstos (0,5005 / 1,4348 / 2,4358 s).
Resultado: `laboratorio-de-midia/resultados/B02_TAXAS/RESOLVE.md`. Não coberto: mismatch de taxa, 59,94 DF.

### 🆕 Casos B03–B06 — Resolve Studio 21.1.0.14, macOS 15.6.1, 2026-10-06 (Laboratório de Mídia)

Resultados completos em `laboratorio-de-midia/resultados/B0{3,4,5,6}_*/RESOLVE.md`.
- ⭐ **API de script EXTERNA no Mac, sem o MCP:** `RESOLVE_SCRIPT_API` = `/Library/Application Support/Blackmagic
  Design/DaVinci Resolve/Developer/Scripting`, `RESOLVE_SCRIPT_LIB` = `…/DaVinci Resolve.app/Contents/Libraries/Fusion/
  fusionscript.so`, `sys.path` + `Modules`, `DaVinciResolveScript.scriptapp("Resolve")` — conecta em ~0 s do Python
  3.9 do sistema, sem o limite de 60 s do MCP. Quando o MCP ficou preso no processo de um Resolve que caiu, este
  caminho funcionou com o Resolve reaberto (o MCP voltou só com `/mcp` → reconectar). Código: `lab/bancadas/resolve.py`
  `conectar()` (com os caminhos do Windows, `pendente`).
- **Layouts de áudio (B03), o mapa do pool:** mov polifônico de 2 canais = 1 estéreo; de 4/5/8/16 = **um mono por
  trilha, ignorando o layout** ("4.0"/"5.0"/"7.1" do ffmpeg); WAV de 4/5/16 = 1 trilha `adaptive_N`, **de 8 = `7.1`**
  (o layout do WAV é usado). ⛔ **Duas trilhas mono saem L = R (misturadas) no render** — a mesma perda do XDCAM; conserto
  `SetAudioMapping` com o par estéreo (B01). A mistura de 16 tons a −20 dBFS satura (sem limitador no bus).
- ⛔ **Timeline só de áudio não renderiza pela API:** `AddRenderJob` = `None` com vídeo; com `ExportVideo: False` o
  trabalho fica "Ready" e não gera arquivo; `SetCurrentRenderFormatAndCodec("wav", "")` recusado,
  `GetRenderCodecs("wav")` = {}. (Confirma o achado do 19 no Windows, 2026-10-05.)
- ⭐ **Meia-noite (B04):** o Resolve NÃO volta a 00 — `End TC` = `24:00:05:00`, a régua segue em 24:…, e a agulha só
  pega `SetCurrentTimecode("24:00:04:24")` (o `00:00:04:24` não pega); no DF, `24:00:00;00`. Converter TC do Resolve
  para quadros exige aceitar hora ≥ 24. O quadro mostrado é o certo.
- **Rasters (B05):** `useCustomSettings` + `timelineResolutionWidth/Height` dá a timeline nativa (inclusive 2880×1080
  para o anamórfico 1440×1080 PAR 2); na timeline do projeto, o "scale entire image to fit" encaixa exato (4K DCI →
  faixas de 34 px, 2K scope → 138, vertical → pillarbox 656–1264, anamórfico → 1920×720 desespremido). O pool lê o
  PAR do `pasp` do mov (`PAR` = "2.0").
- **Som direto (B06):** `AutoSyncAudio` com `AUDIO_SYNC_TIMECODE` liga o BWF ao vídeo (`linked_audio.offset` = 96000
  amostras = os 2,0 s certos) e acrescenta uma trilha `adaptive_4`; no render o som direto soa exatamente onde o TC
  manda (fim aos 6,005 s, esperado 6,0). ⚠️ Só os canais 1–2 do BWF de 4 chegam à mistura estéreo.
- ⛔⛔ **QUEDA do Resolve 21.1 (2×):** timeline vazia (`CreateEmptyTimeline` + `SetStartTimecode`) → `AppendToTimeline`
  com `recordFrame` → (1ª) o BWF na A1 e a câmera depois, que entrou APARADA (100 de 250 quadros) e o Resolve caiu
  logo após; (2ª, API externa) a câmera e então `AddTrack("audio", "adaptive4")` → "DaVinci Resolve quit unexpectedly"
  na hora. Não fazer `AddTrack` de trilha adaptive pela API neste estado; o caminho que funciona é o `AutoSyncAudio`.


## 🆕 2026-10-07/08 — Magic Mask, cópia de grade e API externa (Studio 21.1, macOS)
- `TimelineItem.RegenerateMagicMask()` com a página Color aberta rastreia o AI Magic Mask do clipe (~4 q/s; a chamada estoura os
  60 s do MCP mas o tracking segue). `TimelineItem.CopyGrades([alvo])` leva o nó AI Magic Mask para outro clipe (`confirmado`).
- `MediaStorage.AddClipMattesToMediaPool(item, [arquivo])` + `MediaPool.GetClipMatteList(item)`: matte do clipe, viaja no DRT.
- API externa por um Python COMUM (3.9 do sistema): `RESOLVE_SCRIPT_API`, `RESOLVE_SCRIPT_LIB` e `…/Developer/Scripting/Modules`
  no `sys.path` → `DaVinciResolveScript.scriptapp("Resolve")` (`lab/prmf_para_resolve.py::conectar`).
- `ProjectManager.DeleteProject` apagou junto a pasta do projeto em `~/Movies/CacheClip` (observado 1×, 7 projetos).
- ⛔ `comp.AddTool("Loader")` por script ABRE a janela de escolher arquivo e trava a API até alguém cancelar.
- ⛔ DRT com Magic Mask do FUSION importado sem o cache TRAVA o Resolve (`Fusion::RenderTask::ObtainRenderLock`) — banco
  `protocolos/drt-drp/magic-mask.md`. Render por script num disco cheio sai "Complete" com o arquivo cortado (sem moov).

## 🆕 Expressões do Fusion (SimpleExpression) e o metadado da mídia — 2026-10-09 (Studio 19.0.0b.59, Win11)

Origem: dica de um colega ("no Text+, botão direito → Expression → `Text(MediaIn1.Output.Metadata.TimeCode)`
mostra o TC da fonte"). O autor tentou e a tela ficou preta. Medido pelo scripting externo (`fuscript`), no
PRODB. Manual que vem instalado com o 19: é a edição do **18.6** (`Documents/DaVinci Resolve.pdf`, Fusion
Fundamentals, cap. 74 "Using SimpleExpressions"): uma linha de **Lua** ao lado do parâmetro; `Nó.Entrada.Metadata.X`
lê o metadado da IMAGEM que chega naquela entrada; `time` = quadro atual; `iif()`, `Text()`, `Point()`, `os.date`,
`os.getenv`, `comp.Filename`. O manual NÃO lista as chaves de metadado — dependem do formato (abaixo).

- ⛔ **Por que ficou preto:** o Text+ da TIMELINE (título "Fusion Title") é uma composição só `Template` →
  `MediaOut1`, **sem `MediaIn1`**; e um título não enxerga o clipe da trilha de baixo. A expressão falha e o
  título sai **preto opaco** cobrindo tudo (quadro com média 0; sem o título, o clipe aparece). `confirmado`.
- ⛔ **`Metadata.TimeCode` não existe** nas mídias medidas: MOV (iPhone/H.264 do insert) → só `Filename`,
  `ColorSpace.*`, `GammaSpace.*`; ARRIRAW `.mxf` (ALEXA, 87 chaves) → `reelName`, `clipName`, `cameraSerialNumber`,
  `lensModel`, `lensSerialNumber`, `frame_capture.exposure_index` (ISO), `.exposure_time`, `.color_temperature`,
  `.tint`, `.nd_filter_density`, `lens_config.*` (foco, focal), `camera_position.*` (pan/tilt/roll)… — nenhum TC.
  `Text(nil)` não desenha nada. (Se `TimeCode` existe em outro formato/versão: `pendente`.)
- ✅ **Dentro da composição do PRÓPRIO clipe funciona, por quadro:** `MediaIn1` → `Merge1.Background`, Text+ →
  `Merge1.Foreground`, `Merge1` → `MediaOut1`, e no `StyledText` a expressão
  `Text(MediaIn1.Output.Metadata.reelName .. "  " .. MediaIn1.Output.Metadata.clipName .. "  ISO " ..
  MediaIn1.Output.Metadata.frame_capture.exposure_index .. "  t=" .. time)` desenhou
  "A055R1X0  A055C012_240730_R1X0  ISO 800  t=1208". Tabela aninhada se lê com ponto (`frame_capture.x`).
- ⭐ **Na composição de clipe, `time` = quadro da FONTE** (desde o 1º quadro do arquivo): t = 1208 no 7º quadro de
  um clipe com `GetLeftOffset()` 1201; o comp vai de 0 ao fim do arquivo (`GlobalOut` 1788). Logo o **TC da fonte
  = Start TC do arquivo + `time`**, com o Start TC escrito como número na expressão (não vem no metadado):
  `Text(string.format("%02d:%02d:%02d:%02d", math.floor((S+time)/86400)%24, math.floor((S+time)/1440)%60,
  math.floor((S+time)/24)%60, (S+time)%24))` com S = 954850 (11:03:05:10 a 24) → "11:03:55:18", o esperado.
  `string.format`/`math` funcionam na expressão. (Alternativa sem Lua: modificador `TimeCode` com `StartOffset` = S,
  como o burn-in do De Lá Pra Cá — `pendente` dentro da composição de clipe.)
- ⭐ **A receita do colega, completa — o nó "Set Time Code"** (`Fuse.SetMetaDataTC`, vem com o Resolve 19; o
  manual do Fusion 19.1 o chama `TCMETA`, cap. 48 "Metadata Nodes", mas `AddTool("TCMETA")` dá nil — o ID que
  existe é o do `fu:GetRegList`): ele GRAVA as chaves `TimeCode` ("HH:MM:SS:FF") e `FrameRate` na imagem, a partir
  do tempo da composição + o deslocamento (`TCHours`/`TCMinutes`/`TCSeconds`/`TCFrames`; `FPS` 0 = 24). Como na
  composição de clipe `time` = quadro da fonte, deslocamento = Start TC do arquivo dá o TC da FONTE:
  `MediaIn1` → `SetTimeCode1` (11/3/5/10) → `Merge1.Background`, e no Text+ `Text(SetTimeCode1.Output.Metadata.TimeCode)`
  desenhou "11:03:55:18" (o esperado). Sem o deslocamento: "00:00:50:08" (= 1208 quadros). `confirmado`.
  Os outros do mesmo capítulo: `Fuse.SetMetaData` (Set Metadata: um par nome = valor) e `Fuse.FLS_CopyMetadata`
  (Copy Metadata: junta/substitui/limpa a tabela do Foreground no Background).
- **Chaves do ARRIRAW (ALEXA Mini, SUP 6.01.02)** no `MediaIn1` — a lista completa: `Filename`, `ColorSpace.*`,
  `GammaSpace.*`, `production`, `director`, `cinematographer`, `cameraIndex`, `cameraModel`, `cameraSerialNumber`,
  `cameraSoftwarePackageName`, `reelName`, `clipName`, `clipNumber`, `circleTake`, `lensModel`, `lensSerialNumber`,
  `lensSqueezeFactor`, `lensLimitsFocusMetric.*`, `lens_config.*`, `camera_position.*`, `frame_capture.*` (ISO,
  obturador, temperatura, tint, ND, checksum da imagem), `medium*`, `converter*`, `gamma`, `knee`, `blackGamma`,
  `saturation`, `saturationByHue.*`, `video{Gamma,Pedestal,Slope}.*`. O manual do Fusion 19.1 NÃO lista chaves
  ("Most Loaders will give the color space and file path… Much more if it exists in the image"); o jeito de ver
  é a subview Metadata do viewer (Fusion Studio) ou o dump pelo scripting (`tool.Output[t].Metadata`).
- Manuais conferidos: Fusion 19.1 Reference Manual (fev/2025, `documents.blackmagicdesign.com/UserManuals/
  Fusion19_Manual.pdf`) e Fusion 8 Scripting Guide (`…/Fusion8_Scripting_Guide.pdf`, p. 42: na SimpleExpression
  `Loader1.Output.Metadata.Filename` já é avaliado no tempo atual; Metadata da imagem só se LÊ por script — mudar
  pede Fuse). O PDF que vem instalado com o 19 é o manual do Resolve 18.6.
- Pelo scripting: `Input:SetExpression(texto)` liga a expressão (não devolve valor — `tostring()` dela quebra o
  Lua); `tool:GetInput("StyledText", t)` NÃO devolve o texto avaliado (nil/vazio): conferir pela imagem.
- Uso possível (De Lá Pra Cá): as linhas do burn-in do Premiere que hoje viram "refazer" (nome do clipe, TC da
  fonte) dariam Text+ VIVO na composição de cada clipe da trilha-fonte, montada pela casca depois do import
  (o DRT não leva composição de clipe). Não implementado.

## 🆕 Ler a timeline por fora para a conferência — medido 2026-10-19 (Resolve Studio 19.1.4.11, Windows, API externa)

De Lá Pra Cá, `resolve_externo.ler_timeline` (projeto "DLPC LAB PROTOCOLOS"):
- ⛔⛔ **`Timeline.GetIsTrackEnabled(tipo, n)` devolve `False` para TODA trilha de uma timeline que NÃO é a aberta.**
  LAB_CORTES_01: `[False, False]` fechada × `[True, False]` aberta (a V2 é a referência, desligada de verdade); B22:
  `[False]` × `[True]`. Quem lê o estado das trilhas tem de `SetCurrentTimeline` antes (e devolver a do editor depois).
  Sintoma sem isso: todo plano parece desligado e a conferência fica sem pontos. `confirmado`.
- ⚠️ **`hasattr(objeto_da_api, "QualquerNome")` é sempre `True`** (o objeto é um proxy que aceita qualquer atributo):
  não serve para saber se um método existe nesta versão — chame e trate `None`. `GetClipEnabled()` existe no 19.1.4.
- Item da timeline cujo `GetMediaPoolItem()` existe mas `GetClipProperty("File Path")` é vazio = **timeline aninhada /
  composto** (o "B22" dentro de LAB_CORTES_01.Exported.01 2): é imagem do filme, não título. `confirmado`.
- `GetProperty("ZoomX" | "Opacity" | "CropLeft"…)` respondem por fora (1.0, 100.0, 0.0). Ler uma timeline de 18 itens +
  exportar o DRT (para as transições): **0,4–0,5 s**.
- `AddTrack("video")` + `MediaPool.AppendToTimeline([{mediaPoolItem, startFrame: 0, endFrame: Frames, trackIndex: nova,
  recordFrame: GetStartFrame(), mediaType: 1}])` + `SetTrackName` + `SetTrackEnable(False)`: a referência entra no
  início, desligada, com os 240 quadros inteiros (o `endFrame` = `Frames` não perdeu quadro); `AddTrack("audio",
  "stereo")` + `mediaType: 2` põe o som numa trilha nova. **0,3 s** tudo. `DeleteTrack` desfaz. `confirmado`.

## Arrastar do Media Pool: o gesto SINTÉTICO não sai do Resolve — medido 2026-10-19 (19.1.4.11, Windows)

Pelo piloto (`SendInput`): apertar sobre a miniatura de uma timeline no Media Pool e andar **inicia o arrasto DENTRO do
Resolve** (a miniatura "B22" segue o cursor — foto no meio do gesto), mas **nada chega a outra janela**: nem à sonda
nativa (`piloto/sondas/arrasto_nativo.py`, que em 2026-10-12 recebeu os 3 formatos), nem com a sonda fora do retângulo
do Resolve (janela restaurada), nem com pausa de 1 s depois de apertar e passos de 1 px. O MESMO gesto sintético tira
uma sequência do Premiere 23.6 (ver premiere-cep/arrastar-e-selecao.md §6c). `hipotese`: o Qt do Resolve só entrega o
arrasto ao OLE com entrada física (ou com algo que o `SendInput` não reproduz); o de 2026-10-12 foi provavelmente de mão.
⇒ Teste de arrasto do Media Pool para fora = mão do autor; o piloto não serve.

## Arrastar do Media Pool para o painel (Workflow Integration) — medido 2026-10-12

Resolve Studio **19.0.0b** (Windows 11). Duas sondas, como no Premiere: o próprio painel (`/diag/arrasto`) e uma janela
NATIVA com `IDropTarget` (`piloto/sondas/arrasto_nativo.py`, pywin32), que vê o `IDataObject` inteiro.

**1. No painel (DOM do Electron): chega VAZIO** — `efeito move`, `tipos` nenhum, `arquivos 0`; a mesma assinatura do
Premiere ([premiere-cep/arrastar-e-selecao.md](../premiere-cep/arrastar-e-selecao.md) §1). ⛔ A saída do Premiere (ler a
seleção no soltar) não serve no 19: **não há `GetSelectedClips`** (`TypeError`, fora do `dir()`).
⚠️ CORRIGE em parte (2026-10-24, **19.1.4.11**): `MediaPool.GetSelectedClips` e `SetSelectedClip` EXISTEM no `dir()` do
19.1.4 (o "não existe" vale para o 19.0.0b). Não medido com clipes selecionados no pool.

**2. ⭐⭐ Na janela nativa: a CHAVE está no arrasto** (`confirmado`, 3 timelines diferentes arrastadas; `dragenter` e
`drop`, efeitos que a origem permite = 2, MOVE):

```
MediaPool/Media                  (HGLOBAL, 47 B)   "SourcePointer" + ponteiro do processo — inútil fora dele
MediaPool/FusionMedia            (HGLOBAL, 36 B)   "39476e5a-f811-441f-bb8a-cf1d03284012"  ← UUID em texto
MediaPool/FusionMediaProperties  (HGLOBAL, 1319 B) QDataStream (UTF-16BE): MEDIA_ID, o NOME, MEDIA_SRC_FRAME_RATE
                                                   (23.976), MEDIA_NUM_FRAMES (600), WIDTH/HEIGHT, MARK_OUT, áudio…
```

✅ **O UUID é o `MediaPoolItem.GetMediaId()` do item da timeline** (tipo `Timeline`) — conferido pela API; NÃO é o
`GetUniqueId()` do item nem o da `Timeline`. O nome vem junto (no Resolve o nome de timeline é único no projeto).
⇒ Do item ao objeto `Timeline`: pelo nome (`GetTimelineByIndex` + `GetName`).

**3. ⭐ A ponte para o painel: uma janela nativa que SURGE no meio do arrasto recebe o soltar** (`confirmado`): arrasto
começado com a janela fora do caminho; aos 3/4 do trajeto, `SetWindowPos(HWND_TOPMOST)` a pôs sob o cursor → `dragenter`
+ `drop` com o `MEDIA_ID`. O OLE reavalia o alvo a cada movimento. ⇒ Desenho: o painel vê o `dragenter` vazio com
`move` (só o próprio Resolve arrasta assim; o Explorer traz `Files`), pede ao serviço um alvo nativo sobre a área de
soltar; o editor solta nele; o serviço resolve o `MEDIA_ID` pela API. ⚠️ `ctypes`: o `HWND_TOPMOST` (-1) tem de ir como
`wintypes.HWND(-1)` com `argtypes` declarados — passado como `int` cru, o `SetWindowPos` não move nada, calado.

**4. ⭐ Outra via, sem código nativo: Ctrl+C no Media Pool põe o NOME da timeline como `CF_UNICODETEXT`** (+ `CF_TEXT`,
`CF_OEMTEXT`, `Ole Private Data`) — texto comum, que um Ctrl+V no painel entrega ao DOM (`inferido`: o colar no painel
não foi medido).

`pendente`: o mesmo no Resolve 21 (Mac mini) e no macOS (`NSPasteboard`, sem OLE).

⚠️ **De passagem (piloto):** o Resolve aberto como FILHO de um script Python (`subprocess.Popen`) ficou com o servidor
de scripts mudo (porta 49152 aberta, `scriptapp` → `None`, preferência `Local` ligada); fechado e aberto pelo Windows
(`Start-Process`), a API respondeu em 9 s. Uma vez só — `hipotese`; abrir o Resolve sempre destacado do script.
2ª vez (2026-10-23, 19.1.4.11): o Resolve aberto pelo AUTOR (pai já encerrado) na janela de projetos, mudo do mesmo jeito
(porta 49152 aberta, `scriptapp` nil no Python E no `fuscript -l lua`, `System.Scripting.Mode = 1` no `config.dat`);
`CloseMainWindow` + `Start-Process` → respondeu em 14 s. Então não é (só) o pai Python: a 1ª conexão depois de certas
aberturas falha — o remédio medido, duas vezes, é reabrir pelo `Start-Process`. Causa: `pendente`.


## ⏳ PENDENTE (autor, 2026-10-18): troca dinâmica de projetos — qual é o projeto "em foco"?

Por padrão o Resolve tem UM projeto aberto por vez; com a troca dinâmica de projetos habilitada nas preferências,
vários ficam carregados e o editor alterna entre eles. O app unificado mostra no topo o PROJETO em foco (decisão do
autor: o nome do projeto, com destaque discreto) e age nele — então precisa saber, por script externo, qual é.
A medir: com a troca dinâmica LIGADA e dois projetos carregados, o que o `ProjectManager.GetCurrentProject()`
devolve depois de o editor alternar pela interface (o da frente? o último aberto pela API?); se há como listar os
carregados; e como o app percebe a troca (consulta periódica do nome × evento). `confianca`: pendente.

## 🆕 2026-10-18 (noite) — as chamadas da casca, feitas por FORA (Studio 19.1.4.11, Win11, Python externo)

Bancada do app unificado (`_DeLaPraCa`, organograma https://claude.ai/artifact/VUZWUF4J9go9FZCB5LF8oT, quadro 5):
cada chamada que a casca (Workflow Integration, `plugins/resolve/casca/main.js`) faz por dentro, feita pelo
`DaVinciResolveScript` de um Python comum, com o Resolve aberto. Conecta em 0,04 s, inclusive com o Resolve na
janela de projetos. **48 de 48 funcionam por fora** (as 6 falhas da 1ª rodada eram do caso, refeitas na 2ª):

- projeto: `CreateProject`/`LoadProject`, `GetCurrentProject().GetName()` (o cabeçalho do app), `SetSetting`
  (`timelineFrameRate` antes de importar), `SaveProject`;
- Media Pool: `AddSubFolder`, `SetCurrentFolder`, `ImportMedia`, `GetClipProperty`, `SetClipColor`,
  `CreateTimelineFromClips`, `ImportTimelineFromFile` + `SetName`;
- timeline: `SetCurrentTimeline`, `GetItemListInTrack`, `GetStart`/`GetDuration`/`GetUniqueId`, `AddTrack`,
  `SetTrackEnable`/`GetIsTrackEnabled`, `AddMarker`/`DeleteMarkerByCustomData`, `CreateCompoundClip`,
  `GetTimelineCount`/`GetTimelineByIndex`, `SetCurrentTimecode`/`GetCurrentTimecode`;
- cor: `RefreshLUTList`, `SetLUT`, `SetCDL`; Fusion: `AddFusionComp`, `GetFusionCompNameList`,
  `ExportFusionComp`, `ImportFusionComp`, `LoadFusionCompByName`, `DeleteFusionCompByName`;
- quadros: `OpenPage("color")` + `ExportCurrentFrameAsStill` (PNG de 6 MB).

⭐ **`Timeline.Export(arq, EXPORT_DRT)` de uma timeline que NÃO é a corrente exporta a PEDIDA** (o .drt cita
`BANC_B` e não a corrente `BANC_CLIPS`) — `confirmado` no 19.1.4, o que resolve aqui o registro conflitante de
2026-09-27 (19.0.0b.59). O .drt do 19.1.4 reimporta com os itens.
⚠️ `DeleteFusionCompByName` devolve `false` para a comp CARREGADA; numa não carregada, apaga.
⛔ `.drt` gravado por Resolve MAIS NOVO (o do caso E01, do 21 no Mac): `ImportTimelineFromFile` devolve `None` e
o Resolve abre o modal "Unable to Import Project — A newer version of DaVinci Resolve is needed…" (só OK), que
segura o script até alguém clicar. É o piso do 19 (memória do app: escrever o formato do 19).
Ainda a medir por fora: o .drt GERADO pelo app + montagem completa; o arrasto do Media Pool para a janela do app;
o projeto em foco com a troca dinâmica de projetos.

## 🆕 2026-10-18 (23h) — a montagem COMPLETA por fora: o .drt do app + Fusion + cor + compostos + conferência

`confirmado` (Studio 19.1.4.11, Win11, Python externo pelo serviço do `_DeLaPraCa`, `tools/bancada_resolve/
e2e_prproj.py` sob o vigia). Caso real R04 PRODUCAO-C (`PRODC_FINAL_isolado.prproj` › `PRODC_Trailer_v02_RESGATE`,
80 planos, 14 trilhas de som), projeto novo a 23,976: importar o .drt gerado pelo app 7,2 s; 11/11 composições do
Fusion (Export → compor → Import, conferidas pelo export de volta); 75/75 nós de cor (`SetLUT` pelo caminho
relativo à pasta de LUTs + `SetCDL`); 8/8 `CreateCompoundClip` DEPOIS do Fusion; conferência pela referência
(Color + `SetCurrentTimecode` + `ExportCurrentFrameAsStill` por ponto) 144/144 conferem, semelhança média 0,9975
(mínima 0,963) — no Resolve 21.1 do Mac, pela casca, tinha sido 0,995. A prova do bypass (comp vazia por cima,
quadro igual = bypass ligado) também roda por fora. Responde a pendência "o .drt GERADO pelo app + montagem
completa" do registro anterior.
⚠️ Lição do caso: a régua da imagem só vale com a sequência DE ONDE a referência saiu. O .prproj de 2023
(`PRODUCAO_C_Trailer_Corte_v02`) tem os PRJ-*.mov com Motion › Scale 50 %; com os arquivos de 1920×1080 da
pasta isolada o plano sai com metade do tamanho (27/143 conferem) — fiel ao projeto, não erro do app. A sequência
resgatada pelo autor (`…_RESGATE`) tem 100 %.

## ⛔ O servidor de scripts (`fuscript.exe -s`, porta 1144) e o `scriptapp` que congela quem chama — medido 2026-10-23 (Studio 19.1.4.11, Win11)

- O Resolve, ao abrir, sobe um FILHO `fuscript.exe -s` que escuta em `0.0.0.0:1144`: é o servidor de scripts por onde
  TODO script externo chega (Python com `fusionscript.dll` e o próprio `fuscript.exe -l lua`). Também escutam, do
  `Resolve.exe`: 15000, 20321, 49152. `confirmado` (netstat + `Win32_Process`, pai = Resolve.exe).
- ⛔ Sem esse filho, o `scriptapp("Resolve")` devolve None depois de **~4,1 s** — e o Python **INTEIRO para** nesse
  tempo (o `fusionscript` segura o GIL: um relógio noutra thread parou os mesmos 4,1 s). Um serviço HTTP que chama o
  `scriptapp` a cada pedido de estado fica congelado: no De Lá Pra Cá, `/health` 4 s e uma leitura de .prproj de 1 s
  passou de 10 min. `confirmado`.
- ⛔ CORRIGE (mesmo dia, 17h): o servidor não é DERRUBADO depois — ele nunca chega a ligar. O log do Resolve
  (`%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\logs\ResolveDebug.txt` e `LogArchive\`) mostra, na ABERTURA:
  `Started script server` → `Failed to connect to script server, retrying` (até 3 servidores) → `Failed to connect to
  script server`; o log do servidor diz `RemoteApp::Connect … ioctlsocket(block) err 1` e `Script Server Terminated`.
  A sessão inteira fica muda; **reabrir o Resolve resolve** (não é preciso reboot — a sessão de 15:56 voltou assim).
  Correlação medida (6 aberturas, 2026-10-23): do início do log ao `Started script server` 45 s e 45 s → mudo; 25 s →
  1 falha e conectou; 8–9 s (4×) → de primeira. Máquina ocupada na abertura (uma das ruins foi durante chamada do
  Teams) = corrida perdida. `confirmado` (o padrão); a causa da lentidão em cada abertura, `hipotese`.
  Descartados por medição: Órbita (aberto, sincronizando para o MC, fechado; o zelador só mira `avid-api-gateway.exe`),
  VPN do navegador, portas (Órbita 7817, DLPC 7823, gateway órfão do Avid 4920/4930).
  ⭐ Diagnóstico rápido: `grep "script server" ResolveDebug.txt` — uma linha `Started` = OK; `Failed to connect` = mudo.
  3ª vez (2026-11-04, 19.1.4.11, aberto pelo `explorer.exe` a pedido do chat do Ciclo Assist): arranque 12:22:12 →
  `Started script server` 12:22:56 (44 s) → três falhas → mudo. ⛔⛔ **A porta 1144 PISCA:** o log do servidor diz
  `Script Server Started 312.937` → `Terminated 313.250` — ela fica aberta ~0,3 s, e quem sondava "porta aberta =
  pronto" a pegou nesse instante e deu o Resolve por pronto (o `scriptapp` voltou None em seguida). ⇒ pronto é uma
  CHAMADA da API responder, nunca a porta. ⭐ Remédio automatizado e provado ao vivo no mesmo dia: a linha EXATA
  `Failed to connect to script server` (sem `, retrying`) no `ResolveDebug.txt` da sessão = mudo; com só a janela
  `Project Manager` visível (nada a perder), `WM_CLOSE` nela fechou o Resolve em 12 s sem diálogo, e o relançado
  respondeu à API em 13 s (25,9 s no total). Com um projeto aberto não se fecha: o gesto vai ao editor.
  Implementação: Ciclo Assist `cicloassist/resolve.py` (`servidor_desistiu`, `sem_projeto_aberto`, `abrir`). `confirmado`.
  ⚠️ A frase "o Free não aceita script externo" para o `scriptapp` None ENGANA: o modelo a repetiu ao editor como
  causa provável, com o Studio na máquina.
- Defesa no De Lá Pra Cá (`resolve_externo.conectar`): sondar a 1144 com `socket` (solta o GIL, prazo 0,3 s) antes do
  `scriptapp`; uma tentativa por vez; depois de uma falha, a resposta sai na hora por 15 s. Mac: a porta `pendente`.
  Prova ao vivo (2026-10-24, Studio 19.1.4.11, DLPC v0.1.135): `taskkill` do `fuscript -s` com o serviço aberto →
  por 30 s, `/health` ≤ 25 ms e `/conexao` ≤ 0,34 s (com o `erro` "servidor de scripts … não está no ar"), painel
  amarelo; Resolve fechado (11 s, sem diálogo) e reaberto (servidor em 11,6 s) → `/conexao` verde 8 s depois. `confirmado`.
- ⛔⛔ **NÃO é só o `scriptapp`: QUALQUER chamada da API que espera o Resolve segura o GIL pelo tempo todo** (2026-11-23,
  Studio 21.1, Mac, Ciclo Assist › Conformar, PRODC 80 planos, etapa "importando no Resolve"). A pilha (`sample`, gravada
  pelo supervisor em `logs/diagnostico-conformar-*.txt`): uma thread em `fusionscript.so` `RemoteObject::DoCommand` →
  `RemoteApp::WaitPkt`, e TODAS as outras em `take_gil` (inclusive a do `accept` do HTTP; fila de escuta 5/0/5). O motor
  ficou mudo mais de 15 s (`TOLERANCIA_SEM_PORTA` do `supervisor.rs`), foi religado 3 vezes — o conform morreu no meio —
  e a API do Resolve ficou presa depois (um `GetTimelineCount` estourou 30 s). Qual chamada exata: `inferido` (a da
  importação da timeline). `confirmado`: o GIL preso durante o `DoCommand`. ⇒ Chamada longa da API fora do processo que
  serve HTTP (subprocesso), ou o motor avisa ao supervisor que vai ficar mudo. Na rodada anterior do PRODC → Resolve pelo
  chat (144/144, handoff do Ciclo Assist) a importação coube na tolerância; não medido por quê.
- ⚠️ Medição: o `curl` do Git Bash com `-d '{"caminho":"C:\…"}'` fez POSTs do serviço "travarem" 30 s–2 min que pelo
  Python levam 0,02–0,27 s. POST com caminho Windows no corpo: medir com `urllib`.


## 🆕 Arrastar CLIPES da TIMELINE (página Edit) para fora — Studio 19.1.4.11, Win11 (2026-10-24) — `confirmado`

Sonda nativa (`piloto/sondas/arrasto_nativo.py`), projeto "DLPC PRODA 19 C", clipes de áudio da PRODA agarrados pelo corpo.
- ✅ Ao contrário do Media Pool (que não solta fora), o clipe da TIMELINE **sai** do Resolve e é solto na janela nativa.
- Um formato só: `Timeline/Item` (HGLOBAL, 47 B) = QDataStream: 1 entrada, a chave `"SourcePointer"` + um qulonglong que é
  ponteiro do processo — o MESMO valor para 1 clipe e para 2 clipes (Ctrl+clique). ⇒ só o GESTO; nenhum nome nem tempo.
- ⛔ A API do 19.1.4 não diz a seleção da TIMELINE: `Timeline` só tem `GetCurrentVideoItem` (o item sob a agulha; deu None
  com a agulha em 01:00:30), `GetCurrentTimecode`, `GetCurrentClipThumbnailImage`. Ctrl+C de um clipe da timeline NÃO vai
  para a área de transferência do Windows (0 formatos).
- Timeline intacta depois dos arrastos (foto). ⇒ Para o relink de clipes escolhidos no Resolve o dado precisa vir de
  outro lugar: agulha sobre o clipe (`GetCurrentVideoItem`, só vídeo, só o de cima), marcadores/cor, ou o REA (Frida no
  `Resolve.exe` para achar a seleção atrás do "SourcePointer"). `pendente`: a matriz completa (vídeo, compound, multicam,
  título, ajuste) e o Mac.

## 🆕 ⭐ O mesmo no macOS com o Resolve 21 — o arrasto sai E a API lê a seleção (Studio 21.1.0.14, macOS 15.6.1, 2026-10-24) — `confirmado`

- Sonda `piloto/sondas/arrasto_nativo_mac.swift`; projeto LAB_ARRASTO_MAC criado pela API (`CreateProject`, `ImportMedia`,
  `CreateTimelineFromClips`), 1 clipe V1+A1.
- **Clipe da timeline → fora: SAI**, e com o arrasto SINTÉTICO do piloto (no Windows só com a mão). Tipo
  `com.trolltech.anymime.Timeline--Item` (47 B, `QDataStream` big-endian: 1 entrada, QString `"SourcePointer"`, um inteiro
  de 64 bits = ponteiro). O mesmo "SourcePointer" do Windows: sem dado legível.
- ⭐ **O Resolve 21 tem `Timeline.GetSelectedClips()`** (não existe no 19.1.4): logo depois do arrasto ele devolveu os 2
  itens (video 1 e audio 1, vinculados), com `GetMediaPoolItem().GetClipProperty("File Path")` = o caminho. ⇒ no 21, o
  desenho é o do Premiere: o soltar (`Timeline--Item`) é o GESTO, a API dá o dado. No 19 (o piso, Windows) segue o plano B
  (agulha, `GetCurrentVideoItem`) — o app tem de perguntar se a função existe.
- **Media Pool → fora, arrasto SINTÉTICO: NÃO sai** (igual ao 19 no Windows): a miniatura passa, o Resolve mostra o
  menu de edição dele no monitor da timeline (Overwrite/Replace/Fill/Place on Top/Append) e nada chega à sonda; nenhuma
  edição aconteceu (conferido pela API). **Com a MÃO do autor (10h37): também NÃO sai** — o pasteboard de arrasto nem
  mudou (changeCount igual), timeline intacta. ⇒ no Mac o Media Pool do Resolve 21 não solta para fora (no Windows o
  19 solta `MediaPool/FusionMedia`). O dado do Media Pool no Mac vem da API: `MediaPool.GetSelectedClips()` devolveu o
  clipe arrastado (o gesto deixa a seleção). Para o app: no Mac, "arrastar do Media Pool" não é caminho; um botão
  "usar o que está selecionado" é.
- ⚠️ Abrir o Resolve por código no Mac: `env -u LANG -u LC_ALL open -a …` (o MC aborta com o `LANG` herdado; o Resolve
  abriu sem ele — não medido com ele). O piloto não achou a janela pelo nome do processo: o dono da janela é
  "DaVinci Resolve" (o processo é `Resolve`).

### 🆕 Grade por script no 21.1 (Mac) — `confirmado` 2026-10-24 (De Lá Pra Cá, a estabilização do Avid)

- ⛔ **`hasattr` mente nos objetos da API**: `hasattr(timeline, "ApplyGradeFromDRX")` dá True no 21 e o atributo vale
  `None` (chamar = "'NoneType' object is not callable"). Para saber se um método existe nesta versão:
  `callable(getattr(obj, nome, None))`.
- **`ApplyGradeFromDRX` mudou de lugar**: no 21 é `TimelineItem.GetNodeGraph().ApplyGradeFromDRX(caminho, modo)`
  (True, 0,08 s); no 19 era `Timeline.ApplyGradeFromDRX(caminho, modo, [itens])`. Quem escreve grade tenta os dois.
- `TimelineItem.Stabilize()` por script externo: True em 2 s (144 quadros 1080p) e 3,9 s para 2 clipes 4K da PRODA
  (394 + 204 quadros) — a análise vai no `Body` (`protocolos/drt-drp/estruturas.md` §ESTABILIZADOR).
- `GrabStill` + `GalleryStillAlbum.ExportStills(…, "drx")` funcionaram por script depois de `OpenPage("color")`
  (o estado do painel Gallery nesta máquina não foi conferido — no 19 ele precisava estar ABERTO). Para ler a grade
  sem depender disso: o `Body` do DRT exportado da timeline.
- `TimelineItem.GetSourceStartFrame()` deu 1948 num clipe cujo `In` no DRT exportado é 1949 (as entradas do
  estabilizador também começam em 1949): para casar com o `Body`, use o `In` do DRT.

## A GRADE DE TIMELINE pela API — medido 2026-11-20 (Studio 19.1.4, Windows; Ciclo Assist, a página Color do Premiere)

Para levar uma grade que vale para a timeline inteira (o nível Sequence da página Color do Premiere 2027):
- `Timeline.GetNodeGraph()` EXISTE (README de 28/10/2024) e devolve um `Graph` — com **0 nós** numa timeline que nunca teve
  grade de timeline, mesmo com a página Color aberta. Não há método para CRIAR nó.
- ⛔ `Graph.ApplyGradeFromDRX` no grafo da TIMELINE devolve **False** sempre: com 0 nós, com o modo "Timeline" do editor de
  nós ativo e com 1 nó criado na interface (Alt+S), e até com um `.drx` GENUÍNO exportado pela galeria
  (`GrabStill` + `ExportStills(…, "drx")`) — o MESMO arquivo num clipe dá True (o mínimo do Conformar também).
- ✅ `Graph.SetLUT(1, caminho)` no grafo da timeline FUNCIONA (True, `GetLUT` confere) — mas só depois que existe um nó, e o
  nó só nasce pela interface (página Color › editor de nós › "Clip ⌄" → "Timeline" → Alt+S). `ResetAllGrades` limpa (True).
- ⛔ O `.drt` exportado NÃO leva a grade de timeline: com o nó da timeline e uma LUT de fábrica nele, a LUT não aparece em
  nenhum blob (zstd descomprimido, ASCII e UTF-16). ⇒ nem pelo arquivo.
- ⇒ Grade de timeline automática no 19.1.4: impossível. Caminhos: LUT na timeline SE o usuário já criou o nó (um gesto),
  ou a LUT em cada clipe. `pendente`: o 20/21 (o Mac tem o 21.1).

## Modal aberto (Project Settings): a API responde, as escritas falham caladas — medido 2026-10-28

`confirmado` no Studio 21.1 (Mac), pilotando: com o Project Settings aberto (File ▸ Project Settings…), leituras
(`GetName`, `GetTimelineCount`, `GetSetting`) respondem em milissegundos; **`SetCurrentTimeline` devolve `None` e NÃO
troca**; **`GetCurrentPage()` devolve `None`** (sem modal: `"deliver"`, `"edit"`…). O `None` da página é o sinal do
diálogo: nunca `GetCurrentPage() or "edit"`. Usado no De Lá Pra Cá (`resolve_externo._DIALOGO_ABERTO`, casca). ⏳ O 19.

## 🆕 Trocar a mídia por chart e exportar stills num projeto REAL — 2026-11-21 (Resolve Studio 21.1, Mac M4 16 GB)

Do PRODUCAO-H LAB (cópia por `.drp` do projeto do autor; `laboratorio-de-midia/lab/bancadas/resolve_felipe_ret.py`):
- **`MediaPoolItem.ReplaceClip(arquivo)` casa o quadro pelo TC** (`confirmado`): o trecho 347–353 de um clipe virou 47–53
  de um arquivo que começa 300 quadros depois, com o código de barras do quadro lido no still = 350. Mantém os nós
  (360 e 419 antes = depois), RENOMEIA o item do pool para o nome do arquivo novo e VOLTA o "Input Color Space" para
  "Project" — repor com `SetClipProperty`. Com `separateColorSpaceAndGamma` = 0 (RCM v2) o "Input Gamma" não aceita
  `SetClipProperty` (False) e não importa: vale só o espaço. **PAR numérico (0,8654, 1,322…) não se põe pela API**: ele
  vem do ARQUIVO (o chart gravado com o `setsar` certo; os nomes "Square"/"PAL" se põem).
- ⛔ CORRIGE (2026-11-21): `ImportProject(drp, nome)` **NÃO mantém** os `GetUniqueId()` dos itens do pool (a 1ª leitura comparou
  a cópia com ela mesma); casar a mídia pelo caminho original ou pelo nome. `DuplicateTimeline` + `Graph.ResetAllGrades()`
  em cada item = a referência "sem cor" (as grades do projeto eram locais, `LmVersionTable` por `Sm2TiItem`).
- ⛔ **`TimelineItem.SetClipEnabled(False)` só funciona na timeline ATUAL**: em outra devolve False e não faz nada.
- ⛔⛔ **`Project.ExportCurrentFrameAsStill` em série DERRUBOU o Resolve** (`std::bad_alloc`, 6º still, um clipe 4K com
  Halation/NR) com o **Premiere 2027 aberto ao lado** (16 GB). O 1º lote: 5 stills em 2 s, depois a queda. Depois da
  queda o macOS mostra "DaVinci Resolve quit unexpectedly" (Ignore/Send) e a API diz "not running" até alguém responder.
  ⇒ um NLE pesado por vez nesta máquina; ⬜ remedir os stills sozinho (ou render por trechos).
- ⛔⛔ **A página COLOR derrubou o 21.1 três vezes neste projeto** (`std::bad_alloc` no laço de eventos da interface, ~7 s
  depois de abrir na Color — com os charts ONLINE, OFFLINE e no meio dos stills; a 1ª cópia passou a cair a cada abertura,
  porque reabre na Color). Um projeto descartável com os 86 charts SEM grade na Color não caiu. **A página EDIT não caiu
  nenhuma vez**: reimportado o `.drp` ("PRODUCAO-H LAB 2"), trocados os 82 charts, salvo e reaberto na Edit, e os **710
  stills** (`ExportCurrentFrameAsStill`, que na Edit já sai com a grade) saíram sem queda. ⇒ automação de medida: Edit.
  Causa exata `pendente`. Depois da queda: o aviso "quit unexpectedly" (Ignore) e o próximo `launch` abre o "Untitled".
- `GetSourceStartFrame() > GetSourceEndFrame()` num item = o clipe está **ESPELHADO na horizontal** (flip), não invertido
  no tempo (medido pelo still: o chart saiu espelhado).

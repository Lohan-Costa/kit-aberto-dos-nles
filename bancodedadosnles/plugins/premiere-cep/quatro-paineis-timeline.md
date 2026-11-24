# Quatro painéis do Premiere — o catálogo de operações, e o que dizem sobre o redesenho

Sexto caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md).
Fatos consumíveis em [dados/quatro-paineis.json](dados/quatro-paineis.json).

**Por que esta leva importa:** os cinco casos anteriores foram lidos para entender *arquitetura
de produto*. Estes quatro foram lidos com **uma pergunta operacional em mão** — o painel Timeline
do Premiere não repinta depois que um script move clipes
([api-extendscript §redesenho](api-extendscript.md)), a pendência está parada desde 2026-08-01, e
cinco caminhos já falharam. A pergunta era: *alguém resolveu isto?*

⛔ **A resposta curta é NÃO, e o "não" tem valor.** Nenhum dos quatro **move um clipe já colocado
na timeline**. Eles inserem, sobrescrevem, aplicam efeito, criam marcador e organizam bin — todas
operações que mudam a ESTRUTURA ou o CONTEÚDO, e por isso repintam sozinhas. *O nosso sintoma é
raro porque a nossa operação é rara.* Não há cura pronta para copiar.

⭐⭐ **Mas apareceu uma alavanca que nunca foi tentada aqui: o parâmetro `updateUI`.** Está na §2.

## O que foi inspecionado

| painel | versão | host | forma do código |
|---|---|---|---|
| **Automation Blocks for Premiere Pro** (mamoworld) | 1.1.013 | `PPRO 14.9` | 2 bundles JS de ~6,7 MB; o **ExtendScript inteiro vive embutido como string** (3,2 MB) e é injetado por `evalScript` |
| **FX Launcher Pro** | 1.0.4 | `PPRO [14.0,999.9]` | ⭐ **`host/index.jsx` EM CLARO**, 57 KB, comentado |
| **FireStarter** (`com.mikey.firestarter`) | 1.0.7 | `PPRO [23.0,99.9]` | `index.js` 48 KB em claro; **sem `.jsx`** — gera o ExtendScript em runtime |
| **Markers Pro** | 1.1.1 | `PPRO 9.1` | JSXBIN **dentro de JSXBIN** (o externo carrega uma string `@JSXBIN@ES@2.1@` entregue a `eval()`) — ⛔ nível interno não lido. ⚠️ *Este campo dizia "payload cifrado"; corrigido em 2026-08-24* |

Material em `PROGRAMAS ANALISAR/PLUGINS PREMIERE VARIADOS/`, analisado em 2026-08-24.

---

## 1. O que os quatro fazem com a timeline (e o que NÃO fazem)

| operação | AB | FXL | FS | consequência para o redesenho |
|---|:--:|:--:|:--:|---|
| `insertClip` / `overwriteClip` | ✅ | — | — | estrutural → repinta sozinho |
| aplicar efeito / transição / preset | — | ✅ | — | muda conteúdo → repinta sozinho |
| criar bin, importar, rotular por cor | ✅ | — | ✅ | não toca a timeline |
| criar marcador | ✅ | — | — | painel próprio |
| criar sequência (preset ou a partir de clipes) | ✅ | — | — | estrutural |
| **mover clipe já colocado** | ❌ | ❌ | ❌ | **ninguém faz** |

⭐ **A leitura que sai daí:** o mercado de painéis de Premiere é de *ingest e acabamento*, não de
*rearranjo*. Quem monta timeline monta do zero (`insertClip`/`overwriteClip`); quem já montou não
volta para deslocar. O Órbita faz sync **in-place** numa sequência que o editor já abriu — e é
exatamente essa operação que o painel Timeline não sabe redesenhar.

⚠️ **Um detalhe que confirma o nosso registro, por um caminho independente.** O Automation Blocks
expõe `start` e `end` como propriedades **escrevíveis** de um `TrackItem`
(`dt.start = …`, `dt.end = …`). O nosso `host.jsx` já anota que `clip.start = t` **apara** o clipe
em vez de movê-lo, e que mover é `TrackItem.move(Time)`. Os dois fatos convivem: o produto deles
usa `start`/`end` como *aparo*, que é o que a propriedade faz. Ninguém ali usa `move()`.

---

## 2. ⭐⭐ `updateUI` — a alavanca que este banco não tinha

Achado em dois dos quatro, independentes:

**Automation Blocks**, no setter de `TrackItem`:

```javascript
if (ds == "selected") { dt.setSelected(K(du), true); }
```

O segundo argumento é passado **explicitamente como `true`** — não é omitido. E o mesmo painel
trata `updateUI` como opção de primeira classe nos setters de parâmetro de componente, com
**default `true`**, exposta até o topo como campo de bloco:

```javascript
var e = ("updateUI" in ds) ? ds.updateUI : true;
```

**FX Launcher**, em `resetMotion`, no mesmo padrão:

```javascript
p.setValue([w / 2, h / 2], true);   // Position, Scale, Rotation, Anchor Point
```

⭐ **O que isto significa:** várias APIs de mutação do ExtendScript do Premiere carregam um
booleano de *atualizar a interface* — `TrackItem.setSelected(isSelected, updateUI)` e
`ComponentParam.setValue(value, updateUI)` são os dois vistos. **Dois produtos comerciais
independentes passam `true` sempre.**

### ⚠️⚠️ E por que isto é uma pista viva, não uma repetição

O `host.jsx` do Órbita **não chama `setSelected` em lugar nenhum** — a única ocorrência da palavra
é um comentário dizendo que não se faz isso, com esta justificativa:

> *"NÃO piscamos a seleção (setSelected em todos os clipes): testado na GUI, o Cmd+A manual PIORA
> o sintoma."*

⭐ **O que foi testado ali foi o GESTO, não a API.** `Cmd+A` na GUI é seleção pelo painel;
`trackItem.setSelected(true, true)` é chamada de script com um sinalizador explícito de atualizar
interface. São coisas diferentes, e a segunda **nunca foi executada**. A cascata de cinco
tentativas (playhead, reatribuir sequência, piscar seleção, lock/unlock por QE, trocar o primitivo
para o `move` do QE) não inclui esta.

### ⛔ E um conflito DENTRO do nosso próprio registro, que precisa ser resolvido antes

Duas fontes nossas dizem o oposto sobre o mesmo gesto:

| fonte | o que diz |
|---|---|
| `.dev/DECISIONS.md`, 2026-08-01 | *"O usuário achou o remédio manual — **Cmd+A e andar um frame** — que é a pista do mecanismo: desenhar o realce de seleção obriga o painel a repintar cada clipe."* |
| `plugins/premiere-cep/jsx/host.jsx:414` | *"testado na GUI, o **Cmd+A manual PIORA** o sintoma — some até clipe que não estava na seleção."* |

Uma das duas está errada, e o desenho da próxima rodada depende de qual. ⭐ **Registrar isto é
metade do achado:** a alavanca `updateUI` só vale a pena se a hipótese "seleção força repintura"
for a verdadeira — e hoje o projeto sustenta as duas ao mesmo tempo.

**Ordem sugerida para a próxima rodada** (barata e mede uma variável por vez):

1. Refazer o gesto manual na GUI e **anotar o resultado**, encerrando a contradição.
2. Se seleção repinta: depois de mover, chamar `setSelected(true, true)` **só nos clipes movidos**
   (não `Cmd+A`), e devolver a seleção anterior.
3. Se não repinta: a alavanca cai, e sobra o degrau que nunca rodou — fechar e reabrir a sequência,
   hoje inalcançável porque a cascata escala por **existência** do `locktoggle`, não por efeito.

---

## 3. ⭐ A ponte DOM ↔ QE por ticks (FX Launcher)

O problema: `sequence.getSelection()` devolve `TrackItem`s do DOM, mas as APIs de efeito e
transição só existem no QE, que é um **grafo de objetos paralelo**. Não há identidade comum entre
os dois. A solução deles, em cascata de prioridade:

```
1. start.ticks E end.ticks batem   → casamento exato
2. só start.ticks bate            → bom (quando end não está disponível)
3. nome bate                      → último recurso, só se não houver tick nenhum
```

⭐ **O detalhe que vale:** usar **também o `end`** é o que distingue dois clipes cortados do mesmo
master — pelo nome eles são idênticos, e pelo `start` só se separam se ninguém tiver mexido.

⚠️ **Relevante direto para o nosso `orbitaResolveClip`**, que resolve por índice e, falhando, varre
a track por *caminho + start esperado*. O `end` não entra hoje, e a nossa própria nota de
2026-08-01 registra que a coleção de clipes **reordena por tempo** — ou seja, o cenário em que
dois clipes do mesmo master compartilham caminho e um deles já se moveu é exatamente o que o par
`start`+`end` resolveria.

---

## 4. ⭐ XMP: o namespace decide qual API chamar

Segunda aparição independente do metadado privado do projeto — a primeira foi o
[Chop Chop](chopchop-arquitetura.md), que revelou o URI mas não o mecanismo. O Automation Blocks
mostra o mecanismo inteiro:

```javascript
// prefixo do caminho decide a origem E o destino
var pref = getNameSpacePrefixFromPath(path);
var xmp  = (pref == "premierePrivateProjectMetaData:") ? item.getProjectMetadata()
                                                       : item.getXMPMetadata();
// … e na escrita:
if (pref == "premierePrivateProjectMetaData:")
    item.setProjectMetadata(xmp.serialize(), [removeNameSpacePrefixFromPath(path)]);
else
    item.setXMPMetadata(xmp.serialize());
```

⚠️ **A assimetria é a armadilha:** `setProjectMetadata` recebe **dois** argumentos — o XMP
serializado **e a lista dos caminhos alterados, sem o prefixo do namespace**. `setXMPMetadata`
recebe um só. Escrever no privado com a assinatura do público falha em silêncio.

⭐ Isso tira a pendência de estado da análise do Chop Chop do terreno da hipótese: temos URI,
mecanismo de leitura, mecanismo de escrita e a diferença de assinatura.

---

## 5. O catálogo — 81 blocos de operação do Premiere

O Automation Blocks é, na prática, **uma lista publicada do que dá para fazer via ExtendScript**.
Os nomes de bloco (extraídos dos bundles) por família:

| família | blocos |
|---|---|
| **Sequência** | `new_sequence` (por preset), `new_sequence_from_clips`, `sequence_clone`, `seqence_activate`, `active_seqence`, `sequence_get/set_property`, `sequence_add_clips`, `sequence_preset_file` |
| **Clipe (TrackItem)** | `track_item_get/set_property`, `clip_label_color`, `clip_time_to_sequence_time`, `for_all_sequence_items`, `list_of_sequence_items` |
| **Parâmetro / keyframe** | `component_parameter_path`, `…_path_keyframeable`, `…_get/set_value`, `…_get/set_value_at_time`, `…_remove_key_range`, `for_all_component_params_of_clip` |
| **Marcador** | `marker_create`, `marker_get`, `marker_get_num`, `marker_delete_one`, `marker_delete_all`, `marker_get/set_property`, `marker_for_all_of_project_item`, `marker_color`, `marker_type` |
| **Item de projeto** | `item_get/set_property`, `item_get/set_metadata`, `item_get_time`, `item_set_time`, `item_path`, `item_exists`, `item_set_name`, `item_unique_name`, `item_delete`, `item_move_to_bin`, `item_change_media`, `item_has_extended_type`, `project_item_create_subclip`, `project_item_create_bin` |
| **Metadado de bin** | `item_metadata_color_label_get/set`, `item_metadata_good`, `item_metadata_hide`, `item_metadata_rating`, `item_metadata_usage` |
| **Projeto** | `project_new/open/save/save_as/close`, `project_active_project`, `project_import_file`, `project_import_ae_comps`, `project_select_items`, `project_set_scratch_disk_path`, `sync_project_bin_with_folder`, `project_file`, `project_folder`, `project_name` |
| **Tempo** | `time_from_timecode`, `time_to_timecode`, `time_to_timecode_of_sequence`, `format_time` |
| **Outros** | `replace_mogrt_text`, `execute_code`, `for_all_items_in_bin`, `get_items_in_bin`, `for_all_open_projects` |

### Propriedades de `TrackItem` que eles expõem

Leitura: `name`, `matchName`, `mediaType`, `start`, `end`, `inPoint`, `outPoint`, `duration`,
`speed` (`getSpeed()`), `speedIsReversed` (`isSpeedReversed()`), `trackName`,
`isAdjustmentLayer()`, `projectItem`, `nodeId`, `disabled`.

Escrita: `name`, `start`, `end`, `inPoint`, `outPoint`, `projectItem`, `disabled`,
`selected` (via `setSelected(v, true)`).

⭐ **Três que não usamos e abrem operação:** `isAdjustmentLayer()` (distinguir camada de ajuste de
clipe real numa varredura), `nodeId` (identidade estável de clipe — candidata melhor que
caminho+start para a §3) e `disabled` (desligar um clipe sem removê-lo — um "modo rascunho" para o
stringout).

### Propriedades de sequência com setter

`playerPosition`, `inPoint`, `outPoint`, `zeroPoint`, `name`, `audioDisplayFormat`,
`videoDisplayFormat`, `workAreaEnabled`, `workAreaIn`, `workAreaOut` — e as demais via
`getSettings()` / `setSettings()` (o padrão *ler o objeto inteiro, mexer numa chave, devolver*).

### Outras operações vistas

- `projectItem.createSubClip(name, inTicks, outTicks, hardBoundaries, takeVideo, takeAudio)` —
  subclipe por script; não usamos.
- `insertClip` × `overwriteClip` escolhidos por uma variante (`INSERT`/`OVERWRITE`), com
  `trackNumber` **1-based** convertido para índice 0-based.
- **Efeitos e transições só pelo QE:** `qe.project.getVideoEffectByName` /
  `getVideoEffectList` / `getAudioEffectByName` / `getAudioEffectList` /
  `getVideoTransitionByName` / `getAudioTransitionList`. ⭐ Confirma por produto comercial o que a
  nossa nota de 2026-08-01 já supunha: **o DOM não tem `addEffect`; só o QE adiciona efeito.**
- FX Launcher lê preset do disco e o aplica (`_parsePresetXML`, `applyPreset(path, displayName)`).

---

## 6. Modelo de execução — o FireStarter é o 3º ponto

O FireStarter não tem `.jsx` nenhum. Ele **monta o ExtendScript como string em runtime**
(`buildSetupScript`, `generateCreateBins`, `generateImport`, `generateApplyColors`) e manda por
`evalScript`. É a mesma família do Premiere Copilot, e reforça a classificação de
[`../../transversal/modelo-de-execucao-de-agente.md`](../../transversal/modelo-de-execucao-de-agente.md).

O produto dele é **estrutura de projeto**: varre uma pasta, cria as bins, importa, aplica rótulo
de cor por tipo de arquivo e reporta o que pulou. Nenhuma operação de timeline.

⭐ **Achado de negócio, 2ª aparição:** o FireStarter carrega `lib/aesp.umd.js` — o SDK de
licenciamento do **aescripts+aeplugins**, o mesmo visto no Chat Video Pro. Junto com o Automation
Blocks (que é vendido pela aescripts) e o Chop Chop (que instrui a instalar o ZXP/UXP installer da
aescripts), são **quatro produtos** apontando para o mesmo canal — ver
[distribuicao-e-licenciamento.md](distribuicao-e-licenciamento.md).

---

## ⚠️ A régua — o que NÃO foi feito

- ⛔⚠️ **Markers Pro: parado no invólucro — e a descrição abaixo ESTAVA ERRADA, corrigida em
  2026-08-24 (ver [addendum-desofuscacao.md](addendum-desofuscacao.md) §3).** Não é "payload
  cifrado": é **JSXBIN dentro de JSXBIN** — o `.jsx` externo (ES 2.0) carrega uma string que é
  outro JSXBIN (**ES 2.1**) entregue a `eval()`. Não há cifra nenhuma, há dois invólucros. O que a
  tabela de símbolos externa entrega (polyfill de JSON + `eval`/`charCodeAt`/`replace`) é o
  *carregador*, e eu li isso como *decodificador de blob cifrado*. ⭐ **A lição: "parece cifrado"
  costuma ser "está embrulhado duas vezes"** — e a diferença importa, porque a segunda é trivial
  de abrir e a primeira não. O nível interno segue sem leitura: o ES 2.1 usa codificação diferente
  da ES 2.0, e o decodificador de pares não se aplica. Registro original (impreciso): O `.jsx` é JSXBIN, e a tabela de símbolos decodificada
  devolve **só um polyfill de JSON mais `eval`/`charCodeAt`/`replace`/`test`** — a assinatura de um
  *stub decodificador*, com a lógica real num blob cifrado por dentro do JSXBIN. Duas camadas de
  proteção deliberada. Não foi desfeita, e o painel fica sem análise.
- **Automation Blocks:** o ExtendScript foi extraído porque é **string literal no bundle**, e foi
  lido por busca dirigida (nomes de API, propriedades, literais). Está minificado com
  identificadores de 1–3 letras — nenhuma lógica foi reconstruída, e nada seria legível se fosse.
- **FX Launcher:** o `.jsx` veio em claro e foi lido; ⛔ o **`FX Spell Book.exe` (280 MB) NÃO foi
  analisado** — é uma biblioteca de presets, fora da pergunta desta sessão.
- **FireStarter:** lidos os nomes das funções geradoras e a superfície de API. O `aesp.umd.js`
  (2 MB, obfuscado) não foi desofuscado.
- **Nada instalado, nada executado, nenhuma licença tocada.** ⚠️ O
  `firestarter-1.0.7_licensed.zip` tem "licensed" no nome; nenhum mecanismo de licença foi
  examinado, contornado ou testado.
- Temporários apagados ao fim.

## O que fazer com isto

1. ⭐⭐ **Encerrar a contradição do `Cmd+A`** (§2) — é uma medição de um minuto na GUI e destrava a
   pendência mais antiga do painel.
2. ⭐ **Se seleção repinta: `setSelected(true, true)` nos clipes movidos**, restaurando a seleção
   anterior. Nunca foi tentado.
3. ⭐ **Somar `end.ticks` ao `orbitaResolveClip`** (§3) — e avaliar `nodeId` como identidade
   estável, que resolveria a classe inteira.
4. **`setProjectMetadata` tem dois argumentos** (§4) — anotar antes de tentar o estado em XMP.
5. `pendente`: Markers Pro, se um dia valer a pena.

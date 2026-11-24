# ESION Studio (Acclaim Audio) — o 5º produto dissecado, e o 2º painel do Avid

> **O que é:** um *leveler* de áudio de alta qualidade que se integra ao Media Composer por um
> painel do Panel SDK. Produto pago, licenciado por **iLok**, assinado com certificado EV de
> `Acclaim Audio Corp.` (Orlando, FL), e o `.avpi` é **assinado pela Avid**
> (`esion-studio_25.1.0-signed-2025-10-13.avpi`).
>
> **Por que foi analisado (2026-08-15):** ele faz um gesto que este banco registrava como
> **impossível** — arrastar clipes da bin **para dentro** do painel. A pergunta era *"qual
> comando nos falta?"*. A resposta: **nenhum.** Não é comando.

---

## 1. ⭐⭐ O achado principal: o drag MC → painel não é API, é DOM

A afirmação *"o drop é de mão única"* que este banco registrava estava **errada**. O assunto
inteiro — mecanismo, payload, as seis espécies, os negativos e as armadilhas — tem arquivo
próprio: **[arrastar.md](arrastar.md)**. Em resumo:

```js
MCAPI_ASSET_LIST_MIME_TYPE = 'text/x.avid.mc-api-asset-list+json'

// Handle drag from Media Composer to our app      ← comentário deles
async function handleMediaComposerDrop(e) {
    const dt = e.dataTransfer;
    if (dt.types.includes(MCAPI_ASSET_LIST_MIME_TYPE)) {
        parsedData = JSON.parse(dt.getData(MCAPI_ASSET_LIST_MIME_TYPE));
    }
    ...
}
```

Registro no DOM, sem cerimônia nenhuma:

```js
dropArea.addEventListener('drop', handleMediaComposerDrop, false);
```

**Nada disso é declarado no manifesto.** O `usesApi` do ESION é `["avid.mediacomposer.general"]`
e mais nada; `subscribesToChannels` e `entitlements` estão **vazios**. Ou seja: **a capacidade
não é concedida, ela simplesmente existe** para qualquer painel que escute `drop`.

⭐ **A lição de método** (a mais cara desta análise): procurou-se `Drop*` nos símbolos do
binário do MC, só apareceram os três de saída, e concluiu-se ausência. O pressuposto invisível
era *"se existe, é um rpc"*. **Metade da superfície de um painel é a do navegador, e essa
metade não aparece em `strings` do executável.**

---

## 2. A arquitetura do produto

```
  bin do MC ──drag (MIME custom)──►  PAINEL .avpi (React)
                                        │  ├─ gRPC-Web → gateway  localhost:4930  (mcapi)
                                        │  └─ WebSocket          localhost:52413  (motor ESION)
                                        ▼
                                     daemon launchd  (com.acclaimaudio.esionserver.daemon)
                                        │
                                     motor de áudio 64-bit + iLok  (~1,5 GB)
```

**O fluxo completo de uma operação**, reconstruído dos nomes de função:

1. o editor **arrasta** um ou mais clipes/sequences para o painel;
2. o painel lê `id` + `type` + `in`/`out` do JSON do drop — **sem uma única chamada à API**;
3. `getMobInfoThenExport(id, type)` → `GetMobInfo` e depois `ExportFile`;
4. o export usa um preset **WAV** que o próprio produto instalou (§3);
5. o WAV vai para `mcExportFolder`, um caminho que **o servidor local informa ao painel** na
   resposta do `REGISTER_REQUEST` do WebSocket;
6. o daemon processa; o painel recebe `ExportFinished`;
7. volta por `ImportFile`, com um preset de **Import** também embarcado.

⭐ **É a mesma forma do De Lá Pra Cá e do Órbita** — painel fino + serviço local com o motor —,
com duas diferenças de desenho que valem nota:

| | ESION | De Lá Pra Cá |
|---|---|---|
| Quem fala com o MC | **o painel**, por gRPC-Web no **gateway 4930** (com token, rota oficial) | **o serviço**, por gRPC no backend **9100** (sem token) |
| Painel ↔ serviço | **WebSocket** (`localhost:52413`), servidor = o daemon | **HTTP + SSE** (`127.0.0.1:7823`), servidor = o serviço |
| Entrada do material | **drag** | leitura de bins / seleção |

O ESION usa a via **oficial** (gateway + painel assinado) — o que é coerente com ser parceiro
com `.avpi` assinado pela Avid — e por isso precisa declarar `localhost:4930` em
`allowedDomains`. É a prova de que a rota do gateway funciona de dentro do painel, o que o
nosso caminho (backend direto, sem token, a partir de um processo local) não exercitou.

---

## 3. ⭐ Presets do Avid: uma rota de instalação que não conhecíamos

O produto instala um arquivo **solto** em:

```
/Applications/Avid Media Composer/Settings/ESION.xml
```

com o mesmo envelope `Avid:StreamItems` + `DomainMagic`/`DomainKey` das settings do editor, e um
único bloco `AvClass id="EXst"` de `kind="Export"`, `name="ESION"`.

⭐⭐ **Isto é diferente do que este banco registrava.** Sabíamos que os presets vivem dentro do
`<usuário> Settings.xml` (5 MB, na pasta `Avid Users`), e que **escrever lá exige o MC fechado**,
porque ele reescreve o arquivo inteiro ao sair. O ESION mostra uma segunda rota: **um XML de
setting única, largado na pasta `Settings` da APLICAÇÃO**, entregue pelo instalador.

`pendente`: se o MC **funde** esse arquivo às settings do usuário no boot, e o que acontece com
ele numa atualização do editor. É o teste de maior valor que sai desta análise — resolveria o
maior incômodo do nosso [ADR 0009](../../../_DeLaPraCa/docs/adr/0009-preset-de-export-embarcado.md).

✅ **O incômodo do ADR 0009 resolvido por OUTRA rota (2026-10-11, MC 25.6 Windows):** o rpc `LoadSetting` com
ESTE MESMO envelope — `DomainMagic`/`DomainKey` + **`<AvClass id="SETG"/>`** + o bloco `EXst` — instala o preset
de export **com o MC aberto**, na hora (sem o `SETG`: "No settings objects"). Ver `dados/mcapi-grpc.json` →
`LoadSetting_recusa_preset_de_export`. O XML solto em `Settings/` segue não testado.

### `_EXPORTFORMAT` confirmado por terceiro

```
<AvProp id="ATTR" name="OMFI:ATTB:Name" type="string">_EXPORTFORMAT</AvProp>
<AvProp id="ATTR" name="OMFI:ATTB:IntAttribute" type="int32">9</AvProp>
```

**9 = WAV**, exatamente como a tabela medida em
[dados/export-presets.json](dados/export-presets.json). Um produto comercial em produção usa o
mesmo campo com o mesmo valor: o fato sobe de *"medido por nós"* para **corroborado por
terceiro**.

### E o painel carrega TEMPLATES de setting

Na raiz do `.avpi`, ao lado do manifesto:

```
WAVE-direct.xml       48 KB   Export  WAV   (masterclip)
WAVE-seq-direct.xml   48 KB   Export  WAV   (sequence)
WAVE-import.xml       13 KB   Import
```

Nos três, o campo do nome vem com o literal **`replace-name`** — são **modelos**, e o painel
substitui o nome em tempo de execução. Duas leituras:

- confirma a decisão do nosso ADR 0009 (**embarcar o preset**, não confiar num preset que o
  editor nomeou) e a estende: eles embarcam **import e export**, e **um export por tipo de mob**;
- ⭐ e mostra que **o painel escreve setting do Avid em runtime** — capacidade que não
  tínhamos considerado, já que o painel "não lê disco". Ele não precisa: gera o XML e manda o
  servidor local gravar.

---

## 4. O `mcapi.proto`: segunda verificação oficial, e desta vez fechou 100%

O bundle traz o **protobuf `mcapi` compilado** (gRPC-Web JS), como o painel do Jumper trouxe.
Comparação contra a nossa reconstrução por reflection
([dados/mcapi.proto](dados/mcapi.proto)):

| medida | resultado |
|---|---|
| símbolos `mcapi.*` citados pelo ESION | **220** |
| **rpcs no ESION que não temos** | **0** |
| mensagens/enums no ESION que não temos | **0** (os 9 "faltantes" da primeira passada eram `enum`, não `message`) |

Só sobraram `MCAPIClient` e `MCAPIPromiseClient`, que são **classes geradas pelo gRPC-Web**, não
símbolos do `.proto`.

⭐ **A reconstrução está COMPLETA** — e desta vez contra uma cópia oficial de um build **mais
novo** (25.1.0, out/2025) que o do Jumper. Melhor que o placar anterior, que tinha 1 símbolo
faltando em 262.

---

## 5. Miudezas que valem

- **`allowedDomains`: `acclaim-audio.com`, `localhost:4930`, `localhost:52413`.** Declarar o
  gateway é obrigatório para falar gRPC-Web de dentro do painel.
- **`windowStyle: "fixed"`, 500×500 travado, `singleton: true`.** Painel de gesto, não de
  trabalho.
- ⚠️ **Um caminho de máquina de desenvolvedor ficou no bundle**, num fallback de quando a API
  não responde: `C:\Acclaim-Audio\ESION\server\Export\22_Youth_On_Course_VO_RE22.wav`. Revela o
  layout de instalação no Windows — e é o tipo de coisa que um checklist de release pega.
- **`index.html` é o template cru do `create-react-app`**, com `<title>React App</title>` e
  `%PUBLIC_URL%` não substituído. Não quebra nada (o título de janela vem do manifesto), mas é
  um cheiro de build.
- **O instalador do macOS tem 1,6 GB e o do Windows 156 MB.** A assimetria é o motor de áudio:
  `ESIONserverSupport` sozinho é **1,55 GB** dos 1,6. O README avisa que a primeira instalação
  ainda **baixa ~5 GB**.
- **Licenciamento por iLok** — terceira estratégia distinta que este banco registra, ao lado do
  SDK do aescripts+aeplugins (Chat Video Pro), Stripe no app (Eddie) e LemonSqueezy (CVP).
  ⭐ **iLok é o padrão do mundo do ÁUDIO** — faz sentido para quem já vende plugins de áudio, e
  é o primeiro caso aqui de licenciamento escolhido pelo *mercado* do produto, não pela stack.

---

## 5.5 🆕 ⭐⭐ O protocolo do WebSocket — fechado em 2026-08-24

A primeira rodada deixou isto declarado como não sabido: *"o protocolo do WebSocket em 52413 além do
`REGISTER_REQUEST`"*. O `.avpi` foi reaberto (agora pela via do `.dmg` → `.pkg` → componente
`ESIONserverExtension`) e o bundle **não é obfuscado**: é webpack com módulos nomeados, e há um
`src/types/messageTypes.ts` com o enum inteiro.

### ⚠️⚠️ Primeiro, uma CORREÇÃO: não é uma porta, é uma FAIXA

```
WEBSOCKET_PORTS = [52413, 52414, 52415, 52416, 52417, 52418, 52419, 52420, 52421, 52422]
WEBSOCKET_HOST  = "ws://localhost"
```

O painel tenta as **dez** em sequência (`useMultiPortWebSocketConnection`, com `triedAllPorts`). O
registro anterior — "WebSocket `localhost:52413`" — estava certo sobre a primeira e **errado sobre
o desenho**.

⭐ **É a MESMA estratégia do Quickture** (varredura de faixa), que a
[`paineis-de-terceiros.md` §4](paineis-de-terceiros.md) registrou como alternativa à porta fixa do
Jumper. **Segunda aparição independente:** varrer faixa é o padrão de quem não controla qual porta o
daemon conseguiu abrir.

### ⛔⭐ E uma INCONSISTÊNCIA no produto deles que vale uma pergunta nossa

O `avid-manifest.json` declara:

```json
"allowedDomains": [ "acclaim-audio.com", "localhost:4930", "localhost:52413" ]
```

**Só a primeira porta.** O código varre até a 52422. Ou o `allowedDomains` **não governa `ws://`**,
ou o painel deles quebra silenciosamente quando o daemon cai em 52414+.

🆕 ⭐⭐ **RESPONDIDO em 2026-08-24, por comparação:** o `.avpi` do **Quickture** usa a mesma estratégia
de varredura de faixa — e **declara as dez portas** (`localhost:3030`…`3039`). Dois produtos, mesma
estratégia; o que declara tudo é o que funciona. **Inferência forte: o `allowedDomains` governa sim,
e o manifesto do ESION está INCOMPLETO** — o painel deles quebraria quando o daemon subisse acima da
primeira porta. Ver [`quickture-avid-helper.md` §5](quickture-avid-helper.md).

⚠️ Continua `inferido`: a confirmação definitiva é declarar uma porta a menos num painel nosso e ver
falhar.

### As 19 mensagens

Todas em minúsculas, sem separador, no campo de tipo:

| par | mensagens |
|---|---|
| registro | `registerrequest` · `registerresponse` |
| trabalho | `jobrequest` · `jobresponse` |
| cancelar | `cancelrequest` · `cancelresponse` |
| PDF | `getpdfrequest` · `getpdfresponse` |
| estado | `jobstatus` · `jobstatusresponse` |
| preferências | `preferencesrequest` |
| exibição | `displayrequest` · `displayresponse` |
| fechar | `closerequest` |
| **empurradas pelo servidor** | `progress` · `progressresponse` · `jobprogress` · `processingresponse` · `jobcomplete` |

⭐ **A forma do protocolo:** pares `*request`/`*response` para tudo que o painel inicia, **mais cinco
mensagens que o servidor empurra sem pedido** — progresso em duas granularidades (`progress` e
`jobprogress`), `processingresponse` e `jobcomplete`.

⭐⭐ **A lição de desenho:** o painel **não faz polling de progresso**. Ele registra, manda o job e
**recebe** — e é por isso que o WebSocket existe em vez de HTTP. Compare com o nosso, que usa
**HTTP + SSE** para o mesmo efeito: as duas soluções resolvem *push do servidor para o painel*, que
é o requisito real. *A escolha entre WebSocket e SSE aqui é de gosto, não de capacidade* — SSE
bastaria, porque o tráfego do painel para o servidor é pequeno e requisição/resposta.

⚠️ **`getpdfrequest`** revela uma capacidade que a análise anterior não viu: o painel busca um **PDF**
do servidor (o produto gera relatório de loudness — bate com o componente `ESIONserverPDF` de 14 MB
do instalador e com o `LoudnessMeasurements.tsx` do painel).

### Miudezas do transporte

Biblioteca `react-use-websocket`: heartbeat `ping` a cada 25 s com timeout de 60 s, **limite de 20
reconexões** a 5 s de intervalo. O bundle é nomeado `grpc` no source map — resíduo de scaffold.

⭐ **O painel tem 37 módulos**, e os nomes contam o produto: `DialogueEditor`, `LoudnessMeasurements`,
`PanelProcessingIcons`, `ProgressIndicator`, `SpinnerRainbow`, mais um `PanelContext` +
`panelReducer` + `panelState` (Redux-ish com `useReducer`).

## 5.6 🆕 ⭐ O XML de settings do Avid, agora LIDO

A primeira rodada também deixou em aberto *"se o XML solto em `Settings/` de fato funciona"*. Não dá
para responder isso sem instalar — mas dá para responder **o que ele é**, e o formato é
transferível.

O componente `ESIONserverAvidXML` instala **um** arquivo:
`/Applications/Avid Media Composer/Settings/ESION.xml`, 43 KB.

```xml
<!DOCTYPE Avid:StreamItems SYSTEM "AvidSettingsFile.dtd">
<Avid:StreamItems xmlns:Avid="http://www.avid.com">
  <Avid:XMLFileData>
    <AvProp name="DomainMagic" type="string">Domain</AvProp>
    <AvProp name="DomainKey"   type="char4">1480739396x</AvProp>
    <AvClass id="SETG"/>
    <AvClass id="EXst">
      <AvProp id="ASET" name="name"       type="string">ESION</AvProp>
      <AvProp id="ASET" name="kind"       type="string">Export</AvProp>
      <AvProp id="ASET" name="attributes" type="int16">129</AvProp>
      <AvProp id="ASET" name="type"       type="int16">18</AvProp>
      <AvProp id="EXst" name="iAudioMode" type="int16">5</AvProp>
      …
```

⭐ **A anatomia, que serve para QUALQUER setting do Avid:**

| peça | papel |
|---|---|
| `DomainMagic` / `DomainKey` | cabeçalho do domínio (`char4`) |
| `AvClass id="SETG"` | é uma *setting* |
| `AvClass id="EXst"` | a espécie — aqui **Export** |
| `AvProp id="ASET"` | os 4 campos genéricos de toda setting: `name`, `kind`, `attributes`, `type` |
| `AvProp id="EXst"` | as 21 propriedades específicas de export |
| `AvProp id="ATTR"` | ⭐ **395 ocorrências** — o blob de atributos, onde mora o grosso do preset |

⭐⭐ **O `ATTR` é a mesma família que a pendência da cor de etiqueta de clipe** (`ATTB`/`_USER`,
[`../../protocolos/projeto-avid/`](../../protocolos/projeto-avid/)) — o Avid usa um armazém de
atributos genérico em toda parte, e ele é **legível em XML**. Isso é uma porta de entrada barata
para entender formatos do Avid sem tocar em binário.

⚠️ E o painel **carrega mais três** desses XMLs dentro do `.avpi`: `WAVE-direct.xml`,
`WAVE-seq-direct.xml` (~48 KB cada, export) e `WAVE-import.xml` (~13 KB, import). Confirma o §3: o
produto distribui os próprios presets **como XML**, não como blob binário.

---

## 6. O que isto muda para os nossos apps

1. ⭐ **O De Lá Pra Cá pode receber a timeline por arrasto.** Hoje a rota `/mc/sequences`
   enumera bins a ~500 ms cada — e no MC 25.6, sem `GetListOfWindows`, pergunta a **todas**. Um
   drop entrega `id` + `type: "sequence"` **de graça e instantaneamente**, e resolve de uma vez
   o custo *e* a falta de pré-seleção. É a melhoria de maior relação valor/esforço no painel.
2. **`in`/`out` vêm no payload** — abre relinkar/processar só um trecho, que hoje não temos como
   pedir.
3. **Testar a rota do XML solto em `Settings/`** pode eliminar a exigência de fechar o MC para
   instalar nosso preset de export.
4. **Não precisamos de painel assinado nem de escopo novo** para nada disso: `general` basta, e
   o drop não passa pela API.

---

## Fontes

`ESIONStudioExtension_Installer_Win.exe` (156 MB, Inno Setup, assinado EV Acclaim Audio Corp.) e
`ESIONstudioMC_Extension_Installer_SiliconMac.dmg` (1,6 GB), baixados pelo usuário e analisados
**sem instalar e sem executar nada**, em 2026-08-15.

**Rota de extração** (o `.exe` do Inno não abriu: o 7-Zip não suporta o formato, e o payload é
LZMA sólido — a análise saiu inteira do `.dmg`):

```
.dmg → 7z (HFS aninhado, aberto automaticamente)
     → ESIONstudioExtension_Installer-signed.pkg (xar)
     → sub-.pkg → Payload (cpio+gzip) → arquivos
     → esion-studio_25.1.0-...avpi (ZIP) → manifesto + src/main.js
```

**Régua respeitada** (ver [transversal/analise-de-executaveis.md](../../transversal/analise-de-executaveis.md)):
foram lidos **manifesto, `PackageInfo`, `Bom` (lista de caminhos), XML de settings, constantes de
MIME, nomes de função e o formato do payload do drop** — arquitetura e protocolo. **Não** foi
descompilada a lógica do motor de áudio, **não** foi tocado o licenciamento/iLok, e o
`sourceMappingURL` embutido no bundle **não teve o `sourcesContent` lido**. O payload de 1,55 GB
(`ESIONserverSupport`) foi deliberadamente **não extraído** — é o motor, e é justamente o que a
régua manda não abrir.

**O que NÃO foi feito, e portanto não se sabe** — atualizado em 2026-08-24:

- ~~o protocolo do WebSocket além do `REGISTER_REQUEST`~~ ✅ **fechado (§5.5)**: 19 mensagens, e a
  correção de que são **10 portas**, não uma.
- ~~o que é o XML solto em `Settings/`~~ ✅ **lido (§5.6)** — a anatomia está registrada. ⚠️ **Se ele
  FUNCIONA sem o MC reindexar continua sem resposta**: isso exige instalar, e nada foi instalado.
- ⛔ o significado de `head`/`systemID`/`systemType` no payload do drop — **continua aberto**.
- 🆕 ⛔ **o `allowedDomains` filtra `ws://`?** (§5.5) — pergunta nova, sobre o Panel SDK, medível.
- 🆕 ⛔ o daemon (`ESIONserverExtension` é só o painel; o motor de ~1,5 GB não foi aberto).

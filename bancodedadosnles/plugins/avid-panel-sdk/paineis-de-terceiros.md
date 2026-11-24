# Painéis de terceiros — o que dois parceiros oficiais fazem

Descoberto em **2026-08-08** analisando os instaladores de dois produtos comerciais que são
**parceiros oficiais da Avid** e estão listados em avid.com/media-composer/extensions. Ambos
receberam o SDK pela via oficial — o mesmo que aqui foi reconstruído por engenharia reversa.

| Produto | Empresa | Painel | Versão do painel |
|---|---|---|---|
| **Jumper** | Witchcraft Software AB | `com.witchcraft.jumper.avid` | 1.0.1 |
| **Quickture** | Quickture | `com.quickture.panel` | 1.0.5 |

Método: extração dos instaladores (`.dmg` montado read-only, `.pkg` via `xar`+`cpio`), leitura
dos `.avpi` (ZIP) e dos bundles JS. **Nada instalado, nada executado.** Ver [fontes.md](fontes.md).

> Por que isto vale: são a **referência canônica de uso do SDK** por quem tem a documentação.
> Onde eles confirmam o que estava `inferido`, promove. Onde divergem do nosso desenho, é sinal.

---

## 1. ⭐ Validação independente do `mcapi.proto`

O `AvidFrontend/index.html` do Jumper embute o **protobuf do `mcapi` compilado para JavaScript**
(gRPC-Web, `MCAPIClient` e `MCAPIPromiseClient`) — gerado a partir do `.proto` **oficial**.

Comparando com [dados/mcapi.proto](dados/mcapi.proto), reconstruído aqui por reflection:

| | símbolos |
|---|---|
| `mcapi.proto` reconstruído (reflection) | **281** mensagens/enums, 60 rpcs |
| JS oficial do Jumper | **262** símbolos |
| **Presentes no oficial e ausentes no nosso** | **1** — `apiScope` |

**A reconstrução por reflection estava essencialmente completa.** Um único símbolo escapou. Isso
promove a confiança do `mcapi.proto` inteiro: não é mais "reconstruído, pode faltar coisa" — é
"conferido contra um artefato gerado do `.proto` oficial".

### `apiScope` (`confirmado`, novo)

Enum presente no protobuf oficial e ausente do nosso. Pelo nome e pelo contexto, é o que liga o
`usesApi` do manifesto ao serviço gRPC — provavelmente o campo que declara/valida o escopo de
uma chamada. **Contrato pendente**: só o nome foi recuperado, não os valores.

---

## 2. ⭐ `usesApi` — três escopos promovidos a `confirmado`

O manifesto do **Jumper** declara quatro APIs:

```json
"usesApi": [
  "avid.mediacomposer.general",
  "avid.mediacomposer.timelineEditing",
  "avid.mediacomposer.command",
  "avid.mediacomposer.transportcontrols"
]
```

O do **Quickture** declara apenas `avid.mediacomposer.general`.

Isso **promove de `inferido` para `confirmado`** três entradas de `apis_host` em
[dados/runtime.json](dados/runtime.json): `timelineEditing`, `command` e `transportcontrols`.
Não são mais palpite de nomenclatura — estão num produto em produção, escritos por quem tem a
documentação.

O catálogo conhecido fica em cinco: `general`, `SRT` (Huddle), `timelineEditing`, `command`,
`transportcontrols`. **O contrato de cada um continua `pendente`** — sabemos que existem e que
são aceitos, não o que habilitam.

Observação útil: o Quickture faz um produto inteiro de leitura de bins, montagem de sequência e
exportação **usando só `general`**. Ou seja, os outros escopos não são obrigatórios para
trabalhar com bin e sequência — o trabalho pesado deles vai por outro caminho (§4).

---

## 3. ⭐ O `url` do `uiItem` aceita HTTP absoluto — e isso muda o desenho

Estava registrado que o `url` é **relativo, servido pelo esquema `avpi://` do bundle**. Isso vale
para o Quickture. **Mas o Jumper faz diferente:**

```json
"uiItems": [{
  "type": "dropdown", "menuName": "Tools", "id": "Jumper",
  "url": "http://127.0.0.1:6699/avid/serve_frontend"
}],
"allowedDomains": ["localhost:6699", "127.0.0.1:6699", "download.getjumper.io", "getjumper.io"]
```

O `.avpi` do Jumper tem **apenas dois arquivos**: `avid-manifest.json` e `static/application.svg`
(o ícone). Não há UI dentro do pacote. A página vem do backend local na 6699, servida pela rota
`avid_module.serve_frontend` (confirmado por string no binário; há também
`standalone_module.serve_frontend` — **a mesma UI SvelteKit serve o painel Avid e o app
standalone**).

### Por que isso importa muito

**Servir o painel do próprio backend local torna tudo same-origin.**

O desenho registrado aqui (Órbita) resolve a autenticação painel→app usando `Origin: avpi://`
como identidade, e convive com CORS, preflight e a restrição de header custom
(ver `rede_do_painel` em [dados/runtime.json](dados/runtime.json)). Esse trabalho todo existe
porque a página vem de `avpi://` e o app está em `127.0.0.1`.

No modelo do Jumper, a página **é servida pelo app**. Origem e destino são o mesmo
`http://127.0.0.1:6699`. Resultado:

- **sem CORS, sem preflight, sem header bloqueado** — é same-origin
- **sem necessidade de segredo de pareamento** no `.avpi`
- **a UI atualiza sem reinstalar o painel** — o `.avpi` é só manifesto + ícone e praticamente
  nunca muda (versão 1.0.1 contra 2026.07.27/3283 do app)
- em compensação: **se o backend não está de pé, o painel não abre** — nem mostra erro próprio,
  porque não há UI local para mostrar

⚠️ **A contrapartida — MEDIDA em 2026-08-09, ver §7.1:** com a página vinda de
`http://127.0.0.1:<porta>`, a estratégia de "origem como identidade" de `rede_do_painel` não se
aplica. E é pior que "deixa de ser necessária": **um `GET` same-origin não manda `Origin`
nenhum**. Quem trocar `avpi://` por "a própria origem" e continuar olhando o `Origin` vai ver o
painel carregar e todo `GET` voltar 401. O cabeçalho que serve é `Sec-Fetch-Site: same-origin`.

✅ **O consentimento de localhost NÃO aparece** na navegação de topo (medido, §7.1). Era a
dúvida que mais pesava contra adotar este modelo; não se confirmou.

---

## 4. Duas estratégias de descoberta do app local

### Jumper — porta fixa

`6699`, declarada no manifesto e no `url`. Simples, e o preço é o conflito de porta.

### Quickture — varredura de faixa + magic string (`confirmado`)

O `.avpi` do Quickture embute um **loader** (`static/index.html`, título "Quickture Loader", ~245 KB
de React) cuja função é achar o helper local e carregar a UI real dele. O padrão, lido do bundle:

- monta a faixa `3030..3039` (`Array.from({length:10}, (_,i) => 3030+i)`)
- para cada porta, faz `GET http://localhost:<porta>`
- aceita a porta se a resposta for `ok` **e o corpo contiver a string `"Quickture"`**
- guarda o resultado em `localStorage` sob a chave `quicktureHelperPort`

O `allowedDomains` do manifesto libera `localhost:3000`–`3039` e `localhost:5000` — faixa maior
que a varrida, provavelmente folga para dev/variantes.

**Leitura:** é descoberta de serviço sem porta fixa, resolvendo conflito de porta ao custo de até
10 requisições no primeiro uso. A validação é por **magic string no corpo**, não por handshake —
identifica o serviço certo, não autentica nada.

### Qual copiar

Para o nosso caso (`roadmap.md`), o modelo do **Jumper é mais simples e resolve o problema de
origem de graça**. O do Quickture só se paga quando conflito de porta for real.

---

## 5. O painel pode ser fino a ponto de não falar com o MC

O achado mais surpreendente. O loader do Quickture **não usa o barramento `mcapi`** — as
ocorrências de `onEvent` no bundle são internals do React, não QWebChannel.

A integração com o Media Composer deles é feita **pelo helper**, um daemon **Rust + Tauri** que
traz `tonic` (gRPC), `warp` (HTTP local) e — notável — as crates **`avb-0.3.0`** (bins `.avb`) e
**`cfb-0.7.3`** (Compound File Binary, base do `.aaf` e do `.mdb`). Ou seja: falam gRPC com o MC
**e** leem estrutura de projeto direto do disco, em Rust.

Isso confirma que **a forma "app externo dirige o MC, painel é só janela"** — registrada aqui
como a inversão em relação ao Premiere/Resolve, e usada em produção pelo Órbita — é também o que
um parceiro oficial faz. Não é contorno de quem não tem SDK; é o desenho certo.

E as crates `avb`/`cfb` em Rust convergem com o `LEITOR DE MDB` e o backend AVB do Relinker.

---

## 6. `subscribesToChannels` vazio nos dois

```json
"subscribesToChannels": [],
"entitlements": []
```

**Idêntico nos dois manifestos.** Nenhum dos dois assina canal de evento, e nenhum declara
entitlement.

Isso é confirmação externa forte do que foi medido aqui: a API tem **piso de ~500 ms por chamada
e nenhum canal de evento útil**, logo *observar estado continuamente não cabe; ler sob demanda,
sim* (ver `mcapi-grpc.json`). Dois produtos comerciais chegaram à mesma conclusão de forma
independente. **O desenho do Órbita está alinhado com o estado da arte.**

---

## 7. Eventos vistos no frontend do Jumper

O `AvidFrontend` referencia, além dos já catalogados em [dados/mcapi.json](dados/mcapi.json)
(`BinRowSelectionChanged`, `PlayPositionChangeEvent`, `AboutToPlayEvent`, `DonePlayingEvent`,
`ActiveMonitorChangedEvent`, `MobAdded`, `MobDeleted`, `MobLoadedInViewer`):

| Evento | Status |
|---|---|
| `ImportFileStarted` | **novo aqui** (`inferido`) |
| `ImportFileFinished` | **novo aqui** (`inferido`) |
| `DoCommandFinished` | **novo aqui** (`inferido`) |

⚠️ **Refina — não contradiz — o achado de que "In/Out não emite evento".** Continua não havendo
canal de evento de *estado*. Mas parece haver **notificação de conclusão para operações
assíncronas específicas** (`ImportFile`, `DoCommand`), que é outra coisa: permite saber que um
import ou um comando terminou sem ficar em polling.

`inferido` porque vieram de string no bundle, sem observar o evento chegando. **Se confirmado,
muda o desenho de qualquer fluxo que hoje faz polling depois de `DoCommand`** — vale medir.

---

## 7.1 ⭐ Medido em 2026-08-09: o painel servido por HTTP, na prática

Implementamos o modelo do Jumper no Órbita e medimos dentro do MC 25.12. Três achados
que valem mais que a leitura dos manifestos.

**a) NÃO há diálogo de consentimento de localhost.** A navegação de topo de `avpi://`
para `http://127.0.0.1:<porta>` passa direto — o `allowedDomains` do manifesto basta.
Era o risco apontado como capaz de derrubar o desenho; não se materializou.

**b) ⚠️ Uma requisição `GET` same-origin NÃO manda `Origin`.** O navegador só o envia
em CORS e em POST. Quem tentar identificar a página servida pelo `Origin` vai ver o
painel **carregar** e **toda chamada `GET` voltar 401** — com os POSTs funcionando, o
que torna o sintoma confuso. O cabeçalho a usar é **`Sec-Fetch-Site: same-origin`**,
que é *forbidden header* igual ao `Origin` (um site chega com `cross-site`).

Os cabeçalhos completos que o painel envia estão em
[dados/runtime.json](dados/runtime.json) → `headers_que_o_painel_manda`.

**d) 🆕 ⚠️⚠️ O GET simples do loader também precisa de `Access-Control-Allow-Origin`**
(medido 2026-09-10, MC 25.6 / Windows, no Ciclo Assist).

Já estava registrado que o painel **não** tem passe livre de CORS — mas só para
*preflight* e header custom. Falta o caso que **todo loader faz primeiro**: um `GET`
simples de `avpi://` para `http://127.0.0.1:<porta>/saude`.

Sem `Access-Control-Allow-Origin` na resposta, o browser abre a conexão, o servidor
responde 200, e a página **não recebe nada**: o `fetch` rejeita.

⭐ **E o sintoma acusa a peça errada.** Um loader tem um `catch` só, para "não achei o
serviço" — e `fetch` rejeita igual para *não conectei* e para *conectei e não pude ler*.
Resultado: o painel anuncia **"o serviço não está rodando" com o serviço rodando**, e
manda depurar o serviço, que está certo.

**Como distinguir em segundos:** `netstat` do lado do servidor. Se as conexões do painel
aparecem em `TIME_WAIT`, o TCP aconteceu e o problema é CORS. Foi assim que se achou.

⛔ **A correção é ecoar a origem exata (`avpi://`), nunca `*`** — um curinga abriria o
serviço local para qualquer aba aberta no navegador do editor.

**c) ⭐ O painel tem menu de contexto com RELOAD.** Botão direito numa área vazia →
`Back / Forward / Reload / Save page / View page source`. **Fechar e reabrir o painel
pelo menu Tools não recarrega a página** (fica em cache); o Reload recarrega sem
reiniciar o Media Composer. Isso transforma o ciclo de desenvolvimento de painel:
editar o HTML servido → botão direito → Reload. Ver `menu_de_contexto_do_painel` no
`runtime.json`.

## 8. Resumo do que mudou no banco

| Item | Antes | Agora |
|---|---|---|
| `mcapi.proto` reconstruído | "pode faltar coisa" | conferido contra o oficial: falta 1 símbolo |
| `apiScope` | inexistente | `confirmado` que existe; contrato `pendente` |
| `usesApi`: `command`, `timelineEditing`, `transportcontrols` | `inferido` | **`confirmado`** |
| `url` do `uiItem` | "relativo, `avpi://`" | **também aceita HTTP absoluto para localhost** |
| Estratégia de descoberta do app local | porta fixa | duas estratégias documentadas |
| `subscribesToChannels` vazio | nossa escolha | **prática dos dois parceiros oficiais** |
| `ImportFileStarted/Finished`, `DoCommandFinished` | inexistentes | `inferido`, a medir |
| Consentimento de localhost na navegação | risco em aberto | **não acontece** (`confirmado`) |
| Como a página servida se identifica | supunha-se `Origin` | **`Sec-Fetch-Site`** — GET não manda `Origin` (`confirmado`) |
| CORS no GET simples do loader | só preflight documentado | **`Access-Control-Allow-Origin` é obrigatório**; sem ele o loader mente (`confirmado`) |
| Recarregar o painel sem reiniciar o MC | desconhecido | **botão direito → Reload** (`confirmado`) |

## Ver também

- [arquitetura.md](arquitetura.md) · [dados/runtime.json](dados/runtime.json) ·
  [dados/manifest-schema.json](dados/manifest-schema.json) · [dados/mcapi.proto](dados/mcapi.proto)
- `../../../EDT-ASSIST/pesquisa/` — a dissecação completa dos dois produtos (arquitetura de
  produto e camada de IA; aqui fica só o que é API de NLE)

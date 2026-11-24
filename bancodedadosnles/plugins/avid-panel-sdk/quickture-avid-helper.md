# Quickture Avid Helper — o 3º painel do Avid, e a validação que ele NÃO trouxe

Décimo caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md).
Continuação de [`../premiere-cep/quickture-ppro.md`](../premiere-cep/quickture-ppro.md) — mesmo
produto, outro NLE.

**Material:** `Quickture_Windows_Avid_Helper_1.6.3.msi` (78 MB), aberto em 2026-08-24.

---

## 1. O que vem na caixa

| peça | tamanho | o que é |
|---|---|---|
| `Path` (PE) | 40 MB | o **helper** — processo local |
| `.avpi` | 128 KB | o painel do Media Composer |
| `main-*.js` + `.js.map` | 6,2 MB + 20 MB | ⭐ **o MESMO bundle React do painel CEP do Premiere** |
| `ffmpeg.exe` / `ffprobe.exe` | 79 MB cada | embarcados |
| EULA | 280 KB | PDF |

⭐ **A UI é uma só, servida em dois hosts.** O mesmo React roda dentro do CEP no Premiere e dentro
do `.avpi` no Media Composer. O que muda é a camada que fala com o NLE.

⭐ **E o ffmpeg é embarcado**, como no Órbita — 158 MB dos 78 MB compactados. Terceira aparição do
padrão *"não peça ao usuário para instalar ffmpeg"*.

---

## 2. ⭐⭐ O helper fala gRPC DIRETO — como o nosso, não como o ESION

`mcapi` aparece **184×** e `grpc` **83×** no binário do helper. Ele não passa pelo painel nem pelo
gateway: abre o canal gRPC contra o backend do MC.

⭐ **É a mesma arquitetura do `_DeLaPraCa`**, e o contraste com o ESION fecha o triângulo:

| | quem fala com o MC | por onde |
|---|---|---|
| **ESION** | o **painel** | gRPC-Web no gateway `4930`, com token (rota oficial) |
| **Quickture** | o **helper** | gRPC direto no backend |
| **_DeLaPraCa** | o **serviço** | gRPC direto no backend `9100`, sem token |

⭐ **Dois de três produtos comerciais escolhem o backend direto.** A rota oficial pelo gateway é a
minoria — o que reposiciona a nossa escolha: não é atalho, é o que a maioria faz.

---

## 3. ⛔ A validação que este caso NÃO trouxe — e isso é resultado

Extraí as **32 rotas gRPC** que o helper usa e cruzei com o
[`dados/mcapi.proto`](dados/mcapi.proto) e o [`dados/mcapi-grpc.json`](dados/mcapi-grpc.json).

**31 das 32 já estavam no banco.** A única que não casou foi `CreateCustomColumns` (plural), ao
lado da `CreateCustomColumn` que já existe — provavelmente variante de nome, não rpc nova.

⭐⭐ **Isso é uma boa notícia sobre trabalho antigo, não uma decepção:** o `mcapi.proto` foi extraído
por **gRPC reflection**, e a reflection **entregou a superfície completa**. Um produto comercial em
produção não usa nada que não estivesse lá. *A reflection não deixou nada para trás* — e agora há
prova independente disso.

⚠️ **A lição de calibração:** eu esperava rpc novas e não havia. O valor deste caso não está no
inventário, está em **qual subconjunto um produto real escolhe** — que é informação diferente.

---

## 4. O que o subconjunto usado revela

As 32 rotas, por família:

| família | rotas |
|---|---|
| **marcadores** | `AddMarker` · `AddMarkers` · `ChangeMarker` · `DeleteMarkers` · `GetMarkers` |
| **bins** | `CreateBin` · `OpenBin` · `CloseBin` · `GetBins` · `GetBinFromMob` · `GetListOfBinItems` · `MoveBinItems` · `DuplicateBinItems` · `SelectMobsInBin` |
| **colunas** | ⭐ `CreateCustomColumn(s)` · `GetBinColumnInfo` |
| **mob** | `GetMobInfo` · ⭐ **`SetMobInfo`** · `CreateSubClip` |
| **transporte** | ⭐ **`SetPosition`** · `StartPlay` · `StopPlay` · `LoadMobsIntoViewer` |
| **arquivos** | `ImportFile` · `ExportFile` |
| **settings** | `GetListOfExportSettings` · `GetListOfImportSettings` · ⭐ `LoadSetting` |
| **sessão** | `GetAppInfo` · `GetOpenProjectInfo` · `Echo` |

### ⭐⭐ Três colunas do mapa que isto preenche

1. **Marcadores no Media Composer** — o
   [mapa §J.2](../../transversal/operacoes-de-nle.md) tinha a coluna do MC como ⛔. **Há família
   completa** (criar um, criar vários, alterar, apagar, ler), **em uso de produção**.
2. **ESCREVER metadado no Avid** — o §G dizia *"`SetMetadata` não medido"*. **`SetMobInfo` é usado
   por um produto que vende**, e ⭐ `CreateCustomColumn` + `GetBinColumnInfo` mostram que dá para
   **criar coluna própria na bin** — é o análogo Avid do XMP privado do Premiere: *onde um plugin
   pendura o próprio dado dentro do projeto do usuário*.
3. **`SetPosition` existe mesmo** — o banco registra que ele **não existe no MC 2025.6** e que foi
   preciso mover a agulha por `DoCommand` + teclado simulado. Um produto comercial o usa. ⭐
   **Confirma que a ausência é de VERSÃO, não de invenção nossa** — exatamente o que o
   `SetPosition_DEPENDE_DA_VERSAO` supunha.

⭐ **`LoadSetting`** conversa direto com o achado do ESION: se um produto instala um XML de setting
solto em `Settings/` (ver [`esion-arquitetura.md` §5.6](esion-arquitetura.md)), há um rpc para
**carregá-lo**. As duas metades se encaixam.

---

## 5. ⭐⭐ O manifesto responde a pergunta que o ESION abriu

Uma etapa atrás ficou aberto: *o `allowedDomains` filtra `ws://`?* — porque o ESION varre
**10 portas** (52413–52422) e declara **só a primeira**.

O `avid-manifest.json` do Quickture:

```json
"allowedDomains": [ "localhost:3000",
  "localhost:3030", "localhost:3031", … "localhost:3039",
  "localhost:5000", "quickture.com", … ]
```

⭐⭐ **Ele declara a FAIXA INTEIRA que varre.** Dois produtos, mesma estratégia de varredura, e o que
declara tudo é o que funciona. **Inferência forte: o `allowedDomains` governa sim, e o manifesto do
ESION está incompleto** — o painel deles quebraria quando o daemon subisse acima da primeira porta.

⚠️ Continua sendo `inferido`, não medido: a confirmação definitiva é declarar uma porta a menos num
painel nosso e ver falhar.

### E o resto do manifesto conta o produto

- `url: "static/index.html"` — painel **servido de dentro do `.avpi`**, não de `http://localhost`
  como Jumper e ESION. ⭐ **As duas formas do `url` estão exercitadas por produtos reais.**
- `windowStyle: floating`, `singleton: true`, 800×800, menu `Tools`.
- ⚠️⚠️ **`allowedDomains` inclui muito terceiro:** `gleap.io` (suporte), `pusher.com`,
  `browser-intake-datadoghq.com` (Datadog RUM), `cloudflareinsights.com`, `googletagmanager.com`,
  `consent.cookiebot.eu`, `youtube.com`, `webflow.io`. **Telemetria e chat de terceiros rodando
  dentro do Media Composer.**
- ⭐ **`pusher.com` muda a leitura da arquitetura:** mensageria em tempo real **por serviço de
  nuvem**. O painel do Avid recebe eventos **da nuvem**, não de um daemon local — diferente do
  ESION (WebSocket local) e diferente do nosso (SSE local).

---

## 6. Miudeza que vale: preferências por página descartável

O `.avpi` traz `set-color-scheme.html` e `set-user-interface-language.html` (+21 idiomas). Cada uma
lê um parâmetro da URL, grava em `localStorage` e **se fecha** (`if (window.opener) window.close()`).

⭐ Não é convenção do Panel SDK — é truque do produto, e é um lembrete do que o
[mapa §M](../../transversal/operacoes-de-nle.md) já diz: **metade da superfície de um painel é a do
navegador**. `localStorage` persiste na webview do Avid, e uma página de uma linha basta para
escrever nele de fora do fluxo normal.

---

## ⚠️ A régua desta rodada

- **Lido:** manifesto, estrutura do MSI, nomes de `.pdb`, rotas gRPC e strings dirigidas do binário
  do helper; as duas páginas HTML de preferência.
- ⛔ **O binário do helper NÃO foi descompilado** — não foi preciso: as rotas gRPC e o manifesto
  responderam tudo.
- **Não lido:** o `main-*.js.map` de 20 MB (o mesmo do painel CEP, já fora de escopo lá); o
  instalador macOS (183 MB), redundante.
- **Licenciamento não tocado. Nada instalado, nada executado.**

## Buracos

| # | pergunta |
|---|---|
| 1 | `CreateCustomColumns` (plural) é rpc real ou variante de nome? |
| 2 | O `allowedDomains` filtra `ws://` — confirmar medindo, não por comparação |
| 3 | O que trafega pelo `pusher.com` (o painel do Avid recebe evento de nuvem) |
| 4 | `SetMobInfo`: quais campos aceitam escrita, e o que é somente leitura |

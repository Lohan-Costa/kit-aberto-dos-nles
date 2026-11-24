# Panel SDK do Media Composer — estrutura e como foi descoberto

Tudo aqui saiu da instalação local do **Media Composer 25.12.0.58863** (macOS 24.6.0), em
2026-08-07, sem acesso ao SDK oficial. O método foi: procurar por `*panel*` na instalação,
achar o pacote de exemplo, descompactá-lo, e extrair strings dos binários.

## O caminho da descoberta

1. `find` por `*panel*` em `/Library/Application Support/Avid` → apareceram
   `PanelSDKPlugins/` e `Avid Media Composer/PanelSDK.json`.
2. Dentro de `PanelSDKPlugins/` havia **um painel real já instalado**: `avid-huddle.avpi`
   (12.613 bytes). `file` disse *Zip archive*. Descompactado → `avid-manifest.json` +
   `static/application.svg`. **Esse arquivo é a fonte do schema do manifesto.**
3. `strings` no binário `avid-api-gateway` (Go) → nomes de serviço gRPC, `avid-manifest.json`,
   `IsDevMode`, `AuthManager`.
4. `avid-api-gateway --help` → lista completa de flags (o binário aceita `--help` e imprime).
5. `strings` no `AvidMediaComposer` (236 MB) → feature flags, comandos de console, ids de API.

## Camadas

```
  painel (HTML/JS em QtWebEngine)
        |                    \
   qwebchannel.js         gRPC-Web / WebSocket
   (bridge Qt -> C++)            |
                          avid-api-gateway  (Go, proxy)
                                 |  gRPC
                          Media Composer (backend)
```

O gateway NÃO é o dono da lógica — é proxy. Quem serve as APIs é o MC. O gateway faz
autenticação (token por plugin), CORS e a ponte gRPC-Web, porque um navegador não fala gRPC puro.

### Autenticação

`aag.PluginRepo` expõe: `GetPluginList`, `GetPluginAccessToken`, `GetDirectoryList`,
`GetFileContent`, `HealthCheck`, `RegisterService`. O `AuthManager` tem
`GenerateToken` / `RegisterToken` / `FindToken` / `VerifyAccess` / `IsValid` / `IsDevMode`.

Ou seja: cada painel recebe um token e o gateway valida acesso por `usesApi`/`entitlements`
declarados no manifesto. **É aqui que o modo desenvolvedor entra** — presumivelmente afrouxa
essa verificação para painéis não registrados na Avid. (`hipotese`, não testado.)

### Servir o conteúdo do painel

`GetFileContent` e `GetDirectoryList`, mais o campo proto `relative_path`, indicam que o gateway
**serve os arquivos de dentro do `.avpi`**. É o que já acontece com o ícone: o Huddle declara
`"icon": "static/application.svg"`, caminho relativo dentro do ZIP.

Por analogia, `"url"` deveria aceitar caminho relativo e servir um HTML local do bundle
(**`hipotese`** — o Huddle usa `https://mcwebpanel.avid.com`, remoto, então não há amostra real
de painel local). Se NÃO aceitar, o painel precisa ser hospedado e o domínio declarado em
`allowedDomains`.

## Portas e configuração

Dois arquivos de config, ambos em `/Library/Application Support/Avid/`:

| arquivo | conteúdo real lido | papel |
|---|---|---|
| `Avid Media Composer/PanelSDK.json` | `{"ports": "9100-9110"}` | faixa de portas dos painéis |
| `APIGateway/config.json` | `{"apiPort": 4920, "pluginPort": 4930}` | portas do gateway |

O gateway por padrão faz bind em `[::1]` (só loopback) e `--allow_all_origins` vem `true`.
Default de `--plugin_path` é `/Library/Application Support/Avid/PanelSDKPlugins` — e **é flag**,
ou seja, dá para apontar para outra pasta ao subir o gateway manualmente (útil para dev sem `sudo`).

### ⚠️ Com o Media Composer FECHADO, conectar custa 2,0 s

`medido` (Ciclo Assist, Windows, 2026-09-14): abrir a ponte gRPC em `[::1]:9100` com o MC
fechado leva **2,0 s** até o cliente desistir, e o custo se repete a cada tentativa (a
segunda chamada seguida deu 2,05 s). Não é erro imediato: quem chamar "qual é o projeto
aberto?" dentro de uma ferramenta paga isso por chamada, e duas ferramentas no mesmo turno
do modelo viram 4 s de espera para descobrir duas vezes a mesma ausência.

⇒ Quem consulta o MC em caminho quente **cacheia também a AUSÊNCIA**, por pouco tempo
(30 s no Ciclo Assist): guardar "não há projeto" para sempre faria o editor abrir o Media
Composer e o plugin continuar dizendo que não há.

### ⛔ Trocar de projeto não avisa ninguém

`medido` (Ciclo Assist, 2026-09-14, MC aberto no Windows): **não há evento de abrir, fechar
ou trocar de projeto** — coerente com o catálogo de `onEvent`
([dados/mcapi.json](dados/mcapi.json)), onde ampliar o `usesApi` aos cinco canais não
acrescentou tipo nenhum e nada tem "Project" no nome.

Quem precisa saber o projeto aberto **sonda** `GetOpenProjectInfo`, e a sondagem custa
**0,5 a 0,75 s por chamada** — cinco medições com conexão nova e cinco reaproveitando a
mesma conexão deram o mesmo tempo, ou seja **o piso é da API, não do handshake**.

⇒ O padrão que funciona num painel: perguntar **no gesto** (a aba abriu, a janela voltou
ao foco — que é o que o editor faz logo depois de trocar de projeto) mais uma sondagem
lenta enquanto a tela estiver à vista. Relógio de poucos segundos batendo no MC está fora.

⚠️ E o preço de não sondar é concreto: um plugin que cacheie o caminho do projeto "para
não pagar 500 ms por turno" responde com o material do projeto ANTERIOR depois da troca,
calado, com o editor olhando as bins do novo.

## Feature flag de desenvolvimento

No binário do MC, as feature flags aparecem como pares *caminho + descrição*. A relevante:

```
/Media Composer/3PDevPanelSDK
Enable 3P development for Panel SDK.
```

("3P" = third party.) Vizinhas na mesma tabela: `/Media Composer/CloudUXSSO`,
`/Media Composer/MultiCamFullQuality`, etc. — é a tabela geral de flags do produto.

**Como ligar: `pendente`.** A tabela existe, o mecanismo de escrita não foi identificado.
Candidatos a investigar: `Site Settings.xml` (o binário fala em "Site Settings" e
`siteSettingsContents`), console command, ou plist de preferências. Nenhum testado.

## Comandos de console

Extraídos literalmente do binário, sob o help "Panel SDK Console commands":

- `panelsdk reinit` — *"start the gateway if needed, re-register MC service, and reload all plugins."*
- `panelsdk console on` / `off` — *"log web page console messages to the Console Command window."*

Há também a mensagem de erro *"Panel has lost connection to the gateway. Try running the
`panelsdk reinit` console command."* — confirma que reinit é o remédio padrão.

Outras strings do subsistema: `IsPanelSDKEnabled()`, `avpi://%1` (esquema de URL para instalar
painel?), `PanelWindowManager.cpp`, `PanelSDKMenu.cpp`, `PanelSDK_25.12`.

## O que ainda não se sabe

| item | estado | caminho para resolver |
|---|---|---|
| Assinatura dos métodos das APIs (`.proto`) | `pendente` | gRPC server reflection contra o gateway rodando (`reflection.proto` está linkado no MC) |
| Como ligar `/Media Composer/3PDevPanelSDK` | `pendente` | investigar `Site Settings.xml` / console / plist |
| `url` aceita caminho relativo (HTML local)? | `hipotese` | instalar o painel-teste e observar |
| Painel não-assinado carrega sem dev mode? | `pendente` | instalar o painel-teste e observar |
| Valores válidos de `entitlements` e `subscribesToChannels` | `pendente` | amostra do Huddle traz ambos vazios |
| `category` além de `"suite-plugin"` | `pendente` | só um valor observado |
| Semântica de `avpi://` | `pendente` | string solta no binário |

## Comparação com o CEP do Premiere

| | Premiere CEP | Avid Panel SDK |
|---|---|---|
| SDK público | sim, documentado | **não** — onboarding fechado |
| pacote | pasta + `CSXS/manifest.xml` | `.avpi` (ZIP) + `avid-manifest.json` |
| local | `~/Library/.../CEP/extensions/` (usuário) | `/Library/Application Support/Avid/PanelSDKPlugins/` (**sistema, sudo**) |
| painel não-assinado | `PlayerDebugMode 1` | flag `3PDevPanelSDK` (mecanismo a descobrir) |
| recarregar | fechar+reabrir o painel | `panelsdk reinit` no Console |
| bridge | Node + ExtendScript | QWebChannel + gRPC-Web com token |
| autenticação | nenhuma | token por plugin + entitlements |

A diferença estrutural: o CEP confia no painel; o Avid autentica. Isso é o que torna o caminho
não-oficial mais incerto aqui do que lá.

## 🆕 ⭐ Gateway é autenticado; o 9100 NÃO — medido (2026-10-18, MC 24.6.0/Windows)

Contraste decisivo para o modelo "app por fora":
- **9100 (`mcapi.MCAPI`, backend do MC):** responde a cliente externo com `RequestHeader` VAZIO (sem token). Ver
  `ativar-no-2021-ftf.md` §Teste B.
- **4920 (`aag.PluginRepo`, gateway):** `GetPluginList` chamado de fora (gRPC genérico, serializer pass-through, sem
  o `.proto` — método `/aag.PluginRepo/GetPluginList`) devolve **`UNAUTHENTICATED "unauthorized access"`**. O gateway
  é fechado por token de ponta a ponta. `scratchpad/aag_getpluginlist.py`.
- 4920 = gRPC nativo **sem reflection**; 4930 = HTTP/1.x (conteúdo/gRPC-Web); ambos só em `[::1]` (IPv6), 127.0.0.1 recusa.
- **Token:** `config.json` (`C:\ProgramData\Avid\APIGateway`) tem só `{apiPort:4920, pluginPort:4930}` — **nenhum segredo**;
  não há arquivo de token no disco. O token é JWT gerado **em memória** (`models.GenerateToken`, golang-jwt v4) e
  entregue ao host autenticado, que o injeta na webview. Cliente externo limpo não obtém sem arrancar da memória (invasivo).

⇒ **Para operar o MC por fora, usar o 9100 (sem token), não o gateway.** O gateway/token só importa para hospedar a
webview do painel — a única metade que fica dentro do MC. Fecha também a pergunta "abrir o painel escondido por comando":
nem o host (sem RPC de janela no 24.6.0) nem o gateway (gated) dão caminho externo; o caminho é janela própria + 9100.
[[ativar-no-2021-ftf]]

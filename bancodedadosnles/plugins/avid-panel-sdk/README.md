# Plugins — Avid Media Composer (Panel SDK)

> **Para onde isto vai:** [roadmap.md](roadmap.md) — 3 iniciativas planejadas (Órbita⇄MC,
> Relinker dentro do MC, automações de entrega). Planejamento, ainda não iniciado.


Como fazer um PAINEL que roda DENTRO do Media Composer. Mesmo papel do
[premiere-cep](../premiere-cep/) no Premiere: não é formato de arquivo, é a API de UI/comandos
do editor para um painel fino que dirige um app externo. Fatos consumíveis em
[dados/runtime.json](dados/runtime.json) e [dados/manifest-schema.json](dados/manifest-schema.json).
Narrativa em [arquitetura.md](arquitetura.md). Rastreabilidade em [fontes.md](fontes.md).

> 🆕 ⚠️ **[ativar-no-2021-ftf.md](ativar-no-2021-ftf.md)** — o Panel SDK no **MC 2021.12** está
> **DESLIGADO** atrás da feature flag `/Media Composer/3PDevPanelSDK`. O arquivo mapeia (RE +
> harness contra o `FTF.dll` real) o formato dos `.ftf`, o override global `CIT_OVERRIDE.FTF`
> (JSON texto claro, SEM assinatura, liga QUALQUER toggle — `confirmado` in-process) e o gate de
> build-type. **⛔ CAUSA RAIZ (teste real 2026-10-17): o 2021.12 NÃO TEM o runtime do Panel SDK** —
> sem `avid-api-gateway`, sem `PanelSDKPlugins`, sem registro de `.avpi` (strings ausentes no exe). O
> toggle é resquício; o motor de painel só veio no 25.6+. O patch foi aplicado (MC abre, painel não
> vem). **Rodar painel Panel SDK no 2021.12.10 é impossível — o subsistema não está no produto.**
> ⭐ **Linha do tempo (instaladores inspecionados 2026-10-17):** o Panel SDK aparece COMPLETO só na
> **MC 2023.8.2** (binário `avid-api-gateway.exe` + `PanelSDKPlugins` + `PanelSDK.json` + comandos
> `panelsdk`); 2021.12 e 2022.12.9 não têm (2022 é transição). ⇒ **base recomendada = 2023.8.2.**
> Tabela em [ativar-no-2021-ftf.md](ativar-no-2021-ftf.md).

> 🆕 ⚠️ **[windows.md](windows.md)** — o Panel SDK **no Windows** (MC 25.6), segunda instalação de
> referência. **Leia antes de confiar em caminho ou rpc desta pasta:** ela separa o que é
> *plataforma* do que é *VERSÃO* — distinção impossível com uma instalação só — e três coisas que
> pareciam "como o SDK é" eram "como o 25.12/macOS é". Traz
> `%PROGRAMDATA%\Avid\PanelSDKPlugins`, o menu que **não** é `Extensions`, um rpc que
> **simplesmente não existe** no 25.6 (`GetListOfWindows` → `UNIMPLEMENTED`), a assinatura do
> gateway órfão que **muda de SO** e a coluna `Drive` que é **rótulo de volume, não letra**.
>
> ⚠️⚠️ E traz uma **correção de fato antes `confirmado`**: ~~o drop é de mão única~~ — **o drag
> da bin PARA DENTRO do painel existe**. Ele não é rpc, é **MIME customizado no `ondrop` do
> DOM**, e por isso a busca por símbolo no binário nunca o achava.

> 🆕 ⭐⭐ **[copia-da-timeline.md](copia-da-timeline.md)** — como o painel lê **exatamente** o
> que o editor selecionou na timeline (a API não lê seleção): Ctrl+C do editor →
> `DoCommand(6292)` → `CreateSubClip(use_clip_bounds, end_frame=-1)` numa bin do painel → `.avb`.
> Medido no MC 2025.6/Windows em 2026-09-24.

> 🆕 ⭐⭐ **[arrastar.md](arrastar.md)** — o arrasto **MC → painel**, medido de ponta a ponta e
> com arquivo próprio (não é específico de SO nem de versão). Traz o mecanismo, o payload, **as
> seis espécies e como distinguir cada uma** — inclusive **AMA × gerenciado**, que o `type` não
> separa e a coluna `Source File`/`Source Path` separa —, os resultados **negativos** (bin não
> entrega nada; o `.aaf` anexo tem 0 bytes) e as quatro armadilhas de implementação, entre elas
> a que quebra tudo em silêncio: **`effectAllowed = "move"`**, e forçar `dropEffect: "copy"`
> cancela o drop. Descoberto lendo o [ESION Studio](esion-arquitetura.md).

Confiança geral: **mista, e por parte** (atualizado 2026-08-15):

> 🆕 **[paineis-de-terceiros.md](paineis-de-terceiros.md)** — o que dois **parceiros oficiais da
> Avid** (Jumper e Quickture) fazem nos seus painéis. Valida o `mcapi.proto`, promove três
> escopos de `usesApi`, e revela que o `url` do `uiItem` aceita **HTTP absoluto para localhost**
> (painel same-origin com o app: sem CORS, sem segredo de pareamento).

| parte | confiança |
|---|---|
| Caminhos, portas, comandos de console | `confirmado` — lidos do disco / executados |
| **API `mcapi` pelo backend 9100** | ⭐ `confirmado` — em USO NUMA INTEGRAÇÃO DE PRODUÇÃO (Órbita), com números medidos |
| Formato do `.avpi` e do manifesto | ⭐ `confirmado` — conferido contra os `.avpi` de **dois parceiros oficiais** (Jumper, Quickture) |
| **`mcapi.proto` reconstruído** | ⭐ `confirmado` — diff contra o protobuf **oficial** compilado no painel do Jumper: falta 1 símbolo |
| Painel próprio CARREGANDO no editor | `confirmado` — um painel não-assinado subiu e conectou |
| Chamar a API **de dentro do painel** (grpc-web + token) | `pendente` — é o que falta |
| **Painel → app local por HTTP** (`fetch` de `avpi://` para `127.0.0.1`) | ⭐ `confirmado` — EM PRODUÇÃO no Órbita; origem literal `avpi://`, CORS vale normalmente |

Tudo saiu da instalação real do Media Composer 25.12 (macOS) por engenharia reversa: **o SDK
oficial é fechado** (ver abaixo).

## O ponto que mais importa: o SDK oficial é FECHADO

Diferente do CEP da Adobe (documentação pública, SDK baixável), o **Panel SDK da Avid exige
onboarding de parceiro** e a Avid declara não estar aceitando novos parceiros
(consultado 2026-08-07, [avid.com/media-composer/extensions](https://www.avid.com/media-composer/extensions)).
Não há download público, não há espelho no GitHub, não há `.proto` publicado.

**Por isso este registro existe.** O runtime inteiro já vem instalado com o Media Composer —
o formato do pacote, os caminhos, o gateway e a flag de desenvolvedor são recuperáveis da
própria instalação. É esse o caminho enquanto a fila da Avid não anda.

## Arquitetura

O painel é uma **página web em QtWebEngine** dentro do MC. Dois canais de comunicação:

1. **`qwebchannel.js`** — bridge Qt WebChannel, JS ↔ C++ do host. O arquivo está em
   `AvidMediaComposer.app/Contents/MacOS/qwebchannel.js`.
2. **gRPC-Web via `avid-api-gateway`** — binário Go (gRPC + gRPC-Web + WebSocket, `nhooyr.io/websocket`)
   que roda como proxy. O *backend* gRPC é o próprio Media Composer. O gateway autentica cada
   painel com token (`GetPluginAccessToken`) e serve os arquivos do bundle (`GetFileContent`).

Igual ao Premiere: **painel fino, motor fora**. A diferença é que aqui existe uma camada de
autenticação por token e entitlements que o CEP não tem.

## O pacote `.avpi`

É um **ZIP** com `avid-manifest.json` na raiz mais os assets. Schema completo e comentado em
[dados/manifest-schema.json](dados/manifest-schema.json).

Instalação: copiar o `.avpi` para `/Library/Application Support/Avid/PanelSDKPlugins/`. É local de
sistema, mas o instalador da Avid deixa a pasta `drwxrwxrwx` — **na instalação medida (MC 25.12,
macOS) copiar não exigiu `sudo`**. Não assuma que vale em toda máquina.

## ⚠️ O gateway órfão — achado empírico, e o que ele NÃO prova

**Observado nesta instalação** (MC 25.12, macOS, dois painéis não-assinados; `ps`+`lsof` a 0,5 s
em 5 ciclos de fechar/abrir):

```
MC fecha   → o avid-api-gateway NÃO morre: vira órfão (PPID 1) e SEGUE com 4920/4930
             (52 s de pé num dos ciclos; e já se viu um de pé por 2 DIAS em 07/08,
              antes de existir painel nosso)
MC abre    → por ~5-8 s as portas ainda são do órfão; o registro dos painéis
             nessa janela não acontece → o menu Extensions nem é criado,
             sem erro e sem log
```

É uma **corrida**, e o caso comum — reabrir o MC logo depois de fechar — é o que perde, o que faz
o sintoma parecer intermitente. Quando falha, **some o menu inteiro**: os dois painéis instalados
de uma vez, inclusive um que não fala com app externo nenhum. Ou seja, a falha é no **REGISTRO**,
antes de qualquer código de painel rodar — não tem relação com o que o painel faz.

### ⛔ O que isto NÃO autoriza concluir

**Não conclua que todo painel do Media Composer sofre disto.** Existem painéis comerciais de
terceiros em produção ([avid.com/media-composer/extensions](https://www.avid.com/media-composer/extensions))
e é implausível que todos embarquem um processo para matar o gateway. Logo, uma destas é
verdadeira e não sabemos qual:

- a **pré-condição** (o gateway sobreviver ao MC) não acontece em uso normal — e a hipótese mais
  forte é **encerramento sujo**: esta máquina levantou exceções ao fechar o MC
  (`CENTRAL_ADM_DEVICE_IS_NULL`), e um shutdown que aborta pode pular o passo que para o gateway;
- existe um **mecanismo suportado que desconhecemos** (o `panelsdk reinit` é o candidato óbvio, e
  está quebrado nesta build — pode ser exatamente a peça que falta, funcionando noutra versão);
- painel **assinado/de parceiro** registra por outro caminho;
- ou esses usuários **convivem** com o sintoma e culpam o Media Composer.

Nada disso foi testado. **O SDK é fechado e não temos documentação** — este registro é análise de
comportamento observado, não a regra do fabricante. Trate como achado útil, não como lei: se
aparecer documentação oficial ou um painel de parceiro que não sofra disto, **revise esta entrada
em vez de defendê-la**.

### 🆕 ⚠️⚠️ A variante que NÃO parece o gateway (2026-09-10, MC 25.6 / Windows)

`confirmado`, com round-trip. O órfão nem sempre impede o registro — **ele pode servir
uma lista velha**, e essa é a forma perigosa.

O menu Tools apareceu **completo**, com os quatro painéis que existiam quando o gateway
subiu. Faltava só o quinto, instalado meia hora depois. Nada acusava falha.

⭐ **Por que isso é pior que o sintoma já registrado acima:** quando o menu inteiro some,
a suspeita cai no gateway, que é onde está o problema. Quando só o painel novo falta, a
suspeita cai no **pacote recém-instalado** — e o tempo vai para comparar manifesto,
estrutura do ZIP e schema, tudo correto. Foi exatamente o que aconteceu.

**O diagnóstico custa 30 segundos, se você souber olhar:** compare o `StartTime` do
`avid-api-gateway` com a data de escrita do `.avpi`. Gateway mais velho que o pacote =
lista velha.

```
gateway subiu ....... 15:20:26      ← 30 min ANTES
plugin instalado .... 15:50:10
MC reiniciou ........ 15:52:38      ← PID novo
gateway depois ...... MESMO PID, ainda de pé
```

⚠️ **E isto contradiz a timeline medida no macOS.** Lá o órfão segura as portas por 5–8 s
e morre quando o gateway da sessão nova assume. Aqui sobreviveu **32 minutos e um restart
completo**, continuando o **único** gateway do sistema — o MC novo não subiu outro. Isso
reabre a hipótese *"o MC reutiliza o órfão"*, marcada como errada em 2026-08-08 sobre
medição no macOS. Pode ser plataforma, pode ser versão; **não foi instrumentado**.

⭐ **A regra segura de instalação passa a ser:** fechar o MC → matar o gateway → instalar
→ abrir. Instalar antes de abrir o MC **não basta** se houver órfão de sessão anterior.

### Se você sofrer disto

Um painel **puro** não consegue se corrigir sozinho — a cura exige encerrar um processo com o MC
FECHADO, e um painel só existe dentro do MC. As saídas: um processo externo que faça a faxina (foi
o que o Órbita fez — ADR 0016), documentar o procedimento manual, ou conviver.

Detalhes, hipóteses em aberto e como testar cada uma: [dados/runtime.json](dados/runtime.json) →
`quem_e_afetado_pelo_gateway` e `console_commands.gateway_orfao_quebra_registro`.

## Modo desenvolvedor

Existe e está no produto:

- Feature flag do MC: **`/Media Composer/3PDevPanelSDK`** — descrição literal no binário:
  *"Enable 3P development for Panel SDK."*
- No gateway: `AuthManagerProd.IsDevMode`, log *"[main] Gateway was switched to the developer mode"*.
- Console do MC: **`panelsdk reinit`** (sobe o gateway, re-registra o serviço MC e recarrega todos
  os plugins — é o ciclo de iteração) e **`panelsdk console on`** (joga o console do navegador
  na janela de Console — é o debug).

O `panelsdk reinit` é o equivalente funcional do "fechar e reabrir o painel" do CEP.

### ⚠️⚠️ O Reload do painel trouxe a página ANTIGA (2026-09-11, MC 25.6 / Windows)

**O sintoma é `confirmado`; a causa é `inferido` e o conserto está `por confirmar`** — a
distinção importa e está explicada no fim.

Medido escrevendo uma aba nova num painel próprio (Ciclo Assist) servido por um app local em
`127.0.0.1`. O menu de contexto do painel (botão direito → **Reload**) **mostrou a página
antiga**, idêntica, sem a aba que acabara de ser escrita — enquanto um `curl` no mesmo
endereço, no mesmo instante, devolvia o HTML novo. (E fechar e reabrir pelo menu Tools
tampouco trazia a nova, o que já estava anotado.)

A causa provável não é o SDK: é HTTP. O app servia `/painel` e os estáticos **sem cabeçalho
de cache nenhum**, e o QtWebEngine é livre para guardar página, CSS e JavaScript. A defesa é

```
Cache-Control: no-store
```

na resposta do HTML **e** na dos estáticos.

⛔ **Por que isto merece entrada no banco mesmo antes de fechar:** o sintoma mente. Ele diz
*"o código novo não funcionou"* — não há erro, não há aviso, e o desenvolvedor vai depurar o
código que acabou de escrever. Quem serve um painel de um app local não perde nada mandando
`no-store` desde o primeiro dia.

⚠️ E o pior caso é o misto: HTML novo com JavaScript velho. A tela aparece mudada e se
comporta como a de antes.

⚠️⚠️ **O que FALTA para virar `confirmado`:** ver o Reload trazer a página nova depois do
`no-store`, dentro do MC. O cabeçalho já é enviado (conferido por `curl`), mas a tentativa
de reconfirmar pelo painel foi feita com clique sintético (`mouse_event`), e clique sintético
**provadamente não chega** a algumas webviews — no mesmo dia ele falhou em atingir um Chrome
comum. Enquanto a confirmação for por automação de mouse, ela não vale; precisa ser um
Reload feito por uma pessoa.

### ⛔ `hidden` perde para `display: flex` — `confirmado` (mesmo dia, mesma webview)

Não é específico da Avid — é a cascata do CSS —, mas aparece aqui porque painel de 340–440 px
é feito de flexbox, e a troca de telas de um painel costuma ser escrita como
`el.hidden = true`. O `hidden` do navegador é um `display:none` de **folha padrão**, e
qualquer `display` de autor o vence: a tela "escondida" continua ocupando a janela, por
baixo da nova. A defesa é uma linha, no topo da folha:
`[hidden] { display: none !important; }`.

**Reincidência, 2026-10-05 (De Lá Pra Cá v0.1.82, janela do app Tauri no Windows/WebView2):** a regra
estava no `painel.css` e faltou na folha da OUTRA UI do mesmo app (`app/ui/app.css`): a faixa
"Versão nova:" ficava sempre visível, vazia, com "Baixar". O teste no Mac, feito com o estado
"há versão nova", não podia mostrar. Lição: a linha vai em TODA folha de UI web da família
(painel, janela do app, casca do Resolve), e o caso "não há nada a mostrar" se confere na tela.

## A API real: serviço gRPC `mcapi.MCAPI` (60 métodos)

Há **dois** caminhos de comunicação, descobertos por engenharia reversa + round-trip:

1. **Eventos** (host→painel): sinal `onEvent(tipo, jsonPayload)` do objeto QWebChannel `mcapi`.
   Filtrados pelo `usesApi`. Catálogo confirmado em [dados/mcapi.json](dados/mcapi.json)
   (BinRowSelectionChanged, MobLoadedInViewer, PlayPositionChangeEvent, MobAdded/Deleted…).
2. **Request/response** (painel→host): serviço gRPC **`mcapi.MCAPI`** com **60 métodos**, cada um
   em `/mcapi.MCAPI/<Método>` via gRPC-Web (gateway 4930, token). Lista completa e categorizada em
   [dados/mcapi-grpc.json](dados/mcapi-grpc.json): `GetBins`, `LoadMobsIntoViewer`, `StartPlay`,
   `SetPosition`, `ImportFile`, `ExportFile`, `AddMarker`, `CreateSubClip`, `DoCommand`,
   `GetListOfCommands`, `SetCustomProjectData`…

**Modelo de edição:** não há método `Overwrite`/`Insert`. Edição e marcação passam por
`DoCommand(nome)` — nomes de comando existem no binário (`MarkIN`, `MarkOUT`, `Overwrite`,
`Insert`), enumeráveis por `GetListOfCommands`. Resposta volta como evento `DoCommandFinished{handled}`.
Por isso In/Out e edições **não** aparecem no `onEvent` como eventos próprios: são ações, não
notificações.

## O `.proto` completo — RESOLVIDO

O contrato inteiro está em **[dados/mcapi.proto](dados/mcapi.proto)** (61 rpcs, ~298 messages),
extraído por **gRPC server reflection** do backend do MC (`[::1]:9100`, **sem token** — é o backend
direto, antes da auth do gateway). Resumo em [dados/mcapi-grpc.json](dados/mcapi-grpc.json).

Pontos do contrato:
- **Envelope:** todo request = `{RequestHeader header, XxxRequestBody body}`; header tem
  `company_id` + `access_token` (a auth). Response = `{ResponseHeader header, XxxResponseBody body}`;
  header tem `task_id`, `progress`, `warnings`.
- **DoCommand** usa `commandId` **numérico** — `GetListOfCommands` mapeia id↔nome (MarkIN/Overwrite/…).
- Cada rpc tem `option (mcapi.api_scope)` = o canal que o `usesApi` precisa declarar.
- 5 rpcs são server-streaming (`GetBins`, `GetMobInfo`, `GetValues`, …).

Como reproduzir (MC aberto): `grpcurl -plaintext [::1]:9100 describe mcapi.MCAPI`.

### ⛔ Dois stubs do MESMO `.proto` não cabem num processo — `confirmado` 2026-09-19

O `_pb2` gerado registra as mensagens no pool PADRÃO do protobuf, pelo nome qualificado
(`mcapi.Stereoscopic`…). Dois apps que compilaram este mesmo `.proto` com **nomes de arquivo
diferentes** (`mcapi_types.proto` no Assist anterior, `mcapi_tipos.proto` no Ciclo Assist — as
mesmas mensagens, conferido mensagem a mensagem) não convivem: importar o segundo dá
`TypeError: Couldn't build proto file into descriptor pool: duplicate symbol
'mcapi.Stereoscopic'` (protobuf 7.36.0, Windows). ⇒ Quem funde dois apps num processo fica com
**um** `_pb2` e um cliente gRPC; o outro vira adaptador (Assist anterior,
`motores/cicloassist/avid/mcapi.py`). ⚠️ O mesmo nome de arquivo provavelmente deixaria o
segundo import reaproveitar o primeiro — `hipotese`, não medido.

## ⭐ Integração em PRODUÇÃO pelo 9100 (2026-08-08) — o que ela ensinou

O Órbita (DRAMASYNC) passou a dirigir o Media Composer por este caminho: cliente gRPC em Python
contra `[::1]:9100`, sem painel e sem token. Fluxo validado por um editor na GUI: ler a seleção
das bins → sincronizar → autorar uma `.avb` → abrir no MC → carregar no Record.

Os fatos MEDIDOS estão em [dados/mcapi-grpc.json](dados/mcapi-grpc.json); os que mais mudam
decisão de projeto:

- **Piso de ~500 ms POR CHAMADA**, seja ela qual for (`custo_das_chamadas`). `GetAppInfo`, que
  devolve quatro strings, custa o mesmo que listar uma bin. E **não há canal de evento** nos 61
  métodos. → *Observar estado continuamente não cabe; ler sob demanda, sim.* ⭐ O mesmo recurso
  tem preços diferentes conforme o painel viva DENTRO do NLE ou o app pergunte de FORA.
- **O MobID tem duas representações** e a da API **não** é a do pyavb (`mob_id_duas_representacoes`).
  Passar o hex cru para um writer gera "missing mob".
- **`bin_relative_path` é relativo à pasta do PROJETO, com subpasta** — e os três jeitos errados
  devolvem a MESMA mensagem, `"Bin is not open."`, que aponta o lugar errado (`caminhos_de_bin`).
- **`OpenBin` tem efeito VISÍVEL** (abre a bin na tela) e **não relê o disco** numa bin já aberta.
- **`GetMobInfo` (streaming) traz `Source Path`/`Source File`** — o MC lembra de onde importou cada
  master. É a ponte de uma seleção de bin para caminhos de arquivo.
### ⭐⭐ colunas — o que o `GetMobInfo` devolve, e as três que valem ouro (2026-08-22)

`confirmado` no MC 25.6 / Windows 11, medido no Órbita contra 50 masters de uma diária real.

O `GetMobInfo` é de FLUXO e devolve **~37 pares coluna/valor** por master — as mesmas colunas que
o editor vê na bin. Quase todo mundo pede duas e ignora o resto. Três mudam o desenho de quem
precisa **achar a mídia gerenciada**:

| coluna | exemplo medido | por que importa |
|---|---|---|
| `Name` | `a004_03170917_C003` | é o radical do nome dos arquivos OP-Atom → **filtra o acervo** |
| **`Tracks`** | `V1 A1-2` / `A1-5` | ⭐ **quantos arquivos aquele master tem** (3 / 5) → **diz quando PARAR de procurar** |
| `Drive` | `V-001 (E:)` | o volume — e vem como `RÓTULO (LETRA:)`, ver [windows.md](windows.md) §6 |

⭐ **`Tracks` é o achado.** Somando os 50 masters de uma diária: **198 arquivos previstos**,
exatamente os 198 que a busca encontra. Com ele a varredura deixa de ser "leia tudo e depois
agrupe" e passa a **parar quando cada master estiver completo** — o que torna o custo proporcional
ao MATERIAL PEDIDO, e não ao tamanho do acervo. Medido: 1984 `.mxf` no disco, 109,7 s varrendo
tudo contra 10,9 s com filtro por nome + parada (mesma resposta, arquivo a arquivo).

E vem de graça: a chamada já é feita, uma vez por master, para outra coisa.

Outras que evitam abrir o arquivo: `Frame Count Duration`, `Start`/`End` (TC de fonte), `FPS`,
`Format`, `Audio SR`, `Video`/`Audio File Format`, `Creation Date`/`Modified Date`, `Project`,
`Tape`. ⚠ Substituir o `ffprobe` por elas é tentação maior e mais arriscada (o TC de OP-Atom tem
armadilha própria — ver [../../protocolos/mxf/timecode.md](../../protocolos/mxf/timecode.md));
`pendente`, não medido.

⚠ **Preço:** ~500 ms de piso por chamada, e medido **760 ms** por master numa diária de 50 —
**38 s** só de `GetMobInfo`. Quando a busca de arquivos cai para segundos, isto vira o gargalo.

- **`GetValues` é um eco de brinquedo**: devolve `['0','1','2','3']` para qualquer chave.
- **A API não diz quais bins estão marcadas no painel lateral** (`o_que_a_api_NAO_expoe`).
- **Qualquer diálogo modal trava a API inteira** — inclusive um erro que o próprio MC levanta.
  ⭐ **Até o `GetAppInfo`** (2026-10-24, MC 25.12, Mac, `confirmado`): com "Leave the application?" aberto, a Select
  Project na tela ou o MC subindo, o `GetAppInfo` dá `DEADLINE_EXCEEDED` (não `UNAVAILABLE`: a porta está aberta).
  Quem sonda "o MC está aí?" com o prazo de consulta (20 s) trava 20 s e conclui "não está" — o De Lá Pra Cá
  trocava o painel para o Premiere e mostrava "procurando". Regra: sonda com prazo curto (3 s) e **prazo estourado =
  ocupado, não fechado** (`UNAVAILABLE` = fechado). Medido: a Select Project = ocupado; projeto aberto → 0,22 s.

### ⛔⛔ `Source File`/`Source Path` são ENTRADA, não configuração (2026-08-27, `confirmado`)

São texto livre de um `.avb`/AAF que pode vir de **outra produtora** — o Media Composer não
valida o conteúdo dessas colunas, só as lembra de quando importou o master. Um cliente que
monta `caminho = Path(pasta) / arquivo` está confiando nesse texto sem perceber:

- se `arquivo` for um caminho **absoluto** (incluindo UNC, `\\host\share\x.mov`), o operador
  `/` do `pathlib` **descarta `pasta`** — não é bug do pathlib, é o comportamento documentado;
  o furo é tratar `Source File` como se fosse sempre um nome.
- o dano não é o caminho devolvido: é o `.exists()` que normalmente vem em seguida — **no
  Windows, checar a existência de um UNC abre sessão SMB** no host que o `.avb` escolheu,
  com a credencial da máquina do editor.

**Conserto:** normalizar `Source File` para só o basename antes de montar o caminho
(`PurePath(arquivo.replace("\\", "/")).name`), e logar quando ele chegou disfarçado de
caminho. Achado comparando o `mcapi.py` do Assist anterior com o fork Órbita — `_DeLaPraCa` já
nasceu com essa normalização; foi o Assist anterior que reintroduziu o furo reescrevendo o
cliente de memória, e depois portou o conserto de volta (ver `fontes.md`, linha 2026-08-27).

⭐ **Regra geral para qualquer coluna do `GetMobInfo`:** ela é entrada de um arquivo de
terceiro, não parâmetro do chamador — validar/normalizar antes de usar em qualquer chamada de
sistema (`exists`, `open`, subprocess), não só aqui.

### ⚠️⚠️ Um prazo de CONSULTA aplicado a uma OPERAÇÃO DE ARQUIVO (2026-08-16)

Há um **piso** de ~500 ms por chamada (acima), mas há também um **teto** — e ele não pode
ser o mesmo para os dois tipos de chamada:

| tipo | exemplos | ordem de grandeza |
|---|---|---|
| consulta | `GetMobInfo`, `GetListOf*`, `GetAppInfo` | centenas de ms |
| operação de arquivo | `CloseBin`, `OpenBin`, `ImportFile` | **dezenas de segundos** |

`CloseBin` **salva a bin**: numa com 44 masters AMA o Avid mostra *"Closing bin window,
please wait while the bin is saved"* por muito mais que os 20 s que serviam de teto único.

⭐ **E o modo de falha não é "demorou" — é silencioso e destrutivo de resultado.** O rpc
voltou `DEADLINE_EXCEEDED`, o chamador leu como *"não consegui fechar essa bin"* e gravou
o trabalho **com outro nome**, enquanto o MC seguia fechando a bin normalmente. O editor
ficou com **duas bins**, a certa não estava aberta, e nada acusou erro.

⭐⭐ **A lição é sobre prazo, não sobre bin: um teto curto demais não devolve erro honesto
— devolve uma DECISÃO ERRADA tomada com confiança.** O plano B para "a bin não fecha"
estava correto; o defeito era chamar de *"não fecha"* o que era *"ainda não terminou"*.
Todo `catch` que decide algo a partir de um timeout merece essa pergunta.

⚠️ **E depois do `CloseBin`, espere o arquivo estabilizar antes de reescrevê-lo.** Fechar
salva, e nada garante que o rpc volte depois do último byte — o `DoCommand(Save)` deste
mesmo SDK é comprovadamente assíncrono. Gravar por cima de uma gravação em curso não
levanta erro: produz uma bin plausível e corrompida.

⚠️ **Anuncie a etapa na interface.** Sem isso o painel fica com a barra em 100% da etapa
anterior, um modal do Avid por cima, e o usuário conclui que travou — foi assim que o
problema apareceu.

## Único pendente real

Chamar os métodos **de dentro do painel** (grpc-web + token via `GetPluginAccessToken`), e o formato
exato do `commandId`. O contrato está mapeado; falta o round-trip de uma chamada real.

⚠️ **E um obstáculo de INTEGRAÇÃO, não de SDK, que só aparece quando o painel precisa falar com um
app externo:** o painel roda em QtWebEngine com origem `avpi://` e **não tem acesso a disco**. Se o
app do outro lado autentica por um segredo em ARQUIVO (o padrão de quem já se protegeu contra uma
página web qualquer chamar `localhost`), o painel **não consegue lê-lo** — diferente de um painel
CEP (Node `fs`) ou de um script Lua do Resolve (`io.open`). **RESOLVIDO em 2026-08-08, e não foi com segredo:** o painel manda `Origin: avpi://`, que é um
*forbidden header* — nenhuma página web o forja. Autenticar o painel pela ORIGEM (em rotas
restritas) compra a mesma proteção que o arquivo de token, sem nada para embutir. Um segredo
dentro do `.avpi` seria pior: a pasta é `rwxrwxrwx`, então qualquer processo local o leria.

## ✅ Marcadores e posição pelo MobID da sequência (2026-10-29, MC 25.12 / Mac)

- **`AddMarker`** com `mob_id` (a sequência; ela NÃO precisa estar no Record), `track_label {type: TRACKTYPE_PICTURE
  (0), number: N}` = a trilha **VN**, `offset` = quadro desde o início da sequência, `length 1`, `comment`, `color`
  (enum `Red…Gold`, `Yellow`). O `GetMarkers` devolve os dois de volta com o TC (`01:00:04:00` para o offset 96 a
  23,976), o acento do comentário intacto e o `user` da máquina. Uso: De Lá Pra Cá `avid/mcapi.marcar` (a escala de
  outra mídia na rota Premiere → Avid). O 24.6 (Windows) já tinha sido medido na **TC1** (ativar-no-2021-ftf.md).
  ✅ **MC 24.6.0 (Windows 11, 2026-10-29):** o mesmo pela trilha **VN** — 28 `AddMarker` amarelos em V1–V4 da
  sequência montada (o .prproj de 2023 do R04, 88 planos), com a sequência fora do Record; o `GetMarkers` devolve os
  28 com o comentário acentuado e o TC certo (`00:00:44:11` para o offset 1067 a 23,976).
- **`SetPosition`** existe no 25.12 (no 25.6 Windows não): corpo `mob_id` + `offset` (ou `timecode`) — não há campo
  `position`. Leva o Record ao quadro pedido (conferido pela foto do monitor).

## ⛔⛔ `GetBinFromMob` — duas armadilhas MEDIDAS (2026-09-02, MC 25.6 / Windows)

`confirmado` no Assist anterior, contra a `CENAS/C07.avb` de um projeto real, com o Media
Composer aberto. As duas falham **em silêncio**: o rpc devolve `None`, não erro.

⭐ **No MC 25.12 (Mac, 2026-10-28, De Lá Pra Cá) a armadilha 1 MUDA DE CARA, não de regra:** o mesmo mob em
`26-6-16-8-8`, 64 hex corridos e `0x`+maiúsculas dá **erro** `"Bin not found"` (UNKNOWN) — que parece "o mob não
está em bin nenhuma" — e só o `26-6-16-12-4` acha. Normalizar ANTES de perguntar (`mcapi.mob_id_para_api` do De Lá
Pra Cá, a URN também): os quatro formatos acharam.

### 1. Ele é sensível ao AGRUPAMENTO do texto do MobID

O mesmo identificador, escrito de seis jeitos, contra o mesmo subclipe:

| forma | resultado |
|---|---|
| `26-6-16-12-4` — como a API devolve, **e como o drag-and-drop entrega** | **ACHOU** |
| a mesma, em MAIÚSCULAS | **ACHOU** |
| 64 hexadecimais corridos | `None` |
| `26-6-16-8-8` — o agrupamento do `ffprobe` / do `material_package_umid` | `None` |
| `urn:smpte:umid:` pontuado — a forma do **pyavb** | `None` |
| `0x` + 64 hexadecimais | `None` |

⭐ **Por que ninguém tinha topado com isso:** todo MobID que um painel manipula chega
**do drop ou da própria API**, já no agrupamento certo. A armadilha só aparece no
caminho contrário — ler a bin com pyavb e **perguntar** ao MC —, que é o que um app faz
quando quer casar o que está no arquivo com o que está na tela.

⚠️ **E não vale "cravar os hífens" na validação.** O banco já registra que um validador
que exija agrupamento recusa MobID legítimo (`windows.md` §colunas). São coisas
diferentes: **validar** aceita qualquer forma; **perguntar** normaliza para a da API.

⚠️ Ao converter da URN do pyavb, tirar o prefixo **antes** de filtrar hexadecimais: o
`e` de `smpte` e o `d` de `umid` passam pelo filtro e o total vira **66** dígitos. É
irmão do erro que a família `remap.py` já pagou.

### 2. Ele não localiza TODO masterclipe

Na mesma bin, `GetBinFromMob` respondeu para **todos os 10 subclipes** e para apenas
**1 dos 19 masterclipes**. Os que respondem são os das bins que o Media Composer tem
localizadas; um master de câmera cuja bin de origem está fechada devolve `None` —
embora o mob esteja dentro da `.avb` que se está lendo.

⭐ E, quando responde, ele diz a bin onde o master **de fato vive**, não aquela de onde
o item foi arrastado: um master de som da `CENAS/C07.avb` devolveu `D02_SOM.avb`.

⛔ **Consequência para qualquer painel que use o padrão "um item basta — ele diz qual
bin":** perguntar só pelo PRIMEIRO item faz o resultado depender da ORDEM do arrasto.
No Assist anterior, arrastar só masterclipes dava erro enquanto os **mesmos** masterclipes
funcionavam se viessem depois de um subclipe. ⇒ **pergunte por cada item até um
responder** (para no primeiro, então custa uma chamada no caso normal).

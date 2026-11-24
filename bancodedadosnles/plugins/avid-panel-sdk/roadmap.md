# Roadmap — o que construir sobre o Panel SDK / mcapi do Media Composer

Planejamento registrado em 2026-08-07. **A iniciativa 1 está FEITA** (2026-08-08, ver abaixo); as
outras duas seguem como direções. Foram acordadas depois
de mapear o SDK (formato `.avpi`, eventos `onEvent`, serviço gRPC `mcapi.MCAPI` com 61 métodos, e
a descoberta-chave: o backend em `[::1]:9100` aceita chamadas **sem token**, ver
[dados/mcapi-grpc.json](dados/mcapi-grpc.json) → `backend_9100_sem_auth`).

Dois caminhos de integração possíveis, a escolher por projeto:
- **Painel distribuível** (`.avpi` + grpc-web no gateway 4930 + token): para plugin que roda dentro
  do MC e conversa com um app externo. É o modelo do [premiere-cep](../premiere-cep/) (painel fino).
- **Direto no 9100** (gRPC, sem token, loopback): um app desktop local dirige o MC sem painel.
  Bem mais simples para automação própria. Pode coexistir com um painel só de UI.

---

## 1. Órbita ⇄ Media Composer (integração nativa) — ✅ **FEITA** (2026-08-08)

> **Estado:** entregue e validada na GUI por um editor. O Órbita lê a seleção das bins,
> sincroniza, autora uma `.avb` e a abre no Media Composer, com a timeline online e o
> `Find in Bin` levando ao clipe na bin original. **Não há painel**: o app dirige o MC pelo
> backend 9100. O que a implementação ensinou está no README (§Integração em PRODUÇÃO) e em
> [dados/mcapi-grpc.json](dados/mcapi-grpc.json).
>
> **A forma final ficou INVERTIDA em relação ao Premiere/Resolve** — e vale como conclusão de
> arquitetura, não como detalhe: lá um painel dentro do NLE chama o app; aqui o app chama o NLE.
> A razão é que não existe `Overwrite`/`Insert` com parâmetros na `mcapi` (edição é `DoCommand`
> numa máquina de estado), então a timeline **não é comandada, é AUTORADA** — e autorar não
> precisa de painel.

> ### ⭐ Complemento (2026-08-08, segunda leva): o PAINEL também foi feito
>
> Depois da integração nativa, o Órbita ganhou um **painel `.avpi` de verdade** dentro do MC — não
> por necessidade, por **paridade de gesto** (o editor não sair do Avid, como no Premiere e no
> Resolve). Três conclusões que valem para qualquer painel:
>
> 1. **Ele é um CONTROLE REMOTO, não um canal de dados.** Como o app já lê a seleção sozinho pelo
>    9100, o painel manda um "vai" e nada mais. Isso encolhe o painel a dois botões e reduz a
>    superfície exposta pelo app a duas rotas.
> 2. **Autenticação pela ORIGEM.** O painel não lê disco, então não alcança um segredo em arquivo.
>    A saída foi `Origin: avpi://` — *forbidden header*, que nenhuma página web forja. Um segredo
>    embutido no `.avpi` foi DESCARTADO por medição: a pasta de painéis é `rwxrwxrwx`, então o
>    segredo protegeria contra o mesmo atacante e falharia contra o mesmo. Ver `rede_do_painel`.
> 3. **O gateway órfão é o risco de distribuição**, não a API. Ver
>    `quem_e_afetado_pelo_gateway` — inclusive a corroboração externa (Jumper) de que o sintoma é
>    conhecido no ecossistema e resolvido, por lá, mandando o usuário digitar `panelsdk reinit`.

**Objetivo.** O Órbita (app de sync) já tem integração nativa com Premiere (CEP) e DaVinci Resolve,
cada um com um painel interno que conversa com a aplicação desktop. Fazer o mesmo com o MC: um
painel do Media Composer falando com o Órbita desktop.

**Como encaixa no que sabemos.**
- Arquitetura idêntica à do [premiere-cep](../premiere-cep/): **painel fino** que lê seleção/estado
  e delega o trabalho ao motor externo (o app Órbita). Migrar a lógica entre NLEs não reescreve o motor.
- Leitura de estado no MC: eventos `onEvent` (BinRowSelectionChanged, MobLoadedInViewer,
  PlayPositionChange, MobAdded/Deleted) + métodos gRPC (`GetBins`, `GetListOfBinItems`,
  `GetMobInfo`, `GetViewerMobs`, `GetOpenProjectInfo`).
- Ação no MC: `LoadMobsIntoViewer`, `SelectMobsInBin`, `CreateBin`, `ImportFile`, `LinkFile`,
  `SetPosition`, `DoCommand`, drop (`DropFromPluginToBin/Composer/Timeline`).
- O `mobId` dos eventos é **MobID/UMID** — o mesmo dos `.avb`/`.aaf`, então casa com o que o Órbita
  já entende de mídia (ver [protocolos/avb](../../protocolos/avb/), [protocolos/aaf](../../protocolos/aaf/)).

**Decisão RESOLVIDA (2026-08-08): app dirigindo o 9100, sem painel.** O palpite anterior ("painel
leve de UI + app falando 9100") caiu por um motivo que só apareceu implementando: **não existe
`Overwrite`/`Insert` com parâmetros**, então a timeline é AUTORADA e não comandada — e autorar não
precisa de painel dentro do NLE. O painel voltaria só por PARIDADE DE GESTO (o editor não sair do
Avid), e esbarra num obstáculo de integração descrito no README: o painel não lê disco, logo não
alcança um app que autentique por segredo em arquivo.

**A IDENTIDADE da mídia decide o caminho — e as duas direções do fluxo pedem portas diferentes**
(2026-08-08). Não é "importada *ou* linkada": é uma por sentido.

| direção | mídia | identidade | como os masters aparecem |
|---|---|---|---|
| **MC → Órbita → MC** (editor já importou) | gerenciada, OP-Atom | `material_package_umid` (= MobID do MasterMob) | **já existem** na bin — basta autorar a composição apontando para os MobIDs e `OpenBin` |
| **Órbita → MC** (sync antes de entrar no Avid) | bruta, fora do MC | o **caminho** do arquivo | `LinkFile` cria os masters AMA (o laço validado acima) |

Ou seja, a mídia linkada não é um workflow marginal: é o **único** caminho possível para o push do
app para o MC. Um campo `identity: {kind:"managed", mob_id} | {kind:"ama", path}` no adapter cobre as
duas com um `if` — o resto da cadeia (mapa de sync → segmentos → autoria → abrir) é idêntico.

⚠️ Ler OP-Atom tem 3 armadilhas medidas (TC que pode ser o do material, `reel_name` que não é o nome
do clipe, e a rota por nome de arquivo que cobre ~7% de um acervo real): ver
[protocolos/mxf](../../protocolos/mxf/README.md) §rota ffprobe.

**Referência.** Implementação análoga: painel `Órbita Sync` do DRAMASYNC (ver premiere-cep/fontes).

---

## 2. Relinker dentro do Media Composer (mudança conceitual) — ✅ **CONSTRUÍDA** (2026-08-10)

> **Estado:** o plugin existe, roda e relinka em escala. Vive em
> `PROGRAMAS COM CLAUDE/_DeLaPraCa` — projeto novo, compondo o **motor** do RELINKER com o
> **shell** do Órbita. Nome do produto: **De Lá Pra Cá**.
>
> ⚠️ **INDO PARA O WINDOWS? Leia [windows.md](windows.md) ANTES.** O De Lá Pra Cá herda o shell
> do Órbita, e o Órbita levou uma sessão inteira (2026-08-15) para atravessar — **nenhum dos
> tropeços deu erro; todos foram silenciosos**. Os que atingem este projeto em cheio, porque ele
> também lê bins e resolve caminhos de mídia:
> **(1)** a coluna `Drive` é `RÓTULO (LETRA:)`, e montar o caminho errado reporta "mídia não
> encontrada" com tudo no lugar ([§6](windows.md)); **(2)** `GetListOfWindows` não existe em MC
> mais antigo, e derruba tudo que vier depois dele na mesma chamada ([§3](windows.md));
> **(3)** `OpenBin` em varredura cobre a tela do editor de bins que ninguém pediu
> ([§6b](windows.md)); **(4)** o painel instala em `%PROGRAMDATA%\Avid\PanelSDKPlugins` e cai no
> menu **Tools**, não em `Extensions` ([§1](windows.md), [§2](windows.md)). E, do lado do
> ambiente de desenvolvimento, a armadilha do `localhost` que custou 5 minutos de tela em branco
> por carregamento →
> [transversal/desenvolvimento-cross-platform](../../transversal/desenvolvimento-cross-platform.md).
>
> ### O que mudou em relação ao que estava planejado abaixo
>
> **A conexão timeline→mídia NÃO precisou ser autorada.** O plano dizia que `build_avb` era o
> caminho, porque o relink nativo não é dirigível. Verdade — mas apareceu uma terceira via:
> **`ImportFile` aceita um AAF**, e com os masters AMA já online (via `LinkFile`) o MC casa por
> MobID e monta a timeline **ele mesmo**. Efeitos, transições, timewarp e estabilizadores ficam
> intactos por construção, sem escrevermos uma linha a respeito — confirmado na GUI por um editor.
>
> `build_avb` deixou de ser o caminho do plugin e ficou como backend do app agnóstico (para quem
> **não tem** o Media Composer).
>
> **Medido, em escala real** (AAF de 1172 segmentos, acervo de `PRODUCAO-A`):
>
> ```
> preparar   118 masters · índice 102 arquivos · match          3,0 s
> aplicar    100/100 LinkFile · 0 falhas                       81,2 s
>            738 subclipes achatados · 44 órfãos removidos
>            100/100 remapeados · 841 referências
>            1121 segmentos cobertos
> ```
>
> Matching: **45/45 masters de imagem** por nome exato. Os 18 não resolvidos **não existem no
> acervo** (conferido) — é o teto real.
>
> ### Decisões que valem além deste plugin
>
> - **Matching por MASTER, não por segmento.** 1172 segmentos → 118 masters. Um master resolvido
>   leva todos os seus segmentos.
> - **Sem confirmação visual dentro do NLE.** O pHash contra vídeo de referência faz sentido num app
>   que roda **fora** do editor. Dentro dele o editor tem a imagem na tela e confere de graça — o
>   matcher não abre um único arquivo de mídia e roda em 0,04 s.
> - **O que resolve o acervo é a NORMALIZAÇÃO de nome, não o fuzzy.** Dos 101 casamentos por nome,
>   100 foram exatos. O único frouxo era falso positivo. Fuzzy virou *sugestão*, nunca decisão.
> - **Achatar subclipes/group clips** é diferencial de entrega **e** a saída para o diálogo modal de
>   conflito na reimportação.
>
> Novos achados de API: `ImportFile_aceita_AAF`, `CreateBin_folder_path`,
> `bins_abertas_precisa_de_avb`, `NAO_varra_o_projeto_para_listar_sequences` em
> [dados/mcapi-grpc.json](dados/mcapi-grpc.json); presets de export e `_EXPORTFORMAT` em
> [dados/export-presets.json](dados/export-presets.json).

### O plano original, para referência

**Objetivo.** Assumir o **relink do Avid** por uma interface amigável, operável **de um painel do
próprio MC** (sem ir ao app). Fluxo: pegar uma timeline numa bin com clipes importados (mesmo
**offline**) e relinká-la à **mídia bruta** com uma UX melhor que a nativa. Com a TL relinkada,
enviá-la a DaVinci Resolve ou Premiere fazendo toda a tradução para chegar certo dos dois lados.

**Por que é rico.** Elimina uma dor real do MC (o relink nativo é áspero) e mantém o usuário no MC,
sem trocar de app.

**Como encaixa no que sabemos.**
- Métodos gRPC diretamente úteis: `GetBins`/`GetListOfBinItems`/`GetMobInfo`/`GetMobTrackInfo`
  (ler a TL e seus clipes, inclusive offline), `GetListOfLinkSettings` + `LinkFile` (o relink AMA),
  `ScanAvidMediaFilesFolder` + `CreateClipsFromAvidMediaFilesFolder`, `GetMediaVolumeList/Items`.
- Casa com o conhecimento de relink já no banco: [protocolos/avb](../../protocolos/avb/) (AMA-link,
  relink por byte-patch/clonagem, automatch AAF↔bin por MobID, tradutor AAF→.avb) e
  [protocolos/msm](../../protocolos/msm/) (`.mdb`/`.pmr`, AMA Management).
- Exportar para outras NLEs: [transversal](../../transversal/) (tradução entre NLEs) +
  [protocolos/drt-drp](../../protocolos/drt-drp/) e [protocolos/prproj](../../protocolos/prproj/)
  (o RELINKER já porta o writer de `.drt`; DRAMASYNC provou o writer portar limpo).
- UI: painel `.avpi`. O motor pesado (parser/relink/tradução) fica no RELINKER, chamado pelo painel
  ou rodando ao lado e dirigindo o 9100.

### Visão estratégica: RELINKER ("De Lá Pra Cá") e os DOIS fluxos (2026-08-08)

**RELINKER será rebatizado "De Lá Pra Cá".** É o **coração e o meio-de-campo** do fluxo offline↔online:
facilita a troca entre NLEs por qualquer motivo — migração da edição no meio do caminho, ou envio
para finalização. **Princípio: agnóstico de software.** Existem dois níveis de fluxo:

**Fluxo IDEAL — via plugin do NLE (MC disponível).** Um AAF de montagem chega ao editor online; ele,
*através do Avid* (o plugin), relinka para a mídia em alta e então envia para, p.ex., o Resolve —
também via plugin (a desenvolver). **Consequência do que provamos hoje:** ter o plugin no Avid
**FECHA o gap** de recriar programaticamente a bin do MC — porque o próprio MC constrói/abre a bin
(via `LinkFile`+`Save`+`OpenBin`); o RELINKER só autora a `CompositionMob` por cima (`build_avb`).
Este fluxo está **tecnicamente validado** (ver LOOP COMPLETO PROVADO abaixo). É o caminho mais
alcançável e a prioridade.

**Fluxo MENOS IDEAL — sem acesso ao NLE.** O editor online tem o AAF da montagem mas **não tem o
Media Composer** (nem o programa de edição original). Aí é preciso **mapear e recriar a bin do zero**
— a autoria byte-surgery completa do `.avb` (masters de mídia + descriptors + composição), sem o MC
para ajudar. Isso está **avançando mas ainda incompleto** (o media-bin builder genérico segue
pendente para este caso; no fluxo ideal ele é substituído pelo `LinkFile`). Ver
[protocolos/avb](../../protocolos/avb/) (autoria/clone/relink de `.avb`).

**Resumo da prioridade:** o plugin (fluxo ideal) resolve o caso comum e já funciona ponta a ponta;
a recriação from-scratch (fluxo sem-NLE) é o problema difícil que continua no radar. O matcher do
RELINKER (`.new.01`/subclip/multicam) serve aos DOIS fluxos — é o cérebro comum.

**Estado do RELINKER.** Em desenvolvimento, **pausado para respirar** (2026-08-07). Hoje é
**file-based/offline**: parseia o AAF (`aaf/parser.py`), casa por cascata (metadados/TC/visual,
independente do UID nativo) e autora uma `.avb` externa (`avb_export/`: `translate.py` monta a
CompositionMob; `clone.py`/`relink.py` fazem byte-surgery clonando masters de mídia AMA-online),
entregando uma bin única 100% relinkada que o usuário importa. O motor de matching é a joia; o
media-bin builder genérico e a UI ainda pendem. Esta seria uma reorientação: de app standalone
para motor por trás de um painel do MC.

### Como aplicar o relink DENTRO do MC — análise (2026-08-07, curiosidade, não-execução)

**Princípio.** O motor de matching do RELINKER é agnóstico de transporte. O painel só troca os
**endpoints**: em vez de "AAF entra → .avb sai (importa na mão)", vira "lê a bin viva → casa →
aplica no MC". Três formas de APLICAR, e a honestidade sobre cada uma:

- **Ler a timeline offline ao vivo (ganho de UX imediato).** `GetBins`/`GetListOfBinItems` acham a
  sequência; `GetMobInfo` (streaming, retorna pares coluna/valor) e `GetMobTrackInfo` leem os masters
  referenciados **mesmo offline** (a bin guarda o metadado: Tape, Start TC, Source File, nome).
  Isso pode **dispensar o export manual de AAF** — o painel lê a estrutura direto. *A confirmar:*
  se `GetMobTrackInfo` dá a edit-list completa (in/out/posições) o bastante para o matcher; se não,
  o painel dispara `ExportFile` (AAF) automaticamente e alimenta o RELINKER — ainda sem passo manual.
- **Trazer a mídia bruta online.** `LinkFile{file_path, destination_bin, link_settings_name}` (AMA
  por arquivo) ou `CreateClipsFromAvidMediaFilesFolder{bin_path, media_folder_path, media_file_path[]}`.
  Cria masters online na bin.
- **Conectar timeline → online — o ponto crítico e ainda em aberto.** Três opções:
  1. **`DoCommand(Relink nativo)`** — só serve se as chaves nativas (Tape+TC / Source File / UID)
     estiverem corretas. Como é justamente isso que falha (razão de existir o RELINKER), o relink
     nativo sozinho não resolve o caso difícil. *A verificar ao vivo:* `GetListOfCommands` tem um
     comando de Relink? Ele aceita alvo/critério ou só abre o diálogo?
  2. **Autorar + abrir** (força atual do RELINKER, movida para dentro): o painel lê a sequência viva,
     o RELINKER monta a `.avb`/sequência corrigida (já sabe fazer) e o painel faz `OpenBin` — sem o
     usuário sair do MC. É "gerar + abrir", **não** re-aponte in-place.
  3. **Re-aponte in-place clipe-a-clipe: NÃO existe na API.** Não há método de relink/repoint;
     `SetMobInfo` só edita **coluna de bin** (metadado), não a fonte de essência. Confirmado do
     `.proto`. Então "substituir a fonte de um clipe existente na sequência" não é exposto.

**Conclusão honesta.** O caminho mais viável hoje é **híbrido**: painel como porta de entrada (lê a
bin viva, UI amigável de review, traz raw online via `LinkFile`) + RELINKER como motor (matching +
autoria da estrutura corrigida) + `OpenBin` para entregar dentro do MC. O sonho de "re-apontar cada
clipe da sequência in-place pela API" não é possível com o mcapi 25.12.

**Experimento 2026-08-08 (decidiu a arquitetura).** Rodamos a metade de leitura inteira via 9100
(OpenBin → GetListOfBinItems → ExportFile do AAF → parse pyaaf2: chaves de matching presentes) e
testamos a metade de escrita com um caso real (sequence offline PRODA_CORTE + `.mp4` brutos):
- `LinkFile` de um `.mp4` **funcionou** (master AMA online, colunas ricas, toca no Source).
- `DoCommand(2202 Relink→Linked Media)` na sequence **NÃO conectou** — a timeline seguiu offline.
- **Motivo decisivo:** o relink nativo usa os *Relink Settings* salvos e **não há como dirigir o
  critério pela API** (DoCommand é parameterless; sem SetRelinkSettings; diálogo não abre headless).
  Como o match nativo é justamente o que falha, o atalho "LinkFile + DoCommand(2202)" **não serve**.

**Decisão:** a CONEXÃO timeline→mídia tem de ser **autorada** pelo RELINKER (`.avb`, força que ele já
tem) e entregue via `OpenBin`. `LinkFile`/`CreateClips` trazem a mídia online. Detalhes em
[dados/mcapi-grpc.json](dados/mcapi-grpc.json) → `workflow_relink_validado`.

**LOOP COMPLETO PROVADO (2026-08-08, fatia mínima de 3 clipes).**
```
sequence offline → ExportFile(AAF) → parse_aaf (RELINKER) → LinkFile(.mp4)+Save (media_bin)
   → media_map {nome→mob_hex via pyavb} → build_avb(...) → OpenBin → ONLINE no MC ✓
```
Autorou `MINIMO_RELINK_TESTE` (13271 frames, 3 pic + 16 snd) e abriu no MC com os 3 clipes online
nas posições certas (resto = gap; clipe sem media_map vira gap, não crasha). **Sinergia-chave
confirmada:** o `LinkFile`+`Save` da API constrói a `media_bin` que era o *media-bin builder genérico*
pendente do RELINKER — o `build_avb` autora por cima e o MC abre online.

**O que falta para produção:** trocar os 3 clipes manuais pelo **matcher completo do RELINKER**
(`.new.01`/subclip/multicam → `media_map` de TODOS os clipes) + `LinkFile` em massa (ou
`CreateClipsFromAvidMediaFilesFolder`). O resto do pipeline está validado e é reaproveitável.

**Confirmado antes:** relink nativo (2202/1813) roda headless mas não-dirigível; `GetMobTrackInfo`
não dá edit-list (por isso o AAF via `ExportFile`); mob_id API vs pyavb difere em byte-order (casar
por nome).

**Downstream (enviar relinkada p/ Resolve/Premiere).** Já coberto: RELINKER tem `drp/`, `otio_export/`,
`aaf/writer.py` e a tradução de [transversal](../../transversal/). O painel só dispara.

---

## 3. Automações de qualidade de vida (botões do dia a dia)

**Objetivo.** Botões no painel para acelerar processos repetitivos de entrega/rotina.

**Caso âncora (real).** Entregar edição em **HDCAM direct-out 8 canais** a partir de um **mix estéreo
2ch**: o estéreo se repete em pares nos canais **1-2, 3-4, 7-8**, deixando **5-6 vazios**. Hoje é
feito na mão; é um roteamento fixo — candidato perfeito a um botão.

**Como encaixa no que sabemos.**
- `GetListOfExportSettings` + `ExportFile` (disparar export com preset), `DoCommand` (comandos por
  `commandId`, ver `GetListOfCommands`), roteamento/track via `GetMobTrackInfo`/`SetMobInfo`.
- Enums de áudio no [.proto](dados/mcapi.proto): `AudioTrackType`, `TrackType` — checar o que o SDK
  expõe de roteamento de canais; se o mapeamento 1-2/3-4/7-8 não sair pela API, cair para preset de
  export + `DoCommand`.
- Eventos `ExportFileStarted/Finished` (+ `taskId`) para acompanhar progresso e avisar o usuário.

**Outros candidatos.** Qualquer rotina fixa e repetitiva de entrega/organização. Coletar à medida
que aparecerem.

**Experimento "bounce/sonorização" (2026-08-08) — plugin DEDICADO, sem RELINKER/AAF.** Caso: copiar
uma timeline mantendo só vídeo + pôr o WAV do bounce em A1-2/3-4/7-8 (5-6 vazias) + export xdcam50.
O que ficou provado e o que travou:
- **Export + preset:** trivial. `xdcam50` existe (`GetListOfExportSettings`); `ExportFile{mob_id,
  export_settings_name}` já validado. **GOTCHA:** o preset "AAF" DESTE projeto estava configurado e
  exportou `.wav` (presets são por-projeto; o nome não garante o formato).
- **Mapa de áudio:** autoria OK. O bounce era 2 trilhas mono (slots 1 e 2, len 617 = a TL). Montei as
  8 trilhas de som (A1/A3/A7→slot1, A2/A4/A8→slot2, A5/A6=Filler) em pyavb sem erro.
- **MURO — preservar o vídeo:** a ideia era duplicar a `edicao.avb` e só trocar o áudio (in-place).
  **Bloqueado:** o resave cru do pyavb é recusado pelo MC (FILE_OPEN_FAILURE) — ver
  [protocolos/avb/escrita.md](../../protocolos/avb/escrita.md) (GOTCHA 2026-08-08). Só o caminho
  `build_avb` (comp NOVO) é aceito. Logo, preservar o vídeo VERBATIM regravando a bin não dá; teria
  de RE-AUTORAR o vídeo por segmentos (build_avb) — o que exige parsear a timeline e cobrir efeitos
  (a "edição" tem Matte Keys; Titler/Matte ainda dropam no RELINKER).
- **Caminhos:** (1) **investigar o writer** pyavb×MC 25.12 (por que build_avb passa e resave não) —
  se destravar, o in-place fica trivial e limpo, e vale para TODAS as automações; (2) **via build_avb**
  (exportar AAF real, parsear, autorar vídeo+bounce) — funciona hoje para a cobertura de efeitos do
  RELINKER, mas acopla ao RELINKER e arrisca fidelidade de efeitos. Áudio e export estão prontos nos
  dois. Recomendação: (1) é a de maior alavancagem.

---

## Notas transversais

- **Onde mora a lógica.** Padrão do ecossistema (ver premiere-cep): painel fino, motor no app. Vale
  para os três — o painel do MC é UI + ponte; o trabalho pesado fica no Órbita/RELINKER ou num
  serviço local que fala 9100.
- **Recarga de painel em dev.** Kit em `~/avid-panel-dev/` (`pack.sh`/`reload.sh`, versão visível).
  Cuidado com o gateway órfão (ver runtime.json → `gateway_orfao_quebra_registro`).
- **Distribuição.** Só o caminho painel+gateway precisa de token/onboarding; automação local usa 9100.

## 🧭 Decisão do autor (2026-10-18) — operar o MC pelo 9100, painel só para o drag-in

Com o Teste B (9100 responde sem token nem painel) e o fechamento da trilha da assinatura (check criptográfico, inviável
forjar), o autor decidiu o rumo:

- **Via principal = gRPC 9100 (externo, sem token).** É o caminho com **mais compatibilidade entre versões** (todas as
  builds com runtime, 23.8.2→25.12.2, expõem o 9100; sobrevive ao filtro de painel do host; dispensa token). Operações
  do De Lá Pra Cá/Órbita migram para 9100 + autoria de `.avb`, numa **janela externa ao MC** (modelo do plugin do Resolve).
- **Painel reduzido a UMA função:** receber o **drag-in** de clipes (os MobIDs só chegam à webview do painel). Para isso,
  base = versão que carrega painel não-assinado (25.12.0/25.6) OU assinatura oficial Avid.
- **Descartado como frágil:** abrir a janela do painel por programação (depende de RPC do host que muda por update; no
  24.6.0 nem existe). E forjar assinatura (check criptográfico — fútil).
- **Risco aceito:** a Avid pode fechar o 9100 num update; hoje é a aposta mais estável. Mitigação: travar a versão do MC
  nas máquinas de produção e testar um cliente 9100 mínimo antes de qualquer atualização.

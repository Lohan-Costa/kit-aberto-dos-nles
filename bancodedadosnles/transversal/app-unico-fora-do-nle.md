# O app único, fora do NLE — o desenho da família, e por que voltamos a ele

> **Decisão do autor**, registrada em 2026-10-21 a partir do que o De Lá Pra Cá provou em 2026-10-18/19
> (Windows 11, MC 24.6.0, Premiere 23.6, Resolve Studio 19.1.4). Vale para **todos os apps de NLE da família**:
> De Lá Pra Cá (feito), Órbita e Ciclo Assist (em adaptação, 2026-10-21), e os que vierem.
> Esta página é o MAPA: cada linha aponta para a medição que a sustenta. O que não tem medição está marcado.

## O desenho em uma frase

**Um app, uma janela, servindo os três NLEs por fora.** O editor só interage com a janela do app; dentro do NLE
não há painel de interface. Se um NLE exigir algo instalado nele, é só uma **ponte** que abre a conexão e não tem tela.

```
                 ┌──────────────────────── janela do app (Tauri, WebView2/WKWebView) ───────────────────────┐
                 │  toda a interface · alvo NATIVO de arrasto · o X pergunta se há trabalho em andamento     │
                 └───────────────┬──────────────────────────┬──────────────────────────┬───────────────────┘
                                 │ gRPC 127.0.0.1:9100       │ HTTP local (long-poll)   │ API Python externa
                                 ▼ sem token, sem painel     ▼ ponte CEP INVISÍVEL      ▼ (fuscript), sem WI
                          Media Composer               Premiere Pro                DaVinci Resolve Studio
```

## Por que voltamos a ele (o painel dentro do NLE está saindo)

A família começou com app único (o Órbita sempre teve janela). Os painéis dentro do NLE vieram em 2026-08 com o
Panel SDK do Avid. Voltamos ao app único por estes motivos:

1. **⛔ O Media Composer não aceita painel não registrado, e esse caminho se fechou.** Começamos por sorte nas
   ÚNICAS versões que deixavam: painel não-assinado só aparece do **25.6 ao 25.12.0**. No **24.6.0** e no **25.12.2**
   ele não aparece (o host filtra a lista em `MCLoaderService::GetPluginList`). O **2021.12** e o **2022.12** nem têm o
   motor de painéis; ele só chega completo no 2023.8.2. A assinatura é verificada de verdade, por criptografia (Go
   `zipdsign` no gateway, cadeia até a DigiCert G4 embutida no binário): copiar a de um parceiro ou assinar com chave
   própria não passa. A brecha do `CIT_OVERRIDE.FTF` fica atrás de um teste de tipo de build que a versão release não
   satisfaz. Destravar só com patch no exe da Avid, o que foi descartado. Medições:
   [ativar-no-2021-ftf.md](../plugins/avid-panel-sdk/ativar-no-2021-ftf.md) (tabela de versões, trilha da assinatura) ·
   [arquitetura.md](../plugins/avid-panel-sdk/arquitetura.md).
2. **⭐ A integração não depende mais do painel. Com o REA, vamos por dentro quando precisar.** A API de controle do MC
   (9100) responde de fora com o painel escondido. O que só o painel parecia dar (o ARRASTO da bin com a identidade do
   clipe) foi interceptado **sem painel e em qualquer versão**: Frida pelo REA, gancho em `Qt5Core!QMimeData::setData`.
   E a decompilação (Ghidra pelo REA, mais parsing dirigido com `pefile`/`capstone` quando o binário é grande demais)
   explica como o NLE faz as coisas. ⇒ Uma necessidade de integração nova vira investigação com o REA, não um painel
   novo. Ver [ferramentas-de-desenvolvimento.md](ferramentas-de-desenvolvimento.md) §REA.
3. **Duas superfícies confundem o editor.** Com painel no NLE e janela do app, o editor lida com duas janelas e pode
   fechar a que mantém a conexão. O app de pé é condição para tudo funcionar (autor, 2026-10-19).
4. **A janela do app não tem as amarras do painel:** nem o Chrome do hospedeiro (QtWebEngine no Avid, CEP no Premiere),
   nem a largura de ~400 px, nem a repintura do QtWebEngine. A mesma interface serve os três NLEs.
5. **O Premiere estável não carrega UXP**, e o CEP está em fim de vida. Uma ponte invisível e fina é barata de trocar
   quando o Premiere mudar; uma interface inteira dentro dele não é.

## A rota de cada NLE

| NLE | como o app fala | o que fica instalado no NLE | medição | Mac |
|---|---|---|---|---|
| **Media Composer** | gRPC `127.0.0.1:9100` (`mcapi.MCAPI`), `RequestHeader` vazio: **sem token, sem painel**. O gateway 4920/4930 é autenticado e só serve painel, então não se usa | nada | [ativar-no-2021-ftf.md §Teste B](../plugins/avid-panel-sdk/ativar-no-2021-ftf.md) · [operacoes-de-nle.md](operacoes-de-nle.md) · [arquitetura.md](../plugins/avid-panel-sdk/arquitetura.md) | 25.12.0: 60/60 RPC `confirmado` |
| ↳ MC **24.6** (o instalado nas máquinas de trabalho) | subconjunto do contrato: `GetViewerMobs` sem `view_type`, sem `DoCommand` nem `MakeViewerActive`, `GetListOfWindows`/`GetListOfCommands` = UNIMPLEMENTED, `LinkFile` recusa acento, BWAV com TC abre modal | — | [ativar-no-2021-ftf.md](../plugins/avid-panel-sdk/ativar-no-2021-ftf.md) (blocos do 24.6, apesar do nome do arquivo) | — |
| ↳ **arrastar da bin para o app** | **alvo NATIVO** de arrasto na janela (`_DeLaPraCa/app/src-tauri/src/arrasto_win.rs`: `IDropTarget` próprio, `SetAllowExternalDrop(false)`, lê só `text/x.avid.mc-api-asset-list+json` ou `CF_HDROP`). ⛔ Soltar no drop comum do WebView2 faz o MC **exportar** um AAF com modal que trava | — | [arrastar.md](../plugins/avid-panel-sdk/arrastar.md) (fim: "Soltar timeline do MC numa WEBVIEW comum") | `pendente` |
| ↳ arrastar uma **bin** | ⛔ a identidade da bin não sai no arrasto, em fase nenhuma. Ler e vigiar a pasta do projeto (pyavb) | — | [arrastar.md](../plugins/avid-panel-sdk/arrastar.md) §4 e blocos Frida | — |
| **Premiere Pro** | o app serve a página da ponte; a extensão CEP **invisível** (`AutoVisible=false`, `StartOn`, sem Node) só navega para ela; long-poll + `evalScript` (2,5–4,9 ms por volta). Script fora do HTML (a CSP do serviço recusa inline) | a extensão-ponte (sobe a cada abertura: é o produto) | [painel-servido-e-identidade.md §1, §2, §5, §7c](../plugins/premiere-cep/painel-servido-e-identidade.md) | ponte invisível `confirmado` no 25.6.5; a do DLPC `pendente` |
| **DaVinci Resolve Studio** | API Python **externa** (`fuscript`/`DaVinciResolveScript`). Sem Workflow Integration. Só o Studio (o gratuito não aceita script externo) | nada | [api-scripting.md](../plugins/resolve-scripting/api-scripting.md) (blocos de 2026-10-18/19: 48/48 chamadas por fora, montagem completa) | 21.1 externo `confirmado` |
| **a janela** | Tauri 2, janela única que lembra a posição na área útil do monitor; o X pergunta ao painel | — | [matriz-de-plataforma.md](matriz-de-plataforma.md) (linha "Tauri 2: janela única") | `pendente` |

Implementação de referência: **De Lá Pra Cá** (`9 ARQUIVADOS/_DeLaPraCa`): `app/src-tauri/src/{lib.rs,arrasto_win.rs}`,
`servico/avid/{mcapi.py,acoes.py}`, `plugins/premiere/cep/`, `premiere_ponte.py`, `ui/premiere_ponte.js`,
`resolve_externo.py`. Portar daqui antes de reescrever.

## O que muda para cada app (2026-10-21)

| app | hoje | falta |
|---|---|---|
| De Lá Pra Cá | ✅ no desenho (o `.avpi` e a casca WI saindo) | Mac inteiro `pendente` |
| Órbita | 🆕 2026-10-21: o painel na **janela do app** (`?casca=app`). **Premiere 23.6** pela ponte invisível (sync → sequência/merged). **MC 24.6** pelo 9100 + arrasto nativo: bin → fontes → sync → bin com a sequência; Subclipar (subclipes numa bin e bins por cena) pela subaba da janela — tudo pilotado na D02 da PRODUCAO-A | Resolve por fora; o painel no Mac; timeline do MC em branco depois de montar (recarregar resolve) |
| Ciclo Assist | 🆕 2026-10-21: **janela Tauri** (`app/src-tauri`, a casca do DLPC enxugada) com o serviço 7824 (`--app`/`--pai`). **MC 24.6** pela janela: conversa, arrasto nativo das três origens (sintético pelo piloto, sem export de AAF). **Premiere 23.6** pela ponte INVISÍVEL (`ponte_cep/` → `/premiere/ponte`): conversa e arrasto de PASTA da bin (seleção lida pela ponte); a janela troca de NLE pela `/conexao` | o duplo clique da Busca no Premiere pela janela; Resolve; Mac. Plano: `_CICLO ASSIST/docs/plano/2026-10-18-app-sem-painel.md` |

## 🆕 2026-10-21 (noite) — o GUARDA-CHUVA do Ciclo Assist: os apps como abas (`confirmado`, Windows 11)

Decisão do autor: o Ciclo Assist é um guarda-chuva de quatro abas — Preparar (Órbita) · Assistir · Conformar (De Lá
Pra Cá) · Entregar (Promo Entrega) —, cada aba um app desenvolvido no repo dele. Fase de COMPOSIÇÃO (a cópia importada
vem na unificação): uma janela Tauri com uma **webview filha por aba** (`Window::add_child`, feature `unstable` do
Tauri 2.11.5), cada uma no painel servido pelo motor do módulo. Lições que valem para a família:
- **O mesmo alvo nativo de arrasto serve às webviews filhas**: `SetAllowExternalDrop(false)` em CADA controller e
  `RegisterDragDrop` na janela e em todas as filhas, DEPOIS de criá-las (webview criada depois traz o drop do WebView2,
  que pede o arquivo — o export de AAF do MC). O aviso vai por `eval` à webview da aba visível, com o y descontado da
  barra. Como os três apps vieram da mesma cópia do `arrasto_win.rs`, o formato do aviso é o mesmo e nenhum módulo
  mudou (`cicloArrasto` · `orbitaArrasto` · `delapracaArrasto`).
- **O motor de um app Tauri sem a janela dele**: o Órbita ganhou `--motor` (servidor + sidecar, sem o Painel).
- **Os recados da página remota para a janela** (`--app <exe>` + `single_instance`) funcionam igual com o motor de
  OUTRO app: o De Lá Pra Cá reinvoca o executável do guarda-chuva com `--fixar-mc`/`--janela-larga`/`--encerrar`, e
  ele atende.
- Medido: três motores (7817, 7823, 7824) atendendo em 7–8 s; trocar de aba é esconder/mostrar, sem recarregar.
- ⭐ **O contrato de quem entra no guarda-chuva** (autor, 2026-10-21: a moldura é UMA): a página do painel aceita
  `?embutido=1` — esconde a própria moldura (conexão, pino, engrenagem, assinatura; o guarda-chuva mostra as dele) —
  e expõe `window.cicloEmbutido.configuracoes()`, que vai e volta das configurações dela (a engrenagem única do
  guarda-chuva chama na aba visível). Feito no Assist, no Órbita e no De Lá Pra Cá; o Promo Entrega, quando entrar.
  `configuracoes(false)` FECHA e volta à subaba de antes: o guarda-chuva chama assim no app que SAI de vista (sem
  isso, voltar à aba mostrava os ajustes no lugar do trabalho — visto pelo autor). E as **subabas** de cada app têm a
  MESMA régua (a do De Lá Pra Cá): barra recuada 11 px, linha de 1 px, 10 px antes do conteúdo; botão de 12 px em
  negrito com 8 × 12 px; a ativa sublinhada no verde-água do guarda-chuva (#4cc4b8). As subabas: Preparar = Órbita ·
  Subclipar · Renomear; Assistir = Assistir · Buscar · Vetores; Conformar = De Lá Pra Cá · Daqui Pra Lá.
- ⚠️ Pilotando: clicar no NOME de um item JÁ selecionado (bin do MC ou do Premiere) abre a edição do nome, e o
  arrasto seguinte seleciona TEXTO. Arraste pelo ícone; Esc só fecha a edição com o foco DENTRO do campo.

## 🆕 2026-11-02 — o SUPERVISOR: com o guarda-chuva aberto, todos os motores no ar (`confirmado`, Windows 11)

Decisão do autor: *"se o ciclo assist está on, todos os apps do conjunto devem estar tbm… se houver uma falha em um
deles devem ser reiniciados sozinhos, e se não puderem subir, devemos avisar ao usuário"*. Ciclo Assist
`app/src-tauri/src/supervisor.rs`:

- Vigia a PORTA de cada motor (7817 Órbita, 7824 Assist, 7823 De Lá Pra Cá — a tabela `Modulo::motor`: módulo novo
  entra sem código a mais) a cada 3 s (1 s com algum subindo). Caiu → mata o que sobrou, sobe outro, a aba vai à
  página local "religando…" e volta ao painel quando a porta abre. MEDIDO: De Lá Pra Cá morto → no ar de novo em **1,9 s**.
- ⛔ Teto: 3 religadas em 10 min; depois, `falhou` com o motivo, aviso âmbar NO TOPO (visível de qualquer aba) que é o
  próprio botão "tentar de novo" (zera a conta), e ponto âmbar na aba. Subindo há 90 s sem porta = tentativa falha.
- ⛔ Trava de ENCERRAMENTO antes de `parar_motores`: sem ela, fechar o app religaria o que ele acabou de matar.
- O estado vai a `<dados do Assist>/motores.json` a cada pulso: o serviço Python lê (`servico/conjunto.py`) e o
  conselho do executor de fluxos o recebe — com ele, "o De Lá Pra Cá não respondeu" + "agora no ar" vira
  `tentar_de_novo` (antes: "abra a aba e me avise").
- ⚠️ No Windows, matar o Python que segura a porta faz o LANÇADOR do venv sair junto: o `try_wait` do filho vê a
  saída. ⚠️ Motor que escuta e não responde (travado) NÃO é detectado — só a porta é vigiada. Mac: `pendente`.

## Armadilhas que já custaram caro

- ⛔ Painel não-assinado **some em silêncio** no MC: não há erro, o menu Extensions simplesmente não lista. Não
  diagnosticar pelo pacote; ver a versão primeiro.
- ⛔ O drop do WebView2 com material do MC = export de AAF com modal (trava até o Explorer).
- ⛔ Dois hifens num comentário do manifesto CEP matam a extensão, também em silêncio.
- ⚠️ Instalada, a ponte do Premiere roda **toda vez** que o Premiere abre. Instrumento de teste se desinstala no `finally`.
- ⚠️ O app de pé é condição: com ele fechado, nenhum NLE tem com quem falar. A janela não abre sozinha
  (decisão do autor: "sempre decisão do usuário").

## 🆕 2026-10-21 — o Órbita no desenho (Premiere `confirmado`; MC `pendente`)

O Órbita abre no **painel** (a página do painel do Avid servida pelo app, `?casca=app`) e a interface antiga virou o
"Órbita Studio". Premiere 23.6 (Windows) pela ponte invisível, ponta a ponta: arrasto de clipes E PASTAS da bin →
fontes (agrupadas pela BIN de origem) → sync → sequência montada pela ponte → marcadores de revisão. Lições que valem
para a família:
- ⛔ **servidor de UMA thread não pode segurar o long-poll da ponte** (o Órbita usa `tiny_http`): long-poll numa thread
  própria e chamada em duas etapas (enfileira → pergunta o resultado). No De Lá Pra Cá (Python, threads por pedido) o
  problema não aparece.
- ⛔ o formato do arrasto do Premiere traz o PID (`Adobe<PID>/Premiere/ProjectItem`) — ver
  [arrastar-e-selecao.md §6d](../plugins/premiere-cep/arrastar-e-selecao.md). ⚠️ O De Lá Pra Cá ainda tem o nome fixo.
- a PASTA da bin é a melhor evidência de "qual câmera" (o esqueleto do nome junta câmeras de nome igual).

## 🆕 ⭐⭐ UMA ponte no Premiere para vários módulos — `confirmado` (2026-11-07, Premiere 26.0.2, macOS 15.6)

- Três apps da família tinham, cada um, a SUA extensão CEP invisível (mesmo desenho: `Custom`, sem tela, acorda no
  `applicationActivate`, long-poll no serviço dele). No Ciclo Assist viraram UMA: a página da ponte avalia os três
  `host.jsx` CONCATENADOS (138 KB) numa avaliação só, e os outros serviços pedem a chamada ao serviço dono da ponte
  (`POST /nucleo/premiere/chamar`, token num arquivo 0600, cada módulo só chama o próprio PREFIXO).
- ⛔ A condição medida antes: **nenhum nome de topo em comum** entre os scripts (49 + 58 + 20 nomes; prefixos `ciclo*`,
  `sinc*`, `dlpc*`). No ExtendScript global o último a declarar ganha CALADO — sem prefixo, não junte.
- Provado: Premiere reaberto com UMA extensão nossa; os três serviços leram o Premiere por ela. A fila continua de
  um pedido por vez, com a prioridade do gesto do editor sobre o trabalho de fundo (a marca viaja no pedido).
- Implementação: `_CICLO ASSIST/cicloassist/servico/nucleo.py`, `cicloassist/nle/premiere::host_jsx_inteiro`,
  `cicloassist/integracoes.py` (o instalador que tira as antigas com cópia).

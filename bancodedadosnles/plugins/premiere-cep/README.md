# Plugins — Premiere Pro (CEP)

Como fazer um PAINEL que roda DENTRO do Premiere e dirige um app externo. Não é um formato
de arquivo (por isso vive em `plugins/`, não em `protocolos/`) — é a API de scripting/UI do
editor. Fatos consumíveis em [dados/api-metodos.json](dados/api-metodos.json). As regras
narradas (e as armadilhas) em [api-extendscript.md](api-extendscript.md). Rastreabilidade em
[fontes.md](fontes.md). Confiança geral: **confirmado** (Premiere 25.6.5, macOS, 2026-07-26).

Primeiro plugin do ecossistema (o `Órbita Sync` do DRAMASYNC). Não será o último — DaVinci
Resolve entra em `plugins/resolve/` no mesmo nível, com a mesma arquitetura de painel fino.

⭐ **Validação externa:** [eddie-ai-arquitetura.md](eddie-ai-arquitetura.md) dissecou o **Eddie AI**
(2026-08-09) — assistente de decupagem em produção que escolheu a MESMA arquitetura de painel fino,
com o fio na direção INVERTIDA (o painel SERVE em `127.0.0.1:61202`, o app conecta) e o motor na
nuvem. Leia antes de decidir direção de conexão, autoatualização de painel ou o que subir de mídia
— inclui os três caminhos que ele usa para entregar corte à timeline.

## CEP vs UXP — qual usar

- **UXP** é o padrão novo (Premiere 2026 / Beta). Mas o **Premiere ESTÁVEL (25.6.x) NÃO carrega
  UXP** — o UDT dá "Host Application not available"; só o Beta (25.x) ou o 2026 (26.x) + Developer
  Mode carregam. → Para rodar HOJE no editor estável do usuário: **CEP**.
- **CEP** é o sistema antigo (deprecado ~1 ano, mas maduro e presente no estável). Tem **Node**
  (faz `fetch` de rede, inclusive `127.0.0.1`) + **ExtendScript** (lê a seleção da bin, monta a
  timeline). O painel é NLE-agnóstico do lado do motor — migrar CEP→UXP não perde o servidor.

## Arquitetura: painel FINO + motor externo

O painel NÃO tem lógica de domínio. Ele: (1) lê a seleção da bin, (2) manda os caminhos por HTTP
para o app (Órbita) rodando em background (`127.0.0.1:7817`), (3) recebe o resultado e monta a
sequência NATIVAMENTE. Motivo: **atualizar o motor sem republicar o painel** — o pesado viaja
com o app. O `fetch` para localhost funciona
(**confirmado**; o servidor responde com CORS `*`).

⚠️ **"O CEP sandbox não spawna processo" — AFIRMAÇÃO SOB REVISÃO (2026-08-09).** O bundle do
**Premiere Copilot** usa `window.require("child_process")` (`spawn`/`exec` de `pbpaste`, `open -R`,
`powershell`) em produção, com o **mesmo** `--enable-nodejs --mixed-context` que nós usamos —
ver [premiere-copilot-arquitetura.md](premiere-copilot-arquitetura.md). Não medimos que funciona
(`hipotese`) — teste de 5 min pendente.

⛔ **Mas isto NÃO é um convite a mover o motor para dentro do painel.** Decisão do usuário
(2026-08-09): **motor dentro do painel só serve a produto de UM NLE só.** O Órbita/DRAMASYNC é
multi-NLE por objetivo (Premiere + Resolve + Media Composer) e **continua com o motor no app
externo** — o painel fino é o que permite os três compartilharem o mesmo motor, e o Avid não tem
Node nenhum ([`../avid-panel-sdk/`](../avid-panel-sdk/): o painel é QtWebEngine e **não lê disco**).
Trocar isso por ganho de instalação seria pagar com a portabilidade, que é o ativo.
**Onde o achado VALE:** quando decidirmos fazer algo deliberadamente só-para-Premiere, aí um plugin
standalone (painel + motor, instalação única) passa a ser opção real.

## Instalar (painel não-assinado)

Duas coisas obrigatórias:
1. **Pasta de extensões CEP** (copiar/symlink — o CEP **segue symlink**, confirmado até em volume
   externo):
   - macOS: `~/Library/Application Support/Adobe/CEP/extensions/<bundle-id>/`
   - Windows: `%APPDATA%\Adobe\CEP\extensions\<bundle-id>\`
2. **PlayerDebugMode** ligado (o Adobe só carrega painel não-assinado com ele):
   - macOS: `defaults write com.adobe.CSXS.<N> PlayerDebugMode 1`
   - Windows: `reg add HKCU\Software\Adobe\CSXS.<N> /v PlayerDebugMode /t REG_SZ /d 1 /f`
   - `<N>` = versão da API CSXS; varia por Premiere (25.x usa 11/12). Ligar 10/11/12 é inócuo.

Alternativa "profissional": **ZXP assinado** (cert self-signed via `ZXPSignCmd`) dispensa o
PlayerDebugMode; distribui por `ExManCmd`/Adobe Exchange. Mais setup. Para Alpha, o instalador
embutido no próprio app (copia os arquivos + liga o PlayerDebugMode) é mais simples e cross-platform.

## Manifesto (CSXS/manifest.xml)

- `<Host Name="PPRO" Version="[14.0,99.9]"/>` — faixa ampla cobre 25.x+.
- `RequiredRuntime CSXS 9.0` — roda em CEP 9..12 (máxima compat).
- `CEFCommandLine`: `--allow-file-access`, `--allow-file-access-from-files`, `--enable-nodejs`.
- `ScriptPath` (o `.jsx`) é carregado quando o painel abre → **fechar+reabrir o painel recarrega
  HTML/JS/JSX**. Editou o `.jsx`? Reabra o painel.
- ⭐ [`painel-servido-e-identidade.md`](painel-servido-e-identidade.md) — **a página servida por HTTP tem `__adobe_cep__`** (loader + interface servida, como o `.avpi`), extensão invisível com `StartOn`, proxy e OP-Atom vistos pelo item (23.2 Windows, 2026-09-17)
- [`arrastar-e-selecao.md`](arrastar-e-selecao.md) — ⭐ **o arrasto da bin para o painel CEP NÃO entrega nada** (o do Finder entrega, com `files[].path`); e a tabela adversarial do que uma seleção de bin devolve (sequência e camada de ajuste se declaram `type = CLIP`)

## ⚠️ O Chromium do CEP no Premiere 2023 não conhece `color-mix()` (2026-09-17)

Observado pelo autor no 23.2 (Windows): a linha selecionada da tabela do Órbita, pintada com
`background: color-mix(in srgb, var(--accent) 28%, transparent)`, **não ganhava destaque
nenhum** — a declaração inválida é descartada em silêncio e o clique parece não funcionar
(a seleção existia; só não aparecia). `color-mix` chegou no Chrome 111; o CEP 11 é bem
anterior. Em painel CEP, use `rgba(...)` literal para o que precisa aparecer.
`inferido` pela versão do Chromium; o conserto com `rgba` ainda não foi visto na tela.
